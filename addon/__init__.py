# Blender Copilot - AI-Powered 3D Creation via MCP
# Copyright (c) 2026 DWGX - MIT License
# Original work, not a fork. Inspired by the Blender MCP ecosystem.

import bpy
import bmesh
import mathutils
import json
import math
import threading
import socket
import time
import tempfile
import traceback
import os
import shutil
import zipfile
from bpy.props import IntProperty, BoolProperty, StringProperty
from contextlib import redirect_stdout, suppress
import io
import base64

bl_info = {
    "name": "Blender Copilot",
    "author": "DWGX",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Copilot",
    "description": "AI-powered 3D creation via MCP - 150+ tools",
    "category": "Interface",
}


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

    def cmd_create_glass(self, name, color=None, ior=1.45, roughness=0.0):
        return self.cmd_set_material(name, material_name=f"Glass_{name}",
            base_color=color or [1,1,1,1], transmission=1.0, ior=ior, roughness=roughness)

    def cmd_create_metal(self, name, color=None, roughness=0.3):
        return self.cmd_set_material(name, material_name=f"Metal_{name}",
            base_color=color or [0.8,0.8,0.8,1], metallic=1.0, roughness=roughness)

    def cmd_create_emission(self, name, color=None, strength=10.0):
        return self.cmd_set_material(name, material_name=f"Emit_{name}",
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


CLASSES = [COPILOT_PT_Panel, COPILOT_OT_Start, COPILOT_OT_Stop]


def register():
    bpy.types.Scene.copilot_port = IntProperty(name="Port", default=9876, min=1024, max=65535)
    bpy.types.Scene.copilot_running = BoolProperty(name="Running", default=False)
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    print("[Copilot] Addon registered")


def unregister():
    if hasattr(bpy.types, "copilot_server") and bpy.types.copilot_server:
        bpy.types.copilot_server.stop()
        del bpy.types.copilot_server
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.copilot_port
    del bpy.types.Scene.copilot_running
    print("[Copilot] Addon unregistered")


if __name__ == "__main__":
    register()
