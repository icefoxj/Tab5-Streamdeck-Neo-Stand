# Tab5 + Stream Deck Neo Stand

A 3D-printable desk stand that holds an **M5Stack Tab5** (landscape) and an **Elgato Stream Deck Neo** in flush slots on a single 60° console.

![Stand with the Tab5 and the Stream Deck Neo](images/stand_with_devices.png)

**Ready-to-print STL:** [`stl/tab5_neo_stand.stl`](stl/tab5_neo_stand.stl)

## Features

- **Flush slots.** Both devices sit in slots whose depth matches their thickness, so their front faces are level with the stand and nothing covers the screen, keys or bezels. The stand's face is tilted 60° from the desk, with the Neo at the bottom and the Tab5 on top.
- **Neo slot cut to the real shape.** The outline was traced from Elgato's official Stream Deck Neo device model. It is a 107 × 78 mm rounded "squircle" with slightly bowed top and bottom edges, not a plain rectangle. Finger scoops on both sides let you lift the Neo out.
- **Tab5 slot with R4 corners**, matching the Tab5's rounded corners. The slot is open at the top, and the Tab5 slides in from above.
- **Hidden USB-C plug.** The 90° plug on the Tab5's left edge rides down a channel under the face as the Tab5 slides in. Nothing of the plug or its cable shows from the front.
- **NP-F550 battery (Tab5 Kit):** a notch behind the slot takes the battery, which protrudes 14.7 mm from the back. The Tab5 also fits without the battery.
- **Speaker port.** The Tab5's speaker is on its bottom edge, at the right. A port right below it vents the sound forward through the face.
- **Hidden cables.** The body is hollow. The Neo's captive cable goes through a hole in the floor of its slot, and the Tab5's cable drops through a slot at the top. Both leave through an opening at the back, at desk level.
- Recesses for four 10 mm stick-on rubber feet.

| Front | Back | Side | Top |
|---|---|---|---|
| ![Front](images/stand_front.png) | ![Back](images/stand_back.png) | ![Side](images/stand_side.png) | ![Top](images/stand_top.png) |

## Printing

| | |
|---|---|
| Orientation | As in the STL: upright, base on the bed |
| Supports | None needed (see the note below) |
| Material | PLA or PETG |
| Layer height | 0.2 mm (0.15 mm gives a cleaner Neo slot ceiling) |
| Walls / infill | 3+ perimeters, 15% infill |
| Size | 168 × 135 × 164 mm |
| Volume | 568 cm³ as a solid. The frame around the slots is solid in the model, so most of it prints as infill. |

**About overhangs.** Every surface is printable without support except one. To keep the Neo flush, the top wall of its slot must stay square to the face, which makes it a 60° overhang (about 25 cm²). It sits hidden behind the Neo, and most printers handle 60° fine with good part cooling. If yours struggles, paint a support enforcer on that wall in your slicer. All other overhangs stay within 40° of vertical, and the longest bridge is 20 mm, on the inside ceiling.

## Assembly

1. Stick the four rubber feet into the recesses under the base.
2. **Neo:** fold its integrated stand flat against its back. Push the cable's plug end through the hole in the floor of the Neo slot. It drops through the hollow body and comes out of the rear opening. Press the Neo into its slot. To take it out, use the finger scoops at its sides.
3. **Tab5:** drop the free end of the 90° USB-C cable (the computer or charger end) into the narrow slot at the top left of the stand. It falls through the body and comes out of the rear opening. Plug the 90° end into the Tab5's USB-C port (left edge), with the cable pointing back. Then slide the Tab5 down into its slot from the top, with the battery entering its notch, while the plug rides down the hidden channel. To remove the Tab5, slide it up; you can push it from below through the speaker port.

### Which 90° USB-C cable to use

Use a right-angle plug whose cable leaves towards the **back** of the device, perpendicular to the screen. The channel fits a plug head that sticks out up to 13 mm from the port, is up to 13 mm wide and up to 7 mm thick. You can change these limits with `PLUG`.

## Dimensions used

