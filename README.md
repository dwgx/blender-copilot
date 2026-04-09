# Blender Copilot

**The most comprehensive Blender MCP server — AI-powered 3D creation with 70+ tools.**

最全面的 Blender MCP 伺服器 — AI 驅動的 3D 創作，超過 70 種工具。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.0+](https://img.shields.io/badge/blender-4.0+-orange.svg)](https://www.blender.org/)

---

## Features / 功能特色

| Category | Tools | Description |
|----------|-------|-------------|
| Scene Inspection | 4 | Get scene info, object details, analysis, viewport screenshots |
| Object Creation | 4 | Primitives, curves, 3D text, armatures |
| Transforms | 6 | Translate, rotate, scale, apply, snap to ground, set origin |
| Object Management | 9 | Duplicate, delete, select, parent, visibility, hierarchy, rename |
| Mesh Editing | 14 | Boolean, join, separate, subdivide, extrude, bevel, inset, decimate, remesh, normals, fill holes |
| Modifiers | 5 | Add/apply/remove modifiers, linear array, circular array |
| Materials | 6 | PBR materials, glass, metal, emission, list, batch assign |
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

## Architecture / 架構

```
┌─────────────────┐    stdio/MCP     ┌──────────────────┐    TCP:9876    ┌──────────────┐
│  AI (Claude,    │ ◄──────────────► │  MCP Server      │ ◄────────────► │  Blender     │
│  Cursor, etc.)  │                  │  (server.py)     │                │  Addon       │
└─────────────────┘                  └──────────────────┘                └──────────────┘
```

- **MCP Server** (`src/blender_copilot/server.py`): FastMCP server exposing 70+ tools via stdio transport
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

## License / 授權

MIT License - see [LICENSE](LICENSE)

## Credits / 致謝

Original work by [DWGX](https://github.com/dwgx). Not a fork.

Inspired by the Blender MCP ecosystem, with features consolidated and expanded from research across 17+ community projects.

本項目為原創作品，非 fork。靈感來自 Blender MCP 生態系統，整合並擴展了 17+ 個社群項目的功能。
