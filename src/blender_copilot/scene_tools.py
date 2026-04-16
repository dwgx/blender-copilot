"""
Scene profile tools — adapted from CLI-Anything scene.py patterns.

Provides 10 scene profile templates for common workflows, plus scene
management utilities (collections, visibility, cleanup, stats).
"""
from typing import Dict, Any, List, Optional


# ─── Scene Profiles ──────────────────────────────────────────────────────────

SCENE_PROFILES: Dict[str, Dict[str, Any]] = {
    "preview": {
        "resolution_x": 960,
        "resolution_y": 540,
        "engine": "BLENDER_EEVEE",
        "samples": 16,
        "description": "Quick preview — 960x540 EEVEE",
    },
    "hd720p": {
        "resolution_x": 1280,
        "resolution_y": 720,
        "engine": "BLENDER_EEVEE",
        "samples": 64,
        "description": "720p HD — EEVEE standard",
    },
    "hd1080p": {
        "resolution_x": 1920,
        "resolution_y": 1080,
        "engine": "CYCLES",
        "samples": 128,
        "description": "1080p Full HD — Cycles quality",
    },
    "4k": {
        "resolution_x": 3840,
        "resolution_y": 2160,
        "engine": "CYCLES",
        "samples": 256,
        "description": "4K UHD — Cycles high quality",
    },
    "instagram_square": {
        "resolution_x": 1080,
        "resolution_y": 1080,
        "engine": "BLENDER_EEVEE",
        "samples": 64,
        "description": "Instagram square 1:1 — 1080x1080 EEVEE",
    },
    "instagram_story": {
        "resolution_x": 1080,
        "resolution_y": 1920,
        "engine": "BLENDER_EEVEE",
        "samples": 64,
        "description": "Instagram story 9:16 — 1080x1920 EEVEE",
    },
    "youtube_thumbnail": {
        "resolution_x": 1280,
        "resolution_y": 720,
        "engine": "BLENDER_EEVEE",
        "samples": 32,
        "description": "YouTube thumbnail — 1280x720 fast",
    },
    "product_render": {
        "resolution_x": 2048,
        "resolution_y": 2048,
        "engine": "CYCLES",
        "samples": 256,
        "film_transparent": True,
        "description": "Product shot — 2048x2048 Cycles, transparent BG",
    },
    "turntable": {
        "resolution_x": 1920,
        "resolution_y": 1080,
        "engine": "BLENDER_EEVEE",
        "samples": 64,
        "frame_end": 120,
        "fps": 30,
        "description": "360° turntable — 120 frames, 30fps, EEVEE",
    },
    "vrc_avatar_preview": {
        "resolution_x": 1200,
        "resolution_y": 1600,
        "engine": "BLENDER_EEVEE",
        "samples": 32,
        "film_transparent": True,
        "description": "VRC avatar card — 1200x1600 portrait, transparent",
    },
}


