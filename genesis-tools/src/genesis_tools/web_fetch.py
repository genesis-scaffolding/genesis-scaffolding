import asyncio
import random
from pathlib import Path
from typing import Any

import requests
import trafilatura

from .base import BaseTool
from .schema import ToolResult


def get_random_user_agent() -> str:
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    return random.choice(ua_list)


async def fetch_page(
    url: str,
    timeout: int = 15,
    max_retries: int = 2,
    delay_range: tuple = (1, 3),
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Asynchronously fetches a URL and converts it to Markdown.
    Uses asyncio.to_thread to wrap the blocking requests call.
    """

    # Inner blocking function to be offloaded to a thread
    def _blocking_fetch():
        session = requests.Session()

        default_headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        if headers:
            default_headers.update(headers)
        session.headers.update(default_headers)

        if cookies:
            session.cookies.update(cookies)

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    import time

                    time.sleep(random.uniform(*delay_range))

                # FIXED: allow_redirects=True (default is True anyway)
                response = session.get(url, timeout=timeout, allow_redirects=True)
                response.raise_for_status()

                md_content = trafilatura.extract(
                    response.text, output_format="markdown", include_formatting=True, include_links=True,
                )

                metadata = trafilatura.extract_metadata(response.text)
                title = metadata.title if metadata else "No Title Found"

                return {
                    "url": url,
                    "status_code": response.status_code,
                    "title": title,
                    "content": md_content or None,
                    "raw_html_len": len(response.text),
                    "final_url": response.url,
                }

            except requests.exceptions.RequestException as e:
                if attempt == max_retries:
                    return {
                        "url": url,
                        "status_code": getattr(e.response, "status_code", None)
                        if hasattr(e, "response")
                        else None,
                        "error": str(e),
                        "content": None,
                    }
        return {"url": url, "error": "Max retries reached", "content": None}

    # Offload the blocking _blocking_fetch to a thread so we can 'await' it
    return await asyncio.to_thread(_blocking_fetch)


class WebPageFetchTool(BaseTool):
    name = "fetch_web_page"
    description = (
        "Fetch a URL from the internet, extract its main text content, "
        "and convert it to Markdown. The content will be added to your clipboard."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full URL of the webpage to fetch.",
            },
            "timeout": {
                "type": "integer",
                "default": 15,
                "description": "How many seconds to wait for the page to load.",
            },
            "max_retries": {
                "type": "integer",
                "default": 2,
                "description": "How many times to retry the request if it fails.",
            },
        },
        "required": ["url"],
    }

    async def run(
        self,
        working_directory: Path,
        url: str,
        timeout: int = 15,
        max_retries: int = 2,
        **kwargs: Any,
    ) -> ToolResult:
        # fetch_page is already async and handles its own thread offloading
        result = await fetch_page(url=url, timeout=timeout, max_retries=max_retries)

        # Handle errors from the fetch function
        if "error" in result or not result.get("content"):
            error_msg = result.get("error", "Unknown error or no content found.")
            return ToolResult(status="error", tool_response=f"Failed to fetch {url}: {error_msg}")

        # Prepare clipboard content
        page_title = result.get("title", "No Title Found")
        final_url = result.get("final_url", url)
        md_content = result.get("content")

        clipboard_text = f"### Web Page: {page_title}\nURL: {final_url}\n---\n\n{md_content}"

        return ToolResult(
            status="success",
            tool_response=(
                f"Successfully fetched '{page_title}'. "
                "The page content has been converted to markdown and added to your clipboard."
            ),
            results_to_add_to_clipboard=[clipboard_text],
        )


async def main():
    result = await fetch_page(
        "https://www.neowin.net/news/microsoft-reveals-mu-an-on-device-small-language-model-built-into-windows-11/",
    )
    print(result["content"])


if __name__ == "__main__":
    asyncio.run(main())
