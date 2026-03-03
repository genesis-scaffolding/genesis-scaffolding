import os
import secrets
from pathlib import Path

from pydantic import BaseModel, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    # URL of the model provider backend. Default to openrouter
    base_url: str = "https://openrouter.ai/api/v1"
    # API key for accessing the model provider backend. Required
    api_key: str = Field(default=...)
    # Identifier of the model at the provider backend.
    model: str = "openrouter/nvidia/nemotron-3-nano-30b-a3b:free"


class PathConfigs(BaseModel):
    # Path to working directory. Default to current working directory.
    working_directory: Path = Path(".")
    # Path to workspace directory that stores job directories of workflows
    workspace_directory: Path = Path("./workspaces/")
    # Path to workflow directory that stores YAML manifest files of workflows
    workflow_directory: Path = Path("./workflows/")
    # Path to agent directory that stores YAML manifest files of agents
    agent_directory: Path = Path("./agents/")
    # Path to a directory where user can drop input files for workflows
    inbox_directory: Path = Path("./inbox/")
    # Path to a directory where database would be stored
    db_directory: Path = Path("./database/")

    @model_validator(mode="after")
    def resolve_paths(self) -> "PathConfigs":
        # 1. Resolve Working Directory
        if self.working_directory is None:
            self.working_directory = Path.cwd().resolve()
        else:
            self.working_directory = self.working_directory.resolve()

        # 2. Create workspace and workflow directories underneath working directory
        self.workspace_directory = self.working_directory / "workspaces"
        self.workflow_directory = self.working_directory / "workflows"
        self.agent_directory = self.working_directory / "agents"
        self.inbox_directory = self.working_directory / "inbox"
        self.db_directory = self.working_directory / "database"

        # 3. Side-effect: Ensure they exist
        self.workspace_directory.mkdir(parents=True, exist_ok=True)
        self.workflow_directory.mkdir(parents=True, exist_ok=True)
        self.agent_directory.mkdir(parents=True, exist_ok=True)
        self.inbox_directory.mkdir(parents=True, exist_ok=True)
        self.db_directory.mkdir(parents=True, exist_ok=True)
        return self


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
    # Generates a secure 32-byte hex string if not provided
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 600
    # Initial Admin Account (Optional)
    admin_username: str | None = None
    admin_password: str | None = None
    admin_email: str | None = None
    timezone: str = "Australia/Adelaide"  # Default timezone for the server


class DatabaseConfig(BaseModel):
    # If this is provided (e.g. postgres://...), we use it directly
    dsn: str | None = None
    db_name: str = "myproject.db"
    echo_sql: bool = False

    # We will pass the working directory here during initialization
    _work_dir: Path = Path(".")

    @computed_field
    def connection_string(self) -> str:
        if self.dsn:
            return self.dsn
        # Default to SQLite using the resolved working directory
        db_path = settings.path.db_directory / self.db_name
        return f"sqlite:///{db_path.absolute()}"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="myproject_",
        env_file=[".env", ".env.prod"],
        env_nested_delimiter="_",
        env_nested_max_split=1,
    )

    llm: LLMConfig
    path: PathConfigs = Field(default_factory=PathConfigs)
    server: ServerConfig = Field(default_factory=ServerConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)

    @model_validator(mode="after")
    def sync_db_path(self) -> "Config":
        # Inject the resolved working directory into the DB config
        self.db._work_dir = self.path.working_directory
        return self


# Create the singleton instance
settings = Config()  # pyright: ignore[reportCallIssue]


def main():
    print(os.getcwd())
    print(settings.model_dump_json())


if __name__ == "__main__":
    main()
