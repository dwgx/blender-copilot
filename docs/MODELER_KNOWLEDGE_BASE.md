# 3D Modeler Knowledge Base -- VRChat Avatar Pipeline
> **MUST READ before every build session.** This is the single source of truth for MCP-driven avatar work.

---

## Quick Reference: Performance Rank Limits

### PC

| Metric | Excellent | Good | Medium | Poor |
|---|---|---|---|---|
| Triangles | 32,000 | 70,000 | 70,000 | 70,000 |
| Texture Memory | 40 MB | 75 MB | 110 MB | 150 MB |
| Skinned Meshes | 1 | 2 | 8 | 16 |
| Material Slots | 4 | 8 | 16 | 32 |
| Bones | 75 | 150 | 256 | 400 |
| PhysBone Components | 4 | 8 | 16 | 32 |
| PhysBone Transforms | 16 | 64 | 128 | 256 |
| PhysBone Colliders | 4 | 8 | 16 | 32 |
| Contacts | 4 | 16 | 24 | 32 |
| Constraints | 30 | 60 | 120 | 150 |

### Quest/Android

| Metric | Excellent | Good | Medium | Poor |
|---|---|---|---|---|
| Triangles | 7,500 | 10,000 | 15,000 | 20,000 |
| Texture Memory | 10 MB | 18 MB | 25 MB | 40 MB |
| Skinned Meshes | 1 | 1 | 2 | 2 |
| Material Slots | 1 | 1 | 2 | 4 |
| Bones | 75 | 90 | 150 | 150 |

**Quest hard limits**: >20K tris = blocked. Max compressed upload = 10 MB. Shader = VRChat/Mobile/Toon Lit only.

### Expression Parameters Budget: 256 bits total
- Bool = 1 bit, Int = 8 bits, Float = 8 bits
- VRC reserved ~49 bits → usable ~207 bits
- **Rule**: Plan parameter budget BEFORE building toggles

---

## Blender Pre-Flight Checklist (Before Every Export)

```
[ ] All transforms applied (Ctrl+A > All Transforms) on EVERY object
[ ] Single armature (merge accessory armatures into main)
[ ] Bone names match Unity Humanoid (use vrc_rename_bones)
[ ] No leaf bones in FBX export
[ ] Scale = 1.0 on all objects (check armature AND meshes)
[ ] Normals facing outward (Shift+N in edit mode)
[ ] No loose vertices/edges (Select All > Mesh > Clean Up > Delete Loose)
[ ] Shape keys intact after decimation (validate visemes still work)
[ ] Materials consolidated (target 1-4 for Good/Excellent)
[ ] UV maps present on all visible meshes
```

---

## FBX Export Settings (Blender → Unity)

```python
{
    "axis_forward": "-Z",
    "axis_up": "Y",
    "apply_scalings": "FBX_SCALE_ALL",
    "use_mesh_modifiers": True,
    "mesh_smooth_type": "FACE",
    "add_leaf_bones": False,       # CRITICAL: always False
    "bake_anim": False,            # Unless exporting animations
    "apply_unit_scale": True,
    "apply_scale_options": "FBX_SCALE_ALL",
}
```

## FBX Import Settings (Accessories/Clothes into Blender)

```python
{
    "axis_forward": "-Y",
    "axis_up": "Z",
    "automatic_bone_orientation": False,
    "force_connect_children": False,
    "ignore_leaf_bones": True,
}
```

**WARNING**: Different FBX sources use different axes. If an imported accessory looks rotated 90 degrees, it likely needs axis correction. Common cases:
- Unity-exported FBX: forward=-Z, up=Y → needs conversion
- Mixamo FBX: forward=-Y, up=Z → matches Blender default
- MMD/PMX converted: may need X-axis 90° rotation

---

## Accessory Attachment Protocol (Shoes, Clothes, Hair)

### BEFORE importing an accessory:
1. Note the source format (Unity FBX? Mixamo? MMD?)
2. Import with correct axis preset

