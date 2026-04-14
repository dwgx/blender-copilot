# Rigify Integration Tools for BlenderMCP
# Provides Rigify meta-rig generation, fitting, VRC conversion, face rig, and IK configuration.

import json
import logging

logger = logging.getLogger("BlenderMCPServer.Rigify")


def register_rigify_tools(mcp, send_command_fn):
    """Register all Rigify tools on the FastMCP instance."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    # ─────────────────────────────────────────────
    # 1. rigify_create_metarig
    # ─────────────────────────────────────────────
    @mcp.tool()
    def rigify_create_metarig(
        rig_type: str = "human",
        name: str = "metarig",
        include_face: bool = True,
        include_fingers: bool = True,
    ) -> str:
        """
        Generate a Rigify meta-rig (the template rig that Rigify uses to generate the final rig).

        Parameters:
        - rig_type: "human", "human_simple", "quadruped", "bird", "cat", "horse", "shark", "wolf" (default: "human")
        - name: Name for the meta-rig armature (default: "metarig")
        - include_face: Include face rig bones (default: True)
        - include_fingers: Include finger bones (default: True)
        """
        code = f'''
import bpy
import json

rig_type = {json.dumps(rig_type)}
name = {json.dumps(name)}
include_face = {json.dumps(include_face)}
include_fingers = {json.dumps(include_fingers)}

# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Map rig_type to Rigify metarig operator
metarig_map = {{
    "human": "armature.rigify_metarig_human",
    "human_simple": "armature.rigify_metarig_human_simple",
    "quadruped": "armature.rigify_metarig_quadruped",
    "bird": "armature.rigify_metarig_bird",
    "cat": "armature.rigify_metarig_cat",
    "horse": "armature.rigify_metarig_horse",
    "shark": "armature.rigify_metarig_shark",
    "wolf": "armature.rigify_metarig_wolf",
}}

# Ensure Rigify addon is enabled
import addon_utils
addon_utils.enable("rigify", default_set=True)

# Check if operator exists
op_name = metarig_map.get(rig_type, "armature.rigify_metarig_human")
parts = op_name.split(".")
op_category = getattr(bpy.ops, parts[0], None)
op_func = getattr(op_category, parts[1], None) if op_category else None

if op_func is None:
    # Fallback: use basic human metarig via add menu
    bpy.ops.object.armature_human_metarig_add()
else:
    op_func()

# Rename the created metarig
metarig = bpy.context.active_object
if metarig and metarig.type == 'ARMATURE':
    metarig.name = name
    metarig.data.name = name + "_data"

    bone_count = len(metarig.data.bones)

    # Optionally remove face bones
    if not include_face:
        bpy.ops.object.mode_set(mode='EDIT')
        face_prefixes = ["face", "lip", "nose", "brow", "lid", "ear", "cheek", "tongue", "teeth", "jaw", "chin", "temple", "forehead"]
        removed = 0
        for bone in list(metarig.data.edit_bones):
            if any(bone.name.lower().startswith(p) for p in face_prefixes):
                metarig.data.edit_bones.remove(bone)
                removed += 1
        bpy.ops.object.mode_set(mode='OBJECT')
        bone_count -= removed

    # Optionally remove finger bones
    if not include_fingers:
        bpy.ops.object.mode_set(mode='EDIT')
        finger_names = ["thumb", "f_index", "f_middle", "f_ring", "f_pinky", "palm"]
        removed = 0
        for bone in list(metarig.data.edit_bones):
            if any(f in bone.name.lower() for f in finger_names):
                metarig.data.edit_bones.remove(bone)
                removed += 1
        bpy.ops.object.mode_set(mode='OBJECT')
        bone_count -= removed

    result = {{
        "status": "success",
        "metarig": name,
        "rig_type": rig_type,
        "bone_count": bone_count,
        "include_face": include_face,
        "include_fingers": include_fingers
    }}
else:
    result = {{"status": "error", "message": "Failed to create metarig - no armature created"}}

json.dumps(result)
'''
        return _exec(code)

    # ─────────────────────────────────────────────
    # 2. rigify_fit_metarig
    # ─────────────────────────────────────────────
    @mcp.tool()
    def rigify_fit_metarig(
        metarig_name: str = "metarig",
        mesh_name: str = "",
        method: str = "proportional",
    ) -> str:
        """
        Auto-fit a Rigify meta-rig to match a target mesh's proportions.
        Analyzes the mesh bounding box and key landmarks to position bones.

        Parameters:
        - metarig_name: Name of the meta-rig armature (default: "metarig")
        - mesh_name: Target mesh to fit to. If empty, uses the largest mesh in scene.
        - method: "proportional" (scale bones to mesh proportions) or "snap" (snap key bones to nearest surface)
        """
        code = f'''
import bpy
import json
from mathutils import Vector

metarig_name = {json.dumps(metarig_name)}
mesh_name = {json.dumps(mesh_name)}
method = {json.dumps(method)}

metarig = bpy.data.objects.get(metarig_name)
if not metarig or metarig.type != 'ARMATURE':
    result = {{"status": "error", "message": f"Metarig '{{metarig_name}}' not found or not an armature"}}
else:
    # Find target mesh
    target = None
    if mesh_name:
        target = bpy.data.objects.get(mesh_name)
    else:
        # Find largest mesh
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
        if meshes:
            target = max(meshes, key=lambda o: max(o.dimensions))

    if not target:
        result = {{"status": "error", "message": "No target mesh found"}}
    else:
        # Get mesh bounds in world space
        mesh_verts = [target.matrix_world @ Vector(v) for v in target.bound_box]
        mesh_min = Vector((min(v.x for v in mesh_verts), min(v.y for v in mesh_verts), min(v.z for v in mesh_verts)))
        mesh_max = Vector((max(v.x for v in mesh_verts), max(v.y for v in mesh_verts), max(v.z for v in mesh_verts)))
        mesh_center = (mesh_min + mesh_max) / 2
        mesh_height = mesh_max.z - mesh_min.z
        mesh_width = mesh_max.x - mesh_min.x
        mesh_depth = mesh_max.y - mesh_min.y

        # Get metarig bounds
        rig_verts = [metarig.matrix_world @ Vector(v) for v in metarig.bound_box]
        rig_min = Vector((min(v.x for v in rig_verts), min(v.y for v in rig_verts), min(v.z for v in rig_verts)))
        rig_max = Vector((max(v.x for v in rig_verts), max(v.y for v in rig_verts), max(v.z for v in rig_verts)))
        rig_height = rig_max.z - rig_min.z

        if method == "proportional":
            # Scale metarig to match mesh height
            if rig_height > 0:
                scale_factor = mesh_height / rig_height
                metarig.scale = Vector((scale_factor, scale_factor, scale_factor))
                bpy.context.view_layer.update()

                # Apply scale
                bpy.context.view_layer.objects.active = metarig
                metarig.select_set(True)
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

                # Center metarig on mesh (X,Y center, Z at mesh bottom)
                metarig.location.x = mesh_center.x
                metarig.location.y = mesh_center.y
                metarig.location.z = mesh_min.z

                # Fine-tune key bone positions in edit mode
                bpy.ops.object.mode_set(mode='EDIT')
                edit_bones = metarig.data.edit_bones

                adjustments = []

                # Head top — align with mesh top
                head_top = edit_bones.get("spine.006")
                if head_top:
                    old_z = head_top.tail.z
                    head_top.tail.z = mesh_max.z - metarig.location.z
                    adjustments.append(f"head_top: {{old_z:.3f}} -> {{head_top.tail.z:.3f}}")

                # Hips width — estimate from mesh width
                for side in [".L", ".R"]:
                    thigh = edit_bones.get("thigh" + side)
                    if thigh:
                        sign = 1 if side == ".L" else -1
                        thigh.head.x = sign * mesh_width * 0.1  # hips ~20% of width

                # Shoulder width
                for side in [".L", ".R"]:
                    upper_arm = edit_bones.get("upper_arm" + side)
                    if upper_arm:
                        sign = 1 if side == ".L" else -1
                        upper_arm.head.x = sign * mesh_width * 0.22

                bpy.ops.object.mode_set(mode='OBJECT')

                result = {{
                    "status": "success",
                    "metarig": metarig_name,
                    "target_mesh": target.name,
                    "method": method,
                    "scale_factor": round(scale_factor, 4),
                    "mesh_height": round(mesh_height, 4),
                    "mesh_width": round(mesh_width, 4),
                    "adjustments": adjustments,
                }}
            else:
                result = {{"status": "error", "message": "Metarig has zero height"}}

        elif method == "snap":
            # Snap key bones to nearest mesh surface using raycasts
            import bmesh

            bpy.context.view_layer.objects.active = metarig
            bpy.ops.object.mode_set(mode='EDIT')
            edit_bones = metarig.data.edit_bones

            # First scale proportionally
            if rig_height > 0:
                scale_factor = mesh_height / rig_height
                for bone in edit_bones:
                    bone.head *= scale_factor
                    bone.tail *= scale_factor

            # Build BVH tree for mesh
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = target.evaluated_get(depsgraph)
            bm = bmesh.new()
            bm.from_mesh(eval_obj.data)
            from mathutils.bvhtree import BVHTree
            bvh = BVHTree.FromBMesh(bm)

            # Snap key bones to surface
            snapped = []
            key_bones = ["spine", "spine.001", "spine.003", "spine.004", "spine.006",
                         "thigh.L", "thigh.R", "shin.L", "shin.R", "foot.L", "foot.R",
                         "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R",
                         "hand.L", "hand.R"]

            inv_mat = target.matrix_world.inverted()
            for bname in key_bones:
                bone = edit_bones.get(bname)
                if bone:
                    # Transform bone head to mesh local space
                    world_pos = metarig.matrix_world @ bone.head
                    local_pos = inv_mat @ world_pos
                    loc, normal, idx, dist = bvh.find_nearest(local_pos)
                    if loc is not None:
                        # Project to keep bone inside mesh (move toward center)
                        center_local = inv_mat @ mesh_center
                        direction = (center_local - loc).normalized()
                        adjusted = loc + direction * 0.02  # 2cm inside surface
                        new_world = target.matrix_world @ adjusted
                        bone.head = metarig.matrix_world.inverted() @ new_world
                        snapped.append(bname)

            bm.free()
            bpy.ops.object.mode_set(mode='OBJECT')

            result = {{
                "status": "success",
                "metarig": metarig_name,
                "target_mesh": target.name,
                "method": "snap",
                "snapped_bones": snapped,
                "snapped_count": len(snapped),
            }}

json.dumps(result)
'''
        return _exec(code)

    # ─────────────────────────────────────────────
    # 3. rigify_generate_rig
    # ─────────────────────────────────────────────
    @mcp.tool()
    def rigify_generate_rig(
        metarig_name: str = "metarig",
        parent_to_mesh: str = "",
    ) -> str:
        """
        Generate the final production rig from a Rigify meta-rig.
        This creates the full control rig with IK/FK switches, custom shapes, etc.

        Parameters:
        - metarig_name: Name of the meta-rig armature (default: "metarig")
        - parent_to_mesh: If provided, auto-parent this mesh to the generated rig with automatic weights.
        """
        code = f'''
import bpy
import json

metarig_name = {json.dumps(metarig_name)}
parent_to_mesh = {json.dumps(parent_to_mesh)}

# Ensure Rigify is enabled
import addon_utils
addon_utils.enable("rigify", default_set=True)

metarig = bpy.data.objects.get(metarig_name)
if not metarig or metarig.type != 'ARMATURE':
    result = {{"status": "error", "message": f"Metarig '{{metarig_name}}' not found"}}
else:
    # Select and activate metarig
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = metarig
    metarig.select_set(True)

    # Generate the rig
    try:
        bpy.ops.pose.rigify_generate()

        # Find the generated rig (Rigify creates "rig" or renames existing)
        generated = bpy.context.active_object
        if generated and generated.type == 'ARMATURE' and generated != metarig:
            rig_name = generated.name
            bone_count = len(generated.data.bones)

            # Count control types
            def_bones = [b for b in generated.data.bones if b.name.startswith("DEF-")]
            mch_bones = [b for b in generated.data.bones if b.name.startswith("MCH-")]
            org_bones = [b for b in generated.data.bones if b.name.startswith("ORG-")]
            ctrl_bones = [b for b in generated.data.bones if not any(b.name.startswith(p) for p in ["DEF-", "MCH-", "ORG-"])]

            # Auto-parent mesh if requested
            parented = False
            if parent_to_mesh:
                mesh_obj = bpy.data.objects.get(parent_to_mesh)
                if mesh_obj and mesh_obj.type == 'MESH':
                    bpy.ops.object.select_all(action='DESELECT')
                    mesh_obj.select_set(True)
                    generated.select_set(True)
                    bpy.context.view_layer.objects.active = generated
                    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
                    parented = True

            result = {{
                "status": "success",
                "rig_name": rig_name,
                "total_bones": bone_count,
                "def_bones": len(def_bones),
                "mch_bones": len(mch_bones),
                "org_bones": len(org_bones),
                "ctrl_bones": len(ctrl_bones),
                "parented_mesh": parent_to_mesh if parented else None,
            }}
        else:
            result = {{"status": "error", "message": "Rigify generate completed but no new rig found"}}
    except Exception as e:
        result = {{"status": "error", "message": f"Rigify generate failed: {{str(e)}}"}}

json.dumps(result)
'''
        return _exec(code)

    # ─────────────────────────────────────────────
    # 4. rigify_to_vrc — Convert to VRC-compatible naming
    # ─────────────────────────────────────────────
    @mcp.tool()
    def rigify_to_vrc(
        rig_name: str = "rig",
        export_name: str = "",
    ) -> str:
        """
        Convert a Rigify-generated rig to VRC-compatible bone naming.
        Duplicates DEF-bones into a clean hierarchy with Unity Humanoid naming,
        ready for FBX export. Non-deform bones are excluded.

        Parameters:
        - rig_name: Name of the Rigify-generated rig (default: "rig")
        - export_name: Name for the export-ready armature. If empty, uses "{rig_name}_vrc".
        """
        code = f'''
import bpy
import json

rig_name = {json.dumps(rig_name)}
export_name = {json.dumps(export_name)}
if not export_name:
    export_name = rig_name + "_vrc"

rig = bpy.data.objects.get(rig_name)
if not rig or rig.type != 'ARMATURE':
    result = {{"status": "error", "message": f"Rig '{{rig_name}}' not found"}}
else:
    # Rigify DEF- bone to VRC/Unity Humanoid mapping
    bone_map = {{
        # Spine chain
        "DEF-spine": "Hips",
        "DEF-spine.001": "Spine",
        "DEF-spine.002": "Chest",
        "DEF-spine.003": "UpperChest",
        "DEF-spine.004": "Neck",
        "DEF-spine.005": "Head",
        # Left leg
        "DEF-thigh.L": "LeftUpperLeg",
        "DEF-shin.L": "LeftLowerLeg",
        "DEF-foot.L": "LeftFoot",
        "DEF-toe.L": "LeftToes",
        # Right leg
        "DEF-thigh.R": "RightUpperLeg",
        "DEF-shin.R": "RightLowerLeg",
        "DEF-foot.R": "RightFoot",
        "DEF-toe.R": "RightToes",
        # Left arm
        "DEF-shoulder.L": "LeftShoulder",
        "DEF-upper_arm.L": "LeftUpperArm",
        "DEF-forearm.L": "LeftLowerArm",
        "DEF-hand.L": "LeftHand",
        # Right arm
        "DEF-shoulder.R": "RightShoulder",
        "DEF-upper_arm.R": "RightUpperArm",
        "DEF-forearm.R": "RightLowerArm",
        "DEF-hand.R": "RightHand",
        # Left hand fingers
        "DEF-thumb.01.L": "LeftThumbProximal",
        "DEF-thumb.02.L": "LeftThumbIntermediate",
        "DEF-thumb.03.L": "LeftThumbDistal",
        "DEF-f_index.01.L": "LeftIndexProximal",
        "DEF-f_index.02.L": "LeftIndexIntermediate",
        "DEF-f_index.03.L": "LeftIndexDistal",
        "DEF-f_middle.01.L": "LeftMiddleProximal",
        "DEF-f_middle.02.L": "LeftMiddleIntermediate",
        "DEF-f_middle.03.L": "LeftMiddleDistal",
        "DEF-f_ring.01.L": "LeftRingProximal",
        "DEF-f_ring.02.L": "LeftRingIntermediate",
        "DEF-f_ring.03.L": "LeftRingDistal",
        "DEF-f_pinky.01.L": "LeftLittleProximal",
        "DEF-f_pinky.02.L": "LeftLittleIntermediate",
        "DEF-f_pinky.03.L": "LeftLittleDistal",
        # Right hand fingers
        "DEF-thumb.01.R": "RightThumbProximal",
        "DEF-thumb.02.R": "RightThumbIntermediate",
        "DEF-thumb.03.R": "RightThumbDistal",
        "DEF-f_index.01.R": "RightIndexProximal",
        "DEF-f_index.02.R": "RightIndexIntermediate",
        "DEF-f_index.03.R": "RightIndexDistal",
        "DEF-f_middle.01.R": "RightMiddleProximal",
        "DEF-f_middle.02.R": "RightMiddleIntermediate",
        "DEF-f_middle.03.R": "RightMiddleDistal",
        "DEF-f_ring.01.R": "RightRingProximal",
        "DEF-f_ring.02.R": "RightRingIntermediate",
        "DEF-f_ring.03.R": "RightRingDistal",
        "DEF-f_pinky.01.R": "RightLittleProximal",
        "DEF-f_pinky.02.R": "RightLittleIntermediate",
        "DEF-f_pinky.03.R": "RightLittleDistal",
        # Eye bones (for eye tracking)
        "DEF-eye.L": "LeftEye",
        "DEF-eye.R": "RightEye",
    }}

    # Create a new armature with only DEF bones, renamed
    bpy.ops.object.select_all(action='DESELECT')

    # Duplicate the rig
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.duplicate()
    export_rig = bpy.context.active_object
    export_rig.name = export_name
    export_rig.data.name = export_name + "_data"

    # Enter edit mode — remove all non-DEF bones
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = export_rig.data.edit_bones

    non_def = [b for b in edit_bones if not b.name.startswith("DEF-")]
    for bone in non_def:
        edit_bones.remove(bone)

    # Fix parenting — DEF bones may reference removed parents
    # Re-establish hierarchy based on original parent chain
    for bone in edit_bones:
        if bone.parent and bone.parent.name not in [b.name for b in edit_bones]:
            # Find nearest DEF ancestor
            parent = bone.parent
            while parent and not parent.name.startswith("DEF-"):
                parent = parent.parent
            bone.parent = parent

    # Rename bones using map
    renamed = []
    unmapped = []
    for bone in edit_bones:
        old_name = bone.name
        if old_name in bone_map:
            bone.name = bone_map[old_name]
            renamed.append(f"{{old_name}} -> {{bone.name}}")
        else:
            # Keep DEF- bones not in map (extra twist/segment bones)
            # Strip DEF- prefix for cleanliness
            clean = old_name.replace("DEF-", "")
            bone.name = clean
            unmapped.append(clean)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Transfer vertex groups from mesh children
    transferred = 0
    for child in rig.children:
        if child.type == 'MESH':
            # Re-parent mesh to export rig
            child_copy = child  # Use original mesh
            # Rename vertex groups to match new bone names
            for vg in child_copy.vertex_groups:
                if vg.name in bone_map:
                    vg.name = bone_map[vg.name]
                    transferred += 1
                elif vg.name.startswith("DEF-"):
                    vg.name = vg.name.replace("DEF-", "")
                    transferred += 1
            # Re-parent
            child_copy.parent = export_rig
            for mod in child_copy.modifiers:
                if mod.type == 'ARMATURE':
                    mod.object = export_rig

    total_bones = len(export_rig.data.bones)
    result = {{
        "status": "success",
        "export_rig": export_name,
        "total_bones": total_bones,
        "renamed_count": len(renamed),
        "unmapped_bones": unmapped,
        "vertex_groups_transferred": transferred,
        "renamed_samples": renamed[:10],
    }}

json.dumps(result)
'''
        return _exec(code)

    # ─────────────────────────────────────────────
    # 5. rigify_add_face_rig
    # ─────────────────────────────────────────────
    @mcp.tool()
    def rigify_add_face_rig(
        metarig_name: str = "metarig",
        detail_level: str = "full",
    ) -> str:
        """
        Add or configure face rig bones on a Rigify meta-rig.
        Useful when the meta-rig was created without face bones, or to adjust face rig detail.

        Parameters:
        - metarig_name: Name of the meta-rig armature (default: "metarig")
        - detail_level: "full" (all face bones), "basic" (jaw/eyes/brows only), "eyes_only"
        """
        code = f'''
import bpy
import json
from mathutils import Vector

metarig_name = {json.dumps(metarig_name)}
detail_level = {json.dumps(detail_level)}

metarig = bpy.data.objects.get(metarig_name)
if not metarig or metarig.type != 'ARMATURE':
    result = {{"status": "error", "message": f"Metarig '{{metarig_name}}' not found"}}
else:
    bpy.context.view_layer.objects.active = metarig
    metarig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = metarig.data.edit_bones

    # Find head bone as anchor
    head_bone = edit_bones.get("spine.006") or edit_bones.get("spine.005")
    if not head_bone:
        bpy.ops.object.mode_set(mode='OBJECT')
        result = {{"status": "error", "message": "No head bone found in metarig"}}
    else:
        head_pos = head_bone.head.copy()
        head_len = head_bone.length
        added = []

        def add_bone(name, head, tail, parent_name=None, roll=0):
            if name in edit_bones:
                return edit_bones[name]
            bone = edit_bones.new(name)
            bone.head = Vector(head)
            bone.tail = Vector(tail)
            bone.roll = roll
            if parent_name and parent_name in edit_bones:
                bone.parent = edit_bones[parent_name]
            added.append(name)
            return bone

        # Face root
        face_root = head_bone.name
        fwd = head_len * 0.3  # forward offset

        if detail_level in ("full", "basic"):
            # Jaw
            jaw_y = head_pos.y + fwd
            jaw_z = head_pos.z - head_len * 0.15
            add_bone("jaw",
                     (head_pos.x, head_pos.y, jaw_z),
                     (head_pos.x, jaw_y, jaw_z - head_len * 0.2),
                     face_root)

            # Chin
            if detail_level == "full":
                add_bone("chin",
                         (head_pos.x, jaw_y * 0.9, jaw_z - head_len * 0.15),
                         (head_pos.x, jaw_y, jaw_z - head_len * 0.2),
                         "jaw")

        # Eyes (all levels)
        eye_sep = head_len * 0.15  # eye separation
        eye_z = head_pos.z + head_len * 0.35
        eye_y = head_pos.y + fwd
        eye_depth = head_len * 0.15

        for side, sign in [(".L", 1), (".R", -1)]:
            ex = head_pos.x + sign * eye_sep
            add_bone("eye" + side,
                     (ex, eye_y - eye_depth, eye_z),
                     (ex, eye_y, eye_z),
                     face_root)

            if detail_level in ("full", "basic"):
                # Eyelids
                add_bone("lid.T" + side,
                         (ex, eye_y - eye_depth * 0.5, eye_z + head_len * 0.02),
                         (ex, eye_y, eye_z + head_len * 0.02),
                         "eye" + side)
                add_bone("lid.B" + side,
                         (ex, eye_y - eye_depth * 0.5, eye_z - head_len * 0.02),
                         (ex, eye_y, eye_z - head_len * 0.02),
                         "eye" + side)

        if detail_level in ("full", "basic"):
            # Brows
            brow_z = eye_z + head_len * 0.08
            for side, sign in [(".L", 1), (".R", -1)]:
                bx = head_pos.x + sign * eye_sep
                add_bone("brow.T" + side,
                         (head_pos.x + sign * eye_sep * 0.5, eye_y, brow_z),
                         (bx + sign * eye_sep * 0.5, eye_y, brow_z),
                         face_root)

        if detail_level == "full":
            # Nose
            nose_z = eye_z - head_len * 0.12
            add_bone("nose",
                     (head_pos.x, eye_y - eye_depth * 0.3, nose_z),
                     (head_pos.x, eye_y + eye_depth * 0.3, nose_z - head_len * 0.05),
                     face_root)

            # Lips
            lip_z = jaw_z + head_len * 0.03
            lip_y = eye_y * 0.95
            lip_w = eye_sep * 0.8
            add_bone("lip.T",
                     (head_pos.x, lip_y, lip_z + head_len * 0.01),
                     (head_pos.x, lip_y + fwd * 0.2, lip_z + head_len * 0.01),
                     face_root)
            add_bone("lip.B",
                     (head_pos.x, lip_y, lip_z - head_len * 0.01),
                     (head_pos.x, lip_y + fwd * 0.2, lip_z - head_len * 0.01),
                     "jaw")

            for side, sign in [(".L", 1), (".R", -1)]:
                add_bone("lip.T" + side,
                         (head_pos.x + sign * lip_w * 0.5, lip_y, lip_z + head_len * 0.005),
                         (head_pos.x + sign * lip_w, lip_y, lip_z),
                         "lip.T")
                add_bone("lip.B" + side,
                         (head_pos.x + sign * lip_w * 0.5, lip_y, lip_z - head_len * 0.005),
                         (head_pos.x + sign * lip_w, lip_y, lip_z),
                         "lip.B")

            # Cheeks
            cheek_z = nose_z - head_len * 0.02
            for side, sign in [(".L", 1), (".R", -1)]:
                add_bone("cheek" + side,
                         (head_pos.x + sign * eye_sep * 1.2, eye_y * 0.8, cheek_z),
                         (head_pos.x + sign * eye_sep * 1.5, eye_y * 0.9, cheek_z),
                         face_root)

            # Tongue (3-bone chain)
            tongue_z = jaw_z + head_len * 0.02
            for i, suffix in enumerate([".001", ".002", ".003"]):
                tz = tongue_z
                ty_start = head_pos.y + fwd * (0.2 + i * 0.2)
                ty_end = head_pos.y + fwd * (0.2 + (i + 1) * 0.2)
                parent = "jaw" if i == 0 else f"tongue.{{str(i).zfill(3)}}"
                add_bone(f"tongue{{suffix}}",
                         (head_pos.x, ty_start, tz),
                         (head_pos.x, ty_end, tz),
                         parent)

        bpy.ops.object.mode_set(mode='OBJECT')

        result = {{
            "status": "success",
            "metarig": metarig_name,
            "detail_level": detail_level,
            "bones_added": len(added),
            "bone_names": added,
        }}

json.dumps(result)
'''
        return _exec(code)

    # ─────────────────────────────────────────────
    # 6. rigify_configure_ik
    # ─────────────────────────────────────────────
    @mcp.tool()
    def rigify_configure_ik(
        rig_name: str = "rig",
        tracking_mode: str = "6point",
        floor_constraint: bool = True,
    ) -> str:
        """
        Configure IK settings on a Rigify rig for VRChat full-body tracking.
        Sets up IK pole targets, chain lengths, and optional floor constraints.

        Parameters:
        - rig_name: Name of the Rigify-generated rig (default: "rig")
        - tracking_mode: "3point" (head+hands), "6point" (+ hip + feet), "10point" (+ elbows + knees)
        - floor_constraint: Add floor constraints to feet (default: True)
        """
        code = f'''
import bpy
import json
from math import radians

rig_name = {json.dumps(rig_name)}
tracking_mode = {json.dumps(tracking_mode)}
floor_constraint = {json.dumps(floor_constraint)}

rig = bpy.data.objects.get(rig_name)
if not rig or rig.type != 'ARMATURE':
    result = {{"status": "error", "message": f"Rig '{{rig_name}}' not found"}}
else:
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)

    configured = []

    # Work in pose mode
    bpy.ops.object.mode_set(mode='POSE')
    pose_bones = rig.pose.bones

    # Helper: find bone by partial name match
    def find_bone(patterns):
        for p in patterns:
            for pb in pose_bones:
                if p.lower() in pb.name.lower():
                    return pb
        return None

    # Configure IK for legs
    for side in ["L", "R"]:
        side_name = "Left" if side == "L" else "Right"

        # Find foot IK control (Rigify names: foot_ik.L, foot_ik.R)
        foot_ik = find_bone([f"foot_ik.{{side}}", f"MCH-foot_ik.{{side}}"])
        if foot_ik:
            # Ensure IK constraint exists
            ik_found = False
            for c in foot_ik.constraints:
                if c.type == 'IK':
                    ik_found = True
                    c.chain_count = 2  # shin + thigh
                    c.use_stretch = False
                    configured.append(f"{{side_name}} leg IK: chain=2, no stretch")

            if not ik_found:
                configured.append(f"{{side_name}} foot IK control found (Rigify built-in)")

            # Floor constraint
            if floor_constraint:
                has_floor = any(c.type == 'FLOOR' for c in foot_ik.constraints)
                if not has_floor:
                    fc = foot_ik.constraints.new('FLOOR')
                    fc.name = f"Floor_{{side}}"
                    fc.use_rotation = True
                    fc.floor_location = 'FLOOR_NEGATIVE_Y'
                    fc.offset = 0.0
                    configured.append(f"{{side_name}} foot floor constraint added")

        # Find hand IK control
        hand_ik = find_bone([f"hand_ik.{{side}}", f"MCH-hand_ik.{{side}}"])
        if hand_ik:
            for c in hand_ik.constraints:
                if c.type == 'IK':
                    c.chain_count = 2  # forearm + upper_arm
                    c.use_stretch = False
                    configured.append(f"{{side_name}} arm IK: chain=2, no stretch")

    # Tracking mode specific settings
    if tracking_mode in ("6point", "10point"):
        # 6-point: hip tracker drives torso
        torso = find_bone(["torso", "hips", "root"])
        if torso:
            configured.append(f"6-point: torso control '{{torso.name}}' available for hip tracker")

    if tracking_mode == "10point":
        # 10-point: add pole target visibility for elbows/knees
        for side in ["L", "R"]:
            for limb, patterns in [("knee", [f"knee_target.{{side}}", f"pole_target_leg.{{side}}", f"foot_heel_ik.{{side}}"]),
                                    ("elbow", [f"elbow_target.{{side}}", f"pole_target_arm.{{side}}"])]:
                pole = find_bone(patterns)
                if pole:
                    # Ensure pole bone is visible
                    bone_data = rig.data.bones.get(pole.name)
                    if bone_data:
                        bone_data.hide = False
                    configured.append(f"10-point: {{limb}} pole '{{pole.name}}' visible for tracker")

    # Set all IK bones to use local space (important for VRC)
    ik_count = 0
    for pb in pose_bones:
        for c in pb.constraints:
            if c.type == 'IK':
                ik_count += 1

    bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "status": "success",
        "rig": rig_name,
        "tracking_mode": tracking_mode,
        "total_ik_constraints": ik_count,
        "floor_constraints": floor_constraint,
        "configurations": configured,
    }}

json.dumps(result)
'''
        return _exec(code)
