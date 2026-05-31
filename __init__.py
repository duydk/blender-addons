bl_info = {
    "name": "Waypoint Wall PCG",
    "author": "Codex",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Wall PCG",
    "description": "Generate walls from draggable waypoints",
    "category": "Add Mesh",
}

from .core import register, unregister


if __name__ == "__main__":
    register()
