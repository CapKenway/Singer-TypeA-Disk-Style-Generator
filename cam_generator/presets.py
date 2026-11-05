"""
Standard Historic Stitch Profile Presets for Singer Type A Sewing Machine Cams.
Singer 'Fashion Discs' (Type A) control the bight deflection of the needle
across an 18-stitch cycle.
"""

from typing import Dict, List, Any

PRESETS: Dict[str, Dict[str, Any]] = {
    'disc_38': {
        'id': 'disc_38',
        'preset_number': '38',
        'name': 'Disc #38 / Part #276338',
        'description': 'Authentic Singer Fashion Disc #38 (Part #276338): 6-tooth alternating square dwell blocks (24 stitches) matching the vintage OEM disc photo.',
        'category': 'OEM Disc #38',
        'steps': [12, 12, 0, 0, 12, 12, 0, 0, 12, 12, 0, 0, 12, 12, 0, 0, 12, 12, 0, 0, 12, 12, 0, 0],
    },
    'oem_squares': {
        'id': 'oem_squares',
        'preset_number': '38A',
        'name': 'OEM Alternating Squares (18-Stitch)',
        'description': '18-stitch Singer Type A disc with alternating high and low square dwell blocks.',
        'category': 'OEM Vintage',
        'steps': [12, 12, 0, 0, 12, 12, 0, 0, 12, 12, 0, 0, 12, 12, 0, 0, 12, 12],
    },
    'square_wave': {
        'id': 'square_wave',
        'preset_number': '1S',
        'name': 'OEM Stepped Teeth (Single Step)',
        'description': 'Alternating single stitch high/low plateaus with authentic squared-off dwell flats.',
        'category': 'OEM Vintage',
        'steps': [12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0],
    },
    'zigzag': {
        'id': 'zigzag',
        'preset_number': '1',
        'name': 'Plain Zig-Zag (Cam #1)',
        'description': 'Standard wide zig-zag alternating left and right bight every stitch.',
        'category': 'Basic Utility',
        'steps': [0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12],
    },
    'blind_hem': {
        'id': 'blind_hem',
        'preset_number': '3',
        'name': 'Blind Hem / Blind Stitch (Cam #3)',
        'description': '5 straight utility stitches followed by 1 wide bight bite into the fold.',
        'category': 'Basic Utility',
        'steps': [0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 12],
    },
    'tricot': {
        'id': 'tricot',
        'preset_number': '2',
        'name': '3-Step Zig-Zag / Tricot (Cam #2)',
        'description': 'Evenly stepped multi-stitch zig-zag for elastic and stretch knits.',
        'category': 'Stretch / Knit',
        'steps': [0, 4, 8, 12, 8, 4, 0, 4, 8, 12, 8, 4, 0, 4, 8, 12, 8, 4],
    },
    'scallop': {
        'id': 'scallop',
        'preset_number': '4',
        'name': 'Scallop (Left Needle - Cam #4)',
        'description': 'Left-anchored scallop: baseline at Left (0), bulging outward to Right (12).',
        'category': 'Decorative (Left)',
        'needle_position': 'L',
        'steps': [0, 2, 6, 10, 12, 10, 6, 2, 0, 0, 2, 6, 10, 12, 10, 6, 2, 0],
    },
    'scallop_center': {
        'id': 'scallop_center',
        'preset_number': '4C',
        'name': 'Scallop / Wave (Center Needle)',
        'description': 'Center needle scallop: user commands Center to Right (0 to 12); machine automatically alternates to Left.',
        'category': 'Decorative (Center)',
        'needle_position': 'C',
        'steps': [0, 2, 6, 10, 12, 10, 6, 2, 0, 0, 2, 6, 10, 12, 10, 6, 2, 0],
    },
    'scallop_right': {
        'id': 'scallop_right',
        'preset_number': '4R',
        'name': 'Scallop (Right Needle)',
        'description': 'Right-anchored scallop: baseline at Right (12), bulging inward to Left (0).',
        'category': 'Decorative (Right)',
        'needle_position': 'R',
        'steps': [12, 10, 6, 2, 0, 2, 6, 10, 12, 12, 10, 6, 2, 0, 2, 6, 10, 12],
    },
    'arrowhead': {
        'id': 'arrowhead',
        'preset_number': '5',
        'name': 'Arrowhead / Domino (Cam #5)',
        'description': 'Distinct geometric chevron points creating triangular arrowhead patterns.',
        'category': 'Decorative',
        'steps': [0, 0, 4, 8, 12, 8, 4, 0, 0, 0, 0, 4, 8, 12, 8, 4, 0, 0],
    },
    'sawtooth': {
        'id': 'sawtooth',
        'preset_number': '6',
        'name': 'Ramp / Sawtooth',
        'description': 'Progressive ramp increase with sharp drop-offs for directional stitching.',
        'category': 'Geometric',
        'steps': [0, 2, 5, 8, 10, 12, 0, 2, 5, 8, 10, 12, 0, 2, 5, 8, 10, 12],
    },
    'pennant': {
        'id': 'pennant',
        'preset_number': '10',
        'name': 'Banner / Pennant (Cam #10)',
        'description': 'Compound stitch: thin straight stem followed by dense filled satin flag block.',
        'category': 'Compound (Satin+Line)',
        'steps': [0, 0, 0, 0, 0, 12, 0, 12, 0, 12, 0, 12, 0, 0, 0, 0, 0, 0],
    },
    'straight': {
        'id': 'straight',
        'preset_number': '0',
        'name': 'Straight Stitch (Center)',
        'description': 'Zero bight deflection disk for centered utility straight sewing.',
        'category': 'Basic Utility',
        'needle_position': 'C',
        'steps': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
}

DEFAULT_PRESET_ID = 'zigzag'


def get_preset(preset_id: str) -> Dict[str, Any]:
    """Retrieves a preset dictionary by ID or defaults to zigzag."""
    return PRESETS.get(preset_id, PRESETS[DEFAULT_PRESET_ID])

