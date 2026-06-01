from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Protocol


class PluginProtocol(Protocol):
    def register(self, app_context: dict) -> None: ...


class PluginManager:
    def __init__(self, plugins_dir: str = "plugins") -> None:
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_plugins: list[str] = []

    def load_plugins(self, app_context: dict) -> list[str]:
        for file in self.plugins_dir.glob("*.py"):
            spec = importlib.util.spec_from_file_location(file.stem, file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin = getattr(module, "plugin", None)
            if plugin and hasattr(plugin, "register"):
                plugin.register(app_context)
                self.loaded_plugins.append(file.stem)
        return self.loaded_plugins
