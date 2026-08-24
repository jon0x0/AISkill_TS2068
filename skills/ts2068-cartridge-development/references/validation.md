# Cartridge validation workflow

## Static validation

1. Confirm each supplied chunk is exactly 8192 bytes.
2. Confirm Fuse DCK (`.dck`) cartridge-image byte 0 is the intended bank identifier (ID) and all descriptors are 0-3.
3. Confirm file length equals 9 plus 8192 bytes for each descriptor 2/3.
4. Confirm stored images occur in ascending chunk order.
5. Confirm Application ROM-Oriented Software (AROS) or Language ROM-Oriented Software (LROS) header type, entry, chunk specification, autostart, and reserve values.
6. Confirm the flat physical binary is exactly the hardware-required size and reconstructs the intended chunk images.
7. Validate every generated bank/address/length table against payload placement.
8. Scan assembly for every `$F4` and `$FF` write and document the expected program counter (PC), stack pointer (SP), interrupt-service routine (ISR), ROM, display, and destination visibility after it.

## Deterministic Fuse validation

Run Fuse with `--machine ts2068`, the DCK via `--dock`, and a debugger command program. Prefer address, port, and memory breakpoints over desktop screenshots.

Capture at minimum:

- first cartridge entry;
- every distinct mapping transition during bring-up;
- application handoff;
- first interrupt in each important mapping;
- screen/display RAM after initialization;
- representative reads from every populated cartridge chunk;
- stack pointer and bytes around SP before/after gateways;
- long-run loop or interaction checkpoints.

Use scripts that inject normal host keyboard events only after activating the Fuse process. Arm downstream debugger breakpoints only after the emulated program consumes the key. Keep debugger logs and direct RAM-rendered screenshots.

## Bank-transition assertions

At each `$F4`/`$FF` write, verify:

- the next instruction exists in the new mapping;
- the return address remains visible;
- SP points to writable memory;
- the interrupt vector and ISR are valid, or interrupts are disabled;
- any `LDIR` destination is HOME/writable rather than selected ROM;
- display RAM is CPU-visible before drawing;
- expected ROM/Extension ROM (EXROM) bytes are mapped before calls;
- the old mapping is restored on every success/error path.

## Physical validation

After Fuse passes:

1. verify the programmed image hash;
2. confirm board capacity and address decoding;
3. confirm whether hardware is ROM-only or implements cartridge RAM;
4. test cold power-on, reset, repeated runs, keyboard/joystick, sound, video, and ROM services used;
5. test mapping transitions under real interrupts and timing;
6. record exact hardware, ROM revision, image hash, and result.

Do not call a build complete solely because its DCK parses or its first screen appears.
