import bpy

from .data import building_type_spec
from .hall_builder import build_hall
from .tags import ADDON_TAG, BUILDING_ID_TAG, BUILDING_PROFILE_TAG, BUILDING_TYPE_TAG, PART_TAG, ROOT_TAG

DEFAULT_MATERIALS = {
    "wall": ("BGCP_Wall", (0.62, 0.58, 0.50, 1.0)),
    "roof": ("BGCP_Roof", (0.28, 0.12, 0.08, 1.0)),
    "glass": ("BGCP_Glass", (0.12, 0.30, 0.48, 0.72)),
    "door": ("BGCP_Door", (0.28, 0.14, 0.07, 1.0)),
    "trim": ("BGCP_Trim", (0.78, 0.74, 0.66, 1.0)),
}


def ensure_collection(scene, name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
    elif collection.name not in [child.name for child in scene.collection.children]:
        try:
            scene.collection.children.link(collection)
        except RuntimeError:
            pass
    return collection


def material_from_color(name, color):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True

    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        base_color = bsdf.inputs.get("Base Color")
        roughness = bsdf.inputs.get("Roughness")
        alpha = bsdf.inputs.get("Alpha")
        if base_color is not None:
            base_color.default_value = color
        if roughness is not None:
            roughness.default_value = 0.62
        if alpha is not None:
            alpha.default_value = color[3]
    if color[3] < 1.0:
        mat.blend_method = 'BLEND'
        if hasattr(mat, "use_screen_refraction"):
            mat.use_screen_refraction = True
    return mat


def materials_from_settings(settings):
    return {
        key: material_from_color(name, tuple(getattr(settings, f"{key}_color", color)))
        for key, (name, color) in DEFAULT_MATERIALS.items()
    }


def _box_mesh(name, size):
    sx, sy, sz = (max(0.001, float(value)) for value in size)
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    verts = (
        (-hx, -hy, -hz),
        (hx, -hy, -hz),
        (hx, hy, -hz),
        (-hx, hy, -hz),
        (-hx, -hy, hz),
        (hx, -hy, hz),
        (hx, hy, hz),
        (-hx, hy, hz),
    )
    faces = (
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    )
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, (), faces)
    mesh.update()
    return mesh


def _add_box(collection, parent, name, location, size, material, part_type):
    obj = bpy.data.objects.new(name, _box_mesh(name, size))
    obj.location = location
    obj.parent = parent
    obj[ADDON_TAG] = True
    obj[BUILDING_ID_TAG] = parent.get(BUILDING_ID_TAG)
    obj[BUILDING_TYPE_TAG] = parent.get(BUILDING_TYPE_TAG)
    obj[BUILDING_PROFILE_TAG] = parent.get(BUILDING_PROFILE_TAG)
    obj[PART_TAG] = part_type
    if material is not None:
        obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def _add_gable_roof(collection, parent, settings, material):
    body_height = settings.floors * settings.floor_height
    width = settings.building_width + settings.roof_overhang * 2.0
    depth = settings.building_depth + settings.roof_overhang * 2.0
    roof_height = max(0.05, settings.roof_height)
    hw, hd = width * 0.5, depth * 0.5
    verts = (
        (-hw, -hd, body_height),
        (hw, -hd, body_height),
        (0.0, -hd, body_height + roof_height),
        (-hw, hd, body_height),
        (hw, hd, body_height),
        (0.0, hd, body_height + roof_height),
    )
    faces = (
        (0, 1, 2),
        (3, 5, 4),
        (0, 3, 4, 1),
        (0, 2, 5, 3),
        (1, 4, 5, 2),
    )
    mesh = bpy.data.meshes.new("BGCP_Gable_Roof_Mesh")
    mesh.from_pydata(verts, (), faces)
    mesh.update()

    obj = bpy.data.objects.new("BGCP_Gable_Roof", mesh)
    obj.parent = parent
    obj[ADDON_TAG] = True
    obj[BUILDING_ID_TAG] = parent.get(BUILDING_ID_TAG)
    obj[BUILDING_TYPE_TAG] = parent.get(BUILDING_TYPE_TAG)
    obj[BUILDING_PROFILE_TAG] = parent.get(BUILDING_PROFILE_TAG)
    obj[PART_TAG] = "roof"
    if material is not None:
        obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def _spaced_positions(span, count, edge_padding):
    count = max(0, int(count))
    if count == 0:
        return []
    if count == 1:
        return [0.0]

    usable = max(0.1, span - edge_padding * 2.0)
    start = -usable * 0.5
    step = usable / (count - 1)
    return [start + step * index for index in range(count)]


