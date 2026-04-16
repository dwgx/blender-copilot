"""
Lighting tools — light creation, studio rigs, shadow control.

Provides individual light creation, common lighting setups (3-point, studio,
outdoor), and light management utilities.
"""


def register_lighting_tools(mcp, send_command_fn):
    """Register lighting MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def light_add(
        name: str = "Light",
        light_type: str = "POINT",
        location: list = None,
        rotation: list = None,
        power: float = 1000.0,
        color: list = None,
        size: float = 1.0,
        shadow: bool = True,
    ) -> dict:
        """Add a light to the scene.

        Args:
            name: Light name
            light_type: POINT, SUN, SPOT, AREA
            location: [x, y, z] position
            rotation: [rx, ry, rz] rotation in degrees
            power: Light power (Watts for point/spot/area, strength for sun)
            color: [r, g, b] color (0-1 range)
            size: Light size (area size, point radius, spot cone)
            shadow: Cast shadows
        """
        loc = location or [0, 0, 3]
        rot = rotation or [0, 0, 0]
        col = color or [1.0, 1.0, 1.0]
        code = f"""import bpy, math
ld = bpy.data.lights.new('{name}', '{light_type}')
ld.energy = {power}
ld.color = ({col[0]}, {col[1]}, {col[2]})
ld.use_shadow = {shadow}
"""
        if light_type == "AREA":
            code += f"ld.size = {size}\n"
        elif light_type == "SPOT":
            code += f"ld.spot_size = math.radians({size * 45})\n"
            code += f"ld.spot_blend = 0.15\n"

        code += f"""lo = bpy.data.objects.new('{name}', ld)
bpy.context.collection.objects.link(lo)
lo.location = ({loc[0]}, {loc[1]}, {loc[2]})
lo.rotation_euler = (math.radians({rot[0]}), math.radians({rot[1]}), math.radians({rot[2]}))
result = f'Added {{lo.name}} ({light_type}): power={power}, color=({col[0]},{col[1]},{col[2]})'
"""
        return _exec(code)

    @mcp.tool()
    def light_setup_three_point(
        target_location: list = None,
        key_power: float = 500.0,
        fill_power: float = 200.0,
        rim_power: float = 300.0,
        distance: float = 4.0,
    ) -> dict:
        """Set up classic 3-point lighting (key + fill + rim/back).

        Professional lighting setup for product shots and character renders.

        Args:
            target_location: Center point to light [x, y, z]
            key_power: Key light power
            fill_power: Fill light power
            rim_power: Rim/back light power
            distance: Distance from target
        """
        t = target_location or [0, 0, 1]
        code = f"""import bpy, math

target = ({t[0]}, {t[1]}, {t[2]})
d = {distance}

# Key Light — 45° front-right, slightly above
key_data = bpy.data.lights.new('Key_Light', 'AREA')
key_data.energy = {key_power}
key_data.size = 2
key = bpy.data.objects.new('Key_Light', key_data)
bpy.context.collection.objects.link(key)
key.location = (target[0] + d*0.7, target[1] - d*0.7, target[2] + d*0.5)
constraint = key.constraints.new('TRACK_TO')
empty = bpy.data.objects.new('Light_Target', None)
empty.location = target
bpy.context.collection.objects.link(empty)
constraint.target = empty
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'

# Fill Light — opposite side, lower intensity
fill_data = bpy.data.lights.new('Fill_Light', 'AREA')
fill_data.energy = {fill_power}
fill_data.size = 3
fill = bpy.data.objects.new('Fill_Light', fill_data)
bpy.context.collection.objects.link(fill)
fill.location = (target[0] - d*0.8, target[1] - d*0.5, target[2] + d*0.2)
c2 = fill.constraints.new('TRACK_TO')
c2.target = empty
c2.track_axis = 'TRACK_NEGATIVE_Z'
c2.up_axis = 'UP_Y'

