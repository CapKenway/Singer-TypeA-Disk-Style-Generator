"""
Pure-Python Vector Stroke Font Engine for CNC & Laser CAD/CAM Export.

Converts arbitrary alphanumeric text into vector polylines and curves:
- Formats text along concentric circular arcs (bends letters to follow the spindle bore).
- Formats linear rotated text.
- Zero binary dependencies (pure Python math).
- Solves laser cutter / CNC incompatibilities where raw <text> or <textPath> elements
  are dropped or misrendered by LightBurn, RDWorks, LaserGRBL, and AutoCAD.
"""

from typing import List, Tuple, Dict, Any
import math


# Normalized character stroke definitions: (width, list_of_polyline_strokes)
# Coordinates in local unit space [0, width] x [0, 1.0] (0 = baseline, 1.0 = cap height)
GLYPH_STROKES: Dict[str, Tuple[float, List[List[Tuple[float, float]]]]] = {
    'A': (0.7, [
        [(0.0, 0.0), (0.35, 1.0), (0.7, 0.0)],
        [(0.12, 0.35), (0.58, 0.35)]
    ]),
    'B': (0.65, [
        [(0.0, 0.0), (0.0, 1.0), (0.45, 1.0), (0.65, 0.82), (0.65, 0.62), (0.45, 0.5), (0.0, 0.5)],
        [(0.45, 0.5), (0.65, 0.38), (0.65, 0.18), (0.45, 0.0), (0.0, 0.0)]
    ]),
    'C': (0.65, [
        [(0.65, 0.8), (0.5, 1.0), (0.2, 1.0), (0.0, 0.8), (0.0, 0.2), (0.2, 0.0), (0.5, 0.0), (0.65, 0.2)]
    ]),
    'D': (0.65, [
        [(0.0, 0.0), (0.0, 1.0), (0.4, 1.0), (0.65, 0.75), (0.65, 0.25), (0.4, 0.0), (0.0, 0.0)]
    ]),
    'E': (0.6, [
        [(0.6, 1.0), (0.0, 1.0), (0.0, 0.0), (0.6, 0.0)],
        [(0.0, 0.5), (0.45, 0.5)]
    ]),
    'F': (0.6, [
        [(0.6, 1.0), (0.0, 1.0), (0.0, 0.0)],
        [(0.0, 0.5), (0.45, 0.5)]
    ]),
    'G': (0.7, [
        [(0.65, 0.8), (0.5, 1.0), (0.2, 1.0), (0.0, 0.8), (0.0, 0.2), (0.2, 0.0), (0.55, 0.0), (0.7, 0.2), (0.7, 0.5), (0.4, 0.5)]
    ]),
    'H': (0.65, [
        [(0.0, 0.0), (0.0, 1.0)],
        [(0.65, 0.0), (0.65, 1.0)],
        [(0.0, 0.5), (0.65, 0.5)]
    ]),
    'I': (0.2, [
        [(0.1, 0.0), (0.1, 1.0)]
    ]),
    'J': (0.55, [
        [(0.55, 1.0), (0.55, 0.25), (0.4, 0.0), (0.15, 0.0), (0.0, 0.2)]
    ]),
    'K': (0.65, [
        [(0.0, 0.0), (0.0, 1.0)],
        [(0.65, 1.0), (0.0, 0.4)],
        [(0.25, 0.55), (0.65, 0.0)]
    ]),
    'L': (0.55, [
        [(0.0, 1.0), (0.0, 0.0), (0.55, 0.0)]
    ]),
    'M': (0.85, [
        [(0.0, 0.0), (0.0, 1.0), (0.425, 0.35), (0.85, 1.0), (0.85, 0.0)]
    ]),
    'N': (0.7, [
        [(0.0, 0.0), (0.0, 1.0), (0.7, 0.0), (0.7, 1.0)]
    ]),
    'O': (0.7, [
        [(0.2, 0.0), (0.5, 0.0), (0.7, 0.2), (0.7, 0.8), (0.5, 1.0), (0.2, 1.0), (0.0, 0.8), (0.0, 0.2), (0.2, 0.0)]
    ]),
    'P': (0.65, [
        [(0.0, 0.0), (0.0, 1.0), (0.45, 1.0), (0.65, 0.8), (0.65, 0.6), (0.45, 0.45), (0.0, 0.45)]
    ]),
    'Q': (0.7, [
        [(0.2, 0.0), (0.5, 0.0), (0.7, 0.2), (0.7, 0.8), (0.5, 1.0), (0.2, 1.0), (0.0, 0.8), (0.0, 0.2), (0.2, 0.0)],
        [(0.4, 0.25), (0.7, -0.1)]
    ]),
    'R': (0.65, [
        [(0.0, 0.0), (0.0, 1.0), (0.45, 1.0), (0.65, 0.8), (0.65, 0.6), (0.45, 0.48), (0.0, 0.48)],
        [(0.35, 0.48), (0.65, 0.0)]
    ]),
    'S': (0.6, [
        [(0.6, 0.82), (0.45, 1.0), (0.15, 1.0), (0.0, 0.8), (0.15, 0.55), (0.45, 0.45), (0.6, 0.25), (0.45, 0.0), (0.15, 0.0), (0.0, 0.18)]
    ]),
    'T': (0.65, [
        [(0.0, 1.0), (0.65, 1.0)],
        [(0.325, 1.0), (0.325, 0.0)]
    ]),
    'U': (0.65, [
        [(0.0, 1.0), (0.0, 0.2), (0.2, 0.0), (0.45, 0.0), (0.65, 0.2), (0.65, 1.0)]
    ]),
    'V': (0.65, [
        [(0.0, 1.0), (0.325, 0.0), (0.65, 1.0)]
    ]),
    'W': (0.85, [
        [(0.0, 1.0), (0.2, 0.0), (0.425, 0.65), (0.65, 0.0), (0.85, 1.0)]
    ]),
    'X': (0.65, [
        [(0.0, 0.0), (0.65, 1.0)],
        [(0.0, 1.0), (0.65, 0.0)]
    ]),
    'Y': (0.65, [
        [(0.0, 1.0), (0.325, 0.5), (0.65, 1.0)],
        [(0.325, 0.5), (0.325, 0.0)]
    ]),
    'Z': (0.6, [
        [(0.0, 1.0), (0.6, 1.0), (0.0, 0.0), (0.6, 0.0)]
    ]),
    '0': (0.65, [
        [(0.2, 0.0), (0.45, 0.0), (0.65, 0.2), (0.65, 0.8), (0.45, 1.0), (0.2, 1.0), (0.0, 0.8), (0.0, 0.2), (0.2, 0.0)],
        [(0.12, 0.25), (0.53, 0.75)]
    ]),
    '1': (0.35, [
        [(0.05, 0.8), (0.25, 1.0), (0.25, 0.0)],
        [(0.05, 0.0), (0.35, 0.0)]
    ]),
    '2': (0.6, [
        [(0.0, 0.8), (0.15, 1.0), (0.45, 1.0), (0.6, 0.8), (0.6, 0.6), (0.0, 0.0), (0.6, 0.0)]
    ]),
    '3': (0.6, [
        [(0.0, 0.85), (0.15, 1.0), (0.45, 1.0), (0.6, 0.8), (0.45, 0.52), (0.2, 0.52)],
        [(0.45, 0.52), (0.6, 0.35), (0.6, 0.15), (0.45, 0.0), (0.15, 0.0), (0.0, 0.15)]
    ]),
    '4': (0.65, [
        [(0.5, 0.0), (0.5, 1.0), (0.0, 0.3), (0.65, 0.3)]
    ]),
    '5': (0.6, [
        [(0.55, 1.0), (0.05, 1.0), (0.05, 0.55), (0.4, 0.55), (0.6, 0.4), (0.6, 0.15), (0.4, 0.0), (0.05, 0.0)]
    ]),
    '6': (0.65, [
        [(0.55, 0.9), (0.35, 1.0), (0.15, 0.8), (0.05, 0.4), (0.15, 0.0), (0.45, 0.0), (0.65, 0.2), (0.65, 0.45), (0.45, 0.55), (0.05, 0.5)]
    ]),
    '7': (0.6, [
        [(0.0, 1.0), (0.6, 1.0), (0.25, 0.0)]
    ]),
    '8': (0.6, [
        [(0.3, 0.5), (0.15, 0.65), (0.15, 0.85), (0.3, 1.0), (0.45, 1.0), (0.6, 0.85), (0.6, 0.65), (0.3, 0.5), (0.15, 0.35), (0.15, 0.15), (0.3, 0.0), (0.45, 0.0), (0.6, 0.15), (0.6, 0.35), (0.3, 0.5)]
    ]),
    '9': (0.65, [
        [(0.6, 0.5), (0.2, 0.45), (0.0, 0.55), (0.0, 0.8), (0.2, 1.0), (0.5, 1.0), (0.65, 0.6), (0.5, 0.1), (0.3, 0.0), (0.1, 0.1)]
    ]),
    ' ': (0.35, []),
    '-': (0.45, [[(0.05, 0.5), (0.4, 0.5)]]),
    '_': (0.5, [[(0.0, 0.0), (0.5, 0.0)]]),
    '.': (0.2, [[(0.05, 0.0), (0.15, 0.0), (0.15, 0.1), (0.05, 0.1), (0.05, 0.0)]]),
    ',': (0.2, [[(0.1, 0.1), (0.1, 0.0), (0.0, -0.15)]]),
    ':': (0.2, [[(0.1, 0.2), (0.1, 0.25)], [(0.1, 0.75), (0.1, 0.8)]]),
    ';': (0.2, [[(0.1, 0.1), (0.0, -0.1)], [(0.1, 0.75), (0.1, 0.8)]]),
    '#': (0.65, [
        [(0.2, 0.0), (0.2, 1.0)],
        [(0.45, 0.0), (0.45, 1.0)],
        [(0.05, 0.35), (0.6, 0.35)],
        [(0.05, 0.65), (0.6, 0.65)]
    ]),
    '/': (0.5, [[(0.05, 0.0), (0.45, 1.0)]]),
    '\\': (0.5, [[(0.05, 1.0), (0.45, 0.0)]]),
    '(': (0.35, [[(0.3, 1.0), (0.1, 0.7), (0.1, 0.3), (0.3, 0.0)]]),
    ')': (0.35, [[(0.05, 1.0), (0.25, 0.7), (0.25, 0.3), (0.05, 0.0)]]),
    '+': (0.5, [[(0.05, 0.5), (0.45, 0.5)], [(0.25, 0.25), (0.25, 0.75)]]),
    '*': (0.5, [
        [(0.1, 0.2), (0.4, 0.8)],
        [(0.1, 0.8), (0.4, 0.2)],
        [(0.05, 0.5), (0.45, 0.5)]
    ]),
    '!': (0.2, [[(0.1, 1.0), (0.1, 0.3)], [(0.1, 0.1), (0.1, 0.0)]]),
    '\'': (0.2, [[(0.1, 1.0), (0.05, 0.75)]]),
    '"': (0.35, [[(0.1, 1.0), (0.05, 0.75)], [(0.25, 1.0), (0.2, 0.75)]]),
    '|': (0.25, [[(0.125, 0.0), (0.125, 1.0)]]),
    '[': (0.35, [[(0.28, 1.0), (0.08, 1.0), (0.08, 0.0), (0.28, 0.0)]]),
    ']': (0.35, [[(0.08, 1.0), (0.28, 1.0), (0.28, 0.0), (0.08, 0.0)]]),
    '=': (0.45, [[(0.05, 0.35), (0.40, 0.35)], [(0.05, 0.65), (0.40, 0.65)]]),
    '•': (0.35, [[(0.12, 0.45), (0.23, 0.45), (0.23, 0.55), (0.12, 0.55), (0.12, 0.45)]]),
}


