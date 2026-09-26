# Native AY tunes alongside animation

Use this workflow for a user-supplied `.ay` chiptune or an existing Z80 music
driver. It is distinct from converting PCM speech/effects into synthesized AY
register frames. Keep the original driver when it fits and behaves correctly.

## Inspect before integrating

`python scripts/inspect_ay.py tune.ay --song 0 --json tune.json --extract blocks`
reports the selected ZXAYEMUL entry and extracts its code/data without executing
it. Python's standard library is sufficient. It deliberately rejects truncated
or out-of-range blocks rather than silently repairing a malformed file.

ZXAYEMUL words are big-endian; pointers are signed offsets relative to the
pointer field itself. Parse the song table, initial register values, stack,
init/tick addresses, memory blocks, duration and fade. A zero duration means
unknown, not an empty tune. An init of zero conventionally uses the first block
address. An interrupt entry of zero means the file may install its own interrupt
driver; it is not a callable tick routine. Do not impose the nonzero-entry example
on those files. Preserve the source hash and identify the chosen song explicitly.

The AY file format is described in the [AY Emulator author's documentation](https://documentation.help/AY-3-8910.12-ZX-Spectrum/ay_e04vt.htm).
A TSSoundPlayer `.tss` score and a ZXAYEMUL file are not interchangeable containers.
Inspect the actual local player before deciding whether to reuse it or just its
hardware output convention.

## Hardware adapter and scheduling

The demonstrated TS2068 player selects AY registers at FFF5 and writes at FFF6.
Spectrum FFFD/BFFD writes do not address the TS2068 AY in the same way. Redirect
a verified output helper, or reassemble the driver for the native ports. Do not
blindly replace every matching byte sequence in music data. Check the original
helper signature and preserve the driver-visible registers/flags it promises.
Preserve repeated R13 writes: they retrigger the envelope even if its value is
unchanged. Avoid writes to joystick I/O registers R14/R15 unless explicitly needed.
Do not apply the harmonic toolkit's R13=255 skip sentinel to arbitrary native
driver output; only a stream format that defines that sentinel may skip it.

Most callable AY drivers expect approximately 50 calls/s. On the nominal 60-Hz
TS2068 display, add 5 to a modulo-6 accumulator and tick when it reaches 6. That
gives five ticks per six interrupts rather than speeding the music up to 60 Hz.
For closer timing, use a phase accumulator based on the measured model's actual
refresh rate. Keep musical cadence independent of rendering/throttle; stopping
the character should not inadvertently stop background music.

Determine end/loop behavior by observing the driver, not only the metadata.
The title driver used in Beast Horizons stops producing writes near its end;
rev09 calls its original init again after the declared 5,450 ticks. Validate
reinitialization against fresh/reference playback and include restart work in
the worst-case interrupt budget. A different tune may loop internally or need
a different restart sequence. Do not add a fabricated fade or drop tail frames.

## Memory, interrupts and buffering

Executable drivers often modify their own state/code. Run them in writable HOME
RAM; DCK ROM descriptors do not become writable hardware. Preserve original load
addresses when practical. Relocation requires fixing code and data references,
not applying an offset to every word that resembles an address.

Keep code, ISR/vector, stack and display accessible during source-bank changes.
Save primary/alternate registers and IX/IY as required by the driver. If switching
to a music stack, restore the main stack before selecting a bank that hides the
music stack. Save/restore DECR if touched, retaining ECM and bank-selection bits.
Audit interruptions between software-shadow and hardware-bank updates.

Rev09 kept the driver at C000-D222, moved one scenery cache to HOME E000-FFFF,
and retained the other at A000-BFFF. Rendering used F3 or 53; audio selected 13.
The ISR used a separate stack below E000 and restored the renderer's HSR. These
are case-study addresses, not a general-purpose allocation contract.

Music initially made full-width buffered redraws too expensive. Protecting only
the character's four byte-columns preserved the picture and recovered the CPU
time, while retaining precomposed sprite output. Budget graphics and audio together;
do not quote an audio-only benchmark as spare time for an animated cartridge.

## Verification evidence and reuse limits

Execute the unmodified driver in a reference Z80 harness, capture ordered register
writes for init and each tick, then compare the native cartridge's writes. Preserve
write order and R13 retriggers, not merely final register snapshots. Include the
full song and at least one restart; an apparently successful long run may actually
spend its second half silently idle. Verify nonzero PCM and preview the audio.

In Beast Horizons rev09, TSRun matched 12,000 ticks including two restarts; Fuse
matched the first 1,000 ticks / 10,996 writes. A 6,000-update Fuse graphics/music
run peaked at 166,787 T-states within a 179,208 render bound. Rock transit stayed
about 10.7 seconds. Source tune SHA-256:
`6bf35f961ea524fadf5c303abe86d8f3979cbd92bc3cea9f377172ff19dc4ff9`.
Cartridge SHA-256:
`ac1b31362b696de8613eaf55a065ea9b49534afb6a0fa9533b83b22658db796a`.

Credit **Josef Jelinek** for the TS2068 AY player shared in his post,
**"A new TS 2068 AY music composer preview,"** on
[TS2068.groups.io](https://ts2068.groups.io/g/main). His TSSoundPlayer example
provided the native AY port reference used in this integration; the cartridge
retains the supplied tune's original driver and David Whittaker music credit.

The local TSSoundPlayer test TAP inspected as a port reference had SHA-256
`7796e18c7917e0278b93c348230da9e4cecbf2d62dc730282308ee77ae3c88dc`.
Its binary was not embedded. Neither that player, copyrighted tune, system ROMs
nor game artwork are bundled in this skill. The portable parser and guidance
require user-provided source material. Physical hardware was not tested in the
reference project; emulator output is not a claim of a hardware listening test.
