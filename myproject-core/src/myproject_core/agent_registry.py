import re
from pathlib import Path
from typing import Any

import frontmatter

from myproject_core.agent import Agent

from .agent_memory import AgentMemory
from .configs import Config, get_config
from .schemas import AgentConfig, LLMModel, LLMProvider


class AgentRegistry:
    def __init__(self, settings: Config):
        self.agent_search_paths = settings.path.agent_search_paths
        self.settings = settings
        # Store CONFIGS (blueprints), not INSTANCES
        self.blueprints: dict[str, AgentConfig] = {}
        self.load_all()

    def load_all(self):
        """Scans directory and stores the blueprints."""
        for agent_dir in self.agent_search_paths:
            if not agent_dir.exists():
                continue  # Continue to avoid non-existent directories

            for md_file in agent_dir.glob("*.md"):
                try:
                    agent_manifest = frontmatter.load(str(md_file))
                    raw_data = agent_manifest.metadata
                    raw_data["system_prompt"] = agent_manifest.content.strip()

                    # Automatically add default LLM config to the agent if the agent does not have LLM config
                    if not raw_data.get("llm_config"):
                        raw_data["llm_config"] = self._get_llm_model_config()

                    config = AgentConfig.model_validate(raw_data)
                    # Store the name from the file stem or manifest
                    self.blueprints[md_file.stem] = config
                except Exception as e:
                    print(f"Error loading {md_file.name}: {e}")
                    continue  # Continue so that it does not break init step if user accidentally write a bad agent

    def add_agent(self, agent_data: dict) -> str:
        """
        Persists a new agent to the user's local agent directory.
        Returns the agent_id (filename stem).
        """
        # 1. Determine the writeable path (the user-specific internal state dir)
        # We assume that the last path is the user-specific directory
        write_dir = self.settings.path.agent_search_paths[-1]
        write_dir.mkdir(parents=True, exist_ok=True)

        # 2. Generate a valid filename (slugify the name)
        agent_id = re.sub(r"[^a-z0-9]+", "_", agent_data["name"].lower()).strip("_")
        file_path = write_dir / f"{agent_id}.md"

        if file_path.exists():
            # Basic collision handling: append a suffix if exists
            # In a production app, you might want to return an error instead
            import uuid

            agent_id = f"{agent_id}_{uuid.uuid4().hex[:4]}"
            file_path = write_dir / f"{agent_id}.md"

        # 3. Separate content from metadata
        content = agent_data.pop("system_prompt", "")

        # 4. Create the frontmatter post
        post = frontmatter.Post(content, **agent_data)

        # 5. Write to disk
        with open(file_path, "wb") as f:
            frontmatter.dump(post, f)

        # 6. Reload registry to include the new agent
        self.load_all()

        return agent_id

    def delete_agent(self, agent_id: str):
        """
        Persists a new agent to the user's local agent directory.
        Returns the agent_id (filename stem).
        """
        # Find the requested agent
        blueprint = self.blueprints.get(agent_id)
        if not blueprint:
            raise ValueError(f"Agent '{agent_id}' not found in registry.")

        if blueprint.read_only:
            raise ValueError(f"Agent '{agent_id}' is read-only.")

        agent_file_path = self.settings.path.agent_search_paths[-1] / f"{agent_id}.md"

        if not agent_file_path.exists():
            raise ValueError(f"The specification file of agent '{agent_id}' cannot be found.")

        try:
            agent_file_path.unlink()
        except FileNotFoundError:
            pass

        # Reload the registry so that the change is reflected
        self.load_all()

    def edit_agent(self, agent_id: str, updated_data: dict[str, Any]) -> str:
        """
        Update an existing agent’s metadata and/or system prompt.
        """
        write_dir = self.settings.path.agent_search_paths[-1]
        file_path = write_dir / f"{agent_id}.md"

        if not file_path.exists():
            raise FileNotFoundError(f"Agent '{agent_id}' does not exist.")

        # Load the current file
        existing_post = frontmatter.load(str(file_path))

        # Check read-only status
        if existing_post.get("read_only", False):
            raise ValueError(f"Agent '{agent_id}' is read‑only and cannot be edited.")

        # Extract the system_prompt to be used as the Markdown body
        new_content = updated_data.pop("system_prompt", existing_post.content)

        # Merge metadata
        new_metadata = existing_post.metadata.copy()
        new_metadata.update(updated_data)

        # Create the Post object correctly
        new_post = frontmatter.Post(new_content.strip())

        # We ensure 'system_prompt' isn't accidentally duplicated in the YAML block
        if "system_prompt" in new_metadata:
            del new_metadata["system_prompt"]

        new_post.metadata.update(new_metadata)

        # Write the updated post atomically
        tmp_path = file_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "wb") as f:
                frontmatter.dump(new_post, f)
            tmp_path.replace(file_path)
        except Exception as exc:
            if tmp_path.exists():
                tmp_path.unlink()
            raise OSError(f"Failed to persist updated agent '{agent_id}'.") from exc

        # Refresh the in‑memory registry
        self.load_all()

        return agent_id

    def create_agent(
        self,
        name: str,
        working_directory: Path | None = None,
        memory: AgentMemory | None = None,
        **overrides,
    ) -> Agent:
        """Factory method to spawn a fresh agent instance."""
        blueprint = self.blueprints.get(name)
        if not blueprint:
            raise ValueError(f"Agent '{name}' not found in registry.")

        # Optional: Allow overriding config values at runtime
        # We deepcopy to ensure we don't mutate the original blueprint
        instance_config = blueprint.model_copy(deep=True, update=overrides)

        return Agent(
            agent_config=instance_config,
            working_directory=working_directory,
            memory=memory,
            timezone=self.settings.server.timezone,
        )

    def get_all_agent_types(self):
        return self.blueprints.keys()

    def _get_llm_model_config(self) -> LLMModel:
        base_url = self.settings.llm.base_url
        api_key = self.settings.llm.api_key
        llm_model = self.settings.llm.model
        return LLMModel(provider=LLMProvider(base_url=base_url, api_key=api_key), model=llm_model)


def main():
    settings = get_config()
    agent_registry = AgentRegistry(settings=settings)
    print(agent_registry.get_all_agent_types())


if __name__ == "__main__":
    main()
