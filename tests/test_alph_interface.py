"""Tests for the alph interface layer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from alph.core import (
    AlphConfig,
    NodeDetail,
    NodeResult,
    NodeSummary,
    PoolResult,
    RegistryResult,
    UpdateResult,
)

from fin.alph_interface import (
    alph_create_node,
    alph_ensure_pool,
    alph_ensure_registry,
    alph_list_nodes,
    alph_load_config,
    alph_set_node_status,
    alph_show_node,
)


@patch("fin.alph_interface.load_config")
def test_alph_load_config_delegates(mock_load: MagicMock) -> None:
    expected = AlphConfig(creator="test@test.com")
    mock_load.return_value = expected
    result = alph_load_config(global_config_dir=Path("/tmp/cfg"))
    mock_load.assert_called_once_with(global_config_dir=Path("/tmp/cfg"))
    assert result == expected


@patch("fin.alph_interface.load_config")
@patch("fin.alph_interface.init_registry")
def test_alph_ensure_registry_creates(
    mock_init: MagicMock, mock_load: MagicMock
) -> None:
    mock_load.return_value = AlphConfig()
    mock_init.return_value = RegistryResult(
        config_path=Path("/tmp/cfg/config.yaml"), valid=True, set_as_default=True
    )
    alph_ensure_registry(
        global_config_dir=Path("/tmp/cfg"),
        pools_dir=Path("/tmp/pools"),
        registry_id="tasks",
        context="fin task registry",
    )
    mock_init.assert_called_once()
    call_kwargs = mock_init.call_args.kwargs
    assert call_kwargs["registry_id"] == "tasks"
    assert call_kwargs["pool_home"] == Path("/tmp/pools")


@patch("fin.alph_interface.load_config")
@patch("fin.alph_interface.init_registry")
def test_alph_ensure_registry_skips_existing(
    mock_init: MagicMock, mock_load: MagicMock
) -> None:
    from alph.core import RegistryEntry

    mock_load.return_value = AlphConfig(
        registries={"tasks": RegistryEntry(pool_home="/tmp/pools")}
    )
    alph_ensure_registry(
        global_config_dir=Path("/tmp/cfg"),
        pools_dir=Path("/tmp/pools"),
        registry_id="tasks",
        context="fin task registry",
    )
    mock_init.assert_not_called()


@patch("fin.alph_interface.load_config")
@patch("fin.alph_interface.init_pool")
def test_alph_ensure_pool_creates(
    mock_init_pool: MagicMock, mock_load: MagicMock
) -> None:
    mock_load.return_value = AlphConfig()
    mock_init_pool.return_value = PoolResult(
        pool_path=Path("/tmp/pools/default"), valid=True
    )
    alph_ensure_pool(
        pool_path=Path("/tmp/pools/default"),
        registry_id="tasks",
        name="default",
        context="default context",
        global_config_dir=Path("/tmp/cfg"),
    )
    mock_init_pool.assert_called_once()


@patch("fin.alph_interface.load_config")
@patch("fin.alph_interface.init_pool")
def test_alph_ensure_pool_skips_existing(
    mock_init_pool: MagicMock, mock_load: MagicMock, tmp_path: Path
) -> None:
    pool_path = tmp_path / "existing-pool"
    (pool_path / "snapshots").mkdir(parents=True)
    (pool_path / "live").mkdir(parents=True)
    mock_load.return_value = AlphConfig()

    alph_ensure_pool(
        pool_path=pool_path,
        registry_id="tasks",
        name="default",
        context="default context",
        global_config_dir=Path("/tmp/cfg"),
    )
    mock_init_pool.assert_not_called()


@patch("fin.alph_interface.create_node")
def test_alph_create_node_delegates(mock_create: MagicMock) -> None:
    expected = NodeResult(node_id="abc123def456", path=Path("/tmp/node.md"))
    mock_create.return_value = expected
    result = alph_create_node(
        pool_path=Path("/tmp/pool"),
        source="fin",
        context="write report",
        tags=["work"],
        meta={"due": "2026-04-01"},
        content="write the quarterly report",
        creator="test@test.com",
    )
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["node_type"] == "snapshot"
    assert call_kwargs["content_type"] == "task"
    assert call_kwargs["source"] == "fin"
    assert result == expected


@patch("fin.alph_interface.list_nodes")
def test_alph_list_nodes_delegates(mock_list: MagicMock) -> None:
    expected = [
        NodeSummary(
            node_id="abc123def456",
            context="test",
            node_type="snapshot",
            timestamp="2026-03-13T00:00:00+00:00",
            source="fin",
        )
    ]
    mock_list.return_value = expected
    result = alph_list_nodes(Path("/tmp/pool"))
    mock_list.assert_called_once_with(Path("/tmp/pool"), include_statuses=None)
    assert result == expected


@patch("fin.alph_interface.list_nodes")
def test_alph_list_nodes_with_statuses(mock_list: MagicMock) -> None:
    mock_list.return_value = []
    alph_list_nodes(Path("/tmp/pool"), statuses={"active", "archived"})
    mock_list.assert_called_once_with(
        Path("/tmp/pool"), include_statuses={"active", "archived"}
    )


@patch("fin.alph_interface.show_node")
def test_alph_show_node_delegates(mock_show: MagicMock) -> None:
    expected = NodeDetail(
        node_id="abc123def456",
        context="test",
        node_type="snapshot",
        timestamp="2026-03-13T00:00:00+00:00",
        source="fin",
        creator="test@test.com",
        body="",
    )
    mock_show.return_value = expected
    result = alph_show_node(Path("/tmp/pool"), "abc123def456")
    mock_show.assert_called_once_with(Path("/tmp/pool"), "abc123def456")
    assert result == expected


@patch("fin.alph_interface.update_node")
def test_alph_set_node_status_delegates(mock_update: MagicMock) -> None:
    expected = UpdateResult(node_id="abc123def456", path=Path("/tmp/node.md"))
    mock_update.return_value = expected
    result = alph_set_node_status(
        pool_path=Path("/tmp/pool"),
        node_id="abc123def456",
        status="archived",
    )
    mock_update.assert_called_once_with(
        pool_path=Path("/tmp/pool"),
        node_id="abc123def456",
        status="archived",
    )
    assert result == expected
