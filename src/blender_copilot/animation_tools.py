"""
Animation tools — adapted from CLI-Anything animation.py patterns.

Provides keyframe management, common animation presets, driver creation,
and animation data utilities for the MCP pipeline.
"""
from typing import Dict, Any, List, Optional


# ─── Animation Presets ────────────────────────────────────────────────────────

EASING_TYPES = [
    "LINEAR", "CONSTANT", "BEZIER",
    "SINE", "QUAD", "CUBIC", "QUART", "QUINT",
    "EXPO", "CIRC", "BACK", "BOUNCE", "ELASTIC",
]


def register_animation_tools(mcp, send_command_fn):
    """Register animation MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def anim_insert_keyframe(
        object_name: str,
        data_path: str,
        frame: int,
        value: float = None,
        index: int = -1,
    ) -> dict:
        """Insert a keyframe on an object property.

        Args:
            object_name: Target object name
            data_path: Property path (location, rotation_euler, scale, etc.)
            frame: Frame number
            value: Optional value to set before keying
            index: Channel index (-1 = all channels, 0=X, 1=Y, 2=Z)
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.scene.frame_set({frame})
"""
        if value is not None:
            if index >= 0:
                code += f"    obj.{data_path}[{index}] = {value}\n"
            else:
                code += f"    obj.{data_path} = {value}\n"

        code += f"""    obj.keyframe_insert(data_path='{data_path}', frame={frame}, index={index})
    result = f'Keyframe: {{obj.name}}.{data_path} at frame {frame}'
"""
        return _exec(code)

    @mcp.tool()
    def anim_insert_keyframes_batch(
        object_name: str,
        keyframes: list,
    ) -> dict:
        """Insert multiple keyframes at once.

        Args:
            object_name: Target object name
            keyframes: List of dicts, each with:
                - frame (int): Frame number
                - data_path (str): Property path
                - value: Value to set (single float or [x,y,z] list)
                - index (int, optional): Channel index (-1 for all)

        Example keyframes:
            [
                {"frame": 1, "data_path": "location", "value": [0, 0, 0]},
                {"frame": 30, "data_path": "location", "value": [5, 0, 2]},
                {"frame": 60, "data_path": "location", "value": [0, 0, 0]}
            ]
        """
        kf_str = str(keyframes)
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    keyframes = {kf_str}
    count = 0
    for kf in keyframes:
        frame = kf['frame']
        dp = kf['data_path']
        val = kf.get('value')
        idx = kf.get('index', -1)
        bpy.context.scene.frame_set(frame)
        if val is not None:
            attr = getattr(obj, dp)
            if isinstance(val, (list, tuple)) and hasattr(attr, '__len__'):
                for i, v in enumerate(val):
                    attr[i] = v
            elif idx >= 0:
                attr[idx] = val
            else:
                setattr(obj, dp, val)
        obj.keyframe_insert(data_path=dp, frame=frame, index=idx)
        count += 1
    result = f'Inserted {{count}} keyframes on {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def anim_delete_keyframe(
        object_name: str,
        data_path: str,
        frame: int,
        index: int = -1,
    ) -> dict:
        """Delete a keyframe from an object property.

        Args:
            object_name: Target object name
            data_path: Property path
            frame: Frame number to delete
            index: Channel index (-1 = all)
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.scene.frame_set({frame})
    try:
        obj.keyframe_delete(data_path='{data_path}', frame={frame}, index={index})
        result = f'Deleted keyframe: {{obj.name}}.{data_path} at frame {frame}'
    except RuntimeError:
        result = f'No keyframe found at frame {frame}'
"""
        return _exec(code)

    @mcp.tool()
    def anim_clear_all(object_name: str) -> dict:
        """Remove all animation data from an object."""
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    obj.animation_data_clear()
    result = f'Cleared all animation from {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def anim_set_interpolation(
        object_name: str,
        interpolation: str = "BEZIER",
        easing: str = "",
    ) -> dict:
        """Set interpolation type for all keyframes on an object.

        Args:
            object_name: Target object
            interpolation: CONSTANT, LINEAR, BEZIER, SINE, QUAD, CUBIC, etc.
            easing: EASE_IN, EASE_OUT, EASE_IN_OUT (for non-linear types)
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj or not obj.animation_data or not obj.animation_data.action:
    result = "Error: No animation data on '{object_name}'"
