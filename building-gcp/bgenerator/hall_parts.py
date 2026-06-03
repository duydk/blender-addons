from math import cos, pi, sin

import bpy

from .tags import ADDON_TAG, BUILDING_ID_TAG, BUILDING_PROFILE_TAG, BUILDING_TYPE_TAG, PART_TAG


def tag_part(obj, parent, part_type):
    obj.parent = parent
    obj[ADDON_TAG] = True
    obj[BUILDING_ID_TAG] = parent.get(BUILDING_ID_TAG)
    obj[BUILDING_TYPE_TAG] = parent.get(BUILDING_TYPE_TAG)
    obj[BUILDING_PROFILE_TAG] = parent.get(BUILDING_PROFILE_TAG)
    obj[PART_TAG] = part_type
    return obj


def box_mesh(name, size):
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


def add_box(collection, parent, name, location, size, material, part_type):
    obj = bpy.data.objects.new(name, box_mesh(name, size))
    obj.location = location
    tag_part(obj, parent, part_type)
    if material is not None:
        obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def cylinder_mesh(name, radius, depth, vertices=24):
    radius = max(0.001, float(radius))
    depth = max(0.001, float(depth))
    vertices = max(8, int(vertices))
    hz = depth * 0.5
    verts = []
    for z in (-hz, hz):
        for index in range(vertices):
            angle = (index / vertices) * pi * 2.0
            verts.append((cos(angle) * radius, sin(angle) * radius, z))

    bottom = tuple(range(vertices - 1, -1, -1))
    top = tuple(range(vertices, vertices * 2))
    faces = [bottom, top]
    for index in range(vertices):
        nxt = (index + 1) % vertices
        faces.append((index, nxt, nxt + vertices, index + vertices))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, (), faces)
    mesh.update()
    return mesh


def add_cylinder(collection, parent, name, location, radius, depth, material, part_type, vertices=24):
    obj = bpy.data.objects.new(name, cylinder_mesh(name, radius, depth, vertices))
    obj.location = location
    tag_part(obj, parent, part_type)
    if material is not None:
        obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def add_mesh(collection, parent, name, verts, faces, material, part_type):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, (), faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    tag_part(obj, parent, part_type)
    if material is not None:
        obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def add_mesh_with_material_indices(collection, parent, name, verts, faces, materials, material_indices, part_type):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, (), faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    tag_part(obj, parent, part_type)
    for material in materials:
        if material is not None:
            obj.data.materials.append(material)
    for index, polygon in enumerate(obj.data.polygons):
        if index < len(material_indices):
            polygon.material_index = material_indices[index]
    collection.objects.link(obj)
    return obj
