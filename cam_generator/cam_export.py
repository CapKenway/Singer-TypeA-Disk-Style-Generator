"""
Singer Type A Cam SVG and DXF Exporter.

Generates:
1. Interactive, rich raw inline SVG fragments for HTMX live preview with:
   - Dynamic stitch counts (6 to 36 stitches).
   - Mechanical cam profile modes (Stepped Gear-like with dwell flats & right-angle sawteeth, Spline, Linear).
   - Dual flanking face etching (West / 180° pattern block, East / 0° maker's mark block).
   - Anti-crack radiused keyway end.
2. Production-ready standalone SVG files calibrated for laser cutting with dedicated ETCH and CUT layers.
3. Industry-standard AutoCAD R12 DXF vector files with multi-layer cut/etch sequencing.

Pure Python standard library implementation (no numpy/scipy/shapely/matplotlib).
"""

import math
from typing import List, Tuple, Optional
from .cam_geometry import (
    calculate_outer_perimeter,
    calculate_inner_bore_with_keyway,
    calculate_left_flank_pattern_block,
    calculate_right_flank_maker_block,
    calculate_top_header_block,
    sanitize_stitch_steps,
    stitch_values_to_radii,
    OUTER_MAX_RADIUS,
    BASE_TRACK_RADIUS,
    MAX_TRACK_RADIUS,
    INNER_BORE_RADIUS,
    KEYWAY_WIDTH,
    KEYWAY_DEPTH,
    DEFAULT_STITCH_COUNT,
    MIN_STITCHES,
    MAX_STITCHES,
    DEFAULT_KERF_OFFSET,
    DEFAULT_CUTTER_RADIUS,
    PERIMETER_ROTATION_OFFSET,
)
from .cam_vector_font import (
    render_vector_text_arc,
    render_vector_text_linear,
    strokes_to_svg_path_d,
)


def _polygon_to_svg_path(points: List[Tuple[float, float]], close: bool = True) -> str:
    """Converts a sequence of (x, y) coordinates into an SVG path d-string."""
    if not points:
        return ""
    d_parts = [f"M {points[0][0]:.3f} {points[0][1]:.3f}"]
    for x, y in points[1:]:
        d_parts.append(f"L {x:.3f} {y:.3f}")
    if close:
        d_parts.append("Z")
    return " ".join(d_parts)


