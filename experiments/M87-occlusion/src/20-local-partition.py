"""M87 step 20 -- F1 fails to generalise with a GLOBAL k_F.  Does a LOCAL one fix it?

Step 19 measured the winning arm on a second scene with the parameters chosen on
the bee and no refitting, which is the only honest way to ask whether a remedy
generalises.  It does not:

    bee   ROI_LEG,   F1 global k_F=145 :  -63.4 % (d=40),  -90.4 % (d=80)
    flower with fern, F1 global k_F= 41 :   +1.2 % (d=40),  -16.9 % (d=80)

The diagnosis is visible in the two k_F values.  The bee ROI's mask is one leg
and a body flank at essentially one depth, so a single modal elected frame
describes the whole occluder.  The flower crop's mask holds several buds at very
different depths; their modal elected frame, 41 of 299, describes only the
nearest one, and the forbidden band |k-41| < 40 sits at the start of the sweep
where the far buds are nowhere near focus.  A global k_F is simply the wrong
object for a foreground that spans depth -- the same defect that sank the global
form of the two-layer unmixing in step 13 and that a per-pixel k_F partly
repaired in step 17.

Test: replace the scalar k_F with a per-pixel map -- each treated background
pixel takes the elected frame of its NEAREST foreground pixel -- and forbid
|k - k_F(x)| < DELTA pixel-wise.  If the flower reduction moves to the bee's,
the remedy generalises once it is made local, and the Rust recipe must carry the
map.  If it does not, F1 is a bee-specific tuning and must be reported as one.
"""

import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
SHIP = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")

FLOWER = r"D:\personal\macro\flower-bud-with-background-fern-cpl"
FBOX = (700, 1700, 900, 2100)
FCROP = (120, 820, 40, 940)
BEE_MARGIN = 22
BEE_INNER = (BEE_MARGIN, BEE_MARGIN + 700, BEE_MARGIN, BEE_MARGIN + 1100)
YOKE = 40
DELTAS = (40, 80)
KF_MEDIAN = 15


def kf_map(mask, argbest):
    """Elected frame of the nearest foreground pixel, for every pixel."""
    inside = ndi.median_filter(argbest.astype(np.float32), size=KF_MEDIAN)
    _, (iy, ix) = ndi.distance_transform_edt(~mask, return_indices=True)
    return inside[iy, ix]


def partition(field, cube, treat, kf, delta, per_pixel):
    n, h, w = field.shape
    best = np.full((h, w), -np.inf, np.float32)
    arg = np.zeros((h, w), np.int32)
    for k in range(n):
        fld = np.asarray(field[k], np.float32)
        better = fld > best
        forb = (np.abs(kf - k) < delta) if per_pixel else (abs(k - kf) < delta)
        if per_pixel:
            better &= ~(treat & forb)
        elif forb:
            better &= ~treat
        best[better] = fld[better]
        arg[better] = k
    sel = np.empty((h, w), np.float32)
    for k in range(n):
        m = arg == k
        if m.any():
            sel[m] = np.asarray(cube[k], np.float32)[m]
    return sel, arg


def png(a, path, lo, span, gamma=2.2):
    v = np.clip((a - lo) / span, 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def run(tag, cube, field, mask, sel0, argbest, inner_roi, treat, res):
    pts, nrm = M2.boundary_normals(mask, roi=inner_roi)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    base = M2.score_iso(sel0, p, nv, boot=500)
    kf_glob = int(np.bincount(argbest[mask]).argmax())
    kf = kf_map(mask, argbest)
    spread = float(np.percentile(argbest[mask], 90) - np.percentile(argbest[mask], 10))
    print(f"\n[{tag}] F0 ISO={base['ISO']:.5f} "
          f"CI[{base['ISO_ci'][0]:.5f},{base['ISO_ci'][1]:.5f}]  n={base['n']}")
    print(f"[{tag}] global k_F={kf_glob}  subject k spread p10-p90 = {spread:.0f} frames",
          flush=True)
    res[tag] = {"F0_ISO": base["ISO"], "F0_ci": base["ISO_ci"], "n_prof": base["n"],
                "kF_global": kf_glob, "kF_spread_p10_p90": spread}
    out = {}
    for per_pixel in (False, True):
        for D in DELTAS:
            sel, _ = partition(field, cube, treat,
                               kf if per_pixel else kf_glob, D, per_pixel)
            r = M2.score_iso(sel, p, nv, boot=500)
            d = 100 * (1 - r["ISO"] / base["ISO"])
            name = f"{'local' if per_pixel else 'global'}-d{D}"
            print(f"[{tag}] F1 {name:<10} ISO={r['ISO']:.5f} "
                  f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]  ({d:+.1f}%)",
                  flush=True)
            res[tag][name] = {"ISO": r["ISO"], "ISO_ci": r["ISO_ci"],
                              "delta_pct": float(d)}
            out[name] = sel
    return out


def main():
    res = {}

    # ---- flower ----------------------------------------------------------
    files = L.frames(pathlib.Path(FLOWER))
    n = len(files)
    h, w = FBOX[1] - FBOX[0], FBOX[3] - FBOX[2]
    cube = np.empty((n, h, w), np.float32)
    field = np.empty((n, h, w), np.float32)
    for k, f in enumerate(files):
        _, g1, g2, _ = L.read_planes(f, FBOX)
        lu = 0.5 * (np.maximum(g1 - L.BLACK, 0) + np.maximum(g2 - L.BLACK, 0))
        cube[k] = lu
        field[k] = L.regularised_field(lu, 100.0)
        if k % 100 == 0:
            print(f"  decode {k}/{n}", flush=True)
    argbest = np.argmax(field, axis=0).astype(np.int32)
    sel0 = np.take_along_axis(cube, argbest[None], 0)[0]
    mask, _ = L.foreground_mask(sel0)
    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[30:h - 30, 30:w - 30] = True
    treat = inner & (~mask) & (dist <= YOKE)
    outs = run("flower", cube, field, mask, sel0, argbest,
               (30, h - 30, 30, w - 30), treat, res)
    ref = sel0[FCROP[0]:FCROP[1], FCROP[2]:FCROP[3]]
    lo = float(np.percentile(ref, 0.5))
    span = float(max(np.percentile(ref, 99.7) - lo, 1e-9))
    for name, sel in outs.items():
        if name.startswith("local"):
            png(sel[FCROP[0]:FCROP[1], FCROP[2]:FCROP[3]],
                SHIP / f"08-FLOWER-AFTER-F1-local-{name.split('-')[1]}.png",
                lo, span)
            np.save(CACHE / f"20-flower-{name}.npy", sel)
    del cube, field, outs

    # ---- bee -------------------------------------------------------------
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(CACHE / "bee3-leg-field.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[BEE_INNER[0]:BEE_INNER[1], BEE_INNER[2]:BEE_INNER[3]] = True
    treat = inner & (~mask) & (dist <= YOKE)
    outs = run("bee", cube, field, mask, sel0, argbest, BEE_INNER, treat, res)
    for name, sel in outs.items():
        if name.startswith("local"):
            np.save(CACHE / f"20-bee-{name}.npy", sel)

    json.dump(res, open(DATA / "20-local-partition.json", "w"), indent=1)
    print("\nwrote data/20-local-partition.json")


if __name__ == "__main__":
    main()
