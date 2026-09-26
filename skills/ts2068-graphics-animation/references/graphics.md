# Artwork, gradients, transparency and color conflicts

## Conversion and gradient generation

Compose at the intended native resolution; retain the RGB/RGBA source alongside
the constrained output. Resize before quantization. Inspect an enlarged nearest-
neighbor preview and a native-size preview: softened RGB previews hide ECM errors.
For RGBA resizing, preserve alpha and use premultiplied-alpha filtering when
hidden RGB would otherwise bleed dark fringes into edges. Composite semitransparent
edges against their intended background before choosing palette pairs.

Build a sky from ordered vertical RGB stops. For each scanline, interpolate between
the surrounding stops, clamping outside the range. Design the gradient over the
whole scene before cropping it into cloud/hill bands so their boundaries agree.
Cloud alpha can then reveal the same sky beneath. If a cloud strip includes its
sky, the sky texture scrolls with the cloud; use a separately composed fixed sky
when that motion is undesirable. Plan tile seams as well as internal gradients.

For each legal paper/ink pair p,q, project source RGB onto their mixture:

`t = clamp(dot(rgb-p, q-p) / dot(q-p, q-p), 0, 1)`.

Choose a pair by reconstruction error over an 8x1 cell (static colorful artwork)
or a complete row (coherent scrolling bands). A restricted artistic palette can
outperform unconstrained pair selection for a particular scene. Both colors must
share the BRIGHT level; avoid identical RGB endpoints, including the two blacks.

Quantize coverage t to zero/one and diffuse the error with Sierra Lite weights:
right 1/2, next-row left 1/4, next-row same column 1/4. On reverse serpentine rows,
mirror the horizontal offsets. Do not silently substitute generic RGB error
diffusion: the demonstrated scalar coverage algorithm has different results.
Linear-light fitting is an alternative to compare, not a guaranteed improvement.

Pack bits MSB first. Attribute is `(bright << 6) | (paper << 3) | ink`, with FLASH
off. The screen offset is `((y & 192) << 5) + ((y & 7) << 8) + ((y & 56) << 2) + x/8`.
Use that offset independently in both 6144-byte planes. Declare explicitly if a
tool exports linear rows instead; these layouts are not interchangeable.

## Deblocking and deconfliction

First distinguish low native resolution from palette boundaries, texture crawl,
alpha fringes and incorrect bitmap/attribute alignment. Blurring cannot repair a
banking error or a wrong attribute-plane layout.

Independent palettes can abruptly alternate yellow, magenta and gray between
neighboring eight-pixel cells even when source luminance is smooth. A common
scanline pair removes those hue boundaries. Another option is to lock selected
palette families or apply spatial/temporal penalties to palette changes; validate
the actual result instead of claiming arbitrary-color scrolling.

Beast Horizons rev08 mapped the rock source's luminance and alpha onto a rose/white
coverage image, then applied Sierra Lite once. All eight phases became rigid
rotations of that bitmap with row-constant attributes. This removed palette blocks
and phase-dependent texture changes, but changed the rock hue. That palette and its
contrast curve are an example, not a universal choice for landscapes.

At fractional-byte scroll positions, source cells straddle destination cells.
Simply rotating bitmap bits while byte-rotating arbitrary attributes is wrong.
Use coherent row palettes, compatible cell palettes, or explicit phase conversion
with accepted color/texture tradeoffs. The bundled helper refuses fine phases in
cell-palette mode for this reason.

## Transparency and background creation

Retain alpha separately from RGB. A transparent pixel is not a black pixel and
must not force a black background or overwrite the background's attribute.
For a binary Z80 mask, document threshold and convention: the helper uses **1 to
preserve background**, 0 to replace it. Merge with
`(background & mask) | (sprite & ~mask)`.

For fixed scenes, compose soft edges against the actual background first. For
moving characters over changing scenery, choose an explicit edge/mask policy;
precompositing against a single color can create halos elsewhere. Fully transparent
cells retain both background bits and attributes. Partly covered cells still have
one palette pair for all eight pixels: masking alone cannot eliminate color clash.
Either accept local recoloring, coordinate sprite/background palettes, or quantize
the composite cell. Document the visual tradeoff.

If background pixels were never supplied, create them deliberately (procedural
gradient, layered artwork or an authored plate). Do not label black-fill or unknown
pixels as recovered scenery. Store source layers and their compositing order so
conversion and animation can be reproduced.