def generate_cam_svg(
    steps: List[float],
    kerf_offset: float = DEFAULT_KERF_OFFSET,
    profile_mode: str = 'straight_wall',
    dwell_ratio: float = 0.60,
    corner_fillet: float = 0.50,
    cutter_radius: float = DEFAULT_CUTTER_RADIUS,
    cut_depth: float = 5.0,
    stitch_fill_mode: str = "unfilled",
    name_rotation: float = 90.0,
    is_preview: bool = True,
    cam_label: str = "ZIG-ZAG",
    maker_name: str = "KENWAY",
    enable_etch: bool = True,
    round_keyway: bool = True,
    needle_position: str = "L",
    preset_number: str = "1",
    disc_thickness: Any = None,
    machine_setting: float = 3.0
) -> str:
    """
    Generates an SVG representation of the Singer Type A cam.
    
    Supports:
      - Dynamic stitch count (N = len(steps)).
      - Authentic OEM straight radial walls & subtractive rotary cutter milling.
      - Dual flanking face etching curved along concentric bore arcs.
      - Top North header block with preset/cam number, needle gauge symbol, and machine dial setting.
      - Clean South keyway strictly free of text or annotations.
      - 'unfilled' (open running wave) and 'filled' (solid satin stitch embroidery).
      - Configurable radial cut depth (bight swing amplitude).
    """
    total_stitches = max(MIN_STITCHES, min(MAX_STITCHES, len(steps)))
    sanitized_steps = sanitize_stitch_steps(steps, total_stitches)
    
    # Resolve machine setting (optimal dial 1.0 to 8.0)
    resolved_setting = disc_thickness if disc_thickness is not None else machine_setting
    try:
        resolved_setting = max(1.0, min(8.0, float(resolved_setting)))
    except (ValueError, TypeError):
        resolved_setting = 3.0
    outer_poly = calculate_outer_perimeter(
        sanitized_steps,
        kerf_offset=kerf_offset,
        profile_mode=profile_mode,
        dwell_ratio=dwell_ratio,
        corner_fillet=corner_fillet,
        cutter_radius=cutter_radius,
        cut_depth=cut_depth
    )
    inner_poly = calculate_inner_bore_with_keyway(kerf_offset, round_keyway=round_keyway)
    
    outer_d = _polygon_to_svg_path(outer_poly, close=True)
    inner_d = _polygon_to_svg_path(inner_poly, close=True)
    
    # Flanking face etching geometry (unfilled vs filled solid satin stitch)
    left_block = calculate_left_flank_pattern_block(
        sanitized_steps,
        stitch_fill_mode=stitch_fill_mode,
        needle_position=needle_position,
        cut_depth=cut_depth
    ) if enable_etch else None
    right_block = calculate_right_flank_maker_block(
        maker_name,
        stitch_count=total_stitches,
        name_rotation=name_rotation,
        needle_position=needle_position,
        cut_depth=cut_depth
    ) if enable_etch else None
    top_block = calculate_top_header_block(
        preset_number=preset_number,
        needle_position=needle_position,
        machine_setting=resolved_setting
    ) if enable_etch else None

    # Generate pure vector curve strokes for text (zero-font CNC / laser compatibility)
    title_strokes: List[List[Tuple[float, float]]] = []
    subtitle_strokes: List[List[Tuple[float, float]]] = []
    maker_strokes: List[List[Tuple[float, float]]] = []
    needle_strokes: List[List[Tuple[float, float]]] = []
    top_preset_strokes: List[List[Tuple[float, float]]] = []
    top_specs_strokes: List[List[Tuple[float, float]]] = []
    needle_symbol_strokes: List[List[Tuple[float, float]]] = []

    title_curve_d = ""
    subtitle_curve_d = ""
    maker_curve_d = ""
    needle_curve_d = ""
    top_frame_d = ""
    top_preset_d = ""
    top_specs_d = ""
    needle_symbol_d = ""
    clean_pos = needle_position.strip().upper() if needle_position in ('L', 'C', 'R') else 'L'

    if enable_etch and left_block and right_block:
        title_strokes = render_vector_text_arc(
            text=cam_label,
            radius=left_block.get('title_r', 13.85),
            start_angle_deg=154.0,
            end_angle_deg=206.0,
            char_height=0.75
        )
        subtitle_strokes = render_vector_text_arc(
            text=f"{total_stitches}-STITCH (NEEDLE {clean_pos})",
            radius=left_block.get('subtitle_r', 10.65),
            start_angle_deg=156.0,
            end_angle_deg=204.0,
            char_height=0.58
        )
        if abs(name_rotation) < 1.0:
            maker_strokes = render_vector_text_linear(
                text=maker_name,
                center_x=12.3,
                center_y=0.0,
                char_height=1.10,
                rotation_deg=0.0
            )
        elif name_rotation < 0:
            maker_strokes = render_vector_text_arc(
                text=maker_name,
                radius=right_block.get('maker_r', 12.3),
                start_angle_deg=26.0,
                end_angle_deg=-26.0,
                char_height=1.10
            )
        else:
            maker_strokes = render_vector_text_arc(
                text=maker_name,
                radius=right_block.get('maker_r', 12.3),
                start_angle_deg=-26.0,
                end_angle_deg=26.0,
                char_height=1.10
            )

        # Needle position vector text etched directly on the Right Flank arc
        pos_full = "LEFT" if clean_pos == 'L' else ("CENTER" if clean_pos == 'C' else "RIGHT")
        needle_strokes = render_vector_text_arc(
            text=f"NEEDLE: {pos_full}",
            radius=right_block.get('needle_r', 10.6),
            start_angle_deg=-26.0,
            end_angle_deg=26.0,
            char_height=0.62
        )

        title_curve_d = strokes_to_svg_path_d(title_strokes)
        subtitle_curve_d = strokes_to_svg_path_d(subtitle_strokes)
        maker_curve_d = strokes_to_svg_path_d(maker_strokes)
        needle_curve_d = strokes_to_svg_path_d(needle_strokes)

    if enable_etch and top_block:
        top_preset_strokes = render_vector_text_arc(
            text=top_block['preset_text'],
            radius=top_block['preset_r'],
            start_angle_deg=top_block['preset_start_deg'],
            end_angle_deg=top_block['preset_end_deg'],
            char_height=0.92
        )
        top_specs_strokes = render_vector_text_arc(
            text=top_block['specs_text'],
            radius=top_block['specs_r'],
            start_angle_deg=top_block['specs_start_deg'],
            end_angle_deg=top_block['specs_end_deg'],
            char_height=0.62
        )
        needle_symbol_strokes = top_block.get('needle_symbol_strokes', [])
        top_frame_d = _polygon_to_svg_path(top_block['frame_polygon'], close=True)
        top_preset_d = strokes_to_svg_path_d(top_preset_strokes)
        top_specs_d = strokes_to_svg_path_d(top_specs_strokes)
        needle_symbol_d = strokes_to_svg_path_d(needle_symbol_strokes)
    
    if not is_preview:
        # Standalone laser-ready production SVG
        clean_cam_name = cam_label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").upper()
        clean_maker = (maker_name.strip() or "KENWAY").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").upper()
        
        svg_xml = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            '<svg xmlns="http://www.w3.org/2000/svg"',
            '     width="46mm" height="46mm"',
            '     viewBox="-23 -23 46 46"',
            '     version="1.1">',
            '  <title>Singer Type A Cam - Laser Cut &amp; Etch File</title>',
            f'  <!-- Max OD: 42mm | Min Track: 32mm | Stitches: {total_stitches} | Profile: {profile_mode} -->',
            f'  <!-- Maker: {clean_maker} (Right Flank, {name_rotation:.0f}° Twist) | Pattern: {clean_cam_name} (Left Flank) -->',
            '  <!-- Cutting sequence: 1. Cut inner bore -> 2. Etch flanking face blocks -> 3. Cut outer perimeter -->',
            '',
            '  <!-- LAYER 1: INNER BORE & RADIUSED KEYWAY CUT (Cut First) -->',
            '  <g id="layer_inner_bore_cut" fill="none" stroke="#0000FF" stroke-width="0.1">',
            f'    <path id="inner_spindle_bore_14mm" d="{inner_d}" />',
            '  </g>',
            '',
        ]
        
        if enable_etch and left_block and right_block:
            left_frame_d = _polygon_to_svg_path(left_block['frame_polygon'], close=True)
            left_wave_d = _polygon_to_svg_path(left_block['waveform_points'], close=False)
            is_filled_left = (left_block.get('stitch_fill_mode') == 'filled')
            satin_hatches_d = strokes_to_svg_path_d(left_block.get('satin_hatch_strokes', []))
            satin_ribbon_d = _polygon_to_svg_path(left_block.get('satin_ribbon_polygon', []), close=True)
            
            right_frame_d = _polygon_to_svg_path(right_block['frame_polygon'], close=True)
            right_inner_d = _polygon_to_svg_path(right_block['inner_accent_polygon'], close=True)
            diamond_d = _polygon_to_svg_path(right_block['diamond_points'], close=True)
            bottom_diamond_d = _polygon_to_svg_path(right_block.get('bottom_diamond_points', []), close=True)
            
            left_pattern_svg = []
            if is_filled_left:
                left_pattern_svg.append(f'    <path id="left_flank_satin_hatches" d="{satin_hatches_d}" stroke-width="0.07" stroke-linecap="round" />')
                left_pattern_svg.append(f'    <path id="left_flank_waveform" d="{left_wave_d}" stroke-width="0.08" />')
            else:
                left_pattern_svg.append(f'    <path id="left_flank_waveform" d="{left_wave_d}" stroke-width="0.10" />')
            left_pattern_markup = "\n".join(left_pattern_svg)

            svg_xml.extend([
                '  <!-- LAYER 2: FLANKING & TOP FACE ETCHING / SCORING (Etch Second) -->',
                '  <g id="layer_etch_design" fill="none" stroke="#00AA00" stroke-width="0.08">',
                '    <!-- FAR LEFT FLANK: STITCH PATTERN BLOCK (Vector Curve Outlines) -->',
                f'    <path id="left_flank_frame" d="{left_frame_d}" stroke-dasharray="0.8 0.4" />',
                left_pattern_markup,
                f'    <path id="left_flank_title_curves" d="{title_curve_d}" stroke-width="0.07" stroke-linecap="round" stroke-linejoin="round" />',
                f'    <path id="left_flank_sub_curves" d="{subtitle_curve_d}" stroke-width="0.05" stroke-linecap="round" stroke-linejoin="round" />',
                '',
                '    <!-- FAR RIGHT FLANK: MAKER\'S MARK BLOCK (Vector Curve Outlines) -->',
                f'    <path id="right_flank_frame" d="{right_frame_d}" stroke-dasharray="0.8 0.4" />',
                f'    <path id="maker_diamond_top" d="{diamond_d}" fill="#00AA00" />',
                f'    <path id="maker_diamond_bottom" d="{bottom_diamond_d}" fill="#00AA00" />',
                f'    <path id="right_flank_maker_curves" d="{maker_curve_d}" stroke-width="0.07" stroke-linecap="round" stroke-linejoin="round" />',
                f'    <path id="right_flank_needle_curves" d="{needle_curve_d}" stroke-width="0.06" stroke-linecap="round" stroke-linejoin="round" />',
                '',
                '    <!-- NORTH / TOP: CAM PRESET & NEEDLE SPEC BLOCK (Vector Curve Outlines) -->',
                f'    <path id="top_header_frame" d="{top_frame_d}" stroke-dasharray="0.8 0.4" />',
                f'    <path id="top_header_preset_curves" d="{top_preset_d}" stroke-width="0.08" stroke-linecap="round" stroke-linejoin="round" />',
                f'    <path id="top_header_needle_symbol" d="{needle_symbol_d}" stroke-width="0.08" stroke-linecap="round" stroke-linejoin="round" />',
                f'    <path id="top_header_specs_curves" d="{top_specs_d}" stroke-width="0.06" stroke-linecap="round" stroke-linejoin="round" />',
                '  </g>',
                '',
            ])
            
        svg_xml.extend([
            '  <!-- LAYER 3: OUTER CAM PERIMETER CUT (Cut Last) -->',
            '  <g id="layer_outer_cam_cut" fill="none" stroke="#FF0000" stroke-width="0.1">',
            f'    <path id="outer_perimeter_profile" d="{outer_d}" />',
            '  </g>',
            '</svg>',
        ])
        return "\n".join(svg_xml)

    # Rich HTMX Live Preview SVG
    view_box_dim = 27.0
    stitch_radii = stitch_values_to_radii(sanitized_steps)
    rad_step = (2.0 * math.pi) / float(total_stitches)
    
    sector_lines = []
    stitch_badges = []
    
    for i in range(total_stitches):
        angle = PERIMETER_ROTATION_OFFSET + (float(i) * rad_step)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        x1 = (BASE_TRACK_RADIUS - 0.8) * cos_a
        y1 = (BASE_TRACK_RADIUS - 0.8) * sin_a
        x2 = (OUTER_MAX_RADIUS + 1.2) * cos_a
        y2 = (OUTER_MAX_RADIUS + 1.2) * sin_a
        sector_lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#334155" stroke-width="0.15" stroke-dasharray="0.6 0.6" />'
        )
        
        lbl_r = OUTER_MAX_RADIUS + 3.0
        lbl_x = lbl_r * cos_a
        lbl_y = lbl_r * sin_a
        
        pt_r = stitch_radii[i]
        pt_x = pt_r * cos_a
        pt_y = pt_r * sin_a
        
        stitch_badges.append(
            f'<circle cx="{pt_x:.2f}" cy="{pt_y:.2f}" r="0.45" fill="#38bdf8" />'
        )
        # Display number if not overcrowded
        if total_stitches <= 24 or (i % 2 == 0):
            stitch_badges.append(
                f'<text x="{lbl_x:.2f}" y="{lbl_y:.2f}" fill="#94a3b8" '
                f'font-size="1.2" font-family="ui-monospace, monospace" '
                f'font-weight="bold" text-anchor="middle" dominant-baseline="middle">'
                f'{i+1}</text>'
            )

    sector_markup = "\n    ".join(sector_lines)
    badge_markup = "\n    ".join(stitch_badges)
    combined_body_d = f"{outer_d} {inner_d}"

    etch_markup = ""
    if enable_etch and left_block and right_block:
        left_frame_d = _polygon_to_svg_path(left_block['frame_polygon'], close=True)
        left_wave_d = _polygon_to_svg_path(left_block['waveform_points'], close=False)
        is_filled_left = (left_block.get('stitch_fill_mode') == 'filled')
        satin_hatches_d = strokes_to_svg_path_d(left_block.get('satin_hatch_strokes', []))
        satin_ribbon_d = _polygon_to_svg_path(left_block.get('satin_ribbon_polygon', []), close=True)

        right_frame_d = _polygon_to_svg_path(right_block['frame_polygon'], close=True)
        right_inner_d = _polygon_to_svg_path(right_block['inner_accent_polygon'], close=True)
        diamond_d = _polygon_to_svg_path(right_block['diamond_points'], close=True)
        bottom_diamond_d = _polygon_to_svg_path(right_block.get('bottom_diamond_points', []), close=True)
        
        if is_filled_left:
            left_pattern_render = f"""
      <path id="preview-left-satin-ribbon" d="{satin_ribbon_d}" fill="#064e3b" fill-opacity="0.35" stroke="none" />
      <path id="preview-left-satin-hatches" d="{satin_hatches_d}" fill="none" stroke="#34d399" stroke-width="0.08" stroke-linecap="round" />
      <path id="preview-left-waveform" d="{left_wave_d}" fill="none" stroke="#10b981" stroke-width="0.10" stroke-linecap="round" stroke-linejoin="round" />
"""
        else:
            left_nodes = "".join(f'<circle cx="{pt[0]:.2f}" cy="{pt[1]:.2f}" r="0.08" fill="#34d399" />' for pt in left_block['node_points'])
            left_pattern_render = f"""
      <path id="preview-left-waveform" d="{left_wave_d}" fill="none" stroke="#34d399" stroke-width="0.12" stroke-linecap="round" stroke-linejoin="round" />
      {left_nodes}
"""
        
        etch_markup = f"""
  <!-- DUAL FLANKING FACE ETCHING (Fine Vector Hairlines - Crisp CAD Display) -->
  <g id="face-etching">
    <!-- LEFT FLANK: STITCH PATTERN BLOCK (West / 180°, Fine Vector Curves) -->
    <g id="etch-left-pattern-block">
      <path d="{left_frame_d}" fill="#064e3b" fill-opacity="0.10" stroke="#10b981" stroke-width="0.08" stroke-dasharray="0.8 0.4" />
      {left_pattern_render}
      <path id="preview-left-title-curves" d="{title_curve_d}" fill="none" stroke="#34d399" stroke-width="0.08" stroke-linecap="round" stroke-linejoin="round" />
      <path id="preview-left-sub-curves" d="{subtitle_curve_d}" fill="none" stroke="#059669" stroke-width="0.06" stroke-linecap="round" stroke-linejoin="round" />
    </g>

    <!-- RIGHT FLANK: MAKER'S MARK BLOCK (East / 0°, Fine Vector Curves) -->
    <g id="etch-right-maker-block">
      <path d="{right_frame_d}" fill="#064e3b" fill-opacity="0.10" stroke="#10b981" stroke-width="0.08" stroke-dasharray="0.8 0.4" />
      <path d="{diamond_d}" fill="#34d399" stroke="none" />
      <path d="{bottom_diamond_d}" fill="#34d399" stroke="none" />
      <path id="preview-right-maker-curves" d="{maker_curve_d}" fill="none" stroke="#34d399" stroke-width="0.09" stroke-linecap="round" stroke-linejoin="round" />
      <path id="preview-right-needle-curves" d="{needle_curve_d}" fill="none" stroke="#10b981" stroke-width="0.07" stroke-linecap="round" stroke-linejoin="round" />
    </g>

    <!-- NORTH / TOP: PRESET NUMBER, NEEDLE GAUGE SYMBOL & THICKNESS (Fine Vector Curves) -->
    <g id="etch-top-header-block">
      <path d="{top_frame_d}" fill="#064e3b" fill-opacity="0.10" stroke="#10b981" stroke-width="0.08" stroke-dasharray="0.8 0.4" />
      <path id="preview-top-preset-curves" d="{top_preset_d}" fill="none" stroke="#38bdf8" stroke-width="0.09" stroke-linecap="round" stroke-linejoin="round" />
      <path id="preview-top-needle-symbol" d="{needle_symbol_d}" fill="none" stroke="#34d399" stroke-width="0.09" stroke-linecap="round" stroke-linejoin="round" />
      <path id="preview-top-specs-curves" d="{top_specs_d}" fill="none" stroke="#10b981" stroke-width="0.07" stroke-linecap="round" stroke-linejoin="round" />
    </g>
  </g>
"""

    svg_preview = f"""<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="-{view_box_dim} -{view_box_dim} {view_box_dim*2} {view_box_dim*2}"
     class="w-full h-full max-h-[520px] select-none"
     id="cam-svg-render">
  <defs>
    <pattern id="cam-grid" width="2" height="2" patternUnits="userSpaceOnUse">
      <path d="M 2 0 L 0 0 0 2" fill="none" stroke="#1e293b" stroke-width="0.08" />
    </pattern>
    <radialGradient id="acrylic-gradient" cx="0%" cy="0%" r="90%">
      <stop offset="0%" stop-color="#0284c7" stop-opacity="0.30" />
      <stop offset="60%" stop-color="#0369a1" stop-opacity="0.22" />
      <stop offset="100%" stop-color="#082f49" stop-opacity="0.40" />
    </radialGradient>
    <filter id="laser-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="0.10" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background Grid -->
  <rect x="-{view_box_dim}" y="-{view_box_dim}" width="{view_box_dim*2}" height="{view_box_dim*2}" fill="#0b1120" />
  <rect x="-{view_box_dim}" y="-{view_box_dim}" width="{view_box_dim*2}" height="{view_box_dim*2}" fill="url(#cam-grid)" />

  <!-- Reference Pitch Guides -->
  <!-- Outer Maximum Disc Limit (OD = 42.0mm, R = 21.0mm) -->
  <circle cx="0" cy="0" r="{OUTER_MAX_RADIUS}" fill="none" stroke="#475569" stroke-width="0.2" stroke-dasharray="1.2 0.8" />
  <!-- Base Track Deflection (Min Diameter = 32.0mm, R = 16.0mm) -->
  <circle cx="0" cy="0" r="{BASE_TRACK_RADIUS}" fill="none" stroke="#0284c7" stroke-width="0.18" stroke-dasharray="0.8 0.8" opacity="0.6" />
  <!-- Nominal Spindle Bore (14.0mm Bore, R = 7.0mm) -->
  <circle cx="0" cy="0" r="{INNER_BORE_RADIUS}" fill="none" stroke="#64748b" stroke-width="0.15" stroke-dasharray="0.5 0.5" />

  <!-- Radial Stitch Angular Sectors ({total_stitches} Stitches) -->
  <g id="sector-rays">
    {sector_markup}
  </g>

  <!-- Cam Acrylic Body -->
  <path d="{combined_body_d}"
        fill="url(#acrylic-gradient)"
        fill-rule="evenodd" />

  {etch_markup}

  <!-- Laser Cut Boundary Outlines -->
  <path d="{outer_d}"
        fill="none"
        stroke="#38bdf8"
        stroke-width="0.22"
        filter="url(#laser-glow)" />

  <!-- Inner Spindle Bore + Radiused Anti-Crack Keyway Cut -->
  <path d="{inner_d}"
        fill="#0b1120"
        stroke="#f43f5e"
        stroke-width="0.22" />

  <!-- Center Crosshairs -->
  <line x1="-3.0" y1="0" x2="3.0" y2="0" stroke="#f43f5e" stroke-width="0.15" />
  <line x1="0" y1="-3.0" x2="0" y2="3.0" stroke="#f43f5e" stroke-width="0.15" />

  <!-- Stitch Control Nodes & Indices -->
  <g id="stitch-nodes">
    {badge_markup}
  </g>


  <!-- Visual Dimension Scale / Specs Callout -->
  <g transform="translate(-25.0, 22.0)">
    <rect x="0" y="0" width="14" height="3.2" rx="0.5" fill="#1e293b" fill-opacity="0.9" stroke="#334155" stroke-width="0.15" />
    <line x1="1" y1="2.0" x2="11" y2="2.0" stroke="#38bdf8" stroke-width="0.3" />
    <line x1="1" y1="1.3" x2="1" y2="2.7" stroke="#38bdf8" stroke-width="0.3" />
    <line x1="11" y1="1.3" x2="11" y2="2.7" stroke="#38bdf8" stroke-width="0.3" />
    <text x="6" y="1.3" fill="#e2e8f0" font-size="0.8" font-family="ui-monospace, monospace" text-anchor="middle">10 mm SCALE</text>
  </g>
</svg>"""
    return svg_preview.strip()


