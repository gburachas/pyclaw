"""Route resolver — determines which agent handles a message."""

from __future__ import annotations

import logging

from pytoclaw.config.models import Config
from pytoclaw.models import ResolvedRoute, RouteInput

logger = logging.getLogger(__name__)


class RouteResolver:
    """Resolves message routing to agent instances using binding rules."""

    def __init__(self, config: Config):
        self._config = config

    def resolve(self, route_input: RouteInput) -> ResolvedRoute:
        """Resolve which agent should handle a message.

        Priority cascade:
        1. Peer match (direct/group/channel)
        2. Guild ID match
        3. Team ID match
        4. Account ID match
        5. Channel wildcard match
        6. Default agent
        """
        for binding in self._config.bindings:
            match = binding.match

            # Peer-level match
            if match.peer and route_input.peer:
                if (
                    match.peer.kind == route_input.peer.kind
                    and match.peer.id == route_input.peer.id
                    and (not match.channel or match.channel == route_input.channel)
                ):
                    return self._build_route(binding.agent_id, route_input, "peer")

            # Guild match
            if match.guild_id and match.guild_id == route_input.guild_id:
                return self._build_route(binding.agent_id, route_input, "guild")

            # Team match
            if match.team_id and match.team_id == route_input.team_id:
                return self._build_route(binding.agent_id, route_input, "team")

            # Account match
            if match.account_id and match.account_id == route_input.account_id:
                return self._build_route(binding.agent_id, route_input, "account")

            # Channel wildcard
            if match.channel and match.channel == route_input.channel and not match.peer and not match.account_id:
                return self._build_route(binding.agent_id, route_input, "channel")

        # Default
        return self._build_route("", route_input, "default")

    @staticmethod
    def _build_route(agent_id: str, route_input: RouteInput, matched_by: str) -> ResolvedRoute:
        session_key = f"agent:{agent_id or 'default'}:{route_input.channel}:{route_input.account_id}"
        return ResolvedRoute(
            agent_id=agent_id or "default",
            channel=route_input.channel,
            account_id=route_input.account_id,
            session_key=session_key,
            main_session_key=f"agent:{agent_id or 'default'}:main",
            matched_by=matched_by,
        )
