# Blender Copilot — Agent Onboarding Guide

## What This Project Is

An MCP (Model Context Protocol) server that lets AI agents control Blender for 3D modeling. 135 tools total.

**The user (DWGX) wants the AI to operate like a real 3D modeler** — not just execute commands, but understand mesh topology, weight painting, UV layout, VRChat avatar constraints, and make artistic/technical decisions autonomously.

## Architecture

```
AI ←(stdio/MCP)→ server.py ←(TCP:9876)→ Blender Addon
```

- `src/blender_copilot/server.py` — 102 MCP tools (core + asset integration). Entry point: `main()`.
- `src/blender_copilot/vrc_tools.py` — 23 VRC avatar tools. Registered via `register_vrc_tools(mcp, send_command)`.
- `src/blender_copilot/blender_master_tools.py` — 10 advanced mesh tools. Registered via `register_master_tools(mcp, send_command)`.
- `src/blender_copilot/vrc_constants.py` — VRChat performance rank limits, bone mappings.
- `addon/__init__.py` — Blender-side TCP server, 112 `cmd_*` methods, UI panels for PolyHaven/Sketchfab/Hyper3D/Hunyuan3D.
- `blender_exec.py` — Standalone helper for running Python in Blender headless.

## How Commands Flow

1. AI calls MCP tool (e.g., `vrc_validate`)
2. Tool function calls `send_command("execute_code", {"code": "..."})` (VRC/Master tools all use execute_code)
3. Or for core tools: `send_command("get_scene_info")` → addon dispatches to `cmd_get_scene_info`
4. Addon executes in Blender, returns JSON via TCP

## Tool Name Mapping

- Core tools: server `send_command("xxx")` → addon `cmd_xxx` — 95/95 matched, verified.
- VRC + Master tools: all go through `cmd_execute_code` with generated Python scripts.
- Addon has 12 extra alias methods (e.g., `cmd_decimate_mesh` wraps `cmd_decimate`) — harmless.

## Key Files to Read First

1. `docs/MODELER_KNOWLEDGE_BASE.md` — **READ THIS BEFORE ANY VRC WORK.** Contains performance rank tables, FBX export settings, weight painting rules, the 14-step pipeline, and known pitfalls.
2. `docs/MAYO_VRC_MANUAL.md` — Operation manual for the Mayo avatar (specific model the user works with).

## Development Commands

```bash
# Syntax check all Python
python -m py_compile src/blender_copilot/server.py
python -m py_compile addon/__init__.py

# Run MCP server (requires Blender addon running)
uv run blender-copilot

# Install in dev mode
uv pip install -e .
```

## Conventions

- All tools use `send_command()` to talk to Blender — never bypass this.
- VRC/Master tools generate Python code strings and send via `execute_code` — this is intentional, not a hack.
- Tool docstrings are user-facing (shown in AI client) — keep them descriptive.
- Bilingual comments (EN/ZH) are welcome — the user works in both languages.
- The addon's `cmd_` dispatch pattern: command type string maps to `cmd_{type}` method on CommandExecutor.

## VRChat Avatar Work

The primary use case is VRChat avatar creation and modification. Key constraints:
- PC Excellent: 32K tris, 4 materials, 75 bones, 40MB textures
- Quest: 20K tris hard limit, Mobile/Toon Lit shader only
- Always validate before export (`vrc_validate`)
- Never decimate the only copy — keep backups
- FBX export: `add_leaf_bones=False` is CRITICAL

## Asset Integration APIs

- **PolyHaven**: Free, no API key needed
- **Sketchfab**: Requires API key (set in addon preferences)
- **Hyper3D (Rodin)**: API key required, async job polling
- **Hunyuan3D**: API key required, async job polling

## What NOT to Do

- Don't add tools without matching `cmd_` methods in the addon (or using `execute_code`)
- Don't change the TCP protocol format (JSON over socket, single response)
- Don't assume Blender is running — always handle `ConnectionRefusedError`
- Don't modify VRC constants without checking official VRChat docs first
