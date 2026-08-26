"""Render 1:1 crops at EXACTLY the sites the verdict nominates.

crops.py ranks candidate sites by its own score at a deliberately low
nomination threshold, so the panels it produces are not identical to the hot
clusters analyse.py actually decides on.  For the visual judgement to be
evidence about the verdict, it has to look at the verdict's own sites.

Writes one solo 512x512 PNG per hot cluster, at 1:1, no resampling, plus the
same master's CONTROL site for comparison, into crops/verdict/.

USAGE
    python experiments/BUILD-GHOST/verdictcrops.py [--top N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crops import CROP, _write_png, to8, quiet_site   # noqa: E402

DATA = os.path.join(r"C:\dev\strehl-out\BUILD-GHOST", "data")
SHIP = r"C:\dev\strehl-out\SHIP-V1"
OUTDIR = os.path.join(r"C:\dev\strehl-out\BUILD-GHOST", "crops", "verdict")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=4,
                    help="sites per subject, ranked by excess over the per-K floor")
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    verdict = json.load(open(os.path.join(DATA, "verdict.json")))
    rows = [r for r in verdict["rows"] if r.get("n_hot_clusters")]
    print(f"rendering verdict-nominated sites for {len(rows)} subjects, "
          f"up to {args.top} each, 1:1")

    manifest, n_sites = [], 0
    for r in sorted(rows, key=lambda r: -(r.get("hot_excess") or 0)):
        name = r["subject"]
        p = os.path.join(SHIP, name + ".tiff")
        if not os.path.exists(p):
            print(f"  {name:38s} SKIP, no master")
            continue
        a = tifffile.imread(p)
        assert a.dtype == np.uint16, f"{name}: expected uint16, got {a.dtype}"
        h, w = a.shape[:2]

        for j, c in enumerate(r["hot"][:args.top], 1):
            cy, cx = c["peak_plane_yx"]
            y = int(np.clip(int(cy) * 2 - CROP // 2, 0, h - CROP))
            x = int(np.clip(int(cx) * 2 - CROP // 2, 0, w - CROP))
            fp = os.path.join(OUTDIR, f"{name}__V{j}.png")
            _write_png(fp, to8(a[y:y + CROP, x:x + CROP]))
            manifest.append({"subject": name, "panel": f"V{j}", "png": fp,
                             "master_y": y, "master_x": x,
                             "peak_sensor_px": c["peak_sensor_px"],
                             "k": c["k"], "i": c["i"],
                             "coherence": c["coherence"],
                             "excess": c["excess"]})
            n_sites += 1
        qy, qx = quiet_site(a)
        fp = os.path.join(OUTDIR, f"{name}__CONTROL.png")
        _write_png(fp, to8(a[qy:qy + CROP, qx:qx + CROP]))
        manifest.append({"subject": name, "panel": "CONTROL", "png": fp,
                         "master_y": qy, "master_x": qx})
        print(f"  {name:38s} {min(args.top, len(r['hot']))} sites "
              f"(top excess {r['hot'][0]['excess']:.2f}x floor) + control")
        del a

    json.dump(manifest, open(os.path.join(OUTDIR, "manifest.json"), "w"),
              indent=2, default=float)
    print(f"\nsubjects {len(rows)}   motion sites rendered {n_sites}   "
          f"controls {len(rows)}   files {len(manifest)}")
    print(f"wrote {OUTDIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