def register_scene_tools(mcp, send_command_fn):
    """Register scene profile and management MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def scene_list_profiles() -> dict:
        """List all available scene profiles with descriptions.

        Profiles cover: preview, hd720p, hd1080p, 4k, instagram_square,
        instagram_story, youtube_thumbnail, product_render, turntable, vrc_avatar_preview.
        """
        return {
            "profiles": {
                name: p["description"] for name, p in SCENE_PROFILES.items()
            }
        }

    @mcp.tool()
    def scene_apply_profile(profile_name: str) -> dict:
        """Apply a scene profile (resolution, engine, samples, etc).

        Available profiles:
        - preview: 960x540 EEVEE fast
        - hd720p: 1280x720 EEVEE
        - hd1080p: 1920x1080 Cycles
        - 4k: 3840x2160 Cycles HQ
        - instagram_square: 1080x1080
        - instagram_story: 1080x1920 vertical
        - youtube_thumbnail: 1280x720 fast
        - product_render: 2048x2048 transparent Cycles
        - turntable: 1080p 120-frame rotation
        - vrc_avatar_preview: 1200x1600 portrait transparent
        """
        if profile_name not in SCENE_PROFILES:
            return {"error": f"Unknown profile '{profile_name}'. Available: {list(SCENE_PROFILES.keys())}"}

        p = SCENE_PROFILES[profile_name]
        engine = p["engine"]

        lines = [
            "import bpy",
            "scene = bpy.context.scene",
            f"scene.render.engine = '{engine}'",
            f"scene.render.resolution_x = {p['resolution_x']}",
            f"scene.render.resolution_y = {p['resolution_y']}",
            "scene.render.resolution_percentage = 100",
        ]

        if p.get("film_transparent", False):
            lines.append("scene.render.film_transparent = True")

        if engine == "CYCLES":
            lines.append(f"scene.cycles.samples = {p['samples']}")
            lines.append("scene.cycles.use_denoising = True")
        elif engine == "BLENDER_EEVEE":
            lines.append(f"scene.eevee.taa_render_samples = {p['samples']}")

        if "frame_end" in p:
            lines.append(f"scene.frame_end = {p['frame_end']}")
        if "fps" in p:
            lines.append(f"scene.render.fps = {p['fps']}")

        desc = p["description"]
        lines.append(f"result = 'Applied profile: {profile_name} — {desc}'")
        return _exec("\n".join(lines))

    @mcp.tool()
    def scene_setup_turntable(
        target_name: str = "",
        frames: int = 120,
        radius: float = 5.0,
        height: float = 1.5,
        focal_length: float = 85,
    ) -> dict:
        """Set up a 360° turntable camera animation around a target object.

        Creates a camera orbiting the target with smooth rotation.
        Great for showcasing models and avatars.

        Args:
            target_name: Object to orbit around (empty = scene center)
            frames: Number of frames for full rotation (default 120)
            radius: Camera orbit radius
            height: Camera height
            focal_length: Camera lens mm
        """
        code = f"""import bpy, math

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = {frames}

# Create empty at target
target = None
if '{target_name}':
    target = bpy.data.objects.get('{target_name}')

pivot_loc = list(target.location) if target else [0, 0, 0]

# Create camera
cam_data = bpy.data.cameras.new('Turntable_Camera')
cam_data.lens = {focal_length}
cam = bpy.data.objects.new('Turntable_Camera', cam_data)
bpy.context.collection.objects.link(cam)
scene.camera = cam

# Create empty for orbit pivot
empty = bpy.data.objects.new('Turntable_Pivot', None)
empty.location = pivot_loc
bpy.context.collection.objects.link(empty)

# Parent camera to empty
cam.parent = empty
cam.location = (0, -{radius}, {height})
cam.rotation_euler = (math.radians(80), 0, 0)

# Add rotation keyframes
empty.rotation_euler = (0, 0, 0)
empty.keyframe_insert('rotation_euler', frame=1)
empty.rotation_euler = (0, 0, math.radians(360))
empty.keyframe_insert('rotation_euler', frame={frames})

# Linear interpolation for smooth rotation
for fc in empty.animation_data.action.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'

result = f'Turntable: {{cam.name}} orbiting at r={radius}, h={height}, {frames} frames'
"""
        return _exec(code)

    @mcp.tool()
    def scene_create_collection(name: str, parent: str = "", color_tag: str = "") -> dict:
        """Create a new collection in the scene.

        Args:
            name: Collection name
            parent: Parent collection name (empty = Scene Collection)
            color_tag: COLOR_01 through COLOR_08, or NONE
        """
        code = f"""import bpy
col = bpy.data.collections.new('{name}')
parent_col = None
if '{parent}':
    parent_col = bpy.data.collections.get('{parent}')
if parent_col:
    parent_col.children.link(col)
else:
    bpy.context.scene.collection.children.link(col)
if '{color_tag}':
    col.color_tag = '{color_tag}'
result = f'Created collection: {{col.name}}'
"""
        return _exec(code)

    @mcp.tool()
    def scene_move_to_collection(object_names: list, collection_name: str) -> dict:
        """Move objects to a collection.

        Args:
            object_names: List of object names to move
            collection_name: Target collection name
        """
        names_str = str(object_names)
        code = f"""import bpy
target_col = bpy.data.collections.get('{collection_name}')
if not target_col:
    result = "Error: Collection '{collection_name}' not found"
else:
    moved = []
    for name in {names_str}:
        obj = bpy.data.objects.get(name)
        if obj:
            for col in obj.users_collection:
                col.objects.unlink(obj)
            target_col.objects.link(obj)
            moved.append(name)
    result = f'Moved {{len(moved)}} objects to {collection_name}: {{moved}}'
