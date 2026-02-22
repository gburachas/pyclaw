"""Tests for route resolver."""

from pytoclaw.config.models import AgentBinding, BindingMatch, Config, PeerMatch
from pytoclaw.models import RouteInput, RoutePeer
from pytoclaw.routing.resolver import RouteResolver


def test_default_route():
    cfg = Config()
    resolver = RouteResolver(cfg)
    route = resolver.resolve(RouteInput(channel="test", account_id="user1"))
    assert route.matched_by == "default"
    assert route.agent_id == "default"


def test_channel_binding():
    cfg = Config(bindings=[
        AgentBinding(
            agent_id="agent1",
            match=BindingMatch(channel="telegram"),
        ),
    ])
    resolver = RouteResolver(cfg)
    route = resolver.resolve(RouteInput(channel="telegram", account_id="user1"))
    assert route.agent_id == "agent1"
    assert route.matched_by == "channel"


def test_peer_binding():
    cfg = Config(bindings=[
        AgentBinding(
            agent_id="agent2",
            match=BindingMatch(
                channel="discord",
                peer=PeerMatch(kind="direct", id="user42"),
            ),
        ),
    ])
    resolver = RouteResolver(cfg)
    route = resolver.resolve(RouteInput(
        channel="discord",
        account_id="user42",
        peer=RoutePeer(kind="direct", id="user42"),
    ))
    assert route.agent_id == "agent2"
    assert route.matched_by == "peer"
