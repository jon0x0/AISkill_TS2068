---
name: ts2068-audio-development
description: Convert speech and sound effects into AY-compensated DAC or harmonic AY data with speech2ay, improve and validate ayfit optimization, build TS2068 Audio Lab demos, and integrate callable Z80 audio playback.
---

# TS2068 audio development

The maintained tools are [speech2ay](https://github.com/jon0x0/speech2ay).
Use the bundled [toolkit](assets/audio-tools/README.md) for portable work;
read [project and regression experience](references/project.md) when selecting
a workflow, diagnosing quality, refreshing the copy or updating documentation.

## Select the work

- `audio2aydac.py`: compensated AY4 at 5/6 kHz and DPCM3 at 6 kHz.
- `speech2ay.py`: harmonic synthesis with one, two or three AY channels.
- `ayfit.py`: stateful Ayumi-based parameter optimization. Default conservative
  speech search preserves harmonic structure; `free` explores wider settings.
- `aydemo.py`: TS2068 Audio Lab sample/codec menu, animation, optional offline
  spectra, optimized entries and upstream Audio2AY comparisons.

Read the [command-line guide](assets/audio-tools/docs/command-line-guide.md)
for examples, and [integration](assets/audio-tools/docs/integration.md) before
changing assembly, memory maps, stream layout or interrupts. The
[article](assets/audio-tools/docs/speaking-with-the-ts2068.md) explains Ayumi,
optimizer bounds, CPU/storage accounting and possible improvements.
Read [validation](assets/audio-tools/docs/validation.md) before claiming support.
For browser embedding, the companion skill in the full library is
`ts2068-tsrun-web-demo`; the maintained implementation is the project's `web/`.

## Preserve the hardware and timing assumptions

- CPU 3.528 MHz, modeled AY 1.764750 MHz, display 60.1145 Hz. Call `ay_tick`
  once per display interrupt; preserve registers and the final frame interval.
- DAC playback blocks on a strict sample schedule. Padding is a replaceable
  instruction budget, not automatically returned foreground time. Validate
  inter-sample gaps, contention and group/frame boundaries after changes.
- The expanded animation reserves 340 T-states per DAC sample and restricts
  copies to the first 7168 T-states of the synchronized frame. The AY animation
  has its own interrupt cost; do not quote audio-only spare CPU as total spare CPU.
- R13=255 skips envelope restart. Noise/envelope generators are shared;
  optimizer candidates must start from the same chip and filter state.
- Expanded DCK uses eight ROM chunks, resident DOCK4 at $8000–$9FFF, baseline
  HSR=$10 and native HOME RAM for stack/state. During mappings hiding the stack,
  no calls, stack access or interrupts are safe. Follow the documented memory map.
- Compressed staging at $A800–$BFFF is at most 6144 bytes; expanded playback
  at $D000–$FDFF is at most 11776 bytes. Restore HSR before expansion/playback.
  Physical ROM bytes use flat address offsets; DCK headers are container data.
  Do not mark ROM as writable RAM for an EPROM or USB-programmable PicoROM-28.
- Stop playback before replacing active data. Use each artifact's own symbols.
  Separate BIN data does not imply a supplied runtime tape loader. The supplied
  routines own AY registers; adapt explicitly for concurrent sound or ECM.

## Verify the relevant behavior

Run `python -m unittest discover -s tests -p 'test_*.py'` in the toolkit for
converter/search changes. Use the specific export, timing and banked playback
checks described in validation when changing those mechanisms. The canonical
`tests/verify_tsrun.mjs` exercises all 40 demo choices using a local TSRun checkout;
it does not establish subjective quality or physical hardware behavior.
Preserve source hashes, compare baseline and result, and keep unchanged codecs
byte-identical when replacing selected entries. Regenerate runtime assembly
from `tsaudio/assembly.py`; do not patch output binaries by hand.
