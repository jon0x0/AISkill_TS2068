#!/usr/bin/env python3
"""Run a TS2068 DCK under an unattended Fuse debugger command program."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def default_fuse_path() -> Path:
    if sys.platform == "darwin":
        system_app = Path("/Applications/Fuse.app/Contents/MacOS/Fuse")
        user_app = Path.home() / "Applications/Fuse.app/Contents/MacOS/Fuse"
        return user_app if user_app.exists() and not system_app.exists() else system_app
    if sys.platform == "win32":
        return Path(r"C:\Program Files (x86)\Fuse\fuse.exe")
    return Path("fuse")


def fuse_executable(path: Path) -> Path:
    """Accept either the macOS Fuse.app bundle or its inner executable."""
    if sys.platform == "darwin" and path.suffix.lower() == ".app":
        return path / "Contents/MacOS/Fuse"
    return path


DEFAULT_FUSE = default_fuse_path()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dck", type=Path)
    parser.add_argument("commands", type=Path)
    parser.add_argument(
        "--fuse", type=Path, default=DEFAULT_FUSE,
        help="Fuse executable, or Fuse.app on macOS",
    )
    parser.add_argument("--machine", default="ts2068")
    parser.add_argument("--speed", type=int, default=5000)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    command_text = args.commands.read_text(encoding="utf-8")
    fuse = fuse_executable(args.fuse)
    launch = [str(fuse), "--machine", args.machine, "--speed", str(args.speed),
              "--no-sound", "--no-loading-sound", "--debugger-command", command_text,
              "--dock", str(args.dck.resolve())]
    result = subprocess.run(launch, check=False, capture_output=True, text=True,
                            timeout=args.timeout)
    combined = result.stdout + result.stderr
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(combined, encoding="utf-8")
    else:
        print(combined, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
