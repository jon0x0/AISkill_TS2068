# speech2ay project and experience map

Canonical project: https://github.com/jon0x0/speech2ay
Live comparison: https://jon0x0.github.io/speech2ay/
Bundled toolkit snapshot: `c3f50c6721e6bca160c4a53f5a0a40442b1232b9`, refreshed 2026-09-04.
Prefer the canonical project for ongoing tool development; inspect its current
code and CLI before assuming a newer checkout behaves like this snapshot.
The portable copy in `../assets/audio-tools/` is usable without the game tree.
After refreshing it, update this revision and `SHA256SUMS.json`. Exclude demo
recordings, build scratch, vendored emulator/system ROMs and Git metadata.

## Load the relevant experience

| Task | Read in the bundled toolkit |
|---|---|
| Convert WAVs or reproduce a command | `docs/command-line-guide.md`, `tsaudio/cli.py` |
| Choose codecs or explain CPU/compression | `docs/speaking-with-the-ts2068.md` |
| Modify callable players, data loading or timing | `docs/integration.md`, `tsaudio/assembly.py`, `asm/` |
| Improve harmonic analysis | `tsaudio/harmonic.py`, `bands.py`, `codecs.py` |
| Improve optimizer or diagnose worse sound | `tsaudio/search.py`, `optimizer.py`, `ay_optimizer_worker.c`, `docs/optimizer-regression.json` |
| Build or change the multi-codec UI | `tsaudio/comparison.py`, `spectrum_ui.py`, `spectrum.py`, `examples/update_comparison.py` |
| Decide what a test actually proves | `docs/validation.md`, `tests/` |

These paths are relative to `assets/audio-tools/` in the skill. The same paths
exist at the root of the canonical project. Do not assume machine-specific
WAV, assembler, Ayumi or game locations exist on another installation.

## Regression lessons

- Humanoid optimized3 previously changed all 38 frames, used envelopes in 22
  frames and restarted envelopes 21 times. It sounded worse despite lower
  spectral/waveform errors. Conservative search now keeps routing, disables new
  envelopes, bounds periods to ±6% of each original frame, and accepts only
  improvements with no worsening of any of four clip-average components.
  The checked result changes 9 frames with no envelopes. These are numerical
  and structural checks, not proof of subjective quality. Keep listening A/Bs.
- `--search-mode auto` selects conservative for filtered audio and free for
  `berzerk`. `free` retains wider envelope/mixer/period exploration. Cache keys
  include search mode; record resolved mode, objectives and baseline/retained
  metrics. Preserve source hashes and identical filtering when comparing.
- The Berzerk effect profile uses raw input, legacy 1,774,400 Hz band estimation,
  calibrated 1,764,750 Hz rendering, spectral candidate search and the requested
  final objective (joint by default), two passes. The demo laser is player shot
  **30.wav**; 31.wav was an earlier robot-shot reference, not the current sample.
  Do not alter a game cartridge as a side effect of improving the audio tools.
- Occasional reported low first-play volume was not reproduced in the recorded
  checks. Check AY initialization, playback ordering, envelope state and repeated
  playback before claiming it fixed. Do not replace the reported symptom with
  an unrelated numeric optimization.
- AY4 maps to nonlinear AY volume levels; DPCM3 reconstructs those 4-bit volume
  codes from deltas. Harmonic synthesis uses tone/noise/envelope generators,
  not the AY as a high-rate DAC.
- One/two-channel reference streams still have 14-byte frames. Starred menu
  counts estimate a compact 8/11-byte frame format after the same LZ rules;
  actual `stored_bytes` remain separate from `compact_estimate`. An adapted
  loader/player would be required. Never present estimates as actual ROM use.

## Documentation and publication

Keep **speech2ay** as the project name and **TS2068 Audio Lab** as the demo name.
Use portable relative document links. Distinguish T-states (Z80 clock cycles),
scheduled DAC slots, available foreground time, and interrupt overhead. Include
the 1-bit beeper alternative when discussing playback choices. Separate modeled
spectra from real recordings, and measured evidence from future proposals.
Update source Markdown and run `npm run build:web` for generated article pages.
Explain algorithms from the actual code, including defaults, bounds, acceptance
criteria and known limitations; do not infer them from a codec label.
