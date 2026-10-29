# Driving TSPico memory-controller debug through USB

Use this for live TSPico SRAM, mapping, paging, PIO/DMA and mode-startup tests.
Use [expanded memory](expanded-memory.md) first to establish the intended map.
The examples below target the tested V2.2/RP2040 setup, not every Pico board.

## Three independently running parts

| Part | What interrupt/reset means |
|---|---|
| Pico MicroPython dispatcher | Ctrl-C can stop its Python loop; PIO/DMA may continue servicing memory |
| Pico PIO/DMA memory controller | Continues independently until explicitly stopped/reconfigured or the Pico resets |
| Timex Z80 and SCLD mapping | TS Reset is separate from Pico reset; explicitly establish F4/FF rather than assuming every mapping resets |

After interrupting the dispatcher, stock TSPico commands may no longer be
serviced even though the Timex still executes external memory. Restarting the
PC helper does not resume that dispatcher or clear the Pico interpreter.
Resetting the Timex does not restore replaced Pico state machines.

For a known cold recovery, stop the helper, power off the Timex and remove
Pico USB power. This loses temporary Python definitions and volatile SRAM.
Keeping USB connected may keep the Pico/card powered. Preserve a useful
capture before power cycling. A return-to-stock command is mode-specific,
not implied by any generic reset or by the proposed tpi:mode interface.

## Connect and prepare the interpreter

Use the Pico USB serial port from Thonny, Tera Term, or a PC serial helper;
only one should own the port. Enumerate the port instead of assuming COM14
is portable. Disconnect Thonny without Run/Restart when retaining live state.

At the normal MicroPython REPL, a first check can be:

```python
import sys, os, gc, rp2
print(sys.implementation)
print(os.uname())
print('DMA API:', hasattr(rp2, 'DMA'))
print('free heap:', gc.mem_free())
```

For the tested firmware, guided Ctrl-C twice then Ctrl-B established `>>>`
without a Pico reboot. Interrupt only when the operation/state permits it;
do not interrupt an SD write merely to acquire a console. A generic helper
must not send a reboot to get a prompt. Ctrl-D at normal REPL is a soft reset;
Ctrl-D after a confirmed raw-REPL banner executes the submitted source.

Temporary source can be executed in the existing REPL globals, with multiple
definitions followed by an explicit start call. Loading definitions must not
itself alter pins or PIO. Inspect module top-level code before treating it as
definitions-only. Keep controller objects and DMA buffers referenced so GC
does not invalidate live resources. This approach does not require writing
main.py, installing a /TS package, or replacing frozen firmware.

## Inspect before changing the controller

This is a small read-only RP2040 status snapshot; it does not pause machines,
pop RX FIFOs, execute PIO instructions or change mappings:

```python
from machine import mem32
g = mem32[0xd0000004] & 0xffffffff
print({
    'pio0_enabled': hex(mem32[0x50200000] & 15),
    'pio1_enabled': hex(mem32[0x50300000] & 15),
    'rom_half_pin': (g >> 22) & 1,
    'address_nibble': (g >> 15) & 15,
    'memory_enable_pins': (g >> 19) & 7,
    'roscs': (g >> 26) & 1,
    'dma0_remaining': hex(mem32[0x50000008] & 0xffffffff)
})
```

These pins describe current electrical signals, not a reliable history or a
full logical bank state. The address nibble changes between ROM and DOCK
cycles; pair it with /ROSCS and the CPU window being exercised. DMA remaining
is a raw count, not bytes of Z80 RAM copied. Mask unsigned register values:
MicroPython can otherwise print a large counter as a negative number.

PIO1's register uses local bits 0/1 for global StateMachine(4)/(5). In the
tested stock arrangement those are memory control and address selection;
PIO0 SM0 is normal I/O, replaced by the paging latch in the custom personality.
Inspect actual firmware allocations before assuming that arrangement elsewhere.
Reading an RX FIFO consumes data; even an SM.exec diagnostic can alter live
state. Reading PIO instruction-memory registers is not a program dump: RP2040
instruction memory is write-only. Inspect the assembled instruction arrays.

## Change controller state only with a defined host condition

Keep a resource map of owned PIO words/SMs, DMA channels, GPIO functions and
FIFO users. The tested custom controller took exclusive ownership; do not
reuse its register-DMA backend as an allocator for unrelated firmware.

Use either a brief physical TS Reset hold or a verified HOME trampoline with
DI, HOME stack and explicit handshake before a takeover. Passing
host_held_in_reset=True does not assert or detect reset. The no-reset
trampoline must explicitly set F4/FF and remain in HOME until acknowledgment
and the correct ROM-path readiness check succeed. See the companion reference
for the corrected F4=0 handoff; low DOCK bypasses the ROM-half gate.

Follow each job's release point. Definitions and status normally leave TS
Reset released. For an arm-only probe, hold Reset during arming, release at
DONE, then collect with Reset released. A foreground service job may instead
require release at ARMED, before completion. Do not hold Reset while waiting
for preparation of another job, or press it again for collection.

## Inspect the actual ROM reads

The project's ROM probe temporarily disables paging observation/DMA, preserves
the PIO1 memory controllers, fixes the ROM-half output, and samples qualified
low-ROM reads. It enables the bus buffer to observe data but does not drive
the data pins. That changes the debug configuration; a successful arm is not
a successful boot and a menu is not expected during this probe.

Capture data together with address-nibble, memory enables, ROM-half and
/ROSCS. The failed handoff captured 00 AF 95 8A with /ROSCS=0 and nibble 0,
not expected F3 01 2B 69: the CPU was on the DOCK path. Returning different
bytes alone would not establish that the SRAM image was corrupt.

Collect a snapshot of the FIFO count and read only that many entries, not an
unbounded loop while the producer runs. For longer DMA traces, retain a
bounded ring and stream it to the PC in small chunks. A large Python list or
single JSON result exhausted heap in the original trace collector. If the
buffer still exists after a MemoryError, recover it before re-arming.

## Existing PC helper and source

Spectrum128_PicoCartridge/pico_debug.py is the tested project-local helper;
it is not installed as part of this skill. The reference above also works
with a manually operated REPL. The project's helper supports:

```text
python pico_debug.py ports
python pico_debug.py queue preflight
python pico_debug.py serve --port COM14 --timeout 30 --interrupt --once
```

The last command is one guided example for an interruptible dispatcher; omit
--interrupt if already at the prompt. It prompts before interrupting and
before executing the job. Raw REPL source is executed only after its banner
is verified. Board-specific actions are in the script's ACTIONS table;
definition files and their dependencies are explicitly listed there.

Queued jobs store exact source/hash, reset requirement and description.
Results include stdout, traceback, transport errors and parsed status. Keep
dependency ordering explicit: Windows timestamps tied and random IDs once
reordered definitions, causing missing asm_pio imports. Do not automatically
replay an unfinished running job; a lost PC response does not mean the Pico
stopped executing. A serial `ok` means source finished without an exception,
not that the Timex saw the expected ROM or booted.

Reusable source in that project: pico_debug.py, test_pico_debug.py,
firmware/personality128_stock.py, personality128_fs.py, handoff128.py,
rom_read_probe128.py, gpio_trace_stream128.py, and the serial result files.
Early SERIAL-DEBUG.md text predates --interrupt, additional allowlisted files
and persistent service jobs; verify it against the current script. No USB
connection or Pico configuration is changed merely by reading this reference.
