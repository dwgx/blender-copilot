"""
Blender process management — launch, connect, file ops.
No computer-use or manual UI interaction needed.
"""
import glob
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time

logger = logging.getLogger("BlenderMCPServer.Manager")

# Track the launched Blender subprocess
_blender_process = None


def _find_blender_executable() -> str | None:
    """Auto-detect Blender executable on the system."""
    # 1. Env var override
    env = os.environ.get("BLENDER_PATH")
    if env and os.path.isfile(env):
        return env

    # 2. Windows common paths (newest version first)
    if sys.platform == "win32":
        for base in [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Blender Foundation"),
            r"D:\Software",
            r"E:\Software",
        ]:
            pattern = os.path.join(base, "Blender Foundation", "Blender *", "blender.exe")
            matches = sorted(glob.glob(pattern), reverse=True)
            if matches:
                return matches[0]
            # Also check without "Blender Foundation" nesting (some installs)
            pattern2 = os.path.join(base, "Blender *", "blender.exe")
            matches2 = sorted(glob.glob(pattern2), reverse=True)
            if matches2:
                return matches2[0]

        # Steam
        steam_paths = glob.glob(
            r"C:\Program Files*\Steam\steamapps\common\Blender\blender.exe"
        )
        if steam_paths:
            return steam_paths[0]

    # 3. macOS
    elif sys.platform == "darwin":
        mac_path = "/Applications/Blender.app/Contents/MacOS/Blender"
        if os.path.isfile(mac_path):
            return mac_path

    # 4. PATH fallback (all platforms)
    found = shutil.which("blender")
    if found:
        return found

    return None


def _check_connection(host: str = "localhost", port: int = 9876) -> bool:
    """Check if the Blender addon TCP server is responding."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((host, port))
        sock.sendall(json.dumps({"type": "get_scene_info"}).encode())
        data = sock.recv(4096)
        sock.close()
        return bool(data)
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


# Resolve project root once (blender-copilot/)
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def register_blender_manager_tools(mcp, send_command_fn):
    """Register Blender management tools on the FastMCP instance."""

    @mcp.tool()
    def blender_launch(
        file_path: str = "",
        port: int = 9876,
        blender_path: str = "",
    ) -> str:
        """Launch Blender with Copilot addon auto-started. No manual UI clicks needed.

        file_path: Optional .blend file to open on launch.
        port: TCP port for the addon server (default 9876).
        blender_path: Override Blender executable path (auto-detected if empty).

        The addon is automatically installed (if needed), enabled, and the
        TCP server is started. Connection is verified before returning.
        """
        global _blender_process

        # Already connected?
        host = os.environ.get("BLENDER_HOST", "localhost")
        if _check_connection(host, port):
            return f"Blender already connected on port {port}."

        # Find executable
        exe = blender_path or _find_blender_executable()
        if not exe:
            return (
                "Blender executable not found. Options:\n"
                "1. Set BLENDER_PATH environment variable\n"
                "2. Pass blender_path parameter\n"
                "3. Add Blender to your system PATH"
            )

        startup_script = os.path.join(_PROJECT_ROOT, "scripts", "blender_auto_start.py")
        addon_source = os.path.join(_PROJECT_ROOT, "addon", "__init__.py")

        if not os.path.isfile(startup_script):
            return f"Auto-start script not found: {startup_script}"

        # Build command
        cmd = [exe]
        if file_path:
            cmd.append(os.path.abspath(file_path))
        cmd.extend(["--python", startup_script])

        # Environment
        env = os.environ.copy()
        env["BLENDER_PORT"] = str(port)
        env["COPILOT_ADDON_SOURCE"] = addon_source

        # Launch (redirect stdout to avoid corrupting MCP stdio transport)
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        _blender_process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=creation_flags,
        )

        # Wait for connection (poll every 1s, up to 25s)
        for _ in range(25):
            time.sleep(1)
            if _check_connection(host, port):
                return (
                    f"Blender launched and connected on port {port}. "
                    f"(PID: {_blender_process.pid}, exe: {exe})"
                )
            # Check if process crashed
            if _blender_process.poll() is not None:
                stderr = ""
                try:
                    stderr = _blender_process.stderr.read().decode(errors="replace")[:500]
                except Exception:
                    pass
                return (
                    f"Blender exited with code {_blender_process.returncode}.\n{stderr}"
                )

        return (
            f"Blender launched (PID: {_blender_process.pid}) but connection not ready.\n"
            f"The addon may still be loading — retry get_scene_info in a few seconds."
        )

    @mcp.tool()
    def blender_status(port: int = 9876) -> str:
        """Check Blender connection status, executable path, and scene summary."""
        host = os.environ.get("BLENDER_HOST", "localhost")
        connected = _check_connection(host, port)
        exe = _find_blender_executable()

        lines = [
            f"Connected: {'Yes' if connected else 'No'} (port {port})",
            f"Blender exe: {exe or 'Not found'}",
        ]

        if _blender_process and _blender_process.poll() is None:
            lines.append(f"Managed PID: {_blender_process.pid}")

        if connected:
            try:
                info = send_command_fn("get_scene_info")
                obj_count = len(info.get("objects", []))
                file_name = info.get("file", "unsaved")
                lines.append(f"File: {file_name}")
                lines.append(f"Objects: {obj_count}")
            except Exception:
                pass

        return "\n".join(lines)

    @mcp.tool()
    def blender_open_file(file_path: str) -> dict:
        """Open a .blend file in the running Blender instance.
        Replaces the current scene — save first if needed."""
        abs_path = os.path.abspath(file_path).replace("\\", "/")
        return send_command_fn(
            "execute_code",
            {"code": f'import bpy; bpy.ops.wm.open_mainfile(filepath="{abs_path}")'},
        )

    @mcp.tool()
    def blender_save(file_path: str = "") -> dict:
        """Save the current Blender file. If file_path is given, does Save As.
        If empty and file was never saved, returns an error."""
        if file_path:
            abs_path = os.path.abspath(file_path).replace("\\", "/")
            code = f'import bpy; bpy.ops.wm.save_as_mainfile(filepath="{abs_path}")'
        else:
            code = "import bpy; bpy.ops.wm.save_mainfile()"
        return send_command_fn("execute_code", {"code": code})

    @mcp.tool()
    def blender_new_file() -> dict:
        """Create a new blank Blender file (General template). Discards unsaved changes."""
        return send_command_fn(
            "execute_code",
            {"code": "import bpy; bpy.ops.wm.read_homefile(use_empty=False)"},
        )

    @mcp.tool()
    def blender_quit(save: bool = False) -> str:
        """Quit Blender gracefully. Set save=True to save before quitting."""
        global _blender_process
        try:
            if save:
                send_command_fn(
                    "execute_code",
                    {"code": "import bpy; bpy.ops.wm.save_mainfile()"},
                )
            send_command_fn(
                "execute_code",
                {"code": "import bpy; bpy.ops.wm.quit_blender()"},
            )
        except Exception:
            pass  # Connection drops when Blender exits
        _blender_process = None
        return "Blender quit command sent."
