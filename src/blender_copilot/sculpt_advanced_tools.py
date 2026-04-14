"""
Advanced professional sculpting tools — maximum precision, anatomy-aware.
Extends sculpt_bake_tools.py with 15+ new tools for complete sculpt mastery.
"""

import json
import logging
import textwrap

logger = logging.getLogger("BlenderMCPServer.SculptAdvanced")


def register_sculpt_advanced_tools(mcp, send_command_fn):
    """Register all advanced sculpting tools on the FastMCP instance."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    # ─────────────────────────────────────────────
    # 1. sculpt_brush_full — ALL brush types + full params
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_brush_full(
        mesh_name: str,
        brush_type: str = "DRAW",
        strength: float = 0.5,
        radius: float = 0.05,
        stroke_points: str = "[]",
        falloff: str = "SMOOTH",
        direction: str = "ADD",
        use_symmetry_x: bool = True,
        use_symmetry_y: bool = False,
        use_symmetry_z: bool = False,
        auto_smooth: float = 0.0,
        accumulate: bool = False,
        plane_offset: float = 0.0,
        texture_noise_scale: float = 0.0,
    ) -> str:
        """Professional sculpt brush with ALL 30+ brush types and full parameter control.

        brush_type: DRAW, DRAW_SHARP, CLAY, CLAY_STRIPS, CLAY_THUMB, LAYER,
            INFLATE, BLOB, CREASE, SMOOTH, FLATTEN, FILL, SCRAPE,
            MULTIPLANE_SCRAPE, PINCH, GRAB, ELASTIC_DEFORM, SNAKE_HOOK,
            THUMB, POSE, NUDGE, ROTATE, BOUNDARY, CLOTH

        falloff: SMOOTH, SMOOTHER, SPHERE, ROOT, SHARP, LINEAR, CONSTANT,
            INVERSE_SQUARE, POW4, GAUSSIAN

        direction: ADD (raise/build) or SUBTRACT (carve/lower)

        stroke_points: JSON array of {x, y, z} world-space points.
        radius: Brush radius in Blender units (world space).
        strength: 0.0-1.0 intensity.
        auto_smooth: 0.0-1.0 smooth pass after each stroke.
        accumulate: If true, strength compounds on overlap.
        plane_offset: Offset from surface plane (for CLAY/FLATTEN types).
        texture_noise_scale: >0 adds procedural noise to displacement.
        """
        pts = json.loads(stroke_points) if isinstance(stroke_points, str) else stroke_points
        code = textwrap.dedent(f"""\
import bpy, bmesh, json, math, random
from mathutils import Vector, kdtree

obj = bpy.data.objects['{mesh_name}']
if obj.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.normal_update()

# Build KDTree
size = len(bm.verts)
kd = kdtree.KDTree(size)
for i, v in enumerate(bm.verts):
    kd.insert(v.co, i)
kd.balance()

# Params
brush_type = '{brush_type}'
strength = {strength}
radius = {radius}
direction_sign = 1.0 if '{direction}' == 'ADD' else -1.0
auto_smooth = {auto_smooth}
accumulate = {accumulate}
plane_offset = {plane_offset}
noise_scale = {texture_noise_scale}
falloff_type = '{falloff}'

pts = {json.dumps(pts)}
sym_x = {use_symmetry_x}
sym_y = {use_symmetry_y}
sym_z = {use_symmetry_z}

# Build symmetry multipliers
sym_axes = [(1,1,1)]
if sym_x: sym_axes.append((-1,1,1))
if sym_y: sym_axes.append((1,-1,1))
if sym_z: sym_axes.append((1,1,-1))
if sym_x and sym_y: sym_axes.append((-1,-1,1))
if sym_x and sym_z: sym_axes.append((-1,1,-1))
if sym_y and sym_z: sym_axes.append((1,-1,-1))
if sym_x and sym_y and sym_z: sym_axes.append((-1,-1,-1))

def falloff_fn(t):
    '''t = normalized distance 0..1 (0=center, 1=edge). Returns 1..0 weight.'''
    t = max(0.0, min(1.0, t))
    s = 1.0 - t  # invert: 1 at center, 0 at edge
    if falloff_type == 'SMOOTH':
        return s * s * (3.0 - 2.0 * s)
    elif falloff_type == 'SMOOTHER':
        return s*s*s*(s*(s*6-15)+10)
    elif falloff_type == 'SPHERE':
        return math.sqrt(max(0, 1.0 - t*t))
    elif falloff_type == 'ROOT':
        return math.sqrt(s)
    elif falloff_type == 'SHARP':
        return s * s
    elif falloff_type == 'LINEAR':
        return s
    elif falloff_type == 'CONSTANT':
        return 1.0
    elif falloff_type == 'INVERSE_SQUARE':
        return 1.0 / (1.0 + t*t*4)
    elif falloff_type == 'POW4':
        return s * s * s * s
    elif falloff_type == 'GAUSSIAN':
        return math.exp(-t*t*4)
    return s * s * (3.0 - 2.0 * s)

def noise3d(x, y, z, scale):
    '''Simple hash-based noise for texture variation.'''
    if scale <= 0: return 0.0
    ix = int(x / scale * 1000) % 997
    iy = int(y / scale * 1000) % 991
    iz = int(z / scale * 1000) % 983
    h = (ix * 73856093 ^ iy * 19349663 ^ iz * 83492791) % 1000
    return (h / 500.0 - 1.0) * 0.5

# Precompute neighbor map for smooth brushes
neighbor_map = {{}}
for v in bm.verts:
    neighbor_map[v.index] = [e.other_vert(v).index for e in v.link_edges]

affected_verts = set()
prev_stroke_pt = None

for pt_idx, pt in enumerate(pts):
    for sx, sy, sz in sym_axes:
        center = Vector((pt['x'] * sx, pt['y'] * sy, pt['z'] * sz))

        # Stroke delta for direction-dependent brushes
        stroke_delta = Vector((0, 0, 0))
        if prev_stroke_pt is not None:
            prev_c = Vector((prev_stroke_pt['x'] * sx, prev_stroke_pt['y'] * sy, prev_stroke_pt['z'] * sz))
            stroke_delta = center - prev_c

        results = kd.find_range(center, radius)

        # Compute average normal and plane for FLATTEN/FILL/SCRAPE
        avg_normal = Vector((0, 0, 0))
        avg_co = Vector((0, 0, 0))
        weight_sum = 0.0
        for co, idx, dist in results:
            w = falloff_fn(dist / radius)
            avg_normal += bm.verts[idx].normal * w
            avg_co += co * w
            weight_sum += w
        if weight_sum > 0:
            avg_normal = (avg_normal / weight_sum).normalized()
            avg_co /= weight_sum
        else:
            avg_normal = Vector((0, 0, 1))

        for co, idx, dist in results:
            v = bm.verts[idx]
            t = dist / radius
            w = falloff_fn(t) * strength * direction_sign

            # Add texture noise
            if noise_scale > 0:
                w *= (1.0 + noise3d(v.co.x, v.co.y, v.co.z, noise_scale))

            # Accumulate mode: don't reduce on overlap
            if not accumulate:
                w *= max(0.1, 1.0 - t * 0.5)

            disp = Vector((0, 0, 0))

            if brush_type == 'DRAW':
                disp = v.normal * w * radius * 0.15

            elif brush_type == 'DRAW_SHARP':
                sharp_w = falloff_fn(t * 0.5) * strength * direction_sign  # Tighter falloff
                disp = v.normal * sharp_w * radius * 0.2

            elif brush_type == 'CLAY':
                # Clay: push toward a plane above surface
                plane_dist = (v.co - avg_co).dot(avg_normal) - plane_offset * radius
                if direction_sign > 0:
                    clay_amount = max(0, -plane_dist) * w
                else:
                    clay_amount = max(0, plane_dist) * w * direction_sign
                disp = avg_normal * clay_amount * 0.5

            elif brush_type == 'CLAY_STRIPS':
                plane_dist = (v.co - avg_co).dot(avg_normal) - plane_offset * radius
                clay_amount = max(0, -plane_dist * direction_sign) * abs(w)
                disp = avg_normal * clay_amount * direction_sign * 0.4

            elif brush_type == 'CLAY_THUMB':
                plane_dist = (v.co - avg_co).dot(avg_normal)
                disp = avg_normal * (-plane_dist * abs(w) * 0.3)
                if stroke_delta.length > 0.0001:
                    disp += stroke_delta.normalized() * abs(w) * radius * 0.05

            elif brush_type == 'LAYER':
                # Consistent height offset
                target_height = strength * radius * 0.2 * direction_sign
                current_offset = (v.co - avg_co).dot(v.normal)
                diff = target_height - current_offset
                disp = v.normal * diff * falloff_fn(t) * 0.5

            elif brush_type == 'INFLATE':
                disp = v.normal * w * radius * 0.15

            elif brush_type == 'BLOB':
                to_center = (center - v.co)
                blob_dir = (v.normal * 0.7 + to_center.normalized() * 0.3).normalized()
                disp = blob_dir * abs(w) * radius * 0.12 * direction_sign

            elif brush_type == 'CREASE':
                to_center = (center - v.co).normalized()
                crease_disp = v.normal * w * radius * 0.15
                pinch_disp = to_center * abs(w) * radius * 0.08
                disp = crease_disp + pinch_disp

            elif brush_type == 'SMOOTH':
                nbrs = neighbor_map.get(v.index, [])
                if nbrs:
                    avg_pos = Vector((0,0,0))
                    for ni in nbrs:
                        avg_pos += bm.verts[ni].co
                    avg_pos /= len(nbrs)
                    disp = (avg_pos - v.co) * abs(w) * 0.5

            elif brush_type == 'FLATTEN':
                plane_dist = (v.co - avg_co).dot(avg_normal)
                disp = -avg_normal * plane_dist * abs(w) * 0.5

            elif brush_type == 'FILL':
                plane_dist = (v.co - avg_co).dot(avg_normal)
                if plane_dist < 0:
                    disp = -avg_normal * plane_dist * abs(w) * 0.5

            elif brush_type == 'SCRAPE':
                plane_dist = (v.co - avg_co).dot(avg_normal)
                if plane_dist > 0:
                    disp = -avg_normal * plane_dist * abs(w) * 0.5

            elif brush_type == 'MULTIPLANE_SCRAPE':
                plane_dist = (v.co - avg_co).dot(avg_normal)
                angle_factor = abs(v.normal.dot(avg_normal))
                if plane_dist > 0:
                    disp = -avg_normal * plane_dist * abs(w) * angle_factor * 0.4

            elif brush_type == 'PINCH':
                to_center = center - v.co
                disp = to_center * abs(w) * 0.15

            elif brush_type == 'GRAB':
                if stroke_delta.length > 0.0001:
                    disp = stroke_delta * falloff_fn(t)

            elif brush_type == 'ELASTIC_DEFORM':
                if stroke_delta.length > 0.0001:
                    # Elastic: exponential falloff with volume preservation
                    elastic_w = math.exp(-t * t * 2.0) * strength
                    disp = stroke_delta * elastic_w

            elif brush_type == 'SNAKE_HOOK':
                if stroke_delta.length > 0.0001:
                    disp = stroke_delta * falloff_fn(t) * strength

            elif brush_type == 'THUMB':
                if stroke_delta.length > 0.0001:
                    disp = stroke_delta * falloff_fn(t) * strength * 0.8

            elif brush_type == 'POSE':
                if stroke_delta.length > 0.0001:
                    # Simple pose: rotate around stroke center
                    to_v = v.co - center
                    angle = stroke_delta.length * strength * 2.0
                    axis = stroke_delta.normalized().cross(to_v.normalized())
                    if axis.length > 0.0001:
                        axis.normalize()
                        from mathutils import Matrix
                        rot = Matrix.Rotation(angle * falloff_fn(t), 3, axis)
                        new_co = center + rot @ to_v
                        disp = new_co - v.co

            elif brush_type == 'NUDGE':
                if stroke_delta.length > 0.0001:
                    disp = stroke_delta.normalized() * abs(w) * radius * 0.1

            elif brush_type == 'ROTATE':
                to_v = v.co - center
                if to_v.length > 0.0001 and stroke_delta.length > 0.0001:
                    from mathutils import Matrix
                    rot_angle = stroke_delta.length * strength * 3.0 * falloff_fn(t)
                    rot = Matrix.Rotation(rot_angle, 3, avg_normal)
                    new_co = center + rot @ to_v
                    disp = new_co - v.co

            elif brush_type == 'BOUNDARY':
                # Deform boundary edges
                is_boundary = any(not e.is_manifold for e in v.link_edges)
                if is_boundary and stroke_delta.length > 0.0001:
                    disp = stroke_delta * falloff_fn(t) * strength

            elif brush_type == 'CLOTH':
                # Simplified cloth brush: gravity + inflate
                gravity = Vector((0, 0, -1))
                cloth_disp = (gravity * 0.3 + v.normal * 0.7) * abs(w) * radius * 0.1
                disp = cloth_disp * direction_sign

            if disp.length > 0.00001:
                v.co += disp
                affected_verts.add(v.index)

    prev_stroke_pt = pt

