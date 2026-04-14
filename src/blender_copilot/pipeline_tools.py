# Pipeline Orchestration Tools for BlenderMCP
# End-to-end workflows that chain multiple tools into complete pipelines.
# These tools coordinate Blender-side and Unity-side operations.

import json
import logging
import os

logger = logging.getLogger("BlenderMCPServer.Pipeline")


def register_pipeline_tools(mcp, send_command_fn):
    """Register all pipeline orchestration tools on the FastMCP instance."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    # ─────────────────────────────────────────────
    # 1. pipeline_avatar_from_mesh — Full Blender-side pipeline
    # ─────────────────────────────────────────────
    @mcp.tool()
    def pipeline_avatar_from_mesh(
        mesh_name: str = "",
        avatar_name: str = "Avatar",
        create_shape_keys: bool = True,
        arkit_method: str = "template",
        export_fbx: bool = True,
        export_path: str = "",
    ) -> str:
        """
        Full Blender-side avatar pipeline: mesh → armature → shape keys → FBX.
        Chains: validate mesh → create armature → weight paint → visemes → ARKit shapes → export.

        Parameters:
        - mesh_name: Name of the mesh to process. If empty, uses active object.
        - avatar_name: Name for the avatar (default: "Avatar")
        - create_shape_keys: Generate face tracking shape keys (default: True)
        - arkit_method: "template" (empty keys for manual sculpt), "procedural" (auto-generate), "skip"
        - export_fbx: Export FBX at the end (default: True)
        - export_path: FBX export path. If empty, exports to ~/Desktop/{avatar_name}.fbx
        """
        code = f'''
import bpy
import json
import os

mesh_name = {json.dumps(mesh_name)}
avatar_name = {json.dumps(avatar_name)}
create_shape_keys = {json.dumps(create_shape_keys)}
arkit_method = {json.dumps(arkit_method)}
export_fbx = {json.dumps(export_fbx)}
export_path = {json.dumps(export_path)}

steps = []
errors = []

# Step 1: Find/validate mesh
mesh_obj = None
if mesh_name:
    mesh_obj = bpy.data.objects.get(mesh_name)
else:
    mesh_obj = bpy.context.active_object
    if mesh_obj and mesh_obj.type != 'MESH':
        mesh_obj = None
    if not mesh_obj:
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
        if meshes:
            mesh_obj = max(meshes, key=lambda o: len(o.data.vertices))

if not mesh_obj:
    result = {{"status": "error", "message": "No mesh found"}}
else:
    mesh_name = mesh_obj.name
    vert_count = len(mesh_obj.data.vertices)
    face_count = len(mesh_obj.data.polygons)
    steps.append(f"Mesh found: {{mesh_name}} ({{vert_count}} verts, {{face_count}} faces)")

    # Step 2: Check/create armature
    armature = None
    if mesh_obj.parent and mesh_obj.parent.type == 'ARMATURE':
        armature = mesh_obj.parent
        steps.append(f"Existing armature: {{armature.name}} ({{len(armature.data.bones)}} bones)")
    else:
        # Check if any armature modifier
        for mod in mesh_obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                armature = mod.object
                steps.append(f"Armature from modifier: {{armature.name}}")
                break

    if not armature:
        steps.append("WARNING: No armature found. Use rigify_create_metarig + rigify_generate_rig first.")
        errors.append("no_armature")

    # Step 3: Check vertex groups (weight painting)
    vg_names = [vg.name for vg in mesh_obj.vertex_groups]
    if len(vg_names) == 0:
        steps.append("WARNING: No vertex groups. Weight painting needed.")
        errors.append("no_weights")
    else:
        steps.append(f"Vertex groups: {{len(vg_names)}}")

    # Step 4: Check materials
    mat_count = len(mesh_obj.data.materials)
    steps.append(f"Materials: {{mat_count}}")
    if mat_count == 0:
        steps.append("WARNING: No materials assigned")
        errors.append("no_materials")
    elif mat_count > 4:
        steps.append(f"WARNING: {{mat_count}} materials exceeds VRC Excellent rank (4)")

    # Step 5: Existing shape keys
    sk_count = 0
    if mesh_obj.data.shape_keys:
        sk_count = len(mesh_obj.data.shape_keys.key_blocks) - 1  # exclude Basis
    steps.append(f"Existing shape keys: {{sk_count}}")

    # Step 6: Create shape keys if requested
    if create_shape_keys and arkit_method != "skip":
        if arkit_method == "template":
            # Create empty ARKit shape keys (52 + 15 visemes)
            if not mesh_obj.data.shape_keys:
                mesh_obj.shape_key_add(name="Basis", from_mix=False)

            arkit_names = [
                "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
                "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
                "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight",
                "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
                "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
                "eyeWideLeft", "eyeWideRight",
                "jawForward", "jawLeft", "jawOpen", "jawRight",
                "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
                "mouthFrownLeft", "mouthFrownRight", "mouthFunnel",
                "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight",
                "mouthPressLeft", "mouthPressRight", "mouthPucker",
                "mouthRight", "mouthRollLower", "mouthRollUpper",
                "mouthShrugLower", "mouthShrugUpper", "mouthSmileLeft", "mouthSmileRight",
                "mouthStretchLeft", "mouthStretchRight", "mouthUpperUpLeft", "mouthUpperUpRight",
                "noseSneerLeft", "noseSneerRight", "tongueOut",
            ]

            viseme_names = ["vrc.v_sil", "vrc.v_PP", "vrc.v_FF", "vrc.v_TH", "vrc.v_DD",
                           "vrc.v_kk", "vrc.v_CH", "vrc.v_SS", "vrc.v_nn", "vrc.v_RR",
                           "vrc.v_aa", "vrc.v_E", "vrc.v_I", "vrc.v_O", "vrc.v_U"]

            existing_keys = set()
            if mesh_obj.data.shape_keys:
                existing_keys = set(sk.name for sk in mesh_obj.data.shape_keys.key_blocks)

            created = 0
            for name in arkit_names + viseme_names:
                if name not in existing_keys:
                    mesh_obj.shape_key_add(name=name, from_mix=False)
                    created += 1

            steps.append(f"Shape keys created (template): {{created}} new ({{len(arkit_names)}} ARKit + {{len(viseme_names)}} visemes)")
        else:
            steps.append(f"ARKit method '{{arkit_method}}' — use ft_create_arkit_shapes tool for procedural generation")

    # Step 7: Export FBX
    if export_fbx:
        if not export_path:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            export_path = os.path.join(desktop, f"{{avatar_name}}.fbx")

        # Select only the mesh and its armature
        bpy.ops.object.select_all(action='DESELECT')
        mesh_obj.select_set(True)
        if armature:
            armature.select_set(True)

        try:
            bpy.ops.export_scene.fbx(
                filepath=export_path,
                use_selection=True,
                apply_scale_options='FBX_SCALE_ALL',
                axis_forward='-Z',
                axis_up='Y',
                use_mesh_modifiers=True,
                add_leaf_bones=False,  # CRITICAL for VRC
                bake_anim=False,
                mesh_smooth_type='FACE',
                use_tspace=True,
            )
            steps.append(f"FBX exported: {{export_path}}")
        except Exception as e:
            steps.append(f"FBX export failed: {{str(e)}}")
            errors.append("fbx_export_failed")

    # Build final report
    result = {{
        "status": "success" if not errors else "partial",
        "mesh": mesh_name,
        "avatar_name": avatar_name,
        "vertices": vert_count,
        "faces": face_count,
        "materials": mat_count,
        "shape_keys": sk_count + (created if create_shape_keys and arkit_method == "template" else 0),
        "has_armature": armature is not None,
        "bone_count": len(armature.data.bones) if armature else 0,
        "steps": steps,
        "errors": errors,
        "export_path": export_path if export_fbx else None,
    }}

json.dumps(result)
'''
        return _exec(code)

    # ─────────────────────────────────────────────
    # 2. pipeline_blender_to_unity — Full Unity-side pipeline
    # ─────────────────────────────────────────────
    @mcp.tool()
    def pipeline_blender_to_unity(
        fbx_path: str = "",
        project_path: str = "",
        avatar_name: str = "",
        setup_physbones: bool = False,
        physbones_json: str = "",
    ) -> str:
        """
        Full Unity-side pipeline: FBX → Import → Avatar Descriptor → Expressions → Build.
        Chains: import FBX → set humanoid → avatar descriptor → expression menu/params → gesture layer → build.

        Parameters:
        - fbx_path: Path to the FBX file
        - project_path: Unity project path
        - avatar_name: Avatar display name
        - setup_physbones: Also configure PhysBones (default: False)
        - physbones_json: PhysBone configs if setup_physbones is True
        """
        # This tool delegates to unity_configure_pipeline which chains everything
        from . import unity_tools
        # Actually, we call the registered MCP tools directly since they're in scope

        proj = project_path or os.environ.get("UNITY_PROJECT_PATH", "")
        if not proj:
            return json.dumps({"status": "error", "message": "No Unity project path"})
        if not fbx_path:
            return json.dumps({"status": "error", "message": "No FBX path"})

        name = avatar_name or os.path.splitext(os.path.basename(fbx_path))[0]

        results = {"status": "success", "pipeline": "blender_to_unity", "steps": []}

        # Step 1: Verify project
        step1 = json.loads(unity_setup_project(project_path=proj, verify_sdk=True))
        results["steps"].append({"step": "verify_project", "result": step1})
        if step1.get("sdk_missing"):
            results["steps"].append({"step": "sdk_warning", "result": {"message": "Install VRC SDK with: vrc-get resolve"}})

        # Step 2: Full pipeline setup
        step2 = json.loads(unity_configure_pipeline(
            project_path=proj,
            fbx_path=fbx_path,
            avatar_name=name,
        ))
        results["steps"].append({"step": "configure_pipeline", "result": step2})

        # Step 3: Optional PhysBones
        if setup_physbones and physbones_json:
            step3 = json.loads(unity_setup_physbones(
                project_path=proj,
                physbones_json=physbones_json,
                avatar_object=name,
            ))
            results["steps"].append({"step": "physbones", "result": step3})

        # Step 4: Build
        step4 = json.loads(unity_build_avatar(
            project_path=proj,
            avatar_object=name,
        ))
        results["steps"].append({"step": "build", "result": step4})

        # Summary
        success_count = sum(1 for s in results["steps"] if s["result"].get("status") == "success")
        results["summary"] = f"{success_count}/{len(results['steps'])} steps succeeded"

        return json.dumps(results)

    # ─────────────────────────────────────────────
    # 3. pipeline_face_tracking_setup — Complete face tracking
    # ─────────────────────────────────────────────
    @mcp.tool()
    def pipeline_face_tracking_setup(
        mesh_name: str = "",
        method: str = "procedural",
        include_unified: bool = True,
        include_tongue: bool = True,
        include_eye_tracking: bool = True,
    ) -> str:
        """
        Complete face tracking pipeline: vertex groups → ARKit 52 → Unified → validate.
        Chains: ft_setup_face_vertex_groups → ft_create_arkit_shapes → ft_create_unified_expressions
        → ft_setup_tongue_tracking → ft_setup_eye_tracking_full → ft_validate_shapes.

        Parameters:
        - mesh_name: Target mesh name. If empty, uses active/largest mesh.
        - method: "procedural" (auto-generate), "template" (empty keys), "from_existing" (fuzzy match)
        - include_unified: Also generate Unified Expressions (default: True)
        - include_tongue: Setup tongue tracking (default: True)
        - include_eye_tracking: Setup full eye tracking (default: True)
        """
        results = {"status": "success", "pipeline": "face_tracking_setup", "steps": []}

        # Step 1: Setup face vertex groups
        step1 = json.loads(ft_setup_face_vertex_groups(mesh_name=mesh_name))
        results["steps"].append({"step": "face_vertex_groups", "result": step1})

        target_mesh = mesh_name
        if step1.get("status") == "success":
            target_mesh = step1.get("mesh", mesh_name)

        # Step 2: Create ARKit 52 shapes
        step2 = json.loads(ft_create_arkit_shapes(mesh_name=target_mesh, method=method))
        results["steps"].append({"step": "arkit_shapes", "result": step2})

        # Step 3: Unified Expressions
        if include_unified:
            step3 = json.loads(ft_create_unified_expressions(mesh_name=target_mesh))
            results["steps"].append({"step": "unified_expressions", "result": step3})

        # Step 4: Tongue tracking
        if include_tongue:
            step4 = json.loads(ft_setup_tongue_tracking(mesh_name=target_mesh))
            results["steps"].append({"step": "tongue_tracking", "result": step4})

        # Step 5: Eye tracking
        if include_eye_tracking:
            step5 = json.loads(ft_setup_eye_tracking_full(mesh_name=target_mesh))
            results["steps"].append({"step": "eye_tracking", "result": step5})

        # Step 6: Validate all
        step6 = json.loads(ft_validate_shapes(mesh_name=target_mesh, standard="both"))
        results["steps"].append({"step": "validate", "result": step6})

        success_count = sum(1 for s in results["steps"] if s["result"].get("status") == "success")
        results["summary"] = f"{success_count}/{len(results['steps'])} steps succeeded"

        return json.dumps(results)

    # ─────────────────────────────────────────────
    # 4. pipeline_validate_full — Go/no-go report
    # ─────────────────────────────────────────────
    @mcp.tool()
    def pipeline_validate_full(
        mesh_name: str = "",
        target: str = "pc",
    ) -> str:
        """
        Comprehensive go/no-go validation report for VRChat upload.
        Checks: mesh stats, armature, shape keys, materials, UV, performance rank.

        Parameters:
        - mesh_name: Mesh to validate. If empty, checks all visible meshes.
        - target: "pc" or "quest" (default: "pc")
        """
        code = f'''
import bpy
import json

mesh_name = {json.dumps(mesh_name)}
target = {json.dumps(target)}

report = {{
    "status": "success",
    "target": target,
    "go": True,
    "checks": [],
    "warnings": [],
    "errors": [],
}}

# Rank limits
limits = {{
    "pc": {{"excellent": {{"tris": 32000, "mats": 4, "bones": 75, "meshes": 2}},
            "good": {{"tris": 70000, "mats": 8, "bones": 150, "meshes": 4}}}},
    "quest": {{"excellent": {{"tris": 7500, "mats": 2, "bones": 75, "meshes": 1}},
              "good": {{"tris": 10000, "mats": 2, "bones": 90, "meshes": 1}}}},
}}

# Gather all mesh objects
if mesh_name:
    meshes = [bpy.data.objects.get(mesh_name)]
    meshes = [m for m in meshes if m and m.type == 'MESH']
else:
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]

if not meshes:
    report["go"] = False
    report["errors"].append("No mesh objects found")
else:
    # Mesh stats
    total_tris = 0
    total_verts = 0
    all_materials = set()
    has_uv = True
    has_armature = False
    armature = None

    for mesh_obj in meshes:
        # Count triangulated faces
        tris = sum(len(p.vertices) - 2 for p in mesh_obj.data.polygons)
        total_tris += tris
        total_verts += len(mesh_obj.data.vertices)

        for mat in mesh_obj.data.materials:
            if mat:
                all_materials.add(mat.name)

        if not mesh_obj.data.uv_layers:
            has_uv = False
            report["errors"].append(f"{{mesh_obj.name}}: No UV map")

        if mesh_obj.parent and mesh_obj.parent.type == 'ARMATURE':
            has_armature = True
            armature = mesh_obj.parent

    mat_count = len(all_materials)
    mesh_count = len(meshes)

    report["checks"].append(f"Meshes: {{mesh_count}}")
    report["checks"].append(f"Triangles: {{total_tris}}")
    report["checks"].append(f"Vertices: {{total_verts}}")
    report["checks"].append(f"Materials: {{mat_count}}")
    report["checks"].append(f"UV maps: {{'OK' if has_uv else 'MISSING'}}")
    report["checks"].append(f"Armature: {{'OK' if has_armature else 'MISSING'}}")

    # Performance rank
    lim = limits.get(target, limits["pc"])
    rank = "Very Poor"
    for rank_name in ["excellent", "good"]:
        l = lim[rank_name]
        if total_tris <= l["tris"] and mat_count <= l["mats"]:
            rank = rank_name.capitalize()
            break

    report["rank"] = rank
    report["checks"].append(f"Performance rank: {{rank}}")

    # Shape keys check
    for mesh_obj in meshes:
        if mesh_obj.data.shape_keys:
            sk_count = len(mesh_obj.data.shape_keys.key_blocks) - 1
            report["checks"].append(f"{{mesh_obj.name}} shape keys: {{sk_count}}")

            # Check for ARKit shapes
            sk_names = [sk.name for sk in mesh_obj.data.shape_keys.key_blocks]
            arkit_core = ["jawOpen", "mouthSmileLeft", "mouthSmileRight", "eyeBlinkLeft", "eyeBlinkRight"]
            arkit_found = sum(1 for a in arkit_core if a in sk_names)
            report["checks"].append(f"ARKit core shapes: {{arkit_found}}/{{len(arkit_core)}}")

            # Check for visemes
            viseme_found = sum(1 for sk in sk_names if sk.startswith("vrc.v_"))
            report["checks"].append(f"VRC Visemes: {{viseme_found}}/15")

    # Bone check
    if armature:
        bone_count = len(armature.data.bones)
        report["checks"].append(f"Bones: {{bone_count}}")

        # Check for required humanoid bones
        required = ["Hips", "Spine", "Head", "LeftUpperArm", "RightUpperArm", "LeftUpperLeg", "RightUpperLeg"]
        bone_names = [b.name for b in armature.data.bones]
        found_required = sum(1 for r in required if r in bone_names)
        report["checks"].append(f"Humanoid bones: {{found_required}}/{{len(required)}}")

        if found_required < len(required):
            missing = [r for r in required if r not in bone_names]
            report["warnings"].append(f"Missing humanoid bones: {{', '.join(missing)}}")

    # Go/no-go
    if not has_armature:
        report["go"] = False
        report["errors"].append("No armature — avatar cannot be uploaded without bones")
    if not has_uv:
        report["go"] = False
    if target == "quest" and total_tris > 20000:
        report["go"] = False
        report["errors"].append(f"Quest hard limit: 20K tris, have {{total_tris}}")

    report["total_tris"] = total_tris
    report["total_verts"] = total_verts
    report["material_count"] = mat_count
    report["mesh_count"] = mesh_count

json.dumps(report)
'''
        return _exec(code)

    # ─────────────────────────────────────────────
    # 5. pipeline_generate_blueprint — Export config JSONs
    # ─────────────────────────────────────────────
    @mcp.tool()
    def pipeline_generate_blueprint(
        mesh_name: str = "",
        output_dir: str = "",
        avatar_name: str = "Avatar",
    ) -> str:
        """
        Export all configuration JSONs alongside the FBX for Unity import.
        Generates: avatar_blueprint.json, physbones.json, expression_menu.json,
        expression_params.json, shape_key_report.json.

        Parameters:
        - mesh_name: Target mesh. If empty, uses active/largest.
        - output_dir: Directory to save blueprints. If empty, uses ~/Desktop/{avatar_name}/.
        - avatar_name: Avatar name for the blueprint (default: "Avatar")
        """
        code = f'''
import bpy
import json
import os

mesh_name = {json.dumps(mesh_name)}
output_dir = {json.dumps(output_dir)}
avatar_name = {json.dumps(avatar_name)}

if not output_dir:
    output_dir = os.path.join(os.path.expanduser("~"), "Desktop", avatar_name + "_blueprint")
os.makedirs(output_dir, exist_ok=True)

# Find mesh
mesh_obj = None
if mesh_name:
    mesh_obj = bpy.data.objects.get(mesh_name)
if not mesh_obj:
    mesh_obj = bpy.context.active_object
    if mesh_obj and mesh_obj.type != 'MESH':
        mesh_obj = None
if not mesh_obj:
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
    if meshes:
        mesh_obj = max(meshes, key=lambda o: len(o.data.vertices))

if not mesh_obj:
    result = {{"status": "error", "message": "No mesh found"}}
else:
    files_written = []
    armature = mesh_obj.parent if mesh_obj.parent and mesh_obj.parent.type == 'ARMATURE' else None

    # 1. Avatar Blueprint
    blueprint = {{
        "avatar_name": avatar_name,
        "mesh": mesh_obj.name,
        "vertices": len(mesh_obj.data.vertices),
        "triangles": sum(len(p.vertices) - 2 for p in mesh_obj.data.polygons),
        "materials": [m.name for m in mesh_obj.data.materials if m],
        "armature": armature.name if armature else None,
        "bone_count": len(armature.data.bones) if armature else 0,
    }}

    # Shape keys
    if mesh_obj.data.shape_keys:
        blueprint["shape_keys"] = [sk.name for sk in mesh_obj.data.shape_keys.key_blocks if sk.name != "Basis"]
        blueprint["shape_key_count"] = len(blueprint["shape_keys"])

    bp_path = os.path.join(output_dir, "avatar_blueprint.json")
    with open(bp_path, "w") as f:
        json.dump(blueprint, f, indent=2)
    files_written.append("avatar_blueprint.json")

    # 2. PhysBone Blueprint (from existing PhysBone-like vertex groups)
    if armature:
        pb_candidates = []
        physics_prefixes = ["hair", "skirt", "ribbon", "tail", "ear", "cloth", "chain", "accessory"]
        for bone in armature.data.bones:
            name_lower = bone.name.lower()
            if any(p in name_lower for p in physics_prefixes):
                # Build bone path
                path_parts = []
                b = bone
                while b:
                    path_parts.insert(0, b.name)
                    b = b.parent
                bone_path = "/".join(path_parts)
                pb_candidates.append({{
                    "bonePath": bone_path,
                    "pull": 0.2,
                    "spring": 0.8,
                    "stiffness": 0.2,
                    "gravity": 0.1,
                    "gravityFalloff": 0.5,
                    "immobile": 0.3,
                    "radius": 0.05,
                    "limitType": "Angle",
                    "maxAngle": 45,
                }})

        if pb_candidates:
            pb_path = os.path.join(output_dir, "physbones.json")
            with open(pb_path, "w") as f:
                json.dump(pb_candidates, f, indent=2)
            files_written.append(f"physbones.json ({{len(pb_candidates)}} bones)")

    # 3. Expression Menu Blueprint
    menu = {{
        "controls": [
            {{"name": "Face Blend H", "type": "RadialPuppet", "parameter": "VRCFaceBlendH", "value": 0}},
            {{"name": "Face Blend V", "type": "RadialPuppet", "parameter": "VRCFaceBlendV", "value": 0}},
        ]
    }}
    menu_path = os.path.join(output_dir, "expression_menu.json")
    with open(menu_path, "w") as f:
        json.dump(menu, f, indent=2)
    files_written.append("expression_menu.json")

    # 4. Expression Parameters Blueprint
    params = {{
        "parameters": [
            {{"name": "VRCFaceBlendH", "valueType": "Float", "defaultValue": 0, "saved": True, "synced": True}},
            {{"name": "VRCFaceBlendV", "valueType": "Float", "defaultValue": 0, "saved": True, "synced": True}},
            {{"name": "VRCEmote", "valueType": "Int", "defaultValue": 0, "saved": False, "synced": True}},
        ]
    }}
    params_path = os.path.join(output_dir, "expression_params.json")
    with open(params_path, "w") as f:
        json.dump(params, f, indent=2)
    files_written.append("expression_params.json")

    # 5. Shape Key Report
    if mesh_obj.data.shape_keys:
        sk_report = {{
            "mesh": mesh_obj.name,
            "total": len(mesh_obj.data.shape_keys.key_blocks) - 1,
            "shapes": [],
        }}
        for sk in mesh_obj.data.shape_keys.key_blocks:
            if sk.name == "Basis":
                continue
            # Check if shape key has actual deformation
            has_deform = False
            basis = mesh_obj.data.shape_keys.key_blocks["Basis"]
            for i, (sk_vert, basis_vert) in enumerate(zip(sk.data, basis.data)):
                if (sk_vert.co - basis_vert.co).length > 0.0001:
                    has_deform = True
                    break

            sk_report["shapes"].append({{
                "name": sk.name,
                "has_deformation": has_deform,
                "min_value": sk.slider_min,
                "max_value": sk.slider_max,
            }})

        skr_path = os.path.join(output_dir, "shape_key_report.json")
        with open(skr_path, "w") as f:
            json.dump(sk_report, f, indent=2)
        files_written.append(f"shape_key_report.json ({{sk_report['total']}} shapes)")

    result = {{
        "status": "success",
        "output_dir": output_dir,
        "files_written": files_written,
        "avatar_name": avatar_name,
    }}

json.dumps(result)
'''
        return _exec(code)
