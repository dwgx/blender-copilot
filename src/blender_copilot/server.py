"""
Blender Copilot MCP Server
The most comprehensive Blender MCP server - 70+ AI-powered 3D creation tools.

Connects to the Blender Copilot addon via TCP socket and exposes all tools
through the Model Context Protocol (MCP).
"""

import json
import socket
import sys
import os
import base64
from typing import Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Blender Copilot",
    description="The most comprehensive Blender MCP server - AI-powered 3D creation with 70+ tools",
)

BLENDER_HOST = os.environ.get("BLENDER_HOST", "localhost")
BLENDER_PORT = int(os.environ.get("BLENDER_PORT", "9876"))


def send_command(command_type: str, params: dict | None = None) -> dict:
    """Send a command to the Blender Copilot addon via TCP and return the result."""
    payload = {"type": command_type}
    if params:
        # Strip None values so Blender gets clean kwargs
        payload["params"] = {k: v for k, v in params.items() if v is not None}
    data = json.dumps(payload).encode("utf-8")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(120)
        sock.connect((BLENDER_HOST, BLENDER_PORT))
        sock.sendall(data)

        # Read response
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            # Try to parse - if valid JSON we're done
            try:
                json.loads(b"".join(chunks).decode("utf-8"))
                break
            except json.JSONDecodeError:
                continue
        sock.close()

        if not chunks:
            return {"status": "error", "message": "Empty response from Blender"}
        resp = json.loads(b"".join(chunks).decode("utf-8"))
        if resp.get("status") == "error":
            raise Exception(resp.get("message", "Unknown error from Blender"))
        return resp.get("result", resp)
    except ConnectionRefusedError:
        raise Exception(
            "Cannot connect to Blender. Make sure Blender is running "
            "and the Copilot addon is started (port {}).".format(BLENDER_PORT)
        )
    except socket.timeout:
        raise Exception("Blender command timed out after 120 seconds.")


# =============================================================================
#  SCENE INSPECTION
# =============================================================================

@mcp.tool()
def get_scene_info() -> dict:
    """Get complete scene information including all objects, camera, render settings, and frame range.
    Returns object names, types, locations, vertex/face counts for meshes, and scene metadata."""
    return send_command("get_scene_info")


@mcp.tool()
def get_object_info(name: str) -> dict:
    """Get detailed information about a specific object by name.
    Returns location, rotation, scale, materials, modifiers, constraints,
    vertex/edge/face counts, bounding box, and parent/child hierarchy."""
    return send_command("get_object_info", {"name": name})


@mcp.tool()
def analyze_scene() -> dict:
    """Analyze the entire scene for statistics and potential issues.
    Returns total vertex/face/triangle counts, object type breakdown, material count,
    top objects by triangle count, and issues like non-uniform scale, missing materials, n-gons."""
    return send_command("analyze_scene")


@mcp.tool()
def get_viewport_screenshot(max_size: int = 800) -> dict:
    """Capture a screenshot of the 3D viewport. Returns the file path to the saved image.
    Uses OpenGL render for speed. Useful for visual verification of scene state."""
    return send_command("get_viewport_screenshot", {"max_size": max_size})


# =============================================================================
#  OBJECT CREATION
# =============================================================================

@mcp.tool()
def create_object(
    type: str = "CUBE",
    name: str | None = None,
    location: list[float] | None = None,
    scale: list[float] | None = None,
    rotation: list[float] | None = None,
) -> dict:
    """Create a 3D primitive object in the scene.
    Types: CUBE, SPHERE, UV_SPHERE, ICO_SPHERE, CYLINDER, CONE, TORUS, PLANE, CIRCLE,
    GRID, MONKEY, EMPTY, CAMERA, LIGHT, POINT_LIGHT, SUN_LIGHT, SPOT_LIGHT, AREA_LIGHT.
    Location is [x, y, z]. Rotation is in degrees [x, y, z]. Scale is [x, y, z]."""
    return send_command("create_object", {
        "type": type, "name": name, "location": location,
        "scale": scale, "rotation": rotation,
    })


