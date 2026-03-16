"""Thin wrappers around alph.core — the ONLY file that imports from alph.*."""

from pathlib import Path

from alph.core import (
    AlphConfig,
    NodeDetail,
    NodeResult,
    NodeSummary,
    UpdateResult,
    create_node,
    init_pool,
    init_registry,
    list_nodes,
    load_config,
    show_node,
    update_node,
)


def alph_load_config(*, global_config_dir: Path) -> AlphConfig:
    """Load alph configuration."""
    return load_config(global_config_dir=global_config_dir)


def alph_ensure_registry(
    *,
    global_config_dir: Path,
    pools_dir: Path,
    registry_id: str,
    context: str,
) -> None:
    """Idempotently create a registry if it doesn't exist."""
    cfg = load_config(global_config_dir=global_config_dir)
    if registry_id in cfg.registries:
        return
    init_registry(
        pool_home=pools_dir,
        registry_id=registry_id,
        context=context,
        global_config_dir=global_config_dir,
    )


def alph_ensure_pool(
    *,
    pool_path: Path,
    registry_id: str,
    name: str,
    context: str,
    global_config_dir: Path,
) -> None:
    """Idempotently create a pool if it doesn't exist on disk."""
    snapshots = pool_path / "snapshots"
    live = pool_path / "live"
    if snapshots.is_dir() and live.is_dir():
        return
    init_pool(
        registry_id=registry_id,
        name=name,
        context=context,
        cwd=pool_path.parent,
        global_config_dir=global_config_dir,
    )


def alph_create_node(
    *,
    pool_path: Path,
    source: str,
    context: str,
    tags: list[str],
    meta: dict[str, object],
    content: str,
    creator: str,
) -> NodeResult:
    """Create a snapshot node with content_type=task."""
    return create_node(
        pool_path=pool_path,
        source=source,
        node_type="snapshot",
        context=context,
        creator=creator,
        content=content,
        content_type="task",
        tags=tags,
        meta=meta,
    )


def alph_list_nodes(
    pool_path: Path,
    *,
    statuses: set[str] | None = None,
) -> list[NodeSummary]:
    """List nodes in a pool, optionally filtered by status."""
    result: list[NodeSummary] = list_nodes(pool_path, include_statuses=statuses)
    return result


def alph_show_node(pool_path: Path, node_id: str) -> NodeDetail | None:
    """Return full node detail."""
    return show_node(pool_path, node_id)


def alph_set_node_status(
    *,
    pool_path: Path,
    node_id: str,
    status: str,
) -> UpdateResult:
    """Update a node's status."""
    return update_node(
        pool_path=pool_path,
        node_id=node_id,
        status=status,
    )


def alph_update_node(
    *,
    pool_path: Path,
    node_id: str,
    status: str | None = None,
    tags: list[str] | None = None,
    tags_add: list[str] | None = None,
    tags_remove: list[str] | None = None,
    meta: dict[str, object] | None = None,
    content: str | None = None,
    context: str | None = None,
    related_add: list[str] | None = None,
) -> UpdateResult:
    """Update a node's frontmatter and/or body."""
    return update_node(
        pool_path=pool_path,
        node_id=node_id,
        status=status,
        tags=tags,
        tags_add=tags_add,
        tags_remove=tags_remove,
        meta=meta,
        content=content,
        context=context,
        related_add=related_add,
    )
