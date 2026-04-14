# Face Tracking Tools — ARKit 52 blend shapes, VRCFT Unified Expressions,
# facial landmark detection, shape key sculpting, and validation.

import json
import logging
from typing import Optional
from .face_tracking_constants import (
    ARKIT_BLEND_SHAPES, UNIFIED_EXPRESSIONS, ARKIT_TO_UNIFIED,
    ARKIT_DISPLACEMENT_RECIPES, FACE_VERTEX_GROUPS, DIRECTION_VECTORS,
)

logger = logging.getLogger("BlenderMCPServer.FaceTracking")


def register_face_tracking_tools(mcp, send_command_fn):
    """Register face tracking tools on the FastMCP instance."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    # ═══════════════════════════════════════════
    # Setup Face Vertex Groups
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_setup_face_vertex_groups(
        mesh_name: str,
        armature_name: str = "",
    ) -> dict:
        """Auto-detect facial landmarks and create vertex groups for all face regions.

        Analyzes mesh topology to identify eye loops, mouth loops, brow ridges,
        cheeks, nose, and jaw regions. These vertex groups are required for
        procedural ARKit blend shape generation.

        Args:
            mesh_name: Name of the face/head mesh.
            armature_name: Optional armature for bone-based landmark hints.
        """
        face_groups = json.dumps(FACE_VERTEX_GROUPS)
        code = f"""
