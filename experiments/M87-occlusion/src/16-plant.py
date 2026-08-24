"""M87 step 16 -- the synthetic two-layer plant, its capability check, the
unmixing control that succeeds on known ground truth, and its deliberate
breakage.

WHY THIS PLANT CAN EXPRESS A HALO (required justification; SYNTHESIS facts
567/568/603 record a previous milestone whose plant could not express the effect
it was built to test -- enrichment 0.23x, wrong sign).

The measured mechanism on bee-3-cpl (step 11) is: near-edge background pixels
have their focus field driven by foreground-derived structure, so they elect
k ~ k_F, the frame in which they are least veiled and -- the foreground being
dark -- brightest; far background pixels elect an arbitrary k and land near the
median of their own through-focus distribution; the rim is the seam. For a
plant to reproduce that it needs, and this one has, all four of:

  1. a foreground MUCH DARKER than the background, so a change in coverage is a
     change in brightness (F = 0.08, B mean = 0.75);
  2. a foreground blur radius that sweeps through zero, so alpha_k genuinely
     varies from large to ~0 and back (sigma_F(k) = |k - kF| * SCALE);
  3. BACKGROUND TEXTURE with its own focus peak at a different k, so the far
     field has something to lock onto and does not simply inherit the
     foreground's decision -- without this the plant has no seam and no halo;
  4. compositing in the order SYNTHESIS fact 549 measured as first-order:
     occlude first, blur each layer by its own depth's PSF, composite with the
     BLURRED matte, alpha_k = m * PSF^F_k.

It is also deliberately free of the bee's confounds: a straight silhouette, no
hair fringe, no illumination drift, so a failure here cannot be blamed on them.

Ground truth available: F, B, m, alpha_k, and the all-in-focus composite.
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

H, W = 384, 512
N = 121
KF = 40           # frame at which the foreground is sharp
KB = 90           # frame at which the background is sharp
SCALE = 0.28      # px of blur radius per frame of defocus
LEVEL = 3000.0    # DN, so the noise model is in the same regime as the capture
READ_SD = 6.0
ROI = (40, H - 40, 40, W - 40)


def build():
    rng = np.random.default_rng(87)
    yy, xx = np.mgrid[0:H, 0:W]

    # background: textured, mean 0.75.  The texture must be HIGH FREQUENCY and
    # LOW AMPLITUDE: high frequency so it carries enough gradient to give the
    # far field its own focus peak at KB (without which the plant has no seam
    # and therefore no halo to find), low amplitude so it does not itself
    # dominate the edge-normal profile.  The first build of this plant used
    # 0.10-amplitude texture at ~10 px period and FAILED its own capability
    # check: the ground-truth all-in-focus composite scored ISO = 0.0774,
    # ABOVE the merge's 0.0556, i.e. the metric was reading texture, not halo.
    b = 0.75 + 0.035 * np.sin(xx / 1.6) * np.cos(yy / 1.9)
    b += 0.012 * ndi.gaussian_filter(rng.standard_normal((H, W)), 0.8)
    b = np.clip(b, 0.2, 1.0)

    # foreground: a dark vertical bar with a slight taper, textured a little
    m = ((xx > 150) & (xx < 260)).astype(np.float32)
    m *= (yy > 20) & (yy < H - 20)
    m = ndi.gaussian_filter(m, 0.6)
    m = np.clip(m, 0, 1)
    f = 0.08 + 0.03 * np.sin(yy / 7.0)

    frames = np.empty((N, H, W), np.float32)
    alphas = np.empty((N, H, W), np.float32)
    for k in range(N):
        sf = abs(k - KF) * SCALE
        sb = abs(k - KB) * SCALE
        a = ndi.gaussian_filter(m, sf) if sf > 0.3 else m.copy()
        fb = ndi.gaussian_filter(m * f, sf) if sf > 0.3 else (m * f)
        bb = ndi.gaussian_filter(b, sb) if sb > 0.3 else b.copy()
        img = fb + bb * (1.0 - a)
        alphas[k] = a
        v = img * LEVEL
        frames[k] = v + rng.normal(0, np.sqrt(np.maximum(v, 1.0)) + READ_SD, (H, W))
    truth = (m * f + b * (1.0 - m)) * LEVEL          # all-in-focus composite
    unveiled_b = b * LEVEL                            # what unmixing should give
    return frames, alphas, m, f, b, truth, unveiled_b


def merge(frames, iso=100.0):
    n = len(frames)
    best = np.full(frames.shape[1:], -np.inf, np.float32)
    arg = np.zeros(frames.shape[1:], np.int32)
    for k in range(n):
        fl = L.regularised_field(frames[k], iso)
        better = fl > best
        best[better] = fl[better]
        arg[better] = k
    sel = np.empty(frames.shape[1:], np.float32)
    for k in range(n):
        s = arg == k
        if s.any():
            sel[s] = frames[k][s]
    return sel, arg


def unmix(frames, alpha):
    n = len(frames)
    s1 = float(n)
    sa = alpha.sum(0).astype(np.float64)
    saa = (alpha ** 2).sum(0).astype(np.float64)
    si = frames.sum(0).astype(np.float64)
    sai = (alpha * frames).sum(0).astype(np.float64)
    sii = (frames.astype(np.float64) ** 2).sum(0)
    den = s1 * saa - sa * sa
    den = np.where(np.abs(den) < 1e-9, np.nan, den)
    b = (s1 * sai - sa * si) / den
    a0 = (si - b * sa) / s1
    ss_tot = sii - si * si / s1
    ss_res = sii - a0 * si - b * sai
    r2 = 1.0 - ss_res / np.where(ss_tot < 1e-9, np.nan, ss_tot)
    return a0.astype(np.float32), r2.astype(np.float32)


def alpha_model(m, kf, scale, n):
    a = np.empty((n,) + m.shape, np.float32)
    for k in range(n):
        s = abs(k - kf) * scale
        a[k] = ndi.gaussian_filter(m, s) if s > 0.3 else m
    return a


def png(a, path, lo, hi, gamma=2.2):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def main():
    frames, alphas, m, f, b, truth, unveiled = build()
    mask = m > 0.5
    sel, arg = merge(frames)
    pts, nrm = M2.boundary_normals(mask, roi=ROI)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    print(f"plant {N}x{H}x{W}   boundary {len(pts)} valid {val.sum()}", flush=True)

    def rep(tag, img):
        r = M2.score_iso(img, p, nv, boot=500)
        print(f"  {tag:<34} ISO={r['ISO']:.5f} "
              f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]", flush=True)
        return r

    print("\n--- V5 capability check ---")
    r_truth = rep("ground-truth all-in-focus", truth)
    r_merge = rep("shipped-semantics merge", sel)
    r_frames = [M2.score_iso(frames[k], p, nv, boot=0)["ISO"] for k in range(N)]
    print(f"  {'single frames (max over k)':<34} ISO={max(r_frames):.5f}")
    ok = (r_merge["ISO"] >= 0.02) and (r_truth["ISO"] <= 0.005)
    print(f"  CAPABILITY: {'PASS' if ok else 'FAIL'} "
          f"(merge {r_merge['ISO']:.5f} >= 0.02 and truth {r_truth['ISO']:.5f} <= 0.005)")

    print("\n--- unmixing against KNOWN ground truth ---")
    bgm = ~mask
    res = {"truth_ISO": r_truth["ISO"], "merge_ISO": r_merge["ISO"],
           "frames_ISO_max": float(max(r_frames)), "capability": bool(ok)}
    for tag, (kf, sc, swap) in {
        "true alpha (oracle)": (None, None, False),
        "modelled alpha, correct scale": (KF, SCALE, False),
        "BROKEN: PSF scale x2": (KF, SCALE * 2, False),
        "BROKEN: PSF scale x0.5": (KF, SCALE * 0.5, False),
        "BROKEN: swapped layer order": (KF, SCALE, True),
        "BROKEN: wrong k_F (=KB)": (KB, SCALE, False),
    }.items():
        a = alphas if kf is None else alpha_model(m, kf, sc, N)
        if swap:
            a = 1.0 - a
        est, r2 = unmix(frames, a)
        err = est - unveiled
        rel = float(np.sqrt(np.nanmean(err[bgm] ** 2)) / LEVEL)
        med_r2 = float(np.nanmedian(r2[bgm]))
        fixed = sel.copy()
        good = bgm & np.isfinite(est) & np.isfinite(r2) & (r2 >= 0.5)
        fixed[good] = est[good]
        ri = M2.score_iso(fixed, p, nv, boot=500)
        print(f"  {tag:<32} RMSE/level={rel:.4f}  medR2={med_r2:.3f}  "
              f"cover={good[bgm].mean():.3f}  ISO={ri['ISO']:.5f} "
              f"({100 * (1 - ri['ISO'] / max(r_merge['ISO'], 1e-9)):+.0f}%)", flush=True)
        res[tag] = {"rmse_rel": rel, "median_r2": med_r2,
                    "coverage": float(good[bgm].mean()), "ISO": ri["ISO"]}
        if tag == "modelled alpha, correct scale":
            png(fixed, OUT / "16-plant-fixed.png", 0, LEVEL)

    lo, hi = 0, LEVEL
    png(sel, OUT / "16-plant-merge.png", lo, hi)
    png(truth, OUT / "16-plant-truth.png", lo, hi)
    png(frames[KF], OUT / "16-plant-frame-kF.png", lo, hi)
    json.dump(res, open(DATA / "16-plant.json", "w"), indent=1)
    print("\nwrote data/16-plant.json")


if __name__ == "__main__":
    main()
