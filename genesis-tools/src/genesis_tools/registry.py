from .arxiv import ArxivPaperDetailTool, ArxivSearchTool
from .base import BaseTool
from .date_tools import ComputeDateRangeTool
from .file import (
    DeleteFileTool,
    EditFileTool,
    FindFilesTool,
    ListFilesTool,
    MoveFileTool,
    ReadFileTool,
    SearchFileContentTool,
    WriteFileTool,
)
from .memory_tools import (
    DeleteMemoryTool,
    GetMemoryTool,
    ListMemoriesTool,
    RebuildFtsIndexTool,
    RememberThisTool,
    SearchMemoriesTool,
    UpdateMemoryTool,
)
from .pdf import PdfToMarkdownTool
from .productivity_tools import (
    CreateJournalTool,
    CreateProjectTool,
    CreateTaskTool,
    EditJournalTool,
    ReadJournalTool,
    ReadProjectTool,
    ReadTaskTool,
    SearchJournalsTool,
    SearchProjectsTool,
    SearchTasksTool,
    UpdateProjectTool,
    UpdateTasksTool,
)
from .rss_utils import RssFetchTool
from .test_tools import MockTestTool
from .web_fetch import WebPageFetchTool
from .web_search import NewsSearchTool, WebSearchTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, type[BaseTool]] = {}

    def register(self, name: str, tool_class: type[BaseTool]):
        """Register a tool instance."""
        # hacky implementation for now to overwrite the tool name
        # The goal here is so that the dictionary key matches the name define in class
        tool_class.name = name
        self._tools[name] = tool_class

    def get_tool(self, name: str) -> BaseTool | None:
        """Look up a tool by name."""
        tool_class = self._tools.get(name)
        if not tool_class:
            return None
        return tool_class()

    def get_all_tool_names(self) -> list[str]:
        return list(self._tools.keys())


# Global registry instance
tool_registry = ToolRegistry()

tool_registry.register("test_tool", MockTestTool)
tool_registry.register("get_arxiv_paper_detail", ArxivPaperDetailTool)
tool_registry.register("search_arxiv_paper", ArxivSearchTool)
tool_registry.register("convert_pdf_to_markdown_tool", PdfToMarkdownTool)
tool_registry.register("fetch_rss_feed", RssFetchTool)
tool_registry.register("fetch_web_page", WebPageFetchTool)
tool_registry.register("search_web", WebSearchTool)
tool_registry.register("search_news", NewsSearchTool)
tool_registry.register("list_files", ListFilesTool)
tool_registry.register("read_file", ReadFileTool)
tool_registry.register("write_file", WriteFileTool)
tool_registry.register("edit_file", EditFileTool)
tool_registry.register("find_files", FindFilesTool)
tool_registry.register("delete_file", DeleteFileTool)
tool_registry.register("move_or_rename_file", MoveFileTool)
tool_registry.register("search_file_content", SearchFileContentTool)
tool_registry.register("search_tasks", SearchTasksTool)
tool_registry.register("read_task", ReadTaskTool)
tool_registry.register("search_projects", SearchProjectsTool)
tool_registry.register("read_project", ReadProjectTool)
tool_registry.register("search_journals", SearchJournalsTool)
tool_registry.register("read_journal", ReadJournalTool)
tool_registry.register("create_task", CreateTaskTool)
tool_registry.register("create_project", CreateProjectTool)
tool_registry.register("create_journal", CreateJournalTool)
tool_registry.register("update_tasks", UpdateTasksTool)
tool_registry.register("update_project", UpdateProjectTool)
tool_registry.register("edit_journal", EditJournalTool)
# Memory tools
tool_registry.register("remember_this", RememberThisTool)
tool_registry.register("search_memories", SearchMemoriesTool)
tool_registry.register("list_memories", ListMemoriesTool)
tool_registry.register("get_memory", GetMemoryTool)
tool_registry.register("update_memory", UpdateMemoryTool)
tool_registry.register("delete_memory", DeleteMemoryTool)
tool_registry.register("rebuild_fts_index", RebuildFtsIndexTool)
tool_registry.register("compute_date_range", ComputeDateRangeTool)


def main():
    for tool_name in tool_registry.get_all_tool_names():
        tool = tool_registry.get_tool(tool_name)
        if tool:
            print(tool.name)
            print(tool.description)
            print(tool.parameters)


if __name__ == "__main__":
    main()
