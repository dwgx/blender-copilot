"""
Script execution tools — merged from HKUDS/CLI-Anything approach.

Provides fallback execution mode: generate bpy scripts and run them
via `blender --background --python`, bypassing TCP socket entirely.
Solves the timeout problem for heavy mesh/bmesh operations.

Also provides JSON scene → bpy script generation for declarative scene building.
"""
import json
import math
import os
import tempfile
from typing import Dict, Any, List, Optional


# ─── bpy Script Generator (adapted from CLI-Anything bpy_gen.py) ────────────

def generate_bpy_script(scene_json: Dict[str, Any], output_path: str = "") -> str:
    """Generate a complete bpy Python script from a scene JSON description.

    The scene JSON format:
    {
        "scene": {"name": "...", "unit_system": "METRIC", ...},
        "render": {"engine": "EEVEE", "resolution_x": 1920, ...},
        "materials": [{"name": "Skin", "color": [1,0.88,0.82,1], ...}],
        "objects": [{"mesh_type": "sphere", "name": "Head", "location": [0,0,1.8], ...}],
        "cameras": [{"name": "Cam", "location": [0,-3,1], "focal_length": 85}],
        "lights": [{"name": "Key", "type": "AREA", "location": [2,-2,3], "power": 200}],
    }
    """
    lines = [
        "#!/usr/bin/env python3",
        '"""Auto-generated Blender script from blender-copilot."""',
        "",
        "import bpy",
        "import math",
        "",
        "# ── Clear Scene ──",
        "bpy.ops.object.select_all(action='SELECT')",
        "bpy.ops.object.delete(use_global=False)",
        "",
    ]

    lines.extend(_gen_render_settings(scene_json))
    lines.extend(_gen_materials(scene_json))
    lines.extend(_gen_objects(scene_json))
    lines.extend(_gen_cameras(scene_json))
    lines.extend(_gen_lights(scene_json))

    if output_path:
        lines.extend([
            "",
            "# ── Render ──",
            f"bpy.context.scene.render.filepath = r'{output_path}'",
            "bpy.ops.render.render(write_still=True)",
            f"print('Rendered: {output_path}')",
        ])

    lines.append("")
    lines.append("result = f'Scene built: {len(bpy.data.objects)} objects'")

    return "\n".join(lines)


def _gen_render_settings(scene: Dict[str, Any]) -> List[str]:
    render = scene.get("render", {})
    engine = render.get("engine", "EEVEE")
    engine_map = {"CYCLES": "CYCLES", "EEVEE": "BLENDER_EEVEE", "WORKBENCH": "BLENDER_WORKBENCH"}

    lines = ["# ── Render Settings ──"]
    lines.append(f"bpy.context.scene.render.engine = '{engine_map.get(engine, 'BLENDER_EEVEE')}'")
    if "resolution_x" in render:
        lines.append(f"bpy.context.scene.render.resolution_x = {render['resolution_x']}")
    if "resolution_y" in render:
        lines.append(f"bpy.context.scene.render.resolution_y = {render['resolution_y']}")
    if engine == "CYCLES" and "samples" in render:
        lines.append(f"bpy.context.scene.cycles.samples = {render['samples']}")
    lines.append("")
    return lines


def _gen_materials(scene: Dict[str, Any]) -> List[str]:
    materials = scene.get("materials", [])
    if not materials:
        return []

    lines = ["# ── Materials ──"]
    for mat in materials:
        name = mat.get("name", "Material")
        var = _safe_var(name)
        color = mat.get("color", [0.8, 0.8, 0.8, 1.0])
        if len(color) == 3:
            color = list(color) + [1.0]
        metallic = mat.get("metallic", 0.0)
        roughness = mat.get("roughness", 0.5)

        lines.extend([
            f"mat_{var} = bpy.data.materials.new('{name}')",
            f"mat_{var}.use_nodes = True",
            f"_bsdf = mat_{var}.node_tree.nodes.get('Principled BSDF')",
            f"if _bsdf:",
            f"    _bsdf.inputs['Base Color'].default_value = ({color[0]}, {color[1]}, {color[2]}, {color[3]})",
            f"    _bsdf.inputs['Metallic'].default_value = {metallic}",
            f"    _bsdf.inputs['Roughness'].default_value = {roughness}",
            "",
        ])
    return lines


