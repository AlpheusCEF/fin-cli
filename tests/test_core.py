"""Tests for fin core logic."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alph.core import NodeDetail, NodeResult, NodeSummary

from fin.core import (
    AmbiguousIDError,
    FinTask,
    ParsedContent,
    UnknownIDError,
    add_completed_task,
    add_task,
    build_node_kwargs,
    filter_by_labels,
    format_short_id,
    get_blocked_tasks,
    list_tasks,
    parse_fin_content,
    resolve_short_id,
)

# --- parse_fin_content ---


def test_parse_basic_content() -> None:
    result = parse_fin_content("write the quarterly report")
    assert result.content == "write the quarterly report"
    assert result.tags == []
    assert result.meta == {}


def test_parse_tags() -> None:
    result = parse_fin_content("do thing #work #important")
    assert result.content == "do thing"
    assert "work" in result.tags
    assert "important" in result.tags


def test_parse_shorthand_tags() -> None:
    result = parse_fin_content("urgent thing #i #t")
    assert "important" in result.tags
    assert "today" in result.tags
    assert result.content == "urgent thing"


def test_parse_due_date() -> None:
    result = parse_fin_content("report #due:2026-04-01")
    assert result.meta == {"due": "2026-04-01"}
    assert result.content == "report"


def test_parse_recur() -> None:
    result = parse_fin_content("standup #recur:daily")
    assert result.meta == {"recur": "daily"}
    assert result.content == "standup"


def test_parse_depends() -> None:
    result = parse_fin_content("deploy #depends:abc123")
    assert result.meta == {"depends": "abc123"}
    assert result.content == "deploy"


def test_parse_mixed() -> None:
    result = parse_fin_content(
        "write the quarterly report #work #important #due:2026-04-01"
    )
    assert result.content == "write the quarterly report"
    assert "work" in result.tags
    assert "important" in result.tags
    assert result.meta == {"due": "2026-04-01"}


def test_parse_strips_whitespace() -> None:
    result = parse_fin_content("  do thing  #work  ")
    assert result.content == "do thing"
    assert result.tags == ["work"]


# --- build_node_kwargs ---


def test_build_node_kwargs_basic() -> None:
    parsed = ParsedContent(content="write report", tags=["work"], meta={})
    kwargs = build_node_kwargs(parsed, "default")
    assert kwargs["context"] == "write report"
    assert kwargs["tags"] == ["work"]
    assert kwargs["content"] == "write report"
    assert kwargs["source"] == "fin"


def test_build_node_kwargs_with_meta() -> None:
    parsed = ParsedContent(
        content="report", tags=[], meta={"due": "2026-04-01"}
    )
    kwargs = build_node_kwargs(parsed, "work")
    assert kwargs["meta"] == {"due": "2026-04-01"}


# --- FinTask ---


def test_fin_task_short_id() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={},
        body="",
    )
    assert task.short_id == "abc123"


def test_fin_task_is_important() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=["important"],
        meta={},
        body="",
    )
    assert task.is_important is True


def test_fin_task_is_today() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=["today"],
        meta={},
        body="",
    )
    assert task.is_today is True


def test_fin_task_due_date() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={"due": "2026-04-01"},
        body="",
    )
    assert task.due_date == "2026-04-01"


def test_fin_task_is_overdue() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={"due": "2020-01-01"},
        body="",
    )
    assert task.is_overdue is True


def test_fin_task_not_overdue_future_date() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={"due": "2099-12-31"},
        body="",
    )
    assert task.is_overdue is False


def test_fin_task_not_overdue_no_date() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={},
        body="",
    )
    assert task.is_overdue is False


# --- format_short_id / resolve_short_id ---


def test_format_short_id() -> None:
    assert format_short_id("abc123def456") == "abc123"


def test_resolve_short_id_exact_match(isolated_pool: Path) -> None:
    from tests.conftest import _write_node

    _write_node(isolated_pool, "abc123def456")
    assert resolve_short_id("abc123def456", isolated_pool) == "abc123def456"


def test_resolve_short_id_prefix_match(isolated_pool: Path) -> None:
    from tests.conftest import _write_node

    _write_node(isolated_pool, "abc123def456")
    assert resolve_short_id("abc123", isolated_pool) == "abc123def456"


def test_resolve_short_id_ambiguous(isolated_pool: Path) -> None:
    from tests.conftest import _write_node

    _write_node(isolated_pool, "abc123def456")
    _write_node(isolated_pool, "abc123999888")
    with pytest.raises(AmbiguousIDError):
        resolve_short_id("abc123", isolated_pool)


def test_resolve_short_id_not_found(isolated_pool: Path) -> None:
    with pytest.raises(UnknownIDError):
        resolve_short_id("zzz999", isolated_pool)


# --- add_task ---


def test_add_task(mock_alph_interface: dict[str, MagicMock]) -> None:
    mock_alph_interface["alph_create_node"].return_value = NodeResult(
        node_id="abc123def456", path=Path("/tmp/node.md")
    )
    result = add_task(
        "write report #work #due:2026-04-01",
        pools_dir=Path("/tmp/pools"),
        global_config_dir=Path("/tmp/cfg"),
        creator="test@test.com",
    )
    assert result.node_id == "abc123def456"
    mock_alph_interface["alph_ensure_registry"].assert_called_once()
    mock_alph_interface["alph_ensure_pool"].assert_called_once()
    mock_alph_interface["alph_create_node"].assert_called_once()


def test_add_task_with_pool(
    mock_alph_interface: dict[str, MagicMock],
) -> None:
    mock_alph_interface["alph_create_node"].return_value = NodeResult(
        node_id="abc123def456", path=Path("/tmp/node.md")
    )
    add_task(
        "do thing",
        pool="work",
        pools_dir=Path("/tmp/pools"),
        global_config_dir=Path("/tmp/cfg"),
        creator="test@test.com",
    )
    ensure_pool_call = mock_alph_interface["alph_ensure_pool"].call_args
    assert ensure_pool_call.kwargs["name"] == "work"


# --- list_tasks ---


def test_list_tasks(
    mock_alph_interface: dict[str, MagicMock], tmp_path: Path
) -> None:
    pools_dir = tmp_path / "pools"
    (pools_dir / "default").mkdir(parents=True)
    mock_alph_interface["alph_list_nodes"].return_value = [
        NodeSummary(
            node_id="abc123def456",
            context="test task",
            node_type="snapshot",
            timestamp="2026-03-13T00:00:00+00:00",
            source="fin",
            content_type="task",
        )
    ]
    mock_alph_interface["alph_show_node"].return_value = NodeDetail(
        node_id="abc123def456",
        context="test task",
        node_type="snapshot",
        timestamp="2026-03-13T00:00:00+00:00",
        source="fin",
        creator="test@test.com",
        body="",
        tags=["work"],
        meta={"due": "2026-04-01"},
    )
    tasks = list_tasks(
        pools_dir=pools_dir,
        global_config_dir=Path("/tmp/cfg"),
    )
    assert len(tasks) == 1
    assert tasks[0].node_id == "abc123def456"
    assert "work" in tasks[0].tags
    assert tasks[0].due_date == "2026-04-01"


def test_list_tasks_empty(mock_alph_interface: dict[str, MagicMock]) -> None:
    mock_alph_interface["alph_list_nodes"].return_value = []
    tasks = list_tasks(
        pools_dir=Path("/tmp/nonexistent-pools"),
        global_config_dir=Path("/tmp/cfg"),
    )
    assert tasks == []


# --- add_completed_task ---


def test_add_completed_task(
    mock_alph_interface: dict[str, MagicMock],
) -> None:
    mock_alph_interface["alph_create_node"].return_value = NodeResult(
        node_id="abc123def456", path=Path("/tmp/node.md")
    )
    result = add_completed_task(
        "did the thing",
        pools_dir=Path("/tmp/pools"),
        global_config_dir=Path("/tmp/cfg"),
    )
    assert result.node_id == "abc123def456"
    mock_alph_interface["alph_set_node_status"].assert_called_once()
    status_call = mock_alph_interface["alph_set_node_status"].call_args
    assert status_call.kwargs["status"] == "archived"


# --- filter_by_labels ---


def _task_with_tags(tags: list[str], node_id: str = "abc123") -> FinTask:
    return FinTask(
        node_id=node_id,
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=tags,
        meta={},
        body="",
    )


def test_filter_simple_match() -> None:
    tasks = [_task_with_tags(["work"]), _task_with_tags(["personal"], "def456")]
    result = filter_by_labels(tasks, "work")
    assert len(result) == 1
    assert result[0].tags == ["work"]


def test_filter_and() -> None:
    tasks = [
        _task_with_tags(["work", "urgent"], "aaa111"),
        _task_with_tags(["work"], "bbb222"),
        _task_with_tags(["urgent"], "ccc333"),
    ]
    result = filter_by_labels(tasks, "work AND urgent")
    assert len(result) == 1
    assert result[0].node_id == "aaa111"


def test_filter_or() -> None:
    tasks = [
        _task_with_tags(["work"], "aaa111"),
        _task_with_tags(["personal"], "bbb222"),
        _task_with_tags(["other"], "ccc333"),
    ]
    result = filter_by_labels(tasks, "work OR personal")
    assert len(result) == 2


def test_filter_not() -> None:
    tasks = [
        _task_with_tags(["work", "urgent"], "aaa111"),
        _task_with_tags(["work"], "bbb222"),
    ]
    result = filter_by_labels(tasks, "work AND NOT urgent")
    assert len(result) == 1
    assert result[0].node_id == "bbb222"


def test_filter_parens() -> None:
    tasks = [
        _task_with_tags(["work"], "aaa111"),
        _task_with_tags(["personal"], "bbb222"),
        _task_with_tags(["work", "urgent"], "ccc333"),
    ]
    result = filter_by_labels(tasks, "(work OR personal) AND NOT urgent")
    assert len(result) == 2
    ids = {t.node_id for t in result}
    assert ids == {"aaa111", "bbb222"}


def test_filter_case_insensitive() -> None:
    tasks = [_task_with_tags(["Work"])]
    result = filter_by_labels(tasks, "work")
    assert len(result) == 1


# --- get_blocked_tasks ---


def test_blocked_by_open_dependency() -> None:
    dep_task = _task_with_tags([], "dep111aaa222")
    blocked_task = FinTask(
        node_id="blk222bbb333",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={"depends": "dep111aaa222"},
        body="",
    )
    all_tasks = [dep_task, blocked_task]
    blocked = get_blocked_tasks([blocked_task], all_tasks)
    assert "blk222bbb333" in blocked


def test_not_blocked_no_dependency() -> None:
    task = FinTask(
        node_id="aaa111bbb222",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={},
        body="",
    )
    blocked = get_blocked_tasks([task], [task])
    assert blocked == set()


def test_not_blocked_when_dep_archived() -> None:
    dep_task = FinTask(
        node_id="dep111aaa222",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="archived",
        tags=[],
        meta={},
        body="",
    )
    blocked_task = FinTask(
        node_id="blk222bbb333",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={"depends": "dep111aaa222"},
        body="",
    )
    all_tasks = [dep_task, blocked_task]
    blocked = get_blocked_tasks([blocked_task], all_tasks)
    assert "blk222bbb333" not in blocked


# --- close_task ---


def test_close_task_archives(
    mock_alph_interface: dict[str, MagicMock], isolated_pool: Path
) -> None:
    from fin.core import close_task
    from tests.conftest import _write_node

    _write_node(isolated_pool, "abc123def456", context="do thing")
    mock_alph_interface["alph_show_node"].return_value = NodeDetail(
        node_id="abc123def456",
        context="do thing",
        node_type="snapshot",
        timestamp="2026-03-13T00:00:00+00:00",
        source="fin",
        creator="test@test.com",
        body="",
        tags=[],
        meta={},
    )
    full_id = close_task(
        "abc123",
        pool="test-pool",
        pools_dir=isolated_pool.parent,
        global_config_dir=Path("/tmp/cfg"),
    )
    assert full_id == "abc123def456"
    mock_alph_interface["alph_set_node_status"].assert_called_once()
    call_kwargs = mock_alph_interface["alph_set_node_status"].call_args.kwargs
    assert call_kwargs["status"] == "archived"


def test_close_task_spawns_recurrence(
    mock_alph_interface: dict[str, MagicMock], isolated_pool: Path
) -> None:
    from fin.core import close_task
    from tests.conftest import _write_node

    _write_node(
        isolated_pool,
        "rec123def456",
        context="standup",
        meta={"recur": "daily"},
        tags=["work"],
    )
    mock_alph_interface["alph_show_node"].return_value = NodeDetail(
        node_id="rec123def456",
        context="standup",
        node_type="snapshot",
        timestamp="2026-03-13T00:00:00+00:00",
        source="fin",
        creator="test@test.com",
        body="",
        tags=["work"],
        meta={"recur": "daily"},
    )
    mock_alph_interface["alph_create_node"].return_value = NodeResult(
        node_id="new123def456", path=Path("/tmp/new.md")
    )
    close_task(
        "rec123",
        pool="test-pool",
        pools_dir=isolated_pool.parent,
        global_config_dir=Path("/tmp/cfg"),
    )
    # Should have called create_node for the recurrence spawn
    mock_alph_interface["alph_create_node"].assert_called_once()


# --- spawn_recurrence ---


def test_spawn_recurrence_returns_none_for_non_node_detail() -> None:
    from fin.core import spawn_recurrence

    result = spawn_recurrence(
        "not a NodeDetail",
        pool="default",
        pools_dir=Path("/tmp/pools"),
        global_config_dir=Path("/tmp/cfg"),
    )
    assert result is None


def test_spawn_recurrence_returns_none_without_recur(
    mock_alph_interface: dict[str, MagicMock],
) -> None:
    from fin.core import spawn_recurrence

    detail = NodeDetail(
        node_id="abc123def456",
        context="one-off task",
        node_type="snapshot",
        timestamp="2026-03-13T00:00:00+00:00",
        source="fin",
        creator="test@test.com",
        body="",
        tags=[],
        meta={},
    )
    result = spawn_recurrence(
        detail,
        pool="default",
        pools_dir=Path("/tmp/pools"),
        global_config_dir=Path("/tmp/cfg"),
    )
    assert result is None


# --- list_tasks with date filtering ---


def test_list_tasks_filters_by_days(
    mock_alph_interface: dict[str, MagicMock], tmp_path: Path
) -> None:
    from datetime import UTC, datetime, timedelta

    pools_dir = tmp_path / "pools"
    (pools_dir / "default").mkdir(parents=True)

    old_ts = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    recent_ts = datetime.now(UTC).isoformat()

    mock_alph_interface["alph_list_nodes"].return_value = [
        NodeSummary(
            node_id="old111aaa222",
            context="old task",
            node_type="snapshot",
            timestamp=old_ts,
            source="fin",
        ),
        NodeSummary(
            node_id="new111bbb333",
            context="new task",
            node_type="snapshot",
            timestamp=recent_ts,
            source="fin",
        ),
    ]

    def show_side_effect(pool_path: Path, node_id: str) -> NodeDetail:
        ts = old_ts if node_id == "old111aaa222" else recent_ts
        ctx = "old task" if node_id == "old111aaa222" else "new task"
        return NodeDetail(
            node_id=node_id,
            context=ctx,
            node_type="snapshot",
            timestamp=ts,
            source="fin",
            creator="test@test.com",
            body="",
            tags=[],
            meta={},
        )

    mock_alph_interface["alph_show_node"].side_effect = show_side_effect

    tasks = list_tasks(
        pools_dir=pools_dir,
        global_config_dir=Path("/tmp/cfg"),
        days=7,
    )
    assert len(tasks) == 1
    assert tasks[0].node_id == "new111bbb333"


def test_list_tasks_show_node_returns_none_skips(
    mock_alph_interface: dict[str, MagicMock], tmp_path: Path
) -> None:
    pools_dir = tmp_path / "pools"
    (pools_dir / "default").mkdir(parents=True)

    mock_alph_interface["alph_list_nodes"].return_value = [
        NodeSummary(
            node_id="abc123def456",
            context="test task",
            node_type="snapshot",
            timestamp="2026-03-13T00:00:00+00:00",
            source="fin",
        ),
    ]
    mock_alph_interface["alph_show_node"].return_value = None

    tasks = list_tasks(
        pools_dir=pools_dir,
        global_config_dir=Path("/tmp/cfg"),
    )
    assert tasks == []


# --- add_completed_task duplicate ---


def test_add_completed_task_duplicate_skips_status_change(
    mock_alph_interface: dict[str, MagicMock],
) -> None:
    mock_alph_interface["alph_create_node"].return_value = NodeResult(
        node_id="abc123def456",
        path=Path("/tmp/node.md"),
        duplicate=True,
        existing_creator="test@test.com",
    )
    result = add_completed_task(
        "duplicate thing",
        pools_dir=Path("/tmp/pools"),
        global_config_dir=Path("/tmp/cfg"),
    )
    assert result.duplicate is True
    mock_alph_interface["alph_set_node_status"].assert_not_called()


# --- FinTask edge cases ---


def test_fin_task_is_overdue_invalid_date() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={"due": "not-a-date"},
        body="",
    )
    assert task.is_overdue is False


def test_fin_task_due_date_none_when_missing() -> None:
    task = FinTask(
        node_id="abc123def456",
        context="test",
        timestamp="2026-03-13T00:00:00+00:00",
        status="active",
        tags=[],
        meta={},
        body="",
    )
    assert task.due_date is None
