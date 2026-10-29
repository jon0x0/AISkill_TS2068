# Expanded TSPico memory: stock banking versus custom paging

Use this when choosing an expanded-memory architecture, porting a banked OS,
or deciding whether a mode needs Pico firmware changes. Evidence comes from
the V2.2/RP2040 Spectrum 128 port and CP/M 2.2 SRAM disk implementation.
Apply the wiring equations only to verified matching hardware.

## Choose the smallest required change

**Stock TSPico already has a PIO memory controller.** "No controller changes"
means retaining its `set_ctrl`/`sel_bank` policy and existing command dispatcher,
not accessing the external SRAM without any Pico assistance.

| Requirement | Existing controller and commands | Additional help or boundary |
|---|---|---|
| Large asset store, overlays, heap pages, RAMDisk | Yes: MEMDOCK chooses SRAM region; Z80 F4 chooses visible chunks | Application must manage banks and resident code |
| Execute code from writable DOCK SRAM | Yes, with a safe cartridge/bootstrap map | Keep the caller, stack and interrupt dependencies visible during switches |
| CP/M 2.2 with 160/320 KiB SRAM disk | Demonstrated using stock MEMDOCK and a Z80 block driver | Disk preload/export software, not replacement memory PIO |
| Reach more than 128 KiB, potentially the 512 KiB chip | Stock region selection plus wider/different F4 windows | Capacity is shared with ROMs/cartridges; not 512 KiB contiguous Z80 RAM |
| Change stored ROM/cartridge selection | Stock loader/MEMDOCK and boot controls exist | MEMBOOT may write persistent configuration; not a fast bank API |
| Frequent single-OUT 16 KiB paging and ROM-half switching as in the 128 port | Not provided by stock command semantics | Custom PIO/DMA latch and patched guest ports/ROM |
| Preserve SD while using that custom paging port | Stock dispatcher cannot simply keep owning the same resources | Cooperative HOME gateway and explicit PIO/DMA/SD arbitration |
| Native unpatched Spectrum 7FFD paging | No | Decoder does not expose that port to this controller; patch software or change hardware/emulate |
| True Spectrum bank-2/bank-5 aliases or bank-7 shadow display | No | Custom PIO alone does not overcome address-mux/video limitations |

A bank-aware Timex 128K/512K application can start with stock MEMDOCK. Extra
capacity alone is not a reason to replace the controller. A Spectrum-like
single-OUT API is a performance/compatibility requirement, not a prerequisite
for every banked application. The Timex 128K/512K language/ROM environments
discussed during this work are proposals, not implemented modes.

## Three independent controls

1. **Pico region selection:** MEMDOCK chooses which external SRAM/Flash region
   supplies DOCK. On the inspected legacy command, PMR1=1 selects SRAM and
   PMR2 selects the slot. The normal BASIC form is
   `SAVE "tpi:memdock" CODE 1,n`; a ROM-independent client can issue the same
   packet without Timex BASIC or an installed ROM library.
2. **SCLD HSR, port F4:** bit N overlays external memory at fixed CPU chunk N,
   each 8192 bytes. It does not relocate a chunk to an arbitrary address.
3. **SCLD DECR, port FF:** bit 7 chooses DOCK versus EXROM for those overlays.
   Preserve other video/interrupt bits when modifying a live application.

Changing F4 alone does not select a new 64 KiB TSPico region. Changing MEMDOCK
alone does not decide which HOME chunks are hidden. These controls must be
managed together, with software shadows of F4/FF rather than assumed readback.

For V2.2 DOCK, physical address is:

```text
(GPIO18:16 << 16) | (CPU_address & 0xFFFF)
```

GPIO15 and GPIO22 are bypassed on this path. Even SRAM slots 0,2,...14
identify eight 64 KiB regions in the 512 KiB chip; an odd slot is not another
independent 64 KiB bank. By contrast, the ROM path uses:

```text
(GPIO18:15 << 15) | (GPIO22 << 14) | (CPU_address & 0x3FFF)
```

Here GPIO22 can select the 16 KiB ROM half. Do not transplant a ROM-path
address calculation or ROM-half test into a DOCK access.

## Writing software that uses the expansion RAM

Define a small Z80-side banked-memory interface instead of distributing Pico
commands and F4 writes throughout the application. A useful starting ABI is
`read(handle, HOME_buffer, length)`, `write(handle, HOME_buffer, length)` and
`call_overlay(handle, entry_offset)`. These are suggested application routines,
not existing firmware commands. CP/M's BIOS sector driver is a concrete example.

