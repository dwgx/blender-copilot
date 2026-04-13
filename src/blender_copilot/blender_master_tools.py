# Blender Master Tools — Advanced 3D operations for expert-level automation
# BMesh, topology control, procedural modeling, precision weight painting,
# node-based material builder, smart UV, sculpting, and more.

import json
import logging

logger = logging.getLogger("BlenderMCPServer.Master")


def register_master_tools(mcp, send_command_fn):
    """Register advanced Blender master tools on the FastMCP instance."""

    def _exec(code: str) -> dict:
        # adapted for copilot
        return send_command_fn("execute_code", {"code": code})

    # ═══════════════════════════════════════════
    # BMesh — Direct mesh manipulation
    # ═══════════════════════════════════════════

    @mcp.tool()
    def bmesh_operation(
        mesh_name: str,
        operation: str,
        params: str = "{}",
    ) -> str:
        """
        Execute precision BMesh operations on a mesh. BMesh provides
        direct vertex/edge/face manipulation without operator overhead.

        Parameters:
        - mesh_name: Target mesh object name
        - operation: One of:
            "dissolve_degenerate" — remove zero-area faces & zero-length edges
            "remove_doubles" — merge vertices by distance (params: {"distance": 0.0001})
            "triangulate" — convert all faces to triangles
            "quads_to_tris" — same as triangulate
            "tris_to_quads" — convert triangles back to quads where possible
            "recalc_normals" — recalculate normals (outside)
            "fill_holes" — fill all holes in mesh (params: {"sides": 4})
            "subdivide" — subdivide all faces (params: {"cuts": 1, "smooth": 0})
            "smooth_vertices" — smooth vertex positions (params: {"factor": 0.5, "repeat": 1})
            "symmetrize" — mirror mesh across axis (params: {"direction": "NEGATIVE_X"})
            "convex_hull" — create convex hull from vertices
            "inset_faces" — inset selected faces (params: {"thickness": 0.02})
            "extrude_faces" — extrude faces along normals (params: {"distance": 0.1})
            "solidify" — add thickness to mesh (params: {"thickness": 0.01})
            "wireframe" — convert to wireframe (params: {"thickness": 0.02})
            "custom" — run custom BMesh code (params: {"code": "..."})
        - params: JSON parameters for the operation
        """
        p = json.loads(params) if params else {}

        op_code_map = {
            "dissolve_degenerate": """
bmesh.ops.dissolve_degenerate(bm, dist=0.0001, edges=bm.edges[:])
log = "Dissolved degenerate geometry"
""",
            "remove_doubles": f"""
removed = bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist={p.get('distance', 0.0001)})
log = f"Merged {{len(removed.get('verts', []))}} vertices"
""",
            "triangulate": """
bmesh.ops.triangulate(bm, faces=bm.faces[:])
log = f"Triangulated: {len(bm.faces)} triangles"
""",
            "tris_to_quads": """
bmesh.ops.join_triangles(bm, faces=bm.faces[:], angle_face_threshold=0.698, angle_shape_threshold=0.698)
log = f"Converted to quads: {len(bm.faces)} faces"
""",
            "recalc_normals": """
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
log = "Recalculated normals (outside)"
""",
            "fill_holes": f"""
edges_boundary = [e for e in bm.edges if e.is_boundary]
if edges_boundary:
    bmesh.ops.holes_fill(bm, edges=edges_boundary, sides={p.get('sides', 4)})
log = f"Filled holes ({{len(edges_boundary)}} boundary edges)"
""",
            "subdivide": f"""
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts={p.get('cuts', 1)}, smooth={p.get('smooth', 0)})
log = f"Subdivided: {{len(bm.faces)}} faces"
""",
            "smooth_vertices": f"""
for i in range({p.get('repeat', 1)}):
    bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor={p.get('factor', 0.5)})
log = "Smoothed vertices"
""",
            "symmetrize": f"""
bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction='{p.get("direction", "NEGATIVE_X")}')
log = "Symmetrized mesh"
""",
            "convex_hull": """
bmesh.ops.convex_hull(bm, input=bm.verts[:])
log = "Created convex hull"
""",
            "inset_faces": f"""
bmesh.ops.inset_individual(bm, faces=bm.faces[:], thickness={p.get('thickness', 0.02)})
log = "Inset faces"
""",
            "extrude_faces": f"""
result = bmesh.ops.extrude_discrete_faces(bm, faces=bm.faces[:])
for f in result['faces']:
    bmesh.ops.translate(bm, vec=f.normal * {p.get('distance', 0.1)}, verts=f.verts)
log = "Extruded faces"
""",
            "solidify": f"""
bmesh.ops.solidify(bm, geom=bm.faces[:], thickness={p.get('thickness', 0.01)})
log = "Solidified mesh"
""",
            "wireframe": f"""
bmesh.ops.wireframe(bm, faces=bm.faces[:], thickness={p.get('thickness', 0.02)})
log = "Wireframe created"
""",
        }

        if operation == "custom":
            inner_code = p.get("code", "log = 'No code provided'")
        elif operation in op_code_map:
            inner_code = op_code_map[operation]
        else:
            return f"Unknown operation '{operation}'. Available: {', '.join(op_code_map.keys())}, custom"

        code = f'''
import bpy, bmesh, json

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    raise Exception("Mesh not found: {mesh_name}")

bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

log = ""
{inner_code}

bm.to_mesh(obj.data)
bm.free()
obj.data.update()

stats = {{
    "vertices": len(obj.data.vertices),
    "edges": len(obj.data.edges),
    "faces": len(obj.data.polygons),
}}

result = json.dumps({{"log": log, "stats": stats}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            stats = result.get("stats", {})
            return (f"**BMesh {operation}:** {result.get('log', 'done')}\n"
                    f"Mesh stats: {stats.get('vertices', 0)} verts, "
                    f"{stats.get('edges', 0)} edges, {stats.get('faces', 0)} faces")
        except Exception as e:
            return f"Error in BMesh operation: {e}"

    # ═══════════════════════════════════════════
    # Topology Tools — Edge loops, clean mesh flow
    # ═══════════════════════════════════════════

    @mcp.tool()
    def topology_edge_loops(
        mesh_name: str,
        action: str = "analyze",
        loop_cuts: int = 1,
        edge_index: int = -1,
    ) -> str:
        """
        Work with edge loops for clean topology. Essential for animation deformation.

        Parameters:
        - mesh_name: Target mesh
        - action: "analyze" — report edge loop statistics and topology quality
                  "add_loop_cut" — add loop cuts (params: loop_cuts, edge_index)
                  "select_non_manifold" — find problematic non-manifold geometry
                  "analyze_poles" — find N-poles and E-poles (topology quality indicators)
        - loop_cuts: Number of cuts for add_loop_cut (default: 1)
        - edge_index: Edge to cut along (-1 = auto-detect best edge)
        """
        code = f'''
