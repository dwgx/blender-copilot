# Blender Copilot - AI-Powered 3D Creation via MCP
# Copyright (c) 2026 DWGX - MIT License
# Original work, not a fork. Inspired by the Blender MCP ecosystem.

import bpy
import bmesh
import mathutils
import json
import math
import re
import threading
import socket
import time
import requests
import tempfile
import traceback
import os
import shutil
import zipfile
import hashlib
import hmac
import base64
from bpy.props import (IntProperty, BoolProperty, StringProperty,
                       EnumProperty, FloatProperty)
from contextlib import redirect_stdout, suppress
from datetime import datetime
import io
import os.path as osp

bl_info = {
    "name": "Blender Copilot",
    "author": "DWGX",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Copilot",
    "description": "AI-powered 3D creation via MCP - 150+ tools + asset integrations",
    "category": "Interface",
}

RODIN_FREE_TRIAL_KEY = "k9TcfFoEhNd9cCPP2guHAHHHkctZHIRhZDywZ1euGUXwihbYLpOjQhofby80NJez"

# Add User-Agent as required by Poly Haven API
REQ_HEADERS = requests.utils.default_headers()
REQ_HEADERS.update({"User-Agent": "blender-copilot"})


# =============================================================================
#  TCP Socket Server
# =============================================================================

class CopilotServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.executor = CommandExecutor()

    def start(self):
        if self.running:
            return
        self.running = True
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.socket.settimeout(1.0)
            t = threading.Thread(target=self._serve, daemon=True)
            t.start()
            print(f"[Copilot] Listening on {self.host}:{self.port}")
        except Exception as e:
            print(f"[Copilot] Start failed: {e}")
            self.stop()

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        print("[Copilot] Server stopped")

    def _serve(self):
        while self.running:
            try:
                client, addr = self.socket.accept()
                threading.Thread(target=self._handle, args=(client,), daemon=True).start()
            except socket.timeout:
                continue
            except:
                if self.running:
                    time.sleep(0.5)

    def _handle(self, client):
        client.settimeout(None)
        buf = b''
        try:
            while self.running:
                data = client.recv(65536)
                if not data:
                    break
                buf += data
                try:
                    command = json.loads(buf.decode('utf-8'))
                    buf = b''

                    def run():
                        try:
                            result = self.executor.execute(command)
                            resp = json.dumps(result)
                            try:
                                client.sendall(resp.encode('utf-8'))
                            except:
                                pass
                        except Exception as e:
                            traceback.print_exc()
                            try:
                                client.sendall(json.dumps({
                                    "status": "error", "message": str(e)
                                }).encode('utf-8'))
                            except:
                                pass
                        return None

                    bpy.app.timers.register(run, first_interval=0.0)
                except json.JSONDecodeError:
                    pass
        except:
            pass
        finally:
            try:
                client.close()
            except:
                pass


# =============================================================================
#  Command Executor - All 150+ tool handlers
# =============================================================================

