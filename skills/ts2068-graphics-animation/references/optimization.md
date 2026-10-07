# Measured optimization experience

Use these lessons for games, scrolling demos and retained text interfaces. The
figures below are historical project measurements, not new benchmarks or promises
for another program. Sources were reviewed on 2026-10-07. No physical-hardware
performance claim follows from these emulator results.

## Measure the work that determines latency

Separate physics/layout, source preparation, composition, dirty comparison,
publication, interrupts and waiting. Count completed pictures or editor actions,
not just draw entries or serviced interrupts. Record artifact hashes, emulator
revision/model, clock, warmup, inputs and enabled features. Report worst calls
and deadline misses alongside average throughput. Use the emulator's measured
refresh duration; the existing [validation notes](validation.md) document differing
Fuse and TSRun frame sizes. Do not infer physical timing from host wall time.

Compare identical controlled scenes to isolate an optimization, then exercise
natural motion, clipping, overlap, speech and interaction. Faster simulation can
visit different positions during a natural trace and change its rendering cost.
At 3,528,000 T-states/s, 20 pictures/s allows 176,400 T per completed picture on
average; this does not establish safe raster publication or audio deadlines.

Prefer avoiding work before shortening its inner loop: reject invisible objects,
recognize unchanged content, reuse projection/layout, narrow actual damage, then
consider tables, precomputed phases, compiled rows and unrolling. Include the cost
of generating lists, selecting fast paths, banking and restoring registers. A
small publication phase cannot explain a large whole-frame speedup by itself.

## Berzerk: skip visual work without skipping game behavior

An identical old/new sprite image, destination and shift can bypass a combined
erase/draw while collision and WRITE_PATTERN bookkeeping still run. Register-based
two/three-byte row shifts and a specialized one-byte path reduce remaining work.
The early stationary-player phase fell from about 27,467 to 8,305 T, but that
historical speech build still missed deadlines: a faster blitter was not a
complete scheduling fix.

The 2026-09-19 own-bolt masking fix skipped trail work when erase/write flags were
clear, tested only pixels within a conservative player footprint, and cached
address/mask triples for restoration instead of recalculating them. With two
eight-pixel trails, no-redraw cost fell from 22,740 to 288 T and redraw cost from
45,896 to 27,766 T. Movement cadence constants stayed unchanged.

Correct audio sample counts and mean word duration did not prove uniform output:
the earlier low-demand speech experiment spent about a third of within-word time
in gaps over 1 ms. Four-frame work slicing improved typical spacing but retained
a roughly 16 ms worst gap and reduced player/robot service rates. Preserve these
as incomplete experiments, not recommended production schedules. Measure every
within-word interval and bound expensive work; never filter out stalls or alter
source duration to disguise them. Audio checkpoints must preserve registers and
avoid reentrant drawing.

## Sinistar: retained composition and its limits

Store an object's complete rendered identity: artwork/stage, pose, fine phase,
position, clipped dimensions, visibility and relevant palette state. Retain an
unchanged image in shadow memory, but repair rows touched by other actors/stars in
the original layer order. Erase the last old rectangle on disappearance. Invalidate
on movement, clipping changes, return or cache replacement. Comparing only x/y/width
missed a clipped height shrink and left three stale rows; compare all dimensions.

Compiled planetoid rows embed masks, pixels and colors, skip transparent cells and
share repeated instruction tails. The v4 implementation used 209 shared programs
and phase tables in 7,341 bytes, with a general clipped fallback. Controlled one-rock
no-Sinistar throughput rose from 14.446 to 19.261 fps. This is a case for compiling
frequently reused shapes, not evidence that every sprite should become code.

The v6 retained-rock change raised the controlled three-rock chase from 7.93 to
11.49 fps, while continuous scrolling changed only from 8.09 to 8.15 fps. Camera
motion invalidates much of the retained image. That three-rock profile spent about
43.4% in composition, 24.6% in comparison and only 2.3% in publication. Splitting
dirty rows into left/right spans and separately tracking an empty central gap
were rejected because bookkeeping cost more than the comparisons saved. Revisit
such designs only with a workload and measurements that justify them.

Opaque old/new rectangle overlap can retain the common area and restore at most
four exposed strips. Partial assembly instead needs a silhouette mask: a bounding
box alone incorrectly hides objects through unassembled gaps. Cull drawing of a
fully covered object only when coverage and layer policy prove it safe; preserve
physics/collision. Optional fast modes that retire world populations are behavior
changes and must be reported separately from equivalent-output optimizations.

