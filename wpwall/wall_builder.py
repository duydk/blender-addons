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

    def gate_float(obj, attr_name, fallback):
        if object_is_valid(obj) and hasattr(obj, attr_name):
            try:
                return max(0.05, float(getattr(obj, attr_name)))
            except Exception:
                pass
        if object_is_valid(obj) and attr_name in obj:
            try:
                return max(0.05, float(obj[attr_name]))
            except Exception:
                pass
        return fallback

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
        cut_height = max(0.05, min(gate_float(gate, "wp_wall_gate_height", s.gate_height), s.wall_height))
        angle = tangent.to_2d().angle_signed(Vector((1.0, 0.0)))
        local_matrix = (
            Matrix.Translation(Vector((snapped.x, snapped.y, -floor_overcut)))
            @ Matrix.Rotation(angle, 4, 'Z')
            @ Matrix.Diagonal((
                max(0.05, gate_float(gate, "wp_wall_gate_length", s.gate_length)),
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


def gate_stair_side_items():
    return [
        ('INSIDE', "Inside", "Place stairs on the inside face of the wall"),
        ('OUTSIDE', "Outside", "Place stairs on the outside face of the wall"),
        ('BOTH', "Both", "Place stairs on both wall faces"),
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


def rebuild_wall_instances(scene, context, rig, wall_obj, local_points):
    clear_wall_instances(rig)
    s = settings(scene)
    source = s.wall_source
    if not object_is_valid(source) or len(local_points) < 2:
        return

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


def rebuild_gate_instances(scene, context, rig, wall_obj):
    clear_gate_instances(rig)
    s = settings(scene)
    wall_id = wall_id_from_obj(rig)
    inv = wall_obj.matrix_world.inverted_safe()

    gates = sorted_gates(scene, rig)
    if not gates:
        return

    def gate_tunnel_material():
        mat = bpy.data.materials.get("WP_Gate_Interior")
        if mat is None:
            mat = bpy.data.materials.new("WP_Gate_Interior")
        mat.diffuse_color = (0.42, 0.42, 0.40, 1.0)
        return mat

    def gate_stair_material():
        mat = bpy.data.materials.get("WP_Gate_Stairs")
        if mat is None:
            mat = bpy.data.materials.new("WP_Gate_Stairs")
        mat.diffuse_color = (0.62, 0.62, 0.60, 1.0)
        return mat

    def add_box_faces(bm, x0, x1, y0, y1, z0, z1):
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

    def create_gate_stairs_instance(gate_obj, idx):
        if not object_is_valid(gate_obj) or not bool(getattr(s, "gate_stairs_enabled", True)):
            return

        gate_length = max(0.05, get_gate_length(gate_obj, s.gate_length))
        stair_length = max(0.1, float(getattr(s, "gate_stair_length", 1.6)))
        stair_depth = max(0.05, float(getattr(s, "gate_stair_depth", 0.6)))
        stair_offset = max(0.0, float(getattr(s, "gate_stair_offset", 0.05)))
        stair_steps = max(1, int(getattr(s, "gate_stair_steps", 7)))
        custom_height = float(getattr(s, "gate_stair_height", 0.0))
        stair_height = max(0.05, custom_height if custom_height > 0.0 else s.wall_height)
        stair_side = str(getattr(s, "gate_stair_side", 'INSIDE'))
        gate_half = gate_length * 0.5
        side_gap = stair_offset
        step_len = stair_length / stair_steps
        step_height = stair_height / stair_steps
        face_dirs = []
        if stair_side in {'INSIDE', 'BOTH'}:
            face_dirs.append(1.0)
        if stair_side in {'OUTSIDE', 'BOTH'}:
            face_dirs.append(-1.0)

        mesh = bpy.data.meshes.new(f"GATE_STAIRS_{wall_id:03d}_{idx:03d}_mesh")
        bm = bmesh.new()

        def add_stair_run(inner_x, x_dir, y0, y1):
            landing_len = step_len * 5.0
            total_len = landing_len + (max(0, stair_steps - 1) * step_len)
            profile = [(total_len, 0.0), (0.0, 0.0), (0.0, stair_height), (landing_len, stair_height)]
            for level in range(stair_steps - 1, 0, -1):
                z = level * step_height
                d0 = landing_len + ((stair_steps - 1 - level) * step_len)
                d1 = d0 + step_len
                profile.append((d0, z))
                profile.append((d1, z))
            profile.append((total_len, 0.0))

            front = [bm.verts.new((inner_x + (d * x_dir), y0, z)) for d, z in profile]
            back = [bm.verts.new((inner_x + (d * x_dir), y1, z)) for d, z in profile]
            try:
                bm.faces.new(front)
            except ValueError:
                pass
            try:
                bm.faces.new(tuple(reversed(back)))
            except ValueError:
                pass
            for i in range(len(profile)):
                j = (i + 1) % len(profile)
                try:
                    bm.faces.new((front[i], front[j], back[j], back[i]))
                except ValueError:
                    pass

        for face_dir in face_dirs:
            y_inner = face_dir * ((s.wall_thickness * 0.5) + 0.02)
            y_outer = y_inner + (face_dir * stair_depth)
            y0 = min(y_inner, y_outer)
            y1 = max(y_inner, y_outer)
            add_stair_run(-gate_half - side_gap, -1.0, y0, y1)
            add_stair_run(gate_half + side_gap, 1.0, y0, y1)

        bm.normal_update()
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        stair_obj = bpy.data.objects.new(f"GATE_STAIRS_{wall_id:03d}_{idx:03d}", mesh)
        stair_obj[ADDON_TAG] = True
        stair_obj[GATE_INSTANCE_TAG] = True
        stair_obj[WALL_ID_TAG] = wall_id
        stair_obj.hide_render = False
        stair_obj.hide_set(False)
        stair_obj.data.materials.append(gate_stair_material())
        ensure_collection(context).objects.link(stair_obj)

        local_gate_m = inv @ gate_obj.matrix_world
        local_gate_pos = local_gate_m.translation.copy()
        local_yaw = local_gate_m.to_euler('XYZ').z
        placement_local = (
            Matrix.Translation(Vector((local_gate_pos.x, local_gate_pos.y, 0.0)))
            @ Matrix.Rotation(local_yaw, 4, 'Z')
        )
        stair_obj.matrix_world = wall_obj.matrix_world @ placement_local
        parent_keep_transform(stair_obj, wall_obj)

    def create_gate_tunnel_arch_instance(gate_obj, idx, steps=18):
        if not object_is_valid(gate_obj):
            return

        tunnel_mesh = bpy.data.meshes.new(f"GATE_TUNNEL_ARCH_{wall_id:03d}_{idx:03d}_mesh")
        bm = bmesh.new()

        step_count = max(8, int(steps))
        y_front = -0.51
        y_back = 0.51
        tunnel_width = max(0.1, float(getattr(s, "gate_tunnel_width", 1.0)))
        tunnel_height = max(0.1, float(getattr(s, "gate_tunnel_height", 0.94)))
        outer_radius = tunnel_width * 0.5
        outer_arch_height = min(outer_radius, tunnel_height)
        outer_left = -outer_radius
        outer_right = outer_radius
        outer_shoulder = max(0.0, tunnel_height - outer_arch_height)
        tunnel_thickness = min(max(0.01, outer_radius - 0.05), max(0.01, float(getattr(s, "gate_tunnel_thickness", 0.14))))
        inner_half = max(0.05, outer_radius - tunnel_thickness)
        inner_shoulder = outer_shoulder
        inner_radius = inner_half
        inner_inset = 0.0
        z_lift = float(getattr(s, "gate_tunnel_z_offset", 0.03))

        def outer_arch_z(x):
            arch = max(0.0, outer_radius * outer_radius - x * x) ** 0.5
            return outer_shoulder + ((arch / outer_radius) * outer_arch_height)

        def add_curved_side_strip(x0, x1, strip_steps=4):
            front_bottom = []
            back_bottom = []
            front_top = []
            back_top = []
            for strip_step in range(max(1, int(strip_steps)) + 1):
                t = strip_step / max(1, int(strip_steps))
                x = x0 + ((x1 - x0) * t)
                z = outer_arch_z(x)
                front_bottom.append(bm.verts.new((x, y_front, z_lift)))
                back_bottom.append(bm.verts.new((x, y_back, z_lift)))
                front_top.append(bm.verts.new((x, y_front, z + z_lift)))
                back_top.append(bm.verts.new((x, y_back, z + z_lift)))

            for strip_step in range(len(front_bottom) - 1):
                faces = (
                    (front_bottom[strip_step], front_bottom[strip_step + 1], back_bottom[strip_step + 1], back_bottom[strip_step]),
                    (front_top[strip_step], back_top[strip_step], back_top[strip_step + 1], front_top[strip_step + 1]),
                    (front_bottom[strip_step], front_top[strip_step], front_top[strip_step + 1], front_bottom[strip_step + 1]),
                    (back_bottom[strip_step + 1], back_top[strip_step + 1], back_top[strip_step], back_bottom[strip_step]),
                )
                for face in faces:
                    try:
                        bm.faces.new(face)
                    except ValueError:
                        pass

            for face in (
                (front_bottom[0], back_bottom[0], back_top[0], front_top[0]),
                (front_bottom[-1], front_top[-1], back_top[-1], back_bottom[-1]),
            ):
                try:
                    bm.faces.new(face)
                except ValueError:
                    pass

        # Side jambs follow the outer arch curve instead of ending with a flat step.
        add_curved_side_strip(outer_left, -inner_half)
        add_curved_side_strip(inner_half, outer_right)

        inner_front = []
        inner_back = []
        outer_front = []
        outer_back = []
        for step in range(step_count + 1):
            t = step / step_count
            x = -inner_half + (inner_half * 2.0 * t)
            arch_z = inner_shoulder + max(0.0, inner_radius * inner_radius - x * x) ** 0.5
            inner_z = max(0.0, arch_z - inner_inset)
            outer_z = outer_arch_z(x)
            inner_front.append(bm.verts.new((x, y_front, inner_z + z_lift)))
            inner_back.append(bm.verts.new((x, y_back, inner_z + z_lift)))
            outer_front.append(bm.verts.new((x, y_front, outer_z + z_lift)))
            outer_back.append(bm.verts.new((x, y_back, outer_z + z_lift)))

        # Curved top masonry between the inner opening arch and outer arch.
        for step in range(step_count):
            faces = (
                (inner_back[step], inner_back[step + 1], inner_front[step + 1], inner_front[step]),
                (outer_front[step], outer_front[step + 1], outer_back[step + 1], outer_back[step]),
                (inner_front[step], inner_front[step + 1], outer_front[step + 1], outer_front[step]),
                (outer_back[step], outer_back[step + 1], inner_back[step + 1], inner_back[step]),
            )
            for face in faces:
                try:
                    bm.faces.new(face)
                except ValueError:
                    pass

        for face in (
            (inner_front[0], outer_front[0], outer_back[0], inner_back[0]),
            (inner_back[-1], outer_back[-1], outer_front[-1], inner_front[-1]),
        ):
            try:
                bm.faces.new(face)
            except ValueError:
                pass

        bm.normal_update()
        bm.to_mesh(tunnel_mesh)
        bm.free()
        tunnel_mesh.update()

        tunnel_obj = bpy.data.objects.new(f"GATE_TUNNEL_ARCH_{wall_id:03d}_{idx:03d}", tunnel_mesh)
        tunnel_obj[ADDON_TAG] = True
        tunnel_obj[GATE_INSTANCE_TAG] = True
        tunnel_obj[WALL_ID_TAG] = wall_id
        tunnel_obj.hide_render = False
        tunnel_obj.hide_set(False)
        tunnel_obj.display_type = 'TEXTURED'
        tunnel_obj.show_in_front = False
        tunnel_obj.show_name = False
        tunnel_obj.color = (0.42, 0.42, 0.40, 1.0)
        tunnel_obj.data.materials.append(gate_tunnel_material())
        ensure_collection(context).objects.link(tunnel_obj)

        tunnel_obj.matrix_world = gate_obj.matrix_world.copy()
        parent_keep_transform(tunnel_obj, wall_obj)

    for idx, gate in enumerate(gates):
        if not object_is_valid(gate):
            continue
        create_gate_tunnel_arch_instance(gate, idx)
        create_gate_stairs_instance(gate, idx)
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
    if get_gate_base_style(None, s.gate_base_style) != 'FORTIFIED' or len(local_points) < 1:
        return

    wall_id = wall_id_from_obj(rig)
    closed = bool(s.closed_loop and len(local_points) > 2)
    gate_length = max(0.05, s.gate_length)
    base_width = max(0.05, gate_length * max(0.01, s.gate_base_width_mult))
    base_thickness = max(0.05, s.wall_thickness * max(0.01, s.gate_base_thickness_mult))
    base_height = max(0.05, s.wall_height * max(0.01, s.gate_base_height_mult))
    bottom_width = max(0.05, base_width * max(0.01, s.gate_base_bottom_width_mult))
    bottom_thickness = max(0.05, base_thickness * max(0.01, s.gate_base_bottom_thickness_mult))
    parapet_h = max(0.0, s.parapet_height)
    parapet_w = max(0.0, s.parapet_width)
    crenel_h = max(0.0, s.crenel_height)
    crenel_w = max(0.0, s.crenel_width)
    crenel_g = max(0.0, s.crenel_gap)

    def add_prism(bm, x0, x1, y0, y1, z0, z1):
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

    def build_tower_mesh(mesh_name):
        mesh = bpy.data.meshes.new(mesh_name)
        bm = bmesh.new()
        tw = base_width * 0.5
        tt = base_thickness * 0.5
        bw = bottom_width * 0.5
        bt = bottom_thickness * 0.5
        h = base_height

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

        if parapet_h > 1e-6 and parapet_w > 1e-6 and tt > parapet_w:
            add_prism(bm, -tw, tw, -tt, -tt + parapet_w, h, h + parapet_h)
            add_prism(bm, -tw, tw, tt - parapet_w, tt, h, h + parapet_h)
            add_prism(bm, -tw, -tw + parapet_w, -tt, tt, h, h + parapet_h)
            add_prism(bm, tw - parapet_w, tw, -tt, tt, h, h + parapet_h)

            if crenel_h > 1e-6 and crenel_w > 1e-6:
                step = crenel_w + crenel_g
                if step > 1e-6:
                    offset_x = 0.0
                    while offset_x + crenel_w <= (tw * 2.0) + 1e-6:
                        x0 = -tw + offset_x
                        x1 = min(tw, x0 + crenel_w)
                        add_prism(bm, x0, x1, -tt, -tt + parapet_w, h + parapet_h, h + parapet_h + crenel_h)
                        add_prism(bm, x0, x1, tt - parapet_w, tt, h + parapet_h, h + parapet_h + crenel_h)
                        offset_x += step

                    offset_y = 0.0
                    while offset_y + crenel_w <= (tt * 2.0) + 1e-6:
                        y0 = -tt + offset_y
                        y1 = min(tt, y0 + crenel_w)
                        add_prism(bm, -tw, -tw + parapet_w, y0, y1, h + parapet_h, h + parapet_h + crenel_h)
                        add_prism(bm, tw - parapet_w, tw, y0, y1, h + parapet_h, h + parapet_h + crenel_h)
                        offset_y += step

        bm.normal_update()
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        return mesh

    for idx, (point, tangent) in enumerate(tower_points_with_tangent(local_points, closed)):
        mesh = build_tower_mesh(f"TOWER_{wall_id:03d}_{idx:03d}_mesh")
        instance = bpy.data.objects.new(f"TOWER_{wall_id:03d}_{idx:03d}", mesh)
        instance[ADDON_TAG] = True
        instance[TOWER_INSTANCE_TAG] = True
        instance[WALL_ID_TAG] = wall_id
        instance.hide_render = False
        instance.hide_set(False)
        ensure_collection(context).objects.link(instance)
        placement = (
            Matrix.Translation((wall_obj.matrix_world @ point))
            @ Matrix.Rotation(tangent.to_2d().angle_signed(Vector((1.0, 0.0))), 4, 'Z')
        )
        instance.matrix_world = placement
        parent_keep_transform(instance, wall_obj)


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
                plus.append(_miter_offset_point(prev_p, p, next_p, half, +1.0))
                minus.append(_miter_offset_point(prev_p, p, next_p, half, -1.0))
                continue

            if i == 0:
                d = _safe_dir_2d(points[0], points[1])
                if d is None:
                    continue
                nrm = Vector((-d.y, d.x, 0.0))
                plus.append(p + nrm * half)
                minus.append(p - nrm * half)
            elif i == n - 1:
                d = _safe_dir_2d(points[n - 2], points[n - 1])
                if d is None:
                    continue
                nrm = Vector((-d.y, d.x, 0.0))
                plus.append(p + nrm * half)
                minus.append(p - nrm * half)
            else:
                prev_p = points[i - 1]
                next_p = points[i + 1]
                plus.append(_miter_offset_point(prev_p, p, next_p, half, +1.0))
                minus.append(_miter_offset_point(prev_p, p, next_p, half, -1.0))

        if len(plus) == n and len(minus) == n:
            plus_b = [bm.verts.new(v) for v in plus]
            minus_b = [bm.verts.new(v) for v in minus]
            plus_t = [bm.verts.new(v + Vector((0.0, 0.0, s.wall_height))) for v in plus]
            minus_t = [bm.verts.new(v + Vector((0.0, 0.0, s.wall_height))) for v in minus]
            use_parapets = s.parapet_height > 1e-6 and s.parapet_width > 1e-6 and s.wall_thickness > 1e-6
            parapet_ratio = _clamp(s.parapet_width / max(s.wall_thickness, 1e-6), 0.0, 0.49) if use_parapets else 0.0
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
                    turn_sign = _turn_sign_2d(points[i], points[j], points[k])
                faces = [[plus_b[i], plus_b[j], minus_b[j], minus_b[i]]]
                if use_parapets:
                    if k is not None and abs(turn_sign) > 1e-8:
                        if turn_sign > 0.0:
                            walk_cut = _segment_line_intersection_point_2d(
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
                            walk_cut = _segment_line_intersection_point_2d(
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
                            top_cut = _segment_line_intersection_point_2d(
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
                            top_cut = _segment_line_intersection_point_2d(
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
                    start_dir = _safe_dir_2d(points[0], points[1])
                    end_dir = _safe_dir_2d(points[-2], points[-1])
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
                    tangent = _safe_dir_2d(points[i], points[j])
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
                        wall_dir = _safe_dir_2d(points[0], points[1]) if not is_end else _safe_dir_2d(points[-2], points[-1])
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

    use_wall_source = object_is_valid(s.wall_source)
    wall_obj.hide_viewport = use_wall_source
    wall_obj.hide_render = use_wall_source
    rebuild_wall_instances(scene, ctx, rig, wall_obj, points if len(points) >= 2 else [])

    tower_points = []
    if raw_waypoints:
        inv = wall_obj.matrix_world.inverted_safe()
        for obj in raw_waypoints:
            tower_points.append(inv @ obj.matrix_world.translation.copy())
    rebuild_tower_instances(scene, ctx, rig, wall_obj, raw_waypoints, tower_points if len(tower_points) >= 1 else [])
    rebuild_gate_instances(scene, ctx, rig, wall_obj)
