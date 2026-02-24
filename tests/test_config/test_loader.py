"""Tests for configuration loading."""

import json
import tempfile
from pathlib import Path

import yaml

from pyclaw.config.loader import load_config


def test_load_yaml_config():
    data = {
        "agents": {"defaults": {"model": "test-model"}},
    }
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        yaml.dump(data, f)
        f.flush()
        cfg = load_config(f.name)
    assert cfg.agents.defaults.model == "test-model"


def test_load_json_config():
    data = {
        "agents": {"defaults": {"model": "json-model"}},
    }
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(data, f)
        f.flush()
        cfg = load_config(f.name)
    assert cfg.agents.defaults.model == "json-model"


def test_load_nonexistent_config():
    import pytest
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")
