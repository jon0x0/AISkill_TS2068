# PicoVideo 4.2: 80-column text and bank-aware display capture

Use this for an 80-column console, firmware detection, unexpected garbage while
using DOCK RAM, or palette behavior. PicoVideo is the **display card**, separate
from the **TSPico** SRAM/SD device. Updating one does not update the other.

## Identify the actual implementation

The inspected PicoVideo 4.2 uses ULA+ selector port BF3B and data port FF3B.
Use 16-bit port addressing (`LD BC,port; IN/OUT (C)`) and allow selector/data
settling. Immediate OUT (n),A does not fix the high address byte to BF/FF.
Save/restore the caller's selector and avoid concurrent register writers.

| Register | Inspected 4.2 meaning |
|---|---|
| 7F | Version: 42 hex |
| 40 | Extended display enable |
| 41 | Display mode: 5 for 80-column text; 6 for standard 64-column bitmap |
| 43 | Memory mirror; 0 for ordinary HOME mapping, nonzero redirects DF1 writes |
| 00–3F | ULA+ palette entries |

A response such as `7F=10, 40=00, 41=00, 43=FF` matches the published older
**V4** source. SOFTWARE_VER=10 hex does not prove a product called version 1.0.
That source leaves its 80-column renderer commented out and does not implement
register 43. Do not enable mode 5 merely because some ULA+ registers respond.
Other versions need their own source/register contract; floating FF is not
positive identification. Retain 64-column fallback until support is established.

## Text framebuffer and setup

The inspected renderer uses 80 columns × 24 rows and its installed 8x8 font:

```text
HOME 4000–477F: 1920 character codes, row-major
HOME 4780–4EFF: 1920 corresponding attributes, row-major
offset = row * 80 + column
```

Map HOME while writing those ranges. CPU DOCK data at the same address is not
the framebuffer. Reserve both regions against BASIC, loaders and other buffers.
After positive version/selector validation, set mirror 43=0, select mode 41=5,
set suitable palette entries, initialize all characters/attributes, and enable
40=1. Preserve the host's F4/FF shadows, stack and interrupt ownership.

The CP/M implementation uses fixed attributes selecting palette entry 7 for
ink and 8 for paper. This is an application palette convention, not a required
pair for every program. ULA+ GRB packing is GGGRRRBB. A width switch must select
the corresponding renderer, clear/reinitialize its screen, and tell programs
the actual width. Changing a mode register alone cannot convert a 64-column
bitmap console into an 80-column text console.

Scrolling moves character and attribute rows together and clears the new row.
Preserve an application status row if it owns one. Keyboard handling remains
the host's responsibility. The CP/M driver defaults to 80 only on recognized
4.2 and offers COLUMNS 64/80; applications such as the configured Infocom
interpreter read the width at launch. Restart them after changing it.

## Banking corruption is not necessarily CPU-memory corruption

Older published V4 copies captured video-address writes directly into its
private `gDfRam[addr & 3fff]`, without checking the TS2068 F4 mapping. Programs
using DOCK RAM at 4000–7FFF can therefore appear as random display bytes during
loads or typing while the CPU's HOME video RAM remains intact. Redrawing only
temporarily repairs that separate display copy. Relocating a single preload
buffer cannot prevent arbitrary program writes to the same banked addresses.

The inspected 4.2 bus handler records F4 and only captures DF1 writes when
F4 bit 2 is clear, and DF2 writes when F4 bit 3 is clear. It ignores the
out-of-bank memory writes; it does not blank the whole display whenever DOCK
is selected. Mirror mode adds separate behavior, so clear it for this console.

When debugging, compare HOME screen bytes, DOCK program bytes and a modeled
PicoVideo capture buffer separately. Verify full 16-bit I/O decoding and
bank-restoration paths. Report firmware register values and the exact build;
an emulator without PicoVideo capture cannot prove this hardware behavior.

## 64-column ink and border pitfall

The inspected older and 4.2 source contain:

```c
gTsCol64Ink = ((~gTsRegFF) & 0x3f) | ((gTsRegFF >> 3) & 7);
```

Mode bits leak into the low ink bits: FF=06 produces attribute 39 hex, blue
on white rather than black on white. The source correction uses mask 38 hex.
The CP/M software workaround enables the known 64-column ULA+ mode and gives
both possible ink palette indices the same RGB value. Do not write unverified
registers on unknown firmware. A standard native TS2068 uses the DECR's
ink/complementary-paper convention and the FE border.

Match the border to paper by default; a separate optional argument can select
a custom border. In 64-column palette mode, choose a border entry that does
not overwrite either ink entry or paper. CP/M uses a spare index for this.
Retain the user's chosen border when appropriate; the existing CP/M width
change resets it to matched paper and documents that behavior.

## Upgrade with an exact rollback path

1. Power off/unplug the TS2068 and remove PicoVideo from the expansion connection.
2. Hold BOOTSEL on its Raspberry Pi Pico while connecting a Micro-USB data
   cable to a PC. Release when RPI-RP2 appears. Entering BOOTSEL does not erase.
3. With Raspberry Pi picotool, run `picotool save -a -v PicoVideo-original.uf2`.
   Wait for successful save and verification; retain a second copy. The USB
   drive does not expose the installed firmware as an ordinary file to copy.
4. On Windows, inaccessible BOOTSEL devices may need WinUSB on **RP2 Boot
   (Interface 1)** through Zadig; leave the mass-storage interface untouched.
5. Extract the official 4.2 ZIP and copy its top-level picoTsVid.uf2 to RPI-RP2.
   It disconnects when flashed. Disconnect USB and reinstall with TS2068 off.
6. Check register 7F=42, enable the intended mode and exercise scrolling,
   load transfers and typing on the actual board.

To revert, enter BOOTSEL and copy the verified original UF2 back to RPI-RP2.
BOOTSEL is a Pico ROM loader and remains available if application video fails.
The published V4 UF2 is a fallback, not an exact backup of an unknown installation.
No TSPico SD file or firmware update is needed for a PicoVideo-only upgrade.

## Source and validation boundary

- [Official PicoVideo repository](https://github.com/timex-sinclair-projects/PicoVideo)
- [V4 source archive](https://github.com/timex-sinclair-projects/PicoVideo/blob/main/V4/picoPgmV4.zip)
- [4.2 package](https://github.com/timex-sinclair-projects/PicoVideo/blob/main/v4.2/picoTsVid4_2.zip):
  picoCode/macros.h, coreB/busMain.c, coreV/displayProc80.c, CMakeLists.txt
- [picotool backup commands](https://github.com/raspberrypi/picotool#save)
- [CP/M console example](https://github.com/jon0x0/ts2068/blob/cpm22-v0.1.0/CPM_2068/src/picovideo.asm)
- [Palette workaround](https://github.com/jon0x0/ts2068/blob/cpm22-v0.1.0/CPM_2068/src/console_palette.asm)

The CP/M hardware report identified the older V4 symptoms. 4.2 detection,
palette, wrap/scroll, attributes and bank-filter contracts were tested with
native Z80 models and inspected source; do not promote that to universal
physical-board verification. A future reduced-width-font 80-column renderer
on a plain TS2068 is a separate design, not this PicoVideo framebuffer mode.
