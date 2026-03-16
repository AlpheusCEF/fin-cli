"""Tests for fin editor module."""

from fin.core import FinTask
from fin.editor import (
    AddTagAction,
    AddTaskAction,
    CloseAction,
    DismissAction,
    EditableTask,
    RemoveTagAction,
    ReopenAction,
    SetDueAction,
    UpdateContentAction,
    UpdateNotesAction,
    diff_edit_actions,
    parse_edit_doc,
    render_edit_doc,
    serialize_to_edit_doc,
)


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


# --- serialize_to_edit_doc ---


def test_serialize_basic() -> None:
    tasks = [_make_task(context="write report", tags=["work"])]
    result = serialize_to_edit_doc(tasks)
    assert len(result) == 1
    assert result[0].summary == "write report"
    assert result[0].tags == ["work"]
    assert result[0].node_id == "abc123def456"


def test_serialize_with_due() -> None:
    tasks = [_make_task(meta={"due": "2026-04-01"})]
    result = serialize_to_edit_doc(tasks)
    assert result[0].due == "2026-04-01"


# --- render_edit_doc compact ---


def test_render_compact() -> None:
    editables = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="write report",
            tags=["work"],
            due="2026-04-01",
        )
    ]
    result = render_edit_doc(editables, fmt="compact")
    assert "[ ]" in result
    assert "write report" in result
    assert "#work" in result
    assert "due:2026-04-01" in result
    assert "#ref:abc123" in result


def test_render_compact_archived() -> None:
    editables = [
        EditableTask(
            node_id="abc123def456",
            status="archived",
            summary="done task",
        )
    ]
    result = render_edit_doc(editables, fmt="compact")
    assert "[x]" in result


# --- render_edit_doc yaml ---


def test_render_yaml() -> None:
    editables = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="write report",
            tags=["work", "important"],
            due="2026-04-01",
            notes="Include Q1 metrics.",
        )
    ]
    result = render_edit_doc(editables, fmt="yaml")
    assert "summary: write report" in result
    assert "id: abc123def456" in result
    assert "status: active" in result
    assert "work" in result
    assert "due: 2026-04-01" in result
    assert "Include Q1 metrics." in result


# --- parse_edit_doc compact ---


def test_parse_compact_basic() -> None:
    text = "# Fin Tasks\n[ ] write report #work due:2026-04-01 #ref:abc123\n"
    result = parse_edit_doc(text, fmt="compact")
    assert len(result) == 1
    assert result[0].summary == "write report"
    assert result[0].status == "active"
    assert "work" in result[0].tags
    assert result[0].due == "2026-04-01"
    assert result[0].node_id == "abc123"


def test_parse_compact_closed() -> None:
    text = "[x] done task #ref:abc123\n"
    result = parse_edit_doc(text, fmt="compact")
    assert result[0].status == "archived"


def test_parse_compact_dismissed() -> None:
    text = "[d] dismissed task #ref:abc123\n"
    result = parse_edit_doc(text, fmt="compact")
    assert result[0].status == "suppressed"


# --- parse_edit_doc yaml ---


def test_parse_yaml_basic() -> None:
    text = """
- summary: write report
  id: abc123def456
  status: active
  tags: [work, important]
  due: 2026-04-01
  notes: |
    Include Q1 metrics.
"""
    result = parse_edit_doc(text, fmt="yaml")
    assert len(result) == 1
    assert result[0].summary == "write report"
    assert result[0].node_id == "abc123def456"
    assert "work" in result[0].tags
    assert result[0].due == "2026-04-01"
    assert "Include Q1 metrics." in result[0].notes


# --- diff_edit_actions ---


def test_diff_no_changes() -> None:
    original = [
        EditableTask(
            node_id="abc123def456", status="active", summary="task"
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456", status="active", summary="task"
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert actions == []


def test_diff_close() -> None:
    original = [
        EditableTask(
            node_id="abc123def456", status="active", summary="task"
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456", status="archived", summary="task"
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], CloseAction)


def test_diff_dismiss() -> None:
    original = [
        EditableTask(
            node_id="abc123def456", status="active", summary="task"
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456", status="suppressed", summary="task"
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], DismissAction)


def test_diff_reopen() -> None:
    original = [
        EditableTask(
            node_id="abc123def456", status="archived", summary="task"
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456", status="active", summary="task"
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], ReopenAction)


def test_diff_add_tags() -> None:
    original = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="task",
            tags=["work"],
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="task",
            tags=["work", "urgent"],
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], AddTagAction)
    assert "urgent" in actions[0].tags


def test_diff_remove_tags() -> None:
    original = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="task",
            tags=["work", "urgent"],
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="task",
            tags=["work"],
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], RemoveTagAction)
    assert "urgent" in actions[0].tags


def test_diff_update_content() -> None:
    original = [
        EditableTask(
            node_id="abc123def456", status="active", summary="old content"
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456", status="active", summary="new content"
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], UpdateContentAction)
    assert actions[0].content == "new content"


def test_diff_update_notes() -> None:
    original = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="task",
            notes="old notes",
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="task",
            notes="new notes",
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], UpdateNotesAction)
    assert actions[0].notes == "new notes"


def test_diff_set_due() -> None:
    original = [
        EditableTask(
            node_id="abc123def456", status="active", summary="task"
        )
    ]
    edited = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="task",
            due="2026-04-01",
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], SetDueAction)
    assert actions[0].due == "2026-04-01"


def test_diff_deleted_line_dismisses() -> None:
    original = [
        EditableTask(
            node_id="abc123def456", status="active", summary="task"
        )
    ]
    edited: list[EditableTask] = []
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], DismissAction)


def test_diff_add_new_task() -> None:
    original: list[EditableTask] = []
    edited = [
        EditableTask(
            node_id="",
            status="active",
            summary="new task",
            tags=["work"],
            due="2026-04-01",
        )
    ]
    actions = diff_edit_actions(original, edited)
    assert len(actions) == 1
    assert isinstance(actions[0], AddTaskAction)
    assert actions[0].content == "new task"
    assert "work" in actions[0].tags
    assert actions[0].due == "2026-04-01"


# --- round-trip: compact ---


def test_compact_round_trip() -> None:
    original = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="write report",
            tags=["work"],
            due="2026-04-01",
        )
    ]
    rendered = render_edit_doc(original, fmt="compact")
    parsed = parse_edit_doc(rendered, fmt="compact")
    assert len(parsed) == 1
    assert parsed[0].summary == "write report"
    assert parsed[0].status == "active"
    assert "work" in parsed[0].tags
    assert parsed[0].due == "2026-04-01"


# --- round-trip: yaml ---


def test_yaml_round_trip() -> None:
    original = [
        EditableTask(
            node_id="abc123def456",
            status="active",
            summary="write report",
            tags=["work", "important"],
            due="2026-04-01",
            notes="Include Q1 metrics.",
        )
    ]
    rendered = render_edit_doc(original, fmt="yaml")
    parsed = parse_edit_doc(rendered, fmt="yaml")
    assert len(parsed) == 1
    assert parsed[0].summary == "write report"
    assert parsed[0].node_id == "abc123def456"
    assert "work" in parsed[0].tags
    assert parsed[0].due == "2026-04-01"
    assert "Include Q1 metrics." in parsed[0].notes