def render_vector_text_arc(
    text: str,
    radius: float,
    start_angle_deg: float,
    end_angle_deg: float,
    char_height: float = 0.85,
    char_spacing_ratio: float = 0.22,
    subsample_arc_strokes: bool = True
) -> List[List[Tuple[float, float]]]:
    """
    Renders alphanumeric text bent continuously along a circular arc of radius `radius`.
    Uses an exact SO(2) rigid-body rotation basis to guarantee 100% unmirrored,
    distortion-free letter curves in SVG screen coordinates.
    
    Returns a list of stroke polylines: List[List[Tuple[float, float]]].
    """
    clean_text = text.strip().upper()
    if not clean_text:
        return []

    t_start = math.radians(start_angle_deg)
    t_end = math.radians(end_angle_deg)
    
    direction = 1.0 if t_end >= t_start else -1.0
    total_avail_angle = abs(t_end - t_start)
    center_angle = (t_start + t_end) / 2.0

    # Calculate nominal total string length along the arc
    nominal_spacing = char_height * char_spacing_ratio
    total_len = 0.0
    for i, ch in enumerate(clean_text):
        w_norm, _ = GLYPH_STROKES.get(ch, (0.35, []))
        total_len += (w_norm * char_height)
        if i < len(clean_text) - 1:
            total_len += nominal_spacing

    # Auto-fit scale if string exceeds available arc length
    max_arc_len = radius * total_avail_angle * 0.90
    if total_len > max_arc_len and total_len > 1e-4:
        scale = max_arc_len / total_len
        char_height *= scale
        nominal_spacing *= scale
        total_len *= scale

    # Total angular span of the centered text
    text_angle_span = total_len / radius
    start_cursor_angle = center_angle - (direction * (text_angle_span / 2.0))

    all_strokes: List[List[Tuple[float, float]]] = []
    curr_angle = start_cursor_angle

    for i, ch in enumerate(clean_text):
        w_norm, strokes = GLYPH_STROKES.get(ch, (0.35, []))
        char_w = w_norm * char_height
        
        # Center angle for this character
        char_center_angle = curr_angle + (direction * (char_w / 2.0) / radius)
        c_x = radius * math.cos(char_center_angle)
        c_y = radius * math.sin(char_center_angle)
        
        # Tangent vector in advancing reading direction along the circle
        # d/d_alpha (R cos a, R sin a) = (-R sin a, R cos a)
        tx = -direction * math.sin(char_center_angle)
        ty = direction * math.cos(char_center_angle)
        t_mag = math.sqrt(tx * tx + ty * ty) or 1.0
        tx /= t_mag
        ty /= t_mag

        # Normal vector pointing along letter cap-height (Up)
        # In SVG screen space (where +y is down), for basis (t, n) to have positive chirality (det = -1):
        # n = (ty, -tx)
        nx = ty
        ny = -tx

        for stroke in strokes:
            curved_stroke: List[Tuple[float, float]] = []
            
            for u, v in stroke:
                # Local offset from character center
                lu = (u - (w_norm / 2.0)) * char_height
                lv = (v - 0.5) * char_height

                # Transform to world SVG plane
                px = c_x + (lu * tx) + (lv * nx)
                py = c_y + (lu * ty) + (lv * ny)
                curved_stroke.append((round(px, 4), round(py, 4)))

            if len(curved_stroke) >= 2:
                all_strokes.append(curved_stroke)

        curr_angle += direction * ((char_w + nominal_spacing) / radius)

    return all_strokes


