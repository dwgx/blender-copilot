"""
Anatomy constants and reference data for professional sculpting.
Used by sculpt_advanced_tools.py for anatomy-aware operations.

Sources: anatomy textbooks, VRChat avatar conventions, anime/stylized proportions.
"""

# ══════════════════════════════════════════════════════════════
#  HEAD / FACE PROPORTIONS
# ══════════════════════════════════════════════════════════════

# Realistic face proportions (as fraction of head height)
FACE_PROPORTIONS_REALISTIC = {
    "hairline_to_brow": 1/3,      # Top third
    "brow_to_nose_base": 1/3,     # Middle third
    "nose_base_to_chin": 1/3,     # Bottom third
    # Horizontal fifths (as fraction of head width)
    "eye_width": 1/5,             # Each eye = 1/5 head width
    "inter_eye": 1/5,             # Distance between eyes = 1 eye width
    "nose_width": 1/5,            # Nose width ≈ inter-eye distance
    "mouth_width": 0.4,           # Mouth ≈ distance between iris centers
    # Depth
    "ear_top_aligns": "brow",
    "ear_bottom_aligns": "nose_base",
}

# Anime / VRChat stylized proportions
FACE_PROPORTIONS_ANIME = {
    "eye_vertical_pos": 0.45,     # Eyes lower than realistic (45% from top)
    "eye_size_ratio": 1.4,        # 1.4x larger than realistic
    "forehead_ratio": 0.38,       # Larger forehead
    "chin_ratio": 0.22,           # Smaller chin
    "nose_size": 0.4,             # Minimal nose (40% of realistic)
    "mouth_vertical": 0.72,       # Mouth higher relative to chin
    "face_width_ratio": 0.85,     # Narrower face
    "jaw_roundness": 0.7,         # Rounder jaw (0=square, 1=round)
}

# ══════════════════════════════════════════════════════════════
#  BODY PROPORTIONS (in head-units)
# ══════════════════════════════════════════════════════════════

BODY_PROPORTIONS = {
    "realistic_adult": {
        "total_height": 7.5,       # 7.5 heads tall
        "shoulder_width": 2.0,     # 2 heads wide (male), 1.6 (female)
        "hip_width": 1.5,          # 1.5 heads (male), 1.6 (female)
        "torso_length": 3.0,       # Chin to crotch = 3 heads
        "leg_length": 3.5,         # Crotch to sole = 3.5 heads
        "arm_length": 3.0,         # Shoulder to fingertip = 3 heads
        "hand_length": 0.85,       # Hand = 0.85 head height
        "foot_length": 1.0,        # Foot ≈ 1 head length
        "navel_at": 4.0,           # 4 heads from top
        "crotch_at": 4.5,          # Midpoint at crotch (female slightly higher)
        "knee_at": 5.75,           # 5.75 heads from top
        "elbow_at": 3.0,           # Elbow at navel level
        "wrist_at": 4.5,           # Wrist at crotch level
    },
    "anime_5head": {
        "total_height": 5.5,       # VRChat avatar standard
        "shoulder_width": 1.6,
        "hip_width": 1.3,
        "torso_length": 2.0,
        "leg_length": 2.5,
        "arm_length": 2.2,
        "hand_length": 0.6,
        "foot_length": 0.7,
        "head_size_multiplier": 1.35,  # Larger head vs body
    },
    "chibi_3head": {
        "total_height": 3.0,
        "shoulder_width": 1.2,
        "hip_width": 1.0,
        "torso_length": 1.0,
        "leg_length": 1.0,
        "arm_length": 1.2,
        "head_size_multiplier": 2.0,
    },
}

# ══════════════════════════════════════════════════════════════
#  BONE LANDMARKS (surface positions relative to body part)
# ══════════════════════════════════════════════════════════════

# These define where bones are close to the surface and create
# visible landmarks in sculpting. Positions as (x, y, z) offsets
# from body part center, normalized to part size.

