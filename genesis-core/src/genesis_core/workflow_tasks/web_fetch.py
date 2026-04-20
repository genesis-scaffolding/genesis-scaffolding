import asyncio
from pathlib import Path

# Import the existing tool
from genesis_tools.web_fetch import fetch_page

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


class WebFetchTaskParams(TaskParams):
    urls: list[str]
    # Useful for naming the resulting markdown files
    output_filename_prefix: str = "web_page_"


class WebFetchTask(BaseTask[WebFetchTaskParams, TaskOutput]):
    params_model = WebFetchTaskParams
    output_model = TaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> TaskOutput:
        args = self.params_model.model_validate(params)

        # 1. Fetch all pages in parallel
        # This uses the fetch_page utility which already handles to_thread
        fetch_tasks = [fetch_page(url) for url in args.urls]
        results = await asyncio.gather(*fetch_tasks)

        all_content: list[str] = []

        # 2. Process results and handle errors
        for res in results:
            if not isinstance(res, dict):
                print(f"Unexpected result type from fetch_page: {type(res)}")
                continue

            if "error" in res:
                print(f"Failed to fetch {res.get('url')}: {res['error']}")
                continue

            content = res.get("content")
            if content:
                # We can prepend the title and URL to the content for the LLM's context
                header = f"SOURCE: {res.get('url')}\nTITLE: {res.get('title')}\n\n"
                all_content.append(header + content)
            else:
                print(f"No content extracted from {res.get('url')}")

        # 3. Write to files if requested
        output_paths: list[Path] = []
        if args.write_response_to_file and all_content:
            output_paths = await self.write_content_to_files(
                content=all_content,
                context=context,
                output_filename=args.output_filename,
                output_filename_prefix=args.output_filename_prefix,
                write_response_to_output=args.write_response_to_output,
            )

        return self.output_model(content=all_content, file_paths=output_paths)
