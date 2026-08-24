# TS2068 Cartridge Development Glossary

This glossary collects the cartridge, memory, display, file-format, and Z80 terms used throughout this library.

Core acronyms at a glance: **HSR** means Horizontal Select Register; **DECR** means Display Enhancement Control Register; **SCLD** means Standard Cell Logic Device; **AROS** means Application ROM-Oriented Software; **LROS** means Language ROM-Oriented Software; and **EXROM** means Extension ROM. **DCK** is treated as Fuse's conventional cartridge-format name and `.dck` extension because the available documentation does not establish a longer official expansion.

## AROS

**Application ROM-Oriented Software.** A TS2068 cartridge application supported by the system ROM. An AROS may contain tokenized BASIC or Z80 machine code. Its normal header is at cartridge `$8000-$8007` in chunk 4, with the program or entry point commonly beginning at `$8008`.

## Bank

A physical memory source. The important TS2068 banks are internal HOME, cartridge DOCK, and Extension ROM (EXROM). HSR chooses HOME or external independently by chunk; DECR bit 7 chooses which external bank supplies selected chunks.

## BIN

**Binary image.** In this library, a flat physical-cartridge file. A 64K BIN normally contains eight consecutive 8K chunks in CPU-address order, without the DCK header or descriptors.

## Chunk

One fixed 8K section of the Z80 address space. The TS2068 has chunks 0 through 7. Chunk N always occupies addresses `N*$2000` through `N*$2000+$1FFF`.

## CPU

**Central processing unit.** The Z80 processor. HSR controls whether the CPU sees HOME or external memory in each 8K address range. This selection does not redirect the SCLD's independent display fetches from HOME video RAM.

## DCK

**Fuse cartridge-image format.** DCK is the conventional name and `.dck` extension for Fuse's Timex cartridge container. Treat DCK as the format name; the available TS2068 documentation does not establish a longer official expansion comparable to HSR or DECR. A DCK begins with a bank byte and eight chunk descriptors, followed by payloads for stored chunks. It is not a flat physical-ROM image.

## DECR

**Display Enhancement Control Register.** The write-only TS2068 control register at port `$FF`. Bits 0-2 select video behavior, bit 6 inhibits the periodic interrupt, and bit 7 selects the source for HSR-selected external chunks: clear for DOCK, set for EXROM. Maintain a software shadow and preserve unrelated bits.

## DOCK

The **Dock (Cartridge) Bank**, the name used by the *Timex Sinclair 2068 Technical Reference Manual* for the external memory bank supplied through the cartridge connector. It provides up to 64K of addressable cartridge memory, arranged as eight fixed 8K chunks corresponding to the Z80's eight address-space chunks. HSR selects which chunks replace the same-address HOME chunks, while DECR bit 7 must be clear to choose Dock rather than EXROM. **Dock is a bank name, not an acronym requiring expansion.** See the [Technical Reference Manual, section 1.1.1, PDF page 7](https://github.com/timex-sinclair-projects/TS2068-Ref-Library/blob/main/docs/Timex%20Sinclair%202068%20Technical%20Manual%20%28best%29.pdf).

## ECM

**Extended Color Mode.** A TS2068 display mode using one 8K display file for pixels and the corresponding bytes in the second HOME display file for color information. It is selected through DECR video-control bits.

## EPROM

**Erasable programmable read-only memory.** A nonvolatile memory technology used by some physical cartridges. Normal CPU writes do not modify an EPROM during program execution.

## EXROM

**Extension ROM.** The TS2068's supplementary ROM bank. The production machine's U20 chip supplies an 8K stock EXROM at `$0000-$1FFF` (chunk 0), containing cassette I/O, video-mode services, final initialization, bank-switching support, and the source/jump tables for the RAM-resident function dispatcher. Timex's internal planning recognized 16K EXROM support; a 16K implementation spans chunks 0 and 1 at `$0000-$3FFF` and can be selected together with HSR=`$03`. Do not infer that a factory 8K U20 contains chunk 1, or that the EXROM bank is another cartridge or an extra 64K payload area. EXROM and cartridge DOCK use the same HSR mask and are selected globally by DECR bit 7; select stock chunk-0 services with HSR=`$01`, normally from a HOME-RAM gateway.

