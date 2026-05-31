import bpy
import bmesh
from math import acos, atan2, cos, pi, sin, tan
from mathutils import Matrix, Vector
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup

ADDON_TAG = "WP_WALL_PCG"
RIG_TAG = "wp_wall_rig"
WAYPOINT_TAG = "wp_wall_waypoint"
WALL_ID_TAG = "wp_wall_id"
WALL_OBJ_TAG = "wp_wall_mesh"
WALL_INSTANCE_TAG = "wp_wall_instance"
TOWER_INSTANCE_TAG = "wp_wall_tower_instance"
OPENING_TAG = "wp_wall_opening"
GATE_TAG = "wp_wall_gate"
GATE_INSTANCE_TAG = "wp_wall_gate_instance"


def settings(scene):
    return scene.wp_wall_settings


def object_is_valid(obj):
    if obj is None:
        return False
    try:
        return obj.name in bpy.data.objects
    except ReferenceError:
        return False


def ensure_collection(context):
    scene = context.scene
    name = settings(scene).collection_name
    coll = bpy.data.collections.get(name)
    if coll:
        return coll
    coll = bpy.data.collections.new(name)
    context.scene.collection.children.link(coll)
    return coll


def wall_id_from_obj(obj):
    if not object_is_valid(obj):
        return None
    if obj.get(RIG_TAG):
        return obj.get(WALL_ID_TAG)
    if object_is_valid(obj.parent) and obj.parent.get(RIG_TAG):
        return obj.parent.get(WALL_ID_TAG)
    return obj.get(WALL_ID_TAG)


def active_rig(context):
    scene = context.scene
    obj = context.active_object
    if object_is_valid(obj):
        if obj.get(RIG_TAG):
            scene.wp_wall_active_rig = obj
            return obj
        if object_is_valid(obj.parent) and obj.parent.get(RIG_TAG):
            scene.wp_wall_active_rig = obj.parent
            return obj.parent
    stored = scene.wp_wall_active_rig
    if object_is_valid(stored) and stored.get(RIG_TAG):
        return stored
    return None


def active_rig_readonly(context):
    scene = context.scene
    obj = context.active_object
    if object_is_valid(obj):
        if obj.get(RIG_TAG):
            return obj
        if object_is_valid(obj.parent) and obj.parent.get(RIG_TAG):
            return obj.parent
    stored = scene.wp_wall_active_rig
    if object_is_valid(stored) and stored.get(RIG_TAG):
        return stored
    return None


def new_wall_id(scene):
    scene.wp_wall_next_id += 1
    return scene.wp_wall_next_id


def set_active_rig(scene, rig):
    scene.wp_wall_active_rig = rig


def create_wall_rig(context):
    scene = context.scene
    rig_id = new_wall_id(scene)
    rig = bpy.data.objects.new(f"Wall_Rig_{rig_id:03d}", None)
    rig.empty_display_type = 'PLAIN_AXES'
    rig.empty_display_size = 0.6
    rig[RIG_TAG] = True
    rig[ADDON_TAG] = True
    rig[WALL_ID_TAG] = rig_id
    ensure_collection(context).objects.link(rig)
    if context.view_layer:
        for obj in list(context.selected_objects):
            if object_is_valid(obj):
                obj.select_set(False)
        rig.select_set(True)
        context.view_layer.objects.active = rig
    set_active_rig(scene, rig)
    return rig


def ensure_rig_object(context):
    rig = active_rig(context)
    if rig:
        return rig
    return create_wall_rig(context)


def parent_keep_transform(child, parent):
    if child.parent == parent:
        return
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted_safe()
    child.matrix_world = mw


def sorted_waypoints(scene, rig=None):
    wall_id = wall_id_from_obj(rig) if rig else None
    items = []
    for ref in scene.wp_wall_waypoints:
        obj = ref.obj
        if object_is_valid(obj):
            if wall_id is not None and obj.get(WALL_ID_TAG) != wall_id:
                continue
            items.append((ref.order, obj))
    items.sort(key=lambda item: item[0])
    return [obj for _, obj in items]


def wall_object(scene, rig=None):
    wall_id = wall_id_from_obj(rig)
    if wall_id is None:
        return None
    for obj in bpy.data.objects:
        if obj.get(WALL_OBJ_TAG) and obj.get(WALL_ID_TAG) == wall_id:
            return obj
    return None