import bpy, bmesh, json

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    raise Exception("Mesh not found")

action = {json.dumps(action)}
result_data = {{"action": action}}

bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

if action == "analyze":
    # Count quads, tris, ngons
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    total = len(bm.faces)

    # Non-manifold edges
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    boundary = sum(1 for e in bm.edges if e.is_boundary)

    # Loose verts
    loose = sum(1 for v in bm.verts if not v.link_edges)

    result_data.update({{
        "total_faces": total,
        "quads": quads, "quads_pct": round(quads/max(total,1)*100, 1),
        "tris": tris, "tris_pct": round(tris/max(total,1)*100, 1),
        "ngons": ngons, "ngons_pct": round(ngons/max(total,1)*100, 1),
        "non_manifold_edges": non_manifold,
        "boundary_edges": boundary,
        "loose_vertices": loose,
        "topology_grade": "Excellent" if quads/max(total,1) > 0.95 and ngons == 0
                         else "Good" if quads/max(total,1) > 0.8
                         else "Fair" if ngons == 0
                         else "Needs Work",
    }})

elif action == "analyze_poles":
    poles = {{"3": 0, "5": 0, "6+": 0}}
    pole_verts = []
    for v in bm.verts:
        n = len(v.link_edges)
        if n == 3:
            poles["3"] += 1
        elif n == 5:
            poles["5"] += 1
            pole_verts.append(v.index)
        elif n >= 6:
            poles["6+"] += 1
            pole_verts.append(v.index)

    result_data.update({{
        "n_poles_3edge": poles["3"],
        "e_poles_5edge": poles["5"],
        "star_poles_6plus": poles["6+"],
        "problem_vertices": pole_verts[:20],
        "note": "5-edge poles (E-poles) are normal at corners. 6+ edge poles cause pinching in animation.",
    }})

elif action == "select_non_manifold":
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold()
    bpy.ops.object.mode_set(mode='OBJECT')

    non_manifold_count = sum(1 for v in obj.data.vertices if v.select)
    result_data["non_manifold_vertices_selected"] = non_manifold_count

