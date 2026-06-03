bl_info = {
    "name": "Building Generator GCP",
    "author": "DuyDK",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Building GCP",
    "description": "Generate procedural buildings with floors, windows, doors, and roofs",
    "category": "Add Mesh",
}

if "core" in locals():
    import importlib

    from .bgenerator import builder, data, hall_builder, hall_parts, props_ops, tags, ui
    from . import core

    importlib.reload(tags)
    importlib.reload(data)
    importlib.reload(hall_parts)
    importlib.reload(hall_builder)
    importlib.reload(builder)
    importlib.reload(props_ops)
    importlib.reload(ui)
    importlib.reload(core)

from .core import register, unregister


if __name__ == "__main__":
    register()
