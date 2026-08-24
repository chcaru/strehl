#!/usr/bin/env python
"""Snapshot the two-sided highlight readout for every subject's default arm.

Run once BEFORE re-rendering and once AFTER, then diff. Records the render's
sha256 and the binary that made it alongside the statistic, because after P10
a number without a binary behind it cannot be compared to anything.

Usage:  python highlight_snapshot.py before|after
        python highlight_snapshot.py diff
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheet import (CROP, OUT_ROOT, highlight_stats, load_raw,  # noqa: E402
                   load_subjects, neutrality, provenance)

HERE = Path(__file__).resolve().parent
KEYS = ("region_frac", "region_n", "off", "c_r", "c_g", "c_b", "asym",
        "head_magenta", "head_green", "core_n", "core_off")


def snap() -> dict:
    cfg = load_subjects()
    mp = OUT_ROOT / "manifest.json"
    man = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    out = {"provenance": provenance(), "subjects": {}}
    for sub in cfg["subjects"]:
        tif = OUT_ROOT / sub["name"] / "default.tif"
        clip = next((c for c in sub.get("crops", []) if c["role"] == "clipped"), None)
        if not tif.exists() or not clip:
            continue
        raw = load_raw(tif)
        win = raw[clip["y"]:clip["y"] + CROP, clip["x"]:clip["x"] + CROP]
        s = highlight_stats(win)
        old_frac, old_off = neutrality(win)
        del raw
        me = man.get("subjects", {}).get(sub["name"], {})
        rec = {k: s.get(k) for k in KEYS}
        rec["one_sided_off"] = old_off
        rec["tif_sha256"] = hashlib.sha256(tif.read_bytes()).hexdigest()
        rec["rendered_by"] = (me.get("arms", {}).get("default", {}) or {}).get("binary_sha256")
        rec["rendered_head"] = (me.get("provenance") or {}).get("git_head")
        rec["tile"] = [clip["x"], clip["y"]]
        out["subjects"][sub["name"]] = rec
    return out


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("before", "after", "diff"):
        sys.exit(__doc__)
    mode = sys.argv[1]
    if mode != "diff":
        p = HERE / f"highlight_{mode}.json"
        p.write_text(json.dumps(snap(), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {p}")
        return 0

    a = json.loads((HERE / "highlight_before.json").read_text(encoding="utf-8"))
    b = json.loads((HERE / "highlight_after.json").read_text(encoding="utf-8"))
    print(f"before HEAD {a['provenance']['git_head'][:12]}   "
          f"after HEAD {b['provenance']['git_head'][:12]}\n")
    hdr = (f"{'subject':<20} {'off before':>11} {'off after':>11} {'delta':>10} "
           f"{'bytes':>9}  binary before -> after")
    print(hdr)
    print("-" * len(hdr))
    for k, av in a["subjects"].items():
        bv = b["subjects"].get(k)
        if not bv:
            continue
        d = (bv["off"] - av["off"]) if (av["off"] is not None
                                        and bv["off"] is not None) else None
        same = av["tif_sha256"] == bv["tif_sha256"]
        print(f"{k:<20} {av['off']:>+11.5f} {bv['off']:>+11.5f} "
              f"{(f'{d:+.5f}' if d is not None else 'n/a'):>10} "
              f"{'SAME' if same else 'DIFFER':>9}  "
              f"{(av['rendered_by'] or '?')[:8]} -> {(bv['rendered_by'] or '?')[:8]}")
    print("\nA zero delta with DIFFERING bytes means the render changed elsewhere "
          "but not\nat the highlights. SAME bytes means nothing changed at all.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
