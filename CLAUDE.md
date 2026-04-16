# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Blender Copilot — Agent Onboarding Guide

## What This Project Is

An MCP (Model Context Protocol) server that lets AI agents control Blender for 3D modeling. **308 tools** total — the most comprehensive Blender MCP server available. Full zero-to-published VRChat avatar pipeline plus complete 3D workflow automation.

**The user (DWGX) wants the AI to operate like a real 3D modeler** — not just execute commands, but understand mesh topology, weight painting, UV layout, VRChat avatar constraints, and make artistic/technical decisions autonomously.

## AI Working Principles (Core — applies to ALL sessions)

The AI is a **master executor**, not a designer. This is how every interaction works:

1. **Aesthetics & design judgment → HUMAN.** The AI never assumes what looks good. When aesthetic choices arise, ASK the user. Research references, present options with visual/technical tradeoffs, but the human makes the call.
2. **Form & shape description → HUMAN.** The user describes the shape, silhouette, proportions, character feel. The AI's job is to understand the description as deeply as possible — ask clarifying questions about spatial relationships, curvature intent, muscle/fat distribution, stylization level.
3. **Sculpting → AI must be PERFECT.** This is non-negotiable. The AI must:
   - Master every Blender sculpt brush parameter (radius, strength, falloff, stroke method, texture)
   - Execute systematic sculpting passes: primary forms → secondary forms → tertiary detail
   - Understand anatomy (bone landmarks, muscle insertions, fat pads, skin tension)
   - Use multi-resolution workflow correctly (base shape at low subdiv, detail at high)
   - Generate the most precise sculpt code possible — exact coordinates, curves, pressure profiles
   - Research and apply the best known techniques for each sculpting task
4. **Execution precision → AI must MAXIMIZE.** For every operation (not just sculpting):
   - Push parameter precision to the limit
   - Understand the "why" behind each value, not just copy defaults
   - When uncertain, research first (use codex-subagent for heavy lookups)
5. **Proactive questioning:** When the user gives a vague shape description, don't guess — ask structured questions:
   - "这个曲面是要偏硬（机械感）还是偏软（有机感）？"
   - "参考图里的这个转折，你想要多锐利？"
   - "这个比例是写实还是stylized？大概几头身？"

## Architecture

```
AI ←(stdio/MCP)→ server.py ←(TCP:9876)→ Blender Addon
```

### MCP Server Side (`src/blender_copilot/`)