@mcp.tool()
def create_curve(
    points: list[list[float]],
    name: str | None = None,
    type: str = "BEZIER",
    bevel_depth: float = 0.0,
    resolution: int = 12,
    close: bool = False,
    extrude: float = 0.0,
    fill: str = "FULL",
) -> dict:
    """Create a curve from a list of control points.
    Each point is [x, y, z] (or [x, y, z, w] for NURBS).
    Types: BEZIER, NURBS, POLY. Set bevel_depth > 0 for tubular curves.
    Set close=True for closed loops. Fill modes: FULL, BACK, FRONT, NONE."""
    return send_command("create_curve", {
        "points": points, "name": name, "type": type,
        "bevel_depth": bevel_depth, "resolution": resolution,
        "close": close, "extrude": extrude, "fill": fill,
    })


@mcp.tool()
def create_text(
    text: str,
    name: str | None = None,
    size: float = 1.0,
    extrude: float = 0.0,
    bevel_depth: float = 0.0,
    font_path: str | None = None,
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    align_x: str = "CENTER",
    align_y: str = "CENTER",
) -> dict:
    """Create a 3D text object. Set extrude > 0 for 3D text depth.
    Set bevel_depth > 0 for beveled edges. Rotation in degrees.
    Alignment options: LEFT, CENTER, RIGHT for X; TOP, CENTER, BOTTOM for Y."""
    return send_command("create_text", {
        "text": text, "name": name, "size": size, "extrude": extrude,
        "bevel_depth": bevel_depth, "font_path": font_path,
        "location": location, "rotation": rotation,
        "align_x": align_x, "align_y": align_y,
    })


@mcp.tool()
def create_armature(
    name: str | None = None,
    bones: list[dict] | None = None,
) -> dict:
    """Create an armature (skeleton) with bones for rigging.
    Each bone dict: {"name": "BoneName", "head": [x,y,z], "tail": [x,y,z], "parent": "ParentBone"}.
    Parent is optional. Bones are created in edit mode then switched back to object mode."""
    return send_command("create_armature", {"name": name, "bones": bones})


# =============================================================================
#  OBJECT TRANSFORMS
# =============================================================================

@mcp.tool()
def translate_object(
    name: str, x: float = 0.0, y: float = 0.0, z: float = 0.0, relative: bool = True
) -> dict:
    """Move an object. If relative=True (default), adds to current position.
    If relative=False, sets absolute position. Units are Blender units (meters)."""
    return send_command("translate_object", {
        "name": name, "x": x, "y": y, "z": z, "relative": relative,
    })


@mcp.tool()
def rotate_object(
    name: str, x: float = 0.0, y: float = 0.0, z: float = 0.0,
    relative: bool = True, degrees: bool = True,
) -> dict:
    """Rotate an object. Values are in degrees by default. If relative=True, adds to current rotation."""
    return send_command("rotate_object", {
        "name": name, "x": x, "y": y, "z": z,
        "relative": relative, "degrees": degrees,
    })


@mcp.tool()
def scale_object(
    name: str, x: float = 1.0, y: float = 1.0, z: float = 1.0,
    uniform: float | None = None, relative: bool = True,
) -> dict:
    """Scale an object. Set uniform to scale equally on all axes.
    If relative=True, multiplies current scale. If False, sets absolute scale."""
    return send_command("scale_object", {
        "name": name, "x": x, "y": y, "z": z,
        "uniform": uniform, "relative": relative,
    })


@mcp.tool()
def apply_transform(
    name: str, location: bool = True, rotation: bool = True, scale: bool = True
) -> dict:
    """Apply (freeze) the object's transforms, resetting them to identity.
    Essential before export or after non-uniform scaling."""
    return send_command("apply_transform", {
        "name": name, "location": location, "rotation": rotation, "scale": scale,
    })


@mcp.tool()
def snap_to_ground(name: str) -> dict:
    """Snap an object's lowest point to Z=0 (the ground plane).
    Useful for placing objects on a floor or surface."""
    return send_command("snap_to_ground", {"name": name})


@mcp.tool()
def origin_set(name: str, type: str = "ORIGIN_GEOMETRY") -> dict:
    """Set the origin point of an object.
    Types: ORIGIN_GEOMETRY (center of geometry), ORIGIN_CENTER_OF_MASS,
    ORIGIN_CENTER_OF_VOLUME, ORIGIN_CURSOR, GEOMETRY_ORIGIN."""
    return send_command("origin_set", {"name": name, "type": type})


