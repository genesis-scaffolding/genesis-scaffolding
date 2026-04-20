from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter, PathCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from .commands import COMMAND_MAP
from .streaming import CLIStreamHandler


class ChatSession:
    def __init__(self, agent, console):
        self.agent = agent
        self.console = console
        self.stream_handler = CLIStreamHandler(console)
        self.should_exit = False

        self.bindings = KeyBindings()
        self._setup_bindings()

        self.prompt_session = PromptSession(
            completer=self._setup_completer(),
            style=Style.from_dict(
                {
                    "completion-menu.completion": "bg:#008888 #ffffff",
                    "completion-menu.completion.current": "bg:#00aaaa #000000",
                },
            ),
        )

    def _setup_completer(self):
        """Builds the autocomplete tree for slash commands."""
        return NestedCompleter.from_nested_dict(
            {
                "/exit": None,
                "/quit": None,
                "/clipboard": None,
                "/add": PathCompleter(expanduser=True),
                "/remove": None,
            },
        )

    def _setup_bindings(self):
        """Customizes keyboard behavior.
        """

        # Handle the ENTER key
        @self.bindings.add("enter")
        def _(event):
            buffer = event.current_buffer

            # Case A: If the completion menu is open and an item is highlighted
            # Just accept the completion, don't submit yet.
            if buffer.complete_state:
                buffer.apply_completion(buffer.complete_state.current_completion)
                return

            # Case B: If it's a slash command (single line usually)
            # or if you just want Enter to always submit:
            buffer.validate_and_handle()

        # Handle Shift+Enter (or Alt+Enter as a fallback) for New Lines
        # Note: 'escape', 'enter' is how prompt_toolkit identifies Alt+Enter
        @self.bindings.add("escape", "enter")
        def _(event):
            event.current_buffer.insert_text("\n")

    async def start(self):
        """The main interactive loop."""
        while not self.should_exit:
            try:
                # 1. Get User Input (Multi-line + Autocomplete)
                # Use patch_stdout so Rich prints don't break the prompt
                # Use await prompt_async() instead of prompt()
                with patch_stdout():
                    user_input = await self.prompt_session.prompt_async(
                        HTML("\n<ansiyellow><b>You</b></ansiyellow> > "),
                        complete_while_typing=True,
                        multiline=True,
                    )

                if not user_input:
                    continue

                # 2. Handle Slash Commands
                if user_input.startswith("/"):
                    parts = user_input.split(maxsplit=1)
                    cmd = parts[0].lower()
                    args = parts[1] if len(parts) > 1 else ""

                    handler = COMMAND_MAP.get(cmd)
                    if handler:
                        await handler(self, args)
                    else:
                        self.console.print(f"[red]Unknown command:[/red] {cmd}")
                    continue

                # 3. Standard Agent Execution
                self.stream_handler.reset()

                await self.agent.step(
                    input=user_input,
                    stream=True,
                    content_chunk_callbacks=[self.stream_handler.handle_content],
                    reasoning_chunk_callbacks=[self.stream_handler.handle_reasoning],
                    tool_start_callback=[self.stream_handler.handle_tool_start],
                    tool_result_callback=[self.stream_handler.handle_tool_result],
                )

                # Cleanup UI after response finishes
                self.stream_handler.stop_live()

            except EOFError:  # Ctrl+D
                break
            except KeyboardInterrupt:
                self.stream_handler.stop_live()
                continue
            except Exception as e:
                self.stream_handler.stop_live()
                self.console.print(f"\n[bold red]Error:[/bold red] {e}")
