from math import cos, pi, sin, sqrt

import bpy

from .hall_parts import add_box, add_cylinder, add_mesh, add_mesh_with_material_indices


def _setting(settings, attr_name, fallback):
    return getattr(settings, attr_name, fallback)


def _material(mats, key, fallback="trim"):
    return mats.get(key) or mats.get(fallback)


def _linspace(start, end, count):
    if count <= 1:
        return [(start + end) * 0.5]
    step = (end - start) / (count - 1)
    return [start + step * index for index in range(count)]


def _add_platform(collection, root, mats, settings):
    width = settings.building_width
    depth = settings.building_depth
    height = _setting(settings, "platform_height", 0.8)
    margin = _setting(settings, "platform_margin", 1.0)
    platform_width = width + margin * 2.0
    platform_depth = depth + margin * 2.0
    stone = _material(mats, "wall")

    add_box(
        collection,
        root,
        "BGCP_Hall_Platform",
        (0.0, 0.0, height * 0.5),
        (platform_width, platform_depth, height),
        stone,
        "platform",
    )

    course_height = max(0.08, height / 5.0)
    for row in range(max(2, int(height / course_height))):
        z = course_height * (row + 0.5)
        add_box(
            collection,
            root,
            f"BGCP_Hall_Stone_Course_Front_{row:02d}",
            (0.0, -platform_depth * 0.5 - 0.015, z),
            (platform_width, 0.03, course_height * 0.45),
            _material(mats, "glass", "wall"),
            "stone_course",
        )

    return platform_width, platform_depth, height


def _add_stair_run(collection, root, mats, name, x, y_front, width, platform_height, steps):
    steps = max(1, int(steps))
    step_depth = max(0.16, platform_height * 0.42)
    step_height = platform_height / steps
    stone = _material(mats, "wall")
    rail = _material(mats, "glass", "wall")

    for index in range(steps):
        depth = step_depth * (steps - index)
        z = step_height * (index + 0.5)
        y = y_front - depth * 0.5
        add_box(
            collection,
            root,
            f"{name}_Step_{index:02d}",
            (x, y, z),
            (width, depth, step_height),
            stone,
            "stair",
        )

    rail_height = platform_height * 0.9
    for side in (-1.0, 1.0):
        add_box(
            collection,
            root,
            f"{name}_Rail_{'L' if side < 0 else 'R'}",
            (x + side * width * 0.55, y_front - step_depth * steps * 0.45, platform_height * 0.55),
            (0.12, step_depth * steps * 0.9, rail_height),
            rail,
            "stair_rail",
        )


def _add_side_stair_run(collection, root, mats, name, x_side, y, width, platform_height, steps, side):
    steps = max(1, int(steps))
    step_depth = max(0.16, platform_height * 0.42)
    step_height = platform_height / steps
    stone = _material(mats, "wall")
    rail = _material(mats, "glass", "wall")

    for index in range(steps):
        depth = step_depth * (steps - index)
        z = step_height * (index + 0.5)
        x = x_side + side * depth * 0.5
        add_box(
            collection,
            root,
            f"{name}_Step_{index:02d}",
            (x, y, z),
            (depth, width, step_height),
            stone,
            "stair",
        )

    rail_height = platform_height * 0.9
    for rail_side in (-1.0, 1.0):
        add_box(
            collection,
            root,
            f"{name}_Rail_{'F' if rail_side < 0 else 'B'}",
            (x_side + side * step_depth * steps * 0.45, y + rail_side * width * 0.55, platform_height * 0.55),
            (step_depth * steps * 0.9, 0.12, rail_height),
            rail,
            "stair_rail",
        )


def _stair_layout(settings, platform_width, platform_depth):
    base_width = _setting(settings, "stair_width", settings.building_width * 0.28)
    central_width = base_width * 2.0
    side_width = base_width * 0.55
    side_clearance = max(0.12, platform_depth * 0.04)
    side_y = -platform_depth * 0.5 + side_width * 0.55 + side_clearance
    return central_width, side_width, side_y


def _add_stairs(collection, root, mats, settings, platform_width, platform_depth, platform_height):
    front_y = -platform_depth * 0.5
    steps = _setting(settings, "stair_steps", 7)
    central_width, side_width, side_y = _stair_layout(settings, platform_width, platform_depth)
    _add_stair_run(
        collection,
        root,
        mats,
        "BGCP_Hall_Central_Stair",
        0.0,
        front_y,
        central_width,
        platform_height,
        steps,
    )

    if _setting(settings, "side_stairs_enabled", True):
        for side in (-1.0, 1.0):
            _add_side_stair_run(
                collection,
                root,
                mats,
                f"BGCP_Hall_Side_Stair_{'L' if side < 0 else 'R'}",
                side * platform_width * 0.5,
                side_y,
                side_width,
                platform_height,
                max(3, steps - 2),
                side,
            )


