"""Tests for fin CLI entry points."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from alph.core import NodeDetail, NodeResult, UpdateResult
from typer.testing import CliRunner

from fin.cli import app, fins_app
from fin.core import FinTask

runner = CliRunner()


# --- Helpers ---


def _stub_dirs(
    mock_pools_dir: MagicMock, mock_config_dir: MagicMock
) -> None:
    mock_pools_dir.return_value = Path("/tmp/pools")
    mock_config_dir.return_value = Path("/tmp/cfg")


def _make_fin_task(
    *,
    node_id: str = "abc123def456",
    context: str = "test task",
    status: str = "active",
    tags: list[str] | None = None,
    meta: dict[str, object] | None = None,
    body: str = "",
) -> FinTask:
    return FinTask(
        node_id=node_id,
        context=context,
        timestamp="2026-03-13T00:00:00+00:00",
        status=status,
        tags=tags or [],
        meta=meta or {},
        body=body,
    )


# --- add ---


@patch("fin.cli.add_task")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_add_subcommand(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_add: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_add.return_value = NodeResult(
        node_id="abc123def456", path=Path("/tmp/node.md")
    )
    result = runner.invoke(app, ["add", "write the report"])
    assert result.exit_code == 0
    assert "abc123" in result.output


@patch("fin.cli.add_task")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_add_with_pool(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_add: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_add.return_value = NodeResult(
        node_id="abc123def456", path=Path("/tmp/node.md")
    )
    result = runner.invoke(app, ["add", "-p", "work", "write the report"])
    assert result.exit_code == 0
    mock_add.assert_called_once()
    assert mock_add.call_args.kwargs.get("pool") == "work"


@patch("fin.cli.add_task")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_add_duplicate(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_add: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_add.return_value = NodeResult(
        node_id="abc123def456",
        path=Path("/tmp/node.md"),
        duplicate=True,
        existing_creator="test@test.com",
    )
    result = runner.invoke(app, ["add", "duplicate task"])
    assert result.exit_code == 0
    assert "already exists" in result.output.lower()


# --- list ---


@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_list_no_args(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "no open tasks" in result.output.lower()


@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_list_subcommand(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0


@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_list_with_days(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    result = runner.invoke(app, ["list", "-d", "7"])
    assert result.exit_code == 0
    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs.get("days") == 7


@patch("fin.cli.filter_by_tags")
@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_list_with_tags(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
    mock_filter: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = [_make_fin_task(tags=["work"])]
    mock_filter.return_value = [_make_fin_task(tags=["work"])]
    result = runner.invoke(app, ["list", "-t", "work"])
    assert result.exit_code == 0
    mock_filter.assert_called_once()


@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_list_with_status_filter(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    result = runner.invoke(app, ["list", "-s", "done"])
    assert result.exit_code == 0
    # Should have mapped "done" to "archived"
    call_kwargs = mock_list.call_args.kwargs
    assert "archived" in call_kwargs.get("statuses", set())


# --- close ---


@patch("fin.cli.close_task")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_close_command(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_close: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_close.return_value = "abc123def456"
    result = runner.invoke(app, ["close", "abc123"])
    assert result.exit_code == 0
    assert "closed" in result.output.lower()
    assert "abc123" in result.output


# --- dismiss ---


@patch("fin.cli.alph_set_node_status")
@patch("fin.cli.resolve_short_id")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_dismiss_command(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_resolve: MagicMock,
    mock_status: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_resolve.return_value = "abc123def456"
    mock_status.return_value = UpdateResult(
        node_id="abc123def456", path=Path("/tmp/node.md")
    )
    result = runner.invoke(app, ["dismiss", "abc123"])
    assert result.exit_code == 0
    assert "dismissed" in result.output.lower()
    mock_status.assert_called_once()
    assert mock_status.call_args.kwargs["status"] == "suppressed"


# --- open (reopen) ---


@patch("fin.cli.alph_set_node_status")
@patch("fin.cli.resolve_short_id")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_open_command(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_resolve: MagicMock,
    mock_status: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_resolve.return_value = "abc123def456"
    mock_status.return_value = UpdateResult(
        node_id="abc123def456", path=Path("/tmp/node.md")
    )
    result = runner.invoke(app, ["open", "abc123"])
    assert result.exit_code == 0
    assert "reopened" in result.output.lower()
    mock_status.assert_called_once()
    assert mock_status.call_args.kwargs["status"] == "active"


# --- show ---


@patch("fin.cli.alph_show_node")
@patch("fin.cli.resolve_short_id")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_show_command(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_resolve: MagicMock,
    mock_show: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_resolve.return_value = "abc123def456"
    mock_show.return_value = NodeDetail(
        node_id="abc123def456",
        context="write report",
        node_type="snapshot",
        timestamp="2026-03-13T00:00:00+00:00",
        source="fin",
        creator="test@test.com",
        body="detailed notes",
        tags=["work"],
        meta={},
    )
    result = runner.invoke(app, ["show", "abc123"])
    assert result.exit_code == 0
    assert "write report" in result.output
    assert "abc123" in result.output


@patch("fin.cli.alph_show_node")
@patch("fin.cli.resolve_short_id")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_show_not_found(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_resolve: MagicMock,
    mock_show: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_resolve.return_value = "abc123def456"
    mock_show.return_value = None
    result = runner.invoke(app, ["show", "abc123"])
    assert result.exit_code == 1


@patch("fin.cli.resolve_short_id")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_show_ambiguous_id(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_resolve: MagicMock,
) -> None:
    from fin.core import AmbiguousIDError

    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_resolve.side_effect = AmbiguousIDError("abc", ["abc111", "abc222"])
    result = runner.invoke(app, ["show", "abc"])
    assert result.exit_code == 1
    assert "error" in result.output.lower()


# --- done ---


@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_done_lists_archived(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    result = runner.invoke(app, ["done"])
    assert result.exit_code == 0
    # Verify it requested archived status
    call_kwargs = mock_list.call_args.kwargs
    assert "archived" in call_kwargs.get("statuses", set())


# --- tags ---


@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_tags_command(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = [
        _make_fin_task(tags=["work", "urgent"]),
        _make_fin_task(node_id="def456abc123", tags=["work", "review"]),
    ]
    result = runner.invoke(app, ["tags"])
    assert result.exit_code == 0
    assert "#work" in result.output
    assert "#urgent" in result.output
    assert "#review" in result.output


@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_tags_command_empty(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    result = runner.invoke(app, ["tags"])
    assert result.exit_code == 0
    assert "no tags" in result.output.lower()


# --- pool commands ---


@patch("fin.cli.list_pools")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_pool_list(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list_pools: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list_pools.return_value = ["default", "work"]
    result = runner.invoke(app, ["pool", "list"])
    assert result.exit_code == 0
    assert "default" in result.output
    assert "work" in result.output


@patch("fin.cli.list_pools")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_pool_list_empty(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list_pools: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list_pools.return_value = []
    result = runner.invoke(app, ["pool", "list"])
    assert result.exit_code == 0
    assert "no pools" in result.output.lower()


@patch("fin.cli.set_default_pool")
@patch("fin.cli.ensure_fin_pool")
@patch("fin.cli.ensure_tasks_registry")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_pool_set(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_ensure_reg: MagicMock,
    mock_ensure_pool: MagicMock,
    mock_set: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    result = runner.invoke(app, ["pool", "set", "work"])
    assert result.exit_code == 0
    assert "work" in result.output
    mock_set.assert_called_once_with("work")


@patch("fin.cli.clear_default_pool")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_pool_clear(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_clear: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    result = runner.invoke(app, ["pool", "clear"])
    assert result.exit_code == 0
    assert "default" in result.output


@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_pool_show(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    result = runner.invoke(app, ["pool", "show"])
    assert result.exit_code == 0
    assert "default" in result.output.lower()


# --- config commands ---


@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_config_no_subcommand_shows_all(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "default_pool" in result.output
    assert "wrap_width" in result.output


@patch("fin.cli.set_config_value")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_config_set(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_set: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    result = runner.invoke(app, ["config", "set", "wrap_width", "120"])
    assert result.exit_code == 0
    assert "120" in result.output
    mock_set.assert_called_once_with("wrap_width", "120")


@patch("fin.cli.set_config_value")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_config_set_unknown_key(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_set: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_set.side_effect = ValueError("Unknown config key: bad_key")
    result = runner.invoke(app, ["config", "set", "bad_key", "value"])
    assert result.exit_code == 1
    assert "error" in result.output.lower()


@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_config_show(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    result = runner.invoke(app, ["config", "show", "default_pool"])
    assert result.exit_code == 0
    assert "default_pool" in result.output


@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_config_show_unknown_key(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    result = runner.invoke(app, ["config", "show", "nonexistent_key"])
    assert result.exit_code == 1


# --- fins app ---


@patch("fin.cli.add_completed_task")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_fins_logs_completed_task(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_add: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_add.return_value = NodeResult(
        node_id="abc123def456", path=Path("/tmp/node.md")
    )
    result = runner.invoke(fins_app, ["did the thing"])
    assert result.exit_code == 0
    assert "logged" in result.output.lower()
    assert "abc123" in result.output


@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_fins_no_args_lists_done(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    result = runner.invoke(fins_app, [])
    assert result.exit_code == 0
    # Should request archived tasks
    call_kwargs = mock_list.call_args.kwargs
    assert "archived" in call_kwargs.get("statuses", set())


# --- status resolution ---


def test_resolve_statuses_maps_friendly_names() -> None:
    from fin.cli import _resolve_statuses

    assert _resolve_statuses("open") == {"active"}
    assert _resolve_statuses("done") == {"archived"}
    assert _resolve_statuses("dismissed") == {"suppressed"}
    assert _resolve_statuses("open,done") == {"active", "archived"}
    assert _resolve_statuses(None) is None


# --- error handling ---


@patch("fin.cli.resolve_short_id")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_dismiss_unknown_id_errors(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_resolve: MagicMock,
) -> None:
    from fin.core import UnknownIDError

    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_resolve.side_effect = UnknownIDError("zzz999")
    result = runner.invoke(app, ["dismiss", "zzz999"])
    assert result.exit_code == 1
    assert "error" in result.output.lower()


@patch("fin.cli.alph_set_node_status")
@patch("fin.cli.resolve_short_id")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_status_change_validation_error(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_resolve: MagicMock,
    mock_status: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_resolve.return_value = "abc123def456"
    mock_status.return_value = UpdateResult(
        node_id="abc123def456",
        path=Path("/tmp/node.md"),
        valid=False,
        errors=["Invalid status transition"],
    )
    result = runner.invoke(app, ["dismiss", "abc123"])
    assert result.exit_code == 1
    assert "error" in result.output.lower()


# --- edit command ---


def _editor_that_closes_task(tmp_path_str: str) -> None:
    """Simulate editor: change [ ] to [x] in the temp file."""
    text = Path(tmp_path_str).read_text()
    text = text.replace("status: active", "status: archived")
    Path(tmp_path_str).write_text(text)


@patch("fin.cli.apply_edit_actions")
@patch("fin.cli.subprocess.run")
@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_edit_with_no_changes(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
    mock_subprocess: MagicMock,
    mock_apply: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = [_make_fin_task(context="test task")]

    def noop_editor(cmd: list[str], check: bool = True) -> None:
        pass  # Don't modify file — no changes

    mock_subprocess.side_effect = noop_editor
    result = runner.invoke(app, ["edit"])
    assert result.exit_code == 0
    assert "no changes" in result.output.lower()
    mock_apply.assert_not_called()


@patch("fin.cli.apply_edit_actions")
@patch("fin.cli.subprocess.run")
@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_edit_applies_changes(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
    mock_subprocess: MagicMock,
    mock_apply: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = [_make_fin_task(context="test task")]
    mock_apply.return_value = 1

    def editor_closes_task(cmd: list[str], check: bool = True) -> None:
        _editor_that_closes_task(cmd[1])

    mock_subprocess.side_effect = editor_closes_task
    result = runner.invoke(app, ["edit"])
    assert result.exit_code == 0
    assert "applied 1 change" in result.output.lower()
    mock_apply.assert_called_once()


@patch("fin.cli.apply_edit_actions")
@patch("fin.cli.subprocess.run")
@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_edit_with_pool_option(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
    mock_subprocess: MagicMock,
    mock_apply: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    mock_subprocess.side_effect = lambda cmd, check=True: None
    result = runner.invoke(app, ["edit", "-p", "work"])
    assert result.exit_code == 0
    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs.get("pool") == "work"


@patch("fin.cli.apply_edit_actions")
@patch("fin.cli.subprocess.run")
@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_edit_compact_format(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
    mock_subprocess: MagicMock,
    mock_apply: MagicMock,
) -> None:
    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = [_make_fin_task(context="test task")]
    mock_subprocess.side_effect = lambda cmd, check=True: None
    result = runner.invoke(app, ["edit", "--format", "compact"])
    assert result.exit_code == 0


# --- fine entry point ---


def test_fine_entry_point_exists() -> None:
    """Verify fine_app is importable."""
    from fin.cli import fine_app

    assert fine_app is not None


@patch("fin.cli.apply_edit_actions")
@patch("fin.cli.subprocess.run")
@patch("fin.cli.list_tasks")
@patch("fin.cli.resolve_pools_dir")
@patch("fin.cli.resolve_global_config_dir")
def test_fine_invocation(
    mock_config_dir: MagicMock,
    mock_pools_dir: MagicMock,
    mock_list: MagicMock,
    mock_subprocess: MagicMock,
    mock_apply: MagicMock,
) -> None:
    from fin.cli import fine_app

    _stub_dirs(mock_pools_dir, mock_config_dir)
    mock_list.return_value = []
    mock_subprocess.side_effect = lambda cmd, check=True: None
    result = runner.invoke(fine_app, [])
    assert result.exit_code == 0
