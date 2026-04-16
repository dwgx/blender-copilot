"""
Modifier registry tools — adapted from CLI-Anything modifiers.py patterns.

Provides type-safe modifier application with parameter validation,
batch modifier operations, and common modifier presets.
Supports 15+ Blender modifier types with documented parameters.
"""
from typing import Dict, Any, List, Optional


# ─── Modifier Registry ───────────────────────────────────────────────────────

MODIFIER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "SUBSURF": {
        "bpy_type": "SUBSURF",
        "params": {
            "levels": {"type": "int", "default": 1, "min": 0, "max": 6, "desc": "Viewport subdivision level"},
            "render_levels": {"type": "int", "default": 2, "min": 0, "max": 6, "desc": "Render subdivision level"},
            "uv_smooth": {"type": "str", "default": "PRESERVE_BOUNDARIES", "options": ["NONE", "PRESERVE_CORNERS", "PRESERVE_BOUNDARIES", "PRESERVE_CORNERS_AND_JUNCTIONS", "PRESERVE_CORNERS_JUNCTIONS_AND_CONCAVE", "SMOOTH_ALL"], "desc": "UV smoothing mode"},
            "subdivision_type": {"type": "str", "default": "CATMULL_CLARK", "options": ["CATMULL_CLARK", "SIMPLE"], "desc": "Subdivision algorithm"},
        },
        "description": "Subdivision Surface — smooth mesh by subdividing faces",
    },
    "MIRROR": {
        "bpy_type": "MIRROR",
        "params": {
            "use_axis": {"type": "list", "default": [True, False, False], "desc": "Mirror axes [X, Y, Z]"},
            "use_bisect_axis": {"type": "list", "default": [False, False, False], "desc": "Bisect axes [X, Y, Z]"},
            "use_clip": {"type": "bool", "default": True, "desc": "Prevent vertices crossing mirror plane"},
            "merge_threshold": {"type": "float", "default": 0.001, "min": 0.0, "max": 1.0, "desc": "Distance within which to merge vertices"},
        },
        "description": "Mirror — mirror mesh across axes",
    },
    "ARRAY": {
        "bpy_type": "ARRAY",
        "params": {
            "count": {"type": "int", "default": 2, "min": 1, "max": 1000, "desc": "Number of copies"},
            "use_relative_offset": {"type": "bool", "default": True, "desc": "Use relative offset"},
            "relative_offset_displace": {"type": "list", "default": [1.0, 0.0, 0.0], "desc": "Relative offset [X, Y, Z]"},
            "use_constant_offset": {"type": "bool", "default": False, "desc": "Use constant offset"},
            "constant_offset_displace": {"type": "list", "default": [0.0, 0.0, 0.0], "desc": "Constant offset [X, Y, Z]"},
            "use_merge_vertices": {"type": "bool", "default": False, "desc": "Merge adjacent vertices"},
        },
        "description": "Array — create copies in a pattern",
    },
    "BEVEL": {
        "bpy_type": "BEVEL",
        "params": {
            "width": {"type": "float", "default": 0.1, "min": 0.0, "max": 100.0, "desc": "Bevel width"},
            "segments": {"type": "int", "default": 1, "min": 1, "max": 100, "desc": "Number of segments"},
            "limit_method": {"type": "str", "default": "NONE", "options": ["NONE", "ANGLE", "WEIGHT", "VGROUP"], "desc": "Limit method"},
            "angle_limit": {"type": "float", "default": 0.523599, "min": 0.0, "max": 3.14159, "desc": "Angle limit (radians)"},
            "affect": {"type": "str", "default": "EDGES", "options": ["VERTICES", "EDGES"], "desc": "What to bevel"},
            "profile": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0, "desc": "Bevel profile shape"},
        },
        "description": "Bevel — round off edges/vertices",
    },
    "SOLIDIFY": {
        "bpy_type": "SOLIDIFY",
        "params": {
            "thickness": {"type": "float", "default": 0.01, "min": -10.0, "max": 10.0, "desc": "Shell thickness"},
            "offset": {"type": "float", "default": -1.0, "min": -1.0, "max": 1.0, "desc": "Offset direction (-1=inward, 0=center, 1=outward)"},
            "use_even_offset": {"type": "bool", "default": True, "desc": "Maintain even thickness"},
            "use_rim": {"type": "bool", "default": True, "desc": "Fill rim between inner and outer"},
        },
        "description": "Solidify — give thickness to thin surfaces",
    },
    "BOOLEAN": {
        "bpy_type": "BOOLEAN",
        "params": {
            "operation": {"type": "str", "default": "DIFFERENCE", "options": ["INTERSECT", "UNION", "DIFFERENCE"], "desc": "Boolean operation type"},
            "solver": {"type": "str", "default": "FAST", "options": ["FAST", "EXACT"], "desc": "Boolean solver"},
            "object": {"type": "object", "default": None, "desc": "Target object name (set via _target param)"},
        },
        "description": "Boolean — combine/subtract/intersect meshes",
    },
    "DECIMATE": {
        "bpy_type": "DECIMATE",
        "params": {
            "decimate_type": {"type": "str", "default": "COLLAPSE", "options": ["COLLAPSE", "UNSUBDIV", "DISSOLVE"], "desc": "Decimation method"},
            "ratio": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0, "desc": "Decimation ratio (1.0 = no change)"},
            "use_symmetry": {"type": "bool", "default": False, "desc": "Maintain symmetry"},
        },
        "description": "Decimate — reduce polygon count",
    },
    "SMOOTH": {
        "bpy_type": "SMOOTH",
        "params": {
            "factor": {"type": "float", "default": 0.5, "min": -10.0, "max": 10.0, "desc": "Smoothing factor"},
            "iterations": {"type": "int", "default": 1, "min": 0, "max": 32767, "desc": "Smoothing iterations"},
        },
        "description": "Smooth — smooth mesh geometry",
    },
    "SHRINKWRAP": {
        "bpy_type": "SHRINKWRAP",
        "params": {
            "wrap_method": {"type": "str", "default": "NEAREST_SURFACEPOINT", "options": ["NEAREST_SURFACEPOINT", "PROJECT", "NEAREST_VERTEX", "TARGET_PROJECT"], "desc": "Projection method"},
            "wrap_mode": {"type": "str", "default": "ON_SURFACE", "options": ["ON_SURFACE", "INSIDE", "OUTSIDE", "OUTSIDE_SURFACE", "ABOVE_SURFACE"], "desc": "Wrap mode"},
            "offset": {"type": "float", "default": 0.0, "min": -100.0, "max": 100.0, "desc": "Surface offset"},
        },
        "description": "Shrinkwrap — project mesh onto target surface",
    },
    "LATTICE": {
        "bpy_type": "LATTICE",
        "params": {
            "object": {"type": "object", "default": None, "desc": "Lattice object name"},
            "strength": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "desc": "Effect strength"},
        },
        "description": "Lattice — deform using lattice object",
    },
    "ARMATURE": {
        "bpy_type": "ARMATURE",
        "params": {
            "object": {"type": "object", "default": None, "desc": "Armature object name"},
            "use_deform_preserve_volume": {"type": "bool", "default": False, "desc": "Use dual quaternion for volume preservation"},
        },
        "description": "Armature — deform with skeleton bones",
    },
    "CLOTH": {
        "bpy_type": "CLOTH",
        "params": {
            "quality": {"type": "int", "default": 5, "min": 1, "max": 80, "desc": "Simulation quality steps"},
            "mass": {"type": "float", "default": 0.3, "min": 0.0, "max": 10.0, "desc": "Mass of cloth material", "attr": "settings.mass"},
            "tension_stiffness": {"type": "float", "default": 15.0, "min": 0.0, "max": 10000.0, "desc": "Tension spring stiffness", "attr": "settings.tension_stiffness"},
        },
        "description": "Cloth — cloth physics simulation",
    },
    "WEIGHTED_NORMAL": {
        "bpy_type": "WEIGHTED_NORMAL",
        "params": {
            "mode": {"type": "str", "default": "FACE_AREA", "options": ["FACE_AREA", "CORNER_ANGLE", "FACE_AREA_WITH_ANGLE"], "desc": "Weighting mode"},
            "weight": {"type": "int", "default": 50, "min": 1, "max": 100, "desc": "Weight strength"},
            "keep_sharp": {"type": "bool", "default": True, "desc": "Keep sharp edges"},
        },
        "description": "Weighted Normal — adjust normals by face area/angle",
    },
    "SKIN": {
        "bpy_type": "SKIN",
        "params": {
            "branch_smoothing": {"type": "float", "default": 0.0, "min": 0.0, "max": 1.0, "desc": "Branch joint smoothing"},
            "use_smooth_shade": {"type": "bool", "default": False, "desc": "Apply smooth shading"},
        },
        "description": "Skin — generate mesh skin from vertices/edges",
    },
    "WIREFRAME": {
        "bpy_type": "WIREFRAME",
        "params": {
            "thickness": {"type": "float", "default": 0.02, "min": 0.0, "max": 100.0, "desc": "Wire thickness"},
            "use_even_offset": {"type": "bool", "default": True, "desc": "Even thickness"},
            "use_replace": {"type": "bool", "default": True, "desc": "Replace original geometry"},
        },
        "description": "Wireframe — convert edges to wire mesh",
    },
}