def _add_balustrade(collection, root, mats, settings, platform_width, platform_depth, platform_height):
    if not _setting(settings, "balustrade_enabled", True):
        return

    post_spacing = max(0.4, _setting(settings, "balustrade_post_spacing", 0.8))
    post_height = _setting(settings, "balustrade_height", 0.48)
    post_size = 0.08
    z = platform_height + post_height * 0.5
    rail_z = platform_height + post_height
    stone = _material(mats, "wall")

    x_positions = _linspace(-platform_width * 0.5, platform_width * 0.5, int(platform_width / post_spacing) + 1)
    y_positions = _linspace(-platform_depth * 0.5, platform_depth * 0.5, int(platform_depth / post_spacing) + 1)

    central_width, side_width, side_y = _stair_layout(settings, platform_width, platform_depth)
    opening_padding = post_spacing * 0.35
    front_openings = [(-central_width * 0.5 - opening_padding, central_width * 0.5 + opening_padding)]
    side_openings = []
    if _setting(settings, "side_stairs_enabled", True):
        side_openings.append((side_y - side_width * 0.55 - opening_padding, side_y + side_width * 0.55 + opening_padding))

    front_min = -platform_width * 0.5
    front_max = platform_width * 0.5
    side_min = -platform_depth * 0.5
    side_max = platform_depth * 0.5

    def in_front_opening(x):
        return any(start <= x <= end for start, end in front_openings)

    def in_side_opening(y):
        return any(start <= y <= end for start, end in side_openings)

    def add_front_rail_segments():
        openings = sorted((max(front_min, start), min(front_max, end)) for start, end in front_openings)
        start = front_min
        segment_index = 0
        for gap_start, gap_end in openings:
            if gap_start > start:
                center = (start + gap_start) * 0.5
                add_box(collection, root, f"BGCP_Hall_Balustrade_Rail_F_{segment_index:02d}", (center, -platform_depth * 0.5, rail_z), (gap_start - start, post_size, post_size), stone, "balustrade_rail")
                segment_index += 1
            start = max(start, gap_end)
        if start < front_max:
            center = (start + front_max) * 0.5
            add_box(collection, root, f"BGCP_Hall_Balustrade_Rail_F_{segment_index:02d}", (center, -platform_depth * 0.5, rail_z), (front_max - start, post_size, post_size), stone, "balustrade_rail")

    def add_side_rail_segments(x, side_name):
        openings = sorted((max(side_min, start), min(side_max, end)) for start, end in side_openings)
        start = side_min
        segment_index = 0
        for gap_start, gap_end in openings:
            if gap_start > start:
                center = (start + gap_start) * 0.5
                add_box(collection, root, f"BGCP_Hall_Balustrade_Rail_{side_name}_{segment_index:02d}", (x, center, rail_z), (post_size, gap_start - start, post_size), stone, "balustrade_rail")
                segment_index += 1
            start = max(start, gap_end)
        if start < side_max:
            center = (start + side_max) * 0.5
            add_box(collection, root, f"BGCP_Hall_Balustrade_Rail_{side_name}_{segment_index:02d}", (x, center, rail_z), (post_size, side_max - start, post_size), stone, "balustrade_rail")

    for y in (-platform_depth * 0.5, platform_depth * 0.5):
        for index, x in enumerate(x_positions):
            if y < 0.0 and in_front_opening(x):
                continue
            add_box(collection, root, f"BGCP_Hall_Baluster_X_{index:02d}_{'F' if y < 0 else 'B'}", (x, y, z), (post_size, post_size, post_height), stone, "balustrade_post")
        if y < 0.0:
            add_front_rail_segments()
        else:
            add_box(collection, root, "BGCP_Hall_Balustrade_Rail_B", (0.0, y, rail_z), (platform_width, post_size, post_size), stone, "balustrade_rail")

    for x in (-platform_width * 0.5, platform_width * 0.5):
        side_name = "L" if x < 0 else "R"
        for index, y in enumerate(y_positions):
            if in_side_opening(y):
                continue
            add_box(collection, root, f"BGCP_Hall_Baluster_Y_{index:02d}_{side_name}", (x, y, z), (post_size, post_size, post_height), stone, "balustrade_post")
        if side_openings:
            add_side_rail_segments(x, side_name)
        else:
            add_box(collection, root, f"BGCP_Hall_Balustrade_Rail_{side_name}", (x, 0.0, rail_z), (post_size, platform_depth, post_size), stone, "balustrade_rail")


def _add_front_door_bay(collection, root, mats, name, x_mid, y, base_z, bay_width, wall_height, panel_depth, door_height):
    wood = _material(mats, "door", "trim")
    frame = _material(mats, "trim")
    dark = _material(mats, "glass", "door")
    door_height = max(0.1, min(float(door_height), wall_height - 0.1))
    transom_height = wall_height - door_height
    transom_z = base_z + door_height + transom_height * 0.5

    add_box(collection, root, f"{name}_Door", (x_mid, y, base_z + door_height * 0.5), (bay_width, panel_depth, door_height), wood, "front_door_panel")
    add_box(collection, root, f"{name}_Top_Window", (x_mid, y, transom_z), (bay_width, panel_depth * 1.05, transom_height), dark, "front_top_window")

    rail_height = 0.055
    add_box(collection, root, f"{name}_Top_Window_Lintel", (x_mid, y - panel_depth * 0.15, transom_z + transom_height * 0.5), (bay_width, panel_depth * 1.2, rail_height), frame, "window_lintel")
    add_box(collection, root, f"{name}_Top_Window_Sill", (x_mid, y - panel_depth * 0.15, transom_z - transom_height * 0.5), (bay_width, panel_depth * 1.2, rail_height), frame, "window_sill")
    lower_bar_height = max(0.01, door_height - rail_height * 0.5)
    upper_bar_height = max(0.01, transom_height - rail_height)
    lower_bar_z = base_z + lower_bar_height * 0.5
    upper_bar_z = base_z + door_height + rail_height * 0.5 + upper_bar_height * 0.5
    for offset in (-0.25, 0.0, 0.25):
        bar_x = x_mid + bay_width * offset
        add_box(collection, root, f"{name}_Door_Bar_{offset:+.2f}", (bar_x, y - panel_depth * 0.2, lower_bar_z), (0.035, panel_depth * 1.25, lower_bar_height), frame, "door_bar")
        add_box(collection, root, f"{name}_Top_Window_Bar_{offset:+.2f}", (bar_x, y - panel_depth * 0.2, upper_bar_z), (0.035, panel_depth * 1.25, upper_bar_height), frame, "window_bar")

def _add_solid_wall_bay(collection, root, mats, name, location, size, lower_panel_height=None):
    panel = _material(mats, "door", "trim")
    frame = _material(mats, "trim")
    dark = _material(mats, "glass", "door")
    x, y, z = location
    sx, sy, sz = size
    bottom_z = z - sz * 0.5
    lower_height = sz
    if lower_panel_height is not None:
        lower_height = max(0.1, min(float(lower_panel_height), sz - 0.1))
    window_height = sz - lower_height

    add_box(collection, root, name, (x, y, bottom_z + lower_height * 0.5), (sx, sy, lower_height), panel, "solid_wood_wall")

    rail_height = 0.055
    if sx >= sy:
        rail_size = (sx, sy * 1.15, rail_height)
        add_box(collection, root, f"{name}_Bottom_Rail", (x, y, bottom_z), rail_size, frame, "wall_frame")
        add_box(collection, root, f"{name}_Left_Frame", (x - sx * 0.5, y, z), (0.045, sy * 1.2, sz), frame, "wall_frame")
        add_box(collection, root, f"{name}_Right_Frame", (x + sx * 0.5, y, z), (0.045, sy * 1.2, sz), frame, "wall_frame")
        if window_height > 0.001:
            window_z = bottom_z + lower_height + window_height * 0.5
            bar_height = max(0.01, window_height - rail_height)
            add_box(collection, root, f"{name}_Top_Window", (x, y, window_z), (sx, sy * 1.05, window_height), dark, "wall_top_window")
            add_box(collection, root, f"{name}_Top_Window_Sill", (x, y, bottom_z + lower_height), rail_size, frame, "window_sill")
            add_box(collection, root, f"{name}_Top_Window_Lintel", (x, y, z + sz * 0.5), rail_size, frame, "window_lintel")
            for offset in (-0.25, 0.0, 0.25):
                add_box(collection, root, f"{name}_Top_Window_Bar_{offset:+.2f}", (x + sx * offset, y, window_z), (0.035, sy * 1.25, bar_height), frame, "window_bar")
        else:
            add_box(collection, root, f"{name}_Top_Rail", (x, y, z + sz * 0.5), rail_size, frame, "wall_frame")
    else:
        rail_size = (sx * 1.15, sy, rail_height)
        add_box(collection, root, f"{name}_Bottom_Rail", (x, y, bottom_z), rail_size, frame, "wall_frame")
        add_box(collection, root, f"{name}_Front_Frame", (x, y - sy * 0.5, z), (sx * 1.2, 0.045, sz), frame, "wall_frame")
        add_box(collection, root, f"{name}_Back_Frame", (x, y + sy * 0.5, z), (sx * 1.2, 0.045, sz), frame, "wall_frame")
        if window_height > 0.001:
            window_z = bottom_z + lower_height + window_height * 0.5
            bar_height = max(0.01, window_height - rail_height)
            add_box(collection, root, f"{name}_Top_Window", (x, y, window_z), (sx * 1.05, sy, window_height), dark, "wall_top_window")
            add_box(collection, root, f"{name}_Top_Window_Sill", (x, y, bottom_z + lower_height), rail_size, frame, "window_sill")
            add_box(collection, root, f"{name}_Top_Window_Lintel", (x, y, z + sz * 0.5), rail_size, frame, "window_lintel")
            for offset in (-0.25, 0.0, 0.25):
                add_box(collection, root, f"{name}_Top_Window_Bar_{offset:+.2f}", (x, y + sy * offset, window_z), (sx * 1.25, 0.035, bar_height), frame, "window_bar")
        else:
            add_box(collection, root, f"{name}_Top_Rail", (x, y, z + sz * 0.5), rail_size, frame, "wall_frame")


