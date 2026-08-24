#!/usr/bin/env python3
"""Inspect and validate a Fuse TS2068 DCK image."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from dck_format import CHUNK_SIZE, flat_image, header_summary, parse_dck


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dck", type=Path)
    parser.add_argument("--flat-output", type=Path)
    parser.add_argument("--fill", type=lambda value: int(value, 0), default=0xFF)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    raw = args.dck.read_bytes()
    dck = parse_dck(raw)
    report: dict[str, object] = {
        "path": str(args.dck.resolve()),
        "bytes": len(raw),
        "sha256": sha256(raw),
        "bank_id": dck.bank_id,
        "descriptors": list(dck.descriptors),
        "chunks": [
            {"chunk": index, "address": f"${index * CHUNK_SIZE:04X}",
             "descriptor": dck.descriptors[index], "sha256": sha256(data)}
            for index, data in sorted(dck.chunks.items())
        ],
        "cartridge_header": header_summary(dck),
    }
    print(json.dumps(report, indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.flat_output:
        flat = flat_image(dck, args.fill)
        args.flat_output.parent.mkdir(parents=True, exist_ok=True)
        args.flat_output.write_bytes(flat)
        print(f"wrote flat image {args.flat_output} ({len(flat)} bytes, SHA-256 {sha256(flat)})")
    header = report["cartridge_header"]
    if isinstance(header, dict) and header.get("chunk3_startup_safe") is False:
        raise SystemExit("cartridge chunk specification does not keep chunk 3 HOME at startup")
    if isinstance(header, dict) and header.get("standard_lower_chunks_home") is False:
        print("warning: AROS uses an advanced nonstandard startup mapping for chunks 0-2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