- `server.py` — Entry point (`main()` → `mcp.run(transport="stdio")`). Defines 102 core MCP tools inline and `send_command()` which all tools use. At the bottom, imports and calls all `register_*` functions from extension modules.
- `vrc_tools.py` — 23 VRC avatar tools. `register_vrc_tools(mcp, send_command)`.
- `blender_master_tools.py` — 10 advanced mesh tools (BMesh, retopology, procedural gen). `register_master_tools(mcp, send_command)`.
- `sculpt_bake_tools.py` — 14 sculpt/texture bake tools. `register_sculpt_bake_tools(mcp, send_command)`.
- `sculpt_advanced_tools.py` — 15 professional sculpting tools (full brush control, anatomy-aware sculpting, multi-res workflow). `register_sculpt_advanced_tools(mcp, send_command)`.
- `sculpt_anatomy_data.py` — Anatomy constants: face/body proportions (realistic + anime), muscle groups, bone landmarks. Used by sculpt_advanced_tools.
- `face_tracking_tools.py` — 10 ARKit 52 + Unified Expressions tools. `register_face_tracking_tools(mcp, send_command)`.
- `face_tracking_constants.py` — ARKit 52 names, displacement recipes, Unified Expressions, mappings.
- `rigify_tools.py` — 6 Rigify rig generation/VRC conversion tools. `register_rigify_tools(mcp, send_command)`.
- `unity_tools.py` — 15 Unity automation tools (C# EditorScript generation + CLI). `register_unity_tools(mcp, send_command)`.
- `pipeline_tools.py` — 5 end-to-end pipeline orchestration tools. `register_pipeline_tools(mcp, send_command)`.
- `blender_manager.py` — 6 Blender process management tools (launch/status/open/save/new/quit). `register_blender_manager_tools(mcp, send_command)`. Auto-detects Blender executable, launches with addon auto-start via `scripts/blender_auto_start.py`.
- `script_tools.py` — 4 headless script execution tools (JSON→bpy, headless Blender subprocess). `register_script_tools(mcp, send_command)`.
- `render_tools.py` — 8 render preset/management tools (7 presets, HDRI, animation render). `register_render_tools(mcp, send_command)`.
- `scene_tools.py` — 9 scene profile/management tools (10 profiles, turntable, collections, cleanup). `register_scene_tools(mcp, send_command)`.
- `modifier_tools.py` — 9 modifier tools with parameter validation registry (15 modifier types). `register_modifier_tools(mcp, send_command)`.
- `animation_tools.py` — 9 animation tools (keyframes, interpolation, bounce/orbit presets). `register_animation_tools(mcp, send_command)`.
- `material_tools.py` — 7 material tools (12 PBR presets, texture assignment). `register_material_tools(mcp, send_command)`.
- `uv_tools.py` — 8 UV mapping tools (smart unwrap, projections, seams, packing). `register_uv_tools(mcp, send_command)`.
- `curve_tools.py` — 7 curve tools (Bezier, NURBS, paths, 3D text, conversion). `register_curve_tools(mcp, send_command)`.
- `physics_tools.py` — 7 physics tools (rigid body, cloth, particles, soft body, baking). `register_physics_tools(mcp, send_command)`.
- `armature_tools.py` — 7 armature/bone tools (create, add bones, chains, constraints, auto-weight). `register_armature_tools(mcp, send_command)`.
- `io_tools.py` — 6 file I/O tools (FBX, glTF, OBJ, STL, USD import/export). `register_io_tools(mcp, send_command)`.
- `lighting_tools.py` — 5 lighting tools (add/modify lights, 3-point rig, studio setup). `register_lighting_tools(mcp, send_command)`.
- `measurement_tools.py` — 6 measurement/verification tools (distance, dimensions, overlap, symmetry, mesh quality). `register_measurement_tools(mcp, send_command)`.
- `vrc_constants.py` — VRChat performance rank limits, bone mappings.

### Blender Addon Side (`addon/`)

- `addon/__init__.py` (2915 lines) — Blender-side TCP server + `CommandExecutor` with 112 `cmd_*` methods. Also contains UI panels for PolyHaven/Sketchfab/Hyper3D/Hunyuan3D asset browsers.

### Other

- `blender_exec.py` — Standalone helper for running Python in Blender headless.
- `scripts/blender_auto_start.py` — Startup script passed to `blender --python`. Auto-installs addon, enables it, starts TCP server. Used by `blender_launch` tool.
- `session/` — Gitignored directory for session export files.

## How Commands Flow

1. AI calls MCP tool (e.g., `vrc_validate`)
2. Tool function calls `send_command("execute_code", {"code": "..."})` (VRC/Master/Sculpt tools all generate Python and use execute_code)
3. Or for core tools: `send_command("get_scene_info")` → addon dispatches to `cmd_get_scene_info`
4. `send_command()` sends JSON over TCP to the addon's `CopilotServer`
5. Addon deserializes, dispatches to `CommandExecutor.execute()` via `bpy.app.timers.register()` (ensures execution on Blender's main thread)
6. Result JSON is sent back over the same TCP connection

### Tool Registration Pattern

Extension modules follow a consistent pattern: a single `register_*(mcp, send_command_fn)` function that defines `@mcp.tool()` decorated functions inside it, capturing `send_command_fn` via closure. Most extension tools use a local `_exec(code)` helper that calls `send_command_fn("execute_code", {"code": code})`.

## Tool Name Mapping

- Core tools: server `send_command("xxx")` → addon `cmd_xxx` — 95/95 matched, verified.
- VRC + Master + Sculpt + Face + Rigify + Unity + Pipeline tools: all go through `cmd_execute_code` with generated Python scripts.
- Addon has 12 extra alias methods (e.g., `cmd_decimate_mesh` wraps `cmd_decimate`) — harmless.

## Key Files to Read First

1. `docs/MODELER_KNOWLEDGE_BASE.md` — **READ THIS BEFORE ANY VRC WORK.** Contains performance rank tables, FBX export settings, weight painting rules, the 14-step pipeline, and known pitfalls.
2. `docs/MAYO_VRC_MANUAL.md` — Operation manual for the Mayo avatar (specific model the user works with).

## Development Commands

```bash
# Syntax check all Python source files
python -m py_compile src/blender_copilot/server.py
python -m py_compile addon/__init__.py
# Or check all at once:
for f in src/blender_copilot/*.py addon/__init__.py; do python -m py_compile "$f"; done

# Run MCP server (requires Blender addon running on TCP:9876)
uv run blender-copilot

# Install in dev mode
uv pip install -e .
```

There is no test suite. Validation is done by running the MCP server against a live Blender instance with the addon active.

## Conventions

- All tools use `send_command()` to talk to Blender — never bypass this.
- VRC/Master/Sculpt tools generate Python code strings and send via `execute_code` — this is intentional, not a hack.
- Tool docstrings are user-facing (shown in AI client) — keep them descriptive.
- Bilingual comments (EN/ZH) are welcome — the user works in both languages.
- The addon's `cmd_` dispatch pattern: command type string maps to `cmd_{type}` method on CommandExecutor.

## Adding a New Tool

**If the addon already has a matching `cmd_*` handler:**
Add a `@mcp.tool()` function in `server.py` that calls `send_command("the_command", {...})`.

**If you need new Blender-side logic:**
Either add a `cmd_*` method in `addon/__init__.py`, or (more common for complex tools) generate the Python code string in a new/existing extension module and send it via `execute_code`.

**Adding a new extension module:**
1. Create `src/blender_copilot/your_tools.py` with a `register_your_tools(mcp, send_command_fn)` function
2. Import and call it at the bottom of `server.py` (before the `main()` function)

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
- **Hyper3D (Rodin)**: API key required (addon has a free trial key hardcoded as fallback), async job polling
- **Hunyuan3D**: API key required, async job polling

## What NOT to Do

- Don't add tools without matching `cmd_` methods in the addon (or using `execute_code`)
- Don't change the TCP protocol format (JSON over socket, single response)
- Don't assume Blender is running — always handle `ConnectionRefusedError`
- Don't modify VRC constants without checking official VRChat docs first
