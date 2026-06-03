import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy.types import Operator, PropertyGroup

from .builder import clear_buildings, create_building, rebuild_active_building
from .data import building_type_items, building_type_spec

_SUPPRESS_SETTING_REBUILD = False


def roof_style_items():
    return (
        ('FLAT', "Flat", "Flat roof with a small parapet"),
        ('GABLE', "Gable", "Pitched gable roof"),
    )


def update_building(self, context):
    if _SUPPRESS_SETTING_REBUILD or context is None:
        return
    settings = context.scene.bgcp_settings if context.scene else None
    if settings is not None and settings.auto_update:
        rebuild_active_building(context)


def apply_type_defaults_to_settings(settings, spec):
    global _SUPPRESS_SETTING_REBUILD
    _SUPPRESS_SETTING_REBUILD = True
    try:
        for attr_name, value in spec.defaults.items():
            if hasattr(settings, attr_name):
                setattr(settings, attr_name, value)
    finally:
        _SUPPRESS_SETTING_REBUILD = False


class BGCPSettings(PropertyGroup):
    building_width: FloatProperty(name="Width", default=10.5, min=1.0, update=update_building)
    building_depth: FloatProperty(name="Depth", default=5.2, min=1.0, update=update_building)
    floors: IntProperty(name="Floors", default=1, min=1, max=64, update=update_building)
    floor_height: FloatProperty(name="Floor Height", default=3.2, min=1.0, update=update_building)

    roof_style: EnumProperty(name="Roof Style", items=roof_style_items(), default='GABLE', update=update_building)
    roof_height: FloatProperty(name="Roof Height", default=2.09, min=0.05, update=update_building)
    roof_overhang: FloatProperty(name="Roof Overhang", default=1.89, min=0.0, update=update_building)

    window_columns: IntProperty(name="Front Columns", default=4, min=0, max=32, update=update_building)
    side_window_columns: IntProperty(name="Side Columns", default=2, min=0, max=32, update=update_building)
    window_width: FloatProperty(name="Window Width", default=0.65, min=0.1, update=update_building)
    window_height: FloatProperty(name="Window Height", default=1.0, min=0.1, update=update_building)

    door_width: FloatProperty(name="Door Width", default=1.0, min=0.2, update=update_building)
    door_height: FloatProperty(name="Door Height", default=2.0, min=0.4, update=update_building)

    platform_height: FloatProperty(name="Platform Height", default=0.9, min=0.05, update=update_building)
    platform_margin: FloatProperty(name="Platform Margin", default=2.6, min=0.0, update=update_building)
    stair_width: FloatProperty(name="Stair Width", default=2.8, min=0.2, update=update_building)
    stair_steps: IntProperty(name="Stair Steps", default=7, min=1, max=64, update=update_building)
    side_stairs_enabled: BoolProperty(name="Side Stairs", default=True, update=update_building)
    balustrade_enabled: BoolProperty(name="Balustrade", default=True, update=update_building)
    balustrade_height: FloatProperty(name="Balustrade Height", default=0.36, min=0.05, update=update_building)
    balustrade_post_spacing: FloatProperty(name="Post Spacing", default=0.25, min=0.25, update=update_building)
    bay_count: IntProperty(name="Front Bays", default=5, min=2, max=32, update=update_building)
    side_bay_count: IntProperty(name="Side Bays", default=2, min=1, max=16, update=update_building)
    column_radius: FloatProperty(name="Column Radius", default=0.09, min=0.02, update=update_building)
    column_height: FloatProperty(name="Column Height", default=1.4, min=0.5, update=update_building)
    round_pillar_offset: FloatProperty(name="Round Pillar Offset", default=-0.27, update=update_building)
    horizontal_beam_z_offset: FloatProperty(name="Long Beam Z Offset", default=0.0, update=update_building)
    cross_beam_z_offset: FloatProperty(name="Cross Beam Z Offset", default=0.0, update=update_building)
    cross_beam_length: FloatProperty(name="Cross Beam Length", default=6.16, min=0.1, update=update_building)
    main_door_height: FloatProperty(name="Main Door Height", default=1.0, min=0.1, update=update_building)
    lower_roof_height: FloatProperty(name="Lower Roof Height", default=0.94, min=0.05, update=update_building)
    upper_platform_height: FloatProperty(name="Upper Platform Height", default=0.3, min=0.1, update=update_building)
    upper_roof_height: FloatProperty(name="Upper Roof Height", default=1.46, min=0.05, update=update_building)
    roof_curve: FloatProperty(name="Roof Curve", default=0.12, min=0.0, max=1.0, update=update_building)
    roof_line_width: FloatProperty(name="Roof Line Width", default=0.10, min=0.005, update=update_building)
    roof_line_height: FloatProperty(name="Roof Line Height", default=0.10, min=0.001, update=update_building)
    roof_underside_thickness: FloatProperty(name="Roof Underside Thickness", default=0.01, min=0.001, update=update_building)
    roof_underside_z_offset: FloatProperty(name="Roof Underside Z Offset", default=0.0, update=update_building)
    roof_tiles_enabled: BoolProperty(name="Roof Tiles", default=True, update=update_building)
    roof_ying_tile_radius: FloatProperty(name="Ying Tile Radius", default=0.03, min=0.02, update=update_building)
    roof_yang_tile_radius: FloatProperty(name="Yang Tile Radius", default=0.10, min=0.02, update=update_building)
    roof_ying_tile_z_offset: FloatProperty(name="Ying Tile Z Offset", default=0.03, update=update_building)
    roof_tile_gap: FloatProperty(name="Tile Gap", default=0.02, min=0.0, update=update_building)
    roof_tile_safe_distance: FloatProperty(name="Tile Safe Distance", default=0.08, min=0.0, update=update_building)
    roof_tile_thickness: FloatProperty(name="Tile Thickness", default=0.03, min=0.005, update=update_building)
    roof_tile_segment_length: FloatProperty(name="Tile Segment Length", default=0.18, min=0.12, update=update_building)
    eave_overhang: FloatProperty(name="Eave Overhang", default=0.75, min=0.0, update=update_building)
    lower_eave_overhang: FloatProperty(name="Lower Eave Overhang", default=0.75, min=0.0, update=update_building)
    upper_eave_overhang: FloatProperty(name="Upper Eave Overhang", default=0.45, min=0.0, update=update_building)

    wall_color: FloatVectorProperty(
        name="Wall",
        subtype='COLOR',
        size=4,
        default=(0.62, 0.58, 0.50, 1.0),
        min=0.0,
        max=1.0,
        update=update_building,
    )
    roof_color: FloatVectorProperty(
        name="Roof",
        subtype='COLOR',
        size=4,
        default=(0.28, 0.12, 0.08, 1.0),
        min=0.0,
        max=1.0,
        update=update_building,
    )
    glass_color: FloatVectorProperty(
        name="Glass",
        subtype='COLOR',
        size=4,
        default=(0.12, 0.30, 0.48, 0.72),
        min=0.0,
        max=1.0,
        update=update_building,
    )
    door_color: FloatVectorProperty(
        name="Door",
        subtype='COLOR',
        size=4,
        default=(0.28, 0.14, 0.07, 1.0),
        min=0.0,
        max=1.0,
        update=update_building,
    )
    trim_color: FloatVectorProperty(
        name="Trim",
        subtype='COLOR',
        size=4,
        default=(0.78, 0.74, 0.66, 1.0),
        min=0.0,
        max=1.0,
        update=update_building,
    )

    collection_name: StringProperty(name="Collection", default="Building_GCP")
    use_type_defaults: BoolProperty(name="Use Type Defaults", default=True)
    auto_update: BoolProperty(name="Auto Update Selected Building", default=True)
    select_after_generate: BoolProperty(name="Select Building", default=True)


