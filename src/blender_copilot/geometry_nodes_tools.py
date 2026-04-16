"""
Geometry Nodes tools — node tree creation, node wiring, and presets.

Adapted from blend-ai geometry nodes module. Provides programmatic
geometry nodes setup for procedural modeling workflows.
"""


def register_geometry_nodes_tools(mcp, send_command_fn):
    """Register geometry nodes MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def geonodes_create(
        object_name: str,
        tree_name: str = "GeometryNodes",
    ) -> dict:
        """Create a Geometry Nodes modifier on an object with a new node tree.

        Args:
            object_name: Target object
            tree_name: Name for the node tree
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    mod = obj.modifiers.new('{tree_name}', 'NODES')
    tree = bpy.data.node_groups.new('{tree_name}', 'GeometryNodeTree')
    mod.node_group = tree

    # Add default Group Input/Output
    inp = tree.nodes.new('NodeGroupInput')
    inp.location = (-300, 0)
    out = tree.nodes.new('NodeGroupOutput')
    out.location = (300, 0)

    # Add geometry socket
    tree.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # Connect input → output
    tree.links.new(inp.outputs[0], out.inputs[0])

    result = f'Geometry Nodes on {{obj.name}}: tree={tree_name}'
"""
        return _exec(code)

    @mcp.tool()
    def geonodes_add_node(
        tree_name: str,
        node_type: str,
        name: str = "",
        location: list = None,
    ) -> dict:
        """Add a node to a Geometry Nodes tree.

        Args:
            tree_name: Node tree name
            node_type: Blender node type (e.g., GeometryNodeMeshPrimitiveCube,
                      GeometryNodeSetPosition, GeometryNodeTransform,
                      ShaderNodeMath, GeometryNodeDistributePointsOnFaces, etc.)
            name: Custom node label
            location: [x, y] position in node editor
        """
        loc = location or [0, 0]
        code = f"""import bpy
tree = bpy.data.node_groups.get('{tree_name}')
if not tree:
    result = "Error: Node tree '{tree_name}' not found"
else:
    node = tree.nodes.new('{node_type}')
    node.location = ({loc[0]}, {loc[1]})
    if '{name}':
        node.label = '{name}'
    result = f'Added {{node.bl_label}} ({{node.name}}) to {tree_name}'
"""
        return _exec(code)

    @mcp.tool()
    def geonodes_connect(
        tree_name: str,
        from_node: str,
        from_socket: int,
        to_node: str,
        to_socket: int,
    ) -> dict:
        """Connect two nodes in a Geometry Nodes tree.

        Args:
            tree_name: Node tree name
            from_node: Source node name
            from_socket: Source output socket index
            to_node: Destination node name
            to_socket: Destination input socket index
        """
        code = f"""import bpy
tree = bpy.data.node_groups.get('{tree_name}')
if not tree:
    result = "Error: Node tree '{tree_name}' not found"
else:
    src = tree.nodes.get('{from_node}')
    dst = tree.nodes.get('{to_node}')
    if not src:
        result = "Error: Node '{from_node}' not found"
    elif not dst:
        result = "Error: Node '{to_node}' not found"
    elif {from_socket} >= len(src.outputs):
        result = f"Error: {{src.name}} has {{len(src.outputs)}} outputs, index {from_socket} out of range"
    elif {to_socket} >= len(dst.inputs):
        result = f"Error: {{dst.name}} has {{len(dst.inputs)}} inputs, index {to_socket} out of range"
    else:
        tree.links.new(src.outputs[{from_socket}], dst.inputs[{to_socket}])
        result = f'Connected {{src.name}}[{from_socket}] → {{dst.name}}[{to_socket}]'
"""
        return _exec(code)

    @mcp.tool()
    def geonodes_set_input(
        tree_name: str,
        node_name: str,
        input_index: int,
        value: any,
    ) -> dict:
        """Set a node input's default value.

        Args:
            tree_name: Node tree name
            node_name: Node name
            input_index: Input socket index
            value: Value to set (float, int, vector list, etc.)
        """
        val_str = str(value)
        code = f"""import bpy
tree = bpy.data.node_groups.get('{tree_name}')
if not tree:
    result = "Error: Node tree '{tree_name}' not found"
else:
    node = tree.nodes.get('{node_name}')
    if not node:
        result = "Error: Node '{node_name}' not found"
    elif {input_index} >= len(node.inputs):
        result = f"Error: {{node.name}} has {{len(node.inputs)}} inputs"
    else:
        inp = node.inputs[{input_index}]
        val = {val_str}
        if isinstance(val, (list, tuple)):
            inp.default_value = tuple(val)
        else:
            inp.default_value = val
        result = f'Set {{node.name}} input[{input_index}] = {{val}}'
