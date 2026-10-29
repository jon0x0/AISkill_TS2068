# Oliger-image RAMDisk on TSPico: CP/M 2.2 implementation and reuse

This is the implementation walkthrough for the TS2068 CP/M 2.2 cartridge.
Read it when adapting the SRAM block device to another program. Read
[banked RAM and disk images](banked-ram-and-disk-images.md) for wire-protocol
families, image creation/conversion and persistence details, and
[expanded memory](expanded-memory.md) for stock versus custom memory controllers.

## What was emulated

The TSPico backend replaces the floppy's **disk bytes** with banked SRAM. It
preserves the CP/M filesystem layout used in the project's Oliger/Fuse DSK
images. CP/M's BIOS selects an SRAM sector backend instead of the Oliger WD1770
backend. Applications still use ordinary CP/M file operations.

It does **not** make arbitrary software's Oliger port accesses work on TSPico.
A program using raw WD1770 commands must be adapted to this block API or given
a separate controller emulator. Image compatibility, filesystem compatibility,
controller-register compatibility and firmware compatibility are distinct claims.

## CPU memory layout while CP/M is running

The TS2068 CPU sees 64KiB at once. TSPico expansion capacity is accessed by
switching mappings; it does not make CPU pointers wider than 16 bits.

| CPU address | Normal CP/M use |
|---|---|
| 0000–00FF | Writable low DOCK; CP/M vectors and page-zero data |
| 0100–7FFF | Transient program area in low DOCK RAM |
| 8000–CFFF | Remaining transient program area in HOME RAM |
| D000–D7FF | CCP command processor in HOME |
| D800–E5FF | BDOS in HOME |
| E600–EFFF | BIOS/console and resident buffers; console descriptor near EFF8 |
| F000–F4xx | Banked SRAM driver and its transport, assembled at F000 |
| F500 onward | Resident transport workspace; reply capture at F680 |
| Below F7B0 | Private bank-switching call stack, top F7B0 |
| F800–FDFF | Diagnostic console transcript used by tests |
| Near FF00 | Normal BIOS stack area |

Exact buffer labels and code ends depend on the build; use its symbol file,
not copied numeric addresses. In particular, `bounce` is a 128-byte allocation
inside the BIOS below EFF0. The driver includes other state in its F000 region.
This table identifies reservations, not a promise that every gap is free.

Normal F4=0F selects DOCK in chunks 0–3 and HOME in chunks 4–7. For this port,
DECR/FF selects DOCK rather than EXROM. The two HOME display planes at 4000
and 6000 are hidden from CPU program accesses by the low DOCK mapping, but
remain the physical video display. The console briefly exposes HOME while
updating them. CP/M's TPA is 0100–CFFF: **52,992 bytes**.

Chunk 7 (E000–FFFF) is never replaced with a disk window. It contains the
executing gateway, stack, transport and bounce buffer. A temporary disk map
may hide the program, CCP and low vectors; it must be restored before control
returns to any of them. This is why merely placing the driver in cartridge
ROM would not solve the problem: selecting a different SRAM pair changes
which cartridge bytes are available too.

## How the TSPico expansion was allocated

The build uses stock **MEMDOCK** SRAM selection, not a replacement Pico PIO
controller. Original firmware 1.00 can supply it without a firmware upgrade.
The example's 512KiB expansion is organized as sixteen 32KiB slot numbers;
an even slot selects a pair used here as a 64KiB DOCK image. The cartridge
loader must load CP/M into **slot 4**, reserving pair 4/5.

| Slot pair | Disk page numbers in the 320KiB image | Windows used |
|---|---|---|
| 0/1 | 0–6 | chunks 0–6 |
| 2/3 | 7–13 | chunks 0–6 |
| 4/5 | CP/M cartridge/program RAM | Not disk storage |
| 6/7 | 14–20 | chunks 0–6 |
| 8/9 | 21–27 | chunks 0–6 |
| 10/11 | 28–34 | chunks 0–6 |
| 12/13 | 35–39 | chunks 0–4; two further windows not used by this image |
| 14/15 | Not used by this build | No implied ownership by another application |

