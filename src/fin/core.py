"""All fin business logic."""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alph.core import NodeResult

from fin.alph_interface import (
    alph_create_node,
    alph_list_nodes,
    alph_set_node_status,
    alph_show_node,
    alph_update_node,
)
from fin.config import (
    ensure_fin_pool,
    ensure_tasks_registry,
    get_pool_path,
    load_fin_config,
)

# --- Tag shorthand expansion ---

_TAG_SHORTHANDS: dict[str, str] = {
    "i": "important",
    "t": "today",
}

# Pattern: #word or #key:value
_TAG_PATTERN = re.compile(r"#(\w+(?::\S+)?)")


# --- Errors ---


class AmbiguousIDError(Exception):
    """Multiple nodes match the given ID prefix."""

    def __init__(self, prefix: str, matches: list[str]) -> None:
        self.prefix = prefix
        self.matches = matches
        super().__init__(
            f"Ambiguous ID prefix '{prefix}' matches: "
            + ", ".join(format_short_id(m) for m in matches)
        )


class UnknownIDError(Exception):
    """No node matches the given ID prefix."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        super().__init__(f"No task found matching '{prefix}'")


# --- Data types ---


@dataclass(frozen=True)
class ParsedContent:
    """Result of parsing raw fin input."""

    content: str
    tags: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FinTask:
    """A fin task with computed fields."""

    node_id: str
    context: str  # alph node context (task description)
    timestamp: str
    status: str
    tags: list[str]
    meta: dict[str, object]
    body: str

    @property
    def short_id(self) -> str:
        return format_short_id(self.node_id)

    @property
    def is_important(self) -> bool:
        return "important" in self.tags

    @property
    def is_today(self) -> bool:
        return "today" in self.tags

    @property
    def due_date(self) -> str | None:
        due = self.meta.get("due")
        return str(due) if due is not None else None

    @property
    def is_overdue(self) -> bool:
        due = self.due_date
        if due is None:
            return False
        try:
            return datetime.strptime(due, "%Y-%m-%d").replace(
                tzinfo=UTC
            ) < datetime.now(UTC)
        except ValueError:
            return False


# --- Content parsing ---


def parse_fin_content(raw: str) -> ParsedContent:
    """Parse raw input, extracting tags and meta from #markers."""
    tags: list[str] = []
    meta: dict[str, str] = {}

    matches = _TAG_PATTERN.findall(raw)
    clean = _TAG_PATTERN.sub("", raw).strip()
    # Collapse multiple spaces
    clean = re.sub(r"\s+", " ", clean)

    for match in matches:
        if ":" in match:
            key, value = match.split(":", 1)
            meta[key] = value
        else:
            expanded = _TAG_SHORTHANDS.get(match, match)
            tags.append(expanded)

    return ParsedContent(content=clean, tags=tags, meta=meta)


def build_node_kwargs(parsed: ParsedContent, pool: str) -> dict[str, object]:
    """Map ParsedContent to alph create_node kwargs."""
    kwargs: dict[str, object] = {
        "source": "fin",
        "context": parsed.content,
        "tags": parsed.tags,
        "meta": parsed.meta,
        "content": parsed.content,
    }
    return kwargs


# --- ID resolution ---


def format_short_id(node_id: str) -> str:
    """Return the first 6 characters of a node ID."""
    return node_id[:6]


