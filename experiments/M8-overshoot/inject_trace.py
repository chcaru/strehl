"""Instrument a private source snapshot with the M8 value-only trace hook."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
from pathlib import Path


MAIN_ANCHOR = "mod merge_cmd;\n"
MAIN_REPLACEMENT = "mod merge_cmd;\nmod m8_trace;\n"
GATHER_ANCHOR = "            let inv = 1.0 / gain[ci];\n"
GATHER_REPLACEMENT = """            crate::m8_trace::trace_site(
                frame,
                dx,
                dy,
                geom,
                t_site,
                cx,
                cy,
                ci,
                gain[ci],
                resampler,
                plane,
                &scratch.dst,
            )?;
            let inv = 1.0 / gain[ci];
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def replace_once(path: Path, anchor: str, replacement: str) -> None:
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read().replace("\r\n", "\n")
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            f"{path}: full-line anchor occurred {count} times, required exactly once"
        )
    text = text.replace(anchor, replacement)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", type=Path)
    ap.add_argument("--hook", type=Path, required=True)
    ap.add_argument("--record", type=Path)
    args = ap.parse_args()

    cli = args.snapshot / "crates" / "strehl-cli" / "src"
    main_rs = cli / "main.rs"
    align_rs = cli / "align_cmd.rs"
    if not (main_rs.is_file() and align_rs.is_file()):
        raise FileNotFoundError(f"{args.snapshot}: not a Strehl source snapshot")
    hook_dst = cli / "m8_trace.rs"
    if hook_dst.exists():
        raise RuntimeError(f"{hook_dst}: refusing to overwrite an existing hook")

    before = {
        "main.rs": sha256(main_rs),
        "align_cmd.rs": sha256(align_rs),
        "hook_source": sha256(args.hook),
    }
    shutil.copyfile(args.hook, hook_dst)
    replace_once(main_rs, MAIN_ANCHOR, MAIN_REPLACEMENT)
    replace_once(align_rs, GATHER_ANCHOR, GATHER_REPLACEMENT)
    after = {
        "main.rs": sha256(main_rs),
        "align_cmd.rs": sha256(align_rs),
        "m8_trace.rs": sha256(hook_dst),
    }
    payload = {"snapshot": str(args.snapshot.resolve()), "before": before, "after": after}
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
