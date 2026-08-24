"""M87 addendum 4 / R1 controls -- C-resample, C1, C3, and the owner's crops.

Step 35 measured ISO_U = 0.07227 and ISO_A = 0.06642, an 8.1% drop with heavily
overlapping CIs. Two things are still wrong with that as it stands:

  1. The placebo in step 35 was MINE and it was broken. It called
     foreground_mask(img, hist_roi=ROI_FLAT), which runs Otsu on a region that
     contains ONLY background -- so Otsu dutifully split background noise into
     two classes and manufactured 615 spurious "edges" out of nothing, scoring
     ISO = 0.0139. That is an instrument error, not a finding. The registered
     placebos are the shipped C1 (real mask translated into empty background)
     and C3 (a synthetic disc planted in ROI_FLAT); this script uses those.

  2. Arm A resamples and arm U does not. The M86c gather is Catmull-Rom
     (align_cmd.rs:74 default, align.rs:2303) and warpmap.rs:350-360 records
     M86 measuring that this resampler "destroys most sub-pixel" content. An
     interpolator is a lowpass, so ANY warped arm scores lower on a fine-scale
     edge metric for a reason that has nothing to do with registration. Without
     this control the 8.1% is uninterpretable, and had it come out at 55% the
     control would have been the only thing standing between the project and a
     false R1-A.

C-resample: warp U by the SAME similarity, with the SAME kernel, and re-score.

     resampling effect   = ISO_Uw - ISO_U
     registration effect = ISO_A  - ISO_Uw

Both arms are then resampled exactly once, so the comparison isolates the thing
the experiment is named after. Caveat, stated because it is real: arm A warps
each frame BEFORE selection, this control warps AFTER the merge. It therefore
bounds the interpolator's lowpass rather than reproducing arm A's exact path.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
import m87lib as L          # noqa: E402
import m87metric2 as M2     # noqa: E402

CACHE = HERE / "cache"
DATA = HERE / "data"
ALIGN = CACHE / "align"
DEST = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
ROI_U = L.ROIS["ROI_LEG"]
FLAT = L.ROIS["ROI_FLAT"]


def green_of(p):
    return tifffile.imread(str(p))[:, :, 1].astype(np.float32)


def cr_w(f):
    """Catmull-Rom weights, transcribed from align.rs:2279 verbatim."""
    f2, f3 = f * f, f * f * f
    return np.stack([-0.5 * f3 + f2 - 0.5 * f,
                     1.5 * f3 - 2.5 * f2 + 1.0,
                     -1.5 * f3 + 2.0 * f2 + 0.5 * f,
                     0.5 * f3 - 0.5 * f2])


def cr_axis(img, src, axis):
    """Separable Catmull-Rom gather along one axis at source coords `src`."""
    img = np.moveaxis(img, axis, 0)
    n = img.shape[0]
    i0 = np.floor(src).astype(np.int64)
    w = cr_w((src - i0).astype(np.float32))
    out = np.zeros((len(src),) + img.shape[1:], np.float32)
    for t in range(4):
        idx = np.clip(i0 + t - 1, 0, n - 1)
        out += w[t][:, None] * img[idx]
    return np.moveaxis(out, 0, axis)


def cr_scale(img, cu, ca, s):
    """Warp `img` so content at `cu` and scale 1 lands at `ca` and scale `s`."""
    h, w = img.shape
    ys = (np.arange(h, dtype=np.float64) - ca[0]) / s + cu[0]
    xs = (np.arange(w, dtype=np.float64) - ca[1]) / s + cu[1]
    return cr_axis(cr_axis(img, xs, 1), ys, 0)


def geom(m):
    ys, xs = np.nonzero(m)
    return float(ys.mean()), float(xs.mean()), float(m.sum())


def score_mask(img, mask, roi, tag):
    pts, nrm = M2.boundary_normals(mask, roi=roi)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    if val.sum() < M2.MIN_PROFILES:
        print(f"  {tag:34s} {val.sum():5d} valid profiles -- BELOW "
              f"MIN_PROFILES={M2.MIN_PROFILES}, metric not computed")
        return {"ISO": None, "n": int(val.sum()),
                "note": "below MIN_PROFILES; metric declines to report"}
    r = M2.score_iso(img, pts[val], nrm[val])
    if r is None:
        print(f"  {tag:34s} score_iso declined")
        return {"ISO": None, "n": int(val.sum())}
    print(f"  {tag:34s} ISO={r['ISO']:.5f} "
          f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}] n={r['n']} "
          f"d*={r['d_star']:.0f}")
    return {"ISO": r["ISO"], "ISO_ci": r["ISO_ci"], "n": r["n"],
            "d_star": r["d_star"], "frac_gt_02": r["frac_gt_02"]}


def planted_disc(shape, c, r):
    y, x = np.ogrid[:shape[0], :shape[1]]
    return (y - c[0]) ** 2 + (x - c[1]) ** 2 <= r * r


def png(a, path, lo, hi, gamma=2.2):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def main():
    out = {}
    u = green_of(ALIGN / "U-unaligned.tif")
    a = green_of(ALIGN / "A-aligned.tif")
    mu, tu = L.foreground_mask(u)
    ma, ta = L.foreground_mask(a)
    gu, ga = geom(mu), geom(ma)
    s = float(np.sqrt(ga[2] / gu[2]))
    roi_a = (int(round((ROI_U[0] - gu[0]) * s + ga[0])),
             int(round((ROI_U[1] - gu[0]) * s + ga[0])),
             int(round((ROI_U[2] - gu[1]) * s + ga[1])),
             int(round((ROI_U[3] - gu[1]) * s + ga[1])))

    print("=== C-resample: is the 8.1% just the Catmull-Rom lowpass? ===")
    uw = cr_scale(u, (gu[0], gu[1]), (ga[0], ga[1]), s)
    muw, _ = L.foreground_mask(uw)
    ident = cr_scale(u, (gu[0], gu[1]), (gu[0], gu[1]), 1.0)
    d_ident = float(np.abs(ident - u).max())
    print(f"  identity-warp max |err| = {d_ident:.6g}  "
          f"(Catmull-Rom must reproduce samples exactly at integer positions)")
    out["identity_max_err"] = d_ident

    rU = score_mask(u, mu, ROI_U, "U  unaligned, unresampled")
    rUw = score_mask(uw, muw, roi_a, "Uw unaligned, resampled once")
    rA = score_mask(a, ma, roi_a, "A  aligned,   resampled once")
    out["U"], out["Uw"], out["A"] = rU, rUw, rA

    if rU["ISO"] and rUw["ISO"] and rA["ISO"]:
        res_eff = 100.0 * (rUw["ISO"] - rU["ISO"]) / rU["ISO"]
        reg_eff = 100.0 * (rA["ISO"] - rUw["ISO"]) / rU["ISO"]
        tot = 100.0 * (rA["ISO"] - rU["ISO"]) / rU["ISO"]
        print(f"\n  resampling alone   : {res_eff:+.1f}% of ISO_U")
        print(f"  registration alone : {reg_eff:+.1f}% of ISO_U")
        print(f"  total U -> A       : {tot:+.1f}% of ISO_U")
        out["resample_pct"] = res_eff
        out["registration_pct"] = reg_eff
        out["total_pct"] = tot

    print("\n=== registered placebos (the SHIPPED C1/C3, not step 35's) ===")
    for tag, img, m, roi in (("U", u, mu, ROI_U), ("A", a, ma, roi_a)):
        sh = L.shifted_mask(m, L.SHIFT_OFFSET)
        sroi = (roi[0] + L.SHIFT_OFFSET[0], roi[1] + L.SHIFT_OFFSET[0],
                roi[2] + L.SHIFT_OFFSET[1], roi[3] + L.SHIFT_OFFSET[1])
        sroi = (max(0, sroi[0]), min(img.shape[0], sroi[1]),
                max(0, sroi[2]), min(img.shape[1], sroi[3]))
        out[f"C1_{tag}"] = score_mask(img, sh, sroi, f"C1 {tag} mask shifted to bg")

        cy, cx = (FLAT[0] + FLAT[1]) // 2, (FLAT[2] + FLAT[3]) // 2
        disc = planted_disc(img.shape, (cy, cx), 120)
        droi = (max(cy - 300, 0), min(cy + 300, img.shape[0]),
                max(cx - 170, 0), min(cx + 170, img.shape[1]))
        out[f"C3_{tag}"] = score_mask(img, disc, droi, f"C3 {tag} disc in ROI_FLAT")

    print("\n=== owner crops ===")
    DEST.mkdir(parents=True, exist_ok=True)
    cu = u[ROI_U[0]:ROI_U[1], ROI_U[2]:ROI_U[3]]
    ca = a[roi_a[0]:roi_a[1], roi_a[2]:roi_a[3]]
    ca = np.asarray(Image.fromarray(ca).resize((cu.shape[1], cu.shape[0]),
                                               Image.BILINEAR))
    lo, hi = float(np.percentile(cu, 0.5)), float(np.percentile(cu, 99.5))
    png(cu, DEST / "20-REGISTRATION-unaligned.png", lo, hi)
    png(ca, DEST / "21-REGISTRATION-aligned.png", lo, hi)
    gap = np.full((cu.shape[0], 16), hi, np.float32)
    png(np.hstack([cu, gap, ca]), DEST / "22-REGISTRATION-side-by-side.png", lo, hi)
    print(f"  wrote 3 crops to {DEST}")
    out["crop_levels"] = [lo, hi]
    out["roi_A"] = list(roi_a)
    out["scale"] = s

    (DATA / "36-registration-controls.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("wrote data/36-registration-controls.json")


if __name__ == "__main__":
    main()