def _add_window_wall_bay(collection, root, mats, name, location, size):
    frame = _material(mats, "trim")
    dark = _material(mats, "glass", "door")
    x, y, z = location
    sx, sy, sz = size
    bottom_z = z - sz * 0.5
    top_z = z + sz * 0.5
    rail_height = 0.055
    bar_height = max(0.01, sz - rail_height)

    if sx >= sy:
        rail_size = (sx, sy * 1.15, rail_height)
        add_box(collection, root, name, (x, y, z), (sx, sy * 1.05, sz), dark, "upper_window")
        add_box(collection, root, f"{name}_Bottom_Rail", (x, y, bottom_z), rail_size, frame, "window_sill")
        add_box(collection, root, f"{name}_Top_Rail", (x, y, top_z), rail_size, frame, "window_lintel")
        for offset in (-0.25, 0.0, 0.25):
            add_box(collection, root, f"{name}_Window_Bar_{offset:+.2f}", (x + sx * offset, y, z), (0.035, sy * 1.25, bar_height), frame, "window_bar")
    else:
        rail_size = (sx * 1.15, sy, rail_height)
        add_box(collection, root, name, (x, y, z), (sx * 1.05, sy, sz), dark, "upper_window")
        add_box(collection, root, f"{name}_Bottom_Rail", (x, y, bottom_z), rail_size, frame, "window_sill")
        add_box(collection, root, f"{name}_Top_Rail", (x, y, top_z), rail_size, frame, "window_lintel")
        for offset in (-0.25, 0.0, 0.25):
            add_box(collection, root, f"{name}_Window_Bar_{offset:+.2f}", (x, y + sy * offset, z), (sx * 1.25, 0.035, bar_height), frame, "window_bar")


def _add_columns_and_beams(collection, root, mats, settings, platform_height):
    width = settings.building_width
    depth = settings.building_depth
    bay_count = max(2, int(_setting(settings, "bay_count", 7)))
    side_bays = max(1, int(_setting(settings, "side_bay_count", 2)))
    column_radius = _setting(settings, "column_radius", 0.08)
    column_height = _setting(settings, "column_height", settings.floor_height)
    base_z = platform_height
    column_z = base_z + column_height * 0.5
    wood = _material(mats, "trim")

    x_positions = _linspace(-width * 0.5, width * 0.5, bay_count + 1)
    y_positions = _linspace(-depth * 0.5, depth * 0.5, side_bays + 2)

    for x_index, x in enumerate(x_positions):
        for y_index, y in enumerate(y_positions):
            add_cylinder(
                collection,
                root,
                f"BGCP_Hall_Column_{x_index:02d}_{y_index:02d}",
                (x, y, column_z),
                column_radius,
                column_height,
                wood,
                "column",
                vertices=28,
            )

    beam_height = 0.12
    beam_z = base_z + column_height + beam_height * 0.5
    for y_index, y in enumerate(y_positions):
        add_box(collection, root, f"BGCP_Hall_Long_Beam_{y_index:02d}", (0.0, y, beam_z), (width + column_radius * 4.0, 0.12, beam_height), wood, "beam")
    for x_index, x in enumerate(x_positions):
        add_box(collection, root, f"BGCP_Hall_Cross_Beam_{x_index:02d}", (x, 0.0, beam_z), (0.12, depth + column_radius * 4.0, beam_height), wood, "beam")

    wall_base_z = base_z
    wall_height = max(0.1, column_height)
    wall_z = wall_base_z + wall_height * 0.5
    panel_depth = 0.06
    wall_overlap = column_radius * 1.4
    door_height = _setting(settings, "main_door_height", wall_height * 0.68)
    for index in range(len(x_positions) - 1):
        x_mid = (x_positions[index] + x_positions[index + 1]) * 0.5
        bay_width = abs(x_positions[index + 1] - x_positions[index]) + wall_overlap
        _add_front_door_bay(collection, root, mats, f"BGCP_Hall_Front_Bay_{index:02d}", x_mid, -depth * 0.5 - 0.035, wall_base_z, bay_width, wall_height, panel_depth, door_height)
        _add_solid_wall_bay(collection, root, mats, f"BGCP_Hall_Back_Wall_{index:02d}", (x_mid, depth * 0.5 + 0.035, wall_z), (bay_width, panel_depth, wall_height), door_height)

    for side in (-1.0, 1.0):
        x = side * (width * 0.5 + 0.035)
        for index in range(len(y_positions) - 1):
            y_mid = (y_positions[index] + y_positions[index + 1]) * 0.5
            bay_depth = abs(y_positions[index + 1] - y_positions[index]) + wall_overlap
            _add_solid_wall_bay(collection, root, mats, f"BGCP_Hall_Side_Wall_{'L' if side < 0 else 'R'}_{index:02d}", (x, y_mid, wall_z), (panel_depth, bay_depth, wall_height), door_height)

    return base_z + column_height


