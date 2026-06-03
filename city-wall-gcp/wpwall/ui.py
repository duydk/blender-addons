from bpy.types import Panel

from .wall_builder import *


def draw_brick_controls(parent, s, label, prefix):
    box = parent.box()
    box.label(text=label)
    col = box.column(align=True)
    col.prop(s, f"{prefix}_color_a")
    col.prop(s, f"{prefix}_color_b")
    col.prop(s, f"{prefix}_color_a_percent")
    col.prop(s, f"{prefix}_mortar_color")
    col.prop(s, f"{prefix}_scale")
    col.prop(s, f"{prefix}_mortar_size")
    col.prop(s, f"{prefix}_bump_strength")
    col.prop(s, f"{prefix}_rotation")
    col.prop(s, f"{prefix}_damage_amount")
    col.prop(s, f"{prefix}_damage_scale")


def draw_material_slots(parent, s, label, slot_names):
    box = parent.box()
    box.label(text=label)
    col = box.column(align=True)
    for slot_name in slot_names:
        col.prop(s, slot_name)


def draw_wall_materials(layout, s):
    box = layout.box()
    box.label(text="Wall Materials")
    box.operator("wpwall.apply_brick_material", icon='MATERIAL', text="Apply Brick Materials")
    draw_brick_controls(box, s, "Face Brick", "brick")
    draw_brick_controls(box, s, "Top Brick", "brick_top")
    draw_material_slots(box, s, "Slots", ("wall_material", "wall_top_material"))


def draw_gate_materials(layout, s):
    box = layout.box()
    box.label(text="Gate Materials")
    box.operator("wpwall.apply_brick_material", icon='MATERIAL', text="Apply Brick Materials")
    draw_brick_controls(box, s, "Tunnel Brick", "brick_tunnel")
    if s.gate_stairs_enabled or s.gate_wall_stairs_enabled:
        draw_brick_controls(box, s, "Stair Top Brick", "brick_stair_top")
    slots = ["gate_material", "gate_top_material", "gate_tunnel_material", "gate_tunnel_top_material"]
    if s.gate_stairs_enabled or s.gate_wall_stairs_enabled:
        slots.extend(["stair_material", "stair_top_material"])
    draw_material_slots(box, s, "Slots", slots)


def draw_tower_materials(layout, s):
    box = layout.box()
    box.label(text="Tower Materials")
    box.operator("wpwall.apply_brick_material", icon='MATERIAL', text="Apply Brick Materials")
    if s.tower_wall_stairs_enabled:
        draw_brick_controls(box, s, "Stair Top Brick", "brick_stair_top")
    slots = ["tower_material", "tower_top_material"]
    if s.tower_wall_stairs_enabled:
        slots.extend(["stair_material", "stair_top_material"])
    draw_material_slots(box, s, "Slots", slots)


def draw_ground_stair_materials(layout, s):
    box = layout.box()
    box.label(text="Ground Stair Materials")
    box.operator("wpwall.apply_brick_material", icon='MATERIAL', text="Apply Brick Materials")
    draw_brick_controls(box, s, "Stair Top Brick", "brick_stair_top")
    draw_material_slots(box, s, "Slots", ("stair_material", "stair_top_material"))