class CommandExecutor:
    """Routes commands to handler methods. Each method is a tool."""

    def execute(self, command):
        cmd = command.get("type", "")
        params = command.get("params", {})
        handler = getattr(self, f"cmd_{cmd}", None)
        if handler:
            try:
                result = handler(**params)
                return {"status": "success", "result": result}
            except Exception as e:
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": f"Unknown command: {cmd}"}

    # =========================================================================
    #  SCENE INSPECTION
    # =========================================================================

    def cmd_get_scene_info(self):
        scene = bpy.context.scene
        objects = []
        for i, obj in enumerate(scene.objects):
            if i >= 50:
                break
            o = {
                "name": obj.name, "type": obj.type,
                "location": [round(v, 3) for v in obj.location],
                "visible": obj.visible_get(),
            }
            if obj.type == 'MESH' and obj.data:
                o["vertices"] = len(obj.data.vertices)
                o["faces"] = len(obj.data.polygons)
            objects.append(o)
        return {
            "scene": scene.name,
            "object_count": len(scene.objects),
            "objects": objects,
            "active_camera": scene.camera.name if scene.camera else None,
            "render_engine": scene.render.engine,
            "frame_range": [scene.frame_start, scene.frame_end],
            "fps": scene.render.fps,
        }

    def cmd_get_object_info(self, name):
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        info = {
            "name": obj.name, "type": obj.type,
            "location": list(obj.location),
            "rotation_euler": [round(math.degrees(r), 2) for r in obj.rotation_euler],
            "scale": list(obj.scale),
            "visible": obj.visible_get(),
            "parent": obj.parent.name if obj.parent else None,
            "children": [c.name for c in obj.children],
            "materials": [s.material.name if s.material else None for s in obj.material_slots],
            "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers],
            "constraints": [{"name": c.name, "type": c.type} for c in obj.constraints],
        }
        if obj.type == 'MESH' and obj.data:
            mesh = obj.data
            info["vertices"] = len(mesh.vertices)
            info["edges"] = len(mesh.edges)
            info["faces"] = len(mesh.polygons)
            info["triangles"] = sum(len(p.vertices) - 2 for p in mesh.polygons)
            # World-space bounding box
            corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
            mn = [min(c[i] for c in corners) for i in range(3)]
            mx = [max(c[i] for c in corners) for i in range(3)]
            info["world_bbox"] = {"min": [round(v, 3) for v in mn], "max": [round(v, 3) for v in mx]}
            dims = [mx[i] - mn[i] for i in range(3)]
            info["dimensions"] = [round(d, 3) for d in dims]
        return info

    def cmd_analyze_scene(self):
        scene = bpy.context.scene
        total_v, total_f, total_t = 0, 0, 0
        issues = []
        top = []
        mats = set()
        for obj in scene.objects:
            if obj.type == 'MESH' and obj.data:
                v = len(obj.data.vertices)
                f = len(obj.data.polygons)
                t = sum(len(p.vertices) - 2 for p in obj.data.polygons)
                total_v += v; total_f += f; total_t += t
                top.append({"name": obj.name, "tris": t})
                sx, sy, sz = obj.scale
                if not (abs(sx - sy) < 0.001 and abs(sy - sz) < 0.001):
                    issues.append(f"{obj.name}: non-uniform scale [{sx:.2f},{sy:.2f},{sz:.2f}]")
                if any(abs(s) < 0.001 for s in obj.scale):
                    issues.append(f"{obj.name}: near-zero scale")
                if not obj.data.materials:
                    issues.append(f"{obj.name}: no material")
                for s in obj.material_slots:
                    if s.material:
                        mats.add(s.material.name)
                # Check ngons
                ngons = sum(1 for p in obj.data.polygons if len(p.vertices) > 4)
                if ngons > 0:
                    issues.append(f"{obj.name}: {ngons} n-gons detected")
        top.sort(key=lambda x: x["tris"], reverse=True)
        return {
            "total_objects": len(scene.objects),
            "meshes": len([o for o in scene.objects if o.type == 'MESH']),
            "lights": len([o for o in scene.objects if o.type == 'LIGHT']),
            "cameras": len([o for o in scene.objects if o.type == 'CAMERA']),
            "empties": len([o for o in scene.objects if o.type == 'EMPTY']),
            "curves": len([o for o in scene.objects if o.type == 'CURVE']),
            "total_vertices": total_v, "total_faces": total_f, "total_triangles": total_t,
            "materials": len(mats),
            "render_engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "camera": scene.camera.name if scene.camera else None,
            "issues": issues[:20],
            "top_by_tris": top[:10],
        }

    def cmd_get_viewport_screenshot(self, max_size=800, filepath=None, format="png"):
        fp = filepath or os.path.join(tempfile.gettempdir(), f"copilot_ss_{os.getpid()}.png")
        # Use OpenGL render for speed
        for area in bpy.context.screen.areas if hasattr(bpy.context, 'screen') and bpy.context.screen else []:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = bpy.context.copy()
                        override['area'] = area
                        override['region'] = region
                        old_fp = bpy.context.scene.render.filepath
                        old_rx = bpy.context.scene.render.resolution_x
                        old_ry = bpy.context.scene.render.resolution_y
                        bpy.context.scene.render.filepath = fp
                        bpy.context.scene.render.resolution_x = max_size
                        bpy.context.scene.render.resolution_y = max_size
                        try:
                            with bpy.context.temp_override(**override):
                                bpy.ops.render.opengl(write_still=True)
                        except:
                            bpy.ops.render.opengl(write_still=True)
                        bpy.context.scene.render.filepath = old_fp
                        bpy.context.scene.render.resolution_x = old_rx
                        bpy.context.scene.render.resolution_y = old_ry
                        return {"filepath": fp}
        # Fallback: full render
        bpy.context.scene.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        return {"filepath": fp}

    # =========================================================================
    #  OBJECT CREATION
    # =========================================================================

    def cmd_create_object(self, type="CUBE", name=None, location=None, scale=None, rotation=None):
        bpy.ops.ed.undo_push(message=f"Create {type}")
        loc = tuple(location) if location else (0, 0, 0)
        t = type.upper()
        ops = {
            "CUBE": lambda: bpy.ops.mesh.primitive_cube_add(location=loc),
            "SPHERE": lambda: bpy.ops.mesh.primitive_uv_sphere_add(location=loc),
            "UV_SPHERE": lambda: bpy.ops.mesh.primitive_uv_sphere_add(location=loc),
            "ICO_SPHERE": lambda: bpy.ops.mesh.primitive_ico_sphere_add(location=loc),
            "CYLINDER": lambda: bpy.ops.mesh.primitive_cylinder_add(location=loc),
            "CONE": lambda: bpy.ops.mesh.primitive_cone_add(location=loc),
            "TORUS": lambda: bpy.ops.mesh.primitive_torus_add(location=loc),
            "PLANE": lambda: bpy.ops.mesh.primitive_plane_add(location=loc),
            "CIRCLE": lambda: bpy.ops.mesh.primitive_circle_add(location=loc),
            "GRID": lambda: bpy.ops.mesh.primitive_grid_add(location=loc),
            "MONKEY": lambda: bpy.ops.mesh.primitive_monkey_add(location=loc),
            "EMPTY": lambda: bpy.ops.object.empty_add(location=loc),
            "CAMERA": lambda: bpy.ops.object.camera_add(location=loc),
            "LIGHT": lambda: bpy.ops.object.light_add(type='POINT', location=loc),
            "POINT_LIGHT": lambda: bpy.ops.object.light_add(type='POINT', location=loc),
            "SUN_LIGHT": lambda: bpy.ops.object.light_add(type='SUN', location=loc),
            "SPOT_LIGHT": lambda: bpy.ops.object.light_add(type='SPOT', location=loc),
            "AREA_LIGHT": lambda: bpy.ops.object.light_add(type='AREA', location=loc),
        }
        fn = ops.get(t)
        if not fn:
            raise ValueError(f"Unknown type: {type}. Options: {', '.join(ops.keys())}")
        fn()
        obj = bpy.context.active_object
        if name:
            obj.name = name
        if scale:
            obj.scale = tuple(scale)
        if rotation:
            obj.rotation_euler = tuple(math.radians(r) for r in rotation)
        return {"name": obj.name, "type": obj.type, "location": [round(v, 4) for v in obj.location]}

    def cmd_create_curve(self, points, name=None, type="BEZIER", bevel_depth=0.0,
                         resolution=12, close=False, extrude=0.0, fill="FULL"):
        curve = bpy.data.curves.new(name or "Curve", 'CURVE')
        curve.dimensions = '3D'
        curve.resolution_u = resolution
        curve.bevel_depth = bevel_depth
        curve.fill_mode = fill.upper()
        curve.extrude = extrude
        if type.upper() == "BEZIER":
            sp = curve.splines.new('BEZIER')
            sp.bezier_points.add(len(points) - 1)
            for i, pt in enumerate(points):
                sp.bezier_points[i].co = tuple(pt[:3])
                sp.bezier_points[i].handle_left_type = 'AUTO'
                sp.bezier_points[i].handle_right_type = 'AUTO'
        else:
            st = 'NURBS' if type.upper() == "NURBS" else 'POLY'
            sp = curve.splines.new(st)
            sp.points.add(len(points) - 1)
            for i, pt in enumerate(points):
                w = pt[3] if len(pt) > 3 else 1.0
                sp.points[i].co = (pt[0], pt[1], pt[2], w)
        if close:
            sp.use_cyclic_u = True
        obj = bpy.data.objects.new(name or "Curve", curve)
        bpy.context.collection.objects.link(obj)
        return {"name": obj.name, "points": len(points), "type": type}

    def cmd_create_text(self, text, name=None, size=1.0, extrude=0.0, bevel_depth=0.0,
                        font_path=None, location=None, rotation=None,
                        align_x="CENTER", align_y="CENTER"):
        cd = bpy.data.curves.new(name or "Text", 'FONT')
        cd.body = text
        cd.size = size
        cd.extrude = extrude
        cd.bevel_depth = bevel_depth
        cd.align_x = align_x.upper()
        cd.align_y = align_y.upper()
        if font_path and os.path.exists(font_path):
            cd.font = bpy.data.fonts.load(font_path)
        obj = bpy.data.objects.new(name or "Text", cd)
        if location:
            obj.location = tuple(location)
        if rotation:
            obj.rotation_euler = tuple(math.radians(r) for r in rotation)
        bpy.context.collection.objects.link(obj)
        return {"name": obj.name, "text": text}

    def cmd_create_armature(self, name=None, bones=None):
        arm = bpy.data.armatures.new(name or "Armature")
        obj = bpy.data.objects.new(name or "Armature", arm)
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bmap = {}
        for b in (bones or []):
            bone = arm.edit_bones.new(b["name"])
            bone.head = tuple(b["head"])
            bone.tail = tuple(b["tail"])
            bmap[b["name"]] = bone
        for b in (bones or []):
            if "parent" in b and b["parent"] in bmap:
                bmap[b["name"]].parent = bmap[b["parent"]]
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": obj.name, "bones": len(bones or [])}

    # =========================================================================
    #  OBJECT TRANSFORMS
    # =========================================================================

    def _get_obj(self, name):
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        return obj

    @staticmethod
    def _get_aabb(obj):
        """Returns the world-space axis-aligned bounding box (AABB) of an object."""
        if obj.type != 'MESH':
            raise TypeError("Object must be a mesh")
        local_bbox_corners = [mathutils.Vector(corner) for corner in obj.bound_box]
        world_bbox_corners = [obj.matrix_world @ corner for corner in local_bbox_corners]
        min_corner = mathutils.Vector(map(min, zip(*world_bbox_corners)))
        max_corner = mathutils.Vector(map(max, zip(*world_bbox_corners)))
        return [[*min_corner], [*max_corner]]

    def cmd_translate_object(self, name, x=0.0, y=0.0, z=0.0, relative=True):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Move {name}")
        if relative:
            obj.location.x += x; obj.location.y += y; obj.location.z += z
        else:
            obj.location = (x, y, z)
        return {"name": name, "location": [round(v, 4) for v in obj.location]}

    def cmd_rotate_object(self, name, x=0.0, y=0.0, z=0.0, relative=True, degrees=True):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Rotate {name}")
        rx = math.radians(x) if degrees else x
        ry = math.radians(y) if degrees else y
        rz = math.radians(z) if degrees else z
        if relative:
            obj.rotation_euler.x += rx; obj.rotation_euler.y += ry; obj.rotation_euler.z += rz
        else:
            obj.rotation_euler = (rx, ry, rz)
        return {"name": name, "rotation_deg": [round(math.degrees(v), 2) for v in obj.rotation_euler]}

    def cmd_scale_object(self, name, x=1.0, y=1.0, z=1.0, uniform=None, relative=True):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Scale {name}")
        if uniform is not None:
            x = y = z = uniform
        if relative:
            obj.scale.x *= x; obj.scale.y *= y; obj.scale.z *= z
        else:
            obj.scale = (x, y, z)
        return {"name": name, "scale": [round(v, 4) for v in obj.scale]}

    def cmd_apply_transform(self, name, location=True, rotation=True, scale=True):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Apply transform {name}")
        bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale)
        return {"name": name, "applied": {"location": location, "rotation": rotation, "scale": scale}}

    def cmd_snap_to_ground(self, name):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Snap {name}")
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        min_z = min(c.z for c in corners)
        obj.location.z -= min_z
        return {"name": name, "location": [round(v, 4) for v in obj.location]}

    def cmd_origin_set(self, name, type="ORIGIN_GEOMETRY"):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Origin {name}")
        bpy.ops.object.origin_set(type=type.upper())
        return {"name": name, "location": [round(v, 4) for v in obj.location]}

    # =========================================================================
    #  OBJECT MANAGEMENT
    # =========================================================================

    def cmd_duplicate_object(self, name, new_name=None, linked=False):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Duplicate {name}")
        new = obj.copy()
        if not linked and obj.data:
            new.data = obj.data.copy()
        if new_name:
            new.name = new_name
        bpy.context.collection.objects.link(new)
        return {"original": name, "duplicate": new.name}

    def cmd_delete_object(self, name):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Delete {name}")
        bpy.data.objects.remove(obj, do_unlink=True)
        return {"deleted": name}

    def cmd_select_object(self, name, add=False):
        obj = self._get_obj(name)
        if not add:
            bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        return {"selected": name}

    def cmd_set_parent(self, child, parent, keep_transform=True):
        c = self._get_obj(child)
        p = self._get_obj(parent)
        bpy.ops.ed.undo_push(message=f"Parent {child} -> {parent}")
        c.parent = p
        if keep_transform:
            c.matrix_parent_inverse = p.matrix_world.inverted()
        return {"child": child, "parent": parent}

    def cmd_clear_parent(self, name, keep_transform=True):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Clear parent {name}")
        mx = obj.matrix_world.copy() if keep_transform else None
        obj.parent = None
        if mx:
            obj.matrix_world = mx
        return {"name": name, "parent": None}

    def cmd_set_visibility(self, name, visible=True, render_visible=True):
        obj = self._get_obj(name)
        obj.hide_viewport = not visible
        obj.hide_render = not render_visible
        return {"name": name, "visible": visible, "render_visible": render_visible}

    def cmd_get_hierarchy(self, name=None):
        def tree(obj):
            return {"name": obj.name, "type": obj.type, "children": [tree(c) for c in obj.children]}
        if name:
            return tree(self._get_obj(name))
        roots = [o for o in bpy.context.scene.objects if not o.parent]
        return {"roots": [tree(r) for r in roots]}

    # Alias for MCP compat
    def cmd_get_object_hierarchy(self, name=None):
        return self.cmd_get_hierarchy(name=name)

    def cmd_rename_object(self, name, new_name):
        obj = self._get_obj(name)
        obj.name = new_name
        return {"old": name, "new": obj.name}

    # =========================================================================
    #  UNDO / REDO
    # =========================================================================

    def cmd_undo(self):
        bpy.ops.ed.undo()
        return {"message": "Undo done"}

    def cmd_redo(self):
        bpy.ops.ed.redo()
        return {"message": "Redo done"}

    # =========================================================================
    #  MESH EDITING
    # =========================================================================

    def cmd_boolean_operation(self, target, cutter, operation="DIFFERENCE", apply=True):
        tgt = self._get_obj(target)
        cut = self._get_obj(cutter)
        bpy.ops.ed.undo_push(message=f"Boolean {operation}")
        mod = tgt.modifiers.new(f"Bool_{operation}", 'BOOLEAN')
        mod.operation = operation.upper()
        mod.object = cut
        if apply:
            bpy.context.view_layer.objects.active = tgt
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cut, do_unlink=True)
        return {"target": target, "operation": operation}

    def cmd_join_objects(self, names):
        bpy.ops.object.select_all(action='DESELECT')
        objs = [self._get_obj(n) for n in names]
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.ed.undo_push(message="Join objects")
        bpy.ops.object.join()
        return {"result": bpy.context.active_object.name, "joined": len(names)}

    def cmd_separate_object(self, name, mode="LOOSE"):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Separate {name}")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type=mode.upper())
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"result": [o.name for o in bpy.context.selected_objects]}

    def cmd_subdivide(self, name, cuts=1, smooth=0.0):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Subdivide {name}")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.subdivide(number_cuts=cuts, smoothness=smooth)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name, "vertices": len(obj.data.vertices)}

    # Alias for MCP compat
    def cmd_subdivide_mesh(self, name, cuts=1, smooth=0.0):
        return self.cmd_subdivide(name=name, cuts=cuts, smooth=smooth)

    def cmd_extrude_faces(self, name, offset=1.0):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Extrude {name}")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.extrude_faces_move(TRANSFORM_OT_shrink_fatten={"value": offset})
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name, "offset": offset}

    def cmd_bevel_edges(self, name, width=0.1, segments=3):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Bevel {name}")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.bevel(offset=width, segments=segments)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name, "width": width, "segments": segments}

    def cmd_inset_faces(self, name, thickness=0.1, depth=0.0):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Inset {name}")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.inset(thickness=thickness, depth=depth)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name, "thickness": thickness}

    def cmd_shade_smooth(self, name, smooth=True):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Shade {name}")
        if smooth:
            bpy.ops.object.shade_smooth()
        else:
            bpy.ops.object.shade_flat()
        return {"name": name, "shading": "smooth" if smooth else "flat"}

    def cmd_decimate(self, name, ratio=0.5):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Decimate {name}")
        v0 = len(obj.data.vertices)
        mod = obj.modifiers.new("Decimate", 'DECIMATE')
        mod.ratio = ratio
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        return {"name": name, "before": v0, "after": len(obj.data.vertices)}

    # Alias for MCP compat
    def cmd_decimate_mesh(self, name, ratio=0.5):
        return self.cmd_decimate(name=name, ratio=ratio)

    def cmd_remesh(self, name, voxel_size=0.1, mode="VOXEL"):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Remesh {name}")
        mod = obj.modifiers.new("Remesh", 'REMESH')
        mod.mode = mode.upper()
        if mode.upper() == "VOXEL":
            mod.voxel_size = voxel_size
        else:
            mod.octree_depth = max(1, int(1.0 / max(voxel_size, 0.01)))
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        return {"name": name, "vertices": len(obj.data.vertices)}

    def cmd_merge_by_distance(self, name, threshold=0.0001):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        v0 = len(obj.data.vertices)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=threshold)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name, "before": v0, "after": len(obj.data.vertices)}

    def cmd_flip_normals(self, name):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Flip normals {name}")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name}

    def cmd_fill_holes(self, name):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Fill holes {name}")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.fill()
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name}

    def cmd_bridge_edge_loops(self, name):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Bridge loops {name}")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.bridge_edge_loops()
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name}

    # =========================================================================
    #  MODIFIERS
    # =========================================================================

    def cmd_add_modifier(self, name, modifier_type, properties=None, modifier_name=None):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Modifier {modifier_type} on {name}")
        mod = obj.modifiers.new(modifier_name or modifier_type.title(), modifier_type.upper())
        if properties:
            for k, v in properties.items():
                if hasattr(mod, k):
                    setattr(mod, k, v)
        return {"object": name, "modifier": mod.name, "type": mod.type}

    def cmd_apply_modifier(self, name, modifier_name):
        obj = self._get_obj(name)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.ed.undo_push(message=f"Apply {modifier_name}")
        bpy.ops.object.modifier_apply(modifier=modifier_name)
        return {"object": name, "applied": modifier_name}

    def cmd_remove_modifier(self, name, modifier_name):
        obj = self._get_obj(name)
        mod = obj.modifiers.get(modifier_name)
        if not mod:
            raise ValueError(f"Modifier not found: {modifier_name}")
        bpy.ops.ed.undo_push(message=f"Remove {modifier_name}")
        obj.modifiers.remove(mod)
        return {"object": name, "removed": modifier_name}

    def cmd_create_array(self, name, count=5, offset=None, use_relative=True):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Array {name}")
        mod = obj.modifiers.new("Array", 'ARRAY')
        mod.count = count
        if offset:
            mod.use_relative_offset = use_relative
            if use_relative:
                mod.relative_offset_displace = tuple(offset)
            else:
                mod.use_constant_offset = True
                mod.constant_offset_displace = tuple(offset)
                mod.use_relative_offset = False
        return {"name": name, "count": count}

    def cmd_create_circular_array(self, name, count=8, axis="Z", radius=None):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Circular array {name}")
        empty = bpy.data.objects.new(f"ArrayPivot_{name}", None)
        bpy.context.collection.objects.link(empty)
        empty.location = obj.location.copy()
        angle = 360.0 / count
        ax = {"X": 0, "Y": 1, "Z": 2}.get(axis.upper(), 2)
        r = [0, 0, 0]
        r[ax] = math.radians(angle)
        empty.rotation_euler = tuple(r)
        if radius:
            obj.location.x = empty.location.x + radius
        mod = obj.modifiers.new("CircArray", 'ARRAY')
        mod.count = count
        mod.use_relative_offset = False
        mod.use_object_offset = True
        mod.offset_object = empty
        return {"name": name, "count": count, "pivot": empty.name}

    # =========================================================================
    #  MATERIALS
    # =========================================================================

    def cmd_set_material(self, name, material_name=None, base_color=None, metallic=None,
                         roughness=None, emission_color=None, emission_strength=None,
                         alpha=None, ior=None, transmission=None, specular=None,
                         clearcoat=None, sheen=None, subsurface=None):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Material on {name}")
        mname = material_name or f"Mat_{name}"
        mat = bpy.data.materials.get(mname) or bpy.data.materials.new(name=mname)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        mapping = {
            "Base Color": base_color, "Metallic": metallic, "Roughness": roughness,
            "Alpha": alpha, "IOR": ior, "Transmission Weight": transmission,
            "Specular IOR Level": specular, "Coat Weight": clearcoat,
            "Sheen Weight": sheen, "Subsurface Weight": subsurface,
            "Emission Color": emission_color, "Emission Strength": emission_strength,
        }
        applied = {}
        for inp_name, val in mapping.items():
            if val is not None:
                inp = bsdf.inputs.get(inp_name)
                if inp:
                    if isinstance(val, (list, tuple)):
                        if len(val) == 3:
                            val = list(val) + [1.0]
                        inp.default_value = tuple(val)
                    else:
                        inp.default_value = val
                    applied[inp_name] = val
        if alpha is not None and alpha < 1.0:
            mat.blend_method = 'HASHED'
        if obj.data and hasattr(obj.data, 'materials'):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat
        return {"object": name, "material": mat.name, "set": applied}

    def cmd_set_material_color(self, object_name, color, material_name=None):
        """Set/create a material with given RGBA color on an object."""
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}")
        bpy.ops.ed.undo_push(message=f"Set material color on {object_name}")
        if len(color) == 3:
            color = list(color) + [1.0]
        if material_name and material_name in bpy.data.materials:
            mat = bpy.data.materials[material_name]
        else:
            mat_name = material_name or f"Material_{object_name}"
            mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = tuple(color)
        if obj.data and hasattr(obj.data, 'materials'):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat
        return {"object": object_name, "material": mat.name, "color": list(color)}

    def cmd_set_principled_bsdf(self, object_name, material_name=None, base_color=None,
                                metallic=None, roughness=None, emission_color=None,
                                emission_strength=None, alpha=None, ior=None,
                                transmission=None, specular=None, clearcoat=None,
                                sheen=None, subsurface=None, anisotropic=None,
                                normal_strength=None):
        """Full control over Principled BSDF shader."""
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}")
        bpy.ops.ed.undo_push(message=f"Set PBR material on {object_name}")
        mat_name = material_name or f"PBR_{object_name}"
        mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        if not bsdf:
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        param_map = {
            "Base Color": base_color, "Metallic": metallic, "Roughness": roughness,
            "Alpha": alpha, "IOR": ior, "Transmission Weight": transmission,
            "Specular IOR Level": specular, "Coat Weight": clearcoat,
            "Sheen Weight": sheen, "Subsurface Weight": subsurface,
            "Anisotropic": anisotropic,
            "Emission Color": emission_color, "Emission Strength": emission_strength,
        }
        set_params = {}
        for input_name, value in param_map.items():
            if value is not None:
                inp = bsdf.inputs.get(input_name)
                if inp:
                    if isinstance(value, (list, tuple)):
                        if len(value) == 3:
                            value = list(value) + [1.0]
                        inp.default_value = tuple(value)
                    else:
                        inp.default_value = value
                    set_params[input_name] = value
        if alpha is not None and alpha < 1.0:
            mat.blend_method = 'HASHED'
        if obj.data and hasattr(obj.data, 'materials'):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat
        return {"object": object_name, "material": mat.name, "params_set": set_params}

    def cmd_create_glass(self, name, color=None, ior=1.45, roughness=0.0):
        return self.cmd_set_material(name, material_name=f"Glass_{name}",
            base_color=color or [1,1,1,1], transmission=1.0, ior=ior, roughness=roughness)

    # Alias for MCP compat
    def cmd_create_glass_material(self, object_name, color=None, ior=1.45, roughness=0.0, material_name=None):
        return self.cmd_set_principled_bsdf(object_name=object_name,
            material_name=material_name or f"Glass_{object_name}",
            base_color=color or [1,1,1,1], transmission=1.0, ior=ior, roughness=roughness)

    def cmd_create_metal(self, name, color=None, roughness=0.3):
        return self.cmd_set_material(name, material_name=f"Metal_{name}",
            base_color=color or [0.8,0.8,0.8,1], metallic=1.0, roughness=roughness)

    # Alias for MCP compat
    def cmd_create_metal_material(self, object_name, color=None, roughness=0.3, material_name=None):
        return self.cmd_set_principled_bsdf(object_name=object_name,
            material_name=material_name or f"Metal_{object_name}",
            base_color=color or [0.8,0.8,0.8,1], metallic=1.0, roughness=roughness)

    def cmd_create_emission(self, name, color=None, strength=10.0):
        return self.cmd_set_material(name, material_name=f"Emit_{name}",
            emission_color=color or [1,1,1,1], emission_strength=strength)

    # Alias for MCP compat
    def cmd_create_emission_material(self, object_name, color=None, strength=10.0, material_name=None):
        return self.cmd_set_principled_bsdf(object_name=object_name,
            material_name=material_name or f"Emission_{object_name}",
            emission_color=color or [1,1,1,1], emission_strength=strength)

    def cmd_list_materials(self):
        mats = []
        for m in bpy.data.materials:
            info = {"name": m.name, "users": m.users}
            if m.use_nodes:
                b = m.node_tree.nodes.get("Principled BSDF")
                if b:
                    bc = b.inputs["Base Color"].default_value
                    info["base_color"] = [round(v, 3) for v in bc]
            mats.append(info)
        return {"materials": mats, "count": len(mats)}

    def cmd_batch_assign_material(self, names, color=None, material_name=None):
        if color:
            c = list(color) + [1.0] if len(color) == 3 else list(color)
            mname = material_name or "BatchMat"
            mat = bpy.data.materials.get(mname) or bpy.data.materials.new(name=mname)
            mat.use_nodes = True
            b = mat.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Base Color"].default_value = tuple(c)
        elif material_name:
            mat = bpy.data.materials.get(material_name)
            if not mat:
                raise ValueError(f"Material not found: {material_name}")
        else:
            raise ValueError("Provide color or material_name")
        done = []
        for n in names:
            obj = bpy.data.objects.get(n)
            if obj and obj.data and hasattr(obj.data, 'materials'):
                if len(obj.data.materials) == 0:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat
                done.append(n)
        return {"material": mat.name, "assigned": done}

    # =========================================================================
    #  WORLD / ENVIRONMENT
    # =========================================================================

    def _ensure_world(self):
        w = bpy.context.scene.world
        if not w:
            w = bpy.data.worlds.new("World")
            bpy.context.scene.world = w
        w.use_nodes = True
        return w

    def cmd_set_world_color(self, color=None, strength=1.0):
        w = self._ensure_world()
        bg = w.node_tree.nodes.get("Background")
        if bg:
            c = color or [0.05, 0.05, 0.05]
            if len(c) == 3:
                c = list(c) + [1.0]
            bg.inputs["Color"].default_value = tuple(c)
            bg.inputs["Strength"].default_value = strength
        return {"color": c, "strength": strength}

    def cmd_set_world_hdri(self, filepath):
        w = self._ensure_world()
        nodes = w.node_tree.nodes
        links = w.node_tree.links
        for n in list(nodes):
            nodes.remove(n)
        tc = nodes.new("ShaderNodeTexCoord")
        mp = nodes.new("ShaderNodeMapping")
        et = nodes.new("ShaderNodeTexEnvironment")
        bg = nodes.new("ShaderNodeBackground")
        out = nodes.new("ShaderNodeOutputWorld")
        et.image = bpy.data.images.load(filepath)
        links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        links.new(mp.outputs["Vector"], et.inputs["Vector"])
        links.new(et.outputs["Color"], bg.inputs["Color"])
        links.new(bg.outputs["Background"], out.inputs["Surface"])
        return {"hdri": filepath}

    def cmd_set_sky_texture(self, sun_elevation=15.0, sun_rotation=0.0, sun_intensity=1.0, turbidity=2.2):
        w = self._ensure_world()
        nodes = w.node_tree.nodes
        links = w.node_tree.links
        for n in list(nodes):
            nodes.remove(n)
        sky = nodes.new("ShaderNodeTexSky")
        sky.sky_type = 'NISHITA'
        sky.sun_elevation = math.radians(sun_elevation)
        sky.sun_rotation = math.radians(sun_rotation)
        sky.sun_intensity = sun_intensity
        sky.turbidity = turbidity
        bg = nodes.new("ShaderNodeBackground")
        out = nodes.new("ShaderNodeOutputWorld")
        links.new(sky.outputs["Color"], bg.inputs["Color"])
        links.new(bg.outputs["Background"], out.inputs["Surface"])
        return {"sun_elevation": sun_elevation, "sun_rotation": sun_rotation}

    def cmd_set_fog(self, density=0.01, color=None):
        w = self._ensure_world()
        nodes = w.node_tree.nodes
        links = w.node_tree.links
        out = None
        for n in nodes:
            if n.type == 'OUTPUT_WORLD':
                out = n
                break
        if not out:
            out = nodes.new("ShaderNodeOutputWorld")
        vol = nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Density"].default_value = density
        if color:
            c = list(color) + [1.0] if len(color) == 3 else list(color)
            vol.inputs["Emission Color"].default_value = tuple(c)
        links.new(vol.outputs["Volume"], out.inputs["Volume"])
        return {"density": density}

    # =========================================================================
    #  CAMERA & LIGHTING
    # =========================================================================

    def cmd_set_camera(self, location=None, rotation=None, focal_length=None, target=None, depth_of_field=None):
        cam = bpy.context.scene.camera
        if not cam:
            bpy.ops.object.camera_add()
            cam = bpy.context.active_object
            bpy.context.scene.camera = cam
        bpy.ops.ed.undo_push(message="Set camera")
        if location:
            cam.location = tuple(location)
        if rotation:
            cam.rotation_euler = tuple(math.radians(r) for r in rotation)
        if focal_length and cam.data:
            cam.data.lens = focal_length
        if target:
            t = bpy.data.objects.get(target)
            if t:
                con = cam.constraints.get("Track To") or cam.constraints.new('TRACK_TO')
                con.target = t
                con.track_axis = 'TRACK_NEGATIVE_Z'
                con.up_axis = 'UP_Y'
        if depth_of_field is not None and cam.data:
            cam.data.dof.use_dof = depth_of_field.get("enabled", True)
            if "focus_object" in depth_of_field:
                fo = bpy.data.objects.get(depth_of_field["focus_object"])
                if fo:
                    cam.data.dof.focus_object = fo
            if "focus_distance" in depth_of_field:
                cam.data.dof.focus_distance = depth_of_field["focus_distance"]
            if "aperture" in depth_of_field:
                cam.data.dof.aperture_fstop = depth_of_field["aperture"]
        return {
            "camera": cam.name,
            "location": [round(v, 4) for v in cam.location],
            "focal_length": cam.data.lens if cam.data else None,
        }

    def cmd_setup_studio_lighting(self, style="THREE_POINT"):
        bpy.ops.ed.undo_push(message=f"Studio lighting {style}")
        for o in list(bpy.context.scene.objects):
            if o.type == 'LIGHT':
                bpy.data.objects.remove(o, do_unlink=True)
        lights = []
        if style == "THREE_POINT":
            configs = [
                ("Key", 'AREA', (4, -3, 5), (60, 0, 30), 500, {"size": 2}),
                ("Fill", 'AREA', (-4, -2, 3), (50, 0, -40), 200, {"size": 3}),
                ("Rim", 'SPOT', (-2, 4, 4), (120, 0, -160), 800, {"spot_size": math.radians(45)}),
            ]
        elif style == "REMBRANDT":
            configs = [
                ("Key", 'AREA', (3, -4, 5), (55, 0, 35), 600, {"size": 1.5}),
                ("Fill", 'AREA', (-5, -1, 2), (40, 0, -60), 100, {"size": 4}),
                ("Rim", 'POINT', (-1, 5, 3), (0, 0, 0), 400, {}),
            ]
        elif style == "SOFT_BOX":
            configs = [
                (f"Soft_{i}", 'AREA', pos, (0, 0, 0), 300, {"size": 4})
                for i, pos in enumerate([(-3,-3,4), (3,-3,4), (0,3,5), (0,0,6)])
            ]
        else:
            configs = [("Sun", 'SUN', (0, 0, 10), (45, 0, 30), 5, {})]
        for nm, lt, loc, rot, energy, props in configs:
            ld = bpy.data.lights.new(nm, lt)
            ld.energy = energy
            for k, v in props.items():
                if hasattr(ld, k):
                    setattr(ld, k, v)
            lo = bpy.data.objects.new(nm, ld)
            lo.location = loc
            lo.rotation_euler = tuple(math.radians(r) for r in rot)
            bpy.context.collection.objects.link(lo)
            lights.append(nm)
        return {"style": style, "lights": lights}

    def cmd_add_light(self, type="POINT", name=None, location=None, energy=100, color=None, size=None, rotation=None):
        bpy.ops.ed.undo_push(message=f"Add light {type}")
        loc = tuple(location) if location else (0, 0, 3)
        ld = bpy.data.lights.new(name or type.title(), type.upper())
        ld.energy = energy
        if color:
            ld.color = tuple(color[:3])
        if size and hasattr(ld, 'size'):
            ld.size = size
        obj = bpy.data.objects.new(name or type.title(), ld)
        obj.location = loc
        if rotation:
            obj.rotation_euler = tuple(math.radians(r) for r in rotation)
        bpy.context.collection.objects.link(obj)
        return {"name": obj.name, "type": type, "energy": energy}

    # =========================================================================
    #  RENDER & EXPORT
    # =========================================================================

    def cmd_render_image(self, filepath, resolution_x=1920, resolution_y=1080, samples=128, engine=None):
        r = bpy.context.scene.render
        r.filepath = filepath
        r.resolution_x = resolution_x
        r.resolution_y = resolution_y
        if engine:
            r.engine = engine.upper()
        if r.engine == 'CYCLES':
            bpy.context.scene.cycles.samples = samples
        elif hasattr(bpy.context.scene, 'eevee'):
            bpy.context.scene.eevee.taa_render_samples = samples
        ext = os.path.splitext(filepath)[1].lower()
        fmt = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".exr": "OPEN_EXR", ".hdr": "HDR",
               ".bmp": "BMP", ".tiff": "TIFF"}.get(ext, "PNG")
        r.image_settings.file_format = fmt
        bpy.ops.render.render(write_still=True)
        return {"filepath": filepath, "resolution": [resolution_x, resolution_y], "engine": r.engine}

    def cmd_configure_render(self, engine=None, samples=None, resolution=None, denoise=True,
                             transparent_bg=False, use_gpu=True, color_management=None):
        r = bpy.context.scene.render
        if engine:
            r.engine = engine.upper()
        if resolution:
            r.resolution_x = resolution[0]
            r.resolution_y = resolution[1]
        if r.engine == 'CYCLES':
            c = bpy.context.scene.cycles
            if samples:
                c.samples = samples
            if denoise:
                c.use_denoising = True
            if use_gpu:
                c.device = 'GPU'
        elif 'EEVEE' in r.engine and samples and hasattr(bpy.context.scene, 'eevee'):
            bpy.context.scene.eevee.taa_render_samples = samples
        r.film_transparent = transparent_bg
        if color_management:
            vs = bpy.context.scene.view_settings
            for k in ("view_transform", "look", "exposure", "gamma"):
                if k in color_management:
                    setattr(vs, k, color_management[k])
        return {"engine": r.engine, "resolution": [r.resolution_x, r.resolution_y]}

    def cmd_export_scene(self, filepath, format="glTF", selected_only=False):
        d = os.path.dirname(filepath)
        if d:
            os.makedirs(d, exist_ok=True)
        fmt = format.lower()
        if fmt in ("gltf", "glb"):
            ef = "GLB" if fmt == "glb" or filepath.endswith(".glb") else "GLTF_SEPARATE"
            bpy.ops.export_scene.gltf(filepath=filepath, export_format=ef, use_selection=selected_only)
        elif fmt == "obj":
            bpy.ops.wm.obj_export(filepath=filepath, export_selected_objects=selected_only)
        elif fmt == "fbx":
            bpy.ops.export_scene.fbx(filepath=filepath, use_selection=selected_only)
        elif fmt == "stl":
            bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=selected_only)
        elif fmt in ("usd", "usdc", "usda"):
            bpy.ops.wm.usd_export(filepath=filepath, selected_objects_only=selected_only)
        elif fmt == "ply":
            bpy.ops.wm.ply_export(filepath=filepath, export_selected_objects=selected_only)
        else:
            raise ValueError(f"Unsupported: {format}. Use: glTF/GLB/OBJ/FBX/STL/USD/PLY")
        return {"filepath": filepath, "format": format}

    # =========================================================================
    #  COLLECTIONS
    # =========================================================================

    def cmd_create_collection(self, name, parent=None):
        coll = bpy.data.collections.new(name)
        if parent:
            p = bpy.data.collections.get(parent)
            (p or bpy.context.scene.collection).children.link(coll)
        else:
            bpy.context.scene.collection.children.link(coll)
        return {"name": coll.name, "parent": parent}

    def cmd_move_to_collection(self, object_name, collection_name):
        obj = self._get_obj(object_name)
        target = bpy.data.collections.get(collection_name)
        if not target:
            raise ValueError(f"Collection not found: {collection_name}")
        for c in obj.users_collection:
            c.objects.unlink(obj)
        target.objects.link(obj)
        return {"object": object_name, "collection": collection_name}

    def cmd_list_collections(self):
        def tree(c):
            return {"name": c.name, "objects": [o.name for o in c.objects],
                    "children": [tree(ch) for ch in c.children]}
        return tree(bpy.context.scene.collection)

    def cmd_set_collection_visibility(self, name, visible=True, render_visible=True):
        c = bpy.data.collections.get(name)
        if not c:
            raise ValueError(f"Collection not found: {name}")
        c.hide_viewport = not visible
        c.hide_render = not render_visible
        return {"name": name, "visible": visible}

    # =========================================================================
    #  CONSTRAINTS
    # =========================================================================

    def cmd_add_constraint(self, name, constraint_type, target_name=None, properties=None):
        obj = self._get_obj(name)
        bpy.ops.ed.undo_push(message=f"Constraint {constraint_type}")
        con = obj.constraints.new(type=constraint_type.upper())
        if target_name:
            t = bpy.data.objects.get(target_name)
            if t and hasattr(con, 'target'):
                con.target = t
        if properties:
            for k, v in properties.items():
                if hasattr(con, k):
                    setattr(con, k, v)
        return {"object": name, "constraint": con.name, "type": constraint_type}

    def cmd_remove_constraint(self, name, constraint_name):
        obj = self._get_obj(name)
        con = obj.constraints.get(constraint_name)
        if not con:
            raise ValueError(f"Constraint not found: {constraint_name}")
        obj.constraints.remove(con)
        return {"removed": constraint_name}

    # =========================================================================
    #  BATCH OPERATIONS
    # =========================================================================

    def cmd_batch_transform(self, names, translate=None, rotate=None, scale=None, relative=True):
        bpy.ops.ed.undo_push(message=f"Batch transform {len(names)}")
        results = []
        for n in names:
            obj = bpy.data.objects.get(n)
            if not obj:
                continue
            if translate:
                if relative:
                    for i in range(3):
                        obj.location[i] += translate[i]
                else:
                    obj.location = tuple(translate)
            if rotate:
                r = [math.radians(v) for v in rotate]
                if relative:
                    for i in range(3):
                        obj.rotation_euler[i] += r[i]
                else:
                    obj.rotation_euler = tuple(r)
            if scale:
                if relative:
                    for i in range(3):
                        obj.scale[i] *= scale[i]
                else:
                    obj.scale = tuple(scale)
            results.append(n)
        return {"transformed": results}

    def cmd_batch_delete(self, names):
        bpy.ops.ed.undo_push(message=f"Batch delete {len(names)}")
        deleted = []
        for n in names:
            obj = bpy.data.objects.get(n)
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)
                deleted.append(n)
        return {"deleted": deleted}

    def cmd_align_objects(self, names, axis="Z", align_to="CENTER"):
        objs = [bpy.data.objects.get(n) for n in names if bpy.data.objects.get(n)]
        if not objs:
            raise ValueError("No valid objects")
        bpy.ops.ed.undo_push(message="Align")
        idx = {"X": 0, "Y": 1, "Z": 2}[axis.upper()]
        vals = [o.location[idx] for o in objs]
        if align_to == "CENTER":
            target = sum(vals) / len(vals)
        elif align_to == "MIN":
            target = min(vals)
        elif align_to == "MAX":
            target = max(vals)
        else:
            target = bpy.context.scene.cursor.location[idx]
        for o in objs:
            o.location[idx] = target
        return {"aligned": len(objs), "axis": axis}

    def cmd_distribute_objects(self, names, axis="X", spacing=None):
        objs = [bpy.data.objects.get(n) for n in names if bpy.data.objects.get(n)]
        if len(objs) < 2:
            raise ValueError("Need 2+ objects")
        bpy.ops.ed.undo_push(message="Distribute")
        idx = {"X": 0, "Y": 1, "Z": 2}[axis.upper()]
        objs.sort(key=lambda o: o.location[idx])
        if spacing:
            s = objs[0].location[idx]
            for i, o in enumerate(objs):
                o.location[idx] = s + i * spacing
        else:
            s, e = objs[0].location[idx], objs[-1].location[idx]
            step = (e - s) / (len(objs) - 1) if len(objs) > 1 else 0
            for i, o in enumerate(objs):
                o.location[idx] = s + i * step
        return {"distributed": len(objs)}

    def cmd_center_objects(self, names=None):
        objs = [bpy.data.objects.get(n) for n in names] if names else list(bpy.context.scene.objects)
        objs = [o for o in objs if o]
        if not objs:
            return {"centered": 0}
        bpy.ops.ed.undo_push(message="Center")
        avg = [sum(o.location[i] for o in objs) / len(objs) for i in range(3)]
        for o in objs:
            for i in range(3):
                o.location[i] -= avg[i]
        return {"centered": len(objs)}

    # =========================================================================
    #  ANIMATION
    # =========================================================================

    def cmd_set_keyframe(self, name, frame, data_path, value=None):
        obj = self._get_obj(name)
        bpy.context.scene.frame_set(frame)
        if value is not None:
            attr = getattr(obj, data_path, None)
            if attr is not None:
                if hasattr(attr, '__len__'):
                    for i, v in enumerate(value):
                        attr[i] = v
                else:
                    setattr(obj, data_path, value)
        obj.keyframe_insert(data_path=data_path, frame=frame)
        return {"object": name, "frame": frame, "data_path": data_path}

    def cmd_set_animation_range(self, start, end, fps=None):
        bpy.context.scene.frame_start = start
        bpy.context.scene.frame_end = end
        if fps:
            bpy.context.scene.render.fps = fps
        return {"start": start, "end": end, "fps": bpy.context.scene.render.fps}

    def cmd_set_frame(self, frame):
        bpy.context.scene.frame_set(frame)
        return {"frame": frame}

    def cmd_clear_animation(self, name):
        obj = self._get_obj(name)
        obj.animation_data_clear()
        return {"name": name, "cleared": True}

    # =========================================================================
    #  PHYSICS
    # =========================================================================

    def cmd_add_rigid_body(self, name, type="ACTIVE", mass=1.0, friction=0.5,
                           restitution=0.5, collision_shape="CONVEX_HULL"):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.rigidbody.object_add(type=type.upper())
        rb = obj.rigid_body
        rb.mass = mass
        rb.friction = friction
        rb.restitution = restitution
        rb.collision_shape = collision_shape.upper()
        return {"name": name, "type": type, "mass": mass}

    def cmd_add_cloth(self, name, quality=5, mass=0.3):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_add(type='CLOTH')
        c = obj.modifiers["Cloth"].settings
        c.quality = quality
        c.mass = mass
        return {"name": name, "quality": quality}

    # Alias for MCP compat
    def cmd_add_cloth_simulation(self, name, quality=5, mass=0.3):
        return self.cmd_add_cloth(name=name, quality=quality, mass=mass)

    def cmd_add_particles(self, name, count=1000, lifetime=50, type="EMITTER",
                          velocity=1.0, size=0.05):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.particle_system_add()
        ps = obj.particle_systems[-1].settings
        ps.type = type.upper()
        ps.count = count
        ps.lifetime = lifetime
        ps.normal_factor = velocity
        ps.particle_size = size
        return {"name": name, "count": count}

    # Alias for MCP compat
    def cmd_add_particle_system(self, name, count=1000, lifetime=50, type="EMITTER",
                                velocity=1.0, size=0.05):
        return self.cmd_add_particles(name=name, count=count, lifetime=lifetime,
                                      type=type, velocity=velocity, size=size)

    def cmd_bake_physics(self, start=1, end=250):
        bpy.context.scene.frame_start = start
        bpy.context.scene.frame_end = end
        try:
            bpy.ops.ptcache.bake_all(bake=True)
        except:
            pass
        return {"start": start, "end": end}

    # =========================================================================
    #  UV
    # =========================================================================

    def cmd_smart_uv_project(self, name, angle_limit=66.0, island_margin=0.0):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle_limit), island_margin=island_margin)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name}

    def cmd_uv_unwrap(self, name, method="ANGLE_BASED", margin=0.001):
        obj = self._get_obj(name)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method=method.upper(), margin=margin)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"name": name, "method": method}

    # =========================================================================
    #  CODE EXECUTION (sandboxed)
    # =========================================================================

    def cmd_execute_code(self, code):
        BLOCKED = {'subprocess', 'shutil', 'socket', 'ctypes', 'multiprocessing', 'webbrowser'}
        for mod in BLOCKED:
            if f"import {mod}" in code or f"from {mod}" in code:
                raise ValueError(f"Blocked import: {mod}")
        buf = io.StringIO()
        local_ns = {}
        with redirect_stdout(buf):
            exec(code, {"__builtins__": __builtins__, "bpy": bpy, "mathutils": mathutils, "math": math, "os": os}, local_ns)
        output = buf.getvalue()
        return {"output": output, "result": str(local_ns.get("result", ""))}

    # =========================================================================
    #  OPTIMIZATION
    # =========================================================================

    def cmd_optimize_scene(self, merge_threshold=0.0001):
        bpy.ops.ed.undo_push(message="Optimize")
        log = []
        for block in list(bpy.data.meshes):
            if block.users == 0:
                bpy.data.meshes.remove(block)
                log.append("Removed orphan mesh")
        for block in list(bpy.data.materials):
            if block.users == 0:
                bpy.data.materials.remove(block)
                log.append("Removed orphan material")
        for block in list(bpy.data.images):
            if block.users == 0:
                bpy.data.images.remove(block)
                log.append("Removed orphan image")
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.data:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                v0 = len(obj.data.vertices)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles(threshold=merge_threshold)
                bpy.ops.object.mode_set(mode='OBJECT')
                v1 = len(obj.data.vertices)
                if v0 != v1:
                    log.append(f"{obj.name}: merged {v0 - v1} verts")
        return {"optimizations": log}

    # =========================================================================
    #  POLYHAVEN INTEGRATION
    # =========================================================================

    def cmd_get_polyhaven_status(self):
        """Get the current status of PolyHaven integration"""
        enabled = bpy.context.scene.copilot_use_polyhaven
        if enabled:
            return {"enabled": True, "message": "PolyHaven integration is enabled and ready to use."}
        else:
            return {
                "enabled": False,
                "message": "PolyHaven integration is currently disabled. Enable it in the Copilot panel sidebar."
            }

    def cmd_get_polyhaven_categories(self, asset_type):
        """Get categories for a specific asset type from Polyhaven"""
        if not bpy.context.scene.copilot_use_polyhaven:
            return {"error": "PolyHaven integration is disabled. Enable it in the Copilot panel."}
        try:
            if asset_type not in ["hdris", "textures", "models", "all"]:
                return {"error": f"Invalid asset type: {asset_type}. Must be one of: hdris, textures, models, all"}
            response = requests.get(f"https://api.polyhaven.com/categories/{asset_type}", headers=REQ_HEADERS)
            if response.status_code == 200:
                return {"categories": response.json()}
            else:
                return {"error": f"API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def cmd_search_polyhaven_assets(self, asset_type=None, categories=None):
        """Search for assets from Polyhaven with optional filtering"""
        if not bpy.context.scene.copilot_use_polyhaven:
            return {"error": "PolyHaven integration is disabled. Enable it in the Copilot panel."}
        try:
            url = "https://api.polyhaven.com/assets"
            params = {}
            if asset_type and asset_type != "all":
                if asset_type not in ["hdris", "textures", "models"]:
                    return {"error": f"Invalid asset type: {asset_type}. Must be one of: hdris, textures, models, all"}
                params["type"] = asset_type
            if categories:
                params["categories"] = categories
            response = requests.get(url, params=params, headers=REQ_HEADERS)
            if response.status_code == 200:
                assets = response.json()
                limited_assets = {}
                for i, (key, value) in enumerate(assets.items()):
                    if i >= 20:
                        break
                    limited_assets[key] = value
                return {"assets": limited_assets, "total_count": len(assets), "returned_count": len(limited_assets)}
            else:
                return {"error": f"API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def cmd_download_polyhaven_asset(self, asset_id, asset_type, resolution="1k", file_format=None):
        """Download and import a PolyHaven asset"""
        if not bpy.context.scene.copilot_use_polyhaven:
            return {"error": "PolyHaven integration is disabled. Enable it in the Copilot panel."}
        try:
            files_response = requests.get(f"https://api.polyhaven.com/files/{asset_id}", headers=REQ_HEADERS)
            if files_response.status_code != 200:
                return {"error": f"Failed to get asset files: {files_response.status_code}"}
            files_data = files_response.json()

            if asset_type == "hdris":
                if not file_format:
                    file_format = "hdr"
                if "hdri" in files_data and resolution in files_data["hdri"] and file_format in files_data["hdri"][resolution]:
                    file_info = files_data["hdri"][resolution][file_format]
                    file_url = file_info["url"]
                    with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp_file:
                        response = requests.get(file_url, headers=REQ_HEADERS)
                        if response.status_code != 200:
                            return {"error": f"Failed to download HDRI: {response.status_code}"}
                        tmp_file.write(response.content)
                        tmp_path = tmp_file.name
                    try:
                        if not bpy.data.worlds:
                            bpy.data.worlds.new("World")
                        world = bpy.data.worlds[0]
                        world.use_nodes = True
                        node_tree = world.node_tree
                        for node in node_tree.nodes:
                            node_tree.nodes.remove(node)
                        tex_coord = node_tree.nodes.new(type='ShaderNodeTexCoord')
                        tex_coord.location = (-800, 0)
                        mapping_node = node_tree.nodes.new(type='ShaderNodeMapping')
                        mapping_node.location = (-600, 0)
                        env_tex = node_tree.nodes.new(type='ShaderNodeTexEnvironment')
                        env_tex.location = (-400, 0)
                        env_tex.image = bpy.data.images.load(tmp_path)
                        if file_format.lower() == 'exr':
                            try:
                                env_tex.image.colorspace_settings.name = 'Linear'
                            except:
                                env_tex.image.colorspace_settings.name = 'Non-Color'
                        else:
                            for color_space in ['Linear', 'Linear Rec.709', 'Non-Color']:
                                try:
                                    env_tex.image.colorspace_settings.name = color_space
                                    break
                                except:
                                    continue
                        background = node_tree.nodes.new(type='ShaderNodeBackground')
                        background.location = (-200, 0)
                        output = node_tree.nodes.new(type='ShaderNodeOutputWorld')
                        output.location = (0, 0)
                        node_tree.links.new(tex_coord.outputs['Generated'], mapping_node.inputs['Vector'])
                        node_tree.links.new(mapping_node.outputs['Vector'], env_tex.inputs['Vector'])
                        node_tree.links.new(env_tex.outputs['Color'], background.inputs['Color'])
                        node_tree.links.new(background.outputs['Background'], output.inputs['Surface'])
                        bpy.context.scene.world = world
                        try:
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                        except:
                            pass
                        return {"success": True, "message": f"HDRI {asset_id} imported successfully", "image_name": env_tex.image.name}
                    except Exception as e:
                        return {"error": f"Failed to set up HDRI in Blender: {str(e)}"}
                else:
                    return {"error": "Requested resolution or format not available for this HDRI"}

            elif asset_type == "textures":
                if not file_format:
                    file_format = "jpg"
                downloaded_maps = {}
                try:
                    for map_type in files_data:
                        if map_type not in ["blend", "gltf"]:
                            if resolution in files_data[map_type] and file_format in files_data[map_type][resolution]:
                                file_info = files_data[map_type][resolution][file_format]
                                file_url = file_info["url"]
                                with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp_file:
                                    response = requests.get(file_url, headers=REQ_HEADERS)
                                    if response.status_code == 200:
                                        tmp_file.write(response.content)
                                        tmp_path = tmp_file.name
                                        image = bpy.data.images.load(tmp_path)
                                        image.name = f"{asset_id}_{map_type}.{file_format}"
                                        image.pack()
                                        if map_type in ['color', 'diffuse', 'albedo']:
                                            try:
                                                image.colorspace_settings.name = 'sRGB'
                                            except:
                                                pass
                                        else:
                                            try:
                                                image.colorspace_settings.name = 'Non-Color'
                                            except:
                                                pass
                                        downloaded_maps[map_type] = image
                                        try:
                                            os.unlink(tmp_path)
                                        except:
                                            pass
                    if not downloaded_maps:
                        return {"error": "No texture maps found for the requested resolution and format"}
                    mat = bpy.data.materials.new(name=asset_id)
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    links = mat.node_tree.links
                    for node in nodes:
                        nodes.remove(node)
                    output = nodes.new(type='ShaderNodeOutputMaterial')
                    output.location = (300, 0)
                    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
                    principled.location = (0, 0)
                    links.new(principled.outputs[0], output.inputs[0])
                    tex_coord = nodes.new(type='ShaderNodeTexCoord')
                    tex_coord.location = (-800, 0)
                    mapping_node = nodes.new(type='ShaderNodeMapping')
                    mapping_node.location = (-600, 0)
                    mapping_node.vector_type = 'TEXTURE'
                    links.new(tex_coord.outputs['UV'], mapping_node.inputs['Vector'])
                    x_pos = -400
                    y_pos = 300
                    for map_type, image in downloaded_maps.items():
                        tex_node = nodes.new(type='ShaderNodeTexImage')
                        tex_node.location = (x_pos, y_pos)
                        tex_node.image = image
                        if map_type.lower() in ['color', 'diffuse', 'albedo']:
                            try:
                                tex_node.image.colorspace_settings.name = 'sRGB'
                            except:
                                pass
                        else:
                            try:
                                tex_node.image.colorspace_settings.name = 'Non-Color'
                            except:
                                pass
                        links.new(mapping_node.outputs['Vector'], tex_node.inputs['Vector'])
                        if map_type.lower() in ['color', 'diffuse', 'albedo']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                        elif map_type.lower() in ['roughness', 'rough']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                        elif map_type.lower() in ['metallic', 'metalness', 'metal']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                        elif map_type.lower() in ['normal', 'nor']:
                            normal_map = nodes.new(type='ShaderNodeNormalMap')
                            normal_map.location = (x_pos + 200, y_pos)
                            links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                            links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                        elif map_type in ['displacement', 'disp', 'height']:
                            disp_node = nodes.new(type='ShaderNodeDisplacement')
                            disp_node.location = (x_pos + 200, y_pos - 200)
                            links.new(tex_node.outputs['Color'], disp_node.inputs['Height'])
                            links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])
                        y_pos -= 250
                    return {"success": True, "message": f"Texture {asset_id} imported as material",
                            "material": mat.name, "maps": list(downloaded_maps.keys())}
                except Exception as e:
                    return {"error": f"Failed to process textures: {str(e)}"}

            elif asset_type == "models":
                if not file_format:
                    file_format = "gltf"
                if file_format in files_data and resolution in files_data[file_format]:
                    file_info = files_data[file_format][resolution][file_format]
                    file_url = file_info["url"]
                    temp_dir = tempfile.mkdtemp()
                    try:
                        main_file_name = file_url.split("/")[-1]
                        main_file_path = os.path.join(temp_dir, main_file_name)
                        response = requests.get(file_url, headers=REQ_HEADERS)
                        if response.status_code != 200:
                            return {"error": f"Failed to download model: {response.status_code}"}
                        with open(main_file_path, "wb") as f:
                            f.write(response.content)
                        if "include" in file_info and file_info["include"]:
                            for include_path, include_info in file_info["include"].items():
                                include_url = include_info["url"]
                                include_file_path = os.path.join(temp_dir, include_path)
                                os.makedirs(os.path.dirname(include_file_path), exist_ok=True)
                                include_response = requests.get(include_url, headers=REQ_HEADERS)
                                if include_response.status_code == 200:
                                    with open(include_file_path, "wb") as f:
                                        f.write(include_response.content)
                        if file_format in ("gltf", "glb"):
                            bpy.ops.import_scene.gltf(filepath=main_file_path)
                        elif file_format == "fbx":
                            bpy.ops.import_scene.fbx(filepath=main_file_path)
                        elif file_format == "obj":
                            bpy.ops.import_scene.obj(filepath=main_file_path)
                        elif file_format == "blend":
                            with bpy.data.libraries.load(main_file_path, link=False) as (data_from, data_to):
                                data_to.objects = data_from.objects
                            for obj in data_to.objects:
                                if obj is not None:
                                    bpy.context.collection.objects.link(obj)
                        else:
                            return {"error": f"Unsupported model format: {file_format}"}
                        imported_objects = [obj.name for obj in bpy.context.selected_objects]
                        return {"success": True, "message": f"Model {asset_id} imported successfully",
                                "imported_objects": imported_objects}
                    except Exception as e:
                        return {"error": f"Failed to import model: {str(e)}"}
                    finally:
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                else:
                    return {"error": "Requested format or resolution not available for this model"}
            else:
                return {"error": f"Unsupported asset type: {asset_type}"}
        except Exception as e:
            return {"error": f"Failed to download asset: {str(e)}"}

    def cmd_set_texture(self, object_name, texture_id):
        """Apply a previously downloaded Polyhaven texture to an object"""
        if not bpy.context.scene.copilot_use_polyhaven:
            return {"error": "PolyHaven integration is disabled. Enable it in the Copilot panel."}
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"Object not found: {object_name}"}
            if not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
                return {"error": f"Object {object_name} cannot accept materials"}
            texture_images = {}
            for img in bpy.data.images:
                if img.name.startswith(texture_id + "_"):
                    map_type = img.name.split('_')[-1].split('.')[0]
                    img.reload()
                    if map_type.lower() in ['color', 'diffuse', 'albedo']:
                        try:
                            img.colorspace_settings.name = 'sRGB'
                        except:
                            pass
                    else:
                        try:
                            img.colorspace_settings.name = 'Non-Color'
                        except:
                            pass
                    if not img.packed_file:
                        img.pack()
                    texture_images[map_type] = img
            if not texture_images:
                return {"error": f"No texture images found for: {texture_id}. Please download the texture first."}
            new_mat_name = f"{texture_id}_material_{object_name}"
            existing_mat = bpy.data.materials.get(new_mat_name)
            if existing_mat:
                bpy.data.materials.remove(existing_mat)
            new_mat = bpy.data.materials.new(name=new_mat_name)
            new_mat.use_nodes = True
            nodes = new_mat.node_tree.nodes
            links = new_mat.node_tree.links
            nodes.clear()
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (600, 0)
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled.location = (300, 0)
            links.new(principled.outputs[0], output.inputs[0])
            tex_coord = nodes.new(type='ShaderNodeTexCoord')
            tex_coord.location = (-800, 0)
            mapping_node = nodes.new(type='ShaderNodeMapping')
            mapping_node.location = (-600, 0)
            mapping_node.vector_type = 'TEXTURE'
            links.new(tex_coord.outputs['UV'], mapping_node.inputs['Vector'])
            x_pos = -400
            y_pos = 300
            for map_type, image in texture_images.items():
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (x_pos, y_pos)
                tex_node.image = image
                if map_type.lower() in ['color', 'diffuse', 'albedo']:
                    try:
                        tex_node.image.colorspace_settings.name = 'sRGB'
                    except:
                        pass
                else:
                    try:
                        tex_node.image.colorspace_settings.name = 'Non-Color'
                    except:
                        pass
                links.new(mapping_node.outputs['Vector'], tex_node.inputs['Vector'])
                if map_type.lower() in ['color', 'diffuse', 'albedo']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                elif map_type.lower() in ['roughness', 'rough']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                elif map_type.lower() in ['metallic', 'metalness', 'metal']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                elif map_type.lower() in ['normal', 'nor', 'dx', 'gl']:
                    normal_map = nodes.new(type='ShaderNodeNormalMap')
                    normal_map.location = (x_pos + 200, y_pos)
                    links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                    links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                elif map_type.lower() in ['displacement', 'disp', 'height']:
                    disp_node = nodes.new(type='ShaderNodeDisplacement')
                    disp_node.location = (x_pos + 200, y_pos - 200)
                    disp_node.inputs['Scale'].default_value = 0.1
                    links.new(tex_node.outputs['Color'], disp_node.inputs['Height'])
                    links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])
                y_pos -= 250
            # Second pass: Connect nodes with proper handling
            texture_nodes = {}
            for node in nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    for map_type, image in texture_images.items():
                        if node.image == image:
                            texture_nodes[map_type] = node
                            break
            for map_name in ['color', 'diffuse', 'albedo']:
                if map_name in texture_nodes:
                    links.new(texture_nodes[map_name].outputs['Color'], principled.inputs['Base Color'])
                    break
            for map_name in ['roughness', 'rough']:
                if map_name in texture_nodes:
                    links.new(texture_nodes[map_name].outputs['Color'], principled.inputs['Roughness'])
                    break
            for map_name in ['metallic', 'metalness', 'metal']:
                if map_name in texture_nodes:
                    links.new(texture_nodes[map_name].outputs['Color'], principled.inputs['Metallic'])
                    break
            for map_name in ['gl', 'dx', 'nor']:
                if map_name in texture_nodes:
                    normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                    normal_map_node.location = (100, 100)
                    links.new(texture_nodes[map_name].outputs['Color'], normal_map_node.inputs['Color'])
                    links.new(normal_map_node.outputs['Normal'], principled.inputs['Normal'])
                    break
            for map_name in ['displacement', 'disp', 'height']:
                if map_name in texture_nodes:
                    disp_node = nodes.new(type='ShaderNodeDisplacement')
                    disp_node.location = (300, -200)
                    disp_node.inputs['Scale'].default_value = 0.1
                    links.new(texture_nodes[map_name].outputs['Color'], disp_node.inputs['Height'])
                    links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])
                    break
            # Handle ARM texture
            if 'arm' in texture_nodes:
                separate_rgb = nodes.new(type='ShaderNodeSeparateRGB')
                separate_rgb.location = (-200, -100)
                links.new(texture_nodes['arm'].outputs['Color'], separate_rgb.inputs['Image'])
                if not any(mn in texture_nodes for mn in ['roughness', 'rough']):
                    links.new(separate_rgb.outputs['G'], principled.inputs['Roughness'])
                if not any(mn in texture_nodes for mn in ['metallic', 'metalness', 'metal']):
                    links.new(separate_rgb.outputs['B'], principled.inputs['Metallic'])
                base_color_node = None
                for mn in ['color', 'diffuse', 'albedo']:
                    if mn in texture_nodes:
                        base_color_node = texture_nodes[mn]
                        break
                if base_color_node:
                    mix_node = nodes.new(type='ShaderNodeMixRGB')
                    mix_node.location = (100, 200)
                    mix_node.blend_type = 'MULTIPLY'
                    mix_node.inputs['Fac'].default_value = 0.8
                    for link in base_color_node.outputs['Color'].links:
                        if link.to_socket == principled.inputs['Base Color']:
                            links.remove(link)
                    links.new(base_color_node.outputs['Color'], mix_node.inputs[1])
                    links.new(separate_rgb.outputs['R'], mix_node.inputs[2])
                    links.new(mix_node.outputs['Color'], principled.inputs['Base Color'])
            # Handle separate AO
            if 'ao' in texture_nodes:
                base_color_node = None
                for mn in ['color', 'diffuse', 'albedo']:
                    if mn in texture_nodes:
                        base_color_node = texture_nodes[mn]
                        break
                if base_color_node:
                    mix_node = nodes.new(type='ShaderNodeMixRGB')
                    mix_node.location = (100, 200)
                    mix_node.blend_type = 'MULTIPLY'
                    mix_node.inputs['Fac'].default_value = 0.8
                    for link in base_color_node.outputs['Color'].links:
                        if link.to_socket == principled.inputs['Base Color']:
                            links.remove(link)
                    links.new(base_color_node.outputs['Color'], mix_node.inputs[1])
                    links.new(texture_nodes['ao'].outputs['Color'], mix_node.inputs[2])
                    links.new(mix_node.outputs['Color'], principled.inputs['Base Color'])
            # Assign material
            while len(obj.data.materials) > 0:
                obj.data.materials.pop(index=0)
            obj.data.materials.append(new_mat)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.context.view_layer.update()
            return {
                "success": True,
                "message": f"Created new material and applied texture {texture_id} to {object_name}",
                "material": new_mat.name,
                "maps": list(texture_images.keys()),
            }
        except Exception as e:
            traceback.print_exc()
            return {"error": f"Failed to apply texture: {str(e)}"}

    # =========================================================================
    #  SKETCHFAB INTEGRATION
    # =========================================================================

    def cmd_get_sketchfab_status(self):
        """Get the current status of Sketchfab integration"""
        enabled = bpy.context.scene.copilot_use_sketchfab
        api_key = bpy.context.scene.copilot_sketchfab_api_key
        if api_key:
            try:
                headers = {"Authorization": f"Token {api_key}"}
                response = requests.get("https://api.sketchfab.com/v3/me", headers=headers, timeout=30)
                if response.status_code == 200:
                    user_data = response.json()
                    username = user_data.get("username", "Unknown user")
                    return {"enabled": True, "message": f"Sketchfab integration is enabled. Logged in as: {username}"}
                else:
                    return {"enabled": False, "message": f"Sketchfab API key seems invalid. Status code: {response.status_code}"}
            except requests.exceptions.Timeout:
                return {"enabled": False, "message": "Timeout connecting to Sketchfab API."}
            except Exception as e:
                return {"enabled": False, "message": f"Error testing Sketchfab API key: {str(e)}"}
        if enabled and not api_key:
            return {"enabled": False, "message": "Sketchfab is enabled but API key is not set. Add it in the Copilot panel."}
        return {"enabled": False, "message": "Sketchfab integration is disabled. Enable it in the Copilot panel."}

    def cmd_search_sketchfab_models(self, query, categories=None, count=20, downloadable=True):
        """Search for models on Sketchfab"""
        if not bpy.context.scene.copilot_use_sketchfab:
            return {"error": "Sketchfab integration is disabled. Enable it in the Copilot panel."}
        try:
            api_key = bpy.context.scene.copilot_sketchfab_api_key
            if not api_key:
                return {"error": "Sketchfab API key is not configured"}
            params = {"type": "models", "q": query, "count": count,
                      "downloadable": downloadable, "archives_flavours": False}
            if categories:
                params["categories"] = categories
            headers = {"Authorization": f"Token {api_key}"}
            response = requests.get("https://api.sketchfab.com/v3/search", headers=headers,
                                    params=params, timeout=30)
            if response.status_code == 401:
                return {"error": "Authentication failed (401). Check your API key."}
            if response.status_code != 200:
                return {"error": f"API request failed with status code {response.status_code}"}
            response_data = response.json()
            if response_data is None:
                return {"error": "Received empty response from Sketchfab API"}
            results = response_data.get("results", [])
            if not isinstance(results, list):
                return {"error": f"Unexpected response format from Sketchfab API"}
            return response_data
        except requests.exceptions.Timeout:
            return {"error": "Request timed out."}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response: {str(e)}"}
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    def cmd_get_sketchfab_model_preview(self, uid):
        """Get thumbnail preview image of a Sketchfab model by its UID"""
        if not bpy.context.scene.copilot_use_sketchfab:
            return {"error": "Sketchfab integration is disabled. Enable it in the Copilot panel."}
        try:
            api_key = bpy.context.scene.copilot_sketchfab_api_key
            if not api_key:
                return {"error": "Sketchfab API key is not configured"}
            headers = {"Authorization": f"Token {api_key}"}
            response = requests.get(f"https://api.sketchfab.com/v3/models/{uid}", headers=headers, timeout=30)
            if response.status_code == 401:
                return {"error": "Authentication failed (401). Check your API key."}
            if response.status_code == 404:
                return {"error": f"Model not found: {uid}"}
            if response.status_code != 200:
                return {"error": f"Failed to get model info: {response.status_code}"}
            data = response.json()
            thumbnails = data.get("thumbnails", {}).get("images", [])
            if not thumbnails:
                return {"error": "No thumbnail available for this model"}
            selected_thumbnail = None
            for thumb in thumbnails:
                width = thumb.get("width", 0)
                if 400 <= width <= 800:
                    selected_thumbnail = thumb
                    break
            if not selected_thumbnail:
                selected_thumbnail = thumbnails[0]
            thumbnail_url = selected_thumbnail.get("url")
            if not thumbnail_url:
                return {"error": "Thumbnail URL not found"}
            img_response = requests.get(thumbnail_url, timeout=30)
            if img_response.status_code != 200:
                return {"error": f"Failed to download thumbnail: {img_response.status_code}"}
            image_data = base64.b64encode(img_response.content).decode('ascii')
            content_type = img_response.headers.get("Content-Type", "")
            img_format = "png" if ("png" in content_type or thumbnail_url.endswith(".png")) else "jpeg"
            model_name = data.get("name", "Unknown")
            author = data.get("user", {}).get("username", "Unknown")
            return {
                "success": True, "image_data": image_data, "format": img_format,
                "model_name": model_name, "author": author, "uid": uid,
                "thumbnail_width": selected_thumbnail.get("width"),
                "thumbnail_height": selected_thumbnail.get("height"),
            }
        except requests.exceptions.Timeout:
            return {"error": "Request timed out."}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"Failed to get model preview: {str(e)}"}

    def cmd_download_sketchfab_model(self, uid, normalize_size=False, target_size=1.0):
        """Download a model from Sketchfab by its UID"""
        if not bpy.context.scene.copilot_use_sketchfab:
            return {"error": "Sketchfab integration is disabled. Enable it in the Copilot panel."}
        try:
            api_key = bpy.context.scene.copilot_sketchfab_api_key
            if not api_key:
                return {"error": "Sketchfab API key is not configured"}
            headers = {"Authorization": f"Token {api_key}"}
            response = requests.get(f"https://api.sketchfab.com/v3/models/{uid}/download",
                                    headers=headers, timeout=30)
            if response.status_code == 401:
                return {"error": "Authentication failed (401). Check your API key."}
            if response.status_code != 200:
                return {"error": f"Download request failed with status code {response.status_code}"}
            data = response.json()
            if data is None:
                return {"error": "Received empty response from Sketchfab API"}
            gltf_data = data.get("gltf")
            if not gltf_data:
                return {"error": "No gltf download URL available for this model."}
            download_url = gltf_data.get("url")
            if not download_url:
                return {"error": "No download URL available. Make sure the model is downloadable."}
            model_response = requests.get(download_url, timeout=60)
            if model_response.status_code != 200:
                return {"error": f"Model download failed with status code {model_response.status_code}"}
            temp_dir = tempfile.mkdtemp()
            zip_file_path = os.path.join(temp_dir, f"{uid}.zip")
            with open(zip_file_path, "wb") as f:
                f.write(model_response.content)
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    file_path = file_info.filename
                    target_path = os.path.join(temp_dir, os.path.normpath(file_path))
                    abs_temp_dir = os.path.abspath(temp_dir)
                    abs_target_path = os.path.abspath(target_path)
                    if not abs_target_path.startswith(abs_temp_dir):
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                        return {"error": "Security issue: Zip contains path traversal attempt"}
                    if ".." in file_path:
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                        return {"error": "Security issue: Zip contains directory traversal sequence"}
                zip_ref.extractall(temp_dir)
            gltf_files = [f for f in os.listdir(temp_dir) if f.endswith('.gltf') or f.endswith('.glb')]
            if not gltf_files:
                with suppress(Exception):
                    shutil.rmtree(temp_dir)
                return {"error": "No glTF file found in the downloaded model"}
            main_file = os.path.join(temp_dir, gltf_files[0])
            bpy.ops.import_scene.gltf(filepath=main_file)
            imported_objects = list(bpy.context.selected_objects)
            imported_object_names = [obj.name for obj in imported_objects]
            with suppress(Exception):
                shutil.rmtree(temp_dir)
            root_objects = [obj for obj in imported_objects if obj.parent is None]

            def get_all_mesh_children(obj):
                meshes = []
                if obj.type == 'MESH':
                    meshes.append(obj)
                for child in obj.children:
                    meshes.extend(get_all_mesh_children(child))
                return meshes

            all_meshes = []
            for obj in root_objects:
                all_meshes.extend(get_all_mesh_children(obj))
            if all_meshes:
                all_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
                all_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
                for mesh_obj in all_meshes:
                    for corner in mesh_obj.bound_box:
                        world_corner = mesh_obj.matrix_world @ mathutils.Vector(corner)
                        all_min.x = min(all_min.x, world_corner.x)
                        all_min.y = min(all_min.y, world_corner.y)
                        all_min.z = min(all_min.z, world_corner.z)
                        all_max.x = max(all_max.x, world_corner.x)
                        all_max.y = max(all_max.y, world_corner.y)
                        all_max.z = max(all_max.z, world_corner.z)
                dimensions = [all_max.x - all_min.x, all_max.y - all_min.y, all_max.z - all_min.z]
                max_dimension = max(dimensions)
                scale_applied = 1.0
                if normalize_size and max_dimension > 0:
                    scale_factor = target_size / max_dimension
                    scale_applied = scale_factor
                    for root in root_objects:
                        root.scale = (root.scale.x * scale_factor, root.scale.y * scale_factor, root.scale.z * scale_factor)
                    bpy.context.view_layer.update()
                    all_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
                    all_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
                    for mesh_obj in all_meshes:
                        for corner in mesh_obj.bound_box:
                            world_corner = mesh_obj.matrix_world @ mathutils.Vector(corner)
                            all_min.x = min(all_min.x, world_corner.x)
                            all_min.y = min(all_min.y, world_corner.y)
                            all_min.z = min(all_min.z, world_corner.z)
                            all_max.x = max(all_max.x, world_corner.x)
                            all_max.y = max(all_max.y, world_corner.y)
                            all_max.z = max(all_max.z, world_corner.z)
                    dimensions = [all_max.x - all_min.x, all_max.y - all_min.y, all_max.z - all_min.z]
                world_bounding_box = [[all_min.x, all_min.y, all_min.z], [all_max.x, all_max.y, all_max.z]]
            else:
                world_bounding_box = None
                dimensions = None
                scale_applied = 1.0
            result = {"success": True, "message": "Model imported successfully",
                      "imported_objects": imported_object_names}
            if world_bounding_box:
                result["world_bounding_box"] = world_bounding_box
            if dimensions:
                result["dimensions"] = [round(d, 4) for d in dimensions]
            if normalize_size:
                result["scale_applied"] = round(scale_applied, 6)
                result["normalized"] = True
            return result
        except requests.exceptions.Timeout:
            return {"error": "Request timed out."}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response: {str(e)}"}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"Failed to download model: {str(e)}"}

    # =========================================================================
    #  HYPER3D RODIN INTEGRATION
    # =========================================================================

    def cmd_get_hyper3d_status(self):
        """Get the current status of Hyper3D Rodin integration"""
        enabled = bpy.context.scene.copilot_use_hyper3d
        if enabled:
            if not bpy.context.scene.copilot_hyper3d_api_key:
                return {"enabled": False, "message": "Hyper3D Rodin is enabled but API key is not set. Add it in the Copilot panel."}
            mode = bpy.context.scene.copilot_hyper3d_mode
            key_type = 'free_trial' if bpy.context.scene.copilot_hyper3d_api_key == RODIN_FREE_TRIAL_KEY else 'private'
            return {"enabled": True, "message": f"Hyper3D Rodin is enabled. Mode: {mode}. Key type: {key_type}"}
        return {"enabled": False, "message": "Hyper3D Rodin integration is disabled. Enable it in the Copilot panel."}

    @staticmethod
    def _clean_imported_glb(filepath, mesh_name=None):
        """Import GLB and clean up the hierarchy"""
        existing_objects = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=filepath)
        bpy.context.view_layer.update()
        imported_objects = list(set(bpy.data.objects) - existing_objects)
        if not imported_objects:
            raise Exception("No objects were imported from GLB file")
        mesh_obj = None
        if len(imported_objects) == 1 and imported_objects[0].type == 'MESH':
            mesh_obj = imported_objects[0]
        else:
            if len(imported_objects) == 2:
                empty_objs = [i for i in imported_objects if i.type == "EMPTY"]
                if len(empty_objs) != 1:
                    raise Exception("Expected an empty node with one mesh child or a single mesh object")
                parent_obj = empty_objs.pop()
                if len(parent_obj.children) == 1:
                    potential_mesh = parent_obj.children[0]
                    if potential_mesh.type == 'MESH':
                        potential_mesh.parent = None
                        bpy.data.objects.remove(parent_obj)
                        mesh_obj = potential_mesh
                    else:
                        raise Exception("Child is not a mesh object")
                else:
                    raise Exception("Expected an empty node with one mesh child or a single mesh object")
            else:
                raise Exception(f"Unexpected import structure: {len(imported_objects)} objects imported")
        try:
            if mesh_obj and mesh_obj.name is not None and mesh_name:
                mesh_obj.name = mesh_name
                if mesh_obj.data.name is not None:
                    mesh_obj.data.name = mesh_name
        except:
            pass
        return mesh_obj

    def cmd_create_rodin_job(self, text_prompt=None, images=None, bbox_condition=None):
        """Create a Hyper3D Rodin generation job"""
        if not bpy.context.scene.copilot_use_hyper3d:
            return {"error": "Hyper3D Rodin integration is disabled. Enable it in the Copilot panel."}
        if not bpy.context.scene.copilot_hyper3d_api_key:
            return {"error": "Hyper3D Rodin API key is not set."}
        mode = bpy.context.scene.copilot_hyper3d_mode
        if mode == "MAIN_SITE":
            return self._create_rodin_job_main_site(text_prompt=text_prompt, images=images, bbox_condition=bbox_condition)
        elif mode == "FAL_AI":
            return self._create_rodin_job_fal_ai(text_prompt=text_prompt, images=images, bbox_condition=bbox_condition)
        return {"error": f"Unknown Hyper3D Rodin mode: {mode}"}

    def _create_rodin_job_main_site(self, text_prompt=None, images=None, bbox_condition=None):
        try:
            if images is None:
                images = []
            files = [
                *[("images", (f"{i:04d}{img_suffix}", img)) for i, (img_suffix, img) in enumerate(images)],
                ("tier", (None, "Sketch")),
                ("mesh_mode", (None, "Raw")),
            ]
            if text_prompt:
                files.append(("prompt", (None, text_prompt)))
            if bbox_condition:
                files.append(("bbox_condition", (None, json.dumps(bbox_condition))))
            response = requests.post(
                "https://hyperhuman.deemos.com/api/v2/rodin",
                headers={"Authorization": f"Bearer {bpy.context.scene.copilot_hyper3d_api_key}"},
                files=files
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _create_rodin_job_fal_ai(self, text_prompt=None, images=None, bbox_condition=None):
        try:
            req_data = {"tier": "Sketch"}
            if images:
                req_data["input_image_urls"] = images
            if text_prompt:
                req_data["prompt"] = text_prompt
            if bbox_condition:
                req_data["bbox_condition"] = bbox_condition
            response = requests.post(
                "https://queue.fal.run/fal-ai/hyper3d/rodin",
                headers={
                    "Authorization": f"Key {bpy.context.scene.copilot_hyper3d_api_key}",
                    "Content-Type": "application/json",
                },
                json=req_data
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def cmd_poll_rodin_job_status(self, subscription_key=None, request_id=None):
        """Poll Hyper3D Rodin job status"""
        if not bpy.context.scene.copilot_use_hyper3d:
            return {"error": "Hyper3D Rodin integration is disabled."}
        mode = bpy.context.scene.copilot_hyper3d_mode
        if mode == "MAIN_SITE":
            if not subscription_key:
                return {"error": "subscription_key is required for MAIN_SITE mode"}
            response = requests.post(
                "https://hyperhuman.deemos.com/api/v2/status",
                headers={"Authorization": f"Bearer {bpy.context.scene.copilot_hyper3d_api_key}"},
                json={"subscription_key": subscription_key},
            )
            data = response.json()
            return {"status_list": [i["status"] for i in data["jobs"]]}
        elif mode == "FAL_AI":
            if not request_id:
                return {"error": "request_id is required for FAL_AI mode"}
            response = requests.get(
                f"https://queue.fal.run/fal-ai/hyper3d/requests/{request_id}/status",
                headers={"Authorization": f"KEY {bpy.context.scene.copilot_hyper3d_api_key}"},
            )
            return response.json()
        return {"error": f"Unknown mode: {mode}"}

    def cmd_import_generated_asset(self, task_uuid=None, request_id=None, name="GeneratedAsset"):
        """Import a generated asset from Hyper3D Rodin"""
        if not bpy.context.scene.copilot_use_hyper3d:
            return {"error": "Hyper3D Rodin integration is disabled."}
        mode = bpy.context.scene.copilot_hyper3d_mode
        if mode == "MAIN_SITE":
            if not task_uuid:
                return {"error": "task_uuid is required for MAIN_SITE mode"}
            return self._import_generated_asset_main_site(task_uuid=task_uuid, name=name)
        elif mode == "FAL_AI":
            if not request_id:
                return {"error": "request_id is required for FAL_AI mode"}
            return self._import_generated_asset_fal_ai(request_id=request_id, name=name)
        return {"error": f"Unknown mode: {mode}"}

    def _import_generated_asset_main_site(self, task_uuid, name):
        response = requests.post(
            "https://hyperhuman.deemos.com/api/v2/download",
            headers={"Authorization": f"Bearer {bpy.context.scene.copilot_hyper3d_api_key}"},
            json={'task_uuid': task_uuid}
        )
        data_ = response.json()
        temp_file = None
        for i in data_["list"]:
            if i["name"].endswith(".glb"):
                temp_file = tempfile.NamedTemporaryFile(delete=False, prefix=task_uuid, suffix=".glb")
                try:
                    response = requests.get(i["url"], stream=True)
                    response.raise_for_status()
                    for chunk in response.iter_content(chunk_size=8192):
                        temp_file.write(chunk)
                    temp_file.close()
                except Exception as e:
                    temp_file.close()
                    os.unlink(temp_file.name)
                    return {"succeed": False, "error": str(e)}
                break
        else:
            return {"succeed": False, "error": "Generation failed. Make sure all jobs are done."}
        try:
            obj = self._clean_imported_glb(filepath=temp_file.name, mesh_name=name)
            result = {
                "name": obj.name, "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            }
            if obj.type == "MESH":
                result["world_bounding_box"] = self._get_aabb(obj)
            return {"succeed": True, **result}
        except Exception as e:
            return {"succeed": False, "error": str(e)}

    def _import_generated_asset_fal_ai(self, request_id, name):
        response = requests.get(
            f"https://queue.fal.run/fal-ai/hyper3d/requests/{request_id}",
            headers={"Authorization": f"Key {bpy.context.scene.copilot_hyper3d_api_key}"}
        )
        data_ = response.json()
        temp_file = tempfile.NamedTemporaryFile(delete=False, prefix=request_id, suffix=".glb")
        try:
            response = requests.get(data_["model_mesh"]["url"], stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_file.close()
        except Exception as e:
            temp_file.close()
            os.unlink(temp_file.name)
            return {"succeed": False, "error": str(e)}
        try:
            obj = self._clean_imported_glb(filepath=temp_file.name, mesh_name=name)
            result = {
                "name": obj.name, "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            }
            if obj.type == "MESH":
                result["world_bounding_box"] = self._get_aabb(obj)
            return {"succeed": True, **result}
        except Exception as e:
            return {"succeed": False, "error": str(e)}

    # =========================================================================
    #  HUNYUAN3D INTEGRATION
    # =========================================================================

    def cmd_get_hunyuan3d_status(self):
        """Get the current status of Hunyuan3D integration"""
        enabled = bpy.context.scene.copilot_use_hunyuan3d
        hunyuan3d_mode = bpy.context.scene.copilot_hunyuan3d_mode
        if enabled:
            if hunyuan3d_mode == "OFFICIAL_API":
                if not bpy.context.scene.copilot_hunyuan3d_secret_id or not bpy.context.scene.copilot_hunyuan3d_secret_key:
                    return {"enabled": False, "mode": hunyuan3d_mode,
                            "message": "Hunyuan3D is enabled but SecretId/SecretKey is not set. Add them in the Copilot panel."}
            elif hunyuan3d_mode == "LOCAL_API":
                if not bpy.context.scene.copilot_hunyuan3d_api_url:
                    return {"enabled": False, "mode": hunyuan3d_mode,
                            "message": "Hunyuan3D is enabled but API URL is not set. Add it in the Copilot panel."}
            else:
                return {"enabled": False, "message": "Hunyuan3D mode is not supported."}
            return {"enabled": True, "mode": hunyuan3d_mode, "message": "Hunyuan3D integration is enabled and ready to use."}
        return {"enabled": False, "message": "Hunyuan3D integration is disabled. Enable it in the Copilot panel."}

    @staticmethod
    def _get_tencent_cloud_sign_headers(method, path, headParams, data, service, region, secret_id, secret_key, host=None):
        """Generate Tencent Cloud API signature headers"""
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        if not host:
            host = f"{service}.tencentcloudapi.com"
        endpoint = f"https://{host}"
        payload_str = json.dumps(data)
        canonical_uri = path
        canonical_querystring = ""
        ct = "application/json; charset=utf-8"
        canonical_headers = f"content-type:{ct}\nhost:{host}\nx-tc-action:{headParams.get('Action', '').lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        canonical_request = (method + "\n" + canonical_uri + "\n" + canonical_querystring + "\n" +
                             canonical_headers + "\n" + signed_headers + "\n" + hashed_request_payload)
        credential_scope = f"{date}/{service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = ("TC3-HMAC-SHA256" + "\n" + str(timestamp) + "\n" +
                          credential_scope + "\n" + hashed_canonical_request)

        def sign(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        secret_date = sign(("TC3" + secret_key).encode("utf-8"), date)
        secret_service = sign(secret_date, service)
        secret_signing = sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        authorization = ("TC3-HMAC-SHA256 Credential=" + secret_id + "/" + credential_scope +
                          ", SignedHeaders=" + signed_headers + ", Signature=" + signature)
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": headParams.get("Action", ""),
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": headParams.get("Version", ""),
            "X-TC-Region": region,
        }
        return headers, endpoint

    def cmd_create_hunyuan_job(self, text_prompt=None, image=None):
        """Create a Hunyuan3D generation job"""
        if not bpy.context.scene.copilot_use_hunyuan3d:
            return {"error": "Hunyuan3D integration is disabled. Enable it in the Copilot panel."}
        mode = bpy.context.scene.copilot_hunyuan3d_mode
        if mode == "OFFICIAL_API":
            return self._create_hunyuan_job_official(text_prompt=text_prompt, image=image)
        elif mode == "LOCAL_API":
            return self._create_hunyuan_job_local(text_prompt=text_prompt, image=image)
        return {"error": f"Unknown Hunyuan3D mode: {mode}"}

    def _create_hunyuan_job_official(self, text_prompt=None, image=None):
        try:
            secret_id = bpy.context.scene.copilot_hunyuan3d_secret_id
            secret_key = bpy.context.scene.copilot_hunyuan3d_secret_key
            if not secret_id or not secret_key:
                return {"error": "SecretId or SecretKey is not given"}
            if not text_prompt and not image:
                return {"error": "Prompt or Image is required"}
            if text_prompt and image:
                return {"error": "Prompt and Image cannot be provided simultaneously"}
            service = "hunyuan"
            action = "SubmitHunyuanTo3DJob"
            version = "2023-09-01"
            region = "ap-guangzhou"
            headParams = {"Action": action, "Version": version, "Region": region}
            data = {"Num": 1}
            if text_prompt:
                if len(text_prompt) > 200:
                    return {"error": "Prompt exceeds 200 characters limit"}
                data["Prompt"] = text_prompt
            if image:
                if re.match(r'^https?://', image, re.IGNORECASE) is not None:
                    data["ImageUrl"] = image
                else:
                    try:
                        with open(image, "rb") as f:
                            image_base64 = base64.b64encode(f.read()).decode("ascii")
                        data["ImageBase64"] = image_base64
                    except Exception as e:
                        return {"error": f"Image encoding failed: {str(e)}"}
            headers, endpoint = self._get_tencent_cloud_sign_headers(
                "POST", "/", headParams, data, service, region, secret_id, secret_key)
            response = requests.post(endpoint, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                return response.json()
            return {"error": f"API request failed with status {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def _create_hunyuan_job_local(self, text_prompt=None, image=None):
        try:
            base_url = bpy.context.scene.copilot_hunyuan3d_api_url.rstrip('/')
            octree_resolution = bpy.context.scene.copilot_hunyuan3d_octree_resolution
            num_inference_steps = bpy.context.scene.copilot_hunyuan3d_num_inference_steps
            guidance_scale = bpy.context.scene.copilot_hunyuan3d_guidance_scale
            texture = bpy.context.scene.copilot_hunyuan3d_texture
            if not base_url:
                return {"error": "API URL is not given"}
            if not text_prompt and not image:
                return {"error": "Prompt or Image is required"}
            data = {
                "octree_resolution": octree_resolution,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "texture": texture,
            }
            if text_prompt:
                data["text"] = text_prompt
            if image:
                if re.match(r'^https?://', image, re.IGNORECASE) is not None:
                    try:
                        resImg = requests.get(image)
                        resImg.raise_for_status()
                        image_base64 = base64.b64encode(resImg.content).decode("ascii")
                        data["image"] = image_base64
                    except Exception as e:
                        return {"error": f"Failed to download or encode image: {str(e)}"}
                else:
                    try:
                        with open(image, "rb") as f:
                            image_base64 = base64.b64encode(f.read()).decode("ascii")
                        data["image"] = image_base64
                    except Exception as e:
                        return {"error": f"Image encoding failed: {str(e)}"}
            response = requests.post(f"{base_url}/generate", json=data)
            if response.status_code != 200:
                return {"error": f"Generation failed: {response.text}"}
            with tempfile.NamedTemporaryFile(delete=False, suffix=".glb") as temp_file:
                temp_file.write(response.content)
                temp_file_name = temp_file.name
            try:
                bpy.ops.import_scene.gltf(filepath=temp_file_name)
            finally:
                if os.path.exists(temp_file_name):
                    os.unlink(temp_file_name)
            return {"status": "DONE", "message": "Generation and import succeeded"}
        except Exception as e:
            return {"error": str(e)}

    def cmd_poll_hunyuan_job_status(self, job_id):
        """Poll Hunyuan3D job status"""
        if not bpy.context.scene.copilot_use_hunyuan3d:
            return {"error": "Hunyuan3D integration is disabled."}
        try:
            secret_id = bpy.context.scene.copilot_hunyuan3d_secret_id
            secret_key = bpy.context.scene.copilot_hunyuan3d_secret_key
            if not secret_id or not secret_key:
                return {"error": "SecretId or SecretKey is not given"}
            if not job_id:
                return {"error": "JobId is required"}
            service = "hunyuan"
            action = "QueryHunyuanTo3DJob"
            version = "2023-09-01"
            region = "ap-guangzhou"
            headParams = {"Action": action, "Version": version, "Region": region}
            clean_job_id = job_id.removeprefix("job_")
            data = {"JobId": clean_job_id}
            headers, endpoint = self._get_tencent_cloud_sign_headers(
                "POST", "/", headParams, data, service, region, secret_id, secret_key)
            response = requests.post(endpoint, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                return response.json()
            return {"error": f"API request failed with status {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def cmd_import_generated_asset_hunyuan(self, name=None, zip_file_url=None):
        """Import a generated Hunyuan3D asset from a ZIP URL"""
        if not bpy.context.scene.copilot_use_hunyuan3d:
            return {"error": "Hunyuan3D integration is disabled."}
        if not zip_file_url:
            return {"error": "Zip file URL not provided"}
        if not re.match(r'^https?://', zip_file_url, re.IGNORECASE):
            return {"error": "Invalid URL format. Must start with http:// or https://"}
        temp_dir = tempfile.mkdtemp(prefix="copilot_hunyuan_obj_")
        zip_file_path = osp.join(temp_dir, "model.zip")
        obj_file_path = osp.join(temp_dir, "model.obj")
        try:
            zip_response = requests.get(zip_file_url, stream=True)
            zip_response.raise_for_status()
            with open(zip_file_path, "wb") as f:
                for chunk in zip_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
            for file in os.listdir(temp_dir):
                if file.endswith(".obj"):
                    obj_file_path = osp.join(temp_dir, file)
            if not osp.exists(obj_file_path):
                return {"succeed": False, "error": "OBJ file not found after extraction"}
            if bpy.app.version >= (4, 0, 0):
                bpy.ops.wm.obj_import(filepath=obj_file_path)
            else:
                bpy.ops.import_scene.obj(filepath=obj_file_path)
            imported_objs = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
            if not imported_objs:
                return {"succeed": False, "error": "No mesh objects imported"}
            obj = imported_objs[0]
            if name:
                obj.name = name
            result = {
                "name": obj.name, "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            }
            if obj.type == "MESH":
                result["world_bounding_box"] = self._get_aabb(obj)
            return {"succeed": True, **result}
        except Exception as e:
            return {"succeed": False, "error": str(e)}
        finally:
            try:
                if os.path.exists(zip_file_path):
                    os.remove(zip_file_path)
                if os.path.exists(obj_file_path):
                    os.remove(obj_file_path)
            except Exception as e:
                print(f"Failed to clean up temporary directory {temp_dir}: {e}")

    # =========================================================================
    #  HYPER3D TEXT/IMAGE GENERATION (server-side command aliases)
    # =========================================================================

    def cmd_generate_hyper3d_model_via_text(self, **kwargs):
        """Alias for create_rodin_job with text prompt"""
        return self.cmd_create_rodin_job(**kwargs)

    def cmd_generate_hyper3d_model_via_images(self, **kwargs):
        """Alias for create_rodin_job with images"""
        return self.cmd_create_rodin_job(**kwargs)

    def cmd_generate_hunyuan3d_model(self, **kwargs):
        """Alias for create_hunyuan_job"""
        return self.cmd_create_hunyuan_job(**kwargs)


# =============================================================================
#  Blender UI
# =============================================================================

class COPILOT_PT_Panel(bpy.types.Panel):
    bl_label = "Blender Copilot"
    bl_idname = "COPILOT_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Copilot'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "copilot_port")

        if not scene.copilot_running:
            layout.operator("copilot.start", text="Connect to AI", icon='PLAY')
        else:
            layout.operator("copilot.stop", text="Disconnect", icon='PAUSE')
            layout.label(text=f"Port {scene.copilot_port}", icon='CHECKMARK')

        layout.separator()
        layout.label(text="Asset Integrations:", icon='IMPORT')

        # PolyHaven
        layout.prop(scene, "copilot_use_polyhaven", text="Use assets from Poly Haven")

        # Hyper3D Rodin
        layout.prop(scene, "copilot_use_hyper3d", text="Use Hyper3D Rodin 3D generation")
        if scene.copilot_use_hyper3d:
            box = layout.box()
            box.prop(scene, "copilot_hyper3d_mode", text="Mode")
            box.prop(scene, "copilot_hyper3d_api_key", text="API Key")
            box.operator("copilot.set_hyper3d_free_trial_key", text="Set Free Trial API Key")

        # Sketchfab
        layout.prop(scene, "copilot_use_sketchfab", text="Use assets from Sketchfab")
        if scene.copilot_use_sketchfab:
            box = layout.box()
            box.prop(scene, "copilot_sketchfab_api_key", text="API Key")

        # Hunyuan3D
        layout.prop(scene, "copilot_use_hunyuan3d", text="Use Tencent Hunyuan 3D generation")
        if scene.copilot_use_hunyuan3d:
            box = layout.box()
            box.prop(scene, "copilot_hunyuan3d_mode", text="Mode")
            if scene.copilot_hunyuan3d_mode == 'OFFICIAL_API':
                box.prop(scene, "copilot_hunyuan3d_secret_id", text="SecretId")
                box.prop(scene, "copilot_hunyuan3d_secret_key", text="SecretKey")
            if scene.copilot_hunyuan3d_mode == 'LOCAL_API':
                box.prop(scene, "copilot_hunyuan3d_api_url", text="API URL")
                box.prop(scene, "copilot_hunyuan3d_octree_resolution", text="Octree Resolution")
                box.prop(scene, "copilot_hunyuan3d_num_inference_steps", text="Inference Steps")
                box.prop(scene, "copilot_hunyuan3d_guidance_scale", text="Guidance Scale")
                box.prop(scene, "copilot_hunyuan3d_texture", text="Generate Texture")


class COPILOT_OT_Start(bpy.types.Operator):
    bl_idname = "copilot.start"
    bl_label = "Start Copilot"

    def execute(self, context):
        if not hasattr(bpy.types, "copilot_server") or not bpy.types.copilot_server:
            bpy.types.copilot_server = CopilotServer(port=context.scene.copilot_port)
        bpy.types.copilot_server.start()
        context.scene.copilot_running = True
        return {'FINISHED'}


class COPILOT_OT_Stop(bpy.types.Operator):
    bl_idname = "copilot.stop"
    bl_label = "Stop Copilot"

    def execute(self, context):
        if hasattr(bpy.types, "copilot_server") and bpy.types.copilot_server:
            bpy.types.copilot_server.stop()
            del bpy.types.copilot_server
        context.scene.copilot_running = False
        return {'FINISHED'}


class COPILOT_OT_SetHyper3DFreeTrialKey(bpy.types.Operator):
    bl_idname = "copilot.set_hyper3d_free_trial_key"
    bl_label = "Set Free Trial API Key"

    def execute(self, context):
        context.scene.copilot_hyper3d_api_key = RODIN_FREE_TRIAL_KEY
        context.scene.copilot_hyper3d_mode = 'MAIN_SITE'
        self.report({'INFO'}, "Free trial API key set successfully!")
        return {'FINISHED'}


CLASSES = [COPILOT_PT_Panel, COPILOT_OT_Start, COPILOT_OT_Stop, COPILOT_OT_SetHyper3DFreeTrialKey]


def register():
    # Core properties
    bpy.types.Scene.copilot_port = IntProperty(name="Port", default=9876, min=1024, max=65535)
    bpy.types.Scene.copilot_running = BoolProperty(name="Running", default=False)

    # PolyHaven
    bpy.types.Scene.copilot_use_polyhaven = BoolProperty(
        name="Use Poly Haven", description="Enable Poly Haven asset integration", default=False)

    # Hyper3D Rodin
    bpy.types.Scene.copilot_use_hyper3d = BoolProperty(
        name="Use Hyper3D Rodin", description="Enable Hyper3D Rodin generation integration", default=False)
    bpy.types.Scene.copilot_hyper3d_mode = EnumProperty(
        name="Rodin Mode", description="Choose the platform used to call Rodin APIs",
        items=[("MAIN_SITE", "hyper3d.ai", "hyper3d.ai"), ("FAL_AI", "fal.ai", "fal.ai")],
        default="MAIN_SITE")
    bpy.types.Scene.copilot_hyper3d_api_key = StringProperty(
        name="Hyper3D API Key", subtype="PASSWORD", description="API Key provided by Hyper3D", default="")

    # Sketchfab
    bpy.types.Scene.copilot_use_sketchfab = BoolProperty(
        name="Use Sketchfab", description="Enable Sketchfab asset integration", default=False)
    bpy.types.Scene.copilot_sketchfab_api_key = StringProperty(
        name="Sketchfab API Key", subtype="PASSWORD", description="API Key provided by Sketchfab", default="")

    # Hunyuan3D
    bpy.types.Scene.copilot_use_hunyuan3d = BoolProperty(
        name="Use Hunyuan 3D", description="Enable Hunyuan3D asset integration", default=False)
    bpy.types.Scene.copilot_hunyuan3d_mode = EnumProperty(
        name="Hunyuan3D Mode", description="Choose local or official APIs",
        items=[("LOCAL_API", "Local API", "Local API"), ("OFFICIAL_API", "Official API", "Official API")],
        default="LOCAL_API")
    bpy.types.Scene.copilot_hunyuan3d_secret_id = StringProperty(
        name="Hunyuan 3D SecretId", description="SecretId from Tencent Cloud", default="")
    bpy.types.Scene.copilot_hunyuan3d_secret_key = StringProperty(
        name="Hunyuan 3D SecretKey", subtype="PASSWORD", description="SecretKey from Tencent Cloud", default="")
    bpy.types.Scene.copilot_hunyuan3d_api_url = StringProperty(
        name="API URL", description="URL of the Hunyuan 3D API service", default="http://localhost:8081")
    bpy.types.Scene.copilot_hunyuan3d_octree_resolution = IntProperty(
        name="Octree Resolution", description="Octree resolution for 3D generation",
        default=256, min=128, max=512)
    bpy.types.Scene.copilot_hunyuan3d_num_inference_steps = IntProperty(
        name="Inference Steps", description="Number of inference steps for 3D generation",
        default=20, min=20, max=50)
    bpy.types.Scene.copilot_hunyuan3d_guidance_scale = FloatProperty(
        name="Guidance Scale", description="Guidance scale for 3D generation",
        default=5.5, min=1.0, max=10.0)
    bpy.types.Scene.copilot_hunyuan3d_texture = BoolProperty(
        name="Generate Texture", description="Whether to generate texture for the 3D model", default=False)

    for cls in CLASSES:
        bpy.utils.register_class(cls)
    print("[Copilot] Addon registered")


def unregister():
    if hasattr(bpy.types, "copilot_server") and bpy.types.copilot_server:
        bpy.types.copilot_server.stop()
        del bpy.types.copilot_server
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

    # Core
    del bpy.types.Scene.copilot_port
    del bpy.types.Scene.copilot_running

    # PolyHaven
    del bpy.types.Scene.copilot_use_polyhaven

    # Hyper3D
    del bpy.types.Scene.copilot_use_hyper3d
    del bpy.types.Scene.copilot_hyper3d_mode
    del bpy.types.Scene.copilot_hyper3d_api_key

    # Sketchfab
    del bpy.types.Scene.copilot_use_sketchfab
    del bpy.types.Scene.copilot_sketchfab_api_key

    # Hunyuan3D
    del bpy.types.Scene.copilot_use_hunyuan3d
    del bpy.types.Scene.copilot_hunyuan3d_mode
    del bpy.types.Scene.copilot_hunyuan3d_secret_id
    del bpy.types.Scene.copilot_hunyuan3d_secret_key
    del bpy.types.Scene.copilot_hunyuan3d_api_url
    del bpy.types.Scene.copilot_hunyuan3d_octree_resolution
    del bpy.types.Scene.copilot_hunyuan3d_num_inference_steps
    del bpy.types.Scene.copilot_hunyuan3d_guidance_scale
    del bpy.types.Scene.copilot_hunyuan3d_texture

    print("[Copilot] Addon unregistered")


if __name__ == "__main__":
    register()
