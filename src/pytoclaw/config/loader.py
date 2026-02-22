"""Configuration loading for pytoclaw."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from pytoclaw.config.models import Config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".pytoclaw"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"


def load_config(path: Path | str | None = None) -> Config:
    """Load configuration from a YAML or JSON file.

    Search order:
    1. Explicit path argument
    2. ~/.pytoclaw/config.yaml
    3. ~/.pytoclaw/config.json
    4. Default config
    """
    if path is not None:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return _load_from_file(config_path)

    # Try default locations
    for candidate in [
        DEFAULT_CONFIG_DIR / "config.yaml",
        DEFAULT_CONFIG_DIR / "config.yml",
        DEFAULT_CONFIG_DIR / "config.json",
    ]:
        if candidate.exists():
            logger.info("Loading config from %s", candidate)
            return _load_from_file(candidate)

    logger.info("No config file found, using defaults")
    return Config()


def _load_from_file(path: Path) -> Config:
    """Load config from a specific file."""
    raw = path.read_text(encoding="utf-8")

    if path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(raw) or {}
    elif path.suffix == ".json":
        data = json.loads(raw)
    else:
        raise ValueError(f"Unsupported config format: {path.suffix}")

    return Config.model_validate(data)


def save_config(config: Config, path: Path | None = None) -> None:
    """Save configuration to a YAML file."""
    target = path or DEFAULT_CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(exclude_defaults=True)
    target.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    logger.info("Config saved to %s", target)
