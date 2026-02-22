"""Agent command — interactive chat and one-shot mode."""

from __future__ import annotations

import logging

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from pytoclaw.agent.instance import AgentInstance
from pytoclaw.agent.loop import AgentLoop
from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.config import load_config
from pytoclaw.config.models import AgentConfig
from pytoclaw.providers.factory import create_provider
from pytoclaw.tools.exec_tool import ExecTool
from pytoclaw.tools.file_tools import (
    AppendFileTool,
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from pytoclaw.tools.message_tool import EchoTool
from pytoclaw.tools.web_tools import WebFetchTool, WebSearchTool

logger = logging.getLogger(__name__)
console = Console()


async def run_agent(
    message: str | None = None,
    config_path: str | None = None,
    model_override: str | None = None,
) -> None:
    """Run the agent in interactive or one-shot mode."""
    cfg = load_config(config_path)

    model_name = model_override or cfg.agents.defaults.model
    provider = create_provider(model_name, cfg)
    bus = MessageBus()
    loop = AgentLoop(cfg, bus, provider)

    # Register tools on the default agent
    agent = loop._registry.get_default_agent()
    _register_tools(agent, cfg)

    if message:
        # One-shot mode
        response = await loop.process_direct(message)
        console.print(response)
        return

    # Interactive mode
    console.print(f"[bold]pytoclaw[/bold] (model: {model_name})")
    console.print("Type your message. Use Ctrl+D or 'exit' to quit.\n")

    history_file = f"{cfg.config_dir}/cli_history"
    session: PromptSession[str] = PromptSession(history=FileHistory(history_file))

    while True:
        try:
            user_input = await session.prompt_async("you> ")
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "/quit"):
            console.print("Goodbye!")
            break

        # Handle slash commands
        if user_input.startswith("/"):
            _handle_slash(user_input, agent)
            continue

        response = await loop.process_direct(user_input)
        console.print(f"\n[green]{agent.name}>[/green] {response}\n")


def _register_tools(agent: AgentInstance, cfg: "Config") -> None:
    """Register built-in tools on an agent."""
    ws = agent.workspace
    restrict = agent.restrict_to_workspace

    agent.tools.register(ReadFileTool(ws, restrict))
    agent.tools.register(WriteFileTool(ws, restrict))
    agent.tools.register(EditFileTool(ws, restrict))
    agent.tools.register(AppendFileTool(ws, restrict))
    agent.tools.register(ListDirTool(ws, restrict))
    agent.tools.register(ExecTool(
        ws, restrict,
        custom_deny_patterns=cfg.tools.exec.custom_deny_patterns,
        enable_deny_patterns=cfg.tools.exec.enable_deny_patterns,
    ))
    agent.tools.register(WebFetchTool())
    agent.tools.register(WebSearchTool(
        brave_api_key=cfg.tools.web.brave.api_key,
        tavily_api_key=cfg.tools.web.tavily.api_key,
    ))

    agent.context_builder.set_tools_registry(agent.tools)


def _handle_slash(command: str, agent: AgentInstance) -> None:
    """Handle in-chat slash commands."""
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd == "/help":
        console.print("Available commands:")
        console.print("  /help     - Show this help")
        console.print("  /model    - Show current model")
        console.print("  /tools    - List available tools")
        console.print("  /clear    - Clear session history")
        console.print("  /exit     - Exit")
    elif cmd == "/model":
        console.print(f"Model: {agent.model}")
    elif cmd == "/tools":
        names = agent.tools.list_names()
        console.print(f"Tools ({len(names)}): {', '.join(names)}")
    elif cmd == "/clear":
        agent.sessions.clear("cli")
        console.print("Session cleared.")
    elif cmd in ("/exit", "/quit"):
        raise EOFError
    else:
        console.print(f"Unknown command: {cmd}")
