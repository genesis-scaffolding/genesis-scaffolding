import os
from pathlib import Path

import pathspec
from rich.panel import Panel


def _find_gitignore(start_path):
    """Climb up the directory tree to find a .gitignore file."""
    curr = start_path.absolute()
    for parent in [curr, *curr.parents]:
        git_ignore = parent / ".gitignore"
        if git_ignore.exists():
            return git_ignore
    return None


async def handle_exit(session, args):
    session.should_exit = True


async def handle_clipboard(session, args):
    content = session.agent.get_clipboard().get("content", "Empty")
    session.console.print(Panel(content, title="Clipboard Content", border_style="blue"))


async def handle_add_file(session, args):
    if not args:
        session.console.print("[red]Error:[/red] Usage: /add <path> [--force]")
        return

    path = Path(args.strip().strip("'\"")).expanduser().resolve()

    if not path.exists():
        session.console.print(f"[red]Error:[/red] Path not found: {path}")
        return

    # 1. Prepare Gitignore logic
    spec = None
    # Look for .gitignore in the current directory or parent directories
    gitignore_path = _find_gitignore(path)
    gitignore_root: Path | None = None
    if gitignore_path:
        with open(gitignore_path) as f:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", f)
        gitignore_root = gitignore_path.parent if gitignore_path else None

    # 2. Collect files to add
    files_to_add = []

    if path.is_file():
        files_to_add.append(path)
    elif path.is_dir():
        for root, dirs, files in os.walk(path):
            # Optimization: prevent walking into .git folders
            if ".git" in dirs:
                dirs.remove(".git")

            for file in files:
                full_path = Path(root) / file

                if spec and gitignore_root:
                    # We need the path relative to where the .gitignore is located
                    # for accurate matching
                    rel_path = full_path.relative_to(gitignore_root)
                    if spec.match_file(str(rel_path)):
                        continue

                files_to_add.append(full_path)

    # 3. Add the files to the agent
    if not files_to_add:
        session.console.print("[yellow]No files found (or all files were ignored).[/yellow]")
        return

    for f in files_to_add:
        try:
            await session.agent.add_file(f)
            session.console.print(f"[bold green]✔[/bold green] Added [cyan]{f}[/cyan]")
        except Exception as e:
            session.console.print(f"[red]Failed to add {f}:[/red] {e}")

    session.console.print(f"\n[bold green]Finished adding {len(files_to_add)} file(s).[/bold green]")


async def handle_remove_file(session, args):
    if not args:
        session.console.print("[red]Error:[/red] Usage: /remove <path> [--force]")
        return

    path = Path(args.strip().strip("'\"")).expanduser().resolve()
    removed_files = await session.agent.remove_files(path)
    if not removed_files:
        session.console.print("[yellow]No files found to remove.[/yellow]")
        return

    for f in removed_files:
        session.console.print(f"[bold green]✔[/bold green] Removed [cyan]{f!s}[/cyan]")


# Map of commands to their handler functions
COMMAND_MAP = {
    "/exit": handle_exit,
    "/quit": handle_exit,
    "/clipboard": handle_clipboard,
    "/add": handle_add_file,
    "/remove": handle_remove_file,
}