"""
        return _exec(code)

    @mcp.tool()
    def scene_cleanup(
        remove_unused_materials: bool = True,
        remove_unused_meshes: bool = True,
        remove_unused_images: bool = True,
        remove_unused_textures: bool = True,
    ) -> dict:
        """Clean up unused data blocks from the scene.

        Removes orphaned materials, meshes, images, and textures
        that have zero users. Reduces file size and clutter.
        """
        code = f"""import bpy
removed = {{}}
if {remove_unused_materials}:
    count = 0
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
            count += 1
    removed['materials'] = count

if {remove_unused_meshes}:
    count = 0
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
            count += 1
    removed['meshes'] = count

if {remove_unused_images}:
    count = 0
    for img in list(bpy.data.images):
        if img.users == 0:
            bpy.data.images.remove(img)
            count += 1
    removed['images'] = count

if {remove_unused_textures}:
    count = 0
    for tex in list(bpy.data.textures):
        if tex.users == 0:
            bpy.data.textures.remove(tex)
            count += 1
    removed['textures'] = count

import json
result = json.dumps({{'cleanup': removed, 'total': sum(removed.values())}})
"""
        return _exec(code)

    @mcp.tool()
    def scene_stats() -> dict:
        """Get comprehensive scene statistics.

        Returns object counts by type, total vertices/faces/edges,
        material count, texture memory, collection tree, and frame range.
        """
        code = """import bpy
import json

scene = bpy.context.scene
objects = scene.objects

# Count by type
type_counts = {}
total_verts = 0
total_faces = 0
total_edges = 0

for obj in objects:
    t = obj.type
    type_counts[t] = type_counts.get(t, 0) + 1
    if obj.type == 'MESH' and obj.data:
        total_verts += len(obj.data.vertices)
        total_faces += len(obj.data.polygons)
        total_edges += len(obj.data.edges)

# Collections
collections = [c.name for c in bpy.data.collections]

# Memory estimate for textures
tex_memory = 0
for img in bpy.data.images:
    if img.size[0] > 0:
        bpp = 4 if img.channels == 4 else 3
        tex_memory += img.size[0] * img.size[1] * bpp

stats = {
    'objects': len(objects),
    'object_types': type_counts,
    'total_vertices': total_verts,
    'total_faces': total_faces,
    'total_edges': total_edges,
    'materials': len(bpy.data.materials),
    'images': len(bpy.data.images),
    'texture_memory_mb': round(tex_memory / (1024*1024), 2),
    'collections': collections,
    'frame_range': f'{scene.frame_start}-{scene.frame_end}',
    'fps': scene.render.fps,
    'engine': scene.render.engine,
    'resolution': f'{scene.render.resolution_x}x{scene.render.resolution_y}',
}
result = json.dumps(stats, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def scene_set_units(
        system: str = "METRIC",
        length: str = "METERS",
        scale_length: float = 1.0,
    ) -> dict:
        """Set scene unit system.

        Args:
            system: METRIC, IMPERIAL, or NONE
            length: KILOMETERS, METERS, CENTIMETERS, MILLIMETERS, MILES, FEET, INCHES
            scale_length: Unit scale factor (default 1.0)
        """
        code = f"""import bpy
scene = bpy.context.scene
scene.unit_settings.system = '{system}'
scene.unit_settings.length_unit = '{length}'
scene.unit_settings.scale_length = {scale_length}
result = f'Units: {system} / {length} / scale={scale_length}'
"""
        return _exec(code)

    @mcp.tool()
    def scene_set_visibility(
        object_name: str,
        viewport: bool = True,
        render: bool = True,
        selectable: bool = True,
    ) -> dict:
        """Set object visibility in viewport and render.

        Args:
            object_name: Name of the object
            viewport: Show in viewport
            render: Show in renders
            selectable: Allow selection in viewport
        """
        code = f"""import bpy
obj = bpy.data.objects.get('{object_name}')
if not obj:
    result = "Error: Object '{object_name}' not found"
else:
    obj.hide_viewport = not {viewport}
    obj.hide_render = not {render}
    obj.hide_select = not {selectable}
    result = f'{{obj.name}}: viewport={viewport}, render={render}, selectable={selectable}'
"""
        return _exec(code)