# =============================================================================
#  OBJECT MANAGEMENT
# =============================================================================

@mcp.tool()
def duplicate_object(
    name: str, new_name: str | None = None, linked: bool = False
) -> dict:
    """Duplicate an object. If linked=True, shares mesh data (instance).
    If linked=False (default), creates an independent copy."""
    return send_command("duplicate_object", {
        "name": name, "new_name": new_name, "linked": linked,
    })


@mcp.tool()
def delete_object(name: str) -> dict:
    """Delete an object from the scene by name."""
    return send_command("delete_object", {"name": name})


@mcp.tool()
def select_object(name: str, add: bool = False) -> dict:
    """Select an object and make it active. If add=False (default), deselects all others first."""
    return send_command("select_object", {"name": name, "add": add})


@mcp.tool()
def set_parent(child: str, parent: str, keep_transform: bool = True) -> dict:
    """Set parent-child relationship. If keep_transform=True, child maintains its world position."""
    return send_command("set_parent", {
        "child": child, "parent": parent, "keep_transform": keep_transform,
    })


@mcp.tool()
def clear_parent(name: str, keep_transform: bool = True) -> dict:
    """Remove parent from an object. If keep_transform=True, object stays in place."""
    return send_command("clear_parent", {"name": name, "keep_transform": keep_transform})


@mcp.tool()
def set_visibility(
    name: str, visible: bool = True, render_visible: bool = True
) -> dict:
    """Set viewport and render visibility of an object."""
    return send_command("set_visibility", {
        "name": name, "visible": visible, "render_visible": render_visible,
    })


@mcp.tool()
def get_hierarchy(name: str | None = None) -> dict:
    """Get the parent-child hierarchy tree. If name is given, returns that object's subtree.
    If no name, returns all root objects and their children."""
    return send_command("get_hierarchy", {"name": name} if name else {})


@mcp.tool()
def rename_object(name: str, new_name: str) -> dict:
    """Rename an object. Blender may append .001 if the name already exists."""
    return send_command("rename_object", {"name": name, "new_name": new_name})


# =============================================================================
#  UNDO / REDO
# =============================================================================

@mcp.tool()
def undo() -> dict:
    """Undo the last operation in Blender."""
    return send_command("undo")


@mcp.tool()
def redo() -> dict:
    """Redo the last undone operation in Blender."""
    return send_command("redo")


# =============================================================================
#  MESH EDITING
# =============================================================================

@mcp.tool()
def boolean_operation(
    target: str, cutter: str, operation: str = "DIFFERENCE", apply: bool = True
) -> dict:
    """Perform a boolean operation between two mesh objects.
    Operations: DIFFERENCE (subtract), UNION (add), INTERSECT (overlap only).
    If apply=True, the modifier is applied and the cutter is removed."""
    return send_command("boolean_operation", {
        "target": target, "cutter": cutter,
        "operation": operation, "apply": apply,
    })


@mcp.tool()
def join_objects(names: list[str]) -> dict:
    """Join multiple objects into one. All objects are merged into the first one in the list."""
    return send_command("join_objects", {"names": names})


@mcp.tool()
def separate_object(name: str, mode: str = "LOOSE") -> dict:
    """Separate an object into multiple objects.
    Modes: LOOSE (by loose parts), MATERIAL (by material), SELECTED (by selection)."""
    return send_command("separate_object", {"name": name, "mode": mode})


@mcp.tool()
def subdivide(name: str, cuts: int = 1, smooth: float = 0.0) -> dict:
    """Subdivide all faces of a mesh. Cuts = number of subdivision levels.
    Smooth > 0 applies smoothing to subdivided vertices."""
    return send_command("subdivide", {"name": name, "cuts": cuts, "smooth": smooth})


@mcp.tool()
def extrude_faces(name: str, offset: float = 1.0) -> dict:
    """Extrude all faces of a mesh along their normals by the given offset distance."""
    return send_command("extrude_faces", {"name": name, "offset": offset})


@mcp.tool()
def bevel_edges(name: str, width: float = 0.1, segments: int = 3) -> dict:
    """Bevel all edges of a mesh. Width controls bevel size, segments controls smoothness."""
    return send_command("bevel_edges", {"name": name, "width": width, "segments": segments})


