import asyncio
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import httpx
from ddgs import DDGS

from .base import BaseTool
from .pdf import convert_pdf_to_markdown
from .schema import ToolResult


def _format_result(
    result: Any,
    pdf_path: Path | None = None,
    md_path: Path | None = None,
    source_path: Path | None = None,
) -> dict:
    """Helper to standardize paper metadata output."""
    return {
        "entry_id": result.entry_id,
        "short_id": result.entry_id.split("/")[-1],
        "title": result.title,
        "authors": [author.name for author in result.authors],
        "summary": result.summary,
        "published": result.published.strftime("%Y-%m-%d"),
        "updated": result.updated.strftime("%Y-%m-%d"),
        "journal_ref": result.journal_ref,
        "doi": result.doi,
        "primary_category": result.primary_category,
        "categories": result.categories,
        "pdf_url": result.pdf_url,
        "links": [{"title": link.title, "url": link.href} for link in result.links] if result.links else [],
        "pdf_path": pdf_path,
        "md_path": md_path,
        "source_path": source_path,
    }


def download_paper_pdf(paper_id: str, download_dir: Path, convert_to_markdown: bool = True) -> Path | None:
    """Directly download the PDF of a specific paper by its arXiv ID without using the search client.

    Args:
        paper_id (str): arXiv ID of the paper (e.g. "2107.05580").
        download_dir (Path): Base directory for storage.

    Returns:
        Path | None: Path to the downloaded PDF, or None if the download failed.

    """
    # Predictable direct PDF URL
    url = f"https://arxiv.org/pdf/{paper_id}.pdf"

    # Create a specific folder for the paper or save directly to download_dir
    # Usually better to keep the PDF name clean
    pdf_path = download_dir / f"{paper_id}.pdf"

    try:
        download_dir.mkdir(parents=True, exist_ok=True)

        with httpx.stream("GET", url, follow_redirects=True) as response:
            # ArXiv returns 403 or 404 if the ID is wrong or access is blocked
            response.raise_for_status()

            with open(pdf_path, "wb") as f:
                f.writelines(response.iter_bytes())

        convert_pdf_to_markdown(pdf_path=pdf_path, output_dir=download_dir)

        return pdf_path

    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code} for ID {paper_id}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def download_paper_source(paper_id: str, download_dir: Path) -> Path | None:
    """Download the LaTeX source of a specific paper by its arXiv ID.

    Args:
        paper_id (str): arXiv ID of the paper (e.g. "2107.05580" or "quant-ph/0201082v1")
        download_dir (Optional[str]): Directory to download the source to. If None, uses AI/tmp/arxiv/paper_id/

    Returns:
        Path | None: Path to the extracted source folder, or empty if cannot download

    """
    # Direct e-print URL
    url = f"https://arxiv.org/e-print/{paper_id}"
    tarballs_path = download_dir / "tarballs"
    tarballs_path.mkdir(parents=True, exist_ok=True)
    archive_path = download_dir / "tarballs" / f"{paper_id}.tar.gz"

    with httpx.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        with open(archive_path, "wb") as f:
            f.writelines(response.iter_bytes())

    source_dir = download_dir / paper_id
    source_dir.mkdir(exist_ok=True)
    # Better extraction logic
    try:
        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path) as tar:
                tar.extractall(path=source_dir, filter="data")
        elif zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(source_dir)
        return source_dir
    except Exception as e:
        print(f"Extraction failed: {e}")
        return None


def extract_arxiv_id(input_str: str) -> str:
    """Extracts an arXiv ID from a URL or a string.
    Supports:
    - Modern IDs: 2301.12345, 0704.0001
    - Legacy IDs: hep-th/9901001, math.CO/0101001
    - URLs: https://arxiv.org/abs/2301.12345, https://arxiv.org/pdf/2301.12345.pdf
    - Prefixes: arXiv:2301.12345
    """
    # Pattern for modern IDs (YYMM.NNNNN)
    modern_pattern = r"(\d{4}\.\d{4,5}(v\d+)?)"
    # Pattern for legacy IDs (subject/YYMMNNN)
    legacy_pattern = r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7}(v\d+)?)"

    # Combined search for both patterns
    full_pattern = f"({modern_pattern}|{legacy_pattern})"
    match = re.search(full_pattern, input_str, re.IGNORECASE)

    if match:
        return match.group(0)

    # Fallback: if no pattern matches, return original (it might already be a clean ID)
    return input_str.strip()


