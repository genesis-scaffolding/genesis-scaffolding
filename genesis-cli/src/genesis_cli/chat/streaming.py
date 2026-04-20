from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text


class StreamingDisplay:
    """A dedicated class that Rich knows how to render.
    It acts as a 'data container' that Rich polls for updates.
    """

    def __init__(self):
        self.content = ""
        self.reasoning = ""

    def __rich__(self):
        """This magic method is called by Rich whenever it refreshes the screen."""
        renderables = []
        if self.reasoning:
            renderables.append(Text(f"🔍 {self.reasoning}", style="italic grey50"))

        if self.content:
            if self.reasoning:
                renderables.append(Text(""))  # Spacer
            renderables.append(Markdown(self.content))

        return Group(*renderables)


class CLIStreamHandler:
    def __init__(self, console: Console):
        self.console = console
        self.display = StreamingDisplay()
        self.live = None

    async def handle_reasoning(self, chunk: str):
        if not self.live:
            self.start_live()
        self.display.reasoning += chunk
        # Note: We do NOT call update() here. Rich polls the 'display' object automatically.

    async def handle_content(self, chunk: str):
        if not self.live:
            self.start_live()
        self.display.content += chunk

    async def handle_tool_start(self, name: str, args: dict):
        self.stop_live()
        self.console.print(f"\n[bold green]🛠️  Executing {name}...[/bold green] [dim]({args})[/dim]")

    async def handle_tool_result(self, name: str, args: dict):
        self.stop_live()
        tool_result = args.get("result", "")
        self.console.print(
            f"\n[bold green]🛠️  Finished executing tool {name}...[/bold green] [dim]({tool_result})[/dim]",
        )

    def start_live(self):
        if not self.live:
            # We pass the 'display' object itself.
            # Because it has a __rich__ method, Rich knows how to draw it.
            self.live = Live(
                self.display,
                console=self.console,
                refresh_per_second=10,  # Steady 10 FPS, no bursts, no flicker
                transient=False,
                vertical_overflow="visible",
                auto_refresh=True,
            )
            self.live.start()

    def stop_live(self):
        if self.live:
            # 1. Final update to the current Live block
            self.live.update(self.display, refresh=True)
            # 2. Close the Live context (pins the text to terminal history)
            self.live.stop()
            self.live = None

            # Clear the buffers immediately after pinning.
            # This ensures the NEXT time start_live() is called (even in the same turn),
            # we don't re-print the reasoning from the previous step.
            self.display.content = ""
            self.display.reasoning = ""

    def reset(self):
        """Clears everything for a new prompt."""
        self.stop_live()
        self.display.content = ""
        self.display.reasoning = ""
