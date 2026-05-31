from . import engine_common as _engine_common
from . import engine_instances as _engine_instances

# Preserve access to internal helper symbols (including underscore-prefixed ones)
# after splitting modules.
for _name in dir(_engine_common):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_engine_common, _name)

for _name in dir(_engine_instances):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_engine_instances, _name)

# Compatibility aliases for any stale call sites (e.g., cached bytecode/module reloads)
# that still reference private helpers by local name.
_safe_dir_2d = _engine_common._safe_dir_2d
_miter_offset_point = _engine_common._miter_offset_point
_clamp = _engine_common._clamp
_segment_line_intersection_point_2d = _engine_common._segment_line_intersection_point_2d
_turn_sign_2d = _engine_common._turn_sign_2d

def build_wall_mesh(scene, context=None):
    s = settings(scene)
    ctx = context if context is not None else bpy.context
    if not ctx or getattr(ctx, "scene", None) != scene:
        return
    rig = active_rig(ctx)
    if rig is None:
        return
    wps = sorted_waypoints(scene, rig)
    wall_obj = wall_object(scene, rig)
    if not wall_obj and context is not None:
        wall_obj = ensure_wall_object(context)
    if not wall_obj:
        return

    mesh = wall_obj.data
    bm = bmesh.new()
    raw_waypoints, points = sampled_wall_points(scene, rig, wall_obj)

    if len(points) >= 2:

        n = len(points)
        closed = bool(s.closed_loop and n > 2)
        half = s.wall_thickness * 0.5
        plus = []
        minus = []

        for i, p in enumerate(points):
            if closed:
                prev_p = points[(i - 1) % n]
                next_p = points[(i + 1) % n]
                plus.append(_engine_common._miter_offset_point(prev_p, p, next_p, half, +1.0))
                minus.append(_engine_common._miter_offset_point(prev_p, p, next_p, half, -1.0))
                continue

            if i == 0:
                d = _engine_common._safe_dir_2d(points[0], points[1])
                if d is None:
                    continue
                nrm = Vector((-d.y, d.x, 0.0))
                plus.append(p + nrm * half)
                minus.append(p - nrm * half)
            elif i == n - 1:
                d = _engine_common._safe_dir_2d(points[n - 2], points[n - 1])
                if d is None:
                    continue
                nrm = Vector((-d.y, d.x, 0.0))
                plus.append(p + nrm * half)
                minus.append(p - nrm * half)
            else:
                prev_p = points[i - 1]
                next_p = points[i + 1]
                plus.append(_engine_common._miter_offset_point(prev_p, p, next_p, half, +1.0))
                minus.append(_engine_common._miter_offset_point(prev_p, p, next_p, half, -1.0))

        if len(plus) == n and len(minus) == n:
            plus_b = [bm.verts.new(v) for v in plus]
            minus_b = [bm.verts.new(v) for v in minus]
            plus_t = [bm.verts.new(v + Vector((0.0, 0.0, s.wall_height))) for v in plus]
            minus_t = [bm.verts.new(v + Vector((0.0, 0.0, s.wall_height))) for v in minus]
            use_parapets = s.parapet_height > 1e-6 and s.parapet_width > 1e-6 and s.wall_thickness > 1e-6
            parapet_ratio = _engine_common._clamp(s.parapet_width / max(s.wall_thickness, 1e-6), 0.0, 0.49) if use_parapets else 0.0
            plus_inner_t = []
            minus_inner_t = []
            plus_cap_t = []
            minus_cap_t = []
            plus_inner_cap_t = []
            minus_inner_cap_t = []

            if use_parapets:
                for i in range(n):
                    left_inner = plus[i].lerp(minus[i], parapet_ratio) + Vector((0.0, 0.0, s.wall_height))
                    right_inner = minus[i].lerp(plus[i], parapet_ratio) + Vector((0.0, 0.0, s.wall_height))
                    plus_inner_t.append(bm.verts.new(left_inner))
                    minus_inner_t.append(bm.verts.new(right_inner))
                    plus_cap_t.append(bm.verts.new(plus[i] + Vector((0.0, 0.0, s.wall_height + s.parapet_height))))
                    minus_cap_t.append(bm.verts.new(minus[i] + Vector((0.0, 0.0, s.wall_height + s.parapet_height))))
                    plus_inner_cap_t.append(bm.verts.new(left_inner + Vector((0.0, 0.0, s.parapet_height))))
                    minus_inner_cap_t.append(bm.verts.new(right_inner + Vector((0.0, 0.0, s.parapet_height))))
            edge_count = n if closed else n - 1

            for i in range(edge_count):
                j = (i + 1) % n
                turn_sign = 0.0
                k = None
                if closed or j < n - 1:
                    k = (j + 1) % n
                    turn_sign = _engine_common._turn_sign_2d(points[i], points[j], points[k])
                faces = [[plus_b[i], plus_b[j], minus_b[j], minus_b[i]]]
                if use_parapets:
                    if k is not None and abs(turn_sign) > 1e-8:
                        if turn_sign > 0.0:
                            walk_cut = _engine_common._segment_line_intersection_point_2d(
                                minus_inner_t[i].co, minus_inner_t[j].co,
                                plus_inner_t[j].co, plus_inner_t[k].co,
                            )
                            if walk_cut is not None:
                                walk_cut_v = bm.verts.new(walk_cut)
                                faces.extend([
                                    [plus_inner_t[i], plus_inner_t[j], walk_cut_v, minus_inner_t[i]],
                                    [plus_inner_t[j], minus_inner_t[j], walk_cut_v],
                                    [minus_inner_t[i], walk_cut_v, minus_inner_t[j]],
                                ])
                            else:
                                faces.extend([[plus_inner_t[j], plus_inner_t[i], minus_inner_t[i], minus_inner_t[j]]])
                        else:
                            walk_cut = _engine_common._segment_line_intersection_point_2d(
                                plus_inner_t[i].co, plus_inner_t[j].co,
                                minus_inner_t[j].co, minus_inner_t[k].co,
                            )
                            if walk_cut is not None:
                                walk_cut_v = bm.verts.new(walk_cut)
                                faces.extend([
                                    [plus_inner_t[i], minus_inner_t[i], minus_inner_t[j], walk_cut_v],
                                    [plus_inner_t[i], walk_cut_v, plus_inner_t[j]],
                                    [plus_inner_t[j], walk_cut_v, minus_inner_t[j]],
                                ])
                            else:
                                faces.extend([[plus_inner_t[j], plus_inner_t[i], minus_inner_t[i], minus_inner_t[j]]])
                    else:
                        faces.extend([[plus_inner_t[j], plus_inner_t[i], minus_inner_t[i], minus_inner_t[j]]])
                    faces.extend([
                        [plus_b[i], plus_t[i], plus_t[j], plus_b[j]],
                        [minus_b[j], minus_t[j], minus_t[i], minus_b[i]],
                        [plus_t[i], plus_t[j], plus_cap_t[j], plus_cap_t[i]],
                        [plus_inner_t[j], plus_inner_t[i], plus_inner_cap_t[i], plus_inner_cap_t[j]],
                        [plus_cap_t[i], plus_cap_t[j], plus_inner_cap_t[j], plus_inner_cap_t[i]],
                        [minus_t[j], minus_t[i], minus_cap_t[i], minus_cap_t[j]],
                        [minus_inner_t[i], minus_inner_t[j], minus_inner_cap_t[j], minus_inner_cap_t[i]],
                        [minus_inner_cap_t[i], minus_inner_cap_t[j], minus_cap_t[j], minus_cap_t[i]],
                    ])
                else:
                    if k is not None and abs(turn_sign) > 1e-8:
                        if turn_sign > 0.0:
                            top_cut = _engine_common._segment_line_intersection_point_2d(
                                minus_t[i].co, minus_t[j].co,
                                plus_t[j].co, plus_t[k].co,
                            )
                            if top_cut is not None:
                                top_cut_v = bm.verts.new(top_cut)
                                faces.extend([
                                    [plus_t[i], plus_t[j], top_cut_v, minus_t[i]],
                                    [plus_t[j], minus_t[j], top_cut_v],
                                    [minus_t[i], top_cut_v, minus_t[j]],
                                ])
                            else:
                                faces.extend([[plus_t[j], plus_t[i], minus_t[i], minus_t[j]]])
                        else:
                            top_cut = _engine_common._segment_line_intersection_point_2d(
                                plus_t[i].co, plus_t[j].co,
                                minus_t[j].co, minus_t[k].co,
                            )
                            if top_cut is not None:
                                top_cut_v = bm.verts.new(top_cut)
                                faces.extend([
                                    [plus_t[i], minus_t[i], minus_t[j], top_cut_v],
                                    [plus_t[i], top_cut_v, plus_t[j]],
                                    [plus_t[j], top_cut_v, minus_t[j]],
                                ])
                            else:
                                faces.extend([[plus_t[j], plus_t[i], minus_t[i], minus_t[j]]])
                    else:
                        faces.extend([[plus_t[j], plus_t[i], minus_t[i], minus_t[j]]])
                    faces.extend([
                        [plus_b[i], plus_t[i], plus_t[j], plus_b[j]],
                        [minus_b[j], minus_t[j], minus_t[i], minus_b[i]],
                    ])
                for face in faces:
                    try:
                        bm.faces.new(face)
                    except ValueError:
                        pass

            if not closed:
                end_caps = [
                    [plus_b[0], minus_b[0], minus_t[0], plus_t[0]],
                    [minus_b[-1], plus_b[-1], plus_t[-1], minus_t[-1]],
                ]
                if use_parapets:
                    end_caps.extend([
                        [plus_t[0], plus_cap_t[0], plus_inner_cap_t[0], plus_inner_t[0]],
                        [minus_inner_t[0], minus_inner_cap_t[0], minus_cap_t[0], minus_t[0]],
                        [plus_t[-1], plus_inner_t[-1], plus_inner_cap_t[-1], plus_cap_t[-1]],
                        [minus_inner_t[-1], minus_t[-1], minus_cap_t[-1], minus_inner_cap_t[-1]],
                    ])
                    start_dir = _engine_common._safe_dir_2d(points[0], points[1])
                    end_dir = _engine_common._safe_dir_2d(points[-2], points[-1])
                    if start_dir is not None:
                        start_in0 = plus_t[0].co.copy() + start_dir * s.parapet_width
                        start_in1 = minus_t[0].co.copy() + start_dir * s.parapet_width
                        start_in0_top = start_in0 + Vector((0.0, 0.0, s.parapet_height))
                        start_in1_top = start_in1 + Vector((0.0, 0.0, s.parapet_height))
                        sv = [bm.verts.new(v) for v in (plus_t[0].co.copy(), minus_t[0].co.copy(), start_in1, start_in0, plus_cap_t[0].co.copy(), minus_cap_t[0].co.copy(), start_in1_top, start_in0_top)]
                        end_caps.extend([
                            [sv[0], sv[1], sv[2], sv[3]],
                            [sv[4], sv[7], sv[6], sv[5]],
                            [sv[0], sv[4], sv[5], sv[1]],
                            [sv[3], sv[2], sv[6], sv[7]],
                            [sv[1], sv[5], sv[6], sv[2]],
                            [sv[0], sv[3], sv[7], sv[4]],
                        ])
                    if end_dir is not None:
                        end_in0 = minus_t[-1].co.copy() - end_dir * s.parapet_width
                        end_in1 = plus_t[-1].co.copy() - end_dir * s.parapet_width
                        end_in0_top = end_in0 + Vector((0.0, 0.0, s.parapet_height))
                        end_in1_top = end_in1 + Vector((0.0, 0.0, s.parapet_height))
                        ev = [bm.verts.new(v) for v in (minus_t[-1].co.copy(), plus_t[-1].co.copy(), end_in1, end_in0, minus_cap_t[-1].co.copy(), plus_cap_t[-1].co.copy(), end_in1_top, end_in0_top)]
                        end_caps.extend([
                            [ev[0], ev[1], ev[2], ev[3]],
                            [ev[4], ev[7], ev[6], ev[5]],
                            [ev[0], ev[4], ev[5], ev[1]],
                            [ev[3], ev[2], ev[6], ev[7]],
                            [ev[1], ev[5], ev[6], ev[2]],
                            [ev[0], ev[3], ev[7], ev[4]],
                        ])
                for face in end_caps:
                    try:
                        bm.faces.new(face)
                    except ValueError:
                        pass

            use_crenels = use_parapets and s.crenel_height > 1e-6 and s.crenel_width > 1e-6
            if use_crenels:
                step = max(1e-4, s.crenel_width + s.crenel_gap)
                for i in range(edge_count):
                    j = (i + 1) % n
                    tangent = _engine_common._safe_dir_2d(points[i], points[j])
                    if tangent is None:
                        continue
                    normal = Vector((-tangent.y, tangent.x, 0.0))
                    side_rails = [
                        (plus[i], plus[j], -normal),
                        (minus[i], minus[j], normal),
                    ]
                    for outer_a, outer_b, inward in side_rails:
                        seg_vec = outer_b - outer_a
                        seg_len = seg_vec.length
                        if seg_len <= 1e-6:
                            continue
                        offset = 0.0
                        while offset + s.crenel_width <= seg_len + 1e-6:
                            t0 = offset / seg_len
                            t1 = min(1.0, (offset + s.crenel_width) / seg_len)
                            base0 = outer_a.lerp(outer_b, t0) + Vector((0.0, 0.0, s.wall_height + s.parapet_height))
                            base1 = outer_a.lerp(outer_b, t1) + Vector((0.0, 0.0, s.wall_height + s.parapet_height))
                            inner0 = base0 + inward * s.parapet_width
                            inner1 = base1 + inward * s.parapet_width
                            top0 = base0 + Vector((0.0, 0.0, s.crenel_height))
                            top1 = base1 + Vector((0.0, 0.0, s.crenel_height))
                            inner_top0 = inner0 + Vector((0.0, 0.0, s.crenel_height))
                            inner_top1 = inner1 + Vector((0.0, 0.0, s.crenel_height))
                            verts = [bm.verts.new(v) for v in (base0, base1, inner1, inner0, top0, top1, inner_top1, inner_top0)]
                            crenel_faces = [
                                [verts[0], verts[1], verts[2], verts[3]],
                                [verts[4], verts[7], verts[6], verts[5]],
                                [verts[0], verts[4], verts[5], verts[1]],
                                [verts[3], verts[2], verts[6], verts[7]],
                                [verts[1], verts[5], verts[6], verts[2]],
                                [verts[0], verts[3], verts[7], verts[4]],
                            ]
                            for face in crenel_faces:
                                try:
                                    bm.faces.new(face)
                                except ValueError:
                                    pass
                            offset += step

                if not closed and s.crenel_end_caps:
                    end_faces = [
                        (plus[0], minus[0], points[0], False),
                        (minus[-1], plus[-1], points[-1], True),
                    ]
                    for outer_a, outer_b, center_p, is_end in end_faces:
                        wall_dir = _engine_common._safe_dir_2d(points[0], points[1]) if not is_end else _engine_common._safe_dir_2d(points[-2], points[-1])
                        if wall_dir is None:
                            continue
                        inward = wall_dir if not is_end else -wall_dir
                        rail_vec = outer_b - outer_a
                        rail_len = rail_vec.length
                        if rail_len <= 1e-6:
                            continue
                        offset = 0.0
                        while offset + s.crenel_width <= rail_len + 1e-6:
                            t0 = offset / rail_len
                            t1 = min(1.0, (offset + s.crenel_width) / rail_len)
                            b0 = outer_a.lerp(outer_b, t0) + Vector((0.0, 0.0, s.wall_height + s.parapet_height))
                            b1 = outer_a.lerp(outer_b, t1) + Vector((0.0, 0.0, s.wall_height + s.parapet_height))
                            i0 = b0 + inward * s.parapet_width
                            i1 = b1 + inward * s.parapet_width
                            t0v = b0 + Vector((0.0, 0.0, s.crenel_height))
                            t1v = b1 + Vector((0.0, 0.0, s.crenel_height))
                            it0 = i0 + Vector((0.0, 0.0, s.crenel_height))
                            it1 = i1 + Vector((0.0, 0.0, s.crenel_height))
                            verts = [bm.verts.new(v) for v in (b0, b1, i1, i0, t0v, t1v, it1, it0)]
                            crenel_faces = [
                                [verts[0], verts[1], verts[2], verts[3]],
                                [verts[4], verts[7], verts[6], verts[5]],
                                [verts[0], verts[4], verts[5], verts[1]],
                                [verts[3], verts[2], verts[6], verts[7]],
                                [verts[1], verts[5], verts[6], verts[2]],
                                [verts[0], verts[3], verts[7], verts[4]],
                            ]
                            for face in crenel_faces:
                                try:
                                    bm.faces.new(face)
                                except ValueError:
                                    pass
                            offset += step

    if len(points) >= 2:
        has_height_variation = any(abs(points[i].z - points[(i + 1) % len(points)].z) > 1e-5 for i in range(len(points) - (0 if closed else 1)))
        if has_height_variation:
            # Sloped walls produce many non-planar quads in the parapets/crenels.
            # Triangulating them removes the visible "twist" Blender shows on those faces.
            bmesh.ops.triangulate(bm, faces=list(bm.faces))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    bind_openings_to_wall(scene, rig, wall_obj, points if len(points) >= 2 else [])
    bind_gates_to_wall(scene, rig, wall_obj, points if len(points) >= 2 else [])
    ensure_opening_boolean(scene, ctx, wall_obj, rig)

    created_wall_instances = rebuild_wall_instances(scene, ctx, rig, wall_obj, points if len(points) >= 2 else [])
    use_wall_source = object_is_valid(s.wall_source) and created_wall_instances > 0
    wall_obj.hide_viewport = use_wall_source
    wall_obj.hide_render = use_wall_source

    tower_points = []
    if raw_waypoints:
        inv = wall_obj.matrix_world.inverted_safe()
        for obj in raw_waypoints:
            tower_points.append(inv @ obj.matrix_world.translation.copy())
    rebuild_tower_instances(scene, ctx, rig, wall_obj, raw_waypoints, tower_points if len(tower_points) >= 1 else [])
    rebuild_gate_instances(scene, ctx, rig, wall_obj)
