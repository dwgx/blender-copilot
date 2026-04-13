# VRChat Avatar Performance Rank Constants & Bone Mappings

# Performance rank polygon limits (triangles)
RANK_LIMITS = {
    "pc": {
        "excellent": {"polygons": 32000, "skinned_meshes": 1, "meshes": 4, "materials": 4, "bones": 75,
                      "texture_memory_mb": 40,
                      "physbone_components": 4, "physbone_transforms": 16, "physbone_colliders": 4,
                      "physbone_collision_check": 32,
                      "contacts": 8, "constraints": 100, "constraint_depth": 20,
                      "animators": 1},
        "good":      {"polygons": 70000, "skinned_meshes": 2, "meshes": 8, "materials": 8, "bones": 150,
                      "texture_memory_mb": 75,
                      "physbone_components": 8, "physbone_transforms": 64, "physbone_colliders": 8,
                      "physbone_collision_check": 128,
                      "contacts": 16, "constraints": 250, "constraint_depth": 50,
                      "animators": 4},
        "medium":    {"polygons": 70000, "skinned_meshes": 8, "meshes": 16, "materials": 16, "bones": 256,
                      "texture_memory_mb": 110,
                      "physbone_components": 16, "physbone_transforms": 128, "physbone_colliders": 16,
                      "physbone_collision_check": 256,
                      "contacts": 24, "constraints": 300, "constraint_depth": 80,
                      "animators": 16},
        "poor":      {"polygons": 70000, "skinned_meshes": 16, "meshes": 24, "materials": 32, "bones": 400,
                      "texture_memory_mb": 150,
                      "physbone_components": 32, "physbone_transforms": 256, "physbone_colliders": 32,
                      "physbone_collision_check": 512,
                      "contacts": 32, "constraints": 350, "constraint_depth": 100,
                      "animators": 32},
    },
    "quest": {
        "excellent": {"polygons": 7500, "skinned_meshes": 1, "meshes": 1, "materials": 1, "bones": 75,
                      "texture_memory_mb": 10,
                      "physbone_components": 0, "physbone_transforms": 0, "physbone_colliders": 0,
                      "physbone_collision_check": 0,
                      "contacts": 2, "constraints": 30, "constraint_depth": 5,
                      "animators": 1},
        "good":      {"polygons": 10000, "skinned_meshes": 1, "meshes": 1, "materials": 1, "bones": 90,
                      "texture_memory_mb": 18,
                      "physbone_components": 4, "physbone_transforms": 16, "physbone_colliders": 4,
                      "physbone_collision_check": 16,
                      "contacts": 4, "constraints": 60, "constraint_depth": 15,
                      "animators": 1},
        "medium":    {"polygons": 15000, "skinned_meshes": 2, "meshes": 2, "materials": 2, "bones": 150,
                      "texture_memory_mb": 25,
                      "physbone_components": 6, "physbone_transforms": 32, "physbone_colliders": 8,
                      "physbone_collision_check": 32,
                      "contacts": 8, "constraints": 120, "constraint_depth": 35,
                      "animators": 1},
        "poor":      {"polygons": 20000, "skinned_meshes": 2, "meshes": 2, "materials": 4, "bones": 150,
                      "texture_memory_mb": 40,
                      "physbone_components": 8, "physbone_transforms": 64, "physbone_colliders": 16,
                      "physbone_collision_check": 64,
                      "contacts": 16, "constraints": 150, "constraint_depth": 50,
                      "animators": 2},
    },
}

# VRChat required humanoid bones (Unity Humanoid mapping)
REQUIRED_BONES = [
    "Hips", "Spine", "Chest",
    "Neck", "Head",
    "Left_Shoulder", "Left_UpperArm", "Left_LowerArm", "Left_Hand",
    "Right_Shoulder", "Right_UpperArm", "Right_LowerArm", "Right_Hand",
    "Left_UpperLeg", "Left_LowerLeg", "Left_Foot",
    "Right_UpperLeg", "Right_LowerLeg", "Right_Foot",
]

OPTIONAL_BONES = [
    "UpperChest",
    "Left_Toes", "Right_Toes",
    "Left_Eye", "Right_Eye",
    "Jaw",
]

# Finger bones (3 joints × 5 fingers × 2 hands)
FINGER_BONES = []
for side in ("Left", "Right"):
    for finger in ("Thumb", "Index", "Middle", "Ring", "Little"):
        for joint in ("Proximal", "Intermediate", "Distal"):
            FINGER_BONES.append(f"{side}_{finger}_{joint}")

