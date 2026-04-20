import asyncio
from typing import Any

from genesis_tools.web_search import search_web

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


class WebSearchTaskParams(TaskParams):
    query: list[str]
    number_of_results: int = 10
    output_filename_prefix: str = "search_results"


class WebSearchTaskOutput(TaskOutput):
    pass


class WebSearchTask(BaseTask[WebSearchTaskParams, WebSearchTaskOutput]):
    params_model = WebSearchTaskParams
    output_model = WebSearchTaskOutput

    async def run(
        self,
        context: JobContext,
        agent_registry: AgentRegistry,
        params: dict,
    ) -> WebSearchTaskOutput:
        args = self.params_model.model_validate(params)

        # 1. Create concurrent search tasks for each individual query
        # We perform searches in parallel to avoid blocking and save time
        search_tasks = [
            search_web(query=q, max_results=args.number_of_results, fetch_full=True) for q in args.query
        ]

        # 2. Execute all searches concurrently
        # return_exceptions=True ensures one failing query doesn't crash the whole workflow
        search_results_lists: list[list[Any] | BaseException] = await asyncio.gather(
            *search_tasks,
            return_exceptions=True,
        )

        # 3. Flatten the results and format into Markdown
        formatted_contents: list[str] = []
        seen_urls = set()  # Simple de-duplication across different queries

        for i, result in enumerate(search_results_lists):
            if isinstance(result, BaseException):
                print(f"Error searching for query '{args.query[i]}': {result}")
                continue

            for res in result:
                # Basic de-duplication: skip if we've already found this URL in this step
                if res.url in seen_urls:
                    continue
                seen_urls.add(res.url)

                # Extract content (Prefer full content over snippet)
                main_body = res.full_content or res.snippet

                # Create a clean Markdown block
                md_entry = (
                    f"# {res.title}\n"
                    f"**Source URL:** {res.url}\n"
                    f"**Search Query:** {args.query[i]}\n\n"
                    f"{main_body}\n\n"
                    f"---\n"
                )
                formatted_contents.append(md_entry)

        if not formatted_contents:
            # Instead of crashing, we return empty so 'condition' logic in YAML can handle it
            return self.output_model(content=[], file_paths=None)

        # 4. Write results to individual files in the internal directory
        # This allows the next 'agent_map' step to process each article independently
        all_written_paths = await self.write_content_to_files(
            content=formatted_contents,
            context=context,
            output_filename=args.output_filename,
            output_filename_prefix=args.output_filename_prefix,
            write_response_to_output=args.write_response_to_output,
        )

        # 5. Return the structured output
        return self.output_model(
            content=formatted_contents,
            file_paths=all_written_paths or None,
        )
