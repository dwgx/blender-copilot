# Sculpt & Texture Bake Tools — Sculpt mode, brush strokes, texture baking,
# cloth simulation for modeling, and shape key capture from sculpt/sim states.

import json
import logging
from typing import Optional

logger = logging.getLogger("BlenderMCPServer.SculptBake")


def register_sculpt_bake_tools(mcp, send_command_fn):
    """Register sculpt and texture bake tools on the FastMCP instance."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    # ═══════════════════════════════════════════
    # Sculpt Mode
    # ═══════════════════════════════════════════

    @mcp.tool()
    def sculpt_mode_enter(
        mesh_name: str,
        multires_levels: int = 0,
        dyntopo: bool = False,
        detail_size: float = 12.0,
    ) -> dict:
        """Enter sculpt mode on a mesh object.

        Args:
            mesh_name: Name of the mesh object.
            multires_levels: If > 0, add a Multires modifier with this many subdivision levels.
            dyntopo: Enable dynamic topology sculpting (mutually exclusive with Multires).
            detail_size: Dyntopo detail size (smaller = more detail). Default 12.
        """
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": f"Mesh '{{mesh_name}}' not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)

    multires_levels = {multires_levels}
    dyntopo = {dyntopo}

    if multires_levels > 0:
        mod = obj.modifiers.new(name="Multires", type='MULTIRES')
        for i in range(multires_levels):
            bpy.ops.object.multires_subdivide(modifier="Multires", mode='CATMULL_CLARK')

    bpy.ops.object.mode_set(mode='SCULPT')

    if dyntopo and multires_levels == 0:
        try:
            bpy.ops.sculpt.dynamic_topology_toggle()
            bpy.context.scene.tool_settings.sculpt.detail_size = {detail_size}
        except:
            pass

    info = {{
        "object": obj.name,
        "mode": obj.mode,
        "vertex_count": len(obj.data.vertices),
        "multires_levels": multires_levels if multires_levels > 0 else 0,
        "dyntopo": dyntopo and multires_levels == 0,
    }}
    result = info
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Sculpt Brush Stroke
    # ═══════════════════════════════════════════

    @mcp.tool()
    def sculpt_brush_stroke(
        mesh_name: str,
        brush_type: str = "DRAW",
        strength: float = 0.5,
        radius: float = 50.0,
        stroke_points: str = "[]",
        use_symmetry_x: bool = True,
        use_symmetry_y: bool = False,
        use_symmetry_z: bool = False,
    ) -> dict:
        """Execute a programmatic sculpt brush stroke on a mesh.

        Uses bmesh vertex displacement for precise, reproducible sculpting
        that doesn't depend on screen coordinates.

        Args:
            mesh_name: Name of the mesh object.
            brush_type: Brush to use — DRAW, CLAY_STRIPS, SMOOTH, GRAB, INFLATE,
                       CREASE, FLATTEN, PINCH, SNAKE_HOOK.
            strength: Brush strength 0.0-1.0.
            radius: Brush radius in Blender units (world space).
            stroke_points: JSON array of {"x","y","z"} world-space points defining
                          the stroke path. Each point applies the brush effect.
            use_symmetry_x: Mirror across X axis (left/right).
            use_symmetry_y: Mirror across Y axis.
            use_symmetry_z: Mirror across Z axis.
        """
        code = f"""
