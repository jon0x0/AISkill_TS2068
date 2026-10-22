# TSPico banked SRAM, CP/M RAMDisk and Oliger image interoperability

Use this for MEMDOCK-backed storage, the CP/M 2.2 port, or compatible disk-image
tools. For packet framing and ordinary application files, also read
[protocol.md](protocol.md). The linked CP/M sources contain the advanced loader,
save logic and dual adapter; the six baseline Z80 assets here remain fixed-backend
libraries, not a drop-in CP/M BIOS or general Oliger controller emulator.

## Firmware and capabilities

| Target | SD-facing interface | RAMDisk persistence |
|---|---|---|
| Original 1.00, unchanged | Legacy shared FIFO; TAP CODE transfers and formatted DIR; MEMDOCK SRAM selection | Explicit export of numbered page TAPs plus descriptor; direct reload without PC repacking |
| Inspected modern 2.3.1 / ROM 2.3 interfaces | Nonconsuming status, validated ACK/MID/SYNC and modern channels; TAP operations still available through the modern transport | One multi-record TAP using APPEND, or explicit legacy-compatible split export |
| Modern with optional CP/M service | Native `/CPM/FILES` or direct DSK/TAP sector volume, also snapshot to SRAM | Persistent SD writes in service mode; explicit TPSAVE for RAM snapshots |
| Intermediate/unknown | Establish actual handlers and handshake; version strings alone are insufficient | Do not infer APPEND, channel APIs or a filesystem service from the version number |

Do not send modern SYNC until its protocol family has been established. A
floating FF value is not evidence. The CP/M adapter validates ACK/MID first
and retains a legacy path for newer-compatible TAP operations. This does not
mean modern wire timing can be used on the original shared FIFO.

The TSPico ROM client version, board revision and MicroPython version are not
the Pico filesystem-firmware identity. GETINFO is useful when supported, but
implement against observed interfaces. The optional CP/M service supplies a
sector/filesystem contract beyond the bare raw-file channel commands.

### Legacy saved-file discovery and timing

Named LOAD can return different missing-file statuses in original and later
legacy-dispatch variants, including quiet 00 or 05. A quiet 05 must not be
globally treated as permission to ignore a saved disk. The CP/M loader first
captures a complete bounded DIR reply, requires a recognized listing header,
and matches exact case-insensitive filename tokens. Only verified absence
permits factory preload fallback. Present but unreadable, malformed, incomplete,
mixed or truncated saved sets fail closed.

Drain complete replies even if no text is displayed. Retain command text,
raw function/status, reply text and protocol phase for error reports; stale
previous-response fields after timeout do not establish the failed operation's
reply. Avoid issuing GETINFO into an uncertain in-flight FIFO after timeout.
The successful CP/M physical flow retained long guards after DIR and before
mounting the next factory volume. Functional model success is not hardware
evidence that those guards or byte pacing can be removed.

## Banked SRAM as a block device

MEMDOCK selects the SRAM presented through DOCK; F4 selects which 8KiB windows
the CPU sees. These are distinct controls. For the CP/M implementation, the
command is `TPI:MEMDOCK`, with PMR1=1 and PMR2=the even SRAM slot number. It
uses the command dispatcher/response rules of the detected transport. Do not
substitute a ROM call or interpret command-name case as a separate capability.

Keep live code, stack, return addresses, interrupt dependencies, transport
workspace and bounce buffer in HOME regions that remain visible. Before
switching the SRAM slot, unmap DOCK with F4=0. Map only the required window
while copying. Unmap before restoring the application's slot, then restore
its F4 map. Preserve DECR/FF bank/video/interrupt bits as appropriate for the
host. Avoid concurrent transactions and interrupts into switched-out vectors.

The **CP/M 2.2 example**, not a universal allocation rule, reserves:

