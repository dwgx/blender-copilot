"""
Viewport tools — shading modes, overlays, focus, and viewport control.

Adapted from blend-ai viewport module. Provides viewport configuration
and quick focus/navigation utilities.
"""


def register_viewport_tools(mcp, send_command_fn):
    """Register viewport control MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def viewport_set_shading(
        mode: str = "SOLID",
        studio_light: str = "",
        color_type: str = "",
    ) -> dict:
        """Set viewport shading mode.

        Args:
            mode: WIREFRAME, SOLID, MATERIAL, RENDERED
            studio_light: Studio light name for SOLID mode (e.g., 'studio.exr', 'rim.sl')
            color_type: MATERIAL, SINGLE, OBJECT, RANDOM, VERTEX, TEXTURE (for SOLID mode)
        """
        code = f"""import bpy
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        space = area.spaces[0]
        space.shading.type = '{mode}'
        if '{studio_light}' and '{mode}' == 'SOLID':
            space.shading.studio_light = '{studio_light}'
        if '{color_type}' and '{mode}' == 'SOLID':
            space.shading.color_type = '{color_type}'
        break
result = f'Viewport shading: {mode}'
"""
        return _exec(code)

    @mcp.tool()
    def viewport_set_overlays(
        show_overlays: bool = True,
        show_wireframe: bool = False,
        show_face_orientation: bool = False,
        show_stats: bool = False,
        show_floor: bool = True,
        show_axis_x: bool = True,
        show_axis_y: bool = True,
    ) -> dict:
        """Configure viewport overlays.

        Args:
            show_overlays: Master overlay toggle
            show_wireframe: Show wireframe overlay on solid
            show_face_orientation: Color faces by normal direction (useful for debugging)
            show_stats: Show scene statistics
            show_floor: Show grid floor
            show_axis_x: Show X axis line
            show_axis_y: Show Y axis line
        """
        code = f"""import bpy
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        space = area.spaces[0]
        space.overlay.show_overlays = {show_overlays}
        space.overlay.show_wireframes = {show_wireframe}
        space.overlay.show_face_orientation = {show_face_orientation}
        space.overlay.show_stats = {show_stats}
        space.overlay.show_floor = {show_floor}
        space.overlay.show_axis_x = {show_axis_x}
        space.overlay.show_axis_y = {show_axis_y}
        break
result = f'Overlays: show={show_overlays}, wire={show_wireframe}, face_orient={show_face_orientation}, stats={show_stats}'
"""
        return _exec(code)

    @mcp.tool()
    def viewport_focus_object(object_name: str) -> dict:
        """Focus the viewport on a specific object (zoom to fit).

        Args:
            object_name: Object to focus on
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            with bpy.context.temp_override(area=area):
                bpy.ops.view3d.view_selected()
            break
    result = f'Focused on {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def viewport_set_view(
        view: str = "FRONT",
        perspective: bool = False,
    ) -> dict:
        """Set viewport to a standard view angle.

        Args:
            view: FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM
            perspective: True for perspective, False for orthographic
        """
        view_map = {
            "FRONT": "'FRONT'",
            "BACK": "'BACK'",
            "LEFT": "'LEFT'",
            "RIGHT": "'RIGHT'",
            "TOP": "'TOP'",
            "BOTTOM": "'BOTTOM'",
        }
        if view not in view_map:
            return {"error": f"Unknown view '{view}'. Available: {list(view_map.keys())}"}

        code = f"""import bpy
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        region = area.spaces[0].region_3d
        region.view_perspective = '{'PERSP' if perspective else 'ORTHO'}'
        with bpy.context.temp_override(area=area):
            bpy.ops.view3d.view_axis(type={view_map[view]})
        break
result = f'View: {view} ({'perspective' if perspective else 'orthographic'})'
"""
        return _exec(code)
