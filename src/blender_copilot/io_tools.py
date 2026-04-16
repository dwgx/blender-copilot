"""
File I/O tools — import/export for FBX, OBJ, glTF, USD, STL, etc.

Provides multi-format import/export with common presets,
especially VRChat-optimized FBX export settings.
"""


def register_io_tools(mcp, send_command_fn):
    """Register file import/export MCP tools."""

    def _exec(code: str) -> dict:
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def io_import_file(
        filepath: str,
        file_format: str = "",
    ) -> dict:
        """Import a 3D file into the current scene.

        Auto-detects format from extension. Supports: FBX, OBJ, glTF/GLB, STL,
        USD/USDC/USDA, PLY, ABC (Alembic), DAE (Collada), SVG.

        Args:
            filepath: Path to the file to import
            file_format: Override format detection (fbx, obj, gltf, stl, usd, ply, abc, dae, svg)
        """
        ext = file_format.lower() if file_format else filepath.rsplit(".", 1)[-1].lower()
        import_map = {
            "fbx": "bpy.ops.import_scene.fbx(filepath=r'{fp}')",
            "obj": "bpy.ops.wm.obj_import(filepath=r'{fp}')",
            "gltf": "bpy.ops.import_scene.gltf(filepath=r'{fp}')",
            "glb": "bpy.ops.import_scene.gltf(filepath=r'{fp}')",
            "stl": "bpy.ops.wm.stl_import(filepath=r'{fp}')",
            "usd": "bpy.ops.wm.usd_import(filepath=r'{fp}')",
            "usdc": "bpy.ops.wm.usd_import(filepath=r'{fp}')",
            "usda": "bpy.ops.wm.usd_import(filepath=r'{fp}')",
            "ply": "bpy.ops.wm.ply_import(filepath=r'{fp}')",
            "abc": "bpy.ops.wm.alembic_import(filepath=r'{fp}')",
            "dae": "bpy.ops.wm.collada_import(filepath=r'{fp}')",
            "svg": "bpy.ops.import_curve.svg(filepath=r'{fp}')",
        }

        if ext not in import_map:
            return {"error": f"Unsupported format '{ext}'. Supported: {list(import_map.keys())}"}

        op = import_map[ext].replace("{fp}", filepath)
        code = f"""import bpy
before = set(bpy.data.objects.keys())
{op}
after = set(bpy.data.objects.keys())
new_objects = after - before
result = f'Imported {{len(new_objects)}} objects from {ext.upper()}: {{list(new_objects)[:10]}}'
"""
        return _exec(code)

    @mcp.tool()
    def io_export_fbx(
        filepath: str,
        selected_only: bool = False,
        apply_modifiers: bool = True,
        add_leaf_bones: bool = False,
        mesh_smooth_type: str = "FACE",
        apply_scale: str = "FBX_SCALE_ALL",
        axis_forward: str = "-Z",
        axis_up: str = "Y",
    ) -> dict:
        """Export to FBX format (standard for Unity/VRChat/game engines).

        Default settings are optimized for VRChat/Unity workflow.
        IMPORTANT: add_leaf_bones=False is critical for VRChat.

        Args:
            filepath: Output .fbx path
            selected_only: Export only selected objects
            apply_modifiers: Apply modifiers before export
            add_leaf_bones: Add leaf bones (FALSE for VRChat!)
            mesh_smooth_type: FACE, EDGE, OFF
            apply_scale: FBX_SCALE_ALL, FBX_SCALE_UNITS, FBX_SCALE_CUSTOM, FBX_SCALE_NONE
            axis_forward: Forward axis (-Z for Unity)
            axis_up: Up axis (Y for Unity)
        """
        code = f"""import bpy
bpy.ops.export_scene.fbx(
    filepath=r'{filepath}',
    use_selection={selected_only},
    use_mesh_modifiers={apply_modifiers},
    add_leaf_bones={add_leaf_bones},
    mesh_smooth_type='{mesh_smooth_type}',
    apply_scale_options='{apply_scale}',
    axis_forward='{axis_forward}',
    axis_up='{axis_up}',
    path_mode='AUTO',
    embed_textures=False,
)
result = f'Exported FBX: {filepath}'
"""
        return _exec(code)

    @mcp.tool()
    def io_export_gltf(
        filepath: str,
        export_format: str = "GLB",
        selected_only: bool = False,
        apply_modifiers: bool = True,
        export_materials: str = "EXPORT",
        export_textures: bool = True,
        export_animations: bool = True,
    ) -> dict:
        """Export to glTF/GLB format (standard for web and universal 3D).

        Args:
            filepath: Output path (.glb or .gltf)
            export_format: GLB (binary, single file) or GLTF_SEPARATE (separate files)
            selected_only: Export only selected objects
            apply_modifiers: Apply modifiers
            export_materials: EXPORT, PLACEHOLDER, NONE
            export_textures: Include texture images
            export_animations: Include animations
        """
        code = f"""import bpy
bpy.ops.export_scene.gltf(
    filepath=r'{filepath}',
    export_format='{export_format}',
    use_selection={selected_only},
    export_apply={apply_modifiers},
    export_materials='{export_materials}',
    export_image_format='AUTO',
    export_animations={export_animations},
)
result = f'Exported {export_format}: {filepath}'
"""
        return _exec(code)

    @mcp.tool()
    def io_export_obj(
        filepath: str,
        selected_only: bool = False,
        apply_modifiers: bool = True,
        export_materials: bool = True,
        export_uv: bool = True,
        export_normals: bool = True,
    ) -> dict:
        """Export to OBJ format (universal mesh exchange).

        Args:
            filepath: Output .obj path
            selected_only: Export only selected
            apply_modifiers: Apply modifiers
            export_materials: Write .mtl file
            export_uv: Export UV coordinates
            export_normals: Export vertex normals
        """
        code = f"""import bpy
bpy.ops.wm.obj_export(
    filepath=r'{filepath}',
    export_selected_objects={selected_only},
    apply_modifiers={apply_modifiers},
    export_materials={export_materials},
    export_uv={export_uv},
    export_normals={export_normals},
)
result = f'Exported OBJ: {filepath}'
"""
        return _exec(code)

    @mcp.tool()
    def io_export_stl(
        filepath: str,
        selected_only: bool = False,
        apply_modifiers: bool = True,
        ascii_format: bool = False,
    ) -> dict:
        """Export to STL format (3D printing).

        Args:
            filepath: Output .stl path
            selected_only: Export only selected
            apply_modifiers: Apply modifiers
            ascii_format: ASCII STL (True) or binary (False, smaller file)
        """
        code = f"""import bpy
bpy.ops.wm.stl_export(
    filepath=r'{filepath}',
    export_selected_objects={selected_only},
    apply_modifiers={apply_modifiers},
    ascii_format={ascii_format},
)
result = f'Exported STL: {filepath}'
"""
        return _exec(code)

    @mcp.tool()
    def io_export_usd(
        filepath: str,
        selected_only: bool = False,
        export_materials: bool = True,
        export_animation: bool = True,
    ) -> dict:
        """Export to USD/USDC format (Pixar Universal Scene Description).

        Args:
            filepath: Output .usd/.usdc path
            selected_only: Export only selected
            export_materials: Include materials
            export_animation: Include animation
        """
        code = f"""import bpy
bpy.ops.wm.usd_export(
    filepath=r'{filepath}',
    selected_objects_only={selected_only},
    export_materials={export_materials},
    export_animation={export_animation},
)
result = f'Exported USD: {filepath}'
"""
        return _exec(code)
