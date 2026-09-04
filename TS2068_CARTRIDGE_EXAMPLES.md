# Worked TS2068 Cartridge Examples and Memory Maps

**When to read:** Use for concrete Elite and TSVideoCodec memory maps, resident code and data-transfer patterns. For audio conversion and playback experience, see [audio development](TS2068_AUDIO_GUIDE.md); for browser cartridge demos, see [TSRun embedding](TS2068_BROWSER_DEMOS.md).
These examples show two different ways to organize a full-size Timex Sinclair 2068 cartridge. Elite is a compatibility-oriented copy-and-run conversion of the ZX Spectrum Elite JCV tape program (`ELITEJCV.TAP`): its launcher and media begin in cartridge ROM, but the protected Spectrum program is reconstructed in HOME RAM and runs there. TSVideoCodec is a streaming cartridge: its player and decoders execute directly from cartridge chunk 4 while compressed media is selected from the other seven chunks.

Addresses below are Z80 addresses after a chunk is selected, not offsets in a DCK file. A flat 64K physical cartridge uses the same numerical offset as the chunk's fixed CPU address. See the [glossary](TS2068_CARTRIDGE_GLOSSARY.md) for HOME, DOCK, EXROM, HSR, DECR, ECM, and SCLD.

## Example 1: Elite ECM Spectrum conversion

### Cartridge storage map

This map describes the reproducible `Elite_JCV_TS2068_ECM` cartridge build converted from the ZX Spectrum `ELITEJCV.TAP` tape image. Its AROS header is at cartridge `$8000-$8007`, its entry point is `$8008`, and startup exposes cartridge chunks 2 and 4. The other chunks are selected later by code.

| Cartridge chunk | CPU address when selected | Contents in the current ECM build | Runtime use |
|---:|---|---|---|
| 0 | `$0000-$1FFF` | Elite bytes destined for HOME `$5B00-$5FFF`; temporary IM2 table at `$1000-$1100`; temporary `EI; RETI` handler at `$1818-$181A` | Mapped briefly by the HOME helper, then copied into HOME RAM |
| 1 | `$2000-$3FFF` | Elite bytes destined for HOME `$6000-$7FFF` | Copied by stage 2 |
| 2 | `$4000-$5FFF` | Complete 6144-byte Elite ECM title-screen color/attribute plane at `$4000-$57FF`; padding at `$5800-$5FFF` | Read during the curtain reveal while the SCLD still displays underlying HOME screen RAM |
| 3 | `$6000-$7FFF` | Elite bytes destined for HOME `$8000-$9FFF` | Copied by stage 2 |
| 4 | `$8000-$9FFF` | AROS header/bootstrap; complete 6144-byte Elite ECM title-screen bitmap plane at `$8100-$98FF`; stored display routine `$9900-$99BD`; stage 2 `$9C00-$9C98`; helper `$9D00-$9DAB` | Startup and resident source bank; the bitmap is copied to HOME display RAM and the routines are relocated before they run |
| 5 | `$A000-$BFFF` | Elite bytes destined for HOME `$E000-$FFFF` | Copied by stage 2 |
| 6 | `$C000-$DFFF` | Elite bytes destined for HOME `$A000-$BFFF` | Copied by stage 2 |
| 7 | `$E000-$FFFF` | Elite bytes destined for HOME `$C000-$DFFF`, including the synchronized-startup patch source | Copied by stage 2 |

### ECM title-screen image data flow

The title image is not contained in the attribute plane alone. It was created in [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) by selecting **Timex Extended Color (256×192, 8×1 attrs)** and **Sierra Lite** dithering, then exporting the result as a TAP. The converter's ECM TAP has two independent CODE blocks, both extracted and stored without compression in this build:

| Title-screen component | TAP block | Bytes | Stored in cartridge | CPU source while mapped | HOME display destination | Purpose |
|---|---|---:|---|---|---|---|
| Bitmap/pixel plane | `ecm-pix` | 6144 (`$1800`) | DOCK chunk 4, flat ROM `$8100-$98FF` | `$8100-$98FF` with HSR `$10` | HOME `$4000-$57FF` | Supplies every monochrome pixel bit of the Elite title artwork |
| Extended-color attribute plane | `ecm-atr` | 6144 (`$1800`) | DOCK chunk 2, flat ROM `$4000-$57FF` | `$4000-$57FF` with HSR `$04` | HOME `$6000-$77FF` | Supplies one color byte per 8-pixel cell in Extended Color Mode |

