# Buffered characters and background restoration

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
