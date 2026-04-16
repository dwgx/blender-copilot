"""
UV tools — UV mapping, unwrapping, and texture coordinate management.

Provides smart unwrap, UV projection methods, UV island operations,
and UV layout utilities for the MCP pipeline.
"""
from typing import Dict, Any, List, Optional


def register_uv_tools(mcp, send_command_fn):
    """Register UV mapping MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def uv_smart_unwrap(
        object_name: str,
        angle_limit: float = 66.0,
        island_margin: float = 0.02,
        area_weight: float = 0.0,
    ) -> dict:
        """Smart UV Project — automatic UV unwrapping based on face angles.

        Works well for hard-surface models, mechanical parts, and props.

        Args:
            object_name: Target mesh object
            angle_limit: Angle limit for projection (degrees, default 66)
            island_margin: Margin between UV islands (default 0.02)
            area_weight: Weight given to face area (0-1)
        """
        code = f"""import bpy, math
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(
        angle_limit=math.radians({angle_limit}),
        island_margin={island_margin},
        area_weight={area_weight},
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    uv_count = len(obj.data.uv_layers)
    result = f'Smart UV unwrap on {{obj.name}}: {{uv_count}} UV layers'
"""
        return _exec(code)

    @mcp.tool()
    def uv_unwrap(
        object_name: str,
        method: str = "ANGLE_BASED",
        fill_holes: bool = True,
        margin: float = 0.02,
    ) -> dict:
        """Standard UV Unwrap — follows marked seams.

        Best for organic models where you've marked seams manually.
        Use uv_mark_seams first to define cut lines.

        Args:
            object_name: Target mesh object
            method: ANGLE_BASED or CONFORMAL
            fill_holes: Fill holes in mesh before unwrapping
            margin: Island margin
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(
        method='{method}',
        fill_holes={fill_holes},
        margin={margin},
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    result = f'UV unwrap ({method}) on {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def uv_project_from_view(
        object_name: str,
        projection: str = "cube",
        scale: float = 1.0,
    ) -> dict:
        """Project UV coordinates using simple projection methods.

        Args:
            object_name: Target mesh object
            projection: cube, cylinder, or sphere
            scale: UV scale factor
        """
        proj_map = {
            "cube": "bpy.ops.uv.cube_project(cube_size={scale})",
            "cylinder": "bpy.ops.uv.cylinder_project(scale_to_bounds=True)",
            "sphere": "bpy.ops.uv.sphere_project(scale_to_bounds=True)",
        }
        if projection not in proj_map:
            return {"error": f"Unknown projection '{projection}'. Available: cube, cylinder, sphere"}

        op = proj_map[projection].format(scale=scale)
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    {op}
    bpy.ops.object.mode_set(mode='OBJECT')
    result = f'{projection} UV projection on {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def uv_mark_seams(
        object_name: str,
        edge_indices: list = None,
        sharp_angle: float = 0.0,
        clear_existing: bool = False,
    ) -> dict:
        """Mark UV seams on a mesh.

        Args:
            object_name: Target mesh object
            edge_indices: Specific edge indices to mark as seams
            sharp_angle: Auto-mark seams at edges sharper than this angle (degrees, 0=disabled)
            clear_existing: Clear all existing seams first
        """
        code = f"""import bpy, bmesh, math
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    if {clear_existing}:
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.mark_seam(clear=True)

    seam_count = 0
"""
        if edge_indices:
            code += f"""
    bm = bmesh.from_edit_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    for idx in {edge_indices}:
        if idx < len(bm.edges):
            bm.edges[idx].seam = True
            seam_count += 1
    bmesh.update_edit_mesh(obj.data)
"""
        if sharp_angle > 0:
            code += f"""
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.edges_select_sharp(sharpness=math.radians({sharp_angle}))
    bpy.ops.mesh.mark_seam(clear=False)
    seam_count = sum(1 for e in obj.data.edges if e.use_seam)
"""

        code += """
    bpy.ops.object.mode_set(mode='OBJECT')
    total_seams = sum(1 for e in obj.data.edges if e.use_seam)
    result = f'Seams on {obj.name}: {total_seams} edges marked'
"""
        return _exec(code)

    @mcp.tool()
    def uv_pack_islands(
        object_name: str,
        margin: float = 0.02,
        rotate: bool = True,
    ) -> dict:
        """Pack UV islands to fill UV space efficiently.

        Args:
            object_name: Target mesh object
            margin: Margin between islands
            rotate: Allow island rotation for better packing
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(margin={margin}, rotate={rotate})
    bpy.ops.object.mode_set(mode='OBJECT')
    result = f'UV islands packed on {{obj.name}} (margin={margin})'
"""
        return _exec(code)

    @mcp.tool()
    def uv_get_info(object_name: str) -> dict:
        """Get UV layer info for an object — layer names, island count estimate."""
        code = f"""import bpy, json
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    layers = []
    for uv in obj.data.uv_layers:
        layers.append({{
            'name': uv.name,
            'active': uv.active,
            'active_render': uv.active_render,
        }})

    # Estimate UV coverage
    mesh = obj.data
    uv_area = 0
    if mesh.uv_layers.active:
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                uv_area += 1  # Count UV data points

    result = json.dumps({{
        'object': obj.name,
        'uv_layers': layers,
        'layer_count': len(layers),
        'uv_data_points': uv_area,
        'vertices': len(mesh.vertices),
        'faces': len(mesh.polygons),
    }}, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def uv_add_layer(object_name: str, name: str = "UVMap", set_active: bool = True) -> dict:
        """Add a new UV layer to an object.

        Args:
            object_name: Target mesh object
            name: Name for the new UV layer
            set_active: Make the new layer the active one
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    uv = obj.data.uv_layers.new(name='{name}')
    if {set_active}:
        uv.active = True
    result = f'Added UV layer "{{uv.name}}" to {{obj.name}} (total: {{len(obj.data.uv_layers)}})'
"""
        return _exec(code)

    @mcp.tool()
    def uv_remove_layer(object_name: str, layer_name: str) -> dict:
        """Remove a UV layer from an object.

        Args:
            object_name: Target mesh object
            layer_name: Name of the UV layer to remove
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'MESH':
    result = "Error: Mesh object '{object_name}' not found"
else:
    uv = obj.data.uv_layers.get('{layer_name}')
    if not uv:
        result = "Error: UV layer '{layer_name}' not found"
    else:
        obj.data.uv_layers.remove(uv)
        result = f'Removed UV layer "{layer_name}" from {{obj.name}}'
"""
        return _exec(code)
