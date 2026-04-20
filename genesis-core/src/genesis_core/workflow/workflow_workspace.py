import logging
from datetime import datetime
from pathlib import Path

from ..configs import Config, get_config
from ..schemas import JobContext
from ..utils import slugify

logger = logging.getLogger(__name__)


class WorkspaceManager:
    def __init__(self, settings: Config):
        self.settings = settings
        # Ensure the base 'workspaces' folder exists immediately
        self.settings.path.workspace_directory.mkdir(parents=True, exist_ok=True)

    def _generate_unique_path(self, name: str) -> Path:
        """Combines slug, timestamp, and collision checks."""
        slug = slugify(name)

        # Handle Windows reserved names
        reserved = {"con", "prn", "aux", "nul", "com1", "com2", "lpt1"}
        if slug in reserved:
            slug = f"safe-{slug}"

        # Create a timestamped folder name (Sortable and unique)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = f"{timestamp}_{slug}"

        return self.settings.path.workspace_directory / dir_name

    def create_job(self, name: str) -> JobContext:
        """The main entry point: creates the physical directory structure
        and returns the JobContext.
        """
        job_path = self._generate_unique_path(name)
        logger.info("Creating job workspace: %s", job_path)

        # Create the 'Russian Doll' structure
        job_path.mkdir(parents=True, exist_ok=False)
        (job_path / "input").mkdir()
        (job_path / "internal").mkdir()
        (job_path / "output").mkdir()

        # Optional: Save original name to internal metadata for UI display
        with open(job_path / "internal" / "meta.txt", "w") as f:
            f.write(f"Original Name: {name}\nCreated: {datetime.now().isoformat()}")

        logger.debug("Job workspace created: %s", job_path)
        return JobContext(job_path)


def main():
    settings = get_config()
    print(settings.path)
    workspace_manager = WorkspaceManager(settings)
    job_context = workspace_manager.create_job("my testing workspace dir")
    print(job_context)


if __name__ == "__main__":
    main()
