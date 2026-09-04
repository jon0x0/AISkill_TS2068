# Bundled utilities and templates

## Contents

1. [Select a utility](#select-a-utility)
2. [DCK descriptor contract](#dck-descriptor-contract)
3. [Pack images](#pack-images)
4. [Inspect images](#inspect-images)
5. [Extract stored ranges with `dckls`](#extract-stored-ranges-with-dckls)
6. [Convert BASIC TAPs in a browser](#convert-basic-taps-in-a-browser)
7. [Create ECM artwork with Retro Pixel Converter](#create-ecm-artwork-with-retro-pixel-converter)
8. [Run Fuse deterministically](#run-fuse-deterministically)
9. [Handle Fuse on macOS](#handle-fuse-on-macos)
10. [Use the Python module](#use-the-python-module)
11. [Adapt assembly templates](#adapt-assembly-templates)
12. [Verify outputs](#verify-outputs)

## Select a utility

| Resource | Use |
|---|---|
| `scripts/pack_dck.py` | Build a DOCK DCK from a flat 64K image or exact 8K chunks; optionally emit a physical BIN. |
| `scripts/inspect_dck.py` | Strictly parse a DCK, report descriptors/hashes/header, and optionally expand it to 64K. |
| `scripts/dck_to_picorom.py` | Convert a sparse DCK directly into one contiguous 64K physical ROM image, filling absent/RAM-only chunks. |
| [zx81-utils `dckls`](https://github.com/ryangray/zx81-utils) | External DCK listing tool whose `-d` mode extracts stored contiguous ROM/RAM spans. |
| [TS2068 TAP to Cartridge Builder](https://timex-sinclair-projects.github.io/2068-TAP-To-Cart/) | External browser tool designed for converting TS2068 BASIC TAP programs, with optional CODE blocks, into BIN and DCK. |
| [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) | External browser tool for creating TS2068 ECM bitmap and 8×1 attribute planes and exporting binary data or TAP blocks. |
| `scripts/run_fuse_debug.py` | Run a DCK under Fuse with a debugger command file and capture output. |
| `scripts/dck_format.py` | Import strict parsing/building helpers from custom Python tooling; it has no CLI. |
| `assets/machine-code-aros.asm` | Start a Pasmo-compatible chunk-4 machine-code AROS. |
| `assets/home-bank-gateways.asm` | Adapt HOME-RAM DOCK/EXROM switching patterns. |

Use Python 3.10+; the scripts require only the standard library. Run scripts by their complete path so the sibling `dck_format.py` import resolves. Quote paths containing spaces.

## DCK descriptor contract

The nine-byte header is bank ID plus eight descriptors:

- `0`: absent, no payload;
- `1`: uninitialized RAM, no payload;
- `2`: ROM, followed by exactly 8192 bytes;
- `3`: initialized RAM, followed by exactly 8192 bytes.

These tools emit DOCK bank ID 0. Stored payloads follow in chunk-number order. DCK offsets are container offsets, not CPU addresses. Flat BIN output is always eight consecutive 8K chunks. Fill bytes represent absent/uninitialized ranges but do not provide writable hardware.

## Pack images

Full 64K input:

```powershell
python scripts\pack_dck.py build\app.dck --raw64 build\app.bin --physical-bin build\app-physical.bin
```

Selected chunks:

```powershell
python scripts\pack_dck.py build\app.dck --rom 4=build\c4.bin --rom 5=build\c5.bin --ram 6 --ram-image 7=build\c7.bin --physical-bin build\app.bin --fill 0xFF
```

Repeat `--rom`, `--ram`, or `--ram-image` as needed. Never combine `--raw64` with per-chunk options. Expect hard failures for duplicate/out-of-range chunks, incorrect sizes, descriptor/image mismatch, or malformed raw64 input. Treat the RAM-to-flat warning as a hardware design warning, not cosmetic output.

## Inspect images

```powershell
python scripts\inspect_dck.py build\app.dck --json build\app.json --flat-output build\expanded.bin --fill 0xFF
```

Retain the printed/saved SHA-256 values. Parsing rejects invalid descriptors, truncation, and trailing bytes. Header recognition covers stored chunk-4 BASIC/machine-code AROS and stored chunk-0 LROS. It fails when a recognized header maps cartridge chunk 3 at startup and warns when an AROS deliberately maps lower chunks 0-2.

## Extract stored ranges with `dckls`

Install or build `dckls` from [zx81-utils](https://github.com/ryangray/zx81-utils), then run:

```powershell
dckls -d file.dck
```

The dump filename records the DCK segment and mapped start address. A contiguous DOCK ROM beginning in chunk 0 becomes `file_DOCK_0x0000.rom`; one beginning in chunk 4 becomes `file_DOCK_0x8000.rom`. The tool emits one `.rom` or `.ram` file per contiguous same-type span, so gaps, memory-type changes, and multiple DCK segments may create multiple outputs. Dump mode requires a named input file.

Do not assume every extracted file is a complete physical image. Eight contiguous DOCK ROM chunks produce one 65536-byte file, but sparse DCKs do not. `dckls` does not synthesize missing chunks or combine separated spans into a padded physical image. Use `python scripts/dck_to_picorom.py input.dck physical.bin` for a direct conversion, or `scripts/inspect_dck.py input.dck --flat-output physical.bin --fill 0xFF` when a full inspection report is also wanted. Both default to `$FF` padding. See the PicoROM28 example in [proven-patterns.md](proven-patterns.md#build-the-contiguous-picorom-image).

## Convert BASIC TAPs in a browser

Use the [TS2068 TAP to Cartridge Builder](https://timex-sinclair-projects.github.io/2068-TAP-To-Cart/) for TS2068 BASIC TAP programs. It processes the TAP locally in the browser, lets the user select one BASIC program and optional CODE blocks, exposes their load addresses plus AROS start/reserved/autostart options, and downloads both `.BIN` and `.DCK` outputs.

Apply it only within its stated scope. It builds BASIC AROS in DOCK chunks 4-7 and warns above the 32K content limit. It does not produce LROS or automatically adapt arbitrary Spectrum machine code, ROM calls, interrupts, display assumptions, or banking. Use the custom packer, assembly gateways, and deterministic emulator workflow for those projects.

For repeatable command-line builds, use `tapToCart.py` from the [source repository](https://github.com/timex-sinclair-projects/2068-TAP-To-Cart):

```powershell
python tapToCart.py program.tap
```

Use its documented INI mode for subfile choice, appended binaries, custom addresses, output names, reserved space, or autostart options. Archive the input TAP, configuration file, tool revision, output hashes, and emulator results.

## Create ECM artwork with Retro Pixel Converter

Use [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) as an artwork-authoring step, not as the cartridge packer:

1. Load the source image and select **Timex Extended Color (256×192, 8×1 attrs)**.
2. Adjust crop, scale, palette, and dithering while checking the preview.
3. Export binary data for direct build-script ingestion, or export a TAP for interchange/viewer testing.
4. When using TAP, choose **Attributes first in .TAP** if the tape/viewer path should load colors before pixels.
5. Verify that the bitmap and attribute planes are each exactly 6144 bytes and record their hashes.

The Elite ECM title uses **Sierra Lite** dithering. Preserve the chosen display mode, dithering setting, source artwork, and exported hashes together when reproducibility matters.

An ECM TAP contains `ecm-pix`, loaded at `$4000`, and `ecm-atr`, loaded at `$6000`. Each is a separate 6144-byte CODE block. The attributes use one byte per 8×1 strip in the same interleaved layout as the pixels.

Do not copy the TAP addresses or order blindly into a cartridge layout. Extract the planes, place them wherever the chunk map permits, and have cartridge code copy or decode them into HOME `$4000-$57FF` and `$6000-$77FF`. In the Elite example the bitmap is stored at DOCK `$8100-$98FF`, while the attributes are stored at DOCK `$4000-$57FF`. The converter does not supply AROS headers, bank-switching, ECM entry/exit, animation, DCK descriptors, or physical-ROM packaging.

## Run Fuse deterministically

Create a Fuse debugger text program such as:

```text
breakpoint 0x8008
commands 1
print z80:pc
print z80:sp
print z80:af
print ula:tstates
exit
end
```

Then run:

```powershell
python scripts\run_fuse_debug.py build\app.dck commands.txt --machine ts2068 --speed 5000 --timeout 45 --output build\trace.txt
```

Override Fuse with `--fuse PATH`. Defaults are `C:\Program Files (x86)\Fuse\fuse.exe` on Windows, `/Applications/Fuse.app/Contents/MacOS/Fuse` on macOS, and `fuse` elsewhere. The launcher disables sound/loading sound, passes the command-file contents to `--debugger-command`, captures stdout+stderr, and returns Fuse's exit code. A timeout usually means the breakpoint or `exit` path was not reached. Keep breakpoint numbering explicit and archive the command file with the DCK hash and trace.

Fuse 1.6.0 debugger expressions should be kept simple in unattended command files. In this Windows build, both nested dynamic memory expressions such as `print peek peek16 0x7800` and the seemingly simple `print peek 0x7800` form are rejected as invalid debugger commands and can produce repeated GUI error dialogs. Register expressions such as `print z80:pc`, `print z80:sp`, and `print spectrum:frames` are confirmed safe. Do not attempt unattended memory reads until the exact supported dereference grammar has been verified interactively with a disposable Fuse instance. Resolve pointers and memory through a tested helper or temporary in-program diagnostic counters instead; always give every breakpoint command block its own `exit 0` before `end`.

## Handle Fuse on macOS

Do not state categorically that Fuse for macOS lacks debugger commands. Current official source declares the `debugger_command` setting, preserves `argv` in `fusepb/main.m`, and calls `debugger_command_evaluate` from `fuse.c`. The native app does lack a GUI script-file loader, a `--debugger-command-file` option, and a supported remote command/reply interface.

Run the inner executable directly, or pass the `.app` path to this launcher:

```bash
python3 scripts/run_fuse_debug.py build/app.dck commands.txt --fuse /Applications/Fuse.app --machine ts2068 --output build/trace.txt
```

Do not use Finder or `open -a` for a capture that depends on inherited stdout/stderr and the child exit code. Qualify Mac support as source-supported but release-unverified until a local smoke test breaks at `$8008`, prints `z80:pc`, executes `exit`, produces captured output, and terminates cleanly.

If the packaged app fails, an upstream fix should add `--debugger-command-file`, read/evaluate it after machine and media initialization, preserve output/exit status, test the native bundle, and code-sign/notarize it. A post-startup interactive scripting service would additionally need a pipe/socket protocol and command/reply framing; the current startup program is not a remote debugger API.

## Use the Python module

Import these from `scripts/dck_format.py` when extending build tooling:

- `parse_dck(data)` returns immutable `DCK(bank_id, descriptors, chunks)` and validates the complete container;
- `build_dck(descriptors, chunks, bank_id=0)` validates and serializes;
- `flat_image(dck, fill=0xFF)` expands to 65536 bytes;
- `header_summary(dck)` recognizes basic AROS/LROS header fields;
- `CHUNK_SIZE`, `CHUNK_COUNT`, and descriptor constants prevent duplicated magic numbers.

Do not treat `header_summary` as complete OS validation.

## Adapt assembly templates

`assets/machine-code-aros.asm` produces an exact chunk-4 image with a machine-code AROS header, entry `$8008`, stack in HOME chunk 3, and an example chunk-5-to-HOME-6 copy. Adapt the header, RAM, stack, interrupt policy, and application code; never cover the active stack.

`assets/home-bank-gateways.asm` contains chunk-4 DOCK selection/restoration and a stock EXROM chunk-0 gateway. Copy required code into an unaffected HOME chunk. Replace `EXROM_ENTRY`; place stack, shadows, return path, and gateway in writable HOME memory; initialize HSR/DECR shadows accurately; and adapt service-specific register preservation.

## Verify outputs

1. Check every input is exactly 8K or 64K as applicable.
2. Build DCK and physical BIN deterministically.
3. Inspect the DCK and save JSON/hashes.
4. Compare expanded DCK bytes with intended physical bytes.
5. Trace startup and required checkpoints under the TS2068 Fuse model.
6. Validate physical hardware separately, especially RAM descriptors and electrical decoding.

## Audio and browser demo tools

[speech2ay](https://github.com/jon0x0/speech2ay) supplies audio2aydac, speech2ay, ayfit and aydemo, with documented Z80 players and TS2068 exports. Use the audio-development skill for sample timing, optimization and compact storage estimates. Its `web/` adapter demonstrates automatic DCK loading from live TSRun modules; the TSRun web-demo skill records the integration and validation workflow.
