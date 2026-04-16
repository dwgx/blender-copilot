"""
Curve tools — Bezier, NURBS, path creation and manipulation.

Adapted from blend-ai curves module patterns. Provides curve creation,
3D text, conversion, handle editing, and curve utilities.
"""


def register_curve_tools(mcp, send_command_fn):
    """Register curve creation and editing MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def curve_create_bezier(
        name: str = "BezierCurve",
        points: list = None,
        location: list = None,
        fill_mode: str = "FULL",
        bevel_depth: float = 0.0,
        bevel_resolution: int = 4,
        resolution_u: int = 12,
        extrude: float = 0.0,
    ) -> dict:
        """Create a Bezier curve with custom control points.

        Args:
            name: Object name
            points: List of control point dicts: [{"co": [x,y,z], "handle_left": [x,y,z], "handle_right": [x,y,z], "type": "AUTO"}]
                    If empty, creates a default S-curve.
            location: Object location [x, y, z]
            fill_mode: FULL, BACK, FRONT, HALF, NONE
            bevel_depth: Bevel depth for tube-like appearance
            bevel_resolution: Bevel smoothness
            resolution_u: Curve resolution
            extrude: Extrude amount for flat ribbon
        """
        loc = location or [0, 0, 0]
        pts = points or [
            {"co": [-1, 0, 0], "type": "AUTO"},
            {"co": [0, 1, 0], "type": "AUTO"},
            {"co": [1, 0, 0], "type": "AUTO"},
        ]
        pts_str = str(pts)
        code = f"""import bpy

curve_data = bpy.data.curves.new('{name}', 'CURVE')
curve_data.dimensions = '3D'
curve_data.fill_mode = '{fill_mode}'
curve_data.bevel_depth = {bevel_depth}
curve_data.bevel_resolution = {bevel_resolution}
curve_data.resolution_u = {resolution_u}
curve_data.extrude = {extrude}

spline = curve_data.splines.new('BEZIER')
pts = {pts_str}
spline.bezier_points.add(len(pts) - 1)

for i, p in enumerate(pts):
    bp = spline.bezier_points[i]
    bp.co = tuple(p['co'])
    bp.handle_left_type = p.get('type', 'AUTO')
    bp.handle_right_type = p.get('type', 'AUTO')
    if 'handle_left' in p:
        bp.handle_left = tuple(p['handle_left'])
    if 'handle_right' in p:
        bp.handle_right = tuple(p['handle_right'])

obj = bpy.data.objects.new('{name}', curve_data)
obj.location = {loc}
bpy.context.collection.objects.link(obj)
result = f'Created Bezier curve: {{obj.name}} with {{len(pts)}} points'
"""
        return _exec(code)

    @mcp.tool()
    def curve_create_nurbs(
        name: str = "NurbsCurve",
        points: list = None,
        location: list = None,
        order_u: int = 4,
        bevel_depth: float = 0.0,
        use_cyclic: bool = False,
    ) -> dict:
        """Create a NURBS curve.

        Args:
            name: Object name
            points: List of [x, y, z, w] points (w = weight, default 1.0)
            location: Object location
            order_u: NURBS order (2-6)
            bevel_depth: Tube bevel depth
            use_cyclic: Close the curve into a loop
        """
        loc = location or [0, 0, 0]
        pts = points or [[-2, 0, 0, 1], [-1, 1, 0, 1], [1, 1, 0, 1], [2, 0, 0, 1]]
        pts_str = str(pts)
        code = f"""import bpy

curve_data = bpy.data.curves.new('{name}', 'CURVE')
curve_data.dimensions = '3D'
curve_data.bevel_depth = {bevel_depth}

spline = curve_data.splines.new('NURBS')
pts = {pts_str}
spline.points.add(len(pts) - 1)

for i, p in enumerate(pts):
    w = p[3] if len(p) > 3 else 1.0
    spline.points[i].co = (p[0], p[1], p[2], w)

spline.order_u = {order_u}
spline.use_cyclic_u = {use_cyclic}
spline.use_endpoint_u = True

