#!/usr/bin/env python3
"""Build a Fuse DCK and optional flat 64K image from TS2068 chunks."""

from __future__ import annotations

import argparse
from pathlib import Path

from dck_format import (ABSENT, CHUNK_COUNT, CHUNK_SIZE, RAM_INITIALIZED,
                        RAM_UNINITIALIZED, ROM, build_dck, flat_image, parse_dck)


def assignment(value: str) -> tuple[int, Path]:
    try:
        number, path = value.split("=", 1)
        index = int(number, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("use CHUNK=FILE") from error
    if not 0 <= index < CHUNK_COUNT:
        raise argparse.ArgumentTypeError("chunk must be 0..7")
    return index, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--raw64", type=Path,
                        help="flat 65536-byte input; package all chunks as ROM")
    parser.add_argument("--rom", action="append", type=assignment, default=[],
                        help="CHUNK=FILE, where FILE is exactly 8192 bytes")
    parser.add_argument("--ram", action="append", type=lambda value: int(value, 0), default=[],
                        help="uninitialized DCK RAM chunk number")
    parser.add_argument("--ram-image", action="append", type=assignment, default=[],
                        help="initialized DCK RAM as CHUNK=FILE")
    parser.add_argument("--physical-bin", type=Path)
    parser.add_argument("--fill", type=lambda value: int(value, 0), default=0xFF)
    args = parser.parse_args()

    if args.raw64 and (args.rom or args.ram or args.ram_image):
        parser.error("--raw64 cannot be combined with per-chunk options")
    descriptors = [ABSENT] * CHUNK_COUNT
    chunks: dict[int, bytes] = {}
    if args.raw64:
        raw = args.raw64.read_bytes()
        if len(raw) != CHUNK_COUNT * CHUNK_SIZE:
            raise SystemExit(f"--raw64 must be 65536 bytes, got {len(raw)}")
        descriptors = [ROM] * CHUNK_COUNT
        chunks = {index: raw[index * CHUNK_SIZE:(index + 1) * CHUNK_SIZE]
                  for index in range(CHUNK_COUNT)}
    else:
        claimed: set[int] = set()
        for index, path in args.rom:
            if index in claimed:
                raise SystemExit(f"chunk {index} specified more than once")
            claimed.add(index)
            descriptors[index] = ROM
            chunks[index] = path.read_bytes()
        for index in args.ram:
            if not 0 <= index < CHUNK_COUNT or index in claimed:
                raise SystemExit(f"invalid or duplicate RAM chunk {index}")
            claimed.add(index)
            descriptors[index] = RAM_UNINITIALIZED
        for index, path in args.ram_image:
            if index in claimed:
                raise SystemExit(f"chunk {index} specified more than once")
            claimed.add(index)
            descriptors[index] = RAM_INITIALIZED
            chunks[index] = path.read_bytes()

    image = build_dck(descriptors, chunks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image)
    checked = parse_dck(image)
    print(f"wrote {args.output} ({len(image)} bytes; descriptors {descriptors})")
    if args.physical_bin:
        args.physical_bin.parent.mkdir(parents=True, exist_ok=True)
        physical = flat_image(checked, args.fill)
        args.physical_bin.write_bytes(physical)
        print(f"wrote {args.physical_bin} ({len(physical)} bytes; fill ${args.fill:02X})")
        if any(value in (RAM_UNINITIALIZED, RAM_INITIALIZED) for value in descriptors):
            print("warning: flat bytes do not reproduce writable DCK RAM hardware")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