@mcp.tool()
def inset_faces(name: str, thickness: float = 0.1, depth: float = 0.0) -> dict:
    """Inset all faces of a mesh. Thickness controls inset distance, depth controls push in/out."""
    return send_command("inset_faces", {"name": name, "thickness": thickness, "depth": depth})


@mcp.tool()
def shade_smooth(name: str, smooth: bool = True) -> dict:
    """Set smooth or flat shading on an object. smooth=True for smooth, False for flat."""
    return send_command("shade_smooth", {"name": name, "smooth": smooth})


@mcp.tool()
def decimate(name: str, ratio: float = 0.5) -> dict:
    """Reduce mesh polygon count. Ratio 0.5 = reduce to 50% of original faces.
    Lower ratio = more reduction. Applies modifier immediately."""
    return send_command("decimate", {"name": name, "ratio": ratio})


@mcp.tool()
def remesh(name: str, voxel_size: float = 0.1, mode: str = "VOXEL") -> dict:
    """Remesh an object to create clean, uniform topology.
    Modes: VOXEL (uniform voxels), SMOOTH, SHARP, BLOCKS.
    Smaller voxel_size = higher detail but more polygons."""
    return send_command("remesh", {"name": name, "voxel_size": voxel_size, "mode": mode})


@mcp.tool()
def merge_by_distance(name: str, threshold: float = 0.0001) -> dict:
    """Merge vertices that are closer than the threshold distance.
    Useful for cleaning up duplicate vertices after boolean operations."""
    return send_command("merge_by_distance", {"name": name, "threshold": threshold})


@mcp.tool()
def flip_normals(name: str) -> dict:
    """Flip all face normals of a mesh. Useful when faces appear inside-out."""
    return send_command("flip_normals", {"name": name})


@mcp.tool()
def fill_holes(name: str) -> dict:
    """Automatically detect and fill holes in a mesh by selecting non-manifold edges and filling."""
    return send_command("fill_holes", {"name": name})


@mcp.tool()
def bridge_edge_loops(name: str) -> dict:
    """Bridge two selected edge loops to create connecting faces.
    The object must have exactly two edge loops selected in edit mode."""
    return send_command("bridge_edge_loops", {"name": name})


# =============================================================================
#  MODIFIERS
# =============================================================================

@mcp.tool()
def add_modifier(
    name: str, modifier_type: str,
    properties: dict | None = None, modifier_name: str | None = None,
) -> dict:
    """Add a modifier to an object. Common types: SUBSURF, MIRROR, ARRAY, SOLIDIFY,
    BEVEL, BOOLEAN, SHRINKWRAP, REMESH, DECIMATE, SMOOTH, CAST, WAVE, DISPLACE, LATTICE.
    Properties dict sets modifier attributes, e.g. {"levels": 2} for SUBSURF."""
    return send_command("add_modifier", {
        "name": name, "modifier_type": modifier_type,
        "properties": properties, "modifier_name": modifier_name,
    })


@mcp.tool()
def apply_modifier(name: str, modifier_name: str) -> dict:
    """Apply a modifier to permanently bake its effect into the mesh geometry."""
    return send_command("apply_modifier", {"name": name, "modifier_name": modifier_name})


@mcp.tool()
def remove_modifier(name: str, modifier_name: str) -> dict:
    """Remove a modifier from an object without applying it."""
    return send_command("remove_modifier", {"name": name, "modifier_name": modifier_name})


@mcp.tool()
def create_array(
    name: str, count: int = 5, offset: list[float] | None = None,
    use_relative: bool = True,
) -> dict:
    """Create a linear array of an object. Count = number of copies.
    Offset is [x, y, z]. If use_relative=True, offset is relative to object size.
    Example: offset=[1,0,0] with relative = one object-width apart on X."""
    return send_command("create_array", {
        "name": name, "count": count, "offset": offset, "use_relative": use_relative,
    })


@mcp.tool()
def create_circular_array(
    name: str, count: int = 8, axis: str = "Z", radius: float | None = None,
) -> dict:
    """Create a circular array using an empty as rotation pivot.
    Count = number of copies around the circle. Axis: X, Y, or Z.
    Radius offsets the object from the pivot center."""
    return send_command("create_circular_array", {
        "name": name, "count": count, "axis": axis, "radius": radius,
    })


