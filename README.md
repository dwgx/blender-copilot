# Blender Copilot

**The most comprehensive Blender MCP server — AI-powered 3D creation with 135 tools.**

最全面的 Blender MCP 伺服器 — AI 驅動的 3D 創作，135 種工具。

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
                                     └── blender_master_tools.py (10 advanced tools)
```

- **MCP Server** (`src/blender_copilot/server.py`): FastMCP server exposing 135 tools via stdio transport
- **VRC Tools** (`src/blender_copilot/vrc_tools.py`): VRChat avatar pipeline (registered via `register_vrc_tools`)
- **Master Tools** (`src/blender_copilot/blender_master_tools.py`): Advanced mesh operations (registered via `register_master_tools`)
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
