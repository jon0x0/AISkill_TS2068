# TS2068 AI Skill Library

This folder is a general collection point for reusable AI skills, supporting tools, worked examples, and human-readable technical material for the Timex Sinclair 2068. It is organized so additional TS2068 subjects can be added as independent skills without being folded into the existing cartridge material.

The library includes independent **TS2068 cartridge development** and **TS2068 audio development** skills. Its material applies equally to original TS2068 cartridge software and to sophisticated ports or conversions of Spectrum programs.

## Find relevant experience

| Need | Entry point |
|---|---|
| Convert audio, choose codecs, explain CPU/storage or diagnose optimization | [Audio experience map](TS2068_AUDIO_GUIDE.md) and [speech2ay](https://github.com/jon0x0/speech2ay) |
| Embed TSRun, automatically load a DCK or publish a browser demo | [Browser demo experience map](TS2068_BROWSER_DEMOS.md) |
| Design banking, startup or physical cartridge output | [Cartridge guide](TS2068_CARTRIDGE_GUIDE.md) |
| Reuse a proven memory map | [Worked examples](TS2068_CARTRIDGE_EXAMPLES.md) |
| Find a tool, resolve a specific question or decode terminology | [Utilities](TS2068_CARTRIDGE_UTILITIES.md), [FAQ](TS2068_CARTRIDGE_FAQ.md), [glossary](TS2068_CARTRIDGE_GLOSSARY.md) |

Read the selected skill and its task-specific references rather than loading
the entire library. The independent skills cover cartridge development, audio
development, and TSRun web demos; each directory is a portable skill unit.

## Skill catalog

- [Local AI skill catalog](skills/README.md) lists the skills stored in this library and explains how to add future skills.
- [David Anderson's TS2068 Reference Library](https://github.com/timex-sinclair-projects/TS2068-Ref-Library) is a companion TS2068 programming and AI-reference tree containing broader machine documentation, ROM material, disassemblies, and programming resources.

## AI skill library layout

Reusable skills live under `skills/`, with one self-contained directory per skill:

```text
AISkill_TS2068/
├── README.md
├── TS2068_CARTRIDGE_*.md
└── skills/
    ├── README.md
    ├── ts2068-cartridge-development/
    │   ├── SKILL.md
    │   ├── agents/
    │   ├── references/
    │   ├── scripts/
    │   └── assets/
    ├── ts2068-audio-development/
    │   └── SKILL.md
    └── ts2068-tsrun-web-demo/
        └── SKILL.md
```

The `skills/<skill-name>/` boundary is the unit to copy, install, publish, or give to another AI. Human-oriented library documentation remains at the root. Add future skills as peers of `ts2068-cartridge-development`, never by mixing their scripts or references into an existing skill.

## Cartridge development

The [TS2068 cartridge-development skill](skills/ts2068-cartridge-development/SKILL.md) covers cartridge memory architecture, software conversion, DCK and physical-ROM creation, media packing, and deterministic emulator debugging. It is supported by the following human-readable material.

### Start here

- [General introduction and development guide](TS2068_CARTRIDGE_GUIDE.md) explains how TS2068 cartridges work, how to structure a project, and the differing dos and don'ts for BASIC and machine-code cartridges.
- [Frequently asked questions](TS2068_CARTRIDGE_FAQ.md) gives direct answers about memory, banking, BASIC, ROM coexistence, and use of the full 64K cartridge.
- [Worked examples and memory maps](TS2068_CARTRIDGE_EXAMPLES.md) trace the exact Elite ECM and TSVideoCodec cartridge, RAM, execution, display, decoder, media, and ROM layouts.
- [Utilities guide](TS2068_CARTRIDGE_UTILITIES.md) documents the bundled DCK tools, the external [zx81-utils `dckls`](https://github.com/ryangray/zx81-utils) extractor, the browser-based [TS2068 TAP to Cartridge Builder](https://timex-sinclair-projects.github.io/2068-TAP-To-Cart/), [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) for authoring Extended Color Mode artwork, the deterministic Fuse launcher, Python API, and assembly templates.
- [Glossary](TS2068_CARTRIDGE_GLOSSARY.md) defines acronyms and specialized cartridge, display, file-format, and Z80 terms.
- [Blog article](TS2068_CARTRIDGE_BLOG_POST.md) is a less formal overview suitable for publication or adaptation.

### The central idea

See the [glossary](TS2068_CARTRIDGE_GLOSSARY.md) for complete terminology definitions.

The TS2068 Technical Reference Manual calls the cartridge-supplied external bank the **[Dock (Cartridge) Bank](TS2068_CARTRIDGE_GLOSSARY.md#dock "Dock is a bank name, not an acronym")**. This library normally writes the bank name as **DOCK** to distinguish it visibly from HOME and EXROM; DOCK is not an acronym.

The Z80 central processing unit (CPU) has a 64K address space, which the TS2068 divides into eight fixed 8K chunks. Port `$F4`, the Horizontal Select Register ([HSR](TS2068_CARTRIDGE_GLOSSARY.md#hsr "Horizontal Select Register")), chooses independently whether each address range comes from internal HOME memory or from external memory. Port `$FF`, the Display Enhancement Control Register ([DECR](TS2068_CARTRIDGE_GLOSSARY.md#decr "Display Enhancement Control Register")), controls video and interrupts; its bit 7 decides whether HSR-selected external chunks come from the cartridge DOCK bank or the Extension ROM ([EXROM](TS2068_CARTRIDGE_GLOSSARY.md#exrom "Extension ROM")) bank.

EXROM is the supplementary Extension ROM bank, not another cartridge and not an additional 64K of general storage. The production TS2068 populated it with an 8K U20 ROM in chunk 0 at `$0000-$1FFF`, containing cassette I/O, video-mode services, initialization and bank-switching code, and the source of the RAM-resident function dispatcher. Timex's internal planning recognized that the machine could support a 16K EXROM: such an implementation occupies chunks 0 and 1 at `$0000-$3FFF`, selected together with HSR=`$03`. The factory U20 still supplies only the first 8K, so software using stock services normally selects HSR=`$01`. Selecting EXROM is global: while DECR bit 7 is set, HSR-selected external chunks no longer come from DOCK.

This is an overlay system, not a conventional numbered-page system. Cartridge chunk 5 always appears at `$A000-$BFFF`; it cannot be redirected to `$8000` or another window. Switching changes which physical memory answers an address. It does not move or copy bytes.

There is an important display exception to the CPU's view. If cartridge chunk 2 is selected, a CPU read at `$4000` returns cartridge data, not the HOME screen byte underneath it. The Standard Cell Logic Device ([SCLD](TS2068_CARTRIDGE_GLOSSARY.md#scld "Standard Cell Logic Device")) display hardware nevertheless continues fetching the visible picture from HOME screen random-access memory (RAM). The picture remains on screen, but the CPU cannot read or change that hidden HOME screen until HSR bit 2 is cleared. The same principle applies to the second display file in HOME chunk 3.

### Chunk map

| Chunk | HSR mask | Flat cartridge offset | TS2068 CPU address |
|---:|---:|---|---|
| 0 | `$01` | `$0000-$1FFF` | `$0000-$1FFF` |
| 1 | `$02` | `$2000-$3FFF` | `$2000-$3FFF` |
| 2 | `$04` | `$4000-$5FFF` | `$4000-$5FFF` |
| 3 | `$08` | `$6000-$7FFF` | `$6000-$7FFF` |
| 4 | `$10` | `$8000-$9FFF` | `$8000-$9FFF` |
| 5 | `$20` | `$A000-$BFFF` | `$A000-$BFFF` |
| 6 | `$40` | `$C000-$DFFF` | `$C000-$DFFF` |
| 7 | `$80` | `$E000-$FFFF` | `$E000-$FFFF` |

### Can all 64K be used?

Yes. All eight physical cartridge chunks can hold useful code or data. A practical full-capacity design keeps a small executable player or dispatcher in chunk 4, pages the other seven chunks as data, and preserves selected HOME chunks for the stack, display, ROM, and working RAM. Data stored in cartridge chunks 2 and 3 can be copied into upper HOME RAM early, allowing those HOME chunks to be restored for normal display access.

Although HSR=`$FF` exposes the complete cartridge at once, it also hides every byte of HOME ROM and RAM from the CPU. A read-only cartridge then provides no writable stack or normal interrupt handler. Selective overlays are therefore the normal way to use all 64K of storage.

### Examples

#### Elite: a polished cartridge startup

The Elite TS2068 cartridge is a conversion of the ZX Spectrum Elite JCV tape program (`ELITEJCV.TAP`), not an originally cartridge-based TS2068 program. A title screen can be stored as raw TS2068 Extended Color Mode artwork when cartridge space permits; this is the simplest and fastest form because it needs no decompressor. [Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/) can create the matching bitmap and 8×1 color planes from source artwork; the Elite cartridge's ECM title image was converted using its **Sierra Lite** dithering mode. [PackBits](TS2068_CARTRIDGE_GLOSSARY.md#packbits "PackBits run-length compression") is an optional space-saving step when the two planes need to occupy less cartridge storage. In the Elite build, the complete 6144-byte bitmap plane is stored in cartridge chunk 4 at `$8100-$98FF` and copied to HOME `$4000-$57FF`; the separate 6144-byte color/attribute plane is stored in chunk 2 at `$4000-$57FF` and revealed into HOME `$6000-$77FF`. A small launcher copies the bitmap, reveals the colors with a curtain wipe, holds the finished image, blanks it cleanly, restores normal video mode, and then enters the main program. See the [exact Elite title-screen memory map](TS2068_CARTRIDGE_EXAMPLES.md#example-1-elite-ecm-spectrum-conversion), the [copy, reveal, and display-code execution sequence](TS2068_CARTRIDGE_EXAMPLES.md#ecm-display-routine-procedure-and-execution-location), and the [differences between machine-code and BASIC hosts](TS2068_CARTRIDGE_EXAMPLES.md#machine-code-versus-basic-host-programs).

#### [TSVideoCodec](https://github.com/jon0x0/TSVideoCodec): FIFO-packed media

TSVideoCodec begins playback with a complete Extended Color Mode keyframe: PackBits compresses the first frame's 6144-byte bitmap and 6144-byte color planes, and the cartridge player decompresses both to establish the initial picture before applying later delta frames. Its command-aware [FIFO](TS2068_CARTRIDGE_GLOSSARY.md#fifo "first-in, first-out logical stream") packer treats cartridge chunks 0, 1, 2, 3, 5, 6, and 7 as one logical 56K media stream while chunk 4 holds the resident player and tables. Chunks 2 and 3 are copied into upper HOME RAM at startup so the live display can remain CPU-accessible. Short boundary commands tell the delta decoder when to select the next source chunk, allowing compressed update records to cross 8K boundaries instead of wasting the unused tail of every bank. This occupies the complete cartridge usefully as code plus tightly packed data; a design seeking still more payload can relocate the player to HOME RAM and add the unused ranges of chunk 4 as additional FIFO segments. See the [player, decoder, and media memory map](TS2068_CARTRIDGE_EXAMPLES.md#example-2-tsvideocodec-fifo-media-cartridge).

### Tools included in the cartridge-development skill

- [`pack_dck.py`](skills/ts2068-cartridge-development/scripts/pack_dck.py): creates Fuse DCK files and flat physical-cartridge binaries.
- [`inspect_dck.py`](skills/ts2068-cartridge-development/scripts/inspect_dck.py): reports descriptors, chunk addresses, headers, hashes, and expanded layout.
- [`run_fuse_debug.py`](skills/ts2068-cartridge-development/scripts/run_fuse_debug.py): runs deterministic Fuse debugger command files on Windows, macOS, or Unix-like systems; see the [macOS support qualification](TS2068_CARTRIDGE_UTILITIES.md#fuse-debugger-automation-on-macos).
- [`dck_format.py`](skills/ts2068-cartridge-development/scripts/dck_format.py): shared strict DCK parser/builder API.
- [`machine-code-aros.asm`](skills/ts2068-cartridge-development/assets/machine-code-aros.asm): minimal direct-execution Application ROM-Oriented Software ([AROS](TS2068_CARTRIDGE_GLOSSARY.md#aros "Application ROM-Oriented Software")) cartridge template.
- [`home-bank-gateways.asm`](skills/ts2068-cartridge-development/assets/home-bank-gateways.asm): safe HOME-RAM bank-transition patterns.

See the [complete utilities guide](TS2068_CARTRIDGE_UTILITIES.md) for syntax, examples, validation behavior, and limitations.

The DCK format is an emulator container and is not byte-for-byte identical to a flat physical ROM. Always build and verify both outputs when physical hardware is a target.

### Recommended working method

1. Draw a chunk map before writing code.
2. Record the location of the PC, stack, interrupt handler, display, ROM dependencies, and writable variables for every mapping.
3. Keep software shadows of HSR and DECR.
4. Make bank transitions deterministic and disable interrupts around unsafe intermediate mappings.
5. Test DCK structure statically, then trace exact execution under the TS2068 model in Fuse.
6. Verify the final flat binary on the intended cartridge hardware.


## Audio development

[TS2068 audio-development skill](skills/ts2068-audio-development/SKILL.md) packages audio2aydac, speech2ay, ayfit and aydemo from [speech2ay](https://github.com/jon0x0/speech2ay), documented Z80 players, TAP/DCK/PicoROM exporters and synthetic examples. Read [Speaking with the TS2068](skills/ts2068-audio-development/assets/audio-tools/docs/speaking-with-the-ts2068.md) for quality, CPU and compression tradeoffs. [Tool instructions](skills/ts2068-audio-development/assets/audio-tools/README.md) and [validation scope](skills/ts2068-audio-development/assets/audio-tools/docs/validation.md) accompany the source.

## Browser demos

The [TSRun web-demo skill](skills/ts2068-tsrun-web-demo/SKILL.md) records automatic DCK loading with live upstream emulator modules, browser sound and input handling, and GitHub Pages deployment. Start with the [experience map](TS2068_BROWSER_DEMOS.md).
