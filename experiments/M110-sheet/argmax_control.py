#!/usr/bin/env python
"""Positive control: read the highlight statistic on the path where the defect
was actually measured.

M109's magenta was measured and fixed on `crates/strehl-cli/src/stack.rs` --
`Command::ArgmaxBaseline`, which the CLI help itself calls "THE NAIVE BASELINE,
NOT THE DEFAULT". It was then ported to `merge_cmd.rs` (`Command::Stack`, the
default path) at `e9ad010`, where it was never measured.

My instrument reads "neutral" on the default path. That has two possible
causes and they are not the same:

  (a) there is no defect there, or
  (b) the instrument cannot see the defect on that path.

A synthetic plant distinguishes gain from noise, but it cannot distinguish
these -- it proves the statistic responds to a number I injected, not that it
responds to the real mechanism. Rendering the SAME subject through
argmax-baseline does: it is the same scene, the same raws and the same
statistic, on the code path where the defect is known to have existed.

`3e58676` (the argmax fix) is also in HEAD, so the expected reading is neutral
there too. A MAGENTA reading here would mean that fix did not take and is a
live defect. A neutral reading on both paths, with the per-pixel path and the
~55-frame-averaged path agreeing, says the two paths now agree about
highlights.

Writes to C:\\dev\\strehl-out\\M110-sheet\\<subject>\\argmax.tif -- its own
explicit path, because StackIdentity covers neither reference nor resampler
(fact 1446) and this command shares a stack directory with the default arm.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheet import (BINARY, CROP, OUT_ROOT, highlight_stats,  # noqa: E402
                   load_raw, load_subjects, neutrality, provenance,
                   run, sha256_file)

HERE = Path(__file__).resolve().parent


def main() -> int:
    only = sys.argv[1:] or None
    cfg = load_subjects()
    out = {"provenance": provenance(), "subjects": {}}
    rows = []
    for sub in cfg["subjects"]:
        if only and sub["name"] not in only:
            continue
        clip = next((c for c in sub.get("crops", []) if c["role"] == "clipped"), None)
        if not clip:
            continue
        tif = OUT_ROOT / sub["name"] / "argmax.tif"
        tif.parent.mkdir(parents=True, exist_ok=True)
        expo = ([sub["exposure"]] if sub.get("exposure") else ["--auto-exposure"])
        print(f"  {sub['name']:<20} argmax-baseline ...", end="", flush=True)
        r = run([str(BINARY), "argmax-baseline", sub["dir"], "--srgb", *expo,
                 "--out", str(tif)])
        if r["exit"] != 0:
            print(f" FAILED exit {r['exit']}")
            print("   " + "\n   ".join(r["stderr_tail"][-6:]))
            out["subjects"][sub["name"]] = {"ok": False, "exit": r["exit"],
                                            "stderr_tail": r["stderr_tail"][-6:]}
            continue
        raw = load_raw(tif)
        win = raw[clip["y"]:clip["y"] + CROP, clip["x"]:clip["x"] + CROP]
        s = highlight_stats(win)
        _, old = neutrality(win)
        del raw
        rec = {k: s.get(k) for k in
               ("region_frac", "region_n", "off", "c_r", "c_g", "c_b", "asym",
                "head_magenta", "head_green", "core_n", "core_off")}
        rec.update({"ok": True, "one_sided_off": old, "seconds": r["seconds"],
                    "tif_sha256": sha256_file(tif),
                    "binary_sha256": sha256_file(BINARY),
                    "tile": [clip["x"], clip["y"]]})
        out["subjects"][sub["name"]] = rec
        rows.append((sub["name"], s, old))
        print(f" ok {r['seconds']}s")

    p = HERE / "argmax_control.json"
    p.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    hdr = (f"\n{'subject':<20} {'blown%':>7} {'off':>9} {'one-sided':>10} "
           f"{'c_r':>6} {'c_g':>6} {'c_b':>6}   verdict")
    print(hdr)
    print("-" * (len(hdr) - 1))
    for name, s, old in rows:
        off = s["off"]
        v = ("MAGENTA -- 3e58676 did not take" if off < -0.02 else
             "GREEN OVERSHOOT" if off > 0.02 else "neutral")
        print(f"{name:<20} {s['region_frac'] * 100:>6.3f}% {off:>+9.4f} "
              f"{(f'{old:+.4f}' if old is not None else 'n/a'):>10} "
              f"{s['c_r']:>6.3f} {s['c_g']:>6.3f} {s['c_b']:>6.3f}   {v}")
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