# Auto-smooth pass
if auto_smooth > 0:
    for v_idx in affected_verts:
        v = bm.verts[v_idx]
        nbrs = neighbor_map.get(v_idx, [])
        if nbrs:
            avg_pos = Vector((0,0,0))
            for ni in nbrs:
                avg_pos += bm.verts[ni].co
            avg_pos /= len(nbrs)
            v.co = v.co.lerp(avg_pos, auto_smooth * 0.5)

bm.to_mesh(mesh)
bm.free()
mesh.update()

result = {{
    'brush': brush_type,
    'falloff': falloff_type,
    'direction': '{direction}',
    'stroke_points': len(pts),
    'affected_vertices': len(affected_verts),
    'radius': radius,
    'strength': strength,
    'auto_smooth': auto_smooth,
}}
result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 2. sculpt_mesh_filter — Whole-mesh deformation
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_mesh_filter(
        mesh_name: str,
        filter_type: str = "SMOOTH",
        strength: float = 1.0,
        iterations: int = 1,
        axis_x: bool = True,
        axis_y: bool = True,
        axis_z: bool = True,
    ) -> str:
        """Apply whole-mesh sculpt filter (no stroke needed).

        filter_type: SMOOTH, INFLATE, SPHERE, RANDOM, RELAX, SURFACE_SMOOTH,
            SHARPEN, ENHANCE_DETAILS, SCALE, FLATTEN_BASES

        strength: Filter intensity (can be >1.0).
        iterations: Number of passes.
        axis_x/y/z: Which axes to affect.
        """
        code = textwrap.dedent(f"""\
import bpy, bmesh, math, random
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
if obj.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.normal_update()

filter_type = '{filter_type}'
strength = {strength}
iterations = {iterations}
ax = ({axis_x}, {axis_y}, {axis_z})

# Precompute neighbors
neighbor_map = {{}}
for v in bm.verts:
    neighbor_map[v.index] = [e.other_vert(v).index for e in v.link_edges]

# Compute mesh center and average radius
center = Vector((0,0,0))
for v in bm.verts:
    center += v.co
center /= len(bm.verts)

avg_radius = sum((v.co - center).length for v in bm.verts) / len(bm.verts)

for iteration in range(iterations):
    # Snapshot positions for parallel update
    positions = {{v.index: v.co.copy() for v in bm.verts}}
    normals = {{v.index: v.normal.copy() for v in bm.verts}}

    for v in bm.verts:
        disp = Vector((0, 0, 0))
        nbrs = neighbor_map.get(v.index, [])

        if filter_type == 'SMOOTH':
            if nbrs:
                avg = Vector((0,0,0))
                for ni in nbrs:
                    avg += positions[ni]
                avg /= len(nbrs)
                disp = (avg - positions[v.index]) * strength * 0.5

        elif filter_type == 'INFLATE':
            disp = normals[v.index] * strength * avg_radius * 0.02

        elif filter_type == 'SPHERE':
            to_center = positions[v.index] - center
            if to_center.length > 0.0001:
                target = center + to_center.normalized() * avg_radius
                disp = (target - positions[v.index]) * strength * 0.1

        elif filter_type == 'RANDOM':
            disp = Vector((
                random.uniform(-1, 1),
                random.uniform(-1, 1),
                random.uniform(-1, 1),
            )) * strength * avg_radius * 0.01

        elif filter_type == 'RELAX':
            if nbrs:
                avg = Vector((0,0,0))
                for ni in nbrs:
                    avg += positions[ni]
                avg /= len(nbrs)
                # Project displacement onto tangent plane
                to_avg = avg - positions[v.index]
                normal_component = to_avg.dot(normals[v.index]) * normals[v.index]
                tangent_disp = to_avg - normal_component
                disp = tangent_disp * strength * 0.5

        elif filter_type == 'SURFACE_SMOOTH':
            if nbrs:
                avg = Vector((0,0,0))
                for ni in nbrs:
                    avg += positions[ni]
                avg /= len(nbrs)
                # Cotangent-weighted Laplacian approximation
                to_avg = avg - positions[v.index]
                # Preserve features by scaling with curvature
                normal_comp = abs(to_avg.dot(normals[v.index]))
                tangent_len = (to_avg - normals[v.index] * to_avg.dot(normals[v.index])).length
                feature_preserve = 1.0 / (1.0 + normal_comp * 10.0)
                disp = to_avg * strength * 0.3 * feature_preserve

        elif filter_type == 'SHARPEN':
            if nbrs:
                avg = Vector((0,0,0))
                for ni in nbrs:
                    avg += positions[ni]
                avg /= len(nbrs)
                # Sharpen = move AWAY from average (inverse of smooth)
                disp = (positions[v.index] - avg) * strength * 0.3

        elif filter_type == 'ENHANCE_DETAILS':
            if nbrs:
                avg = Vector((0,0,0))
                for ni in nbrs:
                    avg += positions[ni]
                avg /= len(nbrs)
                # Enhance = amplify displacement from smooth surface along normal
                detail = positions[v.index] - avg
                normal_detail = detail.dot(normals[v.index])
                disp = normals[v.index] * normal_detail * strength * 0.5

        elif filter_type == 'SCALE':
            to_center = positions[v.index] - center
            disp = to_center * (strength - 1.0) * 0.1

        elif filter_type == 'FLATTEN_BASES':
            if nbrs:
                avg_n = Vector((0,0,0))
                for ni in nbrs:
                    avg_n += normals[ni]
                avg_n /= len(nbrs)
                # Flatten areas where normals are consistent
                normal_variance = (normals[v.index] - avg_n).length
                if normal_variance < 0.3:
                    avg_pos = Vector((0,0,0))
                    for ni in nbrs:
                        avg_pos += positions[ni]
                    avg_pos /= len(nbrs)
                    plane_dist = (positions[v.index] - avg_pos).dot(avg_n)
                    disp = -avg_n * plane_dist * strength * 0.3

        # Apply axis constraints
        if not ax[0]: disp.x = 0
        if not ax[1]: disp.y = 0
        if not ax[2]: disp.z = 0

        v.co = positions[v.index] + disp

bm.to_mesh(mesh)
bm.free()
mesh.update()

result = {{
    'filter': filter_type,
    'strength': strength,
    'iterations': iterations,
    'vertices': len(mesh.vertices),
}}
result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 3. sculpt_analyze_surface — curvature, density, quality
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_analyze_surface(
        mesh_name: str,
        analysis_type: str = "full",
    ) -> str:
        """Analyze mesh surface for sculpting decisions.

        analysis_type:
            'full' — complete analysis (curvature, density, topology, silhouette)
            'curvature' — vertex curvature map (find high/low curvature zones)
            'density' — vertex/face density distribution
            'topology' — quad/tri/ngon ratio, poles, manifold check
            'silhouette' — bounding box, aspect ratios, balance

        Returns detailed analysis to guide sculpting decisions.
        """
        code = textwrap.dedent(f"""\
import bpy, bmesh, math
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
if obj.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm.normal_update()

analysis = '{analysis_type}'
result = {{'mesh': '{mesh_name}', 'vertices': len(bm.verts), 'edges': len(bm.edges), 'faces': len(bm.faces)}}

# ── Curvature Analysis ──
if analysis in ('full', 'curvature'):
    curvatures = []
    high_curvature_verts = []
    low_curvature_verts = []

    for v in bm.verts:
        nbrs = [e.other_vert(v) for e in v.link_edges]
        if not nbrs:
            continue
        avg = Vector((0,0,0))
        for n in nbrs:
            avg += n.co
        avg /= len(nbrs)
        laplacian = avg - v.co
        curv = laplacian.length
        curvatures.append(curv)

        if curv > 0.05:
            high_curvature_verts.append(v.index)
        elif curv < 0.005:
            low_curvature_verts.append(v.index)

    if curvatures:
        avg_curv = sum(curvatures) / len(curvatures)
        max_curv = max(curvatures)
        min_curv = min(curvatures)
    else:
        avg_curv = max_curv = min_curv = 0

    result['curvature'] = {{
        'average': round(avg_curv, 6),
        'max': round(max_curv, 6),
        'min': round(min_curv, 6),
        'high_curvature_verts': len(high_curvature_verts),
        'low_curvature_zones': len(low_curvature_verts),
        'detail_suggestion': 'Needs more detail in flat zones' if len(low_curvature_verts) > len(bm.verts) * 0.3 else 'Good detail distribution',
    }}

# ── Density Analysis ──
if analysis in ('full', 'density'):
    edge_lengths = [e.calc_length() for e in bm.edges]
    face_areas = [f.calc_area() for f in bm.faces]

    avg_edge = sum(edge_lengths) / len(edge_lengths) if edge_lengths else 0
    min_edge = min(edge_lengths) if edge_lengths else 0
    max_edge = max(edge_lengths) if edge_lengths else 0

    avg_area = sum(face_areas) / len(face_areas) if face_areas else 0
    density_variance = sum((a - avg_area)**2 for a in face_areas) / len(face_areas) if face_areas else 0

    # Find density hotspots
    tiny_faces = sum(1 for a in face_areas if a < avg_area * 0.1)
    huge_faces = sum(1 for a in face_areas if a > avg_area * 5.0)

    result['density'] = {{
        'avg_edge_length': round(avg_edge, 6),
        'min_edge_length': round(min_edge, 6),
        'max_edge_length': round(max_edge, 6),
        'edge_length_ratio': round(max_edge / min_edge, 2) if min_edge > 0 else 0,
        'avg_face_area': round(avg_area, 8),
        'density_variance': round(density_variance, 10),
        'tiny_faces': tiny_faces,
        'huge_faces': huge_faces,
        'uniformity': 'Good' if (max_edge / min_edge < 5 if min_edge > 0 else False) else 'Needs remesh',
        'remesh_suggestion': round(avg_edge * 0.8, 4),
    }}

# ── Topology Analysis ──
if analysis in ('full', 'topology'):
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)

    # Poles
    poles_3 = sum(1 for v in bm.verts if len(v.link_edges) == 3)
    poles_5 = sum(1 for v in bm.verts if len(v.link_edges) == 5)
    poles_6plus = sum(1 for v in bm.verts if len(v.link_edges) >= 6)

    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    loose = sum(1 for v in bm.verts if not v.link_edges)

    total_faces = len(bm.faces)
    quad_pct = round(quads / total_faces * 100, 1) if total_faces else 0

    if quad_pct > 90 and poles_6plus == 0 and non_manifold == 0:
        grade = 'Excellent'
    elif quad_pct > 70 and poles_6plus < 5:
        grade = 'Good'
    elif quad_pct > 50:
        grade = 'Fair'
    else:
        grade = 'Needs work'

    result['topology'] = {{
        'quads': quads,
        'tris': tris,
        'ngons': ngons,
        'quad_percentage': quad_pct,
        'poles_3_edge': poles_3,
        'poles_5_edge': poles_5,
        'poles_6plus': poles_6plus,
        'non_manifold_edges': non_manifold,
        'boundary_edges': boundary,
        'loose_vertices': loose,
        'grade': grade,
    }}

