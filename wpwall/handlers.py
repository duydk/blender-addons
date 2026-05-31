import bpy

from .engine import *
@bpy.app.handlers.persistent
def depsgraph_update_handler(scene, depsgraph):
    if not settings(scene).auto_update:
        return
    valid_waypoints = {ref.obj for ref in scene.wp_wall_waypoints if ref.obj}
    valid_openings = set(sorted_openings(scene))
    valid_gates = set(sorted_gates(scene))
    changed = False
    for update in depsgraph.updates:
        obj = getattr(update.id, "original", None) or update.id
        if isinstance(obj, bpy.types.Object) and (obj in valid_waypoints or obj in valid_openings or obj in valid_gates):
            if object_is_valid(obj.parent):
                if obj.parent.get(RIG_TAG):
                    scene.wp_wall_active_rig = obj.parent
                elif object_is_valid(obj.parent.parent) and obj.parent.parent.get(RIG_TAG):
                    scene.wp_wall_active_rig = obj.parent.parent
            changed = True
            break
    if changed:
        build_wall_mesh(scene)


