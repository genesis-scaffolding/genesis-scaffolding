import asyncio
from pathlib import Path

# Use the improved tool function
from genesis_tools.arxiv import search_papers_ddgs

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


class ArxivSearchTaskParams(TaskParams):
    query: str
    max_results: int = 5
    output_filename_prefix: str = "arxiv_search_"
    write_response_to_output: bool = True


class ArxivSearchTaskOutput(TaskOutput):
    pdf_paths: list[Path]
    md_paths: list[Path]


class ArxivSearchTask(BaseTask[ArxivSearchTaskParams, ArxivSearchTaskOutput]):
    params_model = ArxivSearchTaskParams
    output_model = ArxivSearchTaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> output_model:  # type: ignore
        args = self.params_model.model_validate(params)

        # Clean up the query to ensure it does not break the parser on arxiv side
        query = args.query
        query = query.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

        download_directory = context.internal / (args.sub_directory or "")
        download_directory.mkdir(parents=True, exist_ok=True)

        # Run the improved tool in a single thread
        # This handles search, download, and path resolution sequentially
        papers = await asyncio.to_thread(
            search_papers_ddgs,
            query=query,
            max_results=args.max_results,
            download_dir=download_directory,
        )

        # Unzip the results into matching lists using a simple list comprehension
        # This guarantees that index 0 of all lists belongs to the same paper.
        pdf_paths = [Path(p["pdf_path"]) for p in papers]
        md_paths = [Path(p["md_path"]) for p in papers]
        contents = [f"Title: {p['title']}\nSummary: {p['summary']}\n\n=====" for p in papers]

        if args.write_response_to_output:
            await self.link_or_copy_to_output(
                context=context,
                internal_file_paths=pdf_paths,
                output_filename=args.output_filename,
                output_filename_prefix=args.output_filename_prefix,
                sub_directory=args.sub_directory,
            )

        return self.output_model(
            content=contents,
            file_paths=md_paths,
            pdf_paths=pdf_paths,
            md_paths=md_paths,
        )
