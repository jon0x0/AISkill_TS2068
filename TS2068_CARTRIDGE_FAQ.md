# TS2068 Cartridge Development FAQ

See the [glossary](TS2068_CARTRIDGE_GLOSSARY.md) for complete acronym and terminology definitions.

## What is a TS2068 cartridge program?

It is software or data stored in the machine's external cartridge bank, called DOCK. The cartridge may contain BASIC or machine-code Application ROM-Oriented Software ([AROS](TS2068_CARTRIDGE_GLOSSARY.md#aros "Application ROM-Oriented Software")), directly executed code, media data, or a bootstrap that copies another program into internal HOME random-access memory (RAM).

## How is the cartridge divided?

The Z80 central processing unit (CPU) can access a 64K DOCK space consisting of eight fixed 8K chunks:

| Chunk | Mask | Cartridge and CPU address |
|---:|---:|---|
| 0 | `$01` | `$0000-$1FFF` |
| 1 | `$02` | `$2000-$3FFF` |
| 2 | `$04` | `$4000-$5FFF` |
| 3 | `$08` | `$6000-$7FFF` |
| 4 | `$10` | `$8000-$9FFF` |
| 5 | `$20` | `$A000-$BFFF` |
| 6 | `$40` | `$C000-$DFFF` |
| 7 | `$80` | `$E000-$FFFF` |

## Where does each cartridge chunk get mapped?

