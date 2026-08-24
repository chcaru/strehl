"""M87 step 5 -- is the halo photometric? (the mundane-cause check, W4/W5)

Step 4 produced, on a common stretch, a gate-0 merge whose background is much
DARKER than the background of any of the individual frames that were plotted
(k=0, 144, 149, 151).  A per-pixel selection merge writes, at every pixel, the
value of exactly one frame.  It therefore cannot be darker everywhere than
every frame in the stack -- unless the stack contains much darker frames and
the background elects them.

That is the photometric hypothesis:

  H_photo : the sweep drifts in level, L(k); a pixel's merged value carries the
            level of whichever frame it elected; the halo is the LEVEL STEP
            between the frame elected in the near-edge band and the frame
            elected in the far background.

It predicts, and this script measures:

  P1  L(k) has a range comparable to the halo amplitude (~2% of level).
  P2  argbest differs systematically between the near-edge band and the far
      background.
  P3  dividing every frame by its own L(k) before the ESTIMATE step -- with the
      SELECTION left bit-identical -- removes most of the halo.

P3 is the decisive one: it changes no selection at all, so anything it removes
was never a selection error.

Everything runs off the cached cubes written by 04-through-focus.py.
"""

import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"

MARGIN = 22
ROI = L.ROIS["ROI_LEG"]
BOX = (ROI[0] - MARGIN, ROI[1] + MARGIN, ROI[2] - MARGIN, ROI[3] + MARGIN)
INNER = (MARGIN, MARGIN + (ROI[1] - ROI[0]), MARGIN, MARGIN + (ROI[3] - ROI[2]))