Store persistent references as descriptors, for example:

```text
region: even MEMDOCK SRAM slot
chunk:  0..7 at its fixed CPU address
offset: 0..8191 within that chunk
```

Logical application bank IDs should translate through an allocation table.
Do not pass Spectrum bank numbers directly as MEMDOCK slot numbers: the
Spectrum top-window implementation, stock 64 KiB regions and 8 KiB chunks
have different geometries. A CPU pointer into DOCK is valid only while its
region and chunk are selected; retain descriptors across bank changes.

An ordinary stock-controller transfer gateway performs this sequence:

1. Enter common HOME code with a HOME stack and bounce buffer. Save the
   caller's region selection and software shadows of F4/FF. Preserve its
   interrupt state; do not always EI on exit if the caller entered with DI.
2. Unmap DOCK before sending MEMDOCK. Wait for the complete command reply
   and the backend's required settling interval. Ensure any interrupt code
   allowed during a long command also remains visible; otherwise keep DI.
3. Select DOCK rather than EXROM while preserving unrelated FF bits, and
   overlay only the chunk needed for this span. Copy directly only if source,
   destination, executing code and stack remain accessible together.
4. Split at 8 KiB chunk and 64 KiB region boundaries. If the selected DOCK
   window hides a HOME source/destination, alternate through the common bounce
   buffer instead of attempting an LDIR between two meanings of one address.
5. Unmap, restore the caller's region, restore FF/F4 and interrupt state, then
   return. If restoration fails, remain in HOME with an error indication.

For code overlays, place the switching stub and return continuation in HOME,
not in the outgoing overlay. Do not retain a callback, stack frame or live
instruction dependency in a bank that the callee is allowed to replace.
Treat the current region and transport as shared state: an ISR or nested file
operation must not independently select another region during a transfer.

Reserve physical ranges for the cartridge/ROM, banked data, disks and scratch
before exposing an allocator. Do not declare untested aliases or overlapping
slot numbers free. Preloading assets into SRAM can amortize SD access, but
MEMDOCK selection still has command latency; batch transfers where practical.
Measure actual operations before choosing a custom paging controller solely
for speed. A suitable first memory test writes distinct region/chunk tags,
changes several regions, and reads them all back; add address/inverse patterns
to catch mirroring and corruption. A single PEEK only tests one current view.

## Stock memory pattern: the CP/M lesson

CP/M separates CPU working memory from its much larger disk store. Its banked
disk is reached through BIOS calls, so switching through the ordinary Pico
command link is acceptable. It does not need each guest OUT to act as an
instantaneous Spectrum paging latch.

The shipped example keeps executing disk/transport code, a writable stack,
state and a 128-byte bounce buffer in HOME E000-FFFF. Before changing MEMDOCK,
it unmaps DOCK with F4=0. It maps only the selected disk chunk during the copy,
unmaps it, restores the application's region, and restores the working F4 map.
If restoring the application region fails, it remains in HOME rather than
returning into the wrong bank. Interrupts require the same visibility contract.

The current map reserves pair 4/5 for the cartridge. Disk pairs are
0/1, 2/3, 6/7, 8/9, 10/11 and 12/13. Only seven chunks per pair are usable by
this driver because chunk 7 must remain HOME. Forty 8 KiB pages give a
320 KiB disk; twenty give 160 KiB. This is a chosen layout, not a hardware
maximum, not an automatic second drive, and not 320 KiB of simultaneous TPA.

For the cold loader, source data is in HOME A000. Mapping DOCK over A000
hides that source: the driver copies via a resident bounce buffer while
alternating mappings. Test readback of every installed page. Do not use the
live HOME screen as an incidental disk staging buffer.

See [banked RAM and disk images](banked-ram-and-disk-images.md) for the exact
LBA mapping, geometry, preload and export formats. Stock SRAM operations still
require a live compatible Pico dispatcher. SRAM is volatile; CP/M file writes
modify the RAM disk, while TPSAVE exports it to SD. Direct native-SD service
is a separate optional firmware feature. CP/M 3.x banking is not implemented
or validated by the CP/M 2.2 example.

## Machine-code bank management: Spectrum 128 and TSPico 128

This section applies to the original Spectrum 128 and the modified TSPico
128 ROM/controller pair, not stock MEMDOCK. Use a common bank-manager ABI
with a target-specific paging backend; do not treat the two interfaces as
interchangeable just because both access external RAM.