def _parse_arxiv_search_page(html: str, max_results: int) -> list[str]:
    """Extract paper IDs from arxiv.org/search/ HTML page."""
    # Paper IDs appear as href links: <a href="https://arxiv.org/abs/2604.09528">
    ids = re.findall(r'href="https://arxiv\.org/abs/([^"]+)"', html)
    return ids[:max_results]


def _parse_arxiv_abs_page(html: str) -> dict | None:
    """Parse metadata from arxiv.org/abs/{id} HTML page."""

    def meta(name: str) -> str | None:
        match = re.search(rf'<meta name="{name}" content="([^"]*)"', html)
        return match.group(1) if match else None

    def link(rel: str) -> str | None:
        match = re.search(rf'<link[^>]+rel="{rel}"[^>]+href="([^"]*)"', html, re.I)
        return match.group(1) if match else None

    title = meta("citation_title")
    if not title:
        return None

    short_id = meta("citation_arxiv_id") or ""
    return {
        "entry_id": f"http://arxiv.org/abs/{short_id}",
        "short_id": short_id,
        "title": title,
        "authors": re.findall(r'<meta name="citation_author" content="([^"]*)"', html),
        "summary": meta("citation_abstract"),
        "published": meta("citation_date"),
        "updated": meta("citation_online_date"),
        "journal_ref": None,  # not always present
        "doi": None,  # not on the abs page
        "primary_category": None,  # not on the abs page
        "categories": [],  # not on the abs page
        "pdf_url": meta("citation_pdf_url"),
        "links": [],  # not on the abs page
        "pdf_path": None,
        "md_path": None,
        "source_path": None,
    }


def get_paper_details(
    paper_id: str,
    download_dir: Path | None = None,
    download_pdf: bool = False,
    download_source: bool = False,
) -> dict | None:
    """Get detailed information about a specific paper by its arXiv ID.

    Fetches metadata directly from the HTML abstract page (arxiv.org/abs/{id}),
    bypassing the rate-limited export API.
    """
    parsed_paper_id: str = extract_arxiv_id(paper_id)
    url = f"https://arxiv.org/abs/{parsed_paper_id}"

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=30) as response:
            response.raise_for_status()
            html_content = response.read()

        result = _parse_arxiv_abs_page(html_content.decode("utf-8"))

        if not result:
            print(f"No paper found with ID: {parsed_paper_id}")
            return None

        # Download PDF if requested
        pdf_path: Path | None = None
        md_path: Path | None = None
        if download_dir and download_pdf:
            try:
                pdf_path = download_paper_pdf(paper_id=parsed_paper_id, download_dir=download_dir)
                if not pdf_path:
                    raise Exception("Cannot download PDF")
                md_path = pdf_path.with_suffix(".md")
            except Exception:
                pass

        # Download source if requested
        source_path: Path | None = None
        if download_dir and download_source:
            try:
                source_path = download_paper_source(paper_id=parsed_paper_id, download_dir=download_dir)
            except Exception:
                pass

        result["pdf_path"] = pdf_path
        result["md_path"] = md_path
        result["source_path"] = source_path
        return result

    except httpx.HTTPStatusError as e:
        print(f"HTTP error fetching details for {parsed_paper_id}: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"Error fetching details for {parsed_paper_id}: {e}")
        return None


def search_papers_arxiv(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    download_dir: Path | None = None,
    download_pdf: bool = False,
    download_source: bool = False,
) -> list[dict]:
    """Search arXiv papers by query, then fetch details (with optional PDF/source download) for each.

    Fetches the search results page directly, parses paper IDs, then calls get_paper_details
    for each to retrieve metadata (and optionally download files).
    """
    # Build search URL — sort_by is kept for signature compatibility but the HTML
    # search page does not support server-side sorting; results are returned as-found.
    url = f"https://arxiv.org/search/?query={query}&searchtype=all&max_results={max_results}"

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=30) as response:
            response.raise_for_status()
            html_content = response.read()

        paper_ids = _parse_arxiv_search_page(html_content.decode("utf-8"), max_results)
    except Exception:
        return []

    results = []
    for paper_id in paper_ids:
        details = get_paper_details(
            paper_id=paper_id,
            download_dir=download_dir,
            download_pdf=download_pdf,
            download_source=download_source,
        )
        if details:
            results.append(
                {
                    "id": details.get("short_id"),
                    "title": details.get("title"),
                    "summary": details.get("summary"),
                    "authors": details.get("authors"),
                    "pdf_path": details.get("pdf_path"),
                    "md_path": details.get("md_path"),
                }
            )

    return results


