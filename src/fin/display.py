"""Rendering functions for fin output. All pure functions, no I/O."""

from fin.core import FinTask


def render_task_list(
    tasks: list[FinTask], *, blocked: set[str] | None = None
) -> str:
    """Render a list of tasks with priority bucketing."""
    if not tasks:
        return "No open tasks."
    blocked = blocked or set()

    important: list[FinTask] = []
    today: list[FinTask] = []
    regular: list[FinTask] = []

    for task in tasks:
        if task.is_important:
            important.append(task)
        elif task.is_today:
            today.append(task)
        else:
            regular.append(task)

    lines: list[str] = []

    if important:
        lines.append("--- important ---")
        for task in important:
            lines.append(_format_task_line(task, blocked=blocked))

    if today:
        lines.append("--- today ---")
        for task in today:
            lines.append(_format_task_line(task, blocked=blocked))

    if regular:
        if important or today:
            lines.append("--- tasks ---")
        for task in regular:
            lines.append(_format_task_line(task, blocked=blocked))

    return "\n".join(lines)


def _format_task_line(
    task: FinTask, *, blocked: set[str] | None = None
) -> str:
    """Format a single task as a one-line summary."""
    blocked = blocked or set()
    parts: list[str] = []
    parts.append(f"  {task.short_id}")

    status_symbol = _status_symbol(task.status)
    parts.append(status_symbol)

    if task.node_id in blocked:
        parts.append("[BLOCKED]")

    parts.append(task.context)

    if task.is_overdue:
        parts.append("[OVERDUE]")
    elif task.due_date:
        parts.append(f"(due {task.due_date})")

    tags = [t for t in task.tags if t not in ("important", "today")]
    if tags:
        parts.append(" ".join(f"#{t}" for t in tags))

    return " ".join(parts)


def _status_symbol(status: str) -> str:
    """Map status to a display symbol."""
    # Use Unicode brackets to avoid Rich markup interpretation
    symbols = {
        "active": "\u2610",   # ☐
        "archived": "\u2611",  # ☑
        "suppressed": "\u2012",  # ‒
    }
    return symbols.get(status, "\u2610")


def render_task_detail(task: FinTask) -> str:
    """Render full task detail."""
    lines: list[str] = []
    lines.append(f"ID:      {task.short_id} ({task.node_id})")
    lines.append(f"Task:    {task.context}")
    lines.append(f"Status:  {task.status}")

    if task.tags:
        lines.append(f"Tags:    {', '.join(task.tags)}")

    if task.due_date:
        due_line = f"Due:     {task.due_date}"
        if task.is_overdue:
            due_line += " [OVERDUE]"
        lines.append(due_line)

    if task.body:
        lines.append("")
        lines.append(task.body)

    return "\n".join(lines)