import bpy, bmesh, json
from mathutils import Vector, kdtree

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    # Work in object mode with bmesh for precision
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    # Build KDTree for spatial queries
    size = len(bm.verts)
    kd = kdtree.KDTree(size)
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    stroke_pts = json.loads({json.dumps(stroke_points)})
    brush = {json.dumps(brush_type)}
    strength = {strength}
    radius = {radius}
    sym_x = {use_symmetry_x}
    sym_y = {use_symmetry_y}
    sym_z = {use_symmetry_z}

    affected_count = 0

    def apply_at(center):
        nonlocal affected_count
        results = kd.find_range(center, radius)
        for co, idx, dist in results:
            v = bm.verts[idx]
            falloff = 1.0 - (dist / radius)
            falloff = falloff * falloff * (3.0 - 2.0 * falloff)  # smoothstep
            displacement = falloff * strength

            if brush == "DRAW":
                v.co += v.normal * displacement * radius * 0.1
            elif brush == "CLAY_STRIPS":
                v.co += Vector((0, 0, 1)) * displacement * radius * 0.05
                v.co += v.normal * displacement * radius * 0.05
            elif brush == "SMOOTH":
                neighbors = [e.other_vert(v).co for e in v.link_edges]
                if neighbors:
                    avg = sum(neighbors, Vector()) / len(neighbors)
                    v.co = v.co.lerp(avg, displacement * 0.5)
            elif brush == "GRAB":
                if len(stroke_pts) >= 2:
                    delta = Vector(stroke_pts[-1].values()) - Vector(stroke_pts[0].values())
                    v.co += delta * displacement * 0.1
            elif brush == "INFLATE":
                v.co += v.normal * displacement * radius * 0.15
            elif brush == "CREASE":
                v.co += v.normal * displacement * radius * 0.08
                neighbors = [e.other_vert(v).co for e in v.link_edges]
                if neighbors:
                    avg = sum(neighbors, Vector()) / len(neighbors)
                    v.co = v.co.lerp(avg, -displacement * 0.3)
            elif brush == "FLATTEN":
                neighbors = [e.other_vert(v).co for e in v.link_edges]
                if neighbors:
                    avg = sum(neighbors, Vector()) / len(neighbors)
                    avg_normal = (avg - center).normalized()
                    plane_dist = (v.co - center).dot(avg_normal)
                    v.co -= avg_normal * plane_dist * displacement
            elif brush == "PINCH":
                to_center = (center - v.co).normalized()
                v.co += to_center * displacement * radius * 0.05
            elif brush == "SNAKE_HOOK":
                if len(stroke_pts) >= 2:
                    delta = Vector(stroke_pts[-1].values()) - Vector(stroke_pts[0].values())
                    v.co += delta * displacement * 0.2
            affected_count += 1

    for pt in stroke_pts:
        center = Vector((pt.get("x", 0), pt.get("y", 0), pt.get("z", 0)))
        apply_at(center)
        if sym_x:
            apply_at(Vector((-center.x, center.y, center.z)))
        if sym_y:
            apply_at(Vector((center.x, -center.y, center.z)))
        if sym_z:
            apply_at(Vector((center.x, center.y, -center.z)))

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    result = {{"brush": brush, "stroke_points": len(stroke_pts), "affected_vertices": affected_count}}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Sculpt Mask
    # ═══════════════════════════════════════════

    @mcp.tool()
    def sculpt_mask(
        mesh_name: str,
        action: str = "CLEAR",
        vertex_group: str = "",
        invert: bool = False,
    ) -> dict:
        """Manage sculpt masks on a mesh.

        Args:
            mesh_name: Name of the mesh object.
            action: Mask action — CLEAR (remove mask), INVERT (flip), SMOOTH,
                   SHARPEN, GROW, SHRINK, FROM_VERTEX_GROUP.
            vertex_group: Vertex group name (required for FROM_VERTEX_GROUP action).
            invert: Invert the resulting mask.
        """
        code = f"""
import bpy, bmesh

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    action = {json.dumps(action)}
    vg_name = {json.dumps(vertex_group)}
    do_invert = {invert}

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    mask_layer = bm.verts.layers.paint_mask.verify()

    if action == "CLEAR":
        for v in bm.verts:
            v[mask_layer] = 0.0
    elif action == "INVERT":
        for v in bm.verts:
            v[mask_layer] = 1.0 - v[mask_layer]
    elif action == "SMOOTH":
        for v in bm.verts:
            neighbors = [e.other_vert(v) for e in v.link_edges]
            if neighbors:
                avg = sum(n[mask_layer] for n in neighbors) / len(neighbors)
                v[mask_layer] = v[mask_layer] * 0.5 + avg * 0.5
    elif action == "SHARPEN":
        for v in bm.verts:
            val = v[mask_layer]
            v[mask_layer] = max(0.0, min(1.0, val * 2.0 - 0.5))
    elif action == "GROW":
        vals = [v[mask_layer] for v in bm.verts]
        for i, v in enumerate(bm.verts):
            neighbors = [e.other_vert(v) for e in v.link_edges]
            v[mask_layer] = max(vals[i], max((vals[n.index] for n in neighbors), default=0))
    elif action == "SHRINK":
        vals = [v[mask_layer] for v in bm.verts]
        for i, v in enumerate(bm.verts):
            neighbors = [e.other_vert(v) for e in v.link_edges]
            if any(vals[n.index] < 0.5 for n in neighbors):
                v[mask_layer] = 0.0
    elif action == "FROM_VERTEX_GROUP":
        vg = obj.vertex_groups.get(vg_name)
        if vg:
            vg_idx = vg.index
            for v in bm.verts:
                try:
                    w = 0.0
                    for g in obj.data.vertices[v.index].groups:
                        if g.group == vg_idx:
                            w = g.weight
                            break
                    v[mask_layer] = w
                except:
                    v[mask_layer] = 0.0

    if do_invert:
        for v in bm.verts:
            v[mask_layer] = 1.0 - v[mask_layer]

    masked = sum(1 for v in bm.verts if v[mask_layer] > 0.5)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    result = {{"action": action, "masked_vertices": masked, "total_vertices": len(obj.data.vertices)}}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Sculpt Remesh
    # ═══════════════════════════════════════════

    @mcp.tool()
    def sculpt_remesh(
        mesh_name: str,
        method: str = "VOXEL",
        voxel_size: float = 0.02,
        detail_size: float = 12.0,
    ) -> dict:
        """Remesh a sculpt for uniform topology.

        Args:
            mesh_name: Name of the mesh object.
            method: VOXEL (uniform density) or DYNTOPO (adaptive, sculpt-mode only).
            voxel_size: Voxel size for VOXEL method (smaller = more detail).
            detail_size: Detail size for DYNTOPO method.
        """
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    method = {json.dumps(method)}
    verts_before = len(obj.data.vertices)

    if method == "VOXEL":
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        obj.data.remesh_voxel_size = {voxel_size}
        bpy.ops.object.voxel_remesh()
    elif method == "DYNTOPO":
        if obj.mode != 'SCULPT':
            bpy.ops.object.mode_set(mode='SCULPT')
        try:
            bpy.ops.sculpt.dynamic_topology_toggle()
        except:
            pass
        bpy.context.scene.tool_settings.sculpt.detail_size = {detail_size}
        bpy.ops.sculpt.detail_flood_fill()

    verts_after = len(obj.data.vertices)
    result = {{"method": method, "verts_before": verts_before, "verts_after": verts_after}}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Sculpt Detail Flood
    # ═══════════════════════════════════════════

    @mcp.tool()
    def sculpt_detail_flood(
        mesh_name: str,
        detail_size: float = 12.0,
    ) -> dict:
        """Flood-fill detail for uniform resolution in dynamic topology sculpting.

        Args:
            mesh_name: Name of the mesh object (must be in sculpt mode with dyntopo).
            detail_size: Target detail size (smaller = finer).
        """
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'SCULPT':
        bpy.ops.object.mode_set(mode='SCULPT')
    bpy.context.scene.tool_settings.sculpt.detail_size = {detail_size}
    try:
        bpy.ops.sculpt.detail_flood_fill()
        result = {{"detail_size": {detail_size}, "vertices": len(obj.data.vertices)}}
    except Exception as e:
        result = {{"error": f"Detail flood failed (dyntopo may not be active): {{e}}"}}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Sculpt Extract Face Set
    # ═══════════════════════════════════════════

    @mcp.tool()
    def sculpt_extract_face_set(
        mesh_name: str,
        face_set_id: int = 1,
        thickness: float = 0.01,
    ) -> dict:
        """Extract a face set from a sculpted mesh as a separate object.

        Useful for creating accessories, clothing pieces, or separating features
        from a base sculpt.

        Args:
            mesh_name: Name of the mesh object.
            face_set_id: Face set ID to extract (starts at 1).
            thickness: Solidify thickness for the extracted piece.
        """
        code = f"""
