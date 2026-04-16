import asyncio
import random
from pathlib import Path

from myproject_tools.arxiv import get_paper_details

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


### Arxiv paper download tasks
class ArxivDownloadTaskParams(TaskParams):
    # Accept a list of paper IDs
    arxiv_paper_ids: list[str]
    write_response_to_output: bool = True
    output_filename_prefix: str = "arxiv_"


class ArxivDownloadTaskOutput(TaskOutput):
    # Return lists of Path objects
    pdf_paths: list[Path]
    md_paths: list[Path]


class ArxivDownloadTask(BaseTask[ArxivDownloadTaskParams, ArxivDownloadTaskOutput]):
    params_model = ArxivDownloadTaskParams
    output_model = ArxivDownloadTaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> output_model:  # type: ignore
        args = self.params_model.model_validate(params)

        print(args)
        arxiv_paper_ids = args.arxiv_paper_ids
        sub_directory = args.sub_directory or ""
        download_directory = context.internal / sub_directory

        # Ensure download directory exists
        download_directory.mkdir(parents=True, exist_ok=True)

        pdf_paths: list[Path] = []
        md_paths: list[Path] = []
        all_details = []

        for i, paper_id in enumerate(arxiv_paper_ids):
            # 1. Mandatory Throttle: ArXiv requires ~3 seconds between requests.
            # We don't sleep on the very first request, but sleep before every subsequent one.
            if i > 0:
                wait_time = 3 + random.uniform(0.5, 1.5)  # Add a little jitter
                print(f"Throttling for ArXiv: Sleeping {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)

            # 2. Retry Logic: Handle 429s gracefully
            max_retries = 3

            for attempt in range(max_retries):
                try:

                    def _do_blocking_download(pid: str):
                        # get_paper_details likely hits the API + the PDF download link
                        details = get_paper_details(
                            paper_id=pid,
                            download_dir=download_directory,
                            download_pdf=True,
                        )
                        if not details:
                            raise ValueError(f"Cannot find paper: {pid}")
                        return details

                    paper_details = await asyncio.to_thread(_do_blocking_download, paper_id)

                    pdf_paths.append(Path(paper_details["pdf_path"]))
                    md_paths.append(Path(paper_details["md_path"]))
                    all_details.append(paper_details)

                    break  # Success! Exit the retry loop.

                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        backoff = (attempt + 1) * 10  # 10s, then 20s
                        print(
                            f"ArXiv Rate Limit hit (429). Retrying in {backoff}s... (Attempt {attempt + 1}/{max_retries})",
                        )
                        await asyncio.sleep(backoff)
                    else:
                        print(f"Failed to download {paper_id}: {e!s}")
                        break  # Give up on this specific paper

        if args.write_response_to_output:
            await self.link_or_copy_to_output(
                context=context,
                internal_file_paths=pdf_paths,
                output_filename=args.output_filename,
                output_filename_prefix=args.output_filename_prefix,
                sub_directory=args.sub_directory,
            )

        # Return the lists of Paths
        return self.output_model(
            content=[str(d) for d in all_details],
            # Combining both for the base class file_paths requirement (as strings)
            file_paths=md_paths,
            # Specific fields for the two matching Path lists
            pdf_paths=pdf_paths,
            md_paths=md_paths,
        )