### AFTER importing, BEFORE parenting:
1. **Visual check**: Is the accessory roughly the right size and orientation?
2. **Apply transforms**: `Ctrl+A > All Transforms` on the accessory
3. **Scale check**: Compare accessory bounding box to avatar body part
4. **Axis check**: If rotated 90°, apply rotation correction first
5. **Origin check**: Set origin to geometry center or world origin as needed

### Parenting to armature:
1. Select accessory mesh → Shift+select armature → `Ctrl+P > Armature Deform`
2. For rigid accessories (shoes, hats): weight to single bone at 1.0
3. For deformable accessories (skirts, capes): transfer weights from body mesh
4. **VALIDATE**: Enter pose mode, rotate target bone, verify accessory follows correctly

### Common Attachment Failures:
| Symptom | Cause | Fix |
|---|---|---|
| Accessory is 10x too large | Scale not normalized | Scale to match, apply transforms |
| Accessory rotated 90° | Axis mismatch from FBX | Rotate to correct, apply transforms |
| Accessory doesn't follow bone | Parent not set or wrong bone | Re-parent to correct bone |
| Accessory deforms weirdly | Bad weight painting | Transfer weights from body mesh |
| Accessory offset from bone | Origin point wrong | Set origin to 3D cursor at bone head |

---

## Outfit Toggle System (Unity Side)

### Architecture (using VRCFury + Modular Avatar):

```
Avatar Root
├── Body (always on)
├── [Outfit_A] ← VRCFury Toggle (default ON) + Exclusive Tag "outfit"
│   └── MA Merge Armature → Avatar Armature
├── [Outfit_B] ← VRCFury Toggle (default OFF) + Exclusive Tag "outfit"
│   └── MA Merge Armature → Avatar Armature
├── [Shoes_A] ← VRCFury Toggle + Exclusive Tag "shoes"
├── [Shoes_B] ← VRCFury Toggle + Exclusive Tag "shoes"
└── [Hair_A] ← VRCFury Toggle + Exclusive Tag "hair"
```

### Key Rules:
1. **Exclusive Tags** = only one in the group can be active (auto-disables others)
2. **MA Merge Armature** = non-destructively merges clothing bones into avatar at build time
3. **VRCFury Toggle** = auto-creates animator layer + expression menu entry + parameter
4. **Saved** = checked for outfits (persists across worlds), unchecked for effects
5. **Default state** = which outfit shows when avatar first loads

### Expression Menu Structure:
```
Main Menu (8 slots max)
├── Outfits (submenu)
│   ├── Default Outfit (toggle, exclusive "outfit")
│   ├── Mayo Bottle (toggle, exclusive "outfit")
│   └── Twin Lady Dress (toggle, exclusive "outfit")
├── Shoes (submenu)
│   ├── Slippers (toggle, exclusive "shoes")
│   └── Soffina Heels (toggle, exclusive "shoes")
├── Hair (submenu)
│   ├── Default Hair (toggle, exclusive "hair")
│   └── Twin Lady Hair (toggle, exclusive "hair")
├── Face (submenu)
│   ├── Natural Makeup (toggle)
│   └── Full Makeup (toggle)
├── Eyes (submenu, radial for color)
└── Emotes (submenu → EmoteBox)
```

---

## Blender Speed Shortcuts

| Shortcut | Action | When to Use |
|---|---|---|
| `Ctrl+A` | Apply All Transforms | **Before every export and before parenting** |
| `Ctrl+J` | Join meshes | Merge into single skinned mesh |
| `Ctrl+L` | Transfer Weights | Copy weights from body to accessory |
| `Shift+N` | Recalculate normals | Fix inverted faces |
| `Ctrl+P` | Parent | Parent accessory to armature |
| `Alt+P` | Clear Parent | Unparent (keep transform) |
| `H / Alt+H` | Hide/Unhide | Declutter viewport |
| `Ctrl+Tab` | Mode pie menu | Quick switch Object/Edit/Weight Paint |
| `Ctrl+Numpad+/-` | Grow/Shrink selection | Weight paint regions |
| `P > By Loose Parts` | Separate by loose | Split multi-piece accessories |
| `M` | Merge vertices | Clean up after import |
| `Shift+D → Right-Click` | Duplicate in place | Copy for mirroring |
| `Ctrl+M → X/Y/Z` | Mirror | Mirror shoes left→right |

