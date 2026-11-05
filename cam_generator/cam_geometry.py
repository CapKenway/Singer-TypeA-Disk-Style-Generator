"""
Singer Type A Cam Geometric & Mathematical Engine.

Pure Python standard library implementation (zero binary dependencies).
Calculates:
1. Dynamic Stitch Count support (6 to 36 stitches, default 18).
2. Mechanical Cam Geometry:
   - Mechanical Stepped / Gear-like mode with authentic circular dwell flats
     and steep right-angle drops for sawteeth (vintage Singer Fashion Disc style).
   - Smooth periodic Catmull-Rom spline mode.
   - Linear ramp mode.
3. Anti-crack stress-relief radiused keyway (R = 1.5mm semi-circular fillet).
4. Dual-block flanking face etching (West / 180° pattern block, East / 0° maker's mark block).
5. Precision laser kerf compensation for 3mm cast acrylic.
"""

import math
from typing import List, Tuple, Dict, Any
from .cam_vector_font import render_vector_text_linear

# Core Geometric Constants for Singer Type A Cams (Updated Physical Measurements)
OUTER_MAX_RADIUS: float = 21.0     # mm (Total outer disc diameter = 42.0 mm)
BASE_TRACK_RADIUS: float = 16.0    # mm (Minimum track diameter = 32.0 mm, Step 0 Far-Left)
MAX_TRACK_RADIUS: float = 21.0     # mm (Maximum track diameter = 42.0 mm, Step 12 Far-Right)
TOTAL_TRACK_WIDTH: float = 5.0     # mm (Modulation window: 21.0 - 16.0 mm)
MIN_CUT_DEPTH: float = 1.0         # mm (Minimum bight travel window)
MAX_CUT_DEPTH: float = 8.0         # mm (Maximum extended bight travel window)
INNER_BORE_RADIUS: float = 7.0     # mm (Key bore spindle diameter = 14.0 mm)
KEYWAY_WIDTH: float = 3.0          # mm (Alignment drive-pin slot width)
KEYWAY_DEPTH: float = 5.0          # mm (Key hole slot length extending outward from bore)

DEFAULT_STITCH_COUNT: int = 18     # Default discrete stitch inputs per 360-degree rotation
MIN_STITCHES: int = 6
MAX_STITCHES: int = 36
RADIAL_STEP_PER_VALUE: float = 5.0 / 12.0  # mm per single step increment (~0.4167 mm)

MIN_STEP_VALUE: float = 0.0
MAX_STEP_VALUE: float = 12.0
DEFAULT_KERF_OFFSET: float = 0.15  # mm (Typical laser kerf for 3mm acrylic)
SAMPLES_PER_WEDGE: int = 24        # Generates smooth polygon vertices

# Flanking Etching Block Dimensions (Slim, elegant annular hub band between 10.0mm and 14.5mm)
FLANK_BLOCK_R_INNER: float = 10.0  # mm
FLANK_BLOCK_R_OUTER: float = 14.5  # mm
DEFAULT_CUTTER_RADIUS: float = 5.0 # mm (Rotary cutter / milling bit radius)
DEFAULT_MACHINE_SETTING: float = 3.0 # Optimal machine dial / stitch thickness setting (1.0 to 8.0)
DEFAULT_DISC_THICKNESS: float = 3.0 # Backward-compatible alias

# Spindle Keyway Alignment: 90° (South, pi/2 radians) aligns Stitch 1 right in the center directly under the keyhole slot
PERIMETER_ROTATION_OFFSET: float = math.pi / 2.0  # 90 degrees (South / positive Y)


