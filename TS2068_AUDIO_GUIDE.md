# TS2068 audio development: experience map

Use this entry point for sampled speech/effects, AY-compensated digitized audio,
harmonic synthesis, optimizer regressions, CPU budgets and Audio Lab demos.

The maintained project is [speech2ay](https://github.com/jon0x0/speech2ay).
Start with the [audio skill](skills/ts2068-audio-development/SKILL.md), then load
only the relevant [project/regression experience](skills/ts2068-audio-development/references/project.md).
Its portable toolkit includes the source, Z80 references, command examples and
[Speaking with the TS2068](skills/ts2068-audio-development/assets/audio-tools/docs/speaking-with-the-ts2068.md).

Key experience: distinguish strict DAC scheduling from interrupt-paced AY;
retain generator/filter state in Ayumi; judge optimized speech by listening
as well as scores; preserve the Berzerk effect profile; distinguish actual ROM
storage from compact-format estimates. The commands are `audio2aydac`,
`speech2ay`, `ayfit`, and `aydemo`; the multi-codec demo is **TS2068 Audio Lab**.

For [web embedding](TS2068_BROWSER_DEMOS.md), use the separate TSRun skill.
For cartridge paging and physical images, use the
[cartridge skill](skills/ts2068-cartridge-development/SKILL.md).