BONE_LANDMARKS = {
    "head": {
        "brow_ridge":       {"pos": (0.0, 0.9, 0.65), "hardness": 0.8},
        "cheekbone":        {"pos": (0.45, 0.7, 0.45), "hardness": 0.7},
        "nasal_bone":       {"pos": (0.0, 0.85, 0.55), "hardness": 0.6},
        "chin":             {"pos": (0.0, 0.7, 0.0), "hardness": 0.8},
        "jaw_angle":        {"pos": (0.45, 0.5, 0.15), "hardness": 0.7},
        "temporal_ridge":   {"pos": (0.4, 0.9, 0.55), "hardness": 0.5},
        "occipital":        {"pos": (0.0, -0.8, 0.45), "hardness": 0.6},
        "mastoid_process":  {"pos": (0.35, -0.5, 0.2), "hardness": 0.7},
    },
    "torso": {
        "clavicle":         {"pos": (0.3, 0.6, 0.95), "hardness": 0.8},
        "sternum":          {"pos": (0.0, 0.5, 0.9), "hardness": 0.7},
        "acromion":         {"pos": (0.5, 0.6, 0.85), "hardness": 0.9},
        "scapula_spine":    {"pos": (0.3, -0.5, 0.85), "hardness": 0.7},
        "iliac_crest":      {"pos": (0.35, 0.1, 0.0), "hardness": 0.8},
        "asis":             {"pos": (0.3, 0.3, 0.05), "hardness": 0.7},  # anterior superior iliac spine
        "ribcage_bottom":   {"pos": (0.2, 0.4, 0.35), "hardness": 0.6},
        "sacrum":           {"pos": (0.0, -0.4, 0.0), "hardness": 0.5},
        "spine_c7":         {"pos": (0.0, -0.5, 0.95), "hardness": 0.8},
    },
    "arm": {
        "lateral_epicondyle":  {"pos": (0.5, 0.0, 0.5), "hardness": 0.8},
        "medial_epicondyle":   {"pos": (-0.5, 0.0, 0.5), "hardness": 0.8},
        "olecranon":           {"pos": (0.0, -0.8, 0.5), "hardness": 0.9},
        "radial_head":         {"pos": (0.4, 0.3, 0.5), "hardness": 0.6},
        "ulna_shaft":          {"pos": (-0.3, -0.5, 0.3), "hardness": 0.7},
        "radial_styloid":      {"pos": (0.4, 0.0, 0.0), "hardness": 0.8},
        "ulnar_styloid":       {"pos": (-0.4, 0.0, 0.0), "hardness": 0.8},
    },
    "leg": {
        "patella":          {"pos": (0.0, 0.8, 0.5), "hardness": 0.9},
        "tibial_tuberosity": {"pos": (0.0, 0.7, 0.45), "hardness": 0.7},
        "tibia_shaft":      {"pos": (0.1, 0.5, 0.2), "hardness": 0.8},
        "medial_malleolus": {"pos": (-0.3, 0.0, 0.0), "hardness": 0.9},
        "lateral_malleolus": {"pos": (0.3, 0.0, 0.0), "hardness": 0.9},
        "fibula_head":      {"pos": (0.3, 0.6, 0.5), "hardness": 0.6},
        "greater_trochanter": {"pos": (0.5, 0.0, 0.95), "hardness": 0.7},
    },
    "hand": {
        "knuckles_mcp":     {"pos": (0.0, 0.8, 0.7), "hardness": 0.8},
        "knuckles_pip":     {"pos": (0.0, 0.7, 0.5), "hardness": 0.7},
        "thumb_cmc":        {"pos": (0.5, 0.3, 0.7), "hardness": 0.6},
        "pisiform":         {"pos": (-0.4, 0.0, 0.7), "hardness": 0.7},
    },
    "foot": {
        "calcaneus":        {"pos": (0.0, -0.8, 0.0), "hardness": 0.8},
        "navicular":        {"pos": (-0.2, 0.2, 0.3), "hardness": 0.5},
        "metatarsal_heads": {"pos": (0.0, 0.8, 0.0), "hardness": 0.7},
        "medial_arch":      {"pos": (-0.2, 0.3, 0.0), "hardness": 0.3},
    },
}