# Common bone name aliases → VRC standard name
# Maps Mixamo, MMD, VRM, and other common naming schemes
BONE_NAME_MAP = {
    # Mixamo
    "mixamorig:Hips": "Hips",
    "mixamorig:Spine": "Spine",
    "mixamorig:Spine1": "Chest",
    "mixamorig:Spine2": "UpperChest",
    "mixamorig:Neck": "Neck",
    "mixamorig:Head": "Head",
    "mixamorig:LeftShoulder": "Left_Shoulder",
    "mixamorig:LeftArm": "Left_UpperArm",
    "mixamorig:LeftForeArm": "Left_LowerArm",
    "mixamorig:LeftHand": "Left_Hand",
    "mixamorig:RightShoulder": "Right_Shoulder",
    "mixamorig:RightArm": "Right_UpperArm",
    "mixamorig:RightForeArm": "Right_LowerArm",
    "mixamorig:RightHand": "Right_Hand",
    "mixamorig:LeftUpLeg": "Left_UpperLeg",
    "mixamorig:LeftLeg": "Left_LowerLeg",
    "mixamorig:LeftFoot": "Left_Foot",
    "mixamorig:LeftToeBase": "Left_Toes",
    "mixamorig:RightUpLeg": "Right_UpperLeg",
    "mixamorig:RightLeg": "Right_LowerLeg",
    "mixamorig:RightFoot": "Right_Foot",
    "mixamorig:RightToeBase": "Right_Toes",
    "mixamorig:LeftEye": "Left_Eye",
    "mixamorig:RightEye": "Right_Eye",
    # Mixamo fingers
    "mixamorig:LeftHandThumb1": "Left_Thumb_Proximal",
    "mixamorig:LeftHandThumb2": "Left_Thumb_Intermediate",
    "mixamorig:LeftHandThumb3": "Left_Thumb_Distal",
    "mixamorig:LeftHandIndex1": "Left_Index_Proximal",
    "mixamorig:LeftHandIndex2": "Left_Index_Intermediate",
    "mixamorig:LeftHandIndex3": "Left_Index_Distal",
    "mixamorig:LeftHandMiddle1": "Left_Middle_Proximal",
    "mixamorig:LeftHandMiddle2": "Left_Middle_Intermediate",
    "mixamorig:LeftHandMiddle3": "Left_Middle_Distal",
    "mixamorig:LeftHandRing1": "Left_Ring_Proximal",
    "mixamorig:LeftHandRing2": "Left_Ring_Intermediate",
    "mixamorig:LeftHandRing3": "Left_Ring_Distal",
    "mixamorig:LeftHandPinky1": "Left_Little_Proximal",
    "mixamorig:LeftHandPinky2": "Left_Little_Intermediate",
    "mixamorig:LeftHandPinky3": "Left_Little_Distal",
    "mixamorig:RightHandThumb1": "Right_Thumb_Proximal",
    "mixamorig:RightHandThumb2": "Right_Thumb_Intermediate",
    "mixamorig:RightHandThumb3": "Right_Thumb_Distal",
    "mixamorig:RightHandIndex1": "Right_Index_Proximal",
    "mixamorig:RightHandIndex2": "Right_Index_Intermediate",
    "mixamorig:RightHandIndex3": "Right_Index_Distal",
    "mixamorig:RightHandMiddle1": "Right_Middle_Proximal",
    "mixamorig:RightHandMiddle2": "Right_Middle_Intermediate",
    "mixamorig:RightHandMiddle3": "Right_Middle_Distal",
    "mixamorig:RightHandRing1": "Right_Ring_Proximal",
    "mixamorig:RightHandRing2": "Right_Ring_Intermediate",
    "mixamorig:RightHandRing3": "Right_Ring_Distal",
    "mixamorig:RightHandPinky1": "Right_Little_Proximal",
    "mixamorig:RightHandPinky2": "Right_Little_Intermediate",
    "mixamorig:RightHandPinky3": "Right_Little_Distal",

    # Common short names (no prefix)
    "spine": "Spine", "chest": "Chest", "upper_chest": "UpperChest",
    "neck": "Neck", "head": "Head", "hips": "Hips",
    "shoulder.L": "Left_Shoulder", "upper_arm.L": "Left_UpperArm",
    "forearm.L": "Left_LowerArm", "hand.L": "Left_Hand",
    "shoulder.R": "Right_Shoulder", "upper_arm.R": "Right_UpperArm",
    "forearm.R": "Right_LowerArm", "hand.R": "Right_Hand",
    "thigh.L": "Left_UpperLeg", "shin.L": "Left_LowerLeg",
    "foot.L": "Left_Foot", "toe.L": "Left_Toes",
    "thigh.R": "Right_UpperLeg", "shin.R": "Right_LowerLeg",
    "foot.R": "Right_Foot", "toe.R": "Right_Toes",

    # MMD / PMX (Japanese)
    "全ての親": "Hips", "センター": "Hips",
    "上半身": "Spine", "上半身2": "Chest", "上半身3": "UpperChest",
    "首": "Neck", "頭": "Head",
    "左肩": "Left_Shoulder", "左腕": "Left_UpperArm",
    "左ひじ": "Left_LowerArm", "左手首": "Left_Hand",
    "右肩": "Right_Shoulder", "右腕": "Right_UpperArm",
    "右ひじ": "Right_LowerArm", "右手首": "Right_Hand",
    "左足": "Left_UpperLeg", "左ひざ": "Left_LowerLeg",
    "左足首": "Left_Foot", "左つま先": "Left_Toes",
    "右足": "Right_UpperLeg", "右ひざ": "Right_LowerLeg",
    "右足首": "Right_Foot", "右つま先": "Right_Toes",
    "左目": "Left_Eye", "右目": "Right_Eye",
    # MMD finger bones
    "左親指０": "Left_Thumb_Proximal", "左親指１": "Left_Thumb_Intermediate", "左親指２": "Left_Thumb_Distal",
    "左人指１": "Left_Index_Proximal", "左人指２": "Left_Index_Intermediate", "左人指３": "Left_Index_Distal",
    "左中指１": "Left_Middle_Proximal", "左中指２": "Left_Middle_Intermediate", "左中指３": "Left_Middle_Distal",
    "左薬指１": "Left_Ring_Proximal", "左薬指２": "Left_Ring_Intermediate", "左薬指３": "Left_Ring_Distal",
    "左小指１": "Left_Little_Proximal", "左小指２": "Left_Little_Intermediate", "左小指３": "Left_Little_Distal",
    "右親指０": "Right_Thumb_Proximal", "右親指１": "Right_Thumb_Intermediate", "右親指２": "Right_Thumb_Distal",
    "右人指１": "Right_Index_Proximal", "右人指２": "Right_Index_Intermediate", "右人指３": "Right_Index_Distal",
    "右中指１": "Right_Middle_Proximal", "右中指２": "Right_Middle_Intermediate", "右中指３": "Right_Middle_Distal",
    "右薬指１": "Right_Ring_Proximal", "右薬指２": "Right_Ring_Intermediate", "右薬指３": "Right_Ring_Distal",
    "右小指１": "Right_Little_Proximal", "右小指２": "Right_Little_Intermediate", "右小指３": "Right_Little_Distal",

    # VRM / VRoid Studio (J_Bip_* format) — most common on BOOTH
    "J_Bip_C_Hips": "Hips", "J_Bip_C_Spine": "Spine", "J_Bip_C_Chest": "Chest",
    "J_Bip_C_UpperChest": "UpperChest", "J_Bip_C_Neck": "Neck", "J_Bip_C_Head": "Head",
    "J_Bip_L_Shoulder": "Left_Shoulder", "J_Bip_L_UpperArm": "Left_UpperArm",
    "J_Bip_L_LowerArm": "Left_LowerArm", "J_Bip_L_Hand": "Left_Hand",
    "J_Bip_R_Shoulder": "Right_Shoulder", "J_Bip_R_UpperArm": "Right_UpperArm",
    "J_Bip_R_LowerArm": "Right_LowerArm", "J_Bip_R_Hand": "Right_Hand",
    "J_Bip_L_UpperLeg": "Left_UpperLeg", "J_Bip_L_LowerLeg": "Left_LowerLeg",
    "J_Bip_L_Foot": "Left_Foot", "J_Bip_L_ToeBase": "Left_Toes",
    "J_Bip_R_UpperLeg": "Right_UpperLeg", "J_Bip_R_LowerLeg": "Right_LowerLeg",
    "J_Bip_R_Foot": "Right_Foot", "J_Bip_R_ToeBase": "Right_Toes",
    "J_Bip_L_Eye": "Left_Eye", "J_Bip_R_Eye": "Right_Eye", "J_Bip_C_Jaw": "Jaw",
    # VRM fingers
    "J_Bip_L_Thumb1": "Left_Thumb_Proximal", "J_Bip_L_Thumb2": "Left_Thumb_Intermediate", "J_Bip_L_Thumb3": "Left_Thumb_Distal",
    "J_Bip_L_Index1": "Left_Index_Proximal", "J_Bip_L_Index2": "Left_Index_Intermediate", "J_Bip_L_Index3": "Left_Index_Distal",
    "J_Bip_L_Middle1": "Left_Middle_Proximal", "J_Bip_L_Middle2": "Left_Middle_Intermediate", "J_Bip_L_Middle3": "Left_Middle_Distal",
    "J_Bip_L_Ring1": "Left_Ring_Proximal", "J_Bip_L_Ring2": "Left_Ring_Intermediate", "J_Bip_L_Ring3": "Left_Ring_Distal",
    "J_Bip_L_Little1": "Left_Little_Proximal", "J_Bip_L_Little2": "Left_Little_Intermediate", "J_Bip_L_Little3": "Left_Little_Distal",
    "J_Bip_R_Thumb1": "Right_Thumb_Proximal", "J_Bip_R_Thumb2": "Right_Thumb_Intermediate", "J_Bip_R_Thumb3": "Right_Thumb_Distal",
    "J_Bip_R_Index1": "Right_Index_Proximal", "J_Bip_R_Index2": "Right_Index_Intermediate", "J_Bip_R_Index3": "Right_Index_Distal",
    "J_Bip_R_Middle1": "Right_Middle_Proximal", "J_Bip_R_Middle2": "Right_Middle_Intermediate", "J_Bip_R_Middle3": "Right_Middle_Distal",
    "J_Bip_R_Ring1": "Right_Ring_Proximal", "J_Bip_R_Ring2": "Right_Ring_Intermediate", "J_Bip_R_Ring3": "Right_Ring_Distal",
    "J_Bip_R_Little1": "Right_Little_Proximal", "J_Bip_R_Little2": "Right_Little_Intermediate", "J_Bip_R_Little3": "Right_Little_Distal",

    # Blender Rigify (DEF-* deform bones, default 6-segment metarig)
    "DEF-spine": "Hips", "DEF-spine.001": "Spine", "DEF-spine.002": "Chest",
    "DEF-spine.003": "UpperChest", "DEF-spine.004": "Neck", "DEF-spine.005": "Head",
    "DEF-eye.L": "Left_Eye", "DEF-eye.R": "Right_Eye", "DEF-jaw": "Jaw",
    "DEF-shoulder.L": "Left_Shoulder", "DEF-upper_arm.L": "Left_UpperArm",
    "DEF-forearm.L": "Left_LowerArm", "DEF-hand.L": "Left_Hand",
    "DEF-shoulder.R": "Right_Shoulder", "DEF-upper_arm.R": "Right_UpperArm",
    "DEF-forearm.R": "Right_LowerArm", "DEF-hand.R": "Right_Hand",
    "DEF-thigh.L": "Left_UpperLeg", "DEF-shin.L": "Left_LowerLeg",
    "DEF-foot.L": "Left_Foot", "DEF-toe.L": "Left_Toes",
    "DEF-thigh.R": "Right_UpperLeg", "DEF-shin.R": "Right_LowerLeg",
    "DEF-foot.R": "Right_Foot", "DEF-toe.R": "Right_Toes",
    # Rigify fingers
    "DEF-thumb.01.L": "Left_Thumb_Proximal", "DEF-thumb.02.L": "Left_Thumb_Intermediate", "DEF-thumb.03.L": "Left_Thumb_Distal",
    "DEF-f_index.01.L": "Left_Index_Proximal", "DEF-f_index.02.L": "Left_Index_Intermediate", "DEF-f_index.03.L": "Left_Index_Distal",
    "DEF-f_middle.01.L": "Left_Middle_Proximal", "DEF-f_middle.02.L": "Left_Middle_Intermediate", "DEF-f_middle.03.L": "Left_Middle_Distal",
    "DEF-f_ring.01.L": "Left_Ring_Proximal", "DEF-f_ring.02.L": "Left_Ring_Intermediate", "DEF-f_ring.03.L": "Left_Ring_Distal",
    "DEF-f_pinky.01.L": "Left_Little_Proximal", "DEF-f_pinky.02.L": "Left_Little_Intermediate", "DEF-f_pinky.03.L": "Left_Little_Distal",
    "DEF-thumb.01.R": "Right_Thumb_Proximal", "DEF-thumb.02.R": "Right_Thumb_Intermediate", "DEF-thumb.03.R": "Right_Thumb_Distal",
    "DEF-f_index.01.R": "Right_Index_Proximal", "DEF-f_index.02.R": "Right_Index_Intermediate", "DEF-f_index.03.R": "Right_Index_Distal",
    "DEF-f_middle.01.R": "Right_Middle_Proximal", "DEF-f_middle.02.R": "Right_Middle_Intermediate", "DEF-f_middle.03.R": "Right_Middle_Distal",
    "DEF-f_ring.01.R": "Right_Ring_Proximal", "DEF-f_ring.02.R": "Right_Ring_Intermediate", "DEF-f_ring.03.R": "Right_Ring_Distal",
    "DEF-f_pinky.01.R": "Right_Little_Proximal", "DEF-f_pinky.02.R": "Right_Little_Intermediate", "DEF-f_pinky.03.R": "Right_Little_Distal",

    # 3ds Max Biped (Bip001 / Bip01 format)
    "Bip001 Pelvis": "Hips", "Bip001 Spine": "Spine", "Bip001 Spine1": "Chest",
    "Bip001 Spine2": "UpperChest", "Bip001 Neck": "Neck", "Bip001 Head": "Head",
    "Bip001 L Clavicle": "Left_Shoulder", "Bip001 L UpperArm": "Left_UpperArm",
    "Bip001 L Forearm": "Left_LowerArm", "Bip001 L Hand": "Left_Hand",
    "Bip001 R Clavicle": "Right_Shoulder", "Bip001 R UpperArm": "Right_UpperArm",
    "Bip001 R Forearm": "Right_LowerArm", "Bip001 R Hand": "Right_Hand",
    "Bip001 L Thigh": "Left_UpperLeg", "Bip001 L Calf": "Left_LowerLeg",
    "Bip001 L Foot": "Left_Foot", "Bip001 L Toe0": "Left_Toes",
    "Bip001 R Thigh": "Right_UpperLeg", "Bip001 R Calf": "Right_LowerLeg",
    "Bip001 R Foot": "Right_Foot", "Bip001 R Toe0": "Right_Toes",
    # Bip001 fingers
    "Bip001 L Finger0": "Left_Thumb_Proximal", "Bip001 L Finger01": "Left_Thumb_Intermediate", "Bip001 L Finger02": "Left_Thumb_Distal",
    "Bip001 L Finger1": "Left_Index_Proximal", "Bip001 L Finger11": "Left_Index_Intermediate", "Bip001 L Finger12": "Left_Index_Distal",
    "Bip001 L Finger2": "Left_Middle_Proximal", "Bip001 L Finger21": "Left_Middle_Intermediate", "Bip001 L Finger22": "Left_Middle_Distal",
    "Bip001 L Finger3": "Left_Ring_Proximal", "Bip001 L Finger31": "Left_Ring_Intermediate", "Bip001 L Finger32": "Left_Ring_Distal",
    "Bip001 L Finger4": "Left_Little_Proximal", "Bip001 L Finger41": "Left_Little_Intermediate", "Bip001 L Finger42": "Left_Little_Distal",
    "Bip001 R Finger0": "Right_Thumb_Proximal", "Bip001 R Finger01": "Right_Thumb_Intermediate", "Bip001 R Finger02": "Right_Thumb_Distal",
    "Bip001 R Finger1": "Right_Index_Proximal", "Bip001 R Finger11": "Right_Index_Intermediate", "Bip001 R Finger12": "Right_Index_Distal",
    "Bip001 R Finger2": "Right_Middle_Proximal", "Bip001 R Finger21": "Right_Middle_Intermediate", "Bip001 R Finger22": "Right_Middle_Distal",
    "Bip001 R Finger3": "Right_Ring_Proximal", "Bip001 R Finger31": "Right_Ring_Intermediate", "Bip001 R Finger32": "Right_Ring_Distal",
    "Bip001 R Finger4": "Right_Little_Proximal", "Bip001 R Finger41": "Right_Little_Intermediate", "Bip001 R Finger42": "Right_Little_Distal",
    # Bip01 variant (no trailing 1)
    "Bip01 Pelvis": "Hips", "Bip01 Spine": "Spine", "Bip01 Spine1": "Chest",
    "Bip01 Spine2": "UpperChest", "Bip01 Neck": "Neck", "Bip01 Head": "Head",
    "Bip01 L Clavicle": "Left_Shoulder", "Bip01 L UpperArm": "Left_UpperArm",
    "Bip01 L Forearm": "Left_LowerArm", "Bip01 L Hand": "Left_Hand",
    "Bip01 R Clavicle": "Right_Shoulder", "Bip01 R UpperArm": "Right_UpperArm",
    "Bip01 R Forearm": "Right_LowerArm", "Bip01 R Hand": "Right_Hand",
    "Bip01 L Thigh": "Left_UpperLeg", "Bip01 L Calf": "Left_LowerLeg",
    "Bip01 L Foot": "Left_Foot", "Bip01 L Toe0": "Left_Toes",
    "Bip01 R Thigh": "Right_UpperLeg", "Bip01 R Calf": "Right_LowerLeg",
    "Bip01 R Foot": "Right_Foot", "Bip01 R Toe0": "Right_Toes",
}