def search_papers_ddgs(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    download_dir: Path | None = None,
    download_pdf: bool = False,
    download_source: bool = False,
) -> list[dict]:
    """Search arXiv papers using DuckDuckGo, then fetch details for each.

    Uses ddgs (DuckDuckGo) to find arXiv paper URLs, extracts IDs, then calls
    get_paper_details per paper. Bypasses the arXiv export API entirely.
    """
    search_query = f"{query} site:arxiv.org"

    try:
        with DDGS() as ddgs:
            results_ddgs = ddgs.text(
                search_query, region="wt-wt", safesearch="moderate", max_results=max_results
            )
            # Extract paper IDs from arXiv URLs in search results
            paper_ids = []
            for r in results_ddgs:
                url = r.get("href", "")
                if "arxiv.org/abs/" in url:
                    paper_id = extract_arxiv_id(url)
                    if paper_id and paper_id not in paper_ids:
                        paper_ids.append(paper_id)
    except Exception as e:
        print(f"DDGS search error: {e}")
        return []

    results = []
    for paper_id in paper_ids:
        details = get_paper_details(
            paper_id=paper_id,
            download_dir=download_dir,
            download_pdf=download_pdf,
            download_source=download_source,
        )
        if details:
            results.append(
                {
                    "id": details.get("short_id"),
                    "title": details.get("title"),
                    "summary": details.get("summary"),
                    "authors": details.get("authors"),
                    "pdf_path": details.get("pdf_path"),
                    "md_path": details.get("md_path"),
                }
            )

    return results


class ArxivSearchTool(BaseTool):
    name = "arxiv_search_tool"
    description = "Search arxiv papers for a given query, download markdown and PDF of the found paper to a directory, and read the markdown files into the clipboard."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query for ArXiv papers (e.g., 'quantum computing')",
            },
            "max_results": {
                "type": "integer",
                "default": 10,
                "description": "The maximum number of papers to return",
            },
            "download_dir": {
                "type": "string",
                "default": ".",
                "description": "The subdirectory where files should be saved",
            },
        },
        "required": ["query"],
    }

    async def run(
        self,
        working_directory: Path,
        query: str,
        max_results: int = 10,
        download_dir: str = ".",
        **kwargs: Any,
    ) -> ToolResult:
        try:
            # Hoisted validation
            valid_download_dir = self._validate_path(
                working_directory,
                download_dir,
                must_exist=True,
                should_be_dir=True,
                create_if_missing=True,
            )
        except ValueError as e:
            return ToolResult(tool_response=str(e), status="error")

        # At this point, the provided path exist, sit within the working directory, and is a valid directory
        results = await asyncio.to_thread(
            search_papers_arxiv,
            query=query,
            max_results=max_results,
            download_dir=valid_download_dir,
        )

        if not results or len(results) == 0:
            return ToolResult(
                status="success",
                tool_response=f"Cannot find any paper for the given search query: {query}",
            )

        num_results = len(results)
        results_to_add_to_clipboard: list[str] = []
        files_to_add_to_clipboard: list[Path] = []
        for result in results:
            results_to_add_to_clipboard.append(
                f"Arxiv Paper ID: {result.get('id', 'unknown')}\nTitle: {result.get('title', 'unknown')}\nSummary: {result.get('summary', 'unknown')}\n\n\n",
            )
            md_path = result.get("md_path")
            if md_path and Path(md_path).exists():
                files_to_add_to_clipboard.append(Path(md_path))

        return ToolResult(
            status="success",
            tool_response=f"Found and downloaded {num_results}. Resulting markdown files have been added to clipboard.",
            files_to_add_to_clipboard=files_to_add_to_clipboard,
            results_to_add_to_clipboard=results_to_add_to_clipboard,
        )


