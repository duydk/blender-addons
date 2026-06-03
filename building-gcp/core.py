import bpy
from bpy.props import IntProperty, PointerProperty

from .bgenerator.props_ops import (
    BGCPSettings,
    BGCP_OT_clear_buildings,
    BGCP_OT_generate_building,
    BGCP_OT_rebuild_building,
)
from .bgenerator.ui import BGCP_PT_panel, BGCP_PT_scene_panel

classes = (
    BGCPSettings,
    BGCP_OT_generate_building,
    BGCP_OT_rebuild_building,
    BGCP_OT_clear_buildings,
    BGCP_PT_panel,
    BGCP_PT_scene_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bgcp_settings = PointerProperty(type=BGCPSettings)
    bpy.types.Scene.bgcp_next_id = IntProperty(name="Next Building Id", default=0)


def unregister():
    if hasattr(bpy.types.Scene, "bgcp_next_id"):
        del bpy.types.Scene.bgcp_next_id
    if hasattr(bpy.types.Scene, "bgcp_settings"):
        del bpy.types.Scene.bgcp_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