else:
    count = 0
    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = '{interpolation}'
            if '{easing}':
                kp.easing = '{easing}'
            count += 1
    result = f'Set {{count}} keyframes to {interpolation} on {{obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def anim_set_frame_range(
        start: int = 1,
        end: int = 250,
        fps: int = 0,
    ) -> dict:
        """Set the scene frame range and optionally FPS.

        Args:
            start: Start frame
            end: End frame
            fps: Frames per second (0 = don't change)
        """
        code = f"""import bpy
scene = bpy.context.scene
scene.frame_start = {start}
scene.frame_end = {end}
"""
        if fps > 0:
            code += f"scene.render.fps = {fps}\n"
        code += f"result = f'Frame range: {{scene.frame_start}}-{{scene.frame_end}} @ {{scene.render.fps}}fps'"
        return _exec(code)

    @mcp.tool()
    def anim_bounce(
        object_name: str,
        height: float = 2.0,
        frames: int = 30,
        bounces: int = 3,
    ) -> dict:
        """Create a bouncing animation preset.

        Object bounces up and down with decreasing amplitude.

        Args:
            object_name: Target object
            height: Initial bounce height
            frames: Total animation duration in frames
            bounces: Number of bounces
        """
        code = f"""import bpy, math

obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    start_z = obj.location.z
    frames_per_bounce = {frames} // {bounces}

    for i in range({bounces}):
        amp = {height} * (0.5 ** i)
        base_frame = 1 + i * frames_per_bounce

        # Ground
        obj.location.z = start_z
        obj.keyframe_insert('location', index=2, frame=base_frame)

        # Peak
        mid_frame = base_frame + frames_per_bounce // 2
        obj.location.z = start_z + amp
        obj.keyframe_insert('location', index=2, frame=mid_frame)

        # Ground again
        end_frame = base_frame + frames_per_bounce
        obj.location.z = start_z
        obj.keyframe_insert('location', index=2, frame=end_frame)

    # Make it smooth
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            if fc.data_path == 'location' and fc.array_index == 2:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'SINE'
                    kp.easing = 'EASE_IN_OUT'

    bpy.context.scene.frame_end = max(bpy.context.scene.frame_end, {frames})
    result = f'Bounce animation: {{obj.name}}, {bounces} bounces, height={height}'
"""
        return _exec(code)

    @mcp.tool()
    def anim_orbit(
        object_name: str,
        center: list = None,
        radius: float = 5.0,
        frames: int = 120,
        axis: str = "Z",
    ) -> dict:
        """Create an orbital/circular motion animation.

        Args:
            object_name: Object to animate
            center: Center point [x, y, z] (default [0,0,0])
            radius: Orbit radius
            frames: Frames for one complete orbit
            axis: Rotation axis (X, Y, or Z)
        """
        center = center or [0, 0, 0]
        code = f"""import bpy, math

obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    center = {center}
    radius = {radius}
    axis = '{axis}'
    n_frames = {frames}

    for i in range(n_frames + 1):
        frame = i + 1
        angle = (i / n_frames) * 2 * math.pi

        if axis == 'Z':
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            z = center[2]
        elif axis == 'Y':
            x = center[0] + radius * math.cos(angle)
            y = center[1]
            z = center[2] + radius * math.sin(angle)
        else:  # X
            x = center[0]
            y = center[1] + radius * math.cos(angle)
            z = center[2] + radius * math.sin(angle)

        obj.location = (x, y, z)
        obj.keyframe_insert('location', frame=frame)

    # Linear interpolation for smooth orbit
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'

    bpy.context.scene.frame_end = max(bpy.context.scene.frame_end, n_frames)
    result = f'Orbit: {{obj.name}} around {center}, r={radius}, {frames} frames'
"""
        return _exec(code)

    @mcp.tool()
    def anim_get_info(object_name: str = "") -> dict:
        """Get animation info — keyframe counts, frame range, actions.

        Args:
            object_name: Specific object (empty = scene-wide summary)
        """
        if object_name:
            code = f"""import bpy, json
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
elif not obj.animation_data or not obj.animation_data.action:
    result = json.dumps({{'object': '{object_name}', 'animated': False}})
else:
    action = obj.animation_data.action
    curves = []
    for fc in action.fcurves:
        curves.append({{
            'data_path': fc.data_path,
            'index': fc.array_index,
            'keyframes': len(fc.keyframe_points),
            'range': [int(fc.range()[0]), int(fc.range()[1])],
        }})
    result = json.dumps({{
        'object': '{object_name}',
        'animated': True,
        'action': action.name,
        'fcurves': len(action.fcurves),
        'curves': curves,
    }}, indent=2)
"""
        else:
            code = """import bpy, json
animated_objects = []
for obj in bpy.context.scene.objects:
    if obj.animation_data and obj.animation_data.action:
        animated_objects.append({
            'name': obj.name,
            'type': obj.type,
            'action': obj.animation_data.action.name,
            'fcurves': len(obj.animation_data.action.fcurves),
        })
result = json.dumps({
    'scene_frames': f'{bpy.context.scene.frame_start}-{bpy.context.scene.frame_end}',
    'fps': bpy.context.scene.render.fps,
    'animated_objects': len(animated_objects),
    'objects': animated_objects,
    'total_actions': len(bpy.data.actions),
}, indent=2)
"""
        return _exec(code)