# =============================================================================
#  MATERIALS
# =============================================================================

@mcp.tool()
def set_material(
    name: str,
    material_name: str | None = None,
    base_color: list[float] | None = None,
    metallic: float | None = None,
    roughness: float | None = None,
    emission_color: list[float] | None = None,
    emission_strength: float | None = None,
    alpha: float | None = None,
    ior: float | None = None,
    transmission: float | None = None,
    specular: float | None = None,
    clearcoat: float | None = None,
    sheen: float | None = None,
    subsurface: float | None = None,
) -> dict:
    """Set PBR material properties on an object using Principled BSDF.
    base_color: [R,G,B] or [R,G,B,A] (0-1 range). metallic: 0=dielectric, 1=metal.
    roughness: 0=mirror, 1=diffuse. transmission: 0=opaque, 1=glass.
    emission_color + emission_strength for glowing materials."""
    return send_command("set_material", {
        "name": name, "material_name": material_name, "base_color": base_color,
        "metallic": metallic, "roughness": roughness,
        "emission_color": emission_color, "emission_strength": emission_strength,
        "alpha": alpha, "ior": ior, "transmission": transmission,
        "specular": specular, "clearcoat": clearcoat,
        "sheen": sheen, "subsurface": subsurface,
    })


@mcp.tool()
def create_glass(
    name: str, color: list[float] | None = None,
    ior: float = 1.45, roughness: float = 0.0,
) -> dict:
    """Apply a glass/transparent material to an object.
    IOR: 1.0=air, 1.33=water, 1.45=glass, 1.52=window glass, 2.42=diamond."""
    return send_command("create_glass", {
        "name": name, "color": color, "ior": ior, "roughness": roughness,
    })


@mcp.tool()
def create_metal(
    name: str, color: list[float] | None = None, roughness: float = 0.3,
) -> dict:
    """Apply a metallic material to an object. Default is silver-ish.
    Color examples: gold=[1.0,0.76,0.33], copper=[0.72,0.45,0.2], steel=[0.8,0.8,0.8]."""
    return send_command("create_metal", {
        "name": name, "color": color, "roughness": roughness,
    })


@mcp.tool()
def create_emission(
    name: str, color: list[float] | None = None, strength: float = 10.0,
) -> dict:
    """Apply an emissive (glowing) material to an object.
    Color is [R,G,B,A]. Strength controls brightness (10+ for visible glow in Cycles)."""
    return send_command("create_emission", {
        "name": name, "color": color, "strength": strength,
    })


@mcp.tool()
def list_materials() -> dict:
    """List all materials in the scene with their base color and user count."""
    return send_command("list_materials")


@mcp.tool()
def batch_assign_material(
    names: list[str], color: list[float] | None = None,
    material_name: str | None = None,
) -> dict:
    """Assign the same material to multiple objects at once.
    Provide either a color [R,G,B] to create a new material, or material_name to use existing."""
    return send_command("batch_assign_material", {
        "names": names, "color": color, "material_name": material_name,
    })


# =============================================================================
#  WORLD / ENVIRONMENT
# =============================================================================

@mcp.tool()
def set_world_color(
    color: list[float] | None = None, strength: float = 1.0,
) -> dict:
    """Set the world background to a solid color. Color is [R,G,B] (0-1 range).
    Strength controls brightness. Good for studio-style renders."""
    return send_command("set_world_color", {"color": color, "strength": strength})


@mcp.tool()
def set_world_hdri(filepath: str) -> dict:
    """Set an HDRI image as the world environment for realistic lighting.
    Provide the full file path to an .hdr or .exr file."""
    return send_command("set_world_hdri", {"filepath": filepath})


@mcp.tool()
def set_sky_texture(
    sun_elevation: float = 15.0, sun_rotation: float = 0.0,
    sun_intensity: float = 1.0, turbidity: float = 2.2,
) -> dict:
    """Set a procedural Nishita sky texture for realistic outdoor lighting.
    sun_elevation: degrees above horizon. sun_rotation: compass direction.
    turbidity: atmospheric haze (2=clear, 10=hazy)."""
    return send_command("set_sky_texture", {
        "sun_elevation": sun_elevation, "sun_rotation": sun_rotation,
        "sun_intensity": sun_intensity, "turbidity": turbidity,
    })


