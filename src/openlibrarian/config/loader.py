"""Load and save configuration from ~/.openlibrarian/config.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from openlibrarian.config.models import AppConfig
from openlibrarian.exceptions import ConfigError

DEFAULT_CONFIG_DIR = Path.home() / ".openlibrarian"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration from YAML file."""
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise ConfigError(
            f"Config file not found at {config_path}. Run 'openlibrarian init' to create one."
        )
    try:
        data = yaml.safe_load(config_path.read_text()) or {}
        return AppConfig.model_validate(data)
    except Exception as e:
        raise ConfigError(f"Failed to load config from {config_path}: {e}") from e


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    """Save configuration to YAML file."""
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return config_path
