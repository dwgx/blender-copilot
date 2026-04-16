"""
Physics tools — rigid body, cloth, fluid, particles, soft body.

Adapted from blend-ai physics module. Provides physics simulation
setup, baking, and common physics presets.
"""


def register_physics_tools(mcp, send_command_fn):
    """Register physics simulation MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def physics_add_rigid_body(
        object_name: str,
        body_type: str = "ACTIVE",
        mass: float = 1.0,
        friction: float = 0.5,
        restitution: float = 0.5,
        collision_shape: str = "CONVEX_HULL",
    ) -> dict:
        """Add rigid body physics to an object.

        Args:
            object_name: Target object
            body_type: ACTIVE (affected by physics) or PASSIVE (static collider)
            mass: Object mass in kg (ACTIVE only)
            friction: Surface friction (0-1)
            restitution: Bounciness (0-1)
            collision_shape: BOX, SPHERE, CAPSULE, CYLINDER, CONE, CONVEX_HULL, MESH
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add(type='{body_type}')
    rb = obj.rigid_body
    rb.mass = {mass}
    rb.friction = {friction}
    rb.restitution = {restitution}
    rb.collision_shape = '{collision_shape}'
    result = f'Rigid body ({body_type}) on {{obj.name}}: mass={mass}kg, shape={collision_shape}'
"""
        return _exec(code)

    @mcp.tool()
    def physics_add_cloth(
        object_name: str,
        quality: int = 5,
        mass: float = 0.3,
        stiffness: float = 15.0,
        damping: float = 5.0,
        use_self_collision: bool = False,
    ) -> dict:
        """Add cloth physics simulation to a mesh.

        Args:
            object_name: Target mesh object
            quality: Simulation quality steps (1-80)
            mass: Cloth mass
            stiffness: Structural stiffness
            damping: Damping factor
            use_self_collision: Enable self-collision detection
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_add(type='CLOTH')
    cloth = obj.modifiers['Cloth']
    cloth.settings.quality = {quality}
    cloth.settings.mass = {mass}
    cloth.settings.tension_stiffness = {stiffness}
    cloth.settings.tension_damping = {damping}
    cloth.collision_settings.use_self_collision = {use_self_collision}
    result = f'Cloth physics on {{obj.name}}: mass={mass}, stiffness={stiffness}'
"""
        return _exec(code)

    @mcp.tool()
    def physics_add_collision(object_name: str, thickness_outer: float = 0.02) -> dict:
        """Add collision physics to an object (makes it a collider for cloth/particles).

        Args:
            object_name: Target object
            thickness_outer: Collision surface thickness
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_add(type='COLLISION')
    col = obj.modifiers['Collision']
    col.settings.thickness_outer = {thickness_outer}
    result = f'Collision on {{obj.name}}: thickness={thickness_outer}'
"""
        return _exec(code)

    @mcp.tool()
    def physics_add_particle_system(
        object_name: str,
        count: int = 1000,
        lifetime: int = 50,
        emit_from: str = "FACE",
        velocity_normal: float = 1.0,
        gravity: float = 1.0,
        size: float = 0.05,
        physics_type: str = "NEWTON",
    ) -> dict:
        """Add a particle system to an object.

        Args:
            object_name: Emitter object
            count: Number of particles
            lifetime: Particle lifetime in frames
            emit_from: VERT, FACE, VOLUME
            velocity_normal: Emission velocity along normals
            gravity: Gravity multiplier
            size: Particle display/render size
            physics_type: NEWTON, KEYED, BOIDS, FLUID
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.particle_system_add()
    ps = obj.particle_systems[-1]
    settings = ps.settings
    settings.count = {count}
    settings.lifetime = {lifetime}
    settings.emit_from = '{emit_from}'
    settings.normal_factor = {velocity_normal}
    settings.effector_weights.gravity = {gravity}
    settings.particle_size = {size}
    settings.physics_type = '{physics_type}'
    result = f'Particle system on {{obj.name}}: {{count}} particles, lifetime={lifetime}'
"""
        return _exec(code)

    @mcp.tool()
    def physics_add_soft_body(
        object_name: str,
        mass: float = 1.0,
        friction: float = 0.5,
        speed: float = 1.0,
        goal_strength: float = 0.7,
    ) -> dict:
        """Add soft body physics to an object.

        Args:
            object_name: Target object
            mass: Total mass
            friction: Surface friction
            speed: Simulation speed multiplier
            goal_strength: How strongly mesh holds original shape (0=floppy, 1=rigid)
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_add(type='SOFT_BODY')
    sb = obj.modifiers['Softbody']
    sb.settings.mass = {mass}
    sb.settings.friction = {friction}
    sb.settings.speed = {speed}
    sb.settings.goal_spring = {goal_strength}
    result = f'Soft body on {{obj.name}}: mass={mass}, goal={goal_strength}'
"""
        return _exec(code)

    @mcp.tool()
    def physics_bake(
        frame_start: int = 1,
        frame_end: int = 250,
        bake_type: str = "ALL",
    ) -> dict:
        """Bake physics simulation for all objects in the scene.

        Args:
            frame_start: Bake start frame
            frame_end: Bake end frame
            bake_type: ALL (all physics), or specific type
        """
        code = f"""import bpy
scene = bpy.context.scene
scene.frame_start = {frame_start}
scene.frame_end = {frame_end}

# Bake all physics
override = bpy.context.copy()
try:
    bpy.ops.ptcache.bake_all(bake=True)
    result = f'Physics baked: frames {frame_start}-{frame_end}'
except Exception as e:
    result = f'Bake attempted: {{str(e)}}'
"""
        return _exec(code)

    @mcp.tool()
    def physics_remove(object_name: str, physics_type: str = "ALL") -> dict:
        """Remove physics from an object.

        Args:
            object_name: Target object
            physics_type: RIGID_BODY, CLOTH, COLLISION, SOFT_BODY, PARTICLE, ALL
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    bpy.context.view_layer.objects.active = obj
    removed = []
    ptype = '{physics_type}'

    if ptype in ('ALL', 'RIGID_BODY') and obj.rigid_body:
        bpy.ops.rigidbody.object_remove()
        removed.append('rigid_body')

    mods_to_remove = []
    for mod in obj.modifiers:
        if ptype == 'ALL' or mod.type == ptype:
            if mod.type in ('CLOTH', 'COLLISION', 'SOFT_BODY', 'PARTICLE_SYSTEM'):
                mods_to_remove.append(mod.name)

    for name in mods_to_remove:
        obj.modifiers.remove(obj.modifiers[name])
        removed.append(name)

    if ptype in ('ALL', 'PARTICLE'):
        while obj.particle_systems:
            bpy.ops.object.particle_system_remove()
            removed.append('particle_system')

    result = f'Removed physics from {{obj.name}}: {{removed}}'
"""
        return _exec(code)