@mcp.tool()
def set_fog(density: float = 0.01, color: list[float] | None = None) -> dict:
    """Add volumetric fog to the world. Density controls thickness.
    Color is [R,G,B] for emission tint. Requires Cycles or EEVEE for volume rendering."""
    return send_command("set_fog", {"density": density, "color": color})


# =============================================================================
#  CAMERA & LIGHTING
# =============================================================================

@mcp.tool()
def set_camera(
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    focal_length: float | None = None,
    target: str | None = None,
    depth_of_field: dict | None = None,
) -> dict:
    """Configure the scene camera. Location is [x,y,z]. Rotation in degrees [x,y,z].
    focal_length in mm (35=normal, 85=portrait, 200=telephoto).
    target: object name to point at. depth_of_field: {"enabled": true, "aperture": 2.8,
    "focus_object": "name", "focus_distance": 5.0}."""
    return send_command("set_camera", {
        "location": location, "rotation": rotation, "focal_length": focal_length,
        "target": target, "depth_of_field": depth_of_field,
    })


@mcp.tool()
def setup_studio_lighting(style: str = "THREE_POINT") -> dict:
    """Set up professional studio lighting. Removes existing lights and creates a new setup.
    Styles: THREE_POINT (key/fill/rim), REMBRANDT (dramatic), SOFT_BOX (even, soft),
    or default SUN lighting for outdoor scenes."""
    return send_command("setup_studio_lighting", {"style": style})


@mcp.tool()
def add_light(
    type: str = "POINT", name: str | None = None,
    location: list[float] | None = None, energy: float = 100,
    color: list[float] | None = None, size: float | None = None,
    rotation: list[float] | None = None,
) -> dict:
    """Add a light to the scene. Types: POINT, SUN, SPOT, AREA.
    Energy in watts. Color is [R,G,B]. Size controls shadow softness (AREA/POINT).
    Rotation in degrees (for SPOT/AREA directional lights)."""
    return send_command("add_light", {
        "type": type, "name": name, "location": location, "energy": energy,
        "color": color, "size": size, "rotation": rotation,
    })


# =============================================================================
#  RENDER & EXPORT
# =============================================================================

@mcp.tool()
def render_image(
    filepath: str, resolution_x: int = 1920, resolution_y: int = 1080,
    samples: int = 128, engine: str | None = None,
) -> dict:
    """Render the scene to an image file. Format is auto-detected from extension
    (.png, .jpg, .exr, .hdr, .bmp, .tiff). Engine: CYCLES, BLENDER_EEVEE_NEXT.
    Samples controls quality (more = better but slower)."""
    return send_command("render_image", {
        "filepath": filepath, "resolution_x": resolution_x,
        "resolution_y": resolution_y, "samples": samples, "engine": engine,
    })


@mcp.tool()
def configure_render(
    engine: str | None = None, samples: int | None = None,
    resolution: list[int] | None = None, denoise: bool = True,
    transparent_bg: bool = False, use_gpu: bool = True,
    color_management: dict | None = None,
) -> dict:
    """Configure render settings without rendering. Engine: CYCLES, BLENDER_EEVEE_NEXT.
    Resolution is [width, height]. denoise=True enables AI denoising in Cycles.
    transparent_bg=True for transparent background. color_management can set
    view_transform, look, exposure, gamma."""
    return send_command("configure_render", {
        "engine": engine, "samples": samples, "resolution": resolution,
        "denoise": denoise, "transparent_bg": transparent_bg,
        "use_gpu": use_gpu, "color_management": color_management,
    })


@mcp.tool()
def export_scene(
    filepath: str, format: str = "glTF", selected_only: bool = False,
) -> dict:
    """Export the scene or selected objects to a file.
    Formats: glTF/GLB (web/game), OBJ, FBX (game engines), STL (3D printing),
    USD/USDC/USDA (VFX), PLY (point clouds). Creates directories as needed."""
    return send_command("export_scene", {
        "filepath": filepath, "format": format, "selected_only": selected_only,
    })


# =============================================================================
#  COLLECTIONS
# =============================================================================

