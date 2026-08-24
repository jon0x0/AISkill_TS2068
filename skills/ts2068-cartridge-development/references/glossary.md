# TS2068 cartridge glossary

Core acronyms: **HSR** = Horizontal Select Register; **DECR** = Display Enhancement Control Register; **SCLD** = Standard Cell Logic Device; **AROS** = Application ROM-Oriented Software; **LROS** = Language ROM-Oriented Software; **EXROM** = Extension ROM. Treat **DCK** as Fuse's conventional cartridge-format name and `.dck` extension; do not assume a longer official expansion.

- **AROS — Application ROM-Oriented Software:** system-ROM-supported cartridge application, normally based in chunk 4 at `$8000`.
- **BIN — binary image:** flat physical-cartridge bytes, normally eight consecutive 8K chunks for a 64K image.
- **chunk:** one fixed 8K range; chunk N occupies `N*$2000` through `N*$2000+$1FFF`.
- **CPU — central processing unit:** the Z80; HSR controls its memory view but not the SCLD display-fetch source.
- **DCK — Fuse cartridge-image format:** conventional name and `.dck` extension for Fuse's descriptor-based Timex cartridge container; do not assume a longer official expansion.
- **DECR — Display Enhancement Control Register:** write-only port `$FF`; controls video, interrupt inhibition, and DOCK/EXROM selection.
- **DOCK:** external cartridge bank; a bank name rather than an acronym.
- **ECM — Extended Color Mode:** TS2068 pixel-plus-color display mode using both HOME display files.
- **EXROM — Extension ROM:** supplementary external ROM bank selected globally instead of cartridge DOCK by DECR bit 7. Factory U20 supplies 8K at EXROM `$0000-$1FFF` (chunk 0); a verified 16K implementation can also supply `$2000-$3FFF` (chunk 1), with HSR=`$03` selecting both. Do not assume the second chunk exists in a stock machine.
- **FIFO — first in, first out:** here, a logical sequential stream over ordered cartridge/RAM segments, advanced by explicit bank-boundary commands; not a hardware FIFO.
- **HOME:** internal TS2068 ROM/RAM bank; a bank name rather than an acronym.
- **HSR — Horizontal Select Register:** port `$F4`; one bit per fixed 8K range, where zero selects HOME and one selects the DECR-selected external bank.
- **IM1 — Z80 Interrupt Mode 1:** maskable interrupts enter `$0038`.
- **ISR — interrupt-service routine:** code entered for an interrupt; keep its code, data, vector, and stack visible.
- **LDIR:** Z80 block-copy instruction; source and destination obey the current HSR mapping.
- **LROS — Language ROM-Oriented Software:** cartridge-resident language/operating environment with broad machine control.
- **OS — operating system:** TS2068 system ROM plus associated HOME-RAM state.
- **overlay:** same-address substitution of DOCK/EXROM for HOME in the CPU's view; no bytes are moved.
- **PackBits:** optional byte-oriented run-length encoding; controls `0-127` copy `control+1` literals, `129-255` repeat the next byte `257-control` times, and `128` is a no-op. Prefer raw data when space permits; use PackBits only for worthwhile savings, and stop from descriptor lengths.
- **PC — program counter:** Z80 register pointing to the next instruction.
- **RAM — random-access memory:** writable memory.
- **ROM — read-only memory:** immutable during normal execution; writes do not pass through to hidden HOME RAM.
- **SCLD — Standard Cell Logic Device:** TS2068 control logic; its display path reads HOME video RAM independently of CPU HSR mapping.
- **SP — stack pointer:** Z80 register locating the active stack; keep it in visible writable memory.
