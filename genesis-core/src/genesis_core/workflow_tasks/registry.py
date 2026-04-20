from .agent_map import AgentMapTask
from .agent_projection import AgentProjectionTask
from .agent_reduce import AgentReduceTask
from .arxiv_download import ArxivDownloadTask
from .arxiv_search import ArxivSearchTask
from .file_ingest import IngestTask
from .file_read import FileReadTask
from .rss_fetch import RSSFetchTask
from .web_fetch import WebFetchTask
from .web_search import WebSearchTask

TASK_LIBRARY = {
    "file_ingest": IngestTask,
    "agent_map": AgentMapTask,
    "agent_projection": AgentProjectionTask,
    "agent_reduce": AgentReduceTask,
    "arxiv_download": ArxivDownloadTask,
    "web_search": WebSearchTask,
    "arxiv_search": ArxivSearchTask,
    "web_fetch": WebFetchTask,
    "file_read": FileReadTask,
    "rss_fetch": RSSFetchTask,
}