Together these two planes occupy 12,288 bytes of cartridge ROM. The bitmap is copied in one `LDIR` before the reveal. The color plane is then copied column by column by the curtain routine. The normal non-ECM cartridge instead stores the byte-exact 6912-byte Spectrum loading screen at cartridge `$8100-$9BFF` and copies it directly to HOME `$4000-$5AFF`.

The converter assigns normal runtime destinations `$4000` to `ecm-pix` and `$6000` to `ecm-atr`. Its **Attributes first in .TAP** option can improve a tape/viewer reveal by loading colors before pixels, but neither the TAP addresses nor block order dictates cartridge storage. The Elite build verifies that each extracted plane is exactly 6144 bytes, then places the bitmap at DOCK `$8100` and attributes at DOCK `$4000` according to the available bank space. The HOME-resident display routine performs the final copies and mode transition.

### Where code starts, moves, and executes

| Phase | Stored at | Executes at | Mapping/action |
|---|---|---|---|
| AROS entry | DOCK `$8008` | DOCK `$8008` | Starts with interrupts disabled and makes the border black |
| ECM display routine | DOCK `$9900-$99BD` | HOME `$7800-$78BD` | Bootstrap copies 190 bytes to HOME and calls `$7800` |
| Stage 2 copier | DOCK `$9C00-$9C98` | HOME `$5B00-$5B98` | Copies the five large Elite payload blocks while selecting only each source bank |
| Final state helper | DOCK `$9D00-$9DAB` | HOME `$606F-$611A` | Copies chunk 0 into HOME `$5B00-$5FFF`, unmaps DOCK, restores the measured loader-return state, and jumps to Elite |
| Elite program | Distributed through cartridge chunks 0, 1, 3, 5, 6, and 7 | HOME `$5B00-$FFFF` | Runs from writable HOME RAM; protected/self-modifying code is not executed in cartridge ROM |
| Elite handoff | HOME payload | HOME `$D07F` | Entry state matches the original Spectrum immediately after its last tape load |

Relocation is essential here. The ECM routine must change HSR between chunks 4 and 2, so it could page itself out if it remained in cartridge chunk 4. Stage 2 also has to write HOME `$8000-$9FFF`; executing it from HOME `$5B00` permits HSR `$08` to expose source chunk 3 without leaving read-only chunk 4 over the destination.

### ECM display routine: procedure and execution location

The display routine is stored in cartridge ROM but does **not** perform the reveal from there. The AROS bootstrap initially executes from DOCK chunk 4 at `$8008`. It copies the 190-byte routine from DOCK `$9900-$99BD` into HOME RAM `$7800-$78BD` and calls HOME `$7800`. All screen copying, mode switching, curtain animation, six-second hold, and cleanup then execute from that HOME-RAM copy with interrupts disabled. The routine moves its writable stack to HOME `$BFFF` before touching the second display area.

| Phase | Code executing from | HSR value | DECR value | CPU-visible source/destination and action |
|---|---|---:|---:|---|
| AROS setup | DOCK chunk 4, `$8008` | startup selection includes chunks 2 and 4 | normal startup state | Copy routine `$9900-$99BD` to HOME `$7800-$78BD`; call `$7800` |
| Prepare display | HOME `$7800-$78BD` | startup selection, then controlled explicitly | `$02` | Move SP to HOME `$BFFF`; clear HOME ECM attributes `$6000-$77FF` to black; enter Extended Color Mode |
| Copy bitmap | HOME `$7800-$78BD` | `$10` | `$02` | Chunk 4 is DOCK and chunk 2 is HOME: `LDIR` 6144 bytes from DOCK `$8100-$98FF` to HOME bitmap `$4000-$57FF` |
| Reveal attributes | HOME `$7800-$78BD` | `$04` | `$02` | Chunk 2 is DOCK and chunk 3 is HOME: read attributes at DOCK `$4000-$57FF` and copy paired center-out columns to HOME `$6000-$77FF` |
| Hold completed image | HOME `$7800-$78BD` | `$00` | `$02` | Restore the CPU's all-HOME view and busy-wait for six seconds; SCLD reads both HOME display planes |
| Blank and leave ECM | HOME `$7800-$78BD` | `$00` | `$02`, then `$00` | Clear HOME `$6000-$77FF` to black, clear HOME `$4000-$5AFF`, then restore normal video mode |
| Return to bootstrap | HOME `$7800-$78BD`, then DOCK `$8008+` | `$10` | `$00` | Remap executable chunk 4 and `RET` to the cartridge bootstrap |

