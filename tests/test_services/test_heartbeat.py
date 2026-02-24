"""Tests for heartbeat service."""

from pathlib import Path

from pyclaw.services.heartbeat import HeartbeatService


def test_creates_default_heartbeat_file(tmp_path):
    svc = HeartbeatService(workspace=str(tmp_path), enabled=True)
    svc._ensure_heartbeat_file()
    assert (tmp_path / "HEARTBEAT.md").exists()


def test_disabled_by_default(tmp_path):
    svc = HeartbeatService(workspace=str(tmp_path))
    assert not svc.is_running()


def test_minimum_interval(tmp_path):
    svc = HeartbeatService(workspace=str(tmp_path), interval_minutes=1)
    # Should enforce minimum of 5 minutes = 300 seconds
    assert svc._interval == 300
