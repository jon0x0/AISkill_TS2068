# TS2068 AI Skill Catalog

This directory is the collection point for reusable AI skills related to the Timex Sinclair 2068. Each immediate child directory is an independent skill package that can be copied, installed, versioned, or published without depending on another skill folder.

## Local skills

| Skill | Purpose |
|---|---|
| [`ts2068-cartridge-development`](ts2068-cartridge-development/SKILL.md) | Design, build, inspect, port, and debug TS2068 DOCK cartridges, including banking, HOME-RAM transfers, AROS/LROS, ECM media, DCK/BIN creation, and deterministic Fuse validation. |

## Companion skill and reference trees

- [David Anderson's TS2068 Reference Library](https://github.com/timex-sinclair-projects/TS2068-Ref-Library) provides broader TS2068 programming material and AI-oriented reference context, including machine documentation, ROM material, disassemblies, and programming resources. Use it as a companion to the cartridge-specific skill rather than copying its contents into this directory.

## Directory contract

Add each future skill as `skills/<skill-name>/`, using lowercase letters, digits, and hyphens in the folder name. A skill package has this shape:

```text
skill-name/
├── SKILL.md              required skill metadata and operating instructions
├── agents/
│   └── openai.yaml       recommended user-interface metadata
├── references/           detailed information loaded only when needed
├── scripts/              deterministic reusable tools
└── assets/               templates or files copied into outputs
```

Only `SKILL.md` is mandatory. Create optional directories only when the skill actually needs them. Do not put a second skill's instructions, scripts, references, or assets inside an existing skill package.

## Adding a future skill

1. Choose a short, descriptive, lowercase hyphenated name.
2. Create a peer folder under `skills/` with a complete `SKILL.md` containing only `name` and `description` in its YAML frontmatter.
3. Keep the main instructions concise and route detailed subject matter into directly linked files under `references/`.
4. Put repeatable executable work in `scripts/`, and output templates or reusable binary resources in `assets/`.
5. Add `agents/openai.yaml` when the target AI system supports skill-list metadata.
6. Validate the complete skill with the target system's skill validator and exercise any bundled scripts before treating it as usable.
7. Add one row to the local-skills table above and link related human documentation from the library root README.

The directory containing `SKILL.md` is the portable unit. When installing a skill into Codex or another compatible AI environment, copy that complete directory rather than selecting individual files.