class BGCP_OT_generate_building(Operator):
    bl_idname = "bgcp.generate_building"
    bl_label = "Generate Building"
    bl_options = {"UNDO"}

    building_type: EnumProperty(name="Type", items=building_type_items(), default='HALL')

    def execute(self, context):
        spec = building_type_spec(self.building_type)
        settings = context.scene.bgcp_settings
        if settings.use_type_defaults:
            apply_type_defaults_to_settings(settings, spec)
        root = create_building(context, spec.identifier)
        if not settings.select_after_generate:
            root.select_set(False)
        self.report({'INFO'}, f"Generated {spec.label}: {root.name}")
        return {'FINISHED'}


class BGCP_OT_rebuild_building(Operator):
    bl_idname = "bgcp.rebuild_building"
    bl_label = "Rebuild Building"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not rebuild_active_building(context):
            self.report({'WARNING'}, "Select a generated building or one of its parts")
            return {'CANCELLED'}
        self.report({'INFO'}, "Building rebuilt")
        return {'FINISHED'}


class BGCP_OT_clear_buildings(Operator):
    bl_idname = "bgcp.clear_buildings"
    bl_label = "Clear Generated Buildings"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        clear_buildings()
        self.report({'INFO'}, "Cleared generated buildings")
        return {'FINISHED'}
