"""
Views for Singer Type A Cam Generator.

Provides:
- Dynamic stitch count (6 to 36 stitches).
- Authentic mechanical gear-tooth profile with circular dwell flats & right-angle sawteeth.
- Dual flanking face etching & radiused keyway end.
- index_view: Renders main workbench dashboard.
- preview_cam_view: HTMX reactive endpoint returning raw inline SVG.
- download_cam_view: Stateless in-memory streaming of laser-ready SVG or DXF files.
- preset_view: HTMX endpoint returning populated slider controls for a selected preset.
"""

from typing import List, Tuple
from django.http import HttpResponse, HttpRequest, Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
import re

from .cam_geometry import (
    sanitize_stitch_steps,
    get_cam_metrics,
    DEFAULT_KERF_OFFSET,
    DEFAULT_STITCH_COUNT,
    DEFAULT_CUTTER_RADIUS,
    MIN_STITCHES,
    MAX_STITCHES,
)
from .cam_export import generate_cam_svg, generate_cam_dxf
from .presets import PRESETS, DEFAULT_PRESET_ID, get_preset


def _extract_steps_and_options(request: HttpRequest) -> Tuple[List[float], float, str, str, bool, bool, str, float, float, float, float, str, float, str, str, float]:
    """
    Extracts and sanitizes stitch values, stitch count, kerf offset, pattern label,
    maker's mark name, etch flag, keyway rounding flag, profile mode, dwell ratio,
    corner fillet, maker mark rotation angle, rotary cutter radius, stitch fill mode,
    radial cut depth, needle position (L, C, R), preset number, and disc thickness.
    """
    data = request.POST if request.method == 'POST' else request.GET
    
    # Dynamic stitch count
    raw_count = data.get('stitch_count', str(DEFAULT_STITCH_COUNT))
    try:
        count = int(raw_count)
        count = max(MIN_STITCHES, min(MAX_STITCHES, count))
    except (ValueError, TypeError):
        count = DEFAULT_STITCH_COUNT
        
    steps: List[float] = []
    for i in range(count):
        raw = data.get(f'step_{i}')
        try:
            steps.append(float(raw) if raw is not None else 0.0)
        except (ValueError, TypeError):
            steps.append(0.0)
            
    sanitized_steps = sanitize_stitch_steps(steps, count=count)
    
    # Kerf offset
    raw_kerf = data.get('kerf_offset', str(DEFAULT_KERF_OFFSET))
    try:
        kerf = float(raw_kerf)
        kerf = max(0.0, min(1.0, kerf))
    except (ValueError, TypeError):
        kerf = DEFAULT_KERF_OFFSET
        
    # Profile mode (subtractive = rotary cutter scoop, straight_wall = true straight radial walls, gear, sawtooth, spline, linear)
    profile_mode = data.get('profile_mode', 'subtractive').strip().lower()
    if profile_mode not in ('subtractive', 'straight_wall', 'gear', 'sawtooth', 'spline', 'linear'):
        profile_mode = 'subtractive'
        
    # Dwell ratio (gear tooth plateau flatness)
    raw_dwell = data.get('dwell_ratio', '0.60')
    try:
        dwell_ratio = float(raw_dwell)
        dwell_ratio = max(0.0, min(0.85, dwell_ratio))
    except (ValueError, TypeError):
        dwell_ratio = 0.60
        
    # Corner blend fillet smoothness
    raw_fillet = data.get('corner_fillet', '0.05')
    try:
        corner_fillet = float(raw_fillet)
        corner_fillet = max(0.0, min(1.0, corner_fillet))
    except (ValueError, TypeError):
        corner_fillet = 0.05
        
    # Rotary cutter radius (mm) for subtractive milling mode
    raw_cutter = data.get('cutter_radius', str(DEFAULT_CUTTER_RADIUS))
    try:
        cutter_radius = float(raw_cutter)
        cutter_radius = max(1.5, min(25.0, cutter_radius))
    except (ValueError, TypeError):
        cutter_radius = DEFAULT_CUTTER_RADIUS
        
    # Radial cut depth / bight travel window (mm) - Extended up to 8.0mm
    raw_cut_depth = data.get('cut_depth', '5.0')
    try:
        cut_depth = float(raw_cut_depth)
        cut_depth = max(1.0, min(8.0, cut_depth))
    except (ValueError, TypeError):
        cut_depth = 5.0

    # Needle position ('L' for Left, 'C' for Center, 'R' for Right)
    needle_pos = data.get('needle_position', 'L').strip().upper()
    if needle_pos not in ('L', 'C', 'R'):
        needle_pos = 'L'

    # Stitch fill mode ('unfilled' for open line wave vs 'filled' for solid satin stitch)
    stitch_fill_mode = data.get('stitch_fill_mode', 'unfilled').strip().lower()
    # Center and Right needle positions are definitely filled
    if needle_pos in ('C', 'R'):
        stitch_fill_mode = 'filled'
    elif stitch_fill_mode not in ('unfilled', 'filled'):
        stitch_fill_mode = 'unfilled'

    # Maker mark text rotation angle (Default: 90 degrees twisted)
    raw_rot = data.get('name_rotation', '90.0')
    try:
        name_rotation = float(raw_rot)
    except (ValueError, TypeError):
        name_rotation = 90.0
        
    cam_name = data.get('cam_name', 'Plain Zig-Zag').strip()
    clean_cam = re.sub(r'[^a-zA-Z0-9_\- ]', '', cam_name) or 'SINGER TYPE A'
    
    maker_name = data.get('maker_name', 'KENWAY').strip()
    clean_maker = re.sub(r'[^a-zA-Z0-9_\- ]', '', maker_name) or 'KENWAY'

    # Separate Preset Number input (e.g. 38, 1, 276338, CAM #1)
    preset_num_raw = data.get('preset_number', '1').strip()
    clean_preset_num = re.sub(r'[^a-zA-Z0-9_\-# ]', '', preset_num_raw) or '1'

    # Machine setting (optimal stitch width / thickness setting on machine, 1.0 to 8.0)
    raw_setting = data.get('machine_setting', data.get('disc_thickness', '3.0'))
    try:
        machine_setting = float(raw_setting)
        machine_setting = max(1.0, min(8.0, machine_setting))
    except (ValueError, TypeError):
        machine_setting = 3.0
    
    enable_etch = data.get('enable_etch', 'true').lower() in ('true', '1', 'yes', 'on')
    round_keyway = data.get('round_keyway', 'true').lower() in ('true', '1', 'yes', 'on')
    
    return (
        sanitized_steps, kerf, clean_cam, clean_maker,
        enable_etch, round_keyway, profile_mode, dwell_ratio,
        corner_fillet, name_rotation, cutter_radius,
        stitch_fill_mode, cut_depth, needle_pos,
        clean_preset_num, machine_setting
    )


