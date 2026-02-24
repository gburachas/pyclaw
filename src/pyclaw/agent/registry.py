"""Agent registry — manages multiple agents and routes messages."""

from __future__ import annotations

import logging

from pyclaw.agent.instance import AgentInstance
from pyclaw.config.models import Config
from pyclaw.models import RouteInput, ResolvedRoute
from pyclaw.protocols import LLMProvider
from pyclaw.routing.resolver import RouteResolver

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry of agent instances with routing support."""

    def __init__(self, config: Config, provider: LLMProvider):
        self._agents: dict[str, AgentInstance] = {}
        self._resolver = RouteResolver(config)
        self._default_id = ""

        # Create agent instances from config
        for agent_cfg in config.agents.agents:
            instance = AgentInstance(agent_cfg, config.agents.defaults, config, provider)
            self._agents[instance.id] = instance
            if agent_cfg.default:
                self._default_id = instance.id

        # Ensure at least a default agent exists
        if not self._agents:
            from pyclaw.config.models import AgentConfig
            default_cfg = AgentConfig(id="default", default=True)
            instance = AgentInstance(default_cfg, config.agents.defaults, config, provider)
            self._agents["default"] = instance
            self._default_id = "default"

        if not self._default_id and self._agents:
            self._default_id = next(iter(self._agents))

    def get_agent(self, agent_id: str) -> AgentInstance | None:
        return self._agents.get(agent_id)

    def get_default_agent(self) -> AgentInstance:
        return self._agents[self._default_id]

    def resolve_route(self, route_input: RouteInput) -> ResolvedRoute:
        return self._resolver.resolve(route_input)

    def list_agent_ids(self) -> list[str]:
        return list(self._agents.keys())

    def can_spawn_subagent(self, parent_id: str, target_id: str) -> bool:
        parent = self._agents.get(parent_id)
        if parent is None or parent.subagents is None:
            return False
        if not parent.subagents.allow_agents:
            return True  # No restriction = allow all
        return target_id in parent.subagents.allow_agents
