import asyncio
from pathlib import Path

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


class FileReadTask(BaseTask[TaskParams, TaskOutput]):
    params_model = TaskParams
    output_model = TaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> TaskOutput:
        args = self.params_model.model_validate(params)

        # Resolve the files (this handles the relative/absolute logic)
        files_to_read = self.resolve_input_file_paths(context=context, input_file_paths=args.files_to_read)

        all_contents: list[str] = []
        valid_paths: list[Path] = []

        def _read_files():
            for p in files_to_read:
                # Only read text-based files
                if p.suffix.lower() in [".md", ".txt"]:
                    try:
                        with open(p, encoding="utf-8") as f:
                            all_contents.append(f.read())
                        valid_paths.append(p)
                    except Exception as e:
                        print(f"Error reading {p.name}: {e}")
            return all_contents, valid_paths

        # Offload I/O to a thread
        contents, paths = await asyncio.to_thread(_read_files)

        return self.output_model(content=contents, file_paths=paths)
