"""Skill registry — discovers, loads, and provides access to skill manifests."""

import logging

import frontmatter

from ..configs import Config
from ..schemas import SkillConfig

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registry for skill manifests.

    Scans skill_search_paths for .md files, parses frontmatter as SkillConfig,
    and stores them as in-memory blueprints. Follows the same pattern as AgentRegistry.
    """

    def __init__(self, settings: Config) -> None:
        self.settings = settings
        self.skill_search_paths = settings.path.skill_search_paths
        self.blueprints: dict[str, SkillConfig] = {}
        self.load_all()

    def load_all(self) -> None:
        """Scan skill_search_paths for .md files and load them as blueprints."""
        logger.info("Loading skill blueprints\n- skill_search_paths: %s", self.skill_search_paths)
        for skill_dir in self.skill_search_paths:
            if not skill_dir.exists():
                logger.debug("Skipping non-existent directory: %s", skill_dir)
                continue

            for md_file in skill_dir.glob("*.md"):
                try:
                    manifest = frontmatter.load(str(md_file))
                    raw_data = dict(manifest.metadata)
                    raw_data["instructions"] = manifest.content.strip()

                    config = SkillConfig.model_validate(raw_data)
                    # Normalise: strip surrounding whitespace so accidental newlines
                    # or trailing spaces in the frontmatter do not cause silent
                    # lookup misses later on.
                    skill_name = config.name.strip()
                    self.blueprints[skill_name] = config
                except Exception as e:
                    logger.error("Error loading %s: %s", md_file.name, e, exc_info=True)
                    continue

    def get_skill(self, name: str) -> SkillConfig | None:
        """Look up a single skill by name."""
        return self.blueprints.get(name.strip())

    def get_skills_by_names(self, names: list[str]) -> list[SkillConfig]:
        """Return skills matching the given names. Silently skip missing names."""
        return [self.blueprints[name.strip()] for name in names if name.strip() in self.blueprints]

    def get_all_skills(self) -> list[SkillConfig]:
        """Return all loaded skills."""
        return list(self.blueprints.values())