| Item | Value | Source |
|---|---|---|
| Tab5 | 128 × 80 × 12 mm, R4 corners | [M5Stack official drawing](https://docs.m5stack.com/en/core/Tab5) |
| Tab5 Kit (with battery) | 26.7 mm thick, so the battery protrudes 14.7 mm | [M5Stack docs](https://docs.m5stack.com/en/core/Tab5) |
| NP-F550 on the back | 38.2 × 70.4 mm at x 81.2–119.4, y 9.5–79.9 mm (seen from the front, origin at the bottom-left corner) | [M5Stack official STL](https://github.com/m5stack/M5_Hardware/tree/master/Products/C145_Tab5/Structures) |
| Tab5 speaker | Bottom edge, x 91.5–110.5 mm | M5Stack official STL |
| Tab5 USB-C | Left edge, centred at y = 40 mm, 2.5 mm from the back face | M5Stack official STL |
| Stream Deck Neo outline | 107 × 78 mm, traced from the official device model render | [Elgato "Stream Deck Neo STP"](https://marketplace.elgato.com/product/stream-deck-neo-stp-399e9aac-8994-4b6c-8709-cfaa4409308a) |
| Stream Deck Neo depth | 26 mm with the stand folded (body about 20 mm, plus the folded stand) | [Elgato specs](https://www.elgato.com/us/en/p/stream-deck-neo-black) |

> **Before printing:** the Neo's outline and depth come from Elgato's official model and specs. They were not measured on a physical unit. If your Neo, with its stand folded, is not 26 mm deep, set `NEO_T` in `generate_stand.py` and regenerate. If it doesn't sit flush, the depth is the number to adjust. If you have Elgato's STP file, you can also check `NEO_OUTLINE_RIGHT` against it.

## Customising and regenerating the STL

The STL is generated by a parametric Python script built on [manifold3d](https://github.com/elalish/manifold). It was tested with Python 3.13.

```bash
pip install -r requirements.txt
python generate_stand.py          # writes stl/tab5_neo_stand.stl
python tools/check_fit.py         # checks fit, printability and mesh
python tools/render_previews.py   # refreshes the images in images/
```

Main parameters, at the top of `generate_stand.py`:

| Parameter | Default | What it does |
|---|---|---|
| `TILT` | 60 | Face angle from the desk, in degrees |
| `NEO_T` | 26 | Neo depth with its stand folded (sets the Neo slot depth) |
| `NEO_OUTLINE_RIGHT` | traced | Right half of the Neo's front outline |
| `CLEAR` | 0.5 | Gap around each device in its slot |
| `SIDE` | 20 | Frame width on each side of the Tab5 (the left one hides the plug) |
| `BOTTOM`, `NEO_Z` | 6.5, 18 | Frame below the Neo, and its height above the desk |
| `SPEAKER_PORT` | 7 | Height of the speaker port below the Tab5 |
| `PLUG`, `PLUG_CLEAR` | 13 × 13 × 7, 0.8 | 90° USB-C plug size and clearance in the hidden channel |
| `NEO_GRIP` | 13, 12 | Finger scoops: half length and depth |
| `WALL`, `FLOOR` | 2.4, 3 | Shell wall and base thickness |
| `TAB5_MIRROR` | `False` | Mirrors the Tab5 features, if your USB-C is on the other side |

### What `tools/check_fit.py` verifies

- The solid is manifold, and the STL has no coincident vertices or zero-area triangles.
- Nothing intersects the Tab5, the battery, the 90° plug and its cable, the Neo, or the Neo's cable.
- The air path from the speaker grille out through the face is clear.
- There is no material in front of either device's outline, so both are fully visible and flush.
- The face material fully covers the USB-C plug, so it is hidden from the front.
- There are no overhangs beyond 45° except the known Neo slot ceiling, and bridges stay under 25 mm.

For the preview renders, the scripts download M5Stack's official Tab5 model into `.cache/` (from the M5_Hardware repository). It is not part of this repository.

## Repository layout

```
generate_stand.py        parametric model -> stl/tab5_neo_stand.stl
stl/                     ready-to-print STL
tools/devices.py         Tab5, battery, plug and Neo envelopes
tools/check_fit.py       fit, printability and mesh checks
tools/render_previews.py README images
images/                  rendered previews
```