obj = bpy.data.objects.new('{name}', curve_data)
obj.location = {loc}
bpy.context.collection.objects.link(obj)
result = f'Created NURBS curve: {{obj.name}} with {{len(pts)}} points'
"""
        return _exec(code)

    @mcp.tool()
    def curve_create_path(
        name: str = "Path",
        length: float = 5.0,
        points: int = 5,
        location: list = None,
    ) -> dict:
        """Create a NURBS path (useful for follow-path animations and hair guides).

        Args:
            name: Path name
            length: Path length
            points: Number of control points
            location: Object location
        """
        loc = location or [0, 0, 0]
        code = f"""import bpy
bpy.ops.curve.primitive_nurbs_path_add(radius={length / 2})
obj = bpy.context.active_object
obj.name = '{name}'
obj.location = {loc}
result = f'Created path: {{obj.name}}, length={length}'
"""
        return _exec(code)

    @mcp.tool()
    def curve_create_circle(
        name: str = "CurveCircle",
        radius: float = 1.0,
        location: list = None,
        fill: bool = False,
    ) -> dict:
        """Create a circle curve (useful as bevel object for tubes/pipes).

        Args:
            name: Circle name
            radius: Circle radius
            location: Object location
            fill: Fill the circle to create a disk
        """
        loc = location or [0, 0, 0]
        code = f"""import bpy
bpy.ops.curve.primitive_bezier_circle_add(radius={radius}, location={loc})
obj = bpy.context.active_object
obj.name = '{name}'
if {fill}:
    obj.data.fill_mode = 'BOTH'
result = f'Created circle curve: {{obj.name}}, r={radius}'
"""
        return _exec(code)

    @mcp.tool()
    def curve_create_text(
        text: str = "Hello",
        name: str = "Text",
        font_size: float = 1.0,
        extrude: float = 0.0,
        bevel_depth: float = 0.0,
        location: list = None,
        align: str = "CENTER",
    ) -> dict:
        """Create 3D text object.

        Args:
            text: Text content
            name: Object name
            font_size: Size of the text
            extrude: Extrusion depth for 3D effect
            bevel_depth: Edge bevel for rounded letters
            location: Object location
            align: LEFT, CENTER, RIGHT, JUSTIFY, FLUSH
        """
        loc = location or [0, 0, 0]
        # Escape single quotes in text
        safe_text = text.replace("'", "\\'")
        code = f"""import bpy
bpy.ops.object.text_add(location={loc})
obj = bpy.context.active_object
obj.name = '{name}'
obj.data.body = '{safe_text}'
obj.data.size = {font_size}
obj.data.extrude = {extrude}
obj.data.bevel_depth = {bevel_depth}
obj.data.align_x = '{align}'
result = f'Created text: "{{obj.data.body}}" as {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def curve_to_mesh(object_name: str, keep_original: bool = False) -> dict:
        """Convert a curve to mesh geometry.

        Args:
            object_name: Curve object to convert
            keep_original: Keep the original curve object
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'CURVE':
    result = "Error: Curve object '{object_name}' not found"
else:
    if {keep_original}:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.duplicate()
        obj = bpy.context.active_object

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    verts = len(obj.data.vertices)
    faces = len(obj.data.polygons)
    result = f'Converted {{obj.name}} to mesh: {{verts}} verts, {{faces}} faces'
"""
        return _exec(code)

    @mcp.tool()
    def curve_set_bevel(
        object_name: str,
        bevel_depth: float = 0.0,
        bevel_resolution: int = 4,
        bevel_object: str = "",
    ) -> dict:
        """Set bevel properties on a curve (creates tube/pipe effect).

        Args:
            object_name: Target curve object
            bevel_depth: Bevel radius (0 = wireframe, >0 = tube)
            bevel_resolution: Smoothness of bevel profile
            bevel_object: Name of curve to use as custom bevel profile
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj or obj.type != 'CURVE':
    result = "Error: Curve object '{object_name}' not found"
else:
    obj.data.bevel_depth = {bevel_depth}
    obj.data.bevel_resolution = {bevel_resolution}
    if '{bevel_object}':
        bevel = bpy.data.objects.get('{bevel_object}')
        if bevel:
            obj.data.bevel_object = bevel
    result = f'Bevel on {{obj.name}}: depth={bevel_depth}, res={bevel_resolution}'
"""
        return _exec(code)
