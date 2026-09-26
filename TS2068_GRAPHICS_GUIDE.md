# TS2068 graphics and animation experience map

Start with the [graphics-and-animation skill](skills/ts2068-graphics-animation/SKILL.md).
It covers ECM image conversion, gradient skies and alpha backgrounds, coherent
Sierra Lite shading, parallax generation, character poses and buffered redraws.

- [Conversion and deblocking](skills/ts2068-graphics-animation/references/graphics.md)
  distinguishes native resolution, eight-pixel palette blocks, dither crawl and
  transparency fringes. It explains the remaining 8x1 color constraint.
- [Parallax](skills/ts2068-graphics-animation/references/parallax.md) covers prepared
  phases, independent rates, circular strips, ROM costs and measured cadence.
- [Buffering](skills/ts2068-graphics-animation/references/buffering.md) covers masked
  compositing, attribute restoration, small protected rectangles and interrupt safety.
- [Validation](skills/ts2068-graphics-animation/references/validation.md) records
  the Beast Horizons results and distinguishes emulator evidence from hardware tests.

The portable Python/Pillow helper generates gradients and converts user-supplied
images to legal bitmap/attribute planes, masks and decoded phase previews. It does
not require the original demo's artwork. Native chiptune integration is documented
in the [audio skill](skills/ts2068-audio-development/references/native-ay.md).