def _validate_param(name: str, value: Any, spec: Dict[str, Any]) -> tuple:
    """Validate a parameter value against its spec. Returns (valid, value_or_error)."""
    ptype = spec["type"]
    if ptype == "int":
        try:
            v = int(value)
        except (TypeError, ValueError):
            return False, f"{name}: expected int, got {type(value).__name__}"
        if "min" in spec and v < spec["min"]:
            return False, f"{name}: {v} < min {spec['min']}"
        if "max" in spec and v > spec["max"]:
            return False, f"{name}: {v} > max {spec['max']}"
        return True, v
    elif ptype == "float":
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False, f"{name}: expected float, got {type(value).__name__}"
        if "min" in spec and v < spec["min"]:
            return False, f"{name}: {v} < min {spec['min']}"
        if "max" in spec and v > spec["max"]:
            return False, f"{name}: {v} > max {spec['max']}"
        return True, v
    elif ptype == "bool":
        return True, bool(value)
    elif ptype == "str":
        v = str(value)
        if "options" in spec and v not in spec["options"]:
            return False, f"{name}: '{v}' not in {spec['options']}"
        return True, v
    elif ptype == "list":
        if not isinstance(value, (list, tuple)):
            return False, f"{name}: expected list, got {type(value).__name__}"
        return True, list(value)
    elif ptype == "object":
        return True, str(value) if value else None
    return True, value