def sorted_openings(scene, rig=None):
    wall_id = wall_id_from_obj(rig) if rig else None
    items = []
    for obj in bpy.data.objects:
        if not obj.get(OPENING_TAG):
            continue
        if wall_id is not None and obj.get(WALL_ID_TAG) != wall_id:
            continue
        items.append(obj)
    items.sort(key=lambda item: item.name)
    return items


def sorted_gates(scene, rig=None):
    wall_id = wall_id_from_obj(rig) if rig else None
    items = []
    for obj in bpy.data.objects:
        if not obj.get(GATE_TAG):
            continue
        if wall_id is not None and obj.get(WALL_ID_TAG) != wall_id:
            continue
        items.append(obj)
    items.sort(key=lambda item: item.name)
    return items


def ensure_wall_object(context):
    rig = ensure_rig_object(context)
    scene = context.scene
    wall_obj = wall_object(scene, rig)
    if wall_obj:
        return wall_obj
    wall_id = wall_id_from_obj(rig)
    mesh = bpy.data.meshes.new(f"Generated_Wall_{wall_id:03d}_mesh")
    wall_obj = bpy.data.objects.new(f"Generated_Wall_{wall_id:03d}", mesh)
    wall_obj[ADDON_TAG] = True
    wall_obj[WALL_OBJ_TAG] = True
    wall_obj[WALL_ID_TAG] = wall_id
    ensure_collection(context).objects.link(wall_obj)
    parent_keep_transform(wall_obj, rig)
    return wall_obj


def _bbox_world_corners(obj, matrix_world=None):
    mw = matrix_world if matrix_world is not None else obj.matrix_world
    return [mw @ Vector(corner) for corner in obj.bound_box]


def _aabb_from_points(points):
    min_v = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    max_v = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return min_v, max_v


def _aabb_overlap(min_a, max_a, min_b, max_b):
    return (
        min_a.x <= max_b.x and max_a.x >= min_b.x and
        min_a.y <= max_b.y and max_a.y >= min_b.y and
        min_a.z <= max_b.z and max_a.z >= min_b.z
    )


def opening_world_aabbs(scene, rig=None):
    boxes = []
    for opening in sorted_openings(scene, rig):
        if object_is_valid(opening):
            boxes.append(_aabb_from_points(_bbox_world_corners(opening)))
    return boxes


def cutter_world_aabbs(scene, rig=None):
    boxes = []
    for obj in sorted_openings(scene, rig) + sorted_gates(scene, rig):
        if object_is_valid(obj):
            boxes.append(_aabb_from_points(_bbox_world_corners(obj)))
    return boxes


def nearest_segment_info(points, target, closed):
    if len(points) < 2:
        return None
    seg_count = len(points) if closed else len(points) - 1
    best = None
    best_dist = None
    for i in range(seg_count):
        a = points[i]
        b = points[(i + 1) % len(points)]
        seg = b - a
        seg_len_sq = seg.length_squared
        if seg_len_sq <= 1e-10:
            continue
        t = _clamp((target - a).dot(seg) / seg_len_sq, 0.0, 1.0)
        snapped = a.lerp(b, t)
        dist = (target - snapped).length_squared
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = (i, snapped, _safe_dir_2d(a, b))
    return best


def bind_openings_to_wall(scene, rig, wall_obj, local_points):
    s = settings(scene)
    if len(local_points) < 2:
        return
    closed = bool(s.closed_loop and len(local_points) > 2)
    cut_depth = max(0.05, s.wall_thickness + 0.05)
    cut_height = max(0.05, s.wall_height + 0.05)
    inv = wall_obj.matrix_world.inverted_safe()

    for opening in sorted_openings(scene, rig):
        if not object_is_valid(opening):
            continue
        target_local = inv @ opening.matrix_world.translation.copy()
        hit = nearest_segment_info(local_points, target_local, closed)
        if hit is None:
            continue
        _seg_idx, snapped, tangent = hit
        if tangent is None:
            tangent = Vector((1.0, 0.0, 0.0))
        angle = tangent.to_2d().angle_signed(Vector((1.0, 0.0)))
        local_matrix = (
            Matrix.Translation(Vector((snapped.x, snapped.y, cut_height * 0.5)))
            @ Matrix.Rotation(angle, 4, 'Z')
            @ Matrix.Diagonal((
                max(0.05, get_opening_length(opening, s.opening_length)),
                cut_depth,
                cut_height,
                1.0,
            ))
        )
        opening.matrix_parent_inverse = Matrix.Identity(4)
        opening.matrix_world = wall_obj.matrix_world @ local_matrix


