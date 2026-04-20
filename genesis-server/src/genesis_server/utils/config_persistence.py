from pathlib import Path
from typing import Any

import yaml


def update_user_yaml_config(user_workdir: Path, key: str, nickname: str, value: Any):
    """Updates a specific entry within 'providers' or 'models' in the user's configs.yaml
    """
    config_path = user_workdir / "config.yaml"

    # 1. Load existing data
    data = {}
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

    # 2. Ensure nested dict exists
    if key not in data:
        data[key] = {}

    # 3. Update the specific nickname
    if value is None:  # Logic for deletion
        if nickname in data[key]:
            del data[key][nickname]
    else:
        data[key][nickname] = value

    # 4. Write back
    with open(config_path, "w") as f:
        yaml.dump(data, f, sort_keys=False)


def update_user_top_level_config(user_workdir: Path, updates: dict):
    """Updates top-level keys like 'default_model'"""
    config_path = user_workdir / "config.yaml"
    data = {}
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

    data.update(updates)

    with open(config_path, "w") as f:
        yaml.dump(data, f, sort_keys=False)