def _hip_roof_mesh(width, depth, base_z, roof_height, thickness, eave_curve, ridge_ratio=0.62, gable_push=0.0):
    hw, hd = width * 0.5, depth * 0.5
    ridge_half = hw * max(0.15, min(0.92, ridge_ratio))
    curve_amount = max(0.0, float(eave_curve))
    edge_bow = curve_amount * 0.42
    curve_power = 1.0 + curve_amount * 2.4
    slope_segments = 8
    edge_segments = 10
    verts = []
    faces = []
    material_indices = []

    def roof_z(t):
        return base_z + roof_height * (t ** curve_power)

    def add_grid(rows, material_index_by_row=None):
        start = len(verts)
        for row in rows:
            verts.extend(row)
        for index in range(len(rows) - 1):
            row_start = start + index * edge_segments
            next_row_start = row_start + edge_segments
            for col in range(edge_segments - 1):
                faces.append((row_start + col, row_start + col + 1, next_row_start + col + 1, next_row_start + col))
                material_indices.append(material_index_by_row(index) if material_index_by_row else 0)

    front_rows = []
    back_rows = []
    left_side_rows = []
    right_side_rows = []
    for index in range(slope_segments + 1):
        t = index / slope_segments
        z = roof_z(t)
        front_y = -hd * (1.0 - t)
        back_y = hd * (1.0 - t)
        left_x = -hw + (hw - ridge_half) * t
        right_x = hw + (ridge_half - hw) * t
        side_y = hd * (1.0 - t)

        front_row = []
        back_row = []
        gable_t = 0.0
        if t > 0.58:
            gable_t = ((t - 0.58) / 0.42) ** 1.35
        gable_offset = max(0.0, float(gable_push)) * gable_t
        for col in range(edge_segments):
            u = col / (edge_segments - 1)
            row_left_x = left_x - gable_offset
            row_right_x = right_x + gable_offset
            x = row_left_x + (row_right_x - row_left_x) * u
            bow = edge_bow * (1.0 - t) * sin(pi * u)
            front_row.append((x, front_y + bow, z))
            back_row.append((x, back_y - bow, z))
        front_rows.append(front_row)
        back_rows.append(back_row)

        left_row = []
        right_row = []
        for col in range(edge_segments):
            u = col / (edge_segments - 1)
            y = -side_y + side_y * 2.0 * u
            bow = edge_bow * (1.0 - t) * sin(pi * u)
            left_row.append((left_x + bow - gable_offset, y, z))
            right_row.append((right_x - bow + gable_offset, -y, z))
        left_side_rows.append(left_row)
        right_side_rows.append(right_row)

    split_index = max(1, min(slope_segments - 1, round(slope_segments * 0.58)))
    add_grid(front_rows)
    add_grid(back_rows)
    add_grid(left_side_rows, lambda row_index: 1 if row_index >= split_index else 0)
    add_grid(right_side_rows, lambda row_index: 1 if row_index >= split_index else 0)

    return verts, faces, material_indices


def _add_upper_roof_side_split_trim(collection, root, mats, roof_width, roof_depth, upper_base_z, upper_height, curve, ridge_ratio):
    trim = _material(mats, "trim")
    hw, hd = roof_width * 0.5, roof_depth * 0.5
    ridge_half = hw * max(0.15, min(0.92, ridge_ratio))
    split_t = round(8 * 0.58) / 8
    curve_amount = max(0.0, float(curve))
    curve_power = 1.0 + curve_amount * 2.4
    z = upper_base_z + upper_height * (split_t ** curve_power)
    side_y = hd * (1.0 - split_t)
    left_x = -hw + (hw - ridge_half) * split_t
    right_x = hw + (ridge_half - hw) * split_t
    for name, x in (("L", left_x), ("R", right_x)):
        add_box(
            collection,
            root,
            f"BGCP_Hall_Upper_Roof_Side_Split_{name}",
            (x, 0.0, z + 0.01),
            (0.045, side_y * 2.0, 0.045),
            trim,
            "upper_roof_side_split",
        )


def _add_curved_eave_trim(collection, root, mats, name, width, depth, z, bow, side_name):
    trim = _material(mats, "trim")
    segments = 18
    trim_width = 0.08
    hw, hd = width * 0.5, depth * 0.5
    verts = []
    faces = []

    for index in range(segments + 1):
        u = index / segments
        curve_offset = max(0.0, float(bow)) * sin(pi * u)
        if side_name == "front":
            x = -hw + width * u
            y = -hd + curve_offset
            verts.extend(((x, y - trim_width * 0.5, z), (x, y + trim_width * 0.5, z)))
        elif side_name == "back":
            x = hw - width * u
            y = hd - curve_offset
            verts.extend(((x, y + trim_width * 0.5, z), (x, y - trim_width * 0.5, z)))
        elif side_name == "left":
            y = hd - depth * u
            x = -hw + curve_offset
            verts.extend(((x - trim_width * 0.5, y, z), (x + trim_width * 0.5, y, z)))
        else:
            y = -hd + depth * u
            x = hw - curve_offset
            verts.extend(((x + trim_width * 0.5, y, z), (x - trim_width * 0.5, y, z)))

    for index in range(segments):
        start = index * 2
        faces.append((start, start + 1, start + 3, start + 2))
    add_mesh(collection, root, name, verts, faces, trim, "eave_trim")


def _add_roof_seam(collection, root, mats, name, start_point, end_point, width=0.055, height=0.045, part_type="roof_seam"):
    trim = _material(mats, "trim")
    width = max(0.005, float(width))
    height = max(0.001, float(height))
    x1, y1, z1 = start_point
    x2, y2, z2 = end_point
    dx = x2 - x1
    dy = y2 - y1
    length = max(0.001, sqrt(dx * dx + dy * dy))
    off_x = -dy / length * width * 0.5
    off_y = dx / length * width * 0.5
    base_lift = 0.01
    z1_base = z1 + base_lift
    z2_base = z2 + base_lift
    z1_top = z1_base + height
    z2_top = z2_base + height
    verts = (
        (x1 + off_x, y1 + off_y, z1_base),
        (x2 + off_x, y2 + off_y, z2_base),
        (x2 - off_x, y2 - off_y, z2_base),
        (x1 - off_x, y1 - off_y, z1_base),
        (x1 + off_x, y1 + off_y, z1_top),
        (x2 + off_x, y2 + off_y, z2_top),
        (x2 - off_x, y2 - off_y, z2_top),
        (x1 - off_x, y1 - off_y, z1_top),
    )
    faces = (
        (4, 5, 6, 7),
        (0, 4, 7, 3),
        (1, 2, 6, 5),
        (0, 1, 5, 4),
        (3, 7, 6, 2),
    )
    add_mesh(collection, root, name, verts, faces, trim, part_type)


def _add_poly_roof_seam(collection, root, mats, name, points, width=0.055, height=0.045, part_type="roof_seam"):
    if len(points) < 2:
        return
    for index in range(len(points) - 1):
        _add_roof_seam(collection, root, mats, f"{name}_{index:02d}", points[index], points[index + 1], width, height, part_type)


