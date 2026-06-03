from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


bl_info = {
    "name": "GCP Generators",
    "author": "DuyDK",
    "version": (0, 3, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Wall PCG / Building GCP",
    "description": "Generate procedural walls and buildings",
    "category": "Add Mesh",
}


_NESTED_ADDONS = (
    ("city-wall-gcp", "city_wall_gcp"),
    ("building-gcp", "building_gcp"),
)


def _nested_package_name(module_name: str) -> str:
    return f"{__package__}.{module_name}"


def _nested_addon_path(folder_name: str) -> Path:
    return Path(__file__).resolve().parent / folder_name


def _unload_nested_addon(package_name: str) -> None:
    prefix = f"{package_name}."
    for module_name in sorted(list(sys.modules), reverse=True):
        if module_name == package_name or module_name.startswith(prefix):
            sys.modules.pop(module_name, None)


def _load_nested_addon(folder_name: str, module_name: str) -> ModuleType:
    package_name = _nested_package_name(module_name)
    if package_name in sys.modules:
        _unload_nested_addon(package_name)

    addon_path = _nested_addon_path(folder_name)
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
    registered_modules = []
    try:
        for folder_name, module_name in _NESTED_ADDONS:
            module = _load_nested_addon(folder_name, module_name)
            module.register()
            registered_modules.append(module)
    except Exception:
        for module in reversed(registered_modules):
            module.unregister()
        raise


def unregister() -> None:
    for folder_name, module_name in reversed(_NESTED_ADDONS):
        module = sys.modules.get(_nested_package_name(module_name))
        if module is None:
            module = _load_nested_addon(folder_name, module_name)
        module.unregister()
