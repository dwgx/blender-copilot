"""
Render preset tools — adapted from CLI-Anything render.py patterns.

Provides quick render preset switching, batch rendering, animation rendering,
and render region/layer management. 7 presets covering all common workflows.
"""
from typing import Dict, Any


# ─── Render Presets ───────────────────────────────────────────────────────────

RENDER_PRESETS: Dict[str, Dict[str, Any]] = {
    "cycles_preview": {
        "engine": "CYCLES",
        "samples": 32,
        "use_denoising": True,
        "denoiser": "OPENIMAGEDENOISE",
        "resolution_x": 1920,
        "resolution_y": 1080,
        "resolution_percentage": 50,
        "use_adaptive_sampling": True,
        "adaptive_threshold": 0.1,
        "film_transparent": False,
        "description": "Fast Cycles preview — 32 samples, 50% res, OID denoiser",
    },
    "cycles_default": {
        "engine": "CYCLES",
        "samples": 128,
        "use_denoising": True,
        "denoiser": "OPENIMAGEDENOISE",
        "resolution_x": 1920,
        "resolution_y": 1080,
        "resolution_percentage": 100,
        "use_adaptive_sampling": True,
        "adaptive_threshold": 0.01,
        "film_transparent": False,
        "description": "Standard Cycles — 128 samples, full res, OID denoiser",
    },
    "cycles_high": {
        "engine": "CYCLES",
        "samples": 512,
        "use_denoising": True,
        "denoiser": "OPENIMAGEDENOISE",
        "resolution_x": 3840,
        "resolution_y": 2160,
        "resolution_percentage": 100,
        "use_adaptive_sampling": True,
        "adaptive_threshold": 0.005,
        "film_transparent": False,
        "description": "High-quality Cycles — 512 samples, 4K, precise denoising",
    },
    "eevee_preview": {
        "engine": "BLENDER_EEVEE",
        "samples": 16,
        "resolution_x": 1920,
        "resolution_y": 1080,
        "resolution_percentage": 50,
        "use_bloom": False,
        "use_ssr": False,
        "use_gtao": False,
        "film_transparent": False,
        "description": "Fast EEVEE preview — 16 samples, 50% res, effects off",
    },
    "eevee_default": {
        "engine": "BLENDER_EEVEE",
        "samples": 64,
        "resolution_x": 1920,
        "resolution_y": 1080,
        "resolution_percentage": 100,
        "use_bloom": True,
        "use_ssr": True,
        "use_gtao": True,
        "film_transparent": False,
        "description": "Standard EEVEE — 64 samples, full res, all effects on",
    },
    "eevee_high": {
        "engine": "BLENDER_EEVEE",
        "samples": 128,
        "resolution_x": 3840,
        "resolution_y": 2160,
        "resolution_percentage": 100,
        "use_bloom": True,
        "use_ssr": True,
        "use_gtao": True,
        "film_transparent": False,
        "description": "High-quality EEVEE — 128 samples, 4K, all effects",
    },
    "workbench": {
        "engine": "BLENDER_WORKBENCH",
        "samples": 0,
        "resolution_x": 1920,
        "resolution_y": 1080,
        "resolution_percentage": 100,
        "film_transparent": False,
        "description": "Workbench solid view — instant, no raytracing",
    },
}


