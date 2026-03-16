"""Shared pytest fixtures for fin tests."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def isolated_pool(tmp_path: Path) -> Path:
    """Create an isolated pool directory with snapshots/ and live/."""
    pool = tmp_path / "test-pool"
    (pool / "snapshots").mkdir(parents=True)
    (pool / "live").mkdir(parents=True)
    return pool


@pytest.fixture()
def isolated_fin_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Set FIN_POOLS_DIR and FIN_CONFIG_DIR to temp directories."""
    pools_dir = tmp_path / "fin-pools"
    pools_dir.mkdir()
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_POOLS_DIR", str(pools_dir))
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("ALPH_CONFIG_DIR", str(tmp_path / "alph-config"))
    return pools_dir


@pytest.fixture()
def mock_alph_interface(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Patch alph_interface functions everywhere they're imported."""
    from fin import alph_interface, config, core

    mocks: dict[str, MagicMock] = {}
    # Map function name -> modules that import it directly
    _patches: dict[str, list[object]] = {
        "alph_load_config": [alph_interface],
        "alph_ensure_registry": [alph_interface, config],
        "alph_ensure_pool": [alph_interface, config],
        "alph_create_node": [alph_interface, core],
        "alph_list_nodes": [alph_interface, core],
        "alph_show_node": [alph_interface, core],
        "alph_set_node_status": [alph_interface, core],
        "alph_update_node": [alph_interface],
    }
    for name, modules in _patches.items():
        mock = MagicMock()
        mocks[name] = mock
        for mod in modules:
            if hasattr(mod, name):
                monkeypatch.setattr(mod, name, mock)
    return mocks


def _write_node(
    pool_path: Path,
    node_id: str,
    *,
    context: str = "test task",
    status: str = "active",
    source: str = "fin",
    creator: str = "test@test.com",
    tags: list[str] | None = None,
    meta: dict[str, Any] | None = None,
    content: str = "",
) -> Path:
    """Write a node file to a pool for testing."""
    import yaml

    frontmatter: dict[str, object] = {
        "schema_version": "1",
        "id": node_id,
        "timestamp": "2026-03-13T00:00:00+00:00",
        "source": source,
        "node_type": "snapshot",
        "context": context,
        "creator": creator,
        "content_type": "task",
        "status": status,
    }
    if tags:
        frontmatter["tags"] = tags
    if meta:
        frontmatter["meta"] = meta

    fm_text = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    body = f"---\n{fm_text}---\n"
    if content:
        body += f"\n{content}\n"

    path = pool_path / "snapshots" / f"{node_id}.md"
    path.write_text(body)
    return path