| Program part | Placement and ownership |
|---|---|
| Bank manager, copy gateways, common state, interrupt handler and stack | Fixed RAM below C000; on the SD personality avoid protected A000-BFFF |
| Banked assets, datasets or code overlays | Application-owned 16 KiB banks, visible at C000-FFFF one at a time |
| ROM/editor and RAM-disk workspaces | Reserve their live banks before allocating application payloads; bank 7 needs particular care, and RAM-disk files can occupy other banks too |

A persistent reference needs `(bank, address)` or `(bank, offset)`, not just
a CPU pointer. For example, bank 3/C200 means offset 0200 in that particular
bank. Several overlays may all be linked at C000, provided each is stored in
its own allocated bank. Their addresses are valid only while that bank is
selected. Bank numbers in an example layout do not establish which banks
are actually free when returning to BASIC or using the ROM RAM disk.

### Paging byte and ROM cooperation

| Control | Original Spectrum 128 | Tested TSPico 128 controller |
|---|---|---|
| Paging output | 7FFD | Private low port 0F; 7F0F matches the modified ROM |
| Bits 0-2 | RAM bank 0-7 at C000 | Same logical bank selection |
| Bit 3 | Display bank 5/7 | No native shadow-screen implementation |
| Bit 4 | ROM selection | ROM-half latch |
| Bit 5 | Disable further paging | Paging lock implemented; do not set during ordinary bank management |
| ROM software shadow | BANK_M at 5B5C | Same variable in the modified 128 ROM |

BANK_M is a software record, not hardware bank-register readback. Keep it
synchronized when cooperating with ROM/BASIC. Code taking complete ownership
can maintain another shadow, but must reconcile the ROM's copy before calling
ROM services. A lock bit already latched in hardware cannot be undone by
clearing BANK_M. Do not rely on a helper that guesses state from a stale copy.

Illustrative bank selector, assembled in fixed RAM. It deliberately requires
the caller to have disabled interrupts; it is not a complete BASIC wrapper:

```z80
BANK_M equ $5B5C
PAGING_PORT equ $7FFD       ; original Spectrum 128
; Use $7F0F instead for the custom TSPico 128 personality.

; A = bank 0..7. Carry clear = success; set = invalid bank or locked.
; Clobbers AF, BC. Preserves DE, HL, IX, IY and interrupt state.
; Code, stack AND return continuation must remain visible below C000.
; BANK_M must accurately reflect the current paging state.
select_bank:
    cp 8
    jr nc,bank_error
    ld b,a
    ld a,(BANK_M)
    bit 5,a
    jr nz,bank_error
    and $18                ; preserve ROM and logical screen selection
    or b
    ld (BANK_M),a
    ld bc,PAGING_PORT
    out (c),a
    or a                   ; clear carry
    ret
bank_error:
    scf
    ret
```

Desktop Z80 execution checked this selector for both ports, all 256 input
bytes and all 64 ordinary paging-shadow values (32,768 cases), including
carry, no output on error, shadow updates and preserved registers. This
checks the routine's contract, not Pico bus timing or a BASIC-callable wrapper.

This routine changes only the RAM bank for valid ordinary 128 paging values.
Preserving bit 3 on TSPico does not implement the missing screen function.
Other Spectrum models, all-RAM configurations or unrelated reserved bits need
their own backend. The TSPico backend needs its controller already running:
stock firmware does not turn these private OUTs into bank selections.
Python does not process each paging request; PIO captures it and DMA passes
the selector to the address PIO, after which CPU accesses use SRAM directly.

### Data access and bank boundaries

Save the caller's full paging byte, select the payload bank, read it directly
or copy a span to a fixed buffer, then restore the saved mapping before
returning. Selection changes address decoding; it does not copy 16 KiB.
Restore the ROM/screen selection too, not just the previous three bank bits.
Every routine allowed to change paging must maintain the same shadow/lock rules.

For data reaching FFFF, transfer only the remaining span, select the next
bank from the allocation table, and continue at C000. Do not allow LDIR's
16-bit address wrap to select the next bank implicitly. A copy between two
different pageable banks needs a common buffer or an equivalent staged copy;
the one C000 window cannot expose both simultaneously. Account for the real
Spectrum's bank-2/5 aliases when choosing any fixed buffer; the TSPico copies
do not have those alias semantics.

### Banked calls, nesting and BASIC entry

