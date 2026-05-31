from . import engine_common as _engine_common

# Preserve access to internal helper symbols (including underscore-prefixed ones)
# after splitting modules.
for _name in dir(_engine_common):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_engine_common, _name)

def rebuild_wall_instances(scene, context, rig, wall_obj, local_points):
    clear_wall_instances(rig)
    s = settings(scene)
    source = s.wall_source
    created_count = 0
    if not object_is_valid(source) or len(local_points) < 2:
        return created_count

    wall_id = wall_id_from_obj(rig)
    _src_loc, src_rot, src_scale = source.matrix_world.decompose()
    src_rot_m = src_rot.to_matrix().to_4x4()
    closed = bool(s.closed_loop and len(local_points) > 2)
    seg_count = len(local_points) if closed else len(local_points) - 1
    base_len = max(abs(source.dimensions.x), 1e-4)
    opening_boxes = cutter_world_aabbs(scene, rig)

    for i in range(seg_count):
        j = (i + 1) % len(local_points)
        a = local_points[i]
        b = local_points[j]
        seg = b - a
        seg_len = seg.length
        if seg_len <= 1e-8:
            continue
        tangent = _safe_dir_2d(a, b)
        if tangent is None:
            continue
        repeat_count = max(1, int((seg_len / max(base_len * s.wall_scale, 1e-4)) + 0.9999))
        spacing = seg_len / repeat_count
        for k in range(repeat_count):
            t = (k + 0.5) / repeat_count
            mid = a.lerp(b, t)
            instance = source.copy()
            if source.data:
                instance.data = source.data
            instance.animation_data_clear()
            instance.name = f"WALL_SEG_{wall_id:03d}_{i:03d}_{k:03d}"
            instance[ADDON_TAG] = True
            instance[WALL_INSTANCE_TAG] = True
            instance[WALL_ID_TAG] = wall_id
            instance.display_type = source.display_type
            instance.hide_render = source.hide_render
            instance.hide_viewport = False
            instance.hide_set(False)
            instance.show_bounds = source.show_bounds
            instance.display_bounds_type = source.display_bounds_type
            ensure_collection(context).objects.link(instance)
            placement = (
                Matrix.Translation((wall_obj.matrix_world @ mid) + Vector((0.0, 0.0, s.wall_z_offset)))
                @ Matrix.Rotation(tangent.to_2d().angle_signed(Vector((1.0, 0.0))) + s.wall_rotation, 4, 'Z')
                @ src_rot_m
                @ Matrix.Diagonal((
                    src_scale.x * (spacing / base_len) * s.wall_scale,
                    src_scale.y * s.wall_scale,
                    src_scale.z * s.wall_scale,
                    1.0,
                ))
            )
            cand_min, cand_max = _aabb_from_points(_bbox_world_corners(source, placement))
            if any(_aabb_overlap(cand_min, cand_max, box_min, box_max) for box_min, box_max in opening_boxes):
                bpy.data.objects.remove(instance, do_unlink=True)
                continue
            instance.matrix_world = placement
            parent_keep_transform(instance, wall_obj)
            created_count += 1
    return created_count


