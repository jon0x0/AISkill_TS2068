# Application ROM-Oriented Software (AROS), Language ROM-Oriented Software (LROS), and BASIC cartridge rules

## Contents

1. [Machine-code AROS](#machine-code-aros)
2. [BASIC AROS](#basic-aros)
3. [BASIC versus machine-code checklist](#basic-versus-machine-code-checklist)
4. [ECM routines in machine-code versus BASIC AROS](#ecm-routines-in-machine-code-versus-basic-aros)
5. [LROS](#lros)
6. [Fuse DCK cartridge-image container](#dck-container)
7. [ROM and OS coexistence](#rom-and-os-coexistence)
8. [Known OS limitations](#known-os-limitations)

## Machine-code AROS

Place the eight-byte header at DOCK `$8000` (chunk 4):

| Offset | Meaning |
|---:|---|
| 0 | language type: 2=machine code only |
| 1 | cartridge type: 2=AROS |
| 2-3 | entry address, little-endian |
| 4 | low-active chunk specification: 0=used, 1=not used |
| 5 | autostart: 1=yes |
| 6-7 | requested HOME-RAM reserve, little-endian |

Known-good minimal machine-code header:

```text
02 02 08 80 EF 01 00 00
```

This starts at `$8008`, declares only chunk 4 in use, and requests no ROM-managed variable area. Keep bits 0-3 of the chunk specification set for the documented portable layout. A proven full-control launcher may expose chunks 0-2 deliberately, but chunk 3 must remain HOME during handoff. If requesting a ROM-managed variable area for machine-code AROS, request `21+n` bytes because of the TS2068 initialization bug; the usable `n` bytes begin after the 21-byte CHANS area at `$6855` in normal mode.

At entry, establish the stack, interrupt policy, Horizontal Select Register (HSR) and Display Enhancement Control Register (DECR) shadows, and RAM layout explicitly. The operating system (OS) has initialized Z80 Interrupt Mode 1 (IM1) and may have interrupts enabled. Leaving chunk 0 HOME preserves the ROM `$0038` path, but application compatibility still requires testing.

## BASIC AROS

Use this header shape:

```text
01 02 <first-line-lo> <first-line-hi> <chunk-spec> <autostart> <reserve-lo> <reserve-hi>
```

The first BASIC line normally begins at `$8008`. Store program lines exactly as in RAM:

```text
[line high][line low][length low][length high][tokenized body][$0D]
```

Follow the final line with a byte whose high bit is set, commonly `$80`.

Observe these rules:

- Keep BASIC program lines in the upper half of the address space beginning at `$8008`.
- Keep chunk-spec bits 0-3 set to 1.
- Let variables and arrays be created in HOME RAM; cartridge variables are not preloaded by the ROM.
- Prefer longer multi-statement lines because the ROM copies a whole cartridge line into ARSBUF before execution.
- Avoid excessively long DATA statements because the whole statement is copied even when READ consumes one item.
- Reserve requested BASIC machine-code/variable bytes from `$6840`; ARSBUF follows the reserved region.
- Return chunks 0-3 to HOME with stack and OS state intact before returning from cartridge USR code.
- Keep advanced second-display mode closed while executing BASIC AROS statements. The BASIC AROS bank code assumes its normal chunk-3 location.
- Avoid user-defined BASIC functions; cartridge support does not implement the needed definition search.

Machine code may be called through USR, but the stock ROM contains an address-classification bug. Verify the chosen USR address on real ROM/Fuse and prefer an explicit resident gateway when banking is nontrivial.

The VU-3D example uses a BASIC AROS header in chunk 4, tokenized BASIC lines, and three stored 8K chunks. It is useful as a format example, but do not infer that every BASIC/USR bank path is bug-free.

## BASIC versus machine-code checklist

Select BASIC AROS only when ROM-managed BASIC execution is an intended part of the design. Select machine-code AROS for exact timing, custom interrupt/video/input behavior, extensive banking, or compatibility launchers.

| BASIC AROS: do | BASIC AROS: do not |
|---|---|
| Encode proper tokenized line records from `$8008`, ending each line with `$0D` and the program with a high-bit marker. | Store ASCII source or copy an ordinary Spectrum BASIC image without rebuilding and validating the AROS layout. |
| Keep chunk-spec bits 0-3 set and retain HOME ROM, system variables, dispatcher, stack, and ARSBUF. | Page lower HOME/OS chunks from a `USR` helper and return before restoring them. |
| Keep variables, arrays, strings, and mutable state in HOME RAM. | Expect cartridge ROM variables or embedded machine code to be writable. |
| Size the reserve area and ARSBUF deliberately; prefer reasonable multi-statement lines. | Use huge `DATA` statements without accounting for whole-statement copying. |
| Give each `USR` helper a register/mapping contract and test its address classification. | Assume stock `USR` address classification or BASIC cartridge ROM paths are bug-free. |
| Keep the normal chunk-3 BASIC workspace active while statements execute. | Execute BASIC AROS statements with the advanced second display file open. |
| Use supported statements and test errors, loops, `READ`, `USR`, and SAVE/LOAD on the target ROM. | Use user-defined functions or exceptional FOR/NEXT cases without replacing/validating the known unsupported paths. |

| Machine-code AROS: do | Machine-code AROS: do not |
|---|---|
| Initialize SP, interrupts, HSR/DECR shadows, video/keyboard state, and HOME-RAM layout explicitly. | Rely on undocumented entry residue. |
| Keep PC, stack, return addresses, writable data, and the active interrupt path visible at every mask. | Put SP, variables, or self-modifying code in read-only cartridge ROM. |
| Run a bank/EXROM transition from unaffected HOME RAM when it removes the current DOCK code. | Change DECR to EXROM while executing only from DOCK. |
| Execute immutable code directly from ROM; copy protected/self-modifying Spectrum code to HOME RAM. | Assume a Spectrum program that expects 48K RAM can execute unchanged in ROM. |
| Verify TS2068 ROM entries and wrap incompatible services. | Call Spectrum ROM addresses by numerical assumption. |
| Confirm cartridge sources and HOME destinations are simultaneously visible and non-overlapping. | Select ROM over the destination and trust a completed `LDIR` as proof of a successful write. |
| Use the complete 64K cartridge selectively, with explicit runtime masks and gateways. | Treat HSR=`$FF` as a normal state with ROM, writable stack/RAM, and interrupts still available. |

For both types, generate DCK/BIN outputs reproducibly, keep mutable state out of physical ROM, distinguish DCK RAM descriptors from real writable hardware, and test on the TS2068 model plus target hardware.

## ECM routines in machine-code versus BASIC AROS

Keep the pixel and attribute targets the same for both hosts: bitmap HOME `$4000-$57FF`, Extended Color Mode (ECM) attributes HOME `$6000-$77FF`. Change the integration contract:

| Concern | Full-control machine-code AROS | BASIC AROS |
|---|---|---|
| Entry/mode ownership | May set DECR mode `$02` directly only after replacing/protecting every stack, dispatcher, interrupt, and data dependency in `$6000-$7BFF` | Invoke a verified helper and normally use EXROM `CHNG_VID` `$0E8E`, A=`$02`, so the operating system relocates BASIC, dispatcher, stack, and pointers |
| Helper location | Can use a known unaffected HOME block; Elite copies DOCK `$9900-$99BD` to HOME `$7800-$78BD` because it bypasses OS relocation | Do not execute at `$6840-$7AFF` across `CHNG_VID`; that region is relocated or cleared. Reserve stable HOME RAM below relocated OS area `$F7C0-$FFFF`, protect it with RAMTOP/allocation policy, and keep its HSR bit clear |
| Stack | May replace SP and never return to the previous environment | Preserve the caller contract; let `CHNG_VID` relocate the machine stack and never overwrite `$F7C0-$FFFF`; restore exact SP/mappings before returning |
| BASIC execution | none | Execute the entire ECM display/hold/exit in machine code. BASIC AROS support assumes normal chunk-3 bank code and cannot execute BASIC statements while the advanced display is open |
| Exit | May blank attributes, write DECR `$00`, remap the next code, and continue one-way | Use a verified/corrected close/relocation path, set `VIDMOD=0`, restore HOME chunks 0-3, dispatcher, ARSBUF, variables, HSR/DECR, registers, SP, and interrupt policy before `RET` |

For BASIC AROS:

1. Enter through a tested `USR` target or explicit gateway; account for the stock USR address-classification bug.
2. Check that `STKEND + $1B00` fits below RAMTOP before calling `CHNG_VID`; reject the stock overflow case where `STKEND > $E4FF`.
3. Run the EXROM transition from unaffected HOME code, preserving mapping shadows and the incoming interrupt policy.
4. After mode entry, avoid `$F7C0-$FFFF`, which contains the relocated dispatcher and machine stack. The normal AROS reserved area at `$6840` moves to `$7B00`, so any access to reserved code/data must depend on `VIDMOD`.
5. Copy/decode the two planes and perform the complete hold/animation without returning to BASIC.
6. Black the ECM attributes and restore normal memory/video before returning. A direct DECR write is insufficient because it does not reverse BASIC/OS relocation.

Treat stock close-display behavior as a verified dependency, not an assumption; known faults can make return to normal mode unreliable. Use a proven correction/full relocation reversal, or make the title a one-way handoff into machine code. A machine-code application that continues to use OS-managed stack/dispatcher/BASIC state must also use the managed path; being written in assembly does not by itself make direct DECR switching safe.

## LROS

An LROS header begins in cartridge chunk 0:

| Offset | Meaning |
|---:|---|
| 0 | unused |
| 1 | cartridge type: 1=LROS |
| 2-3 | entry address, little-endian |
| 4 | low-active chunk specification |

LROS takes control after OS initialization and can implement its own language or full system. Keep header bit 3 set so OS chunk-3 transfer code and stack remain available during handoff. After entry, LROS may replace more HOME memory, but must provide its own stack, interrupt, ROM, and I/O policy.

If LROS is present, the TS2068 does not automatically create an AROS configuration entry. An LROS that supports an integrated AROS must detect and initialize it itself.

## DCK container

Fuse DCK layout:

```text
byte 0     bank ID; 0=DOCK
bytes 1-8  descriptors for chunks 0-7
remaining  8192-byte images for descriptor 2 or 3, in chunk order
```

| Value | Meaning | Image follows |
|---:|---|---|
| 0 | absent; HOME shows through | no |
| 1 | uninitialized cartridge RAM | no |
| 2 | cartridge ROM | yes, 8192 bytes |
| 3 | initialized cartridge RAM | yes, 8192 bytes |

Do not confuse the DCK container with a flat physical ROM binary. A sparse DCK omits absent chunks; a physical 64K image normally contains eight consecutive 8K regions, often filled with `$FF` where unused. RAM descriptors are emulator metadata and cannot create writable memory on read-only hardware.

## ROM and OS coexistence

Keep HSR bits 0 and 1 zero to call HOME ROM directly. Do not assume Spectrum entry addresses retain their meaning; verify TS2068 HOME ROM equivalents.

The Extension ROM (EXROM) and cartridge DOCK bank are mutually exclusive external selections controlled by DECR bit 7. Stock U20 is the built-in 8K system ROM at EXROM `$0000-$1FFF`; a verified 16K EXROM implementation can additionally supply chunk 1 at `$2000-$3FFF`. Neither form is a second cartridge or a general 64K payload bank. Call stock services through a HOME-RAM gateway:

1. enter RAM code in a chunk that remains HOME;
2. preserve registers, DECR/HSR shadows, and interrupt state;
3. disable interrupts;
4. write HSR=`$00` so selected DOCK code disappears only after execution is safely in RAM;
5. set DECR bit 7 while preserving mode bits;
6. select stock EXROM chunk 0 with HSR=`$01`;
7. call the verified EXROM entry;
8. write HSR=`$00` before switching DECR back;
9. restore DECR, HSR, and interrupt state.

EXROM routines may expect HOME system variables, stack, dispatcher, or ROM state. Verify the exact entry contract rather than treating EXROM as a generic library.

## Known OS limitations

- Initialize keyboard mode when depending on ROM keyboard output after machine-code cartridge entry: MODE `$5C41=0`, FLAGS `$5C3B` bit 3 set, if ordinary character codes rather than BASIC keywords are intended.
- Initialize calculator state before invoking calculator-dependent ROM routines as documented by the technical manual.
- Do not mark chunk 3 used in LROS or machine-code AROS startup headers.
- For machine-code AROS RAM reserve, add 21 bytes to the requested application size.
- Avoid the BASIC AROS USR address-classification bug by validation/address choice or explicit banking code.
- Avoid the exceptional FOR/NEXT case where the initial value is already beyond the limit; the AROS ROM path can lose the continuation address.
- Do not execute BASIC AROS statements with the second display file open.
- Disable interrupts during DECR/HSR updates; the stock bank service can be interrupted in an invalid mapping.
- Be cautious with stock SAVE/RESTORE STATUS and CALL BANK services; documented bugs can restore stale DECR state or overwrite memory unless corrected.
