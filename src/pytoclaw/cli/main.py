"""pytoclaw CLI — main entry point."""

from __future__ import annotations

import asyncio
import sys

import typer
from rich.console import Console

from pytoclaw import __version__

app = typer.Typer(
    name="pytoclaw",
    help="Ultra-lightweight personal AI assistant",
    no_args_is_help=True,
)
console = Console()


@app.command()
def agent(
    message: str = typer.Argument(None, help="One-shot message (omit for interactive mode)"),
    config: str = typer.Option(None, "--config", "-c", help="Path to config file"),
    model: str = typer.Option(None, "--model", "-m", help="Override model name"),
) -> None:
    """Interactive chat or one-shot message with the agent."""
    from pytoclaw.cli.agent_cmd import run_agent

    asyncio.run(run_agent(message=message, config_path=config, model_override=model))


@app.command()
def onboard() -> None:
    """Initialize pytoclaw configuration and workspace."""
    from pytoclaw.cli.onboard_cmd import run_onboard

    run_onboard()


@app.command()
def status() -> None:
    """Show pytoclaw status and configuration info."""
    from pytoclaw.config import load_config

    try:
        cfg = load_config()
        console.print(f"[bold]pytoclaw[/bold] v{__version__}")
        console.print(f"  Default model: {cfg.agents.defaults.model}")
        console.print(f"  Workspace: {cfg.agents.defaults.workspace}")
        console.print(f"  Agents: {len(cfg.agents.agents) or 1}")
        console.print(f"  Tools config: exec deny patterns {'enabled' if cfg.tools.exec.enable_deny_patterns else 'disabled'}")
    except FileNotFoundError:
        console.print("[yellow]Not configured. Run 'pytoclaw onboard' first.[/yellow]")


@app.command()
def version() -> None:
    """Show version."""
    console.print(f"pytoclaw v{__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