Each disk pair contributes at most seven 8KiB windows because chunk 7 must
stay HOME. Forty pages provide 327680 bytes; a 160KiB image uses pages 0–19.
The fixed slot table still belongs to the application even if smaller media
leave some reserved capacity unused. Loading the image overwrites SRAM in the
allocated disk windows. Coordinate ownership with any other cartridge or RAM
user instead of assuming these assignments are universal TSPico requirements.

## The sector path: CP/M to SRAM and back

The BIOS handles CP/M DMA addresses; the block driver handles a fixed resident
bounce buffer. A CP/M record is **128 bytes**, while a physical sector in the
supported Oliger DSK is **256 bytes**.

1. BIOS `logical_sector` translates the requested logical track/sector to LBA.
2. On write, BIOS copies 128 bytes from the program's DMA address to `bounce`
   **before** mapping disk SRAM. On read, it copies from `bounce` to the DMA
   address **after** the driver restores the application mapping.
3. The SRAM entry stores the caller's SP and switches to its resident private
   stack. It rejects unsupported drive identifiers and out-of-range LBAs.
4. It computes the page/window and calls MEMDOCK while F4=00 (all HOME).
5. With the selected SRAM pair ready, it maps only the requested DOCK window,
   copies 128 bytes between the window and resident `bounce`, then unmaps it.
6. It selects the CP/M SRAM pair 4/5 again, restores F4=0F, restores the
   caller's stack, and returns status. The caller must not resume earlier.

For this build:

```text
page       = LBA // 64
offset     = (LBA % 64) * 128
slot       = [0, 2, 6, 8, 10, 12][page // 7]
chunk      = page % 7
address    = chunk * 8192 + offset
F4 mask    = 1 << chunk
```

For example LBA 448 starts page 7: select pair 2/3, chunk 0, address 0000.
For LBA 320, page 5 is chunk 5 at A000 in pair 0/1. These addresses are only
valid while that pair/window is selected; do not retain them as flat pointers.

`sram_select` sends TPI:MEMDOCK with PMR1=1 and PMR2=the even slot number.
The adapter supplies the actual legacy or modern transport. The CP/M block
entries `sram_read`/`sram_write` take HL=LBA and C=0, use the linked `bounce`
symbol, and return A=0 on success or an error/carry on failure. This is an
internal linked interface, not a separately versioned binary ABI. Do not assume
register preservation or call addresses without inspecting the build.

If restoring the application slot fails, the driver cannot safely return into
unknown low memory. It stays in HOME and halts with a red border. This is a
deliberate failed-restore policy; another host needs an equally explicit recovery
path that does not execute the wrong bank. The shared workspace/SP state makes
these entry points non-reentrant.

## Loading, using and saving the RAMDisk

At cold startup, the cartridge loader runs from HOME 8000 and receives 8KiB
pages at HOME A000. It installs and verifies them in the reserved SRAM windows.
When the target window is also A000, direct mapping would hide the source.
The special `sram_window5_copy` path moves 128-byte spans through resident
`bounce`, alternating source/destination mappings and verifying the result.
It does not borrow HOME 4000/6000 as an 8KiB staging area.

The disk contains raw CP/M filesystem bytes in SRAM, not CPC DSK track headers.
Host tools remove/add the DSK container; TAP metadata carries image geometry.
Applications use CP/M file operations normally once the image is loaded.
The cartridge contains the OS, so these images need no conventional CP/M
system tracks. Working RAMDisk data does not automatically write back to SD.

The normal session is load cartridge in slot 4, wait for preload/reload, use
CP/M applications, exit them, and run **TPSAVE** before cold restart or power-off.
Original firmware writes numbered page TAPs plus CPMSTATE.TAP; compatible modern
transport can save a single multi-record TAP. Reload uses the complete saved
image directly without PC repacking. A game's SAVE writes a CP/M file into the
RAMDisk; TPSAVE then preserves the whole disk on SD. This is disk persistence,
not a snapshot of CPU registers or the running application.

PicoVideo V4 can capture DOCK writes at video addresses as apparent screen
garbage even when HOME screen RAM remains correct. The inspected 4.2 firmware
filters those banked writes. Separate actual memory corruption from display-copy
corruption when validating this design; see the linked PicoVideo guide.

## Adapting it to another program

