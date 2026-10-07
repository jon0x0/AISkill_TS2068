# Parallax strips and animation

For exact shift conventions, finite-object padding, masks, orientation sets and
cache/storage tradeoffs, read [precomputed graphics](precomputed-graphics.md).

Represent each plane with its Y range, repeat width, direction, position, phase
step, cadence, palette policy and overlap order. Thin bands can imply many depths
without compositing many full screens. Independent clouds, distant terrain, grass
strips and foreground fence/stone bands were effective in Beast Horizons.

For a 256-pixel repeating strip, position decomposes into `fine = position & 7`
and `coarse = position >> 3`. Eight phases give single-pixel movement; four give
two-pixel movement. Store each fine phase's 32-byte rows, then circularly copy at
the coarse byte offset. Do not advance a one-pixel layer by several pixels to
catch up after a missed deadline. Hold a frame or optimize the work instead.

With coherent row palettes, shift the already quantized bits, not the RGB image.
This freezes the dither texture. Shift mask data identically when a layer has
transparency. Attribute bytes can remain static only when their invariance is
established; arbitrary per-cell attributes require their own correct handling.

To cross 256 pixels in approximately ten seconds, budget around 24-26 one-pixel
updates per second. At nominal 60-Hz display refresh, alternating 2/3-interrupt
deadlines gives 24 updates/s and a 10.67-second crossing. Advance an absolute
deadline; avoid an unconditional HALT after a late update. Measure completion
cadence and the slowest work, including interrupts and contention, separately.

Stagger expensive layer refreshes. The example refreshed rocks each update and
runner/foreground every second update; five clouds used 4/8/16/32/64-update periods.
This is workload allocation, not a requirement to use those rates in every scene.
Keep the user's relative speeds and requested step sizes explicit.

Deduplicate prepared bitmap and attribute rows independently. A 63-byte row
(32 bytes plus the first 31 repeated) allows a single coarse-offset 32-byte copy
without a wrap branch, but costs ROM. Circular copies cost less storage. Use a
mixed strategy where it helps the measured bottleneck. Keep each prepared strip
inside its source bank and store pointer/bank descriptors in always-visible memory.

Preserve palettes/dither when optimizing storage. Keep source RGB layers, encoded
phases and decoded hardware previews distinct. A preview must decode legal ECM
output; an unconstrained RGB scene is not evidence of cartridge appearance.