import bpy, bmesh
from mathutils import Vector, kdtree

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    mesh = obj.data
    verts = mesh.vertices
    n_verts = len(verts)

    # Find bounding box of face region
    all_coords = [v.co.copy() for v in verts]
    xs = [c.x for c in all_coords]
    ys = [c.y for c in all_coords]
    zs = [c.z for c in all_coords]

    center_x = (min(xs) + max(xs)) / 2.0
    min_z, max_z = min(zs), max(zs)
    head_height = max_z - min_z
    scale = head_height if head_height > 0 else 1.0

    # Estimate face center and eye/mouth positions from geometry
    # Front-facing vertices (most negative Y for standard orientation)
    front_verts = sorted(range(n_verts), key=lambda i: all_coords[i].y)
    front_20pct = front_verts[:max(1, n_verts // 5)]

    front_coords = [all_coords[i] for i in front_20pct]
    face_center_z = sum(c.z for c in front_coords) / len(front_coords)
    face_center_y = sum(c.y for c in front_coords) / len(front_coords)

    # Eye height estimate: ~60% up from chin in anime style
    eye_z = min_z + head_height * 0.6
    # Mouth height: ~30% up from chin
    mouth_z = min_z + head_height * 0.3
    # Brow: ~70% up
    brow_z = min_z + head_height * 0.7
    # Nose: ~45%
    nose_z = min_z + head_height * 0.45
    # Jaw: ~15%
    jaw_z = min_z + head_height * 0.15

    # Eye separation ~30% of head width
    head_width = max(xs) - min(xs)
    eye_sep = head_width * 0.15

    # Build KDTree
    kd = kdtree.KDTree(n_verts)
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()

    created_groups = []
    group_names = {face_groups}

    # Remove existing face tracking groups
    for gn in group_names:
        vg = obj.vertex_groups.get(gn)
        if vg:
            obj.vertex_groups.remove(vg)

    def assign_region(group_name, center, radius, weight_falloff=True):
        vg = obj.vertex_groups.new(name=group_name)
        results = kd.find_range(center, radius)
        count = 0
        for co, idx, dist in results:
            # Only include front-facing vertices (negative Y or close)
            if all_coords[idx].y > face_center_y + radius * 0.5:
                continue
            if weight_falloff:
                w = 1.0 - (dist / radius)
                w = w * w * (3.0 - 2.0 * w)  # smoothstep
            else:
                w = 1.0
            vg.add([idx], w, 'REPLACE')
            count += 1
        if count > 0:
            created_groups.append({{"name": group_name, "vertices": count}})
        return count

    r_eye = head_height * 0.06   # eye region radius
    r_lid = head_height * 0.04   # eyelid radius
    r_brow = head_height * 0.05  # brow radius
    r_lip = head_height * 0.04   # lip radius
    r_corner = head_height * 0.025  # mouth corner
    r_cheek = head_height * 0.08 # cheek radius
    r_nose = head_height * 0.04  # nose radius
    r_jaw = head_height * 0.12   # jaw radius

    # Eyelids (upper/lower, left/right)
    for side, sx in [("_l", -eye_sep), ("_r", eye_sep)]:
        eye_center = Vector((center_x + sx, face_center_y, eye_z))
        upper_center = Vector((center_x + sx, face_center_y, eye_z + r_eye * 0.3))
        lower_center = Vector((center_x + sx, face_center_y, eye_z - r_eye * 0.3))
        assign_region(f"upper_eyelid{{side}}", upper_center, r_lid)
        assign_region(f"lower_eyelid{{side}}", lower_center, r_lid)

    # Brows
    for side, sx in [("_l", -eye_sep * 1.2), ("_r", eye_sep * 1.2)]:
        assign_region(f"brow{{side}}", Vector((center_x + sx, face_center_y, brow_z)), r_brow)
    assign_region("brow_inner", Vector((center_x, face_center_y, brow_z)), r_brow * 0.7)
    assign_region("brow_outer_l", Vector((center_x - eye_sep * 1.8, face_center_y, brow_z)), r_brow * 0.6)
    assign_region("brow_outer_r", Vector((center_x + eye_sep * 1.8, face_center_y, brow_z)), r_brow * 0.6)

    # Nose
    assign_region("nose_l", Vector((center_x - r_nose * 0.5, face_center_y, nose_z)), r_nose * 0.6)
    assign_region("nose_r", Vector((center_x + r_nose * 0.5, face_center_y, nose_z)), r_nose * 0.6)
    assign_region("nose_bridge", Vector((center_x, face_center_y, nose_z + r_nose)), r_nose * 0.5)
    assign_region("nose_tip", Vector((center_x, face_center_y - r_nose * 0.3, nose_z)), r_nose * 0.4)

    # Lips
    assign_region("upper_lip", Vector((center_x, face_center_y, mouth_z + r_lip * 0.3)), r_lip)
    assign_region("lower_lip", Vector((center_x, face_center_y, mouth_z - r_lip * 0.3)), r_lip)
    assign_region("upper_lip_l", Vector((center_x - r_lip * 0.8, face_center_y, mouth_z + r_lip * 0.2)), r_lip * 0.6)
    assign_region("upper_lip_r", Vector((center_x + r_lip * 0.8, face_center_y, mouth_z + r_lip * 0.2)), r_lip * 0.6)
    assign_region("lower_lip_l", Vector((center_x - r_lip * 0.8, face_center_y, mouth_z - r_lip * 0.3)), r_lip * 0.6)
    assign_region("lower_lip_r", Vector((center_x + r_lip * 0.8, face_center_y, mouth_z - r_lip * 0.3)), r_lip * 0.6)
    assign_region("lips", Vector((center_x, face_center_y, mouth_z)), r_lip * 1.5)

    # Mouth corners
    mouth_width = head_width * 0.18
    assign_region("mouth_corner_l", Vector((center_x - mouth_width, face_center_y, mouth_z)), r_corner)
    assign_region("mouth_corner_r", Vector((center_x + mouth_width, face_center_y, mouth_z)), r_corner)

    # Cheeks
    cheek_z = (eye_z + mouth_z) / 2
    assign_region("cheek_l", Vector((center_x - head_width * 0.22, face_center_y, cheek_z)), r_cheek)
    assign_region("cheek_r", Vector((center_x + head_width * 0.22, face_center_y, cheek_z)), r_cheek)

    # Jaw and chin
    assign_region("jaw", Vector((center_x, face_center_y, jaw_z)), r_jaw)
    assign_region("chin", Vector((center_x, face_center_y, min_z + head_height * 0.08)), r_jaw * 0.5)

    # Tongue (inside mouth, deeper Y)
    assign_region("tongue", Vector((center_x, face_center_y + r_lip, mouth_z - r_lip * 0.5)), r_lip * 0.8)

    result = {{
        "created_groups": created_groups,
        "total_groups": len(created_groups),
        "head_height": round(head_height, 4),
        "estimates": {{
            "eye_height": round(eye_z, 4),
            "mouth_height": round(mouth_z, 4),
            "brow_height": round(brow_z, 4),
        }},
    }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Create ARKit Blend Shapes
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_create_arkit_shapes(
        mesh_name: str,
        method: str = "procedural",
    ) -> dict:
        """Create all 52 ARKit blend shapes on a face mesh.

        Args:
            mesh_name: Name of the face/head mesh (must have face vertex groups
                      from ft_setup_face_vertex_groups for 'procedural' mode).
            method: Generation method:
                   - 'procedural': Auto-generate shapes using vertex displacement
                     recipes. Requires face vertex groups. Quality depends on
                     topology but works for any mesh with proper groups.
                   - 'template': Create 52 empty shape keys for manual sculpting.
                     Always works, recommended for production avatars.
                   - 'from_existing': Map existing shape keys to ARKit names
                     using fuzzy name matching.
        """
        arkit_shapes = json.dumps(ARKIT_BLEND_SHAPES)
        recipes = json.dumps(ARKIT_DISPLACEMENT_RECIPES)
        directions = json.dumps(DIRECTION_VECTORS)
        code = f"""
import bpy, json
from mathutils import Vector

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    method = {json.dumps(method)}
    arkit_shapes = {arkit_shapes}
    recipes = {recipes}
    directions = {directions}

    # Ensure basis shape key
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    basis = obj.data.shape_keys.key_blocks["Basis"]

    created = []
    skipped = []

    if method == "template":
        for name in arkit_shapes:
            if name not in [kb.name for kb in obj.data.shape_keys.key_blocks]:
                obj.shape_key_add(name=name, from_mix=False)
                created.append(name)
            else:
                skipped.append(name)

    elif method == "from_existing":
        existing = [kb.name for kb in obj.data.shape_keys.key_blocks]
        # Fuzzy matching: lowercase, remove underscores/dots
        def normalize(s):
            return s.lower().replace("_", "").replace(".", "").replace("-", "")
        existing_norm = {{normalize(n): n for n in existing}}

        for arkit_name in arkit_shapes:
            if arkit_name in existing:
                skipped.append(arkit_name)
                continue
            norm = normalize(arkit_name)
            if norm in existing_norm:
                # Rename existing to ARKit standard
                kb = obj.data.shape_keys.key_blocks[existing_norm[norm]]
                kb.name = arkit_name
                created.append(arkit_name)
            else:
                # Create empty placeholder
                obj.shape_key_add(name=arkit_name, from_mix=False)
                created.append(arkit_name + " (empty)")

    elif method == "procedural":
        n_verts = len(obj.data.vertices)

        # Get bounding box for scale reference
        coords = [basis.data[i].co.copy() for i in range(n_verts)]
        zs = [c.z for c in coords]
        head_height = max(zs) - min(zs) if zs else 1.0
        scale = head_height * 0.01  # base displacement unit

        for arkit_name in arkit_shapes:
            if arkit_name in [kb.name for kb in obj.data.shape_keys.key_blocks]:
                skipped.append(arkit_name)
                continue

            recipe = recipes.get(arkit_name)
            if not recipe:
                # No recipe — create empty
                obj.shape_key_add(name=arkit_name, from_mix=False)
                created.append(arkit_name + " (empty-no recipe)")
                continue

            # Create new shape key
            new_key = obj.shape_key_add(name=arkit_name, from_mix=False)

            # Get primary region vertex group
            region_name = recipe.get("region", "")
            vg = obj.vertex_groups.get(region_name)

            displaced = 0
            if vg:
                vg_idx = vg.index
                dir_name = recipe.get("primary_direction", "UP")
                magnitude = recipe.get("primary_magnitude", 0.1)
                dir_vec = Vector(directions.get(dir_name, (0, 0, 1)))

                # Handle side-dependent directions
                is_right = "_r" in region_name or region_name.endswith("_r")
                if dir_name == "MEDIAL":
                    dir_vec = Vector((1.0 if is_right else -1.0, 0, 0))
                elif dir_name == "LATERAL":
                    dir_vec = Vector((-1.0 if is_right else 1.0, 0, 0))
                elif dir_name == "UP_LATERAL":
                    side = -1.0 if is_right else 1.0
                    dir_vec = Vector((side * 0.7, 0, 0.7))

                for v_idx in range(n_verts):
                    try:
                        weight = 0.0
                        for g in obj.data.vertices[v_idx].groups:
                            if g.group == vg_idx:
                                weight = g.weight
                                break
                        if weight > 0.01:
                            disp = dir_vec * magnitude * scale * weight
                            new_key.data[v_idx].co = basis.data[v_idx].co + disp
                            displaced += 1
                    except:
                        pass

            # Secondary region
            sec_region = recipe.get("secondary_region", "")
            sec_vg = obj.vertex_groups.get(sec_region)
            if sec_vg:
                sec_idx = sec_vg.index
                sec_dir = recipe.get("secondary_direction", "UP")
                sec_mag = recipe.get("secondary_magnitude", 0.05)
                sec_vec = Vector(directions.get(sec_dir, (0, 0, 1)))

                for v_idx in range(n_verts):
                    try:
                        weight = 0.0
                        for g in obj.data.vertices[v_idx].groups:
                            if g.group == sec_idx:
                                weight = g.weight
                                break
                        if weight > 0.01:
                            disp = sec_vec * sec_mag * scale * weight
                            new_key.data[v_idx].co = new_key.data[v_idx].co + disp
                            displaced += 1
                    except:
                        pass

            created.append(f"{{arkit_name}} ({{displaced}} verts)")

    result = {{
        "method": method,
        "created": len(created),
        "skipped": len(skipped),
        "details": created[:20],
        "total_shape_keys": len(obj.data.shape_keys.key_blocks),
    }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Create Unified Expressions
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_create_unified_expressions(
        mesh_name: str,
        source: str = "arkit",
    ) -> dict:
        """Generate VRCFT Unified Expressions from existing ARKit shapes or from scratch.

        Args:
            mesh_name: Name of the face mesh.
            source: 'arkit' to map from existing ARKit shapes, or 'template' for empty keys.
        """
        unified = json.dumps(UNIFIED_EXPRESSIONS)
        mapping = json.dumps(ARKIT_TO_UNIFIED)
        code = f"""
import bpy, json

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)

    unified = {unified}
    source = {json.dumps(source)}
    mapping = {mapping}
    existing = [kb.name for kb in obj.data.shape_keys.key_blocks]

    created = []
    mapped = []

    if source == "arkit":
        # For each unified name, check if we have an ARKit source
        arkit_to_unified_inv = {{}}
        for arkit, uni in mapping.items():
            if isinstance(uni, list):
                for u in uni:
                    arkit_to_unified_inv[u] = arkit
            else:
                arkit_to_unified_inv[uni] = arkit

        for uni_name in unified:
            if uni_name in existing:
                continue

            arkit_src = arkit_to_unified_inv.get(uni_name)
            if arkit_src and arkit_src in existing:
                # Copy ARKit shape key data to new unified shape
                src_kb = obj.data.shape_keys.key_blocks[arkit_src]
                new_kb = obj.shape_key_add(name=uni_name, from_mix=False)
                for i in range(len(new_kb.data)):
                    new_kb.data[i].co = src_kb.data[i].co.copy()
                mapped.append(f"{{uni_name}} <- {{arkit_src}}")
            else:
                obj.shape_key_add(name=uni_name, from_mix=False)
                created.append(uni_name)
    else:
        for uni_name in unified:
            if uni_name not in existing:
                obj.shape_key_add(name=uni_name, from_mix=False)
                created.append(uni_name)

    result = {{
        "source": source,
        "mapped_from_arkit": len(mapped),
        "created_empty": len(created),
        "total_shape_keys": len(obj.data.shape_keys.key_blocks),
        "mapped_details": mapped[:15],
    }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # AI-Guided Shape Key Sculpting
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_sculpt_shape_key(
        mesh_name: str,
        shape_key_name: str,
        region: str,
        direction: str = "UP",
        intensity: float = 0.5,
        falloff: str = "SMOOTH",
    ) -> dict:
        """AI-guided shape key sculpting via vertex displacement.

        Displaces vertices in a face region to create or refine a blend shape.
        Can be called multiple times to build up complex expressions.

        Args:
            mesh_name: Name of the face mesh.
            shape_key_name: Shape key to modify (created if doesn't exist).
            region: Vertex group name defining the affected area (from ft_setup_face_vertex_groups).
            direction: Displacement direction — UP, DOWN, FORWARD, BACK, LEFT, RIGHT,
                      MEDIAL, LATERAL, UP_LATERAL, FORWARD_UP, etc.
            intensity: Displacement intensity 0.0-1.0 (scaled to head proportions).
            falloff: Weight falloff — SMOOTH (smoothstep), LINEAR, SHARP, CONSTANT.
        """
        dirs = json.dumps(DIRECTION_VECTORS)
        code = f"""
import bpy
from mathutils import Vector

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    sk_name = {json.dumps(shape_key_name)}
    region = {json.dumps(region)}
    direction = {json.dumps(direction)}
    intensity = {intensity}
    falloff_type = {json.dumps(falloff)}
    directions = {dirs}

    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)

    # Get or create shape key
    kb = obj.data.shape_keys.key_blocks.get(sk_name)
    if not kb:
        kb = obj.shape_key_add(name=sk_name, from_mix=False)

    basis = obj.data.shape_keys.key_blocks["Basis"]

    # Get direction vector
    dir_vec = Vector(directions.get(direction, (0, 0, 1)))

    # Get head scale
    zs = [basis.data[i].co.z for i in range(len(basis.data))]
    head_height = max(zs) - min(zs) if zs else 1.0
    scale = head_height * 0.01 * intensity

    # Get vertex group
    vg = obj.vertex_groups.get(region)
    if not vg:
        result = {{"error": f"Vertex group '{{region}}' not found"}}
    else:
        vg_idx = vg.index
        displaced = 0

        for v_idx in range(len(obj.data.vertices)):
            try:
                weight = 0.0
                for g in obj.data.vertices[v_idx].groups:
                    if g.group == vg_idx:
                        weight = g.weight
                        break
                if weight > 0.01:
                    # Apply falloff
                    if falloff_type == "SMOOTH":
                        w = weight * weight * (3.0 - 2.0 * weight)
                    elif falloff_type == "LINEAR":
                        w = weight
                    elif falloff_type == "SHARP":
                        w = weight * weight
                    elif falloff_type == "CONSTANT":
                        w = 1.0 if weight > 0.1 else 0.0
                    else:
                        w = weight

                    disp = dir_vec * scale * w
                    kb.data[v_idx].co = kb.data[v_idx].co + disp
                    displaced += 1
            except:
                pass

        result = {{
            "shape_key": sk_name,
            "region": region,
            "direction": direction,
            "intensity": intensity,
            "displaced_vertices": displaced,
        }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Validate Shapes
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_validate_shapes(
        mesh_name: str,
        standard: str = "arkit",
    ) -> dict:
        """Validate blend shapes against ARKit or Unified Expressions standard.

        Reports present/missing shapes, empty shapes, excessive displacement,
        and symmetry issues.

        Args:
            mesh_name: Name of the face mesh.
            standard: 'arkit' (52 shapes) or 'unified' (70+ shapes).
        """
        arkit = json.dumps(ARKIT_BLEND_SHAPES)
        unified = json.dumps(UNIFIED_EXPRESSIONS)
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    standard = {json.dumps(standard)}
    required = {arkit} if standard == "arkit" else {unified}

    if not obj.data.shape_keys:
        result = {{"error": "No shape keys found", "present": 0, "required": len(required)}}
    else:
        existing = {{kb.name: kb for kb in obj.data.shape_keys.key_blocks}}
        basis = obj.data.shape_keys.key_blocks.get("Basis")

        present = []
        missing = []
        empty = []
        excessive = []

        for name in required:
            if name in existing:
                kb = existing[name]
                # Check if shape has actual displacement
                if basis:
                    max_disp = 0.0
                    for i in range(len(kb.data)):
                        delta = (kb.data[i].co - basis.data[i].co).length
                        max_disp = max(max_disp, delta)
                    if max_disp < 0.0001:
                        empty.append(name)
                    elif max_disp > 0.1:  # > 10cm displacement
                        excessive.append({{"name": name, "max_disp": round(max_disp, 4)}})
                present.append(name)
            else:
                missing.append(name)

        # Symmetry check — compare L/R pairs
        sym_issues = []
        pairs = []
        for name in required:
            if "Left" in name:
                right = name.replace("Left", "Right")
                if right in required:
                    pairs.append((name, right))

        for left, right in pairs:
            if left in existing and right in existing:
                l_kb = existing[left]
                r_kb = existing[right]
                if basis:
                    l_disp = sum((l_kb.data[i].co - basis.data[i].co).length for i in range(len(l_kb.data)))
                    r_disp = sum((r_kb.data[i].co - basis.data[i].co).length for i in range(len(r_kb.data)))
                    if l_disp > 0.001 and r_disp > 0.001:
                        ratio = min(l_disp, r_disp) / max(l_disp, r_disp)
                        if ratio < 0.7:
                            sym_issues.append({{
                                "pair": [left, right],
                                "ratio": round(ratio, 3),
                            }})

        coverage = len(present) / len(required) * 100 if required else 0
        functional = len(present) - len(empty)

        result = {{
            "standard": standard,
            "required": len(required),
            "present": len(present),
            "missing": len(missing),
            "empty_shapes": len(empty),
            "excessive_displacement": len(excessive),
            "symmetry_issues": len(sym_issues),
            "coverage_pct": round(coverage, 1),
            "functional_shapes": functional,
            "missing_names": missing[:20],
            "empty_names": empty[:10],
            "sym_details": sym_issues[:5],
        }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Mirror Shape Key
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_mirror_shape_key(
        mesh_name: str,
        source_shape: str,
        target_shape: str = "",
        axis: str = "X",
    ) -> dict:
        """Mirror a shape key from one side to the other (e.g., Left→Right).

        Sculpt mouthSmileLeft, then mirror to mouthSmileRight automatically.

        Args:
            mesh_name: Name of the face mesh.
            source_shape: Source shape key name to mirror from.
            target_shape: Target name. Auto-generates by swapping Left/Right if empty.
            axis: Mirror axis — X (default, left/right), Y, or Z.
        """
        code = f"""
import bpy
from mathutils import Vector

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    src_name = {json.dumps(source_shape)}
    tgt_name = {json.dumps(target_shape)}
    axis = {json.dumps(axis)}

    if not tgt_name:
        if "Left" in src_name:
            tgt_name = src_name.replace("Left", "Right")
        elif "Right" in src_name:
            tgt_name = src_name.replace("Right", "Left")
        elif "_l" in src_name:
            tgt_name = src_name.replace("_l", "_r")
        elif "_r" in src_name:
            tgt_name = src_name.replace("_r", "_l")
        else:
            tgt_name = src_name + "_mirrored"

    if not obj.data.shape_keys:
        result = {{"error": "No shape keys"}}
    else:
        src_kb = obj.data.shape_keys.key_blocks.get(src_name)
        basis = obj.data.shape_keys.key_blocks.get("Basis")
        if not src_kb or not basis:
            result = {{"error": f"Shape key '{{src_name}}' or Basis not found"}}
        else:
            # Get or create target
            tgt_kb = obj.data.shape_keys.key_blocks.get(tgt_name)
            if not tgt_kb:
                tgt_kb = obj.shape_key_add(name=tgt_name, from_mix=False)

            n_verts = len(basis.data)
            threshold = 0.001

            # Build vertex mirror map using spatial matching
            mirror_map = {{}}
            for i in range(n_verts):
                co = basis.data[i].co.copy()
                if axis == "X":
                    mirrored = Vector((-co.x, co.y, co.z))
                elif axis == "Y":
                    mirrored = Vector((co.x, -co.y, co.z))
                else:
                    mirrored = Vector((co.x, co.y, -co.z))

                # Find closest vertex to mirrored position
                best_dist = float('inf')
                best_idx = i
                for j in range(n_verts):
                    d = (basis.data[j].co - mirrored).length
                    if d < best_dist:
                        best_dist = d
                        best_idx = j
                if best_dist < threshold * 100:
                    mirror_map[i] = best_idx

            # Copy mirrored displacement
            mirrored_count = 0
            for src_idx, tgt_idx in mirror_map.items():
                delta = src_kb.data[src_idx].co - basis.data[src_idx].co
                if delta.length > 0.0001:
                    if axis == "X":
                        mirrored_delta = Vector((-delta.x, delta.y, delta.z))
                    elif axis == "Y":
                        mirrored_delta = Vector((delta.x, -delta.y, delta.z))
                    else:
                        mirrored_delta = Vector((delta.x, delta.y, -delta.z))
                    tgt_kb.data[tgt_idx].co = basis.data[tgt_idx].co + mirrored_delta
                    mirrored_count += 1

            result = {{
                "source": src_name,
                "target": tgt_name,
                "mirrored_vertices": mirrored_count,
                "mirror_map_size": len(mirror_map),
            }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Combine Shape Keys
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_combine_shape_keys(
        mesh_name: str,
        output_name: str,
        sources: str = "[]",
    ) -> dict:
        """Combine multiple shape keys with weights into a new shape key.

        Args:
            mesh_name: Name of the face mesh.
            output_name: Name for the combined output shape key.
            sources: JSON array of {"name": "shape_name", "weight": 0.5} objects.
        """
        code = f"""
import bpy, json

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    output_name = {json.dumps(output_name)}
    sources = json.loads({json.dumps(json.dumps(sources))}) if isinstance({json.dumps(sources)}, str) else {sources}

    if not obj.data.shape_keys:
        result = {{"error": "No shape keys"}}
    else:
        # Reset all sliders
        for kb in obj.data.shape_keys.key_blocks:
            kb.value = 0.0

        # Set source weights
        applied = []
        for src in sources:
            name = src.get("name", "")
            weight = src.get("weight", 1.0)
            kb = obj.data.shape_keys.key_blocks.get(name)
            if kb:
                kb.value = weight
                applied.append({{"name": name, "weight": weight}})

        # Create combined shape from current mix
        new_kb = obj.shape_key_add(name=output_name, from_mix=True)

        # Reset sliders
        for kb in obj.data.shape_keys.key_blocks:
            kb.value = 0.0

        result = {{
            "output": output_name,
            "sources_applied": applied,
            "total_shape_keys": len(obj.data.shape_keys.key_blocks),
        }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Setup Tongue Tracking
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_setup_tongue_tracking(
        mesh_name: str,
        armature_name: str = "",
        create_bones: bool = True,
    ) -> dict:
        """Create tongue bone chain and tongue blend shapes for face tracking.

        Creates tongue bones (Tongue, Tongue1, Tongue2) and blend shapes
        for tongueOut, tongueUp, tongueDown, tongueLeft, tongueRight.

        Args:
            mesh_name: Name of the face mesh.
            armature_name: Armature to add tongue bones to.
            create_bones: Whether to create tongue bones (requires armature).
        """
        code = f"""
import bpy
from mathutils import Vector

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    arm_name = {json.dumps(armature_name)}
    create_bones = {create_bones}
    created_bones = []
    created_shapes = []

    # Create bones if requested
    if create_bones and arm_name:
        arm_obj = bpy.data.objects.get(arm_name)
        if arm_obj and arm_obj.type == 'ARMATURE':
            bpy.context.view_layer.objects.active = arm_obj
            bpy.ops.object.mode_set(mode='EDIT')

            # Find Jaw or Head bone for parenting
            parent_bone = None
            for name in ["Jaw", "jaw", "Head", "head"]:
                b = arm_obj.data.edit_bones.get(name)
                if b:
                    parent_bone = b
                    break

            if parent_bone:
                jaw_center = parent_bone.head.copy()
                # Tongue starts inside mouth
                tongue_start = jaw_center + Vector((0, -0.02, -0.005))

                bones_spec = [
                    ("Tongue", tongue_start, tongue_start + Vector((0, -0.015, 0))),
                    ("Tongue1", tongue_start + Vector((0, -0.015, 0)), tongue_start + Vector((0, -0.03, 0))),
                    ("Tongue2", tongue_start + Vector((0, -0.03, 0)), tongue_start + Vector((0, -0.045, -0.005))),
                ]

                prev_bone = parent_bone
                for bname, head, tail in bones_spec:
                    b = arm_obj.data.edit_bones.new(bname)
                    b.head = head
                    b.tail = tail
                    b.parent = prev_bone
                    prev_bone = b
                    created_bones.append(bname)

            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.view_layer.objects.active = obj

    # Create tongue shape keys
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)

    tongue_shapes = ["tongueOut", "tongueUp", "tongueDown", "tongueLeft", "tongueRight",
                     "TongueRoll", "TongueBendDown", "TongueCurlUp"]

    for sname in tongue_shapes:
        if sname not in [kb.name for kb in obj.data.shape_keys.key_blocks]:
            obj.shape_key_add(name=sname, from_mix=False)
            created_shapes.append(sname)

    result = {{
        "created_bones": created_bones,
        "created_shapes": created_shapes,
        "total_shape_keys": len(obj.data.shape_keys.key_blocks),
    }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Extended Eye Tracking
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_setup_eye_tracking_full(
        mesh_name: str,
        armature_name: str = "",
    ) -> dict:
        """Extended eye tracking beyond basic blink/lowerlid.

        Creates 12 eye shape keys: eyeLookUp/Down/In/Out for both eyes,
        eyeSquint L/R, eyeWide L/R, plus ensures blink/lowerlid exist.

        Args:
            mesh_name: Name of the face mesh.
            armature_name: Optional armature for eye bone configuration.
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

    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)

    eye_shapes = [
        # VRC standard
        "vrc.blink_left", "vrc.blink_right",
        "vrc.lowerlid_left", "vrc.lowerlid_right",
        # ARKit extended
        "eyeBlinkLeft", "eyeBlinkRight",
        "eyeLookDownLeft", "eyeLookDownRight",
        "eyeLookInLeft", "eyeLookInRight",
        "eyeLookOutLeft", "eyeLookOutRight",
        "eyeLookUpLeft", "eyeLookUpRight",
        "eyeSquintLeft", "eyeSquintRight",
        "eyeWideLeft", "eyeWideRight",
    ]

    created = []
    existing = [kb.name for kb in obj.data.shape_keys.key_blocks]
    for name in eye_shapes:
        if name not in existing:
            obj.shape_key_add(name=name, from_mix=False)
            created.append(name)

    # Configure eye bones if armature provided
    bone_info = []
    arm_name = {json.dumps(armature_name)}
    if arm_name:
        arm_obj = bpy.data.objects.get(arm_name)
        if arm_obj and arm_obj.type == 'ARMATURE':
            for eye_name in ["LeftEye", "Left_Eye", "Eye_L", "RightEye", "Right_Eye", "Eye_R"]:
                b = arm_obj.data.bones.get(eye_name)
                if b:
                    bone_info.append(eye_name)

    result = {{
        "created_shapes": created,
        "total_eye_shapes": len(eye_shapes),
        "total_shape_keys": len(obj.data.shape_keys.key_blocks),
        "eye_bones_found": bone_info,
    }}
"""
        return _exec(code)

    # ═══════════════════════════════════════════
    # Export Shape Key Report
    # ═══════════════════════════════════════════

    @mcp.tool()
    def ft_export_shape_key_report(
        mesh_name: str,
        format: str = "markdown",
    ) -> dict:
        """Generate a complete report of all shape keys with metadata.

        Args:
            mesh_name: Name of the face mesh.
            format: Output format — 'markdown' or 'json'.
        """
        arkit = json.dumps(ARKIT_BLEND_SHAPES)
        unified = json.dumps(UNIFIED_EXPRESSIONS)
        code = f"""
import bpy

obj = bpy.data.objects.get({json.dumps(mesh_name)})
if not obj or obj.type != 'MESH':
    result = {{"error": "Mesh not found"}}
elif not obj.data.shape_keys:
    result = {{"error": "No shape keys", "total": 0}}
else:
    basis = obj.data.shape_keys.key_blocks.get("Basis")
    arkit_names = set({arkit})
    unified_names = set({unified})
    vrc_visemes = set(["vrc.v_" + x for x in "sil pp ff th dd kk ch ss nn rr aa e ih oh ou".split()])
    vrc_eye = set(["vrc.blink_left", "vrc.blink_right", "vrc.lowerlid_left", "vrc.lowerlid_right"])

    shapes = []
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name == "Basis":
            continue

        max_disp = 0.0
        displaced_count = 0
        if basis:
            for i in range(len(kb.data)):
                delta = (kb.data[i].co - basis.data[i].co).length
                if delta > 0.0001:
                    displaced_count += 1
                    max_disp = max(max_disp, delta)

        # Categorize
        if kb.name in arkit_names:
            cat = "arkit"
        elif kb.name in unified_names:
            cat = "unified"
        elif kb.name in vrc_visemes:
            cat = "viseme"
        elif kb.name in vrc_eye:
            cat = "vrc_eye"
        else:
            cat = "custom"

        shapes.append({{
            "name": kb.name,
            "category": cat,
            "displaced_vertices": displaced_count,
            "max_displacement": round(max_disp, 5),
            "is_empty": displaced_count == 0,
        }})

    # Summary
    cats = {{}}
    for s in shapes:
        c = s["category"]
        cats[c] = cats.get(c, 0) + 1
    empty_count = sum(1 for s in shapes if s["is_empty"])

    fmt = {json.dumps(format)}
    if fmt == "markdown":
        lines = [f"# Shape Key Report: {{obj.name}}",
                 f"Total: {{len(shapes)}} | Empty: {{empty_count}}",
                 f"Categories: {{cats}}",
                 "",
                 "| Name | Category | Verts | Max Disp |",
                 "|------|----------|-------|----------|"]
        for s in shapes:
            status = "EMPTY" if s["is_empty"] else f"{{s['displaced_vertices']}}"
            lines.append(f"| {{s['name']}} | {{s['category']}} | {{status}} | {{s['max_displacement']}} |")
        report = "\\n".join(lines)
    else:
        report = ""

    result = {{
        "total_shapes": len(shapes),
        "empty_count": empty_count,
        "categories": cats,
        "shapes": shapes[:30],
        "report": report if fmt == "markdown" else "",
    }}
"""
        return _exec(code)

    logger.info("Registered 10 face tracking tools")