# VRChat viseme shape key names (SIL standard, 15 visemes)
VRC_VISEMES = [
    "vrc.v_sil", "vrc.v_pp", "vrc.v_ff", "vrc.v_th", "vrc.v_dd",
    "vrc.v_kk", "vrc.v_ch", "vrc.v_ss", "vrc.v_nn", "vrc.v_rr",
    "vrc.v_aa", "vrc.v_e", "vrc.v_ih", "vrc.v_oh", "vrc.v_ou",
]

# Eye tracking blend shapes
VRC_EYE_TRACKING = [
    "vrc.blink_left", "vrc.blink_right",
    "vrc.lowerlid_left", "vrc.lowerlid_right",
]

# MMD viseme name mapping → VRC viseme
MMD_VISEME_MAP = {
    "あ": "vrc.v_aa", "い": "vrc.v_ih", "う": "vrc.v_ou",
    "え": "vrc.v_e", "お": "vrc.v_oh",
    "a": "vrc.v_aa", "i": "vrc.v_ih", "u": "vrc.v_ou",
    "e": "vrc.v_e", "o": "vrc.v_oh",
}

# CATS-style viseme blend weights: generate 15 visemes from 3 base shapes (mouth_a, mouth_o, mouth_ch)
# Each viseme = {source_shape: weight}. Values near 1.0 (e.g., 0.9998) avoid float edge cases.
# Source: absolute-quantum/cats-blender-plugin/tools/viseme.py
VISEME_BLEND_WEIGHTS = {
    "vrc.v_sil": {"mouth_a": 0.0002, "mouth_ch": 0.0002},
    "vrc.v_pp":  {"mouth_a": 0.0004, "mouth_o": 0.0004},
    "vrc.v_ff":  {"mouth_a": 0.2, "mouth_ch": 0.4},
    "vrc.v_th":  {"mouth_a": 0.4, "mouth_o": 0.15},
    "vrc.v_dd":  {"mouth_a": 0.3, "mouth_ch": 0.7},
    "vrc.v_kk":  {"mouth_a": 0.7, "mouth_ch": 0.4},
    "vrc.v_ch":  {"mouth_ch": 0.9996},
    "vrc.v_ss":  {"mouth_ch": 0.8},
    "vrc.v_nn":  {"mouth_a": 0.2, "mouth_ch": 0.7},
    "vrc.v_rr":  {"mouth_o": 0.3, "mouth_ch": 0.5},
    "vrc.v_aa":  {"mouth_a": 0.9998},
    "vrc.v_e":   {"mouth_o": 0.3, "mouth_ch": 0.7},
    "vrc.v_ih":  {"mouth_a": 0.5, "mouth_ch": 0.2},
    "vrc.v_oh":  {"mouth_a": 0.2, "mouth_o": 0.8},
    "vrc.v_ou":  {"mouth_o": 0.9994},
}

