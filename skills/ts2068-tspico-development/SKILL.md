---
name: ts2068-tspico-development
description: Use TSPico expansion RAM, memory controllers, SD storage, and USB serial debugging from TS2068 software. Choose stock MEMDOCK banking or custom PIO paging, build RAMDisks, and implement ROM-independent legacy or modern file transfers.
---

# TS2068 TSPico Development

Use expansion RAM and storage against the installed **Pico firmware's** interface. A
TSPico ROM extension is an optional Z80 client, not the SD filesystem itself.
Cartridge programs can supply their entire Z80 driver and UI without calling
HOME ROM, EXROM, BASIC, or an installed TSPico library. The Pico must still run
compatible firmware. Loading a DCK through the supplied loader does not make
the resulting cartridge dependent on that loader at runtime.

## Using TSPico expansion RAM and its memory controller

For expanded memory, first read
[expanded-memory.md](references/expanded-memory.md). It separates stock
software-managed DOCK banking (including the CP/M RAMDisk) from the custom
PIO/DMA paging policy used by the Spectrum 128 ports. Stock TSPico already
has a PIO memory controller: using its SRAM does not inherently require
replacing it. Extra capacity, transparent guest paging, ROM switching,
video access, and SD service are separate capabilities.

The reference includes a banked-software interface pattern: keep addresses
as region/chunk/offset descriptors, run banking gateways from stable HOME,
split transfers at mapping boundaries, and restore the caller's map before
returning. Choose this before treating extra SRAM as ordinary flat pointers.

For driving and inspecting the Pico through USB MicroPython, read
[USB memory-controller debugging](references/usb-memory-debugging.md).
It covers temporary definitions, dispatcher interruption, read-only status,
PIO/DMA ownership, reset versus parked-host execution, and bounded ROM probes.

## Select storage and protocol

Read [integration.md](references/integration.md) to choose a storage format,
host API, memory map, deployment route, and optional modules. Then read the
applicable [protocol reference](references/protocol.md) before writing I/O.

For MEMDOCK SRAM, RAMDisk, 160/320KB Oliger DSK interchange, direct SD versus
RAM snapshots, or CP/M save/reload, read
[banked RAM and disk images](references/banked-ram-and-disk-images.md).
It includes the reusable Python image tools and the CP/M 2.2 implementation
boundary. The separate PicoVideo display card is covered by the graphics skill
when available, or the linked CP/M video guide; it is not TSPico firmware.

- **Original firmware 1.00 / legacy shared FIFO:** use TAP CODE block storage
  and formatted directory listings. The modern `chopen/chrd/chwr` commands
  are absent. Never send modern SYNC to port `$0F` on this backend.
- **Modern 2.3 firmware:** use file/directory channels for arbitrary raw-file
  reads, buffered sequential input, and bounded writes. Implement its status
  register, SYNC, command tail, response count, and checksum rules.
- **Unknown/intermediate firmware:** establish its actual protocol from
  firmware/source evidence; board revision or MicroPython version alone does
  not identify it. An older ROM version does not prove which firmware runs.

Keep separate fixed-backend builds available. Dual-backend selection and
autodetection are not implemented by the six baseline library assets. The
linked CP/M 2.2 cartridge provides a separate tested dual-transport adapter;
reuse its handshake evidence rather than assuming the baseline library already
does this.
Do not label a floating `$FF` bus or a modern timeout as successful detection.
Do not silently substitute TAP storage for raw files in an application API.

## Reuse the implementation

The six original assembly files in [assets/z80](assets/z80/) provide transport
and file operations without a renderer, font, keyboard or ROM calls. Read
[assets-and-validation.md](references/assets-and-validation.md) for their ABI,
memory ownership, build commands, limits and evidence. The standalone helper
[build_library.py](scripts/build_library.py) links legacy, modern, or modern
plus streaming libraries with sjasmplus. Relink sources for a host rather
than copying a prelinked binary to an unrelated address.

Keep transport, storage format adapter, file dialog, and optional stream
reader separate. Preserve the host's memory map, stack, interrupt policy,
display and keyboard ownership. Serialize transactions; these drivers are
not reentrant. Drain complete replies, including verbose text and checksums.
Treat stream numbers as shared resources and close handles on all exit paths.

## Validate the right claim

Test complete packets, all byte values, EOF, empty/exact-capacity/oversized
files, overwrite confirmation, cleanup, pagination and navigation. Confirm
boot with the TS2068 model and verify transfers on physical TSPico separately:
Fuse does not supply the Pico filesystem or bus-timing model.

The original-firmware legacy virtual cartridge received a user hardware
success report on 2026-10-17: firmware 1.00, MicroPython 1.20.0, default ROM
1.00, board V2.2. The report was "OK that worked"; do not infer that every
operation, size limit, binary pattern, or throughput was measured on hardware.
See [evidence and sources](references/assets-and-validation.md#evidence-and-sources).

For a physical PicoROM beside TSPico, first resolve which device drives DOCK.
A virtual cartridge supplied by TSPico needs its ordinary memory controller
enabled. A startup override prepared for modern 2.3 is not a legacy solution.
Use the cartridge-development skill, when available, for detailed AROS, DCK
packaging and bank-transition work; this skill's protocol and core libraries
remain usable independently.