1. **Choose the storage contract.** For an existing CP/M application, use BDOS
   files and let the BIOS handle SRAM. For a non-CP/M program, decide whether
   it needs a byte/record store, the same CP/M directory format, or actual
   controller-port compatibility. Only the first two follow from this driver.
2. **Design the host map.** Reserve always-visible HOME code, stack, scratch
   and transport state. Identify interrupt/vector dependencies and preserve
   the host's interrupt policy across mapping changes. Do not copy CP/M's
   hard-coded F000/F500/F7B0 addresses into a host that already uses them.
3. **Parameterize ownership and restore.** Select an available boot/application
   SRAM pair, disk-pair table, page limit and normal F4/FF mapping. The original
   restores pair 4 and F4=0F; those constants must change for a different host.
   Generic code should maintain software shadows of bank-selection registers.
4. **Expose stable operations.** Wrap `read_record(lba, resident_buffer)` and
   `write_record(lba, resident_buffer)` or similar, with explicit bounds/errors.
   Copy a caller's banked buffer while its mapping is visible, or accept a
   region/chunk/offset descriptor. Split larger operations at page boundaries.
5. **Relink and retain the transport guards.** The assembly includes geometry,
   slot and transport files generated by the CP/M build. Reuse their sources,
   not a prelinked binary. Legacy and modern command sequences differ. An
   emulator's immediate replies do not justify removing hardware delays.
6. **Choose initialization and persistence.** Preload an image, initialize
   empty storage, or snapshot a modern SD service volume. Provide an explicit
   save/export action and report failures. For original firmware, retain the
   bounded TAP volumes/chunk format instead of assuming random SD-file writes.
7. **Validate hidden-buffer cases.** Test records at page/pair boundaries,
   window 5 source overlap, maximum LBA, invalid requests, restore failure,
   all-byte patterns, screen preservation and save/reload with the same bytes.
   Run both models and physical-board checks; distinguish their evidence.

For non-CP/M programs no filesystem is required to use the SRAM as record
storage. To share actual files with CP/M, implement/use its filesystem rules
and matching allocation parameters. Keeping a DSK container in SRAM would add
another layer; it is not how the current sector backend works.

## Where this can go: writable Oliger mounts on TSPico v2.x

### Existing optional-service capability

The project already contains a **read/write standard DSK adapter** in
`firmware/cpm_dsk.py`, integrated with the optional v2.x CP/M service. Its
`DskVolume` validates the container/geometry, translates 128-byte record LBAs
to file offsets, reads them, and writes exactly those bytes back through an
`r+b` file with flush. It preserves DSK track/sector headers rather than
reformatting or rewriting the whole image for each record.

For the supported geometry, its file offset is:

```text
offset = 512 + (LBA // 32) * 4352 + (LBA % 32) * 128
```

There are 32 CP/M records per track-side: a 256-byte track header plus 4096
bytes of data after the 256-byte disk header. The formula is specific to this
strict standard DSK layout; use a parsed sector map for other layouts.

Thus a v2.x program can mount a `.dsk` from SD and use it for writes as well
as reads **when the matching optional service is installed**. Stock v2.x
raw-file channels alone do not establish the CP/M mount/sector API. An installed
newer ROM alone is also insufficient. Preserve existing extension dispatch
entries when installing the service; this is a firmware-side extension, unlike
the original-1.00 SRAM backend.

In CP/M service/SD mode, a representative workflow is:

```text
CPMDISK MOUNT WORK.DSK
PIP NOTES.TXT=README.TXT
CPMDISK SAVE BACKUP.DSK
```

Put WORK.DSK in the service's configured CP/M SD folder (the published setup
uses physical `/TAP/CPM`). It must match the supported filesystem and contain
the utilities/files used here, including CPMDISK.COM if switching/export is
needed afterward. Choose persistent SD at startup, not the RAMDisk snapshot.
The PIP operation writes directory/data changes into WORK.DSK. CPMDISK SAVE
creates a separate snapshot; it is not required to make an already completed
direct-image write visible. Keep backups under distinct names. Flush/close
does not make a multi-sector CP/M file update atomic against power loss.

