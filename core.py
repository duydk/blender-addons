import bpy
from bpy.props import CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

from .wpwall.wall_builder import gate_base_items, gate_style_items
from .wpwall.handlers import depsgraph_update_handler
from .wpwall.props_ops import (
    WPWALL_OT_add_gate,
    WPWALL_OT_add_opening,
    WPWALL_OT_add_waypoint,
    WPWALL_OT_build_wall,
    WPWALL_OT_clear_all,
    WPWALL_OT_new_wall,
    WPWALL_OT_remove_last_gate,
    WPWALL_OT_remove_last_opening,
    WPWALL_OT_remove_last_waypoint,
    WPWALL_OT_remove_selected_waypoint,
    WPWALL_OT_select_next_waypoint,
    WPWALL_OT_select_prev_waypoint,
    WPWallSettings,
    WPWallWaypointRef,
    trigger_rebuild,
    update_gate_base_style_object,
    update_gate_height_object,
    update_gate_object,
    update_gate_style_object,
    update_opening_object,
)
from .wpwall.ui import WPWALL_PT_panel, WPWALL_PT_scene_panel

classes = (
    WPWallWaypointRef,
    WPWallSettings,
    WPWALL_OT_select_prev_waypoint,
    WPWALL_OT_select_next_waypoint,
    WPWALL_OT_new_wall,
    WPWALL_OT_add_waypoint,
    WPWALL_OT_remove_last_waypoint,
    WPWALL_OT_remove_selected_waypoint,
    WPWALL_OT_add_opening,
    WPWALL_OT_remove_last_opening,
    WPWALL_OT_add_gate,
    WPWALL_OT_remove_last_gate,
    WPWALL_OT_build_wall,
    WPWALL_OT_clear_all,
    WPWALL_PT_panel,
    WPWALL_PT_scene_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.wp_wall_corner_radius = FloatProperty(
        name="Corner Radius",
        default=0.0,
        min=0.0,
        update=lambda self, ctx: trigger_rebuild(ctx),
    )
    bpy.types.Object.wp_wall_curve_steps = IntProperty(
        name="Curve Detail",
        default=6,
        min=1,
        max=32,
        update=lambda self, ctx: trigger_rebuild(ctx),
    )
    bpy.types.Object.wp_wall_opening_length = FloatProperty(
        name="Opening Length",
        default=2.0,
        min=0.05,
        update=update_opening_object,
    )
    bpy.types.Object.wp_wall_opening_width = FloatProperty(
        name="Opening Length",
        default=2.0,
        min=0.05,
        update=update_opening_object,
    )
    bpy.types.Object.wp_wall_gate_length = FloatProperty(
        name="Gate Length",
        default=2.0,
        min=0.05,
        update=update_gate_object,
    )
    bpy.types.Object.wp_wall_gate_height = FloatProperty(
        name="Gate Height",
        default=2.0,
        min=0.05,
        update=update_gate_height_object,
    )
    bpy.types.Object.wp_wall_gate_style = EnumProperty(
        name="Gate Style",
        items=gate_style_items(),
        default='ARCH',
        update=update_gate_style_object,
    )
    bpy.types.Object.wp_wall_gate_base_style = EnumProperty(
        name="Gate Base",
        items=gate_base_items(),
        default='NONE',
        update=update_gate_base_style_object,
    )
    bpy.types.Scene.wp_wall_settings = PointerProperty(type=WPWallSettings)
    bpy.types.Scene.wp_wall_waypoints = CollectionProperty(type=WPWallWaypointRef)
    bpy.types.Scene.wp_wall_active_rig = PointerProperty(name="Active Wall Rig", type=bpy.types.Object)
    bpy.types.Scene.wp_wall_next_id = IntProperty(name="Next Wall Id", default=0)
    if depsgraph_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_handler)


def unregister():
    if depsgraph_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_handler)
    del bpy.types.Object.wp_wall_gate_base_style
    del bpy.types.Object.wp_wall_gate_style
    del bpy.types.Object.wp_wall_gate_height
    del bpy.types.Object.wp_wall_gate_length
    del bpy.types.Object.wp_wall_opening_length
    del bpy.types.Object.wp_wall_opening_width
    del bpy.types.Object.wp_wall_curve_steps
    del bpy.types.Object.wp_wall_corner_radius
    del bpy.types.Scene.wp_wall_next_id
    del bpy.types.Scene.wp_wall_active_rig
    del bpy.types.Scene.wp_wall_waypoints
    del bpy.types.Scene.wp_wall_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
