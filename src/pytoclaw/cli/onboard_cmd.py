"""Onboard command — first-run setup wizard."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from pytoclaw.config.loader import save_config
from pytoclaw.config.models import Config, ProviderConfig

console = Console()


def run_onboard() -> None:
    """Interactive setup wizard for pytoclaw."""
    console.print("[bold]Welcome to pytoclaw![/bold]\n")
    console.print("Let's set up your configuration.\n")

    config_dir = Path.home() / ".pytoclaw"
    config_file = config_dir / "config.yaml"

    if config_file.exists():
        overwrite = Prompt.ask(
            "Config already exists. Overwrite?", choices=["y", "n"], default="n"
        )
        if overwrite != "y":
            console.print("Setup cancelled.")
            return

    # Choose provider
    provider = Prompt.ask(
        "Primary LLM provider",
        choices=["openai", "anthropic", "ollama", "openrouter"],
        default="openai",
    )

    api_key = ""
    if provider != "ollama":
        api_key = Prompt.ask(f"{provider.title()} API key")

    model = _default_model(provider)
    model = Prompt.ask("Default model", default=model)

    # Build config
    cfg = Config()
    cfg.agents.defaults.model = model

    if provider == "openai":
        cfg.providers.openai.api_key = api_key
    elif provider == "anthropic":
        cfg.providers.anthropic.api_key = api_key
    elif provider == "openrouter":
        cfg.providers.openrouter.api_key = api_key
        cfg.providers.openrouter.api_base = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        cfg.providers.ollama.api_base = "http://localhost:11434/v1"

    # Create workspace
    workspace = Path(cfg.agents.defaults.workspace).expanduser()
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "memory").mkdir(exist_ok=True)
    (workspace / "sessions").mkdir(exist_ok=True)
    (workspace / "skills").mkdir(exist_ok=True)

    # Write default identity files if they don't exist
    _write_if_missing(workspace / "IDENTITY.md", _DEFAULT_IDENTITY)
    _write_if_missing(workspace / "SOUL.md", _DEFAULT_SOUL)
    _write_if_missing(workspace / "AGENT.md", _DEFAULT_AGENT)

    # Save config
    save_config(cfg)

    console.print(f"\n[green]Configuration saved to {config_file}[/green]")
    console.print(f"Workspace created at {workspace}")
    console.print("\nRun [bold]pytoclaw agent[/bold] to start chatting!")


def _default_model(provider: str) -> str:
    return {
        "openai": "gpt-4o",
        "anthropic": "anthropic/claude-sonnet-4-6",
        "ollama": "ollama/llama3",
        "openrouter": "openrouter/meta-llama/llama-3-70b",
    }.get(provider, "gpt-4o")


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


_DEFAULT_IDENTITY = """# Identity

I am pytoclaw, a personal AI assistant.
Version: 0.1.0
"""

_DEFAULT_SOUL = """# Soul

I am helpful, concise, and thoughtful. I focus on getting things done
efficiently while being transparent about what I'm doing.
"""

_DEFAULT_AGENT = """# Agent Instructions

- Use tools to accomplish tasks rather than just describing what to do.
- Read files before modifying them.
- Be concise in responses.
- Remember important facts in MEMORY.md.
"""