def _add_front_back_window(collection, parent, mats, settings, x, z, side, window_height, name):
    depth = settings.building_depth
    pane_depth = 0.04
    frame_depth = 0.035
    frame_y = side * (depth * 0.5 + frame_depth * 0.5)
    pane_y = side * (depth * 0.5 + frame_depth + pane_depth * 0.5)
    width = settings.window_width
    height = window_height

    _add_box(
        collection,
        parent,
        f"{name}_Frame",
        (x, frame_y, z),
        (width + 0.14, frame_depth, height + 0.14),
        mats["trim"],
        "window_frame",
    )
    _add_box(
        collection,
        parent,
        f"{name}_Glass",
        (x, pane_y, z),
        (width, pane_depth, height),
        mats["glass"],
        "window",
    )


def _add_side_window(collection, parent, mats, settings, y, z, side, window_height, name):
    width = settings.building_width
    pane_depth = 0.04
    frame_depth = 0.035
    frame_x = side * (width * 0.5 + frame_depth * 0.5)
    pane_x = side * (width * 0.5 + frame_depth + pane_depth * 0.5)
    window_width = settings.window_width

    _add_box(
        collection,
        parent,
        f"{name}_Frame",
        (frame_x, y, z),
        (frame_depth, window_width + 0.14, window_height + 0.14),
        mats["trim"],
        "window_frame",
    )
    _add_box(
        collection,
        parent,
        f"{name}_Glass",
        (pane_x, y, z),
        (pane_depth, window_width, window_height),
        mats["glass"],
        "window",
    )


def _add_windows(collection, parent, mats, settings):
    width = settings.building_width
    depth = settings.building_depth
    floor_height = settings.floor_height
    window_height = min(settings.window_height, floor_height * 0.72)

    x_positions = _spaced_positions(width, settings.window_columns, settings.window_width * 0.75)
    y_positions = _spaced_positions(depth, max(1, settings.side_window_columns), settings.window_width * 0.75)
    door_block_radius = settings.door_width * 0.65

    for floor_index in range(settings.floors):
        z = floor_index * floor_height + floor_height * 0.55
        z = min(z, (floor_index + 1) * floor_height - window_height * 0.5 - 0.12)
        z = max(z, floor_index * floor_height + window_height * 0.5 + 0.18)

        for column_index, x in enumerate(x_positions):
            if floor_index == 0 and abs(x) < door_block_radius:
                continue
            _add_front_back_window(
                collection,
                parent,
                mats,
                settings,
                x,
                z,
                -1.0,
                window_height,
                f"BGCP_Window_F{floor_index:02d}_Front_{column_index:02d}",
            )
            _add_front_back_window(
                collection,
                parent,
                mats,
                settings,
                x,
                z,
                1.0,
                window_height,
                f"BGCP_Window_F{floor_index:02d}_Back_{column_index:02d}",
            )

        for column_index, y in enumerate(y_positions):
            _add_side_window(
                collection,
                parent,
                mats,
                settings,
                y,
                z,
                -1.0,
                window_height,
                f"BGCP_Window_F{floor_index:02d}_Left_{column_index:02d}",
            )
            _add_side_window(
                collection,
                parent,
                mats,
                settings,
                y,
                z,
                1.0,
                window_height,
                f"BGCP_Window_F{floor_index:02d}_Right_{column_index:02d}",
            )