class ArxivPaperDetailTool(BaseTool):
    name = "arxiv_paper_detail"
    description = (
        "Fetch detailed metadata for a specific arXiv paper by its ID. "
        "Optionally download the PDF and read the converted markdown content into the clipboard."
    )
    parameters = {
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "The arXiv ID (e.g., '2305.16303' or 'cs/0501001')",
            },
            "download_pdf": {
                "type": "boolean",
                "default": False,
                "description": "If true, downloads the PDF and converts it to markdown for the clipboard.",
            },
            "download_dir": {
                "type": "string",
                "default": ".",
                "description": "The relative subdirectory where the paper should be saved.",
            },
        },
        "required": ["paper_id"],
    }

    async def run(
        self,
        working_directory: Path,
        paper_id: str,
        download_pdf: bool = False,
        download_dir: str = ".",
        **kwargs: Any,
    ) -> ToolResult:
        try:
            valid_download_dir = self._validate_path(
                working_directory,
                download_dir,
                must_exist=True,
                should_be_dir=True,
                create_if_missing=True,
            )
        except ValueError as e:
            return ToolResult(tool_response=str(e), status="error")
        # 2. Call the blocking sync function in a separate thread
        # We use asyncio.to_thread to avoid blocking the agent's event loop
        result = await asyncio.to_thread(
            get_paper_details,
            paper_id=paper_id,
            download_dir=valid_download_dir,
            download_pdf=download_pdf,
        )

        if not result:
            return ToolResult(status="error", tool_response=f"No paper found with ArXiv ID: {paper_id}")

        # 3. Prepare the Clipboard content
        # We put the summary/metadata in the clipboard text channel
        paper_metadata = (
            f"ID: {result.get('id')}\n"
            f"Title: {result.get('title')}\n"
            f"Authors: {result.get('authors', 'Unknown')}\n"
            f"Summary: {result.get('summary')}\n"
        )

        results_to_add_to_clipboard = [paper_metadata]
        files_to_add_to_clipboard: list[Path] = []

        # If a markdown conversion was generated, add it to the file clipboard channel
        md_path_str = result.get("md_path")
        if md_path_str:
            md_path = Path(md_path_str)
            if md_path.exists():
                files_to_add_to_clipboard.append(md_path)

        # 4. Return result
        status_msg = f"Successfully fetched details for {paper_id}."
        if download_pdf and files_to_add_to_clipboard:
            status_msg += " Paper content has been converted to markdown and added to the clipboard."
        else:
            status_msg += " Metadata has been added to the clipboard."

        return ToolResult(
            status="success",
            tool_response=status_msg,
            results_to_add_to_clipboard=results_to_add_to_clipboard,
            files_to_add_to_clipboard=files_to_add_to_clipboard,
        )


def main():
    print("reached main")
    paper_id = "2603.28128"
    output_path = download_paper_pdf(paper_id=paper_id, download_dir=Path("./inbox"))
    print(output_path)
    paper_detail = get_paper_details(paper_id=paper_id)
    print(paper_detail)

    print("\n--- Testing search_papers (HTML) ---")
    search_results = search_papers_arxiv(
        "quantum computing",
        max_results=3,
        download_dir=Path("./inbox"),
        download_pdf=True,
    )
    print(f"Found {len(search_results)} results")
    for r in search_results:
        print(f"  {r['id']}: {r['title'][:60]}... | md_path={r['md_path']}")

    print("\n--- Testing search_papers_ddgs ---")
    search_results_ddgs = search_papers_ddgs(
        "quantum computing",
        max_results=3,
        download_dir=Path("./inbox"),
        download_pdf=True,
    )
    print(f"Found {len(search_results_ddgs)} results")
    for r in search_results_ddgs:
        print(f"  {r['id']}: {r['title'][:60]}... | md_path={r['md_path']}")


if __name__ == "__main__":
    main()