# Rim Light — behind and above
rim_data = bpy.data.lights.new('Rim_Light', 'AREA')
rim_data.energy = {rim_power}
rim_data.size = 1.5
rim = bpy.data.objects.new('Rim_Light', rim_data)
bpy.context.collection.objects.link(rim)
rim.location = (target[0], target[1] + d*0.8, target[2] + d*0.7)
c3 = rim.constraints.new('TRACK_TO')
c3.target = empty
c3.track_axis = 'TRACK_NEGATIVE_Z'
c3.up_axis = 'UP_Y'

result = f'3-point lighting: Key({key_power}W) + Fill({fill_power}W) + Rim({rim_power}W)'
"""
        return _exec(code)

    @mcp.tool()
    def light_setup_studio(
        target_location: list = None,
        temperature: str = "neutral",
    ) -> dict:
        """Set up studio lighting with softboxes (4 area lights + white world).

        Args:
            target_location: Scene center point
            temperature: warm (5000K yellowish), neutral (6500K white), cool (8000K bluish)
        """
        t = target_location or [0, 0, 1]
        temp_colors = {
            "warm": [1.0, 0.92, 0.82],
            "neutral": [1.0, 1.0, 1.0],
            "cool": [0.85, 0.92, 1.0],
        }
        col = temp_colors.get(temperature, temp_colors["neutral"])
        code = f"""import bpy, math

target = ({t[0]}, {t[1]}, {t[2]})
color = ({col[0]}, {col[1]}, {col[2]})

# White backdrop world
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new('Studio')
    bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.95, 0.95, 0.95, 1.0)
    bg.inputs['Strength'].default_value = 0.5

# Main overhead softbox
for i, (name, pos, power, size) in enumerate([
    ('Studio_Main', (0, -2, 4), 400, 3.0),
    ('Studio_Fill_L', (-3, -1, 2.5), 200, 2.0),
    ('Studio_Fill_R', (3, -1, 2.5), 200, 2.0),
    ('Studio_Back', (0, 3, 3), 150, 2.0),
]):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = power
    ld.size = size
    ld.color = color
    lo = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(lo)
    lo.location = (target[0] + pos[0], target[1] + pos[1], target[2] + pos[2])
    # Point at target
    direction = [target[j] - lo.location[j] for j in range(3)]
    import mathutils
    rot = mathutils.Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    lo.rotation_euler = rot

result = f'Studio lighting ({temperature}): 4 softboxes + white world'
"""
        return _exec(code)

    @mcp.tool()
    def light_list() -> dict:
        """List all lights in the scene with their properties."""
        code = """import bpy, json
lights = []
for obj in bpy.context.scene.objects:
    if obj.type == 'LIGHT':
        ld = obj.data
        info = {
            'name': obj.name,
            'type': ld.type,
            'power': ld.energy,
            'color': [round(c, 3) for c in ld.color],
            'shadow': ld.use_shadow,
            'location': [round(x, 3) for x in obj.location],
        }
        if ld.type == 'AREA':
            info['size'] = ld.size
        elif ld.type == 'SPOT':
            import math
            info['cone_angle'] = round(math.degrees(ld.spot_size), 1)
        lights.append(info)
result = json.dumps({'lights': lights, 'count': len(lights)}, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def light_modify(
        light_name: str,
        power: float = None,
        color: list = None,
        shadow: bool = None,
        size: float = None,
    ) -> dict:
        """Modify an existing light's properties.

        Args:
            light_name: Light object name
            power: New power value
            color: New [r, g, b] color
            shadow: Enable/disable shadows
            size: New size (area lights)
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{light_name}')
if not obj or obj.type != 'LIGHT':
    result = "Error: Light '{light_name}' not found"
else:
    ld = obj.data
    changes = []
"""
        if power is not None:
            code += f"    ld.energy = {power}\n    changes.append(f'power={power}')\n"
        if color is not None:
            code += f"    ld.color = ({color[0]}, {color[1]}, {color[2]})\n    changes.append('color updated')\n"
        if shadow is not None:
            code += f"    ld.use_shadow = {shadow}\n    changes.append(f'shadow={shadow}')\n"
        if size is not None:
            code += f"""    if ld.type == 'AREA':
        ld.size = {size}
        changes.append(f'size={size}')
"""
        code += "    result = f'Modified {obj.name}: {', '.join(changes)}'\n"
        return _exec(code)