def register_modifier_tools(mcp, send_command_fn):
    """Register modifier registry MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def modifier_list_types() -> dict:
        """List all supported modifier types with descriptions and parameters.

        Returns detailed info about each modifier including parameter names,
        types, defaults, and valid ranges.
        """
        result = {}
        for mod_type, info in MODIFIER_REGISTRY.items():
            params_summary = {}
            for pname, pspec in info["params"].items():
                params_summary[pname] = {
                    "type": pspec["type"],
                    "default": pspec["default"],
                    "desc": pspec["desc"],
                }
                if "options" in pspec:
                    params_summary[pname]["options"] = pspec["options"]
                if "min" in pspec:
                    params_summary[pname]["range"] = f"{pspec['min']} — {pspec['max']}"
            result[mod_type] = {
                "description": info["description"],
                "params": params_summary,
            }
        return result

    @mcp.tool()
    def modifier_add(
        object_name: str,
        modifier_type: str,
        modifier_name: str = "",
        params: dict = None,
    ) -> dict:
        """Add a modifier to an object with validated parameters.

        Supports 15 modifier types with type checking and range validation.
        Invalid parameters are caught before sending to Blender.

        Args:
            object_name: Target object name
            modifier_type: Modifier type (SUBSURF, MIRROR, ARRAY, BEVEL, SOLIDIFY,
                          BOOLEAN, DECIMATE, SMOOTH, SHRINKWRAP, LATTICE, ARMATURE,
                          CLOTH, WEIGHTED_NORMAL, SKIN, WIREFRAME)
            modifier_name: Custom name for the modifier (auto-generated if empty)
            params: Dict of parameter overrides (see modifier_list_types for options)
        """
        mod_type_upper = modifier_type.upper()
        if mod_type_upper not in MODIFIER_REGISTRY:
            return {"error": f"Unknown modifier '{modifier_type}'. Available: {list(MODIFIER_REGISTRY.keys())}"}

        registry = MODIFIER_REGISTRY[mod_type_upper]
        bpy_type = registry["bpy_type"]
        mod_label = modifier_name or mod_type_upper

        # Validate params
        validated = {}
        errors = []
        if params:
            for key, value in params.items():
                if key.startswith("_"):
                    validated[key] = value
                    continue
                if key not in registry["params"]:
                    errors.append(f"Unknown param '{key}' for {mod_type_upper}. Valid: {list(registry['params'].keys())}")
                    continue
                ok, result = _validate_param(key, value, registry["params"][key])
                if not ok:
                    errors.append(result)
                else:
                    validated[key] = result

        if errors:
            return {"error": "Validation errors", "details": errors}

        # Build code
        lines = [
            "import bpy",
            f"obj = bpy.data.objects.get('{object_name}')",
            "if not obj:",
            f"    result = \"Error: Object '{object_name}' not found\"",
            "else:",
            f"    mod = obj.modifiers.new('{mod_label}', '{bpy_type}')",
        ]

        # Apply params
        for key, value in validated.items():
            if key.startswith("_"):
                continue
            spec = registry["params"].get(key, {})
            attr = spec.get("attr", key)  # Allow custom attribute paths

            if spec.get("type") == "object":
                if value:
                    lines.append(f"    target = bpy.data.objects.get('{value}')")
                    lines.append(f"    if target: mod.{attr} = target")
            elif spec.get("type") == "list":
                if key == "use_axis" or key == "use_bisect_axis":
                    for i, axis in enumerate(["x", "y", "z"]):
                        if i < len(value):
                            lines.append(f"    mod.use_{key.split('_')[-1]}_{axis} = {value[i]}")
                else:
                    lines.append(f"    mod.{attr} = {value}")
            elif isinstance(value, str):
                lines.append(f"    mod.{attr} = '{value}'")
            else:
                lines.append(f"    mod.{attr} = {value}")

        lines.append(f"    result = f'Added {{mod.type}} modifier \"{{mod.name}}\" to {{obj.name}}'")
        return _exec("\n".join(lines))

    @mcp.tool()
    def modifier_apply(object_name: str, modifier_name: str) -> dict:
        """Apply (finalize) a modifier on an object.

        This makes the modifier's effect permanent and removes it from the stack.
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    mod = obj.modifiers.get('{modifier_name}')
    if not mod:
        result = "Error: Modifier '{modifier_name}' not found on {object_name}"
    else:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier='{modifier_name}')
        result = f'Applied modifier {modifier_name} on {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def modifier_remove(object_name: str, modifier_name: str) -> dict:
        """Remove a modifier from an object without applying it."""
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    mod = obj.modifiers.get('{modifier_name}')
    if not mod:
        result = "Error: Modifier '{modifier_name}' not found on {object_name}"
    else:
        obj.modifiers.remove(mod)
        result = f'Removed modifier {modifier_name} from {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def modifier_list(object_name: str) -> dict:
        """List all modifiers on an object with their current settings."""
        code = f"""import bpy, json
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    mods = []
    for mod in obj.modifiers:
        mods.append({{
            'name': mod.name,
            'type': mod.type,
            'show_viewport': mod.show_viewport,
            'show_render': mod.show_render,
        }})
    result = json.dumps({{'object': obj.name, 'modifiers': mods, 'count': len(mods)}})
"""
        return _exec(code)

    @mcp.tool()
    def modifier_reorder(object_name: str, modifier_name: str, position: int) -> dict:
        """Move a modifier to a specific position in the stack.

        Args:
            object_name: Target object
            modifier_name: Modifier to move
            position: Target position (0 = top of stack)
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    mod = obj.modifiers.get('{modifier_name}')
    if not mod:
        result = "Error: Modifier '{modifier_name}' not found"
    else:
        current = list(obj.modifiers).index(mod)
        target = {position}
        bpy.context.view_layer.objects.active = obj
        while current > target:
            bpy.ops.object.modifier_move_up(modifier='{modifier_name}')
            current -= 1
        while current < target:
            bpy.ops.object.modifier_move_down(modifier='{modifier_name}')
            current += 1
        result = f'Moved {{mod.name}} to position {position}'
"""
        return _exec(code)

    @mcp.tool()
    def modifier_apply_all(object_name: str) -> dict:
        """Apply all modifiers on an object in stack order."""
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    count = len(obj.modifiers)
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as e:
            pass
    remaining = len(obj.modifiers)
    result = f'Applied {{count - remaining}}/{{count}} modifiers on {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def modifier_batch_add(
        object_names: list,
        modifier_type: str,
        params: dict = None,
    ) -> dict:
        """Add the same modifier to multiple objects at once.

        Args:
            object_names: List of object names
            modifier_type: Modifier type (see modifier_add)
            params: Parameter overrides
        """
        mod_type_upper = modifier_type.upper()
        if mod_type_upper not in MODIFIER_REGISTRY:
            return {"error": f"Unknown modifier '{modifier_type}'"}

        registry = MODIFIER_REGISTRY[mod_type_upper]
        bpy_type = registry["bpy_type"]

        # Validate params
        validated = {}
        if params:
            for key, value in params.items():
                if key in registry["params"]:
                    ok, result = _validate_param(key, value, registry["params"][key])
                    if ok:
                        validated[key] = result

        names_str = str(object_names)
        lines = [
            "import bpy",
            f"names = {names_str}",
            "added = []",
            "for name in names:",
            "    obj = bpy.data.objects.get(name)",
            "    if obj:",
            f"        mod = obj.modifiers.new('{mod_type_upper}', '{bpy_type}')",
        ]

        for key, value in validated.items():
            spec = registry["params"].get(key, {})
            attr = spec.get("attr", key)
            if isinstance(value, str):
                lines.append(f"        mod.{attr} = '{value}'")
            else:
                lines.append(f"        mod.{attr} = {value}")

        lines.extend([
            "        added.append(name)",
            f"result = f'Added {mod_type_upper} to {{len(added)}}/{{len(names)}} objects: {{added}}'",
        ])
        return _exec("\n".join(lines))

    @mcp.tool()
    def modifier_preset_smooth_shade(object_name: str, subdiv_levels: int = 2) -> dict:
        """Apply common smooth shading preset: Subdivision Surface + Smooth Shading + Weighted Normal.

        A one-click polish for any mesh — adds subdivision, smooth shading,
        and weighted normals for clean rendering.
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj

    # Subdivision Surface
    sub = obj.modifiers.new('Subdivision', 'SUBSURF')
    sub.levels = min({subdiv_levels}, 3)
    sub.render_levels = {subdiv_levels}

    # Smooth shading
    bpy.ops.object.shade_smooth()

    # Weighted Normal
    wn = obj.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
    wn.mode = 'FACE_AREA'
    wn.weight = 50
    wn.keep_sharp = True

    verts = len(obj.data.vertices)
    result = f'Smooth preset on {{obj.name}}: SubD({subdiv_levels}) + Smooth + WeightedNormal ({{verts}} verts)'
"""
        return _exec(code)
