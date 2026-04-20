# Web Tools

## Overview

Web tools allow the agent to retrieve external information from the internet and structured feeds.

## Available Tools

| Tool | Description |
|---|---|
| `web_search` | Search the web and return structured results |
| `news_search` | Search for recent news articles |
| `fetch_web_page` | Fetch and extract text content from a URL |
| `rss_fetch` | Fetch and parse an RSS feed |
| `fetch_arxiv` | Search ArXiv for papers and retrieve metadata or abstracts |

## When to Use Each

**Web search vs fetch**: Use web search to find which URL contains the answer. Use fetch to retrieve the actual content once you have a URL.

**RSS fetch**: For structured feeds like blogs, newsletters, or periodic publications. Returns items sorted by publication date.

**ArXiv fetch**: For academic paper search. Returns title, authors, abstract, and PDF link.

## Related Modules

- `genesis_core.tools.web_tools` — Web tool implementations
