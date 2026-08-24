# Proven cartridge architecture patterns

## Elite: copy-and-run compatibility cartridge

The Elite TS2068 cartridge is converted from the ZX Spectrum Elite JCV tape program (`ELITEJCV.TAP`). See [example-memory-maps.md](example-memory-maps.md#elite-ecm-copy-and-run-from-home-ram) for the current Elite ECM build's exact cartridge addresses, relocation chain, HOME-RAM result, and Spectrum-to-TS2068 ROM translations.

Use this pattern for an existing Spectrum program that expects writable RAM, self-modifying code, a particular loader return state, or Spectrum-style memory ownership.

- Boot from machine-code Application ROM-Oriented Software (AROS) in DOCK chunk 4.
- Keep the executing chunk selected while reading other cartridge chunks.
- Copy payload blocks into different, still-HOME destination chunks.
- Run the final program from HOME RAM.
- Reproduce required registers, interrupt mode, stack, and timing at handoff.
- Relocate or wrap incompatible Spectrum ROM calls.
- Put later DOCK/Extension ROM (EXROM) gateways in verified isolated RAM, not merely bytes that happen to be zero in the original image.

Critical lesson: selecting source chunk 3 and executing cartridge chunk 4 while copying into HOME `$8000-$9FFF` kept chunk 4 ROM over the destination. `LDIR` completed but HOME RAM stayed unchanged. Run the copier from HOME and select only the source when the destination lies under the old execution bank.

### Native title-screen prelude and PackBits variant

Create source planes with [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) by selecting **Timex Extended Color (256×192, 8×1 attrs)**. For the Elite cartridge, select **Sierra Lite** dithering to reproduce the current ECM title artwork. Its ECM TAP exports separate 6144-byte `ecm-pix` (`$4000`) and `ecm-atr` (`$6000`) CODE blocks. Treat those addresses and the optional attributes-first TAP order as interchange metadata: validate each plane, then place it according to the cartridge's chunk map.

The accepted Elite ECM build demonstrates the raw-media form of this pattern:

- extract and checksum-validate 6144-byte pixel and 6144-byte color planes;
- store pixels in the tail of DOCK chunk 4 and colors in DOCK chunk 2;
- copy a small launcher into unaffected HOME RAM;
- copy pixels to HOME `$4000-$57FF`;
- reveal colors into HOME `$6000-$77FF` with a center curtain;
- hold for six seconds, clear the color plane to black, restore normal video, and continue into the main bootstrap.

Treat PackBits as optional. Prefer raw planes when they fit comfortably: direct copies need less code, start faster, and reduce validation risk. Use PackBits only when the recovered space is useful enough to justify its decoder, metadata, and runtime cost. Compress each plane independently, store `(codec, HSR mask, source address, packed length, output length)` metadata, and choose raw storage unless PackBits gives a worthwhile saving. Use a decoder with a bank-aware input-byte routine and an exact output counter.

Keep HSR bits 2/3 zero while decoding directly into HOME display RAM. If the compressed source occupies the same cartridge chunk as its HOME destination, decode into a different HOME buffer, restore the destination's HOME mapping, and copy afterward. For a curtain reveal, decode attributes into temporary HOME RAM, clear the live color plane, enter ECM, and copy columns to `$6000-$77FF`.

Verify each compressed stream by build-time round trip, decoded length, and source hash. Validate the live HOME planes byte-for-byte in Fuse before the reveal/handoff. Keep stack and executing code outside every selected source chunk.

Local sources:

- `cartridgeconversion/elite/scripts/build_dck.py`
- `cartridgeconversion/elite/src/ecm_cartridge_startup.asm`
- `cartridgeconversion/elite/PROJECT_STATE.md`

## TSVideoCodec: command-aware FIFO packing

See [example-memory-maps.md](example-memory-maps.md#tsvideocodec-resident-player-plus-fifo-media) for the exact chunk/slot map, shadow preload, display and work RAM, representative decoder symbols, media locations, and runtime source selection.

Repository: [jon0x0/TSVideoCodec](https://github.com/jon0x0/TSVideoCodec)

Use this pattern for media, levels, or large immutable datasets.

- Encode the first complete ECM video frame as a PackBits keyframe, with independent bitmap and color streams. Decompress both into the live HOME display before applying any later delta record.
- Keep the player and tables in DOCK chunk 4 and keep bit 4 set in every cartridge-data HSR mask.
- Use cartridge chunks `0,1,2,3,5,6,7` as seven ordered payload slots, yielding one logical 56K stream.
- At boot select HSR=`$1C`, copy cartridge `$4000-$7FFF` (chunks 2/3) to HOME `$C000-$FFFF` (chunks 6/7), and restore HSR=`$10`. This frees HOME chunks 2/3 for live Extended Color Mode display writes.
- Use this slot table:

| Slot | Stored cartridge chunk | Runtime source | HSR mask |
|---:|---:|---:|---:|
| 0 | 0 | `$0000` | `$11` |
| 1 | 1 | `$2000` | `$12` |
| 2 | 2, preloaded | `$C000` | `$10` |
| 3 | 3, preloaded | `$E000` | `$10` |
| 4 | 5 | `$A000` | `$30` |
| 5 | 6 | `$C000` | `$50` |
| 6 | 7 | `$E000` | `$90` |

Treat the PackBits keyframe as the playback baseline. Store each later delta's FIFO starting slot and source address. Reserve codec control `$C1` for NEXT_BANK and `$C2,0` for NEXT_BANK_PADDED. On `$C1/$C2`, select the next slot and reset the source address; restore HSR=`$10` after the record.

The packer must be codec-aware:

- if a command fits in the current slot, emit it unchanged;
- with one byte left, emit `$C1` and continue the command in the next slot;
- with two bytes left, emit `$C2,0` and continue in the next slot;
- split literal commands into valid shorter literals when that fills a tail;
- convert a sparse mask command that cannot fit into an equivalent eight-byte literal, then split it safely;
- keep audio and any alignment-sensitive record bank-local when its reader requires that.

This removes whole-record bank-tail fragmentation and the 8K maximum frame size while keeping the hot decoder fast: it checks for a bank transition only at command boundaries, not after every input byte. The reference 30-frame measurement used 39,247 payload bytes and only 10 boundary/padding bytes, with exact final-screen reconstruction.

Validate by rebuilding every indexed record from its start slot/address, decoding it, comparing it byte-for-byte with its source, rejecting overflow after slot 6, and checking the output BIN is exactly 64K. The current design provides 56K arbitrary media plus 8K code/tables. For payload nearer 64K, copy the player to HOME RAM and add unused chunk-4 ranges to a segment table; cartridge-resident header/bootstrap/decoder bytes remain unavoidable overhead.

Local sources:

- `TSVideoCodec/src/cartridge/cartridge_boot.asm`
- `TSVideoCodec/src/cartridge/build_cartridge.py`
- `TSVideoCodec/src/encoder/fifo_hybrid.py`

## VU-3D: BASIC AROS packaging

Use the accepted VU-3D Fuse DCK (`.dck`) cartridge image as evidence for a BASIC AROS layout:

- DCK descriptors store cartridge chunks 4-6.
- Chunk 4 begins `01 02 08 80 EF 01 00 02`.
- BASIC lines begin at `$8008` and are tokenized in ROM-executable format.
- The build demonstrates cartridge BASIC plus machine-code/data across multiple upper chunks.

Do not generalize its exact reserve count or USR behavior without tracing the relevant ROM support path; BASIC AROS has documented bugs.

Local examples:

- `cartridges/VU-3D.dck`
- `cartridges/VU3D-rom.bin`
- `cartridges/VU3D256Kbit.bin`

## Berzerk: cartridge ROM plus DCK RAM

Use DCK descriptor 1 or 3 when an emulator test genuinely needs writable cartridge RAM. Keep this distinct from HOME RAM and from physical ROM output. A write to descriptor-2 ROM silently fails.

Local source: `cartridgeconversion/berserk/scripts/make_dck.py`.

## Direct video-mode control from a cartridge

From a machine-code-only cartridge that does not need BASIC's display-state machinery, proven extended-color-mode (ECM) launchers write mode 2 directly to Display Enhancement Control Register (DECR) port `$FF`. Calling a higher-level ROM video-change routine from live DOCK context may depend on stack, dispatcher, and mapping state and has failed in practice.

Preserve DECR bit 7 and all other intended control bits in general-purpose software. A standalone launcher may write a complete known DECR value only when it owns the machine state and deliberately selects DOCK/EXROM behavior.