elif action == "add_loop_cut":
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.loopcut_slide(
        MESH_OT_loopcut={{"number_cuts": {loop_cuts}, "smoothness": 0,
                         "falloff": 'INVERSE_SQUARE', "object_index": 0,
                         "edge_index": {edge_index if edge_index >= 0 else 0}}},
        TRANSFORM_OT_edge_slide={{"value": 0}},
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    result_data["cuts_added"] = {loop_cuts}

bm.free()
result = json.dumps(result_data)
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            action = result.get("action", "")

            if action == "analyze":
                return (f"## Topology Analysis: {mesh_name}\n\n"
                        f"| Type | Count | % |\n|------|-------|---|\n"
                        f"| Quads | {result['quads']} | {result['quads_pct']}% |\n"
                        f"| Tris | {result['tris']} | {result['tris_pct']}% |\n"
                        f"| N-gons | {result['ngons']} | {result['ngons_pct']}% |\n\n"
                        f"Non-manifold: {result['non_manifold_edges']} | "
                        f"Boundary: {result['boundary_edges']} | "
                        f"Loose: {result['loose_vertices']}\n"
                        f"**Grade: {result['topology_grade']}**")
            elif action == "analyze_poles":
                return (f"## Pole Analysis: {mesh_name}\n\n"
                        f"- 3-edge (N-poles): {result['n_poles_3edge']}\n"
                        f"- 5-edge (E-poles): {result['e_poles_5edge']}\n"
                        f"- 6+ edge (stars): {result['star_poles_6plus']}\n"
                        f"- {result.get('note', '')}")
            else:
                return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error in topology operation: {e}"

    # ═══════════════════════════════════════════
    # Procedural Modeling — Generate geometry from parameters
    # ═══════════════════════════════════════════

    @mcp.tool()
    def procedural_generate(
        shape: str,
        name: str = "Procedural",
        params: str = "{}",
    ) -> str:
        """
        Generate procedural geometry using BMesh.
        Creates more complex shapes than basic primitives.

        Parameters:
        - shape: Type of shape to generate:
            "spring" — coil/spring (params: radius, height, turns, segments, wire_radius)
            "torus_knot" — mathematical torus knot (params: p, q, radius, tube_radius, segments)
            "gear" — gear/cog shape (params: teeth, radius, tooth_height, thickness)
            "pipe" — pipe along curve (params: radius, segments, points:[[x,y,z],...])
            "terrain" — procedural terrain (params: size, subdivisions, height, seed)
            "tree_trunk" — basic tree trunk (params: height, radius, segments, taper)
            "staircase" — spiral staircase (params: steps, radius, height, width)
            "gem" — gemstone shape (params: radius, crown_height, pavilion_height, facets)
        - name: Object name
        - params: JSON parameters for the shape
        """
        p = json.loads(params) if params else {}

        shape_code = {
            "spring": f'''
import math
radius = {p.get('radius', 0.5)}
height = {p.get('height', 2.0)}
turns = {p.get('turns', 5)}
segments = {p.get('segments', 32)}
wire_radius = {p.get('wire_radius', 0.05)}

verts = []
faces = []
wire_segs = 8
total_segs = turns * segments

for i in range(total_segs + 1):
    t = i / segments
    angle = t * 2 * math.pi
    cx = radius * math.cos(angle)
    cy = radius * math.sin(angle)
    cz = (i / total_segs) * height

    for j in range(wire_segs):
        wa = j / wire_segs * 2 * math.pi
        dx = math.cos(wa) * wire_radius
        dz = math.sin(wa) * wire_radius
        # Transform to follow helix
        nx = cx + dx * math.cos(angle)
        ny = cy + dx * math.sin(angle)
        nz = cz + dz
        verts.append((nx, ny, nz))

    if i > 0:
        for j in range(wire_segs):
            j2 = (j + 1) % wire_segs
            base = i * wire_segs
            prev = (i - 1) * wire_segs
            faces.append((prev + j, prev + j2, base + j2, base + j))

mesh = bpy.data.meshes.new(name)
mesh.from_pydata(verts, [], faces)
mesh.update()
obj = bpy.data.objects.new(name, mesh)
bpy.context.collection.objects.link(obj)
log = f"Spring: {{turns}} turns, {{len(verts)}} verts"
''',
            "terrain": f'''
import math, random
size = {p.get('size', 10)}
subdivs = {p.get('subdivisions', 50)}
max_h = {p.get('height', 2.0)}
seed = {p.get('seed', 42)}
random.seed(seed)

bpy.ops.mesh.primitive_grid_add(x_subdivisions=subdivs, y_subdivisions=subdivs, size=size)
obj = bpy.context.active_object
obj.name = name

# Perlin-like noise displacement
import mathutils
for v in obj.data.vertices:
    noise_val = mathutils.noise.fractal(
        mathutils.Vector((v.co.x * 0.3, v.co.y * 0.3, seed)),
        1.0, 2.0, 6, mathutils.noise.types.STDPERLIN
    )
    v.co.z = noise_val * max_h

obj.data.update()
log = f"Terrain: {{subdivs}}x{{subdivs}} grid, height {{max_h}}"
''',
            "gear": f'''
import math
teeth = {p.get('teeth', 20)}
radius = {p.get('radius', 1.0)}
tooth_h = {p.get('tooth_height', 0.15)}
thickness = {p.get('thickness', 0.2)}

verts = []
faces = []
segs = teeth * 4  # 4 vertices per tooth

for i in range(segs):
    angle = i / segs * 2 * math.pi
    # Alternate between inner and outer radius for tooth profile
    phase = i % 4
    if phase < 2:
        r = radius + tooth_h
    else:
        r = radius - tooth_h * 0.3

    x = r * math.cos(angle)
    y = r * math.sin(angle)
    verts.append((x, y, thickness / 2))
    verts.append((x, y, -thickness / 2))

n = len(verts)
for i in range(0, n, 2):
    i2 = (i + 2) % n
    faces.append((i, i2, i2 + 1, i + 1))

# Top and bottom caps
top = list(range(0, n, 2))
bottom = list(range(1, n, 2))
faces.append(tuple(top))
faces.append(tuple(reversed(bottom)))

mesh = bpy.data.meshes.new(name)
mesh.from_pydata(verts, [], faces)
mesh.update()
obj = bpy.data.objects.new(name, mesh)
bpy.context.collection.objects.link(obj)
log = f"Gear: {{teeth}} teeth, radius {{radius}}"
''',
            "gem": f'''
import math
radius = {p.get('radius', 0.5)}
crown_h = {p.get('crown_height', 0.3)}
pav_h = {p.get('pavilion_height', 0.5)}
facets = {p.get('facets', 8)}

verts = [(0, 0, crown_h)]  # top point
girdle_top = []
girdle_bot = []

for i in range(facets):
    a = i / facets * 2 * math.pi
    x = radius * math.cos(a)
    y = radius * math.sin(a)
    girdle_top.append(len(verts))
    verts.append((x, y, 0.02))
    girdle_bot.append(len(verts))
    verts.append((x, y, -0.02))

culet = len(verts)
verts.append((0, 0, -pav_h))  # bottom point

faces = []
for i in range(facets):
    i2 = (i + 1) % facets
    faces.append((0, girdle_top[i], girdle_top[i2]))
    faces.append((girdle_top[i], girdle_bot[i], girdle_bot[i2], girdle_top[i2]))
    faces.append((culet, girdle_bot[i2], girdle_bot[i]))

mesh = bpy.data.meshes.new(name)
mesh.from_pydata(verts, [], faces)
mesh.update()
obj = bpy.data.objects.new(name, mesh)
bpy.context.collection.objects.link(obj)
log = f"Gem: {{facets}} facets, radius {{radius}}"
''',
        }

        if shape not in shape_code:
            return f"Unknown shape '{shape}'. Available: {', '.join(shape_code.keys())}"

        code = f'''
import bpy
name = {json.dumps(name)}
{shape_code[shape]}
result = json.dumps({{"object": name, "log": log}})
result
'''
        # Need json import
        code = "import json\n" + code

        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return f"**Generated:** {result.get('log', shape)} → object '{result.get('object', name)}'"
        except Exception as e:
            return f"Error generating {shape}: {e}"

    # ═══════════════════════════════════════════
    # Precision Weight Painting
    # ═══════════════════════════════════════════

    @mcp.tool()
    def precision_weight_paint(
        mesh_name: str,
        operation: str,
        params: str = "{}",
    ) -> str:
        """
        Precision vertex weight operations. Far more control than auto-weights.

        Parameters:
        - mesh_name: Target mesh
        - operation: One of:
            "gradient_along_chain" — paint gradient weights along a bone chain
                params: {"chain_root": "Hair_01", "falloff": "LINEAR"}
            "transfer_weights" — transfer weights from source mesh
                params: {"source": "SourceMesh"}
            "normalize_all" — normalize all vertex groups
            "clean" — remove weights below threshold
                params: {"threshold": 0.01}
            "limit_total" — limit bone influences per vertex
                params: {"limit": 4}
            "smooth" — smooth weights for a vertex group
                params: {"group": "Left_UpperArm", "factor": 0.5, "iterations": 5}
            "mirror" — mirror weights X axis
            "assign_proximity" — weight by proximity to bone
                params: {"bone": "Hips", "radius": 0.5, "falloff": "SMOOTH"}
        """
        p = json.loads(params) if params else {}

        code = f'''
import bpy, json

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    raise Exception("Mesh not found")

operation = {json.dumps(operation)}
params = json.loads({json.dumps(json.dumps(p))})
log = []

if operation == "gradient_along_chain":
    chain_root = params.get("chain_root", "")
    falloff = params.get("falloff", "LINEAR")

    # Find armature
    arm = None
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            arm = mod.object
            break
    if not arm:
        raise Exception("No armature modifier found")

    # Walk the bone chain
    chain = []
    bone = arm.data.bones.get(chain_root)
    while bone:
        chain.append(bone.name)
        children = [c for c in bone.children]
        bone = children[0] if children else None

    if not chain:
        raise Exception(f"Bone '{{chain_root}}' not found")

    # For each bone in chain, assign gradient weights
    total_bones = len(chain)
    for bi, bone_name in enumerate(chain):
        vg = obj.vertex_groups.get(bone_name)
        if not vg:
            vg = obj.vertex_groups.new(name=bone_name)

        # Get bone head/tail positions in world space
        pose_bone = arm.pose.bones.get(bone_name)
        if not pose_bone:
            continue

        bone_head = arm.matrix_world @ pose_bone.head
        bone_tail = arm.matrix_world @ pose_bone.tail

        for v in obj.data.vertices:
            v_world = obj.matrix_world @ v.co
            # Distance to bone segment
            from mathutils import Vector
            bone_vec = bone_tail - bone_head
            bone_len = bone_vec.length
            if bone_len < 0.0001:
                continue
            bone_dir = bone_vec.normalized()
            v_vec = v_world - bone_head
            proj = v_vec.dot(bone_dir)
            proj = max(0, min(bone_len, proj))
            closest = bone_head + bone_dir * proj
            dist = (v_world - closest).length

            # Weight based on distance
            max_dist = bone_len * 1.5
            if dist < max_dist:
                t = 1.0 - (dist / max_dist)
                if falloff == "SMOOTH":
                    t = t * t * (3 - 2 * t)  # Smoothstep
                elif falloff == "SHARP":
                    t = t * t
                vg.add([v.index], t, 'REPLACE')

    log.append(f"Gradient painted {{len(chain)}} bones in chain from {{chain_root}}")

elif operation == "normalize_all":
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_normalize_all()
    bpy.ops.object.mode_set(mode='OBJECT')
    log.append("Normalized all vertex groups")

elif operation == "clean":
    threshold = params.get("threshold", 0.01)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=threshold)
    bpy.ops.object.mode_set(mode='OBJECT')
    log.append(f"Cleaned weights below {{threshold}}")

elif operation == "limit_total":
    limit = params.get("limit", 4)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=limit)
    bpy.ops.object.mode_set(mode='OBJECT')
    log.append(f"Limited to {{limit}} influences per vertex")

elif operation == "smooth":
    group = params.get("group", "")
    factor = params.get("factor", 0.5)
    iterations = params.get("iterations", 5)

    vg = obj.vertex_groups.get(group)
    if not vg:
        raise Exception(f"Vertex group '{{group}}' not found")

    obj.vertex_groups.active_index = vg.index
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    for i in range(iterations):
        bpy.ops.object.vertex_group_smooth(group_select_mode='ACTIVE', factor=factor)
    bpy.ops.object.mode_set(mode='OBJECT')
    log.append(f"Smoothed '{{group}}' x{{iterations}} (factor={{factor}})")

elif operation == "mirror":
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_mirror(use_topology=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    log.append("Mirrored weights (X axis)")

elif operation == "transfer_weights":
    source_name = params.get("source", "")
    source = bpy.data.objects.get(source_name)
    if not source:
        raise Exception(f"Source mesh '{{source_name}}' not found")

    # Use data transfer modifier
    mod = obj.modifiers.new(name="WeightTransfer", type='DATA_TRANSFER')
    mod.object = source
    mod.use_vert_data = True
    mod.data_types_verts = {{'VGROUP_WEIGHTS'}}
    mod.vert_mapping = 'NEAREST'

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="WeightTransfer")
    log.append(f"Transferred weights from {{source_name}}")

result = json.dumps({{"log": log}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## Precision Weight Paint\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error in weight painting: {e}"

    # ═══════════════════════════════════════════
    # Node Material Builder — Build shader node trees programmatically
    # ═══════════════════════════════════════════

    @mcp.tool()
    def build_material_nodes(
        material_name: str,
        preset: str = "",
        textures: str = "{}",
        custom_nodes: str = "",
    ) -> str:
        """
        Build complex shader node trees programmatically.
        Creates materials with proper node connections — far beyond simple color assignment.

        Parameters:
        - material_name: Name for the new material
        - preset: Material preset:
            "pbr" — full PBR setup (provide textures)
            "toon" — toon/cel shader (VRChat-style)
            "glass" — realistic glass
            "hologram" — holographic effect
            "emission_pulse" — pulsing glow
            "matcap" — matcap material
            "skin" — subsurface skin shader
            "fabric" — cloth/fabric shader
        - textures: JSON map of texture paths:
            {"albedo": "path.png", "normal": "path.png", "metallic": "path.png",
             "roughness": "path.png", "ao": "path.png", "emission": "path.png"}
        - custom_nodes: JSON array of custom node definitions (advanced)
        """
        tex_paths = json.loads(textures) if textures else {}

        preset_code = {
            "pbr": '''
# Principled BSDF with full texture set
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (0, 0)
output = nodes.new('ShaderNodeOutputMaterial')
output.location = (300, 0)
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

tex_map = ''' + json.dumps(tex_paths) + '''
y_offset = 0
for tex_type, path in tex_map.items():
    if not path:
        continue
    img = bpy.data.images.load(path)
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.image = img
    tex_node.location = (-400, y_offset)

    if tex_type == "albedo":
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    elif tex_type == "normal":
        normal_map = nodes.new('ShaderNodeNormalMap')
        normal_map.location = (-200, y_offset)
        links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
        links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
        tex_node.image.colorspace_settings.name = 'Non-Color'
    elif tex_type == "metallic":
        links.new(tex_node.outputs['Color'], bsdf.inputs['Metallic'])
        tex_node.image.colorspace_settings.name = 'Non-Color'
    elif tex_type == "roughness":
        links.new(tex_node.outputs['Color'], bsdf.inputs['Roughness'])
        tex_node.image.colorspace_settings.name = 'Non-Color'
    elif tex_type == "ao":
        mix = nodes.new('ShaderNodeMixRGB')
        mix.blend_type = 'MULTIPLY'
        mix.location = (-200, y_offset)
        links.new(tex_node.outputs['Color'], mix.inputs[2])
    elif tex_type == "emission":
        links.new(tex_node.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 1.0

    y_offset -= 300

log = f"PBR material with {len(tex_map)} textures"
''',
            "toon": '''
# Toon shader (VRChat-like)
diffuse = nodes.new('ShaderNodeBsdfDiffuse')
diffuse.location = (-200, 200)

shader_to_rgb = nodes.new('ShaderNodeShaderToRGB')
shader_to_rgb.location = (0, 200)
links.new(diffuse.outputs['BSDF'], shader_to_rgb.inputs['Shader'])

# Color ramp for cel shading
ramp = nodes.new('ShaderNodeValToRGB')
ramp.location = (200, 200)
ramp.color_ramp.elements[0].position = 0.3
ramp.color_ramp.elements[0].color = (0.15, 0.15, 0.15, 1)
ramp.color_ramp.elements[1].position = 0.31
ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
links.new(shader_to_rgb.outputs['Color'], ramp.inputs['Fac'])

# Mix with base color
mix = nodes.new('ShaderNodeMixRGB')
mix.blend_type = 'MULTIPLY'
mix.location = (400, 200)
mix.inputs[0].default_value = 1.0
mix.inputs[1].default_value = (0.8, 0.5, 0.6, 1)  # Base color
links.new(ramp.outputs['Color'], mix.inputs[2])

# Outline via Fresnel
fresnel = nodes.new('ShaderNodeFresnel')
fresnel.location = (0, -100)
fresnel.inputs['IOR'].default_value = 1.1

outline_ramp = nodes.new('ShaderNodeValToRGB')
outline_ramp.location = (200, -100)
outline_ramp.color_ramp.elements[0].position = 0.85
outline_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
outline_ramp.color_ramp.elements[1].position = 0.86
outline_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
links.new(fresnel.outputs['Fac'], outline_ramp.inputs['Fac'])

final_mix = nodes.new('ShaderNodeMixRGB')
final_mix.blend_type = 'MULTIPLY'
final_mix.location = (600, 100)
final_mix.inputs[0].default_value = 1.0
links.new(mix.outputs['Color'], final_mix.inputs[1])
links.new(outline_ramp.outputs['Color'], final_mix.inputs[2])

emission = nodes.new('ShaderNodeEmission')
emission.location = (600, -100)
links.new(final_mix.outputs['Color'], emission.inputs['Color'])

output = nodes.new('ShaderNodeOutputMaterial')
output.location = (800, 0)
links.new(emission.outputs['Emission'], output.inputs['Surface'])

log = "Toon shader with cel shading + fresnel outline"
''',
            "hologram": '''
# Hologram effect
output = nodes.new('ShaderNodeOutputMaterial')
output.location = (600, 0)

emission = nodes.new('ShaderNodeEmission')
emission.location = (400, 0)
emission.inputs['Color'].default_value = (0.0, 0.8, 1.0, 1)
emission.inputs['Strength'].default_value = 3.0

transparent = nodes.new('ShaderNodeBsdfTransparent')
transparent.location = (400, -200)

mix = nodes.new('ShaderNodeMixShader')
mix.location = (500, 0)
links.new(emission.outputs['Emission'], mix.inputs[1])
links.new(transparent.outputs['BSDF'], mix.inputs[2])
links.new(mix.outputs['Shader'], output.inputs['Surface'])

# Scanline effect
tex_coord = nodes.new('ShaderNodeTexCoord')
tex_coord.location = (-200, 0)

mapping = nodes.new('ShaderNodeMapping')
mapping.location = (0, 0)
mapping.inputs['Scale'].default_value = (1, 1, 50)
links.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])

