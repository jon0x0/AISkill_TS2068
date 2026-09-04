# Eight Windows into 64K: Making Serious TS2068 Cartridge Software

**When to read:** Use for an approachable cartridge explanation or publication outline; consult the guide for implementation detail. For audio conversion and playback experience, see [audio development](TS2068_AUDIO_GUIDE.md); for browser cartridge demos, see [TSRun embedding](TS2068_BROWSER_DEMOS.md).
A companion [glossary](TS2068_CARTRIDGE_GLOSSARY.md) defines the specialized terms used in this article.

The cartridge port on the Timex Sinclair 2068 is much more interesting than a simple ROM socket. Used properly, it can support directly executed programs, large media stores, fast loaders, and conversions of software originally written for the ZX Spectrum. The trick is learning to see the machine's memory the way its banking hardware sees it.

The Z80 central processing unit (CPU) has a 64K address space. The TS2068 divides it into eight 8K sections, usually called chunks. Each section can show either the computer's internal HOME memory or external memory. A byte written to port `$F4`, the Horizontal Select Register ([HSR](TS2068_CARTRIDGE_GLOSSARY.md#hsr "Horizontal Select Register")), controls all eight choices: bit 0 controls `$0000-$1FFF`, bit 1 controls `$2000-$3FFF`, and so on through bit 7 at `$E000-$FFFF`.

This is not the kind of paging system where any bank can be dropped into one convenient window. Each cartridge chunk has a permanent address. Cartridge chunk 5 always appears at `$A000-$BFFF`. Selecting it hides the HOME RAM at those addresses, and deselecting it reveals that RAM again. Nothing is copied. The hardware simply changes which memory answers the CPU.

That one fact explains both the power of the system and most of its traps.

## Running straight from the cartridge