A fixed-memory trampoline saves the current map, selects the target bank,
CALLs its entry (for example C000), then restores the caller's map after RET.
The stack, including the return address, stays fixed. A banked routine must
not directly page itself away and then RET through whatever replaced it.

For nested calls A -> B -> C, keep a stack of saved mappings associated with
the call frames. One global "previous bank" variable is insufficient. The
common dispatcher, mapping stack, arguments and return-value storage must
remain accessible at every nesting level. Give the call ABI explicit register,
interrupt and workspace ownership rules.

Short copies can run under DI; long routines need an interrupt handler whose
code, vector, stack and data remain valid in every allowed bank. An ISR must
not independently page memory used by an interrupted transfer unless the
bank manager explicitly supports that reentrancy. Preserve the entry interrupt
state rather than unconditionally EI on return.

Before calling from BASIC, reserve fixed memory for the wrapper and its private
stack, save BASIC's SP and paging state in stable storage, and move SP before
removing any bank containing BASIC's stack. Restore the original map before
restoring SP and returning through BASIC's saved frame. CLEAR can reserve
space; it does not move the active stack, save paging, or assign bank ownership.
On zx128sd, A000-BFFF belongs to the service: neither the wrapper nor its
private stack or copy buffers may use it. Use the cooperative gateway for SD
instead of issuing independent disk I/O while paging owns the shared resources.

The original Spectrum's fixed bank-5 screen and bank-2 RAM aliases, and its
bank-7 display switch, cannot be assumed by this TSPico port. A paging-port
substitution alone is therefore not a general machine-code program conversion.

## Custom memory pattern: the Spectrum 128 lesson

The 128 port presents HOME 4000-BFFF as fixed working/display RAM and selects
eight external 16 KiB regions at C000-FFFF. With only the top 16 KiB in DOCK,
the external physical regions are:

```text
bank n: (n << 16) + 0xC000 through (n << 16) + 0xFFFF, n=0..7
```

That is 128 KiB of external bank storage spread across the chip, not access
to every byte of its 512 KiB. A 32 KiB ROM pair in even slot 4 occupies
20000-27FFF; bank 2 occupies 2C000-2FFFF. An odd ROM slot can overlap one of
the bank regions cleared by startup. Allocate ROMs, working banks and disks
in physical addresses, not just distinct-looking slot numbers.

The custom latch accepts patched writes on private low port 0F, captures the
data once, selects the bank, changes GPIO22 for the ROM half, and implements
paging lock. DMA transfers the packed selector byte to the address state
machine; it does not copy guest RAM. In this implementation:

```text
selector = (bank << 5) | rom_slot
```

This differs from a stock MEMDOCK argument: the upper nibble must select an
even DOCK region. Preserve the proven stock memory-control instruction order
and delays; an earlier rewritten enable controller produced corruption where
the stock-sequence controller passed on the same SRAM image.

PIO handles this fast path; a Python command transaction is not a replacement
for a paging write that must affect following memory cycles. Software with
centralized bank routines could instead be ported to slower stock MEMDOCK
calls if its timing and code/stack placement permit it. Do not claim that
stock banking cannot implement any expanded-memory software.

The board does not decode low port FD for the Pico path. Native Spectrum
7FFD/FFFD/BFFD accesses therefore need reviewed paging/AY patches or another
implementation. Timex AY port translation is separate from SRAM banking.
Offline instruction scanning is useful evidence, not proof that every OUT
site, self-modifying routine or computed port has been covered.

### Limitations extra PIO does not remove

HOME 4000 and 8000 do not become physical aliases of external banks 5 and 2
when those banks appear at C000. Simultaneous access through both views cannot
be repaired just by copying at bank changes. Guest code needs alias-aware
adaptation or an emulator/different hardware where it depends on that behavior.

The SCLD displays internal HOME screen memory, not arbitrary TSPico SRAM.
Timex's alternate screen at HOME 6000 is useful for a reviewed conversion,
but is not Spectrum bank-7 shadow video. Reserve/relocate that HOME area and
translate both drawing addresses and screen selection. Extra SRAM or a DMA
ring does not grant the Pico access to the Z80's HOME/video bus.

### Keeping SD with the custom controller

Private 0F paging conflicts with normal modern status/SYNC semantics; custom
PIO also replaces the ordinary I/O service. Firmware cannot simply run both
owners unchanged. The legacy SD variant uses a cooperative driver and stack
entirely in HOME, interrupts disabled, and a saved bank/ROM-half/lock snapshot.