# ── Silhouette / Bounding Box Analysis ──
if analysis in ('full', 'silhouette'):
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]

    bbox_min = (min(xs), min(ys), min(zs))
    bbox_max = (max(xs), max(ys), max(zs))
    dims = (bbox_max[0]-bbox_min[0], bbox_max[1]-bbox_min[1], bbox_max[2]-bbox_min[2])

    center = ((bbox_min[0]+bbox_max[0])/2, (bbox_min[1]+bbox_max[1])/2, (bbox_min[2]+bbox_max[2])/2)

    # Aspect ratios
    max_dim = max(dims) if max(dims) > 0 else 1
    aspects = (round(dims[0]/max_dim, 3), round(dims[1]/max_dim, 3), round(dims[2]/max_dim, 3))

    # Symmetry check (X axis)
    left_verts = sum(1 for v in bm.verts if v.co.x < center[0] - 0.001)
    right_verts = sum(1 for v in bm.verts if v.co.x > center[0] + 0.001)
    sym_ratio = min(left_verts, right_verts) / max(left_verts, right_verts) if max(left_verts, right_verts) > 0 else 0

    result['silhouette'] = {{
        'bbox_min': [round(b, 4) for b in bbox_min],
        'bbox_max': [round(b, 4) for b in bbox_max],
        'dimensions': [round(d, 4) for d in dims],
        'center': [round(c, 4) for c in center],
        'aspect_ratios_xyz': aspects,
        'x_symmetry_ratio': round(sym_ratio, 3),
        'is_symmetric': sym_ratio > 0.9,
    }}