@mcp.tool()
def create_collection(name: str, parent: str | None = None) -> dict:
    """Create a new collection (like a folder for organizing objects).
    Optionally nest it under a parent collection."""
    return send_command("create_collection", {"name": name, "parent": parent})


@mcp.tool()
def move_to_collection(object_name: str, collection_name: str) -> dict:
    """Move an object to a different collection. Removes from current collection(s)."""
    return send_command("move_to_collection", {
        "object_name": object_name, "collection_name": collection_name,
    })


@mcp.tool()
def list_collections() -> dict:
    """List all collections in the scene as a tree with their objects."""
    return send_command("list_collections")


@mcp.tool()
def set_collection_visibility(
    name: str, visible: bool = True, render_visible: bool = True,
) -> dict:
    """Set viewport and render visibility of a collection and all its objects."""
    return send_command("set_collection_visibility", {
        "name": name, "visible": visible, "render_visible": render_visible,
    })


# =============================================================================
#  CONSTRAINTS
# =============================================================================

@mcp.tool()
def add_constraint(
    name: str, constraint_type: str,
    target_name: str | None = None, properties: dict | None = None,
) -> dict:
    """Add a constraint to an object. Common types: TRACK_TO (aim at target),
    COPY_LOCATION, COPY_ROTATION, COPY_SCALE, LIMIT_LOCATION, LIMIT_ROTATION,
    FOLLOW_PATH, CLAMP_TO, DAMPED_TRACK, LOCKED_TRACK.
    Properties dict sets constraint attributes."""
    return send_command("add_constraint", {
        "name": name, "constraint_type": constraint_type,
        "target_name": target_name, "properties": properties,
    })


@mcp.tool()
def remove_constraint(name: str, constraint_name: str) -> dict:
    """Remove a constraint from an object by constraint name."""
    return send_command("remove_constraint", {
        "name": name, "constraint_name": constraint_name,
    })


# =============================================================================
#  BATCH OPERATIONS
# =============================================================================

@mcp.tool()
def batch_transform(
    names: list[str], translate: list[float] | None = None,
    rotate: list[float] | None = None, scale: list[float] | None = None,
    relative: bool = True,
) -> dict:
    """Apply the same transform to multiple objects at once.
    Translate is [x,y,z], rotate is [x,y,z] in degrees, scale is [x,y,z].
    If relative=True, transforms are additive/multiplicative."""
    return send_command("batch_transform", {
        "names": names, "translate": translate, "rotate": rotate,
        "scale": scale, "relative": relative,
    })


@mcp.tool()
def batch_delete(names: list[str]) -> dict:
    """Delete multiple objects at once by their names."""
    return send_command("batch_delete", {"names": names})


@mcp.tool()
def align_objects(
    names: list[str], axis: str = "Z", align_to: str = "CENTER",
) -> dict:
    """Align multiple objects along an axis. Axis: X, Y, or Z.
    Align_to: CENTER (average), MIN (lowest), MAX (highest), CURSOR (3D cursor)."""
    return send_command("align_objects", {
        "names": names, "axis": axis, "align_to": align_to,
    })


@mcp.tool()
def distribute_objects(
    names: list[str], axis: str = "X", spacing: float | None = None,
) -> dict:
    """Evenly distribute objects along an axis. If spacing is given, uses fixed spacing.
    If spacing is None, distributes evenly between first and last object."""
    return send_command("distribute_objects", {
        "names": names, "axis": axis, "spacing": spacing,
    })


@mcp.tool()
def center_objects(names: list[str] | None = None) -> dict:
    """Move objects so their collective center is at the world origin.
    If no names given, centers all objects in the scene."""
    return send_command("center_objects", {"names": names} if names else {})


# =============================================================================
#  ANIMATION
# =============================================================================

@mcp.tool()
def set_keyframe(
    name: str, frame: int, data_path: str,
    value: list[float] | float | None = None,
) -> dict:
    """Insert a keyframe on an object property at a specific frame.
    data_path examples: "location", "rotation_euler", "scale", "hide_viewport".
    Value sets the property value at that frame (list for vectors, float for scalars)."""
    return send_command("set_keyframe", {
        "name": name, "frame": frame, "data_path": data_path, "value": value,
    })


