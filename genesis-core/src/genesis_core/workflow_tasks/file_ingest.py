import asyncio
import shutil
from pathlib import Path

# Assuming the utility is located here based on your description
from genesis_tools.pdf import convert_pdf_to_markdown

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


class IngestTaskParams(TaskParams):
    """Standard params.
    Inherits files_to_read, sub_directory, etc.
    """

    prune_references: bool = True


class IngestTaskOutput(TaskOutput):
    """Extended output to differentiate between raw files and text-based files."""

    # content: list[str] (Inherited)
    # file_paths: list[Path] (Inherited - contains ALL ingested files)
    readable_paths: list[Path] = []


class IngestTask(BaseTask[IngestTaskParams, IngestTaskOutput]):
    params_model = IngestTaskParams
    output_model = IngestTaskOutput

    async def run(
        self,
        context: JobContext,
        agent_registry: AgentRegistry,
        params: dict,
    ) -> IngestTaskOutput:
        args = self.params_model.model_validate(params)

        # 1. Setup Target Directory
        target_dir = context.input
        if args.sub_directory:
            target_dir = context.input / args.sub_directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # 2. Resolve Input Paths
        files_to_process = self.resolve_input_file_paths(
            context=context,
            input_file_paths=args.files_to_read,
        )

        all_ingested_paths: list[Path] = []
        readable_paths: list[Path] = []

        # 3. Process Files
        for source_path in files_to_process:
            dest_path = target_dir / source_path.name

            try:
                # Clean up existing
                if dest_path.exists() or dest_path.is_symlink():
                    dest_path.unlink()

                # Ingest raw file (Symlink or Copy)
                try:
                    dest_path.symlink_to(source_path)
                except (OSError, PermissionError):
                    shutil.copy2(source_path, dest_path)

                all_ingested_paths.append(dest_path)

                # 4. Handle Content Types
                suffix = dest_path.suffix.lower()

                if suffix in [".md", ".txt"]:
                    readable_paths.append(dest_path)

                elif suffix == ".pdf":
                    # Run PDF conversion in a thread to avoid blocking the event loop
                    md_filename = dest_path.stem + ".md"
                    md_dest_path = target_dir / md_filename

                    # Call your conversion utility
                    # We wrap it in to_thread because pymupdf is synchronous
                    await asyncio.to_thread(
                        convert_pdf_to_markdown,
                        pdf_path=dest_path,
                        output_dir=target_dir,
                        prune_references=args.prune_references,
                    )

                    if md_dest_path.exists():
                        readable_paths.append(md_dest_path)
                        # We also add the generated MD to the general file list
                        all_ingested_paths.append(md_dest_path)

            except Exception as e:
                # We log and continue so one bad file doesn't break the whole batch
                print(f"Failed to ingest {source_path.name}: {e!s}")
                continue

        return self.output_model(
            content=[f"Ingested {len(all_ingested_paths)} files. {len(readable_paths)} are readable text."],
            file_paths=all_ingested_paths,
            readable_paths=readable_paths,
        )
