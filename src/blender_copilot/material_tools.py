"""
Material tools — advanced material creation and management.

Provides PBR material creation, node-based material editing,
material assignment, and common material presets.
"""
from typing import Dict, Any, List, Optional


# ─── Material Presets ─────────────────────────────────────────────────────────

MATERIAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "glossy_plastic": {
        "base_color": [0.8, 0.1, 0.1, 1.0],
        "metallic": 0.0,
        "roughness": 0.2,
        "specular": 0.5,
        "description": "Shiny plastic surface",
    },
    "matte_plastic": {
        "base_color": [0.5, 0.5, 0.5, 1.0],
        "metallic": 0.0,
        "roughness": 0.8,
        "specular": 0.3,
        "description": "Matte plastic surface",
    },
    "brushed_metal": {
        "base_color": [0.7, 0.7, 0.7, 1.0],
        "metallic": 1.0,
        "roughness": 0.4,
        "specular": 0.5,
        "description": "Brushed metal finish",
    },
    "polished_metal": {
        "base_color": [0.9, 0.9, 0.9, 1.0],
        "metallic": 1.0,
        "roughness": 0.05,
        "specular": 0.8,
        "description": "Mirror-polished metal",
    },
    "gold": {
        "base_color": [1.0, 0.766, 0.336, 1.0],
        "metallic": 1.0,
        "roughness": 0.2,
        "specular": 0.5,
        "description": "Gold metal",
    },
    "glass": {
        "base_color": [0.95, 0.95, 0.95, 1.0],
        "metallic": 0.0,
        "roughness": 0.0,
        "specular": 0.5,
        "transmission": 1.0,
        "ior": 1.45,
        "description": "Clear glass",
    },
    "rubber": {
        "base_color": [0.15, 0.15, 0.15, 1.0],
        "metallic": 0.0,
        "roughness": 0.95,
        "specular": 0.2,
        "description": "Black rubber",
    },
    "wood": {
        "base_color": [0.4, 0.24, 0.1, 1.0],
        "metallic": 0.0,
        "roughness": 0.7,
        "specular": 0.3,
        "description": "Natural wood tone",
    },
    "skin": {
        "base_color": [0.87, 0.72, 0.63, 1.0],
        "metallic": 0.0,
        "roughness": 0.5,
        "specular": 0.3,
        "subsurface": 0.3,
        "subsurface_color": [0.7, 0.1, 0.1],
        "description": "Human skin (caucasian)",
    },
    "skin_anime": {
        "base_color": [1.0, 0.88, 0.82, 1.0],
        "metallic": 0.0,
        "roughness": 0.45,
        "specular": 0.4,
        "description": "Anime-style skin (bright, smooth)",
    },
    "fabric": {
        "base_color": [0.3, 0.3, 0.6, 1.0],
        "metallic": 0.0,
        "roughness": 0.9,
        "specular": 0.1,
        "sheen": 0.5,
        "description": "Cloth/fabric material",
    },
    "emissive": {
        "base_color": [1.0, 1.0, 1.0, 1.0],
        "metallic": 0.0,
        "roughness": 0.5,
        "emission_color": [1.0, 0.5, 0.0],
        "emission_strength": 5.0,
        "description": "Self-illuminating emissive",
    },
}


def register_material_tools(mcp, send_command_fn):
    """Register material creation and management MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def material_list_presets() -> dict:
        """List all material presets with descriptions.

        Presets: glossy_plastic, matte_plastic, brushed_metal, polished_metal,
        gold, glass, rubber, wood, skin, skin_anime, fabric, emissive.
        """
        return {
            "presets": {
                name: p["description"] for name, p in MATERIAL_PRESETS.items()
            }
        }

    @mcp.tool()
    def material_create_preset(
        preset_name: str,
        material_name: str = "",
        color_override: list = None,
    ) -> dict:
        """Create a material from a preset and optionally assign it.

        Args:
            preset_name: One of the preset names (see material_list_presets)
            material_name: Custom name for the material (auto if empty)
            color_override: Override base color [r, g, b, a] (0-1 range)
        """
        if preset_name not in MATERIAL_PRESETS:
            return {"error": f"Unknown preset '{preset_name}'. Available: {list(MATERIAL_PRESETS.keys())}"}

        p = MATERIAL_PRESETS[preset_name]
        mat_name = material_name or preset_name.replace("_", " ").title()
        color = color_override or p["base_color"]
        if len(color) == 3:
            color = list(color) + [1.0]

        code = f"""import bpy