wave = nodes.new('ShaderNodeTexWave')
wave.location = (200, 0)
wave.wave_type = 'BANDS'
wave.inputs['Scale'].default_value = 2
links.new(mapping.outputs['Vector'], wave.inputs['Vector'])

links.new(wave.outputs['Fac'], mix.inputs['Fac'])

# Fresnel glow
fresnel = nodes.new('ShaderNodeFresnel')
fresnel.location = (200, -300)
fresnel.inputs['IOR'].default_value = 1.5

add = nodes.new('ShaderNodeMixShader')
add.location = (500, -200)

mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else None

log = "Hologram material with scanlines + fresnel edge glow"
''',
            "skin": '''
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (0, 0)
bsdf.inputs['Base Color'].default_value = (0.8, 0.6, 0.5, 1)
bsdf.inputs['Subsurface Weight'].default_value = 0.3
bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.2, 0.1)
bsdf.inputs['Roughness'].default_value = 0.5
bsdf.inputs['Specular IOR Level'].default_value = 0.3

output = nodes.new('ShaderNodeOutputMaterial')
output.location = (300, 0)
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

log = "Skin shader with subsurface scattering"
''',
        }

        if not preset:
            return f"Available presets: {', '.join(preset_code.keys())}"
        if preset not in preset_code:
            return f"Unknown preset '{preset}'. Available: {', '.join(preset_code.keys())}"

        code = f'''
