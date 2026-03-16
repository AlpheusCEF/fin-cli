"""Thin Typer wrapper exposing core.py as the `fin` CLI."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from fin.alph_interface import alph_set_node_status, alph_show_node
from fin.config import (
    clear_default_pool,
    ensure_fin_pool,
    ensure_tasks_registry,
    get_pool_path,
    list_pools,
    load_fin_config,
    resolve_global_config_dir,
    resolve_pools_dir,
    set_config_value,
    set_default_pool,
)
from fin.core import (
    AmbiguousIDError,
    FinTask,
    UnknownIDError,
    add_completed_task,
    add_task,
    apply_edit_actions,
    close_task,
    filter_by_tags,
    format_short_id,
    get_blocked_tasks,
    list_tasks,
    resolve_short_id,
)
from fin.display import render_task_detail, render_task_list
from fin.editor import (
    diff_edit_actions,
    parse_edit_doc,
    render_edit_doc,
    serialize_to_edit_doc,
)

_help_settings = {"help_option_names": ["-h", "--help"]}
app = typer.Typer(
    name="fin",
    help="Daily task CLI built on AlpheusCEF.",
    invoke_without_command=True,
    context_settings=_help_settings,
)
fins_app = typer.Typer(
    name="fins",
    help="Completed task view and logging.",
    invoke_without_command=True,
    context_settings=_help_settings,
)
fine_app = typer.Typer(
    name="fine",
    help="Bulk task editor. Opens tasks in your editor for quick review and editing.",
    invoke_without_command=True,
    context_settings=_help_settings,
)
pool_app = typer.Typer(
    name="pool",
    help="Pool management commands.",
    context_settings=_help_settings,
)
config_app = typer.Typer(
    name="config",
    help="Configuration management.",
    invoke_without_command=True,
    context_settings=_help_settings,
)
app.add_typer(pool_app, name="pool")
app.add_typer(config_app, name="config")
console = Console()


def _pools_dir() -> Path:
    return resolve_pools_dir()


def _config_dir() -> Path:
    return resolve_global_config_dir()


# --- fin app ---


@app.callback()
def main(
    ctx: typer.Context,
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
    days: Annotated[int | None, typer.Option("-d", "--days", help="Show tasks from the last N days.")] = None,
    tags: Annotated[str | None, typer.Option("-t", "--tags", help="Filter by tag expression.")] = None,
    status: Annotated[str | None, typer.Option("-s", "--status", help="Comma-separated statuses: open,done,dismissed")] = None,
) -> None:
    """fin -- daily task CLI.

    With no subcommand, lists open tasks. Use 'fin add' to create tasks.
    """
    if ctx.invoked_subcommand is not None:
        return

    _do_list(pool=pool, days=days, tags=tags, status=status)


def _resolve_statuses(status_str: str | None) -> set[str] | None:
    """Map user-friendly status names to alph statuses."""
    if status_str is None:
        return None
    mapping = {
        "open": "active",
        "done": "archived",
        "completed": "archived",
        "dismissed": "suppressed",
        "active": "active",
        "archived": "archived",
        "suppressed": "suppressed",
    }
    return {mapping.get(s.strip(), s.strip()) for s in status_str.split(",")}


def _do_add(content: str, *, pool: str | None = None) -> None:
    result = add_task(
        content,
        pool=pool,
        pools_dir=_pools_dir(),
        global_config_dir=_config_dir(),
    )
    if result.duplicate:
        console.print(f"Task already exists: {format_short_id(result.node_id)}")
    else:
        console.print(f"Added: {format_short_id(result.node_id)}")


def _do_list(
    *,
    pool: str | None = None,
    days: int | None = None,
    tags: str | None = None,
    status: str | None = None,
    show_done: bool = False,
) -> None:
    statuses = _resolve_statuses(status)
    if show_done and statuses is None:
        statuses = {"archived"}
    tasks = list_tasks(
        pool=pool,
        pools_dir=_pools_dir(),
        global_config_dir=_config_dir(),
        statuses=statuses,
        days=days,
    )
    if tags:
        tasks = filter_by_tags(tasks, tags)

    # Compute blocked tasks for display
    all_tasks = list_tasks(
        pool=pool,
        pools_dir=_pools_dir(),
        global_config_dir=_config_dir(),
        statuses={"active"},
    ) if tasks else []
    blocked = get_blocked_tasks(tasks, all_tasks) if all_tasks else set()

    output = render_task_list(tasks, blocked=blocked)
    console.print(output)


@app.command()
def add(
    content: Annotated[str, typer.Argument(help="Task content.")],
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
) -> None:
    """Add a new task."""
    _do_add(content, pool=pool)


@app.command(name="list")
def list_cmd(
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
    days: Annotated[int | None, typer.Option("-d", "--days", help="Show tasks from the last N days.")] = None,
    tags: Annotated[str | None, typer.Option("-t", "--tags", help="Filter by tag expression.")] = None,
    status: Annotated[str | None, typer.Option("-s", "--status", help="Comma-separated statuses.")] = None,
) -> None:
    """List open tasks."""
    _do_list(pool=pool, days=days, tags=tags, status=status)


@app.command()
def done(
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
    days: Annotated[int | None, typer.Option("-d", "--days", help="Show tasks from the last N days.")] = None,
    tags: Annotated[str | None, typer.Option("-t", "--tags", help="Filter by tag expression.")] = None,
) -> None:
    """List completed tasks."""
    _do_list(pool=pool, days=days, tags=tags, show_done=True)


@app.command()
def show(
    task_id: Annotated[str, typer.Argument(help="Task ID or prefix.")],
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
) -> None:
    """Show full task detail."""
    cfg = load_fin_config()
    resolved_pool = pool or cfg.default_pool
    pool_path = get_pool_path(resolved_pool, _pools_dir())

    try:
        full_id = resolve_short_id(task_id, pool_path)
    except (AmbiguousIDError, UnknownIDError) as e:
        console.print(f"Error: {e}")
        raise typer.Exit(code=1) from e

    detail = alph_show_node(pool_path, full_id)
    if detail is None:
        console.print(f"Error: task {task_id} not found")
        raise typer.Exit(code=1)

    task = FinTask(
        node_id=detail.node_id,
        context=detail.context,
        timestamp=detail.timestamp,
        status="active",
        tags=detail.tags,
        meta=detail.meta,
        body=detail.body,
    )
    console.print(render_task_detail(task))


def _do_edit(*, pool: str | None = None, fmt: str = "yaml") -> None:
    """Shared edit logic for fin edit and fine."""
    cfg = load_fin_config()
    resolved_pool = pool or cfg.default_pool

    tasks = list_tasks(
        pool=resolved_pool,
        pools_dir=_pools_dir(),
        global_config_dir=_config_dir(),
    )

    editables = serialize_to_edit_doc(tasks)
    doc_text = render_edit_doc(editables, fmt=fmt)

    editor_cmd = cfg.editor or os.environ.get("EDITOR", "vi")

    suffix = ".yaml" if fmt == "yaml" else ".txt"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, prefix="fin-edit-", delete=False
    ) as tmp:
        tmp.write(doc_text)
        tmp_path = tmp.name

    try:
        subprocess.run([editor_cmd, tmp_path], check=True)
        edited_text = Path(tmp_path).read_text()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    edited_tasks = parse_edit_doc(edited_text, fmt=fmt)
    actions = diff_edit_actions(editables, edited_tasks)

    if not actions:
        console.print("No changes.")
        return

    pool_path = get_pool_path(resolved_pool, _pools_dir())
    applied = apply_edit_actions(
        actions=actions,
        pool_path=pool_path,
        pool=resolved_pool,
        pools_dir=_pools_dir(),
        global_config_dir=_config_dir(),
    )
    console.print(f"Applied {applied} change{'s' if applied != 1 else ''}.")


@app.command()
def edit(
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
    fmt: Annotated[str, typer.Option("--format", help="Editor format: compact or yaml.")] = "yaml",
) -> None:
    """Open tasks in editor for bulk editing."""
    _do_edit(pool=pool, fmt=fmt)


@app.command(name="tags")
def list_tags_cmd(
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
) -> None:
    """List all tags in use."""
    tasks = list_tasks(
        pool=pool,
        pools_dir=_pools_dir(),
        global_config_dir=_config_dir(),
        statuses={"active", "archived", "suppressed"},
    )
    all_tags: set[str] = set()
    for task in tasks:
        all_tags.update(task.tags)
    if not all_tags:
        console.print("No tags in use.")
        return
    for tag in sorted(all_tags):
        console.print(f"  #{tag}")


def _change_status(task_id: str, status: str, *, pool: str | None = None, label: str = "") -> None:
    cfg = load_fin_config()
    resolved_pool = pool or cfg.default_pool
    pool_path = get_pool_path(resolved_pool, _pools_dir())

    try:
        full_id = resolve_short_id(task_id, pool_path)
    except (AmbiguousIDError, UnknownIDError) as e:
        console.print(f"Error: {e}")
        raise typer.Exit(code=1) from e

    result = alph_set_node_status(
        pool_path=pool_path,
        node_id=full_id,
        status=status,
    )
    if not result.valid:
        console.print(f"Error: {'; '.join(result.errors)}")
        raise typer.Exit(code=1)
    console.print(f"{label}: {format_short_id(full_id)}")


@app.command()
def close(
    task_id: Annotated[str, typer.Argument(help="Task ID or prefix.")],
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
) -> None:
    """Close (archive) a task. Spawns next instance for recurring tasks."""
    cfg = load_fin_config()
    resolved_pool = pool or cfg.default_pool

    full_id = close_task(
        task_id,
        pool=resolved_pool,
        pools_dir=_pools_dir(),
        global_config_dir=_config_dir(),
    )
    console.print(f"Closed: {format_short_id(full_id)}")


@app.command()
def dismiss(
    task_id: Annotated[str, typer.Argument(help="Task ID or prefix.")],
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
) -> None:
    """Dismiss (suppress) a task."""
    _change_status(task_id, "suppressed", pool=pool, label="Dismissed")


@app.command(name="open")
def reopen(
    task_id: Annotated[str, typer.Argument(help="Task ID or prefix.")],
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
) -> None:
    """Reopen a task."""
    _change_status(task_id, "active", pool=pool, label="Reopened")


# --- fins app ---


@fins_app.callback()
def fins_main(
    ctx: typer.Context,
    content: Annotated[str | None, typer.Argument(help="Log a completed task.")] = None,
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
    days: Annotated[int | None, typer.Option("-d", "--days", help="Show tasks from the last N days.")] = None,
    tags: Annotated[str | None, typer.Option("-t", "--tags", help="Filter by tag expression.")] = None,
) -> None:
    """fins -- completed task view and logging.

    With no args, lists completed tasks. With a positional arg, logs a completed task.
    """
    if ctx.invoked_subcommand is not None:
        return

    if content is not None:
        result = add_completed_task(
            content,
            pool=pool,
            pools_dir=_pools_dir(),
            global_config_dir=_config_dir(),
        )
        console.print(f"Logged: {format_short_id(result.node_id)}")
    else:
        cfg = load_fin_config()
        effective_days = days if days is not None else cfg.default_done_days
        _do_list(
            pool=pool,
            days=effective_days,
            tags=tags,
            show_done=True,
        )


# --- fine app ---


@fine_app.callback()
def fine_main(
    ctx: typer.Context,
    pool: Annotated[str | None, typer.Option("-p", "--pool", help="Task pool.")] = None,
    fmt: Annotated[str, typer.Option("--format", help="Editor format: compact or yaml.")] = "yaml",
) -> None:
    """fine -- bulk task editor.

    Opens tasks in your editor for quick review and editing.
    """
    if ctx.invoked_subcommand is not None:
        return
    _do_edit(pool=pool, fmt=fmt)


# --- pool commands ---


@pool_app.command(name="list")
def pool_list() -> None:
    """List all pools."""
    pools = list_pools(_pools_dir())
    if not pools:
        console.print("No pools.")
        return
    cfg = load_fin_config()
    for pool_name in pools:
        marker = " *" if pool_name == cfg.default_pool else ""
        console.print(f"  {pool_name}{marker}")


@pool_app.command(name="set")
def pool_set(
    name: Annotated[str, typer.Argument(help="Pool name to set as default.")],
) -> None:
    """Set the default pool."""
    ensure_tasks_registry(
        global_config_dir=_config_dir(), pools_dir=_pools_dir()
    )
    ensure_fin_pool(
        pool_name=name,
        pools_dir=_pools_dir(),
        global_config_dir=_config_dir(),
    )
    set_default_pool(name)
    console.print(f"Default pool: {name}")


@pool_app.command(name="clear")
def pool_clear() -> None:
    """Reset default pool to 'default'."""
    clear_default_pool()
    console.print("Default pool: default")


@pool_app.command(name="show")
def pool_show() -> None:
    """Show current default pool."""
    cfg = load_fin_config()
    console.print(f"Default pool: {cfg.default_pool}")


# --- config commands ---


@config_app.callback()
def config_main(ctx: typer.Context) -> None:
    """View or modify fin configuration."""
    if ctx.invoked_subcommand is not None:
        return
    cfg = load_fin_config()
    console.print(f"default_pool: {cfg.default_pool}")
    console.print(f"editor: {cfg.editor or '(system default)'}")
    console.print(f"date_format: {cfg.date_format}")
    console.print(f"wrap_width: {cfg.wrap_width}")
    console.print(f"default_days: {cfg.default_days}")
    console.print(f"default_done_days: {cfg.default_done_days}")
    console.print(f"show_sections: {cfg.show_sections}")
    console.print(f"weekdays_only_lookback: {cfg.weekdays_only_lookback}")
    console.print(f"auto_today_for_important: {cfg.auto_today_for_important}")


@config_app.command(name="set")
def config_set(
    key: Annotated[str, typer.Argument(help="Config key.")],
    value: Annotated[str, typer.Argument(help="Config value.")],
) -> None:
    """Set a config value."""
    try:
        set_config_value(key, value)
        console.print(f"Set {key} = {value}")
    except ValueError as e:
        console.print(f"Error: {e}")
        raise typer.Exit(code=1) from e


@config_app.command(name="show")
def config_show(
    key: Annotated[str, typer.Argument(help="Config key.")],
) -> None:
    """Show a config value."""
    cfg = load_fin_config()
    val = getattr(cfg, key, None)
    if val is None:
        console.print(f"Error: unknown key '{key}'")
        raise typer.Exit(code=1)
    console.print(f"{key}: {val}")