# ══════════════════════════════════════════════════════════════
#  MUSCLE GROUPS (for sculpting passes)
# ══════════════════════════════════════════════════════════════

# Each muscle: origin/insertion zones, bulk direction, tension lines
# "form_impact" = how much it affects surface silhouette (0-1)

MUSCLE_GROUPS = {
    "head_neck": {
        "masseter":           {"form_impact": 0.7, "bulk_dir": "lateral", "region": "jaw"},
        "temporalis":         {"form_impact": 0.5, "bulk_dir": "lateral", "region": "temple"},
        "sternocleidomastoid": {"form_impact": 0.9, "bulk_dir": "diagonal", "region": "neck"},
        "trapezius_upper":    {"form_impact": 0.8, "bulk_dir": "up_lateral", "region": "neck_back"},
        "orbicularis_oculi":  {"form_impact": 0.3, "bulk_dir": "circular", "region": "eye"},
        "orbicularis_oris":   {"form_impact": 0.4, "bulk_dir": "circular", "region": "mouth"},
        "zygomaticus":        {"form_impact": 0.4, "bulk_dir": "diagonal", "region": "cheek"},
        "frontalis":          {"form_impact": 0.3, "bulk_dir": "vertical", "region": "forehead"},
        "platysma":           {"form_impact": 0.3, "bulk_dir": "down", "region": "neck_front"},
    },
    "torso_front": {
        "pectoralis_major":   {"form_impact": 0.9, "bulk_dir": "medial", "region": "chest"},
        "rectus_abdominis":   {"form_impact": 0.7, "bulk_dir": "vertical", "region": "abdomen"},
        "external_oblique":   {"form_impact": 0.6, "bulk_dir": "diagonal", "region": "side"},
        "serratus_anterior":  {"form_impact": 0.5, "bulk_dir": "lateral", "region": "ribcage_side"},
    },
    "torso_back": {
        "trapezius":          {"form_impact": 0.9, "bulk_dir": "medial", "region": "upper_back"},
        "latissimus_dorsi":   {"form_impact": 0.9, "bulk_dir": "lateral", "region": "mid_back"},
        "erector_spinae":     {"form_impact": 0.6, "bulk_dir": "vertical", "region": "spine"},
        "rhomboids":          {"form_impact": 0.4, "bulk_dir": "medial", "region": "mid_back"},
        "infraspinatus":      {"form_impact": 0.5, "bulk_dir": "lateral", "region": "scapula"},
        "teres_major":        {"form_impact": 0.5, "bulk_dir": "lateral", "region": "scapula_lower"},
    },
    "arm": {
        "deltoid_anterior":   {"form_impact": 0.8, "bulk_dir": "forward", "region": "shoulder_front"},
        "deltoid_lateral":    {"form_impact": 0.9, "bulk_dir": "lateral", "region": "shoulder_side"},
        "deltoid_posterior":  {"form_impact": 0.7, "bulk_dir": "backward", "region": "shoulder_back"},
        "biceps_brachii":     {"form_impact": 0.8, "bulk_dir": "up", "region": "upper_arm_front"},
        "triceps":            {"form_impact": 0.8, "bulk_dir": "up", "region": "upper_arm_back"},
        "brachialis":         {"form_impact": 0.5, "bulk_dir": "lateral", "region": "upper_arm_side"},
        "brachioradialis":    {"form_impact": 0.6, "bulk_dir": "forward", "region": "forearm_top"},
        "extensor_group":     {"form_impact": 0.5, "bulk_dir": "backward", "region": "forearm_back"},
        "flexor_group":       {"form_impact": 0.5, "bulk_dir": "forward", "region": "forearm_front"},
    },
    "leg": {
        "gluteus_maximus":    {"form_impact": 0.9, "bulk_dir": "backward", "region": "buttock"},
        "gluteus_medius":     {"form_impact": 0.7, "bulk_dir": "lateral", "region": "hip_side"},
        "quadriceps_rectus":  {"form_impact": 0.8, "bulk_dir": "forward", "region": "thigh_front"},
        "vastus_lateralis":   {"form_impact": 0.7, "bulk_dir": "lateral", "region": "thigh_outer"},
        "vastus_medialis":    {"form_impact": 0.6, "bulk_dir": "medial", "region": "thigh_inner_low"},
        "hamstrings":         {"form_impact": 0.7, "bulk_dir": "backward", "region": "thigh_back"},
        "sartorius":          {"form_impact": 0.4, "bulk_dir": "diagonal", "region": "thigh_inner"},
        "adductors":          {"form_impact": 0.5, "bulk_dir": "medial", "region": "thigh_inner"},
        "gastrocnemius":      {"form_impact": 0.8, "bulk_dir": "backward", "region": "calf"},
        "soleus":             {"form_impact": 0.5, "bulk_dir": "backward", "region": "calf_deep"},
        "tibialis_anterior":  {"form_impact": 0.5, "bulk_dir": "forward", "region": "shin"},
        "peroneus":           {"form_impact": 0.4, "bulk_dir": "lateral", "region": "shin_outer"},
        "tensor_fasciae_latae": {"form_impact": 0.5, "bulk_dir": "lateral", "region": "hip_front"},
        "it_band":            {"form_impact": 0.4, "bulk_dir": "lateral", "region": "thigh_outer_low"},
    },
}

