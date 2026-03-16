"""Tests for fin display module."""

from fin.core import FinTask
from fin.display import render_task_detail, render_task_list


def _make_task(
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


def test_render_empty_list() -> None:
    result = render_task_list([])
    assert "no open tasks" in result.lower()


def test_render_single_task() -> None:
    task = _make_task(context="write report")
    result = render_task_list([task])
    assert "abc123" in result
    assert "write report" in result


def test_render_important_bucket() -> None:
    important = _make_task(
        node_id="imp123def456", context="urgent thing", tags=["important"]
    )
    regular = _make_task(node_id="reg123def456", context="normal thing")
    result = render_task_list([regular, important])
    imp_pos = result.find("urgent thing")
    reg_pos = result.find("normal thing")
    assert imp_pos < reg_pos


def test_render_today_bucket() -> None:
    today = _make_task(
        node_id="tod123def456", context="today thing", tags=["today"]
    )
    regular = _make_task(node_id="reg123def456", context="normal thing")
    result = render_task_list([regular, today])
    today_pos = result.find("today thing")
    reg_pos = result.find("normal thing")
    assert today_pos < reg_pos


def test_render_overdue_marker() -> None:
    task = _make_task(
        context="overdue thing", meta={"due": "2020-01-01"}
    )
    result = render_task_list([task])
    assert "OVERDUE" in result


def test_render_task_detail_basic() -> None:
    task = _make_task(context="write report", body="detailed notes here")
    result = render_task_detail(task)
    assert "abc123" in result
    assert "write report" in result
    assert "detailed notes here" in result


def test_render_task_detail_with_tags() -> None:
    task = _make_task(context="tagged thing", tags=["work", "important"])
    result = render_task_detail(task)
    assert "work" in result
    assert "important" in result


def test_render_task_detail_with_due() -> None:
    task = _make_task(context="due thing", meta={"due": "2026-04-01"})
    result = render_task_detail(task)
    assert "2026-04-01" in result


def test_render_task_detail_overdue_marker() -> None:
    task = _make_task(context="overdue detail", meta={"due": "2020-01-01"})
    result = render_task_detail(task)
    assert "OVERDUE" in result
    assert "2020-01-01" in result


def test_render_blocked_task() -> None:
    task = _make_task(node_id="blk123def456", context="blocked thing")
    result = render_task_list([task], blocked={"blk123def456"})
    assert "BLOCKED" in result


def test_render_due_date_in_task_line() -> None:
    task = _make_task(context="future thing", meta={"due": "2099-12-31"})
    result = render_task_list([task])
    assert "due 2099-12-31" in result


def test_render_tags_in_task_line() -> None:
    task = _make_task(context="tagged thing", tags=["work", "review"])
    result = render_task_list([task])
    assert "#work" in result
    assert "#review" in result


def test_render_priority_section_headers() -> None:
    important = _make_task(
        node_id="imp123def456", context="urgent", tags=["important"]
    )
    today = _make_task(
        node_id="tod123def456", context="today thing", tags=["today"]
    )
    regular = _make_task(node_id="reg123def456", context="normal")
    result = render_task_list([regular, today, important])
    assert "--- important ---" in result
    assert "--- today ---" in result
    assert "--- tasks ---" in result


def test_render_no_section_header_for_regular_only() -> None:
    regular = _make_task(context="normal task")
    result = render_task_list([regular])
    assert "--- tasks ---" not in result


def test_render_archived_status_symbol() -> None:
    task = _make_task(context="done task", status="archived")
    result = render_task_list([task])
    assert "\u2611" in result  # ☑


def test_render_suppressed_status_symbol() -> None:
    task = _make_task(context="dismissed task", status="suppressed")
    result = render_task_list([task])
    assert "\u2012" in result  # ‒
