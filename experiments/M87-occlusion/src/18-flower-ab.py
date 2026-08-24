"""M87 step 18 -- the flower-bud A/B, measured rather than assumed.

`flower-bud-alone-cpl` (205 frames) and `flower-bud-with-background-fern-cpl`
(299) were captured as a with/without-background pair. Step 0 already measured
that they are NOT a controlled pair: different framing and pose, frame-0 green
means 3093 vs 2087, and photometric drift of +26% and +44% across the two
sweeps. So the "alone" stack is not ground truth for the "with background" one,
and no pixel-wise comparison between them is licensed.

What IS licensed, and is what this script does, is a comparison of the METRIC's
value on each: the isotonic-residual overshoot ISO is dimensionless, computed
per profile against that profile's own local far value, on each stack's own
boundary geometry. If the rim is caused by an occluding background, ISO should
be materially larger on the with-background stack than on the alone stack.

That is a weak test and it is reported as one. It cannot separate "background
present" from "different subject pose", which is precisely the caution the owner
recorded when delivering the pair.
"""

import json
import pathlib
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"

STACKS = {
    "alone": r"D:\personal\macro\flower-bud-alone-cpl",
    "with-fern": r"D:\personal\macro\flower-bud-with-background-fern-cpl",
}
BOX = (700, 1700, 900, 2100)
ISO = 100.0


def png(a, path, gamma=2.2):
    lo, hi = np.percentile(a, (0.5, 99.7))
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def main():
    res = {}
    for tag, path in STACKS.items():
        files = L.frames(pathlib.Path(path))
        n = len(files)
        h, w = BOX[1] - BOX[0], BOX[3] - BOX[2]
        best = np.full((h, w), -np.inf, np.float32)
        arg = np.zeros((h, w), np.int32)
        cube = np.empty((n, h, w), np.float32)
        for k, f in enumerate(files):
            _, g1, g2, _ = L.read_planes(f, BOX)
            lu = 0.5 * (np.maximum(g1 - L.BLACK, 0) + np.maximum(g2 - L.BLACK, 0))
            cube[k] = lu
            fld = L.regularised_field(lu, ISO)
            better = fld > best
            best[better] = fld[better]
            arg[better] = k
            if k % 60 == 0:
                print(f"  {tag} {k}/{n}", flush=True)
        sel = np.empty((h, w), np.float32)
        for k in range(n):
            m = arg == k
            if m.any():
                sel[m] = cube[k][m]

        mask, tau = L.foreground_mask(sel)
        roi = (30, h - 30, 30, w - 30)
        pts, nrm = M2.boundary_normals(mask, roi=roi)
        val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
        p, nv = pts[val], nrm[val]
        r = M2.score_iso(sel, p, nv, boot=500)
        iso_k = [M2.score_iso(cube[k], p, nv, boot=0)["ISO"] for k in range(0, n, 10)]
        print(f"\n{tag}: n={n}  tau={tau:.0f}  fg={mask.mean():.4f}  "
              f"profiles={r['n']}")
        print(f"  merge ISO = {r['ISO']:.5f} "
              f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]")
        print(f"  single frames ISO: max over sampled k = {max(iso_k):.5f}",
              flush=True)
        png(sel, OUT / f"18-{tag}-merge.png")
        res[tag] = {"n": n, "tau": float(tau), "fg": float(mask.mean()),
                    "ISO": r["ISO"], "ISO_ci": r["ISO_ci"], "n_prof": r["n"],
                    "frames_ISO_max": float(max(iso_k))}
        np.save(CACHE / f"18-{tag}-sel.npy", sel)
        np.save(CACHE / f"18-{tag}-mask.npy", mask)

    a, b = res["alone"]["ISO"], res["with-fern"]["ISO"]
    print(f"\nwith-fern / alone = {b / max(a, 1e-9):.2f}x")
    res["ratio"] = float(b / max(a, 1e-9))
    json.dump(res, open(DATA / "18-ab.json", "w"), indent=1)
    print("wrote data/18-ab.json")


if __name__ == "__main__":
    main()