| Resource | Allocation |
|---|---|
| CP/M cartridge | SRAM pair 4/5 |
| Disk SRAM | pairs 0/1, 2/3, 6/7, 8/9, 10/11, 12/13 |
| Kept resident | CPU chunk 7, E000–FFFF, in HOME |
| Disk capacities | 20 or 40 pages × 8192 bytes = 160 or 320KiB |
| CPU program memory | 32KiB writable low DOCK plus high HOME; TPA 0100–CFFF |

For a CP/M 128-byte record LBA:

```text
page = LBA // 64
offset = (LBA % 64) * 128
pair = [0, 2, 6, 8, 10, 12][page // 7]
window = page % 7
CPU address = window * 8192 + offset
F4 mask = 1 << window
```

Validate the declared geometry and bounds before applying this mapping. Each
pair offers seven usable windows because chunk 7 contains the resident code.
This makes spare capacity neither automatically free nor a second CP/M drive.
Keep slot ownership explicit; a different application must choose its own map.

The loader receives pages at HOME A000. When the destination is also the A000
DOCK window, a resident 128-byte bounce buffer moves the page in spans while
alternating mappings. Other windows allow direct copy/readback. Do not stage
8KiB pages in HOME 4000/6000 screen RAM. A separate PicoVideo shadow can still
show garbage on older firmware that captures out-of-bank writes; test actual
HOME bytes separately from the visible display.

SRAM provides working disk bytes, not automatic persistence. Bank selection
still uses the Pico link. Full-page compare verification costs a few modeled
CPU seconds over a 320KiB preload; transport and firmware housekeeping add time.
Do not promise throughput from a functional emulator or remove verification
without a clear alternative integrity check.

## Disk-image contract

| Supported geometry | Raw size | CP/M allocation block |
|---|---:|---:|
| 40 cylinders × 1 side × 16 sectors × 256 bytes | 163840 | 1024 |
| 40 cylinders × 2 sides × 16 sectors × 256 bytes | 327680 | 2048 |

The tools handle **standard CPC DSK containers used by this Fuse/JLO setup**,
numbered sectors 1–16, plus the project's CP/M layout and TAP wrappers. A
controller sector is 256 bytes; a CP/M record is 128 bytes. Do not confuse
physical cylinders/sides with the BIOS's synthetic logical tracks.

This is Oliger-compatible CP/M **image/filesystem interchange**, not WD1770 port
emulation on TSPico and not support for arbitrary historical Oliger/DOS layouts.
Extended DSK and unrelated sector maps require their own adapters. Fuse/browser
cartridges currently match a specific geometry; TSPico loader metadata can
select 160/320KiB parameters. The current CP/M release exposes A only.

## Portable Python tools included in this skill

Run from this skill directory with Python 3.10+. No third-party Python packages
are needed. Keep the four scripts together because they import each other.
They are copied from the CP/M project under MIT; attribution/license accompanies
them in scripts/LICENSE-cpm-tools.txt. They edit host files, not live hardware.

```text
python scripts/cpm_disk.py create work160.dsk --size 160
python scripts/cpm_disk.py create work320.dsk --size 320
python scripts/cpm_disk.py put work320.dsk HELLO.COM README.TXT
python scripts/cpm_disk.py list work320.dsk
python scripts/tspico_ram_image.py --dsk work320.dsk --output work320.tap --volumes preload320
python scripts/tspico_ram_image.py --chunks saved-set --output restored.tap --dsk-output restored.dsk
python scripts/tspico_ram_image.py --tap saved.tap --output archive.tap --dsk-output archive.dsk
```

create/put/list also accept the supported TAP/raw containers. Existing files
or names are refused unless the relevant explicit replacement option is used;
retain working disks separately and never edit the same image while mounted.
The low-level oliger_image.py adapter encodes/decodes containers; cpm_disk.py
is the normal user-facing file tool. A .z3 story is not a COM executable;
applications need compatible CP/M-80 binaries and their companion files.

## Load, save, reload and interchange

For original firmware, the physical SD folder `/TAP` is the protocol's root.
The cartridge navigates CD / then CD CPM and uses bare filenames. Do not assume
modern absolute SD-path syntax on 1.00. Factory 320KiB images are packaged as
eight small CPM32000.TAP–CPM32007.TAP volumes, five pages each; 160KiB uses four
volumes. Each stays below the original roughly 50KiB tape-buffer limit.