def _add_roof_edge_lines(collection, root, mats, settings, name_prefix, width, depth, z, bow):
    line_width = _setting(settings, "roof_edge_line_width", 0.055)
    line_height = _setting(settings, "roof_edge_line_height", 0.035)
    hw, hd = width * 0.5, depth * 0.5
    segments = 18

    edges = {
        "Front": [],
        "Back": [],
        "Left": [],
        "Right": [],
    }
    for index in range(segments + 1):
        u = index / segments
        curve_offset = max(0.0, float(bow)) * sin(pi * u)
        x = -hw + width * u
        y = -hd + depth * u
        edges["Front"].append((x, -hd + curve_offset, z))
        edges["Back"].append((hw - width * u, hd - curve_offset, z))
        edges["Left"].append((-hw + curve_offset, hd - depth * u, z))
        edges["Right"].append((hw - curve_offset, y, z))

    for side_name, points in edges.items():
        _add_poly_roof_seam(
            collection,
            root,
            mats,
            f"{name_prefix}_Edge_Line_{side_name}",
            points,
            line_width,
            line_height,
            "roof_edge_line",
        )


def _curved_rect_ring(width, depth, z, bow, segments=16):
    hw, hd = width * 0.5, depth * 0.5
    points = []
    for index in range(segments + 1):
        u = index / segments
        points.append((-hw + width * u, -hd + bow * sin(pi * u), z))
    for index in range(1, segments + 1):
        u = index / segments
        points.append((hw - bow * sin(pi * u), -hd + depth * u, z))
    for index in range(1, segments + 1):
        u = index / segments
        points.append((hw - width * u, hd - bow * sin(pi * u), z))
    for index in range(1, segments):
        u = index / segments
        points.append((-hw + bow * sin(pi * u), hd - depth * u, z))
    return points


def _solidify_flat_polygon(points, thickness):
    thickness = max(0.001, float(thickness))
    top = list(points)
    bottom = [(x, y, z - thickness) for x, y, z in points]
    count = len(top)
    verts = top + bottom
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, nxt + count, index + count))
    return verts, faces


def _add_flat_curved_underside(collection, root, mats, name, width, depth, z, bow, thickness):
    points = _curved_rect_ring(width, depth, z, max(0.0, float(bow)))
    verts, faces = _solidify_flat_polygon(points, thickness)
    add_mesh(collection, root, name, verts, faces, _material(mats, "trim"), "roof_underside")


def _add_flat_tier_underside(collection, root, mats, name, outer_width, outer_depth, inner_width, inner_depth, z, bow, thickness):
    outer = _curved_rect_ring(outer_width, outer_depth, z, max(0.0, float(bow)))
    inner = list(reversed(_curved_rect_ring(inner_width, inner_depth, z, 0.0)))
    verts, faces = _solidify_flat_polygon(outer + inner, thickness)
    add_mesh(collection, root, name, verts, faces, _material(mats, "trim"), "roof_underside")


def _add_lower_tier_roof_seams(collection, root, mats, settings, outer_width, outer_depth, inner_width, inner_depth, base_z, top_z, curve):
    outer_hw, outer_hd = outer_width * 0.5, outer_depth * 0.5
    inner_hw, inner_hd = inner_width * 0.5, inner_depth * 0.5
    curve_amount = max(0.0, float(curve))
    edge_bow = curve_amount * 0.42
    curve_power = 1.0 + curve_amount * 2.4
    segments = 8
    seam_width = _setting(settings, "roof_line_width", 0.055)
    seam_height = _setting(settings, "roof_line_height", 0.045)

    def roof_z(t):
        return base_z + (top_z - base_z) * (t ** curve_power)

    corner_specs = (
        ("LF", -1.0, -1.0),
        ("LB", -1.0, 1.0),
        ("RF", 1.0, -1.0),
        ("RB", 1.0, 1.0),
    )
    for suffix, x_side, y_side in corner_specs:
        points = []
        for index in range(segments + 1):
            t = index / segments
            half_width = outer_hw + (inner_hw - outer_hw) * t
            half_depth = outer_hd + (inner_hd - outer_hd) * t
            bow = edge_bow * (1.0 - t) * sin(pi * t)
            x = x_side * (half_width - bow)
            y = y_side * (half_depth - bow)
            points.append((x, y, roof_z(t) + 0.018))
        _add_poly_roof_seam(collection, root, mats, f"BGCP_Hall_Lower_Roof_Corner_Seam_{suffix}", points, seam_width, seam_height)


def _add_upper_hip_roof_seams(collection, root, mats, settings, roof_width, roof_depth, upper_base_z, upper_height, curve, ridge_ratio, gable_push=0.0):
    hw, hd = roof_width * 0.5, roof_depth * 0.5
    ridge_half = hw * max(0.15, min(0.92, ridge_ratio))
    curve_amount = max(0.0, float(curve))
    edge_bow = curve_amount * 0.42
    curve_power = 1.0 + curve_amount * 2.4
    segments = 8
    seam_width = _setting(settings, "roof_line_width", 0.055)
    seam_height = _setting(settings, "roof_line_height", 0.045)

    def roof_z(t):
        return upper_base_z + upper_height * (t ** curve_power)

    seam_specs = (
        ("LF", -1.0, -1.0),
        ("LB", -1.0, 1.0),
        ("RF", 1.0, -1.0),
        ("RB", 1.0, 1.0),
    )
    for suffix, x_side, y_side in seam_specs:
        points = []
        for index in range(segments + 1):
            t = index / segments
            x = x_side * (hw + (ridge_half - hw) * t)
            y = y_side * (hd * (1.0 - t))
            bow = edge_bow * (1.0 - t) * sin(pi * t)
            x -= x_side * bow
            y -= y_side * bow
            if t > 0.58:
                gable_t = ((t - 0.58) / 0.42) ** 1.35
                x += x_side * max(0.0, float(gable_push)) * gable_t
            points.append((x, y, roof_z(t) + 0.018))
        _add_poly_roof_seam(collection, root, mats, f"BGCP_Hall_Upper_Roof_Hip_Seam_{suffix}", points, seam_width, seam_height)


def _yellow_tile_material(segment_length=0.55):
    color = (1.0, 0.72, 0.08, 1.0)
    mat = bpy.data.materials.get("BGCP_Roof_Tile_Yellow")
    if mat is None:
        mat = bpy.data.materials.new("BGCP_Roof_Tile_Yellow")
    mat.diffuse_color = color
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    wave = nodes.new(type="ShaderNodeTexWave")
    ramp = nodes.new(type="ShaderNodeValToRGB")

    output.location = (520, 0)
    bsdf.location = (300, 0)
    ramp.location = (80, 80)
    wave.location = (-160, 80)

    if hasattr(wave, "wave_type"):
        wave.wave_type = 'BANDS'
    if hasattr(wave, "bands_direction"):
        wave.bands_direction = 'Z'
    scale = max(0.2, 1.0 / max(0.12, float(segment_length)))
    scale_input = wave.inputs.get("Scale")
    distortion_input = wave.inputs.get("Distortion")
    if scale_input is not None:
        scale_input.default_value = scale
    if distortion_input is not None:
        distortion_input.default_value = 0.0

    ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = color
    ramp.color_ramp.elements[1].position = 0.94
    ramp.color_ramp.elements[1].color = (1.0, 0.88, 0.32, 1.0)
    end_element = ramp.color_ramp.elements.new(0.985)
    end_element.color = color

    if bsdf is not None:
        base_color = bsdf.inputs.get("Base Color")
        roughness = bsdf.inputs.get("Roughness")
        if roughness is not None:
            roughness.default_value = 0.48
        if base_color is not None and ramp.outputs.get("Color") is not None:
            links.new(ramp.outputs["Color"], base_color)
        elif base_color is not None:
            base_color.default_value = color
        surface = output.inputs.get("Surface")
        bsdf_output = bsdf.outputs.get("BSDF")
        if surface is not None and bsdf_output is not None:
            links.new(bsdf_output, surface)
    wave_output = wave.outputs.get("Fac") or wave.outputs.get("Color")
    if wave_output is not None and ramp.inputs.get("Fac") is not None:
        links.new(wave_output, ramp.inputs["Fac"])
    return mat