def draw_main_panel(layout, context):
    s = context.scene.wp_wall_settings
    rig = active_rig_readonly(context)
    active = context.active_object
    wall_id = wall_id_from_obj(rig) if object_is_valid(rig) else None
    active_is_waypoint = object_is_valid(active) and active.get(WAYPOINT_TAG) and (wall_id is None or active.get(WALL_ID_TAG) == wall_id)
    active_is_opening = object_is_valid(active) and active.get(OPENING_TAG) and (wall_id is None or active.get(WALL_ID_TAG) == wall_id)
    active_is_gate = object_is_valid(active) and active.get(GATE_TAG) and (wall_id is None or active.get(WALL_ID_TAG) == wall_id)
    active_is_tower = object_is_valid(active) and active.get(TOWER_TAG) and (wall_id is None or active.get(WALL_ID_TAG) == wall_id)
    active_is_rig = object_is_valid(active) and active.get(RIG_TAG)
    active_is_ground_stair = object_is_valid(active) and active.get(GATE_INSTANCE_TAG) and active.name.startswith("GATE_STAIRS_") and (wall_id is None or active.get(WALL_ID_TAG) == wall_id)
    active_is_wall = object_is_valid(active) and (
        active_is_rig or active.get(WALL_OBJ_TAG) or active_is_waypoint or active_is_opening or active_is_gate or active_is_tower
    )

    toolbar = layout.column(align=True)
    toolbar.operator("wpwall.new_wall", icon='DUPLICATE')
    row = toolbar.row(align=True)
    row.operator("wpwall.build_wall", icon='MOD_BUILD')
    row.operator("wpwall.clear_all", icon='TRASH', text="")

    edit_box = layout.box()
    edit_box.label(text="Edit")
    col = edit_box.column(align=True)
    col.operator("wpwall.add_waypoint", icon='EMPTY_AXIS')
    col.operator("wpwall.add_opening", icon='SELECT_SUBTRACT')
    col.operator("wpwall.add_gate", icon='MOD_BOOLEAN')
    col.operator("wpwall.add_tower", icon='MESH_CUBE')
    row = col.row(align=True)
    row.operator("wpwall.remove_last_waypoint", icon='REMOVE')
    row.operator("wpwall.remove_selected_waypoint", icon='X', text="")
    row.operator("wpwall.remove_last_opening", icon='X', text="")
    row.operator("wpwall.remove_last_gate", icon='PANEL_CLOSE', text="")
    row.operator("wpwall.remove_last_tower", icon='TRASH', text="")
    nav = col.row(align=True)
    nav.operator("wpwall.select_prev_waypoint", icon='TRIA_LEFT', text="Prev WP")
    nav.operator("wpwall.select_next_waypoint", icon='TRIA_RIGHT', text="Next WP")

    layout.separator()
    try:
        if active_is_waypoint:
            box = layout.box()
            box.label(text=f"Waypoint: {active.name}")
            col = box.column(align=True)
            col.prop(active, "wp_wall_corner_radius")
            col.prop(active, "wp_wall_curve_steps")
            col.prop(s, "waypoint_display_size")
        elif active_is_opening:
            box = layout.box()
            box.label(text=f"Opening: {active.name}")
            col = box.column(align=True)
            if hasattr(active, "wp_wall_opening_length"):
                col.prop(active, "wp_wall_opening_length")
            else:
                col.prop(active, "wp_wall_opening_width", text="Opening Length")
            box.label(text="Drag it to update its position on the wall")
        elif active_is_ground_stair:
            box = layout.box()
            box.label(text=f"Ground Stair: {active.name}")
            col = box.column(align=True)
            col.prop(s, "gate_stairs_enabled")
            col.prop(s, "gate_stair_side")
            col.prop(s, "gate_stair_length")
            col.prop(s, "gate_stair_depth")
            col.prop(s, "gate_stair_offset")
            col.prop(s, "gate_stair_steps")
            col.prop(s, "gate_stair_top_step_width_mult")
            box.label(text="These settings affect all ground stairs on this wall")
            draw_ground_stair_materials(layout, s)
        elif active_is_gate:
            box = layout.box()
            box.label(text=f"Gate: {active.name}")
            col = box.column(align=True)
            col.prop(active, "wp_wall_gate_style")
            col.prop(active, "wp_wall_gate_base_style")
            col.prop(s, "gate_length")
            col.prop(s, "gate_height")
            col.prop(s, "gate_tunnel_width")
            col.prop(s, "gate_tunnel_height")
            col.prop(s, "gate_tunnel_thickness")
            col.prop(s, "gate_tunnel_z_offset")
            stair_col = box.column(align=True)
            stair_col.prop(s, "gate_stairs_enabled")
            if s.gate_stairs_enabled:
                stair_col.prop(s, "gate_stair_side")
                stair_col.prop(s, "gate_stair_length")
                stair_col.prop(s, "gate_stair_depth")
                stair_col.prop(s, "gate_stair_offset")
                stair_col.prop(s, "gate_stair_steps")
                stair_col.prop(s, "gate_stair_top_step_width_mult")
            wall_stair_col = box.column(align=True)
            wall_stair_col.prop(s, "gate_wall_stairs_enabled")
            if s.gate_wall_stairs_enabled:
                wall_stair_col.prop(s, "gate_wall_stair_length")
                wall_stair_col.prop(s, "gate_wall_stair_depth")
                wall_stair_col.prop(s, "gate_wall_stair_steps")
            if get_gate_base_style(active, s.gate_base_style) == 'FORTIFIED':
                base_col = box.column(align=True)
                base_col.label(text="Fortified Base")
                base_col.prop(s, "gate_tunnel_base_overhang")
                base_col.prop(s, "gate_base_width_mult")
                base_col.prop(s, "gate_base_thickness_mult")
                base_col.prop(s, "gate_base_height_mult")
                base_col.prop(s, "gate_base_bottom_width_mult")
                base_col.prop(s, "gate_base_bottom_thickness_mult")
            box.label(text="Drag it to update its position on the wall")
            draw_gate_materials(layout, s)
        elif active_is_tower:
            box = layout.box()
            box.label(text=f"Tower: {active.name}")
            col = box.column(align=True)
            col.prop(s, "tower_base_style")
            col.prop(s, "tower_length")
            if s.tower_base_style == 'FORTIFIED':
                base_col = box.column(align=True)
                base_col.label(text="Tower Base")
                base_col.prop(s, "tower_base_width_mult")
                base_col.prop(s, "tower_base_thickness_mult")
                base_col.prop(s, "tower_base_height_mult")
                base_col.prop(s, "tower_base_bottom_width_mult")
                base_col.prop(s, "tower_base_bottom_thickness_mult")
                stair_col = box.column(align=True)
                stair_col.prop(s, "tower_wall_stairs_enabled")
                if s.tower_wall_stairs_enabled:
                    if hasattr(active, "wp_wall_tower_stair_side"):
                        stair_col.prop(active, "wp_wall_tower_stair_side")
                    else:
                        stair_col.prop(s, "tower_wall_stair_side")
                    stair_col.prop(s, "tower_wall_stair_length")
                    stair_col.prop(s, "tower_wall_stair_depth")
                    stair_col.prop(s, "tower_wall_stair_steps")
            box.label(text="Drag it to update its position on the wall")
            draw_tower_materials(layout, s)
        elif active_is_wall or object_is_valid(rig):
            box = layout.box()
            box.label(text="Wall")
            col = box.column(align=True)
            col.prop(s, "wall_height")
            col.prop(s, "wall_thickness")
            col.prop(s, "parapet_height")
            col.prop(s, "parapet_width")
            col.prop(s, "crenel_height")
            col.prop(s, "crenel_width")
            col.prop(s, "crenel_top_width")
            col.prop(s, "crenel_gap")
            col.prop(s, "crenel_end_caps")
            col.prop(s, "parapet_drain_enabled")
            if s.parapet_drain_enabled:
                col.prop(s, "parapet_drain_size")
            draw_wall_materials(layout, s)
            if active_is_rig:
                gate_box = layout.box()
                gate_box.label(text="Gate Defaults")
                gcol = gate_box.column(align=True)
                gcol.prop(s, "gate_style")
                gcol.prop(s, "gate_base_style")
                gcol.prop(s, "gate_tunnel_width")
                gcol.prop(s, "gate_tunnel_height")
                gcol.prop(s, "gate_tunnel_thickness")
                gcol.prop(s, "gate_tunnel_z_offset")
                gcol.prop(s, "gate_stairs_enabled")
                if s.gate_stairs_enabled:
                    gcol.prop(s, "gate_stair_side")
                    gcol.prop(s, "gate_stair_length")
                    gcol.prop(s, "gate_stair_depth")
                    gcol.prop(s, "gate_stair_offset")
                    gcol.prop(s, "gate_stair_steps")
                    gcol.prop(s, "gate_stair_top_step_width_mult")
                gcol.prop(s, "gate_wall_stairs_enabled")
                if s.gate_wall_stairs_enabled:
                    gcol.prop(s, "gate_wall_stair_length")
                    gcol.prop(s, "gate_wall_stair_depth")
                    gcol.prop(s, "gate_wall_stair_steps")
                if s.gate_base_style == 'FORTIFIED':
                    gcol.prop(s, "gate_tunnel_base_overhang")
                    gcol.prop(s, "gate_base_width_mult")
                    gcol.prop(s, "gate_base_thickness_mult")
                    gcol.prop(s, "gate_base_height_mult")
                    gcol.prop(s, "gate_base_bottom_width_mult")
                    gcol.prop(s, "gate_base_bottom_thickness_mult")
                tower_box = layout.box()
                tower_box.label(text="Tower Defaults")
                tcol = tower_box.column(align=True)
                tcol.prop(s, "tower_base_style")
                tcol.prop(s, "tower_length")
                if s.tower_base_style == 'FORTIFIED':
                    tcol.prop(s, "tower_base_width_mult")
                    tcol.prop(s, "tower_base_thickness_mult")
                    tcol.prop(s, "tower_base_height_mult")
                    tcol.prop(s, "tower_base_bottom_width_mult")
                    tcol.prop(s, "tower_base_bottom_thickness_mult")
                    tcol.prop(s, "tower_wall_stairs_enabled")
                    if s.tower_wall_stairs_enabled:
                        tcol.prop(s, "tower_wall_stair_side")
                        tcol.prop(s, "tower_wall_stair_length")
                        tcol.prop(s, "tower_wall_stair_depth")
                        tcol.prop(s, "tower_wall_stair_steps")
        else:
            hint = layout.box()
            hint.label(text="Select a wall part to edit its settings")
    except Exception:
        layout.separator()
        layout.label(text="Some controls unavailable. Main tools still work.")


def draw_panel_safe(layout, context):
    try:
        draw_main_panel(layout, context)
    except Exception as exc:
        col = layout.column(align=True)
        col.operator("wpwall.new_wall", icon='DUPLICATE')
        col.operator("wpwall.add_waypoint", icon='EMPTY_AXIS')
        col.operator("wpwall.add_opening", icon='SELECT_SUBTRACT')
        col.operator("wpwall.add_gate", icon='MOD_BOOLEAN')
        col.operator("wpwall.add_tower", icon='MESH_CUBE')
        col.operator("wpwall.build_wall", icon='MOD_BUILD')
        layout.separator()
        layout.operator("wpwall.clear_all", icon='TRASH')
        layout.label(text="Panel recovered from a draw error")
        layout.label(text=str(exc)[:120])


class WPWALL_PT_panel(Panel):
    bl_label = "Wall PCG"
    bl_idname = "WPWALL_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Wall PCG'

    def draw(self, context):
        draw_panel_safe(self.layout, context)


class WPWALL_PT_scene_panel(Panel):
    bl_label = "Wall PCG"
    bl_idname = "WPWALL_PT_scene_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        draw_panel_safe(self.layout, context)
