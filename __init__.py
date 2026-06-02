from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


bl_info = {
    "name": "Waypoint Wall PCG",
    "author": "DuyDK",
    "version": (0, 2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Wall PCG",
    "description": "Generate walls from draggable waypoints",
    "category": "Add Mesh",
}


_NESTED_ADDON_FOLDER = "city-wall-gcp"
_NESTED_ADDON_MODULE = "city_wall_gcp"


def _nested_package_name() -> str:
    return f"{__package__}.{_NESTED_ADDON_MODULE}"


def _nested_addon_path() -> Path:
    return Path(__file__).resolve().parent / _NESTED_ADDON_FOLDER


def _unload_nested_addon(package_name: str) -> None:
    prefix = f"{package_name}."
    for module_name in sorted(list(sys.modules), reverse=True):
        if module_name == package_name or module_name.startswith(prefix):
            sys.modules.pop(module_name, None)


def _load_nested_addon() -> ModuleType:
    package_name = _nested_package_name()
    if package_name in sys.modules:
        _unload_nested_addon(package_name)

    addon_path = _nested_addon_path()
    addon_init = addon_path / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        package_name,
        addon_init,
        submodule_search_locations=[str(addon_path)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load nested Blender add-on from {addon_init}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


def register() -> None:
    _load_nested_addon().register()


def unregister() -> None:
    module = sys.modules.get(_nested_package_name())
    if module is None:
        module = _load_nested_addon()
    module.unregister()
