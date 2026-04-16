# Blender Copilot

**The most comprehensive Blender MCP server — AI-powered 3D creation with 308 tools across 25 modules. Full zero-to-published VRChat avatar pipeline.**

最全面的 Blender MCP 伺服器 — AI 驅動的 3D 創作，308 種工具橫跨 25 模組。完整的從零到上傳 VRChat Avatar 流水線。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.0+](https://img.shields.io/badge/blender-4.0+-orange.svg)](https://www.blender.org/)

---

## Features / 功能特色

### Core Tools (82 tools in `server.py`)

| Category | Tools | Description |
|----------|-------|-------------|
| Scene Inspection | 4 | Get scene info, object details, analysis, viewport screenshots |
| Object Creation | 4 | Primitives, curves, 3D text, armatures |
| Transforms | 6 | Translate, rotate, scale, apply, snap to ground, set origin |
| Object Management | 9 | Duplicate, delete, select, parent, visibility, hierarchy, rename |
| Mesh Editing | 14 | Boolean, join, separate, subdivide, extrude, bevel, inset, decimate, remesh, normals, fill holes |
| Modifiers | 5 | Add/apply/remove modifiers, linear array, circular array |
| Materials | 9 | PBR materials, glass, metal, emission, texture, Principled BSDF, list, batch assign |
| World/Environment | 4 | Background color, HDRI, procedural sky, volumetric fog |
| Camera & Lighting | 3 | Camera setup, studio lighting presets, custom lights |
| Render & Export | 3 | Render to image, configure settings, export (glTF/OBJ/FBX/STL/USD/PLY) |
| Collections | 4 | Create, move objects, list, visibility |
| Constraints | 2 | Add/remove constraints (Track To, Copy Location, etc.) |
| Batch Operations | 5 | Batch transform, delete, align, distribute, center |
| Animation | 4 | Keyframes, animation range, set frame, clear animation |
| Physics | 4 | Rigid body, cloth, particles, bake physics |
| UV Mapping | 2 | Smart UV project, UV unwrap |
| Code Execution | 1 | Sandboxed Python execution inside Blender |
| Optimization | 1 | Clean orphan data, merge duplicate vertices |

### Asset Integration (20 tools in `server.py`)

| Source | Tools | Description |
|--------|-------|-------------|
| PolyHaven | 4 | Search/download free HDRIs, textures, and 3D models from polyhaven.com |
| Sketchfab | 4 | Search/preview/download models from Sketchfab (API key required) |
| Hyper3D (Rodin) | 4 | AI text/image-to-3D generation via Rodin API |
| Hunyuan3D | 4 | Tencent's text/image-to-3D generation |
| Wrappers | 4 | Convenience tools for text-to-3D and image-to-3D workflows |

### VRC Avatar Pipeline (23 tools in `vrc_tools.py`)

| Category | Tools | Description |
|----------|-------|-------------|
| Validation | 2 | Performance rank check (PC/Quest), export readiness |
| Rigging | 5 | Humanoid armature, bone renaming, auto-weight, weight check |
| Visemes & Eyes | 2 | 15 VRC visemes from base shapes, eye tracking setup |
| PhysBones | 3 | Chain setup, physics config (hair/tail/ears/skirt), dynamics budget |
| Accessories | 2 | Auto-align imported accessories, attach to bones |
| Optimization | 3 | Smart decimate (preserves shape keys), material merge, texture atlas bake |
| Avatar Features | 4 | Expression menu, contacts (headpat/boop), gestures, animator generation |
| Import/Export | 2 | VRC-correct FBX import and export |

### Advanced Mesh Tools (10 tools in `blender_master_tools.py`)

| Tool | Description |
|------|-------------|
| bmesh_operation | Low-level BMesh operations (dissolve, collapse, merge, knife) |
| topology_edge_loops | Edge loop analysis and insertion |
| procedural_generate | Parametric mesh generation |
| precision_weight_paint | Vertex-level weight painting with smoothstep interpolation |
| build_material_nodes | Programmatic Shader Editor node trees |
| smart_uv_tools | Advanced UV tools (LSCM, angle-based, pack islands) |
| rig_tools | IK/FK chains, stretch-to, custom shapes |
| retopology | Quad-based retopology from high-poly |
| boolean_cleanup | Post-boolean topology repair |
| create_facial_topology | Face topology from landmarks |

### Sculpt & Texture Bake (14 tools in `sculpt_bake_tools.py`)

| Category | Tools | Description |
|----------|-------|-------------|
| Sculpt Mode | 6 | Enter sculpt, brush strokes, masking, remesh, detail flood, face set extract |
| Shape Keys | 2 | Sculpt to shape key, cloth sim to shape key |
| Texture Bake | 4 | Normal map, AO, diffuse atlas, general bake (Cycles) |
| Paint & Sim | 2 | Texture paint fill, cloth simulation for modeling |

### Face Tracking — ARKit 52 + Unified (10 tools in `face_tracking_tools.py`)

| Tool | Description |
|------|-------------|
| ft_setup_face_vertex_groups | Auto-detect facial landmarks → 28 vertex groups |
| ft_create_arkit_shapes | Create all 52 ARKit blend shapes (procedural/template/from_existing) |
| ft_create_unified_expressions | Generate 70+ VRCFT Unified Expressions |
| ft_sculpt_shape_key | AI-guided shape key sculpting via vertex displacement |
| ft_validate_shapes | Validate against ARKit/Unified standard |
| ft_mirror_shape_key | Mirror Left↔Right shape keys |
| ft_combine_shape_keys | Combine multiple shapes with weights |
| ft_setup_tongue_tracking | Tongue bone chain + blend shapes |
| ft_setup_eye_tracking_full | Extended eye tracking (12 shapes) |
| ft_export_shape_key_report | Shape key report (JSON/markdown) |

### Rigify Integration (6 tools in `rigify_tools.py`)

| Tool | Description |
|------|-------------|
| rigify_create_metarig | Generate Rigify meta-rig (human/quadruped/bird/etc.) |
| rigify_fit_metarig | Auto-fit meta-rig to mesh proportions (proportional/snap) |
| rigify_generate_rig | Generate production rig from meta-rig |
| rigify_to_vrc | Convert DEF-bones to VRC/Unity Humanoid naming |
| rigify_add_face_rig | Add face rig bones (full/basic/eyes_only) |
| rigify_configure_ik | Configure IK for VRC full-body tracking (3/6/10-point) |

### Unity Automation (15 tools in `unity_tools.py`)

| Category | Tools | Description |
|----------|-------|-------------|
| Project Setup | 1 | Verify Unity project, VRC SDK presence |
| Import | 1 | Import FBX with humanoid rig, extract materials/textures |
| Avatar Config | 2 | Avatar Descriptor setup, pipeline manager |
| Expressions | 2 | Expression Menu and Parameters .asset generation |
| Animation | 3 | Animator controller, animation clips, gesture layer |
| Shaders | 2 | Configure Poiyomi/lilToon/UTS2, material preset generation |
| Dynamics | 2 | PhysBone components, ContactSender/Receiver |
| Build & Publish | 2 | Build validation, publish to VRChat (CLI + GUI fallback) |

### Script Execution (4 tools in `script_tools.py`)

| Tool | Description |
|------|-------------|
| execute_script_headless | Run Python in headless Blender subprocess (bypasses TCP timeout) |
| execute_script_on_file | Execute code on an existing .blend file |
| build_scene_from_json | JSON scene description → bpy script → headless execute |
| generate_scene_script | Generate bpy script from JSON without executing |

### Render Presets (8 tools in `render_tools.py`)

| Tool | Description |
|------|-------------|
| render_list_presets | List 7 presets (cycles/eevee preview/default/high, workbench) |
| render_apply_preset | One-click render preset application |
| render_set_output | Configure output path, format, quality |
| render_still | Render single frame |
| render_animation | Render animation (image sequence or FFMPEG video) |
| render_set_camera | Set/create active render camera |
| render_get_settings | Get current render config |
| render_set_world | Set world background (solid color or HDRI) |

### Scene Profiles (9 tools in `scene_tools.py`)

| Tool | Description |
|------|-------------|
| scene_list_profiles | List 10 profiles (preview to 4K, Instagram, YouTube, VRC) |
| scene_apply_profile | Apply resolution/engine/samples profile |
| scene_setup_turntable | 360° camera turntable animation |
| scene_create_collection | Create collections with color tags |
| scene_move_to_collection | Move objects between collections |
| scene_cleanup | Remove unused materials/meshes/images |
| scene_stats | Comprehensive scene statistics |
| scene_set_units | Configure unit system (metric/imperial) |
| scene_set_visibility | Control object viewport/render visibility |

### Modifier Registry (9 tools in `modifier_tools.py`)

| Tool | Description |
|------|-------------|
| modifier_list_types | List 15 modifier types with validated parameters |
| modifier_add | Add modifier with type-safe parameter validation |
| modifier_apply | Apply (finalize) a modifier |
| modifier_remove | Remove modifier without applying |
| modifier_list | List all modifiers on an object |
| modifier_reorder | Move modifier in stack |
| modifier_apply_all | Apply all modifiers at once |
| modifier_batch_add | Add same modifier to multiple objects |
| modifier_preset_smooth_shade | One-click SubD + Smooth + WeightedNormal |

### Animation (9 tools in `animation_tools.py`)

| Tool | Description |
|------|-------------|
| anim_insert_keyframe | Insert keyframe on any property |
| anim_insert_keyframes_batch | Insert multiple keyframes at once |
| anim_delete_keyframe | Delete keyframe |
| anim_clear_all | Clear all animation from object |
| anim_set_interpolation | Set interpolation type (Bezier, Linear, etc.) |
| anim_set_frame_range | Set frame range and FPS |
| anim_bounce | Bouncing animation preset |
| anim_orbit | Orbital/circular motion preset |
| anim_get_info | Get animation data summary |

### Materials (7 tools in `material_tools.py`)

| Tool | Description |
|------|-------------|
| material_list_presets | List 12 presets (metals, glass, skin, fabric, etc.) |
| material_create_preset | Create material from preset |
| material_create_pbr | Full PBR material with all parameters |
| material_assign | Assign material to object |
| material_list | List materials on object or in scene |
| material_duplicate | Duplicate existing material |
| material_set_texture | Add image texture (albedo, normal, roughness, etc.) |

### UV Mapping (8 tools in `uv_tools.py`)

| Tool | Description |
|------|-------------|
| uv_smart_unwrap | Smart UV Project (auto, angle-based) |
| uv_unwrap | Standard unwrap (follows seams) |
| uv_project_from_view | Cube/cylinder/sphere projection |
| uv_mark_seams | Mark UV seams (manual or auto by angle) |
| uv_pack_islands | Pack UV islands efficiently |
| uv_get_info | Get UV layer info |
| uv_add_layer | Add new UV layer |
| uv_remove_layer | Remove UV layer |

### Curves (7 tools in `curve_tools.py`)

| Tool | Description |
|------|-------------|
| curve_create_bezier | Create Bezier curve with custom points |
| curve_create_nurbs | Create NURBS curve |
| curve_create_path | Create NURBS path (for follow-path) |
| curve_create_circle | Create circle curve (bevel profile) |
| curve_create_text | Create 3D text object |
| curve_to_mesh | Convert curve to mesh |
| curve_set_bevel | Set curve bevel (tube/pipe effect) |

### Physics (7 tools in `physics_tools.py`)

| Tool | Description |
|------|-------------|
| physics_add_rigid_body | Rigid body physics (active/passive) |
| physics_add_cloth | Cloth simulation |
| physics_add_collision | Collision surface for cloth/particles |
| physics_add_particle_system | Particle emitter |
| physics_add_soft_body | Soft body physics |
| physics_bake | Bake all physics simulations |
| physics_remove | Remove physics from object |

### Armature & Bones (7 tools in `armature_tools.py`)

| Tool | Description |
|------|-------------|
| armature_create | Create new armature |
| armature_add_bone | Add individual bone |
| armature_add_bones_chain | Add connected bone chain (spine, arm, finger) |
| armature_add_constraint | Add pose bone constraint (IK, Copy Rot, etc.) |
| armature_auto_weight | Parent mesh to armature with automatic weights |
| armature_list_bones | List all bones with hierarchy |
| armature_set_pose | Set bone rotations/positions |

### File I/O (6 tools in `io_tools.py`)

| Tool | Description |
|------|-------------|
| io_import_file | Import any 3D file (auto-detect: FBX, OBJ, glTF, STL, USD, PLY, ABC) |
| io_export_fbx | Export FBX (VRChat-optimized defaults) |
| io_export_gltf | Export glTF/GLB (web-ready) |
| io_export_obj | Export OBJ (universal mesh) |
| io_export_stl | Export STL (3D printing) |
| io_export_usd | Export USD (Pixar format) |

### Lighting (5 tools in `lighting_tools.py`)

| Tool | Description |
|------|-------------|
| light_add | Add any light type (point, sun, spot, area) |
| light_setup_three_point | Classic 3-point lighting rig |
| light_setup_studio | Professional studio softbox setup |
| light_list | List all lights with properties |
| light_modify | Modify existing light properties |

### Measurement & Verification (6 tools in `measurement_tools.py`)

| Tool | Description |
|------|-------------|
| measure_distance | Distance between objects |
| measure_dimensions | Object bounding box and mesh stats |
| measure_overlap | Bounding box overlap detection |
| measure_symmetry | Mesh symmetry analysis |
| mesh_quality_check | Non-manifold, loose verts, degenerate faces, dupes |
| measure_alignment | Check multi-object axis alignment |

### Pipeline Orchestration (5 tools in `pipeline_tools.py`)

| Tool | Description |
|------|-------------|
| pipeline_avatar_from_mesh | Full Blender-side: mesh → armature → shape keys → FBX |
| pipeline_blender_to_unity | Full Unity-side: FBX → import → descriptor → build |
| pipeline_face_tracking_setup | Complete: vertex groups → ARKit 52 → Unified → validate |
| pipeline_validate_full | Comprehensive go/no-go report for VRC upload |
| pipeline_generate_blueprint | Export all config JSONs alongside FBX |

### Blender Addon (112 commands, 2915 lines)

The addon (`addon/__init__.py`) runs inside Blender and handles all commands via TCP.
Includes full UI panels for:

- **PolyHaven Browser** — search and import HDRIs, textures, models
- **Sketchfab Browser** — search, preview, download models
- **Hyper3D (Rodin)** — text/image to 3D generation with progress tracking
- **Hunyuan3D** — Tencent's 3D generation pipeline
- **Copilot Panel** — connection management, port config

## Architecture / 架構

```
┌─────────────────┐    stdio/MCP     ┌──────────────────┐    TCP:9876    ┌──────────────┐
│  AI (Claude,    │ ◄──────────────► │  MCP Server      │ ◄────────────► │  Blender     │
│  Cursor, etc.)  │                  │  (server.py)     │                │  Addon       │
└─────────────────┘                  └──────────────────┘                └──────────────┘
                                     │
                                     ├── vrc_tools.py (23 VRC tools)
                                     ├── blender_master_tools.py (10 advanced tools)
                                     ├── sculpt_bake_tools.py (14 sculpt/bake tools)
                                     ├── face_tracking_tools.py (10 ARKit/Unified tools)
                                     ├── rigify_tools.py (6 Rigify tools)
                                     ├── unity_tools.py (15 Unity automation tools)
                                     └── pipeline_tools.py (5 orchestration tools)
```

- **MCP Server** (`server.py`): FastMCP server exposing 185 tools via stdio transport
- **VRC Tools** (`vrc_tools.py`): VRChat avatar pipeline — validation, rigging, visemes, PhysBones, export
- **Master Tools** (`blender_master_tools.py`): Advanced mesh — BMesh, retopology, procedural generation
- **Sculpt & Bake** (`sculpt_bake_tools.py`): Sculpt mode, brush strokes, texture baking (normal/AO/diffuse)
- **Face Tracking** (`face_tracking_tools.py`): ARKit 52 blend shapes, VRCFT Unified Expressions, tongue/eye tracking
- **Rigify** (`rigify_tools.py`): Meta-rig generation, fitting, VRC bone conversion, IK configuration
- **Unity** (`unity_tools.py`): C# EditorScript generation, Unity CLI automation, avatar descriptor, animator, shaders
- **Pipeline** (`pipeline_tools.py`): End-to-end orchestration — mesh-to-FBX, FBX-to-Unity, face tracking setup
- **Blender Addon** (`addon/__init__.py`): TCP socket server + CommandExecutor with `cmd_` dispatch pattern

## Installation / 安裝

### 1. Install the MCP Server / 安裝 MCP 伺服器

```bash
# Using uv (recommended / 推薦)
uv pip install -e .

# Or using pip
pip install -e .
```

### 2. Install the Blender Addon / 安裝 Blender 外掛

**Option A: Copy directly / 直接複製**

Copy `addon/__init__.py` to your Blender addons directory:

```
# Windows
%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\blender_copilot.py

# macOS
~/Library/Application Support/Blender/<version>/scripts/addons/blender_copilot.py

# Linux
~/.config/blender/<version>/scripts/addons/blender_copilot.py
```

**Option B: Blender Extension (4.2+) / Blender 擴展**

Copy the entire `addon/` folder to your extensions directory:

```
# Windows
%APPDATA%\Blender Foundation\Blender\<version>\extensions\user\blender_copilot\
```

### 3. Enable the Addon / 啟用外掛

1. Open Blender → Edit → Preferences → Add-ons
2. Search for "Blender Copilot"
3. Enable it
4. In the 3D Viewport sidebar (N key) → Copilot tab → Click "Connect to AI"

### 4. Configure Your AI Client / 配置 AI 客戶端

Add to your `.mcp.json` or MCP config:

```json
{
  "mcpServers": {
    "blender-copilot": {
      "command": "uv",
      "args": ["--directory", "/path/to/blender-copilot", "run", "blender-copilot"]
    }
  }
}
```

Or if installed globally:

```json
{
  "mcpServers": {
    "blender-copilot": {
      "command": "blender-copilot"
    }
  }
}
```

## Auto-Start (Optional) / 自動啟動（可選）

Create a startup script to automatically start the Copilot server when Blender launches:

Save as `mcp_autostart.py` in Blender's startup folder:
```
# Windows: %APPDATA%\Blender Foundation\Blender\<version>\scripts\startup\
# macOS: ~/Library/Application Support/Blender/<version>/scripts/startup/
# Linux: ~/.config/blender/<version>/scripts/startup/
```

```python
import bpy

def _auto_start():
    try:
        bpy.context.scene.copilot_port = 9876
        bpy.ops.copilot.start()
        print("[Copilot] Auto-started")
    except:
        pass
    return None

def register():
    bpy.app.timers.register(_auto_start, first_interval=3.0)

def unregister():
    pass
```

## Environment Variables / 環境變數

| Variable | Default | Description |
|----------|---------|-------------|
| `BLENDER_HOST` | `localhost` | Blender addon TCP host |
| `BLENDER_PORT` | `9876` | Blender addon TCP port |

## Compatibility / 相容性

- **Blender**: 4.0+ (tested on 4.2, 5.0, 5.1)
- **Python**: 3.10+
- **OS**: Windows, macOS, Linux
- **AI Clients**: Claude Code, Claude Desktop, Cursor, Windsurf, Cline, or any MCP-compatible client

## Documentation / 文檔

- `docs/MODELER_KNOWLEDGE_BASE.md` — VRChat avatar pipeline reference (performance ranks, export settings, weight painting rules)
- `docs/MAYO_VRC_MANUAL.md` — Complete operation manual for the Mayo avatar project

## License / 授權

MIT License - see [LICENSE](LICENSE)

## Credits / 致謝

Original work by [DWGX](https://github.com/dwgx). Not a fork.

Inspired by the Blender MCP ecosystem, with features consolidated and expanded from research across 17+ community projects.

本項目為原創作品，非 fork。靈感來自 Blender MCP 生態系統，整合並擴展了 17+ 個社群項目的功能。