mat = bpy.data.materials.new('{mat_name}')
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
if bsdf:
    bsdf.inputs['Base Color'].default_value = ({color[0]}, {color[1]}, {color[2]}, {color[3]})
    bsdf.inputs['Metallic'].default_value = {p['metallic']}
    bsdf.inputs['Roughness'].default_value = {p['roughness']}
"""
        if "specular" in p:
            code += f"    bsdf.inputs['Specular IOR Level'].default_value = {p['specular']}\n"
        if "transmission" in p:
            code += f"    bsdf.inputs['Transmission Weight'].default_value = {p['transmission']}\n"
        if "ior" in p:
            code += f"    bsdf.inputs['IOR'].default_value = {p['ior']}\n"
        if "subsurface" in p:
            code += f"    bsdf.inputs['Subsurface Weight'].default_value = {p['subsurface']}\n"
        if "subsurface_color" in p:
            sc = p["subsurface_color"]
            code += f"    bsdf.inputs['Subsurface Radius'].default_value = ({sc[0]}, {sc[1]}, {sc[2]})\n"
        if "emission_color" in p:
            ec = p["emission_color"]
            code += f"    bsdf.inputs['Emission Color'].default_value = ({ec[0]}, {ec[1]}, {ec[2]}, 1.0)\n"
        if "emission_strength" in p:
            code += f"    bsdf.inputs['Emission Strength'].default_value = {p['emission_strength']}\n"

        code += f"result = f'Created material: {{mat.name}} ({preset_name})'\n"
        return _exec(code)

    @mcp.tool()
    def material_create_pbr(
        name: str,
        base_color: list = None,
        metallic: float = 0.0,
        roughness: float = 0.5,
        specular: float = 0.5,
        transmission: float = 0.0,
        ior: float = 1.45,
        emission_color: list = None,
        emission_strength: float = 0.0,
        alpha: float = 1.0,
    ) -> dict:
        """Create a custom PBR material with full control.

        Args:
            name: Material name
            base_color: [r, g, b, a] color (0-1 range)
            metallic: 0.0 (dielectric) to 1.0 (metal)
            roughness: 0.0 (mirror) to 1.0 (diffuse)
            specular: Specular reflection strength
            transmission: 0.0 (opaque) to 1.0 (transparent)
            ior: Index of refraction (glass=1.45, water=1.33, diamond=2.42)
            emission_color: [r, g, b] for self-illumination
            emission_strength: Emission power
            alpha: Overall opacity
        """
        base_color = base_color or [0.8, 0.8, 0.8, 1.0]
        if len(base_color) == 3:
            base_color = list(base_color) + [1.0]

        code = f"""import bpy
mat = bpy.data.materials.new('{name}')
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
if bsdf:
    bsdf.inputs['Base Color'].default_value = ({base_color[0]}, {base_color[1]}, {base_color[2]}, {base_color[3]})
    bsdf.inputs['Metallic'].default_value = {metallic}
    bsdf.inputs['Roughness'].default_value = {roughness}
    bsdf.inputs['Specular IOR Level'].default_value = {specular}
    bsdf.inputs['Transmission Weight'].default_value = {transmission}
    bsdf.inputs['IOR'].default_value = {ior}
    bsdf.inputs['Alpha'].default_value = {alpha}
