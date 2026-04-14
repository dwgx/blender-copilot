# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Blender Copilot — Agent Onboarding Guide

## What This Project Is

An MCP (Model Context Protocol) server that lets AI agents control Blender for 3D modeling. 185 tools total — full zero-to-published VRChat avatar pipeline.

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

- `src/blender_copilot/server.py` — 102 MCP tools (core + asset integration). Entry point: `main()`.
- `src/blender_copilot/vrc_tools.py` — 23 VRC avatar tools. Registered via `register_vrc_tools(mcp, send_command)`.
- `src/blender_copilot/blender_master_tools.py` — 10 advanced mesh tools. Registered via `register_master_tools(mcp, send_command)`.
- `src/blender_copilot/sculpt_bake_tools.py` — 14 sculpt/texture bake tools. Registered via `register_sculpt_bake_tools(mcp, send_command)`.
- `src/blender_copilot/face_tracking_tools.py` — 10 ARKit 52 + Unified Expressions tools. Registered via `register_face_tracking_tools(mcp, send_command)`.
- `src/blender_copilot/face_tracking_constants.py` — ARKit 52 names, displacement recipes, Unified Expressions, mappings.
- `src/blender_copilot/rigify_tools.py` — 6 Rigify rig generation/VRC conversion tools. Registered via `register_rigify_tools(mcp, send_command)`.
- `src/blender_copilot/unity_tools.py` — 15 Unity automation tools (C# EditorScript generation + CLI). Registered via `register_unity_tools(mcp, send_command)`.
- `src/blender_copilot/pipeline_tools.py` — 5 end-to-end pipeline orchestration tools. Registered via `register_pipeline_tools(mcp, send_command)`.
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