def _add_roof_tile_rib(collection, root, name, points, width, height, material):
    if len(points) < 2:
        return

    width = max(0.02, float(width))
    height = max(0.01, float(height))
    cross_segments = 6
    verts = []
    faces = []

    for index, point in enumerate(points):
        if index == 0:
            other = points[1]
            dx = other[0] - point[0]
            dy = other[1] - point[1]
        elif index == len(points) - 1:
            other = points[index - 1]
            dx = point[0] - other[0]
            dy = point[1] - other[1]
        else:
            prev_point = points[index - 1]
            next_point = points[index + 1]
            dx = next_point[0] - prev_point[0]
            dy = next_point[1] - prev_point[1]
        length = max(0.001, sqrt(dx * dx + dy * dy))
        off_x = -dy / length
        off_y = dx / length

        x, y, z = point
        for segment in range(cross_segments + 1):
            angle = pi - (pi * segment / cross_segments)
            offset = cos(angle) * width * 0.5
            lift = sin(angle) * height
            verts.append((x + off_x * offset, y + off_y * offset, z + 0.018 + lift))

    row_size = cross_segments + 1
    for index in range(len(points) - 1):
        row_start = index * row_size
        next_start = row_start + row_size
        for segment in range(cross_segments):
            faces.append((row_start + segment, row_start + segment + 1, next_start + segment + 1, next_start + segment))
    faces.append(tuple(range(row_size - 1, -1, -1)))
    last_start = (len(points) - 1) * row_size
    faces.append(tuple(range(last_start, last_start + row_size)))
    add_mesh(collection, root, name, verts, faces, material, "roof_tile_rib")


def _add_roof_tile_cap(collection, root, name, point, side_name, radius, thickness, material):
    radius = max(0.03, float(radius))
    thickness = max(0.01, float(thickness))
    segments = 18
    x, y, z = point
    z += radius * 0.72

    if side_name == "front":
        normal = (0.0, -1.0)
    elif side_name == "back":
        normal = (0.0, 1.0)
    elif side_name == "left":
        normal = (-1.0, 0.0)
    else:
        normal = (1.0, 0.0)

    verts = []
    for depth_side in (-0.5, 0.5):
        for index in range(segments):
            angle = (index / segments) * pi * 2.0
            horizontal = cos(angle) * radius
            vertical = sin(angle) * radius
            if normal[0] == 0.0:
                verts.append((x + horizontal, y + normal[1] * thickness * depth_side, z + vertical))
            else:
                verts.append((x + normal[0] * thickness * depth_side, y + horizontal, z + vertical))

    faces = [tuple(range(segments - 1, -1, -1)), tuple(range(segments, segments * 2))]
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((index, nxt, nxt + segments, index + segments))
    add_mesh(collection, root, name, verts, faces, material, "roof_tile_cap")


def _tile_centers(span, tile_width, tile_gap):
    span = max(0.001, float(span))
    tile_width = max(0.02, float(tile_width))
    spacing = max(tile_width * 1.05, tile_width + max(0.0, float(tile_gap)))
    count = max(1, int(max(0.0, span - tile_width) / spacing) + 1)
    total_width = (count - 1) * spacing
    start = -total_width * 0.5
    return [start + spacing * index for index in range(count)]


def _add_roof_tiles_from_paths(collection, root, name_prefix, paths, cap_points, settings):
    if not _setting(settings, "roof_tiles_enabled", True):
        return

    rib_width = _setting(settings, "roof_tile_rib_width", 0.16)
    rib_height = _setting(settings, "roof_tile_rib_height", 0.07)
    segment_length = _setting(settings, "roof_tile_segment_length", 0.55)
    material = _yellow_tile_material(segment_length)
    cap_radius = _setting(settings, "roof_tile_cap_radius", 0.11)
    cap_thickness = max(0.035, rib_width * 0.45)

    for index, points in enumerate(paths):
        name = f"{name_prefix}_Tile_Rib_{index:02d}"
        _add_roof_tile_rib(collection, root, name, points, rib_width, rib_height, material)
    for index, (point, side_name) in enumerate(cap_points):
        _add_roof_tile_cap(collection, root, f"{name_prefix}_Tile_Cap_{index:02d}", point, side_name, cap_radius, cap_thickness, material)


def _add_lower_roof_tiles(collection, root, settings, outer_width, outer_depth, inner_width, inner_depth, base_z, top_z, curve):
    tile_width = _setting(settings, "roof_tile_rib_width", 0.16)
    tile_gap = _setting(settings, "roof_tile_gap", 0.10)
    outer_hw, outer_hd = outer_width * 0.5, outer_depth * 0.5
    inner_hw, inner_hd = inner_width * 0.5, inner_depth * 0.5
    curve_amount = max(0.0, float(curve))
    curve_power = 1.0 + curve_amount * 2.4
    segments = 5
    t_end = 1.0
    paths = []
    cap_points = []

    def roof_z(t):
        return base_z + (top_z - base_z) * (t ** curve_power)

    for side_name, y_side in (("front", -1.0), ("back", 1.0)):
        for x_const in _tile_centers(outer_width, tile_width, tile_gap):
            max_t = t_end
            if abs(x_const) > inner_hw and outer_hw > inner_hw:
                max_t = min(t_end, max(0.12, (outer_hw - abs(x_const)) / (outer_hw - inner_hw)))
            points = []
            for segment in range(segments + 1):
                t = max_t * segment / segments
                half_depth = outer_hd + (inner_hd - outer_hd) * t
                x = x_const
                y = y_side * half_depth
                points.append((x, y, roof_z(t)))
            paths.append(points)
            cap_points.append((points[0], side_name))

    for side_name, x_side in (("left", -1.0), ("right", 1.0)):
        for y_const in _tile_centers(outer_depth, tile_width, tile_gap):
            max_t = t_end
            if abs(y_const) > inner_hd and outer_hd > inner_hd:
                max_t = min(t_end, max(0.12, (outer_hd - abs(y_const)) / (outer_hd - inner_hd)))
            points = []
            for segment in range(segments + 1):
                t = max_t * segment / segments
                half_width = outer_hw + (inner_hw - outer_hw) * t
                x = x_side * half_width
                y = y_const
                points.append((x, y, roof_z(t)))
            paths.append(points)
            cap_points.append((points[0], side_name))

    _add_roof_tiles_from_paths(collection, root, "BGCP_Hall_Lower_Roof", paths, cap_points, settings)