def _add_door(collection, parent, mats, settings):
    y = -(settings.building_depth * 0.5 + 0.04)
    _add_box(
        collection,
        parent,
        "BGCP_Door_Frame",
        (0.0, y + 0.01, settings.door_height * 0.5),
        (settings.door_width + 0.18, 0.05, settings.door_height + 0.14),
        mats["trim"],
        "door_frame",
    )
    _add_box(
        collection,
        parent,
        "BGCP_Door",
        (0.0, y - 0.02, settings.door_height * 0.5),
        (settings.door_width, 0.05, settings.door_height),
        mats["door"],
        "door",
    )
    _add_box(
        collection,
        parent,
        "BGCP_Door_Handle",
        (settings.door_width * 0.3, y - 0.055, settings.door_height * 0.52),
        (0.06, 0.035, 0.06),
        mats["trim"],
        "door_handle",
    )


def _add_floor_bands(collection, parent, mats, settings):
    width = settings.building_width
    depth = settings.building_depth
    band_height = 0.06
    band_depth = 0.06
    for floor_index in range(1, settings.floors):
        z = floor_index * settings.floor_height
        _add_box(
            collection,
            parent,
            f"BGCP_Floor_Band_Front_{floor_index:02d}",
            (0.0, -(depth * 0.5 + band_depth * 0.5), z),
            (width + 0.08, band_depth, band_height),
            mats["trim"],
            "floor_band",
        )
        _add_box(
            collection,
            parent,
            f"BGCP_Floor_Band_Back_{floor_index:02d}",
            (0.0, depth * 0.5 + band_depth * 0.5, z),
            (width + 0.08, band_depth, band_height),
            mats["trim"],
            "floor_band",
        )
        _add_box(
            collection,
            parent,
            f"BGCP_Floor_Band_Left_{floor_index:02d}",
            (-(width * 0.5 + band_depth * 0.5), 0.0, z),
            (band_depth, depth + 0.08, band_height),
            mats["trim"],
            "floor_band",
        )
        _add_box(
            collection,
            parent,
            f"BGCP_Floor_Band_Right_{floor_index:02d}",
            (width * 0.5 + band_depth * 0.5, 0.0, z),
            (band_depth, depth + 0.08, band_height),
            mats["trim"],
            "floor_band",
        )


def _add_flat_roof(collection, parent, mats, settings):
    body_height = settings.floors * settings.floor_height
    roof_height = max(0.05, settings.roof_height)
    roof_width = settings.building_width + settings.roof_overhang * 2.0
    roof_depth = settings.building_depth + settings.roof_overhang * 2.0
    _add_box(
        collection,
        parent,
        "BGCP_Flat_Roof",
        (0.0, 0.0, body_height + roof_height * 0.5),
        (roof_width, roof_depth, roof_height),
        mats["roof"],
        "roof",
    )

    parapet_height = min(0.35, max(0.08, roof_height * 0.45))
    parapet_thickness = 0.12
    z = body_height + roof_height + parapet_height * 0.5
    _add_box(collection, parent, "BGCP_Parapet_Front", (0.0, -roof_depth * 0.5, z), (roof_width, parapet_thickness, parapet_height), mats["trim"], "parapet")
    _add_box(collection, parent, "BGCP_Parapet_Back", (0.0, roof_depth * 0.5, z), (roof_width, parapet_thickness, parapet_height), mats["trim"], "parapet")
    _add_box(collection, parent, "BGCP_Parapet_Left", (-roof_width * 0.5, 0.0, z), (parapet_thickness, roof_depth, parapet_height), mats["trim"], "parapet")
    _add_box(collection, parent, "BGCP_Parapet_Right", (roof_width * 0.5, 0.0, z), (parapet_thickness, roof_depth, parapet_height), mats["trim"], "parapet")


def _add_roof(collection, parent, mats, settings):
    if settings.roof_style == 'GABLE':
        _add_gable_roof(collection, parent, settings, mats["roof"])
    else:
        _add_flat_roof(collection, parent, mats, settings)


