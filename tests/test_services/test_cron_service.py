"""Tests for cron service."""

import time

from pytoclaw.services.cron_service import CronService


def test_add_and_list_jobs(tmp_path):
    svc = CronService(str(tmp_path))
    job = svc.add_job(
        name="test job",
        schedule={"kind": "every", "every_ms": 60000},
        message="do something",
    )
    assert job["id"]
    assert job["name"] == "test job"

    jobs = svc.list_jobs()
    assert len(jobs) == 1


def test_remove_job(tmp_path):
    svc = CronService(str(tmp_path))
    job = svc.add_job(name="rm me", schedule={"kind": "every", "every_ms": 1000}, message="x")
    assert svc.remove_job(job["id"])
    assert len(svc.list_jobs()) == 0


def test_enable_disable_job(tmp_path):
    svc = CronService(str(tmp_path))
    job = svc.add_job(name="toggle", schedule={"kind": "every", "every_ms": 1000}, message="x")

    svc.enable_job(job["id"], False)
    jobs = svc.list_jobs(include_disabled=True)
    assert not jobs[0]["enabled"]

    svc.enable_job(job["id"], True)
    jobs = svc.list_jobs()
    assert jobs[0]["enabled"]


def test_persistence(tmp_path):
    svc = CronService(str(tmp_path))
    svc.add_job(name="persist", schedule={"kind": "every", "every_ms": 1000}, message="x")

    # Reload
    svc2 = CronService(str(tmp_path))
    assert len(svc2.list_jobs()) == 1
    assert svc2.list_jobs()[0]["name"] == "persist"


def test_cron_schedule(tmp_path):
    svc = CronService(str(tmp_path))
    job = svc.add_job(
        name="cron job",
        schedule={"kind": "cron", "expr": "0 9 * * *"},
        message="morning check",
    )
    # next_run_ms should be set
    assert job["state"]["next_run_ms"] is not None
    assert job["state"]["next_run_ms"] > int(time.time() * 1000)


def test_at_schedule(tmp_path):
    svc = CronService(str(tmp_path))
    job = svc.add_job(
        name="one-time",
        schedule={"kind": "at", "at_ms": int((time.time() + 3600) * 1000)},
        message="future task",
    )
    assert job["delete_after_run"] is True