During SD access, suspend the memory controller, drive memory enables inactive,
and give the shared GPIO bus to SPI. On return, restore GPIO function ownership
to PIO1, controllers, selector state and lock. Wrap both native SD/MQ paths:
the native SAVE helper uses ENA_SD/ENA_MQ separately from ACTIVATE_SD/ACTIVATE_MQ.
Defer final SAVE acknowledgment until writing, cleanup and I/O restoration finish.

Before re-enabling DMA channel 0's paging bridge, clear its accumulated DREQ
credits (RP2040 CH0_DBG_CTDREQ, 50000800). CPU reads of the reused FIFO left
stale credits and caused 64 spurious transfers in the failed gateway. PIO1's
enable register numbers its local SMs 0-3: global StateMachine(4)/(5) use bits
0/1, not bits 4/5. Recheck register/backend details on other silicon.

The working legacy bench trial used SoftSPI at 100 kHz with command CRC7.
This is a conservative tested setting, not proof of a universal speed ceiling.
MicroPython 1.20 on the tested RP2040 lacks rp2.DMA; its register backend was
specific to this exclusive takeover, not a general DMA allocator.

The SD BASIC variant reserves HOME A000-BFFF and caps RAMTOP/P_RAMT at 9FFF.
Report the reduced BASIC workspace separately from external bank capacity and
the Pico's own Python heap. Spare SRAM does not automatically enlarge BASIC's
contiguous workspace or remove service-code reservations.

## Launch, recovery and evidence

For USB preparation, register inspection, and ROM-bus capture, use
[USB memory-controller debugging](usb-memory-debugging.md). It distinguishes
the live Pico interpreter, hardware PIO/DMA and Timex CPU state.

Loading ROM bytes into an unused SRAM slot needs no host reset. Starting a
new controller policy needs either a real reset hold or a validated cooperative
HOME handoff. A flag named host_held_in_reset is an assertion, not an electrical
reset command. machine.reset() restarts the Pico, not the Timex.

The no-reset prototype parks the Z80 in HOME with its HOME stack and DI,
unmaps DOCK/EXROM, then sends a validated request. The Pico acknowledges through
the old I/O handler, installs the new controllers with ROM 1 as a boot gate,
and releases ROM 0 only after setup. The Z80 checks the ROM fingerprint and
enters its startup code. Keep F4=0 while checking this HOME ROM path: copying
ZX48's OUT 244,3 mapped low DOCK instead and produced a red timeout. The model
originally missed this because it always returned ROM for low-address reads.
Probe results after a TS Reset still showed the DOCK path; explicitly establish
F4/FF rather than assuming a reset button resets all mapping and Pico state.

A no-reset handoff is not a standalone launcher. Temporary USB definitions
disappear on Pico power loss. SD Python/JSON packages need an installed loader
and dispatcher hook before a new tpi:mode command exists. Such a hook, return
to normal Timex, and native 2.3 SD support were not delivered by this experiment.
For this session's no-permanent-change trial, installed modules/main.py/UF2
were left intact. Do not infer permission to install a launcher from a memory test.

| Evidence checked for this update | Supported claim |
|---|---|
| CP/M 2.2 stock MEMDOCK sources and prior original-1.00 hardware reports | Large software-managed SRAM RAMDisk without a replacement memory policy |
| Spectrum 128 physical bank/ROM/lock tests, BASIC, PLAY and RAM-disk reports | Custom controller works for the tested modified ROM; not universal Spectrum software |
| Legacy filesystem bench: all-green load/save/reload and subsequent paging | Cooperative SD gateway works on the tested configuration |
| User's SD BASIC CODE-load report | That LOAD worked; do not promote all desktop BASIC tests to hardware passes |
| 2026-10-27 revision-2 baseline handoff report | zx128 starts without TS Reset; zx128sd no-reset handoff remained pending in this record |

Reusable local source roots are Spectrum128_PicoCartridge and
cartridgeconversion/CPM_2068. Inspect firmware/personality128_stock.py,
personality128_fs.py, handoff128.py, build_handoff128.py and
tspico-mapping-analysis.json in the former; src/sram_disk.asm,
src/sram_loader.asm and docs/tspico-firmware.md in the latter. Older audit
paragraphs retain historical "pending" statements: reconcile them with later
user reports and result files instead of treating every paragraph as current.
Published CP/M source links are in the companion banked-disk reference.
