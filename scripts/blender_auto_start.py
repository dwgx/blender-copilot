"""
Blender Copilot auto-start script.
Launched via: blender [file.blend] --python scripts/blender_auto_start.py

Automatically installs (if needed), enables addon, and starts TCP server.
Bypasses bpy.ops which can fail in timer/headless context.

Environment variables:
  BLENDER_PORT           — TCP port (default 9876)
  COPILOT_ADDON_SOURCE   — path to addon/__init__.py
"""
import bpy
import os
import sys
import shutil
import traceback


_LOG_FILE = os.path.join(os.environ.get("TEMP", "/tmp"), "copilot_autostart.log")


def _log(msg: str):
    """Print and log to file for debugging."""
    line = f"[Copilot] {msg}"
    print(line)
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _install_addon(addon_src: str) -> bool:
    """Copy addon source into Blender's user addons directory."""
    addon_dir = bpy.utils.user_resource('SCRIPTS', path="addons")
    os.makedirs(addon_dir, exist_ok=True)
    dst = os.path.join(addon_dir, "blender_copilot.py")
    shutil.copy2(addon_src, dst)
    _log(f"Installed addon to {dst}")
    return True


def _setup():
    """Enable addon and start TCP server directly."""
    # Clear log
    try:
        with open(_LOG_FILE, "w") as f:
            f.write("")
    except Exception:
        pass

    port = int(os.environ.get("BLENDER_PORT", "9876"))
    addon_src = os.environ.get("COPILOT_ADDON_SOURCE", "")
    module_name = "blender_copilot"

    _log(f"Starting setup (port={port})")

    # Step 1: Ensure addon is enabled via addon_utils (no UI context needed)
    import addon_utils

    mod = None
    try:
        mod = addon_utils.enable(module_name, default_set=True, persistent=True)
        _log("Addon enabled via addon_utils")
    except Exception as e:
        _log(f"addon_utils.enable failed: {e}")
        # Maybe not installed — install from source
        if addon_src and os.path.isfile(addon_src):
            _install_addon(addon_src)
            try:
                # Refresh module list after install
                addon_utils.modules_refresh()
                mod = addon_utils.enable(module_name, default_set=True, persistent=True)
                _log("Addon installed and enabled")
            except Exception as e2:
                _log(f"Still failed after install: {e2}")
                traceback.print_exc()
                return None
        else:
            _log(f"Addon source not found: {addon_src}")
            return None

    # Step 2: Get the addon module (for CopilotServer class)
    if mod is None:
        # addon_utils.enable may return None if already enabled — find it
        for m in addon_utils.modules():
            if m.__name__ == module_name:
                mod = m
                break

    if mod is None:
        # Last resort: try direct import
        try:
            import importlib
            mod = importlib.import_module(module_name)
            _log("Module imported via importlib")
        except ImportError as e:
            _log(f"Cannot find addon module: {e}")
            return None

    # Step 3: Start TCP server directly (bypass bpy.ops which needs UI context)
    try:
        if not hasattr(mod, "CopilotServer"):
            _log(f"Module has no CopilotServer class. attrs: {[a for a in dir(mod) if not a.startswith('_')]}")
            return None

        bpy.context.scene.copilot_port = port

        if not hasattr(bpy.types, "copilot_server") or not bpy.types.copilot_server:
            bpy.types.copilot_server = mod.CopilotServer(port=port)
            _log("Created CopilotServer instance")

        bpy.types.copilot_server.start()
        bpy.context.scene.copilot_running = True
        _log(f"Server started on port {port}")
    except Exception as e:
        _log(f"Server start failed: {e}")
        traceback.print_exc()

    return None  # Don't repeat


# Delay 3s to ensure Blender is fully initialized
bpy.app.timers.register(_setup, first_interval=3.0)
print("[Copilot] Auto-start scheduled (3s delay)...")
