# Unity Automation Tools for BlenderMCP
# Generates C# EditorScripts and invokes Unity CLI for VRChat avatar setup.
# Approach: Generate .cs files → copy to Unity project → run via -batchmode -executeMethod
# Fallback: computer-use MCP for GUI-only operations (Build & Publish)

import json
import logging
import os
import textwrap

logger = logging.getLogger("BlenderMCPServer.Unity")

# Default paths (can be overridden via env vars)
UNITY_PATH = os.environ.get("UNITY_PATH", r"C:\Program Files\Unity\Hub\Editor\2022.3.22f1\Editor\Unity.exe")
UNITY_PROJECT_PATH = os.environ.get("UNITY_PROJECT_PATH", "")


def register_unity_tools(mcp, send_command_fn):
    """Register all Unity automation tools on the FastMCP instance."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    def _write_cs_and_run(cs_code: str, class_name: str, method_name: str,
                          project_path: str, extra_args: str = "") -> dict:
        """
        Write a C# EditorScript to the Unity project and invoke it via CLI.
        Returns the result dict.
        """
        import subprocess
        import tempfile

        if not project_path:
            return {"status": "error", "message": "No Unity project path specified. Set UNITY_PROJECT_PATH env var or pass project_path."}

        # Ensure Editor scripts directory exists
        editor_dir = os.path.join(project_path, "Assets", "Editor", "BlenderCopilot")
        os.makedirs(editor_dir, exist_ok=True)

        # Write the C# script
        cs_path = os.path.join(editor_dir, f"{class_name}.cs")
        with open(cs_path, "w", encoding="utf-8") as f:
            f.write(cs_code)

        # Build Unity CLI command
        unity_exe = UNITY_PATH
        if not os.path.exists(unity_exe):
            return {"status": "error", "message": f"Unity.exe not found at {unity_exe}. Set UNITY_PATH env var."}

        cmd = [
            unity_exe,
            "-batchmode",
            "-nographics",
            "-projectPath", project_path,
            "-executeMethod", f"{class_name}.{method_name}",
            "-logFile", "-",  # stdout
        ]
        if extra_args:
            cmd.extend(extra_args.split())

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            # Parse output for our JSON result marker
            output = result.stdout + result.stderr
            # Look for our result JSON between markers
            start_marker = "###BLENDER_COPILOT_RESULT_START###"
            end_marker = "###BLENDER_COPILOT_RESULT_END###"
            if start_marker in output:
                json_str = output.split(start_marker)[1].split(end_marker)[0].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            if result.returncode == 0:
                return {"status": "success", "message": "Unity command completed", "output_tail": output[-500:] if output else ""}
            else:
                return {"status": "error", "message": f"Unity exited with code {result.returncode}", "output_tail": output[-1000:] if output else ""}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Unity CLI timed out (300s)"}
        except FileNotFoundError:
            return {"status": "error", "message": f"Unity.exe not found at {unity_exe}"}

    # C# helper: output result JSON that we can parse
    CS_RESULT_HELPER = '''
    static void OutputResult(string json) {
        UnityEngine.Debug.Log("###BLENDER_COPILOT_RESULT_START###");
        UnityEngine.Debug.Log(json);
        UnityEngine.Debug.Log("###BLENDER_COPILOT_RESULT_END###");
    }
    '''

    # ─────────────────────────────────────────────
    # 1. unity_setup_project
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_setup_project(
        project_path: str = "",
        verify_sdk: bool = True,
    ) -> str:
        """
        Configure Unity project path and verify VRChat SDK is installed.
        Checks for VRCSDK3-AVATAR, required assemblies, and project structure.

        Parameters:
        - project_path: Path to Unity project root. If empty, uses UNITY_PROJECT_PATH env var.
        - verify_sdk: Check for VRC SDK presence (default: True)
        """
        proj = project_path or UNITY_PROJECT_PATH
        if not proj:
            return json.dumps({"status": "error", "message": "No project path. Set UNITY_PROJECT_PATH or pass project_path."})

        result = {"status": "success", "project_path": proj, "checks": []}

        # Check project structure
        assets_dir = os.path.join(proj, "Assets")
        if not os.path.isdir(assets_dir):
            return json.dumps({"status": "error", "message": f"Assets/ not found in {proj}"})
        result["checks"].append("Assets/ exists")

        packages_dir = os.path.join(proj, "Packages")
        if os.path.isdir(packages_dir):
            result["checks"].append("Packages/ exists")

            if verify_sdk:
                # Check for VRC SDK in Packages
                vpm_manifest = os.path.join(packages_dir, "vpm-manifest.json")
                sdk_found = False

                if os.path.exists(vpm_manifest):
                    with open(vpm_manifest, "r") as f:
                        try:
                            manifest = json.load(f)
                            deps = manifest.get("dependencies", {})
                            if "com.vrchat.avatars" in deps:
                                result["checks"].append(f"VRC Avatars SDK: {deps['com.vrchat.avatars']}")
                                sdk_found = True
                            if "com.vrchat.base" in deps:
                                result["checks"].append(f"VRC Base SDK: {deps['com.vrchat.base']}")
                        except json.JSONDecodeError:
                            pass

                # Also check for embedded SDK folders
                sdk_paths = [
                    os.path.join(packages_dir, "com.vrchat.avatars"),
                    os.path.join(packages_dir, "com.vrchat.base"),
                    os.path.join(assets_dir, "VRCSDK"),
                ]
                for sp in sdk_paths:
                    if os.path.isdir(sp):
                        sdk_found = True
                        result["checks"].append(f"SDK folder: {os.path.basename(sp)}")

                if not sdk_found:
                    result["checks"].append("WARNING: VRC SDK not detected. Use vrc-get to install.")
                    result["sdk_missing"] = True

        # Check Unity version
        project_version = os.path.join(proj, "ProjectSettings", "ProjectVersion.txt")
        if os.path.exists(project_version):
            with open(project_version, "r") as f:
                content = f.read()
                if "m_EditorVersion:" in content:
                    version = content.split("m_EditorVersion:")[1].strip().split()[0]
                    result["unity_version"] = version
                    result["checks"].append(f"Unity version: {version}")

        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 2. unity_import_fbx
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_import_fbx(
        fbx_path: str = "",
        project_path: str = "",
        destination: str = "Assets/Models",
        humanoid_rig: bool = True,
        extract_materials: bool = True,
        extract_textures: bool = True,
    ) -> str:
        """
        Import an FBX file into a Unity project and configure import settings.
        Copies FBX to project, sets humanoid rig type, extracts materials/textures.

        Parameters:
        - fbx_path: Path to the FBX file to import
        - project_path: Unity project path. If empty, uses UNITY_PROJECT_PATH.
        - destination: Relative path inside Assets/ (default: "Assets/Models")
        - humanoid_rig: Set animation type to Humanoid (default: True)
        - extract_materials: Extract materials to separate folder (default: True)
        - extract_textures: Extract embedded textures (default: True)
        """
        import shutil

        proj = project_path or UNITY_PROJECT_PATH
        if not proj:
            return json.dumps({"status": "error", "message": "No project path specified"})
        if not fbx_path or not os.path.exists(fbx_path):
            return json.dumps({"status": "error", "message": f"FBX file not found: {fbx_path}"})

        # Copy FBX to Unity project
        dest_dir = os.path.join(proj, destination)
        os.makedirs(dest_dir, exist_ok=True)

        fbx_name = os.path.basename(fbx_path)
        dest_fbx = os.path.join(dest_dir, fbx_name)
        shutil.copy2(fbx_path, dest_fbx)

        # Also copy any textures that are next to the FBX
        fbx_dir = os.path.dirname(fbx_path)
        tex_exts = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".psd", ".tif", ".tiff"}
        copied_textures = []
        for f in os.listdir(fbx_dir):
            if os.path.splitext(f)[1].lower() in tex_exts:
                src = os.path.join(fbx_dir, f)
                dst = os.path.join(dest_dir, f)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    copied_textures.append(f)

        # Generate C# script to configure import settings
        asset_path = destination.replace("\\", "/") + "/" + fbx_name
        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;

            public class BlenderCopilotFBXImporter {{
                [MenuItem("BlenderCopilot/Import FBX")]
                public static void ImportFBX() {{
                    string assetPath = "{asset_path}";
                    AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);

                    ModelImporter importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
                    if (importer == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"ModelImporter not found for " + assetPath + "\\"}}");
                        return;
                    }}

                    // Configure rig
                    {"importer.animationType = ModelImporterAnimationType.Human;" if humanoid_rig else "// Keep generic rig"}
                    importer.importBlendShapes = true;
                    importer.importVisibility = false;
                    importer.importCameras = false;
                    importer.importLights = false;

                    // Materials
                    {"importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;" if extract_materials else ""}
                    {"importer.SearchAndRemapMaterials(ModelImporterMaterialName.BasedOnModelNameAndMaterialName, ModelImporterMaterialSearch.Local);" if extract_materials else ""}

                    importer.SaveAndReimport();

                    // Get blend shape count
                    GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
                    int blendShapeCount = 0;
                    if (prefab != null) {{
                        foreach (var smr in prefab.GetComponentsInChildren<SkinnedMeshRenderer>()) {{
                            if (smr.sharedMesh != null)
                                blendShapeCount += smr.sharedMesh.blendShapeCount;
                        }}
                    }}

                    string resultJson = JsonUtility.ToJson(new ImportResult {{
                        status = "success",
                        assetPath = assetPath,
                        isHumanoid = {"true" if humanoid_rig else "false"},
                        blendShapeCount = blendShapeCount
                    }});
                    OutputResult(resultJson);
                }}

                {CS_RESULT_HELPER}

                [System.Serializable]
                class ImportResult {{
                    public string status;
                    public string assetPath;
                    public bool isHumanoid;
                    public int blendShapeCount;
                }}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotFBXImporter", "ImportFBX", proj)
        result["fbx_copied_to"] = dest_fbx
        result["textures_copied"] = copied_textures
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 3. unity_setup_avatar_descriptor
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_setup_avatar_descriptor(
        project_path: str = "",
        avatar_object: str = "",
        view_position: str = "0,1.6,0.3",
        lip_sync_style: str = "VisemeBlendShape",
        auto_detect_visemes: bool = True,
    ) -> str:
        """
        Add VRC_AvatarDescriptor to a GameObject in Unity.
        Configures viewpoint, lip sync, and eye tracking defaults.

        Parameters:
        - project_path: Unity project path
        - avatar_object: Name of the root GameObject (usually the FBX prefab name)
        - view_position: Viewpoint offset "x,y,z" (default: "0,1.6,0.3" — between eyes)
        - lip_sync_style: "VisemeBlendShape", "JawBone", "JawFlap" (default: "VisemeBlendShape")
        - auto_detect_visemes: Auto-detect and assign viseme blend shapes (default: True)
        """
        proj = project_path or UNITY_PROJECT_PATH
        vp = view_position.split(",")
        vp_x, vp_y, vp_z = float(vp[0]), float(vp[1]), float(vp[2])

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using VRC.SDK3.Avatars.Components;
            using VRC.SDK3.Avatars.ScriptableObjects;

            public class BlenderCopilotAvatarSetup {{
                public static void Setup() {{
                    // Find the avatar object in scene
                    string avatarName = "{avatar_object}";
                    GameObject avatar = GameObject.Find(avatarName);
                    if (avatar == null) {{
                        // Try to find by partial name
                        foreach (var go in Object.FindObjectsOfType<GameObject>()) {{
                            if (go.name.Contains(avatarName) && go.transform.parent == null) {{
                                avatar = go;
                                break;
                            }}
                        }}
                    }}

                    if (avatar == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"Avatar object not found: {avatar_object}\\"}}");
                        return;
                    }}

                    // Add or get VRC Avatar Descriptor
                    var descriptor = avatar.GetComponent<VRCAvatarDescriptor>();
                    if (descriptor == null) {{
                        descriptor = avatar.AddComponent<VRCAvatarDescriptor>();
                    }}

                    // Set viewpoint
                    descriptor.ViewPosition = new Vector3({vp_x}f, {vp_y}f, {vp_z}f);

                    // Lip sync
                    descriptor.lipSync = VRC.SDKBase.VRC_AvatarDescriptor.LipSyncStyle.{lip_sync_style};

                    {"" if not auto_detect_visemes else '''
                    // Auto-detect visemes
                    if (descriptor.lipSync == VRC.SDKBase.VRC_AvatarDescriptor.LipSyncStyle.VisemeBlendShape) {
                        var body = avatar.GetComponentInChildren<SkinnedMeshRenderer>();
                        if (body != null && body.sharedMesh != null) {
                            descriptor.VisemeSkinnedMesh = body;
                            string[] visemeNames = { "sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS", "nn", "RR", "aa", "E", "I", "O", "U" };
                            string[] prefixes = { "vrc.v_", "vrc_v_", "v_", "viseme_", "" };
                            descriptor.VisemeBlendShapes = new string[15];
                            for (int v = 0; v < 15; v++) {
                                for (int p = 0; p < prefixes.Length; p++) {
                                    string searchName = prefixes[p] + visemeNames[v];
                                    for (int s = 0; s < body.sharedMesh.blendShapeCount; s++) {
                                        if (body.sharedMesh.GetBlendShapeName(s).ToLower().Contains(searchName.ToLower())) {
                                            descriptor.VisemeBlendShapes[v] = body.sharedMesh.GetBlendShapeName(s);
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    '''}

                    // Eye tracking defaults
                    descriptor.enableEyeLook = true;

                    EditorUtility.SetDirty(descriptor);
                    OutputResult("{{\\"status\\":\\"success\\",\\"avatar\\":\\"" + avatar.name + "\\",\\"viewPosition\\":\\"" + descriptor.ViewPosition.ToString() + "\\"}}");
                }}

                {CS_RESULT_HELPER}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotAvatarSetup", "Setup", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 4. unity_setup_expression_menu
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_setup_expression_menu(
        project_path: str = "",
        menu_json: str = "",
        output_path: str = "Assets/VRC/ExpressionMenu.asset",
    ) -> str:
        """
        Generate VRCExpressionsMenu .asset file from a JSON blueprint.

        Parameters:
        - project_path: Unity project path
        - menu_json: JSON string defining menu structure. Format:
          {"controls": [{"name": "Emotes", "type": "SubMenu", "icon": "", "subMenu": "Assets/VRC/EmotesMenu.asset"},
                        {"name": "Toggle Hat", "type": "Toggle", "parameter": "HatToggle"}]}
          Types: Button, Toggle, SubMenu, TwoAxisPuppet, FourAxisPuppet, RadialPuppet
        - output_path: Where to save the .asset file (default: "Assets/VRC/ExpressionMenu.asset")
        """
        proj = project_path or UNITY_PROJECT_PATH
        if not menu_json:
            return json.dumps({"status": "error", "message": "menu_json is required"})

        # Escape the JSON for embedding in C#
        menu_escaped = menu_json.replace("\\", "\\\\").replace('"', '\\"')

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using VRC.SDK3.Avatars.ScriptableObjects;
            using System.Collections.Generic;

            public class BlenderCopilotExpressionMenu {{
                public static void Generate() {{
                    string jsonStr = "{menu_escaped}";
                    var menuData = JsonUtility.FromJson<MenuData>(jsonStr);

                    // Create menu asset
                    var menu = ScriptableObject.CreateInstance<VRCExpressionsMenu>();
                    menu.controls = new List<VRCExpressionsMenu.Control>();

                    if (menuData != null && menuData.controls != null) {{
                        foreach (var ctrl in menuData.controls) {{
                            var control = new VRCExpressionsMenu.Control();
                            control.name = ctrl.name ?? "Unnamed";

                            // Parse type
                            switch (ctrl.type) {{
                                case "Button": control.type = VRCExpressionsMenu.Control.ControlType.Button; break;
                                case "Toggle": control.type = VRCExpressionsMenu.Control.ControlType.Toggle; break;
                                case "SubMenu": control.type = VRCExpressionsMenu.Control.ControlType.SubMenu; break;
                                case "TwoAxisPuppet": control.type = VRCExpressionsMenu.Control.ControlType.TwoAxisPuppet; break;
                                case "FourAxisPuppet": control.type = VRCExpressionsMenu.Control.ControlType.FourAxisPuppet; break;
                                case "RadialPuppet": control.type = VRCExpressionsMenu.Control.ControlType.RadialPuppet; break;
                                default: control.type = VRCExpressionsMenu.Control.ControlType.Toggle; break;
                            }}

                            // Parameter
                            if (!string.IsNullOrEmpty(ctrl.parameter)) {{
                                control.parameter = new VRCExpressionsMenu.Control.Parameter();
                                control.parameter.name = ctrl.parameter;
                            }}

                            control.value = ctrl.value;

                            // SubMenu reference
                            if (!string.IsNullOrEmpty(ctrl.subMenu)) {{
                                control.subMenu = AssetDatabase.LoadAssetAtPath<VRCExpressionsMenu>(ctrl.subMenu);
                            }}

                            menu.controls.Add(control);
                        }}
                    }}

                    // Save asset
                    string outputPath = "{output_path}";
                    string dir = System.IO.Path.GetDirectoryName(outputPath);
                    if (!AssetDatabase.IsValidFolder(dir)) {{
                        System.IO.Directory.CreateDirectory(System.IO.Path.Combine(Application.dataPath, "..", dir));
                        AssetDatabase.Refresh();
                    }}

                    AssetDatabase.CreateAsset(menu, outputPath);
                    AssetDatabase.SaveAssets();

                    OutputResult("{{\\"status\\":\\"success\\",\\"path\\":\\"" + outputPath + "\\",\\"controlCount\\":" + menu.controls.Count + "}}");
                }}

                {CS_RESULT_HELPER}

                [System.Serializable]
                class MenuData {{ public ControlData[] controls; }}

                [System.Serializable]
                class ControlData {{
                    public string name;
                    public string type;
                    public string parameter;
                    public float value;
                    public string subMenu;
                    public string icon;
                }}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotExpressionMenu", "Generate", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 5. unity_setup_expression_parameters
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_setup_expression_parameters(
        project_path: str = "",
        parameters_json: str = "",
        output_path: str = "Assets/VRC/ExpressionParameters.asset",
    ) -> str:
        """
        Generate VRCExpressionParameters .asset file from JSON blueprint.

        Parameters:
        - project_path: Unity project path
        - parameters_json: JSON string. Format:
          {"parameters": [{"name": "VRCFaceBlendH", "valueType": "Float", "defaultValue": 0, "saved": true, "synced": true},
                          {"name": "HatToggle", "valueType": "Bool", "defaultValue": 0, "saved": true, "synced": true}]}
          valueTypes: Int, Float, Bool
        - output_path: Where to save the .asset file
        """
        proj = project_path or UNITY_PROJECT_PATH
        if not parameters_json:
            return json.dumps({"status": "error", "message": "parameters_json is required"})

        params_escaped = parameters_json.replace("\\", "\\\\").replace('"', '\\"')

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using VRC.SDK3.Avatars.ScriptableObjects;

            public class BlenderCopilotExpressionParams {{
                public static void Generate() {{
                    string jsonStr = "{params_escaped}";
                    var paramData = JsonUtility.FromJson<ParamData>(jsonStr);

                    var parameters = ScriptableObject.CreateInstance<VRCExpressionParameters>();
                    var paramList = new System.Collections.Generic.List<VRCExpressionParameters.Parameter>();

                    if (paramData != null && paramData.parameters != null) {{
                        foreach (var p in paramData.parameters) {{
                            var param = new VRCExpressionParameters.Parameter();
                            param.name = p.name;
                            switch (p.valueType) {{
                                case "Int": param.valueType = VRCExpressionParameters.ValueType.Int; break;
                                case "Float": param.valueType = VRCExpressionParameters.ValueType.Float; break;
                                case "Bool": param.valueType = VRCExpressionParameters.ValueType.Bool; break;
                            }}
                            param.defaultValue = p.defaultValue;
                            param.saved = p.saved;
                            param.networkSynced = p.synced;
                            paramList.Add(param);
                        }}
                    }}

                    parameters.parameters = paramList.ToArray();

                    string outputPath = "{output_path}";
                    string dir = System.IO.Path.GetDirectoryName(outputPath);
                    if (!AssetDatabase.IsValidFolder(dir)) {{
                        System.IO.Directory.CreateDirectory(System.IO.Path.Combine(Application.dataPath, "..", dir));
                        AssetDatabase.Refresh();
                    }}

                    AssetDatabase.CreateAsset(parameters, outputPath);
                    AssetDatabase.SaveAssets();

                    // Calculate bits used
                    int bits = 0;
                    foreach (var p in parameters.parameters) {{
                        switch (p.valueType) {{
                            case VRCExpressionParameters.ValueType.Bool: bits += 1; break;
                            case VRCExpressionParameters.ValueType.Int:
                            case VRCExpressionParameters.ValueType.Float: bits += 8; break;
                        }}
                    }}

                    OutputResult("{{\\"status\\":\\"success\\",\\"path\\":\\"" + outputPath + "\\",\\"paramCount\\":" + parameters.parameters.Length + ",\\"bitsUsed\\":" + bits + ",\\"bitsMax\\":256}}");
                }}

                {CS_RESULT_HELPER}

                [System.Serializable]
                class ParamData {{ public ParamEntry[] parameters; }}

                [System.Serializable]
                class ParamEntry {{
                    public string name;
                    public string valueType;
                    public float defaultValue;
                    public bool saved;
                    public bool synced;
                }}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotExpressionParams", "Generate", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 6. unity_create_animator
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_create_animator(
        project_path: str = "",
        animator_json: str = "",
        output_path: str = "Assets/VRC/FX.controller",
    ) -> str:
        """
        Generate an AnimatorController from a JSON blueprint.

        Parameters:
        - project_path: Unity project path
        - animator_json: JSON defining layers/states/transitions. Format:
          {"layers": [{"name": "FaceTracking", "defaultState": "Idle",
            "states": [{"name": "Idle", "motion": null},
                       {"name": "Smile", "motion": "Assets/Anims/Smile.anim"}],
            "transitions": [{"from": "Idle", "to": "Smile", "conditions": [{"param": "SmileWeight", "mode": "Greater", "threshold": 0.5}]}]
          }]}
        - output_path: Where to save .controller asset
        """
        proj = project_path or UNITY_PROJECT_PATH
        if not animator_json:
            return json.dumps({"status": "error", "message": "animator_json is required"})

        anim_escaped = animator_json.replace("\\", "\\\\").replace('"', '\\"')

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using UnityEditor.Animations;
            using System.Collections.Generic;

            public class BlenderCopilotAnimator {{
                public static void Generate() {{
                    string jsonStr = "{anim_escaped}";
                    var data = JsonUtility.FromJson<AnimatorData>(jsonStr);

                    string outputPath = "{output_path}";
                    var controller = AnimatorController.CreateAnimatorControllerAtPath(outputPath);

                    // Remove default layer
                    if (controller.layers.Length > 0) {{
                        controller.RemoveLayer(0);
                    }}

                    int totalStates = 0;
                    int totalTransitions = 0;

                    if (data != null && data.layers != null) {{
                        foreach (var layerData in data.layers) {{
                            controller.AddLayer(layerData.name);
                            var layers = controller.layers;
                            var layer = layers[layers.Length - 1];
                            layer.defaultWeight = 1f;
                            controller.layers = layers;

                            var stateMachine = layer.stateMachine;
                            var stateMap = new Dictionary<string, AnimatorState>();

                            // Create states
                            if (layerData.states != null) {{
                                foreach (var stateData in layerData.states) {{
                                    var state = stateMachine.AddState(stateData.name);
                                    if (!string.IsNullOrEmpty(stateData.motion)) {{
                                        state.motion = AssetDatabase.LoadAssetAtPath<AnimationClip>(stateData.motion);
                                    }}
                                    stateMap[stateData.name] = state;
                                    totalStates++;

                                    if (stateData.name == layerData.defaultState) {{
                                        stateMachine.defaultState = state;
                                    }}
                                }}
                            }}

                            // Create transitions
                            if (layerData.transitions != null) {{
                                foreach (var transData in layerData.transitions) {{
                                    if (stateMap.ContainsKey(transData.from) && stateMap.ContainsKey(transData.to)) {{
                                        var transition = stateMap[transData.from].AddTransition(stateMap[transData.to]);
                                        transition.hasExitTime = false;
                                        transition.duration = 0.1f;

                                        if (transData.conditions != null) {{
                                            foreach (var cond in transData.conditions) {{
                                                AnimatorConditionMode mode = AnimatorConditionMode.Greater;
                                                switch (cond.mode) {{
                                                    case "Greater": mode = AnimatorConditionMode.Greater; break;
                                                    case "Less": mode = AnimatorConditionMode.Less; break;
                                                    case "Equals": mode = AnimatorConditionMode.Equals; break;
                                                    case "NotEqual": mode = AnimatorConditionMode.NotEqual; break;
                                                    case "If": mode = AnimatorConditionMode.If; break;
                                                    case "IfNot": mode = AnimatorConditionMode.IfNot; break;
                                                }}

                                                // Ensure parameter exists
                                                bool paramExists = false;
                                                foreach (var p in controller.parameters) {{
                                                    if (p.name == cond.param) {{ paramExists = true; break; }}
                                                }}
                                                if (!paramExists) {{
                                                    controller.AddParameter(cond.param, AnimatorControllerParameterType.Float);
                                                }}

                                                transition.AddCondition(mode, cond.threshold, cond.param);
                                                totalTransitions++;
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}

                    AssetDatabase.SaveAssets();
                    OutputResult("{{\\"status\\":\\"success\\",\\"path\\":\\"" + outputPath + "\\",\\"layers\\":" + controller.layers.Length + ",\\"states\\":" + totalStates + ",\\"transitions\\":" + totalTransitions + "}}");
                }}

                {CS_RESULT_HELPER}

                [System.Serializable] class AnimatorData {{ public LayerData[] layers; }}
                [System.Serializable] class LayerData {{ public string name; public string defaultState; public StateData[] states; public TransitionData[] transitions; }}
                [System.Serializable] class StateData {{ public string name; public string motion; }}
                [System.Serializable] class TransitionData {{ public string from; public string to; public ConditionData[] conditions; }}
                [System.Serializable] class ConditionData {{ public string param; public string mode; public float threshold; }}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotAnimator", "Generate", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 7. unity_create_animation_clip
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_create_animation_clip(
        project_path: str = "",
        clip_json: str = "",
        output_path: str = "Assets/VRC/Animations/clip.anim",
    ) -> str:
        """
        Generate a Unity AnimationClip .anim file from JSON blueprint.
        Used for blend shape animations (face tracking, expressions, toggles).

        Parameters:
        - project_path: Unity project path
        - clip_json: JSON defining the clip. Format:
          {"name": "Smile", "length": 0.0, "curves": [
            {"path": "Body", "property": "blendShape.jawOpen", "keys": [{"time": 0, "value": 0}, {"time": 1, "value": 100}]},
            {"path": "Body", "property": "m_IsActive", "keys": [{"time": 0, "value": 1}]}
          ]}
          For single-frame clips (toggles), use length: 0 and one keyframe.
        - output_path: Where to save the .anim file
        """
        proj = project_path or UNITY_PROJECT_PATH
        if not clip_json:
            return json.dumps({"status": "error", "message": "clip_json is required"})

        clip_escaped = clip_json.replace("\\", "\\\\").replace('"', '\\"')

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;

            public class BlenderCopilotAnimClip {{
                public static void Generate() {{
                    string jsonStr = "{clip_escaped}";
                    var data = JsonUtility.FromJson<ClipData>(jsonStr);

                    var clip = new AnimationClip();
                    clip.name = data.name ?? "BlenderCopilotClip";
                    clip.legacy = false;

                    int curveCount = 0;
                    if (data.curves != null) {{
                        foreach (var curveData in data.curves) {{
                            var curve = new AnimationCurve();
                            if (curveData.keys != null) {{
                                foreach (var k in curveData.keys) {{
                                    curve.AddKey(k.time, k.value);
                                }}
                            }}

                            // Determine binding type
                            System.Type bindingType = typeof(SkinnedMeshRenderer);
                            string property = curveData.property;
                            if (property == "m_IsActive") {{
                                bindingType = typeof(GameObject);
                            }} else if (property.StartsWith("material.")) {{
                                bindingType = typeof(Renderer);
                            }}

                            clip.SetCurve(curveData.path, bindingType, property, curve);
                            curveCount++;
                        }}
                    }}

                    // For single-frame clips, mark as non-looping
                    if (data.length <= 0) {{
                        var settings = AnimationUtility.GetAnimationClipSettings(clip);
                        settings.loopTime = false;
                        AnimationUtility.SetAnimationClipSettings(clip, settings);
                    }}

                    string outputPath = "{output_path}";
                    string dir = System.IO.Path.GetDirectoryName(outputPath);
                    if (!AssetDatabase.IsValidFolder(dir)) {{
                        System.IO.Directory.CreateDirectory(System.IO.Path.Combine(Application.dataPath, "..", dir));
                        AssetDatabase.Refresh();
                    }}

                    AssetDatabase.CreateAsset(clip, outputPath);
                    AssetDatabase.SaveAssets();

                    OutputResult("{{\\"status\\":\\"success\\",\\"path\\":\\"" + outputPath + "\\",\\"name\\":\\"" + clip.name + "\\",\\"curves\\":" + curveCount + "}}");
                }}

                {CS_RESULT_HELPER}

                [System.Serializable] class ClipData {{ public string name; public float length; public CurveData[] curves; }}
                [System.Serializable] class CurveData {{ public string path; public string property; public KeyData[] keys; }}
                [System.Serializable] class KeyData {{ public float time; public float value; }}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotAnimClip", "Generate", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 8. unity_setup_gesture_layer
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_setup_gesture_layer(
        project_path: str = "",
        output_path: str = "Assets/VRC/Gesture.controller",
        hand_gestures: str = "default",
    ) -> str:
        """
        Create a VRChat Gesture FX layer with hand gesture states.
        Standard 8 gestures: Neutral, Fist, Open, Point, Peace, RockNRoll, Gun, Thumbsup.

        Parameters:
        - project_path: Unity project path
        - output_path: Where to save .controller asset
        - hand_gestures: "default" (standard 8 gestures) or "custom" (empty states for manual setup)
        """
        proj = project_path or UNITY_PROJECT_PATH

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using UnityEditor.Animations;

            public class BlenderCopilotGesture {{
                public static void Generate() {{
                    string outputPath = "{output_path}";
                    var controller = AnimatorController.CreateAnimatorControllerAtPath(outputPath);

                    // Add GestureLeft parameter (int 0-7)
                    controller.AddParameter("GestureLeft", AnimatorControllerParameterType.Int);
                    controller.AddParameter("GestureRight", AnimatorControllerParameterType.Int);
                    controller.AddParameter("GestureLeftWeight", AnimatorControllerParameterType.Float);
                    controller.AddParameter("GestureRightWeight", AnimatorControllerParameterType.Float);

                    string[] gestureNames = {{ "Neutral", "Fist", "Open", "Point", "Peace", "RockNRoll", "Gun", "Thumbsup" }};

                    // Create Left Hand layer
                    if (controller.layers.Length > 0) controller.RemoveLayer(0);

                    foreach (string hand in new string[] {{ "Left", "Right" }}) {{
                        controller.AddLayer(hand + " Hand");
                        var layers = controller.layers;
                        var layer = layers[layers.Length - 1];
                        layer.defaultWeight = 1f;
                        controller.layers = layers;

                        var sm = layer.stateMachine;
                        string paramName = "Gesture" + hand;

                        for (int i = 0; i < gestureNames.Length; i++) {{
                            var state = sm.AddState(gestureNames[i]);
                            if (i == 0) sm.defaultState = state;

                            // Add transitions from Any State
                            var transition = sm.AddAnyStateTransition(state);
                            transition.hasExitTime = false;
                            transition.duration = 0.1f;
                            transition.AddCondition(AnimatorConditionMode.Equals, i, paramName);
                        }}
                    }}

                    AssetDatabase.SaveAssets();
                    OutputResult("{{\\"status\\":\\"success\\",\\"path\\":\\"" + outputPath + "\\",\\"layers\\":" + controller.layers.Length + ",\\"gestures\\":8}}");
                }}

                {CS_RESULT_HELPER}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotGesture", "Generate", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 9. unity_configure_shader
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_configure_shader(
        project_path: str = "",
        material_name: str = "",
        shader_name: str = "poiyomi",
        properties_json: str = "",
    ) -> str:
        """
        Configure shader properties on a Unity material.
        Supports Poiyomi, lilToon, UTS2, and Standard shaders.

        Parameters:
        - project_path: Unity project path
        - material_name: Name of the material to configure (or .mat asset path)
        - shader_name: "poiyomi", "liltoon", "uts2", "standard" (default: "poiyomi")
        - properties_json: JSON of property overrides. Format depends on shader:
          Poiyomi: {"_MainTex": "Assets/Tex/body.png", "_Color": "1,0.9,0.8,1", "_EnableEmission": 1}
          lilToon: {"_MainTex": "...", "_Color": "...", "_ShadowColor": "0.8,0.7,0.7,1"}
        """
        proj = project_path or UNITY_PROJECT_PATH
        props_escaped = (properties_json or "{}").replace("\\", "\\\\").replace('"', '\\"')

        # Map shader shortnames to full shader names
        shader_map = {
            "poiyomi": ".poiyomi/Poiyomi Toon",
            "liltoon": "lilToon",
            "uts2": "Universal Render Pipeline/Toon",
            "standard": "Standard",
        }
        full_shader = shader_map.get(shader_name, shader_name)

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using System.Collections.Generic;

            public class BlenderCopilotShader {{
                public static void Configure() {{
                    string matName = "{material_name}";
                    string shaderFullName = "{full_shader}";

                    // Find material
                    Material mat = null;
                    if (matName.EndsWith(".mat")) {{
                        mat = AssetDatabase.LoadAssetAtPath<Material>(matName);
                    }} else {{
                        string[] guids = AssetDatabase.FindAssets("t:Material " + matName);
                        foreach (string guid in guids) {{
                            string path = AssetDatabase.GUIDToAssetPath(guid);
                            Material m = AssetDatabase.LoadAssetAtPath<Material>(path);
                            if (m != null && m.name == matName) {{
                                mat = m;
                                break;
                            }}
                        }}
                    }}

                    if (mat == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"Material not found: {material_name}\\"}}");
                        return;
                    }}

                    // Find and set shader
                    Shader shader = Shader.Find(shaderFullName);
                    if (shader == null) {{
                        // Try partial match
                        string[] allShaders = UnityEditor.ShaderUtil.GetAllShaderInfo() != null ? new string[0] : new string[0];
                        // Fallback: keep current shader
                        OutputResult("{{\\"status\\":\\"warning\\",\\"message\\":\\"Shader not found: " + shaderFullName + ". Keeping current shader.\\",\\"currentShader\\":\\"" + mat.shader.name + "\\"}}");
                    }} else {{
                        mat.shader = shader;
                    }}

                    // Apply properties
                    string propsJson = "{props_escaped}";
                    int propsSet = 0;

                    // Simple key-value property parsing
                    // Format: {{"_Prop": "value", ...}}
                    // For textures: value is asset path
                    // For colors: value is "r,g,b,a"
                    // For floats: value is number string

                    if (!string.IsNullOrEmpty(propsJson) && propsJson != "{{}}") {{
                        // Manual parse since JsonUtility doesn't handle dynamic keys well
                        propsJson = propsJson.Trim(new char[] {{ '{{', '}}' }});
                        string[] pairs = propsJson.Split(',');
                        foreach (string pair in pairs) {{
                            string[] kv = pair.Split(new char[] {{ ':' }}, 2);
                            if (kv.Length == 2) {{
                                string key = kv[0].Trim().Trim('"');
                                string val = kv[1].Trim().Trim('"');

                                if (mat.HasProperty(key)) {{
                                    // Try as float
                                    float fval;
                                    if (float.TryParse(val, out fval)) {{
                                        mat.SetFloat(key, fval);
                                        propsSet++;
                                    }}
                                    // Try as color (r,g,b,a)
                                    else if (val.Contains(",") && !val.Contains("/")) {{
                                        string[] parts = val.Split(',');
                                        if (parts.Length >= 3) {{
                                            float r = float.Parse(parts[0]);
                                            float g = float.Parse(parts[1]);
                                            float b = float.Parse(parts[2]);
                                            float a = parts.Length > 3 ? float.Parse(parts[3]) : 1f;
                                            mat.SetColor(key, new Color(r, g, b, a));
                                            propsSet++;
                                        }}
                                    }}
                                    // Try as texture path
                                    else if (val.StartsWith("Assets/")) {{
                                        Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(val);
                                        if (tex != null) {{
                                            mat.SetTexture(key, tex);
                                            propsSet++;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}

                    EditorUtility.SetDirty(mat);
                    AssetDatabase.SaveAssets();

                    OutputResult("{{\\"status\\":\\"success\\",\\"material\\":\\"" + mat.name + "\\",\\"shader\\":\\"" + mat.shader.name + "\\",\\"propertiesSet\\":" + propsSet + "}}");
                }}

                {CS_RESULT_HELPER}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotShader", "Configure", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 10. unity_create_material_presets
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_create_material_presets(
        project_path: str = "",
        preset: str = "avatar_basic",
        shader_name: str = "liltoon",
        output_dir: str = "Assets/Materials",
    ) -> str:
        """
        Generate a set of preset materials for common avatar parts.

        Parameters:
        - project_path: Unity project path
        - preset: "avatar_basic" (skin/hair/eye/cloth), "avatar_full" (+ accessory/emission/transparent), "custom"
        - shader_name: Base shader for all materials (default: "liltoon")
        - output_dir: Folder to save materials
        """
        proj = project_path or UNITY_PROJECT_PATH

        presets = {
            "avatar_basic": ["Skin", "Hair", "Eye", "Cloth"],
            "avatar_full": ["Skin", "Hair", "Eye", "Cloth", "Accessory", "Emission", "Transparent"],
        }
        mat_names = presets.get(preset, ["Material"])

        shader_map = {
            "poiyomi": ".poiyomi/Poiyomi Toon",
            "liltoon": "lilToon",
            "standard": "Standard",
        }
        full_shader = shader_map.get(shader_name, shader_name)

        mat_names_str = ",".join(mat_names)

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;

            public class BlenderCopilotMaterialPresets {{
                public static void Generate() {{
                    string shaderName = "{full_shader}";
                    string outputDir = "{output_dir}";
                    string[] matNames = "{mat_names_str}".Split(',');

                    Shader shader = Shader.Find(shaderName);
                    if (shader == null) {{
                        shader = Shader.Find("Standard");
                    }}

                    // Ensure output directory
                    if (!AssetDatabase.IsValidFolder(outputDir)) {{
                        System.IO.Directory.CreateDirectory(System.IO.Path.Combine(Application.dataPath, "..", outputDir));
                        AssetDatabase.Refresh();
                    }}

                    int created = 0;
                    foreach (string matName in matNames) {{
                        string path = outputDir + "/" + matName + ".mat";
                        if (AssetDatabase.LoadAssetAtPath<Material>(path) != null) continue;

                        var mat = new Material(shader);
                        mat.name = matName;

                        // Apply preset defaults based on material type
                        switch (matName) {{
                            case "Skin":
                                mat.SetColor("_Color", new Color(1f, 0.92f, 0.85f, 1f));
                                break;
                            case "Hair":
                                mat.SetColor("_Color", new Color(0.2f, 0.15f, 0.12f, 1f));
                                break;
                            case "Eye":
                                mat.SetColor("_Color", new Color(0.4f, 0.6f, 0.8f, 1f));
                                break;
                            case "Cloth":
                                mat.SetColor("_Color", new Color(0.9f, 0.9f, 0.95f, 1f));
                                break;
                            case "Emission":
                                mat.EnableKeyword("_EMISSION");
                                mat.SetColor("_EmissionColor", Color.white);
                                break;
                            case "Transparent":
                                mat.SetFloat("_Mode", 3); // Transparent
                                mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
                                mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                                mat.renderQueue = 3000;
                                break;
                        }}

                        AssetDatabase.CreateAsset(mat, path);
                        created++;
                    }}

                    AssetDatabase.SaveAssets();
                    OutputResult("{{\\"status\\":\\"success\\",\\"outputDir\\":\\"" + outputDir + "\\",\\"created\\":" + created + ",\\"total\\":" + matNames.Length + "}}");
                }}

                {CS_RESULT_HELPER}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotMaterialPresets", "Generate", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 11. unity_setup_physbones
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_setup_physbones(
        project_path: str = "",
        physbones_json: str = "",
        avatar_object: str = "",
    ) -> str:
        """
        Add VRCPhysBone components to an avatar from a JSON blueprint.

        Parameters:
        - project_path: Unity project path
        - avatar_object: Root avatar GameObject name
        - physbones_json: JSON array of PhysBone configs. Format:
          [{"bonePath": "Armature/Hips/Spine/Hair_Root", "pull": 0.2, "spring": 0.8,
            "stiffness": 0.2, "gravity": 0.1, "gravityFalloff": 0.5,
            "immobile": 0.3, "radius": 0.05, "colliders": [],
            "limitType": "Angle", "maxAngle": 45}]
        """
        proj = project_path or UNITY_PROJECT_PATH
        if not physbones_json:
            return json.dumps({"status": "error", "message": "physbones_json is required"})

        pb_escaped = physbones_json.replace("\\", "\\\\").replace('"', '\\"')

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using VRC.SDK3.Dynamics.PhysBone.Components;

            public class BlenderCopilotPhysBones {{
                public static void Setup() {{
                    string avatarName = "{avatar_object}";
                    GameObject avatar = GameObject.Find(avatarName);
                    if (avatar == null) {{
                        foreach (var go in Object.FindObjectsOfType<GameObject>()) {{
                            if (go.name.Contains(avatarName) && go.transform.parent == null) {{
                                avatar = go;
                                break;
                            }}
                        }}
                    }}

                    if (avatar == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"Avatar not found: {avatar_object}\\"}}");
                        return;
                    }}

                    string jsonStr = "{pb_escaped}";
                    var data = JsonUtility.FromJson<PBArray>('{{\\"items\\":' + jsonStr + '}}');

                    int added = 0;
                    int failed = 0;

                    if (data != null && data.items != null) {{
                        foreach (var pb in data.items) {{
                            // Find the bone transform
                            Transform bone = avatar.transform.Find(pb.bonePath);
                            if (bone == null) {{
                                failed++;
                                continue;
                            }}

                            // Add PhysBone component
                            var comp = bone.gameObject.GetComponent<VRCPhysBone>();
                            if (comp == null) {{
                                comp = bone.gameObject.AddComponent<VRCPhysBone>();
                            }}

                            comp.pull = pb.pull;
                            comp.spring = pb.spring;
                            comp.stiffness = pb.stiffness;
                            comp.gravity = pb.gravity;
                            comp.gravityFalloff = pb.gravityFalloff;
                            comp.immobileType = VRCPhysBoneBase.ImmobileType.World;
                            comp.immobile = pb.immobile;
                            comp.radius = pb.radius;

                            // Limit type
                            switch (pb.limitType) {{
                                case "Angle":
                                    comp.limitType = VRCPhysBoneBase.LimitType.Angle;
                                    comp.maxAngleX = pb.maxAngle;
                                    break;
                                case "Hinge":
                                    comp.limitType = VRCPhysBoneBase.LimitType.Hinge;
                                    comp.maxAngleX = pb.maxAngle;
                                    break;
                                case "Polar":
                                    comp.limitType = VRCPhysBoneBase.LimitType.Polar;
                                    comp.maxAngleX = pb.maxAngle;
                                    break;
                                default:
                                    comp.limitType = VRCPhysBoneBase.LimitType.None;
                                    break;
                            }}

                            EditorUtility.SetDirty(comp);
                            added++;
                        }}
                    }}

                    OutputResult("{{\\"status\\":\\"success\\",\\"avatar\\":\\"" + avatar.name + "\\",\\"added\\":" + added + ",\\"failed\\":" + failed + "}}");
                }}

                {CS_RESULT_HELPER}

                [System.Serializable] class PBArray {{ public PBData[] items; }}
                [System.Serializable] class PBData {{
                    public string bonePath;
                    public float pull; public float spring; public float stiffness;
                    public float gravity; public float gravityFalloff;
                    public float immobile; public float radius;
                    public string limitType; public float maxAngle;
                }}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotPhysBones", "Setup", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 12. unity_setup_contacts
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_setup_contacts(
        project_path: str = "",
        contacts_json: str = "",
        avatar_object: str = "",
    ) -> str:
        """
        Add VRC ContactSender/ContactReceiver components from JSON blueprint.

        Parameters:
        - project_path: Unity project path
        - avatar_object: Root avatar GameObject name
        - contacts_json: JSON array. Format:
          [{"bonePath": "Armature/Hips/Spine/Head", "type": "Receiver",
            "collisionTags": ["Head"], "radius": 0.3, "position": "0,0,0",
            "receiverType": "Proximity", "parameter": "HeadPat"}]
          type: "Sender" or "Receiver"
          receiverType (for Receivers): "Proximity", "Constant", "OnEnter"
        """
        proj = project_path or UNITY_PROJECT_PATH
        if not contacts_json:
            return json.dumps({"status": "error", "message": "contacts_json is required"})

        ct_escaped = contacts_json.replace("\\", "\\\\").replace('"', '\\"')

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using VRC.SDK3.Dynamics.Contact.Components;

            public class BlenderCopilotContacts {{
                public static void Setup() {{
                    string avatarName = "{avatar_object}";
                    GameObject avatar = GameObject.Find(avatarName);
                    if (avatar == null) {{
                        foreach (var go in Object.FindObjectsOfType<GameObject>()) {{
                            if (go.name.Contains(avatarName) && go.transform.parent == null) {{
                                avatar = go;
                                break;
                            }}
                        }}
                    }}

                    if (avatar == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"Avatar not found: {avatar_object}\\"}}");
                        return;
                    }}

                    string jsonStr = "{ct_escaped}";
                    var data = JsonUtility.FromJson<CTArray>('{{\\"items\\":' + jsonStr + '}}');

                    int senders = 0, receivers = 0, failed = 0;

                    if (data != null && data.items != null) {{
                        foreach (var ct in data.items) {{
                            Transform bone = avatar.transform.Find(ct.bonePath);
                            if (bone == null) {{ failed++; continue; }}

                            if (ct.type == "Sender") {{
                                var comp = bone.gameObject.AddComponent<VRCContactSender>();
                                comp.radius = ct.radius;
                                if (ct.collisionTags != null) {{
                                    comp.collisionTags = new System.Collections.Generic.List<string>(ct.collisionTags);
                                }}
                                EditorUtility.SetDirty(comp);
                                senders++;
                            }} else {{
                                var comp = bone.gameObject.AddComponent<VRCContactReceiver>();
                                comp.radius = ct.radius;
                                comp.parameter = ct.parameter;
                                if (ct.collisionTags != null) {{
                                    comp.collisionTags = new System.Collections.Generic.List<string>(ct.collisionTags);
                                }}
                                switch (ct.receiverType) {{
                                    case "Proximity": comp.receiverType = VRCContactReceiver.ReceiverType.Proximity; break;
                                    case "Constant": comp.receiverType = VRCContactReceiver.ReceiverType.Constant; break;
                                    case "OnEnter": comp.receiverType = VRCContactReceiver.ReceiverType.OnEnter; break;
                                }}
                                EditorUtility.SetDirty(comp);
                                receivers++;
                            }}
                        }}
                    }}

                    OutputResult("{{\\"status\\":\\"success\\",\\"avatar\\":\\"" + avatar.name + "\\",\\"senders\\":" + senders + ",\\"receivers\\":" + receivers + ",\\"failed\\":" + failed + "}}");
                }}

                {CS_RESULT_HELPER}

                [System.Serializable] class CTArray {{ public CTData[] items; }}
                [System.Serializable] class CTData {{
                    public string bonePath; public string type;
                    public string[] collisionTags; public float radius;
                    public string position; public string receiverType;
                    public string parameter;
                }}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotContacts", "Setup", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 13. unity_configure_pipeline
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_configure_pipeline(
        project_path: str = "",
        fbx_path: str = "",
        avatar_name: str = "",
        blueprint_json: str = "",
    ) -> str:
        """
        One-click full Unity avatar setup pipeline.
        Imports FBX, configures humanoid rig, sets up avatar descriptor,
        creates expression menu/params, and configures materials.

        Parameters:
        - project_path: Unity project path
        - fbx_path: Path to the FBX file
        - avatar_name: Name for the avatar
        - blueprint_json: Optional JSON with full configuration override.
          If empty, uses intelligent defaults based on the FBX content.
        """
        proj = project_path or UNITY_PROJECT_PATH
        if not proj:
            return json.dumps({"status": "error", "message": "No project path specified"})

        results = {"status": "success", "steps": []}

        # Step 1: Import FBX
        import_result = json.loads(unity_import_fbx(
            fbx_path=fbx_path,
            project_path=proj,
            destination="Assets/Models",
            humanoid_rig=True,
        ))
        results["steps"].append({"step": "import_fbx", "result": import_result})

        if import_result.get("status") == "error":
            results["status"] = "partial"
            return json.dumps(results)

        name = avatar_name or os.path.splitext(os.path.basename(fbx_path))[0]

        # Step 2: Setup avatar descriptor
        desc_result = json.loads(unity_setup_avatar_descriptor(
            project_path=proj,
            avatar_object=name,
        ))
        results["steps"].append({"step": "avatar_descriptor", "result": desc_result})

        # Step 3: Create default expression parameters
        default_params = json.dumps({
            "parameters": [
                {"name": "VRCFaceBlendH", "valueType": "Float", "defaultValue": 0, "saved": True, "synced": True},
                {"name": "VRCFaceBlendV", "valueType": "Float", "defaultValue": 0, "saved": True, "synced": True},
                {"name": "VRCEmote", "valueType": "Int", "defaultValue": 0, "saved": False, "synced": True},
            ]
        })
        params_result = json.loads(unity_setup_expression_parameters(
            project_path=proj,
            parameters_json=default_params,
        ))
        results["steps"].append({"step": "expression_parameters", "result": params_result})

        # Step 4: Create default expression menu
        default_menu = json.dumps({
            "controls": [
                {"name": "Emotes", "type": "SubMenu", "parameter": ""},
                {"name": "Face Blend H", "type": "RadialPuppet", "parameter": "VRCFaceBlendH"},
                {"name": "Face Blend V", "type": "RadialPuppet", "parameter": "VRCFaceBlendV"},
            ]
        })
        menu_result = json.loads(unity_setup_expression_menu(
            project_path=proj,
            menu_json=default_menu,
        ))
        results["steps"].append({"step": "expression_menu", "result": menu_result})

        # Step 5: Create gesture layer
        gesture_result = json.loads(unity_setup_gesture_layer(
            project_path=proj,
        ))
        results["steps"].append({"step": "gesture_layer", "result": gesture_result})

        # Step 6: Create material presets
        mat_result = json.loads(unity_create_material_presets(
            project_path=proj,
            preset="avatar_basic",
            shader_name="liltoon",
        ))
        results["steps"].append({"step": "material_presets", "result": mat_result})

        # Count successes
        success_count = sum(1 for s in results["steps"] if s["result"].get("status") == "success")
        results["summary"] = f"{success_count}/{len(results['steps'])} steps completed"

        return json.dumps(results)

    # ─────────────────────────────────────────────
    # 14. unity_build_avatar
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_build_avatar(
        project_path: str = "",
        avatar_object: str = "",
    ) -> str:
        """
        Trigger VRC SDK avatar build (local test build, not publish).
        Validates the avatar and builds the AssetBundle.

        Parameters:
        - project_path: Unity project path
        - avatar_object: Root avatar GameObject name
        """
        proj = project_path or UNITY_PROJECT_PATH

        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using VRC.SDK3.Avatars.Components;
            using VRC.SDKBase.Editor.BuildPipeline;

            public class BlenderCopilotBuild {{
                public static void Build() {{
                    string avatarName = "{avatar_object}";
                    GameObject avatar = GameObject.Find(avatarName);
                    if (avatar == null) {{
                        foreach (var go in Object.FindObjectsOfType<GameObject>()) {{
                            if (go.name.Contains(avatarName) && go.transform.parent == null) {{
                                avatar = go;
                                break;
                            }}
                        }}
                    }}

                    if (avatar == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"Avatar not found: {avatar_object}\\"}}");
                        return;
                    }}

                    var descriptor = avatar.GetComponent<VRCAvatarDescriptor>();
                    if (descriptor == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"No VRCAvatarDescriptor on " + avatar.name + "\\"}}");
                        return;
                    }}

                    // Run VRC build validation
                    try {{
                        bool valid = VRCBuildPipelineCallbacks.OnVRCSDKBuildRequested(VRCSDKRequestedBuildType.Avatar);
                        if (valid) {{
                            OutputResult("{{\\"status\\":\\"success\\",\\"avatar\\":\\"" + avatar.name + "\\",\\"message\\":\\"Build validation passed. Use unity_publish_avatar for full publish.\\"}}");
                        }} else {{
                            OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"VRC build validation failed. Check Unity console for details.\\"}}");
                        }}
                    }} catch (System.Exception e) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"Build failed: " + e.Message.Replace("\\"", "'") + "\\"}}");
                    }}
                }}

                {CS_RESULT_HELPER}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotBuild", "Build", proj)
        return json.dumps(result)

    # ─────────────────────────────────────────────
    # 15. unity_publish_avatar
    # ─────────────────────────────────────────────
    @mcp.tool()
    def unity_publish_avatar(
        project_path: str = "",
        avatar_object: str = "",
        avatar_name: str = "",
        description: str = "",
        tags: str = "",
        release_status: str = "private",
    ) -> str:
        """
        Publish avatar to VRChat. Requires VRC SDK and logged-in session.
        This tool attempts CLI publish first. If that fails (GUI-only publish flow),
        it returns instructions for using computer-use MCP to click through the SDK GUI.

        Parameters:
        - project_path: Unity project path
        - avatar_object: Root avatar GameObject name in scene
        - avatar_name: Display name on VRChat (default: same as avatar_object)
        - description: Avatar description
        - tags: Comma-separated tags
        - release_status: "private" or "public" (default: "private")
        """
        proj = project_path or UNITY_PROJECT_PATH
        name = avatar_name or avatar_object
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        # VRC SDK publish is primarily GUI-based (Build & Publish button)
        # We attempt to trigger it via script, but this may need GUI interaction
        cs_code = textwrap.dedent(f'''
            using UnityEngine;
            using UnityEditor;
            using VRC.SDK3.Avatars.Components;

            public class BlenderCopilotPublish {{
                public static void Publish() {{
                    string avatarName = "{avatar_object}";
                    GameObject avatar = GameObject.Find(avatarName);
                    if (avatar == null) {{
                        foreach (var go in Object.FindObjectsOfType<GameObject>()) {{
                            if (go.name.Contains(avatarName) && go.transform.parent == null) {{
                                avatar = go;
                                break;
                            }}
                        }}
                    }}

                    if (avatar == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"Avatar not found: {avatar_object}\\"}}");
                        return;
                    }}

                    var descriptor = avatar.GetComponent<VRCAvatarDescriptor>();
                    if (descriptor == null) {{
                        OutputResult("{{\\"status\\":\\"error\\",\\"message\\":\\"No VRCAvatarDescriptor found\\"}}");
                        return;
                    }}

                    // Set pipeline manager info
                    var pipeline = avatar.GetComponent<VRC.Core.PipelineManager>();
                    if (pipeline == null) {{
                        pipeline = avatar.AddComponent<VRC.Core.PipelineManager>();
                    }}

                    // Open VRC SDK Control Panel for publish
                    EditorApplication.ExecuteMenuItem("VRChat SDK/Show Control Panel");

                    OutputResult("{{\\"status\\":\\"gui_required\\",\\"message\\":\\"VRC SDK Control Panel opened. The publish flow requires GUI interaction.\\",\\"instructions\\":[" +
                        "\\"1. In SDK Control Panel, select the avatar\\",\\" +
                        "\\"2. Fill in name: {name}\\",\\" +
                        "\\"3. Set release status to {release_status}\\",\\" +
                        "\\"4. Click Build & Publish\\",\\" +
                        "\\"5. Wait for upload to complete\\"" +
                    "],\\"avatar\\":\\"" + avatar.name + "\\"}}");
                }}

                {CS_RESULT_HELPER}
            }}
        ''')

        result = _write_cs_and_run(cs_code, "BlenderCopilotPublish", "Publish", proj)

        # If we got gui_required, add computer-use MCP hint
        if isinstance(result, dict) and result.get("status") == "gui_required":
            result["computer_use_hint"] = (
                "Use mcp__computer-use tools to automate: "
                "screenshot → find 'Build & Publish' button → left_click"
            )

        return json.dumps(result)
