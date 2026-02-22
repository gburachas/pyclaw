"""Tests for configuration models."""

from pytoclaw.config.models import AgentDefaults, Config


def test_config_defaults():
    cfg = Config()
    assert cfg.agents.defaults.model == "gpt-4o"
    assert cfg.agents.defaults.max_tokens == 8192
    assert cfg.agents.defaults.restrict_to_workspace is True
    assert cfg.agents.defaults.max_tool_iterations == 20


def test_config_from_dict():
    data = {
        "agents": {
            "defaults": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 4096,
            }
        }
    }
    cfg = Config.model_validate(data)
    assert cfg.agents.defaults.model == "claude-sonnet-4-6"
    assert cfg.agents.defaults.max_tokens == 4096
    # Other defaults still apply
    assert cfg.agents.defaults.temperature == 0.7


def test_agent_defaults_workspace_expansion():
    defaults = AgentDefaults(workspace="~/.pytoclaw/workspace")
    assert "~" in defaults.workspace  # Raw, not expanded — expansion happens in AgentInstance