def generate_cam_dxf(
    steps: List[float],
    kerf_offset: float = DEFAULT_KERF_OFFSET,
    profile_mode: str = 'straight_wall',
    dwell_ratio: float = 0.60,
    corner_fillet: float = 0.50,
    cutter_radius: float = DEFAULT_CUTTER_RADIUS,
    cut_depth: float = 5.0,
    stitch_fill_mode: str = "unfilled",
    name_rotation: float = 90.0,
    enable_etch: bool = True,
    round_keyway: bool = True,
    maker_name: str = "KENWAY",
    cam_label: str = "PLAIN ZIG-ZAG",
    needle_position: str = "L",
    preset_number: str = "1",
    disc_thickness: Any = None,
    machine_setting: float = 3.0
) -> str:
    """
    Generates a compliant, production-grade AutoCAD R12 DXF file (pure Python).
    
    Includes:
      - CUT_INNER (Bore & radiused keyway)
      - ETCH_DESIGN (Flanking pattern & maker mark blocks with pure vector curve text,
                     open wave outline or filled satin embroidery hatching)
      - CUT_OUTER (42mm outer cam perimeter)
    """
    total_stitches = max(MIN_STITCHES, min(MAX_STITCHES, len(steps)))
    sanitized_steps = sanitize_stitch_steps(steps, total_stitches)

    # Resolve machine setting (optimal dial 1.0 to 8.0)
    resolved_setting = disc_thickness if disc_thickness is not None else machine_setting
    try:
        resolved_setting = max(1.0, min(8.0, float(resolved_setting)))
    except (ValueError, TypeError):
        resolved_setting = 3.0

    outer_poly = calculate_outer_perimeter(
        sanitized_steps,
        kerf_offset=kerf_offset,
        profile_mode=profile_mode,
        dwell_ratio=dwell_ratio,
        corner_fillet=corner_fillet,
        cutter_radius=cutter_radius,
        cut_depth=cut_depth
    )
    inner_poly = calculate_inner_bore_with_keyway(kerf_offset, round_keyway=round_keyway)
    
    left_block = calculate_left_flank_pattern_block(
        sanitized_steps,
        stitch_fill_mode=stitch_fill_mode,
        needle_position=needle_position,
        cut_depth=cut_depth
    ) if enable_etch else None
    right_block = calculate_right_flank_maker_block(
        maker_name,
        stitch_count=total_stitches,
        name_rotation=name_rotation,
        needle_position=needle_position,
        cut_depth=cut_depth
    ) if enable_etch else None
    top_block = calculate_top_header_block(
        preset_number=preset_number,
        needle_position=needle_position,
        machine_setting=resolved_setting
    ) if enable_etch else None

    # Generate pure vector curve strokes for text in DXF (zero-font CNC / laser compatibility)
    title_strokes: List[List[Tuple[float, float]]] = []
    subtitle_strokes: List[List[Tuple[float, float]]] = []
    maker_strokes: List[List[Tuple[float, float]]] = []
    needle_strokes: List[List[Tuple[float, float]]] = []
    top_preset_strokes: List[List[Tuple[float, float]]] = []
    top_specs_strokes: List[List[Tuple[float, float]]] = []
    needle_symbol_strokes: List[List[Tuple[float, float]]] = []
    clean_pos = needle_position.strip().upper() if needle_position in ('L', 'C', 'R') else 'L'

    if enable_etch and left_block and right_block:
        title_strokes = render_vector_text_arc(
            text=cam_label,
            radius=left_block.get('title_r', 13.85),
            start_angle_deg=154.0,
            end_angle_deg=206.0,
            char_height=0.75
        )
        subtitle_strokes = render_vector_text_arc(
            text=f"{total_stitches}-STITCH (NEEDLE {clean_pos})",
            radius=left_block.get('subtitle_r', 10.65),
            start_angle_deg=156.0,
            end_angle_deg=204.0,
            char_height=0.58
        )
        if abs(name_rotation) < 1.0:
            maker_strokes = render_vector_text_linear(
                text=maker_name,
                center_x=12.3,
                center_y=0.0,
                char_height=1.10,
                rotation_deg=0.0
            )
        elif name_rotation < 0:
            maker_strokes = render_vector_text_arc(
                text=maker_name,
                radius=right_block.get('maker_r', 12.3),
                start_angle_deg=26.0,
                end_angle_deg=-26.0,
                char_height=1.10
            )
        else:
            maker_strokes = render_vector_text_arc(
                text=maker_name,
                radius=right_block.get('maker_r', 12.3),
                start_angle_deg=-26.0,
                end_angle_deg=26.0,
                char_height=1.10
            )

        # Needle position vector text etched directly on the Right Flank arc in DXF
        pos_full = "LEFT" if clean_pos == 'L' else ("CENTER" if clean_pos == 'C' else "RIGHT")
        needle_strokes = render_vector_text_arc(
            text=f"NEEDLE: {pos_full}",
            radius=right_block.get('needle_r', 10.6),
            start_angle_deg=-26.0,
            end_angle_deg=26.0,
            char_height=0.62
        )

    if enable_etch and top_block:
        top_preset_strokes = render_vector_text_arc(
            text=top_block['preset_text'],
            radius=top_block['preset_r'],
            start_angle_deg=top_block['preset_start_deg'],
            end_angle_deg=top_block['preset_end_deg'],
            char_height=0.92
        )
        top_specs_strokes = render_vector_text_arc(
            text=top_block['specs_text'],
            radius=top_block['specs_r'],
            start_angle_deg=top_block['specs_start_deg'],
            end_angle_deg=top_block['specs_end_deg'],
            char_height=0.62
        )
        needle_symbol_strokes = top_block.get('needle_symbol_strokes', [])
    
    dxf_lines: List[str] = [
        "0", "SECTION",
        "2", "HEADER",
        "9", "$ACADVER",
        "1", "AC1009",
        "9", "$INSUNITS",
        "70", "4",
        "0", "ENDSEC",
        
        "0", "SECTION",
        "2", "TABLES",
        "0", "TABLE",
        "2", "LAYER",
        "70", "4",
        "0", "LAYER",
        "2", "CUT_INNER",
        "70", "0",
        "62", "5",
        "6", "CONTINUOUS",
        "0", "LAYER",
        "2", "ETCH_DESIGN",
        "70", "0",
        "62", "3",
        "6", "CONTINUOUS",
        "0", "LAYER",
        "2", "CUT_OUTER",
        "70", "0",
        "62", "1",
        "6", "CONTINUOUS",
        "0", "LAYER",
        "2", "REFERENCE",
        "70", "0",
        "62", "7",
        "6", "CONTINUOUS",
        "0", "ENDTAB",
        "0", "ENDSEC",
        
        "0", "SECTION",
        "2", "ENTITIES",
    ]
    
    # CUT_INNER
    dxf_lines.extend([
        "0", "POLYLINE",
        "8", "CUT_INNER",
        "66", "1",
        "70", "1",
    ])
    for x, y in inner_poly:
        dxf_lines.extend([
            "0", "VERTEX",
            "8", "CUT_INNER",
            "10", f"{x:.4f}",
            "20", f"{y:.4f}",
            "30", "0.0",
        ])
    dxf_lines.extend(["0", "SEQEND", "8", "CUT_INNER"])
    
    # ETCH_DESIGN
    if enable_etch and left_block and right_block:
        # Left frame
        dxf_lines.extend([
            "0", "POLYLINE",
            "8", "ETCH_DESIGN",
            "66", "1",
            "70", "1",
        ])
        for x, y in left_block['frame_polygon']:
            dxf_lines.extend([
                "0", "VERTEX",
                "8", "ETCH_DESIGN",
                "10", f"{x:.4f}",
                "20", f"{y:.4f}",
                "30", "0.0",
            ])
        dxf_lines.extend(["0", "SEQEND", "8", "ETCH_DESIGN"])
        
        # Left waveform & satin embroidery hatching
        dxf_lines.extend([
            "0", "POLYLINE",
            "8", "ETCH_DESIGN",
            "66", "1",
            "70", "0",
        ])
        for x, y in left_block['waveform_points']:
            dxf_lines.extend([
                "0", "VERTEX",
                "8", "ETCH_DESIGN",
                "10", f"{x:.4f}",
                "20", f"{y:.4f}",
                "30", "0.0",
            ])
        dxf_lines.extend(["0", "SEQEND", "8", "ETCH_DESIGN"])

        # Dense satin stitch hatch lines for 'filled' mode in DXF
        if left_block.get('stitch_fill_mode') == 'filled' and 'satin_hatch_strokes' in left_block:
            for stroke in left_block['satin_hatch_strokes']:
                if len(stroke) >= 2:
                    dxf_lines.extend([
                        "0", "LINE",
                        "8", "ETCH_DESIGN",
                        "10", f"{stroke[0][0]:.4f}",
                        "20", f"{stroke[0][1]:.4f}",
                        "30", "0.0",
                        "11", f"{stroke[1][0]:.4f}",
                        "21", f"{stroke[1][1]:.4f}",
                        "31", "0.0",
                    ])

        # Right frame
        dxf_lines.extend([
            "0", "POLYLINE",
            "8", "ETCH_DESIGN",
            "66", "1",
            "70", "1",
        ])
        for x, y in right_block['frame_polygon']:
            dxf_lines.extend([
                "0", "VERTEX",
                "8", "ETCH_DESIGN",
                "10", f"{x:.4f}",
                "20", f"{y:.4f}",
                "30", "0.0",
            ])
        dxf_lines.extend(["0", "SEQEND", "8", "ETCH_DESIGN"])

        # Right diamonds
        dxf_lines.extend([
            "0", "POLYLINE",
            "8", "ETCH_DESIGN",
            "66", "1",
            "70", "1",
        ])
        for x, y in right_block['diamond_points']:
            dxf_lines.extend([
                "0", "VERTEX",
                "8", "ETCH_DESIGN",
                "10", f"{x:.4f}",
                "20", f"{y:.4f}",
                "30", "0.0",
            ])
        dxf_lines.extend(["0", "SEQEND", "8", "ETCH_DESIGN"])

        if 'bottom_diamond_points' in right_block:
            dxf_lines.extend([
                "0", "POLYLINE",
                "8", "ETCH_DESIGN",
                "66", "1",
                "70", "1",
            ])
            for x, y in right_block['bottom_diamond_points']:
                dxf_lines.extend([
                    "0", "VERTEX",
                    "8", "ETCH_DESIGN",
                    "10", f"{x:.4f}",
                    "20", f"{y:.4f}",
                    "30", "0.0",
                ])
            dxf_lines.extend(["0", "SEQEND", "8", "ETCH_DESIGN"])

        # NORTH / TOP HEADER BLOCK (Frame & Vector Letter Curves)
        if top_block:
            dxf_lines.extend([
                "0", "POLYLINE",
                "8", "ETCH_DESIGN",
                "66", "1",
                "70", "1",
            ])
            for x, y in top_block['frame_polygon']:
                dxf_lines.extend([
                    "0", "VERTEX",
                    "8", "ETCH_DESIGN",
                    "10", f"{x:.4f}",
                    "20", f"{y:.4f}",
                    "30", "0.0",
                ])
            dxf_lines.extend(["0", "SEQEND", "8", "ETCH_DESIGN"])

        # PURE VECTOR TEXT CURVES (Etched directly as CNC / Laser toolpaths)
        all_vector_strokes = (
            title_strokes + subtitle_strokes + maker_strokes + needle_strokes +
            top_preset_strokes + top_specs_strokes + needle_symbol_strokes
        )
        for stroke in all_vector_strokes:
            if len(stroke) < 2:
                continue
            dxf_lines.extend([
                "0", "POLYLINE",
                "8", "ETCH_DESIGN",
                "66", "1",
                "70", "0",  # open polyline for letter strokes
            ])
            for x, y in stroke:
                dxf_lines.extend([
                    "0", "VERTEX",
                    "8", "ETCH_DESIGN",
                    "10", f"{x:.4f}",
                    "20", f"{y:.4f}",
                    "30", "0.0",
                ])
            dxf_lines.extend(["0", "SEQEND", "8", "ETCH_DESIGN"])
    
    # CUT_OUTER
    dxf_lines.extend([
        "0", "POLYLINE",
        "8", "CUT_OUTER",
        "66", "1",
        "70", "1",
    ])
    for x, y in outer_poly:
        dxf_lines.extend([
            "0", "VERTEX",
            "8", "CUT_OUTER",
            "10", f"{x:.4f}",
            "20", f"{y:.4f}",
            "30", "0.0",
        ])
    dxf_lines.extend(["0", "SEQEND", "8", "CUT_OUTER"])

    # REFERENCE
    dxf_lines.extend([
        "0", "LINE",
        "8", "REFERENCE",
        "10", "-3.0",
        "20", "0.0",
        "30", "0.0",
        "11", "3.0",
        "21", "0.0",
        "31", "0.0",
        "0", "LINE",
        "8", "REFERENCE",
        "10", "0.0",
        "20", "-3.0",
        "30", "0.0",
        "11", "0.0",
        "21", "3.0",
        "31", "0.0",
    ])
    
    dxf_lines.extend([
        "0", "ENDSEC",
        "0", "EOF",
    ])
    
    return "\n".join(dxf_lines) + "\n"
