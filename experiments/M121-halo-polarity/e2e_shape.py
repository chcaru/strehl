"""E2e -- does the tweezers rim END, or does it just run on?

E2d reported a DARK rim on the bright-object class at +0.1326, which is
P-POLARITY's killer prediction firing.  Before believing it, two things have
to be true and neither has been checked:

  1.  A RIM ENDS.  bee-3's dark-object rim reads +0.156 / +0.169 / -0.002 /
      -0.042 / -0.031 across the 1.5-6, 6-12, 12-18, 18-24, 24-30 px bands: it
      is over by 12 px and slightly negative after.  A slow background
      gradient -- bokeh falloff, vignetting, a big out-of-focus shape -- would
      instead stay positive all the way out, and would be mis-normalised by a
      "plateau" at 30-45 px that is not actually flat.  E2d's tweezers rim has
      w50 = 22.75 px and cutoff 28.25 px, which is the edge of the measurement
      range.  That is the signature of the second thing, not the first.

  2.  IT MUST BEAT ITS OWN NO-MERGE CONTROL BY MORE THAN A LITTLE.  On bee-3
      the merged rim is 28x the single-frame N1 floor.  On tweezers E2d got
      2.8x, on n=13.

This script prints the band tables for both subjects side by side and writes
crops centred on the strongest tweezers edges so the thing can be LOOKED AT
(discipline 824), which is what started this milestone.

Run:  python experiments/M121-halo-polarity/e2e_shape.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from e2_polarity import (  # noqa: E402
    FLAT_TOL, GRAD_PCT, ISO, MAX_EDGES, MIN_AMPLITUDE, commissioned_max_rise,
    focus_field, make_classifier, polarity_table,
)
from e2d_tweezers import SAT_DEFAULT, index_classifier, load_idx  # noqa: E402
from halo_lib import BANDS, band_mean  # noqa: E402
from m121_io import FRAMES, OUT, arm_path, load_u16, luma  # noqa: E402
from runner import scan  # noqa: E402

TW = pathlib.Path(r"C:\dev\strehl-out\M121\tweezers")
LOOK = OUT / "look"


def bands_of(r, side, want, label, res):
    s = r.get(side)
    if s is None:
        return
    sel = np.asarray(s["obj"]) == want
    if sel.sum() < 8:
        print(f"  {label:34s} n={int(sel.sum())} -- too few")
        return
    dist = r["dist"]
    med = np.median(s["stack"][sel], axis=0)
    vals = [band_mean(dist, med, a, b) for a, b in BANDS]
    res[label] = {"n": int(sel.sum()),
                  "bands": {f"{a:g}-{b:g}": v for (a, b), v in zip(BANDS, vals)}}
    txt = "  ".join(f"{a:g}-{b:g}:{v:+.4f}" for (a, b), v in zip(BANDS, vals))
    print(f"  {label:34s} n={int(sel.sum()):4d}  {txt}")
    # does it end?  positive in the near bands and non-positive by 18-24 px
    ends = vals[1] > 0 and vals[3] <= 0.25 * max(vals[0], vals[1])
    res[label]["ends_within_24px"] = bool(ends)
    print(f"  {'':34s} -> {'ENDS like a rim' if ends else 'DOES NOT END -- runs on like a gradient'}")


def save_crop(img, y, x, name, half=90):
    h, w = img.shape
    y0, x0 = max(int(y) - half, 0), max(int(x) - half, 0)
    y1, x1 = min(int(y) + half, h), min(int(x) + half, w)
    c = img[y0:y1, x0:x1].astype(np.float64)
    p1, p99 = np.percentile(c, 1), np.percentile(c, 99.5)
    c = np.clip((c - p1) / max(p99 - p1, 1e-9), 0, 1) ** (1 / 2.2)
    Image.fromarray((c * 255).astype(np.uint8)).resize(
        ((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST).save(LOOK / name)


def main():
    LOOK.mkdir(parents=True, exist_ok=True)
    max_rise = commissioned_max_rise()
    res = {}

    print("=== band tables: does the rim END? ===")
    print("    bands are 1.5-6, 6-12, 12-18, 18-24, 24-30 px from the edge\n")

    bee = luma(load_u16(arm_path("armM4-gate4-binlin")))
    frames = {n: luma(load_u16(arm_path(n))) for n in FRAMES}
    fmax = np.max(np.stack([focus_field(f) for f in frames.values()]), axis=0)
    rb = scan(bee, label="bee", grad_percentile=GRAD_PCT, max_edges=MAX_EDGES,
              isolation_frac=ISO, flat_tol=FLAT_TOL, classify=make_classifier(fmax),
              max_rise=max_rise, min_amplitude=MIN_AMPLITUDE, verbose=False)
    bands_of(rb, "bright", -1, "bee-3 dark-obj/bright-surr", res)

    tw = luma(load_u16(TW / "tweezers-gate4.tif"))
    t1 = luma(load_u16(TW / "tweezers-1f.tif"))
    tc = index_classifier(load_idx(TW / "index.tif"), True)
    rt = scan(tw, label="tw", grad_percentile=GRAD_PCT, max_edges=MAX_EDGES,
              isolation_frac=ISO, flat_tol=FLAT_TOL, classify=tc, max_rise=max_rise,
              min_amplitude=MIN_AMPLITUDE, sat_level=SAT_DEFAULT,
              collect_edges=True, verbose=False)
    bands_of(rt, "dark", +1, "tweezers bright-obj/dark-surr", res)

    r1 = scan(t1, label="tw1f", grad_percentile=GRAD_PCT, max_edges=MAX_EDGES,
              isolation_frac=ISO, flat_tol=FLAT_TOL, classify=tc, max_rise=max_rise,
              min_amplitude=MIN_AMPLITUDE, sat_level=SAT_DEFAULT, verbose=False)
    bands_of(r1, "dark", +1, "tweezers N1 single frame", res)

    print("\n=== crops to LOOK AT (discipline 824) ===")
    s = rt["dark"]
    sel = np.asarray(s["obj"]) == +1
    dist = rt["dist"]
    m = (dist >= 6.0) & (dist <= 18.0)
    v = s["stack"][sel][:, m].mean(axis=1)
    ys = np.asarray(s["lo"])[sel] * 0 + 0     # placeholder; use kept edges below
    order = np.argsort(-v)[:4]
    ke = rt["kept_edges"]
    for j, k in enumerate(order):
        if k < ke.shape[0]:
            y, x = ke[k, 0], ke[k, 1]
            save_crop(tw, y, x, f"tweezers-merged-{j}.png")
            save_crop(t1, y, x, f"tweezers-1frame-{j}.png")
            print(f"  edge {j}: y={y:.0f} x={x:.0f} rim={v[k]:+.4f} "
                  f"-> tweezers-merged-{j}.png / tweezers-1frame-{j}.png")

    (OUT / "e2e-shape.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT / 'e2e-shape.json'}  and crops in {LOOK}")


if __name__ == "__main__":
    main()
