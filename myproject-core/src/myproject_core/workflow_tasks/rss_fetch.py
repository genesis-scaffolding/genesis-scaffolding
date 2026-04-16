import asyncio
import re
from pathlib import Path
from typing import Any

from myproject_tools.rss_utils import fetch_single_rss

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


class RSSFetchTaskParams(TaskParams):
    feed_urls: list[str]
    since_days: int = 1
    # Default prefix for individual files
    output_filename_prefix: str = "rss_item_"


class RSSFetchTask(BaseTask[RSSFetchTaskParams, TaskOutput]):
    params_model = RSSFetchTaskParams
    output_model = TaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> TaskOutput:
        args = self.params_model.model_validate(params)

        # 1. Fetch entries in parallel
        fetch_tasks = [asyncio.to_thread(fetch_single_rss, url, args.since_days) for url in args.feed_urls]

        results: list[list[dict[str, Any]] | BaseException] = await asyncio.gather(
            *fetch_tasks,
            return_exceptions=True,
        )

        all_entries: list[dict[str, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                print(f"Error fetching RSS from {args.feed_urls[i]}: {result}")
                continue
            all_entries.extend(result)

        # 2. Format content for blackboard and generate file paths
        formatted_content: list[str] = []
        file_paths: list[Path] = []

        if all_entries:
            sub_dir = args.sub_directory or ""
            save_dir = context.internal / sub_dir
            save_dir.mkdir(parents=True, exist_ok=True)

            for idx, e in enumerate(all_entries):
                # Prepare the text content
                content_str = (
                    f"Source: {e.get('feed_title', 'Unknown')}\n"
                    f"Title: {e.get('title', 'No Title')}\n"
                    f"Link: {e.get('link', '')}\n"
                    f"Published: {e.get('published', 'Unknown')}\n\n"
                    f"Summary:\n{e.get('summary', '')}"
                )
                formatted_content.append(content_str)

                # 3. Handle File Writing
                if args.write_response_to_file:
                    # Sanitize feed title for the filename (remove non-alphanumeric)
                    safe_title = (
                        re.sub(r"[^\w\s-]", "", e.get("feed_title", "feed")).strip().replace(" ", "_")
                    )

                    # Construct unique filename: prefix_feedname_index.md
                    file_name = f"{args.output_filename_prefix}{safe_title}_{idx:03d}.md"
                    file_path = save_dir / file_name

                    file_path.write_text(content_str, encoding="utf-8")
                    file_paths.append(file_path)

            # 4. Sync to output directory if requested
            if args.write_response_to_output and file_paths:
                await self.link_or_copy_to_output(
                    context=context,
                    internal_file_paths=file_paths,
                    output_filename=args.output_filename,
                    output_filename_prefix=args.output_filename_prefix,
                    sub_directory=args.sub_directory,
                )

        return self.output_model(content=formatted_content, file_paths=file_paths)