Each chunk overlays the same-numbered HOME chunk. Chunk 2 always appears at `$4000-$5FFF`; chunk 7 always appears at `$E000-$FFFF`. Native Horizontal Select Register ([HSR](TS2068_CARTRIDGE_GLOSSARY.md#hsr "Horizontal Select Register")) banking cannot map an arbitrary cartridge chunk into a different window.

## How is bank switching performed?

Write an eight-bit mask to port `$F4`, the HSR. A one selects external memory for that chunk; a zero selects HOME. With DOCK selected, HSR=`$10` exposes cartridge chunk 4, while HSR=`$30` exposes chunks 4 and 5 together.

Port `$FF`, the Display Enhancement Control Register ([DECR](TS2068_CARTRIDGE_GLOSSARY.md#decr "Display Enhancement Control Register")), selects whether HSR-selected chunks come from DOCK or the Extension ROM ([EXROM](TS2068_CARTRIDGE_GLOSSARY.md#exrom "Extension ROM")) through bit 7. Bit 7 clear selects DOCK; bit 7 set selects EXROM. Preserve the other DECR bits because they affect video and interrupts.

## What is the TS2068 Extension ROM?

EXROM is the TS2068's supplementary Extension ROM bank. The production machine populates it with the 8K U20 system ROM, which supplements the 16K HOME ROM and contains cassette I/O, the video-mode change service, final initialization, bank-switching routines, and the source/jump tables for the operating-system function dispatcher. Its stock address range is EXROM `$0000-$1FFF`, so it is normally selected as chunk 0 with HSR=`$01` after DECR bit 7 has been set.

Timex's internal planning recognized that the design could support a 16K EXROM. A 16K implementation occupies chunks 0 and 1 at `$0000-$3FFF`; select chunk 1 with HSR=`$02` or both chunks with HSR=`$03`. This capability does not mean the factory 8K U20 has hidden upper bytes, and it does not make EXROM another cartridge, an LROS language cartridge, or an extra 64K payload area. DECR chooses either DOCK or EXROM globally for every HSR bit that is set. Switch from a HOME-RAM gateway, retain required HOME system variables and stack memory, and call only entries present in the exact installed EXROM image.

## Does switching copy memory?

No. It changes which physical memory responds at an address. Hidden HOME RAM retains its contents and reappears when the corresponding HSR bit is cleared.

## When does a bank switch take effect?

For the next memory access after the `OUT` instruction. The next opcode fetch, stack operation, data read/write, or interrupt can therefore see the new mapping.

## Can code execute directly from cartridge ROM?

Yes. Machine-code AROS software commonly begins at `$8008` in chunk 4 and executes there. The chunk containing the current PC must remain selected. Cartridge ROM is suitable for immutable code and data, but not for writable variables, self-modifying code, or the stack.

## Can a program use TS2068 RAM at the same time?

Yes. Leave the HSR bits clear for every HOME RAM chunk the program needs. For example, HSR=`$10` gives cartridge code at `$8000-$9FFF` and leaves all other HOME ROM/RAM available.

## Can the whole 64K cartridge be used?

Yes. All eight chunks can store useful bytes. Keep resident code in chunk 4, page the other chunks as payload, and retain selected HOME chunks for the stack, display, ROM, and work buffers. The unused part of chunk 4 can also hold data.

## How does FIFO packing use cartridge space efficiently?

[TSVideoCodec](https://github.com/jon0x0/TSVideoCodec) first uses PackBits to compress the complete ECM keyframe at the beginning of video playback. The player decompresses that first frame's bitmap and color planes into the live display; later frames are delta records applied to that baseline. Those records occupy the seven non-code chunks—0, 1, 2, 3, 5, 6, and 7—as one logical 56K [FIFO](TS2068_CARTRIDGE_GLOSSARY.md#fifo "first-in, first-out logical stream"). A delta records its starting FIFO slot and address; when the decoder reaches an explicit `$C1` or `$C2` boundary command, it selects the next slot and resumes at that slot's start. The build-time packer splits only at codec command boundaries, including splitting literal runs when safe, so records can cross 8K banks and fill bank tails that a one-record-per-bank scheme would waste.

This is a logical stream implemented in software, not a hardware FIFO. In the proven layout chunk 4 still contains the player and tables, so the contiguous data capacity is 56K and the entire 64K image is useful as code plus data. To approach 64K of payload, copy a compact player to HOME RAM and describe the unused portions of chunk 4 as extra stream segments; the AROS header, bootstrap, and any code that must remain in ROM are still unavoidable overhead.

## Can all 64K be visible simultaneously?

HSR=`$FF` exposes all eight external chunks, but it also hides all HOME ROM and RAM. With a ROM cartridge there is then no writable HOME stack or normal ROM interrupt handler. This is possible as a controlled state, but selective overlays are far more useful.

## Are any cartridge chunks inaccessible?

No chunk is permanently inaccessible. Some are inconvenient at startup or runtime. Chunk 0 hides the ROM interrupt vector, chunks 2 and 3 hide CPU access to the display region, and chunk 3 often hides the active stack or OS dispatcher. These chunks are best treated as delayed-use storage.

## Why is chunk 4 normally used for startup?

The standard cartridge header occupies `$8000-$8007`, and the conventional machine-code entry is `$8008`. This makes chunk 4 a natural resident bootstrap/player chunk.

## Do I need to copy a switching routine into RAM?

Not when resident cartridge code remains selected. Code in chunk 4 can set another HSR bit, read a data chunk, and restore the old mask.

Use a HOME-RAM gateway when the switch will hide the current code, uncover HOME RAM beneath that code, or change DECR globally between DOCK and EXROM.

## How do I copy a cartridge chunk into the HOME RAM beneath it?

The cartridge and HOME versions of the same chunk cannot be visible together. Copy the cartridge data into a temporary HOME chunk at a different address, restore the target HOME chunk, and then copy from the temporary buffer to the final destination.

## What happens if I select ROM over a RAM destination?

The write does not pass through to hidden HOME RAM. A transfer such as `LDIR` may complete while the intended destination remains unchanged. Confirm that every source and destination chunk is simultaneously visible with the correct read/write type.

## What happens to the display when chunks 2 or 3 are selected?

The Standard Cell Logic Device ([SCLD](TS2068_CARTRIDGE_GLOSSARY.md#scld "Standard Cell Logic Device")) continues fetching the displayed pixels and attributes from HOME video RAM independently of the CPU's HSR mapping. HSR changes the CPU's view, not the SCLD's display source.

For example, with cartridge chunk 2 selected, a CPU read at `$4000` returns the cartridge byte at `$4000`, while the SCLD simultaneously reads the visible primary-screen byte from HOME RAM at `$4000`. The existing picture remains visible, but CPU reads do not return those screen bytes and CPU writes do not update the hidden HOME screen. Clear HSR bit 2 before CPU access to the primary display, or bit 3 before access to the second display file.

## Can a compressed TS2068 title screen run before the main program?

Yes, but compression is optional. If the raw pixel and color planes fit, store and copy them directly; that is simpler and faster, and it is the method used by the current Elite ECM cartridge. Use [PackBits](TS2068_CARTRIDGE_GLOSSARY.md#packbits "PackBits run-length compression") when its storage saving justifies a decoder and decompression time. Compress the planes independently and retain raw storage for any plane that does not become meaningfully smaller.

For a curtain wipe, decode the color plane into a temporary HOME buffer first, clear the live color plane to black, and copy columns from the buffer to `$6000-$77FF`. After the title hold, clear the color plane to black before returning to normal video mode, restore the intended HSR/DECR state, and enter the main application. Validate exact 6144-byte output lengths and source hashes during the build because PackBits has no required end marker and may expand incompressible data slightly.

## Why can interrupts cause crashes after banking?

In Z80 Interrupt Mode 1 ([IM1](TS2068_CARTRIDGE_GLOSSARY.md#im1 "Z80 Interrupt Mode 1")), the CPU enters `$0038`. Selecting external chunk 0 replaces the HOME ROM handler at that address. Either keep chunk 0 HOME, disable interrupts during the mapping, or provide a valid handler in the selected external memory.

## What happens to the stack?

Stack reads and writes use the current mapping like every other memory access. Never select ROM over the chunk containing SP. Calls, returns, pushes, pops, and interrupts will otherwise use the wrong bytes or attempt to write to ROM.

## How should DOCK-to-EXROM calls be made?

Run a gateway from unaffected HOME RAM. Disable interrupts, set HSR to zero, change DECR bit 7, select EXROM chunk 0 with HSR=`$01` for a stock EXROM service, call the verified routine, set HSR to zero again, and restore DECR, HSR, and interrupt state.

## Can a BASIC program run from cartridge?

Yes. A BASIC AROS stores tokenized program lines in cartridge memory beginning at `$8008`, while variables and changing state live in HOME RAM. Keep the documented HOME chunks available and account for known TS2068 ROM limitations.

For a TS2068 BASIC TAP program, the [TS2068 TAP to Cartridge Builder](https://timex-sinclair-projects.github.io/2068-TAP-To-Cart/) provides a quick browser-based route to BIN and DCK files, with optional appended CODE blocks. It is designed specifically for TS2068 BASIC programs and builds BASIC AROS in DOCK chunks 4-7; it is not an automatic converter for arbitrary Spectrum machine-code software.

## Should I choose a BASIC or machine-code cartridge?

Choose BASIC AROS when BASIC statements and ROM-managed program flow are central to the application. Keep tokenized lines and immutable program material in cartridge ROM, mutable variables in HOME RAM, lower HOME chunks available to the interpreter, and every `USR` helper disciplined about restoring the ROM's mapping and workspace.

Choose machine-code AROS for direct hardware control, exact timing, custom interrupts, extensive banking, codecs, games, or Spectrum compatibility launchers. It can execute immutable code straight from cartridge, but it must explicitly provide a writable stack and variables, safe interrupt and ROM-call policies, and RAM copies of anything self-modifying. See the complete [BASIC versus machine-code dos and don'ts](TS2068_CARTRIDGE_GUIDE.md#basic-versus-machine-code-cartridges-dos-and-donts).

## Can an ordinary Spectrum BASIC program simply be copied into ROM?

Sometimes it can be adapted, but it should not be assumed. Program layout, variables, machine-code helpers, ROM calls, display assumptions, and address-sensitive behavior may need changes. A purpose-built BASIC AROS is more reliable.

## What is the difference between Fuse DCK and flat BIN files?

A Fuse [DCK](TS2068_CARTRIDGE_GLOSSARY.md#dck "Fuse cartridge-image format") (`.dck`) cartridge-image file is a container with a header, eight descriptors, and payloads only for stored chunks. A flat binary (BIN) file contains eight consecutive 8K regions in address order and is normally the starting point for physical cartridge programming.

The external [`dckls` utility from zx81-utils](https://github.com/ryangray/zx81-utils) can extract the stored spans with `dckls -d file.dck`; for example, a contiguous DOCK ROM beginning at chunk 0 becomes `file_DOCK_0x0000.rom`. This does not guarantee a padded 64K image: sparse DCKs can yield shorter or multiple files. Use the bundled `inspect_dck.py --flat-output ... --fill 0xFF` when an exact 65536-byte physical image is required.

## Can Fuse debugger automation be used on macOS?

Possibly, but verify the exact packaged release. The current official Fuse for macOS source retains the `--debugger-command` startup setting and command evaluator, although the native app has no graphical script loader, no `--debugger-command-file`, and no supported remote command/reply interface. Invoke `/Applications/Fuse.app/Contents/MacOS/Fuse` directly—rather than Finder or `open -a`—and run a print-and-exit breakpoint smoke test. The bundled `run_fuse_debug.py` selects that path automatically. See the [macOS utility note](TS2068_CARTRIDGE_UTILITIES.md#fuse-debugger-automation-on-macos) for verification and implementation details.

## Does a DCK RAM chunk mean the physical cartridge is writable?

No. DCK descriptors can emulate RAM. Physical writability requires RAM hardware and correct write-signal handling. A ROM, EPROM, flash cartridge, or PicoROM image remains read-only unless its hardware explicitly supports writes.

## Can native banking address more than 64K of cartridge data?

Not by itself. HSR addresses eight fixed DOCK chunks totaling 64K. A cartridge larger than 64K needs its own paging register or hardware protocol in addition to the native TS2068 mechanism.

## What should be documented for every project?

Record the contents of all eight chunks, every HSR/DECR mask, the PC and stack location, interrupt policy, HOME RAM allocation, display mapping, ROM/EXROM calls, build commands, binary hashes, and emulator/hardware test results.
