"""pyclaw CLI — main entry point."""

from __future__ import annotations

import asyncio
import sys

import typer
from rich.console import Console

from pyclaw import __version__

app = typer.Typer(
    name="pyclaw",
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
    from pyclaw.cli.agent_cmd import run_agent

    asyncio.run(run_agent(message=message, config_path=config, model_override=model))


@app.command()
def onboard() -> None:
    """Initialize pyclaw configuration and workspace."""
    from pyclaw.cli.onboard_cmd import run_onboard

    run_onboard()


@app.command()
def status() -> None:
    """Show pyclaw status and configuration info."""
    from pyclaw.config import load_config

    try:
        cfg = load_config()
        console.print(f"[bold]pyclaw[/bold] v{__version__}")
        console.print(f"  Default model: {cfg.agents.defaults.model}")
        console.print(f"  Workspace: {cfg.agents.defaults.workspace}")
        console.print(f"  Agents: {len(cfg.agents.agents) or 1}")
        console.print(f"  Tools config: exec deny patterns {'enabled' if cfg.tools.exec.enable_deny_patterns else 'disabled'}")
    except FileNotFoundError:
        console.print("[yellow]Not configured. Run 'pyclaw onboard' first.[/yellow]")


@app.command()
def version() -> None:
    """Show version."""
    console.print(f"pyclaw v{__version__}")


@app.command()
def gateway(
    config: str = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Start multi-channel gateway server."""
    from pyclaw.cli.gateway_cmd import run_gateway

    asyncio.run(run_gateway(config_path=config))


# Register sub-command groups
from pyclaw.cli.auth_cmd import auth_app
from pyclaw.cli.cron_cmd import cron_app
from pyclaw.cli.skills_cmd import skills_app

app.add_typer(auth_app)
app.add_typer(cron_app)
app.add_typer(skills_app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
