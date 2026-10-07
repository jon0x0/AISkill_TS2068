# Scratch-RAM compositing and background restoration

Scratch RAM can hold a small row/rectangle, a retained playfield shadow, or a
prepared object cache. These have different lifetimes: transient composition can
be reused after publication, a retained shadow survives into the next picture,
and a phase cache survives until its source changes. Assign ownership and lifetime
explicitly rather than treating every apparently free range as interchangeable.

## Compose a complete result before publishing

1. Determine damage from both old and new clipped objects, including fine-phase
   spill cells, disappearing objects and changes of pose, mask or palette.
2. Restore the affected background in scratch, or retain proven unchanged regions.
   Reconstruct from scenery/world data when a saved background has become stale
   through scrolling or another actor's motion.
3. Draw all layers intersecting the damaged region in their original order, even
   when a layer's own position has not changed. A retained rock still needs repair
   where another object crossed it. Avoid restoring one sprite's saved-under image
   over a newer overlapping sprite.
4. Compose bitmap and ECM attributes under an explicit mask/palette policy. Fully
   transparent cells preserve both planes; partial coverage still shares one 8x1
   color pair. Resolve that conflict deliberately rather than assuming a bit mask
   also masks colors.
5. After composition is complete, compare with the published image if changed-only
   output is worthwhile, and publish final bytes in a bounded, raster-aware pass.
   A complete scratch image prevents visible intermediate erase/draw states but
   does not by itself prevent tearing while the final image is copied.

Keep dirty bounds until publication succeeds. If an update list exceeds its
capacity or raster budget, retain the complete pending state and use a defined
retry/fallback; do not discard dirty spans or publish an arbitrary prefix as though
the picture were complete. Measure compare/list-building costs: in Sinistar they
could be much larger than final screen writes.

## Choose the buffer and memory contract

Use a row or byte-aligned protected rectangle when its dependencies are local;
use a retained shadow where overlapping moving objects require wider recomposition.
A full 256x192 ECM shadow costs 12,288 bytes for bitmap plus attributes before
masks or metadata. Partial buffers can use linear rows with explicit screen-address
tables; do not confuse their stride with the display's nonlinear layout. Stage a
whole overlapping source row when required, or choose a safe traversal direction
for in-place scrolling. Handle each display plane explicitly.

For every composition phase, list the CPU-visible source, scratch destination,
code, stack and interrupt state. HOME RAM underneath a mapped DOCK chunk is not
CPU-accessible merely because the SCLD still displays HOME. Sinistar's banked
incremental helper therefore used HOME 7BA0 scratch instead of HOME 58xx hidden
by DOCK2; this is an example of visibility, not an address prescription.

Keep row staging, phase caches, dirty snapshots, update records, temporary stacks
and ISR/audio workspace disjoint while live. Reuse memory only after its consumer
finishes, and invalidate retained lookup state when another staging operation
overwrites it. Sinistar's selected-phase mask lookup required precisely this
invalidation. Effects reused publication scratch only after normal publication.
Assert allocation bounds in the build and check bank/stack restoration at runtime.

## Experience across projects

- Beast Horizons composes scenery plus the runner only in protected columns,
  avoiding a full-width duplicate background copy. The detailed rev09 example
  below preserves its original dimensions; rev14 moved the protected columns.
- Sinistar retains bitmap/attribute shadows, repairs old/new damage in layer order,
  uses masks for incomplete assembly, and emits changed final bytes. It also uses
  separate front/back object caches: those are prepared sources, not hardware
  screen pages or substitutes for scene composition.
- TSWriter retains line layout and pixels, builds glyph/line output with HOME
  buffers visible under the selected font/render bank, and copies retained lines
  for scrolling. New glyphs or changed line tails can use guarded local paths;
  general layout changes fall back to recomposition.
- Berzerk's XOR renderer demonstrates a related but different optimization:
  skip identical image work and cache address/mask data while preserving collision
  bookkeeping. Do not describe that path as a full scratch-shadow compositor or
  replace it merely to impose this architecture.

See [measured optimization](optimization.md) for evidence and source notes, and
[precomputed graphics](precomputed-graphics.md) for phase-cache preparation.

## Protected runner example (Beast Horizons rev09)

Build the next background in a protected RAM region, superimpose the new masked
pose, resolve that region's attributes, then copy only completed output to display.
Never visibly erase the old sprite before constructing its replacement. For a
moving screen-space sprite, cover the union of old and new rectangles, including
any cells touched by unaligned edges. The centered runner example does not solve
arbitrary X/Y movement automatically.

The smallest useful buffer is often the character's byte-aligned rectangle,
not a full-width strip. Rev09 protects X=112-143, Y=120-159: four bytes per row.
Other scenery can be drawn directly if it does not write the protected cells.
The older full-width buffer was correct but copied background twice unnecessarily.
Narrowing it recovered the CPU time needed by concurrent music.

The rev09 full update composes 40 rows, publishing 160 bitmap + 160 attribute
bytes. Intermediate rock-only updates compose the top 32 rows under the unchanged
pose and publish 128 bitmap bytes; the feet and attributes remain valid. This
optimization depends on the unchanged pose and fixed background palettes in those
cells. Restore/recompute attributes when either condition no longer holds.

In the example, each of six poses contains 320 mask/bitmap bytes followed by a
160-byte prepared attribute overlay. A fully transparent cell keeps the known
background attribute; a covered cell uses the sprite pair. Preparing attributes
offline is valid because the background's row palettes are fixed. It does not
generalize to arbitrary moving multi-color backgrounds without recomposition.

## Circular mixed destination copier

Rev09 copies a 32-byte scenery row as 14 bytes to display, four bytes to RAM,
and 14 bytes to display. The protected four are later published after the sprite.
The resident source wrap helper is reached through DOCK RST 08. One RAM-resident
LDI slot is patched to RST 08 / NOP, restored before the next scroll setup.
This uses the existing two-byte LDI slots instead of a per-byte wrap test.

This is an advanced example, not a drop-in routine. It requires an owned RST 08
vector, visible DOCK chunk 0 in every relevant bank mask, writable copier RAM,
safe stack/ISR placement, and an ISR that never invokes or alters the copier.
Otherwise use ordinary circular copies or preexpanded wrap lookahead. Never
write self-modifying code to a ROM image and assume cartridge hardware can patch it.

## Interrupt coexistence

Keep the ISR, vector and stack visible throughout rendering. A music ISR that
changes banks must preserve primary/alternate registers and IX/IY as required by
the driver, then restore the renderer's map. Save and restore SP if switching to
an audio stack. Do not restore a map that hides that stack before popping registers.

For the example's single HSR change from resident code, storing the intended
shadow BEFORE OUT allows an ISR to restore that intended map early; no data access
occurs between those two instructions. This is not a blanket replacement for DI
around multi-register or multi-bank transitions. Audit each interrupt window.