"""
        if emission_color:
            code += f"    bsdf.inputs['Emission Color'].default_value = ({emission_color[0]}, {emission_color[1]}, {emission_color[2]}, 1.0)\n"
            code += f"    bsdf.inputs['Emission Strength'].default_value = {emission_strength}\n"

        if alpha < 1.0:
            code += "mat.blend_method = 'BLEND'\n"

        code += f"result = f'Created PBR material: {{mat.name}}'\n"
        return _exec(code)

    @mcp.tool()
    def material_assign(object_name: str, material_name: str, slot_index: int = -1) -> dict:
        """Assign a material to an object.

        Args:
            object_name: Target object
            material_name: Material name (must exist in bpy.data.materials)
            slot_index: Material slot (-1 = append new slot, 0+ = replace slot)
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
mat = bpy.data.materials.get('{material_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
elif not mat:
    result = "Error: Material '{material_name}' not found"
else:
    if {slot_index} >= 0 and {slot_index} < len(obj.data.materials):
        obj.data.materials[{slot_index}] = mat
    else:
        obj.data.materials.append(mat)
    result = f'Assigned {{mat.name}} to {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def material_list(object_name: str = "") -> dict:
        """List materials — on a specific object or all materials in the scene.

        Args:
            object_name: Object name (empty = list all scene materials)
        """
        if object_name:
            code = f"""import bpy, json
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
elif not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
    result = json.dumps({{'object': '{object_name}', 'materials': []}})
else:
    mats = []
    for i, mat in enumerate(obj.data.materials):
        mats.append({{'slot': i, 'name': mat.name if mat else '(empty)'}})
    result = json.dumps({{'object': '{object_name}', 'materials': mats}})
"""
        else:
            code = """import bpy, json
mats = []
for mat in bpy.data.materials:
    info = {'name': mat.name, 'users': mat.users, 'use_nodes': mat.use_nodes}
    if mat.use_nodes:
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bc = bsdf.inputs['Base Color'].default_value
            info['base_color'] = [round(bc[0], 3), round(bc[1], 3), round(bc[2], 3)]
            info['metallic'] = round(bsdf.inputs['Metallic'].default_value, 3)
            info['roughness'] = round(bsdf.inputs['Roughness'].default_value, 3)
    mats.append(info)
result = json.dumps({'materials': mats, 'count': len(mats)}, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def material_duplicate(material_name: str, new_name: str = "") -> dict:
        """Duplicate an existing material.

        Args:
            material_name: Source material name
            new_name: Name for the copy (auto if empty)
        """
        new = new_name or f"{material_name}_copy"
        code = f"""import bpy
src = bpy.data.materials.get('{material_name}')
if not src:
    result = "Error: Material '{material_name}' not found"
else:
    copy = src.copy()
    copy.name = '{new}'
    result = f'Duplicated: {{src.name}} → {{copy.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def material_set_texture(
        material_name: str,
        texture_path: str,
        texture_type: str = "base_color",
    ) -> dict:
        """Add an image texture to a material's Principled BSDF.

        Args:
            material_name: Target material
            texture_path: Path to image file
            texture_type: Where to connect:
                - base_color: Albedo/diffuse
                - normal: Normal map
                - roughness: Roughness map
                - metallic: Metallic map
                - emission: Emission map
        """
        input_map = {
            "base_color": "Base Color",
            "normal": "Normal",
            "roughness": "Roughness",
            "metallic": "Metallic",
            "emission": "Emission Color",
        }
        if texture_type not in input_map:
            return {"error": f"Unknown texture_type '{texture_type}'. Valid: {list(input_map.keys())}"}

        bsdf_input = input_map[texture_type]

        code = f"""import bpy
mat = bpy.data.materials.get('{material_name}')
if not mat:
    result = "Error: Material '{material_name}' not found"
else:
    if not mat.use_nodes:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    if not bsdf:
        result = "Error: No Principled BSDF node found"
    else:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(r'{texture_path}')
        tex.location = (bsdf.location.x - 300, bsdf.location.y)
"""
        if texture_type == "normal":
            code += """
        nmap = nt.nodes.new('ShaderNodeNormalMap')
        nmap.location = (bsdf.location.x - 150, bsdf.location.y - 200)
        nt.links.new(tex.outputs['Color'], nmap.inputs['Color'])
        nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
        tex.image.colorspace_settings.name = 'Non-Color'
"""
        elif texture_type in ("roughness", "metallic"):
            code += f"""
        nt.links.new(tex.outputs['Color'], bsdf.inputs['{bsdf_input}'])
        tex.image.colorspace_settings.name = 'Non-Color'
"""
        else:
            code += f"""
        nt.links.new(tex.outputs['Color'], bsdf.inputs['{bsdf_input}'])
"""
        code += f"        result = f'Added {{texture_type}} texture to {{mat.name}}'\n"
        return _exec(code)