A machine-code cartridge program can begin at `$8008`, immediately after its eight-byte Application ROM-Oriented Software ([AROS](TS2068_CARTRIDGE_GLOSSARY.md#aros "Application ROM-Oriented Software")) header in chunk 4. It can continue running directly from read-only memory (ROM), leaving most of the TS2068's internal random-access memory (RAM) free for the screen, variables, buffers, and stack.

If the program needs data from chunk 5, it can change the HSR mask from `$10` to `$30`. Chunk 4 stays present, so the next instruction still comes from the right place, and chunk 5 appears beside it at `$A000-$BFFF`. When the data has been read, the program restores `$10` and HOME RAM reappears under chunk 5.

The dangerous version is clearing the bit for the chunk containing the current instruction. The bank switch takes effect immediately: the next opcode comes from whichever memory has just appeared at that address. The CPU does not object or warn you. It simply runs the new byte, which is why a bad mapping often looks like a spontaneous crash or reset.

The stack and interrupt handler follow the same rule. If the stack lies in HOME chunk 3 and cartridge chunk 3 is selected, calls and returns start using the cartridge area. If interrupts are enabled while chunk 0 is selected, a Z80 Interrupt Mode 1 ([IM1](TS2068_CARTRIDGE_GLOSSARY.md#im1 "Z80 Interrupt Mode 1")) interrupt jumps to cartridge address `$0038` rather than the familiar HOME ROM handler. A solid cartridge design therefore treats the program counter, stack pointer, interrupt vector, and memory map as one inseparable system.

## The built-in Extension ROM

The third memory source, EXROM, is sometimes mistaken for another cartridge bank. In a production TS2068 it is populated by an 8K mask ROM chip, U20, built into the computer. It supplements the 16K HOME ROM with cassette I/O, the change-video-mode service, final startup code, bank-switching support, and the source of the function dispatcher copied into RAM during initialization.

The stock EXROM occupies `$0000-$1FFF`, or chunk 0. Timex nevertheless knew the design could support a 16K Extension ROM: a 16K implementation spans chunks 0 and 1 through `$3FFF`, with HSR=`$03` selecting both. This is a distinction between the EXROM bank's capability and the factory chip actually fitted to the machine—not evidence of hidden bytes in stock U20.

Software selects the stock service ROM by setting DECR bit 7 and then selecting chunk 0 in HSR. The important catch is that DECR chooses EXROM or DOCK globally. A cartridge program cannot keep executing from selected DOCK code while casually flipping to EXROM; it must pass through unaffected HOME RAM, remove the DOCK mapping, select EXROM, call the required service, and reverse the sequence afterward. EXROM services may also expect HOME system variables and stack state, so they are operating-system calls rather than free-standing utility routines.

## Can a cartridge really use all 64K?

Yes—all eight 8K chunks can contain useful code or data. The practical way to do it is not to select the whole cartridge at once.

Keep a small resident player, decompressor, or dispatcher in chunk 4. Use the other seven chunks for pageable assets, compressed screens, levels, sound, or application code. Leave the HOME chunks needed for the stack and working buffers visible, then select one cartridge data chunk at a time.

Chunks 2 and 3 are especially interesting because they overlap the CPU's screen area, yet the Standard Cell Logic Device ([SCLD](TS2068_CARTRIDGE_GLOSSARY.md#scld "Standard Cell Logic Device")) has its own access to HOME video RAM. If cartridge chunk 2 is paged in, a CPU read at `$4000` returns the cartridge byte. At that same moment, the SCLD still fetches the displayed pixel from HOME screen RAM at `$4000`. The picture therefore remains visible, but the CPU cannot read or update the HOME screen underneath the cartridge overlay. A program can copy cartridge data elsewhere, restore HOME chunks 2 and 3, and then update the display. A high-throughput design may preload those two cartridge chunks into upper HOME RAM during startup.

This resident-code-plus-paged-data arrangement was proven useful in [TSVideoCodec](https://github.com/jon0x0/TSVideoCodec): seven chunks could carry media while chunk 4 held the hot player and tables. The unused tail of the code chunk could carry data as well, making productive use of the entire physical 64K image.

Setting HSR to `$FF` does expose the complete cartridge from `$0000` to `$FFFF`. It also removes the entire HOME ROM and RAM from the CPU's view. With a read-only cartridge, there is nowhere for an ordinary writable stack and no standard interrupt handler. It is a technically valid mapping, but not usually a comfortable place to run a complete application.

## Treating seven banks as one FIFO

TSVideoCodec starts with a complete ECM keyframe. PackBits compresses the first frame's bitmap and color planes, and the player expands both into display RAM to create the initial picture. The remaining video frames are delta updates against that baseline.

For those updates, TSVideoCodec goes a step beyond simply assigning one compressed frame to each bank. Its build tool treats chunks 0, 1, 2, 3, 5, 6, and 7 as a single logical 56K [FIFO](TS2068_CARTRIDGE_GLOSSARY.md#fifo "first-in, first-out logical stream"), while chunk 4 contains the always-available player and lookup tables. At boot, data from cartridge chunks 2 and 3 is copied into HOME chunks 6 and 7. The player can then restore the screen area to HOME while still reading those two portions of the stream from their RAM copies.

A conventional best-fit packer keeps each complete frame within one 8K bank. It is simple and fast, but the gap after one frame may be too small for any later frame, and no frame may exceed 8K. The FIFO packer instead inserts a tiny next-bank command at a valid codec-command boundary. A one-byte `$C1` command fills a one-byte bank tail; `$C2,0` fills a two-byte tail. Literal commands can be shortened and continued, while sparse commands that do not fit can be expanded to an equivalent literal form. The decoder checks for a bank change only when it reads a command, not after every media byte.

Each frame index stores its FIFO starting slot and source address. The runtime advances through the ordered sources—cartridge 0, cartridge 1, the RAM copies of cartridge 2 and 3, then cartridge 5, 6, and 7—and restores HSR=`$10` when it is finished. In one measured 30-frame image, 39,247 bytes of payload required only 10 bytes of boundary markers and padding, while reconstruction of the final screen remained exact.

This arrangement uses all seven media chunks with almost no fragmentation and makes the whole cartridge productive as 56K of tightly packed media plus 8K of resident code and tables. A more aggressive variant can copy the player into HOME RAM and add free ranges in chunk 4 to a segment table, approaching 64K of payload; a self-contained cartridge still needs some bytes for its header, bootstrap, and decoder, so those bytes cannot simultaneously be arbitrary media data.

## A native title screen packed into the cartridge

Banking can do more than hold a large program. It can give original TS2068 software—or a Spectrum port—a polished native introduction before the main application begins.

Consider a TS2068 Extended Color Mode title screen. Its pixel plane occupies 6144 bytes and its color plane another 6144 bytes. The Elite cartridge demonstrates the presentation technique with raw planes: its launcher copies the pixels into HOME screen RAM, reveals the colors from the center like opening curtains, holds the finished image for six seconds, fades it cleanly to black, restores normal video mode, and continues into Elite.

When space is available, raw planes are a perfectly good—and simpler—choice: copy them directly without a decoder or decompression delay. When cartridge space is tight, the two planes can instead be compressed independently with [PackBits](TS2068_CARTRIDGE_GLOSSARY.md#packbits "PackBits run-length compression"). A build tool should choose compressed storage only when it gives a worthwhile saving, retain raw storage otherwise, and round-trip any compressed result against the original artwork.

At startup, resident code in chunk 4 selects the compressed-data chunk while leaving HOME screen chunks 2 and 3 visible to the CPU. It decodes the pixels to `$4000-$57FF`. For a curtain effect, it expands the color plane into a temporary HOME buffer, clears the live color plane at `$6000-$77FF`, enters Extended Color Mode, and copies columns from the buffer to the screen from the center outward.

The mapping matters. If compressed data is read from cartridge chunk 2, the CPU cannot simultaneously write the HOME pixel memory underneath that chunk. It must decode to another HOME buffer, clear HSR bit 2, and then copy into the screen. Throughout the sequence the SCLD continues fetching the visible display from HOME RAM, independently of the CPU's cartridge view.

This small prelude combines several sophisticated cartridge techniques: build-time media conversion, compression, per-stream metadata, bank-aware reads, direct execution from ROM, use of HOME RAM as a decode target, native TS2068 video modes, animated reveal, deterministic timing, and a carefully controlled handoff to the application.

## Converting existing software

Cartridges are also excellent containers for software that was never designed to run in ROM. A small bootstrap can page in the original bytes, copy them into their expected HOME RAM addresses, restore the register and memory state normally created by a tape loader, unmap the cartridge, and jump into the program.

That sounds simple until the program calls a Spectrum ROM routine, expects a Kempston joystick, saves data through a Spectrum cassette entry, relies on exact interrupt timing, or modifies its own code. These are not really cartridge-format problems; they are machine-compatibility problems. Keeping the banking layer separate from compatibility patches makes them much easier to diagnose.

The Elite conversion provided a good example of the debugging method. The TS2068 cartridge was derived from the ZX Spectrum Elite JCV tape program (`ELITEJCV.TAP`), rather than from an existing cartridge edition. Instead of relying on repeated manual play sessions, that original tape was automated under Spectrum emulation. Exact Z80 state was captured after the final ROM loader returned and before the game's handoff. The cartridge build reproduced that state, and scripted traces were used to locate the first true TS2068 divergence. The same approach helped isolate display, chart, launch-sequence, cassette, and interrupt issues without treating every crash as an unexplained emulator quirk.

## A Fuse [DCK](TS2068_CARTRIDGE_GLOSSARY.md#dck "Fuse cartridge-image format") cartridge image is not the physical cartridge

Fuse's DCK (`.dck`) cartridge-image format is extremely useful, but it is a description of a cartridge rather than a raw ROM dump. Its header says which chunks are absent, ROM, uninitialized RAM, or initialized RAM. Only stored chunks have payload bytes in the file.

A physical 64K cartridge image is normally much simpler: eight consecutive 8K regions in address order. Emulator RAM descriptors do not make physical ROM writable, and a cartridge board that decodes only 16K cannot magically expose the remaining 48K. Good build scripts therefore generate and inspect both the DCK and the exact flat binary intended for the hardware.

## A better way to approach the machine

The TS2068's banking stops feeling obscure once every transition is described concretely. Before an `OUT`, ask four questions:

1. Where will the next instruction be fetched?
2. Is the stack still in writable memory?
3. What will happen if an interrupt occurs?
4. Which physical memory will receive every read and write?

Draw the eight chunks. Mark each one internal HOME, cartridge DOCK, or Extension ROM ([EXROM](TS2068_CARTRIDGE_GLOSSARY.md#exrom "Extension ROM")) for every phase. Preserve shadow copies of the control registers. Use a short routine in unaffected HOME RAM for transitions that would remove the executing cartridge code or switch between DOCK and EXROM. Then test with deterministic emulator scripts and exact CPU-state checkpoints.

The reward is a cartridge system far more capable than its modest connector suggests: direct execution, almost instant loading, the full 64K available as storage, coexistence with internal RAM and ROM, and a strong foundation for original TS2068 software as well as ambitious, sophisticated Spectrum ports.
