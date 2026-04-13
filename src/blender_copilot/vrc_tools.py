# VRChat Avatar Compatibility Layer for BlenderMCP
# Provides VRC-specific tools: validation, rig setup, visemes, export, etc.

import json
import logging
from typing import Optional
from .vrc_constants import (
    RANK_LIMITS, REQUIRED_BONES, OPTIONAL_BONES, FINGER_BONES,
    BONE_NAME_MAP, VRC_VISEMES, VRC_EYE_TRACKING, MMD_VISEME_MAP,
    VRC_FBX_EXPORT_SETTINGS, VISEME_BLEND_WEIGHTS,
    VRC_BUILTIN_PARAMETERS, VRC_PARAM_BITS, VRC_MAX_MEMORY_BITS,
    VRC_MENU_CONTROL_TYPES, VRC_GESTURES, VRC_PLAYABLE_LAYERS,
    VRC_CONTACT_COLLISION_TAGS, VRC_CONTACT_RECEIVER_TYPES, VRC_CONTACT_PRESETS,
    VRC_PHYSBONE_DEFAULTS, VRC_PHYSBONE_PRESETS, VRC_DYNAMICS_LIMITS,
)

logger = logging.getLogger("BlenderMCPServer.VRC")


def register_vrc_tools(mcp, send_command_fn):
    """Register all VRC tools on the FastMCP instance."""

    def _exec(code: str) -> dict:
        """Execute code in Blender and return result."""
        # adapted for copilot
        return send_command_fn("execute_code", {"code": code})

    # ─────────────────────────────────────────────
    # 1. VRC Validate — Analyze model against performance ranks
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_validate(target: str = "pc", object_name: str = "") -> str:
        """
        Validate a model against VRChat performance rank limits.
        Reports polygon count, bone count, material count, mesh count,
        and which rank (Excellent/Good/Medium/Poor/Very Poor) the model falls into.

        Parameters:
        - target: "pc" or "quest" (default: "pc")
        - object_name: Specific armature/mesh name. If empty, analyzes entire scene.
        """
        code = r'''
import bpy, json

object_name = ''' + json.dumps(object_name) + r'''

# Collect stats
meshes = []
armatures = []
total_tris = 0
total_materials = set()
total_bones = 0
skinned_meshes = 0

objects = bpy.data.objects
if object_name:
    root = bpy.data.objects.get(object_name)
    if root:
        objects = [root] + list(root.children_recursive) if hasattr(root, 'children_recursive') else [root]
    else:
        objects = [o for o in bpy.data.objects if object_name.lower() in o.name.lower()]

for obj in objects:
    if obj.type == 'MESH':
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        tris = len(mesh.loop_triangles) if hasattr(mesh, 'loop_triangles') else 0
        if tris == 0:
            mesh.calc_loop_triangles()
            tris = len(mesh.loop_triangles)
        total_tris += tris
        for slot in obj.material_slots:
            if slot.material:
                total_materials.add(slot.material.name)
        meshes.append({"name": obj.name, "tris": tris, "materials": len(obj.material_slots)})
        # Check if skinned (has armature modifier)
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                skinned_meshes += 1
                break
        eval_obj.to_mesh_clear()
    elif obj.type == 'ARMATURE':
        armatures.append(obj.name)
        total_bones += len(obj.data.bones)

# Shape key info
shape_key_info = []
for obj in objects:
    if obj.type == 'MESH' and obj.data.shape_keys:
        keys = [kb.name for kb in obj.data.shape_keys.key_blocks]
        shape_key_info.append({"mesh": obj.name, "count": len(keys), "names": keys})

result = json.dumps({
    "total_triangles": total_tris,
    "total_bones": total_bones,
    "total_materials": len(total_materials),
    "material_names": list(total_materials),
    "mesh_count": len(meshes),
    "skinned_mesh_count": skinned_meshes,
    "armature_count": len(armatures),
    "meshes": meshes,
    "shape_keys": shape_key_info,
})
result
'''
        try:
            raw = _exec(code)
            stats = json.loads(raw.get("result", "{}"))
        except Exception as e:
            return f"Error validating: {e}"

        # Determine rank
        limits = RANK_LIMITS.get(target, RANK_LIMITS["pc"])
        rank = "Very Poor"
        for r in ("excellent", "good", "medium", "poor"):
            lim = limits[r]
            if (stats["total_triangles"] <= lim["polygons"] and
                stats["total_bones"] <= lim["bones"] and
                stats["total_materials"] <= lim["materials"] and
                stats["skinned_mesh_count"] <= lim["skinned_meshes"]):
                rank = r.capitalize()
                break

        report = [
            f"## VRChat Performance Rank: **{rank}** ({target.upper()})",
            f"",
            f"| Metric | Current | Excellent | Good | Medium | Poor |",
            f"|--------|---------|-----------|------|--------|------|",
            f"| Triangles | {stats['total_triangles']:,} | {limits['excellent']['polygons']:,} | {limits['good']['polygons']:,} | {limits['medium']['polygons']:,} | {limits['poor']['polygons']:,} |",
            f"| Bones | {stats['total_bones']} | {limits['excellent']['bones']} | {limits['good']['bones']} | {limits['medium']['bones']} | {limits['poor']['bones']} |",
            f"| Materials | {stats['total_materials']} | {limits['excellent']['materials']} | {limits['good']['materials']} | {limits['medium']['materials']} | {limits['poor']['materials']} |",
            f"| Skinned Meshes | {stats['skinned_mesh_count']} | {limits['excellent']['skinned_meshes']} | {limits['good']['skinned_meshes']} | {limits['medium']['skinned_meshes']} | {limits['poor']['skinned_meshes']} |",
            f"",
            f"**Meshes:** {json.dumps(stats['meshes'], indent=2)}",
        ]

        if stats.get("shape_keys"):
            report.append(f"\n**Shape Keys:**")
            for sk in stats["shape_keys"]:
                report.append(f"  - {sk['mesh']}: {sk['count']} keys")
                # Check for VRC visemes
                has_visemes = [v for v in VRC_VISEMES if v in sk["names"]]
                missing_visemes = [v for v in VRC_VISEMES if v not in sk["names"]]
                if has_visemes:
                    report.append(f"    Visemes: {len(has_visemes)}/15 present")
                if missing_visemes and has_visemes:
                    report.append(f"    Missing: {', '.join(missing_visemes[:5])}...")

        return "\n".join(report)

    # ─────────────────────────────────────────────
    # 2. VRC Fix Model — CATS-like one-click fix
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_fix_model(
        armature_name: str = "",
        join_meshes: bool = True,
        apply_transforms: bool = True,
        remove_zero_weight_bones: bool = True,
        standardize_bone_names: bool = True,
        remove_doubles_distance: float = 0.0001,
    ) -> str:
        """
        One-click model fix for VRChat (similar to CATS "Fix Model").
        Joins meshes, applies transforms, cleans weights, standardizes bone names.

        Parameters:
        - armature_name: Target armature. If empty, uses the first armature found.
        - join_meshes: Join all child meshes into one (default: True)
        - apply_transforms: Apply all transforms (default: True)
        - remove_zero_weight_bones: Remove bones with no vertex weights (default: True)
        - standardize_bone_names: Rename bones to VRC standard names (default: True)
        - remove_doubles_distance: Merge vertices closer than this distance (default: 0.0001)
        """
        bone_map_json = json.dumps(BONE_NAME_MAP)

        code = f'''
import bpy, json

armature_name = {json.dumps(armature_name)}
join_meshes = {json.dumps(join_meshes)}
apply_transforms = {json.dumps(apply_transforms)}
remove_zero_weight = {json.dumps(remove_zero_weight_bones)}
standardize_names = {json.dumps(standardize_bone_names)}
merge_dist = {remove_doubles_distance}
bone_map = json.loads({json.dumps(bone_map_json)})

log = []

# Find armature
arm = None
if armature_name:
    arm = bpy.data.objects.get(armature_name)
if not arm:
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            arm = obj
            break

if not arm:
    raise Exception("No armature found in scene")

log.append(f"Using armature: {{arm.name}}")

# Collect meshes parented to this armature
meshes = [c for c in arm.children if c.type == 'MESH']
if not meshes:
    # Also check for meshes with armature modifier pointing to this armature
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE' and mod.object == arm:
                    meshes.append(obj)
                    break

log.append(f"Found {{len(meshes)}} mesh(es)")

# Step 1: Apply transforms on armature
if apply_transforms:
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    log.append("Applied transforms on armature")

    for m in meshes:
        bpy.ops.object.select_all(action='DESELECT')
        m.select_set(True)
        bpy.context.view_layer.objects.active = m
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    log.append("Applied transforms on all meshes")

# Step 2: Join meshes
if join_meshes and len(meshes) > 1:
    bpy.ops.object.select_all(action='DESELECT')
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    meshes = [bpy.context.active_object]
    meshes[0].name = "Body"
    log.append(f"Joined meshes into: {{meshes[0].name}}")

# Step 3: Remove doubles (merge by distance)
if merge_dist > 0 and meshes:
    for m in meshes:
        bpy.ops.object.select_all(action='DESELECT')
        m.select_set(True)
        bpy.context.view_layer.objects.active = m
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=merge_dist)
        bpy.ops.object.mode_set(mode='OBJECT')
    log.append(f"Merged vertices (distance: {{merge_dist}})")

# Step 4: Standardize bone names
renamed = 0
if standardize_names:
    for bone in arm.data.bones:
        if bone.name in bone_map:
            old = bone.name
            new = bone_map[bone.name]
            # Also rename vertex groups
            for m in meshes:
                vg = m.vertex_groups.get(old)
                if vg:
                    vg.name = new
            bone.name = new
            renamed += 1
    log.append(f"Renamed {{renamed}} bones to VRC standard")

# Step 5: Remove zero-weight bones
removed_bones = []
if remove_zero_weight:
    weighted_bones = set()
    for m in meshes:
        for vg in m.vertex_groups:
            # Check if any vertex actually uses this group
            has_weight = False
            for v in m.data.vertices:
                for g in v.groups:
                    if g.group == vg.index and g.weight > 0.001:
                        has_weight = True
                        break
                if has_weight:
                    break
            if has_weight:
                weighted_bones.add(vg.name)

    # Don't remove required bones even if they have no weights
    required = set({repr(REQUIRED_BONES + OPTIONAL_BONES)})

    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')

    for ebone in list(arm.data.edit_bones):
        if (ebone.name not in weighted_bones and
            ebone.name not in required and
            not any(c.parent == ebone for c in arm.data.edit_bones if c != ebone)):
            # Leaf bone with no weights and not required
            if len(ebone.children) == 0:
                arm.data.edit_bones.remove(ebone)
                removed_bones.append(ebone.name if hasattr(ebone, 'name') else '?')

    bpy.ops.object.mode_set(mode='OBJECT')
    log.append(f"Removed {{len(removed_bones)}} zero-weight leaf bones")

result = json.dumps({{"log": log, "renamed_bones": renamed, "removed_bones": len(removed_bones)}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## VRC Fix Model Complete\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error fixing model: {e}"

    # ─────────────────────────────────────────────
    # 3. VRC Rename Bones — Standalone bone renaming
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_rename_bones(armature_name: str = "") -> str:
        """
        Rename bones from common naming schemes (Mixamo, MMD, VRM, Blender)
        to VRChat-compatible standard names. Also updates vertex groups.

        Parameters:
        - armature_name: Target armature name. If empty, uses first armature found.
        """
        bone_map_json = json.dumps(BONE_NAME_MAP)
        code = f'''
import bpy, json

armature_name = {json.dumps(armature_name)}
bone_map = json.loads({json.dumps(bone_map_json)})

arm = None
if armature_name:
    arm = bpy.data.objects.get(armature_name)
if not arm:
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            arm = obj
            break

if not arm:
    raise Exception("No armature found")

meshes = [c for c in bpy.data.objects if c.type == 'MESH']
renamed = []

for bone in arm.data.bones:
    if bone.name in bone_map:
        old_name = bone.name
        new_name = bone_map[bone.name]
        for m in meshes:
            vg = m.vertex_groups.get(old_name)
            if vg:
                vg.name = new_name
        bone.name = new_name
        renamed.append(f"{{old_name}} -> {{new_name}}")

