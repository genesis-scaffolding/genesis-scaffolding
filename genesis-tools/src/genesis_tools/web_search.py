import asyncio
from pathlib import Path
from typing import Any

from ddgs import DDGS
from pydantic import BaseModel

from .base import BaseTool
from .schema import ToolResult
from .web_fetch import fetch_page


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    full_content: str | None = None
    # For news results
    date: str | None = None
    source: str | None = None


def _ddgs_search(query: str, max_results: int) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=max_results))


async def search_web(query: str, max_results: int = 5, fetch_full: bool = False) -> list[SearchResult]:
    results = []
    try:
        search_results = await asyncio.to_thread(_ddgs_search, query, max_results)

        for r in search_results:
            item = SearchResult(
                title=r.get("title", ""), url=r.get("href", ""), snippet=r.get("body", ""),
            )

            if fetch_full:
                full_data = await fetch_page(item.url)
                item.full_content = full_data.get("content", "")

            results.append(item)

        return results
    except Exception as e:
        print(f"DDGS Search Error: {e}")
        return []


def _ddgs_news(query: str, max_results: int) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.news(query, max_results=max_results))


async def search_news(query: str, max_results: int = 5, fetch_full: bool = False) -> list[SearchResult]:
    results = []
    try:
        news_results = await asyncio.to_thread(_ddgs_news, query, max_results)

        for r in news_results:
            item = SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("body", ""),
                date=r.get("date"),
                source=r.get("source"),
            )

            if fetch_full:
                full_data = await fetch_page(item.url)
                item.full_content = full_data.get("content", "")

            results.append(item)
        return results
    except Exception as e:
        print(f"DDGS News Error: {e}")
        return []


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the internet for a given query. Returns a list of titles, snippets, and URLs. "
        "Setting fetch_full to True will also extract the main text from each result."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "max_results": {
                "type": "integer",
                "default": 5,
                "description": "Number of results to return.",
            },
            "fetch_full": {
                "type": "boolean",
                "default": False,
                "description": "Whether to fetch and convert the full content of each search result.",
            },
        },
        "required": ["query"],
    }

    async def run(
        self,
        working_directory: Path,
        query: str,
        max_results: int = 5,
        fetch_full: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        results = await search_web(query=query, max_results=max_results, fetch_full=fetch_full)

        if not results:
            return ToolResult(status="success", tool_response=f"No results found for query: {query}")

        formatted_results = []
        for r in results:
            entry = f"Title: {r.title}\nURL: {r.url}\nSnippet: {r.snippet}\n"
            if r.full_content:
                entry += f"Full Content (Markdown):\n{r.full_content}\n"
            entry += "---"
            formatted_results.append(entry)

        return ToolResult(
            status="success",
            tool_response=f"Found {len(results)} results for '{query}'. Details are in your clipboard.",
            results_to_add_to_clipboard=formatted_results,
        )


class NewsSearchTool(BaseTool):
    name = "news_search"
    description = (
        "Search for recent news articles. Returns headlines, sources, dates, and snippets. "
        "Setting fetch_full to True will extract the full article text for the results."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The news search query."},
            "max_results": {
                "type": "integer",
                "default": 5,
                "description": "Number of news articles to return.",
            },
            "fetch_full": {
                "type": "boolean",
                "default": False,
                "description": "Whether to fetch the full text of each news article.",
            },
        },
        "required": ["query"],
    }

    async def run(
        self,
        working_directory: Path,
        query: str,
        max_results: int = 5,
        fetch_full: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        results = await search_news(query=query, max_results=max_results, fetch_full=fetch_full)

        if not results:
            return ToolResult(status="success", tool_response=f"No recent news found for query: {query}")

        formatted_news = []
        for r in results:
            entry = (
                f"Headline: {r.title}\n"
                f"Source: {r.source or 'Unknown'}\n"
                f"Date: {r.date or 'Unknown'}\n"
                f"URL: {r.url}\n"
                f"Snippet: {r.snippet}\n"
            )
            if r.full_content:
                entry += f"Full Article Content:\n{r.full_content}\n"
            entry += "---"
            formatted_news.append(entry)

        return ToolResult(
            status="success",
            tool_response=f"Found {len(results)} news articles for '{query}'. Headlines and summaries are in your clipboard.",
            results_to_add_to_clipboard=formatted_news,
        )


async def main():
    # Example: Deep Web Search
    print("--- Web Search with Content ---")
    web_results = await search_web(query="Small Language Model deployment", max_results=1, fetch_full=True)
    for res in web_results:
        print(f"Title: {res.title}")
        if res.full_content:
            print(f"Full Content: {res.full_content[:500]}...\n")

    # Example: Deep News Search (Requested)
    print("--- News Search with Content ---")
    news_results = await search_news(query="Australian news", max_results=1, fetch_full=True)
    for res in news_results:
        print(f"Source: {res.source} | Date: {res.date}")
        print(f"Title: {res.title}")
        print(f"Snippet: {res.snippet}")
        if res.full_content:
            print(f"Full Content: {res.full_content[:500]}...")


if __name__ == "__main__":
    asyncio.run(main())
