# Validation and demonstrated experience

For later Berzerk, Sinistar, Beast Horizons rev14 and TSWriter optimization lessons,
read [optimization experience](optimization.md). The rev07-09 results below remain
historical evidence for their named artifacts.

The source experience is ParallaxDemo / Beast Horizons, preserved revisions 07-09
(2026-09-26). If that project is available, inspect its archived sources, build
scripts and reports. This package does not require that checkout and does not
bundle the game artwork, tune, system ROMs or emulator binaries.

Meaningful graphics checks:

- Decode both output planes independently; compare complete emulator display
  RAM against an independent compositor across every fine/coarse scroll position.
- Check mask convention, alpha holes, cell attributes, wraparound and all poses.
  Include stopping, restarting and maximum motion speed.
- Assert the protected sprite rectangle stays unchanged until composition ends;
  each subsequent write must be its final expected value. Compare the active
  buffer cells, not unused space reserved around a narrowed buffer.
- Verify rigid phase shifts and palette invariance separately. Correct bit motion
  does not prove correct attributes or absence of dither crawl.
- Check cartridge ROM immutability, cached data, stack limits and bank masks while
  graphics and interrupts run together. Inspect the DCK header and expanded BIN.
- Use real completion timestamps for GIF durations; describe frame-loop jumps.
  A display-RAM capture cannot establish live raster tear freedom.

Revision 09 retained byte-identical rev08 artwork. TSRun passed 2,305 exact display
and protected-buffer comparisons. Fuse passed 6,000 maximum-speed animation
updates with the AY tune and two restarts active: maximum render interval
166,787 T-states versus a 179,208 three-refresh bound. Rock transit was 10.68 s
for the first cycle and 10.67 s averaged over the long run. These are measured
results for that artifact, not budgets promised for a different scene.

The Fuse reports used its observed 59,736 T-states per video frame; TSRun reports
used 58,688. Confirm the actual model/version and frame counter before converting
traces to time; do not combine one emulator's frame size with another's trace.
Physical TS2068 hardware remained untested in this reference project.

The rev09 DCK SHA-256 is
`ac1b31362b696de8613eaf55a065ea9b49534afb6a0fa9533b83b22658db796a`.
When the project requires revision preservation, retain accepted source, artifacts,
previews and evidence before edits; do not overwrite a populated revision archive.