# FBX export settings optimized for VRChat
VRC_FBX_EXPORT_SETTINGS = {
    "filepath": "",  # Set at export time
    "use_selection": False,
    "apply_scale_options": "FBX_SCALE_ALL",
    "axis_forward": "-Z",
    "axis_up": "Y",
    "use_mesh_modifiers": True,
    "mesh_smooth_type": "FACE",
    "add_leaf_bones": False,  # Critical: leaf bones confuse Unity
    "bake_anim": False,
    "use_armature_deform_only": False,
    "bake_space_transform": False,
}

# FBX import settings for different source conventions
VRC_FBX_IMPORT_PRESETS = {
    "default": {
        "axis_forward": "-Y",
        "axis_up": "Z",
        "automatic_bone_orientation": False,
        "force_connect_children": False,
        "ignore_leaf_bones": True,
    },
    "unity": {
        # FBX exported from Unity uses -Z forward, Y up
        "axis_forward": "-Z",
        "axis_up": "Y",
        "automatic_bone_orientation": False,
        "force_connect_children": False,
        "ignore_leaf_bones": True,
    },
    "mixamo": {
        "axis_forward": "-Y",
        "axis_up": "Z",
        "automatic_bone_orientation": True,
        "force_connect_children": False,
        "ignore_leaf_bones": True,
    },
    "mmd": {
        # MMD/PMX-converted FBX often has disconnected bone chains
        "axis_forward": "-Y",
        "axis_up": "Z",
        "automatic_bone_orientation": False,
        "force_connect_children": True,
        "ignore_leaf_bones": True,
    },
}

