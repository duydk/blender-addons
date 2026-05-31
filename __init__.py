bl_info = {
    "name": "Waypoint Wall PCG",
    "author": "Codex",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Wall PCG",
    "description": "Generate walls from draggable waypoints",
    "category": "Add Mesh",
}

if "core" in locals():
    import importlib

    from .wpwall import handlers, props_ops, ui, wall_builder
    from . import core

    importlib.reload(wall_builder)
    importlib.reload(props_ops)
    importlib.reload(ui)
    importlib.reload(handlers)
    importlib.reload(core)

from .core import register, unregister


if __name__ == "__main__":
    register()
