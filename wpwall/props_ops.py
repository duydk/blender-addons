import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import Operator, PropertyGroup

from .wall_builder import *
class WPWallWaypointRef(PropertyGroup):
    obj: PointerProperty(name="Waypoint", type=bpy.types.Object)
    order: IntProperty(name="Order", default=0)


class WPWallSettings(PropertyGroup):
    wall_height: FloatProperty(name="Height", default=2.5, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    wall_thickness: FloatProperty(name="Wall Width", default=0.2, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    parapet_height: FloatProperty(name="Parapet Height", default=0.8, min=0.0, update=lambda self, ctx: trigger_rebuild(ctx))
    parapet_width: FloatProperty(name="Parapet Width", default=0.18, min=0.0, update=lambda self, ctx: trigger_rebuild(ctx))
    crenel_height: FloatProperty(name="Crenel Height", default=0.35, min=0.0, update=lambda self, ctx: trigger_rebuild(ctx))
    crenel_width: FloatProperty(name="Crenel Width", default=0.45, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    crenel_gap: FloatProperty(name="Crenel Gap", default=0.3, min=0.0, update=lambda self, ctx: trigger_rebuild(ctx))
    crenel_end_caps: BoolProperty(name="Crenels On Open Ends", default=False, update=lambda self, ctx: trigger_rebuild(ctx))
    closed_loop: BoolProperty(name="Closed Loop", default=False, update=lambda self, ctx: trigger_rebuild(ctx))
    auto_update: BoolProperty(name="Auto Update", default=True)
    wall_source: PointerProperty(name="Wall Source", type=bpy.types.Object, update=lambda self, ctx: trigger_rebuild(ctx))
    wall_scale: FloatProperty(name="Wall Scale", default=1.0, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    wall_z_offset: FloatProperty(name="Wall Z Offset", default=0.0, update=lambda self, ctx: trigger_rebuild(ctx))
    wall_rotation: FloatProperty(name="Wall Rotation", default=0.0, subtype='ANGLE', update=lambda self, ctx: trigger_rebuild(ctx))
    tower_source: PointerProperty(name="Tower Source", type=bpy.types.Object, update=lambda self, ctx: trigger_rebuild(ctx))
    tower_scale: FloatProperty(name="Tower Scale", default=1.0, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    tower_z_offset: FloatProperty(name="Tower Z Offset", default=0.0, update=lambda self, ctx: trigger_rebuild(ctx))
    tower_rotation: FloatProperty(name="Tower Rotation", default=0.0, subtype='ANGLE', update=lambda self, ctx: trigger_rebuild(ctx))
    gate_length: FloatProperty(name="Gate Length", default=2.0, min=0.05, update=lambda self, ctx: set_scene_gate_length(self, ctx))
    gate_height: FloatProperty(name="Gate Height", default=2.0, min=0.05, update=lambda self, ctx: set_scene_gate_height(self, ctx))
    gate_style: EnumProperty(name="Gate Style", items=gate_style_items(), default='ARCH', update=lambda self, ctx: set_scene_gate_style(self, ctx))
    gate_base_style: EnumProperty(name="Gate Base", items=gate_base_items(), default='NONE', update=lambda self, ctx: set_scene_gate_base_style(self, ctx))
    gate_tunnel_width: FloatProperty(name="Tunnel Width", default=1.0, min=0.1, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_tunnel_height: FloatProperty(name="Tunnel Height", default=0.94, min=0.1, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_tunnel_thickness: FloatProperty(name="Tunnel Thickness", default=0.14, min=0.01, max=0.45, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_tunnel_z_offset: FloatProperty(name="Tunnel Z Offset", default=0.03, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_stairs_enabled: BoolProperty(name="Gate Stairs", default=True, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_stair_side: EnumProperty(name="Stair Side", items=gate_stair_side_items(), default='INSIDE', update=lambda self, ctx: trigger_rebuild(ctx))
    gate_stair_length: FloatProperty(name="Stair Length", default=1.6, min=0.1, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_stair_height: FloatProperty(name="Stair Height", default=0.0, min=0.0, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_stair_depth: FloatProperty(name="Stair Depth", default=0.6, min=0.05, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_stair_offset: FloatProperty(name="Stair Offset", default=0.05, min=0.0, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_stair_steps: IntProperty(name="Stair Steps", default=7, min=1, max=64, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_base_width_mult: FloatProperty(name="Base Width x", default=3.0, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_base_thickness_mult: FloatProperty(name="Base Thickness x", default=3.0, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_base_height_mult: FloatProperty(name="Base Height x", default=1.2, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_base_bottom_width_mult: FloatProperty(name="Bottom Width x", default=1.2, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    gate_base_bottom_thickness_mult: FloatProperty(name="Bottom Thickness x", default=1.2, min=0.01, update=lambda self, ctx: trigger_rebuild(ctx))
    opening_length: FloatProperty(name="Opening Length", default=2.0, min=0.05, update=lambda self, ctx: set_scene_opening_length(self, ctx))
    waypoint_display_size: FloatProperty(name="Waypoint Size", default=0.5, min=0.05, update=lambda self, ctx: trigger_rebuild(ctx))
    collection_name: bpy.props.StringProperty(name="Collection", default="WP_Wall_PCG")


def trigger_rebuild(context):
    if context and context.scene:
        build_wall_mesh(context.scene, context)


def update_opening_object(self, context):
    trigger_rebuild(context)


def get_opening_length(obj, default=2.0):
    if not object_is_valid(obj):
        return default
    if hasattr(obj, "wp_wall_opening_length"):
        try:
            return max(0.05, float(obj.wp_wall_opening_length))
        except Exception:
            pass
    if hasattr(obj, "wp_wall_opening_width"):
        try:
            return max(0.05, float(obj.wp_wall_opening_width))
        except Exception:
            pass
    if "wp_wall_opening_length" in obj:
        try:
            return max(0.05, float(obj["wp_wall_opening_length"]))
        except Exception:
            pass
    return default


def set_opening_length(obj, value):
    value = max(0.05, float(value))
    if hasattr(obj, "wp_wall_opening_length"):
        obj.wp_wall_opening_length = value
    if hasattr(obj, "wp_wall_opening_width"):
        obj.wp_wall_opening_width = value
    obj["wp_wall_opening_length"] = value


def set_scene_opening_length(self, context):
    active = getattr(context, "active_object", None)
    if not (object_is_valid(active) and active.get(OPENING_TAG)):
        for obj in getattr(context, "selected_objects", []):
            if object_is_valid(obj) and obj.get(OPENING_TAG):
                active = obj
                break
    if object_is_valid(active) and active.get(OPENING_TAG):
        set_opening_length(active, self.opening_length)
    trigger_rebuild(context)


def get_gate_length(obj, default=2.0):
    if not object_is_valid(obj):
        return default
    if hasattr(obj, "wp_wall_gate_length"):
        try:
            return max(0.05, float(obj.wp_wall_gate_length))
        except Exception:
            pass
    if "wp_wall_gate_length" in obj:
        try:
            return max(0.05, float(obj["wp_wall_gate_length"]))
        except Exception:
            pass
    return default


def set_gate_length(obj, value):
    value = max(0.05, float(value))
    if hasattr(obj, "wp_wall_gate_length"):
        obj.wp_wall_gate_length = value
    obj["wp_wall_gate_length"] = value


def update_gate_object(self, context):
    trigger_rebuild(context)


def set_scene_gate_length(self, context):
    rig = active_rig(context) if context else None
    gates = sorted_gates(context.scene, rig) if context and context.scene else []
    if gates:
        for gate in gates:
            if object_is_valid(gate):
                set_gate_length(gate, self.gate_length)
    else:
        active = getattr(context, "active_object", None)
        if not (object_is_valid(active) and active.get(GATE_TAG)):
            for obj in getattr(context, "selected_objects", []):
                if object_is_valid(obj) and obj.get(GATE_TAG):
                    active = obj
                    break
        if object_is_valid(active) and active.get(GATE_TAG):
            set_gate_length(active, self.gate_length)
    trigger_rebuild(context)


def get_gate_height(obj, default=2.0):
    if not object_is_valid(obj):
        return default
    if hasattr(obj, "wp_wall_gate_height"):
        try:
            return max(0.05, float(obj.wp_wall_gate_height))
        except Exception:
            pass
    if "wp_wall_gate_height" in obj:
        try:
            return max(0.05, float(obj["wp_wall_gate_height"]))
        except Exception:
            pass
    return default


def set_gate_height(obj, value):
    value = max(0.05, float(value))
    if hasattr(obj, "wp_wall_gate_height"):
        obj.wp_wall_gate_height = value
    obj["wp_wall_gate_height"] = value


def update_gate_height_object(self, context):
    trigger_rebuild(context)


def set_scene_gate_height(self, context):
    rig = active_rig(context) if context else None
    gates = sorted_gates(context.scene, rig) if context and context.scene else []
    if gates:
        for gate in gates:
            if object_is_valid(gate):
                set_gate_height(gate, self.gate_height)
    else:
        active = getattr(context, "active_object", None)
        if not (object_is_valid(active) and active.get(GATE_TAG)):
            for obj in getattr(context, "selected_objects", []):
                if object_is_valid(obj) and obj.get(GATE_TAG):
                    active = obj
                    break
        if object_is_valid(active) and active.get(GATE_TAG):
            set_gate_height(active, self.gate_height)
    trigger_rebuild(context)


def update_gate_style_object(self, context):
    trigger_rebuild(context)


def set_scene_gate_style(self, context):
    rig = active_rig(context) if context else None
    gates = sorted_gates(context.scene, rig) if context and context.scene else []
    if gates:
        for gate in gates:
            if object_is_valid(gate):
                set_gate_style(gate, self.gate_style)
    else:
        active = getattr(context, "active_object", None)
        if not (object_is_valid(active) and active.get(GATE_TAG)):
            for obj in getattr(context, "selected_objects", []):
                if object_is_valid(obj) and obj.get(GATE_TAG):
                    active = obj
                    break
        if object_is_valid(active) and active.get(GATE_TAG):
            set_gate_style(active, self.gate_style)
    trigger_rebuild(context)


def update_gate_base_style_object(self, context):
    trigger_rebuild(context)


def set_scene_gate_base_style(self, context):
    rig = active_rig(context) if context else None
    gates = sorted_gates(context.scene, rig) if context and context.scene else []
    if gates:
        for gate in gates:
            if object_is_valid(gate):
                set_gate_base_style(gate, self.gate_base_style)
    else:
        active = getattr(context, "active_object", None)
        if not (object_is_valid(active) and active.get(GATE_TAG)):
            for obj in getattr(context, "selected_objects", []):
                if object_is_valid(obj) and obj.get(GATE_TAG):
                    active = obj
                    break
        if object_is_valid(active) and active.get(GATE_TAG):
            set_gate_base_style(active, self.gate_base_style)
    trigger_rebuild(context)


class WPWALL_OT_select_prev_waypoint(Operator):
    bl_idname = "wpwall.select_prev_waypoint"
    bl_label = "Select Prev Waypoint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        rig = active_rig(context)
        wps = sorted_waypoints(context.scene, rig)
        if not wps:
            self.report({'WARNING'}, "No waypoints")
            return {'CANCELLED'}
        active = context.active_object
        idx = 0
        if object_is_valid(active) and active in wps:
            idx = max(0, wps.index(active) - 1)
        target = wps[idx]
        for obj in list(context.selected_objects):
            obj.select_set(False)
        target.select_set(True)
        context.view_layer.objects.active = target
        return {'FINISHED'}


class WPWALL_OT_select_next_waypoint(Operator):
    bl_idname = "wpwall.select_next_waypoint"
    bl_label = "Select Next Waypoint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        rig = active_rig(context)
        wps = sorted_waypoints(context.scene, rig)
        if not wps:
            self.report({'WARNING'}, "No waypoints")
            return {'CANCELLED'}
        active = context.active_object
        idx = 0
        if object_is_valid(active) and active in wps:
            idx = min(len(wps) - 1, wps.index(active) + 1)
        target = wps[idx]
        for obj in list(context.selected_objects):
            obj.select_set(False)
        target.select_set(True)
        context.view_layer.objects.active = target
        return {'FINISHED'}


class WPWALL_OT_new_wall(Operator):
    bl_idname = "wpwall.new_wall"
    bl_label = "New Wall"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        rig = create_wall_rig(context)
        self.report({'INFO'}, f"Active wall: {rig.name}")
        return {'FINISHED'}


class WPWALL_OT_add_waypoint(Operator):
    bl_idname = "wpwall.add_waypoint"
    bl_label = "Add Waypoint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        rig = ensure_rig_object(context)
        wall = ensure_wall_object(context)
        coll = ensure_collection(context)
        wall_id = wall_id_from_obj(rig)
        waypoints = sorted_waypoints(scene, rig)

        location = context.scene.cursor.location.copy()
        insert_order = next_waypoint_index(scene, rig)
        active = context.active_object

        if object_is_valid(active) and active.get(WAYPOINT_TAG) and active.get(WALL_ID_TAG) == wall_id:
            location = active.matrix_world.translation.copy() + Vector((2.0, 0.0, 0.0))
            selected_ref = None
            for ref in scene.wp_wall_waypoints:
                if ref.obj == active:
                    selected_ref = ref
                    break
            if selected_ref is not None:
                insert_order = selected_ref.order + 1
                for ref in scene.wp_wall_waypoints:
                    if object_is_valid(ref.obj) and ref.obj.get(WALL_ID_TAG) == wall_id and ref.order >= insert_order:
                        ref.order += 1
        elif waypoints:
            location = waypoints[-1].matrix_world.translation.copy() + Vector((2.0, 0.0, 0.0))

        bpy.ops.object.empty_add(type='SPHERE', radius=0.2, align='WORLD', location=location)
        obj = context.active_object
        obj.name = f"WP_{wall_id:03d}_{next_waypoint_index(scene, rig):03d}"
        obj.empty_display_size = scene.wp_wall_settings.waypoint_display_size
        obj[WAYPOINT_TAG] = True
        obj[ADDON_TAG] = True
        obj[WALL_ID_TAG] = wall_id
        obj.show_name = True
        obj.show_in_front = True
        obj.wp_wall_corner_radius = 0.0
        obj.wp_wall_curve_steps = 6
        obj.wp_wall_tower_x_offset = 0.0
        obj.wp_wall_tower_y_offset = 0.0
        obj.wp_wall_tower_z_offset = 0.0
        obj.wp_wall_tower_rotation = 0.0

        if obj.name not in coll.objects:
            coll.objects.link(obj)
            if obj.name in context.scene.collection.objects:
                context.scene.collection.objects.unlink(obj)

        parent_keep_transform(obj, wall)
        ref = scene.wp_wall_waypoints.add()
        ref.obj = obj
        ref.order = insert_order
        refresh_waypoint_orders(scene, rig)
        build_wall_mesh(scene, context)
        return {'FINISHED'}


class WPWALL_OT_add_opening(Operator):
    bl_idname = "wpwall.add_opening"
    bl_label = "Add Opening"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        rig = ensure_rig_object(context)
        wall = ensure_wall_object(context)
        coll = ensure_collection(context)
        wall_id = wall_id_from_obj(rig)
        waypoints = sorted_waypoints(scene, rig)
        location = context.scene.cursor.location.copy()
        active = context.active_object

        if object_is_valid(active) and active.get(WAYPOINT_TAG) and active.get(WALL_ID_TAG) == wall_id:
            location = active.matrix_world.translation.copy()
        elif len(waypoints) >= 2:
            location = (waypoints[0].matrix_world.translation + waypoints[1].matrix_world.translation) * 0.5

        mesh = bpy.data.meshes.new(f"OPENING_{wall_id:03d}_mesh")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new(f"OPENING_{wall_id:03d}_{len(sorted_openings(scene, rig)):03d}", mesh)
        obj[ADDON_TAG] = True
        obj[OPENING_TAG] = True
        obj[WALL_ID_TAG] = wall_id
        obj.display_type = 'WIRE'
        obj.show_in_front = True
        obj.show_name = True
        obj.hide_render = True
        obj.location = location
        set_opening_length(obj, scene.wp_wall_settings.opening_length)
        coll.objects.link(obj)
        parent_keep_transform(obj, wall)

        for item in list(context.selected_objects):
            if object_is_valid(item):
                item.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        build_wall_mesh(scene, context)
        return {'FINISHED'}


class WPWALL_OT_add_gate(Operator):
    bl_idname = "wpwall.add_gate"
    bl_label = "Add Gate"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        rig = ensure_rig_object(context)
        wall = ensure_wall_object(context)
        coll = ensure_collection(context)
        wall_id = wall_id_from_obj(rig)
        waypoints = sorted_waypoints(scene, rig)
        location = context.scene.cursor.location.copy()
        active = context.active_object

        if object_is_valid(active) and active.get(WAYPOINT_TAG) and active.get(WALL_ID_TAG) == wall_id:
            location = active.matrix_world.translation.copy()
        elif len(waypoints) >= 2:
            location = (waypoints[0].matrix_world.translation + waypoints[1].matrix_world.translation) * 0.5

        mesh = bpy.data.meshes.new(f"GATE_{wall_id:03d}_mesh")
        obj = bpy.data.objects.new(f"GATE_{wall_id:03d}_{len(sorted_gates(scene, rig)):03d}", mesh)
        obj[ADDON_TAG] = True
        obj[GATE_TAG] = True
        obj[WALL_ID_TAG] = wall_id
        obj.display_type = 'WIRE'
        obj.show_in_front = True
        obj.show_name = True
        obj.hide_render = True
        obj.location = location
        set_gate_length(obj, scene.wp_wall_settings.gate_length)
        set_gate_height(obj, scene.wp_wall_settings.gate_height)
        set_gate_style(obj, scene.wp_wall_settings.gate_style)
        set_gate_base_style(obj, scene.wp_wall_settings.gate_base_style)
        rebuild_gate_cutter_mesh(obj)
        coll.objects.link(obj)
        parent_keep_transform(obj, wall)

        for item in list(context.selected_objects):
            if object_is_valid(item):
                item.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        build_wall_mesh(scene, context)
        return {'FINISHED'}


class WPWALL_OT_remove_last_gate(Operator):
    bl_idname = "wpwall.remove_last_gate"
    bl_label = "Remove Last Gate"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        rig = active_rig(context)
        gates = sorted_gates(scene, rig)
        if not gates:
            self.report({'WARNING'}, "No gate to remove")
            return {'CANCELLED'}
        obj = gates[-1]
        bpy.data.objects.remove(obj, do_unlink=True)
        build_wall_mesh(scene, context)
        return {'FINISHED'}


class WPWALL_OT_remove_last_opening(Operator):
    bl_idname = "wpwall.remove_last_opening"
    bl_label = "Remove Last Opening"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        rig = active_rig(context)
        openings = sorted_openings(scene, rig)
        if not openings:
            self.report({'WARNING'}, "No opening to remove")
            return {'CANCELLED'}
        obj = openings[-1]
        bpy.data.objects.remove(obj, do_unlink=True)
        build_wall_mesh(scene, context)
        return {'FINISHED'}


class WPWALL_OT_remove_last_waypoint(Operator):
    bl_idname = "wpwall.remove_last_waypoint"
    bl_label = "Remove Last Waypoint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        rig = active_rig(context)
        wps = sorted_waypoints(scene, rig)
        if not wps:
            self.report({'WARNING'}, "No waypoint to remove")
            return {'CANCELLED'}
        obj = wps[-1]
        for idx, ref in enumerate(scene.wp_wall_waypoints):
            if ref.obj == obj:
                scene.wp_wall_waypoints.remove(idx)
                break
        if object_is_valid(obj):
            bpy.data.objects.remove(obj, do_unlink=True)
        refresh_waypoint_orders(scene, rig)
        build_wall_mesh(scene, context)
        return {'FINISHED'}


class WPWALL_OT_build_wall(Operator):
    bl_idname = "wpwall.build_wall"
    bl_label = "Rebuild Wall"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        build_wall_mesh(context.scene, context)
        self.report({'INFO'}, "Wall rebuilt")
        return {'FINISHED'}


class WPWALL_OT_clear_all(Operator):
    bl_idname = "wpwall.clear_all"
    bl_label = "Clear Waypoints + Wall"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        for obj in list(bpy.data.objects):
            if obj.get(ADDON_TAG):
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0 and mesh.name.startswith("Generated_Wall_"):
                bpy.data.meshes.remove(mesh)
        scene.wp_wall_waypoints.clear()
        scene.wp_wall_active_rig = None
        self.report({'INFO'}, "Cleared wall setup")
        return {'FINISHED'}
