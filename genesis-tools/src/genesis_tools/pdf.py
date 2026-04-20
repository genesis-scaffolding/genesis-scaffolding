import asyncio
from pathlib import Path
from typing import Any

import pymupdf4llm

from .base import BaseTool
from .schema import ToolResult


def convert_pdf_to_markdown(
    pdf_path: Path, output_dir: Path | None = None, prune_references: bool = True,
) -> str:
    """Converts a PDF (like an ArXiv paper) to Markdown text.

    Args:
        pdf_path: Path to the local PDF file.
        output_dir: Optional directory to save the .md file.

    Returns:
        str: The converted Markdown content.

    """
    try:
        # Convert the PDF to Markdown text
        # write_images=False keeps it lightweight; set to True if you want the figures.
        md_text = pymupdf4llm.to_markdown(str(pdf_path), write_images=False)

        # Ensure md_text is a string (handle list-return edge case)
        if isinstance(md_text, list):
            md_text = "\n".join(
                [page.get("text", "") if isinstance(page, dict) else str(page) for page in md_text],
            )

        # ArXiv Specific Pruning: Stop at References
        # Agents rarely need the full bibliography for immediate reasoning.
        if prune_references:
            # Common headers in ArXiv papers
            for header in ["## References", "## BIBLIOGRAPHY", "## Acknowledgments", "**References**"]:
                if header in md_text:
                    md_text = (
                        md_text.split(header)[0]
                        + f"\n\n(Note: {header} and subsequent content pruned for brevity.)"
                    )
                    break

        # Optionally save to disk
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            md_filename = pdf_path.stem + ".md"
            with open(output_dir / md_filename, "w", encoding="utf-8") as f:
                f.write(md_text)
            print(output_dir / md_filename)

        return md_text

    except Exception as e:
        print(f"Failed to convert {pdf_path}: {e}")
        return ""


class PdfToMarkdownTool(BaseTool):
    name = "pdf_to_markdown"
    description = (
        "Convert a local PDF file into Markdown text. "
        "The converted text will be added to your clipboard for easy reading. "
        "By default, it prunes references and bibliographies to save context space."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pdf_path": {
                "type": "string",
                "description": "The relative path to the PDF file to convert.",
            },
            "output_dir": {
                "type": "string",
                "description": "Optional: Relative path to a directory where the .md file should be saved.",
            },
            "prune_references": {
                "type": "boolean",
                "default": True,
                "description": "Whether to cut off the References/Bibliography section to save tokens.",
            },
        },
        "required": ["pdf_path"],
    }

    async def run(
        self,
        working_directory: Path,
        pdf_path: str,
        output_dir: str | None = None,
        prune_references: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        # 1. Validate Input PDF
        try:
            valid_pdf_path = self._validate_path(
                working_directory, pdf_path, must_exist=True, should_be_file=True,
            )
        except ValueError as e:
            return ToolResult(tool_response=str(e), status="error")

        # 2. Validate Output Directory (if provided)
        valid_output_dir = None
        if output_dir:
            try:
                valid_output_dir = self._validate_path(
                    working_directory, output_dir, must_exist=True, should_be_dir=True,
                )
            except ValueError as e:
                return ToolResult(tool_response=str(e), status="error")

        # 3. Run conversion in a separate thread
        md_text = await asyncio.to_thread(
            convert_pdf_to_markdown,
            pdf_path=valid_pdf_path,
            output_dir=valid_output_dir,
            prune_references=prune_references,
        )

        if not md_text:
            return ToolResult(
                status="error",
                tool_response=f"Failed to convert PDF: {pdf_path}. The file might be corrupted or password protected.",
            )

        # 4. Prepare Clipboard response
        results_to_add = []
        files_to_add = []

        # If we saved a file, tell the system to track it in the clipboard too
        if valid_output_dir:
            generated_md = valid_output_dir / (valid_pdf_path.stem + ".md")
            if generated_md.exists():
                files_to_add.append(generated_md)

        return ToolResult(
            status="success",
            tool_response=(
                f"Successfully converted '{pdf_path}' to markdown. "
                "The content has been added to your clipboard."
            ),
            results_to_add_to_clipboard=results_to_add,
            files_to_add_to_clipboard=files_to_add,
        )


def main():
    convert_pdf_to_markdown(
        Path("/home/gentran/Documents/genesis/inbox/2505.08588v1.pdf"), output_dir=Path("./inbox"),
    )


if __name__ == "__main__":
    main()