The exact sequence is:

1. The AROS header starts the bootstrap at DOCK `$8008` with cartridge chunks 2 and 4 available.
2. The bootstrap copies the display routine out of cartridge `$9900-$99BD` into unaffected HOME chunk 3 at `$7800-$78BD`, then calls `$7800`.
3. The HOME routine disables interrupts, preserves the bootstrap return address, moves SP to writable HOME `$BFFF`, and clears HOME `$6000-$77FF`. Starting with a black color plane prevents stale colors from flashing onto the screen.
4. It writes `$02` to DECR port `$FF`, selecting TS2068 Extended Color Mode while keeping DOCK as the external bank.
5. It writes `$10` to HSR port `$F4`. Only cartridge chunk 4 is now selected, so the bitmap source at `$8100` is visible while HOME bitmap RAM at `$4000` remains writable. One `LDIR` copies `$1800` bytes to HOME `$4000-$57FF`.
6. It writes `$04` to HSR. Cartridge chunk 2 now supplies the attribute source at CPU `$4000-$57FF`; HOME chunk 3, containing both the executing routine and destination `$6000-$77FF`, remains selected. The curtain loop copies 16 paired columns from the center outward, with a short delay after each pair.
7. During the attribute copy, the CPU reads cartridge bytes at `$4000`, but the Standard Cell Logic Device (SCLD) independently continues reading the visible bitmap from the underlying HOME `$4000-$57FF`. Thus the picture remains visible even though those HOME addresses are temporarily hidden from the CPU.
8. After all attributes are present, the routine writes `$00` to HSR so the CPU again sees all HOME memory and holds the finished two-plane image for six seconds.
9. It clears HOME `$6000-$77FF` to black first, clears the normal screen at HOME `$4000-$5AFF`, writes `$00` to DECR to restore normal video, writes `$10` to HSR to make the cartridge bootstrap visible again, and returns to it.

Running the reveal from HOME `$7800` is mandatory for this arrangement. If it continued executing in cartridge chunk 4, changing HSR from `$10` to `$04` would page out the instructions currently being executed. Keeping the routine and stack in HOME chunks 3 and 5 also ensures that both remain readable and writable through every mapping used by the display sequence.

### Machine-code versus BASIC host programs

The two 6144-byte plane transfers do not change: the bitmap still ends at HOME `$4000-$57FF`, and the ECM attributes still end at HOME `$6000-$77FF`. What changes is how the routine may enter ECM, where it can execute, and what must be restored afterward.

| Concern | Full-control machine-code program, as in Elite | BASIC or BASIC AROS program |
|---|---|---|
| Caller | Cartridge bootstrap or machine-code application | A BASIC statement calls a verified machine-code helper, normally through `USR` or a resident gateway |
| Mode entry | May write DECR `$02` directly **only** after taking responsibility for the stack, dispatcher, interrupts, and everything normally stored in `$6000-$7BFF` | Normally call the TS2068 EXROM `CHNG_VID` service with mode `$02`; it relocates the BASIC program, ROM dispatcher, stack, channels, and related pointers before chunk 3 becomes display memory |
| Display-code location | Elite stores the routine at DOCK `$9900`, copies it to HOME `$7800`, and runs it there; direct mode entry does not clear `$7800` | Do not reuse Elite's `$7800` address when using `CHNG_VID`: opening the second display file clears `$6000-$7AFF`. Run the helper from protected HOME RAM outside both that range and relocated OS area `$F7C0-$FFFF`, for example a deliberately reserved high-RAM block below `$F7C0` |
| Stack | May establish a new known HOME stack, as Elite does at `$BFFF`, because it will not return to the previous environment | Preserve the BASIC/ROM stack contract. `CHNG_VID` relocates the machine stack to chunk 7; do not install a private stack over `$F7C0-$FFFF`. If a temporary stack is used, save and restore the exact caller SP before returning |
| BASIC workspace | Not applicable when the launcher abandons the interpreter and owns the machine | The normal BASIC AROS reserve/ARSBUF area begins at `$6840` and is relocated when the second display opens; reserved code/data must be addressed according to `VIDMOD`. BASIC AROS statements cannot execute while the advanced display is open |
| HSR/DECR | The application chooses its own masks and may finish by mapping the next machine-code stage | Save or shadow the caller's mapping, perform EXROM transitions from unaffected HOME RAM, restore lower HOME chunks and the BASIC-visible HSR/DECR state before `RET` |
| Registers/interrupts | Define the next program's entry contract; there may be no caller to preserve | Preserve the `USR`/gateway register contract, especially ROM-critical index registers and alternate state as required, and restore the incoming interrupt-enable policy rather than issuing an unconditional `EI` |
| Mode exit | Directly blanking the attributes and writing DECR `$00` is sufficient only because Elite deliberately discards the old OS/BASIC layout | Black the attributes, then use a verified mode-close/relocation path that restores normal memory organization and `VIDMOD=0` before returning. Merely writing DECR `$00` leaves relocated BASIC/OS state inconsistent |
| Return | Remap cartridge chunk 4 and continue into another machine-code stage | Return to BASIC only after normal video, HOME chunks 0-3, stack, dispatcher, ARSBUF, variables, HSR/DECR, and interrupts are all valid again |

