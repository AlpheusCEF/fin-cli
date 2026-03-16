"""Bulk editor format: serialize, render, parse, diff, apply."""

from dataclasses import dataclass, field

from fin.core import FinTask


@dataclass(frozen=True)
class EditableTask:
    """A task in the editor intermediary format."""

    node_id: str
    status: str
    summary: str
    tags: list[str] = field(default_factory=list)
    due: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class EditAction:
    """Base for editor diff actions."""

    node_id: str


@dataclass(frozen=True)
class CloseAction(EditAction):
    """Mark a task as archived."""


@dataclass(frozen=True)
class ReopenAction(EditAction):
    """Reopen an archived/dismissed task."""


@dataclass(frozen=True)
class DismissAction(EditAction):
    """Mark a task as suppressed."""


@dataclass(frozen=True)
class AddTagAction(EditAction):
    """Add tags to a task."""

    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RemoveTagAction(EditAction):
    """Remove tags from a task."""

    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UpdateContentAction(EditAction):
    """Update a task's summary/context."""

    content: str = ""


@dataclass(frozen=True)
class UpdateNotesAction(EditAction):
    """Update a task's body/notes."""

    notes: str = ""


@dataclass(frozen=True)
class SetDueAction(EditAction):
    """Set or clear a task's due date."""

    due: str | None = None


@dataclass(frozen=True)
class AddTaskAction:
    """Add a new task from editor."""

    content: str
    tags: list[str] = field(default_factory=list)
    due: str | None = None


def serialize_to_edit_doc(tasks: list[FinTask]) -> list[EditableTask]:
    """Convert FinTasks to editable intermediary format."""
    result: list[EditableTask] = []
    for task in tasks:
        result.append(
            EditableTask(
                node_id=task.node_id,
                status=task.status,
                summary=task.context,
                tags=list(task.tags),
                due=task.due_date,
                notes=task.body,
            )
        )
    return result


def render_edit_doc(
    editables: list[EditableTask], *, fmt: str = "compact"
) -> str:
    """Render editable tasks to a string for editing."""
    if fmt == "yaml":
        return _render_yaml(editables)
    return _render_compact(editables)


def _status_checkbox(status: str) -> str:
    return {"active": "[ ]", "archived": "[x]", "suppressed": "[d]"}.get(
        status, "[ ]"
    )


def _checkbox_to_status(checkbox: str) -> str:
    return {"[ ]": "active", "[x]": "archived", "[d]": "suppressed"}.get(
        checkbox, "active"
    )


def _render_compact(editables: list[EditableTask]) -> str:
    lines = ["# Fin Tasks - Edit and save to update"]
    for et in editables:
        short_id = et.node_id[:6]
        cb = _status_checkbox(et.status)
        parts = [cb, et.summary]
        tags = [t for t in et.tags if t not in ("important", "today")]
        if tags:
            parts.append(" ".join(f"#{t}" for t in tags))
        if et.due:
            parts.append(f"due:{et.due}")
        parts.append(f"#ref:{short_id}")
        lines.append(" ".join(parts))
    return "\n".join(lines) + "\n"


def _render_yaml(editables: list[EditableTask]) -> str:
    lines: list[str] = []
    for et in editables:
        lines.append(f"- summary: {et.summary}")
        lines.append(f"  id: {et.node_id}")
        lines.append(f"  status: {et.status}")
        if et.tags:
            tag_str = ", ".join(et.tags)
            lines.append(f"  tags: [{tag_str}]")
        if et.due:
            lines.append(f"  due: {et.due}")
        if et.notes:
            lines.append("  notes: |")
            for note_line in et.notes.splitlines():
                lines.append(f"    {note_line}")
        lines.append("")
    return "\n".join(lines)


def parse_edit_doc(text: str, *, fmt: str = "compact") -> list[EditableTask]:
    """Parse editor output back to editable tasks."""
    if fmt == "yaml":
        return _parse_yaml(text)
    return _parse_compact(text)