# Common accessory attachment bone targets
ACCESSORY_BONE_TARGETS = {
    "hat": "Head",
    "glasses": "Head",
    "earring_l": "Head",
    "earring_r": "Head",
    "necklace": "Neck",
    "backpack": "Chest",
    "belt": "Hips",
    "shoe_l": "Left_Foot",
    "shoe_r": "Right_Foot",
    "glove_l": "Left_Hand",
    "glove_r": "Right_Hand",
    "watch": "Left_Hand",
    "weapon_r": "Right_Hand",
    "weapon_l": "Left_Hand",
    "tail": "Hips",
    "wings": "Chest",
}

# ─── VRC Expression Parameters ───
# Parameter memory budget: 256 bits total (synced across network)
# Types: bool (1 bit), int (8 bits), float (8 bits)
VRC_BUILTIN_PARAMETERS = {
    # These are auto-provided by VRC, do NOT define them in your menu
    "IsLocal": {"type": "bool", "bits": 0},
    "Viseme": {"type": "int", "bits": 0},
    "Voice": {"type": "float", "bits": 0},
    "GestureLeft": {"type": "int", "bits": 0},
    "GestureRight": {"type": "int", "bits": 0},
    "GestureLeftWeight": {"type": "float", "bits": 0},
    "GestureRightWeight": {"type": "float", "bits": 0},
    "AngularY": {"type": "float", "bits": 0},
    "VelocityX": {"type": "float", "bits": 0},
    "VelocityY": {"type": "float", "bits": 0},
    "VelocityZ": {"type": "float", "bits": 0},
    "VelocityMagnitude": {"type": "float", "bits": 0},
    "Upright": {"type": "float", "bits": 0},
    "Grounded": {"type": "bool", "bits": 0},
    "Seated": {"type": "bool", "bits": 0},
    "AFK": {"type": "bool", "bits": 0},
    "TrackingType": {"type": "int", "bits": 0},
    "VRMode": {"type": "int", "bits": 0},
    "MuteSelf": {"type": "bool", "bits": 0},
    "InStation": {"type": "bool", "bits": 0},
    "Earmuffs": {"type": "bool", "bits": 0},
    "IsOnFriendsList": {"type": "bool", "bits": 0},
    "ScaleModified": {"type": "bool", "bits": 0},
    "ScaleFactor": {"type": "float", "bits": 0},
    "ScaleFactorInverse": {"type": "float", "bits": 0},
    "EyeHeightAsMeters": {"type": "float", "bits": 0},
    "EyeHeightAsPercent": {"type": "float", "bits": 0},
}