@mcp.tool()
def set_animation_range(start: int, end: int, fps: int | None = None) -> dict:
    """Set the animation frame range and optionally the FPS.
    Standard FPS values: 24 (film), 25 (PAL), 30 (NTSC), 60 (smooth)."""
    return send_command("set_animation_range", {
        "start": start, "end": end, "fps": fps,
    })


@mcp.tool()
def set_frame(frame: int) -> dict:
    """Set the current frame in the timeline."""
    return send_command("set_frame", {"frame": frame})


@mcp.tool()
def clear_animation(name: str) -> dict:
    """Remove all animation data from an object."""
    return send_command("clear_animation", {"name": name})


# =============================================================================
#  PHYSICS
# =============================================================================

@mcp.tool()
def add_rigid_body(
    name: str, type: str = "ACTIVE", mass: float = 1.0,
    friction: float = 0.5, restitution: float = 0.5,
    collision_shape: str = "CONVEX_HULL",
) -> dict:
    """Add rigid body physics to an object. Types: ACTIVE (affected by gravity),
    PASSIVE (static collider). collision_shape: BOX, SPHERE, CAPSULE, CYLINDER,
    CONE, CONVEX_HULL (default, fits shape), MESH (exact, slow)."""
    return send_command("add_rigid_body", {
        "name": name, "type": type, "mass": mass,
        "friction": friction, "restitution": restitution,
        "collision_shape": collision_shape,
    })


@mcp.tool()
def add_cloth(name: str, quality: int = 5, mass: float = 0.3) -> dict:
    """Add cloth simulation to a mesh object.
    Quality controls simulation accuracy (1-10). Mass in kg."""
    return send_command("add_cloth", {"name": name, "quality": quality, "mass": mass})


@mcp.tool()
def add_particles(
    name: str, count: int = 1000, lifetime: int = 50,
    type: str = "EMITTER", velocity: float = 1.0, size: float = 0.05,
) -> dict:
    """Add a particle system to an object. Types: EMITTER (emit over time), HAIR (static strands).
    Count = number of particles. Lifetime in frames. Velocity = emission speed."""
    return send_command("add_particles", {
        "name": name, "count": count, "lifetime": lifetime,
        "type": type, "velocity": velocity, "size": size,
    })


@mcp.tool()
def bake_physics(start: int = 1, end: int = 250) -> dict:
    """Bake all physics simulations in the scene to cache.
    Must be baked before rendering physics simulations."""
    return send_command("bake_physics", {"start": start, "end": end})


# =============================================================================
#  UV MAPPING
# =============================================================================

@mcp.tool()
def smart_uv_project(
    name: str, angle_limit: float = 66.0, island_margin: float = 0.0,
) -> dict:
    """Automatically UV unwrap a mesh using Smart UV Project.
    angle_limit in degrees controls island splitting (66 is good default).
    island_margin adds padding between UV islands."""
    return send_command("smart_uv_project", {
        "name": name, "angle_limit": angle_limit, "island_margin": island_margin,
    })


@mcp.tool()
def uv_unwrap(
    name: str, method: str = "ANGLE_BASED", margin: float = 0.001,
) -> dict:
    """UV unwrap a mesh using seam-based unwrapping.
    Methods: ANGLE_BASED (good default), CONFORMAL (preserves angles better).
    Margin adds padding between UV islands."""
    return send_command("uv_unwrap", {
        "name": name, "method": method, "margin": margin,
    })


# =============================================================================
#  CODE EXECUTION
# =============================================================================

@mcp.tool()
def execute_code(code: str) -> dict:
    """Execute arbitrary Python code inside Blender. Has access to bpy, mathutils, math, os.
    Blocked imports: subprocess, shutil, socket, ctypes, multiprocessing, webbrowser.
    Store results in a variable named 'result' to return them.
    Use this for advanced operations not covered by other tools."""
    return send_command("execute_code", {"code": code})


# =============================================================================
#  OPTIMIZATION
# =============================================================================

@mcp.tool()
def optimize_scene(merge_threshold: float = 0.0001) -> dict:
    """Optimize the entire scene: remove orphan meshes/materials/images,
    and merge duplicate vertices on all meshes. Returns a log of all optimizations performed."""
    return send_command("optimize_scene", {"merge_threshold": merge_threshold})


# =============================================================================
#  Entry point
# =============================================================================

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
