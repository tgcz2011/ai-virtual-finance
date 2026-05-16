"""YAML configuration loader with automatic config/ directory discovery.

Provides a type-safe interface for accessing nested configuration values
via ``.get(type, key)`` and supports merging ``.example`` templates with
user overrides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """Loads and serves YAML configuration files from the ``config/`` directory.

    The loader discovers the project root by looking for ``config/`` next to
    ``src/`` (development layout) or inside the current working directory
    (installed layout).  Each logical config file is loaded once and cached.

    Example::

        cfg = ConfigLoader()
        rate: float = cfg.get("fee_schedule", "commissions.us_stocks.per_share")
    """

    _CONFIG_DIR_NAME = "config"
    _SRC_DIR_NAME = "src"

    def __init__(self, config_dir: str | Path | None = None) -> None:
        """Initialise the loader.

        Args:
            config_dir: Explicit path to the configuration directory.  When
                ``None`` the loader attempts auto-discovery.
        """
        if config_dir is not None:
            self._config_dir = Path(config_dir).resolve()
        else:
            self._config_dir = self._discover_config_dir()

        self._cache: dict[str, dict[str, Any]] = {}

    # --------------------------------------------------------------------- #
    # Discovery
    # --------------------------------------------------------------------- #

    @classmethod
    def _discover_config_dir(cls) -> Path:
        """Locate the ``config/`` directory.

        Search order:
        1. ``config/`` sibling of the current working directory.
        2. ``config/`` sibling of the file that imported this module (i.e.
           the project root when running from ``src/``).
        3. ``config/`` inside the current working directory.
        """
        cwd = Path.cwd()

        # 1. CWD sibling
        candidate = cwd.parent / cls._CONFIG_DIR_NAME
        if candidate.is_dir():
            return candidate.resolve()

        # 2. Module-import sibling (project root)
        try:
            module_file = Path(__file__).resolve()
            if module_file.name != "<stdin>":
                candidate = module_file.parents[1] / cls._CONFIG_DIR_NAME
                if candidate.is_dir():
                    return candidate.resolve()
        except (OSError, ValueError):
            pass

        # 3. CWD child
        candidate = cwd / cls._CONFIG_DIR_NAME
        if candidate.is_dir():
            return candidate.resolve()

        msg = (
            f"Unable to discover '{cls._CONFIG_DIR_NAME}/' directory. "
            "Pass config_dir explicitly or ensure the directory exists."
        )
        raise FileNotFoundError(msg)

    # --------------------------------------------------------------------- #
    # Loading
    # --------------------------------------------------------------------- #

    def _path_for(self, name: str) -> Path:
        """Return the resolved Path for a logical config name.

        Tries ``{name}.yaml`` first, then falls back to
        ``{name}.yaml.example`` so that templates work out of the box.
        """
        for suffix in (".yaml", ".yaml.example"):
            candidate = self._config_dir / f"{name}{suffix}"
            if candidate.exists():
                return candidate.resolve()
        msg = f"Config file for '{name}' not found in {self._config_dir}"
        raise FileNotFoundError(msg)

    def _load(self, name: str) -> dict[str, Any]:
        """Load and cache a configuration file by logical name."""
        if name not in self._cache:
            path = self._path_for(name)
            with open(path, encoding="utf-8") as fh:
                data: Any = yaml.safe_load(fh)
            if not isinstance(data, dict):
                msg = f"Top-level structure in {path} must be a mapping"
                raise ValueError(msg)
            self._cache[name] = data
        return self._cache[name]

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def get(
        self,
        config_type: str,
        key: str,
        default: int | float | str | bool | list[Any] | dict[str, Any] | None = None,
    ) -> int | float | str | bool | list[Any] | dict[str, Any] | None:
        """Return a typed configuration value.

        The *key* uses dot-notation to traverse nested mappings, e.g.
        ``commissions.us_stocks.per_share``.

        Args:
            config_type: Logical config name (e.g. ``fee_schedule``).
            key: Dot-separated path to the desired value.
            default: Value returned when the key is missing.

        Returns:
            The configuration value cast to the type of *default*, or
            *default* itself when the key is absent.

        Raises:
            FileNotFoundError: When the config file does not exist.
            ValueError: When an intermediate key is not a mapping.
        """
        data: Any = self._load(config_type)
        parts = key.split(".")

        for part in parts:
            if not isinstance(data, dict):
                msg = (
                    f"Cannot traverse key '{part}' in '{config_type}.{key}': "
                    f"intermediate value is not a mapping"
                )
                raise ValueError(msg)
            if part not in data:
                return default
            data = data[part]

        if default is None:
            result: int | float | str | bool | list[Any] | dict[str, Any] | None = data
            return result

        expected_type = type(default)
        if isinstance(data, expected_type):
            return data

        try:
            converted: int | float | str | bool | list[Any] | dict[str, Any]
            if expected_type is int:
                converted = int(data)
            elif expected_type is float:
                converted = float(data)
            elif expected_type is str:
                converted = str(data)
            elif expected_type is bool:
                converted = bool(data)
            else:
                converted = expected_type(data)
            return converted
        except (TypeError, ValueError) as exc:
            msg = (
                f"Value for '{config_type}.{key}' has type {type(data).__name__}, "
                f"expected {expected_type.__name__}"
            )
            raise ValueError(msg) from exc

    def section(self, config_type: str, key: str | None = None) -> dict[str, Any]:
        """Return an entire configuration section as a dictionary.

        Args:
            config_type: Logical config name.
            key: Optional dot-separated path to a sub-section.

        Returns:
            A shallow copy of the requested mapping.

        Raises:
            FileNotFoundError: When the config file does not exist.
            ValueError: When the resolved value is not a mapping.
        """
        data: Any = self._load(config_type)
        if key:
            parts = key.split(".")
            for part in parts:
                if not isinstance(data, dict):
                    msg = (
                        f"Cannot traverse key '{part}' in '{config_type}.{key}': "
                        f"intermediate value is not a mapping"
                    )
                    raise ValueError(msg)
                data = data[part]
        if not isinstance(data, dict):
            msg = f"Value for '{config_type}.{key or ''}' is not a mapping"
            raise ValueError(msg)
        return dict(data)

    def reload(self, config_type: str | None = None) -> None:
        """Clear the cache for *config_type* (or all configs if None)."""
        if config_type is None:
            self._cache.clear()
        else:
            self._cache.pop(config_type, None)
