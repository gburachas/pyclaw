"""Agent instance — individual agent configuration and state."""

from __future__ import annotations

from pathlib import Path

from pytoclaw.agent.context import ContextBuilder
from pytoclaw.config.models import AgentConfig, AgentDefaults, Config
from pytoclaw.models import FallbackCandidate
from pytoclaw.protocols import LLMProvider
from pytoclaw.session.manager import SessionManager
from pytoclaw.tools.registry import ToolRegistry


class AgentInstance:
    """A configured agent with its own workspace, model, tools, and session."""

    def __init__(
        self,
        agent_cfg: AgentConfig,
        defaults: AgentDefaults,
        config: Config,
        provider: LLMProvider,
    ):
        self.id = agent_cfg.id or "default"
        self.name = agent_cfg.name or self.id
        self.workspace = str(
            Path(agent_cfg.workspace or defaults.workspace).expanduser().resolve()
        )

        # Model config
        if agent_cfg.model:
            self.model = agent_cfg.model.primary or defaults.model
            self.fallbacks = agent_cfg.model.fallbacks or defaults.model_fallbacks
        else:
            self.model = defaults.model
            self.fallbacks = defaults.model_fallbacks

        self.max_iterations = defaults.max_tool_iterations
        self.max_tokens = defaults.max_tokens
        self.temperature = defaults.temperature or 0.7
        self.restrict_to_workspace = defaults.restrict_to_workspace

        self.provider = provider
        self.skills_filter = agent_cfg.skills
        self.subagents = agent_cfg.subagents

        # Initialize components
        sessions_dir = str(Path(self.workspace) / "sessions")
        self.sessions = SessionManager(sessions_dir)
        self.context_builder = ContextBuilder(self.workspace)
        self.tools = ToolRegistry()

        # Build fallback candidates
        self.candidates = self._build_candidates()

    def _build_candidates(self) -> list[FallbackCandidate]:
        """Build ordered list of provider/model candidates for fallback."""
        candidates = [FallbackCandidate(provider="primary", model=self.model)]
        for fb in self.fallbacks:
            candidates.append(FallbackCandidate(provider="fallback", model=fb))
        return candidates
