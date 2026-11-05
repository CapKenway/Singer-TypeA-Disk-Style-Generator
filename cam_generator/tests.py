"""
Test suite for Singer Type A Cam Generator.

Covers:
- Physical geometric dimensions (42mm OD, 32mm min track, 14mm bore, 5mm key hole length).
- Dynamic stitch count (6 to 36 stitches).
- Mechanical cam profiles:
  - Gear-like mode with flat circular dwell plateaus & right-angle sawtooth transitions.
  - Spline and linear modes.
- Anti-crack stress relief radiused keyway geometry (R = 1.5mm semi-circular fillet).
- Dual flanking face etching (West / 180° pattern block, East / 0° maker's mark block).
- Laser kerf compensation (outer expansion & inner shrinkage).
- Pure-Python SVG and AutoCAD DXF export engines with dedicated ETCH and CUT layers.
- HTMX preview endpoint, interactive wave studio dashboard, and stateless downloads.
"""

from django.test import TestCase, Client
from django.urls import reverse
import math

from .cam_geometry import (
    OUTER_MAX_RADIUS,
    INNER_BORE_RADIUS,
    KEYWAY_WIDTH,
    KEYWAY_DEPTH,
    BASE_TRACK_RADIUS,
    MAX_TRACK_RADIUS,
    TOTAL_TRACK_WIDTH,
    DEFAULT_STITCH_COUNT,
    RADIAL_STEP_PER_VALUE,
    DEFAULT_KERF_OFFSET,
    sanitize_stitch_steps,
    stitch_values_to_radii,
    catmull_rom_spline_1d,
    calculate_outer_perimeter,
    calculate_inner_bore_with_keyway,
    calculate_left_flank_pattern_block,
    calculate_right_flank_maker_block,
    calculate_top_header_block,
    get_cam_metrics,
)
from .cam_export import generate_cam_svg, generate_cam_dxf
from .presets import PRESETS, get_preset