def clear_buildings():
    for obj in list(bpy.data.objects):
        if obj.get(ADDON_TAG):
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0 and mesh.name.startswith("BGCP_"):
            bpy.data.meshes.remove(mesh)


def root_from_object(obj):
    current = obj
    while current is not None:
        if current.get(ADDON_TAG) and current.get(ROOT_TAG):
            return current
        current = current.parent
    return None


def active_building_root(context):
    active = getattr(context, "active_object", None)
    root = root_from_object(active)
    if root is not None:
        return root
    for obj in getattr(context, "selected_objects", []):
        root = root_from_object(obj)
        if root is not None:
            return root
    return None


def _remove_generated_children(root):
    building_id = root.get(BUILDING_ID_TAG)
    for obj in list(bpy.data.objects):
        if obj == root:
            continue
        if obj.get(ADDON_TAG) and obj.get(BUILDING_ID_TAG) == building_id:
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0 and mesh.name.startswith("BGCP_"):
            bpy.data.meshes.remove(mesh)


def _build_generic_building(collection, root, mats, settings):
    body_height = settings.floors * settings.floor_height
    _add_box(
        collection,
        root,
        "BGCP_Body",
        (0.0, 0.0, body_height * 0.5),
        (settings.building_width, settings.building_depth, body_height),
        mats["wall"],
        "body",
    )
    _add_floor_bands(collection, root, mats, settings)
    _add_door(collection, root, mats, settings)
    _add_windows(collection, root, mats, settings)
    _add_roof(collection, root, mats, settings)


def _build_by_profile(collection, root, mats, settings, spec):
    if spec.generator_profile == "ly_dynasty_ceremonial_hall":
        build_hall(collection, root, mats, settings)
    else:
        _build_generic_building(collection, root, mats, settings)


def _collection_for_root(scene, root, settings):
    if root.users_collection:
        return root.users_collection[0]
    return ensure_collection(scene, settings.collection_name)


def rebuild_building(context, root=None):
    scene = context.scene
    settings = scene.bgcp_settings
    root = root or active_building_root(context)
    if root is None:
        return False

    building_type = root.get(BUILDING_TYPE_TAG)
    if not building_type:
        return False

    spec = building_type_spec(building_type)
    collection = _collection_for_root(scene, root, settings)
    mats = materials_from_settings(settings)
    root.empty_display_size = max(settings.building_width, settings.building_depth) * 0.35
    root[BUILDING_PROFILE_TAG] = spec.generator_profile
    _remove_generated_children(root)
    _build_by_profile(collection, root, mats, settings, spec)
    for obj in list(context.selected_objects):
        if obj != root:
            obj.select_set(False)
    root.select_set(True)
    context.view_layer.objects.active = root
    return True


def rebuild_active_building(context):
    return rebuild_building(context)


def create_building(context, building_type):
    scene = context.scene
    scene_settings = scene.bgcp_settings
    spec = building_type_spec(building_type)
    settings = scene_settings
    collection = ensure_collection(scene, scene_settings.collection_name)
    mats = materials_from_settings(settings)
    building_id = scene.bgcp_next_id
    scene.bgcp_next_id += 1

    root = bpy.data.objects.new(f"BGCP_{spec.label}_{building_id:03d}", None)
    root.empty_display_type = 'CUBE'
    root.empty_display_size = max(settings.building_width, settings.building_depth) * 0.35
    root.location = scene.cursor.location.copy()
    root[ADDON_TAG] = True
    root[ROOT_TAG] = True
    root[BUILDING_ID_TAG] = building_id
    root[BUILDING_TYPE_TAG] = spec.identifier
    root[BUILDING_PROFILE_TAG] = spec.generator_profile
    collection.objects.link(root)

    _build_by_profile(collection, root, mats, settings, spec)

    for obj in list(context.selected_objects):
        obj.select_set(False)
    root.select_set(True)
    context.view_layer.objects.active = root
    return root
