#!/usr/bin/env python3
"""Expand a Fuse TS2068 DCK into a contiguous 64K physical ROM image."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from dck_format import CHUNK_SIZE, flat_image, parse_dck


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a sparse DCK to an eight-chunk physical ROM image."
    )
    parser.add_argument("dck", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fill", type=lambda value: int(value, 0), default=0xFF)
    args = parser.parse_args()

    dck = parse_dck(args.dck.read_bytes())
    if dck.bank_id != 0:
        raise SystemExit(f"expected DOCK bank 0, got {dck.bank_id}")
    image = flat_image(dck, args.fill)
    if len(image) != CHUNK_SIZE * 8:
        raise SystemExit(f"internal error: flat image is {len(image)} bytes")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image)
    digest = hashlib.sha256(image).hexdigest().upper()
    descriptors = " ".join(str(value) for value in dck.descriptors)
    print(
        f"wrote {args.output} ({len(image)} bytes; descriptors: {descriptors}; "
        f"SHA-256 {digest})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