Precomputed assembly phases and mask-pattern lookup remove repeated shifts; see
[precomputed graphics](precomputed-graphics.md). The v20 changing-phase overlap
fixture improved 8.62 to 9.81 fps, while fixed scenes were slightly slower. V21
natural fast assembly/pursuit measured 7.84/13.49 fps after gameplay changes;
neither establishes the 20 fps target. Keep revision and fixture labels with numbers.

## Shadow of the Beast demo: prepare data for the actual copy path

Beast Horizons uses quantized rigid phases, row-coherent palettes, independently
deduplicated bitmap/attribute rows, and a mixture of circular rows and 63-byte
lookahead rows. Skip attribute copies only where invariance is proven. Stagger
layer work while keeping requested motion step sizes and relative speeds.

Buffer only the protected character columns and publish their final composite;
other scenery can use its appropriate direct path. Rev14's mixed copier sent
13 columns to display, four to the character buffer and 15 to display. Full updates
published 320 final protected bytes; rock-only updates published 128. These sizes
come from that scene, not a universal buffer layout. Patched copy kernels lived
in writable HOME RAM; ROM source strips stayed within their 8K banks. Interrupts
used a separate stack and restored mapping. Copy buffering is not a page flip.

Alternating two/three-refresh absolute deadlines gave roughly 24 updates/s and
one-pixel hill movement. Do not add an unconditional HALT after a late update or
hide missed deadlines with larger motion jumps. Rev09's measured bound and
10.67-second transit are recorded in [validation](validation.md).

## TSWriter: retain layout as well as pixels

Resume parsing at a safe unchanged visible line with its incoming font/style,
and stop after both the visible region and caret have been measured. Invalidate
on earlier edits, width/view changes or unsafe image continuations. Text-only
eight-line checkpoints let backward navigation resume near its target; they are
not a full font cache. Hoist a glyph's source-width mask outside its row loop and
shift packed rows in registers. The latter reduced Prologue glyph-building cost
by about 26%, with initial-display gains of 7.3-9.3% across tested modes/widths.

Use narrowly guarded edit paths. Ordinary left-aligned ASCII append at document
end can draw one glyph and its affected columns; wrapping, alignment, selection,
middle edits, style changes and panning use the general path. At 90 characters,
refresh fell from 1,152,826 to 54,284 T, glyph draws from 91 to one, and display
writes including caret from 1,052 to 124. These are refresh costs, excluding
keyboard polling/frame scheduling, not end-to-end input latency.

Compare selection spans per retained line; repaint only changed highlights.
Reuse retained pixels for scrolling with overlap-safe copies and explicit nonlinear
scanline addresses for each plane. Draw the incoming line rather than the entire
viewport. EOF backspace can repair a line tail only when retained geometry remains
valid. Keep a full repaint oracle for both ECM and high resolution.

Responsiveness also requires input service during rendering. TSWriter used a bounded
16-byte press/release queue and an ISR that samples without drawing; low-priority
free-space text waits for idle input and redraws only changed digits. Keep queue,
ISR and stack visible during font banking. An interrupt during LD A,I can invalidate
a naive P/V-based interrupt-state guard on NMOS Z80; retain the project's tested
race handling rather than copying the shortcut into bank gateways.

## Acceptance and provenance

Compare complete bitmap and attribute output with an independent compositor or a
fresh uncached repaint. Also inspect writes: final equality can hide an erase flash,
redundant writes or late raster publication. Exercise phase/wrap/clip boundaries,
overlap entry/exit, stage changes during preparation, restart, font/style/selection
changes and long navigation. Check ROM immutability, bank restoration and stack
bounds with interrupts/audio active. Preserve semantic timing and document bytes.

These local project-relative sources provide deeper context if their checkouts
are available; this skill does not require them or bundle their assets:

| Project | Source notes and reproducer names |
|---|---|
| cartridgeconversion/berserk | PORT_STATUS.md; PROJECT_STATE.md; docs/performance-2026-08-30.md; docs/performance-sliced-2026-08-30.md; scripts/measure_owned_draw.py; scripts/test_sprite_blitters.py |
| cartridgeconversion/sinistar | port/SCROLLING.md; port/ONE_ROCK_PROFILE.md; port/FAST_MODE_PROFILE.md; port/ASSEMBLY_CACHE.md; port/scripts/verify_scrolling.mjs |
| ParallaxDemo / Beast Horizons | MEMORY.md (rev14); preserved rev07-09 evidence summarized in validation.md |
| TSWriter2068 | docs/RESPONSIVENESS.md; docs/RENDER_SPEED_VALIDATION.md; tests/append_speed.mjs; tests/backspace_speed.mjs; tests/render_speed.mjs |
