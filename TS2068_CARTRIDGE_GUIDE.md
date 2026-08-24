# Developing Cartridge Software for the Timex Sinclair 2068

See the [glossary](TS2068_CARTRIDGE_GLOSSARY.md) for the complete definitions of acronyms and specialized terms used here.

## Introduction

The Timex Sinclair 2068 has an unusually capable memory system for an eight-bit computer. A cartridge is not limited to replacing one small read-only memory (ROM) window. The machine divides its entire 64K Z80 central processing unit (CPU) address space into eight independently selectable 8K chunks, allowing external cartridge memory to replace selected portions of the internal memory map.

That flexibility makes it possible to execute software directly from cartridge, combine cartridge code with internal RAM, store a complete 64K of code and media, or use the cartridge as a fast source for a program copied into RAM. It also introduces hazards: a single bank-switch can hide the instruction being executed, the stack, the interrupt vector, the display memory, or the ROM routine the program expects to call.

The safest way to think about TS2068 cartridge programming is as memory-map design. At every point in the program, know which physical memory is visible at each address and why.

## The three memory sources

The CPU can encounter three memory sources:

- **HOME** is the TS2068's internal ROM and random-access memory (RAM).
- **DOCK**, called the **Dock (Cartridge) Bank** by the TS2068 Technical Reference Manual, is the external cartridge memory bank. It can supply up to 64K as eight fixed 8K chunks. Dock is a name, not an acronym.
- **Extension ROM ([EXROM](TS2068_CARTRIDGE_GLOSSARY.md#exrom "Extension ROM"))** is the supplementary ROM bank. The factory machine populates 8K, while a 16K implementation can occupy its first two chunks.

The Z80 still sees only one 64K address space. Hardware selects which source responds within each 8K address range.

Two output ports control this:

- Port `$F4`, the **Horizontal Select Register ([HSR](TS2068_CARTRIDGE_GLOSSARY.md#hsr "Horizontal Select Register"))**, selects HOME or external memory independently for each 8K chunk.
- Port `$FF`, the **Display Enhancement Control Register ([DECR](TS2068_CARTRIDGE_GLOSSARY.md#decr "Display Enhancement Control Register"))**, selects whether all HSR-selected external chunks come from DOCK or EXROM through bit 7. Its other bits also control video mode and interrupt behavior, so they must be preserved deliberately.

### What EXROM is

The stock TS2068 contains two system ROM chips. U16 is the 16K HOME ROM at `$0000-$3FFF`. U20 is the factory 8K **Extension ROM**, normally called EXROM. It supplements HOME ROM with services that did not fit in the main ROM:

- final system-initialization code;
- cassette read, write, LOAD, and SAVE support;
- the `CHNG_VID` video-mode service;
- bank-switching support;
- the source and jump table for the function dispatcher copied into HOME RAM during startup;
- compatible reset, error, and interrupt entry paths for periods when EXROM covers the lower ROM.

The stock U20 image occupies EXROM `$0000-$1FFF`, corresponding to chunk 0. Do not confuse that populated-chip size with the full capability of the EXROM design. Timex's internal planning notes recognized support for a 16K Extension ROM, and a 16K implementation spans EXROM chunks 0 and 1 at `$0000-$3FFF`; HSR=`$01` selects its lower 8K, HSR=`$02` its upper 8K, and HSR=`$03` both. Modified 16K EXROM implementations provide a practical example. Whether the second chunk exists depends on the installed EXROM hardware and image—the factory U20 does not supply it.

EXROM is still not a second cartridge, not a Language ROM-Oriented Software (LROS) cartridge, and not an automatic extra 64K application ROM. Although the architecture describes DOCK and EXROM as alternative external banks under the same HSR mask, do not assume meaningful bytes beyond the implemented EXROM range. See [David Anderson's TS2068 Reference Library](https://github.com/timex-sinclair-projects/TS2068-Ref-Library) for the stock ROM material, technical documentation, and expanded-EXROM work.

To expose the stock EXROM, set DECR bit 7 and set HSR bit 0, normally giving HSR=`$01`. This hides HOME ROM `$0000-$1FFF` from the CPU and places EXROM there. DOCK and EXROM are globally mutually exclusive: setting DECR bit 7 makes every selected HSR chunk request EXROM instead of the cartridge. A routine executing from selected DOCK must therefore not flip DECR directly. Enter a gateway in unaffected HOME RAM, disable interrupts, set HSR=`$00`, select EXROM in DECR, select chunk 0, and call the documented entry. Reverse that sequence on return.

EXROM services often expect HOME system variables, the operating-system stack, and RAM dispatcher state. Prefer documented interfaces and verify the ROM revision and entry contract. In particular, the TS2068 technical manual supplies a HOME-RAM interface for direct cassette and `CHNG_VID` calls because those services are not all safe through the general dispatcher.

## The fixed chunk map

| Chunk | Address range | HSR bit/mask | HOME content normally hidden from the CPU when external is selected |
|---:|---|---:|---|
| 0 | `$0000-$1FFF` | bit 0 / `$01` | lower HOME ROM, reset entry, and Z80 Interrupt Mode 1 ([IM1](TS2068_CARTRIDGE_GLOSSARY.md#im1 "Z80 Interrupt Mode 1")) vector at `$0038` |
| 1 | `$2000-$3FFF` | bit 1 / `$02` | upper HOME ROM |
| 2 | `$4000-$5FFF` | bit 2 / `$04` | primary screen and HOME RAM/system variables |
| 3 | `$6000-$7FFF` | bit 3 / `$08` | HOME RAM, operating-system (OS) dispatcher/stack area, second display plane |
| 4 | `$8000-$9FFF` | bit 4 / `$10` | HOME RAM; conventional cartridge header and entry area |
| 5 | `$A000-$BFFF` | bit 5 / `$20` | HOME RAM |
| 6 | `$C000-$DFFF` | bit 6 / `$40` | HOME RAM |
| 7 | `$E000-$FFFF` | bit 7 / `$80` | HOME RAM |

The mapping is fixed. Cartridge chunk 0 always maps to `$0000-$1FFF`, chunk 4 always maps to `$8000-$9FFF`, and so forth. HSR is an eight-bit selection mask, not a page number.

For a flat 64K cartridge image, the file offsets correspond directly to these ranges. Fuse [DCK](TS2068_CARTRIDGE_GLOSSARY.md#dck "Fuse cartridge-image format") (`.dck`) cartridge-image files are containers with a header and per-chunk descriptors, so their internal file offsets must be parsed rather than treated as CPU addresses.

## What bank switching actually does

Suppose code is running from cartridge chunk 4 with HSR=`$10`. The CPU sees cartridge memory at `$8000-$9FFF`, while every other address comes from HOME.

Writing HSR=`$30` sets bits 4 and 5. Cartridge chunk 4 remains visible, so execution continues. Cartridge chunk 5 now replaces HOME RAM at `$A000-$BFFF`. The HOME RAM has not moved and has not been erased; it is merely hidden. Restoring HSR=`$10` reveals that RAM again with its old contents.

The new selection applies to the next memory access after the output instruction. This includes instruction fetches, data reads, writes, stack accesses, and interrupt-vector fetches. Hardware provides no safety check.

A typical operation looks like this:

```asm
                DI
                LD      A,$30          ; DOCK chunks 4 and 5
                LD      BC,$00F4
                OUT     (C),A
                LD      HL,$A000       ; cartridge chunk 5
                LD      DE,$C000       ; HOME chunk 6 remains visible
                LD      BC,$2000
                LDIR
                LD      A,$10          ; keep code chunk, hide data chunk
                LD      BC,$00F4
                OUT     (C),A
```

This copies 8K from cartridge chunk 5 to internal RAM chunk 6 while the program continues executing from cartridge chunk 4.

## Direct execution from cartridge

A machine-code Application ROM-Oriented Software ([AROS](TS2068_CARTRIDGE_GLOSSARY.md#aros "Application ROM-Oriented Software")) program normally has an eight-byte header at cartridge `$8000-$8007` and begins at `$8008` in chunk 4. Code can remain in ROM and execute there for the life of the program.

Direct execution works well for immutable code, lookup tables, and media readers. It does not support self-modifying code, writable variables, or a stack in read-only cartridge space. Any chunk containing the current instruction must remain selected until control has safely moved elsewhere.

Code can also span multiple cartridge chunks. Because each chunk occupies a different address range, chunks 4 and 5 can both remain selected while code calls from one into the other. A RAM gateway is needed only when a transition would hide the currently executing code, reveal HOME RAM underneath it, or switch globally between DOCK and EXROM.

## Combining cartridge storage with HOME RAM

Selective mapping is the normal operating mode. Keep zeroes in HSR for HOME regions needed as writable RAM or ROM, and ones for the cartridge regions currently required.

A common arrangement is:

- chunks 0-3 HOME for ROM, display, system state, and stack;
- chunk 4 DOCK for resident cartridge code;
- chunks 5-7 selected temporarily for code or data and restored to HOME for working RAM.

To copy from cartridge, the source and destination must occupy different visible chunks. Cartridge chunk 6 and HOME chunk 6 cannot be visible at the same time because both occupy `$C000-$DFFF`. Copy through a temporary HOME chunk or run a carefully placed RAM routine using a non-conflicting source and destination.

## A practical way to use all 64K

All eight cartridge chunks can contain useful bytes, but a robust program normally accesses them selectively.

Use chunk 4 for:

- the AROS header and bootstrap;
- the resident player, decompressor, or dispatcher;
- bank-selection routines;
- indexes and frequently used tables;
- remaining immutable data in unused space.

Use chunks 0, 1, 2, 3, 5, 6, and 7 for pageable payload. Keep chunk 4 selected while the program is executing there and add one data-chunk bit to HSR as needed.

Chunks 2 and 3 overlap the CPU's access to the display region. Their cartridge data can be copied into upper HOME RAM during startup, then chunks 2 and 3 can be returned to HOME so drawing proceeds normally. This approach was useful in the [TSVideoCodec](https://github.com/jon0x0/TSVideoCodec) architecture: media occupied all seven non-code chunks, while the resident player lived in chunk 4.

HSR=`$FF` technically exposes all 64K of cartridge memory at once. On a read-only cartridge this also removes all writable HOME RAM, the HOME ROM, the normal stack, and the standard interrupt handler. It is rarely a useful steady-state mapping.

## Display behavior

The 16K video RAM is physically in HOME chunks 2 and 3, but the CPU and the Standard Cell Logic Device ([SCLD](TS2068_CARTRIDGE_GLOSSARY.md#scld "Standard Cell Logic Device")) display hardware do not use the same selection path. HSR controls the CPU's view of those addresses. The SCLD continues to fetch pixels and attributes from HOME screen RAM independently, according to the current video mode.

Consider code running from cartridge chunk 4 with HSR=`$14`. Bit 4 keeps the code visible, and bit 2 maps cartridge chunk 2 over `$4000-$5FFF`:

- A CPU read from `$4000` returns the byte in cartridge chunk 2.
- A CPU write to `$4000` targets external chunk 2 and normally has no effect when it is ROM.
- At the same time, the SCLD fetches the displayed primary-screen byte from HOME RAM at `$4000`.

The old picture therefore remains visible even though CPU reads in its address range return cartridge data. The CPU cannot inspect or modify the HOME screen underneath the overlay. Clear HSR bit 2 before drawing to the primary display. Likewise, clear HSR bit 3 before CPU access to the second display file in HOME chunk 3.

This can be useful for brief media transfers: show the old frame, map cartridge data over the display address range, copy or decode it elsewhere, restore HOME mapping, then draw the next frame.

## Advanced example: a raw or compressed TS2068 title-screen prelude

A cartridge can show a native TS2068 title image before either an original cartridge application or a converted Spectrum program starts. Extended Color Mode is a strong example because it uses a 6144-byte pixel plane and a 6144-byte color plane, for 12K of uncompressed artwork.

The browser-based [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) can author these planes from ordinary source artwork. Select **Timex Extended Color (256×192, 8×1 attrs)**, adjust the image, palette, and dithering while previewing the result, then export binary data or a TAP. Its ECM TAP contains a 6144-byte `ecm-pix` CODE block for `$4000` and a 6144-byte `ecm-atr` CODE block for `$6000`; the **Attributes first in .TAP** option is useful for tape/viewer workflows that want colors loaded before the visible pixels.

For a cartridge, treat those blocks as artwork inputs rather than a finished memory map. Verify both lengths and hashes, extract the pixel and attribute bytes, and place each plane wherever the cartridge's bank layout allows; the startup routine later copies them to HOME `$4000-$57FF` and `$6000-$77FF`. The attributes-first option controls TAP block order only—it does not require the attribute plane to precede the bitmap in cartridge ROM. Retro Pixel Converter creates the display data, not the AROS header, bank-switching code, ECM entry/exit code, reveal animation, or final DCK/BIN package.

The proven Elite ECM artwork was generated in Retro Pixel Converter using **Sierra Lite** dithering. Its launcher stores both planes raw in cartridge chunks 4 and 2, copies pixels into HOME `$4000-$57FF`, reveals the color plane into HOME `$6000-$77FF` with a center curtain, holds the result for six seconds, clears the colors to black, returns to normal video mode, and continues into Elite.

That direct mode-switching pattern is specific to a full-control machine-code handoff. A BASIC-hosted routine must protect the interpreter's relocatable program, ARSBUF, dispatcher, and stack; normally it enters through EXROM `CHNG_VID`, runs the complete display/hold/exit inside machine code, and restores normal mode and memory organization before returning to BASIC. See the [machine-code versus BASIC ECM procedure](TS2068_CARTRIDGE_EXAMPLES.md#machine-code-versus-basic-host-programs) for the complete comparison and stock-ROM cautions.

Compression is not required. Prefer raw planes when the 12K fits comfortably: the launcher is smaller, startup is faster, and there is less code and state to validate. Apply [PackBits](TS2068_CARTRIDGE_GLOSSARY.md#packbits "PackBits run-length compression") only when recovering cartridge space is worth the decoder, metadata, and decompression time—for example, when adding more program code or media, or when a plane must fit a particular bank layout.

Classic PackBits uses one control byte per run:

| Control byte | Meaning |
|---:|---|
| `0-127` | copy the following `control+1` literal bytes |
| `128` | no operation; normally omit it |
| `129-255` | repeat the following byte `257-control` times |

If compression is useful, pack the pixel and color streams independently and store a small descriptor for each: codec, starting cartridge chunk/mask, source address, compressed length, and expected output length. PackBits can expand slightly on noisy data, so let the build choose raw storage unless compression produces a meaningful saving.

A safe startup sequence is:

1. Run the bootstrap and decoder from a cartridge chunk that remains selected, normally chunk 4.
2. Put the stack in a writable HOME chunk that will not be selected as compressed source during the decode.
3. Keep HSR bits 2 and 3 clear while writing the primary and secondary HOME display files.
4. Select the cartridge chunk containing the compressed pixels, decode exactly 6144 output bytes to HOME `$4000-$57FF`, and restore the normal HSR mask.
5. For an immediate reveal, decode the 6144 color bytes directly to HOME `$6000-$77FF`. For a curtain reveal, decode them first into an uncovered HOME buffer such as `$C000-$D7FF`, clear `$6000-$77FF` to black, enter Extended Color Mode, and copy buffer columns outward from the center.
6. Hold the completed title for the desired time.
7. Clear the Extended Color Mode color plane to black before changing video modes, clear or prepare the normal screen, restore the saved DECR/HSR state, and enter the main program.

Do not store the compressed source over the same HOME chunk being written unless using an intermediate buffer. For example, with cartridge chunk 2 selected, the CPU can read compressed bytes at `$4000`, and the SCLD can still display HOME screen RAM, but CPU writes at `$4000` cannot reach that hidden HOME screen. Store the source in chunk 4/5/6, or decode chunk 2 into a different HOME buffer and copy after restoring HOME chunk 2.

A bank-aware byte reader can make a compressed stream span several 8K chunks. Switch only between PackBits commands, or guarantee that the reader can fetch a control byte and its associated data across a boundary. Keep the executing-code and stack chunks valid in every generated HSR mask.

At build time, immediately decompress each generated stream and compare its length and hash with the source plane. At runtime, stop on the exact expected output count rather than relying on an in-band end marker. Emulator validation should compare the live HOME display planes byte-for-byte with the source artwork before the reveal or handoff is accepted.

## Advanced example: FIFO packing across all media banks

Keeping each compressed frame, level, or sound inside one 8K chunk makes the reader simple, but it creates two limits: no record can exceed 8192 bytes, and unusable gaps accumulate at bank tails. TSVideoCodec's command-aware [FIFO](TS2068_CARTRIDGE_GLOSSARY.md#fifo "first-in, first-out logical stream") mode removes both restrictions by treating the seven non-code chunks as one ordered 56K byte stream.

Playback starts with a full 12,288-byte ECM keyframe—the first video frame—not with a delta. PackBits compresses its bitmap and color planes independently, and the resident player decompresses both into HOME `$4000-$57FF` and `$6000-$77FF`. That complete image becomes the baseline; subsequent records are FIFO-packed delta updates applied against the already displayed frame.

Chunk 4 remains selected as the resident player. At boot, cartridge chunks 2 and 3 are copied together from `$4000-$7FFF` into HOME `$C000-$FFFF`, after which HSR is restored to `$10`. The logical FIFO slots are then:

| FIFO slot | Original cartridge chunk | Runtime source address | HSR mask while reading |
|---:|---:|---:|---:|
| 0 | 0 | `$0000` | `$11` |
| 1 | 1 | `$2000` | `$12` |
| 2 | 2, preloaded to HOME chunk 6 | `$C000` | `$10` |
| 3 | 3, preloaded to HOME chunk 7 | `$E000` | `$10` |
| 4 | 5 | `$A000` | `$30` |
| 5 | 6 | `$C000` | `$50` |
| 6 | 7 | `$E000` | `$90` |

Every record descriptor stores its starting FIFO slot and source address. Ordinary encoded bytes are read directly; the decoder does not pay for a boundary test on every byte. Instead, the packer inserts reserved commands only where the codec expects a new command:

| Boundary command | Use |
|---|---|
| `$C1` | Fill the final one byte of a bank, select the next FIFO slot, and continue there. |
| `$C2,0` | Fill the final two bytes; the decoder ignores the pad byte and selects the next slot. |

The packer must understand the encoded format. It may split a literal run into a shorter literal that fills the bank and a continuation in the next slot. If a sparse mask command cannot fit, it can be converted to an equivalent eight-byte literal and split safely. It must never cut an arbitrary control sequence in half. Records such as audio blocks that require alignment or bank-local access can retain separate placement rules.

After a record finishes, restore HSR=`$10` so only resident chunk 4 overlays HOME. Build validation should reconstruct every FIFO record from its recorded start, interpret every boundary command, compare decoded output byte-for-byte with the source, reject stream overflow beyond slot 6, and verify the final flat image is exactly 65536 bytes.

This layout supplies 56K of tightly packed payload plus the 8K resident code/table chunk. It therefore makes the entire cartridge useful, but does not provide 65536 arbitrary data bytes. To approach that payload figure, copy the decoder/player into HOME RAM after boot and describe free ranges in chunk 4 as additional FIFO segments. The AROS header, bootstrap, and any code retained in cartridge remain storage overhead; only an external loader or deliberately dual-purpose bytes could remove that fundamental tradeoff.

## Interrupts and stack safety

Interrupts are a frequent source of apparently mysterious crashes. In IM1 the CPU jumps to `$0038`. If chunk 0 is mapped to cartridge, `$0038` no longer refers to the HOME ROM handler unless the cartridge deliberately provides a compatible routine there.

The stack presents the same problem. If SP is in chunk 3 and cartridge chunk 3 is selected, calls, returns, pushes, pops, and interrupt stacking access the external chunk rather than HOME RAM. Writes to ROM do not create a valid stack.

Before changing banks:

1. Know where the program counter (PC), stack pointer (SP), interrupt-service routine ([ISR](TS2068_CARTRIDGE_GLOSSARY.md#isr "interrupt-service routine")), and return address are located.
2. Disable interrupts during unsafe intermediate states.
3. Keep the executing-code and stack chunks visible and writable as required.
4. Preserve the previous interrupt state instead of automatically issuing `EI` afterward.

## DOCK and EXROM transitions

DECR bit 7 globally changes the source requested by every set HSR bit. Flipping it while executing from selected DOCK code removes the cartridge immediately. In the stock machine only EXROM chunk 0 contains the factory 8K ROM, so a fetch from another selected chunk is not a valid continuation path. A verified 16K EXROM may also supply chunk 1, but that does not make it safe to switch away from executing DOCK code.

Perform the transition from unaffected HOME RAM:

1. Save the HSR, DECR, registers, and interrupt state.
2. Set HSR to zero so all memory is HOME.
3. Change DECR bit 7.
4. Select the required EXROM chunk with HSR—normally chunk 0 (`$01`) for a stock service; use `$02` or `$03` only for a verified 16K EXROM implementation that supplies chunk 1.
5. Call the verified EXROM routine.
6. Set HSR to zero again.
7. Restore DOCK selection, the old HSR mask, and interrupt state.

Never assume a Spectrum ROM address has the same function in the TS2068 HOME ROM or EXROM. Verify the correct entry and its required machine state.

## BASIC programs on cartridge

The TS2068 supports AROS BASIC programs stored in tokenized form beginning at `$8008`. BASIC variables and changing state remain in HOME RAM. Cartridge BASIC works best when the program is designed for the environment rather than treated as an ordinary text file copied verbatim into ROM.

Keep the documented lower chunks HOME for a portable BASIC AROS. Account for TS2068 ROM bugs and limitations, including reserve-area behavior and routines that make assumptions about program addresses. Machine-code helpers called with `USR` must return with the expected HOME mapping restored.

## BASIC versus machine-code cartridges: dos and don'ts

Choose BASIC AROS when the program benefits from the TS2068 BASIC interpreter, tokenized statements, and ROM-managed program flow. Choose machine-code AROS when execution speed, exact timing, custom interrupts, direct hardware control, extensive banking, or a Spectrum compatibility layer matters more.

| Concern | BASIC AROS cartridge | Machine-code AROS cartridge |
|---|---|---|
| Header | Language byte `1`; entry field identifies the first BASIC line | Language byte `2`; entry field is the executable Z80 address, commonly `$8008` |
| What executes | The ROM copies a cartridge line into the RAM Application ROM System Buffer (ARSBUF) and interprets it | The CPU fetches instructions directly from selected cartridge ROM, or from HOME RAM after an explicit copy |
| Writable state | Variables, arrays, strings, and changing state belong in HOME RAM | Allocate every variable, buffer, stack, and self-modifying routine explicitly in HOME RAM |
| Banking | Preserve the ROM's lower-memory, stack, and dispatcher assumptions; keep banking inside small, verified helpers | Direct HSR/DECR control is appropriate, but the program owns every mapping, stack, interrupt, and return-path consequence |
| ROM use | Prefer supported BASIC statements and documented AROS behavior | Verify every HOME-ROM or EXROM entry and calling convention; Spectrum ROM addresses are not automatically portable |
| Best fit | Menus, utilities, educational software, and BASIC-led programs with modest machine-code helpers | Games, codecs, animation, protected ports, high-performance code, and full-control launchers |

### BASIC cartridge dos

- Store tokenized program lines, not ASCII source. Begin normally at `$8008`, use the RAM line-record format, terminate each line with `$0D`, and place a high-bit end marker after the final line.
- Keep startup chunk-specification bits 0-3 set so HOME ROM, screen/system variables, and OS workspace remain available.
- Let BASIC create variables and arrays in HOME RAM. Treat cartridge bytes as immutable program text and data unless the hardware really supplies cartridge RAM.
- Prefer sensible multi-statement lines because the ROM copies a whole cartridge line into ARSBUF before interpreting it.
- Reserve enough HOME memory for any machine-code workspace and for ARSBUF. Verify the actual reserve placement and limits.
- Keep `USR` helpers small and explicit. Give each one a documented entry/exit register contract and restore the BASIC-visible HSR, DECR, stack, interrupt, and display state before `RET`.
- Test program flow, `READ`/`DATA`, loops, errors, `USR`, SAVE/LOAD, and return to BASIC under the actual TS2068 ROM revision and on hardware.

### BASIC cartridge don'ts

- Do not copy an ordinary textual or tokenized Spectrum BASIC program into cartridge ROM and assume it has become a valid TS2068 BASIC AROS. Rebuild its header, line layout, memory assumptions, ROM dependencies, and machine-code calls deliberately.
- Do not pre-store changing BASIC variables in cartridge ROM and expect the interpreter to update them there.
- Do not use extremely long `DATA` statements casually; the complete statement is copied even when one item is read.
- Do not use user-defined BASIC functions in a cartridge program without replacing the unsupported definition-search behavior.
- Do not execute BASIC AROS statements while the advanced second display file is open; the ROM's BASIC AROS banking path assumes its normal chunk-3 workspace.
- Do not assume every `USR` target is classified correctly by the stock ROM. Test the address or call through a verified gateway.
- Do not let a `USR` routine return with lower HOME chunks, the ROM interrupt vector, ARSBUF, stack, or dispatcher covered by DOCK/EXROM.

### Machine-code cartridge dos

- Establish SP, interrupt mode, interrupt enable state, HSR/DECR shadows, video mode, keyboard state, and RAM allocation at entry instead of relying on undocumented residue.
- Keep the chunk containing PC selected. Execute a transition from unaffected HOME RAM whenever it would page out the current routine or switch globally between DOCK and EXROM.
- Put the stack, variables, decompression destinations, and other writable objects in uncovered HOME RAM or real cartridge RAM.
- Copy protected, self-modifying, or RAM-assuming Spectrum software into HOME RAM before execution and reproduce any loader-created registers or memory state it requires.
- Keep bank-switching code separate from application compatibility patches and document every runtime mask.
- Provide a valid interrupt path for every mapping: keep HOME chunk 0 visible for normal IM1, disable interrupts temporarily, or install a proven alternative handler.
- Use direct cartridge execution for immutable code and tables, and pageable chunks for media. Validate source and destination visibility before every transfer.

### Machine-code cartridge don'ts

- Do not place SP, variables, or self-modifying instructions in read-only cartridge ROM; failed writes may be silent.
- Do not select a cartridge source over the HOME destination being written. An `LDIR` can complete while the hidden RAM remains unchanged.
- Do not page out the instruction following `OUT ($F4),A`, its return address, or an interrupt vector that can be taken immediately afterward.
- Do not call Spectrum ROM addresses on the TS2068 by assumption. Relocate to verified HOME-ROM/EXROM entries or supply wrappers.
- Do not change DECR bit 7 from code that exists only in DOCK; selecting EXROM globally removes that code. Use a HOME-RAM gateway.
- Do not treat HSR=`$FF` as an ordinary full-64K operating state on a ROM cartridge; it hides HOME ROM, RAM, display access, stack, and the normal interrupt handler from the CPU.
- Do not assume a DCK RAM descriptor makes a physical ROM cartridge writable.

The dividing line is responsibility: BASIC AROS retains substantial ROM management and must respect the interpreter's workspace and limitations; machine-code AROS gains direct control but must define and verify the entire machine state itself.

## Converting existing Spectrum software

A Spectrum-to-TS2068 cartridge conversion often uses a copy-and-run approach:

1. Store the original program and loading media in cartridge chunks.
2. Run a small TS2068 cartridge bootstrap.
3. Copy the program into its original HOME RAM addresses.
4. Reproduce important Z80 registers and loader-created state.
5. Remove cartridge overlays and enter the original program.
6. Replace Spectrum ROM dependencies, joystick assumptions, cassette routines, video setup, and other machine-specific behavior as required.

Deterministic emulator tracing is especially useful. Break at known handoff addresses, capture the exact register and memory state of the original program, reproduce it in the cartridge build, and trace the first instruction where the TS2068 execution diverges.

## DCK versus physical cartridge images

A DCK file describes each 8K chunk as absent, uninitialized RAM, ROM, or initialized RAM. Those descriptors allow Fuse to model configurations that a physical ROM cartridge cannot provide.

A physical 64K image is normally eight consecutive 8K regions. Its actual behavior depends on the board's address decoding, capacity, and write circuitry. A DCK RAM descriptor does not make a PicoROM or erasable programmable read-only memory (EPROM) device writable.

Build both formats reproducibly and verify hashes, chunk order, erased-byte fill, and the target programmer's expected binary layout.

## Recommended development workflow

See the [utilities guide](TS2068_CARTRIDGE_UTILITIES.md) for complete commands and examples for the bundled DCK packer, inspector, Fuse debugger launcher, Python module, and assembly templates.

1. Inventory the program, assets, ROM calls, I/O ports, self-modifying code, stack, and interrupt behavior.
2. Draw the intended HOME/DOCK/EXROM chunk map for startup and every runtime phase.
3. Choose direct execution, copy-and-run, resident-player, or BASIC AROS architecture.
4. Implement bank routines separately from application compatibility patches.
5. Generate DCK and flat binaries from scripts.
6. Inspect descriptors, headers, entry addresses, and per-chunk hashes.
7. Run Fuse under the TS2068 model with scripted debugger commands and deterministic input.
8. Capture exact state at important handoffs and find the first divergence from a known-good run.
9. Test display, keyboard, joystick, sound, interrupts, cassette operations, and reset paths.
10. Validate the same flat image on physical hardware.

## Final rule of thumb

Every bank switch should answer four questions before it is written: Where will the next instruction come from? Where is the stack? What happens if an interrupt arrives? Which physical memory receives each read and write? If those answers are explicit, TS2068 cartridge programming becomes predictable rather than mysterious.