def calculate_subtractive_cutter_perimeter(
    steps: List[float],
    kerf_offset: float = DEFAULT_KERF_OFFSET,
    max_radius: float = OUTER_MAX_RADIUS,    # 21.0 mm (42mm OD)
    base_radius: float = BASE_TRACK_RADIUS,  # 16.0 mm (32mm Min Track)
    cutter_radius: float = DEFAULT_CUTTER_RADIUS,  # 5.0 mm bit radius
    cut_depth: float = 5.0,                  # Radial cut depth travel (1.0 to 5.0 mm)
    samples_per_wedge: int = SAMPLES_PER_WEDGE,
    angle_offset: float = PERIMETER_ROTATION_OFFSET
) -> List[Tuple[float, float]]:
    """
    Subtractive Rotary Cutter / Grinding Bit Cam Geometry.
    
    Analytic subtractive milling model:
      1. Blank starts as a perfect circle at max_radius (peaks stay on the circle).
      2. For valley pockets (step < 12), a rotating circular milling cutter of radius
         cutter_radius plunges radially inward at the stitch angle.
      3. Cutter center distance:
           cutter_center_dist = max_radius + cutter_radius - depth
      4. Analytic circular scoop intersections form natural filleted gear teeth
         and smooth valley floors.
    """
    total_stitches = max(MIN_STITCHES, len(steps))
    sanitized_steps = sanitize_stitch_steps(steps, total_stitches)
    half_kerf = max(0.0, float(kerf_offset)) / 2.0
    cutter_radius = max(1.5, min(25.0, float(cutter_radius)))
    cut_depth = max(1.0, min(max_radius - INNER_BORE_RADIUS - 2.0, float(cut_depth)))
    effective_base_radius = max_radius - cut_depth
    
    rad_step = (2.0 * math.pi) / float(total_stitches)
    max_depth = cut_depth  # Configurable travel window (default 5.0 mm)
    
    # Pre-calculate cutter center distance and angles for pockets
    cutters: List[Tuple[float, float]] = []  # (center_dist, angle_rad)
    for i in range(total_stitches):
        val_curr = sanitized_steps[i]
        angle_curr = angle_offset + (float(i) * rad_step)
        
        if val_curr < 11.99:  # Pocket cutout required
            depth = ((12.0 - val_curr) / 12.0) * max_depth
            center_dist = max_radius + cutter_radius - depth
            cutters.append((center_dist, angle_curr))
            
        # Continuous cutter sweep along valley floor between adjacent low stitches
        val_next = sanitized_steps[(i + 1) % total_stitches]
        if val_curr < 11.99 and val_next < 11.99:
            sweep_samples = 8
            for s in range(1, sweep_samples):
                u = float(s) / float(sweep_samples)
                v_interp = val_curr + (u * (val_next - val_curr))
                depth_interp = ((12.0 - v_interp) / 12.0) * max_depth
                c_dist_interp = max_radius + cutter_radius - depth_interp
                a_interp = angle_curr + (u * rad_step)
                cutters.append((c_dist_interp, a_interp))
            
    polygon: List[Tuple[float, float]] = []
    total_samples = total_stitches * samples_per_wedge
    
    for s in range(total_samples):
        theta = angle_offset + ((float(s) / float(total_samples)) * (2.0 * math.pi))
        r = max_radius
        
        # Test against all active rotary cutters
        for c_dist, c_angle in cutters:
            delta_theta = (theta - c_angle + math.pi) % (2.0 * math.pi) - math.pi
            if math.cos(delta_theta) > 0.0:
                sin_dt = math.sin(delta_theta)
                term = (cutter_radius * cutter_radius) - (c_dist * c_dist * sin_dt * sin_dt)
                if term >= 0.0:
                    r_cutter = (c_dist * math.cos(delta_theta)) - math.sqrt(term)
                    if r_cutter < r:
                        r = r_cutter
                        
        r = max(effective_base_radius - 0.5, min(max_radius, r))
        r_cut = r + half_kerf
        x = round(r_cut * math.cos(theta), 4)
        y = round(r_cut * math.sin(theta), 4)
        polygon.append((x, y))
        
    return polygon


def sanitize_stitch_steps(raw_steps: List[Any], count: int = DEFAULT_STITCH_COUNT) -> List[float]:
    """
    Sanitizes and clamps a list of stitch deflection values to count elements.
    Each value represents needle bight deflection (0.0 to 12.0).
    """
    count = max(MIN_STITCHES, min(MAX_STITCHES, int(count)))
    cleaned: List[float] = []
    for i in range(count):
        val = 0.0
        if raw_steps and i < len(raw_steps):
            try:
                val = float(raw_steps[i])
            except (ValueError, TypeError):
                val = 0.0
        val = max(MIN_STEP_VALUE, min(MAX_STEP_VALUE, val))
        cleaned.append(val)
    return cleaned


def stitch_values_to_radii(steps: List[float], cut_depth: float = 5.0) -> List[float]:
    """
    Maps discrete step values (0..12) to physical radii.
    With default cut_depth=5.0: maps to (16.0..21.0 mm).
    With custom cut_depth: maps to ((21.0 - cut_depth)..21.0 mm).
    """
    cut_depth = max(1.0, min(OUTER_MAX_RADIUS - INNER_BORE_RADIUS - 2.0, float(cut_depth)))
    base_r = OUTER_MAX_RADIUS - cut_depth
    step_inc = cut_depth / 12.0
    return [
        base_r + (step * step_inc)
        for step in steps
    ]


