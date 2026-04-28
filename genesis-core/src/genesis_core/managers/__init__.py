"""
Managers for genesis_core subsystems.

Each manager wraps DB operations for a subsystem:
- UserManager: User (system DB)
- ChatSessionManager: ChatSession, ChatMessage (system DB)
- WorkflowJobManager: WorkflowJob (system DB)
- ScheduledJobManager: WorkflowSchedule (system DB)
- ProductivityManager: Project, Task, JournalEntry (user DB)
- MemoryManager: EventLog, TopicalMemory (memory DB)
"""

from .chat import ChatSessionManager
from .memory import MemoryManager
from .productivity import ProductivityManager
from .scheduled_job import ScheduledJobManager
from .user import UserManager
from .workflow_job import WorkflowJobManager

__all__ = [
    "UserManager",
    "ChatSessionManager",
    "WorkflowJobManager",
    "ScheduledJobManager",
    "ProductivityManager",
    "MemoryManager",
]
