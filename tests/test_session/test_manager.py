"""Tests for session manager."""

from pyclaw.session.manager import SessionManager


def test_get_or_create(tmp_path):
    sm = SessionManager(str(tmp_path))
    session = sm.get_or_create("test")
    assert session.key == "test"
    assert session.messages == []


def test_add_and_get_history(tmp_path):
    sm = SessionManager(str(tmp_path))
    sm.add_message("test", "user", "hello")
    sm.add_message("test", "assistant", "hi there")
    history = sm.get_history("test")
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].content == "hi there"


def test_save_and_reload(tmp_path):
    sm = SessionManager(str(tmp_path))
    sm.add_message("test", "user", "hello")
    sm.set_summary("test", "User said hello")
    sm.save("test")

    # Reload
    sm2 = SessionManager(str(tmp_path))
    history = sm2.get_history("test")
    assert len(history) == 1
    assert sm2.get_summary("test") == "User said hello"


def test_truncate_history(tmp_path):
    sm = SessionManager(str(tmp_path))
    for i in range(10):
        sm.add_message("test", "user", f"msg {i}")
    sm.truncate_history("test", 3)
    assert len(sm.get_history("test")) == 3


def test_clear(tmp_path):
    sm = SessionManager(str(tmp_path))
    sm.add_message("test", "user", "hello")
    sm.set_summary("test", "summary")
    sm.clear("test")
    assert sm.get_history("test") == []
    assert sm.get_summary("test") == ""