def catmull_rom_spline_1d(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    """
    Evaluates a 1D uniform Catmull-Rom spline at normalized parameter t in [0, 1].
    Provides continuous C1 velocity matching between adjacent segments.
    """
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2.0 * p1) +
        (-p0 + p2) * t +
        (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 +
        (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def calculate_outer_perimeter(
    steps: List[float],
    kerf_offset: float = DEFAULT_KERF_OFFSET,
    profile_mode: str = 'straight_wall',
    dwell_ratio: float = 0.60,
    corner_fillet: float = 0.50,
    cutter_radius: float = DEFAULT_CUTTER_RADIUS,
    cut_depth: float = 5.0,
    samples_per_wedge: int = SAMPLES_PER_WEDGE,
    angle_offset: float = PERIMETER_ROTATION_OFFSET
) -> List[Tuple[float, float]]:
    """
    Generates a closed polygon for the outer cam perimeter (42.0mm OD max, 32.0mm min track).
    
    Profile Modes:
      - 'straight_wall' (Default OEM Machine Pattern):
        True 100% straight radial walls perpendicular to the circular bore.
        Creates authentic squared-off gear teeth, right-angle sawteeth, and alternating
        square dwell blocks exactly matching vintage Singer Type A fashion discs.
        Consecutive identical stitches merge into continuous unbroken plateaus.
      - 'subtractive' (Rotary Cutter Scoop):
        Milling cutter math where a circular cutter bit of radius cutter_radius
        plunges inward at valley angles, scooping out circular pockets from the outer circle.
      - 'gear':
        Concentric circular dwell flats connected by steep transition flanks with
        smooth corner blend fillets (zero-jerk quintic smootherstep).
      - 'sawtooth':
        Progressive ramps on rising edges and steep right-angle radial drops on falling edges.
      - 'spline':
        Smooth periodic Catmull-Rom spline across all stitch radii.
      - 'linear':
        Direct linear faceted polygonal segments.
        
    Parameters:
      - dwell_ratio: Fraction of stitch wedge allocated to constant-radius dwell (0.0 to 0.85).
      - corner_fillet: Blend factor for transition corners (0.0 = razor straight to 1.0 = soft rounded).
      - cutter_radius: Radius of rotary cutter bit (mm) for 'subtractive' mode.
      - cut_depth: Radial cut depth / bight travel window (1.0 to 5.0 mm).
      - kerf_offset: Laser beam kerf expansion (mm).
      - angle_offset: Radial rotation offset (radians). Default PERIMETER_ROTATION_OFFSET (pi/2)
        aligns Stitch 1 right in the center directly under the spindle keyhole.
    """
    if profile_mode in ('subtractive', 'cutter'):
        return calculate_subtractive_cutter_perimeter(
            steps=steps,
            kerf_offset=kerf_offset,
            max_radius=OUTER_MAX_RADIUS,
            base_radius=BASE_TRACK_RADIUS,
            cutter_radius=cutter_radius,
            cut_depth=cut_depth,
            samples_per_wedge=samples_per_wedge,
            angle_offset=angle_offset
        )

    total_stitches = max(MIN_STITCHES, len(steps))
    sanitized_steps = sanitize_stitch_steps(steps, total_stitches)
    radii = stitch_values_to_radii(sanitized_steps, cut_depth=cut_depth)
    half_kerf = max(0.0, float(kerf_offset)) / 2.0
    
    polygon: List[Tuple[float, float]] = []
    rad_step = (2.0 * math.pi) / float(total_stitches)
    dwell_ratio = max(0.0, min(0.85, float(dwell_ratio)))
    corner_fillet = max(0.0, min(1.0, float(corner_fillet)))
    
    # Half-dwell fraction on each side of the stitch ray
    half_dwell = dwell_ratio / 2.0
    transition_width = 1.0 - dwell_ratio

    for i in range(total_stitches):
        r_current = radii[i]
        r_next = radii[(i + 1) % total_stitches]
        angle_start = angle_offset + (float(i) * rad_step)
        angle_end = angle_offset + (float(i + 1) * rad_step)
        angle_mid = angle_offset + ((float(i) + 0.5) * rad_step)
        
        # 4-point neighborhood for spline mode
        p0 = radii[(i - 1) % total_stitches]
        p1 = r_current
        p2 = r_next
        p3 = radii[(i + 2) % total_stitches]
        
        if profile_mode in ('straight_wall', 'sawtooth') and abs(r_current - r_next) >= 1e-4:
            # TRUE STRAIGHT RADIAL WALL LOGIC
            is_sawtooth_drop = (profile_mode == 'sawtooth' and r_next < r_current)
            is_straight = (profile_mode == 'straight_wall' or is_sawtooth_drop)
            
            if is_straight:
                # Samples for arc leading up to midpoint
                arc_samples = max(4, samples_per_wedge // 2)
                
                if corner_fillet <= 0.15:
                    # 100% PURE STRAIGHT RADIAL WALL (Razor Sharp 90° Corners)
                    # 1. Circular dwell arc at r_current from angle_start up to angle_mid
                    for s in range(arc_samples):
                        u = float(s) / float(arc_samples)
                        a = angle_start + (u * 0.5 * rad_step)
                        r = r_current + half_kerf
                        polygon.append((round(r * math.cos(a), 4), round(r * math.sin(a), 4)))
                        
                    # 2. Point on top of the straight radial wall at angle_mid
                    r_top = r_current + half_kerf
                    polygon.append((round(r_top * math.cos(angle_mid), 4), round(r_top * math.sin(angle_mid), 4)))
                    
                    # 3. Point at the bottom of the straight radial wall at the EXACT SAME angle_mid!
                    # This creates a 100% straight radial line segment perpendicular to circumference!
                    r_bot = r_next + half_kerf
                    polygon.append((round(r_bot * math.cos(angle_mid), 4), round(r_bot * math.sin(angle_mid), 4)))
                    
                    # 4. Circular dwell arc at r_next from angle_mid to angle_end
                    for s in range(1, arc_samples):
                        u = float(s) / float(arc_samples)
                        a = angle_mid + (u * 0.5 * rad_step)
                        r = r_next + half_kerf
                        polygon.append((round(r * math.cos(a), 4), round(r * math.sin(a), 4)))
                    continue
                else:
                    # Filleted Straight Radial Wall (OEM Cam with Machined Corner Blend)
                    # Fillet angular span (controls how much the corner is radiused)
                    fillet_angle = corner_fillet * 0.18 * rad_step
                    a_fillet_start = angle_mid - fillet_angle
                    a_fillet_end = angle_mid + fillet_angle
                    
                    for s in range(samples_per_wedge):
                        t = float(s) / float(samples_per_wedge)
                        a = angle_start + (t * rad_step)
                        
                        if a <= a_fillet_start:
                            r_nom = r_current
                        elif a >= a_fillet_end:
                            r_nom = r_next
                        else:
                            # S-curve transition over fillet window
                            u = (a - a_fillet_start) / (a_fillet_end - a_fillet_start)
                            w = u * u * (3.0 - (2.0 * u))
                            r_nom = r_current + ((r_next - r_current) * w)
                            
                        r_cut = r_nom + half_kerf
                        polygon.append((round(r_cut * math.cos(a), 4), round(r_cut * math.sin(a), 4)))
                    continue

        # Standard sampling for Gear, Spline, Linear, or Consecutive Plateaus
        for s in range(samples_per_wedge):
            t = float(s) / float(samples_per_wedge)
            
            if profile_mode in ('gear', 'straight_wall'):
                # Symmetrical dwell plateau with filleted transition
                if abs(r_current - r_next) < 1e-4:
                    r_nominal = r_current
                elif t < half_dwell:
                    r_nominal = r_current
                elif t > (1.0 - half_dwell):
                    r_nominal = r_next
                else:
                    u = (t - half_dwell) / max(1e-5, transition_width)
                    u = max(0.0, min(1.0, u))
                    w_smooth = u * u * u * (u * (u * 6.0 - 15.0) + 10.0)
                    if corner_fillet < 0.5:
                        steep = 1.0 + (0.5 - corner_fillet) * 6.0
                        w = math.pow(w_smooth, steep) if u < 0.5 else 1.0 - math.pow(1.0 - w_smooth, steep)
                    else:
                        w = w_smooth
                    r_nominal = r_current + ((r_next - r_current) * w)

            elif profile_mode == 'sawtooth':
                # Rising ramp
                if t < half_dwell:
                    r_nominal = r_current
                elif t > (1.0 - half_dwell):
                    r_nominal = r_next
                else:
                    u = (t - half_dwell) / max(1e-5, transition_width)
                    r_nominal = r_current + ((r_next - r_current) * u)

            elif profile_mode == 'linear':
                r_nominal = r_current + ((r_next - r_current) * t)

            else:
                # Spline
                r_nominal = catmull_rom_spline_1d(p0, p1, p2, p3, t)
                
            r_nominal = max(BASE_TRACK_RADIUS - 0.5, min(OUTER_MAX_RADIUS, r_nominal))
            r_cut = r_nominal + half_kerf
            angle = angle_start + (t * rad_step)
            
            x = r_cut * math.cos(angle)
            y = r_cut * math.sin(angle)
            polygon.append((round(x, 4), round(y, 4)))

    return polygon


def calculate_inner_bore_with_keyway(
    kerf_offset: float = DEFAULT_KERF_OFFSET,
    keyway_width: float = KEYWAY_WIDTH,
    keyway_depth: float = KEYWAY_DEPTH,
    round_keyway: bool = True,
    arc_samples: int = 56
) -> List[Tuple[float, float]]:
    """
    Generates a closed polygon for the center spindle bore with drive-pin keyway slot.
    Bore diameter: 14mm (Radius: 7mm). Keyway slot length: 5mm.
    Anti-Crack Stress Relief: semi-circular radiused end (R = 1.5mm).
    """
    half_kerf = max(0.0, float(kerf_offset)) / 2.0
    
    r_bore = max(1.0, INNER_BORE_RADIUS - half_kerf)
    w_key = max(0.5, keyway_width - (2.0 * half_kerf))
    r_key = max(r_bore + 0.5, (INNER_BORE_RADIUS + keyway_depth) - half_kerf)
    
    half_w = w_key / 2.0
    if half_w >= r_bore:
        half_w = r_bore * 0.95
        
    y_int = math.sqrt(r_bore * r_bore - half_w * half_w)
    polygon: List[Tuple[float, float]] = []
    
    polygon.append((round(half_w, 4), round(y_int, 4)))
    
    if round_keyway:
        r_fillet = half_w
        y_center = r_key - r_fillet
        
        polygon.append((round(half_w, 4), round(y_center, 4)))
        
        fillet_steps = 14
        for step in range(1, fillet_steps):
            beta = (float(step) / float(fillet_steps)) * math.pi
            arc_x = r_fillet * math.cos(beta)
            arc_y = y_center + (r_fillet * math.sin(beta))
            polygon.append((round(arc_x, 4), round(arc_y, 4)))
            
        polygon.append((round(-half_w, 4), round(y_center, 4)))
        polygon.append((round(-half_w, 4), round(y_int, 4)))
    else:
        polygon.append((round(half_w, 4), round(r_key, 4)))
        polygon.append((round(-half_w, 4), round(r_key, 4)))
        polygon.append((round(-half_w, 4), round(y_int, 4)))
    
    theta_left = math.atan2(y_int, -half_w)
    theta_right = math.atan2(y_int, half_w)
    sweep = (2.0 * math.pi) - (theta_left - theta_right)
    
    for step in range(1, arc_samples):
        u = float(step) / float(arc_samples)
        alpha = theta_left + (u * sweep)
        x = r_bore * math.cos(alpha)
        y = r_bore * math.sin(alpha)
        polygon.append((round(x, 4), round(y, 4)))
        
    return polygon


def _create_arc_band_polygon(
    theta_start_deg: float,
    theta_end_deg: float,
    r_inner: float,
    r_outer: float,
    num_pts: int = 18
) -> List[Tuple[float, float]]:
    """Creates a closed sector/cartouche boundary polygon between two angles and radii."""
    t_start = math.radians(theta_start_deg)
    t_end = math.radians(theta_end_deg)
    
    pts: List[Tuple[float, float]] = []
    for i in range(num_pts + 1):
        u = float(i) / float(num_pts)
        angle = t_start + u * (t_end - t_start)
        pts.append((round(r_outer * math.cos(angle), 4), round(r_outer * math.sin(angle), 4)))
        
    for i in range(num_pts, -1, -1):
        u = float(i) / float(num_pts)
        angle = t_start + u * (t_end - t_start)
        pts.append((round(r_inner * math.cos(angle), 4), round(r_inner * math.sin(angle), 4)))
        
    return pts


def calculate_left_flank_pattern_block(
    steps: List[float],
    stitch_fill_mode: str = 'unfilled',
    needle_position: str = 'L',
    cut_depth: float = 5.0
) -> Dict[str, Any]:
    """
    Generates geometry for the STITCH PATTERN BLOCK located on the far LEFT FLANK (West / 180°).
    Includes concentric circular guide arcs for text-on-path rendering along the bore.
    
    Supports authentic vintage sewing machine needle positions and satin fill mechanics:
      - 'L' (Left Needle): Baseline at inner rim, positive filling from bottom up to wave.
      - 'C' (Center Needle): Mirrored from center line -> serrations become filled diamonds!
      - 'R' (Right Needle): Inverted negative filling -> top baseline filled down to wave, bottom unfilled.
      - If needle is Center or Right, filled mode is definitely activated.
      - Bight fill width scales with user-configurable cut_depth (up to 8.0 mm).
    """
    total_stitches = max(MIN_STITCHES, len(steps))
    sanitized_steps = sanitize_stitch_steps(steps, total_stitches)
    clean_pos = needle_position.strip().upper() if needle_position in ('L', 'C', 'R') else 'L'

    # Center or Right needle positions are definitely filled
    if clean_pos in ('C', 'R'):
        stitch_fill_mode = 'filled'
    elif stitch_fill_mode not in ('unfilled', 'filled'):
        stitch_fill_mode = 'unfilled'

    cut_depth = max(MIN_CUT_DEPTH, min(MAX_CUT_DEPTH, float(cut_depth)))
    
    frame_pts = _create_arc_band_polygon(
        theta_start_deg=148.0,
        theta_end_deg=212.0,
        r_inner=FLANK_BLOCK_R_INNER,
        r_outer=FLANK_BLOCK_R_OUTER,
        num_pts=18
    )
    
    start_deg = 154.0
    end_deg = 206.0
    
    # Scale bight radial window based on cut_depth up to 8.0 mm
    # 5.0mm default maps to 1.25mm span on the disc cartouche; 8.0mm maps to 1.70mm span
    bight_radial_span = min(1.80, 0.90 + (0.80 * (cut_depth / 8.0)))
    r_inner_base = 11.50
    r_outer_base = r_inner_base + bight_radial_span
    r_midline = (r_inner_base + r_outer_base) / 2.0
    half_span = bight_radial_span / 2.0
    
    waveform_pts: List[Tuple[float, float]] = []
    node_pts: List[Tuple[float, float]] = []
    centerline_pts: List[Tuple[float, float]] = []
    
    for i in range(total_stitches):
        val = sanitized_steps[i]
        u = float(i) / float(total_stitches - 1) if total_stitches > 1 else 0.5
        angle = math.radians(start_deg + (u * (end_deg - start_deg)))
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Center datum line reference point
        centerline_pts.append((round(r_midline * cos_a, 4), round(r_midline * sin_a, 4)))
        
        if clean_pos == 'C':
            # Center Needle: user commands Center to Right (0.0 = Center, 12.0 = Max Right).
            # Machine automatically alternates to Left by the exact same chosen amount.
            bight_frac = max(0.0, min(1.0, val / MAX_STEP_VALUE))
            delta = bight_frac * half_span
            r_right = r_midline + delta
            r_left = r_midline - delta
            
            # The machine penetrates alternating between Left (even) and Right (odd)
            r_stitch = r_left if (i % 2 == 0) else r_right
            waveform_pts.append((round(r_stitch * cos_a, 4), round(r_stitch * sin_a, 4)))
            # Command nodes are positioned on the commanded Right curve
            node_pts.append((round(r_right * cos_a, 4), round(r_right * sin_a, 4)))
        elif clean_pos == 'R':
            r_val = r_inner_base + ((val / MAX_STEP_VALUE) * bight_radial_span)
            waveform_pts.append((round(r_val * cos_a, 4), round(r_val * sin_a, 4)))
            node_pts.append((round(r_val * cos_a, 4), round(r_val * sin_a, 4)))
        else:
            r_val = r_inner_base + ((val / MAX_STEP_VALUE) * bight_radial_span)
            waveform_pts.append((round(r_val * cos_a, 4), round(r_val * sin_a, 4)))
            node_pts.append((round(r_val * cos_a, 4), round(r_val * sin_a, 4)))

    # Dense Satin Stitch Hatching & Solid Ribbon Polygon for 'filled' mode
    satin_hatch_strokes: List[List[Tuple[float, float]]] = []
    satin_ribbon_pts: List[Tuple[float, float]] = []
    
    num_satin_passes = max(40, total_stitches * 3)
    top_contour: List[Tuple[float, float]] = []
    bot_contour: List[Tuple[float, float]] = []
    
    for s in range(num_satin_passes + 1):
        u = float(s) / float(num_satin_passes)
        angle = math.radians(start_deg + (u * (end_deg - start_deg)))
        
        # Continuous linear / dwell interpolation between stitch points
        st_pos = u * float(total_stitches - 1)
        i0 = int(st_pos)
        i1 = min(total_stitches - 1, i0 + 1)
        frac = st_pos - float(i0)
        v_interp = sanitized_steps[i0] + (frac * (sanitized_steps[i1] - sanitized_steps[i0]))
        
        if clean_pos == 'C':
            # Center Needle: user commands Center to Right (0 to 12).
            # Symmetrical satin ribbon: top contour at Right, bottom contour at auto Left
            bight_frac = max(0.0, min(1.0, v_interp / MAX_STEP_VALUE))
            delta = bight_frac * half_span
            r_top = r_midline + delta  # Right commanded contour
            r_bot = r_midline - delta  # Left automatically alternated contour
        elif clean_pos == 'R':
            # Negative to positive filling: top baseline filled down to wave, bottom empty
            r_bot = r_inner_base + ((v_interp / MAX_STEP_VALUE) * bight_radial_span)
            r_top = r_outer_base
        else:
            # Left needle: positive filling from bottom up to wave
            r_bot = r_inner_base
            r_top = r_inner_base + ((v_interp / MAX_STEP_VALUE) * bight_radial_span)
        
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        x_bot = round(r_bot * cos_a, 4)
        y_bot = round(r_bot * sin_a, 4)
        x_top = round(r_top * cos_a, 4)
        y_top = round(r_top * sin_a, 4)
        
        bot_contour.append((x_bot, y_bot))
        top_contour.append((x_top, y_top))
        
        # Dense satin embroidery thread stroke across the bight
        if abs(r_top - r_bot) > 0.03:
            satin_hatch_strokes.append([(x_bot, y_bot), (x_top, y_top)])
            
    # Closed ribbon polygon: along bottom baseline forward, along top contour backward
    satin_ribbon_pts = bot_contour + list(reversed(top_contour))
        
    # Concentric circular arc path for Title curved along the bore at R = 13.8mm
    r_title = 13.8
    t_start_rad = math.radians(154.0)
    t_end_rad = math.radians(206.0)
    t_x1, t_y1 = round(r_title * math.cos(t_start_rad), 3), round(r_title * math.sin(t_start_rad), 3)
    t_x2, t_y2 = round(r_title * math.cos(t_end_rad), 3), round(r_title * math.sin(t_end_rad), 3)
    title_arc_d = f"M {t_x1} {t_y1} A {r_title} {r_title} 0 0 1 {t_x2} {t_y2}"
    
    # Concentric circular arc path for Subtitle curved along the bore at R = 10.6mm
    r_sub = 10.6
    s_start_rad = math.radians(156.0)
    s_end_rad = math.radians(204.0)
    s_x1, s_y1 = round(r_sub * math.cos(s_start_rad), 3), round(r_sub * math.sin(s_start_rad), 3)
    s_x2, s_y2 = round(r_sub * math.cos(s_end_rad), 3), round(r_sub * math.sin(s_end_rad), 3)
    subtitle_arc_d = f"M {s_x1} {s_y1} A {r_sub} {r_sub} 0 0 1 {s_x2} {s_y2}"
        
    return {
        'frame_polygon': frame_pts,
        'waveform_points': waveform_pts,
        'node_points': node_pts,
        'centerline_points': centerline_pts,
        'satin_hatch_strokes': satin_hatch_strokes,
        'satin_ribbon_polygon': satin_ribbon_pts,
        'stitch_fill_mode': stitch_fill_mode,
        'needle_position': clean_pos,
        'center_x': -12.4,
        'center_y': 0.0,
        'title_pos': (-12.4, -4.8),
        'subtitle_pos': (-12.4, 4.8),
        'title_arc_d': title_arc_d,
        'subtitle_arc_d': subtitle_arc_d,
        'title_r': r_title,
        'subtitle_r': r_sub,
        'stitch_count': total_stitches,
        'cut_depth': cut_depth,
    }


def calculate_right_flank_maker_block(
    maker_name: str = "KENWAY",
    stitch_count: int = DEFAULT_STITCH_COUNT,
    name_rotation: float = 90.0,
    needle_position: str = "L",
    cut_depth: float = 5.0
) -> Dict[str, Any]:
    """
    Generates geometry for the MAKER'S MARK BLOCK located on the far RIGHT FLANK (East / 0°).
    Includes concentric circular guide arcs for text curved along the bore:
      - Outer arc (R = 13.8mm): Maker's Mark Name (KENWAY)
      - Inner arc (R = 10.6mm): Needle Position Etch (NEEDLE POS: LEFT/CENTER/RIGHT)
    """
    frame_pts = _create_arc_band_polygon(
        theta_start_deg=-32.0,
        theta_end_deg=32.0,
        r_inner=FLANK_BLOCK_R_INNER,
        r_outer=FLANK_BLOCK_R_OUTER,
        num_pts=18
    )
    
    inner_accent = _create_arc_band_polygon(
        theta_start_deg=-26.0,
        theta_end_deg=26.0,
        r_inner=10.4,
        r_outer=14.2,
        num_pts=14
    )
    
    # Diamond accent at the top of the vertical cartouche (Y = -4.8mm)
    d_x, d_y = 12.3, -4.8
    diamond_pts = [
        (round(d_x, 3), round(d_y - 0.7, 3)),
        (round(d_x + 0.7, 3), round(d_y, 3)),
        (round(d_x, 3), round(d_y + 0.7, 3)),
        (round(d_x - 0.7, 3), round(d_y, 3)),
        (round(d_x, 3), round(d_y - 0.7, 3)),
    ]
    
    # Bottom accent diamond at Y = +4.8mm
    b_x, b_y = 12.3, 4.8
    bottom_diamond_pts = [
        (round(b_x, 3), round(b_y - 0.6, 3)),
        (round(b_x + 0.6, 3), round(b_y, 3)),
        (round(b_x, 3), round(b_y + 0.6, 3)),
        (round(b_x - 0.6, 3), round(b_y, 3)),
        (round(b_x, 3), round(b_y - 0.6, 3)),
    ]
    
    clean_maker = (maker_name.strip() or "KENWAY").upper()
    clean_pos = needle_position.strip().upper() if needle_position in ('L', 'C', 'R') else 'L'
    pos_label = "LEFT" if clean_pos == 'L' else ("CENTER" if clean_pos == 'C' else "RIGHT")
    needle_text = f"NEEDLE: {pos_label}"
    
    # Concentric circular arc path for Maker's Mark curved along the bore at R = 12.3mm
    r_maker = 12.3
    m_start_rad = math.radians(26.0)
    m_end_rad = math.radians(-26.0)
    m_x1, m_y1 = round(r_maker * math.cos(m_start_rad), 3), round(r_maker * math.sin(m_start_rad), 3)
    m_x2, m_y2 = round(r_maker * math.cos(m_end_rad), 3), round(r_maker * math.sin(m_end_rad), 3)
    maker_arc_d = f"M {m_x1} {m_y1} A {r_maker} {r_maker} 0 0 0 {m_x2} {m_y2}"
    
    # Concentric circular arc path for Needle Position curved along the bore at R = 10.6mm
    r_needle = 10.6
    n_start_rad = math.radians(-26.0)
    n_end_rad = math.radians(26.0)
    n_x1, n_y1 = round(r_needle * math.cos(n_start_rad), 3), round(r_needle * math.sin(n_start_rad), 3)
    n_x2, n_y2 = round(r_needle * math.cos(n_end_rad), 3), round(r_needle * math.sin(n_end_rad), 3)
    needle_arc_d = f"M {n_x1} {n_y1} A {r_needle} {r_needle} 0 0 1 {n_x2} {n_y2}"

    return {
        'frame_polygon': frame_pts,
        'inner_accent_polygon': inner_accent,
        'diamond_points': diamond_pts,
        'bottom_diamond_points': bottom_diamond_pts,
        'center_x': 12.3,
        'center_y': 0.0,
        'name_pos': (12.3, 0.0),
        'specs_pos': (12.3, 4.8),
        'maker_arc_d': maker_arc_d,
        'maker_r': r_maker,
        'needle_arc_d': needle_arc_d,
        'needle_r': r_needle,
        'needle_text': needle_text,
        'needle_position': clean_pos,
        'needle_pos_label': pos_label,
        'name_rotation': float(name_rotation),
        'maker_name': clean_maker,
        'stitch_count': stitch_count,
        'cut_depth': float(cut_depth),
    }


def calculate_top_header_block(
    preset_number: str = "1",
    needle_position: str = "L",
    machine_setting: float = 3.0,
    disc_thickness: Any = None
) -> Dict[str, Any]:
    """
    Generates geometry for the TOP HEADER BLOCK located on the NORTH sector (12 o'clock, Y < 0).
    
    Contains:
      1. Boundary frame arc band (theta = -124° to -56°, R = 8.0 to 14.8 mm).
      2. Upper Arc (R = 13.5mm): Preset Number / Cam # (e.g. CAM #38 or custom user input).
      3. Center Gauge (Y ≈ -11.0mm): Dedicated Needle Position Symbol
         - Horizontal needle gauge rail with end stops and tick marks for Left, Center, Right.
         - Downward-pointing sewing machine needle arrow and blade indicating active position.
         - L, C, R vector letter labels with active position highlight indicator box.
      4. Lower Arc (R = 8.8mm): Needle Position & Machine Setting Etch (e.g. NEEDLE L • SET:3.0).
         Indicates the recommended machine dial setting for optimal stitch width/thickness.
    """
    clean_num = str(preset_number).strip().upper() or "1"
    clean_pos = needle_position.strip().upper() if needle_position in ('L', 'C', 'R') else 'L'
    
    setting_val = disc_thickness if disc_thickness is not None else machine_setting
    try:
        clean_setting = max(1.0, min(8.0, float(setting_val)))
    except (ValueError, TypeError):
        clean_setting = 3.0

    # Frame polygon covering the top annular sector (North, Y < 0)
    frame_pts = _create_arc_band_polygon(
        theta_start_deg=-124.0,
        theta_end_deg=-56.0,
        r_inner=8.0,
        r_outer=14.8,
        num_pts=20
    )

    # Preset / Cam number string formatting
    if any(clean_num.startswith(p) for p in ("CAM", "DISC", "PART", "#")):
        preset_text = clean_num
    else:
        preset_text = f"CAM #{clean_num}"

    # Machine dial setting & needle position summary string (e.g. NEEDLE C • SET:3.0)
    specs_text = f"NEEDLE {clean_pos} • SET:{clean_setting:.1f}"

    # Multi-component pure vector strokes for the Needle Position Symbol
    needle_strokes: List[List[Tuple[float, float]]] = []

    # 1. Horizontal needle gauge rail & stops at Y = -11.0mm
    y_rail = -11.0
    needle_strokes.append([(-3.6, y_rail), (3.6, y_rail)])
    needle_strokes.append([(-3.6, y_rail - 0.3), (-3.6, y_rail + 0.3)])
    needle_strokes.append([(3.6, y_rail - 0.3), (3.6, y_rail + 0.3)])

    # 2. Tick marks for Left (-2.6mm), Center (0.0mm), Right (+2.6mm)
    x_positions = {'L': -2.6, 'C': 0.0, 'R': 2.6}
    for pos_key, x_tick in x_positions.items():
        needle_strokes.append([(x_tick, y_rail - 0.35), (x_tick, y_rail + 0.35)])

    # 3. Vector letter labels L, C, R located below the track at Y = -9.9mm
    y_label = -9.9
    char_h = 0.65
    needle_strokes.extend(render_vector_text_linear('L', center_x=-2.6, center_y=y_label, char_height=char_h))
    needle_strokes.extend(render_vector_text_linear('C', center_x=0.0, center_y=y_label, char_height=char_h))
    needle_strokes.extend(render_vector_text_linear('R', center_x=2.6, center_y=y_label, char_height=char_h))

    # 4. Active Needle Graphic (shank, eyelet, downward arrow point)
    x_act = x_positions.get(clean_pos, -2.6)
    # Needle vertical shank
    needle_strokes.append([(x_act, -12.9), (x_act, -11.55)])
    # Needle eyelet
    needle_strokes.append([(x_act - 0.25, -12.1), (x_act + 0.25, -12.1)])
    # Downward arrow point targeting the tick mark
    needle_strokes.append([
        (round(x_act - 0.48, 3), -11.55),
        (round(x_act + 0.48, 3), -11.55),
        (round(x_act, 3), -11.0),
        (round(x_act - 0.48, 3), -11.55)
    ])
    # Active position highlight box around the active letter
    needle_strokes.append([
        (round(x_act - 0.72, 3), round(y_label - 0.45, 3)),
        (round(x_act + 0.72, 3), round(y_label - 0.45, 3)),
        (round(x_act + 0.72, 3), round(y_label + 0.45, 3)),
        (round(x_act - 0.72, 3), round(y_label + 0.45, 3)),
        (round(x_act - 0.72, 3), round(y_label - 0.45, 3))
    ])

    return {
        'frame_polygon': frame_pts,
        'preset_text': preset_text,
        'preset_number': clean_num,
        'specs_text': specs_text,
        'machine_setting': clean_setting,
        'disc_thickness': clean_setting,  # backward compatibility
        'needle_position': clean_pos,
        'preset_r': 13.5,
        'preset_start_deg': -120.0,
        'preset_end_deg': -60.0,
        'specs_r': 8.8,
        'specs_start_deg': -118.0,
        'specs_end_deg': -62.0,
        'needle_symbol_strokes': needle_strokes,
    }


def get_cam_metrics(
    steps: List[float],
    kerf_offset: float = DEFAULT_KERF_OFFSET,
    profile_mode: str = 'straight_wall',
    dwell_ratio: float = 0.60,
    corner_fillet: float = 0.50,
    cutter_radius: float = DEFAULT_CUTTER_RADIUS,
    needle_position: str = 'L',
    cut_depth: float = 5.0,
    preset_number: str = "1",
    disc_thickness: Any = None,
    machine_setting: float = 3.0
) -> Dict[str, Any]:
    """
    Computes diagnostic and technical metrics for the cam design.
    """
    total_stitches = max(MIN_STITCHES, len(steps))
    sanitized = sanitize_stitch_steps(steps, total_stitches)
    cut_depth = max(MIN_CUT_DEPTH, min(MAX_CUT_DEPTH, float(cut_depth)))
    radii = stitch_values_to_radii(sanitized, cut_depth=cut_depth)
    min_r = min(radii)
    max_r = max(radii)
    min_step = min(sanitized)
    max_step = max(sanitized)
    
    clean_pos = needle_position.strip().upper() if needle_position in ('L', 'C', 'R') else 'L'
    pos_label = "Left (0.0mm)" if clean_pos == 'L' else ("Center (Alternating)" if clean_pos == 'C' else "Right (12.0mm)")

    setting_val = disc_thickness if disc_thickness is not None else machine_setting
    try:
        clean_setting = max(1.0, min(8.0, float(setting_val)))
    except (ValueError, TypeError):
        clean_setting = 3.0

    return {
        'stitch_count': total_stitches,
        'angular_step_deg': round(360.0 / total_stitches, 2),
        'outer_max_diameter_mm': round(OUTER_MAX_RADIUS * 2.0, 1),
        'min_diameter_mm': round((OUTER_MAX_RADIUS - cut_depth) * 2.0, 1),
        'max_diameter_mm': round(OUTER_MAX_RADIUS * 2.0, 1),
        'inner_bore_diameter_mm': round(INNER_BORE_RADIUS * 2.0, 1),
        'keyway_width_mm': KEYWAY_WIDTH,
        'keyway_depth_mm': KEYWAY_DEPTH,
        'keyway_fillet_radius_mm': KEYWAY_WIDTH / 2.0,
        'kerf_offset_mm': round(kerf_offset, 3),
        'min_step_value': min_step,
        'max_step_value': max_step,
        'min_track_radius_mm': round(min_r, 2),
        'max_track_radius_mm': round(max_r, 2),
        'total_follower_travel_mm': round(max_r - min_r, 2),
        'cut_depth_mm': round(cut_depth, 2),
        'profile_mode': profile_mode,
        'dwell_ratio': round(dwell_ratio, 2),
        'corner_fillet': round(corner_fillet, 2),
        'cutter_radius': round(cutter_radius, 1),
        'needle_position': clean_pos,
        'needle_position_label': pos_label,
        'preset_number': str(preset_number),
        'machine_setting': clean_setting,
        'disc_thickness_mm': clean_setting,
    }
