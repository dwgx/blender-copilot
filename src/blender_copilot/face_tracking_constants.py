# Face Tracking Constants — ARKit 52, VRCFT Unified Expressions,
# displacement recipes, and mapping tables.

# ═══════════════════════════════════════════════════════════════
# Apple ARKit 52 Blend Shapes (official standard)
# ═══════════════════════════════════════════════════════════════

ARKIT_BLEND_SHAPES = [
    # Eye (14)
    "eyeBlinkLeft", "eyeBlinkRight",
    "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight",
    "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight",
    "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight",
    # Jaw (4)
    "jawForward", "jawLeft", "jawRight", "jawOpen",
    # Mouth (24)
    "mouthClose",
    "mouthFunnel", "mouthPucker",
    "mouthLeft", "mouthRight",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthFrownLeft", "mouthFrownRight",
    "mouthDimpleLeft", "mouthDimpleRight",
    "mouthStretchLeft", "mouthStretchRight",
    "mouthRollLower", "mouthRollUpper",
    "mouthShrugLower", "mouthShrugUpper",
    "mouthPressLeft", "mouthPressRight",
    "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    # Nose (2)
    "noseSneerLeft", "noseSneerRight",
    # Cheek (3)
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    # Brow (5)
    "browDownLeft", "browDownRight",
    "browInnerUp",
    "browOuterUpLeft", "browOuterUpRight",
    # Tongue (1)
    "tongueOut",
]

# ═══════════════════════════════════════════════════════════════
# VRCFT Unified Expressions (VRCFaceTracking standard)
# Superset of ARKit — adds tongue detail, cheek detail, etc.
# ═══════════════════════════════════════════════════════════════

UNIFIED_EXPRESSIONS = [
    # Eye (14) — same as ARKit
    "EyeClosedLeft", "EyeClosedRight",
    "EyeSquintLeft", "EyeSquintRight",
    "EyeWideLeft", "EyeWideRight",
    "EyeLookUpLeft", "EyeLookUpRight",
    "EyeLookDownLeft", "EyeLookDownRight",
    "EyeLookInLeft", "EyeLookInRight",
    "EyeLookOutLeft", "EyeLookOutRight",
    # Eyelid extras (4)
    "EyeDilationLeft", "EyeDilationRight",
    "EyeConstrictLeft", "EyeConstrictRight",
    # Jaw (4)
    "JawOpen", "JawForward", "JawLeft", "JawRight",
    # Mouth — shape (16)
    "MouthClosed",
    "MouthUpperUpLeft", "MouthUpperUpRight",
    "MouthLowerDownLeft", "MouthLowerDownRight",
    "MouthSmileLeft", "MouthSmileRight",
    "MouthFrownLeft", "MouthFrownRight",
    "MouthStretchLeft", "MouthStretchRight",
    "MouthDimpleLeft", "MouthDimpleRight",
    "MouthPressLeft", "MouthPressRight",
    "MouthTightenerLeft", "MouthTightenerRight",
    # Mouth — lip (4)
    "LipPuckerLeft", "LipPuckerRight",
    "LipFunnelUpperLeft", "LipFunnelUpperRight",
    "LipFunnelLowerLeft", "LipFunnelLowerRight",
    "LipSuckUpperLeft", "LipSuckUpperRight",
    "LipSuckLowerLeft", "LipSuckLowerRight",
    # Mouth — roll (2)
    "MouthRollUpper", "MouthRollLower",
    # Cheek (5)
    "CheekPuffLeft", "CheekPuffRight",
    "CheekSquintLeft", "CheekSquintRight",
    "CheekSuckLeft", "CheekSuckRight",
    # Nose (2)
    "NoseSneerLeft", "NoseSneerRight",
    # Brow (6)
    "BrowDownLeft", "BrowDownRight",
    "BrowInnerUpLeft", "BrowInnerUpRight",
    "BrowOuterUpLeft", "BrowOuterUpRight",
    # Tongue (10)
    "TongueOut", "TongueUp", "TongueDown",
    "TongueLeft", "TongueRight",
    "TongueRoll", "TongueBendDown", "TongueCurlUp",
    "TongueSquish", "TongueFlat",
]

# ═══════════════════════════════════════════════════════════════
# ARKit → Unified Expressions mapping
# ═══════════════════════════════════════════════════════════════

