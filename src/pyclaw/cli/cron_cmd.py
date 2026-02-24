"""Cron command — manage scheduled tasks."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

console = Console()
cron_app = typer.Typer(name="cron", help="Manage scheduled tasks")


@cron_app.command("list")
def list_jobs() -> None:
    """List all scheduled jobs."""
    from pyclaw.services.cron_service import CronService
    from pyclaw.config import load_config

    cfg = load_config()
    workspace = cfg.agents.defaults.workspace
    service = CronService(f"{workspace}/cron")

    jobs = service.list_jobs()
    if not jobs:
        console.print("No scheduled jobs.")
        return

    table = Table(title="Scheduled Jobs")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Schedule")
    table.add_column("Status")
    table.add_column("Next Run")

    for job in jobs:
        schedule = job.get("schedule", {})
        kind = schedule.get("kind", "?")
        if kind == "every":
            sched_str = f"every {schedule.get('every_ms', 0) // 1000}s"
        elif kind == "cron":
            sched_str = schedule.get("expr", "?")
        elif kind == "at":
            sched_str = "one-time"
        else:
            sched_str = kind

        status = "[green]enabled[/green]" if job.get("enabled", True) else "[dim]disabled[/dim]"
        next_run = job.get("state", {}).get("next_run", "—")

        table.add_row(job["id"][:8], job["name"], sched_str, status, str(next_run))

    console.print(table)


@cron_app.command("add")
def add_job(
    name: str = typer.Option(..., "--name", "-n", help="Job name"),
    message: str = typer.Option(..., "--message", "-m", help="Task prompt"),
    every: int = typer.Option(None, "--every", "-e", help="Interval in seconds"),
    cron: str = typer.Option(None, "--cron", "-c", help="Cron expression"),
    deliver: bool = typer.Option(True, "--deliver", "-d", help="Send directly to channel"),
    channel: str = typer.Option("", "--channel", help="Target channel"),
    to: str = typer.Option("", "--to", help="Target chat ID"),
) -> None:
    """Add a scheduled job."""
    from pyclaw.services.cron_service import CronService
    from pyclaw.config import load_config

    cfg = load_config()
    workspace = cfg.agents.defaults.workspace
    service = CronService(f"{workspace}/cron")

    schedule: dict = {}
    if every:
        schedule = {"kind": "every", "every_ms": every * 1000}
    elif cron:
        schedule = {"kind": "cron", "expr": cron}
    else:
        console.print("[red]Either --every or --cron is required.[/red]")
        return

    job = service.add_job(
        name=name, schedule=schedule, message=message,
        deliver=deliver, channel=channel, chat_id=to,
    )
    console.print(f"[green]Job '{name}' created with ID: {job['id']}[/green]")


@cron_app.command("remove")
def remove_job(
    job_id: str = typer.Argument(..., help="Job ID to remove"),
) -> None:
    """Remove a scheduled job."""
    from pyclaw.services.cron_service import CronService
    from pyclaw.config import load_config

    cfg = load_config()
    workspace = cfg.agents.defaults.workspace
    service = CronService(f"{workspace}/cron")

    if service.remove_job(job_id):
        console.print(f"[green]Job {job_id} removed.[/green]")
    else:
        console.print(f"[red]Job {job_id} not found.[/red]")


@cron_app.command("enable")
def enable_job(
    job_id: str = typer.Argument(..., help="Job ID to enable"),
) -> None:
    """Enable a scheduled job."""
    from pyclaw.services.cron_service import CronService
    from pyclaw.config import load_config

    cfg = load_config()
    workspace = cfg.agents.defaults.workspace
    service = CronService(f"{workspace}/cron")
    service.enable_job(job_id, True)
    console.print(f"[green]Job {job_id} enabled.[/green]")


@cron_app.command("disable")
def disable_job(
    job_id: str = typer.Argument(..., help="Job ID to disable"),
) -> None:
    """Disable a scheduled job."""
    from pyclaw.services.cron_service import CronService
    from pyclaw.config import load_config

    cfg = load_config()
    workspace = cfg.agents.defaults.workspace
    service = CronService(f"{workspace}/cron")
    service.enable_job(job_id, False)
    console.print(f"[green]Job {job_id} disabled.[/green]")
