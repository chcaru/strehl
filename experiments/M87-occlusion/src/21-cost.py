"""M87 step 21 -- what the winning arm COSTS, and where it fires falsely.

Step 20 measured the fix: a per-pixel mode partition removes 87.9% (bee) and
84.6% (flower) of the halo at DELTA = 40 with one parameter set and no
refitting.  A reduction is not a result until its price is on the table, so this
step prices it three ways and builds the control that is designed to make it
fail.

  1. WHAT IT MOVED.  Fraction of treated pixels whose elected frame actually
     changed, and -- among those -- the ratio of the focus value they end up
     with to the one they were denied.  This is the physical cost: focus quality
     surrendered.  At a genuine occlusion boundary the background's own focus
     peak is far from the foreground's, so the ratio should be near 1.  Where it
     is not, the fix has taken a real in-focus sample away from a real pixel.

  2. WHERE IT MADE THINGS WORSE.  Per-profile, the fraction where the isotonic
     residual o_j INCREASES.  A median improving while a third of profiles
     degrade is a different result from a uniform improvement.

  3. WHAT IT LEFT ALONE.  Max |delta| outside the treated set, which must be
     exactly zero by construction, and is checked rather than asserted.

  4. THE CONTROL THAT MUST FAIL.  A synthetic disc planted in flat background,
     where the "foreground" is fake and the surface behind it is at the SAME
     depth -- a non-occluding edge.  Forbidding frames near that mask's own
     elected frame must cost focus quality, because there is no second depth to
     fall back on.  If the fix is free here too, it is not doing what this report
     says it does.
"""

import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
SHIP = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")

MARGIN = 22
INNER = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)
YOKE = 40
KF_MEDIAN = 15
DELTAS = (20, 40, 80)
CROP = (150, 700, 120, 1000)
DISC_C, DISC_R = (330, 980), 90


def kf_map(mask, argbest):
    inside = ndi.median_filter(argbest.astype(np.float32), size=KF_MEDIAN)
    _, (iy, ix) = ndi.distance_transform_edt(~mask, return_indices=True)
    return inside[iy, ix]


def partition(field, cube, treat, kf, delta):
    n, h, w = field.shape
    best = np.full((h, w), -np.inf, np.float32)
    arg = np.zeros((h, w), np.int32)
    for k in range(n):
        fld = np.asarray(field[k], np.float32)
        better = (fld > best) & ~(treat & (np.abs(kf - k) < delta))
        best[better] = fld[better]
        arg[better] = k
    sel = np.empty((h, w), np.float32)
    for k in range(n):
        m = arg == k
        if m.any():
            sel[m] = np.asarray(cube[k], np.float32)[m]
    return sel, arg, best