def bind_gates_to_wall(scene, rig, wall_obj, local_points):
    s = settings(scene)
    if len(local_points) < 2:
        return
    closed = bool(s.closed_loop and len(local_points) > 2)
    cut_depth = max(0.05, s.wall_thickness + 0.05)
    fortified_depth = max(
        0.05,
        s.wall_thickness
        * max(0.01, s.gate_base_thickness_mult)
        * max(0.01, s.gate_base_bottom_thickness_mult)
        + 0.05,
    )
    floor_overcut = 0.05
    inv = wall_obj.matrix_world.inverted_safe()

    for gate in sorted_gates(scene, rig):
        if not object_is_valid(gate):
            continue
        rebuild_gate_cutter_mesh(gate)
        target_local = inv @ gate.matrix_world.translation.copy()
        hit = nearest_segment_info(local_points, target_local, closed)
        if hit is None:
            continue
        _seg_idx, snapped, tangent = hit
        if tangent is None:
            tangent = Vector((1.0, 0.0, 0.0))
        gate_base_style = get_gate_base_style(gate, s.gate_base_style)
        gate_cut_depth = fortified_depth if gate_base_style == 'FORTIFIED' else cut_depth
        cut_height = max(0.05, min(get_gate_height(gate, s.gate_height), s.wall_height))
        angle = tangent.to_2d().angle_signed(Vector((1.0, 0.0)))
        local_matrix = (
            Matrix.Translation(Vector((snapped.x, snapped.y, -floor_overcut)))
            @ Matrix.Rotation(angle, 4, 'Z')
            @ Matrix.Diagonal((
                max(0.05, get_gate_length(gate, s.gate_length)),
                gate_cut_depth,
                cut_height + floor_overcut,
                1.0,
            ))
        )
        gate.matrix_parent_inverse = Matrix.Identity(4)
        gate.matrix_world = wall_obj.matrix_world @ local_matrix


