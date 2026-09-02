---
name: ts2068-cartridge-development
description: Design, build, port, inspect, and debug Timex Sinclair 2068 DOCK cartridges, Application ROM-Oriented Software (AROS), Language ROM-Oriented Software (LROS), Fuse DCK (.dck) cartridge images, and flat physical-cartridge binaries. Use for original TS2068 software or Spectrum ports involving cartridge memory maps, 8K chunk selection, port $F4/$FF banking, cartridge-to-HOME-RAM transfers, direct cartridge execution, ROM/Extension ROM (EXROM) coexistence, display-memory overlays, PackBits-compressed title screens or media, command-aware FIFO packing across banks, BASIC AROS programs, full-64K packing, Fuse validation, and cartridge conversion work.
---

# TS2068 Cartridge Development

Build cartridge software around the TS2068's eight fixed-address 8K chunks. Treat banking, execution location, stack, interrupts, display access, and ROM dependencies as one memory-contract problem.

## Start every task

1. Inspect the target program, existing DCK/BIN files, build scripts, and emulator evidence.
2. Read [glossary.md](references/glossary.md) when interpreting TS2068 cartridge acronyms or specialized terms.
3. Read [memory-banking-faq.md](references/memory-banking-faq.md) for the complete chunk/address table, hardware, full-64K questions, exact Horizontal Select Register (HSR) and Display Enhancement Control Register (DECR) switching mechanics, and worked transitions.
4. Read [aros-and-basic.md](references/aros-and-basic.md) for AROS, LROS, BASIC, headers, or OS integration.
5. Read [proven-patterns.md](references/proven-patterns.md) when selecting an architecture or porting existing software.
6. Read [example-memory-maps.md](references/example-memory-maps.md) when adapting the Elite copy-and-run or TSVideoCodec resident-player/FIFO architectures.
7. Read [validation.md](references/validation.md) before declaring a cartridge functional.
8. Read [utilities.md](references/utilities.md) before using or adapting the bundled or external image/cartridge tools, Fuse launcher, Python module, or assembly templates.
9. Produce a chunk map before writing code. For every chunk, state its cartridge contents, current CPU-visible bank, writable status, and any code, stack, interrupt, display, or OS dependency.