# ══════════════════════════════════════════════════════════════
#  FAT PAD LOCATIONS (subcutaneous fat accumulation zones)
# ══════════════════════════════════════════════════════════════

FAT_PADS = {
    "face": {
        "buccal":       {"softness": 0.9, "region": "cheek_lower"},
        "malar":        {"softness": 0.7, "region": "cheekbone_area"},
        "nasolabial":   {"softness": 0.8, "region": "nose_to_mouth"},
        "submental":    {"softness": 0.9, "region": "under_chin"},
    },
    "torso": {
        "breast":       {"softness": 0.9, "region": "chest"},
        "abdominal":    {"softness": 0.8, "region": "belly"},
        "love_handles": {"softness": 0.9, "region": "waist_side"},
        "lower_back":   {"softness": 0.7, "region": "lumbar"},
    },
    "limbs": {
        "inner_thigh":  {"softness": 0.8, "region": "thigh_inner"},
        "knee_medial":  {"softness": 0.5, "region": "knee_inner"},
        "upper_arm":    {"softness": 0.7, "region": "arm_inner"},
        "buttock":      {"softness": 0.9, "region": "glute"},
    },
}

# ══════════════════════════════════════════════════════════════
#  SKIN TENSION / WRINKLE LINES
# ══════════════════════════════════════════════════════════════

SKIN_TENSION_LINES = {
    "forehead_horizontal": {"direction": "horizontal", "depth": 0.3, "region": "forehead"},
    "glabellar":           {"direction": "vertical", "depth": 0.5, "region": "between_brows"},
    "crows_feet":          {"direction": "radial", "depth": 0.3, "region": "eye_outer"},
    "nasolabial_fold":     {"direction": "diagonal", "depth": 0.6, "region": "nose_to_mouth"},
    "marionette":          {"direction": "vertical", "depth": 0.4, "region": "mouth_corner_down"},
    "neck_rings":          {"direction": "horizontal", "depth": 0.3, "region": "neck"},
    "elbow_crease":        {"direction": "horizontal", "depth": 0.4, "region": "elbow_front"},
    "wrist_creases":       {"direction": "horizontal", "depth": 0.3, "region": "wrist"},
    "knuckle_creases":     {"direction": "horizontal", "depth": 0.5, "region": "finger_joints"},
    "knee_crease":         {"direction": "horizontal", "depth": 0.3, "region": "knee_back"},
}

# ══════════════════════════════════════════════════════════════
#  SCULPT PASS DEFINITIONS (systematic workflow)
# ══════════════════════════════════════════════════════════════