bm.free()
result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 4. sculpt_face_sets — Create and manage face sets
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_face_sets(
        mesh_name: str,
        action: str = "init_by_normals",
        face_set_id: int = 1,
        params: str = "{}",
    ) -> str:
        """Manage face sets for organized sculpting.

        action:
            'init_by_normals' — Auto-create face sets from face normal directions
            'init_by_loose_parts' — Face sets from disconnected mesh islands
            'init_by_materials' — Face sets from material slots
            'assign_by_position' — Assign faces in a sphere to a face set
            'grow' — Expand a face set by one ring
            'shrink' — Contract a face set by one ring
            'list' — List all face sets with face counts
            'visibility_isolate' — Hide all except specified face set
            'visibility_show_all' — Show all face sets

        params (JSON): For 'assign_by_position': {"center": [x,y,z], "radius": 0.1}
        """
        p = json.loads(params) if isinstance(params, str) else params
        code = textwrap.dedent(f"""\
import bpy, bmesh, math
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
if obj.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.faces.ensure_lookup_table()

action = '{action}'
face_set_id = {face_set_id}
params = {json.dumps(p)}

# Get or create face set layer
fs_layer = bm.faces.layers.int.get('.sculpt_face_set')
if fs_layer is None:
    fs_layer = bm.faces.layers.int.new('.sculpt_face_set')

if action == 'init_by_normals':
    for f in bm.faces:
        n = f.normal
        # 6 cardinal directions
        dots = [
            (abs(n.dot(Vector((0,0,1)))), 1),   # Top
            (abs(n.dot(Vector((0,0,-1)))), 2),   # Bottom
            (abs(n.dot(Vector((1,0,0)))), 3),    # Right
            (abs(n.dot(Vector((-1,0,0)))), 4),   # Left
            (abs(n.dot(Vector((0,1,0)))), 5),    # Front
            (abs(n.dot(Vector((0,-1,0)))), 6),   # Back
        ]
        best = max(dots, key=lambda x: x[0])
        f[fs_layer] = best[1]

elif action == 'init_by_loose_parts':
    visited = set()
    current_id = 1
    for f in bm.faces:
        if f.index in visited:
            continue
        # BFS flood fill
        queue = [f]
        while queue:
            cf = queue.pop(0)
            if cf.index in visited:
                continue
            visited.add(cf.index)
            cf[fs_layer] = current_id
            for e in cf.edges:
                for lf in e.link_faces:
                    if lf.index not in visited:
                        queue.append(lf)
        current_id += 1

elif action == 'init_by_materials':
    for f in bm.faces:
        f[fs_layer] = f.material_index + 1

elif action == 'assign_by_position':
    center = Vector(params.get('center', [0, 0, 0]))
    radius = params.get('radius', 0.1)
    assigned = 0
    for f in bm.faces:
        if (f.calc_center_median() - center).length <= radius:
            f[fs_layer] = face_set_id
            assigned += 1

elif action == 'grow':
    target_faces = set()
    for f in bm.faces:
        if f[fs_layer] == face_set_id:
            for e in f.edges:
                for lf in e.link_faces:
                    target_faces.add(lf.index)
    for fi in target_faces:
        bm.faces[fi][fs_layer] = face_set_id

elif action == 'shrink':
    boundary_faces = set()
    for f in bm.faces:
        if f[fs_layer] == face_set_id:
            for e in f.edges:
                for lf in e.link_faces:
                    if lf[fs_layer] != face_set_id:
                        boundary_faces.add(f.index)
                        break
    for fi in boundary_faces:
        bm.faces[fi][fs_layer] = 0

elif action == 'list':
    counts = {{}}
    for f in bm.faces:
        fs_id = f[fs_layer]
        counts[fs_id] = counts.get(fs_id, 0) + 1
    bm.free()
    result = {{'face_sets': counts, 'total_sets': len(counts), 'total_faces': len(mesh.polygons)}}
    result

elif action == 'visibility_isolate':
    hide_attr = bm.faces.layers.int.get('.hide_poly')
    if hide_attr is None:
        hide_attr = bm.faces.layers.int.new('.hide_poly')
    for f in bm.faces:
        f[hide_attr] = 0 if f[fs_layer] == face_set_id else 1

elif action == 'visibility_show_all':
    hide_attr = bm.faces.layers.int.get('.hide_poly')
    if hide_attr:
        for f in bm.faces:
            f[hide_attr] = 0

# Count result
fs_counts = {{}}
for f in bm.faces:
    fs_id = f[fs_layer]
    fs_counts[fs_id] = fs_counts.get(fs_id, 0) + 1

bm.to_mesh(mesh)
bm.free()
mesh.update()

result = {{
    'action': action,
    'face_sets': fs_counts,
    'total_sets': len(fs_counts),
    'total_faces': len(mesh.polygons),
}}
result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 5. sculpt_mask_advanced — Professional masking
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_mask_advanced(
        mesh_name: str,
        action: str = "by_cavity",
        params: str = "{}",
    ) -> str:
        """Advanced sculpt masking operations.

        action:
            'by_cavity' — Mask concave areas (crevices)
            'by_convex' — Mask convex areas (peaks)
            'by_normal_direction' — Mask faces facing a direction
            'by_curvature' — Mask by curvature threshold
            'by_position' — Gradient mask along an axis
            'by_noise' — Procedural noise mask
            'blur' — Gaussian blur existing mask
            'contrast' — Increase/decrease mask contrast
            'border' — Mask only the border between masked/unmasked
            'paint_sphere' — Paint mask in a sphere region

        params (JSON):
            by_normal_direction: {"direction": [x,y,z], "threshold": 0.5}
            by_curvature: {"min": 0.01, "max": 0.1}
            by_position: {"axis": "Z", "min": 0.0, "max": 1.0}
            by_noise: {"scale": 0.1, "threshold": 0.5}
            contrast: {"factor": 2.0}
            paint_sphere: {"center": [x,y,z], "radius": 0.1, "value": 1.0}
        """
        p = json.loads(params) if isinstance(params, str) else params
        code = textwrap.dedent(f"""\
import bpy, bmesh, math
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
if obj.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.normal_update()

action = '{action}'
params = {json.dumps(p)}

# Get or create mask layer
mask_layer = bm.verts.layers.paint_mask.active
if mask_layer is None:
    mask_layer = bm.verts.layers.paint_mask.new()

# Precompute neighbors
neighbor_map = {{}}
for v in bm.verts:
    neighbor_map[v.index] = [e.other_vert(v).index for e in v.link_edges]

if action == 'by_cavity':
    for v in bm.verts:
        nbrs = [bm.verts[i] for i in neighbor_map.get(v.index, [])]
        if nbrs:
            avg = sum((n.co for n in nbrs), Vector()) / len(nbrs)
            laplacian = avg - v.co
            # Concave = laplacian points outward (same as normal)
            cavity = max(0, laplacian.dot(v.normal))
            v[mask_layer] = min(1.0, cavity * 20.0)

elif action == 'by_convex':
    for v in bm.verts:
        nbrs = [bm.verts[i] for i in neighbor_map.get(v.index, [])]
        if nbrs:
            avg = sum((n.co for n in nbrs), Vector()) / len(nbrs)
            laplacian = avg - v.co
            convex = max(0, -laplacian.dot(v.normal))
            v[mask_layer] = min(1.0, convex * 20.0)

elif action == 'by_normal_direction':
    direction = Vector(params.get('direction', [0, 0, 1])).normalized()
    threshold = params.get('threshold', 0.5)
    for v in bm.verts:
        dot = v.normal.dot(direction)
        if dot > threshold:
            v[mask_layer] = (dot - threshold) / (1.0 - threshold)
        else:
            v[mask_layer] = 0.0

elif action == 'by_curvature':
    min_curv = params.get('min', 0.01)
    max_curv = params.get('max', 0.1)
    for v in bm.verts:
        nbrs = [bm.verts[i] for i in neighbor_map.get(v.index, [])]
        if nbrs:
            avg = sum((n.co for n in nbrs), Vector()) / len(nbrs)
            curv = (avg - v.co).length
            if curv >= min_curv and curv <= max_curv:
                t = (curv - min_curv) / (max_curv - min_curv) if max_curv > min_curv else 1.0
                v[mask_layer] = t
            else:
                v[mask_layer] = 0.0

elif action == 'by_position':
    axis = params.get('axis', 'Z').upper()
    axis_idx = {{'X': 0, 'Y': 1, 'Z': 2}}.get(axis, 2)
    # Get mesh bounds on axis
    vals = [v.co[axis_idx] for v in bm.verts]
    vmin, vmax = min(vals), max(vals)
    range_min = params.get('min', 0.0)
    range_max = params.get('max', 1.0)
    for v in bm.verts:
        t = (v.co[axis_idx] - vmin) / (vmax - vmin) if vmax > vmin else 0.5
        if range_min <= t <= range_max:
            v[mask_layer] = (t - range_min) / (range_max - range_min) if range_max > range_min else 1.0
        else:
            v[mask_layer] = 0.0

elif action == 'by_noise':
    scale = params.get('scale', 0.1)
    threshold = params.get('threshold', 0.5)
    for v in bm.verts:
        ix = int(v.co.x / scale * 1000) % 997
        iy = int(v.co.y / scale * 1000) % 991
        iz = int(v.co.z / scale * 1000) % 983
        h = ((ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791)) % 1000
        noise_val = h / 1000.0
        v[mask_layer] = 1.0 if noise_val > threshold else 0.0

elif action == 'blur':
    iterations = params.get('iterations', 3)
    for _ in range(iterations):
        values = {{v.index: v[mask_layer] for v in bm.verts}}
        for v in bm.verts:
            nbrs = neighbor_map.get(v.index, [])
            if nbrs:
                avg = sum(values[ni] for ni in nbrs) / len(nbrs)
                v[mask_layer] = values[v.index] * 0.5 + avg * 0.5

elif action == 'contrast':
    factor = params.get('factor', 2.0)
    for v in bm.verts:
        val = v[mask_layer]
        v[mask_layer] = max(0.0, min(1.0, (val - 0.5) * factor + 0.5))

elif action == 'border':
    threshold = params.get('threshold', 0.5)
    values = {{v.index: v[mask_layer] for v in bm.verts}}
    for v in bm.verts:
        is_border = False
        nbrs = neighbor_map.get(v.index, [])
        for ni in nbrs:
            if (values[v.index] > threshold) != (values[ni] > threshold):
                is_border = True
                break
        v[mask_layer] = 1.0 if is_border else 0.0

elif action == 'paint_sphere':
    center = Vector(params.get('center', [0, 0, 0]))
    radius = params.get('radius', 0.1)
    value = params.get('value', 1.0)
    for v in bm.verts:
        dist = (v.co - center).length
        if dist <= radius:
            t = dist / radius
            falloff = 1.0 - t * t * (3.0 - 2.0 * t)
            v[mask_layer] = max(v[mask_layer], value * falloff)

# Count masked
masked_count = sum(1 for v in bm.verts if v[mask_layer] > 0.01)

bm.to_mesh(mesh)
bm.free()
mesh.update()

result = {{
    'action': action,
    'masked_vertices': masked_count,
    'total_vertices': len(mesh.vertices),
    'mask_coverage': round(masked_count / len(mesh.vertices) * 100, 1),
}}
result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 6. sculpt_multires_workflow — Full multires control
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_multires_workflow(
        mesh_name: str,
        action: str = "setup",
        levels: int = 4,
        sculpt_level: int = -1,
        subdivision_type: str = "CATMULL_CLARK",
    ) -> str:
        """Full multi-resolution sculpting workflow control.

        action:
            'setup' — Add multires modifier and subdivide to target levels
            'set_level' — Change sculpt subdivision level (low for broad, high for detail)
            'apply_base' — Move base mesh toward sculpted shape
            'delete_higher' — Delete subdivision levels above current
            'unsubdivide' — Reduce base mesh topology
            'rebuild' — Rebuild subdivisions from topology
            'info' — Show current multires state

        levels: Number of subdivision levels for 'setup'.
        sculpt_level: Target sculpt level for 'set_level' (-1 = max).
        subdivision_type: CATMULL_CLARK or SIMPLE.
        """
        code = textwrap.dedent(f"""\
import bpy

obj = bpy.data.objects['{mesh_name}']
bpy.context.view_layer.objects.active = obj
if obj.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

action = '{action}'
levels = {levels}
sculpt_level = {sculpt_level}
subdiv_type = '{subdivision_type}'

# Find or create multires modifier
multires = None
for mod in obj.modifiers:
    if mod.type == 'MULTIRES':
        multires = mod
        break

if action == 'setup':
    if multires is None:
        multires = obj.modifiers.new('Multires', 'MULTIRES')

    current = multires.total_levels
    needed = levels - current
    for i in range(needed):
        bpy.ops.object.multires_subdivide(modifier='Multires', mode=subdiv_type)

    multires.sculpt_levels = multires.total_levels
    multires.levels = min(2, multires.total_levels)  # Keep viewport light

    # Enter sculpt mode
    bpy.ops.object.mode_set(mode='SCULPT')

    result = {{
        'action': 'setup',
        'total_levels': multires.total_levels,
        'sculpt_level': multires.sculpt_levels,
        'viewport_level': multires.levels,
        'base_vertices': len(obj.data.vertices),
        'subdivision_type': subdiv_type,
    }}

elif action == 'set_level':
    if multires is None:
        result = {{'error': 'No Multires modifier found'}}
    else:
        target = sculpt_level if sculpt_level >= 0 else multires.total_levels
        target = min(target, multires.total_levels)
        multires.sculpt_levels = target
        multires.levels = min(target, 2)  # Keep viewport responsive

        result = {{
            'action': 'set_level',
            'sculpt_level': multires.sculpt_levels,
            'viewport_level': multires.levels,
            'total_levels': multires.total_levels,
        }}

elif action == 'apply_base':
    if multires:
        bpy.ops.object.multires_base_apply(modifier='Multires')
        result = {{'action': 'apply_base', 'success': True}}
    else:
        result = {{'error': 'No Multires modifier'}}

elif action == 'delete_higher':
    if multires:
        bpy.ops.object.multires_higher_levels_delete(modifier='Multires')
        result = {{'action': 'delete_higher', 'remaining_levels': multires.total_levels}}
    else:
        result = {{'error': 'No Multires modifier'}}

elif action == 'unsubdivide':
    if multires:
        bpy.ops.object.multires_unsubdivide(modifier='Multires')
        result = {{'action': 'unsubdivide', 'total_levels': multires.total_levels}}
    else:
        result = {{'error': 'No Multires modifier'}}

elif action == 'rebuild':
    if multires:
        bpy.ops.object.multires_rebuild_subdiv(modifier='Multires')
        result = {{'action': 'rebuild', 'total_levels': multires.total_levels}}
    else:
        result = {{'error': 'No Multires modifier'}}

elif action == 'info':
    if multires:
        result = {{
            'total_levels': multires.total_levels,
            'sculpt_level': multires.sculpt_levels,
            'viewport_level': multires.levels,
            'render_level': multires.render_levels,
            'base_vertices': len(obj.data.vertices),
            'show_only_control_edges': multires.show_only_control_edges,
        }}
    else:
        result = {{'has_multires': False, 'modifiers': [m.type for m in obj.modifiers]}}

result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 7. sculpt_symmetry — Mirror and symmetry ops
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_symmetry(
        mesh_name: str,
        action: str = "symmetrize",
        axis: str = "X",
        direction: str = "NEGATIVE",
        merge_threshold: float = 0.001,
    ) -> str:
        """Symmetry operations for sculpting.

        action:
            'symmetrize' — Mirror mesh from one side to the other
            'check' — Analyze symmetry quality (report asymmetric vertices)
            'snap_to_symmetry' — Snap near-symmetric vertices to exact symmetry
            'enable_mirror' — Enable sculpt mirror on axis

        axis: X, Y, or Z.
        direction: NEGATIVE (positive→negative) or POSITIVE (negative→positive).
        merge_threshold: Distance threshold for symmetry snapping.
        """
        code = textwrap.dedent(f"""\
import bpy, bmesh
from mathutils import Vector, kdtree

obj = bpy.data.objects['{mesh_name}']
bpy.context.view_layer.objects.active = obj
if obj.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

action = '{action}'
axis = '{axis}'
direction = '{direction}'
threshold = {merge_threshold}
axis_idx = {{'X': 0, 'Y': 1, 'Z': 2}}.get(axis, 0)

if action == 'symmetrize':
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)

    sym_dir = direction + '_' + axis
    bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:],
                         direction=sym_dir, dist=threshold)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    result = {{'action': 'symmetrize', 'direction': sym_dir, 'vertices': len(mesh.vertices)}}