def rebuild_gate_instances(scene, context, rig, wall_obj):
    clear_gate_instances(rig)
    s = settings(scene)
    wall_id = wall_id_from_obj(rig)
    inv = wall_obj.matrix_world.inverted_safe()

    gates = sorted_gates(scene, rig)
    if not gates:
        return

    for idx, gate in enumerate(gates):
        if not object_is_valid(gate):
            continue
        if get_gate_base_style(gate, s.gate_base_style) != 'FORTIFIED':
            continue

        gate_length = max(0.05, get_gate_length(gate, s.gate_length))
        base_width = max(0.05, gate_length * max(0.01, s.gate_base_width_mult))
        base_thickness = max(0.05, s.wall_thickness * max(0.01, s.gate_base_thickness_mult))
        base_height = max(0.05, s.wall_height * max(0.01, s.gate_base_height_mult))
        bottom_width = max(0.05, base_width * max(0.01, s.gate_base_bottom_width_mult))
        bottom_thickness = max(0.05, base_thickness * max(0.01, s.gate_base_bottom_thickness_mult))

        local_gate_m = inv @ gate.matrix_world
        local_gate_pos = local_gate_m.translation.copy()
        local_yaw = local_gate_m.to_euler('XYZ').z

        mesh = bpy.data.meshes.new(f"GATE_BASE_{wall_id:03d}_{idx:03d}_mesh")
        bm = bmesh.new()
        tw = base_width * 0.5
        tt = base_thickness * 0.5
        bw = bottom_width * 0.5
        bt = bottom_thickness * 0.5
        h = base_height
        parapet_h = max(0.0, s.parapet_height)
        parapet_w = max(0.0, s.parapet_width)
        crenel_h = max(0.0, s.crenel_height)
        crenel_w = max(0.0, s.crenel_width)
        crenel_g = max(0.0, s.crenel_gap)

        def add_prism(x0, x1, y0, y1, z0, z1):
            verts = [
                bm.verts.new((x0, y0, z0)),
                bm.verts.new((x1, y0, z0)),
                bm.verts.new((x1, y1, z0)),
                bm.verts.new((x0, y1, z0)),
                bm.verts.new((x0, y0, z1)),
                bm.verts.new((x1, y0, z1)),
                bm.verts.new((x1, y1, z1)),
                bm.verts.new((x0, y1, z1)),
            ]
            for face in (
                (verts[0], verts[1], verts[2], verts[3]),
                (verts[4], verts[7], verts[6], verts[5]),
                (verts[0], verts[4], verts[5], verts[1]),
                (verts[1], verts[5], verts[6], verts[2]),
                (verts[2], verts[6], verts[7], verts[3]),
                (verts[3], verts[7], verts[4], verts[0]),
            ):
                try:
                    bm.faces.new(face)
                except ValueError:
                    pass

        v0 = bm.verts.new((-bw, -bt, 0.0))
        v1 = bm.verts.new((bw, -bt, 0.0))
        v2 = bm.verts.new((bw, bt, 0.0))
        v3 = bm.verts.new((-bw, bt, 0.0))
        v4 = bm.verts.new((-tw, -tt, h))
        v5 = bm.verts.new((tw, -tt, h))
        v6 = bm.verts.new((tw, tt, h))
        v7 = bm.verts.new((-tw, tt, h))
        for face in (
            (v0, v1, v2, v3),
            (v4, v7, v6, v5),
            (v0, v4, v5, v1),
            (v1, v5, v6, v2),
            (v2, v6, v7, v3),
            (v3, v7, v4, v0),
        ):
            try:
                bm.faces.new(face)
            except ValueError:
                pass

        # Add parapets and crenels on top of fortified base using existing wall settings.
        if parapet_h > 1e-6 and parapet_w > 1e-6 and tt > parapet_w:
            # Front and back parapet rails.
            add_prism(-tw, tw, -tt, -tt + parapet_w, h, h + parapet_h)
            add_prism(-tw, tw, tt - parapet_w, tt, h, h + parapet_h)
            # Left and right parapet rails.
            add_prism(-tw, -tw + parapet_w, -tt, tt, h, h + parapet_h)
            add_prism(tw - parapet_w, tw, -tt, tt, h, h + parapet_h)

            # Crenels: small raised blocks with configurable width/gap along each rail.
            if crenel_h > 1e-6 and crenel_w > 1e-6:
                step = crenel_w + crenel_g
                if step > 1e-6:
                    # Front/back rails (vary along X).
                    rail_len_x = tw * 2.0
                    offset_x = 0.0
                    while offset_x + crenel_w <= rail_len_x + 1e-6:
                        x0 = -tw + offset_x
                        x1 = min(tw, x0 + crenel_w)
                        add_prism(x0, x1, -tt, -tt + parapet_w, h + parapet_h, h + parapet_h + crenel_h)
                        add_prism(x0, x1, tt - parapet_w, tt, h + parapet_h, h + parapet_h + crenel_h)
                        offset_x += step

                    # Left/right rails (vary along Y).
                    rail_len_y = tt * 2.0
                    offset_y = 0.0
                    while offset_y + crenel_w <= rail_len_y + 1e-6:
                        y0 = -tt + offset_y
                        y1 = min(tt, y0 + crenel_w)
                        add_prism(-tw, -tw + parapet_w, y0, y1, h + parapet_h, h + parapet_h + crenel_h)
                        add_prism(tw - parapet_w, tw, y0, y1, h + parapet_h, h + parapet_h + crenel_h)
                        offset_y += step
        bm.to_mesh(mesh)
        bm.free()

        instance = bpy.data.objects.new(f"GATE_BASE_{wall_id:03d}_{idx:03d}", mesh)
        instance[ADDON_TAG] = True
        instance[GATE_INSTANCE_TAG] = True
        instance[WALL_ID_TAG] = wall_id
        instance.hide_render = False
        instance.hide_set(False)
        ensure_collection(context).objects.link(instance)

        placement_local = (
            Matrix.Translation(Vector((local_gate_pos.x, local_gate_pos.y, 0.0)))
            @ Matrix.Rotation(local_yaw, 4, 'Z')
        )
        instance.matrix_world = wall_obj.matrix_world @ placement_local
        parent_keep_transform(instance, wall_obj)

        # Cut the fortified base using the same gate cutter shape so the opening passes through.
        bool_mod = instance.modifiers.new(name="WP_GateBaseCut", type='BOOLEAN')
        bool_mod.operation = 'DIFFERENCE'
        bool_mod.solver = 'EXACT'
        bool_mod.object = gate


