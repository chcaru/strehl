#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


def ascii_out(text: str) -> None:
    print(text.encode("ascii", "replace").decode("ascii"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["file", "diff", "show"])
    parser.add_argument("path")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()
    if args.mode == "file":
        text = Path(args.path).read_text(encoding="utf-8")
    else:
        cmd = ["git", "--no-pager"]
        if args.mode == "diff":
            cmd += ["diff", "--", args.path]
        else:
            cmd += ["show", "HEAD:" + args.path]
        raw = subprocess.run(cmd, check=True, stdout=subprocess.PIPE).stdout
        text = raw.decode("utf-8")
    lines = text.splitlines()
    end = args.end if args.end is not None else len(lines)
    selected = []
    for n in range(args.start, min(end, len(lines)) + 1):
        selected.append(f"{n:5}: {lines[n - 1]}")
    ascii_out("\n".join(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())