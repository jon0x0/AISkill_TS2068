---
name: ts2068-graphics-animation
description: Convert artwork and gradients to TS2068 extended color, build parallax scenery and animated sprites, precompute rotated and shifted graphics, reduce attribute conflicts, and optimize retained game and text rendering using measured Z80 timing.
---

# TS2068 graphics and animation

Use this for 256x192 extended-color artwork and Z80 animation. Preserve the
user's composition, palette priorities and requested motion before optimizing.
Do not replace an existing working renderer merely to match the example map.

- For image conversion, gradient skies, transparency, backgrounds and attribute
  deblocking, read [graphics conversion](references/graphics.md).
- For scroll phases, independent layer rates, memory packing and wraparound,
  read [parallax generation](references/parallax.md).
- For scratch-RAM composition, retained shadows, running poses, layer restoration,
  buffer lifetimes and final screen publication, read
  [scratch compositing and buffering](references/buffering.md).
- For timings, emulator comparisons and the proven Beast Horizons implementation,
  read [validation and experience](references/validation.md).
- For profiling, unchanged-image skips, retained composition, incremental text
  editing and lessons from Berzerk, Sinistar, Beast Horizons and TSWriter,
  read [optimization experience](references/optimization.md).
- For circular strip rotation, finite sprite shifts, orientation sets, masks,
  compiled rows and dynamic phase caches, read
  [precomputed graphics](references/precomputed-graphics.md).

## Essential constraints

ECM has two colors sharing BRIGHT per **8x1** cell, not unrestricted pixel color.
The bitmap at HOME 4000-57FF and attributes at HOME 6000-77FF use the same
nonlinear scanline layout. Select video mode without accidentally changing
DECR's bank/interrupt bits. Account for CPU-visible banks separately from the
SCLD's HOME display fetches.

Quantize moving artwork once and shift the resulting dither when its palettes
permit it. Requantizing each fine-scroll phase can make texture crawl. Independent
cell palettes can create eight-pixel blocks: coherent row palettes trade some
local color accuracy for smooth shading and inexpensive pixel scrolling.

Compose the affected background and masked character in RAM before writing its
protected screen rectangle. Buffering removes erase/draw flicker; a copied buffer
is not a hardware page flip and does not prove absence of raster tearing.

## Portable conversion helper

Requires Python 3.10+ and Pillow. From this skill directory:

```text
python scripts/ecm_art.py gradient --stop 0:5c377d --stop 191:f1a9b8 --out sky
python scripts/ecm_art.py convert scenery.png --palette-mode row --phase-step 1 --out scenery
python scripts/ecm_art.py convert sprite.png --background scene-crop.png --palette-mode cell --out composite
python scripts/test_ecm_art.py
```

The helper exports 6144-byte bitmap/attribute planes, an alpha-derived preserve
mask, decoded previews and metadata. Row palettes support rigid 1/2-pixel phase
sets; cell palettes export a static phase only. This is an offline reference
converter, not a cartridge builder, sprite engine or RetroPixelConverter clone.
Read its `--help` before choosing resize, alpha threshold and background.

The package is self-contained. Cartridge banking and native AY music may also
benefit from the library's separate cartridge/audio skills when installed.