import bpy, bmesh

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    if obj.mode != 'OBJECT':
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')

    # Duplicate the mesh
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate()
    extracted = bpy.context.active_object
    extracted.name = f"{{obj.name}}_faceset_{{face_set_id}}"

    # Remove faces not in the target face set
    bm = bmesh.new()
    bm.from_mesh(extracted.data)
    bm.faces.ensure_lookup_table()

    fs_layer = bm.faces.layers.face_map.active or bm.faces.layers.int.get('.sculpt_face_set')
    faces_to_remove = []

    if fs_layer:
        for f in bm.faces:
            if f[fs_layer] != {face_set_id}:
                faces_to_remove.append(f)
    else:
        # No face sets — extract based on selection or keep all
        pass

    bmesh.ops.delete(bm, geom=faces_to_remove, context='FACES')
    bm.to_mesh(extracted.data)
    bm.free()

    # Optional solidify
    thickness = {thickness}
    if thickness > 0:
        mod = extracted.modifiers.new("Solidify", 'SOLIDIFY')
        mod.thickness = thickness
        bpy.context.view_layer.objects.active = extracted
        bpy.ops.object.modifier_apply(modifier="Solidify")

    extracted.data.update()
    result = {{
        "extracted": extracted.name,
        "vertices": len(extracted.data.vertices),
        "faces": len(extracted.data.polygons),
    }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Sculpt to Shape Key
    # ═══════════════════════════════════════════

    @mcp.tool()
    def sculpt_to_shape_key(
        mesh_name: str,
        shape_key_name: str,
        basis_name: str = "Basis",
    ) -> dict:
        """Save the current mesh state as a shape key relative to the basis.

        Critical for face tracking workflow — sculpt a facial pose, then
        save it as a blend shape (shape key).

        Args:
            mesh_name: Name of the mesh object.
            shape_key_name: Name for the new shape key (e.g., 'mouthSmileLeft').
            basis_name: Name of the basis shape key (auto-created if missing).
        """
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    if obj.mode != 'OBJECT':
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')

    sk_name = {json.dumps(shape_key_name)}
    basis = {json.dumps(basis_name)}

    # Ensure basis exists
    if not obj.data.shape_keys:
        obj.shape_key_add(name=basis, from_mix=False)

    # Current vertex positions are the sculpted state
    current_coords = [v.co.copy() for v in obj.data.vertices]

    # Create new shape key from current state
    new_key = obj.shape_key_add(name=sk_name, from_mix=False)

    # Copy current coordinates to the new shape key
    for i, v in enumerate(new_key.data):
        v.co = current_coords[i]

    # Reset mesh to basis (restore vertices to basis positions)
    basis_kb = obj.data.shape_keys.key_blocks.get(basis)
    if basis_kb:
        for i, v in enumerate(obj.data.vertices):
            v.co = basis_kb.data[i].co.copy()
    obj.data.update()

    # Count displaced vertices
    displaced = 0
    max_disp = 0.0
    for i in range(len(current_coords)):
        delta = (current_coords[i] - basis_kb.data[i].co).length
        if delta > 0.0001:
            displaced += 1
            max_disp = max(max_disp, delta)

    result = {{
        "shape_key": sk_name,
        "displaced_vertices": displaced,
        "max_displacement": round(max_disp, 6),
        "total_shape_keys": len(obj.data.shape_keys.key_blocks),
    }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Bake Textures
    # ═══════════════════════════════════════════

    @mcp.tool()
    def bake_textures(
        mesh_name: str,
        bake_types: str = '["DIFFUSE"]',
        resolution: int = 2048,
        output_dir: str = "//textures",
        samples: int = 64,
        margin: int = 16,
        high_poly: str = "",
    ) -> dict:
        """Bake texture maps from a mesh (or high-poly to low-poly).

        Args:
            mesh_name: Target mesh (low-poly for high→low bake, or single mesh).
            bake_types: JSON array of bake types — "NORMAL", "AO", "DIFFUSE",
                       "ROUGHNESS", "EMIT", "COMBINED", "SHADOW".
            resolution: Texture resolution (512, 1024, 2048, 4096).
            output_dir: Output directory for baked textures (Blender path format).
            samples: Render samples for baking.
            margin: Pixel margin around UV islands.
            high_poly: Optional high-poly mesh name for high→low baking.
        """
        code = f"""
import bpy, os

low = bpy.data.objects.get({json.dumps(mesh_name)})
if not low or low.type != 'MESH':
    result = {{"error": "Target mesh not found"}}
else:
    high_name = {json.dumps(high_poly)}
    high = bpy.data.objects.get(high_name) if high_name else None
    bake_types = {bake_types}
    resolution = {resolution}
    samples = {samples}
    margin = {margin}
    output_dir = bpy.path.abspath({json.dumps(output_dir)})

    os.makedirs(output_dir, exist_ok=True)

    # Switch to Cycles for baking
    prev_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = samples
    bpy.context.scene.render.bake.margin = margin

    # Ensure UV map exists
    if not low.data.uv_layers:
        bpy.context.view_layer.objects.active = low
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')

    baked = []
    for bake_type in bake_types:
        # Create image for baking
        img_name = f"{{low.name}}_{{bake_type.lower()}}"
        is_data = bake_type in ("NORMAL", "ROUGHNESS", "AO")
        img = bpy.data.images.new(img_name, width=resolution, height=resolution,
                                   alpha=False, float_buffer=is_data)
        img.colorspace_settings.name = 'Non-Color' if is_data else 'sRGB'

        # Assign image to all materials
        for mat_slot in low.material_slots:
            mat = mat_slot.material
            if not mat or not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                node.select = False
            # Create or find bake target node
            bake_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            bake_node.image = img
            bake_node.select = True
            mat.node_tree.nodes.active = bake_node

        # Select objects for baking
        bpy.ops.object.select_all(action='DESELECT')
        low.select_set(True)
        bpy.context.view_layer.objects.active = low

        if high:
            high.select_set(True)
            bpy.context.scene.render.bake.use_selected_to_active = True
            bpy.context.scene.render.bake.cage_extrusion = 0.02
        else:
            bpy.context.scene.render.bake.use_selected_to_active = False

        # Configure bake type specifics
        if bake_type == "DIFFUSE":
            bpy.context.scene.render.bake.use_pass_direct = False
            bpy.context.scene.render.bake.use_pass_indirect = False
            bpy.context.scene.render.bake.use_pass_color = True

        # Bake
        try:
            bpy.ops.object.bake(type=bake_type)
            filepath = os.path.join(output_dir, f"{{img_name}}.png")
            img.filepath_raw = filepath
            img.file_format = 'PNG'
            img.save()
            baked.append({{"type": bake_type, "path": filepath, "resolution": resolution}})
        except Exception as e:
            baked.append({{"type": bake_type, "error": str(e)}})

        # Clean up bake nodes
        for mat_slot in low.material_slots:
            mat = mat_slot.material
            if mat and mat.use_nodes:
                for node in list(mat.node_tree.nodes):
                    if node.type == 'TEX_IMAGE' and node.image == img:
                        mat.node_tree.nodes.remove(node)

    bpy.context.scene.render.engine = prev_engine
    result = {{"baked": baked, "output_dir": output_dir}}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Bake AO (simplified)
    # ═══════════════════════════════════════════

    @mcp.tool()
    def bake_ao(
        mesh_name: str,
        resolution: int = 1024,
        samples: int = 128,
        output_path: str = "",
    ) -> dict:
        """Bake ambient occlusion map for a mesh. Simplified single-map bake.

        Args:
            mesh_name: Name of the mesh object.
            resolution: Texture resolution.
            samples: Render samples (higher = cleaner).
            output_path: Custom output path. Auto-generates if empty.
        """
        code = f"""
import bpy, os

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    resolution = {resolution}
    output_path = {json.dumps(output_path)}
    if not output_path:
        output_path = bpy.path.abspath(f"//textures/{{obj.name}}_ao.png")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    prev_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = {samples}

    # Ensure UVs
    if not obj.data.uv_layers:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')

    img = bpy.data.images.new(f"{{obj.name}}_ao", width=resolution, height=resolution,
                               float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'

    # Set up bake target
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat and mat.use_nodes:
            node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            node.image = img
            node.select = True
            mat.node_tree.nodes.active = node

    # If no material, create one
    if not obj.material_slots:
        mat = bpy.data.materials.new(f"{{obj.name}}_bake")
        mat.use_nodes = True
        obj.data.materials.append(mat)
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = img
        node.select = True
        mat.node_tree.nodes.active = node

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.scene.render.bake.use_selected_to_active = False

    try:
        bpy.ops.object.bake(type='AO')
        img.filepath_raw = output_path
        img.file_format = 'PNG'
        img.save()
        result = {{"path": output_path, "resolution": resolution}}
    except Exception as e:
        result = {{"error": str(e)}}

    # Cleanup
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat and mat.use_nodes:
            for node in list(mat.node_tree.nodes):
                if node.type == 'TEX_IMAGE' and node.image == img:
                    mat.node_tree.nodes.remove(node)

    bpy.context.scene.render.engine = prev_engine
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Bake Normal Map
    # ═══════════════════════════════════════════

    @mcp.tool()
    def bake_normal_map(
        high_poly: str,
        low_poly: str,
        resolution: int = 2048,
        cage_extrusion: float = 0.02,
        samples: int = 64,
        output_path: str = "",
    ) -> dict:
        """Bake a normal map from high-poly to low-poly mesh.

        Args:
            high_poly: Name of the high-poly source mesh.
            low_poly: Name of the low-poly target mesh.
            resolution: Texture resolution (2048 recommended for body, 1024 for accessories).
            cage_extrusion: Ray distance for projection (increase if bake has gaps).
            samples: Render samples.
            output_path: Custom output path. Auto-generates if empty.
        """
        code = f"""
import bpy, os

high = bpy.data.objects.get({json.dumps(high_poly)})
low = bpy.data.objects.get({json.dumps(low_poly)})

if not high or not low:
    result = {{"error": "High-poly or low-poly mesh not found"}}
elif high.type != 'MESH' or low.type != 'MESH':
    result = {{"error": "Both objects must be meshes"}}
else:
    resolution = {resolution}
    output_path = {json.dumps(output_path)}
    if not output_path:
        output_path = bpy.path.abspath(f"//textures/{{low.name}}_normal.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    prev_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = {samples}
    bpy.context.scene.render.bake.margin = 16

    # Ensure UV on low-poly
    if not low.data.uv_layers:
        bpy.context.view_layer.objects.active = low
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')

    img = bpy.data.images.new(f"{{low.name}}_normal", width=resolution, height=resolution,
                               float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'

    # Ensure low-poly has material with bake target
    if not low.material_slots:
        mat = bpy.data.materials.new(f"{{low.name}}_bake")
        mat.use_nodes = True
        low.data.materials.append(mat)

    for mat_slot in low.material_slots:
        mat = mat_slot.material
        if mat and mat.use_nodes:
            node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            node.image = img
            node.select = True
            mat.node_tree.nodes.active = node

    # Select high, active low
    bpy.ops.object.select_all(action='DESELECT')
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low

    bpy.context.scene.render.bake.use_selected_to_active = True
    bpy.context.scene.render.bake.cage_extrusion = {cage_extrusion}

    try:
        bpy.ops.object.bake(type='NORMAL')
        img.filepath_raw = output_path
        img.file_format = 'PNG'
        img.save()
        result = {{"path": output_path, "resolution": resolution, "high": high.name, "low": low.name}}
    except Exception as e:
        result = {{"error": str(e)}}

    # Cleanup
    for mat_slot in low.material_slots:
        mat = mat_slot.material
        if mat and mat.use_nodes:
            for node in list(mat.node_tree.nodes):
                if node.type == 'TEX_IMAGE' and node.image == img:
                    mat.node_tree.nodes.remove(node)

    bpy.context.scene.render.engine = prev_engine
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Bake Diffuse to Atlas
    # ═══════════════════════════════════════════

    @mcp.tool()
    def bake_diffuse_to_atlas(
        mesh_names: str = "[]",
        atlas_size: int = 2048,
        output_path: str = "",
    ) -> dict:
        """Bake multiple meshes' diffuse colors to a single texture atlas.

        Combines all materials into one atlas, repacking UVs.

        Args:
            mesh_names: JSON array of mesh names to combine.
            atlas_size: Atlas texture resolution.
            output_path: Custom output path.
        """
        code = f"""
import bpy, os

names = {mesh_names}
meshes = [bpy.data.objects.get(n) for n in names if bpy.data.objects.get(n)]
meshes = [m for m in meshes if m.type == 'MESH']

if not meshes:
    result = {{"error": "No valid meshes found"}}
else:
    atlas_size = {atlas_size}
    output_path = {json.dumps(output_path)}
    if not output_path:
        output_path = bpy.path.abspath(f"//textures/atlas_diffuse.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    prev_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 32

    img = bpy.data.images.new("atlas_diffuse", width=atlas_size, height=atlas_size)

    for obj in meshes:
        # Ensure UV
        if not obj.data.uv_layers:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
            bpy.ops.object.mode_set(mode='OBJECT')

        for mat_slot in obj.material_slots:
            mat = mat_slot.material
            if mat and mat.use_nodes:
                node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                node.image = img
                node.select = True
                mat.node_tree.nodes.active = node

    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    bpy.context.scene.render.bake.use_selected_to_active = False
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True

    try:
        bpy.ops.object.bake(type='DIFFUSE')
        img.filepath_raw = output_path
        img.file_format = 'PNG'
        img.save()
        result = {{"path": output_path, "atlas_size": atlas_size, "meshes": [m.name for m in meshes]}}
    except Exception as e:
        result = {{"error": str(e)}}

    # Cleanup bake nodes
    for obj in meshes:
        for mat_slot in obj.material_slots:
            mat = mat_slot.material
            if mat and mat.use_nodes:
                for node in list(mat.node_tree.nodes):
                    if node.type == 'TEX_IMAGE' and node.image == img:
                        mat.node_tree.nodes.remove(node)

    bpy.context.scene.render.engine = prev_engine
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Texture Paint Fill
    # ═══════════════════════════════════════════

    @mcp.tool()
    def texture_paint_fill(
        mesh_name: str,
        color: str = "[1.0, 1.0, 1.0, 1.0]",
        resolution: int = 1024,
        image_name: str = "",
    ) -> dict:
        """Fill a texture with a solid color. Creates image if it doesn't exist.

        Foundation for texture painting workflow — creates a clean base texture.

        Args:
            mesh_name: Name of the mesh object.
            color: RGBA color as JSON array [R, G, B, A] with values 0.0-1.0.
            resolution: Image resolution if creating new.
            image_name: Name for the texture. Auto-generated if empty.
        """
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    color = {color}
    resolution = {resolution}
    img_name = {json.dumps(image_name)} or f"{{obj.name}}_texture"

    # Create or get image
    img = bpy.data.images.get(img_name)
    if not img:
        img = bpy.data.images.new(img_name, width=resolution, height=resolution, alpha=True)

    # Fill with color
    pixels = list(img.pixels)
    for i in range(0, len(pixels), 4):
        pixels[i] = color[0]
        pixels[i+1] = color[1]
        pixels[i+2] = color[2]
        pixels[i+3] = color[3] if len(color) > 3 else 1.0
    img.pixels[:] = pixels
    img.update()

    # Assign to material if possible
    if obj.material_slots:
        mat = obj.material_slots[0].material
        if mat and mat.use_nodes:
            principled = None
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled = node
                    break
            if principled:
                tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                tex_node.image = img
                mat.node_tree.links.new(tex_node.outputs['Color'],
                                         principled.inputs['Base Color'])

    result = {{"image": img_name, "resolution": resolution, "color": color}}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Cloth Simulation for Modeling
    # ═══════════════════════════════════════════

    @mcp.tool()
    def cloth_sim_model(
        mesh_name: str,
        pin_vertex_group: str = "",
        frames: int = 60,
        quality: int = 5,
        gravity: float = -9.8,
        stiffness: float = 15.0,
        damping: float = 5.0,
    ) -> dict:
        """Run cloth simulation for modeling purposes (e.g., draping fabric).

        Simulates cloth physics and applies the result to the mesh. Useful for
        creating natural fabric drapes, cape rest poses, or skirt shapes.

        Args:
            mesh_name: Name of the mesh to simulate.
            pin_vertex_group: Vertex group for pinned vertices (e.g., waist for skirt).
            frames: Number of frames to simulate.
            quality: Simulation quality steps per frame.
            gravity: Gravity strength (negative = downward).
            stiffness: Cloth structural stiffness.
            damping: Cloth damping.
        """
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Remove existing cloth modifier
    for mod in obj.modifiers:
        if mod.type == 'CLOTH':
            obj.modifiers.remove(mod)

    # Add cloth modifier
    mod = obj.modifiers.new("Cloth", 'CLOTH')
    cloth = mod.settings
    cloth.quality = {quality}
    cloth.mass = 0.3
    cloth.tension_stiffness = {stiffness}
    cloth.compression_stiffness = {stiffness}
    cloth.bending_stiffness = {stiffness} * 0.5
    cloth.tension_damping = {damping}
    cloth.compression_damping = {damping}

    # Pin group
    pin_group = {json.dumps(pin_vertex_group)}
    if pin_group and pin_group in [vg.name for vg in obj.vertex_groups]:
        cloth.vertex_group_mass = pin_group

    # Set gravity
    bpy.context.scene.gravity[2] = {gravity}

    # Set frame range and bake
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = {frames}
    bpy.context.scene.frame_set(1)

    # Bake the simulation
    override = bpy.context.copy()
    override['point_cache'] = mod.point_cache
    try:
        bpy.ops.ptcache.bake(override, bake=True)
    except:
        # Fallback: step through frames
        for f in range(1, {frames} + 1):
            bpy.context.scene.frame_set(f)

    # Go to last frame and apply
    bpy.context.scene.frame_set({frames})
    bpy.ops.object.modifier_apply(modifier="Cloth")

    result = {{
        "mesh": obj.name,
        "frames_simulated": {frames},
        "vertices": len(obj.data.vertices),
        "pin_group": pin_group or "none",
    }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Cloth to Shape Key
    # ═══════════════════════════════════════════

    @mcp.tool()
    def cloth_to_shape_key(
        mesh_name: str,
        shape_key_name: str = "cloth_rest",
        pin_vertex_group: str = "",
        frames: int = 40,
        stiffness: float = 15.0,
    ) -> dict:
        """Run cloth simulation and save result as a shape key.

        Useful for creating natural rest poses for skirts, capes, and other
        clothing that should hang naturally from a pin point.

        Args:
            mesh_name: Name of the mesh object.
            shape_key_name: Name for the resulting shape key.
            pin_vertex_group: Vertex group for pinned vertices.
            frames: Simulation frames.
            stiffness: Cloth stiffness.
        """
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    sk_name = {json.dumps(shape_key_name)}

    # Ensure basis shape key
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)

    # Save original positions
    basis_coords = [v.co.copy() for v in obj.data.vertices]

    # Duplicate for simulation
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.object.duplicate()
    sim_obj = bpy.context.active_object
    sim_obj.name = f"{{obj.name}}_cloth_sim_temp"

    # Remove shape keys from sim copy
    if sim_obj.data.shape_keys:
        bpy.context.view_layer.objects.active = sim_obj
        while sim_obj.data.shape_keys and len(sim_obj.data.shape_keys.key_blocks) > 0:
            sim_obj.shape_key_clear()

    # Add cloth modifier
    mod = sim_obj.modifiers.new("Cloth", 'CLOTH')
    cloth = mod.settings
    cloth.quality = 5
    cloth.tension_stiffness = {stiffness}
    cloth.compression_stiffness = {stiffness}

    pin_group = {json.dumps(pin_vertex_group)}
    if pin_group and pin_group in [vg.name for vg in sim_obj.vertex_groups]:
        cloth.vertex_group_mass = pin_group

    bpy.context.scene.gravity[2] = -9.8
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = {frames}

    # Step through simulation
    for f in range(1, {frames} + 1):
        bpy.context.scene.frame_set(f)

    # Apply cloth modifier
    bpy.context.view_layer.objects.active = sim_obj
    bpy.ops.object.modifier_apply(modifier="Cloth")

    # Transfer simulated positions to shape key on original
    sim_coords = [v.co.copy() for v in sim_obj.data.vertices]

    new_key = obj.shape_key_add(name=sk_name, from_mix=False)
    for i, v in enumerate(new_key.data):
        if i < len(sim_coords):
            v.co = sim_coords[i]

    # Clean up sim object
    bpy.data.objects.remove(sim_obj, do_unlink=True)
    bpy.context.scene.frame_set(1)

    # Count displacement
    displaced = sum(1 for i in range(len(basis_coords))
                    if i < len(sim_coords) and (basis_coords[i] - sim_coords[i]).length > 0.0001)

    result = {{
        "shape_key": sk_name,
        "displaced_vertices": displaced,
        "total_shape_keys": len(obj.data.shape_keys.key_blocks),
    }}
"""
        return _exec(code)

    logger.info("Registered 14 sculpt & bake tools")
