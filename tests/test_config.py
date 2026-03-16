"""Tests for fin config layer."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fin.config import (
    TASKS_REGISTRY_ID,
    clear_default_pool,
    ensure_fin_pool,
    ensure_tasks_registry,
    get_pool_path,
    list_pools,
    load_fin_config,
    resolve_config_dir,
    resolve_pools_dir,
    save_fin_config,
    set_config_value,
    set_default_pool,
)


def test_tasks_registry_id_is_tasks() -> None:
    assert TASKS_REGISTRY_ID == "tasks"


def test_resolve_pools_dir_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIN_POOLS_DIR", raising=False)
    result = resolve_pools_dir()
    assert result == Path.home() / ".fin" / "pools"


def test_resolve_pools_dir_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIN_POOLS_DIR", "/custom/pools")
    assert resolve_pools_dir() == Path("/custom/pools")


def test_resolve_config_dir_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIN_CONFIG_DIR", raising=False)
    result = resolve_config_dir()
    assert result == Path.home() / ".config" / "fin"


def test_resolve_config_dir_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIN_CONFIG_DIR", "/custom/config")
    assert resolve_config_dir() == Path("/custom/config")


def test_load_fin_config_defaults() -> None:
    cfg = load_fin_config()
    assert cfg.default_pool == "default"
    assert cfg.wrap_width == 80
    assert cfg.default_days == 1
    assert cfg.default_done_days == 2
    assert cfg.auto_today_for_important is True


def test_load_fin_config_from_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))
    config_file = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"default_pool": "work", "wrap_width": 120})
    )
    cfg = load_fin_config()
    assert cfg.default_pool == "work"
    assert cfg.wrap_width == 120


def test_save_and_load_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fin.config import FinConfig

    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))

    cfg = FinConfig(default_pool="work", wrap_width=100)
    save_fin_config(cfg)
    loaded = load_fin_config()
    assert loaded.default_pool == "work"
    assert loaded.wrap_width == 100


def test_set_config_value_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))

    result = set_config_value("default_pool", "work")
    assert result.default_pool == "work"
    loaded = load_fin_config()
    assert loaded.default_pool == "work"


def test_set_config_value_int(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))

    result = set_config_value("wrap_width", "120")
    assert result.wrap_width == 120


def test_set_config_value_bool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))

    result = set_config_value("show_sections", "false")
    assert result.show_sections is False


def test_set_config_value_unknown_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))

    with pytest.raises(ValueError, match="Unknown config key"):
        set_config_value("nonexistent_key", "value")


def test_get_pool_path() -> None:
    pools_dir = Path("/tmp/pools")
    assert get_pool_path("work", pools_dir) == Path("/tmp/pools/work")
    assert get_pool_path("default", pools_dir) == Path("/tmp/pools/default")


def test_list_pools(tmp_path: Path) -> None:
    pools_dir = tmp_path / "pools"
    pools_dir.mkdir()
    (pools_dir / "work").mkdir()
    (pools_dir / "personal").mkdir()
    (pools_dir / ".hidden").mkdir()
    result = list_pools(pools_dir)
    assert result == ["personal", "work"]


def test_list_pools_empty(tmp_path: Path) -> None:
    assert list_pools(tmp_path / "nonexistent") == []


def test_set_default_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))

    result = set_default_pool("work")
    assert result.default_pool == "work"
    loaded = load_fin_config()
    assert loaded.default_pool == "work"


def test_clear_default_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))

    set_default_pool("work")
    result = clear_default_pool()
    assert result.default_pool == "default"


def test_ensure_tasks_registry_calls_interface(
    mock_alph_interface: dict[str, MagicMock],
) -> None:
    ensure_tasks_registry(
        global_config_dir=Path("/tmp/cfg"),
        pools_dir=Path("/tmp/pools"),
    )
    mock_alph_interface["alph_ensure_registry"].assert_called_once_with(
        global_config_dir=Path("/tmp/cfg"),
        pools_dir=Path("/tmp/pools"),
        registry_id="tasks",
        context="fin daily task registry",
    )


def test_ensure_fin_pool_calls_interface(
    mock_alph_interface: dict[str, MagicMock],
) -> None:
    ensure_fin_pool(
        pool_name="work",
        pools_dir=Path("/tmp/pools"),
        global_config_dir=Path("/tmp/cfg"),
    )
    mock_alph_interface["alph_ensure_pool"].assert_called_once_with(
        pool_path=Path("/tmp/pools/work"),
        registry_id="tasks",
        name="work",
        context="fin tasks: work",
        global_config_dir=Path("/tmp/cfg"),
    )


def test_resolve_global_config_dir_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fin.config import resolve_global_config_dir

    monkeypatch.delenv("ALPH_CONFIG_DIR", raising=False)
    result = resolve_global_config_dir()
    assert result == Path.home() / ".config" / "alph"


def test_resolve_global_config_dir_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fin.config import resolve_global_config_dir

    monkeypatch.setenv("ALPH_CONFIG_DIR", "/custom/alph")
    assert resolve_global_config_dir() == Path("/custom/alph")


def test_load_fin_config_corrupt_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))
    (config_dir / "config.json").write_text("{invalid json")
    cfg = load_fin_config()
    assert cfg.default_pool == "default"  # Falls back to defaults


def test_load_fin_config_non_dict_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "fin-config"
    config_dir.mkdir()
    monkeypatch.setenv("FIN_CONFIG_DIR", str(config_dir))
    (config_dir / "config.json").write_text('"just a string"')
    cfg = load_fin_config()
    assert cfg.default_pool == "default"  # Falls back to defaults