def render_vector_text_linear(
    text: str,
    center_x: float,
    center_y: float,
    char_height: float = 1.2,
    char_spacing_ratio: float = 0.22,
    rotation_deg: float = 0.0
) -> List[List[Tuple[float, float]]]:
    """
    Renders alphanumeric text along a straight vector line rotated by rotation_deg.
    Returns a list of stroke polylines: List[List[Tuple[float, float]]].
    """
    clean_text = text.strip().upper()
    if not clean_text:
        return []

    nominal_spacing = char_height * char_spacing_ratio
    total_len = 0.0
    for i, ch in enumerate(clean_text):
        w_norm, _ = GLYPH_STROKES.get(ch, (0.35, []))
        total_len += (w_norm * char_height)
        if i < len(clean_text) - 1:
            total_len += nominal_spacing

    rot_rad = math.radians(rotation_deg)
    cos_r = math.cos(rot_rad)
    sin_r = math.sin(rot_rad)

    start_u = -total_len / 2.0
    curr_u = start_u
    all_strokes: List[List[Tuple[float, float]]] = []

    for i, ch in enumerate(clean_text):
        w_norm, strokes = GLYPH_STROKES.get(ch, (0.35, []))
        char_w = w_norm * char_height

        for stroke in strokes:
            linear_stroke: List[Tuple[float, float]] = []
            for u, v in stroke:
                # Local coords relative to center
                lx = curr_u + (u * char_height)
                ly = -(v - 0.5) * char_height
                
                # Rotate & translate
                x = round(center_x + (lx * cos_r - ly * sin_r), 4)
                y = round(center_y + (lx * sin_r + ly * cos_r), 4)
                linear_stroke.append((x, y))

            if len(linear_stroke) >= 2:
                all_strokes.append(linear_stroke)

        curr_u += (char_w + nominal_spacing)

    return all_strokes


def strokes_to_svg_path_d(strokes: List[List[Tuple[float, float]]]) -> str:
    """Converts a list of stroke polylines into an SVG path 'd' string."""
    cmds: List[str] = []
    for stroke in strokes:
        if not stroke or len(stroke) < 2:
            continue
        cmds.append(f"M {stroke[0][0]:.3f} {stroke[0][1]:.3f}")
        for pt in stroke[1:]:
            cmds.append(f"L {pt[0]:.3f} {pt[1]:.3f}")
    return " ".join(cmds)

