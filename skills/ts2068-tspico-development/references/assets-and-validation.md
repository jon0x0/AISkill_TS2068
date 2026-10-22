# Reusable drivers, ABI and evidence

## CP/M banked RAM and host disk-image tools

The [banked-RAM/disk-image reference](banked-ram-and-disk-images.md) adds the
separate CP/M 2.2 MEMDOCK block-device example and exact links to its loader,
dual adapter and snapshot code. These are not silently substituted for the
baseline drivers below. The skill includes four MIT Python tools in scripts/:
cpm_disk.py, make_disk.py, oliger_image.py and tspico_ram_image.py, with
LICENSE-cpm-tools.txt. They require Python 3.10+, no third-party modules.

Validation of these copied tools created both 160KiB and 320KiB disks, copied
a file, converted DSK to TAP and factory volumes, decoded the volumes, converted
back to DSK, and compared all raw disk bytes and the file contents. This is host
image interoperability evidence, not a physical TSPico transfer test. Consult
the linked CP/M source for the additional native-Z80/hardware evidence.

## Assets

`assets/z80` contains original Z80 sources from the cartridge file project:

| Files | Link for |
| --- | --- |
| `layout.inc`, `tpi_legacy.asm`, `files_legacy.asm` | Original single-FIFO TAP storage |
| `layout.inc`, `tpi.asm`, `files.asm` | Modern 2.3 raw-file channels |
| `stream.asm`, added to modern files | Optional buffered sequential reader |

All execute at their linked address and use writable HOME workspace. There
are no runtime HOME/EXROM/BASIC calls, self-modifying code, renderer, keyboard,
cartridge header or automatic interrupt enabling in these core files. The host
supplies a writable stack and safe bank/interrupt policy. Drivers are serialized,
not reentrant. General-purpose registers are scratch unless an ABI result says
otherwise. Carry clear means success, carry set means A=error.

The compiled sizes at ORG `$1000` are 1107 bytes legacy, 831 modern, and 955
modern+stream. Streaming adds 124 ROM bytes. These are measured snapshots,
not size guarantees for future revisions.

## Build or include in a host

Install/provide **sjasmplus**; it is not bundled. With Python 3:

```text
python scripts/build_library.py --backend legacy --out build/legacy
python scripts/build_library.py --backend modern --out build/modern
python scripts/build_library.py --backend modern --stream --out build/stream
```

Add `--assembler PATH`, `--origin 0xNNNN` or `--workspace 0xNNNN` as needed.
The output includes a wrapper, binary, symbols and listing. The wrapper has
no entry bootstrap: the host calls labels by the resulting symbol addresses.
For native host source integration, use sjasmplus `DEFINE WORK_BASE $7800`
(a preprocessor definition), choose ORG/link position,
then include the selected files in the table's order. No generated font or
other skill folder is needed.

Changing WORK_BASE relocates the 1 KB workspace only. Legacy response scratch
and modern stream buffers have separate equates. Check code/workspace/payload/
stack/display overlap in the host; the helper cannot infer its memory map.
Initialize workspace before use. In particular clear STREAM_ACTIVE before the
first `stream_open`, which closes any previously active stream first. Reinitializing
an active library without closing its handles can leak Pico resources.

## Modern ABI

| Entry | Contract |
| --- | --- |
| `f_open` | A=stream, HL=NUL path, DE=NUL mode (`rb`, `wb`, `ab` etc.); path <=191 bytes |
| `f_close` | A=stream |
| `f_read` | A=stream, B=1..255 (0 means 255), HL=destination; BC=bytes received, 0 EOF |
| `f_write` | A=stream, B=1..96, HL=source; rejects `$17` |
| `f_load` | HL=path, DE=buffer, BC=capacity; FILE_DONE=bytes loaded |
| `f_save` | HL=path, DE=source, BC=length; entire input checked before truncating |
| `stream_open` | HL=NUL path; reserves stream 202 |
| `stream_get` | NC/A=next byte, C/A=7 EOF or other error |
| `stream_close` | Discard buffered input and close |

