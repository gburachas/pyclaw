"""Skills command — manage skill packages."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console

console = Console()
skills_app = typer.Typer(name="skills", help="Manage skill packages")


@skills_app.command("list")
def list_skills() -> None:
    """List installed skills."""
    from pytoclaw.config import load_config

    cfg = load_config()
    workspace = Path(cfg.agents.defaults.workspace).expanduser()
    skills_dir = workspace / "skills"

    if not skills_dir.exists():
        console.print("No skills installed.")
        return

    skills = [d for d in sorted(skills_dir.iterdir()) if d.is_dir()]
    if not skills:
        console.print("No skills installed.")
        return

    console.print(f"[bold]Installed skills ({len(skills)}):[/bold]")
    for skill_dir in skills:
        skill_file = skill_dir / "SKILL.md"
        origin_file = skill_dir / ".skill-origin.json"

        name = skill_dir.name
        source = ""
        if origin_file.exists():
            import json
            origin = json.loads(origin_file.read_text())
            source = f" (from {origin.get('registry', '?')})"

        has_def = "[green]SKILL.md[/green]" if skill_file.exists() else "[dim]no SKILL.md[/dim]"
        console.print(f"  {name}{source} — {has_def}")


@skills_app.command("show")
def show_skill(
    name: str = typer.Argument(..., help="Skill name to show"),
) -> None:
    """Display a skill's definition."""
    from pytoclaw.config import load_config

    cfg = load_config()
    workspace = Path(cfg.agents.defaults.workspace).expanduser()
    skill_file = workspace / "skills" / name / "SKILL.md"

    if not skill_file.exists():
        console.print(f"[red]Skill '{name}' not found or has no SKILL.md[/red]")
        return

    console.print(skill_file.read_text())


@skills_app.command("remove")
def remove_skill(
    name: str = typer.Argument(..., help="Skill name to remove"),
) -> None:
    """Remove an installed skill."""
    from pytoclaw.config import load_config

    cfg = load_config()
    workspace = Path(cfg.agents.defaults.workspace).expanduser()
    skill_dir = workspace / "skills" / name

    if not skill_dir.exists():
        console.print(f"[red]Skill '{name}' not found.[/red]")
        return

    shutil.rmtree(skill_dir)
    console.print(f"[green]Skill '{name}' removed.[/green]")


@skills_app.command("install-builtin")
def install_builtin() -> None:
    """Install built-in skills to workspace."""
    from pytoclaw.config import load_config

    cfg = load_config()
    workspace = Path(cfg.agents.defaults.workspace).expanduser()
    skills_dir = workspace / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Built-in skills shipped with pytoclaw
    builtins = {
        "weather": "# Weather Skill\n\nGet current weather for a location.\n\nWhen the user asks about weather, use the web_search tool to find current conditions.\n",
        "calculator": "# Calculator Skill\n\nPerform mathematical calculations.\n\nWhen the user asks for calculations, use Python expressions via the exec tool.\n",
    }

    installed = 0
    for name, content in builtins.items():
        target = skills_dir / name
        target.mkdir(exist_ok=True)
        skill_file = target / "SKILL.md"
        if not skill_file.exists():
            skill_file.write_text(content)
            console.print(f"  Installed: {name}")
            installed += 1
        else:
            console.print(f"  Skipped (exists): {name}")

    console.print(f"[green]{installed} built-in skill(s) installed.[/green]")