---

## Weight Painting Rules

1. **Use bmesh over bpy.ops.mesh** — faster, more predictable, no context dependency
2. **Smoothstep interpolation** (`3t²-2t³`) instead of linear — avoids visible joint creases
3. **Transfer weights** from body mesh to clothing (Nearest Face Interpolated mode)
4. **Normalize All** after manual edits — weights must sum to 1.0 per vertex
5. **Limit Total** to 4 influences per vertex (GPU skinning limit on Quest)
6. **Clean** with threshold 0.01 — remove near-zero weights that waste bone slots

---

## Material & Texture Rules

1. **Non-Color colorspace** for normal/roughness/metallic/AO maps (NOT sRGB)
2. **sRGB colorspace** for albedo/diffuse/emission only
3. **Target texture sizes**: Body 2048x2048, Face 1024x1024, Eyes 512x512
4. **Quest textures**: Halve all sizes, use ASTC 6x6 compression
5. **Atlas everything** for optimization — tools: d4rkAvatarOptimizer or AAO
6. **Poiyomi Shader** is the VRC standard — supports dissolve toggles, AudioLink, outlines

---

## The 10 Commandments of VRC Avatars

1. **Apply transforms before export** (Ctrl+A)
2. **One skinned mesh renderer** (merge everything in Unity/optimizer)
3. **Minimize materials** (atlas textures)
4. **No leaf bones** (uncheck in FBX export)
5. **Write Defaults consistency** (all ON or all OFF — never mix)
6. **Plan parameter budget** (256 bits, track usage)
7. **Use non-destructive tools** (VRCFury/MA, never manually edit FX controller)
8. **Test on Quest** (even if PC-only, Quest users can't see you without fallback)
9. **Optimize LAST** (AAO/d4rk after all components set up)
10. **Keep backup of un-optimized version** (never decimate your only copy)

---

## MCP Tool Chain (Recommended Order)

```
1. vrc_import_model       → Import with correct axis
2. vrc_accessory_auto_align → Scale/rotate/position accessories
3. vrc_attach_accessory   → Parent to correct bone
4. vrc_fix_model          → Auto-fix common issues
5. vrc_rename_bones       → Ensure Unity Humanoid names
6. vrc_setup_visemes      → 15 visemes from 3 base shapes
7. vrc_setup_eye_tracking → Eye bone constraints
8. vrc_physbone_config    → Hair/tail/ears/skirt physics
9. vrc_setup_contacts     → Headpat/boop/handshake
10. vrc_validate          → Check against performance rank
11. vrc_decimate          → Reduce polys if needed (preserves shape keys)
12. vrc_bake_atlas        → Merge textures/materials
13. vrc_validate          → Re-check after optimization
14. vrc_export_fbx        → Export with correct settings
```

**After Blender export → Unity:**
```
1. Import FBX + set as Humanoid rig
2. Install VRCFury + Modular Avatar + NDMF
3. Drag clothing prefabs as children of avatar
4. Add MA Merge Armature to each clothing piece
5. Add VRCFury Toggle to each toggleable item
6. Set Exclusive Tags for outfit groups
7. Add VRCFury Full Controller for EmoteBox
8. Add AAO Trace and Optimize to avatar root
9. Test with VRC Gesture Manager (no upload needed)
10. Upload via VRC SDK
```

---

## Known Pitfalls from Past Sessions

- **Mayo_Mayo is a novelty mayo bottle costume** — it's supposed to be big, not a bug
- **Shoe FBX from BOOTH often has axis mismatch** — always check after import
- **UnityPackage files can't directly import to Blender** — extract FBX using tarfile Python
- **Blender 5.1 uses `context.temp_override()`** for headless/batch operations
- **GBK encoding errors on Windows** — always use `sys.stdout.reconfigure(encoding='utf-8')` in Python scripts

---

*Last updated: 2026-04-13*
*Source: Web research + session analysis + VRChat official docs*
