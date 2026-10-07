# Pre-rotating, pre-shifting and preparing scrolling data

Move repeatable work into the asset build or an amortized preparation stage when
the ROM/RAM cost and bank access are cheaper than doing it in the draw loop.
Precomputation includes masks, address tables, clipping metadata and row programs,
not just visible pixels. Profile preparation and publication as well as drawing.

## Distinguish three transformations

- **Circular strip rotation:** periodic scenery wraps pixels from one end to the
  other. For strip width W divisible by eight, normalize signed position modulo W,
  then use fine = position & 7 and coarse = position >> 3. Eight fine phases plus
  coarse byte selection support every pixel offset. Declare whether positive
  position moves the artwork or the camera; their directions are opposite.
- **Finite sprite shifting:** bits leaving a row enter a spill byte or are clipped;
  they must not wrap into its opposite edge. Prepare pixel and mask data together
  for phases 0-7. Byte-aligned width w needs w/8+1 bytes for nonzero phases, while
  phase zero needs w/8 unless a fixed padded stride is chosen. General width uses
  ceil((w+phase)/8); initialize padding as transparent, not opaque black.
- **Geometric rotation:** headings/angles are different artwork, not circular bit
  shifts. Generate each required orientation around a declared pivot and bounding
  box, then quantize and prepare its fine phases. Keep collision geometry distinct
  from padded rendering bounds. The cited projects demonstrate scroll phases;
  arbitrary-angle rotation is an extension of the method, not a measured result.

For MSB-first pixels shifted right by s (1-7), a row byte j can be formed as
`(src[j] >> s) | ((src[j-1] << (8-s)) & 255)`. Circular strips wrap j-1;
finite sprites supply transparent outside pixels. Handle s=0 separately. Shift
coverage identically. With a preserve mask (1 means keep background), outside
bits must be 1, and composition is `(background & mask) | (pixels & ~mask)`.
Do not rotate a finite sprite's mask or zero-fill its preserve-mask margins.

## Plan storage and runtime selection together

For H rows, P phases, B stored bytes per row and K equally sized planes, the raw
cost is H*P*B*K bytes per pose/orientation. Add descriptors, alignment, spill bytes,
code, palette data and bank padding explicitly. For example, a fixed three-byte
stride for a 16x16 sprite at eight phases costs 768 bytes for pixels plus mask,
before attributes; multiplying by every pose and direction can exhaust a cartridge.

Use only reachable phases when motion allows it (four phases for a two-pixel step
with fixed parity). Camera offsets may require all eight even if object motion
does not. Store a smaller frequent set with a correct runtime fallback when that
is cheaper. Deduplicate equal rows, masks and compiled tails independently; a
shared bitmap does not imply shared attributes. Do not lose source-to-pose indices.

A periodic 32-byte row plus its first 31 bytes yields a 63-byte row: any coarse
offset 0-31 can then copy 32 contiguous bytes. Alternatively split a circular
copy at the seam. Lookahead trades ROM for fewer branches; mix strategies by
measured hotness. Keep accessed spans inside a mapped source bank, or explicitly
split the operation. Cache descriptors and gateway code where they remain visible.

Precompute nonlinear screen-row addresses, row bounds, transparent/opaque runs,
phase pointers and clipping extents when reused. A compiled row can embed constant
masks/pixels/colors and omit transparent cells. Share repeated tails when a jump
costs less than the saved ROM is worth. Keep a general clipped/overlap fallback.
Runtime-patched kernels require writable RAM, a documented register/stack contract
and interrupt safety; do not assume cartridge ROM is self-modifiable.

## Preserve attributes and texture

Quantize once and shift the resulting bitmap when its palette policy permits;
independently requantizing each scroll phase can make dither crawl. Shift alpha or
masks with the pixels. In ECM, fine shifts move source pixels across destination
8x1 palette boundaries: rotating bitmap bits and byte-rotating arbitrary attributes
is not a valid general solution. Use row-coherent palettes, compatible cell pairs,
or explicitly converted phase palettes with documented tradeoffs. A mask alone
does not solve mixed-cell color conflicts. Precompute attributes against scenery
only when that background palette is known to stay valid.

For vertical movement, row selection can replace bit shifting, but destination
addresses still follow the nonlinear display layout. A linear memmove over screen
memory does not implement general vertical scrolling. Move both ECM planes and
choose overlap-safe copy direction. A repeated strip may wrap vertically; a finite
object must clip. State whether generated assets are linear rows or screen layout.

## Dynamic caches: Sinistar assembly example

When stage-dependent artwork cannot all fit in ROM, build a back cache over bounded
calls while retaining the complete front cache. Key validity by stage, pose/phase,
palette and source generation as appropriate; invalidate a selected-phase lookup
when any shared scratch use overwrites it. Swap the front/back identity atomically
only after pixels, masks and metadata are complete. Restart an obsolete back build
without corrupting the displayed front. Report preparation latency explicitly.

Sinistar v20 used two 4K HOME caches. Each held eight 357-byte bitmap phases,
52 overlap flags, 364 mask-pattern indices, up to 100 eight-byte mask patterns and
a count byte, with alignment gaps. A 100-byte selected-phase lookup avoided shifting
364 mask cells at draw time. Actual stages used at most 99 shared patterns.
Colors were stored separately. This layout is an example, not a reusable fixed map.

The back cache took 52 row calls at two calls per picture: 26 picture updates before
an atomic swap. Worst measured builder call rose from 9,275 to 52,298 T. Being below
one 58,688-T refresh did not make this cost free or guarantee the complete frame
deadline. Changing-phase overlap improved about 14% (409,230 to 359,473 T/picture),
while fixed cases slightly regressed. Use this tradeoff when repeated draws amortize
preparation; an uncached fallback may be better for short-lived states.

## Verify the generated representation

Decode every orientation/pose and fine phase against a simple reference transform.
Exercise coarse wrap, negative coordinates, spill bytes, transparent edges, all
clipped dimensions and patterned backgrounds. Check palettes independently from
pixel/mask geometry. For dynamic caches, test stage changes mid-build, scratch
reuse, repeated phase changes and atomic swaps. Verify old-image restoration and
new-image composition together. Use actual emulated bank/stack/write traces before
accepting a fast path; matching offline pictures alone cannot prove it executable
within the target memory map or deadlines.

See [optimization experience](optimization.md) for project measurements and
[parallax generation](parallax.md) for scheduling and layer-specific guidance.