ARKIT_TO_UNIFIED = {
    "eyeBlinkLeft": "EyeClosedLeft",
    "eyeBlinkRight": "EyeClosedRight",
    "eyeLookDownLeft": "EyeLookDownLeft",
    "eyeLookDownRight": "EyeLookDownRight",
    "eyeLookInLeft": "EyeLookInLeft",
    "eyeLookInRight": "EyeLookInRight",
    "eyeLookOutLeft": "EyeLookOutLeft",
    "eyeLookOutRight": "EyeLookOutRight",
    "eyeLookUpLeft": "EyeLookUpLeft",
    "eyeLookUpRight": "EyeLookUpRight",
    "eyeSquintLeft": "EyeSquintLeft",
    "eyeSquintRight": "EyeSquintRight",
    "eyeWideLeft": "EyeWideLeft",
    "eyeWideRight": "EyeWideRight",
    "jawForward": "JawForward",
    "jawLeft": "JawLeft",
    "jawRight": "JawRight",
    "jawOpen": "JawOpen",
    "mouthClose": "MouthClosed",
    "mouthFunnel": ["LipFunnelUpperLeft", "LipFunnelUpperRight",
                     "LipFunnelLowerLeft", "LipFunnelLowerRight"],
    "mouthPucker": ["LipPuckerLeft", "LipPuckerRight"],
    "mouthLeft": "MouthStretchLeft",
    "mouthRight": "MouthStretchRight",
    "mouthSmileLeft": "MouthSmileLeft",
    "mouthSmileRight": "MouthSmileRight",
    "mouthFrownLeft": "MouthFrownLeft",
    "mouthFrownRight": "MouthFrownRight",
    "mouthDimpleLeft": "MouthDimpleLeft",
    "mouthDimpleRight": "MouthDimpleRight",
    "mouthStretchLeft": "MouthStretchLeft",
    "mouthStretchRight": "MouthStretchRight",
    "mouthRollLower": "MouthRollLower",
    "mouthRollUpper": "MouthRollUpper",
    "mouthShrugLower": "MouthLowerDownLeft",  # approximate
    "mouthShrugUpper": "MouthUpperUpLeft",     # approximate
    "mouthPressLeft": "MouthPressLeft",
    "mouthPressRight": "MouthPressRight",
    "mouthLowerDownLeft": "MouthLowerDownLeft",
    "mouthLowerDownRight": "MouthLowerDownRight",
    "mouthUpperUpLeft": "MouthUpperUpLeft",
    "mouthUpperUpRight": "MouthUpperUpRight",
    "noseSneerLeft": "NoseSneerLeft",
    "noseSneerRight": "NoseSneerRight",
    "cheekPuff": ["CheekPuffLeft", "CheekPuffRight"],
    "cheekSquintLeft": "CheekSquintLeft",
    "cheekSquintRight": "CheekSquintRight",
    "browDownLeft": "BrowDownLeft",
    "browDownRight": "BrowDownRight",
    "browInnerUp": ["BrowInnerUpLeft", "BrowInnerUpRight"],
    "browOuterUpLeft": "BrowOuterUpLeft",
    "browOuterUpRight": "BrowOuterUpRight",
    "tongueOut": "TongueOut",
}

# ═══════════════════════════════════════════════════════════════
# Vertex Displacement Recipes for procedural ARKit generation
# Each recipe defines: affected region, direction, magnitude
# Magnitudes are relative to head height (scaled at runtime)
# ═══════════════════════════════════════════════════════════════