def _gen_objects(scene: Dict[str, Any]) -> List[str]:
    objects = scene.get("objects", [])
    if not objects:
        return []

    materials = scene.get("materials", [])
    mat_names = {m.get("name"): _safe_var(m["name"]) for m in materials if "name" in m}

    lines = ["# ── Objects ──"]
    for obj in objects:
        mesh_type = obj.get("mesh_type", "cube")
        name = obj.get("name", "Object")
        loc = obj.get("location", [0, 0, 0])
        rot = obj.get("rotation", [0, 0, 0])
        scl = obj.get("scale", [1, 1, 1])
        params = obj.get("mesh_params", {})
        collection = obj.get("collection")

        lines.append(f"# {name}")

        # Primitive creation
        ops_map = {
            "cube": f"bpy.ops.mesh.primitive_cube_add(size={params.get('size', 2)}, location=({loc[0]}, {loc[1]}, {loc[2]}))",
            "sphere": f"bpy.ops.mesh.primitive_uv_sphere_add(radius={params.get('radius', 1)}, segments={params.get('segments', 32)}, ring_count={params.get('rings', 16)}, location=({loc[0]}, {loc[1]}, {loc[2]}))",
            "cylinder": f"bpy.ops.mesh.primitive_cylinder_add(radius={params.get('radius', 1)}, depth={params.get('depth', 2)}, vertices={params.get('vertices', 32)}, location=({loc[0]}, {loc[1]}, {loc[2]}))",
            "cone": f"bpy.ops.mesh.primitive_cone_add(radius1={params.get('radius1', 1)}, radius2={params.get('radius2', 0)}, depth={params.get('depth', 2)}, location=({loc[0]}, {loc[1]}, {loc[2]}))",
            "plane": f"bpy.ops.mesh.primitive_plane_add(size={params.get('size', 2)}, location=({loc[0]}, {loc[1]}, {loc[2]}))",
            "torus": f"bpy.ops.mesh.primitive_torus_add(major_radius={params.get('major_radius', 1)}, minor_radius={params.get('minor_radius', 0.25)}, location=({loc[0]}, {loc[1]}, {loc[2]}))",
            "monkey": f"bpy.ops.mesh.primitive_monkey_add(location=({loc[0]}, {loc[1]}, {loc[2]}))",
        }

        if mesh_type in ops_map:
            lines.append(ops_map[mesh_type])
        else:
            lines.append(f"bpy.ops.mesh.primitive_cube_add(location=({loc[0]}, {loc[1]}, {loc[2]}))")

        lines.append("_obj = bpy.context.active_object")
        lines.append(f"_obj.name = '{name}'")
        if rot != [0, 0, 0]:
            lines.append(f"_obj.rotation_euler = (math.radians({rot[0]}), math.radians({rot[1]}), math.radians({rot[2]}))")
        if scl != [1, 1, 1]:
            lines.append(f"_obj.scale = ({scl[0]}, {scl[1]}, {scl[2]})")

        # Apply scale if non-uniform
        if scl != [1, 1, 1]:
            lines.append("bpy.ops.object.transform_apply(scale=True)")

        # Smooth shading
        if obj.get("smooth", False):
            lines.append("bpy.ops.object.shade_smooth()")

        # Material assignment
        mat_name = obj.get("material")
        if mat_name and mat_name in mat_names:
            var = mat_names[mat_name]
            lines.append(f"_obj.data.materials.append(mat_{var})")

        # Modifiers
        for mod in obj.get("modifiers", []):
            mod_type = mod.get("type", "")
            bpy_type = mod.get("bpy_type", _modifier_bpy_type(mod_type))
            mod_name = mod.get("name", mod_type)
            lines.append(f"_mod = _obj.modifiers.new('{mod_name}', '{bpy_type}')")
            for k, v in mod.get("params", {}).items():
                lines.append(f"_mod.{k} = {v}")

        # Collection
        if collection:
            lines.extend([
                f"_col = bpy.data.collections.get('{collection}')",
                "if _col:",
                "    for c in _obj.users_collection: c.objects.unlink(_obj)",
                "    _col.objects.link(_obj)",
            ])

        lines.append("")

    return lines


def _gen_cameras(scene: Dict[str, Any]) -> List[str]:
    cameras = scene.get("cameras", [])
    if not cameras:
        return []

    lines = ["# ── Cameras ──"]
    for cam in cameras:
        name = cam.get("name", "Camera")
        loc = cam.get("location", [0, -5, 2])
        rot = cam.get("rotation", [80, 0, 0])
        focal = cam.get("focal_length", 50)

        lines.extend([
            f"_cam_data = bpy.data.cameras.new('{name}')",
            f"_cam_data.lens = {focal}",
            f"_cam = bpy.data.objects.new('{name}', _cam_data)",
            "bpy.context.collection.objects.link(_cam)",
            f"_cam.location = ({loc[0]}, {loc[1]}, {loc[2]})",
            f"_cam.rotation_euler = (math.radians({rot[0]}), math.radians({rot[1]}), math.radians({rot[2]}))",
        ])
        if cam.get("active", False):
            lines.append("bpy.context.scene.camera = _cam")
        lines.append("")
    return lines