VRC_PARAM_BITS = {"bool": 1, "int": 8, "float": 8}
VRC_MAX_MEMORY_BITS = 256

# Expression Menu control types
VRC_MENU_CONTROL_TYPES = [
    "Button",         # Momentary press, sets param to value while held
    "Toggle",         # On/off switch, toggles bool parameter
    "SubMenu",        # Opens a sub-menu
    "TwoAxisPuppet",  # Joystick control, 2 float params (-1 to 1)
    "FourAxisPuppet", # 4-direction control, 4 float params (0 to 1)
    "RadialPuppet",   # Radial dial, 1 float param (0 to 1)
]

# Gesture IDs (for GestureLeft / GestureRight parameters)
VRC_GESTURES = {
    0: "Neutral",
    1: "Fist",
    2: "HandOpen",
    3: "FingerPoint",
    4: "Victory",
    5: "RockNRoll",
    6: "HandGun",
    7: "ThumbsUp",
}

# ─── VRC Playable Layers ───
# Each layer has a specific purpose in the Animator Controller
VRC_PLAYABLE_LAYERS = {
    "Base":     "Locomotion — walking, running, jumping, falling. Usually default.",
    "Additive": "Additive on top of Base — breathing, idle variations.",
    "Gesture":  "Hand gestures & finger poses. Driven by GestureLeft/GestureRight.",
    "Action":   "Full-body overrides — emotes, AFK animation. Highest priority.",
    "FX":       "Everything else — toggles, effects, material swaps, blendshapes. Most customization here.",
}