def _add_upper_roof_tiles(collection, root, settings, roof_width, roof_depth, base_z, roof_height, curve, ridge_ratio, gable_push):
    tile_width = _setting(settings, "roof_tile_rib_width", 0.16)
    tile_gap = _setting(settings, "roof_tile_gap", 0.10)
    hw, hd = roof_width * 0.5, roof_depth * 0.5
    ridge_half = hw * max(0.15, min(0.92, ridge_ratio))
    curve_amount = max(0.0, float(curve))
    curve_power = 1.0 + curve_amount * 2.4
    segments = 5
    t_end = 1.0
    side_tile_t_end = round(8 * 0.58) / 8
    paths = []
    cap_points = []

    def roof_z(t):
        return base_z + roof_height * (t ** curve_power)

    def gable_offset(t):
        if t <= 0.58:
            return 0.0
        return max(0.0, float(gable_push)) * (((t - 0.58) / 0.42) ** 1.35)

    def front_row_bounds(t):
        return (
            -hw + (hw - ridge_half) * t - gable_offset(t),
            hw + (ridge_half - hw) * t + gable_offset(t),
        )

    def max_front_t_for_x(x):
        left, right = front_row_bounds(t_end)
        if left <= x <= right:
            return t_end
        low, high = 0.0, t_end
        for _ in range(14):
            mid = (low + high) * 0.5
            left, right = front_row_bounds(mid)
            if left <= x <= right:
                low = mid
            else:
                high = mid
        return max(0.12, low)

    for side_name, y_side in (("front", -1.0), ("back", 1.0)):
        for x_const in _tile_centers(roof_width, tile_width, tile_gap):
            max_t = max_front_t_for_x(x_const)
            points = []
            for segment in range(segments + 1):
                t = max_t * segment / segments
                front_back_y = y_side * hd * (1.0 - t)
                x = x_const
                y = front_back_y
                points.append((x, y, roof_z(t)))
            paths.append(points)
            cap_points.append((points[0], side_name))

    for side_name, x_side in (("left", -1.0), ("right", 1.0)):
        for y_const in _tile_centers(roof_depth, tile_width, tile_gap):
            max_t = side_tile_t_end
            if abs(y_const) > hd * (1.0 - side_tile_t_end):
                max_t = min(side_tile_t_end, max(0.12, 1.0 - abs(y_const) / hd))
            points = []
            for segment in range(segments + 1):
                t = max_t * segment / segments
                side_y = hd * (1.0 - t)
                side_x = x_side * (hw + (ridge_half - hw) * t)
                x = side_x + x_side * gable_offset(t)
                y = y_const
                points.append((x, y, roof_z(t)))
            paths.append(points)
            cap_points.append((points[0], side_name))

    _add_roof_tiles_from_paths(collection, root, "BGCP_Hall_Upper_Roof", paths, cap_points, settings)


def _tier_roof_mesh(outer_width, outer_depth, inner_width, inner_depth, base_z, top_z, thickness, eave_curve):
    outer_hw, outer_hd = outer_width * 0.5, outer_depth * 0.5
    inner_hw, inner_hd = inner_width * 0.5, inner_depth * 0.5
    curve_amount = max(0.0, float(eave_curve))
    edge_bow = curve_amount * 0.42
    curve_power = 1.0 + curve_amount * 2.4
    slope_segments = 8
    edge_segments = 10
    verts = []
    faces = []

    def roof_z(t):
        return base_z + (top_z - base_z) * (t ** curve_power)

    def add_grid(rows):
        start = len(verts)
        for row in rows:
            verts.extend(row)
        for index in range(len(rows) - 1):
            row_start = start + index * edge_segments
            next_row_start = row_start + edge_segments
            for col in range(edge_segments - 1):
                faces.append((row_start + col, row_start + col + 1, next_row_start + col + 1, next_row_start + col))

    front_rows = []
    back_rows = []
    left_rows = []
    right_rows = []
    for index in range(slope_segments + 1):
        t = index / slope_segments
        z = roof_z(t)
        half_width = outer_hw + (inner_hw - outer_hw) * t
        half_depth = outer_hd + (inner_hd - outer_hd) * t
        front_row = []
        back_row = []
        for col in range(edge_segments):
            u = col / (edge_segments - 1)
            x = -half_width + half_width * 2.0 * u
            bow = edge_bow * (1.0 - t) * sin(pi * u)
            front_row.append((x, -half_depth + bow, z))
            back_row.append((-x, half_depth - bow, z))
        front_rows.append(front_row)
        back_rows.append(back_row)

        left_row = []
        right_row = []
        for col in range(edge_segments):
            u = col / (edge_segments - 1)
            y = -half_depth + half_depth * 2.0 * u
            bow = edge_bow * (1.0 - t) * sin(pi * u)
            left_row.append((-half_width + bow, half_depth - half_depth * 2.0 * u, z))
            right_row.append((half_width - bow, y, z))
        left_rows.append(left_row)
        right_rows.append(right_row)

    add_grid(front_rows)
    add_grid(back_rows)
    add_grid(left_rows)
    add_grid(right_rows)

    return verts, faces


