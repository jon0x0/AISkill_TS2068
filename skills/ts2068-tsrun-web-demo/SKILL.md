---
name: ts2068-tsrun-web-demo
description: Embed TSRun in a web page with automatic TS2068 DCK loading, live upstream emulator modules, browser audio and keyboard controls, and GitHub Pages deployment.
---

# TSRun browser cartridge demos

Use this for a browser-playable TS2068 cartridge demo. Read
[embedding and validation](references/embedding.md) for the working integration,
audio-worklet pitfall, frame pacing, source locations and deployment checks.

The reusable example is [speech2ay web/](https://github.com/jon0x0/speech2ay/tree/main/web),
running as [TS2068 Audio Lab](https://jon0x0.github.io/speech2ay/).
Its emulator modules and ROMs come from the live
[TSRun site](https://josef-jelinek.github.io/TSRun/); its adapter and DCK come from
the demo project. Inspect the current upstream interface before adapting it.

Keep emulator integration distinct from cartridge generation. Use an existing
verified DCK or the appropriate cartridge/audio workflow for a new one. Do not
promise automatic file injection into a cross-origin iframe unless upstream
explicitly supports it. A same-origin adapter can import upstream modules and
load the local DCK itself, as in the reference implementation.

Preserve user-chosen naming and links between demo and source repository.
Ask for publishing decisions only when absent; this skill does not itself
authorize commits, pushes, deployments or scheduled updates. A documentation
update does not require deploying a demonstration site.