def rebuild_tower_instances(scene, context, rig, wall_obj, waypoint_objs, local_points):
    clear_tower_instances(rig)
    s = settings(scene)
    source = s.tower_source
    if not object_is_valid(source) or len(local_points) < 1:
        return

    wall_id = wall_id_from_obj(rig)
    _src_loc, src_rot, src_scale = source.matrix_world.decompose()
    src_rot_m = src_rot.to_matrix().to_4x4()
    closed = bool(s.closed_loop and len(local_points) > 2)

    for idx, (point, tangent) in enumerate(tower_points_with_tangent(local_points, closed)):
        waypoint_obj = waypoint_objs[idx] if idx < len(waypoint_objs) else None
        local_x_offset = 0.0
        local_y_offset = 0.0
        local_z_offset = 0.0
        local_rotation = 0.0
        if object_is_valid(waypoint_obj):
            local_x_offset = float(getattr(waypoint_obj, "wp_wall_tower_x_offset", 0.0))
            local_y_offset = float(getattr(waypoint_obj, "wp_wall_tower_y_offset", 0.0))
            local_z_offset = float(getattr(waypoint_obj, "wp_wall_tower_z_offset", 0.0))
            local_rotation = float(getattr(waypoint_obj, "wp_wall_tower_rotation", 0.0))
        local_offset = Vector((local_x_offset, local_y_offset, local_z_offset))
        instance = source.copy()
        if source.data:
            instance.data = source.data
        instance.animation_data_clear()
        instance.name = f"TOWER_{wall_id:03d}_{idx:03d}"
        instance[ADDON_TAG] = True
        instance[TOWER_INSTANCE_TAG] = True
        instance[WALL_ID_TAG] = wall_id
        instance.display_type = source.display_type
        instance.hide_render = source.hide_render
        instance.hide_viewport = False
        instance.hide_set(False)
        instance.show_bounds = source.show_bounds
        instance.display_bounds_type = source.display_bounds_type
        ensure_collection(context).objects.link(instance)
        placement = (
            Matrix.Translation((wall_obj.matrix_world @ point))
            @ Matrix.Rotation(tangent.to_2d().angle_signed(Vector((1.0, 0.0))), 4, 'Z')
            @ Matrix.Translation(Vector((local_offset.x, local_offset.y, s.tower_z_offset + local_offset.z)))
            @ Matrix.Rotation(s.tower_rotation + local_rotation, 4, 'Z')
            @ src_rot_m
            @ Matrix.Diagonal((
                src_scale.x * s.tower_scale,
                src_scale.y * s.tower_scale,
                src_scale.z * s.tower_scale,
                1.0,
            ))
        )
        instance.matrix_world = placement
        parent_keep_transform(instance, wall_obj)