def resolve_short_id(prefix: str, pool_path: Path) -> str:
    """Resolve a short ID prefix to a full node ID."""
    all_ids: list[str] = []
    for subdir in ("snapshots", "live"):
        directory = pool_path / subdir
        if not directory.exists():
            continue
        for node_file in directory.glob("*.md"):
            all_ids.append(node_file.stem)

    # Exact match
    if prefix in all_ids:
        return prefix

    # Prefix match
    matches = [nid for nid in all_ids if nid.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AmbiguousIDError(prefix, matches)
    raise UnknownIDError(prefix)


# --- Task operations ---


def add_task(
    content: str,
    *,
    pool: str | None = None,
    pools_dir: Path,
    global_config_dir: Path,
    creator: str = "",
) -> NodeResult:
    """Add a new task."""
    cfg = load_fin_config()
    resolved_pool = pool or cfg.default_pool

    ensure_tasks_registry(
        global_config_dir=global_config_dir, pools_dir=pools_dir
    )
    ensure_fin_pool(
        pool_name=resolved_pool,
        pools_dir=pools_dir,
        global_config_dir=global_config_dir,
    )

    parsed = parse_fin_content(content)
    pool_path = get_pool_path(resolved_pool, pools_dir)

    return alph_create_node(
        pool_path=pool_path,
        source="fin",
        context=parsed.content,
        tags=parsed.tags,
        meta=dict(parsed.meta),
        content=parsed.content,
        creator=creator,
    )


def list_tasks(
    *,
    pool: str | None = None,
    pools_dir: Path,
    global_config_dir: Path,
    statuses: set[str] | None = None,
    days: int | None = None,
) -> list[FinTask]:
    """List tasks with optional filtering."""
    cfg = load_fin_config()
    resolved_pool = pool or cfg.default_pool
    pool_path = get_pool_path(resolved_pool, pools_dir)

    if not pool_path.exists():
        return []

    summaries = alph_list_nodes(pool_path, statuses=statuses)
    tasks: list[FinTask] = []

    for summary in summaries:
        detail = alph_show_node(pool_path, summary.node_id)
        if detail is None:
            continue
        task = FinTask(
            node_id=detail.node_id,
            context=detail.context,
            timestamp=detail.timestamp,
            status=summary.status,
            tags=detail.tags,
            meta=detail.meta,
            body=detail.body,
        )
        if days is not None:
            try:
                ts = datetime.fromisoformat(task.timestamp)
                cutoff = datetime.now(UTC).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=days)
                if ts < cutoff:
                    continue
            except ValueError:
                pass
        tasks.append(task)

    return tasks


def add_completed_task(
    content: str,
    *,
    pool: str | None = None,
    pools_dir: Path,
    global_config_dir: Path,
    creator: str = "",
) -> NodeResult:
    """Add a task and immediately mark it archived (completed)."""
    result = add_task(
        content,
        pool=pool,
        pools_dir=pools_dir,
        global_config_dir=global_config_dir,
        creator=creator,
    )
    if not result.duplicate:
        cfg = load_fin_config()
        resolved_pool = pool or cfg.default_pool
        pool_path = get_pool_path(resolved_pool, pools_dir)
        alph_set_node_status(
            pool_path=pool_path,
            node_id=result.node_id,
            status="archived",
        )
    return result


def close_task(
    task_id: str,
    *,
    pool: str | None = None,
    pools_dir: Path,
    global_config_dir: Path,
) -> str:
    """Close a task, spawning recurrence if applicable. Returns full node ID."""
    cfg = load_fin_config()
    resolved_pool = pool or cfg.default_pool
    pool_path = get_pool_path(resolved_pool, pools_dir)
    full_id = resolve_short_id(task_id, pool_path)

    # Check for recurrence before closing
    detail = alph_show_node(pool_path, full_id)
    if detail is not None:
        recur = detail.meta.get("recur")
        if recur is not None:
            spawn_recurrence(
                detail,
                pool=resolved_pool,
                pools_dir=pools_dir,
                global_config_dir=global_config_dir,
            )

    alph_set_node_status(
        pool_path=pool_path,
        node_id=full_id,
        status="archived",
    )
    return full_id


# --- Label filtering ---


def filter_by_labels(tasks: list[FinTask], expression: str) -> list[FinTask]:
    """Filter tasks by a boolean label expression.

    Supports AND, OR, NOT operators and parentheses.
    Case-insensitive substring matching on tag names.
    """
    tokens = _tokenize_label_expr(expression)
    tree = _parse_label_expr(tokens)
    return [t for t in tasks if _eval_label_expr(tree, t.tags)]


def _tokenize_label_expr(expr: str) -> list[str]:
    """Tokenize a label expression into words and parens."""
    padded = expr.replace("(", " ( ").replace(")", " ) ")
    return [t for t in padded.split() if t]


def _parse_label_expr(tokens: list[str]) -> object:
    """Parse tokens into an expression tree. Precedence: NOT > AND > OR."""
    pos = [0]

    def _parse_or() -> object:
        left = _parse_and()
        while pos[0] < len(tokens) and tokens[pos[0]].upper() == "OR":
            pos[0] += 1
            right = _parse_and()
            left = ("OR", left, right)
        return left

    def _parse_and() -> object:
        left = _parse_not()
        while pos[0] < len(tokens) and tokens[pos[0]].upper() == "AND":
            pos[0] += 1
            right = _parse_not()
            left = ("AND", left, right)
        return left

    def _parse_not() -> object:
        if pos[0] < len(tokens) and tokens[pos[0]].upper() == "NOT":
            pos[0] += 1
            operand = _parse_not()
            return ("NOT", operand)
        return _parse_atom()

    def _parse_atom() -> object:
        if pos[0] < len(tokens) and tokens[pos[0]] == "(":
            pos[0] += 1
            result = _parse_or()
            if pos[0] < len(tokens) and tokens[pos[0]] == ")":
                pos[0] += 1
            return result
        if pos[0] < len(tokens):
            token = tokens[pos[0]]
            pos[0] += 1
            return token
        return ""

    return _parse_or()