For a BASIC-hosted ECM title, the safe sequence is therefore:

1. Reserve a stable machine-code region that will remain HOME and will not be moved, cleared, or covered by a cartridge chunk. Do not place the active helper at `$6840-$7AFF`; use a protected high-RAM region below `$F7C0` and keep its HSR bit clear.
2. Enter the helper through a tested `USR` address or explicit gateway. BASIC AROS has a documented USR address-classification bug, so do not assume every address is dispatched correctly.
3. Preserve the caller's registers, mapping shadows, SP relationship, and interrupt state. Make sure the BASIC area has at least `$1B00` bytes of relocation room below `RAMTOP`; the stock size check has an overflow bug when `STKEND` is already above `$E4FF`.
4. From unaffected HOME code, select EXROM chunk 0 and call verified `CHNG_VID` at EXROM `$0E8E` with A=`$02`. Restore DOCK/HOME selection afterward. This moves the BASIC area and ROM-resident dispatcher/stack state out of chunk 3 and sets `VIDMOD`.
5. Copy or decode the bitmap to HOME `$4000-$57FF`, clear the live color plane, and copy or reveal the attributes into HOME `$6000-$77FF`. Keep the helper, its data, and the relocated stack visible throughout.
6. Perform the entire hold or animation in machine code. Do not return to or execute a BASIC AROS statement while ECM is active, because the BASIC AROS support path directly assumes its normal chunk-3 bank code.
7. Clear `$6000-$77FF` to black before leaving ECM. Restore normal mode through a verified/corrected close path, restore `VIDMOD`, mappings, stack, registers, and interrupt policy, and only then return to BASIC.

The final step requires testing on the intended ROM. The stock second-display close path has documented faults, so a BASIC program that must return from ECM should use a proven correction or its own complete relocation reversal. A program that cannot guarantee this should either remain in machine code after showing the title or avoid opening ECM from BASIC. By contrast, the Elite prelude can use the smaller direct-DECR routine precisely because it is a one-way handoff into a full-control machine-code program and does not promise to restore the BASIC environment.

### Elite HOME-RAM result

After stage 2 and the helper finish, the original 42,240-byte Elite payload occupies HOME `$5B00-$FFFF`. The cartridge is unmapped for normal play, the original program runs from RAM, and the temporary startup code has relinquished its workspace. A temporary IM2 vector table in cartridge chunk 0 supports the synchronized first interrupt; Elite subsequently uses its own HOME-RAM interrupt service routine at `$FF25`.

### Spectrum and TS2068 ROM dependencies

| Purpose | Original Spectrum behavior | TS2068 cartridge behavior |
|---|---|---|
| Final tape load | Spectrum `LD-BYTES` at `$0556`, followed by the handoff at `$D07F` | No ROM load is performed. Cartridge bank copies recreate the loaded image and the exact captured Z80 state before jumping to HOME `$D07F` |
| Pixel address, interior entry | Calls Spectrum `$22B0` at six renderer sites | Calls the matching TS2068 HOME ROM entry `$2609` |
| Pixel address, next-byte entry | Calls Spectrum `$22B1` at one site | Calls TS2068 HOME ROM `$260A` |
| Checked pixel address | Calls Spectrum `$22AA` at two chart sites | Calls TS2068 HOME ROM `$2603` |
| ECM mode change | Not present in the Spectrum program | The cartridge launcher writes DECR `$02` directly and later restores `$00`; it deliberately does not call TS2068 EXROM `CHNG_VID` at `$0E8E` |
| Commander SAVE | Calls Spectrum SAVE-BYTES `$04C6` | Verified TS2068 EXROM counterpart is `$006C` |
| Commander LOAD | Calls the Elite entry into Spectrum LD-BYTES at `$0562` | Verified TS2068 EXROM counterpart is `$0108` |