def _gen_lights(scene: Dict[str, Any]) -> List[str]:
    lights = scene.get("lights", [])
    if not lights:
        return []

    lines = ["# ── Lights ──"]
    for light in lights:
        name = light.get("name", "Light")
        ltype = light.get("type", "POINT")
        loc = light.get("location", [0, 0, 3])
        rot = light.get("rotation", [0, 0, 0])
        power = light.get("power", 1000)
        color = light.get("color", [1, 1, 1])

        lines.extend([
            f"_ld = bpy.data.lights.new('{name}', '{ltype}')",
            f"_ld.energy = {power}",
            f"_ld.color = ({color[0]}, {color[1]}, {color[2]})",
        ])
        if ltype == "AREA":
            lines.append(f"_ld.size = {light.get('size', 1)}")
        lines.extend([
            f"_lo = bpy.data.objects.new('{name}', _ld)",
            "bpy.context.collection.objects.link(_lo)",
            f"_lo.location = ({loc[0]}, {loc[1]}, {loc[2]})",
            f"_lo.rotation_euler = (math.radians({rot[0]}), math.radians({rot[1]}), math.radians({rot[2]}))",
            "",
        ])
    return lines


def _safe_var(name: str) -> str:
    result = name.replace(" ", "_").replace(".", "_").replace("-", "_")
    result = "".join(c for c in result if c.isalnum() or c == "_")
    if result and result[0].isdigit():
        result = "_" + result
    return result or "unnamed"


def _modifier_bpy_type(mod_type: str) -> str:
    mapping = {
        "subdivision_surface": "SUBSURF",
        "mirror": "MIRROR",
        "array": "ARRAY",
        "bevel": "BEVEL",
        "solidify": "SOLIDIFY",
        "decimate": "DECIMATE",
        "boolean": "BOOLEAN",
        "smooth": "SMOOTH",
    }
    return mapping.get(mod_type, mod_type.upper())


# ─── MCP Tool Registration ──────────────────────────────────────────────────

def register_script_tools(mcp, send_command_fn):
    """Register script execution MCP tools."""

    from .server import run_blender_script

    @mcp.tool()
    def execute_script_headless(code: str, timeout: int = 300) -> dict:
        """Execute Python code directly in Blender headless mode (no TCP).

        Use this for heavy operations that timeout over the socket connection:
        - Complex bmesh mesh creation (many vertices/faces)
        - Batch operations on many objects
        - File import/export operations
        - Any operation that takes > 2 minutes

        The code runs in a fresh Blender instance via subprocess.
        Variable 'result' will be captured as the return value.
        """
        return run_blender_script(code, timeout=timeout)

    @mcp.tool()
    def execute_script_on_file(blend_file: str, code: str, save: bool = True, timeout: int = 300) -> dict:
        """Execute Python code on an existing .blend file in headless mode.

        Opens the file, runs the code, optionally saves.
        Great for batch modifications to existing files.
        """
        import shutil

        wrapper = f'''import bpy
bpy.ops.wm.open_mainfile(filepath=r"{blend_file}")
{code}
{"bpy.ops.wm.save_mainfile()" if save else ""}
result = f"Executed on {{blend_file}}"
'''
        return run_blender_script(wrapper, timeout=timeout)

    @mcp.tool()
    def build_scene_from_json(scene_json: str, blend_output: str = "", render_output: str = "") -> dict:
        """Build a complete Blender scene from a JSON description.

        Generates a bpy script from the JSON and executes it in headless Blender.
        Adapted from CLI-Anything's scene building approach.

        The JSON format supports:
        - materials: [{name, color, metallic, roughness}]
        - objects: [{mesh_type, name, location, rotation, scale, material, modifiers, collection, smooth}]
        - cameras: [{name, location, rotation, focal_length, active}]
        - lights: [{name, type, location, rotation, power, color, size}]
        - render: {engine, resolution_x, resolution_y, samples}

        Example:
        {
            "materials": [{"name": "Red", "color": [1,0,0,1]}],
            "objects": [
                {"mesh_type": "sphere", "name": "Ball", "location": [0,0,1],
                 "material": "Red", "smooth": true,
                 "modifiers": [{"type": "subdivision_surface", "params": {"levels": 2}}]}
            ],
            "cameras": [{"name": "Cam", "location": [0,-5,2], "rotation": [80,0,0], "focal_length": 85, "active": true}],
            "lights": [{"name": "Key", "type": "AREA", "location": [2,-2,3], "power": 200}]
        }
        """
        scene = json.loads(scene_json) if isinstance(scene_json, str) else scene_json

        script = generate_bpy_script(scene, output_path=render_output)

        # Add save if requested
        if blend_output:
            script += f"\nbpy.ops.wm.save_as_mainfile(filepath=r'{blend_output}')"
            script += f"\nresult = f'Saved: {blend_output}'"

        return run_blender_script(script, timeout=300)

    @mcp.tool()
    def generate_scene_script(scene_json: str) -> str:
        """Generate a bpy Python script from a JSON scene description WITHOUT executing it.

        Returns the script as a string for review or manual execution.
        See build_scene_from_json for the JSON format.
        """
        scene = json.loads(scene_json) if isinstance(scene_json, str) else scene_json
        return generate_bpy_script(scene)