ARKIT_DISPLACEMENT_RECIPES = {
    # === EYE ===
    "eyeBlinkLeft": {
        "region": "upper_eyelid_l",
        "secondary_region": "lower_eyelid_l",
        "primary_direction": "DOWN",     # upper lid closes down
        "primary_magnitude": 0.6,
        "secondary_direction": "UP",     # lower lid rises slightly
        "secondary_magnitude": 0.15,
    },
    "eyeBlinkRight": {
        "region": "upper_eyelid_r",
        "secondary_region": "lower_eyelid_r",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.6,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.15,
    },
    "eyeLookDownLeft": {
        "region": "upper_eyelid_l",
        "secondary_region": "lower_eyelid_l",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.25,
        "secondary_direction": "DOWN",
        "secondary_magnitude": 0.1,
    },
    "eyeLookDownRight": {
        "region": "upper_eyelid_r",
        "secondary_region": "lower_eyelid_r",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.25,
        "secondary_direction": "DOWN",
        "secondary_magnitude": 0.1,
    },
    "eyeLookInLeft": {
        "region": "upper_eyelid_l",
        "primary_direction": "MEDIAL",
        "primary_magnitude": 0.05,
    },
    "eyeLookInRight": {
        "region": "upper_eyelid_r",
        "primary_direction": "MEDIAL",
        "primary_magnitude": 0.05,
    },
    "eyeLookOutLeft": {
        "region": "upper_eyelid_l",
        "primary_direction": "LATERAL",
        "primary_magnitude": 0.05,
    },
    "eyeLookOutRight": {
        "region": "upper_eyelid_r",
        "primary_direction": "LATERAL",
        "primary_magnitude": 0.05,
    },
    "eyeLookUpLeft": {
        "region": "upper_eyelid_l",
        "primary_direction": "UP",
        "primary_magnitude": 0.15,
    },
    "eyeLookUpRight": {
        "region": "upper_eyelid_r",
        "primary_direction": "UP",
        "primary_magnitude": 0.15,
    },
    "eyeSquintLeft": {
        "region": "lower_eyelid_l",
        "secondary_region": "cheek_l",
        "primary_direction": "UP",
        "primary_magnitude": 0.2,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.1,
    },
    "eyeSquintRight": {
        "region": "lower_eyelid_r",
        "secondary_region": "cheek_r",
        "primary_direction": "UP",
        "primary_magnitude": 0.2,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.1,
    },
    "eyeWideLeft": {
        "region": "upper_eyelid_l",
        "secondary_region": "brow_l",
        "primary_direction": "UP",
        "primary_magnitude": 0.3,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.15,
    },
    "eyeWideRight": {
        "region": "upper_eyelid_r",
        "secondary_region": "brow_r",
        "primary_direction": "UP",
        "primary_magnitude": 0.3,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.15,
    },
    # === JAW ===
    "jawForward": {
        "region": "jaw",
        "primary_direction": "FORWARD",
        "primary_magnitude": 0.15,
    },
    "jawLeft": {
        "region": "jaw",
        "primary_direction": "LEFT",
        "primary_magnitude": 0.1,
    },
    "jawRight": {
        "region": "jaw",
        "primary_direction": "RIGHT",
        "primary_magnitude": 0.1,
    },
    "jawOpen": {
        "region": "jaw",
        "secondary_region": "lower_lip",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.5,
        "secondary_direction": "DOWN",
        "secondary_magnitude": 0.3,
    },
    # === MOUTH ===
    "mouthClose": {
        "region": "lower_lip",
        "secondary_region": "upper_lip",
        "primary_direction": "UP",
        "primary_magnitude": 0.1,
        "secondary_direction": "DOWN",
        "secondary_magnitude": 0.05,
    },
    "mouthFunnel": {
        "region": "lips",
        "primary_direction": "FORWARD",
        "primary_magnitude": 0.2,
    },
    "mouthPucker": {
        "region": "lips",
        "primary_direction": "FORWARD",
        "primary_magnitude": 0.25,
        "contract": 0.3,  # lips contract inward
    },
    "mouthLeft": {
        "region": "lips",
        "primary_direction": "LEFT",
        "primary_magnitude": 0.15,
    },
    "mouthRight": {
        "region": "lips",
        "primary_direction": "RIGHT",
        "primary_magnitude": 0.15,
    },
    "mouthSmileLeft": {
        "region": "mouth_corner_l",
        "secondary_region": "cheek_l",
        "primary_direction": "UP_LATERAL",
        "primary_magnitude": 0.3,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.15,
    },
    "mouthSmileRight": {
        "region": "mouth_corner_r",
        "secondary_region": "cheek_r",
        "primary_direction": "UP_LATERAL",
        "primary_magnitude": 0.3,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.15,
    },
    "mouthFrownLeft": {
        "region": "mouth_corner_l",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.2,
    },
    "mouthFrownRight": {
        "region": "mouth_corner_r",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.2,
    },
    "mouthDimpleLeft": {
        "region": "mouth_corner_l",
        "primary_direction": "BACK",
        "primary_magnitude": 0.1,
    },
    "mouthDimpleRight": {
        "region": "mouth_corner_r",
        "primary_direction": "BACK",
        "primary_magnitude": 0.1,
    },
    "mouthStretchLeft": {
        "region": "mouth_corner_l",
        "primary_direction": "LATERAL",
        "primary_magnitude": 0.2,
    },
    "mouthStretchRight": {
        "region": "mouth_corner_r",
        "primary_direction": "LATERAL",
        "primary_magnitude": 0.2,
    },
    "mouthRollLower": {
        "region": "lower_lip",
        "primary_direction": "BACK_UP",
        "primary_magnitude": 0.15,
    },
    "mouthRollUpper": {
        "region": "upper_lip",
        "primary_direction": "BACK_DOWN",
        "primary_magnitude": 0.15,
    },
    "mouthShrugLower": {
        "region": "lower_lip",
        "primary_direction": "FORWARD_UP",
        "primary_magnitude": 0.1,
    },
    "mouthShrugUpper": {
        "region": "upper_lip",
        "primary_direction": "FORWARD_UP",
        "primary_magnitude": 0.1,
    },
    "mouthPressLeft": {
        "region": "mouth_corner_l",
        "primary_direction": "COMPRESS",
        "primary_magnitude": 0.1,
    },
    "mouthPressRight": {
        "region": "mouth_corner_r",
        "primary_direction": "COMPRESS",
        "primary_magnitude": 0.1,
    },
    "mouthLowerDownLeft": {
        "region": "lower_lip_l",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.15,
    },
    "mouthLowerDownRight": {
        "region": "lower_lip_r",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.15,
    },
    "mouthUpperUpLeft": {
        "region": "upper_lip_l",
        "primary_direction": "UP",
        "primary_magnitude": 0.15,
    },
    "mouthUpperUpRight": {
        "region": "upper_lip_r",
        "primary_direction": "UP",
        "primary_magnitude": 0.15,
    },
    # === NOSE ===
    "noseSneerLeft": {
        "region": "nose_l",
        "secondary_region": "upper_lip_l",
        "primary_direction": "UP",
        "primary_magnitude": 0.12,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.05,
    },
    "noseSneerRight": {
        "region": "nose_r",
        "secondary_region": "upper_lip_r",
        "primary_direction": "UP",
        "primary_magnitude": 0.12,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.05,
    },
    # === CHEEK ===
    "cheekPuff": {
        "region": "cheek_l",
        "secondary_region": "cheek_r",
        "primary_direction": "LATERAL",
        "primary_magnitude": 0.2,
        "secondary_direction": "LATERAL",
        "secondary_magnitude": 0.2,
    },
    "cheekSquintLeft": {
        "region": "cheek_l",
        "secondary_region": "lower_eyelid_l",
        "primary_direction": "UP",
        "primary_magnitude": 0.15,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.1,
    },
    "cheekSquintRight": {
        "region": "cheek_r",
        "secondary_region": "lower_eyelid_r",
        "primary_direction": "UP",
        "primary_magnitude": 0.15,
        "secondary_direction": "UP",
        "secondary_magnitude": 0.1,
    },
    # === BROW ===
    "browDownLeft": {
        "region": "brow_l",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.15,
    },
    "browDownRight": {
        "region": "brow_r",
        "primary_direction": "DOWN",
        "primary_magnitude": 0.15,
    },
    "browInnerUp": {
        "region": "brow_inner",
        "primary_direction": "UP",
        "primary_magnitude": 0.2,
    },
    "browOuterUpLeft": {
        "region": "brow_outer_l",
        "primary_direction": "UP",
        "primary_magnitude": 0.15,
    },
    "browOuterUpRight": {
        "region": "brow_outer_r",
        "primary_direction": "UP",
        "primary_magnitude": 0.15,
    },
    # === TONGUE ===
    "tongueOut": {
        "region": "tongue",
        "primary_direction": "FORWARD_DOWN",
        "primary_magnitude": 0.4,
    },
}

