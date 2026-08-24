#!/usr/bin/env python3
"""Small, dependency-free helpers for Fuse TS2068 DCK images."""

from __future__ import annotations

from dataclasses import dataclass

CHUNK_SIZE = 0x2000
CHUNK_COUNT = 8
DOCK_BANK_ID = 0
ABSENT = 0
RAM_UNINITIALIZED = 1
ROM = 2
RAM_INITIALIZED = 3
VALID_DESCRIPTORS = {ABSENT, RAM_UNINITIALIZED, ROM, RAM_INITIALIZED}


@dataclass(frozen=True)
class DCK:
    bank_id: int
    descriptors: tuple[int, ...]
    chunks: dict[int, bytes]


def parse_dck(data: bytes) -> DCK:
    if len(data) < 9:
        raise ValueError("DCK is shorter than its 9-byte header")
    bank_id = data[0]
    descriptors = tuple(data[1:9])
    invalid = [(index, value) for index, value in enumerate(descriptors)
               if value not in VALID_DESCRIPTORS]
    if invalid:
        raise ValueError(f"invalid DCK descriptors: {invalid}")
    chunks: dict[int, bytes] = {}
    position = 9
    for index, descriptor in enumerate(descriptors):
        if descriptor in (ROM, RAM_INITIALIZED):
            end = position + CHUNK_SIZE
            if end > len(data):
                raise ValueError(f"DCK ends inside chunk {index}")
            chunks[index] = data[position:end]
            position = end
    if position != len(data):
        raise ValueError(f"DCK has {len(data) - position} trailing bytes")
    return DCK(bank_id, descriptors, chunks)


def build_dck(descriptors: list[int], chunks: dict[int, bytes], bank_id: int = 0) -> bytes:
    if len(descriptors) != CHUNK_COUNT:
        raise ValueError("exactly eight chunk descriptors are required")
    for index, descriptor in enumerate(descriptors):
        if descriptor not in VALID_DESCRIPTORS:
            raise ValueError(f"chunk {index}: invalid descriptor {descriptor}")
        needs_image = descriptor in (ROM, RAM_INITIALIZED)
        has_image = index in chunks
        if needs_image != has_image:
            raise ValueError(f"chunk {index}: descriptor/image mismatch")
        if has_image and len(chunks[index]) != CHUNK_SIZE:
            raise ValueError(f"chunk {index}: expected 8192 bytes, got {len(chunks[index])}")
    return bytes((bank_id, *descriptors)) + b"".join(
        chunks[index] for index, descriptor in enumerate(descriptors)
        if descriptor in (ROM, RAM_INITIALIZED)
    )


def flat_image(dck: DCK, fill: int = 0xFF) -> bytes:
    if not 0 <= fill <= 0xFF:
        raise ValueError("fill must be 0..255")
    blank = bytes((fill,)) * CHUNK_SIZE
    return b"".join(dck.chunks.get(index, blank) for index in range(CHUNK_COUNT))


def header_summary(dck: DCK) -> dict[str, object] | None:
    if 4 in dck.chunks:
        block = dck.chunks[4]
        if block[1] == 2 and block[0] in (1, 2):
            return {
                "kind": "BASIC AROS" if block[0] == 1 else "machine-code AROS",
                "entry": block[2] | block[3] << 8,
                "chunk_spec": block[4],
                "autostart": block[5],
                "ram_reserve": block[6] | block[7] << 8,
                "standard_lower_chunks_home": (block[4] & 0x0F) == 0x0F,
                "chunk3_startup_safe": bool(block[4] & 0x08),
            }
    if 0 in dck.chunks:
        block = dck.chunks[0]
        if block[1] == 1:
            return {
                "kind": "LROS",
                "entry": block[2] | block[3] << 8,
                "chunk_spec": block[4],
                "chunk3_startup_safe": bool(block[4] & 0x08),
            }
    return None