# ─── VRC Contact System ───
VRC_CONTACT_COLLISION_TAGS = [
    "Head", "Torso", "Hand", "Foot", "Finger",
    "Custom",  # User-defined tag string
]

VRC_CONTACT_RECEIVER_TYPES = [
    "Constant",   # Always outputs a value based on number of contacts
    "OnEnter",    # Triggers once when contact first touches
    "Proximity",  # Outputs 0-1 based on distance (closest contact)
]

# Standard contact setups for common interactive features
VRC_CONTACT_PRESETS = {
    "headpat": {
        "sender": {"position": [0, 0.1, 0], "parent_bone": "Head", "radius": 0.15, "tags": ["Head"]},
        "receiver": {"position": [0, 0.12, 0], "parent_bone": "Head", "radius": 0.2,
                     "tags": ["Hand", "Finger"], "receiver_type": "Proximity",
                     "parameter": "Headpat_Proximity"},
    },
    "boop": {
        "sender": {"position": [0, 0.03, 0.06], "parent_bone": "Head", "radius": 0.03, "tags": ["Head"]},
        "receiver": {"position": [0, 0.03, 0.07], "parent_bone": "Head", "radius": 0.05,
                     "tags": ["Finger"], "receiver_type": "OnEnter",
                     "parameter": "Boop_Trigger"},
    },
    "handshake": {
        "sender": {"position": [0, 0, 0], "parent_bone": "Right_Hand", "radius": 0.08, "tags": ["Hand"]},
        "receiver": {"position": [0, 0, 0], "parent_bone": "Right_Hand", "radius": 0.1,
                     "tags": ["Hand"], "receiver_type": "Proximity",
                     "parameter": "Handshake_Proximity"},
    },
    "hug": {
        "sender": {"position": [0, 0, 0], "parent_bone": "Chest", "radius": 0.25, "tags": ["Torso"]},
        "receiver": {"position": [0, 0, 0], "parent_bone": "Chest", "radius": 0.3,
                     "tags": ["Torso", "Hand"], "receiver_type": "Proximity",
                     "parameter": "Hug_Proximity"},
    },
}