@require_http_methods(["GET"])
def index_view(request: HttpRequest) -> HttpResponse:
    """Renders the main workbench dashboard."""
    preset_key = request.GET.get('preset', DEFAULT_PRESET_ID)
    preset = get_preset(preset_key)
    
    count = len(preset.get('steps', [])) or DEFAULT_STITCH_COUNT
    initial_steps = sanitize_stitch_steps(preset['steps'], count=count)
    initial_kerf = DEFAULT_KERF_OFFSET
    initial_label = preset.get('name', 'Plain Zig-Zag')
    initial_maker = 'KENWAY'
    initial_mode = 'subtractive'
    initial_dwell = 0.60
    initial_fillet = 0.05
    initial_rot = 90.0
    initial_cutter = DEFAULT_CUTTER_RADIUS
    initial_fill_mode = 'unfilled'
    initial_cut_depth = 5.0
    initial_needle_pos = preset.get('needle_position', 'L')
    initial_preset_num = preset.get('preset_number', '1')
    initial_setting = 3.0
    
    initial_svg = generate_cam_svg(
        initial_steps,
        initial_kerf,
        profile_mode=initial_mode,
        dwell_ratio=initial_dwell,
        corner_fillet=initial_fillet,
        cutter_radius=initial_cutter,
        cut_depth=initial_cut_depth,
        stitch_fill_mode=initial_fill_mode,
        name_rotation=initial_rot,
        is_preview=True,
        cam_label=initial_label,
        maker_name=initial_maker,
        enable_etch=True,
        round_keyway=True,
        needle_position=initial_needle_pos,
        preset_number=initial_preset_num,
        machine_setting=initial_setting
    )
    metrics = get_cam_metrics(
        initial_steps,
        initial_kerf,
        profile_mode=initial_mode,
        dwell_ratio=initial_dwell,
        corner_fillet=initial_fillet,
        cutter_radius=initial_cutter,
        needle_position=initial_needle_pos,
        cut_depth=initial_cut_depth,
        preset_number=initial_preset_num,
        machine_setting=initial_setting
    )
    
    stitch_controls = [
        {
            'index': i,
            'number': i + 1,
            'angle': round(i * (360.0 / count), 1),
            'value': initial_steps[i],
        }
        for i in range(count)
    ]
    
    context = {
        'presets': PRESETS,
        'selected_preset': preset,
        'stitch_controls': stitch_controls,
        'stitch_count': count,
        'kerf_offset': initial_kerf,
        'initial_svg': initial_svg,
        'metrics': metrics,
        'cam_name': initial_label,
        'maker_name': initial_maker,
        'round_keyway': True,
        'profile_mode': initial_mode,
        'dwell_ratio': initial_dwell,
        'corner_fillet': initial_fillet,
        'cutter_radius': initial_cutter,
        'cut_depth': initial_cut_depth,
        'stitch_fill_mode': initial_fill_mode,
        'name_rotation': initial_rot,
        'needle_position': initial_needle_pos,
        'preset_number': initial_preset_num,
        'machine_setting': initial_setting,
        'disc_thickness': initial_setting,
    }
    return render(request, 'cam_generator/workbench.html', context)