This path is useful for operating on the same image in Fuse and on TSPico:
close/unmount it on one system before editing it on the other, then move the
DSK without converting the filesystem. It is still not transparent controller
emulation for programs that issue Oliger hardware commands directly.

### Generalize the mount interface

A reusable component for other programs could expose a volume handle with
`mount(path, mode)`, `geometry`, `read_record`, `write_record`, `flush`, and
`unmount`, backed either by `DskVolume` on SD or the banked SRAM driver. These
names describe a proposed host interface, not commands already implemented by
stock firmware. Keep record size, geometry, write protection, error reporting
and ownership explicit. Keep the filesystem layer above this block boundary.

For callers that need ordinary SD files instead, use raw-file channels or
the native-directory service; mounting a DSK should not silently substitute
native files for its contained CP/M directory. Verify arbitrary binary writes
and the exact deployed modern channel implementation before building on it.
The existing CP/M extension's sector-write path is an alternative with a
defined, tested packet contract; do not infer that every firmware's generic
write command has equivalent behavior.

### Two useful performance/persistence modes

| Mode | Working bytes | Write behavior |
|---|---|---|
| Direct SD image | DSK on SD | Completed sector operations update that image; report flush/errors |
| Whole-image RAMDisk | TSPico SRAM | Fast local copies after bank selection; explicit export/save-back required |
| Proposed cached SD image | Bounded SRAM cache | Needs dirty-block tracking, eviction/writeback, flush/unmount and recovery policy |

Whole-image RAMDisk already exists: selecting R snapshots the current service
volume. It leaves the original SD image unchanged during the session; modern
TPSAVE writes its TAP export rather than automatically updating the original
DSK. A future **save back to mounted DSK** action should explicitly preserve
the source image's identity/geometry, offer a separate-output option, and only
report success after the output completes. Do not describe that automatic
save-back as implemented today.

Further work can add multiple volume handles/drive letters and several 160KiB
images in SRAM. It must allocate disjoint pages and retain per-drive geometry,
source path, dirty state and save destination. Those handles are different
from adding true WD1770 register emulation, which is a larger separate task.

For this existing adapter, writable-media behavior has host/service-model
coverage. Confirm the exact v2.x extension and its physical transfer behavior
on the intended hardware before calling the complete SD write path validated.

## Source map and reproducible implementation links

Repository: [TS2068 hub, CP/M 2.2 source](https://github.com/jon0x0/ts2068/tree/main/CPM_2.2_2068).
The following links pin the published implementation at revision 867060e:

| Concern | Source |
|---|---|
| SRAM selection, record I/O, restoration and page transfer | [src/sram_disk.asm](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/src/sram_disk.asm) |
| DMA/bounce glue, logical sectors and OS memory placement | [src/bios.asm](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/src/bios.asm) |
| Cold preload, geometry, saved-disk discovery and diagnostics | [src/sram_loader.asm](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/src/sram_loader.asm) |
| Explicit disk export | [src/tpsave.asm](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/src/tpsave.asm) |
| Writable DSK adapter on the Pico | [firmware/cpm_dsk.py](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/firmware/cpm_dsk.py) |
| Optional mount/read/write service | [firmware/cpm_service.py](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/firmware/cpm_service.py) |
| Host mount/snapshot utility | [src/cpmdisk.asm](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/src/cpmdisk.asm) |
| Generated slot table, transport includes and linker symbols | [tools/build.py](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/tools/build.py) |
| Legacy/modern transport adaptation | [tools/dual_transport.py](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/tools/dual_transport.py) |
| DSK/TAP/raw image tools | [tools](https://github.com/jon0x0/ts2068/tree/867060e/CPM_2.2_2068/tools) |
| Bank/screen and snapshot regression tests | [test_sram_screen.mjs](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/tools/test_sram_screen.mjs), [test_saved_ramdisk.mjs](https://github.com/jon0x0/ts2068/blob/867060e/CPM_2.2_2068/tools/test_saved_ramdisk.mjs) |

The source/build revision defines this example's ABI and map. Later code may
change them. These notes describe **CP/M 2.2**, not CP/M 3.x or a generally
transparent Oliger hardware replacement. Original-1.00 hardware boot/application
operation was reported; modern protocol and error paths also have model tests.
