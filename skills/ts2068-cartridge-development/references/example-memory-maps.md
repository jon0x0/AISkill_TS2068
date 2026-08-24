# Worked example memory maps

Use these maps when selecting between copy-and-run compatibility and direct cartridge execution. Addresses are Z80 addresses after the named cartridge chunk is selected.

## Elite ECM: copy and run from HOME RAM

This TS2068 cartridge is a conversion of the ZX Spectrum Elite JCV tape program (`ELITEJCV.TAP`), not an originally cartridge-based TS2068 release.

Current build: `Elite_JCV_TS2068_ECM`, AROS entry `$8008`, startup cartridge chunks 2 and 4 visible.

| DOCK chunk | CPU range | Cartridge contents | Final/runtime use |
|---:|---|---|---|
| 0 | `$0000-$1FFF` | Elite bytes for HOME `$5B00-$5FFF`; IM2 table `$1000-$1100`; handler `$1818` | Helper maps/copies it, then unmaps DOCK |
| 1 | `$2000-$3FFF` | Elite bytes for HOME `$6000-$7FFF` | Stage-2 copy |
| 2 | `$4000-$5FFF` | Complete 6144-byte ECM title-screen color/attribute plane (`ecm-atr`) at `$4000-$57FF` | Curtain source copied into HOME `$6000-$77FF` |
| 3 | `$6000-$7FFF` | Elite bytes for HOME `$8000-$9FFF` | Stage-2 copy |
| 4 | `$8000-$9FFF` | Header/boot; complete 6144-byte ECM title-screen bitmap plane (`ecm-pix`) at `$8100-$98FF`; display routine `$9900-$99BD`; stage 2 `$9C00-$9C98`; helper `$9D00-$9DAB` | Bootstrap runs here; bitmap copies to HOME `$4000-$57FF`; other routines relocate |
| 5 | `$A000-$BFFF` | Elite bytes for HOME `$E000-$FFFF` | Stage-2 copy |
| 6 | `$C000-$DFFF` | Elite bytes for HOME `$A000-$BFFF` | Stage-2 copy |
| 7 | `$E000-$FFFF` | Elite bytes for HOME `$C000-$DFFF` | Stage-2 copy |

Execution chain:

1. DOCK `$8008` copies the 190-byte ECM routine from `$9900` to HOME `$7800` and calls it.
2. HOME `$7800-$78BD` selects DOCK chunk 4 to copy pixels to HOME `$4000-$57FF`, then chunk 2 to reveal colors into HOME `$6000-$77FF`. SCLD display fetches remain from HOME while CPU reads the chunk-2 overlay.
3. The ECM routine holds six seconds, blanks colors, restores normal mode, selects chunk 4, and returns.
4. Bootstrap copies stage 2 from DOCK `$9C00-$9C98` to HOME `$5B00-$5B98` and jumps there.
5. Stage 2 selects only each source chunk and reconstructs the original 42,240-byte payload in HOME `$5B00-$FFFF`.
6. Stage 2 copies the final helper from DOCK `$9D00-$9DAB` to HOME `$606F-$611A`; the helper copies chunk 0, unmaps DOCK, recreates captured loader-return state, and jumps HOME `$D07F`.

Title-screen planes:

The source planes can be authored with [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) in **Timex Extended Color (256×192, 8×1 attrs)** mode. The Elite title specifically uses **Sierra Lite** dithering. Its TAP exports 6144-byte `ecm-pix` and `ecm-atr` blocks for runtime destinations `$4000` and `$6000`; extract and validate them, then use the cartridge-specific storage addresses below rather than assuming the TAP order is the ROM layout.

| Component | Bytes | Cartridge storage/source | HOME destination | Transfer |
|---|---:|---|---|---|
| Bitmap (`ecm-pix`) | 6144 | DOCK chunk 4, `$8100-$98FF`, HSR `$10` | `$4000-$57FF` | One `LDIR` before the wipe |
| ECM attributes (`ecm-atr`) | 6144 | DOCK chunk 2, `$4000-$57FF`, HSR `$04` | `$6000-$77FF` | Column-by-column curtain reveal |

The two uncompressed planes total 12,288 bytes. The bitmap provides the actual title artwork; the attribute plane supplies its Extended Color Mode colors.

Exact display procedure and execution location:

| Phase | PC/code location | SP | HSR | DECR | Operation |
|---|---|---|---:|---:|---|
| Bootstrap | DOCK `$8008` | AROS startup stack | startup chunks 2+4 | startup mode | Copy 190-byte display routine from DOCK `$9900-$99BD` to HOME `$7800-$78BD`; call `$7800` |
| Prepare | HOME `$7800-$78BD` | move to HOME `$BFFF` | controlled by routine | `$02` | Disable interrupts, preserve return address, clear HOME attributes `$6000-$77FF`, enter ECM |
| Bitmap | HOME `$7800-$78BD` | HOME `$BFFF` | `$10` | `$02` | `LDIR` `$1800` bytes from DOCK `$8100-$98FF` to HOME `$4000-$57FF` |
| Curtain | HOME `$7800-$78BD` | HOME `$BFFF` | `$04` | `$02` | Copy the DOCK attribute plane at CPU `$4000-$57FF` into HOME `$6000-$77FF` as 16 paired center-out columns |
| Hold | HOME `$7800-$78BD` | HOME `$BFFF` | `$00` | `$02` | Restore all HOME mappings and display the completed image for six seconds |
| Cleanup/return | HOME `$7800-$78BD`, then DOCK chunk 4 | HOME `$BFFF` | `$00`, then `$10` | `$02`, then `$00` | Black the attribute plane, clear the normal screen, leave ECM, remap chunk 4, and return to the bootstrap |

