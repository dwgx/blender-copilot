"""
DWGX Catgirl Avatar — Direct Blender build script.
Run via: blender --python scripts/build_dwgx_direct.py

Bypasses TCP entirely. Creates full base mesh in Blender's own Python context.
After building, starts the MCP addon server for continued AI interaction.
"""
import bpy
import bmesh
import math
import os
import sys

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants — 5-head loli proportions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
H = 0.22          # head unit (total height ~1.1m = 5 * H)
HEAD_R = 0.14     # head sphere radius
HEAD_Z = H * 7.9 + HEAD_R * 0.6   # head center Z
BODY_SEGS = 12    # body ring segments
LIMB_SEGS = 8     # ear/tail/arm segments

print("\n" + "=" * 60)
print("  DWGX Catgirl Avatar Builder — Direct Mode")
print("=" * 60)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 0: Clean scene & create collections
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[0/8] Cleaning scene...")

# Remove all objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=True)

# Remove non-default collections
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)

# Purge orphan data
bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

# Create collections
collection_names = ["Body", "Head", "Hair", "Ears_Tail", "Eyes", "Outfit", "Lighting"]
for name in collection_names:
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    print(f"  Collection: {name}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper: ring of verts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def make_ring(bm, center_x, center_y, center_z, radius_x, radius_y, num_segs):
    """Create a ring of vertices in the XY plane at given Z."""
    verts = []
    for i in range(num_segs):
        a = 2 * math.pi * i / num_segs
        v = bm.verts.new((center_x + radius_x * math.cos(a),
                          center_y + radius_y * math.sin(a),
                          center_z))
        verts.append(v)
    return verts


def bridge_rings(bm, ring_a, ring_b, num_segs):
    """Connect two rings with quad faces."""
    for j in range(num_segs):
        jn = (j + 1) % num_segs
        try:
            bm.faces.new([ring_a[j], ring_a[jn], ring_b[jn], ring_b[j]])
        except Exception:
            pass


def finalize_mesh(bm, mesh, obj_name, collection_name, subdiv=1):
    """Apply bmesh to mesh, create object, smooth shade, add subsurf."""
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(obj_name, mesh)
    bpy.data.collections[collection_name].objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    if subdiv > 0:
        obj.modifiers.new("SS", "SUBSURF").levels = subdiv
    obj.select_set(False)
    return obj


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 1: Body torso
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[1/8] Building body torso...")

mesh_body = bpy.data.meshes.new("Body_mesh")
bm = bmesh.new()

# Profile: (z_height, width_x, depth_y) — loli proportions
body_profile = [
    (0.00,  0.040, 0.040),   # feet
    (0.05,  0.050, 0.050),   # ankle
    (0.20,  0.055, 0.055),   # calf
    (0.35,  0.060, 0.060),   # knee
    (0.38,  0.062, 0.065),   # above knee
    (0.42,  0.060, 0.060),   # lower thigh
    (0.55,  0.080, 0.080),   # upper thigh
    (0.65,  0.100, 0.100),   # hip joint
    (H*4,   0.100, 0.120),   # pelvis
    (H*4+0.06, 0.110, 0.130),  # waist low
    (H*4.5, 0.100, 0.110),   # waist
    (H*5.3, 0.080, 0.090),   # underbust
    (H*5.6, 0.090, 0.100),   # bust
    (H*6.0, 0.100, 0.110),   # chest
    (H*6.4, 0.110, 0.120),   # upper chest
    (H*6.6, 0.100, 0.110),   # shoulders low
    (H*7.0, 0.120, 0.100),   # shoulders
    (H*7.4, 0.060, 0.050),   # neck base
    (H*7.7, 0.045, 0.040),   # neck mid
    (H*7.9, 0.040, 0.038),   # neck top
]

body_rings = []
for z, w, d in body_profile:
    ring = make_ring(bm, 0, 0, z, w, d, BODY_SEGS)
    body_rings.append(ring)

bm.verts.ensure_lookup_table()

for i in range(len(body_rings) - 1):
    bridge_rings(bm, body_rings[i], body_rings[i + 1], BODY_SEGS)

# Cap bottom
try:
    bm.faces.new(list(reversed(body_rings[0])))
except Exception:
    pass

body_obj = finalize_mesh(bm, mesh_body, "Body", "Body", subdiv=1)
print(f"  Body: {len(mesh_body.vertices)}v, {len(mesh_body.polygons)}f")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 2: Head
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[2/8] Building head...")

bpy.ops.mesh.primitive_uv_sphere_add(
    radius=HEAD_R, segments=16, ring_count=12,
    location=(0, 0, HEAD_Z)
)
head = bpy.context.active_object
head.name = "Head"
# Move to Head collection
for c in head.users_collection:
    c.objects.unlink(head)
bpy.data.collections["Head"].objects.link(head)
bpy.ops.object.shade_smooth()
# Slightly wider, less deep — anime proportions
head.scale = (1.08, 0.92, 0.96)
bpy.ops.object.transform_apply(scale=True)
print(f"  Head: {len(head.data.vertices)}v at Z={HEAD_Z:.3f}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 3: Cat Ears
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[3/8] Building cat ears...")

EAR_Z = HEAD_Z + 0.10

def make_ear(side):
    name = "Ear_L" if side > 0 else "Ear_R"
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    xo = side * 0.08  # offset from center

    # Tapered ear layers: (z, width, depth, center_x)
    ear_layers = [
        (EAR_Z,        0.040, 0.025, xo),
        (EAR_Z + 0.05, 0.032, 0.018, xo + side * 0.01),
        (EAR_Z + 0.10, 0.020, 0.012, xo + side * 0.02),
        (EAR_Z + 0.14, 0.010, 0.006, xo + side * 0.025),
    ]

    rings = []
    for z, w, d, cx in ear_layers:
        ring = make_ring(bm, cx, 0, z, w, d, LIMB_SEGS)
        rings.append(ring)

    # Ear tip
    tip = bm.verts.new((xo + side * 0.03, 0, EAR_Z + 0.16))
    bm.verts.ensure_lookup_table()

    # Bridge layers
    for i in range(len(rings) - 1):
        bridge_rings(bm, rings[i], rings[i + 1], LIMB_SEGS)

    # Top cone to tip
    for j in range(LIMB_SEGS):
        jn = (j + 1) % LIMB_SEGS
        try:
            bm.faces.new([rings[-1][j], rings[-1][jn], tip])
        except Exception:
            pass

    # Cap bottom
    try:
        bm.faces.new(list(reversed(rings[0])))
    except Exception:
        pass

    obj = finalize_mesh(bm, mesh, name, "Ears_Tail", subdiv=2)
    print(f"  {name}: {len(mesh.vertices)}v")
    return obj

ear_l = make_ear(1)
ear_r = make_ear(-1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 4: Tail
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[4/8] Building tail...")

TAIL_Z = H * 4 + 0.06   # starts at pelvis
TAIL_Y = 0.13            # behind body

mesh_tail = bpy.data.meshes.new("Tail_mesh")
bm = bmesh.new()

# Curved tail path: (x, y, z, radius)
tail_pts = [
    (0, TAIL_Y,        TAIL_Z,        0.035),
    (0, TAIL_Y + 0.08, TAIL_Z + 0.03, 0.032),
    (0, TAIL_Y + 0.18, TAIL_Z + 0.05, 0.028),
    (0, TAIL_Y + 0.28, TAIL_Z + 0.04, 0.024),
    (0, TAIL_Y + 0.36, TAIL_Z + 0.01, 0.020),
    (0, TAIL_Y + 0.42, TAIL_Z - 0.03, 0.016),
    (0, TAIL_Y + 0.46, TAIL_Z - 0.08, 0.012),
    (0, TAIL_Y + 0.48, TAIL_Z - 0.12, 0.008),
]

tail_rings = []
for px, py, pz, rd in tail_pts:
    ring = []
    for i in range(LIMB_SEGS):
        a = 2 * math.pi * i / LIMB_SEGS
        # Tail rings in XZ plane (perpendicular to Y-forward direction)
        ring.append(bm.verts.new((px + rd * math.cos(a), py, pz + rd * math.sin(a))))
    tail_rings.append(ring)

bm.verts.ensure_lookup_table()

for i in range(len(tail_rings) - 1):
    bridge_rings(bm, tail_rings[i], tail_rings[i + 1], LIMB_SEGS)

# Tail tip
tail_tip = bm.verts.new((0, tail_pts[-1][1] + 0.02, tail_pts[-1][2]))
for j in range(LIMB_SEGS):
    jn = (j + 1) % LIMB_SEGS
    try:
        bm.faces.new([tail_rings[-1][j], tail_rings[-1][jn], tail_tip])
    except Exception:
        pass

# Cap base
try:
    bm.faces.new(list(reversed(tail_rings[0])))
except Exception:
    pass

tail_obj = finalize_mesh(bm, mesh_tail, "Tail", "Ears_Tail", subdiv=2)
print(f"  Tail: {len(mesh_tail.vertices)}v")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 5: Arms
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[5/8] Building arms...")

SHOULDER_Z = H * 7.0    # shoulder height
SHOULDER_X = 0.12       # shoulder offset

def make_arm(side):
    name = "Arm_L" if side > 0 else "Arm_R"
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    sx = side * SHOULDER_X

    # Arm profile: (x, y, z, radius)
    arm_pts = [
        (sx,                0, SHOULDER_Z,        0.040),   # shoulder
        (sx + side * 0.05,  0, SHOULDER_Z - 0.05, 0.038),   # upper arm
        (sx + side * 0.12,  0, SHOULDER_Z - 0.15, 0.032),   # mid arm
        (sx + side * 0.15,  0, SHOULDER_Z - 0.28, 0.028),   # elbow
        (sx + side * 0.16,  0, SHOULDER_Z - 0.38, 0.025),   # forearm
        (sx + side * 0.16,  0, SHOULDER_Z - 0.43, 0.022),   # wrist
    ]

    arm_rings = []
    for px, py, pz, rd in arm_pts:
        ring = make_ring(bm, px, py, pz, rd, rd, LIMB_SEGS)
        arm_rings.append(ring)

    bm.verts.ensure_lookup_table()

    for i in range(len(arm_rings) - 1):
        bridge_rings(bm, arm_rings[i], arm_rings[i + 1], LIMB_SEGS)

    # Cap ends
    try:
        bm.faces.new(arm_rings[-1])
    except Exception:
        pass
    try:
        bm.faces.new(list(reversed(arm_rings[0])))
    except Exception:
        pass

    obj = finalize_mesh(bm, mesh, name, "Body", subdiv=1)
    print(f"  {name}: {len(mesh.vertices)}v")
    return obj

arm_l = make_arm(1)
arm_r = make_arm(-1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 6: Legs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[6/8] Building legs...")

LEG_Z = H * 4   # hip height
LEG_X = 0.055   # hip offset

def make_leg(side):
    name = "Leg_L" if side > 0 else "Leg_R"
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    lx = side * LEG_X

    # Leg profile: (x, y, z, radius)
    leg_pts = [
        (lx,               0, LEG_Z,        0.055),   # hip
        (lx,               0, LEG_Z - 0.08, 0.052),   # upper thigh
        (lx,               0, LEG_Z - 0.20, 0.045),   # mid thigh
        (lx,               0, LEG_Z - 0.35, 0.038),   # knee
        (lx,               0, LEG_Z - 0.38, 0.040),   # below knee
        (lx,               0, LEG_Z - 0.52, 0.032),   # calf
        (lx,               0, LEG_Z - 0.65, 0.025),   # ankle
        (lx,              -0.01, LEG_Z - 0.72, 0.022),   # heel area
        (lx,              -0.03, LEG_Z - 0.76, 0.030),   # foot
    ]

    leg_rings = []
    for px, py, pz, rd in leg_pts:
        ring = make_ring(bm, px, py, pz, rd, rd, LIMB_SEGS)
        leg_rings.append(ring)

    bm.verts.ensure_lookup_table()

    for i in range(len(leg_rings) - 1):
        bridge_rings(bm, leg_rings[i], leg_rings[i + 1], LIMB_SEGS)

    # Cap foot bottom and hip top
    try:
        bm.faces.new(leg_rings[-1])
    except Exception:
        pass
    try:
        bm.faces.new(list(reversed(leg_rings[0])))
    except Exception:
        pass

    obj = finalize_mesh(bm, mesh, name, "Body", subdiv=1)
    print(f"  {name}: {len(mesh.vertices)}v")
    return obj

leg_l = make_leg(1)
leg_r = make_leg(-1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 7: Hair base
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[7/8] Building hair...")

bpy.ops.mesh.primitive_uv_sphere_add(
    radius=HEAD_R * 1.15, segments=16, ring_count=10,
    location=(0, 0, HEAD_Z + 0.01)
)
hair = bpy.context.active_object
hair.name = "Hair_Base"
for c in hair.users_collection:
    c.objects.unlink(hair)
bpy.data.collections["Hair"].objects.link(hair)
hair.scale = (1.1, 1.05, 1.0)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.shade_smooth()
hair.modifiers.new("SS", "SUBSURF").levels = 1
print(f"  Hair_Base: {len(hair.data.vertices)}v")

# Hair bangs (front fringe)
bpy.ops.mesh.primitive_cube_add(size=0.08, location=(0, -0.12, HEAD_Z + 0.06))
bangs = bpy.context.active_object
bangs.name = "Hair_Bangs"
for c in bangs.users_collection:
    c.objects.unlink(bangs)
bpy.data.collections["Hair"].objects.link(bangs)
bangs.scale = (2.2, 0.3, 0.8)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.shade_smooth()
bangs.modifiers.new("SS", "SUBSURF").levels = 2
print(f"  Hair_Bangs: {len(bangs.data.vertices)}v")

# Hair back (long hair flowing down)
mesh_hback = bpy.data.meshes.new("Hair_Back_mesh")
bm = bmesh.new()

hair_back_profile = [
    (HEAD_Z + 0.08, 0.10, 0.08),   # top back
    (HEAD_Z - 0.02, 0.11, 0.09),   # crown
    (HEAD_Z - 0.15, 0.09, 0.07),   # nape
    (H * 6.0,       0.08, 0.06),   # upper back
    (H * 5.0,       0.10, 0.05),   # mid back
    (H * 4.0,       0.08, 0.04),   # lower back / tips
]

hb_rings = []
for z, w, d in hair_back_profile:
    ring = make_ring(bm, 0, 0.04, z, w, d, LIMB_SEGS)
    hb_rings.append(ring)

bm.verts.ensure_lookup_table()
for i in range(len(hb_rings) - 1):
    bridge_rings(bm, hb_rings[i], hb_rings[i + 1], LIMB_SEGS)

try:
    bm.faces.new(list(reversed(hb_rings[0])))
except Exception:
    pass
try:
    bm.faces.new(hb_rings[-1])
except Exception:
    pass

hair_back = finalize_mesh(bm, mesh_hback, "Hair_Back", "Hair", subdiv=1)
print(f"  Hair_Back: {len(mesh_hback.vertices)}v")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 8: Materials + Lighting + Camera
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[8/8] Applying materials & setting up scene...")

def make_material(name, r, g, b, roughness=0.6):
    mat = bpy.data.materials.new(name)
    # Blender 5.x: nodes enabled by default, use_nodes deprecated in 6.0
    if not mat.node_tree:
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

# Materials — dark purple-black hair, fair skin, pink inner ear
mat_skin = make_material("Skin", 1.0, 0.88, 0.82, 0.5)
mat_hair = make_material("Hair_Dark", 0.15, 0.12, 0.18, 0.4)
mat_ear_inner = make_material("Ear_Pink", 0.95, 0.75, 0.78, 0.5)
mat_eye_white = make_material("Eye_White", 0.95, 0.95, 0.97, 0.3)

# Assign materials
skin_objects = ["Body", "Arm_L", "Arm_R", "Leg_L", "Leg_R", "Head"]
hair_objects = ["Hair_Base", "Hair_Bangs", "Hair_Back", "Tail"]
ear_objects = ["Ear_L", "Ear_R"]

for name in skin_objects:
    obj = bpy.data.objects.get(name)
    if obj:
        obj.data.materials.append(mat_skin)

for name in hair_objects:
    obj = bpy.data.objects.get(name)
    if obj:
        obj.data.materials.append(mat_hair)

for name in ear_objects:
    obj = bpy.data.objects.get(name)
    if obj:
        obj.data.materials.append(mat_ear_inner)

print(f"  Materials: {len(bpy.data.materials)} created")

# Camera
cam_data = bpy.data.cameras.new("AvatarCam_data")
cam_data.lens = 85  # portrait lens
cam = bpy.data.objects.new("AvatarCam", cam_data)
bpy.data.collections["Lighting"].objects.link(cam)
cam.location = (0.6, -2.2, 1.0)
cam.rotation_euler = (1.35, 0, 0.12)
bpy.context.scene.camera = cam
print("  Camera: 85mm portrait lens")

# Key light
light_data = bpy.data.lights.new("KeyLight_data", type='AREA')
light_data.energy = 200
light_data.size = 2
light = bpy.data.objects.new("KeyLight", light_data)
bpy.data.collections["Lighting"].objects.link(light)
light.location = (1.5, -1.5, 2.5)
light.rotation_euler = (0.8, 0.2, -0.5)

# Fill light
fill_data = bpy.data.lights.new("FillLight_data", type='AREA')
fill_data.energy = 80
fill_data.size = 3
fill = bpy.data.objects.new("FillLight", fill_data)
bpy.data.collections["Lighting"].objects.link(fill)
fill.location = (-1.2, -1.0, 1.8)
fill.rotation_euler = (1.0, -0.3, 0.5)
print("  Lighting: Key + Fill")

# Set viewport to material preview
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
                space.region_3d.view_perspective = 'PERSP'
                space.region_3d.view_distance = 3.0

# Render settings
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Save file
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "dwgx_avatar.blend")
bpy.ops.wm.save_as_mainfile(filepath=save_path)
print(f"\n  Saved: {save_path}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Scene summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n" + "=" * 60)
print("  SCENE SUMMARY")
print("=" * 60)

total_verts = 0
total_faces = 0
for obj in sorted(bpy.data.objects, key=lambda x: x.name):
    if obj.type == 'MESH':
        v = len(obj.data.vertices)
        f = len(obj.data.polygons)
        total_verts += v
        total_faces += f
        col_name = obj.users_collection[0].name if obj.users_collection else "?"
        mat_name = obj.data.materials[0].name if obj.data.materials else "none"
        print(f"  {obj.name:15s} | {v:4d}v {f:4d}f | {col_name:10s} | {mat_name}")
    elif obj.type in ('CAMERA', 'LIGHT'):
        print(f"  {obj.name:15s} | {obj.type:10s}")

print(f"\n  TOTAL: {total_verts}v, {total_faces}f")
print(f"  Collections: {len(bpy.data.collections)}")
print(f"  Materials: {len(bpy.data.materials)}")
print("=" * 60)
print("  DWGX avatar base mesh complete!")
print("=" * 60 + "\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Start MCP addon server for continued AI interaction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("[Post-build] Starting MCP addon server...")

def _start_addon():
    import addon_utils
    module_name = "blender_copilot"
    port = int(os.environ.get("BLENDER_PORT", "9876"))

    mod = None
    try:
        mod = addon_utils.enable(module_name, default_set=True, persistent=True)
    except Exception:
        pass

    if mod is None:
        for m in addon_utils.modules():
            if m.__name__ == module_name:
                mod = m
                break

    if mod and hasattr(mod, "CopilotServer"):
        if not hasattr(bpy.types, "copilot_server") or not bpy.types.copilot_server:
            bpy.types.copilot_server = mod.CopilotServer(port=port)
        bpy.types.copilot_server.start()
        bpy.context.scene.copilot_port = port
        bpy.context.scene.copilot_running = True
        print(f"[Post-build] MCP server running on port {port}")
    else:
        print("[Post-build] WARNING: addon not found, MCP server not started")
    return None

bpy.app.timers.register(_start_addon, first_interval=1.0)