# ═══════════════════════════════════════════════════════════════
# Face vertex group names used for auto-detection
# ═══════════════════════════════════════════════════════════════

FACE_VERTEX_GROUPS = [
    # Eyelids
    "upper_eyelid_l", "upper_eyelid_r",
    "lower_eyelid_l", "lower_eyelid_r",
    # Brow
    "brow_l", "brow_r", "brow_inner", "brow_outer_l", "brow_outer_r",
    # Nose
    "nose_l", "nose_r", "nose_bridge", "nose_tip",
    # Lips
    "upper_lip", "lower_lip", "upper_lip_l", "upper_lip_r",
    "lower_lip_l", "lower_lip_r", "lips",
    # Mouth corners
    "mouth_corner_l", "mouth_corner_r",
    # Cheeks
    "cheek_l", "cheek_r",
    # Jaw
    "jaw", "chin",
    # Tongue
    "tongue",
]

# ═══════════════════════════════════════════════════════════════
# Direction vectors (relative, get scaled by magnitude at runtime)
# ═══════════════════════════════════════════════════════════════

DIRECTION_VECTORS = {
    "UP":           (0.0,  0.0,  1.0),
    "DOWN":         (0.0,  0.0, -1.0),
    "FORWARD":      (0.0, -1.0,  0.0),
    "BACK":         (0.0,  1.0,  0.0),
    "LEFT":         (-1.0, 0.0,  0.0),
    "RIGHT":        (1.0,  0.0,  0.0),
    "MEDIAL":       (1.0,  0.0,  0.0),   # toward center (flipped per side)
    "LATERAL":      (-1.0, 0.0,  0.0),   # away from center (flipped per side)
    "UP_LATERAL":   (-0.7, 0.0,  0.7),
    "FORWARD_UP":   (0.0, -0.7,  0.7),
    "FORWARD_DOWN": (0.0, -0.7, -0.7),
    "BACK_UP":      (0.0,  0.7,  0.7),
    "BACK_DOWN":    (0.0,  0.7, -0.7),
    "COMPRESS":     (0.0,  0.3, -0.3),
}
