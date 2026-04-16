"""
Armature/bone tools — skeleton creation, bone editing, constraints, weighting.

Complements rigify_tools (which handles full Rigify rig generation) with
lower-level bone operations for custom rigs and weight painting.
"""


def register_armature_tools(mcp, send_command_fn):
    """Register armature and bone MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def armature_create(
        name: str = "Armature",
        location: list = None,
    ) -> dict:
        """Create a new armature object with a single root bone.

        Args:
            name: Armature object name
            location: Object location [x, y, z]
        """
        loc = location or [0, 0, 0]
        code = f"""import bpy
bpy.ops.object.armature_add(location={loc})
arm = bpy.context.active_object
arm.name = '{name}'
arm.data.name = '{name}_Data'
result = f'Created armature: {{arm.name}} with 1 bone'
"""
        return _exec(code)

    @mcp.tool()
    def armature_add_bone(
        armature_name: str,
        bone_name: str,
        head: list = None,
        tail: list = None,
        parent_bone: str = "",
        connected: bool = False,
    ) -> dict:
        """Add a bone to an existing armature.

        Args:
            armature_name: Target armature object
            bone_name: Name for the new bone
            head: Bone head position [x, y, z]
            tail: Bone tail position [x, y, z]
            parent_bone: Name of parent bone (empty = no parent)
            connected: Connect to parent bone's tail
        """
        head = head or [0, 0, 0]
        tail = tail or [0, 0, 1]
        code = f"""import bpy
arm_obj = bpy.data.objects.get('{armature_name}')
if not arm_obj or arm_obj.type != 'ARMATURE':
    result = "Error: Armature '{armature_name}' not found"
else:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    arm = arm_obj.data
    bone = arm.edit_bones.new('{bone_name}')
    bone.head = {head}
    bone.tail = {tail}
    if '{parent_bone}':
        parent = arm.edit_bones.get('{parent_bone}')
        if parent:
            bone.parent = parent
            bone.use_connect = {connected}
    bpy.ops.object.mode_set(mode='OBJECT')
    result = f'Added bone: {bone_name} to {{arm_obj.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def armature_add_bones_chain(
        armature_name: str,
        chain_name: str,
        joints: list = None,
        parent_bone: str = "",
    ) -> dict:
        """Add a chain of connected bones (e.g., spine, arm, finger).

        Args:
            armature_name: Target armature
            chain_name: Base name for bones (appends .001, .002, etc.)
            joints: List of [x, y, z] positions for each joint (head of each bone)
                    Needs at least 2 points to form 1 bone.
            parent_bone: Parent bone for the first bone in chain
        """
        joints = joints or [[0, 0, 0], [0, 0, 0.5], [0, 0, 1.0]]
        joints_str = str(joints)
        code = f"""import bpy
arm_obj = bpy.data.objects.get('{armature_name}')
if not arm_obj or arm_obj.type != 'ARMATURE':
    result = "Error: Armature '{armature_name}' not found"
else:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    arm = arm_obj.data
    joints = {joints_str}
    bones = []

    parent = arm.edit_bones.get('{parent_bone}') if '{parent_bone}' else None

    for i in range(len(joints) - 1):
        bname = f'{chain_name}.{{str(i+1).zfill(3)}}'
        bone = arm.edit_bones.new(bname)
        bone.head = tuple(joints[i])
        bone.tail = tuple(joints[i + 1])
        if parent:
            bone.parent = parent
            bone.use_connect = (i > 0)
        parent = bone
        bones.append(bname)

    bpy.ops.object.mode_set(mode='OBJECT')
    result = f'Added bone chain: {{len(bones)}} bones ({{", ".join(bones)}})'
"""
        return _exec(code)

    @mcp.tool()
    def armature_add_constraint(
        armature_name: str,
        bone_name: str,
        constraint_type: str,
        target_armature: str = "",
        target_bone: str = "",
        params: dict = None,
    ) -> dict:
        """Add a constraint to a pose bone.

        Args:
            armature_name: Armature containing the bone
            bone_name: Bone to constrain
            constraint_type: COPY_LOCATION, COPY_ROTATION, COPY_SCALE,
                           TRACK_TO, DAMPED_TRACK, IK, LIMIT_ROTATION,
                           STRETCH_TO, FLOOR, CHILD_OF
            target_armature: Target armature object (for bone targets)
            target_bone: Target bone name
            params: Additional constraint parameters dict
        """
        params = params or {}
        params_str = str(params)
        target_arm = target_armature or armature_name
        code = f"""import bpy
arm_obj = bpy.data.objects.get('{armature_name}')
if not arm_obj or arm_obj.type != 'ARMATURE':
    result = "Error: Armature '{armature_name}' not found"
else:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pbone = arm_obj.pose.bones.get('{bone_name}')
    if not pbone:
        bpy.ops.object.mode_set(mode='OBJECT')
        result = "Error: Bone '{bone_name}' not found"
    else:
        c = pbone.constraints.new('{constraint_type}')
        if '{target_bone}':
            target = bpy.data.objects.get('{target_arm}')
            if target:
                c.target = target
                c.subtarget = '{target_bone}'

        params = {params_str}
        for k, v in params.items():
            try:
                setattr(c, k, v)
            except:
                pass

        bpy.ops.object.mode_set(mode='OBJECT')
        result = f'Added {constraint_type} to {{pbone.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def armature_auto_weight(
        armature_name: str,
        mesh_name: str,
    ) -> dict:
        """Parent mesh to armature with automatic weights.

        This is the standard way to skin a mesh to a skeleton.

        Args:
            armature_name: Armature to parent to
            mesh_name: Mesh to skin
        """
        code = f"""import bpy