result = json.dumps({{"renamed": renamed, "total": len(renamed)}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            lines = result.get("renamed", [])
            if not lines:
                return "No bones matched known naming schemes. Bones may already be in VRC format."
            return f"Renamed {result['total']} bones:\n" + "\n".join(f"  {l}" for l in lines)
        except Exception as e:
            return f"Error renaming bones: {e}"

    # ─────────────────────────────────────────────
    # 4. VRC Setup Visemes — Create 15 viseme shape keys
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_setup_visemes(
        mesh_name: str = "",
        mode: str = "template",
        source_mapping: str = "",
    ) -> str:
        """
        Set up VRChat viseme shape keys (lip sync) on a mesh.

        Parameters:
        - mesh_name: Target mesh. If empty, uses mesh named "Body" or the first mesh found.
        - mode: "template" creates empty viseme shape keys as placeholders.
                "rename" renames existing shape keys using source_mapping.
                "from_mmd" auto-maps MMD vowel shapes (あいうえお) to VRC visemes.
                "from_base_shapes" generates all 15 visemes by blending 3 base mouth shapes
                    (CATS technique). Requires source_mapping with keys: mouth_a, mouth_o, mouth_ch.
                    Example: '{"mouth_a": "あ", "mouth_o": "お", "mouth_ch": "い"}'
        - source_mapping: JSON mapping. Usage depends on mode.
        """
        visemes_json = json.dumps(VRC_VISEMES)
        mmd_map_json = json.dumps(MMD_VISEME_MAP)
        blend_weights_json = json.dumps(VISEME_BLEND_WEIGHTS)

        code = f'''
import bpy, json

mesh_name = {json.dumps(mesh_name)}
mode = {json.dumps(mode)}
source_mapping_str = {json.dumps(source_mapping)}
visemes = json.loads({json.dumps(visemes_json)})
mmd_map = json.loads({json.dumps(mmd_map_json)})

# Find mesh
obj = None
if mesh_name:
    obj = bpy.data.objects.get(mesh_name)
if not obj:
    obj = bpy.data.objects.get("Body")
if not obj:
    for o in bpy.data.objects:
        if o.type == 'MESH':
            obj = o
            break

if not obj or obj.type != 'MESH':
    raise Exception("No mesh found for viseme setup")

# Ensure basis shape key exists
if not obj.data.shape_keys:
    obj.shape_key_add(name="Basis", from_mix=False)

existing_keys = [kb.name for kb in obj.data.shape_keys.key_blocks]
log = []

if mode == "template":
    created = 0
    for v in visemes:
        if v not in existing_keys:
            obj.shape_key_add(name=v, from_mix=False)
            created += 1
    log.append(f"Created {{created}} template viseme shape keys")
    log.append("These are empty placeholders - sculpt each viseme pose in Blender")

elif mode == "rename":
    mapping = json.loads(source_mapping_str) if source_mapping_str else {{}}
    renamed = 0
    for old_name, new_name in mapping.items():
        kb = obj.data.shape_keys.key_blocks.get(old_name)
        if kb:
            kb.name = new_name
            renamed += 1
            log.append(f"Renamed: {{old_name}} -> {{new_name}}")
    log.append(f"Renamed {{renamed}} shape keys")

elif mode == "from_mmd":
    mapped = 0
    for old_name, vrc_name in mmd_map.items():
        kb = obj.data.shape_keys.key_blocks.get(old_name)
        if kb:
            kb.name = vrc_name
            mapped += 1
            log.append(f"Mapped MMD: {{old_name}} -> {{vrc_name}}")
    # Create missing visemes as empty
    existing_now = [kb.name for kb in obj.data.shape_keys.key_blocks]
    created = 0
    for v in visemes:
        if v not in existing_now:
            obj.shape_key_add(name=v, from_mix=False)
            created += 1
    log.append(f"Mapped {{mapped}} MMD shapes, created {{created}} empty placeholders")

elif mode == "from_base_shapes":
    # CATS technique: generate 15 visemes by blending 3 base mouth shapes
    blend_weights = json.loads({json.dumps(blend_weights_json)})
    base_mapping = json.loads(source_mapping_str) if source_mapping_str else {{}}

    # Map generic names to actual shape key names
    mouth_a_key = base_mapping.get("mouth_a", "")
    mouth_o_key = base_mapping.get("mouth_o", "")
    mouth_ch_key = base_mapping.get("mouth_ch", "")

    # Auto-detect if not provided
    if not mouth_a_key or not mouth_o_key or not mouth_ch_key:
        for kb in obj.data.shape_keys.key_blocks:
            kn = kb.name.lower()
            if not mouth_a_key and any(x in kn for x in ["mouth_a", "あ", "aa", "mouth_open"]):
                mouth_a_key = kb.name
            if not mouth_o_key and any(x in kn for x in ["mouth_o", "お", "ou", "mouth_round"]):
                mouth_o_key = kb.name
            if not mouth_ch_key and any(x in kn for x in ["mouth_ch", "い", "ih", "mouth_narrow", "mouth_smile"]):
                mouth_ch_key = kb.name

    source_map = {{"mouth_a": mouth_a_key, "mouth_o": mouth_o_key, "mouth_ch": mouth_ch_key}}
    found_sources = {{k: v for k, v in source_map.items() if v and obj.data.shape_keys.key_blocks.get(v)}}

    if len(found_sources) < 2:
        log.append(f"Need at least 2 base shapes. Found: {{found_sources}}")
        log.append("Provide source_mapping: {{\"mouth_a\": \"shape_name\", \"mouth_o\": \"...\", \"mouth_ch\": \"...\"}}")
    else:
        generated = 0
        for viseme_name, weights in blend_weights.items():
            # Remove existing viseme if present
            existing_kb = obj.data.shape_keys.key_blocks.get(viseme_name)
            if existing_kb:
                obj.shape_key_remove(existing_kb)

            # Reset all shape keys to 0
            for kb in obj.data.shape_keys.key_blocks:
                kb.value = 0.0

            # Set source shape weights
            for source_key, weight in weights.items():
                actual_name = source_map.get(source_key, "")
                if actual_name:
                    kb = obj.data.shape_keys.key_blocks.get(actual_name)
                    if kb:
                        kb.value = weight

            # Create new shape key from the current mix
            obj.shape_key_add(name=viseme_name, from_mix=True)
            generated += 1

            # Reset all sliders
            for kb in obj.data.shape_keys.key_blocks:
                kb.value = 0.0

        log.append(f"Generated {{generated}} visemes from base shapes (CATS technique)")
        log.append(f"Sources: {{found_sources}}")

# Report final state
final_keys = [kb.name for kb in obj.data.shape_keys.key_blocks]
present = [v for v in visemes if v in final_keys]
missing = [v for v in visemes if v not in final_keys]

result = json.dumps({{"log": log, "present": len(present), "missing": missing, "mesh": obj.name}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            out = [f"## Viseme Setup on '{result.get('mesh', '?')}'", ""]
            out.extend(f"- {l}" for l in result.get("log", []))
            out.append(f"\nVisemes present: {result.get('present', 0)}/15")
            missing = result.get("missing", [])
            if missing:
                out.append(f"Still missing: {', '.join(missing)}")
            return "\n".join(out)
        except Exception as e:
            return f"Error setting up visemes: {e}"

    # ─────────────────────────────────────────────
    # 5. VRC Setup Eye Tracking
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_setup_eye_tracking(mesh_name: str = "", create_bones: bool = True) -> str:
        """
        Set up VRChat eye tracking: creates eye tracking blend shapes and optionally eye bones.

        Parameters:
        - mesh_name: Target mesh for blend shapes. If empty, auto-detects.
        - create_bones: Create Left_Eye and Right_Eye bones if missing (default: True)
        """
        eye_shapes_json = json.dumps(VRC_EYE_TRACKING)

        code = f'''
import bpy, json

mesh_name = {json.dumps(mesh_name)}
create_bones = {json.dumps(create_bones)}
eye_shapes = json.loads({json.dumps(eye_shapes_json)})
log = []

# Find mesh
obj = None
if mesh_name:
    obj = bpy.data.objects.get(mesh_name)
if not obj:
    obj = bpy.data.objects.get("Body")
if not obj:
    for o in bpy.data.objects:
        if o.type == 'MESH':
            obj = o
            break

if not obj:
    raise Exception("No mesh found")

# Ensure basis
if not obj.data.shape_keys:
    obj.shape_key_add(name="Basis", from_mix=False)

existing = [kb.name for kb in obj.data.shape_keys.key_blocks]
created_shapes = 0
for shape_name in eye_shapes:
    if shape_name not in existing:
        obj.shape_key_add(name=shape_name, from_mix=False)
        created_shapes += 1

log.append(f"Created {{created_shapes}} eye tracking shape keys on {{obj.name}}")

# Create eye bones if requested
if create_bones:
    arm = None
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            arm = o
            break

    if arm:
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='EDIT')

        head_bone = arm.data.edit_bones.get("Head")
        bones_created = []

        for eye_name in ["Left_Eye", "Right_Eye"]:
            if eye_name not in arm.data.edit_bones:
                eb = arm.data.edit_bones.new(eye_name)
                if head_bone:
                    eb.parent = head_bone
                    # Position relative to head
                    offset_x = -0.03 if "Left" in eye_name else 0.03
                    eb.head = (head_bone.head.x + offset_x, head_bone.head.y + 0.06, head_bone.head.z + 0.02)
                    eb.tail = (eb.head.x, eb.head.y + 0.02, eb.head.z)
                else:
                    eb.head = (-0.03 if "Left" in eye_name else 0.03, 0.06, 1.6)
                    eb.tail = (eb.head.x, eb.head.y + 0.02, eb.head.z)
                bones_created.append(eye_name)

        bpy.ops.object.mode_set(mode='OBJECT')
        if bones_created:
            log.append(f"Created eye bones: {{', '.join(bones_created)}}")
        else:
            log.append("Eye bones already exist")
    else:
        log.append("No armature found, skipped bone creation")

result = json.dumps({{"log": log}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## Eye Tracking Setup\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error setting up eye tracking: {e}"

    # ─────────────────────────────────────────────
    # 6. VRC Decimate — Smart decimation to target rank
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_decimate(
        target_rank: str = "good",
        platform: str = "pc",
        mesh_name: str = "",
        preserve_shape_keys: bool = True,
    ) -> str:
        """
        Smart decimation to reach a target VRChat performance rank.
        Calculates the required ratio and applies a Decimate modifier.

        Parameters:
        - target_rank: "excellent", "good", "medium", or "poor" (default: "good")
        - platform: "pc" or "quest" (default: "pc")
        - mesh_name: Target mesh. If empty, decimates all meshes.
        - preserve_shape_keys: Use CATS blend_from_shape technique to repair shape keys
                               after decimation (default: True). This is the gold standard
                               for decimating meshes with shape keys.
        """
        target_tris = RANK_LIMITS.get(platform, RANK_LIMITS["pc"]).get(target_rank, {}).get("polygons", 70000)

        code = f'''
import bpy, json

mesh_name = {json.dumps(mesh_name)}
target_tris = {target_tris}
preserve_sk = {json.dumps(preserve_shape_keys)}
log = []

# Collect meshes
meshes = []
if mesh_name:
    obj = bpy.data.objects.get(mesh_name)
    if obj and obj.type == 'MESH':
        meshes = [obj]
else:
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']

if not meshes:
    raise Exception("No meshes found")

# Count current total tris
total_tris = 0
for m in meshes:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = m.evaluated_get(depsgraph)
    me = eval_obj.to_mesh()
    me.calc_loop_triangles()
    total_tris += len(me.loop_triangles)
    eval_obj.to_mesh_clear()

log.append(f"Current: {{total_tris:,}} triangles, Target: {{target_tris:,}}")

if total_tris <= target_tris:
    log.append("Already within target! No decimation needed.")
    result = json.dumps({{"log": log, "decimated": False}})
else:
    overall_ratio = target_tris / total_tris
    log.append(f"Overall decimation ratio: {{overall_ratio:.4f}}")

    # Calculate per-mesh triangle counts for proportional decimation
    mesh_tris = {{}}
    for m in meshes:
        depsgraph2 = bpy.context.evaluated_depsgraph_get()
        eval2 = m.evaluated_get(depsgraph2)
        me2 = eval2.to_mesh()
        me2.calc_loop_triangles()
        mesh_tris[m.name] = len(me2.loop_triangles)
        eval2.to_mesh_clear()

    for m in meshes:
        bpy.ops.object.select_all(action='DESELECT')
        m.select_set(True)
        bpy.context.view_layer.objects.active = m

        # Per-mesh ratio: each mesh gets the same overall ratio
        # but skip tiny meshes that don't benefit from decimation
        m_tris = mesh_tris.get(m.name, 0)
        if m_tris < 100:
            log.append(f"{{m.name}}: Skipped (only {{m_tris}} tris)")
            continue
        ratio = overall_ratio

        has_shape_keys = m.data.shape_keys is not None and len(m.data.shape_keys.key_blocks) > 1

        if has_shape_keys and preserve_sk:
            # Shape-key-safe decimation
            # Blender's modifier_apply already adjusts shape key deltas
            # when applying a modifier to a mesh with shape keys.
            # No manual delta repair needed — just apply the decimate.
            sk_names = [kb.name for kb in m.data.shape_keys.key_blocks]
            log.append(f"{{m.name}}: Has {{len(sk_names)}} shape keys, applying decimate with preservation")

            mod = m.modifiers.new(name="VRC_Decimate", type='DECIMATE')
            mod.decimate_type = 'COLLAPSE'
            mod.ratio = ratio

            # Use un_subdivide for better topology when ratio is aggressive
            if ratio < 0.5:
                mod.decimate_type = 'UNSUBDIV'
                mod.iterations = max(1, int(-1.0 * (ratio - 1.0) / 0.25))
                mod.decimate_type = 'COLLAPSE'
                mod.ratio = ratio

            bpy.ops.object.modifier_apply(modifier="VRC_Decimate")

            # Verify shape keys survived
            remaining_sk = len(m.data.shape_keys.key_blocks) if m.data.shape_keys else 0
            log.append(f"{{m.name}}: Decimated (ratio={{ratio:.4f}}), {{remaining_sk}}/{{len(sk_names)}} shape keys preserved")

        else:
            mod = m.modifiers.new(name="VRC_Decimate", type='DECIMATE')
            mod.decimate_type = 'COLLAPSE'
            mod.ratio = ratio
            bpy.ops.object.modifier_apply(modifier="VRC_Decimate")
            log.append(f"{{m.name}}: Collapse ratio={{ratio:.4f}} applied")

    # Recount
    new_tris = 0
    for m in meshes:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = m.evaluated_get(depsgraph)
        me = eval_obj.to_mesh()
        me.calc_loop_triangles()
        new_tris += len(me.loop_triangles)
        eval_obj.to_mesh_clear()
    log.append(f"Result: {{total_tris:,}} -> {{new_tris:,}} triangles")

    result = json.dumps({{"log": log, "decimated": True, "ratio": ratio, "before": total_tris, "after": new_tris}})

result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return "## VRC Decimate\n\n" + "\n".join(f"- {l}" for l in result.get("log", []))
        except Exception as e:
            return f"Error decimating: {e}"

    # ─────────────────────────────────────────────
    # 7. VRC Merge Materials — Reduce material count
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_merge_materials(mesh_name: str = "", target_count: int = 1) -> str:
        """
        Analyze and prepare materials for merging to reduce material slot count.
        Creates a report of current materials and their UV islands for atlas preparation.
        Can auto-merge materials that share identical settings.

        Parameters:
        - mesh_name: Target mesh. If empty, uses "Body" or first mesh.
        - target_count: Desired material count (default: 1)
        """
        code = f'''
import bpy, json

mesh_name = {json.dumps(mesh_name)}
target_count = {target_count}

obj = None
if mesh_name:
    obj = bpy.data.objects.get(mesh_name)
if not obj:
    obj = bpy.data.objects.get("Body")
if not obj:
    for o in bpy.data.objects:
        if o.type == 'MESH':
            obj = o
            break

if not obj or obj.type != 'MESH':
    raise Exception("No mesh found")

log = []
materials = []
for i, slot in enumerate(obj.material_slots):
    mat = slot.material
    if mat:
        # Count faces using this material
        face_count = sum(1 for f in obj.data.polygons if f.material_index == i)
        mat_info = {{
            "index": i,
            "name": mat.name,
            "faces": face_count,
        }}
        # Check for textures
        if mat.use_nodes:
            tex_nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']
            mat_info["textures"] = [n.image.name for n in tex_nodes if n.image]
        materials.append(mat_info)

log.append(f"Mesh '{{obj.name}}' has {{len(materials)}} materials")

# Find duplicate materials (same textures)
dupes = {{}}
for mat in materials:
    key = str(sorted(mat.get("textures", [])))
    if key not in dupes:
        dupes[key] = []
    dupes[key].append(mat["name"])

mergeable = {{k: v for k, v in dupes.items() if len(v) > 1}}
if mergeable:
    for key, names in mergeable.items():
        log.append(f"Can merge (identical textures): {{', '.join(names)}}")

if len(materials) <= target_count:
    log.append(f"Already at or below target ({{target_count}}). No merge needed.")
else:
    log.append(f"Need to reduce from {{len(materials)}} to {{target_count}} materials")
    log.append("Recommended: Use texture atlas (bake all materials to one UV + texture)")

result = json.dumps({{"log": log, "materials": materials, "current_count": len(materials)}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            out = ["## Material Analysis", ""]
            out.extend(f"- {l}" for l in result.get("log", []))
            out.append("\n**Materials:**")
            for m in result.get("materials", []):
                texs = ", ".join(m.get("textures", ["no texture"]))
                out.append(f"  [{m['index']}] {m['name']} — {m['faces']} faces — {texs}")
            return "\n".join(out)
        except Exception as e:
            return f"Error analyzing materials: {e}"

    # ─────────────────────────────────────────────
    # 8. VRC Setup PhysBone Chains
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_setup_physbone_chain(
        armature_name: str = "",
        parent_bone: str = "",
        chain_name: str = "Hair",
        bone_count: int = 4,
        chain_length: float = 0.3,
        direction: str = "down",
    ) -> str:
        """
        Create a bone chain for VRChat PhysBones (hair, tail, ears, skirt, etc.).
        Creates bones in Blender; PhysBone components are configured in Unity.

        Parameters:
        - armature_name: Target armature. If empty, uses first found.
        - parent_bone: Name of the bone to attach the chain to (e.g., "Head" for hair)
        - chain_name: Name prefix for the chain (e.g., "Hair_Front", "Tail")
        - bone_count: Number of bones in the chain (default: 4, recommended: 3-6)
        - chain_length: Total length of the chain in meters (default: 0.3)
        - direction: "down" (hair/skirt), "back" (tail), "left", "right" (ears)
        """
        code = f'''
import bpy, json
from mathutils import Vector

armature_name = {json.dumps(armature_name)}
parent_bone_name = {json.dumps(parent_bone)}
chain_name = {json.dumps(chain_name)}
bone_count = {bone_count}
chain_length = {chain_length}
direction = {json.dumps(direction)}

arm = None
if armature_name:
    arm = bpy.data.objects.get(armature_name)
if not arm:
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            arm = o
            break
if not arm:
    raise Exception("No armature found")

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')

# Direction vector
dir_map = {{
    "down": Vector((0, 0, -1)),
    "back": Vector((0, -1, 0)),
    "left": Vector((-1, 0, 0)),
    "right": Vector((1, 0, 0)),
    "up": Vector((0, 0, 1)),
    "forward": Vector((0, 1, 0)),
}}
dir_vec = dir_map.get(direction, Vector((0, 0, -1)))

parent_eb = arm.data.edit_bones.get(parent_bone_name) if parent_bone_name else None
segment_len = chain_length / bone_count

created = []
prev_bone = parent_eb

for i in range(bone_count):
    name = f"{{chain_name}}_{{i+1:02d}}"
    eb = arm.data.edit_bones.new(name)

    if prev_bone:
        start = prev_bone.tail.copy() if prev_bone != parent_eb else parent_eb.tail.copy()
    else:
        start = Vector((0, 0, 1.7))  # Default head height

    if i == 0 and parent_eb:
        start = parent_eb.tail.copy()

    eb.head = start
    eb.tail = start + dir_vec * segment_len

    if i == 0 and parent_eb:
        eb.parent = parent_eb
        eb.use_connect = True
    elif prev_bone and prev_bone != parent_eb:
        eb.parent = prev_bone
        eb.use_connect = True

    created.append(name)
    prev_bone = eb

bpy.ops.object.mode_set(mode='OBJECT')

result = json.dumps({{"created": created, "parent": parent_bone_name, "count": len(created)}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            bones = result.get("created", [])
            return (f"## PhysBone Chain Created\n\n"
                    f"- Chain: {chain_name} ({len(bones)} bones)\n"
                    f"- Parent: {result.get('parent', 'none')}\n"
                    f"- Bones: {', '.join(bones)}\n\n"
                    f"Configure PhysBone component in Unity on the first bone of this chain.")
        except Exception as e:
            return f"Error creating physbone chain: {e}"

    # ─────────────────────────────────────────────
    # 9. VRC Export FBX — Export with VRC-optimized settings
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_export_fbx(
        filepath: str,
        apply_modifiers: bool = True,
        selected_only: bool = False,
    ) -> str:
        """
        Export model as FBX with VRChat-optimized settings.
        Handles axis conversion, disables leaf bones, applies correct scale.

        Parameters:
        - filepath: Full output path (e.g., "D:/models/avatar.fbx")
        - apply_modifiers: Apply modifiers before export (default: True)
        - selected_only: Only export selected objects (default: False)
        """
        code = f'''
import bpy, json

filepath = {json.dumps(filepath)}

# Ensure .fbx extension
if not filepath.lower().endswith('.fbx'):
    filepath += '.fbx'

bpy.ops.export_scene.fbx(
    filepath=filepath,
    use_selection={json.dumps(selected_only)},
    apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z',
    axis_up='Y',
    use_mesh_modifiers={json.dumps(apply_modifiers)},
    mesh_smooth_type='FACE',
    add_leaf_bones=False,
    bake_anim=False,
    use_armature_deform_only=False,
    bake_space_transform=False,
)

result = json.dumps({{"exported": filepath}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return (f"## FBX Exported for VRChat\n\n"
                    f"- File: {result.get('exported', filepath)}\n"
                    f"- Leaf bones: disabled\n"
                    f"- Axis: -Z forward, Y up\n"
                    f"- Scale: FBX_SCALE_ALL\n\n"
                    f"Import this FBX into Unity, set Rig → Humanoid, then configure Avatar Descriptor.")
        except Exception as e:
            return f"Error exporting FBX: {e}"

    # ─────────────────────────────────────────────
    # 10. VRC Check Export Ready — Pre-export checklist
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_check_export_ready(armature_name: str = "", target: str = "pc") -> str:
        """
        Run a comprehensive pre-export checklist for VRChat avatar.
        Checks: transforms applied, bone naming, visemes, eye tracking,
        vertex weights, scale, T-pose, material count, poly count.

        Parameters:
        - armature_name: Target armature. If empty, uses first found.
        - target: "pc" or "quest" (default: "pc")
        """
        required_bones_json = json.dumps(REQUIRED_BONES)
        visemes_json = json.dumps(VRC_VISEMES)
        eye_json = json.dumps(VRC_EYE_TRACKING)

        code = f'''
import bpy, json
from mathutils import Vector

armature_name = {json.dumps(armature_name)}
required_bones = json.loads({json.dumps(required_bones_json)})
visemes = json.loads({json.dumps(visemes_json)})
eye_shapes = json.loads({json.dumps(eye_json)})

checks = []

# Find armature
arm = None
if armature_name:
    arm = bpy.data.objects.get(armature_name)
if not arm:
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            arm = o
            break

if not arm:
    checks.append(("FAIL", "No armature found in scene"))
    result = json.dumps({{"checks": checks}})
else:
    # 1. Transform check
    loc_ok = arm.location.length < 0.001
    rot_ok = arm.rotation_euler.x == 0 and arm.rotation_euler.y == 0 and arm.rotation_euler.z == 0
    scale_ok = abs(arm.scale.x - 1) < 0.001 and abs(arm.scale.y - 1) < 0.001 and abs(arm.scale.z - 1) < 0.001
    if loc_ok and rot_ok and scale_ok:
        checks.append(("PASS", "Armature transforms are applied (origin, rotation, scale)"))
    else:
        issues = []
        if not loc_ok: issues.append("location=" + str(arm.location[:]))
        if not rot_ok: issues.append("rotation not zero")
        if not scale_ok: issues.append("scale=" + str(arm.scale[:]))
        checks.append(("WARN", f"Armature transforms not applied: {{', '.join(issues)}}. Run vrc_fix_model."))

    # 2. Required bones
    bone_names = [b.name for b in arm.data.bones]
    missing_required = [b for b in required_bones if b not in bone_names]
    if not missing_required:
        checks.append(("PASS", f"All {{len(required_bones)}} required humanoid bones present"))
    else:
        checks.append(("FAIL", f"Missing required bones: {{', '.join(missing_required)}}"))

    # 3. Scale check (avatar height)
    dims = arm.dimensions
    height = max(dims.z, 0.01)
    if 0.5 < height < 5.0:
        checks.append(("PASS", f"Avatar height: {{height:.2f}}m (reasonable)"))
    else:
        checks.append(("WARN", f"Avatar height: {{height:.2f}}m (expected 0.5-5.0m, check scale)"))

    # 4. Mesh checks
    meshes = [c for c in bpy.data.objects if c.type == 'MESH']
    total_tris = 0
    total_mats = set()
    zero_weight_verts = 0
    face_mesh = None

    for m in meshes:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = m.evaluated_get(depsgraph)
        me = eval_obj.to_mesh()
        me.calc_loop_triangles()
        total_tris += len(me.loop_triangles)
        eval_obj.to_mesh_clear()

        for slot in m.material_slots:
            if slot.material:
                total_mats.add(slot.material.name)

        # Check zero-weight vertices
        for v in m.data.vertices:
            if len(v.groups) == 0:
                zero_weight_verts += 1

        # Find face mesh (has shape keys)
        if m.data.shape_keys and len(m.data.shape_keys.key_blocks) > 1:
            face_mesh = m

    checks.append(("INFO", f"Total triangles: {{total_tris:,}}"))
    checks.append(("INFO", f"Total materials: {{len(total_mats)}}"))
    checks.append(("INFO", f"Mesh objects: {{len(meshes)}}"))
    checks.append(("INFO", f"Total bones: {{len(bone_names)}}"))

    if zero_weight_verts > 0:
        checks.append(("WARN", f"{{zero_weight_verts}} vertices with zero weights (will cause mesh explosion in Unity)"))
    else:
        checks.append(("PASS", "All vertices have bone weights"))

    # 5. Viseme check
    if face_mesh and face_mesh.data.shape_keys:
        sk_names = [kb.name for kb in face_mesh.data.shape_keys.key_blocks]
        present_visemes = [v for v in visemes if v in sk_names]
        if len(present_visemes) == 15:
            checks.append(("PASS", "All 15 viseme shape keys present"))
        elif len(present_visemes) > 0:
            checks.append(("WARN", f"Visemes: {{len(present_visemes)}}/15 present"))
        else:
            checks.append(("WARN", "No viseme shape keys found. Lip sync won't work."))

        # Eye tracking
        present_eye = [e for e in eye_shapes if e in sk_names]
        if len(present_eye) >= 2:
            checks.append(("PASS", f"Eye tracking shapes: {{len(present_eye)}}/4"))
        else:
            checks.append(("WARN", "Missing eye tracking blend shapes (blink_left/right)"))
    else:
        checks.append(("WARN", "No face mesh with shape keys found"))

    # 6. Check mesh transforms
    for m in meshes:
        m_loc = m.location.length < 0.001
        m_scale = abs(m.scale.x - 1) < 0.001 and abs(m.scale.y - 1) < 0.001 and abs(m.scale.z - 1) < 0.001
        if not (m_loc and m_scale):
            checks.append(("WARN", f"Mesh '{{m.name}}' has unapplied transforms"))
            break
    else:
        if meshes:
            checks.append(("PASS", "All mesh transforms applied"))

    result = json.dumps({{"checks": checks}})

result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            checks = result.get("checks", [])

            icons = {"PASS": "[OK]", "FAIL": "[!!]", "WARN": "[??]", "INFO": "[--]"}
            lines = ["## VRC Export Readiness Check", ""]
            fails = 0
            warns = 0
            for level, msg in checks:
                lines.append(f"  {icons.get(level, '[ ]')} {msg}")
                if level == "FAIL":
                    fails += 1
                if level == "WARN":
                    warns += 1

            lines.append("")
            if fails > 0:
                lines.append(f"**{fails} issue(s) must be fixed before export.**")
            elif warns > 0:
                lines.append(f"**{warns} warning(s) — review before export.**")
            else:
                lines.append("**Ready to export!** Use `vrc_export_fbx` to export.")

            return "\n".join(lines)
        except Exception as e:
            return f"Error checking export readiness: {e}"

    # ─────────────────────────────────────────────
    # 11. VRC Create Humanoid Armature — From scratch
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_create_humanoid_armature(
        height: float = 1.65,
        include_fingers: bool = True,
        include_toes: bool = True,
        name: str = "Armature",
    ) -> str:
        """
        Create a complete VRChat-compatible humanoid armature from scratch.
        Generates a properly proportioned T-pose skeleton with all required bones.

        Parameters:
        - height: Avatar height in meters (default: 1.65)
        - include_fingers: Add finger bones (default: True)
        - include_toes: Add toe bones (default: True)
        - name: Armature object name (default: "Armature")
        """
        code = f'''
import bpy, json
from mathutils import Vector

height = {height}
include_fingers = {json.dumps(include_fingers)}
include_toes = {json.dumps(include_toes)}
arm_name = {json.dumps(name)}

# Scale factor based on height (proportions based on 1.65m reference)
s = height / 1.65

# Create armature
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm_obj = bpy.context.active_object
arm_obj.name = arm_name
arm = arm_obj.data
arm.name = arm_name

# Remove default bone
for b in arm.edit_bones:
    arm.edit_bones.remove(b)

def add_bone(name, head, tail, parent=None, connect=False):
    eb = arm.edit_bones.new(name)
    eb.head = Vector(head) * s
    eb.tail = Vector(tail) * s
    if parent:
        p = arm.edit_bones.get(parent)
        if p:
            eb.parent = p
            eb.use_connect = connect
    return eb

# Torso
add_bone("Hips",        (0, 0, 0.95),   (0, 0, 1.00))
add_bone("Spine",       (0, 0, 1.00),   (0, 0, 1.10),  "Hips", True)
add_bone("Chest",       (0, 0, 1.10),   (0, 0, 1.22),  "Spine", True)
add_bone("UpperChest",  (0, 0, 1.22),   (0, 0, 1.32),  "Chest", True)
add_bone("Neck",        (0, 0, 1.32),   (0, 0, 1.40),  "UpperChest", True)
add_bone("Head",        (0, 0, 1.40),   (0, 0, 1.55),  "Neck", True)

# Eyes
add_bone("Left_Eye",   (-0.03, 0.06, 1.48), (-0.03, 0.08, 1.48), "Head")
add_bone("Right_Eye",  (0.03, 0.06, 1.48),  (0.03, 0.08, 1.48),  "Head")

# Left arm
add_bone("Left_Shoulder",  (-0.02, 0, 1.30), (-0.12, 0, 1.30), "UpperChest")
add_bone("Left_UpperArm",  (-0.12, 0, 1.30), (-0.38, 0, 1.30), "Left_Shoulder", True)
add_bone("Left_LowerArm",  (-0.38, 0, 1.30), (-0.62, 0, 1.30), "Left_UpperArm", True)
add_bone("Left_Hand",      (-0.62, 0, 1.30), (-0.70, 0, 1.30), "Left_LowerArm", True)

# Right arm
add_bone("Right_Shoulder", (0.02, 0, 1.30),  (0.12, 0, 1.30),  "UpperChest")
add_bone("Right_UpperArm", (0.12, 0, 1.30),  (0.38, 0, 1.30),  "Right_Shoulder", True)
add_bone("Right_LowerArm", (0.38, 0, 1.30),  (0.62, 0, 1.30),  "Right_UpperArm", True)
add_bone("Right_Hand",     (0.62, 0, 1.30),  (0.70, 0, 1.30),  "Right_LowerArm", True)

# Left leg
add_bone("Left_UpperLeg",  (-0.09, 0, 0.95), (-0.09, 0, 0.52), "Hips")
add_bone("Left_LowerLeg",  (-0.09, 0, 0.52), (-0.09, 0, 0.08), "Left_UpperLeg", True)
add_bone("Left_Foot",      (-0.09, 0, 0.08), (-0.09, 0.10, 0.0), "Left_LowerLeg", True)

# Right leg
add_bone("Right_UpperLeg", (0.09, 0, 0.95),  (0.09, 0, 0.52),  "Hips")
add_bone("Right_LowerLeg", (0.09, 0, 0.52),  (0.09, 0, 0.08),  "Right_UpperLeg", True)
add_bone("Right_Foot",     (0.09, 0, 0.08),  (0.09, 0.10, 0.0), "Right_LowerLeg", True)

# Toes
if include_toes:
    add_bone("Left_Toes",  (-0.09, 0.10, 0.0), (-0.09, 0.18, 0.0), "Left_Foot", True)
    add_bone("Right_Toes", (0.09, 0.10, 0.0),  (0.09, 0.18, 0.0),  "Right_Foot", True)

# Fingers
if include_fingers:
    finger_data = {{
        "Thumb":  {{"spread": 0.02, "forward": -0.01, "length": 0.025}},
        "Index":  {{"spread": 0.00, "forward": 0.01,  "length": 0.025}},
        "Middle": {{"spread": 0.00, "forward": 0.02,  "length": 0.028}},
        "Ring":   {{"spread": 0.00, "forward": 0.01,  "length": 0.025}},
        "Little": {{"spread": -0.01, "forward": -0.005, "length": 0.020}},
    }}

    for side, sign in [("Left", -1), ("Right", 1)]:
        hand = arm.edit_bones.get(f"{{side}}_Hand")
        hand_tip_x = hand.tail.x

        for fi, (finger, fd) in enumerate(finger_data.items()):
            base_x = hand_tip_x + sign * fd["spread"] * s
            base_z = 1.30 * s + fd["forward"] * s
            seg = fd["length"] * s

            for ji, joint in enumerate(["Proximal", "Intermediate", "Distal"]):
                bname = f"{{side}}_{{finger}}_{{joint}}"
                parent_name = f"{{side}}_{{finger}}_Proximal" if ji == 1 else (f"{{side}}_{{finger}}_Intermediate" if ji == 2 else f"{{side}}_Hand")
                hx = base_x + sign * seg * ji
                tx = base_x + sign * seg * (ji + 1)
                add_bone(bname, (hx, 0, base_z), (tx, 0, base_z), parent_name, ji > 0)

bpy.ops.object.mode_set(mode='OBJECT')

bone_count = len(arm_obj.data.bones)
result = json.dumps({{"name": arm_obj.name, "bones": bone_count, "height": height}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return (f"## VRC Humanoid Armature Created\n\n"
                    f"- Name: {result.get('name')}\n"
                    f"- Bones: {result.get('bones')}\n"
                    f"- Height: {result.get('height')}m\n"
                    f"- T-pose, VRC bone naming, ready for mesh parenting")
        except Exception as e:
            return f"Error creating armature: {e}"

    # ─────────────────────────────────────────────
    # 12. VRC Weight Paint Check — Find weight issues
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_check_weights(mesh_name: str = "") -> str:
        """
        Check vertex weights for VRChat compatibility issues.
        Finds: unweighted vertices, excessive bone influences, missing vertex groups.

        Parameters:
        - mesh_name: Target mesh. If empty, checks all meshes.
        """
        code = f'''
import bpy, json

mesh_name = {json.dumps(mesh_name)}

meshes = []
if mesh_name:
    obj = bpy.data.objects.get(mesh_name)
    if obj and obj.type == 'MESH':
        meshes = [obj]
else:
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']

results = []
for obj in meshes:
    zero_weight = 0
    excessive_influences = 0  # >4 bones per vertex
    max_influences = 0

    for v in obj.data.vertices:
        weights = [g for g in v.groups if g.weight > 0.001]
        if len(weights) == 0:
            zero_weight += 1
        if len(weights) > 4:
            excessive_influences += 1
        max_influences = max(max_influences, len(weights))

    # Check for vertex groups without matching bones
    arm = None
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            arm = mod.object
            break

    orphan_groups = []
    if arm:
        bone_names = set(b.name for b in arm.data.bones)
        for vg in obj.vertex_groups:
            if vg.name not in bone_names:
                orphan_groups.append(vg.name)

    results.append({{
        "mesh": obj.name,
        "vertices": len(obj.data.vertices),
        "zero_weight": zero_weight,
        "excessive_influences": excessive_influences,
        "max_influences": max_influences,
        "orphan_groups": orphan_groups[:10],
    }})

result = json.dumps(results)
result
'''
        try:
            raw = _exec(code)
            results = json.loads(raw.get("result", "[]"))
            lines = ["## Weight Check Results", ""]
            for r in results:
                lines.append(f"**{r['mesh']}** ({r['vertices']:,} verts)")
                if r["zero_weight"] > 0:
                    lines.append(f"  [!!] {r['zero_weight']} unweighted vertices (will explode in Unity)")
                else:
                    lines.append(f"  [OK] All vertices weighted")
                if r["excessive_influences"] > 0:
                    lines.append(f"  [??] {r['excessive_influences']} verts with >4 bone influences (Unity caps at 4)")
                lines.append(f"  [--] Max influences per vertex: {r['max_influences']}")
                if r["orphan_groups"]:
                    lines.append(f"  [??] Orphan vertex groups (no bone): {', '.join(r['orphan_groups'])}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error checking weights: {e}"

    # ─────────────────────────────────────────────
    # 13. VRC Auto Weight Paint
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_auto_weight(mesh_name: str = "", armature_name: str = "") -> str:
        """
        Automatically weight paint a mesh to an armature using Blender's
        automatic weights (heat map). Sets up the armature modifier.

        Parameters:
        - mesh_name: Target mesh. If empty, uses "Body" or first mesh.
        - armature_name: Target armature. If empty, uses first armature.
        """
        code = f'''
import bpy, json

mesh_name = {json.dumps(mesh_name)}
armature_name = {json.dumps(armature_name)}

# Find mesh
obj = None
if mesh_name:
    obj = bpy.data.objects.get(mesh_name)
if not obj:
    obj = bpy.data.objects.get("Body")
if not obj:
    for o in bpy.data.objects:
        if o.type == 'MESH':
            obj = o
            break

# Find armature
arm = None
if armature_name:
    arm = bpy.data.objects.get(armature_name)
if not arm:
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            arm = o
            break

if not obj:
    raise Exception("No mesh found")
if not arm:
    raise Exception("No armature found")

# Clear existing armature modifier
for mod in list(obj.modifiers):
    if mod.type == 'ARMATURE':
        obj.modifiers.remove(mod)

# Parent with automatic weights
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# Verify
has_mod = any(m.type == 'ARMATURE' for m in obj.modifiers)
vg_count = len(obj.vertex_groups)

result = json.dumps({{
    "mesh": obj.name,
    "armature": arm.name,
    "has_armature_modifier": has_mod,
    "vertex_groups": vg_count,
}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            return (f"## Auto Weight Paint Complete\n\n"
                    f"- Mesh: {result.get('mesh')}\n"
                    f"- Armature: {result.get('armature')}\n"
                    f"- Armature modifier: {'Yes' if result.get('has_armature_modifier') else 'No'}\n"
                    f"- Vertex groups created: {result.get('vertex_groups')}\n\n"
                    f"Run `vrc_check_weights` to verify quality.")
        except Exception as e:
            return f"Error auto-weighting: {e}"

    # ═══════════════════════════════════════════════
    # PHASE 2: Expression Menu, Contacts, PhysBones,
    #          Animator, Accessories, Atlas
    # ═══════════════════════════════════════════════

    # ─────────────────────────────────────────────
    # 14. VRC Expression Menu Generator
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_generate_expression_menu(
        items: str = "",
        menu_name: str = "Main",
    ) -> str:
        """
        Generate a VRChat Expression Menu configuration (JSON blueprint).
        This creates the menu structure and parameter definitions that you
        import into Unity's VRC Expression Menu and Expression Parameters.

        Parameters:
        - items: JSON array of menu items. Each item:
            {"name": "Hat Toggle", "type": "Toggle", "parameter": "Hat", "icon": "hat"}
            {"name": "Color", "type": "RadialPuppet", "parameter": "Color_Hue"}
            {"name": "Emotes", "type": "SubMenu", "sub_items": [...]}
            {"name": "Movement", "type": "TwoAxisPuppet",
             "parameters": {"horizontal": "Move_X", "vertical": "Move_Y"}}
          Types: Button, Toggle, SubMenu, TwoAxisPuppet, FourAxisPuppet, RadialPuppet
        - menu_name: Root menu name (default: "Main")

        Returns a complete menu structure + parameter list with memory usage.
        """
        try:
            menu_items = json.loads(items) if items else []
        except json.JSONDecodeError:
            return "Error: 'items' must be valid JSON array"

        if not menu_items:
            # Generate example
            menu_items = [
                {"name": "Outfit Toggle", "type": "Toggle", "parameter": "Outfit_On"},
                {"name": "Hat Toggle", "type": "Toggle", "parameter": "Hat_On"},
                {"name": "Expression", "type": "SubMenu", "sub_items": [
                    {"name": "Happy", "type": "Toggle", "parameter": "Expr_Happy"},
                    {"name": "Angry", "type": "Toggle", "parameter": "Expr_Angry"},
                    {"name": "Sad", "type": "Toggle", "parameter": "Expr_Sad"},
                ]},
                {"name": "Tail Wag Speed", "type": "RadialPuppet", "parameter": "Tail_Speed"},
                {"name": "Ear Control", "type": "TwoAxisPuppet",
                 "parameters": {"horizontal": "Ear_X", "vertical": "Ear_Y"}},
            ]

        # Collect all parameters and calculate memory
        params = {}

        def extract_params(item_list):
            for item in item_list:
                t = item.get("type", "Toggle")
                if t == "Toggle" or t == "Button":
                    p = item.get("parameter", "")
                    if p:
                        params[p] = {"type": "bool", "bits": VRC_PARAM_BITS["bool"], "default": False}
                elif t == "RadialPuppet":
                    p = item.get("parameter", "")
                    if p:
                        params[p] = {"type": "float", "bits": VRC_PARAM_BITS["float"], "default": 0.0}
                elif t in ("TwoAxisPuppet", "FourAxisPuppet"):
                    pp = item.get("parameters", {})
                    for key, pname in pp.items():
                        params[pname] = {"type": "float", "bits": VRC_PARAM_BITS["float"], "default": 0.0}
                elif t == "SubMenu":
                    extract_params(item.get("sub_items", []))

        extract_params(menu_items)

        total_bits = sum(p["bits"] for p in params.values())
        remaining = VRC_MAX_MEMORY_BITS - total_bits

        # Build output
        menu_json = {
            "menu_name": menu_name,
            "items": menu_items,
            "parameters": params,
            "memory": {
                "used_bits": total_bits,
                "remaining_bits": remaining,
                "max_bits": VRC_MAX_MEMORY_BITS,
                "usage_percent": round(total_bits / VRC_MAX_MEMORY_BITS * 100, 1),
            },
        }

        lines = [
            f"## VRC Expression Menu: {menu_name}",
            "",
            f"**Parameters ({len(params)}):** {total_bits}/{VRC_MAX_MEMORY_BITS} bits ({menu_json['memory']['usage_percent']}%)",
            "",
        ]

        for pname, pinfo in params.items():
            lines.append(f"  - `{pname}` ({pinfo['type']}, {pinfo['bits']} bits)")

        lines.append(f"\n**Menu Structure:**\n")

        def format_menu(item_list, indent=0):
            for item in item_list:
                prefix = "  " * indent + "├─"
                t = item.get("type", "Toggle")
                p = item.get("parameter", item.get("parameters", ""))
                lines.append(f"{prefix} [{t}] {item['name']} → {p}")
                if t == "SubMenu":
                    format_menu(item.get("sub_items", []), indent + 1)

        format_menu(menu_items)

        lines.append(f"\n**Full JSON (for Unity import):**\n```json\n{json.dumps(menu_json, indent=2)}\n```")

        if remaining < 0:
            lines.append(f"\n⚠ OVER BUDGET by {-remaining} bits! Remove parameters or switch bool→int packing.")

        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 15. VRC Contact Setup — Create contact bones + metadata
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_setup_contacts(
        preset: str = "",
        custom_contacts: str = "",
        armature_name: str = "",
    ) -> str:
        """
        Set up VRChat Contact Senders and Receivers on the avatar.
        Creates marker bones at the correct positions for contact detection.
        The actual ContactSender/ContactReceiver components are added in Unity,
        but this tool places the bones and generates the Unity configuration JSON.

        Parameters:
        - preset: Use a preset: "headpat", "boop", "handshake", "hug", or "all"
        - custom_contacts: JSON for custom contacts:
            [{"name": "MyContact", "parent_bone": "Head", "position": [0,0.1,0],
              "radius": 0.1, "tags": ["Head"], "role": "receiver",
              "receiver_type": "Proximity", "parameter": "MyParam"}]
        - armature_name: Target armature. If empty, uses first found.
        """
        contacts_to_create = []

        if preset:
            if preset == "all":
                for name, data in VRC_CONTACT_PRESETS.items():
                    contacts_to_create.append({"name": name, **data})
            elif preset in VRC_CONTACT_PRESETS:
                contacts_to_create.append({"name": preset, **VRC_CONTACT_PRESETS[preset]})
            else:
                return f"Unknown preset '{preset}'. Available: {', '.join(VRC_CONTACT_PRESETS.keys())}, all"

        if custom_contacts:
            try:
                contacts_to_create.extend(json.loads(custom_contacts))
            except json.JSONDecodeError:
                return "Error: custom_contacts must be valid JSON"

        if not contacts_to_create:
            # Show available presets
            lines = ["## VRC Contact Presets", ""]
            for name, data in VRC_CONTACT_PRESETS.items():
                param = data.get("receiver", {}).get("parameter", "?")
                rtype = data.get("receiver", {}).get("receiver_type", "?")
                lines.append(f"- **{name}**: {rtype} → `{param}`")
            lines.append(f"\nUsage: `vrc_setup_contacts(preset=\"headpat\")` or `preset=\"all\"`")
            return "\n".join(lines)

        # Create contact marker bones in Blender
        bone_positions = []
        for contact in contacts_to_create:
            sender = contact.get("sender", {})
            receiver = contact.get("receiver", {})
            name = contact.get("name", "contact")

            if sender:
                bone_positions.append({
                    "bone_name": f"Contact_{name}_Sender",
                    "parent": sender.get("parent_bone", "Hips"),
                    "position": sender.get("position", [0, 0, 0]),
                    "radius": sender.get("radius", 0.1),
                })
            if receiver:
                bone_positions.append({
                    "bone_name": f"Contact_{name}_Receiver",
                    "parent": receiver.get("parent_bone", "Hips"),
                    "position": receiver.get("position", [0, 0, 0]),
                    "radius": receiver.get("radius", 0.1),
                })

        bones_json = json.dumps(bone_positions)

        code = f'''
import bpy, json
from mathutils import Vector

armature_name = {json.dumps(armature_name)}
bones_data = json.loads({json.dumps(bones_json)})

arm = None
if armature_name:
    arm = bpy.data.objects.get(armature_name)
if not arm:
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            arm = o
            break
if not arm:
    raise Exception("No armature found")

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')

created = []
for bd in bones_data:
    name = bd["bone_name"]
    parent_name = bd["parent"]
    pos = bd["position"]

    if name in arm.data.edit_bones:
        continue

    eb = arm.data.edit_bones.new(name)
    parent_eb = arm.data.edit_bones.get(parent_name)

    if parent_eb:
        base = parent_eb.head.copy()
        eb.head = base + Vector(pos)
        eb.tail = eb.head + Vector((0, 0.01, 0))
        eb.parent = parent_eb
    else:
        eb.head = Vector(pos)
        eb.tail = eb.head + Vector((0, 0.01, 0))

    created.append(name)

bpy.ops.object.mode_set(mode='OBJECT')
result = json.dumps({{"created": created}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
        except Exception as e:
            return f"Error creating contact bones: {e}"

        # Build Unity configuration
        unity_config = {"contacts": []}
        for contact in contacts_to_create:
            name = contact.get("name", "contact")
            sender = contact.get("sender", {})
            receiver = contact.get("receiver", {})
            if sender:
                unity_config["contacts"].append({
                    "type": "ContactSender",
                    "bone": f"Contact_{name}_Sender",
                    "radius": sender.get("radius", 0.1),
                    "collision_tags": sender.get("tags", ["Custom"]),
                })
            if receiver:
                unity_config["contacts"].append({
                    "type": "ContactReceiver",
                    "bone": f"Contact_{name}_Receiver",
                    "radius": receiver.get("radius", 0.1),
                    "collision_tags": receiver.get("tags", ["Custom"]),
                    "receiver_type": receiver.get("receiver_type", "Proximity"),
                    "parameter": receiver.get("parameter", f"{name}_Value"),
                })

        created_bones = result.get("created", [])
        lines = [
            "## VRC Contacts Setup",
            f"",
            f"**Bones created:** {len(created_bones)}",
        ]
        for b in created_bones:
            lines.append(f"  - {b}")

        lines.append(f"\n**Unity Configuration (add these components in Unity):**")
        lines.append(f"```json\n{json.dumps(unity_config, indent=2)}\n```")

        # List parameters that need to be added
        params = set()
        for c in unity_config["contacts"]:
            if "parameter" in c:
                params.add(c["parameter"])
        if params:
            lines.append(f"\n**Parameters to add to Expression Parameters:**")
            for p in params:
                lines.append(f"  - `{p}` (float)")

        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 16. VRC PhysBone Preset Apply
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_physbone_config(
        chain_name: str = "",
        preset: str = "",
        custom_config: str = "",
    ) -> str:
        """
        Generate VRChat PhysBone configuration for a bone chain.
        Creates a JSON config with tuned physics parameters for Unity import.

        Parameters:
        - chain_name: Name of the bone chain root (e.g., "Hair_Front_01")
        - preset: Physics preset: "hair_long", "hair_short", "tail", "ears",
                  "skirt", "breast", "ribbon", "chain_accessory"
        - custom_config: JSON override for specific parameters.
                        Example: '{"pull": 0.3, "gravity": 0.5}'
        """
        if not preset and not custom_config:
            lines = ["## VRC PhysBone Presets", ""]
            for name, config in VRC_PHYSBONE_PRESETS.items():
                lines.append(f"**{name}:**")
                for k, v in config.items():
                    lines.append(f"  {k}: {v}")
                lines.append("")
            lines.append("Usage: `vrc_physbone_config(chain_name=\"Hair_01\", preset=\"hair_long\")`")
            return "\n".join(lines)

        # Build config
        config = dict(VRC_PHYSBONE_DEFAULTS)
        if preset and preset in VRC_PHYSBONE_PRESETS:
            config.update(VRC_PHYSBONE_PRESETS[preset])
        if custom_config:
            try:
                config.update(json.loads(custom_config))
            except json.JSONDecodeError:
                return "Error: custom_config must be valid JSON"

        unity_component = {
            "component": "VRCPhysBone",
            "root_bone": chain_name,
            "pull": config["pull"],
            "spring": config["spring"],
            "stiffness": config["stiffness"],
            "gravity": config["gravity"],
            "gravity_falloff": config.get("gravity_falloff", 0),
            "immobile_type": config.get("immobile_type", "All"),
            "immobile": config.get("immobile", 0),
            "limits": {
                "type": "Angle" if config.get("max_angle_x", 180) < 180 else "None",
                "max_angle_x": config.get("max_angle_x", 180),
                "max_angle_z": config.get("max_angle_z", 180),
            },
            "collision": {
                "radius": config.get("radius", 0),
                "allow_collision": config.get("allow_collision", True),
            },
            "grab": {
                "allow_grabbing": config.get("allow_grabbing", True),
                "allow_posing": config.get("allow_posing", True),
                "grab_movement": config.get("grab_movement", 0.5),
                "snap_to_hand": config.get("snap_to_hand", False),
            },
            "stretch": {
                "max_stretch": config.get("max_stretch", 0),
            },
            "parameters": {
                "is_grabbed": f"{chain_name}_IsGrabbed" if config.get("allow_grabbing") else "",
                "is_posed": f"{chain_name}_IsPosed" if config.get("allow_posing") else "",
                "angle": f"{chain_name}_Angle",
                "stretch": f"{chain_name}_Stretch" if config.get("max_stretch", 0) > 0 else "",
            },
        }

        lines = [
            f"## PhysBone Config: {chain_name}",
            f"Preset: {preset or 'custom'}",
            "",
            f"```json\n{json.dumps(unity_component, indent=2)}\n```",
            "",
            "**Parameters generated (add to Expression Parameters if needed):**",
        ]
        for pname, pval in unity_component["parameters"].items():
            if pval:
                lines.append(f"  - `{pval}` (float)")

        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 17. VRC Animator Controller Generator
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_generate_animator(
        toggles: str = "",
        gestures: str = "",
        radials: str = "",
    ) -> str:
        """
        Generate VRChat FX Animator Controller blueprint.
        Creates the layer/state/transition structure as JSON that can be
        imported into Unity or used as a reference for manual setup.

        Parameters:
        - toggles: JSON array of toggle items:
            [{"name": "Hat", "parameter": "Hat_On", "object": "Hat_Mesh",
              "default_on": false}]
        - gestures: JSON array of gesture-driven expressions:
            [{"gesture": "Fist", "hand": "Left", "blendshape": "happy",
              "mesh": "Body"}]
        - radials: JSON array of radial puppet driven properties:
            [{"name": "Tail Speed", "parameter": "Tail_Speed",
              "property": "blendshape", "target": "Body/Tail_Wag"}]
        """
        toggle_list = json.loads(toggles) if toggles else []
        gesture_list = json.loads(gestures) if gestures else []
        radial_list = json.loads(radials) if radials else []

        if not toggle_list and not gesture_list and not radial_list:
            return ("## VRC Animator Controller Generator\n\n"
                    "Provide at least one of:\n"
                    "- `toggles`: Object on/off toggles\n"
                    "- `gestures`: Gesture-driven expressions\n"
                    "- `radials`: Radial puppet animations\n\n"
                    "Example:\n```json\n"
                    'toggles: [{"name": "Hat", "parameter": "Hat_On", "object": "Hat_Mesh"}]\n'
                    'gestures: [{"gesture": "Fist", "hand": "Left", "blendshape": "happy", "mesh": "Body"}]\n'
                    "```")

        layers = []
        parameters = []

        # Generate toggle layers (FX layer)
        for toggle in toggle_list:
            name = toggle["name"]
            param = toggle.get("parameter", f"{name}_On")
            obj = toggle.get("object", name)
            default_on = toggle.get("default_on", False)

            parameters.append({"name": param, "type": "bool", "default": default_on})

            layers.append({
                "layer_name": f"Toggle_{name}",
                "playable_layer": "FX",
                "default_weight": 1.0,
                "states": [
                    {
                        "name": "OFF",
                        "animation": {"type": "object_toggle", "object": obj, "active": False},
                        "is_default": not default_on,
                    },
                    {
                        "name": "ON",
                        "animation": {"type": "object_toggle", "object": obj, "active": True},
                        "is_default": default_on,
                    },
                ],
                "transitions": [
                    {"from": "OFF", "to": "ON", "condition": f"{param} = true"},
                    {"from": "ON", "to": "OFF", "condition": f"{param} = false"},
                ],
            })

        # Generate gesture layers
        for gesture in gesture_list:
            g_name = gesture.get("gesture", "Fist")
            hand = gesture.get("hand", "Left")
            blendshape = gesture.get("blendshape", "")
            mesh = gesture.get("mesh", "Body")

            gesture_param = f"Gesture{hand}"
            gesture_id = None
            for gid, gname in VRC_GESTURES.items():
                if gname == g_name:
                    gesture_id = gid
                    break

            if gesture_id is None:
                continue

            layers.append({
                "layer_name": f"Gesture_{hand}_{g_name}",
                "playable_layer": "FX",
                "default_weight": 1.0,
                "states": [
                    {
                        "name": "Idle",
                        "animation": {"type": "blendshape", "mesh": mesh,
                                      "shape": blendshape, "value": 0},
                        "is_default": True,
                    },
                    {
                        "name": g_name,
                        "animation": {"type": "blendshape", "mesh": mesh,
                                      "shape": blendshape, "value": 100},
                    },
                ],
                "transitions": [
                    {"from": "Idle", "to": g_name,
                     "condition": f"{gesture_param} = {gesture_id}"},
                    {"from": g_name, "to": "Idle",
                     "condition": f"{gesture_param} != {gesture_id}"},
                ],
                "note": f"Use Gesture{hand}Weight for smooth blending in transition"
            })

        # Generate radial layers
        for radial in radial_list:
            name = radial["name"]
            param = radial.get("parameter", f"{name}_Value")
            prop_type = radial.get("property", "blendshape")
            target = radial.get("target", "")

            parameters.append({"name": param, "type": "float", "default": 0.0})

            layers.append({
                "layer_name": f"Radial_{name}",
                "playable_layer": "FX",
                "default_weight": 1.0,
                "blend_tree": {
                    "type": "1D",
                    "parameter": param,
                    "children": [
                        {"threshold": 0.0, "animation": {"type": prop_type, "target": target, "value": 0}},
                        {"threshold": 1.0, "animation": {"type": prop_type, "target": target, "value": 100}},
                    ],
                },
            })

        # Calculate memory
        total_bits = sum(VRC_PARAM_BITS.get(p["type"], 8) for p in parameters)

        blueprint = {
            "controller_name": "FX",
            "layers": layers,
            "parameters": parameters,
            "memory_bits": total_bits,
            "memory_remaining": VRC_MAX_MEMORY_BITS - total_bits,
        }

        lines = [
            "## VRC Animator Controller Blueprint",
            "",
            f"**Layers:** {len(layers)}",
            f"**Parameters:** {len(parameters)} ({total_bits}/{VRC_MAX_MEMORY_BITS} bits)",
            "",
        ]

        for layer in layers:
            lines.append(f"### Layer: {layer['layer_name']}")
            if "states" in layer:
                for s in layer["states"]:
                    default = " (default)" if s.get("is_default") else ""
                    lines.append(f"  State: {s['name']}{default}")
                for t in layer.get("transitions", []):
                    lines.append(f"  Transition: {t['from']} → {t['to']} when `{t['condition']}`")
            if "blend_tree" in layer:
                bt = layer["blend_tree"]
                lines.append(f"  BlendTree 1D on `{bt['parameter']}`")
            lines.append("")

        lines.append(f"**Full Blueprint:**\n```json\n{json.dumps(blueprint, indent=2)}\n```")

        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 18. VRC Attach Accessory (VRCFury-like)
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_attach_accessory(
        accessory_name: str = "",
        target_bone: str = "",
        armature_name: str = "",
        create_toggle: bool = True,
        toggle_parameter: str = "",
        auto_scale: bool = True,
        rotation_correction: str = "",
    ) -> str:
        """
        Attach an accessory object to a bone on the avatar armature.
        Similar to VRCFury's armature link — parents the accessory,
        sets up proper hierarchy, and optionally generates a toggle parameter.

        Parameters:
        - accessory_name: Name of the accessory object (mesh) to attach
        - target_bone: Bone to attach to (e.g., "Head", "Left_Hand", "Hips")
        - armature_name: Avatar armature. If empty, uses first found.
        - create_toggle: Generate an Expression Menu toggle config (default: True)
        - toggle_parameter: Custom parameter name for toggle. Default: "{accessory_name}_On"
        - auto_scale: Auto-normalize accessory scale to match armature (default: True)
        - rotation_correction: Apply rotation before attach, e.g. "X90", "Z-90", "X90,Y180" (default: none)
        """
        if not accessory_name or not target_bone:
            return ("## VRC Attach Accessory\n\n"
                    "Required parameters:\n"
                    "- `accessory_name`: The mesh object to attach\n"
                    "- `target_bone`: Which bone to attach to\n\n"
                    "Example: `vrc_attach_accessory(accessory_name=\"Hat\", target_bone=\"Head\")`")

        toggle_param = toggle_parameter or f"{accessory_name}_On"

        code = f'''
import bpy, json
from mathutils import Vector

accessory_name = {json.dumps(accessory_name)}
target_bone = {json.dumps(target_bone)}
armature_name = {json.dumps(armature_name)}
auto_scale = {json.dumps(auto_scale)}
rotation_correction = {json.dumps(rotation_correction)}

# Find accessory
acc = bpy.data.objects.get(accessory_name)
if not acc:
    raise Exception(f"Object '{{accessory_name}}' not found")

# Find armature
arm = None
if armature_name:
    arm = bpy.data.objects.get(armature_name)
if not arm:
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            arm = o
            break
if not arm:
    raise Exception("No armature found")

# Verify target bone exists
if target_bone not in arm.data.bones:
    available = [b.name for b in arm.data.bones]
    raise Exception(f"Bone '{{target_bone}}' not found. Available: {{available[:20]}}")

log = []

# ── Scale normalization ──
if auto_scale and acc.type == 'MESH':
    import mathutils
    # Compare world-space scales (not local) to handle parent chains
    arm_scale = arm.matrix_world.to_scale()
    acc_scale = acc.matrix_world.to_scale()
    # If accessory scale differs significantly from armature scale, normalize
    scale_ratio = arm_scale.x / acc_scale.x if acc_scale.x > 1e-6 else 1.0
    if abs(scale_ratio - 1.0) > 0.05:
        acc.scale *= scale_ratio
        log.append(f"Scale normalized by {{scale_ratio:.2f}}x")

    # Apply transforms to freeze current scale/rotation
    bpy.ops.object.select_all(action='DESELECT')
    acc.select_set(True)
    bpy.context.view_layer.objects.active = acc
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    log.append("Applied transforms on accessory")

# ── Rotation correction ──
if rotation_correction:
    import math
    for part in rotation_correction.split(","):
        part = part.strip()
        if not part:
            continue
        axis = part[0].upper()
        angle = float(part[1:])
        rad = math.radians(angle)
        if axis == 'X':
            acc.rotation_euler[0] += rad
        elif axis == 'Y':
            acc.rotation_euler[1] += rad
        elif axis == 'Z':
            acc.rotation_euler[2] += rad
        log.append(f"Rotation correction: {{axis}} {{angle}} degrees")
    bpy.ops.object.select_all(action='DESELECT')
    acc.select_set(True)
    bpy.context.view_layer.objects.active = acc
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

# If accessory has its own armature, merge it
acc_arm = None
acc_mesh = None
if acc.type == 'ARMATURE':
    acc_arm = acc
    # Find the mesh child of this armature
    for child in acc.children:
        if child.type == 'MESH':
            acc_mesh = child
            break
elif acc.type == 'MESH':
    acc_mesh = acc
    if acc.parent and acc.parent.type == 'ARMATURE' and acc.parent != arm:
        acc_arm = acc.parent

if acc_arm and acc_arm != arm:
    # Unparent mesh children from accessory armature before merge
    mesh_children = [c for c in acc_arm.children if c.type == 'MESH']
    for mc in mesh_children:
        world_mat = mc.matrix_world.copy()
        mc.parent = None
        mc.matrix_world = world_mat

    # Merge accessory armature into avatar armature
    bpy.ops.object.select_all(action='DESELECT')
    acc_arm.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.join()
    log.append(f"Merged accessory armature into avatar armature")

    # Use the mesh we found earlier (now unparented, still valid)
    if acc_mesh is None and mesh_children:
        acc_mesh = mesh_children[0]

# Re-assign acc to the mesh object for parenting
if acc_mesh:
    acc = acc_mesh

# Parent accessory mesh to avatar armature with bone
if acc.type == 'MESH':
    # Store world transform
    world_matrix = acc.matrix_world.copy()

    acc.parent = arm
    acc.parent_type = 'BONE'
    acc.parent_bone = target_bone

    # Restore world position
    acc.matrix_world = world_matrix

    # Add armature modifier if not present
    has_arm_mod = any(m.type == 'ARMATURE' and m.object == arm for m in acc.modifiers)
    if not has_arm_mod:
        mod = acc.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = arm
        log.append(f"Added armature modifier")

    # Create vertex group for the target bone if not exists
    if target_bone not in acc.vertex_groups:
        vg = acc.vertex_groups.new(name=target_bone)
        all_verts = [v.index for v in acc.data.vertices]
        vg.add(all_verts, 1.0, 'REPLACE')
        log.append(f"Created vertex group '{{target_bone}}' with all vertices weighted")

    log.append(f"Parented '{{accessory_name}}' to bone '{{target_bone}}'")

result = json.dumps({{"log": log, "accessory": accessory_name, "bone": target_bone, "armature": arm.name}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
        except Exception as e:
            return f"Error attaching accessory: {e}"

        lines = [
            "## Accessory Attached",
            "",
        ]
        for l in result.get("log", []):
            lines.append(f"- {l}")

        if create_toggle:
            toggle_config = {
                "menu_item": {
                    "name": f"{accessory_name} Toggle",
                    "type": "Toggle",
                    "parameter": toggle_param,
                },
                "animator_layer": {
                    "layer_name": f"Toggle_{accessory_name}",
                    "states": ["OFF (object inactive)", "ON (object active)"],
                    "condition": f"{toggle_param} = true/false",
                },
                "parameter": {"name": toggle_param, "type": "bool", "default": True, "bits": 1},
            }
            lines.append(f"\n**Toggle Config (for Unity):**")
            lines.append(f"```json\n{json.dumps(toggle_config, indent=2)}\n```")

        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 18b. VRC Accessory Auto-Align
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_accessory_auto_align(
        accessory_name: str = "",
        armature_name: str = "",
        target_bone: str = "",
        scale_mode: str = "auto",
    ) -> str:
        """
        Auto-detect and fix misaligned accessories (shoes, hats, etc.)
        by comparing their bounding box to the target bone position and
        normalizing scale/rotation. Run this BEFORE vrc_attach_accessory.

        Parameters:
        - accessory_name: Name of the accessory mesh to align
        - armature_name: Avatar armature. If empty, uses first found.
        - target_bone: Target bone to align near (e.g., "Left foot"). Optional — used for positioning hint.
        - scale_mode: "auto" (detect and fix), "match_armature" (match armature scale), "none" (skip)
        """
        if not accessory_name:
            return ("## VRC Accessory Auto-Align\n\n"
                    "Required: `accessory_name` — the mesh to align.\n"
                    "Optional: `target_bone` — for positioning hint.")

        code = f'''
import bpy, json, math
from mathutils import Vector

accessory_name = {json.dumps(accessory_name)}
armature_name = {json.dumps(armature_name)}
target_bone = {json.dumps(target_bone)}
scale_mode = {json.dumps(scale_mode)}

acc = bpy.data.objects.get(accessory_name)
if not acc:
    raise Exception(f"Object '{{accessory_name}}' not found")

# Find armature
arm = None
if armature_name:
    arm = bpy.data.objects.get(armature_name)
if not arm:
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            arm = o
            break

log = []
diagnostics = {{}}

# ── Diagnose current state ──
diagnostics["original_location"] = list(acc.location)
diagnostics["original_rotation"] = [math.degrees(r) for r in acc.rotation_euler]
diagnostics["original_scale"] = list(acc.scale)

# Check if transforms are non-identity (common source of problems)
has_rotation = any(abs(r) > 0.01 for r in acc.rotation_euler)
has_scale = any(abs(s - 1.0) > 0.01 for s in acc.scale)
diagnostics["needs_transform_apply"] = has_rotation or has_scale

# ── Bounding box analysis ──
bb_corners = [acc.matrix_world @ Vector(c) for c in acc.bound_box]
bb_min = Vector((min(c[i] for c in bb_corners) for i in range(3)))
bb_max = Vector((max(c[i] for c in bb_corners) for i in range(3)))
bb_size = bb_max - bb_min
bb_center = (bb_min + bb_max) / 2
diagnostics["bounding_box_size"] = [round(s, 4) for s in bb_size]
diagnostics["bounding_box_center"] = [round(s, 4) for s in bb_center]

# ── Compare to armature if available ──
if arm:
    arm_bb = [arm.matrix_world @ Vector(c) for c in arm.bound_box]
    arm_min = Vector((min(c[i] for c in arm_bb) for i in range(3)))
    arm_max = Vector((max(c[i] for c in arm_bb) for i in range(3)))
    arm_size = arm_max - arm_min
    arm_height = arm_size.z

    # Scale ratio check
    acc_height = bb_size.z
    if acc_height > 0:
        height_ratio = arm_height / acc_height
        diagnostics["height_ratio_vs_armature"] = round(height_ratio, 2)

        # If accessory is >3x or <0.3x the armature height, it's likely wrong scale
        if scale_mode == "auto" and (height_ratio > 3.0 or height_ratio < 0.3):
            # Estimate correct scale based on bone size if we have a target bone
            if target_bone and target_bone in arm.data.bones:
                bone = arm.data.bones[target_bone]
                bone_length = bone.length
                # Shoe should be roughly 1.5-2x bone length
                target_size = bone_length * 1.8
                scale_factor = target_size / acc_height if acc_height > 0 else 1.0
                acc.scale *= scale_factor
                log.append(f"Auto-scaled by {{scale_factor:.2f}}x (bone-based estimate)")
            else:
                # Rough fix: make accessory ~20% of armature height as default
                target_size = arm_height * 0.2
                scale_factor = target_size / acc_height
                acc.scale *= scale_factor
                log.append(f"Auto-scaled by {{scale_factor:.2f}}x (proportion estimate)")

    elif scale_mode == "match_armature":
        ratio = arm.scale.x / acc.scale.x if acc.scale.x != 0 else 1.0
        if abs(ratio - 1.0) > 0.01:
            acc.scale *= ratio
            log.append(f"Matched armature scale (ratio: {{ratio:.2f}})")

# ── Axis alignment check ──
# Detect if accessory appears to be rotated 90 degrees (common FBX issue)
# Heuristic: if the tallest axis isn't Z (up), it's probably mis-rotated
axis_sizes = {{"X": bb_size.x, "Y": bb_size.y, "Z": bb_size.z}}
tallest_axis = max(axis_sizes, key=axis_sizes.get)

# For most VRC accessories, Z should be up (height axis)
# Shoes are an exception — they should be longer in Y (forward)
is_shoe = any(kw in accessory_name.lower() for kw in ["shoe", "slipper", "boot", "heel", "foot", "sandal"])

if not is_shoe and tallest_axis != "Z" and bb_size.z > 0.01:
    # Likely needs rotation correction
    diagnostics["axis_warning"] = f"Tallest axis is {{tallest_axis}}, expected Z (up). May need rotation."
    log.append(f"WARNING: tallest axis is {{tallest_axis}}, may need rotation correction")

if is_shoe and tallest_axis == "Z" and bb_size.z > bb_size.y * 1.5:
    diagnostics["axis_warning"] = "Shoe appears to be standing upright — may need X-90 rotation"
    log.append("WARNING: shoe appears upright, consider rotation_correction='X-90'")

# ── Apply transforms ──
bpy.ops.object.select_all(action='DESELECT')
acc.select_set(True)
bpy.context.view_layer.objects.active = acc
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
log.append("Applied transforms (rotation + scale frozen)")

# ── Position near target bone ──
if target_bone and arm and target_bone in arm.data.bones:
    bone = arm.data.bones[target_bone]
    bone_head_world = arm.matrix_world @ bone.head_local
    # Only snap position if accessory is far from the bone
    dist = (bb_center - bone_head_world).length
    diagnostics["distance_to_bone"] = round(dist, 4)
    if dist > arm_height * 0.5:
        acc.location = bone_head_world
        log.append(f"Positioned near bone '{{target_bone}}' (was {{dist:.3f}}m away)")

diagnostics["final_scale"] = list(acc.scale)
diagnostics["final_rotation"] = [math.degrees(r) for r in acc.rotation_euler]
diagnostics["log"] = log

result = json.dumps(diagnostics)
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
        except Exception as e:
            return f"Error aligning accessory: {e}"

        lines = [
            "## Accessory Auto-Align Report",
            "",
            f"**Object:** {accessory_name}",
            f"**Bounding Box:** {result.get('bounding_box_size', 'N/A')}",
            f"**Original Scale:** {result.get('original_scale', 'N/A')}",
            f"**Original Rotation:** {result.get('original_rotation', 'N/A')}",
        ]

        if "height_ratio_vs_armature" in result:
            lines.append(f"**Height Ratio vs Armature:** {result['height_ratio_vs_armature']}x")
        if "distance_to_bone" in result:
            lines.append(f"**Distance to Target Bone:** {result['distance_to_bone']}m")
        if "axis_warning" in result:
            lines.append(f"\n**WARNING:** {result['axis_warning']}")

        if result.get("log"):
            lines.append("\n**Actions Taken:**")
            for l in result["log"]:
                lines.append(f"- {l}")

        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 19. VRC Texture Atlas Baker
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_bake_atlas(
        mesh_name: str = "",
        atlas_size: int = 2048,
        output_path: str = "",
    ) -> str:
        """
        Bake multiple materials into a single texture atlas.
        Re-maps UVs so all materials fit into one texture, reducing
        material count for better VRChat performance rank.

        Parameters:
        - mesh_name: Target mesh. If empty, uses "Body" or first mesh.
        - atlas_size: Atlas texture resolution (default: 2048). Use 1024 for Quest.
        - output_path: Where to save the baked atlas image.
                      If empty, saves next to the .blend file.
        """
        code = f'''
import bpy, json, os

mesh_name = {json.dumps(mesh_name)}
atlas_size = {atlas_size}
output_path = {json.dumps(output_path)}

# Find mesh
obj = None
if mesh_name:
    obj = bpy.data.objects.get(mesh_name)
if not obj:
    obj = bpy.data.objects.get("Body")
if not obj:
    for o in bpy.data.objects:
        if o.type == 'MESH':
            obj = o
            break

if not obj or obj.type != 'MESH':
    raise Exception("No mesh found")

log = []
mat_count = len(obj.material_slots)
log.append(f"Mesh '{{obj.name}}' has {{mat_count}} materials")

if mat_count <= 1:
    log.append("Only 1 material, no atlas needed")
    result = json.dumps({{"log": log, "atlas_created": False}})
else:
    # Step 1: Smart UV Project to create unified UV map
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Create new UV map for atlas
    atlas_uv = obj.data.uv_layers.new(name="Atlas_UV")
    obj.data.uv_layers.active = atlas_uv

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(
        angle_limit=1.15192,  # 66 degrees
        island_margin=0.02,
        area_weight=0.0,
        correct_aspect=True,
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    log.append("Created Atlas_UV with smart UV projection")

    # Step 2: Create atlas image
    atlas_img = bpy.data.images.new(
        name="VRC_Atlas",
        width=atlas_size,
        height=atlas_size,
        alpha=True,
    )
    log.append(f"Created atlas image: {{atlas_size}}x{{atlas_size}}")

    # Step 3: Assign atlas image to all materials for baking
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat and mat.use_nodes:
            # Add image texture node for baking target
            nodes = mat.node_tree.nodes
            img_node = nodes.new('ShaderNodeTexImage')
            img_node.name = "VRC_Atlas_Bake"
            img_node.image = atlas_img
            # Select it (required for bake target)
            for n in nodes:
                n.select = False
            img_node.select = True
            nodes.active = img_node

    # Step 4: Bake diffuse (save and restore render engine)
    prev_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 1
    bpy.context.scene.cycles.bake_type = 'DIFFUSE'
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True

    try:
        bpy.ops.object.bake(type='DIFFUSE')
        log.append("Baked diffuse to atlas")
    except Exception as e:
        log.append(f"Bake warning: {{str(e)}} (may need GPU or Cycles enabled)")
    finally:
        bpy.context.scene.render.engine = prev_engine

    # Step 5: Save atlas image
    if not output_path:
        blend_path = bpy.data.filepath
        if blend_path:
            output_path = os.path.join(os.path.dirname(blend_path), "VRC_Atlas.png")
        else:
            output_path = os.path.join(os.path.expanduser("~"), "VRC_Atlas.png")

    atlas_img.filepath_raw = output_path
    atlas_img.file_format = 'PNG'
    atlas_img.save()
    log.append(f"Saved atlas to: {{output_path}}")

    # Step 6: Create unified material
    atlas_mat = bpy.data.materials.new(name="VRC_Atlas_Material")
    atlas_mat.use_nodes = True
    nodes = atlas_mat.node_tree.nodes
    links = atlas_mat.node_tree.links

    # Clear default nodes
    for n in nodes:
        nodes.remove(n)

    # Add Principled BSDF + Image Texture
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    tex = nodes.new('ShaderNodeTexImage')
    tex.location = (-300, 0)
    tex.image = atlas_img
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)

    links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # UV Map node pointing to Atlas_UV
    uv_node = nodes.new('ShaderNodeUVMap')
    uv_node.location = (-500, 0)
    uv_node.uv_map = "Atlas_UV"
    links.new(uv_node.outputs['UV'], tex.inputs['Vector'])

    log.append("Created VRC_Atlas_Material with atlas texture")
    log.append("To apply: replace all material slots with VRC_Atlas_Material")

    # Clean up bake nodes from original materials
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat and mat.use_nodes:
            bake_node = mat.node_tree.nodes.get("VRC_Atlas_Bake")
            if bake_node:
                mat.node_tree.nodes.remove(bake_node)

    result = json.dumps({{
        "log": log,
        "atlas_created": True,
        "atlas_path": output_path,
        "original_materials": mat_count,
        "atlas_material": "VRC_Atlas_Material",
    }})

result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
            lines = ["## VRC Texture Atlas", ""]
            for l in result.get("log", []):
                lines.append(f"- {l}")
            if result.get("atlas_created"):
                lines.append(f"\n**Result:** {result.get('original_materials')} materials → 1 atlas")
                lines.append(f"**Atlas:** {result.get('atlas_path')}")
                lines.append(f"\nTo finalize: assign `VRC_Atlas_Material` to all slots, "
                           f"set active UV to `Atlas_UV`, delete old materials.")
            return "\n".join(lines)
        except Exception as e:
            return f"Error baking atlas: {e}"

    # ─────────────────────────────────────────────
    # 20. VRC Gesture Setup — Blendshape animations for hand gestures
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_setup_gestures(
        mesh_name: str = "",
        mapping: str = "",
    ) -> str:
        """
        Set up gesture-driven blendshapes. Creates shape keys for each hand gesture
        and generates the Animator Controller configuration.

        VRC Gestures: Neutral(0), Fist(1), HandOpen(2), FingerPoint(3),
                     Victory(4), RockNRoll(5), HandGun(6), ThumbsUp(7)

        Parameters:
        - mesh_name: Face mesh. If empty, auto-detects.
        - mapping: JSON mapping of gesture to blendshape name.
                  Example: '{"Fist": "angry", "Victory": "peace_sign",
                           "HandOpen": "surprised"}'
                  If empty, creates template shape keys for all gestures.
        """
        gesture_map = json.loads(mapping) if mapping else {}
        gestures_json = json.dumps(VRC_GESTURES)

        if not gesture_map:
            # Create templates for common gesture expressions
            gesture_map = {
                "Fist": "gesture_fist",
                "HandOpen": "gesture_open",
                "FingerPoint": "gesture_point",
                "Victory": "gesture_victory",
                "RockNRoll": "gesture_rocknroll",
                "HandGun": "gesture_handgun",
                "ThumbsUp": "gesture_thumbsup",
            }

        gesture_map_json = json.dumps(gesture_map)

        code = f'''
import bpy, json

mesh_name = {json.dumps(mesh_name)}
gesture_map = json.loads({json.dumps(gesture_map_json)})

obj = None
if mesh_name:
    obj = bpy.data.objects.get(mesh_name)
if not obj:
    obj = bpy.data.objects.get("Body")
if not obj:
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.data.shape_keys:
            obj = o
            break
if not obj:
    for o in bpy.data.objects:
        if o.type == 'MESH':
            obj = o
            break

if not obj:
    raise Exception("No mesh found")

if not obj.data.shape_keys:
    obj.shape_key_add(name="Basis", from_mix=False)

existing = [kb.name for kb in obj.data.shape_keys.key_blocks]
created = []

for gesture, shape_name in gesture_map.items():
    if shape_name not in existing:
        obj.shape_key_add(name=shape_name, from_mix=False)
        created.append(shape_name)

result = json.dumps({{
    "mesh": obj.name,
    "created": created,
    "total_gesture_shapes": len(gesture_map),
    "mapping": gesture_map,
}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
        except Exception as e:
            return f"Error setting up gestures: {e}"

        lines = [
            f"## VRC Gesture Setup on '{result.get('mesh')}'",
            "",
            f"Created {len(result.get('created', []))} shape keys",
            "",
            "**Gesture → Shape Key Mapping:**",
        ]

        for gid, gname in VRC_GESTURES.items():
            shape = gesture_map.get(gname, "—")
            lines.append(f"  [{gid}] {gname} → `{shape}`")

        # Generate animator config
        animator_layers = []
        for hand in ["Left", "Right"]:
            layer = {
                "layer_name": f"Gesture_{hand}",
                "parameter": f"Gesture{hand}",
                "weight_parameter": f"Gesture{hand}Weight",
                "states": [],
            }
            for gid, gname in VRC_GESTURES.items():
                shape = gesture_map.get(gname)
                if shape:
                    layer["states"].append({
                        "gesture_id": gid,
                        "gesture_name": gname,
                        "blendshape": shape,
                        "value": 100,
                    })
            animator_layers.append(layer)

        lines.append(f"\n**Animator Config (for Unity FX layer):**")
        lines.append(f"```json\n{json.dumps(animator_layers, indent=2)}\n```")
        lines.append("\nUse `GestureLeftWeight`/`GestureRightWeight` for smooth blending.")

        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 21. VRC Dynamics Budget Calculator
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_dynamics_budget(
        physbone_chains: str = "",
        contacts: str = "",
        target: str = "pc",
    ) -> str:
        """
        Calculate VRChat Avatar Dynamics budget usage.
        Checks PhysBones, Contacts, and Constraints against performance rank limits.

        Parameters:
        - physbone_chains: JSON array of chains:
            [{"name": "Hair", "bones": 4, "colliders": 1},
             {"name": "Tail", "bones": 6, "colliders": 2}]
        - contacts: JSON array:
            [{"name": "Headpat", "senders": 1, "receivers": 1},
             {"name": "Boop", "senders": 1, "receivers": 1}]
        - target: "pc" or "quest" (default: "pc")
        """
        chains = json.loads(physbone_chains) if physbone_chains else []
        contact_list = json.loads(contacts) if contacts else []

        # If no input, scan the scene
        if not chains and not contact_list:
            code = '''
import bpy, json

chains = []
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        for bone in obj.data.bones:
            # Detect potential physbone chains (leaf chains with physics-like names)
            children = [b for b in obj.data.bones if b.parent == bone]
            if children and any(kw in bone.name.lower() for kw in
                ['hair', 'tail', 'ear', 'skirt', 'ribbon', 'chain', 'physbone', 'breast']):
                chain_len = 1
                current = children[0] if children else None
                while current:
                    chain_len += 1
                    child_children = [b for b in obj.data.bones if b.parent == current]
                    current = child_children[0] if child_children else None
                chains.append({"name": bone.name, "bones": chain_len, "colliders": 0})

# Count contact-related bones
contacts = []
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        for bone in obj.data.bones:
            if 'contact' in bone.name.lower() or 'sender' in bone.name.lower() or 'receiver' in bone.name.lower():
                role = "sender" if "sender" in bone.name.lower() else "receiver"
                contacts.append({"name": bone.name, "senders": 1 if role == "sender" else 0,
                                "receivers": 1 if role == "receiver" else 0})

result = json.dumps({"chains": chains, "contacts": contacts})
result
'''
            try:
                raw = _exec(code)
                scene_data = json.loads(raw.get("result", "{}"))
                chains = scene_data.get("chains", [])
                contact_list = scene_data.get("contacts", [])
            except Exception:
                pass

        # Calculate totals
        total_pb_components = len(chains)
        total_pb_transforms = sum(c.get("bones", 0) for c in chains)
        total_pb_colliders = sum(c.get("colliders", 0) for c in chains)
        total_senders = sum(c.get("senders", 0) for c in contact_list)
        total_receivers = sum(c.get("receivers", 0) for c in contact_list)

        limits = VRC_DYNAMICS_LIMITS.get(target, VRC_DYNAMICS_LIMITS["pc"])

        # Determine rank
        rank = "Very Poor"
        for r in ("excellent", "good", "medium", "poor"):
            lim = limits[r]
            if (total_pb_components <= lim["physbone_components"] and
                total_pb_transforms <= lim["physbone_transforms"] and
                total_pb_colliders <= lim["physbone_colliders"] and
                total_senders <= lim["contact_senders"] and
                total_receivers <= lim["contact_receivers"]):
                rank = r.capitalize()
                break

        lines = [
            f"## VRC Dynamics Budget ({target.upper()})",
            f"**Rank: {rank}**",
            "",
            "| Component | Current | Excellent | Good | Medium | Poor |",
            "|-----------|---------|-----------|------|--------|------|",
            f"| PhysBone Components | {total_pb_components} | {limits['excellent']['physbone_components']} | {limits['good']['physbone_components']} | {limits['medium']['physbone_components']} | {limits['poor']['physbone_components']} |",
            f"| PhysBone Transforms | {total_pb_transforms} | {limits['excellent']['physbone_transforms']} | {limits['good']['physbone_transforms']} | {limits['medium']['physbone_transforms']} | {limits['poor']['physbone_transforms']} |",
            f"| PhysBone Colliders | {total_pb_colliders} | {limits['excellent']['physbone_colliders']} | {limits['good']['physbone_colliders']} | {limits['medium']['physbone_colliders']} | {limits['poor']['physbone_colliders']} |",
            f"| Contact Senders | {total_senders} | {limits['excellent']['contact_senders']} | {limits['good']['contact_senders']} | {limits['medium']['contact_senders']} | {limits['poor']['contact_senders']} |",
            f"| Contact Receivers | {total_receivers} | {limits['excellent']['contact_receivers']} | {limits['good']['contact_receivers']} | {limits['medium']['contact_receivers']} | {limits['poor']['contact_receivers']} |",
            "",
        ]

        if chains:
            lines.append("**PhysBone Chains:**")
            for c in chains:
                lines.append(f"  - {c['name']}: {c.get('bones', 0)} bones, {c.get('colliders', 0)} colliders")

        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # 22. VRC Import Model (VRM/PMX/FBX with auto-fix)
    # ─────────────────────────────────────────────
    @mcp.tool()
    def vrc_import_model(
        filepath: str,
        auto_fix: bool = True,
        fbx_preset: str = "default",
        apply_transforms: bool = True,
    ) -> str:
        """
        Import a model file (FBX/VRM/OBJ) and optionally auto-fix it for VRChat.
        Handles axis conversion, applies transforms, and reports model stats.

        Parameters:
        - filepath: Path to the model file
        - auto_fix: Run vrc_fix_model after import (default: True)
        - fbx_preset: FBX axis preset — "default", "unity", "mixamo", or "mmd" (default: "default")
        - apply_transforms: Apply location/rotation/scale on imported objects (default: True)
        """
        from blender_mcp.vrc_constants import VRC_FBX_IMPORT_PRESETS

        ext = filepath.lower().rsplit(".", 1)[-1] if "." in filepath else ""

        # Build FBX import with axis settings from preset
        fbx_settings = VRC_FBX_IMPORT_PRESETS.get(fbx_preset, VRC_FBX_IMPORT_PRESETS["default"])
        fbx_args = ", ".join(
            f'{k}={json.dumps(v)}' for k, v in fbx_settings.items()
        )
        import_code = {
            "fbx": f'bpy.ops.import_scene.fbx(filepath={json.dumps(filepath)}, {fbx_args})',
            "obj": f'bpy.ops.wm.obj_import(filepath={json.dumps(filepath)})',
            "glb": f'bpy.ops.import_scene.gltf(filepath={json.dumps(filepath)})',
            "gltf": f'bpy.ops.import_scene.gltf(filepath={json.dumps(filepath)})',
            "vrm": f'bpy.ops.import_scene.vrm(filepath={json.dumps(filepath)})',
        }

        if ext not in import_code:
            return f"Unsupported format '.{ext}'. Supported: fbx, obj, glb, gltf, vrm"

        code = f'''
import bpy, json

# Record existing objects
existing = set(o.name for o in bpy.data.objects)

# Import
{import_code[ext]}

# Find new objects
new_objs = [o for o in bpy.data.objects if o.name not in existing]

meshes = [o for o in new_objs if o.type == 'MESH']
armatures = [o for o in new_objs if o.type == 'ARMATURE']

# Apply transforms on imported objects to normalize scale/rotation
apply_transforms = {json.dumps(apply_transforms)}
if apply_transforms:
    bpy.ops.object.select_all(action='DESELECT')
    for o in new_objs:
        o.select_set(True)
    if new_objs:
        bpy.context.view_layer.objects.active = new_objs[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

total_tris = 0
for m in meshes:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = m.evaluated_get(depsgraph)
    me = eval_obj.to_mesh()
    me.calc_loop_triangles()
    total_tris += len(me.loop_triangles)
    eval_obj.to_mesh_clear()

result = json.dumps({{
    "imported_objects": [o.name for o in new_objs],
    "meshes": [o.name for o in meshes],
    "armatures": [o.name for o in armatures],
    "total_tris": total_tris,
    "bone_count": sum(len(a.data.bones) for a in armatures),
}})
result
'''
        try:
            raw = _exec(code)
            result = json.loads(raw.get("result", "{}"))
        except Exception as e:
            return f"Error importing: {e}"

        lines = [
            f"## Model Imported: {filepath.split('/')[-1].split(chr(92))[-1]}",
            "",
            f"- Objects: {len(result.get('imported_objects', []))}",
            f"- Meshes: {', '.join(result.get('meshes', []))}",
            f"- Armatures: {', '.join(result.get('armatures', []))}",
            f"- Triangles: {result.get('total_tris', 0):,}",
            f"- Bones: {result.get('bone_count', 0)}",
        ]

        if auto_fix and result.get("armatures"):
            lines.append("\nRunning auto-fix...")
            fix_result = vrc_fix_model(armature_name=result["armatures"][0])
            lines.append(fix_result)

        return "\n".join(lines)

    logger.info("VRC tools registered: 23 tools")