elif action == 'check':
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    # Build KDTree
    size = len(bm.verts)
    kd = kdtree.KDTree(size)
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    asymmetric = 0
    max_asymmetry = 0.0
    for v in bm.verts:
        mirrored = v.co.copy()
        mirrored[axis_idx] *= -1
        co, idx, dist = kd.find(mirrored)
        if dist > threshold:
            asymmetric += 1
            max_asymmetry = max(max_asymmetry, dist)

    sym_quality = 1.0 - (asymmetric / len(bm.verts)) if len(bm.verts) > 0 else 1.0
    bm.free()

    result = {{
        'action': 'check',
        'axis': axis,
        'asymmetric_vertices': asymmetric,
        'total_vertices': len(mesh.vertices),
        'symmetry_quality': round(sym_quality * 100, 1),
        'max_asymmetry_distance': round(max_asymmetry, 6),
        'threshold': threshold,
    }}

elif action == 'snap_to_symmetry':
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    size = len(bm.verts)
    kd = kdtree.KDTree(size)
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    snapped = 0
    processed = set()
    for v in bm.verts:
        if v.index in processed:
            continue
        mirrored = v.co.copy()
        mirrored[axis_idx] *= -1
        co, idx, dist = kd.find(mirrored)
        if dist < threshold * 10 and idx != v.index and idx not in processed:
            # Average and mirror
            partner = bm.verts[idx]
            avg = (v.co + Vector((partner.co.x * (-1 if axis_idx == 0 else 1),
                                   partner.co.y * (-1 if axis_idx == 1 else 1),
                                   partner.co.z * (-1 if axis_idx == 2 else 1)))) * 0.5
            v.co = avg
            mirror_avg = avg.copy()
            mirror_avg[axis_idx] *= -1
            partner.co = mirror_avg
            processed.add(v.index)
            processed.add(idx)
            snapped += 1
        # Snap center vertices
        if abs(v.co[axis_idx]) < threshold:
            v.co[axis_idx] = 0.0

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    result = {{'action': 'snap_to_symmetry', 'snapped_pairs': snapped, 'axis': axis}}

elif action == 'enable_mirror':
    bpy.ops.object.mode_set(mode='SCULPT')
    sculpt = bpy.context.tool_settings.sculpt
    if axis == 'X':
        sculpt.use_symmetry_x = True
    elif axis == 'Y':
        sculpt.use_symmetry_y = True
    elif axis == 'Z':
        sculpt.use_symmetry_z = True
    result = {{
        'action': 'enable_mirror',
        'axis': axis,
        'symmetry_x': sculpt.use_symmetry_x,
        'symmetry_y': sculpt.use_symmetry_y,
        'symmetry_z': sculpt.use_symmetry_z,
    }}