SCULPT_PASSES = {
    "primary_forms": {
        "description": "Big shapes — silhouette, mass distribution, gesture",
        "brush_types": ["CLAY", "GRAB", "ELASTIC_DEFORM", "SMOOTH"],
        "strength_range": (0.5, 1.0),
        "radius_multiplier": 3.0,    # Large brush relative to feature
        "subdiv_level": 1,           # Low subdiv for big forms
        "targets": [
            "Overall silhouette",
            "Head mass and tilt",
            "Torso ribcage vs pelvis tilt",
            "Limb gesture and rhythm",
            "Weight distribution",
        ],
    },
    "secondary_forms": {
        "description": "Muscle groups, fat pads, major anatomical landmarks",
        "brush_types": ["CLAY_STRIPS", "DRAW", "CREASE", "FLATTEN", "SMOOTH"],
        "strength_range": (0.3, 0.7),
        "radius_multiplier": 1.5,
        "subdiv_level": 2,
        "targets": [
            "Major muscle volumes",
            "Bone landmark suggestions",
            "Fat pad volumes",
            "Joint transitions",
            "Gender-specific forms",
        ],
    },
    "tertiary_forms": {
        "description": "Surface detail — wrinkles, pores, subtle transitions",
        "brush_types": ["DRAW_SHARP", "CREASE", "PINCH", "LAYER", "SMOOTH"],
        "strength_range": (0.1, 0.4),
        "radius_multiplier": 0.5,
        "subdiv_level": 4,
        "targets": [
            "Skin wrinkles and folds",
            "Tendon suggestions",
            "Subtle bone landmarks",
            "Skin stretching at joints",
            "Stylized detail (if applicable)",
        ],
    },
}

# ══════════════════════════════════════════════════════════════
#  ALL BLENDER SCULPT BRUSH TYPES
# ══════════════════════════════════════════════════════════════

ALL_SCULPT_BRUSHES = {
    # Standard brushes
    "DRAW":              {"category": "build", "description": "Move vertices along normals"},
    "DRAW_SHARP":        {"category": "build", "description": "Sharp draw with hard falloff"},
    "CLAY":              {"category": "build", "description": "Add clay with flat plane limit"},
    "CLAY_STRIPS":       {"category": "build", "description": "Clay strips with square tip"},
    "CLAY_THUMB":        {"category": "build", "description": "Flatten while dragging"},
    "LAYER":             {"category": "build", "description": "Consistent height layer"},
    "INFLATE":           {"category": "volume", "description": "Push along normals outward"},
    "BLOB":              {"category": "volume", "description": "Spherical inflation"},
    "CREASE":            {"category": "detail", "description": "Sharp indent/ridge"},
    "SMOOTH":            {"category": "smooth", "description": "Average vertex positions"},
    "FLATTEN":           {"category": "smooth", "description": "Push to average plane"},
    "FILL":              {"category": "smooth", "description": "Raise low areas to plane"},
    "SCRAPE":            {"category": "smooth", "description": "Lower high areas to plane"},
    "MULTIPLANE_SCRAPE": {"category": "smooth", "description": "Two-angled plane scrape"},
    "PINCH":             {"category": "detail", "description": "Pull toward stroke center"},
    # Deform brushes
    "GRAB":              {"category": "deform", "description": "Move vertices with mouse"},
    "ELASTIC_DEFORM":    {"category": "deform", "description": "Physically-based elastic"},
    "SNAKE_HOOK":        {"category": "deform", "description": "Pull along stroke path"},
    "THUMB":             {"category": "deform", "description": "Smear in stroke direction"},
    "POSE":              {"category": "deform", "description": "IK-based rotation/scale"},
    "NUDGE":             {"category": "deform", "description": "Push in stroke direction"},
    "ROTATE":            {"category": "deform", "description": "Spin around stroke center"},
    "TOPOLOGY":          {"category": "deform", "description": "Slide/relax along surface"},
    "BOUNDARY":          {"category": "deform", "description": "Deform mesh boundaries"},
    # Special brushes
    "CLOTH":             {"category": "special", "description": "Cloth dynamics during stroke"},
    "SIMPLIFY":          {"category": "special", "description": "Collapse edges (dyntopo)"},
    "MASK":              {"category": "mask", "description": "Paint mask values"},
    "DRAW_FACE_SETS":    {"category": "mask", "description": "Paint face set IDs"},
    "DISPLACEMENT_ERASER": {"category": "multires", "description": "Erase multires displacement"},
    "DISPLACEMENT_SMEAR":  {"category": "multires", "description": "Smear multires displacement"},
    "PAINT":             {"category": "color", "description": "Vertex color painting"},
    "SMEAR":             {"category": "color", "description": "Blend vertex colors"},
}

