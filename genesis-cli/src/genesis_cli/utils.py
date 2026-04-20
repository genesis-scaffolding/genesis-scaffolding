from genesis_core.schemas import WorkflowEvent, WorkflowEventType
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table


class RichWorkflowRenderer:
    def __init__(self, console: Console):
        self.console = console
        # This holds the active spinner state
        self.status: Status | None = None

    async def __call__(self, event: WorkflowEvent):
        if event.event_type == WorkflowEventType.STEP_START:
            # 1. Start the spinner
            if not self.status:
                self.status = self.console.status(f"[bold cyan]Executing {event.step_id}...[/bold cyan]")
                self.status.start()
            else:
                self.status.update(f"[bold cyan]Executing {event.step_id}...[/bold cyan]")

        elif event.event_type == WorkflowEventType.STEP_COMPLETED:
            # 2. Stop the spinner temporarily to print the result panel
            if self.status:
                self.status.stop()
                self.status = None

            # 3. Create the result table
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Key", style="dim")
            table.add_column("Value", style="green")

            if isinstance(event.data, dict):
                for k, v in event.data.items():
                    val_str = str(v)
                    display_v = (val_str[:97] + "...") if len(val_str) > 100 else val_str
                    table.add_row(k, display_v)

            self.console.print(
                Panel(
                    table,
                    title=f"[bold green]✓ {event.step_id} Success[/bold green]",
                    title_align="left",
                    border_style="green",
                ),
            )

        elif event.event_type == WorkflowEventType.ERROR:
            if self.status:
                self.status.stop()
            self.console.print(f"\n[bold red]Error in {event.step_id}:[/bold red] {event.message}")
