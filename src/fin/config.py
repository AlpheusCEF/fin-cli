"""fin config management."""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from fin.alph_interface import alph_ensure_pool, alph_ensure_registry

TASKS_REGISTRY_ID = "tasks"
_CONFIG_FILENAME = "config.json"


@dataclass
class FinConfig:
    """fin-specific configuration."""

    default_pool: str = "default"
    editor: str = ""
    date_format: str = "%Y-%m-%d"
    wrap_width: int = 80
    default_days: int = 1
    default_done_days: int = 2
    show_sections: bool = True
    weekdays_only_lookback: bool = True
    auto_today_for_important: bool = True
    pool_default_tag_filters: dict[str, str] = field(default_factory=dict)


def resolve_pools_dir() -> Path:
    """Resolve the pools directory from env or default."""
    env = os.environ.get("FIN_POOLS_DIR")
    if env:
        return Path(env)
    return Path.home() / ".fin" / "pools"


def resolve_config_dir() -> Path:
    """Resolve the fin config directory from env or default."""
    env = os.environ.get("FIN_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".config" / "fin"


def resolve_global_config_dir() -> Path:
    """Resolve the alph global config directory from env or default."""
    env = os.environ.get("ALPH_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".config" / "alph"


def _config_path() -> Path:
    return resolve_config_dir() / _CONFIG_FILENAME


def load_fin_config() -> FinConfig:
    """Load fin-specific config from disk, falling back to defaults."""
    path = _config_path()
    if not path.exists():
        return FinConfig()
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return FinConfig()
        return FinConfig(
            default_pool=str(data.get("default_pool", "default")),
            editor=str(data.get("editor", "")),
            date_format=str(data.get("date_format", "%Y-%m-%d")),
            wrap_width=int(data.get("wrap_width", 80)),
            default_days=int(data.get("default_days", 1)),
            default_done_days=int(data.get("default_done_days", 2)),
            show_sections=bool(data.get("show_sections", True)),
            weekdays_only_lookback=bool(
                data.get("weekdays_only_lookback", True)
            ),
            auto_today_for_important=bool(
                data.get("auto_today_for_important", True)
            ),
            pool_default_tag_filters=dict(
                data.get("pool_default_tag_filters", {})
            ),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return FinConfig()


def save_fin_config(cfg: FinConfig) -> None:
    """Save fin config to disk."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg), indent=2) + "\n")


def set_config_value(key: str, value: str) -> FinConfig:
    """Set a single config key and save. Returns updated config."""
    cfg = load_fin_config()
    bool_keys = {
        "show_sections",
        "weekdays_only_lookback",
        "auto_today_for_important",
    }
    int_keys = {"wrap_width", "default_days", "default_done_days"}
    str_keys = {"default_pool", "editor", "date_format"}

    if key in bool_keys:
        setattr(cfg, key, value.lower() in ("true", "1", "yes"))
    elif key in int_keys:
        setattr(cfg, key, int(value))
    elif key in str_keys:
        setattr(cfg, key, value)
    else:
        msg = f"Unknown config key: {key}"
        raise ValueError(msg)

    save_fin_config(cfg)
    return cfg


def get_pool_path(pool: str, pools_dir: Path) -> Path:
    """Get the filesystem path for a named pool."""
    return pools_dir / pool


def list_pools(pools_dir: Path) -> list[str]:
    """List all pool names (pool directories)."""
    if not pools_dir.exists():
        return []
    return sorted(
        d.name
        for d in pools_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def set_default_pool(pool: str) -> FinConfig:
    """Set the default pool and save config."""
    cfg = load_fin_config()
    cfg = FinConfig(
        default_pool=pool,
        editor=cfg.editor,
        date_format=cfg.date_format,
        wrap_width=cfg.wrap_width,
        default_days=cfg.default_days,
        default_done_days=cfg.default_done_days,
        show_sections=cfg.show_sections,
        weekdays_only_lookback=cfg.weekdays_only_lookback,
        auto_today_for_important=cfg.auto_today_for_important,
        pool_default_tag_filters=cfg.pool_default_tag_filters,
    )
    save_fin_config(cfg)
    return cfg


def clear_default_pool() -> FinConfig:
    """Reset default pool to 'default'."""
    return set_default_pool("default")


def ensure_tasks_registry(
    *, global_config_dir: Path, pools_dir: Path
) -> None:
    """Idempotently create the tasks registry."""
    alph_ensure_registry(
        global_config_dir=global_config_dir,
        pools_dir=pools_dir,
        registry_id=TASKS_REGISTRY_ID,
        context="fin daily task registry",
    )


def ensure_fin_pool(
    *,
    pool_name: str,
    pools_dir: Path,
    global_config_dir: Path,
) -> None:
    """Idempotently create a fin pool."""
    pool_path = get_pool_path(pool_name, pools_dir)
    alph_ensure_pool(
        pool_path=pool_path,
        registry_id=TASKS_REGISTRY_ID,
        name=pool_name,
        context=f"fin tasks: {pool_name}",
        global_config_dir=global_config_dir,
    )
