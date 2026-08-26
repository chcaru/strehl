"""What is the smallest difference this instrument can actually resolve?

The subject results cluster at roughly +/-0.45 px on every subject and every
statistic. A constant answer across six very different subjects is the
signature of an instrument floor, not of a subject property, and reporting it
as a result would be exactly the kind of number this project has had to retract
before.

Two things are measured here, on real tiles from the real renders:

  RESOLUTION   plant a known blur from 0.05 to 1.20 px and ask the same
               inversion blureq.py uses to recover it. Gaussian blur below
               about a third of a pixel barely changes a sampled image at all,
               so the inversion has a dead zone near zero and the first sigma
               it can report is not zero. That first sigma is the detection
               limit, and every subject number smaller than it is NOT A
               MEASUREMENT.

  NOISE NULL   plant NO blur and instead add white noise until the tile's sigma
               matches the argmax arm's measured noise. The arms really do
               differ in noise -- 1.06x to 2.68x across the corpus -- so
               whatever equivalent blur the inversion reports for noise alone
               is the part of every subject number that is not detail.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stats import STATS, noise_sigma  # noqa: E402
from blureq import invert  # noqa: E402

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS")
RENDERS = OUT / "renders"
RNG = np.random.default_rng(4242)
PLANTS = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.80, 1.20]


def signed(tm, ta, fn):
    vm, va = fn(tm), fn(ta)
    return invert(tm, va, fn) if va <= vm else -invert(ta, vm, fn)


def main():
    data = json.loads((OUT / "measure-subjects.json").read_text(encoding="utf8"))
    tiles = []
    sigrat = {}
    for rec in data:
        sigrat[rec["subject"]] = rec["sigma_ratio_argmax_over_merge"]
        img = tifffile.imread(str(RENDERS / rec["subject"] / "merge.tif"))
        g = img[:, :, 1].astype(np.float64)
        for t in rec["tiles"][:2]:
            x, y = t["merge_xy"]
            n = t["tile_px_merge"]
            tiles.append((rec["subject"], g[y:y + n, x:x + n]))

    print("RESOLUTION -- planted blur vs recovered equivalent blur (px)")
    print(f"  {'planted':>8}" + "".join(f"{k:>12}" for k in STATS))
    rec_rows = []
    for s in PLANTS:
        got = {k: [] for k in STATS}
        for _, t in tiles:
            tb = gaussian_filter(t, s)
            for k, fn in STATS.items():
                got[k].append(signed(t, tb, fn))
        rec_rows.append(dict(planted=s, **{k: float(np.median(v)) for k, v in got.items()}))
        print(f"  {s:>8.2f}" + "".join(f"{np.median(got[k]):>12.3f}" for k in STATS))

    print("\nNOISE NULL -- no blur at all, only the arms' real noise difference")
    print(f"  {'subject':<20}{'sigma ratio':>12}" + "".join(f"{k:>12}" for k in STATS))
    null_rows = []
    for subj, t in tiles:
        r = sigrat[subj]
        if not np.isfinite(r) or r <= 1.0:
            continue
        s0 = noise_sigma(t)
        add = float(np.sqrt(max((r * s0) ** 2 - s0 ** 2, 0.0)))
        tn = t + RNG.normal(0.0, add, t.shape)
        row = {k: signed(t, tn, fn) for k, fn in STATS.items()}
        null_rows.append(dict(subject=subj, sigma_ratio=r, **row))
        print(f"  {subj:<20}{r:>12.3f}" + "".join(f"{row[k]:>12.3f}" for k in STATS))

    (OUT / "limits.json").write_text(
        json.dumps(dict(resolution=rec_rows, noise_null=null_rows), indent=1),
        encoding="utf8")
    print(f"\nwrote {OUT / 'limits.json'}")


if __name__ == "__main__":
    main()
