# TS2068 graphics and animation experience map

Start with the [graphics-and-animation skill](skills/ts2068-graphics-animation/SKILL.md).
It covers ECM image conversion, gradient skies and alpha backgrounds, coherent
Sierra Lite shading, parallax generation, character poses and buffered redraws.

- [Conversion and deblocking](skills/ts2068-graphics-animation/references/graphics.md)
  distinguishes native resolution, eight-pixel palette blocks, dither crawl and
  transparency fringes. It explains the remaining 8x1 color constraint.
- [Parallax](skills/ts2068-graphics-animation/references/parallax.md) covers prepared
  phases, independent rates, circular strips, ROM costs and measured cadence.
- [Scratch-RAM compositing](skills/ts2068-graphics-animation/references/buffering.md)
  covers masked layers, old/new damage restoration, retained shadows, small protected
  rectangles, scratch lifetimes, bank visibility and final-only screen publication.
- [Validation](skills/ts2068-graphics-animation/references/validation.md) records
  the Beast Horizons results and distinguishes emulator evidence from hardware tests.
- [Optimization experience](skills/ts2068-graphics-animation/references/optimization.md)
  captures Berzerk's draw skips and audio deadlines, Sinistar's retained composition
  and cache tradeoffs, Beast Horizons' prepared copy paths, and TSWriter's incremental
  layout, typing and scrolling. Measurements retain their revision and workload limits.
- [Precomputed graphics](skills/ts2068-graphics-animation/references/precomputed-graphics.md)
  explains circular rotation versus finite shifts, orientation sets, spill bytes,
  synchronized masks, palette constraints, storage budgets and atomic cache swaps.

The portable Python/Pillow helper generates gradients and converts user-supplied
images to legal bitmap/attribute planes, masks and decoded phase previews. It does
not require the original demo's artwork. Native chiptune integration is documented
in the [audio skill](skills/ts2068-audio-development/references/native-ay.md).
