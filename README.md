# Singer Type A Cam Generator

A lightweight, serverless-optimized CAD/CAM web application built with **Django 6**, **HTMX**, and **Tailwind CSS**. It enables makers, sewists, and machinists to visually design custom and historic pattern cams for vintage sewing machines (such as the **Singer 306, 319, 401, and 500 series**) and export production-ready `.svg` and `.dxf` vector files calibrated for laser cutting and face etching **3mm cast acrylic**.

---

## What's New

### 1. Mechanical Cam Profiles (Gear-Like Dwell Teeth & Right-Angle Sawteeth)
- **Authentic Vintage Singer Geometry:** Real sewing machine cams feature circular dwell flats (plateaus where the follower rests while the needle penetrates the fabric), followed by steep mechanical transitions.
- **Profile Modes:**
  - **Mechanical Gear / Dwell (Default):** Squared-off gear-like teeth with concentric circular dwell arcs and steep, clean transitions—enabling true **right-angle sawteeth** without artificial rounding.
  - **Harmonic Spline:** Continuous sinusoidal Catmull-Rom waves for gentle scallops.
  - **Linear Ramp:** Chiseled straight-line facets.
- **Adjustable Dwell Ratio (Flatness Slider):** Tune dwell plateau width from `0%` (continuous transition) to `55%` (vintage Singer standard) up to `80%` (square teeth).

### 2. Dynamic Stitch Count (6 to 36 Points)
- Fully customizable number of stitches per $360^\circ$ rotation:
  - Quick count presets: `12`, `16`, `18` (standard Type A), `24`, and `36`.
  - Dedicated `[−]` and `[+]` steppers to add or remove stitches dynamically.
  - Angular sector automatically scales ($\Delta \theta = 360^\circ / N$).

### 3. Responsive Side-by-Side Workbench
- Optimized layout with `md:grid-cols-12` breakpoint ensuring the live $42\text{ mm}$ vector preview is always sticky and visible side-by-side with the interactive wave canvas on all laptop and desktop viewports.

### 4. Directly Interactive & Editable Stitch Waveform Studio
- Directly click and drag needle nodes up/down between **Right ($12$)**, **Center ($6$)**, and **Left ($0$)**.
- Click and drag across the canvas to literally **draw your stitch wave in one continuous stroke**.
- Micro `R`, `C`, `L` snap buttons under each column for 1-click bight positioning.

### 5. Flanking Dual-Block Face Etching & Anti-Crack Keyway
- **Flanking Toolmark Blocks:** Separated across the diameter on opposite flanks:
  - **Left Flank (West / 180°):** Miniature stitch waveform & pattern name cartouche with zero text collision.
  - **Right Flank (East / 0°):** Personalized Maker's Mark (e.g. `KENWAY`), diamond emblem, and machine specs.
- **Anti-Crack Keyway:** Full semi-circular radiused fillet ($R = 1.5\text{ mm}$) at the tip of the $5\text{ mm}$ keyway slot to eliminate sharp notch stress concentration.
- **Zero-Font Vector Curve Text Export:** All letters, titles, and maker's marks are exported as **pure vector polylines/curves** rather than font elements. Bends naturally along concentric arcs of the 14mm bore with 100% compatibility across LightBurn, RDWorks, LaserGRBL, and AutoCAD without requiring installed fonts or text exploding.

### 6. Subtractive Rotary Milling Cutter Engine
- Simulates a rotating circular endmill or grinding cutter bit of adjustable radius plunging radially into the 42mm circular blank to machine authentic gear-tooth pockets and dwell valleys.
- Features continuous sweep along valley floors for seamless OEM alternating square blocks and circular scallop transitions.

---

## Physical Dimensions (Calibrated Measurements)

| Physical Dimension | Value | Description |
| :--- | :--- | :--- |
| `OUTER_MAX_RADIUS` | 21.0 mm | Blank outer disc boundary (42.0 mm outer diameter) |
| `BASE_TRACK_RADIUS` | 16.0 mm | Minimum track boundary (32.0 mm diameter, Step 0 Far-Left) |
| `MAX_TRACK_RADIUS` | 21.0 mm | Maximum track deflection (42.0 mm diameter, Step 12 Far-Right) |
| `TOTAL_TRACK_WIDTH` | 5.0 mm | Full needle bight deflection window (21.0 mm - 16.0 mm) |
| `INNER_BORE_RADIUS` | 7.0 mm | Center drive spindle key bore (14.0 mm diameter) |
| `KEYWAY_DEPTH` | 5.0 mm | Key hole slot length extending radially from bore |
| `KEYWAY_WIDTH` | 3.0 mm | Alignment drive-pin keyway slot width |
| `KEYWAY_ROUND_RADIUS` | 1.5 mm | Anti-crack semi-circular stress relief fillet |
| `STITCH_RANGE` | 6 – 36 Stitches | Dynamically adjustable stitch count (Default: 18) |
| `DWELL_RATIO` | 0.0 – 0.80 | Gear-like dwell plateau fraction (Default: 0.55) |
| `DEFAULT_KERF_OFFSET` | 0.15 mm | Standard laser kerf for 3mm cast acrylic |

---

## Laser Cutting & Etching Guidelines (3mm Acrylic)

1. **Cutting & Etching Sequence:**
   - **Step 1:** Cut the **14mm inner bore and radiused 5mm keyway slot** first (Layer: `CUT_INNER` / Blue `#0000FF`).
   - **Step 2:** Lightly score/etch the **Flanking Left Pattern Block and Right Maker's Mark** onto the face (Layer: `ETCH_DESIGN` / Green `#00AA00`).
   - **Step 3:** Cut the **42mm outer cam perimeter** last (Layer: `CUT_OUTER` / Red `#FF0000`).
2. **Material:** Use **cast acrylic** (PMMA) for crisp etched lines and clean cut edges.
3. **Kerf Tuning:** Default kerf is set to `0.15 mm`. If the cam fits too tightly onto your machine's 14mm spindle, increase the kerf offset slider slightly (e.g. `0.18 mm`).

---

## License & Credits

This project is open-source software licensed under the **[MIT License](LICENSE)**.

- **Developer:** [Abdul Wahab](https://github.com/capkenway)
- **Portfolio:** [capkenway.github.io](https://capkenway.github.io)
