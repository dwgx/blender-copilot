"""
Measurement and verification tools — adapted from blender-ai-mcp patterns.

Provides distance measurement, dimension checking, overlap detection,
symmetry verification, and mesh quality analysis.
"""


def register_measurement_tools(mcp, send_command_fn):
    """Register measurement and verification MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def measure_distance(object_a: str, object_b: str) -> dict:
        """Measure the distance between two objects (center to center).

        Args:
            object_a: First object name
            object_b: Second object name
        """
        code = f"""import bpy, json
a = bpy.data.objects.get('{object_a}')
b = bpy.data.objects.get('{object_b}')
if not a:
    result = "Error: Object '{object_a}' not found"
elif not b:
    result = "Error: Object '{object_b}' not found"
else:
    dist = (a.location - b.location).length
    delta = [round(b.location[i] - a.location[i], 4) for i in range(3)]
    result = json.dumps({{
        'distance': round(dist, 4),
        'delta': {{'x': delta[0], 'y': delta[1], 'z': delta[2]}},
        'from': '{object_a}',
        'to': '{object_b}',
    }})
"""
        return _exec(code)

    @mcp.tool()
    def measure_dimensions(object_name: str) -> dict:
        """Measure object dimensions (bounding box size in world space).

        Returns width (X), depth (Y), height (Z), volume estimate,
        and world-space bounding box corners.
        """
        code = f"""import bpy, json
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    dims = obj.dimensions
    bb = [obj.matrix_world @ __import__('mathutils').Vector(c) for c in obj.bound_box]
    bb_min = [min(v[i] for v in bb) for i in range(3)]
    bb_max = [max(v[i] for v in bb) for i in range(3)]

    info = {{
        'object': obj.name,
        'dimensions': {{
            'width': round(dims.x, 4),
            'depth': round(dims.y, 4),
            'height': round(dims.z, 4),
        }},
        'volume_estimate': round(dims.x * dims.y * dims.z, 4),
        'bounding_box': {{
            'min': [round(x, 4) for x in bb_min],
            'max': [round(x, 4) for x in bb_max],
        }},
        'location': [round(x, 4) for x in obj.location],
    }}

    if obj.type == 'MESH' and obj.data:
        info['mesh'] = {{
            'vertices': len(obj.data.vertices),
            'faces': len(obj.data.polygons),
            'edges': len(obj.data.edges),
        }}

    result = json.dumps(info, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def measure_overlap(object_a: str, object_b: str) -> dict:
        """Check if two objects' bounding boxes overlap.

        Returns overlap status, overlap volume, and intersection dimensions.
        """
        code = f"""import bpy, json
from mathutils import Vector

a = bpy.data.objects.get('{object_a}')
b = bpy.data.objects.get('{object_b}')
if not a:
    result = "Error: Object '{object_a}' not found"
elif not b:
    result = "Error: Object '{object_b}' not found"
else:
    def world_bb(obj):
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        mn = [min(v[i] for v in corners) for i in range(3)]
        mx = [max(v[i] for v in corners) for i in range(3)]
        return mn, mx

    a_min, a_max = world_bb(a)
    b_min, b_max = world_bb(b)

    overlap = all(a_min[i] < b_max[i] and b_min[i] < a_max[i] for i in range(3))

    if overlap:
        o_min = [max(a_min[i], b_min[i]) for i in range(3)]
        o_max = [min(a_max[i], b_max[i]) for i in range(3)]
        o_dims = [o_max[i] - o_min[i] for i in range(3)]
        o_vol = o_dims[0] * o_dims[1] * o_dims[2]
    else:
        o_dims = [0, 0, 0]
        o_vol = 0
        gap = []
        for i in range(3):
            if a_max[i] < b_min[i]:
                gap.append(b_min[i] - a_max[i])
            elif b_max[i] < a_min[i]:
                gap.append(a_min[i] - b_max[i])
            else:
                gap.append(0)

    info = {{
        'overlapping': overlap,
        'overlap_dimensions': [round(x, 4) for x in o_dims],
        'overlap_volume': round(o_vol, 4),
    }}
    if not overlap:
        info['gap'] = [round(x, 4) for x in gap]

    result = json.dumps(info)
"""
        return _exec(code)

    @mcp.tool()
    def measure_symmetry(object_name: str, axis: str = "X", threshold: float = 0.001) -> dict:
        """Check mesh symmetry across an axis.

        Analyzes vertex positions to determine how symmetric the mesh is.

        Args:
            object_name: Mesh object to check
            axis: Symmetry axis (X, Y, or Z)
            threshold: Distance threshold for considering vertices as symmetric
        """
        axis_idx = {"X": 0, "Y": 1, "Z": 2}.get(axis, 0)
        code = f"""import bpy, json

obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    mesh = obj.data
    axis = {axis_idx}
    threshold = {threshold}

    positive = []
    negative = []
    center = []

    for v in mesh.vertices:
        co = v.co
        if abs(co[axis]) < threshold:
            center.append(v.index)
        elif co[axis] > 0:
            positive.append(v)
        else:
            negative.append(v)

    # Try to match positive to negative
    matched = 0
    unmatched_pos = []
    neg_coords = []
    for v in negative:
        mirror = list(v.co)
        mirror[axis] = -mirror[axis]
        neg_coords.append(mirror)

    for v in positive:
        found = False
        for i, nc in enumerate(neg_coords):
            dist = sum((v.co[j] - nc[j])**2 for j in range(3)) ** 0.5
            if dist < threshold:
                matched += 1
                found = True
                neg_coords[i] = [999, 999, 999]  # mark used
                break
        if not found:
            unmatched_pos.append(v.index)

    total_pairs = max(len(positive), len(negative))
    symmetry_pct = (matched / total_pairs * 100) if total_pairs > 0 else 100

    result = json.dumps({{
        'object': obj.name,
        'axis': '{axis}',
        'symmetry_percent': round(symmetry_pct, 1),
        'matched_pairs': matched,
        'center_vertices': len(center),
        'positive_side': len(positive),
        'negative_side': len(negative),
        'unmatched': len(unmatched_pos),
        'total_vertices': len(mesh.vertices),
    }}, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def mesh_quality_check(object_name: str) -> dict:
        """Analyze mesh quality — find non-manifold edges, loose vertices,
        degenerate faces, duplicate vertices, and other issues.

        Essential for 3D printing, game assets, and VRChat avatars.
        """
        code = f"""import bpy, bmesh, json

obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)

    issues = {{}}

    # Non-manifold edges
    non_manifold = [e.index for e in bm.edges if not e.is_manifold]
    issues['non_manifold_edges'] = len(non_manifold)

    # Loose vertices (not connected to any face)
    loose_verts = [v.index for v in bm.verts if not v.link_faces]
    issues['loose_vertices'] = len(loose_verts)

    # Loose edges (not connected to any face)
    loose_edges = [e.index for e in bm.edges if not e.link_faces]
    issues['loose_edges'] = len(loose_edges)

    # Degenerate faces (zero area)
    degen_faces = [f.index for f in bm.faces if f.calc_area() < 1e-6]
    issues['degenerate_faces'] = len(degen_faces)

    # Duplicate vertices (very close together)
    dupes = 0
    checked = set()
    for v in bm.verts:
        if v.index in checked:
            continue
        for v2 in bm.verts:
            if v2.index <= v.index or v2.index in checked:
                continue
            if (v.co - v2.co).length < 0.0001:
                dupes += 1
                checked.add(v2.index)
                break
    issues['duplicate_vertices'] = dupes

    # N-gons (faces with > 4 vertices)
    ngons = [f.index for f in bm.faces if len(f.verts) > 4]
    issues['ngons'] = len(ngons)

    # Triangles count
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)

    total_issues = sum(v for k, v in issues.items())

    bpy.ops.object.mode_set(mode='OBJECT')

    result = json.dumps({{
        'object': obj.name,
        'quality': 'CLEAN' if total_issues == 0 else 'HAS_ISSUES',
        'total_issues': total_issues,
        'issues': issues,
        'topology': {{
            'vertices': len(bm.verts),
            'edges': len(bm.edges),
            'faces': len(bm.faces),
            'triangles': tris,
            'quads': quads,
            'ngons': len(ngons),
        }},
    }}, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def measure_alignment(objects: list, axis: str = "X") -> dict:
        """Check if multiple objects are aligned along an axis.

        Args:
            objects: List of object names to check alignment
            axis: Axis to check (X, Y, or Z)
        """
        objects_str = str(objects)
        axis_idx = {"X": 0, "Y": 1, "Z": 2}.get(axis, 0)
        code = f"""import bpy, json

names = {objects_str}
axis = {axis_idx}
axis_name = '{axis}'

positions = []
for name in names:
    obj = bpy.data.objects.get(name)
    if obj:
        positions.append({{'name': name, 'pos': round(obj.location[axis], 4)}})

if len(positions) < 2:
    result = "Error: Need at least 2 valid objects"
else:
    values = [p['pos'] for p in positions]
    spread = max(values) - min(values)
    avg = sum(values) / len(values)
    aligned = spread < 0.01

    result = json.dumps({{
        'axis': axis_name,
        'aligned': aligned,
        'spread': round(spread, 4),
        'average_position': round(avg, 4),
        'objects': positions,
    }}, indent=2)
"""
        return _exec(code)