Run the display routine from HOME RAM, not from cartridge chunk 4. HSR `$04` is required to expose the cartridge attribute plane, and that value removes cartridge chunk 4 from the CPU view. A routine still executing there would page itself out. HOME `$7800` remains visible because HSR bit 3 stays clear, and the stack at HOME `$BFFF` remains writable because bit 5 stays clear. During HSR `$04`, SCLD continues displaying the underlying HOME bitmap even though CPU reads at `$4000` return cartridge attributes.

This exact `$7800`/direct-DECR routine is a full-control machine-code prelude. Do not transplant it unchanged into BASIC AROS: the ROM video service clears `$6000-$7AFF`, relocates the BASIC/dispatcher/stack state, and BASIC AROS cannot execute statements while that advanced display is open. For a BASIC host, use stable protected HOME code, enter through verified EXROM `CHNG_VID`, keep the whole title/hold/exit inside machine code, and completely restore normal mode before returning. Read [aros-and-basic.md](aros-and-basic.md#ecm-routines-in-machine-code-versus-basic-aros) for the complete contract and known ROM faults.

Do not keep chunk 4 selected while stage 2 writes HOME `$8000-$9FFF`: read-only DOCK would cover the destination. The Elite program executes from HOME because its protected/self-modifying Spectrum code requires writable RAM.

ROM translation:

| Purpose | Spectrum | TS2068 adaptation |
|---|---:|---:|
| Final `LD-BYTES` | `$0556` | Replaced by cartridge copies/state restoration |
| Pixel entry | `$22B0` | HOME ROM `$2609` |
| Next-byte pixel entry | `$22B1` | HOME ROM `$260A` |
| Checked pixel entry | `$22AA` | HOME ROM `$2603` |
| Commander SAVE | `$04C6` | EXROM `$006C`, verified but disabled in current stable build |
| Commander LOAD | `$0562` | EXROM `$0108`, verified but disabled in current stable build |
| ECM mode | n/a | Direct DECR `$02/$00`; do not call EXROM `CHNG_VID` `$0E8E` from this launcher |

The standard non-ECM variant stores the exact 6912-byte Spectrum screen at DOCK `$8100-$9BFF` and copies it to HOME `$4000-$5AFF`.

## TSVideoCodec: resident player plus FIFO media

Repository: [jon0x0/TSVideoCodec](https://github.com/jon0x0/TSVideoCodec)

Chunk 4 contains the AROS player and executes directly at `$8008-$9FFF`. Other chunks form seven logical FIFO slots:

| Slot | Stored chunk/address | Runtime source | HSR |
|---:|---|---|---:|
| 0 | 0 / `$0000` | DOCK `$0000` | `$11` |
| 1 | 1 / `$2000` | DOCK `$2000` | `$12` |
| 2 | 2 / `$4000` | preloaded HOME `$C000` | `$10` |
| 3 | 3 / `$6000` | preloaded HOME `$E000` | `$10` |
| 4 | 5 / `$A000` | DOCK `$A000` | `$30` |
| 5 | 6 / `$C000` | DOCK `$C000` | `$50` |
| 6 | 7 / `$E000` | DOCK `$E000` | `$90` |

At boot, `PRELOAD_SHADOW` uses HSR `$1C` to copy cartridge `$4000-$7FFF` to HOME `$C000-$FFFF`, then restores HSR `$10`. This keeps HOME `$4000-$57FF` and `$6000-$77FF` available as live ECM bitmap/color planes. Player variables occupy HOME `$7800-$781C`; SP starts at HOME `$7FFF`.

Exact symbols for representative build `dino_full_6fps_1800/cartridge_fifo_fast`:

| Symbol | Address |
|---|---:|
| `START` | `$8008` |
| `PRELOAD_SHADOW` | `$80C0` |
| `COPY_FRAME` | `$80D4` |
| `COPY_PACK_KEY` / `DECODE_PACKBITS` | `$8128` / `$8159` |
| `COPY_FIFO_HYBRID` | `$81CF` |
| `FIFO_SELECT` / `FIFO_NEXT` | `$81EA` / `$8201` |
| `DECODE_FIFO_HYBRID_PLANE` | `$822F` |
| `COPY_DONE` / `FIFO_MASKS` | `$83D6` / `$83DE` |
| `FRAME_TABLE_PTRS` | `$8565` |

These exact addresses are generated-build-specific. Code and lookup tables always reside in chunk 4, but options and generated tables can move labels.

Playback first calls `COPY_PACK_KEY` to decompress the complete PackBits ECM keyframe—the first video frame—into HOME `$4000` and `$6000`. After that baseline exists, the delta decoder runs directly from cartridge, selects each update record's starting slot, reads commands, and XORs changes into those HOME planes. `$C1` selects the next FIFO slot; `$C2,0` skips one padding byte and then selects it. `COPY_DONE` restores HSR `$10`. SCLD continues fetching the HOME display while CPU reads a cartridge source.

In the representative 30-frame build, the first frame's two raw ECM planes total 12,288 bytes and its PackBits keyframe is 4,363 bytes: bitmap starts slot 0 `$0000`, colors start `$08C1`, and the first subsequent FIFO delta starts `$110B`. Frame tables hold later delta slot/address pairs. The build carries 39,247 payload bytes with 10 FIFO marker/padding bytes in an exact 64K BIN.

TSVideoCodec has no Spectrum ROM call translations. It controls HSR `$F4`, DECR `$FF`, and AY `$F5/$F6` directly. HSR `$10` keeps HOME chunk 0 visible for the normal TS2068 IM1 vector at `$0038`, and scheduling reads HOME frame counter `$5C78`.