def _eval_label_expr(tree: object, tags: list[str]) -> bool:
    """Evaluate a parsed label expression against a tag list."""
    if isinstance(tree, str):
        needle = tree.lower()
        return any(needle in tag.lower() for tag in tags)
    if isinstance(tree, tuple):
        op = tree[0]
        if op == "NOT":
            return not _eval_label_expr(tree[1], tags)
        if op == "AND":
            return _eval_label_expr(tree[1], tags) and _eval_label_expr(
                tree[2], tags
            )
        if op == "OR":
            return _eval_label_expr(tree[1], tags) or _eval_label_expr(
                tree[2], tags
            )
    return False


# --- Recurring tasks ---


def spawn_recurrence(
    detail: object,
    *,
    pool: str,
    pools_dir: Path,
    global_config_dir: Path,
    creator: str = "",
) -> NodeResult | None:
    """Create the next instance of a recurring task."""
    from alph.core import NodeDetail

    if not isinstance(detail, NodeDetail):
        return None
    recur = detail.meta.get("recur")
    if recur is None:
        return None

    # Rebuild content with tags and meta
    parts = [detail.context]
    for tag in detail.tags:
        parts.append(f"#{tag}")
    for key, value in detail.meta.items():
        parts.append(f"#{key}:{value}")

    content = " ".join(parts)
    return add_task(
        content,
        pool=pool,
        pools_dir=pools_dir,
        global_config_dir=global_config_dir,
        creator=creator,
    )


# --- Dependencies ---


def get_blocked_tasks(
    tasks: list[FinTask], all_tasks: list[FinTask]
) -> set[str]:
    """Return node IDs of tasks that are blocked by open dependencies."""
    active_ids = {t.node_id for t in all_tasks if t.status == "active"}
    blocked: set[str] = set()
    for task in tasks:
        depends = task.meta.get("depends")
        if depends is not None and str(depends) in active_ids:
            blocked.add(task.node_id)
    return blocked


# --- Edit action application ---


def apply_edit_actions(
    *,
    actions: Sequence[object],
    pool_path: Path,
    pool: str,
    pools_dir: Path,
    global_config_dir: Path,
) -> int:
    """Apply editor diff actions to the pool. Returns count of actions applied."""
    from fin.editor import (
        AddTagAction,
        AddTaskAction,
        CloseAction,
        DismissAction,
        RemoveTagAction,
        ReopenAction,
        SetDueAction,
        UpdateContentAction,
        UpdateNotesAction,
    )

    applied = 0
    for action in actions:
        if isinstance(action, CloseAction):
            alph_set_node_status(
                pool_path=pool_path, node_id=action.node_id, status="archived"
            )
            applied += 1
        elif isinstance(action, DismissAction):
            alph_set_node_status(
                pool_path=pool_path, node_id=action.node_id, status="suppressed"
            )
            applied += 1
        elif isinstance(action, ReopenAction):
            alph_set_node_status(
                pool_path=pool_path, node_id=action.node_id, status="active"
            )
            applied += 1
        elif isinstance(action, AddTagAction):
            alph_update_node(
                pool_path=pool_path, node_id=action.node_id, tags_add=action.tags
            )
            applied += 1
        elif isinstance(action, RemoveTagAction):
            alph_update_node(
                pool_path=pool_path, node_id=action.node_id, tags_remove=action.tags
            )
            applied += 1
        elif isinstance(action, UpdateContentAction):
            alph_update_node(
                pool_path=pool_path, node_id=action.node_id, context=action.content
            )
            applied += 1
        elif isinstance(action, UpdateNotesAction):
            alph_update_node(
                pool_path=pool_path, node_id=action.node_id, content=action.notes
            )
            applied += 1
        elif isinstance(action, SetDueAction):
            meta: dict[str, object] = {"due": action.due} if action.due else {}
            alph_update_node(
                pool_path=pool_path, node_id=action.node_id, meta=meta
            )
            applied += 1
        elif isinstance(action, AddTaskAction):
            content_parts = [action.content]
            for tag in action.tags:
                content_parts.append(f"#{tag}")
            if action.due:
                content_parts.append(f"#due:{action.due}")
            add_task(
                " ".join(content_parts),
                pool=pool,
                pools_dir=pools_dir,
                global_config_dir=global_config_dir,
            )
            applied += 1
    return applied
