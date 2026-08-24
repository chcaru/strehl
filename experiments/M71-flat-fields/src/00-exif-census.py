"""M71 step 00 -- EXIF census of the delivered flat-field set.

Task zero, part A: recover the structure of the capture from metadata ALONE,
before any pixel is read. Nothing here may look at signal level; the signal
cross-check is step 01 and it is only a cross-check if it is independent.

Outputs `data/00-census.json` with, per directory:
  * the exposure groups EXIF actually reports (the owner remembered 8, EXIF
    says 9 -- rule: trust EXIF and say so),
  * the within-group capture-time ordering and the gaps between frames,
  * the proposed CPL split: the owner shot CPL-on first, so within each
    shutter-speed group the earlier half is CPL and the later half is not.

`AGENTS.md` rule 8: every claim needs a command that was run.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CSV_PATH = HERE / "data" / "exif-all.csv"
OUT = HERE / "data" / "00-census.json"
DIRS = ("flat-fields", "subject-focus-sweep-with-cpl", "subject-focus-sweep-no-cpl")


def parse_dt(s: str) -> datetime:
    # SubSecDateTimeOriginal: '2026:08:23 16:41:30.106-07:00'
    date, rest = s.split(" ", 1)
    y, mo, d = date.split(":")
    if rest.endswith(("-07:00", "+00:00")) or rest[-6] in "+-":
        rest = rest[:-6]
    if "." in rest:
        hms, frac = rest.split(".")
    else:
        hms, frac = rest, "0"
    h, mi, se = hms.split(":")
    micro = int(round(float("0." + frac) * 1e6))
    return datetime(int(y), int(mo), int(d), int(h), int(mi), int(se), micro)


def exp_seconds(s: str) -> float:
    return float(Fraction(s)) if "/" in s else float(s)


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    # discipline 388: assert a non-zero file count before doing arithmetic
    assert len(rows) == 484, f"expected 484 frames, read {len(rows)}"

    for r in rows:
        r["_dt"] = parse_dt(r["SubSecDateTimeOriginal"])
        r["_exp"] = exp_seconds(r["ExposureTime"])
        r["_dir"] = Path(r["Directory"]).name

    # Invariants that the whole milestone assumes. Assert, do not hope.
    const = {
        "Model": {r["Model"] for r in rows},
        "ISO": {r["ISO"] for r in rows},
        "FNumber": {r["FNumber"] for r in rows},
        "FocalLength": {r["FocalLength"] for r in rows},
        "LensModel": {r["LensModel"] for r in rows},
        "ImageWidth": {r["ImageWidth"] for r in rows},
        "ImageHeight": {r["ImageHeight"] for r in rows},
        "FocusMode": {r["FocusMode"] for r in rows},
    }
    for k, v in const.items():
        assert len(v) == 1, f"{k} is not constant across the set: {sorted(v)}"

    out: dict = {
        "n_frames": len(rows),
        "constant_exif": {k: sorted(v)[0] for k, v in const.items()},
        "dirs": {},
    }

    for dname in ("flat-fields", "subject-focus-sweep-with-cpl", "subject-focus-sweep-no-cpl"):
        sub = sorted([r for r in rows if r["_dir"] == dname], key=lambda r: r["_dt"])
        span = sub[-1]["_dt"] - sub[0]["_dt"]
        groups = defaultdict(list)
        for r in sub:
            groups[r["ExposureTime"]].append(r)
        g_out = {}
        for et, frames in groups.items():
            frames.sort(key=lambda r: r["_dt"])
            gaps = [
                (frames[i + 1]["_dt"] - frames[i]["_dt"]).total_seconds()
                for i in range(len(frames) - 1)
            ]
            # The largest interior gap is the candidate CPL changeover.
            big_i = max(range(len(gaps)), key=lambda i: gaps[i]) if gaps else None
            g_out[et] = {
                "exposure_s": frames[0]["_exp"],
                "n": len(frames),
                "first": frames[0]["FileName"],
                "last": frames[-1]["FileName"],
                "t0": frames[0]["_dt"].isoformat(),
                "t1": frames[-1]["_dt"].isoformat(),
                "span_s": (frames[-1]["_dt"] - frames[0]["_dt"]).total_seconds(),
                "median_gap_s": sorted(gaps)[len(gaps) // 2] if gaps else None,
                "max_gap_s": max(gaps) if gaps else None,
                "max_gap_after_index": big_i,
                "files": [r["FileName"] for r in frames],
                "shuttercount": [int(r["ShutterCount"]) for r in frames],
                "brightnessvalue": [float(r["BrightnessValue"]) for r in frames],
                "focusposition2": sorted({r["FocusPosition2"] for r in frames}),
            }
        out["dirs"][dname] = {
            "n": len(sub),
            "t0": sub[0]["_dt"].isoformat(),
            "t1": sub[-1]["_dt"].isoformat(),
            "span_s": span.total_seconds(),
            "n_exposure_groups": len(groups),
            "groups": g_out,
            "shuttercount_min": min(int(r["ShutterCount"]) for r in sub),
            "shuttercount_max": max(int(r["ShutterCount"]) for r in sub),
        }

    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    # ---- human-readable summary -------------------------------------------
    print(f"{len(rows)} frames; constant EXIF:")
    for k, v in out["constant_exif"].items():
        print(f"   {k:16s} {v}")
    for dname, d in out["dirs"].items():
        print(f"\n=== {dname}: n={d['n']} span={d['span_s']:.1f}s "
              f"groups={d['n_exposure_groups']} "
              f"shuttercount {d['shuttercount_min']}..{d['shuttercount_max']}")
        for et, g in sorted(d["groups"].items(), key=lambda kv: kv[1]["exposure_s"]):
            print(f"  {et:>7s} ({g['exposure_s']:.4f}s) n={g['n']:3d} "
                  f"{g['t0'][11:]}..{g['t1'][11:]} span={g['span_s']:6.1f}s "
                  f"medgap={g['median_gap_s']} maxgap={g['max_gap_s']} "
                  f"after#{g['max_gap_after_index']} fp2={g['focusposition2']}")

    # ShutterCount is a MECHANICAL actuation count, so it is only a
    # missing-frame check for directories that used the mechanical shutter.
    # Report it per directory rather than globally: the 360 flats all carry a
    # single value (no mechanical actuation -- electronic shutter), so a
    # global "non-unit steps" count is uninformative there and reads as an
    # error when it is not one.
    all_sorted = sorted(rows, key=lambda r: r["_dt"])
    print("\nShutterCount per directory (mechanical actuations):")
    for d in DIRS:
        sub = [r for r in all_sorted if r["_dir"] == d]
        sc = [int(r["ShutterCount"]) for r in sub]
        distinct = len(set(sc))
        if distinct == 1:
            print(f"  {d:32s} n={len(sc):3d} constant at {sc[0]} "
                  f"-> electronic shutter, no contiguity check possible")
        else:
            breaks = [i for i in range(len(sc) - 1) if sc[i + 1] != sc[i] + 1]
            print(f"  {d:32s} n={len(sc):3d} {min(sc)}..{max(sc)} "
                  f"distinct={distinct} non-unit-steps={len(breaks)} "
                  f"-> {'contiguous, no frames missing' if not breaks else 'GAPS'}")


if __name__ == "__main__":
    main()