The native cassette address translations are verified, but the current stable ECM build leaves the cassette patch disabled because earlier HOME-RAM gateway locations overlapped live Elite workspace. They document the required ROM translation, not a claim that the released build has completed commander LOAD/SAVE support.

## Example 2: TSVideoCodec FIFO media cartridge

[TSVideoCodec source repository](https://github.com/jon0x0/TSVideoCodec)

### Cartridge storage map

TSVideoCodec uses the opposite architecture: the hot player remains in cartridge chunk 4 and runs directly from ROM. Chunks 0, 1, 2, 3, 5, 6, and 7 form one logical 56K media stream.

| Logical media slot | Physical cartridge chunk | Stored address | Runtime source address | HSR mask while reading |
|---:|---:|---|---|---:|
| 0 | 0 | `$0000-$1FFF` | DOCK `$0000-$1FFF` | `$11` |
| 1 | 1 | `$2000-$3FFF` | DOCK `$2000-$3FFF` | `$12` |
| 2 | 2 | `$4000-$5FFF` | preloaded HOME `$C000-$DFFF` | `$10` |
| 3 | 3 | `$6000-$7FFF` | preloaded HOME `$E000-$FFFF` | `$10` |
| 4 | 5 | `$A000-$BFFF` | DOCK `$A000-$BFFF` | `$30` |
| 5 | 6 | `$C000-$DFFF` | DOCK `$C000-$DFFF` | `$50` |
| 6 | 7 | `$E000-$FFFF` | DOCK `$E000-$FFFF` | `$90` |

Every mask includes bit 4, so the player at `$8000-$9FFF` remains selected. At boot, `PRELOAD_SHADOW` selects HSR `$1C` and copies cartridge chunks 2 and 3 from `$4000-$7FFF` into underlying HOME chunks 6 and 7 at `$C000-$FFFF`. It then restores HSR `$10`, making HOME `$4000-$7FFF` writable for the two ECM display planes. The two copied media slots are later read from upper HOME RAM instead of reselecting cartridge chunks 2 and 3.

### Player, decoder, display, and work RAM map

| Address | Selected memory | Use |
|---|---|---|
| `$0000-$3FFF` | HOME except while FIFO slots 0/1 are read | HOME ROM and RAM normally; cartridge media transiently overlays one slot |
| `$4000-$57FF` | HOME | Live 6144-byte ECM bitmap plane |
| `$5800-$5FFF` | HOME | System variables include the frame counter at `$5C78` |
| `$6000-$77FF` | HOME | Live 6144-byte ECM color plane |
| `$7800-$781C` | HOME | Player variables: table pointers, scheduler state, FIFO slot, audio state, and decoder counters |
| `$781D-$7FFF` | HOME | Remaining workspace and writable stack; startup sets SP to `$7FFF` |
| `$8000-$9FFF` | DOCK chunk 4 | AROS header, player, all decoder routines, row tables, generated frame tables, audio tables, and padding; code executes directly here |
| `$A000-$BFFF` | Usually HOME | DOCK media slot 4 only while HSR `$30` is active |
| `$C000-$DFFF` | HOME or DOCK | HOME shadow of original cartridge chunk 2 with HSR `$10`; DOCK media slot 5 with HSR `$50` |
| `$E000-$FFFF` | HOME or DOCK | HOME shadow of original cartridge chunk 3 with HSR `$10`; DOCK media slot 6 with HSR `$90` |

### Exact player addresses in a representative FIFO build

The following symbols are from `dino_full_6fps_1800/cartridge_fifo_fast`. They are useful for debugging this exact build; generated tables and selected codec options can move them in another build.

| Routine/table | Address | Execution role |
|---|---:|---|
| AROS `START` | `$8008` | Initializes audio, preloads shadow media, enters ECM, and starts playback |
| `PRELOAD_SHADOW` | `$80C0` | Copies cartridge chunks 2/3 to HOME `$C000-$FFFF` |
| `COPY_FRAME` | `$80D4` | Dispatches keyframe or delta record types |
| `COPY_PACK_KEY` | `$8128` | Decodes the initial PackBits bitmap and color-plane keyframe before delta playback |
| `DECODE_PACKBITS` | `$8159` | Resident PackBits decoder |
| `COPY_FIFO_HYBRID` | `$81CF` | Starts a FIFO delta record |
| `FIFO_SELECT` | `$81EA` | Converts logical slot number to an HSR mask |
| `FIFO_NEXT` | `$8201` | Advances to the next source slot and resets its source address |
| `DECODE_FIFO_HYBRID_PLANE` | `$822F` | Applies the command-aware XOR/mask delta stream directly to a HOME display plane |
| `COPY_DONE` | `$83D6` | Restores HSR `$10`, leaving only code chunk 4 selected |
| `FIFO_MASKS` | `$83DE` | Seven-byte slot-to-HSR lookup table |
| `FRAME_TABLE_PTRS` | `$8565` | Build-generated pointers to each frame record |

The delta decoder does not get copied to RAM: it executes directly from DOCK chunk 4. It reads compressed bytes from the currently selected FIFO slot and modifies the live HOME bitmap at `$4000` and color plane at `$6000`. Because HSR never selects cartridge chunks 2 or 3 during ordinary display updates, both HOME display planes stay CPU-writable. The SCLD continues reading those HOME planes regardless of which other cartridge source chunk the CPU is reading.

### Where the media is and how it is consumed

TSVideoCodec begins video playback by reconstructing a complete ECM keyframe. In the representative 30-frame build, this 12,288-byte first frame—6144 bitmap bytes plus 6144 color bytes—compresses to 4,363 bytes with PackBits. `COPY_PACK_KEY` decompresses both planes into the live HOME display, establishing the baseline image before any delta is applied. The keyframe's bitmap stream starts in slot 0 at `$0000`, its color stream at `$08C1`, and the first subsequent FIFO delta record at `$110B`. Generated frame tables store each later update's starting logical slot and source address. For example, frame 12 begins in slot 1 at `$20D8`, frame 21 begins in preloaded slot 2 at HOME `$C149`, and frame 29 begins in slot 4 at DOCK `$A1FA`.

The FIFO packer places records across the ordered slots rather than forcing each record into one 8K bank. A `$C1` command advances at a clean decoder-command boundary; `$C2,0` consumes one padding byte and then advances. The reader changes HSR, resets the source pointer to the next slot's base, and continues decoding the same frame. This build carries 39,247 bytes of update payload with only 10 FIFO boundary/padding bytes; the physical BIN is still an exact 64K image with unused media capacity padded.

### ROM and hardware dependencies

TSVideoCodec is original TS2068 software rather than a Spectrum ROM-dependent port, so it has no Spectrum-to-TS2068 ROM call translation table. The player controls cartridge banking and ECM directly through HSR port `$F4` and DECR port `$FF`, and optional sound through the AY ports `$F5/$F6`. With HSR restored to `$10`, HOME chunk 0 remains visible, so normal IM1 interrupts can enter the TS2068 HOME ROM handler at `$0038`; the scheduler observes the HOME system frame counter at `$5C78`.

## What the two examples demonstrate

| Design question | Elite | TSVideoCodec |
|---|---|---|
| Main execution location | Copied to HOME `$5B00-$FFFF` | Directly from DOCK `$8000-$9FFF` |
| Why | Compatibility with writable, protected Spectrum code and exact loader state | Fast resident decoder with immutable code |
| Display strategy | Temporary RAM-resident prelude copies/reveals cartridge artwork | Permanent HOME ECM display updated by a cartridge-resident decoder |
| Data banking | Deterministic block copies during startup | Repeated FIFO slot selection during playback |
| Image and chunks 2/3 | Title bitmap source in chunk 4; ECM color/attribute source in chunk 2; Elite payload in chunk 3 | Both media chunks are preloaded to upper HOME RAM so live display chunks remain HOME |
| ROM strategy | Patch or replace verified Spectrum ROM dependencies | Avoid Spectrum ROM calls; use TS2068 hardware and normal HOME interrupt support |

Together these maps show that there is no single required cartridge architecture. The safe design follows from the live location of the program counter, stack, interrupt path, writable destination, display files, and ROM services at every HSR transition.