"""
        return _exec(code)

    @mcp.tool()
    def geonodes_list_nodes(tree_name: str) -> dict:
        """List all nodes in a Geometry Nodes tree with their connections."""
        code = f"""import bpy, json
tree = bpy.data.node_groups.get('{tree_name}')
if not tree:
    result = "Error: Node tree '{tree_name}' not found"
else:
    nodes = []
    for n in tree.nodes:
        inputs = [{{
            'index': i,
            'name': s.name,
            'type': s.bl_idname,
            'linked': s.is_linked,
        }} for i, s in enumerate(n.inputs)]
        outputs = [{{
            'index': i,
            'name': s.name,
            'type': s.bl_idname,
            'linked': s.is_linked,
        }} for i, s in enumerate(n.outputs)]
        nodes.append({{
            'name': n.name,
            'type': n.bl_idname,
            'label': n.label,
            'location': [int(n.location.x), int(n.location.y)],
            'inputs': inputs,
            'outputs': outputs,
        }})

    links = []
    for l in tree.links:
        links.append({{
            'from': f'{{l.from_node.name}}[{{l.from_socket.name}}]',
            'to': f'{{l.to_node.name}}[{{l.to_socket.name}}]',
        }})

    result = json.dumps({{
        'tree': '{tree_name}',
        'nodes': len(nodes),
        'links': len(links),
        'node_list': nodes,
        'connections': links,
    }}, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def geonodes_preset_scatter(
        object_name: str,
        instance_type: str = "SPHERE",
        density: float = 10.0,
        scale: float = 0.1,
        seed: int = 0,
    ) -> dict:
        """Apply a preset: scatter instances on a surface.

        Creates a complete geo-nodes setup that distributes point instances
        on the object's surface — great for grass, rocks, particles, etc.

        Args:
            object_name: Surface object to scatter on
            instance_type: SPHERE, CUBE, CONE, or object name for custom instance
            density: Points per unit area
            scale: Instance scale
            seed: Random seed
        """
        code = f"""import bpy

obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    tree = bpy.data.node_groups.new('Scatter', 'GeometryNodeTree')

    # Add modifier
    mod = obj.modifiers.new('Scatter', 'NODES')
    mod.node_group = tree

    # Sockets
    tree.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # Nodes
    inp = tree.nodes.new('NodeGroupInput')
    inp.location = (-600, 0)
    out = tree.nodes.new('NodeGroupOutput')
    out.location = (600, 0)

    dist = tree.nodes.new('GeometryNodeDistributePointsOnFaces')
    dist.location = (-200, 0)
    dist.distribute_method = 'POISSON'
    dist.inputs['Density'].default_value = {density}
    dist.inputs['Seed'].default_value = {seed}

    inst_on = tree.nodes.new('GeometryNodeInstanceOnPoints')
    inst_on.location = (100, 0)

    # Instance geometry
    mesh_type = '{instance_type}'
    if mesh_type in ('SPHERE', 'CUBE', 'CONE'):
        prim_map = {{
            'SPHERE': 'GeometryNodeMeshUVSphere',
            'CUBE': 'GeometryNodeMeshCube',
            'CONE': 'GeometryNodeMeshCone',
        }}
        prim = tree.nodes.new(prim_map[mesh_type])
        prim.location = (-200, -200)
        tree.links.new(prim.outputs[0], inst_on.inputs['Instance'])
    else:
        # Custom object as instance
        obj_info = tree.nodes.new('GeometryNodeObjectInfo')
        obj_info.location = (-200, -200)
        custom = bpy.data.objects.get(mesh_type)
        if custom:
            obj_info.inputs['Object'].default_value = custom
        tree.links.new(obj_info.outputs['Geometry'], inst_on.inputs['Instance'])

    # Scale
    scale_node = tree.nodes.new('FunctionNodeInputVector')
    scale_node.location = (-200, -350)
    scale_node.vector = ({scale}, {scale}, {scale})
    tree.links.new(scale_node.outputs[0], inst_on.inputs['Scale'])

    # Join original + instances
    join = tree.nodes.new('GeometryNodeJoinGeometry')
    join.location = (350, 0)

    # Connections
    tree.links.new(inp.outputs[0], dist.inputs['Mesh'])
    tree.links.new(dist.outputs['Points'], inst_on.inputs['Points'])
    tree.links.new(inp.outputs[0], join.inputs['Geometry'])
    tree.links.new(inst_on.outputs['Instances'], join.inputs['Geometry'])
    tree.links.new(join.outputs[0], out.inputs[0])

    result = f'Scatter preset on {{obj.name}}: density={density}, scale={scale}, instance={instance_type}'
"""
        return _exec(code)
