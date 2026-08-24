# TS2068 cartridge memory and banking FAQ

## Contents

1. [Memory model and complete chunk address map](#memory-model)
2. [What is the Extension ROM?](#what-is-the-extension-rom)
3. [Can a program use the entire 64K cartridge?](#can-a-program-use-the-entire-64k-cartridge)
4. [Can code execute directly from cartridge?](#can-code-execute-directly-from-cartridge)
5. [How does bank switching work?](#how-does-bank-switching-work)
6. [How do cartridge ROM and TS2068 RAM coexist?](#how-do-cartridge-rom-and-ts2068-ram-coexist)
7. [When is a HOME-RAM switching routine required?](#when-is-a-home-ram-switching-routine-required)
8. [Are any cartridge chunks inaccessible?](#are-any-cartridge-chunks-inaccessible)
9. [What happens to the display while chunks 2/3 are mapped to cartridge?](#what-happens-to-the-display-while-chunks-23-are-mapped-to-cartridge)
10. [How should program code and stored data be divided?](#how-should-program-code-and-stored-data-be-divided)
11. [What must not be done?](#what-must-not-be-done)
12. [Safe mask examples](#safe-mask-examples)
13. [Physical cartridge qualifications](#physical-cartridge-qualifications)

## Memory model

The Z80 central processing unit (CPU) sees one 64K address space divided into eight fixed 8K chunks. Native TS2068 banking is a one-to-one overlay: cartridge chunk N appears only over internal HOME read-only memory (ROM) or random-access memory (RAM) chunk N. It cannot be mapped into a different address range. External selections come from either the cartridge DOCK bank or the Extension ROM (EXROM) bank.

Port `$F4` is the Horizontal Select Register (HSR). A one in bit N exposes external chunk N; a zero exposes HOME chunk N. Port `$FF` is the Display Enhancement Control Register (DECR); bit 7 chooses whether selected external chunks come from DOCK (0) or EXROM (1). DECR bits 0-2 select the video mode and bit 6 inhibits the periodic interrupt, so maintain a software shadow and change only intended bits.

### Complete chunk address map

| Chunk | HSR bit | Single-bit mask | Flat 64K cartridge offset | CPU address when selected | HOME memory hidden from the CPU |
|---:|---:|---:|---|---|---|
| 0 | 0 | `$01` | `$0000-$1FFF` | `$0000-$1FFF` | first half of HOME ROM; reset and Z80 Interrupt Mode 1 (IM1) `$0038` vector |
| 1 | 1 | `$02` | `$2000-$3FFF` | `$2000-$3FFF` | second half of HOME ROM |
| 2 | 2 | `$04` | `$4000-$5FFF` | `$4000-$5FFF` | primary display bitmap/attributes and HOME RAM/system variables |
| 3 | 3 | `$08` | `$6000-$7FFF` | `$6000-$7FFF` | HOME RAM, operating-system (OS) dispatcher/stack area, and second display plane |
| 4 | 4 | `$10` | `$8000-$9FFF` | `$8000-$9FFF` | HOME RAM; normal Application ROM-Oriented Software (AROS) header at cartridge `$8000-$8007` and entry at `$8008` |
| 5 | 5 | `$20` | `$A000-$BFFF` | `$A000-$BFFF` | HOME RAM |
| 6 | 6 | `$40` | `$C000-$DFFF` | `$C000-$DFFF` | HOME RAM |
| 7 | 7 | `$80` | `$E000-$FFFF` | `$E000-$FFFF` | HOME RAM |

For a conventional flat 64K physical cartridge binary, the file offsets match the CPU addresses because the chunks are stored consecutively in address order. Byte `$0123` in the flat image is cartridge address `$0123`; byte `$A123` is cartridge address `$A123` in chunk 5.

A Fuse DCK (`.dck`) cartridge-image file is different: its first nine bytes are a DCK container header and only descriptors 2 or 3 are followed by an 8K payload. Therefore, do not use DCK file offsets as cartridge CPU addresses. Parse the descriptors or use `scripts/inspect_dck.py` to recover the chunks and their mapped addresses.

Examples:

- HSR=`$00`: every range is HOME; no DOCK/EXROM memory is CPU-visible.
- HSR=`$10`: cartridge chunk 4 appears at `$8000-$9FFF`; all other ranges remain HOME.
- HSR=`$A0` (`$20+$80`): cartridge chunks 5 and 7 appear at `$A000-$BFFF` and `$E000-$FFFF` respectively.
- HSR=`$FF`: all cartridge chunks appear across `$0000-$FFFF`; no HOME ROM or RAM is CPU-visible.

The CPU always uses the same addresses. Changing HSR changes which physical device answers those addresses.

The native scheme does not remap an arbitrary bank into a common window. Cartridge chunk 5 is always visible at `$A000-$BFFF`, chunk 6 at `$C000-$DFFF`, and so on. Several chunks may be exposed simultaneously by setting several HSR bits.

## What is the Extension ROM?

The stock TS2068 has a 16K U16 HOME ROM and a separate 8K U20 Extension ROM. Factory U20 occupies `$0000-$1FFF` in the EXROM source, corresponding to chunk 0. It is built into the computer: it is neither the cartridge nor another 64K of application storage.

Keep the installed-ROM size separate from the EXROM bank's supported layout. Timex's internal planning recognized a 16K EXROM configuration. In such an implementation, the lower half is chunk 0 at `$0000-$1FFF`, the upper half is chunk 1 at `$2000-$3FFF`, and HSR=`$03` exposes both when DECR bit 7 selects EXROM. Modified 16K EXROM images demonstrate this layout. The factory 8K U20 does not provide the upper chunk, so probe or identify the exact hardware/image before relying on it.

EXROM supplements HOME ROM with final initialization, cassette I/O, the `CHNG_VID` video-mode service, bank-switching routines, compatible low-memory vectors, and the source/jump tables for the function dispatcher copied into HOME RAM at boot. Direct EXROM callers must preserve the HOME system variables, operating-system stack, and other RAM state expected by the service.

DECR bit 7 makes all set HSR bits request EXROM instead of DOCK, so the two external sources are globally mutually exclusive. For a stock EXROM service, switch from unaffected HOME RAM, disable interrupts, set HSR=`$00`, set DECR bit 7, then set HSR=`$01` to expose EXROM chunk 0. On return, set HSR=`$00` before restoring DOCK in DECR and the previous HSR mask. Use HSR=`$02` or `$03` only with a verified 16K EXROM, do not assume meaningful bytes beyond its implemented chunks, and verify the ROM revision and documented entry contract.

## Can a program use the entire 64K cartridge?

Yes. A conventional 64K DOCK cartridge can contain eight 8K chunks, and every chunk can be read by the CPU. The whole cartridge can even be selected at once with DOCK selected and HSR=`$FF`.

That does **not** mean a useful program normally keeps all 64K selected simultaneously. HSR=`$FF` hides the HOME ROM, all HOME RAM, the CPU's access to display RAM, the normal stack, and the standard interrupt handler. A ROM cartridge also supplies no writable memory. A practical design alternates mappings or keeps selected HOME chunks visible.

### Recommended full-64K strategy

Use every physical cartridge byte as follows:

1. Put the AROS header, bootstrap, hot player/decoder, bank reader, and indexes in chunk 4.
2. Use the unused tail of chunk 4 for immutable tables or payload.
3. Fill chunks 0, 1, 2, 3, 5, 6, and 7 with banked payload.
4. Keep HSR bit 4 set while executing the resident player, and add one payload bit at a time.
5. Copy or decode each selected payload into a different, still-HOME RAM chunk.
6. Treat chunks 0 and 3 as delayed-use payload because startup/interrupt/stack code initially needs their HOME counterparts.
7. At boot, temporarily map cartridge chunks 2/3 and copy their 16K payload into HOME chunks 6/7. Restore chunks 2/3 HOME for the live display, then read the saved payload from `$C000-$FFFF` whenever cartridge chunks 6/7 are not selected.
8. Pack records bank-locally for simple fast readers, or use explicit next-bank markers at decoder command boundaries to fill all bank tails.

This is the proven TSVideoCodec architecture: 56K of media in the seven non-code chunks plus 8K for resident code/tables and any remaining payload. It uses all 64K of storage while retaining a working HOME display, ROM, stack, and RAM through selective mapping.

## Can code execute directly from cartridge?

Yes. A machine-code AROS normally starts at `$8008` in DOCK chunk 4 and continues executing there. Keep HSR bit 4 set whenever the program counter (PC) is in that chunk.

Code may span several cartridge chunks. Calls and jumps must select the destination chunk before entering it and preserve the caller/return path. Since chunks have fixed addresses, a call from chunk 4 to chunk 5 can run with HSR bits 4 and 5 both set. No copy is required.

Direct ROM execution implies:

- no self-modifying code in the cartridge region;
- no stack or writable variables in ROM chunks;
- no mapping away the current code chunk before a safe continuation point;
- valid interrupt handling for the active mapping.

## How does bank switching work?

### What the hardware actually switches

The TS2068 does not copy or relocate memory when software switches banks. Address lines A13-A15 divide the Z80's address space into eight fixed 8K address ranges. For every memory access, the corresponding HSR bit chooses which physical memory responds at that address:

- HSR bit `0`: `$0000-$1FFF`
- HSR bit `1`: `$2000-$3FFF`
- HSR bit `2`: `$4000-$5FFF`
- HSR bit `3`: `$6000-$7FFF`
- HSR bit `4`: `$8000-$9FFF`
- HSR bit `5`: `$A000-$BFFF`
- HSR bit `6`: `$C000-$DFFF`
- HSR bit `7`: `$E000-$FFFF`

For each bit, zero selects the normal internal HOME ROM/RAM and one selects external memory. DECR bit 7 decides whether all HSR-selected ranges request DOCK or EXROM. It is one global DOCK/EXROM choice, not a separate choice per chunk. Stock U20 physically supplies only its 8K chunk 0; a 16K EXROM supplies chunks 0-1. The 64K external-bank model does not imply 64K of installed EXROM.

Writing a new value to HSR replaces the complete eight-bit selection mask at once. It is not a bank number. For example, `$30` is binary `%00110000`, so DOCK chunks 4 and 5 appear together while every other address range remains HOME.

The write takes effect for the next memory access after the `OUT`. The hidden HOME bytes are not erased or changed; they simply stop responding to CPU reads and writes until their HSR bits return to zero. Likewise, cartridge bytes remain where they are when hidden.

If the selected external chunk is ROM:

- CPU reads obtain cartridge bytes;
- CPU writes do not update the hidden HOME RAM and normally have no effect;
- instructions can execute directly from it, but variables, stack writes, and self-modifying code cannot.

If the physical cartridge provides writable RAM, or Fuse models the chunk as DCK RAM, writes go to that external RAM instead. This behavior must not be assumed for a ROM/PicoROM cartridge.

### Programming the registers

Keep software shadows of HSR and DECR because code should not depend on reading either port back. A typical DOCK setup is:

```asm
PORT_HSR        EQU     $F4
PORT_DECR       EQU     $FF

                DI
                LD      A,(DECR_SHADOW)
                AND     $7F         ; bit 7=0 selects DOCK for external chunks
                LD      (DECR_SHADOW),A
                LD      BC,$00FF
                OUT     (C),A

                LD      A,$10       ; DOCK chunk 4, every other chunk HOME
                LD      (HSR_SHADOW),A
                LD      BC,$00F4
                OUT     (C),A
```

Preserve DECR bits 0-2, which control the video mode, and bit 6, which controls interrupt inhibition. Do not replace DECR with a convenient constant unless the program deliberately owns the complete machine state.

For a single HSR change within an already selected DOCK environment, code executing from chunk 4 can expose data in chunk 1 as follows:

```asm
                DI
                LD      A,$12       ; bits 4 and 1: code + data
                LD      (HSR_SHADOW),A
                LD      BC,$00F4
                OUT     (C),A
                ; read cartridge data at $2000-$3FFF
                LD      A,$10       ; keep code, restore all other HOME chunks
                LD      (HSR_SHADOW),A
                OUT     (C),A
                EI                  ; only if interrupts were enabled on entry
```

Use `LD BC,$00F4 / OUT (C),A` for an unambiguous HSR port write. Preserve the previous interrupt state rather than blindly issuing `EI` in reusable code.

### What happens during a worked transition

Assume the CPU is executing at `$8100` from cartridge chunk 4, the stack is in HOME chunk 3, and HSR is `$10`:

1. Before the switch, `$8000-$9FFF` reads DOCK chunk 4; `$A000-$BFFF` reads HOME RAM.
2. Execute `OUT ($F4),$30` through the equivalent register form.
3. The next instruction still works because bit 4 remains set and therefore the executing code is still visible.
4. `$A000-$BFFF` now reads DOCK chunk 5. The HOME RAM underneath it is hidden but unchanged.
5. Copying from `$A000` to `$C000` reads cartridge chunk 5 and writes HOME chunk 6 because HSR bit 6 is zero.
6. Write HSR=`$10`. HOME RAM at `$A000-$BFFF` immediately becomes visible again, containing exactly what it held before the switch.

This is overlay selection: it changes which memory answers at an address, not the address used by the program.

### Why execution can fail immediately

The processor does not know that a mapping is unsafe. After the `OUT`, its next opcode fetch, stack access, interrupt acknowledge, or data access uses the new mapping:

- If code at `$8100` clears HSR bit 4, the next opcode comes from HOME RAM at the following address, not from the cartridge routine.
- If the stack pointer (SP) is in `$6000-$7FFF` and HSR bit 3 becomes one, `CALL`, `RET`, `PUSH`, `POP`, and interrupt stack writes use external chunk 3 rather than the HOME stack.
- If IM1 is enabled and HSR bit 0 becomes one, an interrupt jumps to cartridge/EXROM `$0038` instead of the HOME ROM handler.
- If a destination is under a selected ROM chunk, instructions such as `LDIR` appear to run but cannot update the hidden HOME RAM.

Disable interrupts around unsafe transitions and execute the switching code from a chunk that remains visible. Use a HOME-RAM gateway when the operation must remove the current code chunk, uncover HOME RAM beneath it, or change DECR between DOCK and EXROM.

### Changing between DOCK and EXROM

Because DECR bit 7 changes the external source for every set HSR bit, do not flip it while executing from a selected DOCK chunk. The safe sequence is:

1. Enter a gateway already copied to unaffected HOME RAM.
2. Disable interrupts and preserve the old HSR, DECR, and interrupt state.
3. Write HSR=`$00`, making all addresses HOME.
4. Change only DECR bit 7.
5. Write HSR=`$01` for a documented stock EXROM chunk-0 entry and call it.
6. Write HSR=`$00` again before changing DECR back to DOCK.
7. Restore the previous HSR and interrupt state.

See [the HOME-bank gateway template](../assets/home-bank-gateways.asm) for an adaptable implementation.

### Same-address copy limitation

Cartridge chunk N and HOME chunk N occupy the same CPU address range and cannot both be visible at once. To copy cartridge chunk 6 into HOME chunk 6, use another HOME chunk as a temporary buffer:

1. With resident code in chunk 4, select HSR=`$50` and copy cartridge `$C000-$DFFF` to HOME `$A000-$BFFF`.
2. Restore HSR=`$10`, revealing HOME chunk 6.
3. Copy the temporary bytes from `$A000-$BFFF` to HOME `$C000-$DFFF`.

Alternatively, run a copier from unaffected HOME RAM and arrange source and destination chunks so their HSR requirements do not conflict.

HSR=`$FF` can expose all 64K of DOCK at once, but that also removes all CPU-visible HOME ROM and RAM. With a ROM cartridge there is then no writable stack or standard interrupt handler, so this is normally useful only for tightly controlled, register-only transitions or cartridge hardware that supplies writable RAM. Selective overlays are the practical way to use all 64K of cartridge storage.

## How do cartridge ROM and TS2068 RAM coexist?

Set only the bits for chunks that should come from cartridge. Every zero bit leaves the corresponding HOME ROM/RAM visible. A common machine-code layout is:

| Chunk | Runtime selection | Purpose |
|---:|---|---|
| 0-3 | HOME | ROM, display, system variables, stack/dispatcher |
| 4 | DOCK | resident player/bootstrap |
| 5 | selected as needed | cartridge code/data or HOME RAM |
| 6-7 | HOME or selected as needed | work RAM or cartridge media |

To copy cartridge data, expose the source chunk while leaving a different HOME destination chunk unselected. The Elite conversion found the critical failure mode: selecting cartridge chunk 4 while copying into HOME `$8000-$9FFF` left the destination covered by read-only ROM, so `LDIR` wrote nothing. The fix was to run the copier from HOME RAM and select only the source chunk.

If source and desired destination occupy the same CPU addresses, they cannot be visible at the same time. Copy through a temporary buffer in another HOME chunk, or store/preload the cartridge data into a different HOME chunk.

## When is a HOME-RAM switching routine required?

A RAM routine is **not** required merely to select another data chunk while executing from cartridge. Keep the executing chunk's HSR bit set and add the data chunk bit.

Use a routine in unaffected HOME RAM when:

- the switch will deselect the chunk containing the current PC;
- the code must expose HOME RAM underneath its own cartridge chunk;
- the code changes DECR bit 7 between DOCK and EXROM, changing the source of every selected external chunk;
- no cartridge chunk can safely remain resident during the transition;
- a robust gateway must restore HSR, DECR, registers, and interrupt state.

For DOCK-to-EXROM calls, execute entirely from HOME RAM. First set HSR to zero, then select EXROM in DECR, then set HSR=`$01` for a stock chunk-0 service. On return, set HSR to zero again before restoring DOCK selection and the previous HSR mask. Verify each EXROM entry point and its required HOME chunks.

An alternative is mirrored continuation code: place matching instructions at the same address in both banks so the next fetch remains valid after the switch. This can be fast but is fragile; prefer a RAM gateway unless timing requires otherwise.

## Are any cartridge chunks inaccessible?

No cartridge chunk is permanently inaccessible to machine code after control has safely reached the application. There are startup and runtime restrictions:

- Standard AROS discovery lives at cartridge `$8000`; its first eight bytes are header overhead.
- The documented portable AROS format marks chunks 0-3 as not in use. Proven machine-code launchers may deliberately expose chunks 0-2 when they no longer depend on the covered HOME state, but this is an advanced, validated exception rather than a default.
- Chunk 3 must not be selected by the initial header, but application code may select it after handoff.
- Chunk 0 requires interrupt discipline because IM1 enters `$0038`.
- Chunks 2/3 hide CPU access to HOME display RAM while selected, although video output continues.
- Any chunk containing active HOME stack, OS state, or relocated dispatcher code must remain HOME until those dependencies move.

Thus chunks 0-3 are delayed-use storage in a normal AROS, not wasted storage. Chunk 3 is the hard startup restriction because the handoff code and stack occupy HOME chunk 3.

## What happens to the display while chunks 2/3 are mapped to cartridge?

The Standard Cell Logic Device (SCLD) and CPU have different access paths to the 16K video RAM in HOME chunks 2 and 3. HSR controls which memory the **CPU** sees. It does not redirect the SCLD's display fetches. The SCLD continues reading pixel and attribute data from HOME screen RAM according to the selected video mode even while the same CPU address range is overlaid with DOCK or EXROM.

For example, assume code runs from DOCK chunk 4 and HSR=`$14` selects cartridge chunks 4 and 2:

| Access | Physical source |
|---|---|
| CPU reads `$4000-$5FFF` | DOCK cartridge chunk 2 |
| CPU writes `$4000-$5FFF` | selected external chunk 2; ignored if it is ROM |
| SCLD fetches the primary display | HOME video RAM beginning at `$4000` |
| CPU reads/writes `$6000-$7FFF` | HOME chunk 3 because HSR bit 3 is zero |

The previously drawn primary screen therefore remains visible while the CPU reads cartridge bytes at `$4000-$5FFF`. Those CPU reads do **not** return the pixels currently being displayed; they return cartridge data. CPU writes also do not pass through to the hidden HOME screen RAM. Clear HSR bit 2 before the CPU updates the primary display.

The same principle applies to the second display file in HOME chunk 3. When HSR bit 3 is set, the SCLD can continue fetching that HOME display data while the CPU sees external chunk 3 at `$6000-$7FFF`; clear bit 3 before CPU drawing or reading the second HOME display file.

This makes chunks 2/3 valuable media storage: briefly map and copy/decode from them while the old frame remains visible, then restore HOME mapping to write the next frame. For high-throughput video, preload those cartridge chunks into HOME chunks 6/7 to reduce mapping conflicts.

## How should program code and stored data be divided?

### Resident core plus records

Keep bootstrap, bank reader, interrupt code, and hot decoder in chunk 4. Pack independent records into the other chunks. Store a table of `(HSR mask, address, length)` descriptors in the resident chunk.

### Copy-and-run conversion

Use cartridge code to copy an existing program into its expected HOME addresses, reproduce the original entry state, unmap the cartridge, and jump into RAM. Keep later cartridge access behind RAM gateways. This suits protected or self-modifying Spectrum software.

### Bank-local records

Keep each compressed object, level, sound, or frame delta inside one 8K chunk. This minimizes switching logic and is fastest, but may waste tail space.

### Logical multi-bank stream

Insert explicit boundary markers and switch only at command boundaries. This fills chunk tails efficiently and lets a decoder treat several chunks as one stream. Never fetch an opcode or multi-byte object across a boundary without a defined transition rule.

The proven TSVideoCodec FIFO orders cartridge chunks `0,1,2,3,5,6,7` as seven logical slots. It preloads chunks 2/3 into HOME chunks 6/7, so the runtime sources are `$0000,$2000,$C000,$E000,$A000,$C000,$E000` with HSR masks `$11,$12,$10,$10,$30,$50,$90`. Each record stores a starting slot and address.

Its hybrid decoder reserves `$C1` as a one-byte NEXT_BANK command and `$C2,0` as a padded two-byte form. The command-aware packer splits literal runs at safe points and converts an unsplittable sparse command to an equivalent literal when necessary. This removes the 8K per-record limit and bank-tail fragmentation without adding a boundary comparison to every input byte. Bank-local audio or alignment-sensitive records can use separate placement rules.

This produces a compact 56K payload stream while chunk 4 holds resident code and tables. To approach 64K of payload, relocate the player to HOME RAM and represent free ranges of chunk 4 as extra stream segments. Header/bootstrap/decoder bytes still occupy cartridge capacity and cannot simultaneously be arbitrary payload.

### Compression and indexes

Compress bulk media, generate deterministic placement tables, and verify every table entry against the packed binary. Keep frequently used tables resident; page large immutable payloads.

## What must not be done?

- Do not assume `$F4` chooses one bank number; every set bit independently overlays its fixed chunk.
- Do not forget to keep the executing cartridge chunk selected.
- Do not put the stack in ROM or select ROM over a HOME-RAM stack.
- Do not map cartridge chunk 0 with interrupts enabled unless `$0038` is valid in that mapping.
- Do not switch DECR/HSR in an interruptible half-configured state.
- Do not assume an `LDIR` destination remains HOME when its HSR bit is set.
- Do not call Spectrum ROM addresses on a TS2068 without verifying or wrapping them.
- Do not call EXROM by flipping DECR while still executing in a selected DOCK chunk.
- Do not assume DCK descriptor 1/3 implies writable physical hardware.
- Do not use undefined DECR mode values.
- Do not overwrite HOME chunks 2/3/7 while relying on OS system variables, dispatcher, stack, or advanced-video relocation.

## Safe mask examples

Assume resident code in DOCK chunk 4:

| Need | HSR | CPU-visible external chunks |
|---|---:|---|
| code only | `$10` | 4 |
| code + chunk 0 data | `$11` | 0,4; disable/provide interrupts |
| code + chunk 1 data | `$12` | 1,4 |
| code + chunk 2 data | `$14` | 2,4; CPU display access hidden |
| code + chunk 3 data | `$18` | 3,4; HOME stack/dispatcher hidden |
| code + chunk 5 data | `$30` | 4,5 |
| code + chunk 6 data | `$50` | 4,6 |
| code + chunk 7 data | `$90` | 4,7 |
| all HOME | `$00` | none |
| all DOCK | `$FF` | 0-7; no HOME ROM/RAM visible to CPU |

## Physical cartridge qualifications

The native DOCK interface exposes enough address lines and chip-select signals for a 64K fixed-address image. Actual capacity and write behavior depend on the cartridge board:

- a passive 8K/16K/32K board cannot expose bytes it does not physically decode;
- a 64K ROM/PicoROM implementation can supply all eight chunks;
- writable cartridge RAM requires RAM hardware and correct `/WR` handling;
- smart cartridges larger than 64K need their own paging register/protocol; native HSR alone addresses only the eight fixed DOCK chunks.

Generate both a DCK for Fuse and the exact flat image expected by the physical programmer. Verify byte order, erased fill, electrical mapping, and whether the hardware expects 8K, 16K, 32K, or 64K output.
