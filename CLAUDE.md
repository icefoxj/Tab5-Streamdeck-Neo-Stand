# CLAUDE.md

3D-printable desk stand for an M5Stack Tab5 (landscape, top) and an Elgato Stream Deck Neo (bottom). Both sit in flush slots on a 60° face. A parametric Python script generates a one-colour STL and a two-colour 3MF with a livery inlaid in the face. Never hand-edit the STL or the 3MF.

## Commands

```bash
pip install -r requirements.txt     # numpy, manifold3d, matplotlib (Python 3.13 tested)
python generate_stand.py            # -> stl/tab5_neo_stand.stl, 3mf/tab5_neo_stand_2color.3mf
python tools/check_fit.py           # must exit 0 before committing
python tools/render_previews.py     # -> images/*.png (about 30 s)
```

After any geometry change, run all three and commit the STL, the 3MF and the images together with the code.

## Geometry conventions (generate_stand.py)

- Output frame: X = width (left to right seen from the front, 0 = centre), Y = depth (front to back), Z = up. The part prints upright as it sits on the desk.
- Feature frame on the slope:
  - `u` = X.
  - `v` = up the slope (0 = bottom edge of the Neo).
  - `w` = out of the face (0 = front face; slots go into negative `w`).
  - `FACE` maps (u, v, w) to global, and `vw()` maps (v, w) to the side profile (Y, Z).
  - `face_cut()` extrudes a (u, v) shape along `w`, and `slope_prism()` extrudes a (v, w) shape along `u`.
- Body = rounded outer prism − `cavity()` − `cutouts()`.
- The cavity is the inner offset minus a solid frame parallel to the face:
  - `LOWER_DEPTH` deep up to `LOWER_TOP`, around the Neo;
  - `UPPER_DEPTH` deep everywhere, around the Tab5 slot and plug channel;
  - walls around the battery notch.
- The frame's back faces lean 30° off vertical and its steps face up, so the hollow prints without support.

## Design constraints to preserve

- **Flush, closed slots:** the user asked for both devices to sit in slots, flush with the face.
  - The Neo slot is `NEO_T` deep and the Tab5 slot `TAB5_T` deep.
  - The Tab5 slot is closed, with a `SIDE` frame at the top as well as at the sides (user request).
  - There are no finger scoops: the devices come out when the stand is tipped forward (user request).
- **Hidden USB-C plug:** the 90° plug must not be visible from the front. It sits in a channel under at least 5 mm of face, so the Tab5 has to go in tilted.
  - The Tab5 tilts by `TAB5_TILT_IN` about its plug-side front edge (`tab5_motion()`), with the plug hooked under the frame, then it slides by `TAB5_SLIDE`.
  - `CHANNEL_U` and `CHANNEL_W` are computed from that sweep. The slot clearance and `BATTERY_SWING` are what let the body and the battery rotate.
  - `check_fit` walks the path (`devices.tab5_removal_path()`) and verifies that the face covers the plug. If you change the slot, the plug or the battery, re-run it.
- **Speaker (user request):** the front must stay closed. The Tab5 grille is on its bottom edge at x 91.5–110.5.
  - The sound drops through an opening in the slot floor into `speaker_duct()`, a channel in the band between the slots.
  - A 45° ramp in the u–v plane at the channel's closed end, under the grille, turns the sound towards the side away from the plug, and it exits through the side wall.
  - `check_fit` verifies that the path is clear and that the front is closed.
- **Printable upright without support:** keep surfaces within `MAX_OVERHANG` (40°):
  - Holes in sloped floors go through `face_hole()`, a vertical sweep.
  - Upper ends of recesses lean inward by `RUN_PER_RISE`.
  - The only accepted exceptions are the top walls of the two slots (60°, hidden behind the devices). They must stay square to the face for the devices to sit flush, and `check_fit` whitelists exactly those regions.
- **Clean topology:** coplanar or touching faces leave coincident vertices in the STL. Offset parts slightly so they cross instead (see the battery-notch walls in `cavity()` and the uniform slot clearance).
- **Two-colour livery (user request):** a mech-style ornament on the face, as on anime mechs: straight lines, 45° cuts, stripes and inscriptions. It is inlaid `ORNAMENT_DEPTH` (0.6 mm, as requested) into the wall as a separate part, in a 3MF, for the user's Creality printer with a CFS.
  - `ornament()` draws it in (u, v), and `build_parts()` returns the stand minus the recess and the stand ∩ recess, so the two parts fit exactly. The STL stays one colour and unchanged.
  - `write_3mf()` writes core 3MF (2015/02) with no slicer extensions: one named mesh per part (`stand`, `ornament`) grouped in one object. Creality Print loads that as one object with two parts. Filaments are assigned in the slicer.
  - Colours (user request): a black stand with yellow lettering and markings. `COLOURS` stores them in the 3MF as core base materials, as a hint the slicer may ignore. The renders use the same scheme, with the black lifted a little so the shading shows.
  - The lettering comes from `mech_font.py`, a stroked, chamfered font with only the glyphs used so far. Add glyphs to `GLYPHS` as needed.
  - Strokes and gaps must be at least 1.4 mm across the slope (u) and 0.7 mm up it (v). Printed upright, each layer cuts the inlay into a strip about 0.7 mm wide. `check_fit` measures this.
  - Keep at least `ORNAMENT_GAP` from the slot edges and the rounded outer edges. `check_fit` verifies that the inlay is full depth everywhere.
  - Keep the livery in a few horizontal rows. Every layer that contains it costs two filament changes. It is in 148 layers at 0.2 mm now: README quotes this number and the Z ranges, so update them when it changes.

## Device data and where it came from

- **Tab5:** the official drawing and STL come from https://github.com/m5stack/M5_Hardware (`Products/C145_Tab5/Structures/Tab5.stl`).
  - In that STL, the screen is at z = 0 and the back at z = −12.
  - The assembled unit sits at y 0.9–80.9, and an exploded view is at negative y.
  - Seen from the front, x runs left to right, so the USB-C is on the left edge (x = 0) and the battery and speaker are on the right half.
  - `tools/devices.py` downloads the file to `.cache/`, which is gitignored. Do not commit it.
- **Tab5 Kit:** 26.7 mm thick with the battery, so the battery protrudes 14.7 mm.
- **Stream Deck Neo outline (`NEO_OUTLINE_RIGHT`):** traced from the front-view render of Elgato's official "Stream Deck Neo STP" device model on Elgato Marketplace. The STP itself needs a login.
  - The render's silhouette is 956 × 697 px, which matches 107 × 78 mm exactly. It was symmetrised and lightly smoothed.
- **Neo depth:** 26 mm from the official spec, with the integrated stand folded flat. Side photos show a body of about 20 mm. Its captive cable leaves the middle of the back. None of this has been measured on a physical unit.

## Docs

`README.md` is in English, for a public audience. Keep its parameter table, its "Dimensions used" table and the livery's layer count and Z ranges in sync with the code.
