# TS2068 browser demos: experience map

Use this entry point to embed an automatically loaded DCK in a web page or
publish a playable TS2068 example on GitHub Pages.

Read the [TSRun web-demo skill](skills/ts2068-tsrun-web-demo/SKILL.md) and its
[integration reference](skills/ts2068-tsrun-web-demo/references/embedding.md).
The working example is [TS2068 Audio Lab](https://jon0x0.github.io/speech2ay/),
with [source in speech2ay](https://github.com/jon0x0/speech2ay/tree/main/web).

Key experience: a same-origin adapter imports live upstream TSRun modules,
loads the local cartridge, and handles audio activation and keys. A remote
iframe alone cannot inject a cartridge without an upstream loading API. Keep
the local worklet shim, frame pacing, CORS/API checks and fallback download.
Automatic loading still needs a user gesture for audible playback.

For generating the audio cartridge itself, start with [audio development](TS2068_AUDIO_GUIDE.md).