arm = bpy.data.objects.get('{armature_name}')
mesh = bpy.data.objects.get('{mesh_name}')
if not arm or arm.type != 'ARMATURE':
    result = "Error: Armature '{armature_name}' not found"
elif not mesh or mesh.type != 'MESH':
    result = "Error: Mesh '{mesh_name}' not found"
else:
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    result = f'Auto-weighted {{mesh.name}} to {{arm.name}} ({{len(arm.data.bones)}} bones)'
"""
        return _exec(code)

    @mcp.tool()
    def armature_list_bones(armature_name: str) -> dict:
        """List all bones in an armature with hierarchy info."""
        code = f"""import bpy, json
arm_obj = bpy.data.objects.get('{armature_name}')
if not arm_obj or arm_obj.type != 'ARMATURE':
    result = "Error: Armature '{armature_name}' not found"
else:
    bones = []
    for b in arm_obj.data.bones:
        bones.append({{
            'name': b.name,
            'parent': b.parent.name if b.parent else None,
            'head': [round(x, 4) for x in b.head_local],
            'tail': [round(x, 4) for x in b.tail_local],
            'length': round(b.length, 4),
            'connected': b.use_connect,
            'children': len(b.children),
        }})
    result = json.dumps({{
        'armature': arm_obj.name,
        'bone_count': len(bones),
        'bones': bones,
    }}, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def armature_set_pose(
        armature_name: str,
        bone_poses: list = None,
    ) -> dict:
        """Set bone poses (rotation/location) on an armature.

        Args:
            armature_name: Target armature
            bone_poses: List of pose dicts:
                [{"bone": "Upper Arm.L", "rotation": [45, 0, 0], "location": [0, 0, 0]}]
                Rotation in degrees (Euler XYZ).
        """
        poses_str = str(bone_poses or [])
        code = f"""import bpy, math
arm_obj = bpy.data.objects.get('{armature_name}')
if not arm_obj or arm_obj.type != 'ARMATURE':
    result = "Error: Armature '{armature_name}' not found"
else:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    poses = {poses_str}
    applied = []
    for p in poses:
        pbone = arm_obj.pose.bones.get(p['bone'])
        if pbone:
            if 'rotation' in p:
                r = p['rotation']
                pbone.rotation_euler = (math.radians(r[0]), math.radians(r[1]), math.radians(r[2]))
            if 'location' in p:
                pbone.location = tuple(p['location'])
            applied.append(p['bone'])
    bpy.ops.object.mode_set(mode='OBJECT')
    result = f'Posed {{len(applied)}} bones: {{applied}}'
"""
        return _exec(code)