TPSAVE exports original-protocol disks as twenty/forty CPMnn.TAP files plus
CPMSTATE.TAP. The descriptor records geometry, completion and per-page Fletcher
checksums. Reload the whole matching set directly; no PC repack is needed.
The completion marker is invalidated before replacement and completed only
after all pages succeed. This detects incomplete replacement, not an atomic
save or a historical backup. Preserve previous exports separately.

On the inspected modern protocol, TPSAVE creates/mounts one CPMRAM.TAP and uses
APPEND for its metadata and CODE records. `TPSAVE SPLIT` requests compatible
chunks on either family. If both save formats exist, the modern loader asks
which to use. Original 1.00 does not gain reliable single-large-TAP persistence
merely because the container can hold multiple records.

For CP/M: work in A, exit applications, run TPSAVE, confirm and wait for success
before power-off. Game SAVE writes into SRAM; it must be followed by TPSAVE.
An export failure means retain the live disk and resolve/retry before shutting
down. The export is disk contents, not CPU/screen/program state. CP/M's built-in
SAVE saves memory to a CP/M file and is unrelated to RAMDisk export.

To move back to Fuse, convert the saved TAP/set to DSK using the tools, then
use the matching Oliger cartridge. To move from browser to original TSPico,
Download 1.00 TAP set yields the reloadable files. Preserve the old SAVE set
before replacing it. Cold startup prioritizes saved disks over factory volumes.

## Native SD versus image versus RAM snapshot

With the optional modern service, native `/CPM/FILES` synthesizes the CP/M
directory/sector interface from ordinary SD files. Raw chopen/chrd/chwr alone
do not implement that mapping. Direct image mode instead exposes one DSK/TAP
as sectors. `CPMDISK MOUNT NAME.DSK` or NAME.TAP and CPMDISK DIR select the
service source; CPMDISK SAVE exports a service snapshot. Put CPMDISK.COM on
custom mounted images if the user needs to switch back.

Selecting R copies the current service volume into SRAM; subsequent RAMDisk
changes do not write back to the original SD image/native directory. Include
TPSAVE.COM before selecting R, and export explicitly. Native SD/service mode
and RAM snapshot mode have different persistence contracts; do not promise
automatic synchronization. Current RAMDisk mode refuses service remounts;
switching to another source requires restart. Multiple simultaneous drive
letters need per-drive geometry, allocation, identity, dirty state and save
destination; they are future work, not an already available B command.

## Evidence and reusable source

- [CP/M 2.2 release](https://github.com/jon0x0/ts2068/releases/tag/cpm22-v0.1.0)
- [Banked block driver](https://github.com/jon0x0/ts2068/blob/cpm22-v0.1.0/CPM_2068/src/sram_disk.asm),
  [loader](https://github.com/jon0x0/ts2068/blob/cpm22-v0.1.0/CPM_2068/src/sram_loader.asm),
  [export](https://github.com/jon0x0/ts2068/blob/cpm22-v0.1.0/CPM_2068/src/tpsave.asm),
  [dual adapter](https://github.com/jon0x0/ts2068/blob/cpm22-v0.1.0/CPM_2068/tools/dual_transport.py)
- [Optional modern service](https://github.com/jon0x0/ts2068/tree/cpm22-v0.1.0/CPM_2068/firmware)
- [Hardware/emulator quickstart](https://jon0x0.github.io/ts2068/CPM_2068/docs/quickstart.html),
  [PicoVideo](https://jon0x0.github.io/ts2068/CPM_2068/docs/picovideo.html)

Original-1.00 hardware boot and game operation in 64 columns were reported during
CP/M development. Native Z80 tests cover both protocols, bank/screen safety,
save/reload, malformed sets and both sizes. Modern service and PicoVideo 4.2
coverage is primarily source/model evidence; distinguish that from a physical
board test. CP/M 3.x is not implemented or validated by this 2.2 example.