def _add_upper_body(collection, root, mats, settings, base_z, width, depth, lower_roof_contact_z):
    bay_count = max(2, int(_setting(settings, "bay_count", 7)))
    column_radius = _setting(settings, "column_radius", 0.08) * 0.72
    height = _setting(settings, "upper_platform_height", settings.column_height * 0.42)
    deck_height = 0.12
    wood = _material(mats, "trim")

    add_box(
        collection,
        root,
        "BGCP_Hall_Upper_Platform",
        (0.0, 0.0, base_z + deck_height * 0.5),
        (width, depth, deck_height),
        wood,
        "upper_platform",
    )
    skirt_height = max(0.08, base_z - lower_roof_contact_z)
    if skirt_height > 0.081:
        add_box(
            collection,
            root,
            "BGCP_Hall_Upper_Platform_Skirt",
            (0.0, 0.0, base_z - skirt_height * 0.5),
            (width, depth, skirt_height),
            _material(mats, "trim"),
            "upper_platform_skirt",
        )

    column_z = base_z + deck_height + height * 0.5
    x_positions = _linspace(-width * 0.5, width * 0.5, bay_count + 1)
    y_positions = (-depth * 0.5, depth * 0.5)
    for x_index, x in enumerate(x_positions):
        for y_index, y in enumerate(y_positions):
            add_cylinder(
                collection,
                root,
                f"BGCP_Hall_Upper_Column_{x_index:02d}_{y_index:02d}",
                (x, y, column_z),
                column_radius,
                height,
                wood,
                "upper_column",
                vertices=24,
            )

    beam_z = base_z + deck_height + height + 0.06
    for y_index, y in enumerate(y_positions):
        add_box(collection, root, f"BGCP_Hall_Upper_Long_Beam_{y_index:02d}", (0.0, y, beam_z), (width + column_radius * 4.0, 0.09, 0.12), wood, "upper_beam")

    wall_base_z = base_z + deck_height
    wall_height = max(0.1, height)
    wall_z = wall_base_z + wall_height * 0.5
    panel_depth = 0.05
    wall_overlap = column_radius * 1.4
    for index in range(len(x_positions) - 1):
        x_mid = (x_positions[index] + x_positions[index + 1]) * 0.5
        bay_width = abs(x_positions[index + 1] - x_positions[index]) + wall_overlap
        _add_window_wall_bay(collection, root, mats, f"BGCP_Hall_Upper_Front_Window_{index:02d}", (x_mid, -depth * 0.5 - 0.03, wall_z), (bay_width, panel_depth, wall_height))
        _add_window_wall_bay(collection, root, mats, f"BGCP_Hall_Upper_Back_Window_{index:02d}", (x_mid, depth * 0.5 + 0.03, wall_z), (bay_width, panel_depth, wall_height))

    for side in (-1.0, 1.0):
        x = side * (width * 0.5 + 0.03)
        _add_window_wall_bay(collection, root, mats, f"BGCP_Hall_Upper_Side_Window_{'L' if side < 0 else 'R'}", (x, 0.0, wall_z), (panel_depth, depth + wall_overlap, wall_height))

    return base_z + deck_height + height


def _add_layered_roof(collection, root, mats, settings, column_top_z):
    width = settings.building_width
    depth = settings.building_depth
    overhang = _setting(settings, "eave_overhang", settings.roof_overhang)
    curve = _setting(settings, "roof_curve", 0.18)
    tile = _material(mats, "roof")
    trim = _material(mats, "trim")
    underside_thickness = _setting(settings, "roof_underside_thickness", 0.08)
    underside_z_offset = _setting(settings, "roof_underside_z_offset", 0.0)

    lower_height = _setting(settings, "lower_roof_height", settings.roof_height * 0.55)
    upper_height = _setting(settings, "upper_roof_height", settings.roof_height)
    lower_z = column_top_z + 0.16
    upper_body_width = width * 0.76
    upper_body_depth = depth * 0.72
    upper_body_base_z = lower_z + lower_height

    lower_outer_width = width + overhang * 2.0
    lower_outer_depth = depth + overhang * 2.0
    lower_roof_thickness = 0.18
    verts, faces = _tier_roof_mesh(lower_outer_width, lower_outer_depth, upper_body_width, upper_body_depth, lower_z, upper_body_base_z, lower_roof_thickness, curve)
    add_mesh(collection, root, "BGCP_Hall_Lower_Roof", verts, faces, tile, "roof_lower")
    _add_lower_roof_tiles(collection, root, settings, lower_outer_width, lower_outer_depth, upper_body_width, upper_body_depth, lower_z, upper_body_base_z, curve)
    lower_eave_z = lower_z
    lower_bow = max(0.0, float(curve)) * 0.42
    _add_flat_tier_underside(collection, root, mats, "BGCP_Hall_Lower_Roof_Underside", lower_outer_width, lower_outer_depth, upper_body_width, upper_body_depth, lower_eave_z - 0.015 + underside_z_offset, lower_bow, underside_thickness)
    _add_lower_tier_roof_seams(collection, root, mats, settings, lower_outer_width, lower_outer_depth, upper_body_width, upper_body_depth, lower_z, upper_body_base_z, curve)

    upper_base_z = _add_upper_body(collection, root, mats, settings, upper_body_base_z, upper_body_width, upper_body_depth, upper_body_base_z) + 0.08
    upper_width = upper_body_width
    upper_depth = upper_body_depth
    upper_roof_width = upper_width + overhang * 1.2
    upper_roof_depth = upper_depth + overhang * 1.2
    upper_roof_curve = curve * 1.2
    upper_ridge_ratio = 0.58
    gable_push = (upper_roof_width - upper_width) * 0.5
    upper_roof_thickness = 0.16
    verts, faces, material_indices = _hip_roof_mesh(upper_roof_width, upper_roof_depth, upper_base_z, upper_height, upper_roof_thickness, upper_roof_curve, ridge_ratio=upper_ridge_ratio, gable_push=gable_push)
    add_mesh_with_material_indices(collection, root, "BGCP_Hall_Upper_Roof", verts, faces, (tile, _material(mats, "door", "trim")), material_indices, "roof_upper")
    _add_upper_roof_tiles(collection, root, settings, upper_roof_width, upper_roof_depth, upper_base_z, upper_height, upper_roof_curve, upper_ridge_ratio, gable_push)
    upper_bow = max(0.0, float(upper_roof_curve)) * 0.42
    _add_flat_curved_underside(collection, root, mats, "BGCP_Hall_Upper_Roof_Underside", upper_roof_width, upper_roof_depth, upper_base_z - 0.015 + underside_z_offset, upper_bow, underside_thickness)
    _add_upper_hip_roof_seams(collection, root, mats, settings, upper_roof_width, upper_roof_depth, upper_base_z, upper_height, upper_roof_curve, upper_ridge_ratio, gable_push)
    _add_upper_roof_side_split_trim(collection, root, mats, upper_roof_width, upper_roof_depth, upper_base_z, upper_height, upper_roof_curve, upper_ridge_ratio)

    ridge_z = upper_base_z + upper_height + 0.04
    ridge_overlap = _setting(settings, "roof_line_width", 0.055)
    ridge_length = upper_roof_width * upper_ridge_ratio + gable_push * 2.0 + ridge_overlap
    add_box(collection, root, "BGCP_Hall_Ridge_Beam", (0.0, 0.0, ridge_z), (ridge_length, 0.12, 0.08), trim, "roof_ridge")

    upper_eave_z = upper_base_z
    _add_roof_edge_lines(collection, root, mats, settings, "BGCP_Hall_Lower_Roof", lower_outer_width, lower_outer_depth, lower_eave_z, lower_bow)
    _add_roof_edge_lines(collection, root, mats, settings, "BGCP_Hall_Upper_Roof", upper_roof_width, upper_roof_depth, upper_eave_z, upper_bow)

    return upper_base_z + upper_height


def build_hall(collection, root, mats, settings):
    platform_width, platform_depth, platform_height = _add_platform(collection, root, mats, settings)
    _add_stairs(collection, root, mats, settings, platform_width, platform_depth, platform_height)
    _add_balustrade(collection, root, mats, settings, platform_width, platform_depth, platform_height)
    column_top_z = _add_columns_and_beams(collection, root, mats, settings, platform_height)
    _add_layered_roof(collection, root, mats, settings, column_top_z)
