# Re-export User from genesis_core so that imports like `from .models.user import User`
# continue to work throughout the server without needing to know about genesis_core.
from genesis_core.database.models import User

__all__ = ["User"]