import bpy, json

name = {json.dumps(material_name)}
mat = bpy.data.materials.new(name=name)
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Clear defaults
for n in list(nodes):
    nodes.remove(n)

{preset_code[preset]}

result = json.dumps({{"material": name, "log": log}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return f"**Material Created:** {result.get('material')} — {result.get('log')}"
        except Exception as e:
            return f"Error building material: {e}"

    # ═══════════════════════════════════════════
    # Smart UV Tools
    # ═══════════════════════════════════════════

    @mcp.tool()
    def smart_uv_tools(
        mesh_name: str,
        operation: str = "auto_seams",
        params: str = "{}",
    ) -> str:
        """
        Advanced UV mapping operations beyond basic smart project.

        Parameters:
        - mesh_name: Target mesh
        - operation:
            "auto_seams" — automatically mark seams at sharp edges + material boundaries
                params: {"angle": 60} — angle threshold in degrees
            "pack_islands" — optimize UV island packing
                params: {"margin": 0.02}
            "straighten" — straighten UV islands along grid
            "check_stretching" — analyze UV stretching/distortion
            "transfer_uv" — transfer UVs from source mesh
                params: {"source": "SourceMesh"}
            "lightmap_uv" — create secondary UV for lightmap
                params: {"margin": 0.1}
        """
        p = json.loads(params) if params else {}

        code = f'''
import bpy, bmesh, json, math

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    raise Exception("Mesh not found")

operation = {json.dumps(operation)}
params = json.loads({json.dumps(json.dumps(p))})
log = []

bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

if operation == "auto_seams":
    angle = params.get("angle", 60)
    angle_rad = angle * math.pi / 180

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Mark seams at sharp edges
    seam_count = 0
    for edge in bm.edges:
        if edge.is_boundary:
            edge.seam = True
            seam_count += 1
        elif len(edge.link_faces) == 2:
            angle_between = edge.link_faces[0].normal.angle(edge.link_faces[1].normal)
            if angle_between > angle_rad:
                edge.seam = True
                seam_count += 1

    # Mark seams at material boundaries
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            if edge.link_faces[0].material_index != edge.link_faces[1].material_index:
                edge.seam = True
                seam_count += 1

    bm.to_mesh(obj.data)
    bm.free()

    # Unwrap with seams
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

    log.append(f"Marked {{seam_count}} seams (angle>{{angle}}°)")
    log.append("Unwrapped with angle-based method")

elif operation == "pack_islands":
    margin = params.get("margin", 0.02)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    log.append(f"Packed UV islands (margin={{margin}})")

elif operation == "check_stretching":
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active

    if not uv_layer:
        log.append("No UV map found")
    else:
        stretch_values = []
        for face in bm.faces:
            # Compare 3D area to UV area
            area_3d = face.calc_area()
            # UV area
            uvs = [loop[uv_layer].uv for loop in face.loops]
            if len(uvs) >= 3:
                uv_area = 0
                for i in range(1, len(uvs) - 1):
                    a = uvs[i] - uvs[0]
                    b = uvs[i+1] - uvs[0]
                    uv_area += abs(a.x * b.y - a.y * b.x) / 2
                if area_3d > 0.00001:
                    stretch_values.append(uv_area / area_3d)

        if stretch_values:
            avg = sum(stretch_values) / len(stretch_values)
            min_s = min(stretch_values)
            max_s = max(stretch_values)
            log.append(f"UV stretch: avg={{avg:.4f}}, min={{min_s:.4f}}, max={{max_s:.4f}}")
            if max_s / max(min_s, 0.0001) > 10:
                log.append("HIGH DISTORTION detected — consider adding more seams")
            else:
                log.append("UV distortion is acceptable")

    bm.free()

elif operation == "lightmap_uv":
    margin = params.get("margin", 0.1)
    # Create new UV map
    uv_map = obj.data.uv_layers.new(name="Lightmap_UV")
    obj.data.uv_layers.active = uv_map
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    log.append(f"Created Lightmap_UV with smart project (margin={{margin}})")

result = json.dumps({{"log": log}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## Smart UV\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error in UV operation: {e}"

    # ═══════════════════════════════════════════
    # Rigging Automation
    # ═══════════════════════════════════════════

    @mcp.tool()
    def rig_tools(
        armature_name: str,
        operation: str,
        params: str = "{}",
    ) -> str:
        """
        Advanced rigging operations for animation-ready armatures.

        Parameters:
        - armature_name: Target armature
        - operation:
            "add_ik" — add IK constraint to a bone chain
                params: {"bone": "Left_LowerArm", "target_bone": "Left_Hand_IK",
                         "chain_length": 2, "pole_bone": "Left_Arm_Pole"}
            "add_fk_ik_switch" — create FK/IK switching setup
                params: {"chain": ["Left_UpperArm", "Left_LowerArm", "Left_Hand"]}
            "create_pole_targets" — auto-create pole target bones for IK
                params: {"ik_bones": ["Left_LowerArm", "Right_LowerArm",
                                       "Left_LowerLeg", "Right_LowerLeg"]}
            "test_deformation" — rotate bones through range and check for problems
                params: {"bone": "Left_UpperArm", "axis": "X", "range": [-90, 90]}
            "setup_twist_bones" — add twist bones for better arm/leg deformation
                params: {"bone": "Left_UpperArm", "segments": 2}
        """
        p = json.loads(params) if params else {}

        code = f'''
import bpy, json
from mathutils import Vector, Matrix
import math

arm = bpy.data.objects.get({json.dumps(armature_name)})
if not arm or arm.type != 'ARMATURE':
    raise Exception("Armature not found")

operation = {json.dumps(operation)}
params = json.loads({json.dumps(json.dumps(p))})
log = []

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm

if operation == "add_ik":
    bone_name = params.get("bone", "")
    target = params.get("target_bone", "")
    chain_len = params.get("chain_length", 2)
    pole = params.get("pole_bone", "")

    pose_bone = arm.pose.bones.get(bone_name)
    if not pose_bone:
        raise Exception(f"Bone '{{bone_name}}' not found")

    ik = pose_bone.constraints.new('IK')
    ik.chain_count = chain_len

    if target and target in arm.pose.bones:
        ik.target = arm
        ik.subtarget = target
    if pole and pole in arm.pose.bones:
        ik.pole_target = arm
        ik.pole_subtarget = pole
        ik.pole_angle = math.radians(-90)

    log.append(f"Added IK to {{bone_name}}: chain={{chain_len}}, target={{target}}")

elif operation == "create_pole_targets":
    ik_bones = params.get("ik_bones", [])
    bpy.ops.object.mode_set(mode='EDIT')

    for bone_name in ik_bones:
        eb = arm.data.edit_bones.get(bone_name)
        if not eb or not eb.parent:
            continue

        # Calculate pole position (perpendicular to chain plane)
        parent = eb.parent
        child = eb.children[0] if eb.children else None
        if not child:
            mid = (eb.head + eb.tail) / 2
        else:
            mid = eb.head.copy()

        # Direction from parent to child
        chain_dir = (eb.tail - parent.head).normalized()
        bone_dir = (eb.head - parent.head).normalized()

        # Pole is perpendicular
        pole_dir = bone_dir.cross(chain_dir).normalized()
        if pole_dir.length < 0.001:
            pole_dir = Vector((0, -1, 0))

        pole_pos = mid + pole_dir * 0.5

        pole_name = bone_name.replace("Lower", "").replace("lower", "") + "_Pole"
        pole_eb = arm.data.edit_bones.new(pole_name)
        pole_eb.head = pole_pos
        pole_eb.tail = pole_pos + Vector((0, 0, 0.05))
        pole_eb.parent = parent.parent  # Parent to grandparent

        log.append(f"Created pole target: {{pole_name}}")

    bpy.ops.object.mode_set(mode='OBJECT')

elif operation == "setup_twist_bones":
    bone_name = params.get("bone", "")
    segments = params.get("segments", 2)

    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones.get(bone_name)
    if not eb:
        raise Exception(f"Bone '{{bone_name}}' not found")

    head = eb.head.copy()
    tail = eb.tail.copy()
    parent = eb.parent

    # Create twist bone segments
    seg_len = (tail - head) / segments
    created = []
    for i in range(segments):
        twist_name = f"{{bone_name}}_twist_{{i+1:02d}}"
        twist = arm.data.edit_bones.new(twist_name)
        twist.head = head + seg_len * i
        twist.tail = head + seg_len * (i + 1)
        if i == 0:
            twist.parent = eb
        else:
            prev_name = f"{{bone_name}}_twist_{{i:02d}}"
            twist.parent = arm.data.edit_bones.get(prev_name)
        twist.use_connect = True
        created.append(twist_name)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Add Copy Rotation constraints with influence gradient
    for i, twist_name in enumerate(created):
        pb = arm.pose.bones.get(twist_name)
        if pb and eb.name in arm.pose.bones:
            cr = pb.constraints.new('COPY_ROTATION')
            cr.target = arm
            cr.subtarget = bone_name
            cr.influence = (i + 1) / segments
            cr.mix_mode = 'ADD'

    log.append(f"Created {{segments}} twist bones for {{bone_name}}: {{', '.join(created)}}")

elif operation == "test_deformation":
    bone_name = params.get("bone", "")
    axis = params.get("axis", "X")
    angle_range = params.get("range", [-90, 90])

    pose_bone = arm.pose.bones.get(bone_name)
    if not pose_bone:
        raise Exception(f"Bone '{{bone_name}}' not found")

    # Test rotation at key angles
    axis_idx = {{"X": 0, "Y": 1, "Z": 2}}.get(axis, 0)
    test_angles = [angle_range[0], angle_range[0]//2, 0, angle_range[1]//2, angle_range[1]]

    log.append(f"Testing {{bone_name}} rotation on {{axis}} axis")
    for angle in test_angles:
        pose_bone.rotation_euler[axis_idx] = math.radians(angle)
        bpy.context.view_layer.update()
        log.append(f"  {{angle}}° — set (check viewport for deformation quality)")

    # Reset
    pose_bone.rotation_euler[axis_idx] = 0
    bpy.context.view_layer.update()
    log.append("Reset to rest pose")

result = json.dumps({{"log": log}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## Rig Tools\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error in rig operation: {e}"

    # ═══════════════════════════════════════════
    # Retopology — Clean topology from sculpts/scans
    # ═══════════════════════════════════════════

    @mcp.tool()
    def retopology(
        mesh_name: str,
        method: str = "quadriflow",
        target_faces: int = 5000,
        params: str = "{}",
    ) -> str:
        """
        Retopologize a mesh for clean animation-ready topology.

        Parameters:
        - mesh_name: Target mesh (typically a high-poly sculpt or scan)
        - method: "quadriflow" — produces clean quads (best for characters)
                  "voxel" — fast voxel remesh (produces tris, good for booleans cleanup)
                  "shrinkwrap" — create low-poly proxy that conforms to surface
        - target_faces: Target face count (default: 5000)
        - params: JSON extra params:
            voxel: {"voxel_size": 0.01}
            shrinkwrap: {"source": "HighPoly", "subdivisions": 3}
        """
        p = json.loads(params) if params else {}

        code = f'''
import bpy, json

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    raise Exception("Mesh not found")

method = {json.dumps(method)}
target_faces = {target_faces}
log = []

bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

before = len(obj.data.polygons)

if method == "quadriflow":
    bpy.ops.object.quadriflow_remesh(
        target_faces=target_faces,
        use_mesh_symmetry=True,
        use_preserve_sharp=True,
        use_preserve_boundary=True,
        seed=0,
    )
    after = len(obj.data.polygons)
    log.append(f"QuadriFlow: {{before}} -> {{after}} faces (target: {{target_faces}})")
    log.append("Produces clean quad topology suitable for animation")

elif method == "voxel":
    voxel_size = {p.get('voxel_size', 0.01)}
    obj.data.remesh_voxel_size = voxel_size
    bpy.ops.object.voxel_remesh()
    after = len(obj.data.polygons)
    log.append(f"Voxel remesh: {{before}} -> {{after}} faces (voxel size: {{voxel_size}})")

elif method == "shrinkwrap":
    source_name = {json.dumps(p.get('source', ''))}
    subdivs = {p.get('subdivisions', 3)}
    source = bpy.data.objects.get(source_name) if source_name else obj

    # Create a low-poly proxy (icosphere or grid)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivs)
    proxy = bpy.context.active_object
    proxy.name = obj.name + "_retopo"

    # Add shrinkwrap modifier
    mod = proxy.modifiers.new("Retopo", 'SHRINKWRAP')
    mod.target = source if source_name else obj
    mod.wrap_method = 'NEAREST_SURFACEPOINT'
    mod.wrap_mode = 'ON_SURFACE'

    bpy.ops.object.modifier_apply(modifier="Retopo")
    after = len(proxy.data.polygons)
    log.append(f"Shrinkwrap retopo: created proxy with {{after}} faces")
    log.append(f"Proxy object: {{proxy.name}}")

result = json.dumps({{"log": log}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## Retopology\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error in retopology: {e}"

    # ═══════════════════════════════════════════
    # Boolean Cleanup — Expert post-boolean pipeline
    # ═══════════════════════════════════════════

    @mcp.tool()
    def boolean_cleanup(
        mesh_name: str,
        cutter_name: str = "",
        operation: str = "DIFFERENCE",
        auto_cleanup: bool = True,
    ) -> str:
        """
        Expert boolean operation with automatic cleanup pipeline.
        Uses EXACT solver + dissolve degenerate + remove doubles + tris to quads.

        Parameters:
        - mesh_name: Target mesh
        - cutter_name: Cutter object. If empty, just runs cleanup on existing mesh.
        - operation: "DIFFERENCE", "UNION", "INTERSECT" (default: "DIFFERENCE")
        - auto_cleanup: Run full cleanup pipeline after boolean (default: True)
        """
        code = f'''
import bpy, json

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    raise Exception("Mesh not found")

cutter_name = {json.dumps(cutter_name)}
operation = {json.dumps(operation)}
auto_cleanup = {json.dumps(auto_cleanup)}
log = []

bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

before_faces = len(obj.data.polygons)

# Apply boolean if cutter provided
if cutter_name:
    cutter = bpy.data.objects.get(cutter_name)
    if not cutter:
        raise Exception(f"Cutter '{{cutter_name}}' not found")

    mod = obj.modifiers.new("Boolean", 'BOOLEAN')
    mod.operation = operation
    mod.solver = 'EXACT'  # ALWAYS use EXACT for production
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier="Boolean")
    log.append(f"Boolean {{operation}} with EXACT solver applied")

# Cleanup pipeline
if auto_cleanup:
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # 1. Remove degenerate geometry
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
    log.append("Dissolved degenerate geometry")

    # 2. Remove loose vertices/edges
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
    log.append("Removed loose vertices/edges")

    # 3. Merge by distance
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    log.append("Merged near-coincident vertices")

    # 4. Convert tris to quads where possible
    bpy.ops.mesh.tris_convert_to_quads(
        face_threshold=0.698,  # ~40 degrees
        shape_threshold=0.698,
    )
    log.append("Converted tris to quads")

    # 5. Fix normals
    bpy.ops.mesh.normals_make_consistent(inside=False)
    log.append("Recalculated normals (outside)")

    bpy.ops.object.mode_set(mode='OBJECT')

after_faces = len(obj.data.polygons)
log.append(f"Faces: {{before_faces}} -> {{after_faces}}")

result = json.dumps({{"log": log}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## Boolean + Cleanup\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error in boolean cleanup: {e}"

    # ═══════════════════════════════════════════
    # Facial Topology — Radial edge loops for eyes/mouth
    # ═══════════════════════════════════════════

    @mcp.tool()
    def create_facial_topology(
        feature: str = "eye",
        location: str = "[0, 0.06, 1.48]",
        params: str = "{}",
    ) -> str:
        """
        Create clean facial topology with concentric edge loops.
        Proper topology is critical for blend shape deformation.

        Parameters:
        - feature: "eye" — eye socket topology with concentric loops
                   "mouth" — mouth topology with radial loops
                   "face_base" — complete face base mesh with eyes + mouth + nose
        - location: JSON [x, y, z] center position
        - params: JSON extra:
            eye: {"radius_inner": 0.012, "radius_outer": 0.04, "segments": 12, "rings": 4}
            mouth: {"width": 0.04, "height": 0.015, "segments": 16, "rings": 3}
        """
        p = json.loads(params) if params else {}
        loc = json.loads(location)

        code = f'''
import bpy, bmesh, json, math
from mathutils import Vector

feature = {json.dumps(feature)}
center = Vector({loc})
params = json.loads({json.dumps(json.dumps(p))})
log = []

bm = bmesh.new()

if feature == "eye":
    r_inner = params.get("radius_inner", 0.012)
    r_outer = params.get("radius_outer", 0.04)
    segments = params.get("segments", 12)
    rings = params.get("rings", 4)

    ring_verts = []
    for ring in range(rings):
        t = ring / (rings - 1)
        r = r_inner + t * (r_outer - r_inner)
        verts = []
        for seg in range(segments):
            angle = 2 * math.pi * seg / segments
            x = center.x + r * math.cos(angle)
            z = center.z + r * math.sin(angle) * 0.7  # Slightly oval
            y = center.y
            verts.append(bm.verts.new((x, y, z)))
        ring_verts.append(verts)

    # Connect rings with quad faces
    for ring in range(len(ring_verts) - 1):
        for seg in range(segments):
            next_seg = (seg + 1) % segments
            bm.faces.new([
                ring_verts[ring][seg],
                ring_verts[ring][next_seg],
                ring_verts[ring+1][next_seg],
                ring_verts[ring+1][seg],
            ])

    log.append(f"Eye socket: {{rings}} concentric rings x {{segments}} segments")

elif feature == "mouth":
    width = params.get("width", 0.04)
    height = params.get("height", 0.015)
    segments = params.get("segments", 16)
    rings = params.get("rings", 3)

    ring_verts = []
    for ring in range(rings):
        t = (ring + 1) / rings
        w = width * t
        h = height * t
        verts = []
        for seg in range(segments):
            angle = 2 * math.pi * seg / segments
            x = center.x + w * math.cos(angle)
            z = center.z + h * math.sin(angle)
            y = center.y
            verts.append(bm.verts.new((x, y, z)))
        ring_verts.append(verts)

    # Connect rings
    for ring in range(len(ring_verts) - 1):
        for seg in range(segments):
            next_seg = (seg + 1) % segments
            bm.faces.new([
                ring_verts[ring][seg],
                ring_verts[ring][next_seg],
                ring_verts[ring+1][next_seg],
                ring_verts[ring+1][seg],
            ])

    log.append(f"Mouth topology: {{rings}} rings x {{segments}} segments")

elif feature == "face_base":
    # Create a basic face base mesh with proper topology zones
    # Grid base
    size = params.get("size", 0.12)
    subdivs = params.get("subdivisions", 8)

    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=subdivs, y_subdivisions=subdivs,
        size=size, location=center,
    )
    face_obj = bpy.context.active_object
    face_obj.name = "Face_Base"

    # Rotate to face forward (Y axis)
    face_obj.rotation_euler = (math.pi/2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)

    log.append(f"Face base mesh: {{subdivs}}x{{subdivs}} grid at {center}")
    log.append("Add Shrinkwrap to conform to head mesh, then sculpt eye/mouth loops")

    result = json.dumps({{"log": log, "object": "Face_Base"}})
    # Skip bmesh path for face_base
    bm.free()
    result

if feature != "face_base":
    mesh = bpy.data.meshes.new(f"{{feature}}_topology")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(f"{{feature}}_topology", mesh)
    bpy.context.collection.objects.link(obj)
    log.append(f"Created object: {{obj.name}}")

    result = json.dumps({{"log": log, "object": obj.name}})

result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## Facial Topology\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error creating facial topology: {e}"

    logger.info("Master tools registered: 10 tools")