# ══════════════════════════════════════════════════════════════
#  FALLOFF CURVES (mathematical definitions)
# ══════════════════════════════════════════════════════════════

# Each curve: name → Python expression where `t` is 0..1 (0=center, 1=edge)
FALLOFF_CURVES = {
    "SMOOTH":         "t * t * (3.0 - 2.0 * t)",          # Smoothstep (default)
    "SMOOTHER":       "t*t*t*(t*(t*6-15)+10)",             # Perlin smootherstep
    "SPHERE":         "(1.0 - t*t) ** 0.5",                # Spherical
    "ROOT":           "t ** 0.5",                           # Square root (soft)
    "SHARP":          "t * t",                              # Quadratic (sharp peak)
    "LINEAR":         "t",                                  # Linear
    "CONSTANT":       "1.0",                                # Constant (flat)
    "INVERSE_SQUARE": "1.0 / (1.0 + t*t*4)",               # Inverse square
    "POW4":           "t * t * t * t",                      # Very sharp peak
    "GAUSSIAN":       "__import__('math').exp(-t*t*4)",     # Gaussian bell
    "SPIKE":          "max(0, 1.0 - abs(t) * 4) if t < 0.25 else 0",  # Narrow spike
}

# ══════════════════════════════════════════════════════════════
#  MESH FILTER TYPES (whole-mesh deformations)
# ══════════════════════════════════════════════════════════════

MESH_FILTERS = {
    "SMOOTH":           "Average vertex positions — reduce noise",
    "SCALE":            "Scale mesh from pivot",
    "INFLATE":          "Push vertices along normals",
    "SPHERE":           "Push toward spherical shape",
    "RANDOM":           "Random displacement (noise)",
    "RELAX":            "Relax mesh topology (equalize edge lengths)",
    "RELAX_FACE_SETS":  "Relax within face set boundaries",
    "SURFACE_SMOOTH":   "Smooth preserving volume/features",
    "SHARPEN":          "Enhance existing detail",
    "ENHANCE_DETAILS":  "Amplify displacement from smooth version",
    "ERASE_DISPLACEMENT": "Remove multires displacement",
}

# ══════════════════════════════════════════════════════════════
#  STYLIZATION SCALES (how much to deviate from realistic)
# ══════════════════════════════════════════════════════════════

STYLE_PRESETS = {
    "realistic": {
        "proportion_scale": 1.0,
        "detail_level": 1.0,
        "edge_sharpness": 0.5,
        "form_simplification": 0.0,
        "muscle_definition": 1.0,
        "fat_softness": 1.0,
    },
    "semi_realistic": {
        "proportion_scale": 1.1,      # Slightly idealized
        "detail_level": 0.7,
        "edge_sharpness": 0.4,
        "form_simplification": 0.2,
        "muscle_definition": 0.8,
        "fat_softness": 0.9,
    },
    "anime_standard": {              # VRChat typical
        "proportion_scale": 1.3,
        "detail_level": 0.3,
        "edge_sharpness": 0.6,        # Clean edges
        "form_simplification": 0.6,
        "muscle_definition": 0.2,
        "fat_softness": 0.5,
    },
    "chibi": {
        "proportion_scale": 2.0,
        "detail_level": 0.1,
        "edge_sharpness": 0.8,
        "form_simplification": 0.9,
        "muscle_definition": 0.0,
        "fat_softness": 0.3,
    },
}