@require_http_methods(["GET", "POST"])
def preview_cam_view(request: HttpRequest) -> HttpResponse:
    """
    Dedicated HTMX endpoint.
    Calculates the mechanical cam profile in real-time and returns
    only the raw <svg> element fragment to swap into #cam-preview-container.
    """
    (
        steps, kerf, cam_label, maker_name,
        enable_etch, round_keyway, profile_mode, dwell_ratio,
        corner_fillet, name_rotation, cutter_radius,
        stitch_fill_mode, cut_depth, needle_position,
        preset_number, machine_setting
    ) = _extract_steps_and_options(request)
    
    svg_fragment = generate_cam_svg(
        steps,
        kerf,
        profile_mode=profile_mode,
        dwell_ratio=dwell_ratio,
        corner_fillet=corner_fillet,
        cutter_radius=cutter_radius,
        cut_depth=cut_depth,
        stitch_fill_mode=stitch_fill_mode,
        name_rotation=name_rotation,
        is_preview=True,
        cam_label=cam_label,
        maker_name=maker_name,
        enable_etch=enable_etch,
        round_keyway=round_keyway,
        needle_position=needle_position,
        preset_number=preset_number,
        machine_setting=machine_setting
    )
    return HttpResponse(svg_fragment, content_type="image/svg+xml")


@require_http_methods(["GET", "POST"])
def download_cam_view(request: HttpRequest) -> HttpResponse:
    """
    Stateless in-memory file delivery endpoint.
    Streams a production-ready standalone SVG or AutoCAD DXF file
    without writing anything to disk.
    """
    data = request.POST if request.method == 'POST' else request.GET
    file_format = data.get('format', 'svg').strip().lower()
    
    (
        steps, kerf, cam_name, maker_name,
        enable_etch, round_keyway, profile_mode, dwell_ratio,
        corner_fillet, name_rotation, cutter_radius,
        stitch_fill_mode, cut_depth, needle_position,
        preset_number, machine_setting
    ) = _extract_steps_and_options(request)
    
    clean_filename = re.sub(r'[^a-zA-Z0-9_\-]', '_', f"{maker_name}_{cam_name}") or 'singer_cam_42mm'
    
    if file_format == 'dxf':
        dxf_content = generate_cam_dxf(
            steps,
            kerf,
            profile_mode=profile_mode,
            dwell_ratio=dwell_ratio,
            corner_fillet=corner_fillet,
            cutter_radius=cutter_radius,
            cut_depth=cut_depth,
            stitch_fill_mode=stitch_fill_mode,
            name_rotation=name_rotation,
            enable_etch=enable_etch,
            round_keyway=round_keyway,
            maker_name=maker_name,
            cam_label=cam_name,
            needle_position=needle_position,
            preset_number=preset_number,
            machine_setting=machine_setting
        )
        response = HttpResponse(dxf_content, content_type="application/dxf")
        response['Content-Disposition'] = f'attachment; filename="{clean_filename}.dxf"'
        return response
    
    # Standalone laser-ready SVG
    svg_content = generate_cam_svg(
        steps,
        kerf,
        profile_mode=profile_mode,
        dwell_ratio=dwell_ratio,
        corner_fillet=corner_fillet,
        cutter_radius=cutter_radius,
        cut_depth=cut_depth,
        stitch_fill_mode=stitch_fill_mode,
        name_rotation=name_rotation,
        is_preview=False,
        cam_label=cam_name,
        maker_name=maker_name,
        enable_etch=enable_etch,
        round_keyway=round_keyway,
        needle_position=needle_position,
        preset_number=preset_number,
        machine_setting=machine_setting
    )
    response = HttpResponse(svg_content, content_type="image/svg+xml")
    response['Content-Disposition'] = f'attachment; filename="{clean_filename}.svg"'
    return response


@require_http_methods(["GET"])
def preset_view(request: HttpRequest, preset_id: str) -> HttpResponse:
    """
    HTMX endpoint that returns the updated slider controls for a selected preset
    and triggers an immediate preview refresh.
    """
    if preset_id not in PRESETS:
        raise Http404("Preset not found")
        
    preset = PRESETS[preset_id]
    count = len(preset.get('steps', [])) or DEFAULT_STITCH_COUNT
    steps = sanitize_stitch_steps(preset['steps'], count=count)
    
    stitch_controls = [
        {
            'index': i,
            'number': i + 1,
            'angle': round(i * (360.0 / count), 1),
            'value': steps[i],
        }
        for i in range(count)
    ]
    
    return render(request, 'cam_generator/partials/sliders_form.html', {
        'stitch_controls': stitch_controls,
        'selected_preset': preset,
    })