# ─── VRC PhysBone Parameters ───
VRC_PHYSBONE_DEFAULTS = {
    "pull": 0.2,          # Return to rest pose strength (0-1)
    "spring": 0.2,        # Springiness / bounciness (0-1)
    "stiffness": 0.2,     # Resistance to movement (0-1)
    "gravity": 0.0,       # Gravity multiplier (-1 to 1, negative = upward)
    "gravity_falloff": 0.0,  # How much gravity decreases along chain (0-1)
    "immobile_type": "All",  # "All" or "World" — what counts as immobile
    "immobile": 0.0,      # How much the root is immobile (0-1)
    "max_angle_x": 180,   # Angle limit (0-180)
    "max_angle_z": 180,
    "radius": 0.0,        # Collision radius
    "allow_collision": True,
    "allow_grabbing": True,
    "allow_posing": True,
    "grab_movement": 0.5,
    "snap_to_hand": False,
    "max_stretch": 0.0,   # 0 = no stretch, 1 = 2x length
    "is_animated": False,
}

# PhysBone presets for common use cases
VRC_PHYSBONE_PRESETS = {
    "hair_long": {"pull": 0.15, "spring": 0.3, "stiffness": 0.1, "gravity": 0.3,
                  "max_angle_x": 90, "max_angle_z": 45, "radius": 0.02},
    "hair_short": {"pull": 0.3, "spring": 0.4, "stiffness": 0.4, "gravity": 0.15,
                   "max_angle_x": 45, "max_angle_z": 30, "radius": 0.015},
    "tail": {"pull": 0.2, "spring": 0.25, "stiffness": 0.15, "gravity": 0.2,
             "max_angle_x": 120, "max_angle_z": 120, "radius": 0.03,
             "allow_grabbing": True, "allow_posing": True},
    "ears": {"pull": 0.4, "spring": 0.5, "stiffness": 0.3, "gravity": 0.05,
             "max_angle_x": 40, "max_angle_z": 40, "radius": 0.02},
    "skirt": {"pull": 0.15, "spring": 0.2, "stiffness": 0.2, "gravity": 0.4,
              "max_angle_x": 60, "max_angle_z": 30, "radius": 0.03},
    "breast": {"pull": 0.3, "spring": 0.4, "stiffness": 0.2, "gravity": 0.3,
               "max_angle_x": 30, "max_angle_z": 20, "radius": 0.05,
               "allow_grabbing": False},
    "ribbon": {"pull": 0.1, "spring": 0.15, "stiffness": 0.05, "gravity": 0.5,
               "max_angle_x": 150, "max_angle_z": 90, "radius": 0.01},
    "chain_accessory": {"pull": 0.2, "spring": 0.1, "stiffness": 0.0, "gravity": 0.8,
                        "max_angle_x": 180, "max_angle_z": 180, "radius": 0.005,
                        "allow_grabbing": True},
}

# ─── Avatar Dynamics Budget (per performance rank) ───
# VRC_DYNAMICS_LIMITS — derived from RANK_LIMITS to avoid duplication
# Access via RANK_LIMITS["pc"]["good"]["physbone_components"] etc.
# Kept as alias for backward compatibility
VRC_DYNAMICS_LIMITS = {
    platform: {
        rank: {k: v for k, v in limits.items()
               if k in ("physbone_components", "physbone_transforms", "physbone_colliders",
                         "physbone_collision_check", "contacts", "constraints", "constraint_depth")}
        for rank, limits in ranks.items()
    }
    for platform, ranks in RANK_LIMITS.items()
}