def png(a, path, lo, span, gamma=2.2):
    v = np.clip((a - lo) / span, 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def main():
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(CACHE / "bee3-leg-field.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    best0 = np.load(CACHE / "bee3-leg-best.npy")
    n, h, w = field.shape

    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[INNER[0]:INNER[1], INNER[2]:INNER[3]] = True
    treat = inner & (~mask) & (dist <= YOKE)
    kf = kf_map(mask, argbest)

    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    base = M2.score_iso(sel0, p, nv, boot=500)
    o0 = np.asarray(base["o"])
    print(f"bee F0 ISO={base['ISO']:.5f}  n={base['n']}", flush=True)
    res = {"bee": {"F0_ISO": base["ISO"], "n_prof": int(base["n"])}}

    ref = sel0[CROP[0]:CROP[1], CROP[2]:CROP[3]]
    lo = float(np.percentile(ref, 0.5))
    span = float(max(np.percentile(ref, 99.7) - lo, 1e-9))
    png(ref, SHIP / "09-BEE-BEFORE-shipped-merge.png", lo, span)

    for D in DELTAS:
        sel, arg, best = partition(field, cube, treat, kf, D)
        r = M2.score_iso(sel, p, nv, boot=500)
        o1 = np.asarray(r["o"])
        moved = treat & (arg != argbest)
        ret = (best[moved] / np.maximum(best0[moved], 1e-9))
        outside = ~treat
        d_out = float(np.abs(sel[outside] - sel0[outside]).max())
        worse = float(np.mean(o1 > o0 + 0.005))
        better = float(np.mean(o1 < o0 - 0.005))
        row = {
            "ISO": r["ISO"], "ISO_ci": r["ISO_ci"],
            "delta_pct": float(100 * (1 - r["ISO"] / base["ISO"])),
            "moved_frac_of_treated": float(moved.sum() / max(treat.sum(), 1)),
            "focus_retention_median": float(np.median(ret)),
            "focus_retention_p05": float(np.percentile(ret, 5)),
            "max_abs_delta_outside_treated": d_out,
            "profiles_worse_frac": worse, "profiles_better_frac": better,
        }
        res["bee"][f"local-d{D}"] = row
        print(f"  d={D:<3} ISO={r['ISO']:.5f} ({row['delta_pct']:+.1f}%)  "
              f"moved={row['moved_frac_of_treated']:.3f}  "
              f"focus retention med={row['focus_retention_median']:.3f} "
              f"p05={row['focus_retention_p05']:.3f}  "
              f"outside |d|max={d_out:.1f}  "
              f"profiles worse={worse:.3f} better={better:.3f}", flush=True)
        png(sel[CROP[0]:CROP[1], CROP[2]:CROP[3]],
            SHIP / f"10-BEE-AFTER-F1-local-d{D}.png", lo, span)
        np.save(CACHE / f"21-bee-local-d{D}.npy", sel)

    # ---- the control that must fail: a non-occluding edge -----------------
    yy, xx = np.ogrid[:h, :w]
    disc = ((yy - DISC_C[0]) ** 2 + (xx - DISC_C[1]) ** 2) <= DISC_R ** 2
    disc &= ~mask
    print(f"\nplanted disc: {disc.sum()} px, overlaps real fg: "
          f"{(disc & mask).sum()}", flush=True)
    ddist = ndi.distance_transform_edt(~disc).astype(np.float32)
    dtreat = inner & (~disc) & (~mask) & (ddist <= YOKE)
    dkf = kf_map(disc, argbest)
    res["control_nonoccluding_disc"] = {"px": int(disc.sum())}
    for D in DELTAS:
        sel, arg, best = partition(field, cube, dtreat, dkf, D)
        moved = dtreat & (arg != argbest)
        ret = best[moved] / np.maximum(best0[moved], 1e-9)
        row = {"moved_frac_of_treated": float(moved.sum() / max(dtreat.sum(), 1)),
               "focus_retention_median": float(np.median(ret)),
               "focus_retention_p05": float(np.percentile(ret, 5))}
        res["control_nonoccluding_disc"][f"local-d{D}"] = row
        print(f"  d={D:<3} moved={row['moved_frac_of_treated']:.3f}  "
              f"focus retention med={row['focus_retention_median']:.3f} "
              f"p05={row['focus_retention_p05']:.3f}", flush=True)

    # ---- flower: profile-level cost from step 20's saved arrays -----------
    fs0 = np.load(CACHE / "19-flower-sel0.npy")
    fmask = np.load(CACHE / "19-flower-mask.npy")
    fh, fw = fmask.shape
    fpts, fnrm = M2.boundary_normals(fmask, roi=(30, fh - 30, 30, fw - 30))
    fval = M2.valid_profiles(fmask, fpts, fnrm, d_max=M2.D_MAX)
    fp, fnv = fpts[fval], fnrm[fval]
    fb = M2.score_iso(fs0, fp, fnv, boot=0)
    fo0 = np.asarray(fb["o"])
    fdist = ndi.distance_transform_edt(~fmask)
    finner = np.zeros(fmask.shape, bool)
    finner[30:fh - 30, 30:fw - 30] = True
    ftreat = finner & (~fmask) & (fdist <= YOKE)
    res["flower"] = {"F0_ISO": fb["ISO"], "n_prof": int(fb["n"])}
    print(f"\nflower F0 ISO={fb['ISO']:.5f}  n={fb['n']}", flush=True)
    for D in (40, 80):
        sel = np.load(CACHE / f"20-flower-local-d{D}.npy")
        r = M2.score_iso(sel, fp, fnv, boot=0)
        o1 = np.asarray(r["o"])
        d_out = float(np.abs(sel[~ftreat] - fs0[~ftreat]).max())
        row = {"ISO": r["ISO"],
               "delta_pct": float(100 * (1 - r["ISO"] / fb["ISO"])),
               "max_abs_delta_outside_treated": d_out,
               "profiles_worse_frac": float(np.mean(o1 > fo0 + 0.005)),
               "profiles_better_frac": float(np.mean(o1 < fo0 - 0.005))}
        res["flower"][f"local-d{D}"] = row
        print(f"  d={D:<3} ISO={r['ISO']:.5f} ({row['delta_pct']:+.1f}%)  "
              f"outside |d|max={d_out:.1f}  "
              f"profiles worse={row['profiles_worse_frac']:.3f} "
              f"better={row['profiles_better_frac']:.3f}", flush=True)

    json.dump(res, open(DATA / "21-cost.json", "w"), indent=1)
    for f in SHIP.glob("09-BEE-*.png"):
        Image.open(f).save(OUT / f.name)
    for f in SHIP.glob("10-BEE-*.png"):
        Image.open(f).save(OUT / f.name)
    print("\nwrote data/21-cost.json")


if __name__ == "__main__":
    main()