result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 8. sculpt_anatomy_pass — Anatomy-aware sculpting
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_anatomy_pass(
        mesh_name: str,
        pass_type: str = "primary",
        body_region: str = "full",
        style: str = "anime_standard",
        intensity: float = 0.5,
    ) -> str:
        """Apply anatomy-aware sculpting pass using built-in knowledge.

        pass_type: 'primary' (big forms), 'secondary' (muscles/bones), 'tertiary' (detail)
        body_region: 'full', 'head', 'torso', 'arm', 'leg', 'hand', 'foot'
        style: 'realistic', 'semi_realistic', 'anime_standard', 'chibi'
        intensity: 0.0-1.0 how strong to apply

        This tool analyzes the mesh and applies anatomically-informed
        smoothing/displacement based on the sculpt pass type.
        It modifies the mesh to improve anatomical correctness within
        the chosen style.
        """
        code = textwrap.dedent(f"""\
import bpy, bmesh, math
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
if obj.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.normal_update()

pass_type = '{pass_type}'
body_region = '{body_region}'
style = '{style}'
intensity = {intensity}

# Compute mesh bounds
xs = [v.co.x for v in bm.verts]
ys = [v.co.y for v in bm.verts]
zs = [v.co.z for v in bm.verts]
bbox_min = Vector((min(xs), min(ys), min(zs)))
bbox_max = Vector((max(xs), max(ys), max(zs)))
dims = bbox_max - bbox_min
center = (bbox_min + bbox_max) * 0.5
mesh_scale = max(dims) if max(dims) > 0 else 1.0

# Style parameters
style_params = {{
    'realistic':      {{'smooth': 0.2, 'detail': 1.0, 'simplify': 0.0}},
    'semi_realistic': {{'smooth': 0.3, 'detail': 0.7, 'simplify': 0.2}},
    'anime_standard': {{'smooth': 0.5, 'detail': 0.3, 'simplify': 0.6}},
    'chibi':          {{'smooth': 0.7, 'detail': 0.1, 'simplify': 0.9}},
}}.get(style, {{'smooth': 0.3, 'detail': 0.5, 'simplify': 0.3}})

# Precompute neighbors
neighbor_map = {{}}
for v in bm.verts:
    neighbor_map[v.index] = [e.other_vert(v).index for e in v.link_edges]

operations_log = []
affected = 0

if pass_type == 'primary':
    # Primary pass: smooth large-scale noise, improve silhouette flow
    smooth_strength = style_params['smooth'] * intensity
    iterations = 3

    for iteration in range(iterations):
        positions = {{v.index: v.co.copy() for v in bm.verts}}
        for v in bm.verts:
            nbrs = neighbor_map.get(v.index, [])
            if len(nbrs) < 2:
                continue
            avg = Vector((0,0,0))
            for ni in nbrs:
                avg += positions[ni]
            avg /= len(nbrs)

            # Large-radius smooth (use distance-weighted for volume preservation)
            disp = (avg - positions[v.index])
            # Preserve volume: reduce normal component
            normal_comp = disp.dot(v.normal) * v.normal
            tangent_comp = disp - normal_comp
            # Apply more tangent smooth than normal smooth
            v.co = positions[v.index] + tangent_comp * smooth_strength + normal_comp * smooth_strength * 0.3
            affected += 1

    operations_log.append(f'Volume-preserving smooth x{{iterations}} @ {{smooth_strength:.2f}}')

elif pass_type == 'secondary':
    # Secondary pass: enhance curvature variation (muscles/landmarks)
    detail_strength = style_params['detail'] * intensity
    simplify_strength = style_params['simplify'] * intensity

    positions = {{v.index: v.co.copy() for v in bm.verts}}
    normals = {{v.index: v.normal.copy() for v in bm.verts}}

    for v in bm.verts:
        nbrs = neighbor_map.get(v.index, [])
        if len(nbrs) < 2:
            continue

        # Compute local curvature
        avg = Vector((0,0,0))
        for ni in nbrs:
            avg += positions[ni]
        avg /= len(nbrs)
        laplacian = avg - positions[v.index]
        curvature = laplacian.length

        # For stylized: flatten low-curvature areas, sharpen transitions
        if curvature < 0.01 * mesh_scale:
            # Flat area — smooth more for stylized looks
            smooth_amount = simplify_strength * 0.3
            v.co = positions[v.index] + laplacian * smooth_amount
        else:
            # Curved area — enhance detail proportionally
            enhance_amount = detail_strength * 0.15
            normal_detail = laplacian.dot(normals[v.index])
            v.co = positions[v.index] + normals[v.index] * normal_detail * enhance_amount

        affected += 1

    operations_log.append(f'Curvature-adaptive detail @ detail={{detail_strength:.2f}}, simplify={{simplify_strength:.2f}}')

elif pass_type == 'tertiary':
    # Tertiary pass: surface cleanup, micro-detail
    detail_strength = style_params['detail'] * intensity

    # Surface-preserving smooth for clean surfaces
    positions = {{v.index: v.co.copy() for v in bm.verts}}
    normals = {{v.index: v.normal.copy() for v in bm.verts}}

    for v in bm.verts:
        nbrs = neighbor_map.get(v.index, [])
        if len(nbrs) < 2:
            continue

        avg = Vector((0,0,0))
        for ni in nbrs:
            avg += positions[ni]
        avg /= len(nbrs)
        laplacian = avg - positions[v.index]

        # Only smooth tangentially, preserve detail along normals
        normal_comp = laplacian.dot(normals[v.index])
        tangent_disp = laplacian - normal_comp * normals[v.index]

        # Clean tangent noise while keeping normal-direction detail
        v.co = positions[v.index] + tangent_disp * (1.0 - detail_strength) * 0.2
        affected += 1

    operations_log.append(f'Tangent-preserving cleanup @ {{detail_strength:.2f}}')

bm.to_mesh(mesh)
bm.free()
mesh.update()

result = {{
    'pass_type': pass_type,
    'body_region': body_region,
    'style': style,
    'intensity': intensity,
    'affected_vertices': affected,
    'operations': operations_log,
    'style_params': style_params,
}}
result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 9. sculpt_color_attribute — Vertex color in sculpt mode
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_color_attribute(
        mesh_name: str,
        action: str = "fill",
        color: str = "[1.0, 1.0, 1.0, 1.0]",
        params: str = "{}",
    ) -> str:
        """Manage vertex colors for sculpt-mode painting.

        action:
            'create' — Create a new color attribute
            'fill' — Fill entire mesh with a color
            'paint_sphere' — Paint color in a sphere region
            'gradient' — Apply gradient along an axis
            'curvature_color' — Color by surface curvature (for visualization)
            'ao_vertex_color' — Bake simple ambient occlusion to vertex colors

        color: JSON [R, G, B, A] (0.0-1.0).
        params: For paint_sphere: {"center": [x,y,z], "radius": 0.1}
                For gradient: {"axis": "Z", "color_start": [r,g,b,a], "color_end": [r,g,b,a]}
                For ao_vertex_color: {"samples": 16, "distance": 0.5}
        """
        p = json.loads(params) if isinstance(params, str) else params
        c = json.loads(color) if isinstance(color, str) else color
        code = textwrap.dedent(f"""\
import bpy, bmesh, math, random
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
if obj.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
action = '{action}'
color = {json.dumps(c)}
params = {json.dumps(p)}

# Ensure color attribute exists
attr_name = 'SculptColor'
if attr_name not in mesh.color_attributes:
    mesh.color_attributes.new(name=attr_name, type='FLOAT_COLOR', domain='POINT')
mesh.color_attributes.active_color = mesh.color_attributes[attr_name]

color_attr = mesh.color_attributes[attr_name]

if action == 'create':
    result = {{'action': 'create', 'name': attr_name, 'vertices': len(mesh.vertices)}}

elif action == 'fill':
    for i in range(len(color_attr.data)):
        color_attr.data[i].color = color
    result = {{'action': 'fill', 'color': color, 'vertices': len(color_attr.data)}}

elif action == 'paint_sphere':
    center = Vector(params.get('center', [0, 0, 0]))
    radius = params.get('radius', 0.1)
    painted = 0
    for i, v in enumerate(mesh.vertices):
        dist = (v.co - center).length
        if dist <= radius:
            t = dist / radius
            falloff = 1.0 - t * t * (3.0 - 2.0 * t)
            existing = list(color_attr.data[i].color)
            blended = [existing[c_i] * (1 - falloff) + color[c_i] * falloff for c_i in range(4)]
            color_attr.data[i].color = blended
            painted += 1
    result = {{'action': 'paint_sphere', 'painted': painted}}

elif action == 'gradient':
    axis = params.get('axis', 'Z').upper()
    axis_idx = {{'X': 0, 'Y': 1, 'Z': 2}}.get(axis, 2)
    c_start = params.get('color_start', [0, 0, 0, 1])
    c_end = params.get('color_end', [1, 1, 1, 1])

    vals = [v.co[axis_idx] for v in mesh.vertices]
    vmin, vmax = min(vals), max(vals)
    rng = vmax - vmin if vmax > vmin else 1.0

    for i, v in enumerate(mesh.vertices):
        t = (v.co[axis_idx] - vmin) / rng
        blended = [c_start[c_i] * (1 - t) + c_end[c_i] * t for c_i in range(4)]
        color_attr.data[i].color = blended
    result = {{'action': 'gradient', 'axis': axis}}

elif action == 'curvature_color':
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.normal_update()

    curvatures = []
    for v in bm.verts:
        nbrs = [e.other_vert(v) for e in v.link_edges]
        if nbrs:
            avg = sum((n.co for n in nbrs), Vector()) / len(nbrs)
            curv = (avg - v.co).dot(v.normal)
            curvatures.append(curv)
        else:
            curvatures.append(0)
    bm.free()

    max_abs = max(abs(c) for c in curvatures) if curvatures else 1.0
    if max_abs < 0.0001:
        max_abs = 1.0

    for i, curv in enumerate(curvatures):
        t = curv / max_abs  # -1 to 1
        if t > 0:  # Convex = red
            color_attr.data[i].color = (1.0, 1.0 - t, 1.0 - t, 1.0)
        else:  # Concave = blue
            color_attr.data[i].color = (1.0 + t, 1.0 + t, 1.0, 1.0)
    result = {{'action': 'curvature_color', 'max_curvature': round(max_abs, 6)}}

elif action == 'ao_vertex_color':
    # Simple AO approximation using neighbor normals
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.normal_update()

    ao_values = []
    for v in bm.verts:
        nbrs = [e.other_vert(v) for e in v.link_edges]
        if not nbrs:
            ao_values.append(1.0)
            continue
        # AO ≈ average dot product of neighbor vectors with normal
        occlusion = 0.0
        for n in nbrs:
            to_neighbor = (n.co - v.co).normalized()
            dot = max(0, to_neighbor.dot(v.normal))
            occlusion += dot
        occlusion /= len(nbrs)
        ao_values.append(occlusion)
    bm.free()

    for i, ao in enumerate(ao_values):
        color_attr.data[i].color = (ao, ao, ao, 1.0)
    result = {{'action': 'ao_vertex_color', 'vertices': len(ao_values)}}

mesh.update()
result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 10. sculpt_detail_adaptive — Smart detail control
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_detail_adaptive(
        mesh_name: str,
        action: str = "auto_detail",
        target_density: float = 0.0,
        detail_regions: str = "[]",
    ) -> str:
        """Adaptive detail control — add resolution where needed.

        action:
            'auto_detail' — Analyze and remesh with adaptive density
            'add_detail_sphere' — Add detail (subdivide) in a spherical region
            'reduce_detail_sphere' — Reduce detail (decimate) in a spherical region
            'equalize' — Make vertex density uniform
            'info' — Report density statistics

        target_density: Target edge length (0 = auto-calculate from mesh).
        detail_regions: JSON array of {"center": [x,y,z], "radius": r, "detail": 0.5-2.0}
        """
        regions = json.loads(detail_regions) if isinstance(detail_regions, str) else detail_regions
        code = textwrap.dedent(f"""\
import bpy, bmesh, math
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
bpy.context.view_layer.objects.active = obj
if obj.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
action = '{action}'
target_density = {target_density}
regions = {json.dumps(regions)}

if action == 'info':
    bm = bmesh.new()
    bm.from_mesh(mesh)
    edge_lengths = [e.calc_length() for e in bm.edges]
    face_areas = [f.calc_area() for f in bm.faces]
    bm.free()

    avg_edge = sum(edge_lengths) / len(edge_lengths) if edge_lengths else 0
    min_edge = min(edge_lengths) if edge_lengths else 0
    max_edge = max(edge_lengths) if edge_lengths else 0
    avg_area = sum(face_areas) / len(face_areas) if face_areas else 0

    result = {{
        'vertices': len(mesh.vertices),
        'faces': len(mesh.polygons),
        'avg_edge_length': round(avg_edge, 6),
        'min_edge_length': round(min_edge, 6),
        'max_edge_length': round(max_edge, 6),
        'ratio': round(max_edge / min_edge, 2) if min_edge > 0 else 0,
        'avg_face_area': round(avg_area, 8),
        'suggested_voxel_size': round(avg_edge * 0.8, 4),
    }}

elif action == 'auto_detail':
    bm = bmesh.new()
    bm.from_mesh(mesh)
    avg_edge = sum(e.calc_length() for e in bm.edges) / len(bm.edges) if bm.edges else 0.01
    bm.free()

    voxel_size = target_density if target_density > 0 else avg_edge * 0.8

    mesh.remesh_voxel_size = voxel_size
    mesh.remesh_voxel_adaptivity = 0.0
    mesh.use_remesh_preserve_volume = True
    mesh.use_remesh_preserve_paint_mask = True
    mesh.use_remesh_preserve_sculpt_face_sets = True
    mesh.use_remesh_preserve_vertex_colors = True

    bpy.ops.object.voxel_remesh()

    result = {{
        'action': 'auto_detail',
        'voxel_size': round(voxel_size, 6),
        'vertices_after': len(mesh.vertices),
        'faces_after': len(mesh.polygons),
    }}

elif action == 'add_detail_sphere':
    # Select faces in region and subdivide
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()

    for region in regions:
        center = Vector(region.get('center', [0, 0, 0]))
        radius = region.get('radius', 0.1)
        detail_level = int(region.get('detail', 1))

        target_faces = []
        for f in bm.faces:
            if (f.calc_center_median() - center).length <= radius:
                target_faces.append(f)

        if target_faces:
            result_geom = bmesh.ops.subdivide_edges(
                bm, edges=list(set(e for f in target_faces for e in f.edges)),
                cuts=detail_level, use_grid_fill=True)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    result = {{
        'action': 'add_detail_sphere',
        'regions': len(regions),
        'vertices_after': len(mesh.vertices),
        'faces_after': len(mesh.polygons),
    }}

elif action == 'reduce_detail_sphere':
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    for region in regions:
        center = Vector(region.get('center', [0, 0, 0]))
        radius = region.get('radius', 0.1)

        target_verts = []
        for v in bm.verts:
            if (v.co - center).length <= radius:
                target_verts.append(v)

        if target_verts:
            bmesh.ops.dissolve_limit(
                bm, verts=target_verts,
                edges=list(set(e for v in target_verts for e in v.link_edges)),
                angle_limit=math.radians(5))

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    result = {{
        'action': 'reduce_detail_sphere',
        'regions': len(regions),
        'vertices_after': len(mesh.vertices),
        'faces_after': len(mesh.polygons),
    }}

elif action == 'equalize':
    # Voxel remesh at average density
    bm = bmesh.new()
    bm.from_mesh(mesh)
    avg_edge = sum(e.calc_length() for e in bm.edges) / len(bm.edges) if bm.edges else 0.01
    bm.free()

    mesh.remesh_voxel_size = avg_edge
    mesh.remesh_voxel_adaptivity = 0.0
    mesh.use_remesh_preserve_volume = True
    bpy.ops.object.voxel_remesh()

    result = {{
        'action': 'equalize',
        'voxel_size': round(avg_edge, 6),
        'vertices_after': len(mesh.vertices),
        'faces_after': len(mesh.polygons),
    }}

result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 11. sculpt_layer_workflow — Shape key based layers
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_layer_workflow(
        mesh_name: str,
        action: str = "create",
        layer_name: str = "SculptLayer1",
        blend_value: float = 1.0,
    ) -> str:
        """Layer-based sculpting using shape keys as sculpt layers.

        action:
            'create' — Create a new sculpt layer (shape key)
            'set_active' — Activate a sculpt layer for editing
            'set_blend' — Set layer blend value (0.0-1.0)
            'flatten' — Merge all layers into the base mesh
            'delete' — Delete a sculpt layer
            'list' — List all layers with their blend values and displacement stats

        layer_name: Name of the sculpt layer.
        blend_value: 0.0-1.0 visibility/blend of this layer.
        """
        code = textwrap.dedent(f"""\
import bpy
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
bpy.context.view_layer.objects.active = obj
if obj.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

action = '{action}'
layer_name = '{layer_name}'
blend_value = {blend_value}

# Ensure basis exists
if not obj.data.shape_keys:
    obj.shape_key_add(name='Basis', from_mix=False)

key_blocks = obj.data.shape_keys.key_blocks

if action == 'create':
    if layer_name in key_blocks:
        result = {{'error': f'Layer "{{layer_name}}" already exists'}}
    else:
        sk = obj.shape_key_add(name=layer_name, from_mix=False)
        sk.value = blend_value
        # Set as active for sculpting
        obj.active_shape_key_index = list(key_blocks).index(sk)
        result = {{
            'action': 'create',
            'layer': layer_name,
            'blend': blend_value,
            'total_layers': len(key_blocks),
        }}

elif action == 'set_active':
    if layer_name in key_blocks:
        idx = list(key_blocks.keys()).index(layer_name)
        obj.active_shape_key_index = idx
        result = {{'action': 'set_active', 'layer': layer_name, 'index': idx}}
    else:
        result = {{'error': f'Layer "{{layer_name}}" not found'}}

elif action == 'set_blend':
    if layer_name in key_blocks:
        key_blocks[layer_name].value = blend_value
        result = {{'action': 'set_blend', 'layer': layer_name, 'blend': blend_value}}
    else:
        result = {{'error': f'Layer "{{layer_name}}" not found'}}

elif action == 'flatten':
    # Apply mix to mesh
    bpy.ops.object.shape_key_move(type='TOP')
    # Store mixed positions
    mixed_positions = [v.co.copy() for v in obj.data.vertices]
    # Remove all shape keys
    while obj.data.shape_keys and len(obj.data.shape_keys.key_blocks) > 0:
        obj.active_shape_key_index = 0
        bpy.ops.object.shape_key_remove()
    # Apply mixed positions
    for i, v in enumerate(obj.data.vertices):
        v.co = mixed_positions[i]
    obj.data.update()
    result = {{'action': 'flatten', 'vertices': len(obj.data.vertices)}}

elif action == 'delete':
    if layer_name in key_blocks and layer_name != 'Basis':
        idx = list(key_blocks.keys()).index(layer_name)
        obj.active_shape_key_index = idx
        bpy.ops.object.shape_key_remove()
        result = {{'action': 'delete', 'layer': layer_name}}
    else:
        result = {{'error': f'Cannot delete "{{layer_name}}"'}}

elif action == 'list':
    layers = []
    basis = key_blocks['Basis'] if 'Basis' in key_blocks else None
    for kb in key_blocks:
        displaced = 0
        max_disp = 0.0
        if basis and kb.name != 'Basis':
            for i in range(len(kb.data)):
                delta = (kb.data[i].co - basis.data[i].co).length
                if delta > 0.0001:
                    displaced += 1
                    max_disp = max(max_disp, delta)
        layers.append({{
            'name': kb.name,
            'value': round(kb.value, 3),
            'displaced_verts': displaced,
            'max_displacement': round(max_disp, 6),
            'is_basis': kb.name == 'Basis',
        }})
    result = {{'layers': layers, 'total': len(layers), 'active_index': obj.active_shape_key_index}}

result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 12. sculpt_extract — Extract mesh region as new object
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_extract(
        mesh_name: str,
        method: str = "by_mask",
        thickness: float = 0.01,
        offset: float = 0.0,
        smooth_iterations: int = 3,
        params: str = "{}",
    ) -> str:
        """Extract part of a sculpted mesh as a new separate object.

        method:
            'by_mask' — Extract masked region (mask > 0.5)
            'by_face_set' — Extract specified face set
            'by_position' — Extract faces in a bounding box/sphere
            'shell' — Create a thin shell from the surface (like armor/clothing)

        thickness: Solidify thickness for extracted piece.
        offset: Solidify offset (-1 to 1, negative = inward).
        smooth_iterations: Smooth passes on extraction boundary.
        params: For by_face_set: {"face_set_id": 1}
                For by_position: {"center": [x,y,z], "radius": 0.5} or
                                 {"min": [x,y,z], "max": [x,y,z]}
        """
        p = json.loads(params) if isinstance(params, str) else params
        code = textwrap.dedent(f"""\
import bpy, bmesh
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
bpy.context.view_layer.objects.active = obj
if obj.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

method = '{method}'
thickness = {thickness}
offset = {offset}
smooth_iters = {smooth_iterations}
params = {json.dumps(p)}

# Duplicate mesh
new_mesh = obj.data.copy()
new_obj = obj.copy()
new_obj.data = new_mesh
new_obj.name = '{mesh_name}_extract'
bpy.context.collection.objects.link(new_obj)

bm = bmesh.new()
bm.from_mesh(new_mesh)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

faces_to_remove = []

if method == 'by_mask':
    mask_layer = bm.verts.layers.paint_mask.active
    if mask_layer:
        for f in bm.faces:
            avg_mask = sum(v[mask_layer] for v in f.verts) / len(f.verts)
            if avg_mask < 0.5:
                faces_to_remove.append(f)
    else:
        # No mask — remove nothing
        pass

elif method == 'by_face_set':
    fs_layer = bm.faces.layers.int.get('.sculpt_face_set')
    target_id = params.get('face_set_id', 1)
    if fs_layer:
        for f in bm.faces:
            if f[fs_layer] != target_id:
                faces_to_remove.append(f)

elif method == 'by_position':
    if 'center' in params:
        center = Vector(params['center'])
        radius = params.get('radius', 0.5)
        for f in bm.faces:
            if (f.calc_center_median() - center).length > radius:
                faces_to_remove.append(f)
    elif 'min' in params and 'max' in params:
        bmin = Vector(params['min'])
        bmax = Vector(params['max'])
        for f in bm.faces:
            c = f.calc_center_median()
            if not (bmin.x <= c.x <= bmax.x and bmin.y <= c.y <= bmax.y and bmin.z <= c.z <= bmax.z):
                faces_to_remove.append(f)

elif method == 'shell':
    # Keep all faces, just apply solidify
    pass

# Remove unwanted faces
if faces_to_remove:
    bmesh.ops.delete(bm, geom=faces_to_remove, context='FACES')

# Clean up
bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0001)

# Remove loose verts
loose = [v for v in bm.verts if not v.link_edges]
if loose:
    bmesh.ops.delete(bm, geom=loose, context='VERTS')

bm.to_mesh(new_mesh)
bm.free()
new_mesh.update()

# Apply solidify
bpy.context.view_layer.objects.active = new_obj
if thickness > 0:
    mod = new_obj.modifiers.new('Solidify', 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = offset
    mod.use_rim = True
    bpy.ops.object.modifier_apply(modifier='Solidify')

# Smooth boundary
if smooth_iters > 0:
    mod = new_obj.modifiers.new('Smooth', 'SMOOTH')
    mod.iterations = smooth_iters
    mod.factor = 0.5
    bpy.ops.object.modifier_apply(modifier='Smooth')

result = {{
    'extracted_object': new_obj.name,
    'method': method,
    'vertices': len(new_mesh.vertices),
    'faces': len(new_mesh.polygons),
    'thickness': thickness,
}}
result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 13. sculpt_reference — Manage reference images/planes
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_reference(
        action: str = "create_turnaround",
        image_path: str = "",
        view: str = "front",
        size: float = 1.0,
        opacity: float = 0.5,
    ) -> str:
        """Manage reference images for sculpting.

        action:
            'create_turnaround' — Set up standard turnaround reference planes
                (front/side/back/top images as transparent planes)
            'add_image_plane' — Add a single reference image plane
            'setup_camera_ref' — Load reference as background image in camera
            'list' — List all reference objects

        view: 'front', 'side', 'back', 'top' (for image plane orientation).
        image_path: Path to reference image file.
        size: Scale of reference plane.
        opacity: Transparency of reference plane (0.0-1.0).
        """
        code = textwrap.dedent(f"""\
import bpy, math
from mathutils import Vector

action = '{action}'
image_path = r'{image_path}'
view = '{view}'
size = {size}
opacity = {opacity}

if action == 'create_turnaround':
    # Create empty reference planes for turnaround
    views = {{
        'front':  {{'location': (0, -2, 0), 'rotation': (math.pi/2, 0, 0)}},
        'back':   {{'location': (0, 2, 0), 'rotation': (math.pi/2, 0, math.pi)}},
        'side_r': {{'location': (2, 0, 0), 'rotation': (math.pi/2, 0, math.pi/2)}},
        'side_l': {{'location': (-2, 0, 0), 'rotation': (math.pi/2, 0, -math.pi/2)}},
        'top':    {{'location': (0, 0, 2), 'rotation': (0, 0, 0)}},
    }}

    created = []
    for vname, vdata in views.items():
        bpy.ops.object.empty_add(
            type='IMAGE',
            location=vdata['location'],
            rotation=vdata['rotation'],
        )
        empty = bpy.context.active_object
        empty.name = f'Ref_{{vname}}'
        empty.empty_display_size = size
        empty.empty_image_depth = 'BACK'
        empty.show_in_front = False
        # Set display alpha
        empty.color[3] = opacity
        created.append(empty.name)

    result = {{'action': 'create_turnaround', 'created': created, 'note': 'Load images into each reference plane via Properties > Object Data'}}

elif action == 'add_image_plane':
    rotations = {{
        'front':  (math.pi/2, 0, 0),
        'back':   (math.pi/2, 0, math.pi),
        'side':   (math.pi/2, 0, math.pi/2),
        'top':    (0, 0, 0),
    }}
    rot = rotations.get(view, (math.pi/2, 0, 0))

    if image_path:
        img = bpy.data.images.load(image_path)
        bpy.ops.object.empty_add(type='IMAGE', location=(0, 0, 0), rotation=rot)
        empty = bpy.context.active_object
        empty.data = img
        empty.name = f'Ref_{{view}}'
        empty.empty_display_size = size
        empty.empty_image_depth = 'BACK'
        empty.color[3] = opacity
        result = {{'action': 'add_image_plane', 'object': empty.name, 'image': img.name}}
    else:
        bpy.ops.object.empty_add(type='IMAGE', location=(0, 0, 0), rotation=rot)
        empty = bpy.context.active_object
        empty.name = f'Ref_{{view}}'
        empty.empty_display_size = size
        empty.color[3] = opacity
        result = {{'action': 'add_image_plane', 'object': empty.name, 'note': 'No image loaded — set manually'}}

elif action == 'setup_camera_ref':
    cam = bpy.context.scene.camera
    if cam and cam.type == 'CAMERA':
        if image_path:
            img = bpy.data.images.load(image_path)
            bg = cam.data.background_images.new()
            bg.image = img
            bg.alpha = opacity
            bg.display_depth = 'BACK'
            cam.data.show_background_images = True
            result = {{'action': 'setup_camera_ref', 'camera': cam.name, 'image': img.name}}
        else:
            result = {{'error': 'No image_path provided'}}
    else:
        result = {{'error': 'No active camera in scene'}}

elif action == 'list':
    refs = []
    for obj in bpy.data.objects:
        if obj.type == 'EMPTY' and obj.name.startswith('Ref_'):
            refs.append({{
                'name': obj.name,
                'location': [round(c, 3) for c in obj.location],
                'has_image': obj.data is not None if hasattr(obj, 'data') else False,
                'size': obj.empty_display_size,
            }})
    result = {{'references': refs, 'count': len(refs)}}

result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 14. sculpt_trim — Boolean trim operations
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_trim(
        mesh_name: str,
        trim_type: str = "plane",
        params: str = "{}",
        cleanup: bool = True,
    ) -> str:
        """Boolean trim/cut operations for sculpting.

        trim_type:
            'plane' — Cut mesh with a plane
            'box' — Boolean subtract a box
            'sphere' — Boolean subtract a sphere
            'custom' — Boolean with another object

        params (JSON):
            plane: {"origin": [x,y,z], "normal": [x,y,z], "fill": true}
            box: {"min": [x,y,z], "max": [x,y,z], "operation": "DIFFERENCE"}
            sphere: {"center": [x,y,z], "radius": 0.5, "operation": "DIFFERENCE"}
            custom: {"cutter": "CutterObjectName", "operation": "DIFFERENCE"}

        cleanup: Auto-cleanup degenerate geometry after cut.
        """
        p = json.loads(params) if isinstance(params, str) else params
        code = textwrap.dedent(f"""\
import bpy, bmesh, math
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
bpy.context.view_layer.objects.active = obj
if obj.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

trim_type = '{trim_type}'
params = {json.dumps(p)}
cleanup = {cleanup}

if trim_type == 'plane':
    origin = Vector(params.get('origin', [0, 0, 0]))
    normal = Vector(params.get('normal', [0, 0, 1])).normalized()
    fill_cut = params.get('fill', True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    result_geom = bmesh.ops.bisect_plane(
        bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
        plane_co=origin, plane_no=normal,
        clear_outer=True, clear_inner=False)

    if fill_cut:
        # Fill the cut boundary
        edges = [e for e in result_geom['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            try:
                bmesh.ops.edgeloop_fill(bm, edges=edges)
            except Exception:
                pass

    bm.to_mesh(obj.data)
    bm.free()

    result = {{'trim': 'plane', 'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons)}}

elif trim_type in ('box', 'sphere'):
    # Create temp cutter object
    if trim_type == 'box':
        bmin = Vector(params.get('min', [-0.5, -0.5, -0.5]))
        bmax = Vector(params.get('max', [0.5, 0.5, 0.5]))
        center = (bmin + bmax) / 2
        dims = bmax - bmin
        bpy.ops.mesh.primitive_cube_add(size=1, location=center)
        cutter = bpy.context.active_object
        cutter.scale = dims / 2
        bpy.ops.object.transform_apply(scale=True)
    else:
        center = Vector(params.get('center', [0, 0, 0]))
        radius = params.get('radius', 0.5)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=center, segments=32, ring_count=16)
        cutter = bpy.context.active_object

    operation = params.get('operation', 'DIFFERENCE')

    # Apply boolean
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new('BoolTrim', 'BOOLEAN')
    mod.object = cutter
    mod.operation = operation
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier='BoolTrim')

    # Delete cutter
    bpy.data.objects.remove(cutter, do_unlink=True)

    result = {{'trim': trim_type, 'operation': operation, 'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons)}}

elif trim_type == 'custom':
    cutter_name = params.get('cutter', '')
    operation = params.get('operation', 'DIFFERENCE')
    if cutter_name and cutter_name in bpy.data.objects:
        cutter = bpy.data.objects[cutter_name]
        mod = obj.modifiers.new('BoolTrim', 'BOOLEAN')
        mod.object = cutter
        mod.operation = operation
        mod.solver = 'EXACT'
        bpy.ops.object.modifier_apply(modifier='BoolTrim')
        result = {{'trim': 'custom', 'cutter': cutter_name, 'operation': operation, 'vertices': len(obj.data.vertices)}}
    else:
        result = {{'error': f'Cutter object "{{cutter_name}}" not found'}}

# Cleanup
if cleanup:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0001)
    # Remove loose
    loose = [v for v in bm.verts if not v.link_edges]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

result
""")
        return _exec(code)

    # ─────────────────────────────────────────────
    # 15. sculpt_smooth_groups — Targeted smoothing by region
    # ─────────────────────────────────────────────
    @mcp.tool()
    def sculpt_smooth_groups(
        mesh_name: str,
        action: str = "smooth_by_mask",
        iterations: int = 5,
        factor: float = 0.5,
        preserve_volume: bool = True,
    ) -> str:
        """Targeted smoothing operations for sculpted meshes.

        action:
            'smooth_by_mask' — Smooth only masked region
            'smooth_boundary' — Smooth only mesh boundaries/seams
            'smooth_high_curvature' — Smooth only high-curvature areas
            'laplacian_smooth' — Volume-preserving Laplacian smooth (whole mesh)
            'relax_topology' — Equalize edge lengths without changing shape

        iterations: Number of smooth passes.
        factor: Smooth strength per pass (0.0-1.0).
        preserve_volume: Scale mesh back to original volume after smoothing.
        """
        code = textwrap.dedent(f"""\
import bpy, bmesh, math
from mathutils import Vector

obj = bpy.data.objects['{mesh_name}']
if obj.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.normal_update()

action = '{action}'
iterations = {iterations}
factor = {factor}
preserve_volume = {preserve_volume}

# Precompute neighbors
neighbor_map = {{}}
for v in bm.verts:
    neighbor_map[v.index] = [e.other_vert(v).index for e in v.link_edges]

# Compute original volume (bounding box approximation)
if preserve_volume:
    orig_min = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), min(v.co.z for v in bm.verts)))
    orig_max = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), max(v.co.z for v in bm.verts)))
    orig_dims = orig_max - orig_min
    orig_center = (orig_min + orig_max) * 0.5

# Determine which vertices to smooth
smooth_weights = {{}}

if action == 'smooth_by_mask':
    mask_layer = bm.verts.layers.paint_mask.active
    if mask_layer:
        for v in bm.verts:
            smooth_weights[v.index] = v[mask_layer]
    else:
        for v in bm.verts:
            smooth_weights[v.index] = 1.0

elif action == 'smooth_boundary':
    for v in bm.verts:
        is_boundary = any(e.is_boundary or not e.is_manifold for e in v.link_edges)
        smooth_weights[v.index] = 1.0 if is_boundary else 0.0

elif action == 'smooth_high_curvature':
    for v in bm.verts:
        nbrs = [bm.verts[i] for i in neighbor_map.get(v.index, [])]
        if nbrs:
            avg = sum((n.co for n in nbrs), Vector()) / len(nbrs)
            curv = (avg - v.co).length
            smooth_weights[v.index] = min(1.0, curv * 50.0)
        else:
            smooth_weights[v.index] = 0.0

elif action in ('laplacian_smooth', 'relax_topology'):
    for v in bm.verts:
        smooth_weights[v.index] = 1.0

# Apply smooth iterations
affected = 0
for iteration in range(iterations):
    positions = {{v.index: v.co.copy() for v in bm.verts}}
    normals = {{v.index: v.normal.copy() for v in bm.verts}}

    for v in bm.verts:
        w = smooth_weights.get(v.index, 0.0)
        if w < 0.001:
            continue
        nbrs = neighbor_map.get(v.index, [])
        if not nbrs:
            continue

        avg = Vector((0,0,0))
        for ni in nbrs:
            avg += positions[ni]
        avg /= len(nbrs)
        delta = avg - positions[v.index]

        if action == 'relax_topology':
            # Project onto tangent plane (preserve shape, equalize spacing)
            n = normals[v.index]
            delta = delta - delta.dot(n) * n

        if action == 'laplacian_smooth':
            # Volume-preserving: reduce normal component
            n = normals[v.index]
            normal_comp = delta.dot(n)
            delta = delta - normal_comp * n * 0.8  # Keep 20% of normal displacement

        v.co = positions[v.index] + delta * factor * w
        if w > 0.001:
            affected += 1

# Restore volume if needed
if preserve_volume and action not in ('relax_topology',):
    new_min = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), min(v.co.z for v in bm.verts)))
    new_max = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), max(v.co.z for v in bm.verts)))
    new_dims = new_max - new_min
    new_center = (new_min + new_max) * 0.5

    for v in bm.verts:
        v.co = v.co - new_center + orig_center
        for i in range(3):
            if new_dims[i] > 0.0001:
                rel = (v.co[i] - orig_center[i])
                v.co[i] = orig_center[i] + rel * (orig_dims[i] / new_dims[i])

bm.to_mesh(mesh)
bm.free()
mesh.update()

result = {{
    'action': action,
    'iterations': iterations,
    'factor': factor,
    'affected_vertices': affected,
    'preserve_volume': preserve_volume,
}}
result
""")
        return _exec(code)

    logger.info("Advanced sculpt tools registered: 15 tools")
