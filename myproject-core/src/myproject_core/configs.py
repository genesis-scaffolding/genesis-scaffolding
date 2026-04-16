import secrets
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import LLMModelConfig, LLMProvider

PACKAGE_ROOT = Path(__file__).parent.resolve()  # Find the myproject_core directory in source


class PathConfigs(BaseModel):
    # Current working directory context (can be server or individual user's workspace)
    working_directory: Path = Field(default_factory=lambda: Path.cwd().resolve())
    # Server root (i.e., where the cli is called)
    server_root_directory: Path = Field(default_factory=lambda: Path.cwd().resolve())

    @property
    def server_users_directory(self) -> Path:
        return self.working_directory / "user_directories"

    @property
    def internal_state_dir(self) -> Path:
        return self.working_directory / ".myproject"

    @computed_field
    @property
    def agent_search_paths(self) -> list[Path]:
        return [PACKAGE_ROOT / "agents" / "builtin_agents", self.internal_state_dir / "agents"]

    @computed_field
    @property
    def workflow_search_paths(self) -> list[Path]:
        return [PACKAGE_ROOT / "workflow" / "builtin_workflows", self.internal_state_dir / "workflows"]

    @computed_field
    @property
    def workspace_directory(self) -> Path:
        return self.internal_state_dir / "workspaces"

    @computed_field
    @property
    def inbox_directory(self) -> Path:
        return self.internal_state_dir / "inbox"

    def ensure_dirs(self):
        self.workspace_directory.mkdir(parents=True, exist_ok=True)
        self.inbox_directory.mkdir(parents=True, exist_ok=True)
        self.server_users_directory.mkdir(parents=True, exist_ok=True)


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_origins_extra: str = ""  # Comma-separated additional origins (e.g., "https://yoga.tail43a73c.ts.net,https://other.tail.net")

    @computed_field
    @property
    def all_cors_origins(self) -> list[str]:
        """Combine default cors_origins with extra origins from env var."""
        extra = [o.strip() for o in self.cors_origins_extra.split(",") if o.strip()]
        return self.cors_origins + extra

    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 600
    admin_username: str | None = None
    admin_password: str | None = None
    admin_email: str | None = None


class DatabaseConfig(BaseModel):
    dsn: str | None = None
    db_name: str = "myproject.db"
    echo_sql: bool = False
    db_directory: Path = Field(default_factory=lambda: Path.cwd() / ".myproject" / "database")

    @computed_field
    @property
    def connection_string(self) -> str:
        if self.dsn:
            return self.dsn
        return f"sqlite:///{self.db_directory.absolute() / self.db_name}"


class AgentLoopConfig(BaseModel):
    clipboard_item_ttl: int = 100


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="myproject__",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Timezone for this specific working context (single user CLI use, or per-user on server)
    timezone: str = "Australia/Adelaide"

    # Dictionaries of providers and models
    # Key is the nickname used in the app
    providers: dict[str, LLMProvider] = Field(default_factory=dict)
    models: dict[str, LLMModelConfig] = Field(default_factory=dict)

    # Optional: pointer to which model nickname to use by default
    default_model: str = "default"

    # Configuration of various types of file paths
    path: PathConfigs = Field(default_factory=PathConfigs)

    # Server-specific configurations
    server: ServerConfig = Field(default_factory=ServerConfig)

    # Database configurations
    # system-wide database
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    # user-specific database
    user_db: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig(db_name="user_private.db"))
    # user-specific memory database
    memory_db: DatabaseConfig = Field(
        default_factory=lambda: DatabaseConfig(db_name="memory/user_memory.db")
    )

    # Agent configurations
    agent_loop_config: AgentLoopConfig = Field(default_factory=AgentLoopConfig)

    @model_validator(mode="after")
    def validate_llm_references(self) -> "Config":
        """Ensures all models point to valid providers and the default_model exists."""
        # 1. Check if all models reference an existing provider
        for model_nickname, model_cfg in self.models.items():
            if model_cfg.provider not in self.providers:
                available = list(self.providers.keys())
                raise ValueError(
                    f"Model '{model_nickname}' references unknown provider '{model_cfg.provider}'. "
                    f"Available providers: {available}",
                )

        # 2. Check if default_model actually exists in the models dict
        # We only check this if models are actually defined
        if self.models and self.default_model not in self.models:
            raise ValueError(
                f"default_model '{self.default_model}' is not defined in the 'models' dictionary.",
            )

        return self

    @property
    def default_llm_config(self) -> tuple[LLMModelConfig, LLMProvider]:
        """Convenience property to get the currently selected default LLM details."""
        m = self.models[self.default_model]
        p = self.providers[m.provider]
        return m, p


def deep_merge(base: dict, update: dict) -> dict:
    """Recursively merges two dictionaries.
    This ensures that adding a new model in YAML doesn't delete existing models from .env.
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            base[key] = deep_merge(base[key], value)
        else:
            base[key] = value
    return base


# @lru_cache()
def get_config(user_workdir: Path | None = None, override_yaml: Path | None = None) -> Config:
    # 1. Initialize from Environment Variables / .env
    # Pydantic BaseSettings automatically populates this
    conf_dict = Config().model_dump()

    # 2. Apply YAML Overrides (Merging instead of overwriting)
    if override_yaml and override_yaml.exists():
        with open(override_yaml) as f:
            yaml_data = yaml.safe_load(f)
            if yaml_data:
                conf_dict = deep_merge(conf_dict, yaml_data)

    # Re-validate the merged dictionary into the Config model
    conf = Config(**conf_dict)

    # 3. Apply User Workspace Isolation
    if user_workdir:
        conf.path.working_directory = user_workdir.resolve()

    # --- DATABASE PATH LOGIC ---

    # System DB: Should always stay in the 'database' folder relative to
    # the server's starting directory, NOT the user's sandbox.
    # We anchor this to Path.cwd() at the time of app start.
    if not conf.db.dsn:
        # If not provided by user, ensure it stays in the global database dir
        conf.db.db_directory = conf.path.server_root_directory / ".myproject" / "database"

    # User DB: Should always be inside the internal_state_dir (.myproject)
    # whether in CLI mode (current dir) or Server mode (user sandbox).
    if not conf.user_db.dsn:
        conf.user_db.db_directory = conf.path.internal_state_dir

    # Memory DB: Same as user_db — inside internal_state_dir/memory/
    if not conf.memory_db.dsn:
        conf.memory_db.db_directory = conf.path.internal_state_dir / "memory"
        conf.memory_db.db_name = "user_memory.db"

    # Ensure runtime directories exist
    conf.path.ensure_dirs()
    conf.db.db_directory.mkdir(parents=True, exist_ok=True)
    conf.user_db.db_directory.mkdir(parents=True, exist_ok=True)
    conf.memory_db.db_directory.mkdir(parents=True, exist_ok=True)

    return conf


settings = get_config()