For broader TS2068 programming information beyond cartridge mechanics, consult [David Anderson's TS2068 Reference Library](https://github.com/timex-sinclair-projects/TS2068-Ref-Library) as a companion reference tree. Verify any machine-specific ROM address or hardware claim against the exact ROM and target configuration used by the project.

## Apply the core model

- Use **DOCK** for the Technical Reference Manual's **Dock (Cartridge) Bank**, the external bank supplied through the cartridge connector. Treat Dock as a bank name, not an acronym.
- Divide `$0000-$FFFF` into chunks 0-7, each `$2000` bytes.
- Write HSR port `$F4`: bit N=1 selects external chunk N; bit N=0 selects HOME chunk N.
- Use DECR port `$FF` bit 7 to choose which external bank HSR selects: 0=DOCK cartridge, 1=EXROM. Preserve the video mode and interrupt-inhibit bits.
- Distinguish the EXROM bank's capacity from the factory ROM fitted to it. Treat stock U20 as an 8K system ROM at EXROM `$0000-$1FFF` (chunk 0) and select HSR=`$01` for documented stock services. A verified 16K EXROM can also supply chunk 1 at `$2000-$3FFF` and uses HSR=`$02` or `$03`; do not assume that upper chunk exists on a stock machine or treat EXROM as another 64K cartridge.
- Treat HSR as a fixed-address overlay selector, not a relocatable paging window. DOCK chunk N always appears at `N*$2000`.
- Keep software shadows of `$F4` and `$FF`; do not depend on reading the ports back.
- Disable interrupts around multi-write mapping changes. Ensure the active interrupt vector and stack remain visible and writable.

## Choose an architecture

Prefer one of these patterns:

1. **Resident cartridge code plus pageable data:** execute from DOCK chunk 4 and keep bit 4 set in every HSR mask; select one or more data chunks as needed.
2. **Copy-and-run:** execute a small cartridge bootstrap, copy the application into HOME RAM, unmap DOCK, and use RAM-resident gateways to fetch later cartridge data.
3. **Cartridge code plus HOME display/RAM:** keep chunks 0-3 HOME and chunk 4 DOCK; use chunks 5-7 for data or more code.
4. **Full 64K cartridge:** use chunk 4 for the AROS player and all seven other physical chunks for payload. Preload cartridge data from chunks 2/3 into upper HOME RAM when the live display must remain CPU-writable. Use the unused tail of chunk 4 for tables/data.
   For variable-sized compressed records, treat the seven payload chunks as an ordered logical FIFO and insert next-bank commands only at safe codec-command boundaries; see [proven-patterns.md](references/proven-patterns.md).
5. **BASIC AROS:** store tokenized BASIC lines from `$8008` upward and keep dynamic variables in HOME RAM. Use this only when ROM-managed BASIC execution is desired.

Do not map away the chunk containing the current program counter (PC), stack, return address, or interrupt-service routine (ISR) unless control continues through verified mirrored code or a routine already copied to unaffected HOME RAM.

## Build and inspect images

- Follow [utilities.md](references/utilities.md) for exact CLI syntax, descriptor semantics, debugger-command examples, template adaptation, and verification behavior.
- Use `scripts/pack_dck.py` to package exact 8K chunk images or a flat 64K image.
- Use `scripts/inspect_dck.py` to verify descriptors, stored chunk order, headers, hashes, and flat-image expansion.
- Use `scripts/dck_to_picorom.py` to convert a sparse DCK into one contiguous 64K physical ROM image with explicit fill bytes.
- Use external [zx81-utils `dckls`](https://github.com/ryangray/zx81-utils) with `-d` to extract stored contiguous ROM/RAM spans. Do not mistake sparse extracted spans for a padded 64K physical image.
- Use the external [TS2068 TAP to Cartridge Builder](https://timex-sinclair-projects.github.io/2068-TAP-To-Cart/) or its `tapToCart.py` command-line version for TS2068 BASIC TAP programs. Do not treat it as an automatic Spectrum machine-code porting tool.
- Use [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) to author Timex Extended Color bitmap and 8×1 attribute planes. Verify the two 6144-byte outputs independently and let the cartridge map—not their TAP order or load addresses—determine ROM placement.
- Use `scripts/run_fuse_debug.py` to run deterministic Fuse debugger command files.
- Copy and adapt [machine-code-aros.asm](assets/machine-code-aros.asm) for a minimal direct-execution AROS.
- Copy and adapt [home-bank-gateways.asm](assets/home-bank-gateways.asm) when mapping would remove the executing cartridge code or when entering EXROM.

## Enforce safety invariants

- For a portable AROS, keep header bits 0-3 set to 1 during OS handoff. A full-control machine-code bootstrap may deliberately expose chunks 0-2 only with proven initialization state; never designate chunk 3 as cartridge-owned in the startup header.
- Keep chunk 0 HOME while using the stock Z80 Interrupt Mode 1 (IM1) handler, or disable interrupts/provide a valid cartridge-side `$0038` handler.
- Keep the stack in writable HOME RAM or real cartridge RAM; writes to cartridge ROM silently fail.
- Ensure `LDIR` source and destination are simultaneously visible. Do not select cartridge ROM over the intended HOME destination.
- Keep HOME chunks 2 and 3 available to OS routines that require system variables/dispatcher state; keep chunk 7 HOME if advanced-video relocation placed OS RAM there.
- Use TS2068 ROM addresses only after verification. Spectrum ROM addresses are not portable by assumption.
- Distinguish DCK-emulated RAM descriptors from physical ROM hardware. A flat PicoROM image does not become writable merely because Fuse can model a RAM chunk.
- Validate on the TS2068 machine model and, before release, on the intended physical cartridge hardware.

## Deliverables

Provide:

- a per-chunk memory map and runtime HSR/DECR masks;
- source-controlled assembly and deterministic packing scripts;
- Fuse `.dck` and, when required, exact physical `.bin` output;
- static validation plus scripted runtime checkpoints;
- documented ROM calls, interrupt assumptions, stack location, and bank transitions;
- hashes and a test history for accepted builds.
