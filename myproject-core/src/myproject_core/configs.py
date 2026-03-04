import secrets
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# This resolves to .../myproject-core/src/myproject_core
# Agents and workflows are now subdirectories of this path
PACKAGE_ROOT = Path(__file__).parent.resolve()


class LLMConfig(BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = Field(default=...)
    model: str = "openrouter/nvidia/nemotron-3-nano-30b-a3b:free"


class PathConfigs(BaseModel):
    # The 'root' for the current execution context.
    # In CLI: This is where the user runs the command.
    # In Server: This is the user's isolated home directory.
    working_directory: Path = Field(default_factory=lambda: Path.cwd().resolve())

    # The location where server would store user's working directory when the system runs in server mode
    @property
    def server_users_directory(self) -> Path:
        return self.working_directory / "user_directories"

    @property
    def internal_state_dir(self) -> Path:
        return self.working_directory / ".myproject"

    # --- Discovery Paths (Read-Only) ---
    # We look for YAMLs in the user's local folder first, then fallback to package defaults.

    @computed_field
    @property
    def agent_search_paths(self) -> List[Path]:
        return [
            PACKAGE_ROOT / "agents",
            self.internal_state_dir / "agents",
        ]

    @computed_field
    @property
    def workflow_search_paths(self) -> List[Path]:
        return [
            PACKAGE_ROOT / "workflows",
            self.internal_state_dir / "workflows",
        ]

    # --- Runtime Paths (Read-Write) ---
    # We use a hidden folder to avoid polluting the user's working directory.
    @computed_field
    @property
    def workspace_directory(self) -> Path:
        return self.internal_state_dir / "workspaces"

    @computed_field
    @property
    def inbox_directory(self) -> Path:
        return self.internal_state_dir / "inbox"

    def ensure_dirs(self):
        """Creates the necessary runtime directories."""
        self.workspace_directory.mkdir(parents=True, exist_ok=True)
        self.inbox_directory.mkdir(parents=True, exist_ok=True)
        self.server_users_directory.mkdir(parents=True, exist_ok=True)


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 600
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    admin_email: Optional[str] = None
    timezone: str = "Australia/Adelaide"


class DatabaseConfig(BaseModel):
    dsn: Optional[str] = None
    db_name: str = "myproject.db"
    echo_sql: bool = False
    # Where the SQLite file lives (Server-wide)
    db_directory: Path = Field(default_factory=lambda: Path.cwd() / "database")

    @computed_field
    def connection_string(self) -> str:
        if self.dsn:
            return self.dsn
        return f"sqlite:///{self.db_directory.absolute() / self.db_name}"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="myproject__",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    llm: LLMConfig
    path: PathConfigs = Field(default_factory=PathConfigs)
    server: ServerConfig = Field(default_factory=ServerConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)


@lru_cache()
def get_config(user_workdir: Optional[Path] = None, override_yaml: Optional[Path] = None) -> Config:
    """
    Factory to retrieve the configuration.

    1. Loads global defaults from Environment Variables / .env
    2. If user_workdir is provided, anchors all paths to that location.
    3. If override_yaml is provided, merges that YAML file into the config.
    """
    # Initialize with Env Vars
    conf = Config()  # type: ignore

    # Apply User Workspace Isolation
    if user_workdir:
        conf.path.working_directory = user_workdir.resolve()

    # Apply YAML Overrides (e.g. for custom LLM keys or specific user preferences)
    if override_yaml and override_yaml.exists():
        with open(override_yaml, "r") as f:
            yaml_data = yaml.safe_load(f)
            if yaml_data:
                # model_copy with update performs a deep merge of the dict
                conf = conf.model_copy(update=yaml_data, deep=True)

    # Ensure runtime directories exist
    conf.path.ensure_dirs()

    return conf


# Default singleton for simple scripts/CLI use
settings = get_config()