Streams 200/201 are the file/directory defaults in the example layout; avoid
conflicts with the host. Whole-file helpers close on error. On E4, `f_load`
keeps a bounded prefix and reports FILE_DONE; the host decides whether that
partial buffer is usable. The stream reader closes on EOF; callers close it
on other errors/abort. STREAM_TOTAL counts delivered bytes modulo 2^32.

## Legacy ABI

| Entry | Contract |
| --- | --- |
| `legacy_capabilities` | NC/A=7 (directory text, TAP CODE load, TAP CODE save) |
| `legacy_directory` | Captures text in LEGACY_REPLY_BUFFER; LEGACY_USED is length |
| `legacy_chdir` | HL=NUL folder name, `..` or `/`; changes global cwd |
| `legacy_mount` | HL=NUL filename or `&nnn` in current folder |
| `f_load` | HL=filename/index, DE=buffer, BC=capacity; first TAP CODE pair, FILE_DONE on success |
| `f_save` | HL=1..10 uppercase letters/digits basename, DE=source, BC=length; adds `.tap` on firmware |

The core has no overwrite dialog: the host confirms before calling f_save.
SAVE closes the prior mount to disable append, and payload can contain all
256 byte values. It does not encode arbitrary raw files. The raw channel
entries f_open/f_close/f_read/f_write return E3 without accessing the ports.
FILE_DONE remains 0 on a failed whole-TAP load; payload memory may still have
received data before a checksum error. Do not display it as a verified file.

LEGACY_PHASE and LEGACY_BYTE help diagnose failures: phases 1 preheader/ACK,
2 initial ready, 3 command body, 4 final command-ready, 5 LOAD, 6 SAVE header,
7 SAVE data. LEGACY_BYTE is the last polled FIFO byte, not a firmware report.
The capture has a finite byte budget. E0 cannot automatically recover the old
transport; reestablish a clean command boundary before retrying.

## RAM ownership

| Area | Default |
| --- | --- |
| Core workspace | `$7800–$7BFF`, relocatable by WORK_BASE |
| Legacy verbose/directory scratch | `$E000–$F7FF`, includes bounded NUL-terminated text |
| Modern optional stream state | `$7C00–$7C07` |
| Modern optional stream refill | `$E000–$E0FE` |
| Demonstrator payload buffer (not mandatory library storage) | `$A000–$DFFF` |

Legacy replies use separate scratch so they never overwrite loaded/saved
payload bytes. Do not place a legacy payload inside reply scratch. Do not
link these unnamespaced backend files together: labels/workspace overlap.
Implement namespaced backends and an explicit shared adapter before attempting
a combined build. Only the selected backend and optional stream file need be
linked in a size-constrained program.

## Evidence and sources

The reference project is
`C:/Users/Jon/Documents/ChatGPT/TS2068_TSPicoAnalysis` on the original machine.
That path is a provenance aid, not a dependency for this skill. Its
`docs/LEGACY-TEST.md`, `docs/VIRTUAL-DOCK-TEST.md`, source, Python tests and build
reports contain the worked demos and detailed deployment procedure.

On 2026-10-17 the user reported **"OK that worked"** after testing the legacy
virtual cartridge with firmware 1.00, MicroPython 1.20.0, default ROM 1.00,
board V2.2. The supplied tested image's DCK SHA256 was
`6a4910428ab3183ba3dc55c56ff900180e2740f1d18ef65c51f39e0004a361e0`.
This is a hardware success report for that test flow. No individual per-operation
log, throughput measurement or bus capture was supplied. Do not promote all
host coverage to hardware validation.