class CamGeometryTestCase(TestCase):
    """Verifies core geometric calculations and physical measurements."""

    def test_geometric_constants(self):
        """Ensures all physical dimensions match updated Singer Type A measurements."""
        self.assertEqual(OUTER_MAX_RADIUS, 21.0)       # 42.0 mm outer max diameter
        self.assertEqual(BASE_TRACK_RADIUS, 16.0)      # 32.0 mm min track diameter
        self.assertEqual(MAX_TRACK_RADIUS, 21.0)       # 42.0 mm max track diameter
        self.assertEqual(TOTAL_TRACK_WIDTH, 5.0)       # 5.0 mm total bight swing
        self.assertEqual(INNER_BORE_RADIUS, 7.0)       # 14.0 mm spindle key bore
        self.assertEqual(KEYWAY_DEPTH, 5.0)            # 5.0 mm key hole length
        self.assertEqual(KEYWAY_WIDTH, 3.0)
        self.assertEqual(DEFAULT_STITCH_COUNT, 18)
        self.assertAlmostEqual(RADIAL_STEP_PER_VALUE, 5.0 / 12.0)

    def test_dynamic_stitch_counts(self):
        """Verifies that cam perimeter adapts to dynamic stitch counts (12, 16, 24)."""
        for count in (12, 16, 24):
            steps = [0, 12] * (count // 2)
            poly = calculate_outer_perimeter(steps, samples_per_wedge=10)
            self.assertEqual(len(poly), count * 10)

    def test_mechanical_gear_tooth_dwell_and_sawtooth(self):
        """
        Verifies that 'gear' profile mode creates flat circular dwell plateaus
        centered symmetrically at stitch points, and merges consecutive identical stitches.
        """
        # Alternating 2-step square blocks: 12, 12, 0, 0
        steps = [12.0, 12.0, 0.0, 0.0]
        poly = calculate_outer_perimeter(
            steps,
            kerf_offset=0.0,
            profile_mode='gear',
            dwell_ratio=0.60,
            samples_per_wedge=20
        )
        # Wedge 0 (from Stitch 0=12 to Stitch 1=12): continuous unbroken dwell plateau at 21.0mm
        for idx in range(0, 20):
            x, y = poly[idx]
            r = math.sqrt(x*x + y*y)
            self.assertAlmostEqual(r, 21.0, places=2)
            
        # Wedge 2 (from Stitch 2=0 to Stitch 3=0): continuous unbroken dwell plateau at 16.0mm
        for idx in range(40, 60):
            x, y = poly[idx]
            r = math.sqrt(x*x + y*y)
            self.assertAlmostEqual(r, 16.0, places=2)

    def test_sawtooth_right_angle_drop(self):
        """Verifies that 'sawtooth' mode creates a steep right-angle drop on falling edges."""
        steps = [0.0, 12.0, 0.0, 12.0]
        poly = calculate_outer_perimeter(
            steps,
            kerf_offset=0.0,
            profile_mode='sawtooth',
            samples_per_wedge=50
        )
        # In wedge 1 (drop from 12.0 to 0.0):
        # Before t=0.46 (index 50 + 20 = 70): at 21.0mm
        x_top, y_top = poly[70]
        self.assertAlmostEqual(math.sqrt(x_top*x_top + y_top*y_top), 21.0, places=2)
        # After t=0.54 (index 50 + 30 = 80): dropped to 16.0mm
        x_bot, y_bot = poly[80]
        self.assertAlmostEqual(math.sqrt(x_bot*x_bot + y_bot*y_bot), 16.0, places=2)

    def test_subtractive_rotary_cutter_perimeter(self):
        """
        Verifies that 'subtractive' profile mode simulates a circular rotary cutter bit
        scooping pockets out of the 42.0mm outer disc blank.
        """
        # Alternating peak (12) and valley (0)
        steps = [12.0, 0.0, 12.0, 0.0]  # 4 stitches (90 deg apart)
        poly = calculate_outer_perimeter(
            steps,
            kerf_offset=0.0,
            profile_mode='subtractive',
            cutter_radius=5.0,
            samples_per_wedge=30
        )
        # Stitch 0 (angle = 0): Peak (12) -> should remain at 21.0mm outer circle
        p0 = poly[0]
        r0 = math.sqrt(p0[0]**2 + p0[1]**2)
        self.assertAlmostEqual(r0, 21.0, places=1)
        
        # Stitch 1 (angle = 90 deg, index 30): Valley (0) -> scooped to 16.0mm base track
        p1 = poly[30]
        r1 = math.sqrt(p1[0]**2 + p1[1]**2)
        self.assertAlmostEqual(r1, 16.0, places=1)

    def test_straight_radial_walls(self):
        """Verifies that 'straight_wall' creates 100% straight radial walls at midpoint."""
        steps = [12.0, 0.0] * 9  # 18 stitches
        poly = calculate_outer_perimeter(
            steps,
            kerf_offset=0.0,
            profile_mode='straight_wall',
            corner_fillet=0.0,
            samples_per_wedge=20
        )
        # Find points around the first step (angle_mid = 0.5 * 2pi/18 = 10 deg)
        # The wall drops from 21.0mm down to 16.0mm along the exact same ray angle
        wall_found = False
        for idx in range(len(poly) - 1):
            p1 = poly[idx]
            p2 = poly[idx + 1]
            r1 = math.sqrt(p1[0]**2 + p1[1]**2)
            r2 = math.sqrt(p2[0]**2 + p2[1]**2)
            if abs(r1 - 21.0) < 0.05 and abs(r2 - 16.0) < 0.05:
                # Check that both points lie along the same radial ray (within 0.01 rad)
                a1 = math.atan2(p1[1], p1[0])
                a2 = math.atan2(p2[1], p2[0])
                self.assertAlmostEqual(a1, a2, places=3)
                wall_found = True
                break
        self.assertTrue(wall_found, "Straight radial wall transition not found")

    def test_keyway_anti_crack_round(self):
        """Verifies radiused keyway end reaches apex at radius 12.0mm."""
        poly_rounded = calculate_inner_bore_with_keyway(kerf_offset=0.0, round_keyway=True)
        max_y = max(pt[1] for pt in poly_rounded)
        self.assertAlmostEqual(max_y, 12.0, places=2)

    def test_flanking_etching_positions_and_90deg_twist(self):
        """Verifies West flank (left) and East flank (right) etching positions and 90° text twist."""
        steps = [0, 12] * 9
        left = calculate_left_flank_pattern_block(steps)
        right = calculate_right_flank_maker_block("KENWAY", stitch_count=18, name_rotation=90.0)
        
        self.assertLess(left['center_x'], -5.0)
        self.assertGreater(right['center_x'], 5.0)
        self.assertEqual(right['maker_name'], "KENWAY")
        self.assertEqual(right['name_rotation'], 90.0)
        self.assertIn('bottom_diamond_points', right)

    def test_sanitize_stitch_steps(self):
        """Tests that values are clamped to [0.0, 12.0]."""
        raw = [-5, 0, 6.5, 12, 15, "invalid"]
        cleaned = sanitize_stitch_steps(raw, count=6)
        self.assertEqual(len(cleaned), 6)
        self.assertEqual(cleaned[0], 0.0)
        self.assertEqual(cleaned[2], 6.5)
        self.assertEqual(cleaned[3], 12.0)
        self.assertEqual(cleaned[4], 12.0)
        self.assertEqual(cleaned[5], 0.0)

    def test_stitch_values_to_radii(self):
        """Verifies mapping from deflection step to physical millimeter radius."""
        steps = [0.0, 6.0, 12.0]
        radii = stitch_values_to_radii(steps)
        self.assertAlmostEqual(radii[0], 16.0)  # Step 0 = 16.0 mm
        self.assertAlmostEqual(radii[1], 18.5)  # Step 6 = 18.5 mm
        self.assertAlmostEqual(radii[2], 21.0)  # Step 12 = 21.0 mm

    def test_kerf_offset_adjustment(self):
        """Verifies outer expansion and inner shrinkage."""
        steps = [6.0] * 18
        poly_no_kerf = calculate_outer_perimeter(steps, kerf_offset=0.0)
        poly_with_kerf = calculate_outer_perimeter(steps, kerf_offset=0.20)
        
        x_no_kerf = poly_no_kerf[0][0]
        x_with_kerf = poly_with_kerf[0][0]
        self.assertAlmostEqual(x_with_kerf - x_no_kerf, 0.10, places=3)


class CamExportTestCase(TestCase):
    """Verifies pure-Python SVG and DXF generation with gear profiles and flanking etching."""

    def setUp(self):
        self.steps = [0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12]

    def test_svg_preview_markup_with_gear_mode(self):
        """Generates inline SVG fragment with vector curve text rather than font tags."""
        svg = generate_cam_svg(
            self.steps,
            kerf_offset=0.15,
            profile_mode='gear',
            dwell_ratio=0.60,
            corner_fillet=0.50,
            name_rotation=90.0,
            is_preview=True,
            cam_label="ZIGZAG",
            maker_name="KENWAY",
            enable_etch=True,
            round_keyway=True
        )
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        self.assertIn('id="cam-svg-render"', svg)
        self.assertIn('id="etch-left-pattern-block"', svg)
        self.assertIn('id="etch-right-maker-block"', svg)
        self.assertIn('preview-left-title-curves', svg)
        self.assertIn('preview-right-maker-curves', svg)
        # Verify text is exported as vector curves, NOT raw font textPath tags
        self.assertNotIn('<textPath', svg)

    def test_svg_standalone_markup(self):
        """Generates complete standalone laser-cutting XML with vector curve text."""
        svg = generate_cam_svg(
            self.steps,
            kerf_offset=0.15,
            profile_mode='gear',
            dwell_ratio=0.60,
            corner_fillet=0.50,
            name_rotation=90.0,
            is_preview=False,
            cam_label="ZIGZAG",
            maker_name="KENWAY",
            enable_etch=True,
            round_keyway=True
        )
        self.assertIn('<?xml version="1.0" encoding="UTF-8"', svg)
        self.assertIn('width="46mm"', svg)
        self.assertIn('id="layer_inner_bore_cut"', svg)
        self.assertIn('id="layer_etch_design"', svg)
        self.assertIn('id="layer_outer_cam_cut"', svg)
        self.assertIn('left_flank_title_curves', svg)
        self.assertIn('right_flank_maker_curves', svg)
        # Zero font tags for 100% laser cutter / LightBurn compatibility
        self.assertNotIn('<textPath', svg)
        self.assertNotIn('<text ', svg)

    def test_dxf_generation(self):
        """Generates compliant AutoCAD R12 DXF with vector text curves on ETCH_DESIGN."""
        dxf = generate_cam_dxf(
            self.steps,
            kerf_offset=0.15,
            profile_mode='gear',
            dwell_ratio=0.60,
            corner_fillet=0.50,
            name_rotation=90.0,
            enable_etch=True,
            round_keyway=True,
            maker_name="KENWAY",
            cam_label="ZIGZAG"
        )
        self.assertIn("AC1009", dxf)
        self.assertIn("CUT_INNER", dxf)
        self.assertIn("ETCH_DESIGN", dxf)
        self.assertIn("CUT_OUTER", dxf)
        # DXF contains multiple open polylines (70 0) for etched letter curves
        self.assertIn("70\n0", dxf)
        self.assertTrue(dxf.strip().endswith("EOF"))


class CamViewsTestCase(TestCase):
    """Verifies Django 6 views and HTMX response fragments."""

    def setUp(self):
        self.client = Client()

    def test_index_view(self):
        """Workbench dashboard loads successfully with status 200."""
        response = self.client.get(reverse('index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "42mm")
        self.assertContains(response, "14mm")
        self.assertContains(response, "KENWAY")
        self.assertContains(response, 'id="interactive-wave-svg"')
        self.assertContains(response, 'name="profile_mode"')
        self.assertContains(response, 'name="dwell_ratio"')
        self.assertContains(response, 'workbench-layout')
        self.assertContains(response, 'straight_wall')

    def test_preview_cam_view_dynamic_stitches_and_gear_mode(self):
        """HTMX preview endpoint handles dynamic stitch counts and gear dwell mode."""
        params = {
            'stitch_count': '12',
            'profile_mode': 'gear',
            'dwell_ratio': '0.60',
            'kerf_offset': '0.15',
            'cam_name': 'SAWTOOTH',
            'maker_name': 'KENWAY',
            'enable_etch': 'true',
            'round_keyway': 'true',
        }
        for i in range(12):
            params[f'step_{i}'] = 12 if i % 2 == 0 else 0
        response = self.client.get(reverse('preview_cam_view'), data=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertContains(response, '<svg')
        self.assertContains(response, 'preview-left-title-curves')
        self.assertContains(response, 'preview-right-maker-curves')

    def test_preview_cam_view_subtractive_cutter_mode(self):
        """HTMX preview endpoint handles subtractive rotary cutter milling mode."""
        params = {
            'stitch_count': '18',
            'profile_mode': 'subtractive',
            'cutter_radius': '5.0',
            'kerf_offset': '0.15',
            'cam_name': 'ZIGZAG',
            'maker_name': 'KENWAY',
            'enable_etch': 'true',
            'round_keyway': 'true',
        }
        for i in range(18):
            params[f'step_{i}'] = 12 if i % 2 == 0 else 0
        response = self.client.get(reverse('preview_cam_view'), data=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertContains(response, '<svg')
        self.assertContains(response, 'preview-left-title-curves')
        self.assertContains(response, 'preview-right-maker-curves')
        self.assertNotContains(response, '<textPath')

    def test_vector_font_arc_and_linear(self):
        """Verifies vector stroke font generates valid curve coordinates on arcs and lines."""
        from .cam_vector_font import render_vector_text_arc, render_vector_text_linear
        
        # Test circular arc rendering
        strokes = render_vector_text_arc("KENWAY", radius=12.3, start_angle_deg=-26.0, end_angle_deg=26.0, char_height=1.2)
        self.assertGreater(len(strokes), 5)
        for s in strokes:
            self.assertGreaterEqual(len(s), 2)
            for x, y in s:
                r = math.sqrt(x*x + y*y)
                # Points should lie radially around the target radius 12.3mm (+/- char_height/2)
                self.assertAlmostEqual(r, 12.3, delta=0.8)
                
        # Test linear rendering
        lin_strokes = render_vector_text_linear("KENWAY", center_x=10.0, center_y=5.0, char_height=1.2, rotation_deg=0.0)
        self.assertGreater(len(lin_strokes), 5)
        for s in lin_strokes:
            for x, y in s:
                self.assertAlmostEqual(y, 5.0, delta=0.8)

    def test_download_cam_view_svg_with_gear_profile(self):
        """Downloads standalone laser-ready SVG with gear profile."""
        data = {
            'format': 'svg',
            'stitch_count': '16',
            'profile_mode': 'gear',
            'dwell_ratio': '0.50',
            'cam_name': 'sawtooth_cam',
            'maker_name': 'KENWAY',
            'enable_etch': 'true',
            'round_keyway': 'true'
        }
        for i in range(16):
            data[f'step_{i}'] = 6
        response = self.client.post(reverse('download_cam_view'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertIn('attachment; filename="KENWAY_sawtooth_cam.svg"', response['Content-Disposition'])

    def test_download_cam_view_dxf(self):
        """Downloads AutoCAD DXF as an attachment."""
        data = {
            'format': 'dxf',
            'stitch_count': '18',
            'profile_mode': 'gear',
            'dwell_ratio': '0.55',
            'cam_name': 'sawtooth_cam',
            'maker_name': 'KENWAY',
            'enable_etch': 'true',
            'round_keyway': 'true'
        }
        for i in range(18):
            data[f'step_{i}'] = 8
        response = self.client.post(reverse('download_cam_view'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/dxf')
        self.assertIn('attachment; filename="KENWAY_sawtooth_cam.dxf"', response['Content-Disposition'])
        self.assertContains(response, 'ETCH_DESIGN')

    def test_stitch_fill_mode_and_cut_depth(self):
        """Verifies filled (satin stitch) and unfilled (open wave) modes and cut depth scaling."""
        # Unfilled mode
        svg_unfilled = generate_cam_svg(
            [0, 12] * 9,
            stitch_fill_mode='unfilled',
            cut_depth=5.0,
            is_preview=True
        )
        self.assertIn('preview-left-waveform', svg_unfilled)
        self.assertNotIn('preview-left-satin-hatches', svg_unfilled)

        # Filled (solid satin stitch) mode
        svg_filled = generate_cam_svg(
            [0, 12] * 9,
            stitch_fill_mode='filled',
            cut_depth=3.0,
            is_preview=True
        )
        self.assertIn('preview-left-satin-ribbon', svg_filled)
        self.assertIn('preview-left-satin-hatches', svg_filled)

        # Configurable cut depth
        radii_full = stitch_values_to_radii([0.0, 12.0], cut_depth=5.0)
        self.assertAlmostEqual(radii_full[0], 16.0)
        self.assertAlmostEqual(radii_full[1], 21.0)

        radii_shallow = stitch_values_to_radii([0.0, 12.0], cut_depth=3.0)
        self.assertAlmostEqual(radii_shallow[0], 18.0)
        self.assertAlmostEqual(radii_shallow[1], 21.0)

    def test_disc_38_preset_and_geometry(self):
        """Verifies Disc #38 (Part #276338) preset and 6-lobe square dwell geometry."""
        preset = get_preset('disc_38')
        self.assertEqual(preset['id'], 'disc_38')
        self.assertEqual(len(preset['steps']), 24)
        # Verify 6-lobe alternating 2-step block pattern [12, 12, 0, 0] * 6
        self.assertEqual(preset['steps'], [12, 12, 0, 0] * 6)
        
        # Test perimeter generation with straight_wall profile
        poly = calculate_outer_perimeter(
            preset['steps'],
            profile_mode='straight_wall',
            corner_fillet=0.0,
            samples_per_wedge=16
        )
        self.assertGreater(len(poly), 100)
        # Verify peaks and valleys stay within 16mm and 21mm limits
        for x, y in poly:
            r = math.sqrt(x*x + y*y)
            self.assertGreaterEqual(r, 15.8)
            self.assertLessEqual(r, 21.2)

    def test_left_flank_vector_text_orientation_unmirrored(self):
        """
        Verifies that Left Flank pattern label text curves clockwise from South-West (154°)
        to North-West (206°), with the normal vector pointing radially outward toward the
        disc perimeter so letters are 100% upright, readable, and never mirrored.
        """
        from .cam_vector_font import render_vector_text_arc, render_vector_text_linear

        # Render 'PLAIN ZIG-ZAG' on the left flank arc
        strokes = render_vector_text_arc(
            text="PLAIN ZIG-ZAG",
            radius=13.8,
            start_angle_deg=154.0,
            end_angle_deg=206.0,
            char_height=0.85
        )
        self.assertGreater(len(strokes), 0)

        # First stroke of first letter 'P' should be in the South-West quadrant (x < 0, y > 0)
        p_pt = strokes[0][0]
        self.assertLess(p_pt[0], 0.0) # West (negative x)
        self.assertGreater(p_pt[1], 0.0) # South (positive y)

        # Last stroke of last letter 'G' should be in the North-West quadrant (x < 0, y < 0)
        g_pt = strokes[-1][-1]
        self.assertLess(g_pt[0], 0.0) # West (negative x)
        self.assertLess(g_pt[1], 0.0) # North (negative y)

        # Verify that linear text has upright vertical polarity (cap height at negative y in SVG)
        linear_strokes = render_vector_text_linear(
            text="L",
            center_x=0.0,
            center_y=0.0,
            char_height=1.0,
            rotation_deg=0.0
        )
        # 'L' top point (v=1.0) must have y < 0 (upward in SVG screen space)
        top_y = min(pt[1] for stroke in linear_strokes for pt in stroke)
        bot_y = max(pt[1] for stroke in linear_strokes for pt in stroke)
        self.assertLess(top_y, 0.0)
        self.assertGreaterEqual(bot_y, 0.0)

    def test_needle_position_in_preview_and_presets(self):
        """Verifies 3 needle position support (L, C, R) across views and presets."""
        for pos in ('L', 'C', 'R'):
            response = self.client.post(reverse('preview_cam_view'), {
                'needle_position': pos,
                'cam_name': f'Scallop {pos}',
                'step_0': '6',
                'step_1': '12',
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'<svg', response.content)

    def test_needle_position_filling_mechanics(self):
        """
        Verifies needle position satin fill mechanics:
        - Center ('C'): Mirrored from center line into filled diamonds.
        - Right ('R'): Inverted negative filling (top filled down to wave).
        - Left ('L'): Positive filling (bottom filled up to wave).
        - Automatic filled mode activation for Center and Right.
        """
        steps = [0.0, 12.0, 0.0, 12.0]

        # Left Needle: positive fill from baseline
        block_l = calculate_left_flank_pattern_block(steps, needle_position='L')
        self.assertEqual(block_l['needle_position'], 'L')

        # Center Needle: mirrored into filled diamonds
        block_c = calculate_left_flank_pattern_block(steps, needle_position='C')
        self.assertEqual(block_c['needle_position'], 'C')
        self.assertEqual(block_c['stitch_fill_mode'], 'filled')
        self.assertGreater(len(block_c['satin_hatch_strokes']), 0)

        # Right Needle: negative filling
        block_r = calculate_left_flank_pattern_block(steps, needle_position='R')
        self.assertEqual(block_r['needle_position'], 'R')
        self.assertEqual(block_r['stitch_fill_mode'], 'filled')
        self.assertGreater(len(block_r['satin_hatch_strokes']), 0)

    def test_extended_cut_depth_up_to_8mm(self):
        """Verifies support for configurable cut depth / bight up to 8.0 mm."""
        # At cut_depth=8.0, step 0 -> 13.0mm, step 12 -> 21.0mm
        radii_8mm = stitch_values_to_radii([0.0, 12.0], cut_depth=8.0)
        self.assertAlmostEqual(radii_8mm[0], 13.0)
        self.assertAlmostEqual(radii_8mm[1], 21.0)

        # Test metrics report 8.0mm travel
        metrics = get_cam_metrics([0.0, 12.0], cut_depth=8.0)
        self.assertEqual(metrics['cut_depth_mm'], 8.0)
        self.assertAlmostEqual(metrics['total_follower_travel_mm'], 8.0)

        # Verify preview endpoint accepts cut_depth=8.0
        response = self.client.post(reverse('preview_cam_view'), {
            'cut_depth': '8.0',
            'stitch_count': '18',
            'step_0': '0',
            'step_1': '12',
        })
        self.assertEqual(response.status_code, 200)

    def test_needle_position_etched_in_disk_svg_and_dxf(self):
        """Verifies needle position is etched onto the disc in SVG preview, standalone SVG, and DXF."""
        for pos in ('L', 'C', 'R'):
            # SVG preview: etched on top North header block and right flank
            svg_preview = generate_cam_svg(
                [0, 12] * 9,
                needle_position=pos,
                is_preview=True,
                preset_number="38",
                disc_thickness=3.0
            )
            self.assertIn('preview-top-preset-curves', svg_preview)
            self.assertIn('preview-top-needle-symbol', svg_preview)
            self.assertIn('preview-top-specs-curves', svg_preview)

            # Keyway clean check: South keyway (y > 7) must NOT have text or arrow overlays
            self.assertNotIn('ROUNDED KEY (5mm)', svg_preview)
            self.assertNotIn('y="10.2"', svg_preview)

            # Standalone laser SVG
            svg_laser = generate_cam_svg(
                [0, 12] * 9,
                needle_position=pos,
                is_preview=False,
                preset_number="38",
                disc_thickness=3.0
            )
            self.assertIn('top_header_preset_curves', svg_laser)
            self.assertIn('top_header_needle_symbol', svg_laser)
            self.assertIn('top_header_specs_curves', svg_laser)

            # DXF
            dxf = generate_cam_dxf(
                [0, 12] * 9,
                needle_position=pos,
                preset_number="38",
                disc_thickness=3.0
            )
            self.assertIn('ETCH_DESIGN', dxf)

    def test_top_header_block_geometry(self):
        """Verifies top header block calculation, preset number, needle symbol, and optimal machine setting."""
        block = calculate_top_header_block(preset_number="38", needle_position="C", machine_setting=3.0)
        self.assertEqual(block['preset_text'], "CAM #38")
        self.assertIn("NEEDLE C", block['specs_text'])
        self.assertIn("SET:3.0", block['specs_text'])
        self.assertEqual(block['needle_position'], "C")
        self.assertEqual(block['machine_setting'], 3.0)

        # Verify all frame polygon vertices are in the top sector (Y < 0)
        for x, y in block['frame_polygon']:
            self.assertLess(y, 0.0)

        # Verify needle symbol strokes exist and are located in North sector
        self.assertGreater(len(block['needle_symbol_strokes']), 6)
        for stroke in block['needle_symbol_strokes']:
            for px, py in stroke:
                self.assertLess(py, 0.0)

    def test_center_needle_command_to_right_and_auto_left_alternation(self):
        """
        Verifies Center Needle mechanics:
        - User commands Center-to-Right (0 to 12).
        - Machine automatically alternates to Left by the chosen amount.
        - Left flank disc etch generates alternating Left/Right waveform points and symmetric satin ribbon.
        """
        # User commands Center-to-Right: 0 (center), 6 (mid-right), 12 (max-right)
        steps = [0.0, 12.0, 6.0, 12.0]
        block = calculate_left_flank_pattern_block(steps, needle_position='C', cut_depth=5.0)

        self.assertEqual(block['needle_position'], 'C')
        self.assertEqual(block['stitch_fill_mode'], 'filled')
        self.assertGreater(len(block['waveform_points']), 0)
        self.assertGreater(len(block['centerline_points']), 0)

        # Even stitches penetrate at Left (r < r_midline), Odd stitches penetrate at Right (r > r_midline)
        # For step 1 (odd, val=12.0): penetrates on Right contour
        # For step 0 (even, val=0.0): delta=0, on midline
        r_mid = math.sqrt(block['centerline_points'][0][0]**2 + block['centerline_points'][0][1]**2)
        r_odd = math.sqrt(block['waveform_points'][1][0]**2 + block['waveform_points'][1][1]**2)
        self.assertGreater(r_odd, r_mid)

        # Satin ribbon polygon bridges across Center line from auto-Left to commanded-Right
        self.assertGreater(len(block['satin_ribbon_polygon']), 10)
        self.assertGreater(len(block['satin_hatch_strokes']), 10)

    def test_clean_south_keyway_area(self):
        """Ensures nothing other than keyway cut lines are placed on or above the keyway slot."""
        svg = generate_cam_svg([0, 12] * 9, is_preview=True)
        # Keyway slot is located in South (y in [7, 12]); ensure no text elements exist there
        self.assertNotIn('y="10.2"', svg)
        self.assertNotIn('ROUNDED KEY', svg)
        self.assertNotIn('points="0,12.4', svg)

    def test_preset_number_and_thickness_inputs_in_views(self):
        """Verifies custom preset number and thickness inputs propagate through HTMX endpoints."""
        response = self.client.post(reverse('preview_cam_view'), {
            'preset_number': 'PART #276338',
            'disc_thickness': '4.5',
            'needle_position': 'R',
            'stitch_count': '18',
            'step_0': '12',
            'step_1': '0',
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('preview-top-preset-curves', content)
        self.assertIn('preview-top-needle-symbol', content)
        self.assertIn('preview-top-specs-curves', content)
        # Ensure keyway remains completely clean
        self.assertNotIn('ROUNDED KEY', content)
        self.assertNotIn('y="10.2"', content)
