# Utilities for TS2068 Cartridge Development

**When to read:** Use for DCK/BIN tools, validation commands, Fuse automation and reusable assembly templates. For audio conversion and playback experience, see [audio development](TS2068_AUDIO_GUIDE.md); for browser cartridge demos, see [TSRun embedding](TS2068_BROWSER_DEMOS.md).
The cartridge-development skill includes small, dependency-free Python utilities for creating and checking Fuse DCK cartridge images, expanding them into physical 64K binaries, and running deterministic Fuse debugger sessions. It also includes two Pasmo-compatible Z80 assembly templates and documents useful external cartridge tools.

## Contents

1. [Requirements and paths](#requirements-and-paths)
2. [DCK descriptor values](#dck-descriptor-values)
3. [`pack_dck.py`](#pack_dckpy)
4. [`inspect_dck.py`](#inspect_dckpy)
5. [External `dckls` extractor](#external-dckls-extractor)
6. [TS2068 TAP to Cartridge Builder](#ts2068-tap-to-cartridge-builder)
7. [Retro Pixel Converter](#retro-pixel-converter)
8. [`run_fuse_debug.py`](#run_fuse_debugpy)
9. [Fuse debugger automation on macOS](#fuse-debugger-automation-on-macos)
10. [`dck_format.py`](#dck_formatpy)
11. [Assembly templates](#assembly-templates)
12. [Recommended end-to-end workflow](#recommended-end-to-end-workflow)
13. [Common problems](#common-problems)

## Requirements and paths

- Python 3.10 or later is recommended. The Python tools use only the standard library.
- `run_fuse_debug.py` requires Fuse. It defaults to `C:\Program Files (x86)\Fuse\fuse.exe` on Windows, `/Applications/Fuse.app/Contents/MacOS/Fuse` on macOS, and `fuse` on other systems. Override this with `--fuse` when necessary.
- The assembly templates use syntax compatible with Pasmo. Copy them into a project and adapt them; they are not complete applications.
- Run a utility by its complete path, or change to the skill directory first. Quote paths that contain spaces.

The examples below assume the current directory is `ts2068-cartridge-development`:

```powershell
python scripts\pack_dck.py --help
python scripts\inspect_dck.py --help
python scripts\run_fuse_debug.py --help
```

## DCK descriptor values

A Fuse DCK begins with one bank-identification byte followed by eight chunk descriptors. Payload bytes then follow only for descriptors that require an initial image.

| Value | Meaning | 8K payload stored in DCK? | Physical-cartridge implication |
|---:|---|---|---|
| `0` | absent | no | flat output fills the range with `--fill` |
| `1` | uninitialized RAM | no | requires actual writable cartridge RAM; flat output is only fill bytes |
| `2` | ROM | yes | ordinary read-only cartridge content |
| `3` | initialized RAM | yes | Fuse starts with supplied bytes, but real hardware must provide writable RAM |

The tools create DOCK-bank DCK files with bank ID `0`. Each stored payload must be exactly 8192 bytes. A DCK is a container, so its file offsets are not cartridge CPU addresses. A physical binary is eight consecutive 8K ranges and is always exactly 65536 bytes.

## `pack_dck.py`

[`pack_dck.py`](skills/ts2068-cartridge-development/scripts/pack_dck.py) creates a DCK from either a complete 64K image or individual chunk files. It can create a matching flat physical binary in the same operation.

### Package a complete 64K ROM image

```powershell
python scripts\pack_dck.py build\program.dck `
  --raw64 build\program.bin `
  --physical-bin build\program-physical.bin
```

`--raw64` requires exactly 65536 bytes and marks all eight chunks as ROM. It cannot be combined with per-chunk options.

### Package selected chunks

```powershell
python scripts\pack_dck.py build\program.dck `
  --rom 4=build\chunk4.bin `
  --rom 5=build\chunk5.bin `
  --ram 6 `
  --ram-image 7=build\chunk7-initial.bin `
  --physical-bin build\program-physical.bin `
  --fill 0xFF
```

Options may be repeated:

- `--rom CHUNK=FILE` stores an 8192-byte ROM payload.
- `--ram CHUNK` declares uninitialized Fuse RAM without storing a payload.
- `--ram-image CHUNK=FILE` stores an 8192-byte initialized RAM payload.
- `--physical-bin FILE` also writes an eight-chunk flat image.
- `--fill VALUE` chooses the byte used for absent and uninitialized-RAM ranges in flat output; it defaults to `$FF` and accepts forms such as `0x00`, `0xFF`, or `255`.

The tool rejects duplicate chunk declarations, chunk numbers outside 0-7, incorrect payload sizes, invalid combinations, and a `--raw64` file of the wrong length. If the DCK describes RAM, it warns that a flat binary cannot reproduce writable DCK RAM hardware.

## `inspect_dck.py`

[`inspect_dck.py`](skills/ts2068-cartridge-development/scripts/inspect_dck.py) strictly parses a DCK and prints a JSON report containing:

- resolved input path, byte length, and SHA-256 hash;
- bank ID and all eight descriptors;
- mapped address and SHA-256 hash for every stored chunk;
- a recognized BASIC AROS, machine-code AROS, or LROS header summary when present.

```powershell
python scripts\inspect_dck.py build\program.dck `
  --json build\program-report.json `
  --flat-output build\program-expanded.bin `
  --fill 0xFF
```

- `--json FILE` saves the printed report.
- `--flat-output FILE` writes a 65536-byte expansion.
- `--fill VALUE` supplies bytes for absent or uninitialized chunks in that expansion.

Parsing fails for invalid descriptors, truncated chunk data, or trailing bytes. When a recognizable cartridge header declares cartridge chunk 3 active at startup, inspection fails because that mapping is unsafe for the normal TS2068 handoff. A nonstandard AROS mapping of lower chunks 0-2 produces a warning and requires deliberate validation.

## External `dckls` extractor

The [zx81-utils project](https://github.com/ryangray/zx81-utils) includes `dckls`, a C utility that lists a TS2068 DCK and can extract its stored ROM and initialized-RAM payloads:

```powershell
dckls -d file.dck
```

When a contiguous DOCK ROM span begins in chunk 0, this creates `file_DOCK_0x0000.rom`. The start address in the name reflects the first stored chunk, so a chunk-4-only image instead creates `file_DOCK_0x8000.rom`. The utility writes one output file for each contiguous span of the same memory type; gaps, ROM/RAM changes, or multiple DCK segments can therefore produce several files. Initialized-RAM spans use the `.ram` extension. Dump mode requires an input filename rather than standard input.

This is extraction, not unconditional 64K flattening. A DCK containing eight contiguous DOCK ROM chunks naturally produces one 65536-byte ROM file, but a sparse image can produce one or more shorter files whose names record their mapped start addresses. When physical hardware requires an exact 64K image with absent ranges padded, use the bundled inspector instead:

```powershell
python scripts\inspect_dck.py file.dck `
  --flat-output file-physical.bin `
  --fill 0xFF
```

Build or install `dckls` according to the zx81-utils repository and ensure it is on `PATH`. Its human-readable DCK report goes to standard output, while dump-file notices go to standard error.

## TS2068 TAP to Cartridge Builder

The [browser-based TS2068 TAP to Cartridge Builder](https://timex-sinclair-projects.github.io/2068-TAP-To-Cart/) is designed for TS2068 BASIC TAP programs. It converts a TS2068 `.TAP` containing a BASIC program into both an emulator `.DCK` and an EPROM-oriented `.BIN`. Processing is performed locally in the browser; the selected file is not uploaded.

The interface can:

- select one BASIC program from a multi-block TAP;
- optionally include CODE blocks at their original or edited load addresses;
- set the BASIC start address and reserved HOME-memory bytes;
- preserve a TAP autostart line or request autostart when the program has none;
- download the completed BIN and DCK directly.

This is a convenient path for turning suitable TS2068 BASIC software into BASIC Application ROM-Oriented Software (AROS). Its BIN is padded to the next 8K boundary, and its normal cartridge layout uses DOCK chunks 4-7, giving a maximum practical AROS content area of 32K. It does not convert arbitrary Spectrum machine-code programs, generate Language ROM-Oriented Software (LROS), solve ROM-call incompatibilities, or replace the custom banking and debugging work needed for ports such as Elite.

The [project repository](https://github.com/timex-sinclair-projects/2068-TAP-To-Cart) also provides the Python `tapToCart.py` command-line version. A direct conversion uses:

```powershell
python tapToCart.py program.tap
```

For multi-file selection, appended binaries, custom output names, addresses, or autostart control, use the repository's documented INI-file mode. The browser and command-line implementations are intended to produce the same cartridge format.

## Retro Pixel Converter

[Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) is a browser-based image conversion tool that includes a **Timex Extended Color (256×192, 8×1 attrs)** mode. Use it to prepare ECM artwork before the cartridge packing step:

1. Load the source artwork and select the Timex Extended Color display mode.
2. Adjust framing, palette, and dithering while checking the ECM preview.
3. Export binary data for a custom build pipeline, or export a TAP for interchange and viewer testing.
4. For a TAP, enable **Attributes first in .TAP** when the tape/viewer workflow should load colors before the visible bitmap.
5. Verify and archive the exported plane lengths and hashes before inserting them into cartridge chunks.

The Elite cartridge's ECM title artwork uses **Sierra Lite** dithering in Retro Pixel Converter. Record the selected conversion and dithering settings with the source image so the exact artwork can be regenerated later.

The ECM TAP carries two CODE blocks: `ecm-pix`, 6144 bytes for `$4000-$57FF`, and `ecm-atr`, 6144 bytes for `$6000-$77FF`. The attribute plane uses one byte per 8×1 pixel strip and follows the same interleaved screen layout as the bitmap plane.

For cartridge use, separate image authoring from memory placement. Extract the two 6144-byte planes and put them at addresses chosen by the cartridge map; the display routine copies or decodes them into their HOME display destinations. The Elite example stores the bitmap at DOCK `$8100-$98FF` and the attributes at DOCK `$4000-$57FF`. The TAP's load addresses and attributes-first ordering do not impose those cartridge locations. This converter does not generate an AROS header, bank-switching or mode-transition code, a reveal animation, DCK descriptors, or a physical ROM image.

## `run_fuse_debug.py`

[`run_fuse_debug.py`](skills/ts2068-cartridge-development/scripts/run_fuse_debug.py) launches a DCK under Fuse without requiring manual debugger operation. It passes the complete contents of a text file to Fuse as a debugger command program and captures standard output and error together.

Example `commands.txt`:

```text
breakpoint 0x8008
commands 1
print z80:pc
print z80:sp
print z80:af
print z80:bc
print z80:de
print z80:hl
print ula:tstates
exit
end
```

Run it with:

```powershell
python scripts\run_fuse_debug.py build\program.dck commands.txt `
  --machine ts2068 `
  --speed 5000 `
  --timeout 45 `
  --output build\fuse-trace.txt
```

Options:

- `--fuse PATH` overrides the Fuse executable.
- `--machine NAME` defaults to `ts2068`.
- `--speed PERCENT` defaults to `5000` for faster unattended execution.
- `--timeout SECONDS` defaults to 45 seconds.
- `--output FILE` saves combined output; without it, output is printed.

The launcher disables sound and loading sound to improve deterministic unattended runs. It returns Fuse's process exit code. A timeout raises an error, usually indicating that the breakpoint was never reached, the debugger program did not issue `exit`, the machine model was wrong, or startup crashed first.

Fuse debugger command numbering depends on breakpoint creation order. Keep command files small, number their `commands N` blocks deliberately, and end a capture path with `exit`. Record the DCK hash, command file, machine model, Fuse version, and captured output together.

## Fuse debugger automation on macOS

The native Fuse for macOS application has an interactive debugger, but it does not expose a graphical debugger-script loader, a `--debugger-command-file` option, or a supported remote debugger console. That can make it appear that the Mac port has no scripting interface.

Current official source shows that the startup interface itself is present: [`settings.dat`](https://sourceforge.net/p/fuse-for-macosx/fuse/ci/master/tree/settings.dat) declares `debugger_command`, [`main.m`](https://sourceforge.net/p/fuse-for-macosx/fuse/ci/master/tree/fusepb/main.m) preserves terminal arguments for `fuse_init`, and [`fuse.c`](https://sourceforge.net/p/fuse-for-macosx/fuse/ci/master/tree/fuse.c) evaluates the supplied command after emulator initialization. This is source-level verification, not a runtime certification of every released/notarized app bundle.

For the existing interface, launch the executable inside the application bundle directly. Do not launch by double-clicking in Finder, and avoid `open -a Fuse --args` for unattended tracing because `open` returns separately and does not provide straightforward child-process output or exit-code capture.

```bash
python3 scripts/run_fuse_debug.py build/program.dck commands.txt \
  --fuse /Applications/Fuse.app/Contents/MacOS/Fuse \
  --machine ts2068 --output build/fuse-trace.txt
```

The launcher now recognizes either `/Applications/Fuse.app` or its inner executable and passes the multiline command text as one argument without shell quoting. Before relying on a particular Mac release, use a small command program that breaks at `$8008`, prints `z80:pc`, and issues `exit`. Success means the trace contains the expected PC and the process terminates normally. Also test a path containing spaces and confirm standard output/error are captured.

If that smoke test fails, check the inner executable for `--debugger-command` rather than assuming the interactive Cocoa debugger implies automation support. A minimal upstream-quality implementation would:

1. add a `--debugger-command-file PATH` setting or early command-line option;
2. read the file as UTF-8 and pass its complete contents to `debugger_command_evaluate` after machine/media initialization;
3. preserve debugger `print` output on standard output and propagate the debugger `exit` value as the process exit code;
4. add macOS tests for multiline breakpoint handlers, `.dck` startup, output capture, and clean termination;
5. rebuild, code-sign, and notarize the application bundle.

That file option would remove awkward multiline command-line quoting. A genuinely interactive automation API—sending commands after startup and receiving structured replies—would require additional pipe/socket protocol and debugger-loop work; it is not the same feature as the existing startup command program. Until an actual Mac smoke test passes, describe the workflow as source-supported but release-unverified and keep Windows/Linux Fuse or another deterministic emulator available for authoritative traces.

## `dck_format.py`

[`dck_format.py`](skills/ts2068-cartridge-development/scripts/dck_format.py) is the shared Python library used by the packer and inspector. It has no command-line interface. Its useful public pieces are:

- constants for chunk size/count and descriptor values;
- `DCK`, an immutable parsed-image data class;
- `parse_dck(data)` for strict container parsing;
- `build_dck(descriptors, chunks, bank_id=0)` for deterministic serialization;
- `flat_image(dck, fill=0xFF)` for 64K expansion;
- `header_summary(dck)` for recognized AROS/LROS fields.

Example from a script placed beside or configured to import the skill's `scripts` directory:

```python
from pathlib import Path
from dck_format import flat_image, parse_dck

dck = parse_dck(Path("build/program.dck").read_bytes())
Path("build/program.bin").write_bytes(flat_image(dck))
```

`header_summary` is a convenience check rather than a complete operating-system validator. It recognizes headers only when their containing chunk is stored in the DCK.

## Assembly templates

### `machine-code-aros.asm`

[`machine-code-aros.asm`](skills/ts2068-cartridge-development/assets/machine-code-aros.asm) is a minimal machine-code Application ROM-Oriented Software (AROS) chunk-4 image:

- origin `$8000`;
- eight-byte machine-code AROS header;
- autostart entry `$8008`;
- only cartridge chunk 4 declared at startup;
- stack placed in HOME chunk 3;
- example copy from cartridge chunk 5 to HOME chunk 6;
- padding through `$9FFF` with `$FF` to produce exactly 8192 bytes.

Adapt the stack, RAM initialization, interrupts, header chunk specification, and main entry. Do not enable cartridge chunk 3 over the template's stack.

### `home-bank-gateways.asm`

[`home-bank-gateways.asm`](skills/ts2068-cartridge-development/assets/home-bank-gateways.asm) contains patterns for:

- selecting a DOCK data chunk while keeping resident chunk-4 code visible;
- restoring the chunk-4-only mapping;
- entering the stock EXROM safely through unaffected HOME RAM while preserving HSR, DECR, and interrupt policy.

Copy and assemble the required gateway into a HOME chunk that remains visible throughout the transition. Replace the `EXROM_ENTRY` placeholder, ensure the stack and shadow variables are writable and uncovered, initialize `HSR_SHADOW` and `DECR_SHADOW` to the real machine state, and adjust register preservation for the called service. Treat the file as an adaptable pattern, not a universal drop-in routine.

## Recommended end-to-end workflow

1. Assemble or generate exact 8192-byte chunks, or one exact 65536-byte flat image.
2. Build the DCK and physical binary with `pack_dck.py`.
3. Inspect the DCK with `inspect_dck.py`; retain its JSON report and hashes.
4. Compare the expanded flat image with the intended physical binary.
5. Run deterministic startup and state-capture command files with `run_fuse_debug.py`.
6. Verify the CPU-visible chunk map, program counter, stack, interrupts, display state, and relevant RAM at checkpoints.
7. Test the exact flat binary on the intended physical cartridge hardware.

## Common problems

- **Chunk file is rejected:** make it exactly 8192 bytes; do not pass an entire DCK as one chunk.
- **DCK and BIN sizes differ:** expected. A DCK has a nine-byte header and stores only ROM/initialized-RAM payloads; a flat BIN is always 65536 bytes.
- **Expanded absent areas contain `$FF`:** change `--fill` if the hardware expects another erased value.
- **DCK RAM works but physical ROM does not:** descriptor RAM is an emulator feature unless the cartridge contains writable RAM and implements writes.
- **AROS inspection reports unsafe chunk 3:** fix the startup chunk-specification byte or redesign the handoff; do not suppress the check blindly.
- **Fuse times out:** first verify the executable path, DCK, machine model, reachable breakpoint, breakpoint number, and terminating `exit` command.
- **macOS opens Fuse but produces no trace:** invoke `Fuse.app/Contents/MacOS/Fuse` directly, not Finder or `open`; then run the `$8008` print-and-exit smoke test. Treat failure as a limitation of that packaged release until its command-line/output path is repaired.
- **A direct EXROM call crashes:** run the gateway from unaffected HOME RAM, use HSR=`$01` for stock EXROM chunk 0, preserve DECR video bits, and retain every HOME chunk the service expects.
