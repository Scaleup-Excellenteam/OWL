"""Tests for the CLI's opt-in zero-downtime snapshot bootstrap."""

from pathlib import Path

from main import resolve_snapshots_root


def test_resolve_snapshots_root_is_none_when_env_var_is_unset(monkeypatch):
    monkeypatch.delenv("OWL_SNAPSHOTS_DIR", raising=False)
    assert resolve_snapshots_root() is None


def test_resolve_snapshots_root_reads_the_env_var(monkeypatch):
    monkeypatch.setenv("OWL_SNAPSHOTS_DIR", "/tmp/owl-snapshots")
    assert resolve_snapshots_root() == Path("/tmp/owl-snapshots")