## FIFO

**First in, first out.** In the cartridge examples, this means a logical sequential stream implemented by a build-time packer and a bank-aware decoder, not a hardware FIFO device. Records are stored across an ordered list of cartridge or preloaded HOME-RAM segments. Explicit commands at safe decoder boundaries advance to the next segment, allowing data to fill 8K bank tails efficiently.

## HOME

The TS2068's internal ROM and RAM bank. An HSR bit of zero exposes the corresponding HOME chunk to the CPU. HOME is a bank name, not an acronym.

## HSR

**Horizontal Select Register.** The TS2068 memory-selection register at port `$F4`. Each of its eight bits controls one fixed 8K CPU address range. A zero selects HOME; a one selects the external bank chosen by DECR bit 7. HSR is a mask, not a bank number.

## ID

**Identifier.** A numeric or textual value used to identify something. In a DCK header, byte 0 is the bank identifier.

## IM1

**Z80 Interrupt Mode 1.** A Z80 interrupt mode in which a maskable interrupt transfers control to `$0038`. Mapping cartridge chunk 0 hides the HOME ROM routine at `$0038`, so interrupts must be disabled or handled by valid external code.

## ISR

**Interrupt-service routine.** Code entered in response to an interrupt. Its code, vector, data, and stack must remain visible under the current memory mapping.

## LDIR

A Z80 block-copy instruction that repeatedly copies from `(HL)` to `(DE)`. Its source and destination use the current HSR mapping. If cartridge ROM covers the intended HOME destination, LDIR does not write through to the hidden RAM.

## LROS

**Language ROM-Oriented Software.** A cartridge-resident language or operating environment that can replace or augment the standard system software. An LROS normally begins in chunk 0 and takes broader control of memory, interrupts, and initialization than an AROS.

## OS

**Operating system.** The TS2068 system software in ROM and its associated HOME-RAM state, including system variables and dispatcher support.

## Overlay

The replacement of one HOME chunk in the CPU's view by the same-address DOCK or EXROM chunk. The hidden HOME bytes are neither moved nor erased. Clearing the HSR bit reveals them again.

## PackBits

An optional byte-oriented run-length encoding well suited to a small Z80 decoder. It is useful when cartridge space matters, but raw data is simpler and faster when it already fits. Control bytes `0-127` introduce `control+1` literal bytes; `129-255` repeat the following byte `257-control` times; `128` is a no-operation value. PackBits has no required end marker, so a cartridge decoder should stop after a descriptor-supplied compressed length or exact output length. Incompressible input can grow slightly and should remain raw unless compression gives a worthwhile saving.

## PC

**Program counter.** The Z80 register containing the address of the next instruction. Never switch away the chunk containing PC unless execution continues through verified mirrored code or a routine in unaffected RAM.

## PicoROM

A hardware cartridge implementation that supplies ROM data electronically. Its exact capacity and write behavior depend on the hardware; a DCK RAM descriptor does not make a PicoROM image writable.

## RAM

**Random-access memory.** Writable working memory. HOME RAM can coexist with cartridge code by leaving its HSR chunks unselected. External RAM exists only when the cartridge hardware or emulator configuration supplies it.

## ROM

**Read-only memory.** Memory used for immutable code or data during normal execution. CPU writes to a selected ROM chunk do not pass through to hidden HOME RAM.

## SCLD

**Standard Cell Logic Device.** The TS2068 control-logic device responsible for memory selection, display generation, timing, and other machine functions. Its video path reads HOME display RAM independently of the CPU's HSR mapping. Thus the SCLD may display a HOME byte at `$4000` while a CPU read at `$4000` returns a cartridge byte.

## SP

**Stack pointer.** The Z80 register locating the current stack. The stack must remain in writable, CPU-visible memory through calls, returns, pushes, pops, and interrupts.

## Z80

The TS2068's eight-bit microprocessor architecture. It has a 16-bit address bus and therefore a 64K CPU address space.
