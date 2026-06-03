from bpy.types import Panel

from .data import BUILDING_TYPE_ORDER, building_type_spec


def draw_building_panel(layout, context):
    settings = context.scene.bgcp_settings

    create_box = layout.box()
    create_box.label(text="Create Building")
    col = create_box.column(align=True)
    for identifier in BUILDING_TYPE_ORDER:
        spec = building_type_spec(identifier)
        op = col.operator("bgcp.generate_building", icon='MESH_CUBE', text=f"Create {spec.label}")
        op.building_type = spec.identifier
    row = create_box.row(align=True)
    row.operator("bgcp.rebuild_building", icon='FILE_REFRESH')
    row.operator("bgcp.clear_buildings", icon='TRASH', text="")

    size_box = layout.box()
    size_box.label(text="Creation Parameters")
    col = size_box.column(align=True)
    col.prop(settings, "building_width")
    col.prop(settings, "building_depth")
    col.prop(settings, "floors")
    col.prop(settings, "floor_height")

    roof_box = layout.box()
    roof_box.label(text="Roof")
    col = roof_box.column(align=True)
    col.prop(settings, "roof_style")
    col.prop(settings, "roof_height")
    col.prop(settings, "roof_overhang")

    hall_box = layout.box()
    hall_box.label(text="Hall Style")
    col = hall_box.column(align=True)
    col.prop(settings, "platform_height")
    col.prop(settings, "platform_margin")
    col.prop(settings, "bay_count")
    col.prop(settings, "side_bay_count")
    col.prop(settings, "column_radius")
    col.prop(settings, "column_height")
    col.prop(settings, "round_pillar_offset")
    col.prop(settings, "horizontal_beam_z_offset")
    col.prop(settings, "cross_beam_z_offset")
    col.prop(settings, "cross_beam_length")
    col.prop(settings, "main_door_height")
    col.prop(settings, "stair_width")
    col.prop(settings, "stair_steps")
    col.prop(settings, "side_stairs_enabled")
    col.prop(settings, "balustrade_enabled")
    if settings.balustrade_enabled:
        col.prop(settings, "balustrade_height")
        col.prop(settings, "balustrade_post_spacing")
    col.prop(settings, "lower_roof_height")
    col.prop(settings, "upper_platform_height")
    col.prop(settings, "upper_roof_height")
    col.prop(settings, "lower_eave_overhang")
    col.prop(settings, "upper_eave_overhang")
    col.prop(settings, "roof_curve")
    col.prop(settings, "roof_line_width")
    col.prop(settings, "roof_line_height")
    col.prop(settings, "roof_underside_thickness")
    col.prop(settings, "roof_underside_z_offset")
    col.prop(settings, "roof_tiles_enabled")
    if settings.roof_tiles_enabled:
        col.prop(settings, "roof_ying_tile_radius")
        col.prop(settings, "roof_yang_tile_radius")
        col.prop(settings, "roof_ying_tile_z_offset")
        col.prop(settings, "roof_tile_gap")
        col.prop(settings, "roof_tile_safe_distance")
        col.prop(settings, "roof_tile_thickness")
        col.prop(settings, "roof_tile_segment_length")

    openings_box = layout.box()
    openings_box.label(text="Openings")
    col = openings_box.column(align=True)
    col.prop(settings, "window_columns")
    col.prop(settings, "side_window_columns")
    col.prop(settings, "window_width")
    col.prop(settings, "window_height")
    col.prop(settings, "door_width")
    col.prop(settings, "door_height")

    materials_box = layout.box()
    materials_box.label(text="Materials")
    col = materials_box.column(align=True)
    col.prop(settings, "wall_color")
    col.prop(settings, "roof_color")
    col.prop(settings, "glass_color")
    col.prop(settings, "door_color")
    col.prop(settings, "trim_color")

    options_box = layout.box()
    options_box.label(text="Options")
    col = options_box.column(align=True)
    col.prop(settings, "collection_name")
    col.prop(settings, "use_type_defaults")
    col.prop(settings, "auto_update")
    col.prop(settings, "select_after_generate")


class BGCP_PT_panel(Panel):
    bl_label = "Building Generator"
    bl_idname = "BGCP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Building GCP'

    def draw(self, context):
        draw_building_panel(self.layout, context)


class BGCP_PT_scene_panel(Panel):
    bl_label = "Building Generator"
    bl_idname = "BGCP_PT_scene_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        draw_building_panel(self.layout, context)
