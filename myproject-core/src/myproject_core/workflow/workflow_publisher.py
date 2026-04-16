import asyncio
import shutil
from pathlib import Path
from typing import Any

from ..schemas import JobContext, OutputDefinition


class OutputPublisher:
    """Copies output files from a completed workflow's job directory to the user's working directory."""

    def __init__(self, working_directory: Path):
        self.working_directory = working_directory

    async def publish(
        self,
        output_definitions: dict[str, OutputDefinition],
        workflow_result: dict[str, Any],
        resolved_destinations: dict[str, str | None],
        job_context: JobContext,
    ) -> None:
        """
        Copy output files to the user's working directory based on destination declarations.

        - If an output's value resolves to a Path (string that is an existing file in the job output),
          copy it to working_directory / destination (as a file).
        - If an output's value resolves to a list of Paths,
          copy each file into working_directory / destination / (as a directory).
        - If destination is None, skip (no-op).
        - If value is a string that is not an existing file path, write it as text content.
        """
        for name, _defn in output_definitions.items():
            destination = resolved_destinations.get(name)
            if destination is None:
                continue

            value = workflow_result.get(name)
            if value is None:
                continue

            dest = self.working_directory / destination

            if isinstance(value, list):
                # Multi-file: treat destination as a directory; copy each file into it
                dest.mkdir(parents=True, exist_ok=True)
                for item in value:
                    src_path = Path(item)
                    if src_path.exists():
                        await asyncio.to_thread(shutil.copy2, src_path, dest / src_path.name)
                    else:
                        raise FileNotFoundError(
                            f"Output '{name}' references file '{src_path}' which was not found "
                            f"in job output directory '{job_context.output}'."
                        )
            elif isinstance(value, str):
                src_path = Path(value)
                if src_path.exists() and src_path.is_relative_to(job_context.output):
                    # It's a file path in the job output — copy it to the destination
                    dest_dir = dest.parent if dest.suffix else dest
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    await asyncio.to_thread(shutil.copy2, src_path, dest_dir / src_path.name)
                else:
                    # It's a literal content string — write to destination file
                    dest_file = dest if dest.suffix else dest / "output.txt"
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    await asyncio.to_thread(dest_file.write_text, value)
            else:
                # Not a path or string — nothing to copy
                continue