def _parse_compact(text: str) -> list[EditableTask]:
    import re

    result: list[EditableTask] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            # Check if this is a comment vs a task line starting with checkbox
            if line.startswith("# "):
                continue
            if not line:
                continue

        # Match checkbox pattern
        cb_match = re.match(r"(\[[ xd]\])\s+(.+)", line)
        if not cb_match:
            continue

        checkbox = cb_match.group(1)
        rest = cb_match.group(2)
        status = _checkbox_to_status(checkbox)

        # Extract #ref:ID
        ref_match = re.search(r"#ref:(\w+)", rest)
        node_id = ref_match.group(1) if ref_match else ""
        if ref_match:
            rest = rest[: ref_match.start()].strip()

        # Extract due:DATE
        due_match = re.search(r"due:(\S+)", rest)
        due = due_match.group(1) if due_match else None
        if due_match:
            rest = rest[: due_match.start()] + rest[due_match.end() :]
            rest = rest.strip()

        # Extract #tags
        tags: list[str] = []
        tag_matches = re.findall(r"#(\w+)", rest)
        for tag in tag_matches:
            tags.append(tag)
        rest = re.sub(r"#\w+", "", rest).strip()
        # Collapse whitespace
        rest = re.sub(r"\s+", " ", rest).strip()

        result.append(
            EditableTask(
                node_id=node_id,
                status=status,
                summary=rest,
                tags=tags,
                due=due,
            )
        )
    return result


def _parse_yaml(text: str) -> list[EditableTask]:
    import yaml

    data = yaml.safe_load(text)
    if not isinstance(data, list):
        return []
    result: list[EditableTask] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        tags_raw = item.get("tags", [])
        tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []
        due_raw = item.get("due")
        due = str(due_raw) if due_raw is not None else None
        result.append(
            EditableTask(
                node_id=str(item.get("id", "")),
                status=str(item.get("status", "active")),
                summary=str(item.get("summary", "")),
                tags=tags,
                due=due,
                notes=str(item.get("notes", "")),
            )
        )
    return result


def diff_edit_actions(
    original: list[EditableTask], edited: list[EditableTask]
) -> list[EditAction | AddTaskAction]:
    """Diff original vs edited to produce action list."""
    original_map = {et.node_id: et for et in original}
    edited_map = {et.node_id: et for et in edited if et.node_id}
    actions: list[EditAction | AddTaskAction] = []

    for node_id, orig in original_map.items():
        if node_id not in edited_map:
            # Deleted — dismiss
            actions.append(DismissAction(node_id=node_id))
            continue
        edit = edited_map[node_id]

        # Status change
        if orig.status != edit.status:
            if edit.status == "archived":
                actions.append(CloseAction(node_id=node_id))
            elif edit.status == "suppressed":
                actions.append(DismissAction(node_id=node_id))
            elif edit.status == "active":
                actions.append(ReopenAction(node_id=node_id))

        # Tag changes
        orig_tags = set(orig.tags)
        edit_tags = set(edit.tags)
        added_tags = edit_tags - orig_tags
        removed_tags = orig_tags - edit_tags
        if added_tags:
            actions.append(
                AddTagAction(node_id=node_id, tags=sorted(added_tags))
            )
        if removed_tags:
            actions.append(
                RemoveTagAction(node_id=node_id, tags=sorted(removed_tags))
            )

        # Content change
        if orig.summary != edit.summary:
            actions.append(
                UpdateContentAction(node_id=node_id, content=edit.summary)
            )

        # Notes change
        if orig.notes != edit.notes:
            actions.append(
                UpdateNotesAction(node_id=node_id, notes=edit.notes)
            )

        # Due date change
        if orig.due != edit.due:
            actions.append(SetDueAction(node_id=node_id, due=edit.due))

    # New tasks (no node_id)
    for edit in edited:
        if not edit.node_id:
            actions.append(
                AddTaskAction(
                    content=edit.summary, tags=edit.tags, due=edit.due
                )
            )

    return actions