def to_png(a, path, lo, hi, gamma=2.2):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def main():
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    n = lumas.shape[0]
    print(f"cube {lumas.shape}  mask fg {mask.mean():.4f}", flush=True)

    # ---- distance from the merged foreground mask -----------------------
    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[INNER[0]:INNER[1], INNER[2]:INNER[3]] = True

    band = inner & (~mask) & (dist >= 2) & (dist <= 24)
    far = inner & (~mask) & (dist >= 60)
    print(f"band px {band.sum()}   far px {far.sum()}", flush=True)

    # ---- P1: the level curve L(k) over a FIXED far-background set --------
    # far is fixed across k, so L(k) is a pure per-frame level, not a
    # per-pixel selection effect.
    lk_p, lb_p = OUT / "05-Lk.npy", OUT / "05-Lband.npy"
    if lk_p.exists() and lb_p.exists():
        Lk, Lband = np.load(lk_p), np.load(lb_p)
    else:
        Lk = np.empty(n, np.float64)
        Lband = np.empty(n, np.float64)
        for k in range(n):
            f = np.asarray(lumas[k], np.float32)
            Lk[k] = float(f[far].mean())
            Lband[k] = float(f[band].mean())
        np.save(lk_p, Lk)
        np.save(lb_p, Lband)

    print("\nL(k) over the FIXED far-background set (DN, green luma):")
    for k in range(0, n, 20):
        print(f"  k={k:3d}  L={Lk[k]:9.1f}   band={Lband[k]:9.1f}")
    print(f"  k={n - 1:3d}  L={Lk[-1]:9.1f}   band={Lband[-1]:9.1f}")
    rng = Lk.max() - Lk.min()
    print(f"\nL(k): min {Lk.min():.1f} @k={int(Lk.argmin())}  "
          f"max {Lk.max():.1f} @k={int(Lk.argmax())}  "
          f"range {rng:.1f} DN = {100 * rng / Lk.mean():.2f}% of mean")

    # ---- P2: which frames do band and far elect? -------------------------
    ab_band = argbest[band]
    ab_far = argbest[far]
    print(f"\nargbest  band: median {np.median(ab_band):.0f}  "
          f"mean {ab_band.mean():.1f}  p10 {np.percentile(ab_band, 10):.0f}  "
          f"p90 {np.percentile(ab_band, 90):.0f}")
    print(f"argbest  far : median {np.median(ab_far):.0f}  "
          f"mean {ab_far.mean():.1f}  p10 {np.percentile(ab_far, 10):.0f}  "
          f"p90 {np.percentile(ab_far, 90):.0f}")
    dL_pred = Lk[ab_band].mean() - Lk[ab_far].mean()
    print(f"\nPREDICTED level step from election alone: "
          f"<L(k_band)> - <L(k_far)> = {dL_pred:.1f} DN")

    # ---- the observed step ----------------------------------------------
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    obs = float(sel[band].mean() - sel[far].mean())
    print(f"OBSERVED  step in the gate-0 merge:        "
          f"<M|band> - <M|far>      = {obs:.1f} DN")
    print(f"explained fraction = {100 * dL_pred / obs:.1f}%"
          if abs(obs) > 1e-6 else "")

    # ---- P3: renormalise the ESTIMATE only, selection untouched ----------
    ref = float(np.median(Lk))
    gain = (ref / Lk).astype(np.float32)
    sel_norm = sel * gain[argbest]
    np.save(CACHE / "bee3-leg-sel-norm.npy", sel_norm)

    prof_raw, _ = L.band_profile(sel, mask, INNER)
    prof_nrm, _ = L.band_profile(sel_norm, mask, INNER)
    np.save(OUT / "05-prof-raw.npy", prof_raw)
    np.save(OUT / "05-prof-norm.npy", prof_nrm)

    print("\n d   E_raw(d)   E_norm(d)      (mean merged value at distance d)")
    for d in range(1, 97):
        a, b = prof_raw[d], prof_nrm[d]
        if np.isfinite(a):
            print(f"{d:3d}  {a:9.1f}  {b:9.1f}")

    def amp(p):
        seg = p[2:25]
        base = np.nanmean(p[60:97])
        return float(np.nanmax(seg) - base), float(base)

    a_raw, b_raw = amp(prof_raw)
    a_nrm, b_nrm = amp(prof_nrm)
    print(f"\nhalo amplitude (max over d in [2,24]  minus  mean over d in [60,96])")
    print(f"  raw        {a_raw:8.1f} DN   (far level {b_raw:.1f}, "
          f"{100 * a_raw / b_raw:.2f}%)")
    print(f"  normalised {a_nrm:8.1f} DN   (far level {b_nrm:.1f}, "
          f"{100 * a_nrm / b_nrm:.2f}%)")
    if abs(a_raw) > 1e-9:
        print(f"  removed by photometric normalisation: "
              f"{100 * (a_raw - a_nrm) / a_raw:.1f}%")

    sub = (300, 800, 100, 800)
    lo, hi = np.percentile(sel[sub[0]:sub[1], sub[2]:sub[3]], (0.5, 99.7))
    to_png(sel[sub[0]:sub[1], sub[2]:sub[3]], OUT / "05-raw.png", lo, hi)
    to_png(sel_norm[sub[0]:sub[1], sub[2]:sub[3]], OUT / "05-norm.png", lo, hi)

    json.dump({
        "n": n, "Lk_min": float(Lk.min()), "Lk_max": float(Lk.max()),
        "Lk_argmin": int(Lk.argmin()), "Lk_argmax": int(Lk.argmax()),
        "Lk_range_pct": float(100 * rng / Lk.mean()),
        "argbest_band_median": float(np.median(ab_band)),
        "argbest_far_median": float(np.median(ab_far)),
        "dL_pred": float(dL_pred), "obs_step": obs,
        "amp_raw": a_raw, "amp_norm": a_nrm,
        "far_raw": b_raw, "far_norm": b_nrm,
    }, open(DATA / "05-photometry.json", "w"), indent=1)
    print("\nwrote data/05-photometry.json")


if __name__ == "__main__":
    main()