Ten legacy host tests passed: assembled Z80 code against recovered pre-dual-port
LOAD_TS/SAVE_TS/END_MSG, modeled command dispatch/directory pagination, and own
keyboard/display. Coverage included all byte values, empty files, save/reopen,
directory bounds, checksums/types/capacity, 16 KB data and AROS handoff. The
frozen v1.00 bytecode was not executed in that model. Its absolute watchdog
thread was disabled; the transfer loop was timed separately (~1.59 seconds
Z80 time for 16 KB; Pico/SD latency excluded). The modern 12-test suite used
real channel/catalog logic with a protocol model. Fuse 1.7.0 TS2068 cold-boot
checks passed all three cartridge profiles; Fuse does not emulate TSPico.

Primary evidence, already inspected for this work:

- [Original project](https://github.com/timex-sinclair-projects/TS-Pico):
  original v1 UF2 and manuals/TAP programs; [firmware image](https://github.com/timex-sinclair-projects/TS-Pico/blob/f79cef005292d9bd5572fa440c95df9ebcaa8d0f/firmware/tspicofirmware%20v1.uf2)
  has SHA256 `20350721dbc473bac2c4a35c85fe2607d94776cf9fecf9bc55ff6b26dfac7573`.
  Decoding UF2 by block target address reveals the original version string,
  command names, directory formats and end-of-list prompt. Strings alone do
  not establish function bytecode identity.
- [Recovered pre-dual-port I/O handlers](https://github.com/timex-sinclair-projects/tspico-firmware-build/blob/b2758a5ad0a444ebedb052bb2c532b1e71975712/src/TS/tspico_io.py):
  LOAD_TS/SAVE_TS/END_MSG still use literal `$40` FIFO tokens even though the
  initial repository also introduced dual-port PIO. Select functions, not a
  whole-version assumption, when reconstructing older behavior.
- [Exposed legacy dispatcher](https://github.com/timex-sinclair-projects/TS-Pico/blob/8ec5a79bea23a0ea6dfd319ae207594f01c10239/src/src_new_v1.1/TS/tspico.py):
  PROCESS_CMD, DIR, SEND_MSG/SEND_MSG2 and command tables. This is later legacy
  source, not source proof for every frozen v1.00 handler.
- [Modern low-level code](https://github.com/timex-sinclair-projects/tspico-firmware-build/blob/6b72847e1121112e438d6d4c2ec41835df90f940/src/TS/tspico_io.py),
  [dispatcher](https://github.com/timex-sinclair-projects/tspico-firmware-build/blob/6b72847e1121112e438d6d4c2ec41835df90f940/src/TS/tspico.py),
  [channels](https://github.com/timex-sinclair-projects/tspico-firmware-build/blob/6b72847e1121112e438d6d4c2ec41835df90f940/src/TS/channels.py), and
  [current protocol description at that commit](https://github.com/timex-sinclair-projects/tspico-firmware-build/blob/6b72847e1121112e438d6d4c2ec41835df90f940/docs/PROTOCOL.md).
- [Gustavo's original protocol specification](https://github.com/timex-sinclair-projects/tspico-firmware-build/blob/6b72847e1121112e438d6d4c2ec41835df90f940/docs/LOW-LEVEL-PROTOCOL-V5.TXT),
  [ROM-derived correction](https://github.com/timex-sinclair-projects/tspico-firmware-build/blob/6b72847e1121112e438d6d4c2ec41835df90f940/docs/rom-analysis/PROTOCOL_FROM_ROM.md), and
  [legacy/dual-port comparison](https://github.com/timex-sinclair-projects/tspico-firmware-build/blob/6b72847e1121112e438d6d4c2ec41835df90f940/docs/SAVE_1.1C_VS_1.5.md).

When source/docs disagree, trace the relevant deployed handler and exact ROM
client rather than copying a preliminary timing constant or treating old
documentation as modern wire truth. `tspico_io.py` and Gustavo's specification
are now publicly available in firmware-build; the original project's small
filesystem tree alone does not contain all frozen-module source.
