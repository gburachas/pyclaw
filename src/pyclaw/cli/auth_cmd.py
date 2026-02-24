"""Auth command — credential management."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from pyclaw.config import load_config
from pyclaw.config.loader import save_config

console = Console()
auth_app = typer.Typer(name="auth", help="Manage authentication credentials")


@auth_app.command("login")
def login(
    provider: str = typer.Option(
        ..., "--provider", "-p", help="Provider name (openai, anthropic, etc.)"
    ),
) -> None:
    """Login to an LLM provider."""
    cfg = load_config()

    api_key = Prompt.ask(f"Enter API key for {provider}")
    if not api_key:
        console.print("[red]No API key provided.[/red]")
        return

    # Update the appropriate provider config
    provider_map = {
        "openai": cfg.providers.openai,
        "anthropic": cfg.providers.anthropic,
        "openrouter": cfg.providers.openrouter,
        "groq": cfg.providers.groq,
        "deepseek": cfg.providers.deepseek,
        "gemini": cfg.providers.gemini,
        "qwen": cfg.providers.qwen,
        "ollama": cfg.providers.ollama,
        "cerebras": cfg.providers.cerebras,
    }

    pcfg = provider_map.get(provider)
    if pcfg is None:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        console.print(f"Available: {', '.join(provider_map.keys())}")
        return

    pcfg.api_key = api_key
    save_config(cfg)
    console.print(f"[green]Credentials saved for {provider}.[/green]")


@auth_app.command("logout")
def logout(
    provider: str = typer.Option(
        None, "--provider", "-p", help="Provider to logout from (all if omitted)"
    ),
) -> None:
    """Remove stored credentials."""
    cfg = load_config()

    if provider:
        _clear_provider(cfg, provider)
    else:
        for name in ["openai", "anthropic", "openrouter", "groq", "deepseek",
                      "gemini", "qwen", "ollama", "cerebras"]:
            _clear_provider(cfg, name, quiet=True)
        console.print("[green]All credentials cleared.[/green]")

    save_config(cfg)


@auth_app.command("status")
def auth_status() -> None:
    """Show authentication status for all providers."""
    cfg = load_config()
    table = Table(title="Authentication Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Status")
    table.add_column("API Base")

    providers = {
        "openai": cfg.providers.openai,
        "anthropic": cfg.providers.anthropic,
        "openrouter": cfg.providers.openrouter,
        "groq": cfg.providers.groq,
        "deepseek": cfg.providers.deepseek,
        "gemini": cfg.providers.gemini,
        "qwen": cfg.providers.qwen,
        "ollama": cfg.providers.ollama,
        "cerebras": cfg.providers.cerebras,
    }

    for name, pcfg in providers.items():
        if pcfg.api_key:
            masked = pcfg.api_key[:8] + "..." + pcfg.api_key[-4:]
            status = f"[green]Authenticated[/green] ({masked})"
        else:
            status = "[dim]Not configured[/dim]"
        table.add_row(name, status, pcfg.api_base or "(default)")

    console.print(table)


def _clear_provider(cfg: "Config", name: str, quiet: bool = False) -> None:
    providers = {
        "openai": cfg.providers.openai,
        "anthropic": cfg.providers.anthropic,
        "openrouter": cfg.providers.openrouter,
        "groq": cfg.providers.groq,
        "deepseek": cfg.providers.deepseek,
        "gemini": cfg.providers.gemini,
        "qwen": cfg.providers.qwen,
        "ollama": cfg.providers.ollama,
        "cerebras": cfg.providers.cerebras,
    }
    pcfg = providers.get(name)
    if pcfg:
        pcfg.api_key = ""
        pcfg.auth_method = ""
        if not quiet:
            console.print(f"[green]Credentials cleared for {name}.[/green]")
