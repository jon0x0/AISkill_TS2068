# Adding disk support to a TS2068 program

For banked SRAM as a block device and Oliger-compatible disk image workflows,
read [banked RAM and disk images](banked-ram-and-disk-images.md). Raw-file access,
a mounted filesystem service, and a loaded RAMDisk snapshot are distinct host
interfaces; choose one explicitly rather than treating all SD access as a disk.

## Choose the host boundary

| Host | Practical implementation |
| --- | --- |
| ROM-independent cartridge, ZXDesk or TSWriter component | Link a Z80 transport and storage backend into cartridge code; keep workspace, stack and payloads in writable memory. Supply host callbacks for UI. |
| RAM-resident machine-code program | Link the same drivers at its actual code address; reserve their workspace and preserve the program's interrupt/bank map. No cartridge-specific I/O protocol is needed. |
| BASIC with known TSPico extensions | Existing BASIC LOAD/SAVE commands can use the installed ROM client. Declare this dependency and its version. |
| BASIC calling a machine-code storage component | Reserve code/workspace against BASIC allocation and define a stable argument/result wrapper. The component may implement the protocol directly if the ROM extensions are unavailable. |

The Z80 need not implement FAT, SPI, SD initialization, or the MicroPython
filesystem. The Pico firmware owns those. The Z80 implements command framing,
flow control, response handling and payload transfer. Calling existing ROM
routines is optional only when the host explicitly permits that dependency
and the exact ROM/banking ABI has been checked.

Use `host -> storage adapter -> backend -> transport -> ports -> Pico -> SD`.
A dialog uses the storage adapter, not Pico port reads scattered through UI.

## Storage formats and capabilities

| Capability | Legacy single FIFO | Modern 2.3 channels |
| --- | --- | --- |
| Directory | Firmware-formatted text; file index selection | `d:` directory channel with CR-delimited names |
| Load application bytes | Mount TAP, inspect CODE header, receive data block | Open raw file `rb`, read counted packets until EOF |
| Save application bytes | Create/overwrite a TAP CODE file | Open raw file `wb`, send bounded writes; see `$17` restriction |
| Working directory | Legacy CD changes global Pico cwd | Directory channel can enumerate without changing cwd |
| Streaming included here | None | Optional buffered sequential reader |

The legacy format can hold TSWriter document bytes in a CODE payload, but the
on-disk file is a TAP container, not a plain text file. An application should
name and document this format. For interoperability with ordinary PC files,
use verified modern firmware or add a separately designed firmware extension;
do not claim that original firmware has raw-file channels.

An application-facing adapter should return a backend identifier plus explicit
capabilities for formatted directory text, structured enumeration, TAP payload
read/write, raw read/write and sequential read. The bundled legacy query uses
A=7 solely for its own three capabilities; it is not an established cross-firmware
capability standard. Unsupported raw-file entry points return E3 without I/O.

## Cartridge and host memory

Keep the executing chunk, return addresses, writable stack and interrupt
vectors visible throughout a transfer. Maintain software shadows of `$F4`
and `$FF`; external selection is a fixed-address overlay, not a relocatable
window. Direct port I/O does not require selecting the TSPico ROM.

The demonstrated cartridge maps DOCK chunks 0–1 at `$0000–$3FFF`, HOME chunks
2–7, HSR `$03`, DECR `$40`, interrupts disabled and stack below `$FFF0`.
Its AROS bootstrap runs in chunk 4 before switching to low cartridge code.
This is a demo map, not a requirement for a ZXDesk/TSWriter component. Reassign
the backend scratch areas and use the host's interrupt policy. A banked host
must provide a resident gateway if its normal mapping hides the library.

Extra TSPico SRAM is a separate memory-controller facility, not part of disk
channel allocation. An SRAM slot selected for DOCK supplies the fixed external
bank; file streams do not automatically page more CPU RAM. Verify memory/slot
commands for the exact firmware before repurposing another SRAM pair.

## File dialogs

Keep directory model, keyboard input, rendering and filesystem operations
separate so the host can supply its own widgets. Open dialog returns a selected
path/index; loading bytes is a separate action. Save dialog returns a name and
explicit create/overwrite decision; opening/truncating a file follows that.

Legacy directories truncate displayed names and may paginate interactively.
Display the list and accept its three-digit file number through `tpi:&nnn`,
or accept a typed exact filename. Do not treat a truncated label as a reliable
filename. Refresh after saving/changing folders because indices can change.
The tested demo's C/B/H commands select folder/parent/root; selection by index
applies to files. Save basenames are restricted to 1–10 letters/digits, no suffix;
firmware adds `.tap`. Close a previous mount before SAVE to clear APPEND mode.

Modern enumeration uses records ending in CR, folders ending `/`, and absolute
paths relative to the public SD root. Bound record length and entry count;
drain the stream even after the display table fills. Skip unrepresentable names
rather than truncating them into actionable paths. The demonstrated browser
uses 96 entries of 64 bytes; those are UI limits, not protocol limits.

## Streaming video and ROM size

Keep streaming optional: a document editor should link only the backend it
needs. The modern buffered reader exposes open/get-byte/close and refills in
255-byte packets, allowing data larger than RAM. Reserve its stream and buffers,
count delivered bytes rather than fetched bytes, and close on EOF, abort or error.

A TSVideoCodec integration needs a decoder input abstraction and measured
on-device producer/consumer throughput. Validate packet refill latency, frame
deadlines, buffering, EOF and interruption. A successful directory read or
full-file load is not proof of continuous video playback. The host model's
~6314 B/s modern streaming result excludes Pico/SD latency; the legacy 16 KB
load loop's ~1.59 s also excludes that latency. Neither is a hardware benchmark.

## Deploy without changing Pico files

For first testing, use a virtual DOCK supplied by ordinary TSPico SRAM, with
no physical PicoROM attached. Merge a DCK into `/TAP/`, mount it with
`LOAD "tpi:NAME.DCK"`, then `LOAD ""` to run the supplied loader. Select an
unused even SRAM pair and the loader's DOCK/restart option. Leave BOOT alone.
Only the chosen pair's previous image is replaced. The loader is an installation
dependency, not a runtime ROM dependency. Power loss discards SRAM contents.

For the tested legacy package, the file is `PFILE1.DCK` and its fixtures are
`LEGACY/HELLO.TAP` and `LEGACY/BYTES.TAP`. Before mounting, `SAVE "tpi:cd /"`
selects the public root. Do not jump directly to low overlays with `OUT 244,3`;
the AROS bootstrap is part of cartridge startup.

Physical PicoROM coexistence requires deliberate chip-select ownership. TSPico
may already be driving DOCK. Do not apply a firmware-2.3 controller override to
firmware 1.00 or disable the controller that supplies a virtual cartridge.