def register_render_tools(mcp, send_command_fn):
    """Register render preset and management MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def render_list_presets() -> dict:
        """List all available render presets with descriptions.

        Presets: cycles_preview, cycles_default, cycles_high,
                 eevee_preview, eevee_default, eevee_high, workbench.
        """
        return {
            "presets": {
                name: p["description"] for name, p in RENDER_PRESETS.items()
            }
        }

    @mcp.tool()
    def render_apply_preset(preset_name: str) -> dict:
        """Apply a render preset to the current scene.

        Available presets:
        - cycles_preview: Fast Cycles, 32 samples, 50% res
        - cycles_default: Standard Cycles, 128 samples, full HD
        - cycles_high: HQ Cycles, 512 samples, 4K
        - eevee_preview: Fast EEVEE, effects off, 50% res
        - eevee_default: Standard EEVEE, all effects, full HD
        - eevee_high: HQ EEVEE, all effects, 4K
        - workbench: Instant solid view render
        """
        if preset_name not in RENDER_PRESETS:
            return {"error": f"Unknown preset '{preset_name}'. Available: {list(RENDER_PRESETS.keys())}"}

        p = RENDER_PRESETS[preset_name]
        engine = p["engine"]

        lines = [
            "import bpy",
            "scene = bpy.context.scene",
            f"scene.render.engine = '{engine}'",
            f"scene.render.resolution_x = {p['resolution_x']}",
            f"scene.render.resolution_y = {p['resolution_y']}",
            f"scene.render.resolution_percentage = {p['resolution_percentage']}",
            f"scene.render.film_transparent = {p['film_transparent']}",
        ]

        if engine == "CYCLES":
            lines.extend([
                f"scene.cycles.samples = {p['samples']}",
                f"scene.cycles.use_denoising = {p['use_denoising']}",
                f"scene.cycles.use_adaptive_sampling = {p['use_adaptive_sampling']}",
                f"scene.cycles.adaptive_threshold = {p['adaptive_threshold']}",
            ])
            if p.get("use_denoising"):
                lines.append(f"scene.cycles.denoiser = '{p['denoiser']}'")
        elif engine == "BLENDER_EEVEE":
            lines.append(f"scene.eevee.taa_render_samples = {p['samples']}")
        # Workbench has no sample settings

        desc = p["description"]
        lines.append(f"result = 'Applied preset: {preset_name} — {desc}'")
        return _exec("\n".join(lines))

    @mcp.tool()
    def render_set_output(
        filepath: str,
        file_format: str = "PNG",
        color_mode: str = "RGBA",
        color_depth: str = "8",
        compression: int = 15,
        quality: int = 90,
    ) -> dict:
        """Configure render output path and format.

        Args:
            filepath: Output file path (use // for relative to .blend)
            file_format: PNG, JPEG, OPEN_EXR, TIFF, BMP, HDR
            color_mode: BW, RGB, RGBA
            color_depth: 8, 16, 32 (depends on format)
            compression: PNG compression 0-100 (default 15)
            quality: JPEG quality 0-100 (default 90)
        """
        code = f"""import bpy
scene = bpy.context.scene
scene.render.filepath = r'{filepath}'
scene.render.image_settings.file_format = '{file_format}'
scene.render.image_settings.color_mode = '{color_mode}'
scene.render.image_settings.color_depth = '{color_depth}'
"""
        if file_format == "PNG":
            code += f"scene.render.image_settings.compression = {compression}\n"
        elif file_format == "JPEG":
            code += f"scene.render.image_settings.quality = {quality}\n"

        code += f"result = f'Output: {{scene.render.filepath}} ({file_format} {color_mode} {color_depth}bit)'"
        return _exec(code)

    @mcp.tool()
    def render_still(filepath: str = "", open_after: bool = False) -> dict:
        """Render a single frame (still image).

        Args:
            filepath: Optional output path. If empty, uses scene default.
            open_after: If True, open the rendered image in Blender's viewer.
        """
        code = "import bpy\n"
        if filepath:
            code += f"bpy.context.scene.render.filepath = r'{filepath}'\n"
        code += "bpy.ops.render.render(write_still=True)\n"
        if open_after:
            code += "bpy.ops.render.view_show()\n"
        code += "result = f'Rendered: {bpy.context.scene.render.filepath}'"
        return _exec(code)

    @mcp.tool()
    def render_animation(
        filepath: str = "",
        frame_start: int = 0,
        frame_end: int = 0,
        file_format: str = "",
    ) -> dict:
        """Render an animation sequence.

        Args:
            filepath: Output path. For image sequences, use # for frame number.
            frame_start: Start frame (0 = use scene default)
            frame_end: End frame (0 = use scene default)
            file_format: Override format (FFMPEG for video, PNG for sequence)
        """
        code = "import bpy\nscene = bpy.context.scene\n"
        if filepath:
            code += f"scene.render.filepath = r'{filepath}'\n"
        if frame_start > 0:
            code += f"scene.frame_start = {frame_start}\n"
        if frame_end > 0:
            code += f"scene.frame_end = {frame_end}\n"
        if file_format:
            code += f"scene.render.image_settings.file_format = '{file_format}'\n"
            if file_format == "FFMPEG":
                code += "scene.render.ffmpeg.format = 'MPEG4'\n"
                code += "scene.render.ffmpeg.codec = 'H264'\n"
                code += "scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'\n"
        code += "bpy.ops.render.render(animation=True)\n"
        code += "result = f'Animation rendered: frames {scene.frame_start}-{scene.frame_end} to {scene.render.filepath}'"
        return _exec(code)

    @mcp.tool()
    def render_set_camera(camera_name: str = "", create_if_missing: bool = True) -> dict:
        """Set the active render camera.

        Args:
            camera_name: Name of camera object. Empty = auto-find or create.
            create_if_missing: Create a default camera if none exists.
        """
        code = f"""import bpy
cam = None
if '{camera_name}':
    cam = bpy.data.objects.get('{camera_name}')
    if cam and cam.type != 'CAMERA':
        cam = None

if not cam:
    # Find first camera in scene
    for obj in bpy.context.scene.objects:
        if obj.type == 'CAMERA':
            cam = obj
            break

if not cam and {create_if_missing}:
    cam_data = bpy.data.cameras.new('Camera')
    cam_data.lens = 50
    cam = bpy.data.objects.new('Camera', cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, -5, 2)
    import math
    cam.rotation_euler = (math.radians(75), 0, 0)

if cam:
    bpy.context.scene.camera = cam
    result = f'Active camera: {{cam.name}} at {{list(cam.location)}}'
else:
    result = 'Error: No camera found'
"""
        return _exec(code)

    @mcp.tool()
    def render_get_settings() -> dict:
        """Get current render settings — engine, resolution, samples, output, camera."""
        code = """import bpy
scene = bpy.context.scene
r = scene.render
engine = r.engine
info = {
    'engine': engine,
    'resolution': f'{r.resolution_x}x{r.resolution_y} @ {r.resolution_percentage}%',
    'output_path': r.filepath,
    'file_format': r.image_settings.file_format,
    'film_transparent': r.film_transparent,
    'camera': scene.camera.name if scene.camera else None,
    'frame_range': f'{scene.frame_start}-{scene.frame_end}',
}
if engine == 'CYCLES':
    info['samples'] = scene.cycles.samples
    info['denoising'] = scene.cycles.use_denoising
    info['adaptive_sampling'] = scene.cycles.use_adaptive_sampling
elif engine == 'BLENDER_EEVEE':
    info['samples'] = scene.eevee.taa_render_samples
import json
result = json.dumps(info, indent=2)
"""
        return _exec(code)

    @mcp.tool()
    def render_set_world(
        color: list = None,
        hdri_path: str = "",
        strength: float = 1.0,
    ) -> dict:
        """Set world background — solid color or HDRI.

        Args:
            color: RGB [r, g, b] for solid color (0-1 range)
            hdri_path: Path to .hdr/.exr file for environment lighting
            strength: Background strength multiplier
        """
        if hdri_path:
            code = f"""import bpy
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new('World')
    bpy.context.scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
bg = nt.nodes.new('ShaderNodeBackground')
bg.inputs['Strength'].default_value = {strength}
env = nt.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(r'{hdri_path}')
mapping = nt.nodes.new('ShaderNodeMapping')
coord = nt.nodes.new('ShaderNodeTexCoord')
output = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
nt.links.new(mapping.outputs['Vector'], env.inputs['Vector'])
nt.links.new(env.outputs['Color'], bg.inputs['Color'])
nt.links.new(bg.outputs['Background'], output.inputs['Surface'])
result = f'World HDRI: {hdri_path}, strength={strength}'
"""
        elif color:
            r, g, b = color[0], color[1], color[2]
            code = f"""import bpy
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new('World')
    bpy.context.scene.world = world
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = ({r}, {g}, {b}, 1.0)
    bg.inputs['Strength'].default_value = {strength}
result = f'World color: ({r}, {g}, {b}), strength={strength}'
"""
        else:
            return {"error": "Provide either color=[r,g,b] or hdri_path"}
        return _exec(code)