def ensure_opening_boolean(scene, context, wall_obj, rig):
    openings = sorted_openings(scene, rig) + sorted_gates(scene, rig)
    existing = wall_obj.modifiers.get("WP_Openings")
    if not openings:
        if existing:
            wall_obj.modifiers.remove(existing)
        return
    bool_mod = existing or wall_obj.modifiers.new(name="WP_Openings", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.solver = 'EXACT'
    bool_mod.operand_type = 'COLLECTION'
    coll_name = f"WP_Cutters_{wall_id_from_obj(rig):03d}"
    coll = bpy.data.collections.get(coll_name)
    if coll is None:
        coll = bpy.data.collections.new(coll_name)
        ensure_collection(context).children.link(coll)
    for obj in list(coll.objects):
        coll.objects.unlink(obj)
    for opening in openings:
        if opening.name not in coll.objects:
            coll.objects.link(opening)
    bool_mod.collection = coll


def next_waypoint_index(scene, rig=None):
    refs = sorted_waypoints(scene, rig)
    return len(refs)


def refresh_waypoint_orders(scene, rig=None):
    for idx, obj in enumerate(sorted_waypoints(scene, rig)):
        for ref in scene.wp_wall_waypoints:
            if ref.obj == obj:
                ref.order = idx
                break


def _safe_dir_2d(a, b):
    vec = Vector((b.x - a.x, b.y - a.y, 0.0))
    if vec.length < 1e-8:
        return None
    return vec.normalized()


def _clamp(value, low, high):
    return max(low, min(high, value))


def _line_intersection_2d(p1, d1, p2, d2):
    cross = d1.x * d2.y - d1.y * d2.x
    if abs(cross) < 1e-8:
        return None
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    t = (dx * d2.y - dy * d2.x) / cross
    return Vector((p1.x + d1.x * t, p1.y + d1.y * t, p1.z))


def _segment_line_intersection_point_2d(a, b, c, d):
    ab = Vector((b.x - a.x, b.y - a.y, 0.0))
    cd = Vector((d.x - c.x, d.y - c.y, 0.0))
    hit = _line_intersection_2d(a, ab, c, cd)
    if hit is None:
        return None
    denom = ab.x * ab.x + ab.y * ab.y
    if denom <= 1e-10:
        return None
    t = ((hit.x - a.x) * ab.x + (hit.y - a.y) * ab.y) / denom
    # Only accept cuts that land on the current segment.
    # Letting the intersection fall far outside this span can create huge
    # stretched faces when nearly-parallel corner rails are extended.
    if t < -1e-4 or t > 1.0001:
        return None
    hit.z = a.z + (b.z - a.z) * t
    return hit


def _turn_sign_2d(a, b, c):
    abx = b.x - a.x
    aby = b.y - a.y
    bcx = c.x - b.x
    bcy = c.y - b.y
    return abx * bcy - aby * bcx


def _miter_offset_point(prev_p, p, next_p, half, sign):
    d0 = _safe_dir_2d(prev_p, p)
    d1 = _safe_dir_2d(p, next_p)
    if d0 is None or d1 is None:
        return Vector((p.x, p.y, p.z))
    n0 = Vector((-d0.y, d0.x, 0.0))
    n1 = Vector((-d1.y, d1.x, 0.0))
    off0 = p + n0 * (half * sign)
    off1 = p + n1 * (half * sign)
    hit = _line_intersection_2d(off0, d0, off1, d1)
    if hit is not None:
        prev_len = Vector((p.x - prev_p.x, p.y - prev_p.y, 0.0)).length
        next_len = Vector((next_p.x - p.x, next_p.y - p.y, 0.0)).length
        max_miter = max(half * 4.0, min(prev_len, next_len) * 0.75)
        if (hit - p).length <= max_miter:
            hit.z = p.z
            return hit
    n = n0 + n1
    if n.length < 1e-8:
        n = n0
    n.normalize()
    return p + n * (half * sign)


def _append_unique(points, point, eps=1e-5):
    if not points or (points[-1] - point).length > eps:
        points.append(point)


def gate_style_items():
    return [
        ('ARCH', "Arch", "Rounded arch gate opening"),
        ('RECT', "Rectangle", "Flat-top rectangular gate opening"),
        ('POINTED', "Pointed", "Pointed arch gate opening"),
        ('HORSESHOE', "Horseshoe", "Tall rounded horseshoe opening"),
    ]


def gate_base_items():
    return [
        ('NONE', "None", "No gate base"),
        ('FORTIFIED', "Fortified Base", "Add a fortified base block around the gate"),
    ]


def get_gate_style(obj, default='ARCH'):
    if not object_is_valid(obj):
        return default
    if hasattr(obj, "wp_wall_gate_style"):
        try:
            value = str(obj.wp_wall_gate_style)
            if value in {'ARCH', 'RECT', 'POINTED', 'HORSESHOE'}:
                return value
        except Exception:
            pass
    if "wp_wall_gate_style" in obj:
        try:
            value = str(obj["wp_wall_gate_style"])
            if value in {'ARCH', 'RECT', 'POINTED', 'HORSESHOE'}:
                return value
        except Exception:
            pass
    return default


def set_gate_style(obj, value):
    value = str(value)
    if value not in {'ARCH', 'RECT', 'POINTED', 'HORSESHOE'}:
        value = 'ARCH'
    if hasattr(obj, "wp_wall_gate_style"):
        obj.wp_wall_gate_style = value
    obj["wp_wall_gate_style"] = value


def get_gate_base_style(obj, default='NONE'):
    if not object_is_valid(obj):
        return default
    if hasattr(obj, "wp_wall_gate_base_style"):
        try:
            value = str(obj.wp_wall_gate_base_style)
            if value in {'NONE', 'FORTIFIED'}:
                return value
        except Exception:
            pass
    if "wp_wall_gate_base_style" in obj:
        try:
            value = str(obj["wp_wall_gate_base_style"])
            if value in {'NONE', 'FORTIFIED'}:
                return value
        except Exception:
            pass
    return default


def set_gate_base_style(obj, value):
    value = str(value)
    if value not in {'NONE', 'FORTIFIED'}:
        value = 'NONE'
    if hasattr(obj, "wp_wall_gate_base_style"):
        obj.wp_wall_gate_base_style = value
    obj["wp_wall_gate_base_style"] = value


def rebuild_gate_cutter_mesh(obj, arc_steps=12):
    if not object_is_valid(obj) or obj.type != 'MESH' or obj.data is None:
        return

    mesh = obj.data
    bm = bmesh.new()
    style = get_gate_style(obj, 'ARCH')
    front_y = -0.5
    back_y = 0.5

    if style == 'RECT':
        profile = [
            Vector((-0.5, 0.0)),
            Vector((0.5, 0.0)),
            Vector((0.5, 1.0)),
            Vector((-0.5, 1.0)),
        ]
    elif style == 'POINTED':
        shoulder_z = 0.5
        profile = [
            Vector((-0.5, 0.0)),
            Vector((0.5, 0.0)),
            Vector((0.5, shoulder_z)),
            Vector((0.0, 1.15)),
            Vector((-0.5, shoulder_z)),
        ]
    elif style == 'HORSESHOE':
        shoulder_z = 0.28
        radius_x = 0.5
        radius_z = 0.72
        profile = [
            Vector((-0.5, 0.0)),
            Vector((0.5, 0.0)),
            Vector((0.5, shoulder_z)),
        ]
        step_count = max(3, arc_steps)
        for step in range(1, step_count):
            angle = (step / step_count) * pi
            profile.append(Vector((cos(angle) * radius_x, shoulder_z + sin(angle) * radius_z)))
        profile.append(Vector((-0.5, shoulder_z)))
    else:
        shoulder_z = 0.5
        radius = 0.5
        profile = [
            Vector((-0.5, 0.0)),
            Vector((0.5, 0.0)),
            Vector((0.5, shoulder_z)),
        ]
        step_count = max(2, arc_steps)
        for step in range(1, step_count):
            angle = (step / step_count) * pi
            profile.append(Vector((cos(angle) * radius, shoulder_z + sin(angle) * radius)))
        profile.append(Vector((-0.5, shoulder_z)))

    front = [bm.verts.new((point.x, front_y, point.y)) for point in profile]
    back = [bm.verts.new((point.x, back_y, point.y)) for point in profile]

    try:
        bm.faces.new(front)
    except ValueError:
        pass
    try:
        bm.faces.new(list(reversed(back)))
    except ValueError:
        pass

    for i in range(len(profile)):
        j = (i + 1) % len(profile)
        try:
            bm.faces.new((front[i], front[j], back[j], back[i]))
        except ValueError:
            pass

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def _rounded_corner_samples(prev_p, p, next_p, radius, steps):
    if radius <= 1e-6:
        return [p.copy()]

    in_vec = prev_p - p
    out_vec = next_p - p
    in_len = in_vec.length
    out_len = out_vec.length
    if in_len <= 1e-6 or out_len <= 1e-6:
        return [p.copy()]

    v1 = in_vec.normalized()
    v2 = out_vec.normalized()
    theta = acos(_clamp(v1.dot(v2), -1.0, 1.0))
    if theta <= 1e-4 or abs(theta - pi) <= 1e-4:
        return [p.copy()]

    tan_half = tan(theta * 0.5)
    sin_half = sin(theta * 0.5)
    if abs(tan_half) <= 1e-6 or abs(sin_half) <= 1e-6:
        return [p.copy()]

    trim = min(radius / tan_half, in_len * 0.45, out_len * 0.45)
    if trim <= 1e-6:
        return [p.copy()]

    actual_radius = trim * tan_half
    tangent_in = p + v1 * trim
    tangent_out = p + v2 * trim
    bisector = v1 + v2
    if bisector.length <= 1e-6:
        return [p.copy()]
    bisector.normalize()
    center = p + bisector * (actual_radius / sin_half)

    start_vec = tangent_in - center
    end_vec = tangent_out - center
    start_angle = atan2(start_vec.y, start_vec.x)
    end_angle = atan2(end_vec.y, end_vec.x)
    cross = start_vec.x * end_vec.y - start_vec.y * end_vec.x

    if cross >= 0.0:
        if end_angle < start_angle:
            end_angle += 2.0 * pi
    else:
        if end_angle > start_angle:
            end_angle -= 2.0 * pi

    samples = [tangent_in]
    detail = max(1, steps)
    for step in range(1, detail):
        factor = step / detail
        angle = start_angle + (end_angle - start_angle) * factor
        z = tangent_in.z + (tangent_out.z - tangent_in.z) * factor
        point = Vector((
            center.x + cos(angle) * actual_radius,
            center.y + sin(angle) * actual_radius,
            z,
        ))
        samples.append(point)
    samples.append(tangent_out)
    return samples


def sampled_wall_points(scene, rig, wall_obj):
    s = settings(scene)
    waypoints = sorted_waypoints(scene, rig)
    if len(waypoints) < 2:
        return waypoints, []

    inv = wall_obj.matrix_world.inverted_safe()
    raw_points = []
    for obj in waypoints:
        parent_keep_transform(obj, wall_obj)
        obj.empty_display_size = s.waypoint_display_size
        obj.show_in_front = True
        raw_points.append(inv @ obj.matrix_world.translation.copy())

    if len(raw_points) < 3:
        return waypoints, raw_points

    closed = bool(s.closed_loop and len(raw_points) > 2)
    sampled = []

    if not closed:
        _append_unique(sampled, raw_points[0].copy())
        for i in range(1, len(raw_points) - 1):
            obj = waypoints[i]
            radius = max(0.0, obj.wp_wall_corner_radius)
            steps = max(1, obj.wp_wall_curve_steps)
            if radius > 1e-6:
                for point in _rounded_corner_samples(raw_points[i - 1], raw_points[i], raw_points[i + 1], radius, steps):
                    _append_unique(sampled, point)
            else:
                _append_unique(sampled, raw_points[i].copy())
        _append_unique(sampled, raw_points[-1].copy())
        return waypoints, sampled

    for i in range(len(raw_points)):
        prev_p = raw_points[(i - 1) % len(raw_points)]
        p = raw_points[i]
        next_p = raw_points[(i + 1) % len(raw_points)]
        obj = waypoints[i]
        radius = max(0.0, obj.wp_wall_corner_radius)
        steps = max(1, obj.wp_wall_curve_steps)
        if radius > 1e-6:
            for point in _rounded_corner_samples(prev_p, p, next_p, radius, steps):
                _append_unique(sampled, point)
        else:
            _append_unique(sampled, p.copy())
    return waypoints, sampled


def clear_wall_instances(rig):
    wall_id = wall_id_from_obj(rig)
    for obj in list(bpy.data.objects):
        if obj.get(WALL_INSTANCE_TAG) and obj.get(WALL_ID_TAG) == wall_id:
            bpy.data.objects.remove(obj, do_unlink=True)


def clear_tower_instances(rig):
    wall_id = wall_id_from_obj(rig)
    for obj in list(bpy.data.objects):
        if obj.get(TOWER_INSTANCE_TAG) and obj.get(WALL_ID_TAG) == wall_id:
            bpy.data.objects.remove(obj, do_unlink=True)


def clear_gate_instances(rig):
    wall_id = wall_id_from_obj(rig)
    for obj in list(bpy.data.objects):
        if obj.get(GATE_INSTANCE_TAG) and obj.get(WALL_ID_TAG) == wall_id:
            bpy.data.objects.remove(obj, do_unlink=True)


def tower_points_with_tangent(points, closed):
    out = []
    for idx, point in enumerate(points):
        if closed and len(points) > 2:
            prev_point = points[(idx - 1) % len(points)]
            next_point = points[(idx + 1) % len(points)]
            tangent = _safe_dir_2d(prev_point, next_point)
        elif idx < len(points) - 1:
            tangent = _safe_dir_2d(points[idx], points[idx + 1])
        elif idx > 0:
            tangent = _safe_dir_2d(points[idx - 1], points[idx])
        else:
            tangent = Vector((1.0, 0.0, 0.0))
        if tangent is None:
            tangent = Vector((1.0, 0.0, 0.0))
        out.append((point, tangent))
    return out


