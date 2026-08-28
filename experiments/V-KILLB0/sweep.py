"""V-KILLB0 sweep: one pass per subject pair, every statistic that needs the
pixels, so a 200 MB TIFF is decoded once instead of five times.

Includes STRUCTURE-SELECTIVE acuity, which exists because of a defect found in
contrast_ms.py:

  contrast_ms.py scores "EDGE" on 256x256 TILES chosen by mean gradient.  At
  this magnification an edge tile is still overwhelmingly flat area -- measured
  below as `edge_px_frac` -- so its band statistic is dominated by the SAME
  flat noise the arm is removing, and an arm that softened every edge while
  cleaning the surrounding flat would still score near 1.0.  Selecting PIXELS
  on a coarse, signal-dominated structure map and reading the fine bands only
  there removes that dilution.

  The selector is the 0.05-0.17 cyc/px structure magnitude, which both arms
  agree on to ~2-4% (measured, `rho` in the coh table), so it is a nearly
  arm-independent choice of where the picture is.

Reported per subject:
  * clip% / black% / median, whole image and per site set (fact 1817)
  * band ratios, FLAT / EDGE / ALL tiles, luma and green
  * coherent gain g and D = ln g / ln rho, the denoise-vs-blur discriminator
  * structure-selective fine-band ratio at the top 1% and top 0.1% structure
    pixels, and at the bottom 50% (the true flat)
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp
import coh


def structure_stats(la, lb):
    """Fine-band amplitude ratio as a function of how structured the pixel is."""
    # selector: coarse structure magnitude, 0.05-0.17 cyc/px-ish, from arm A
    sel = np.abs(gaussian_filter(la, 1.5) - gaussian_filter(la, 4.0))
    sel = gaussian_filter(sel, 2.0)
    # bands, matched to the two disputed regions
    fa = la - gaussian_filter(la, 0.6366)          # 0.25-0.5  ("NOISE" band)
    fb = lb - gaussian_filter(lb, 0.6366)
    ma = gaussian_filter(la, 0.6366) - gaussian_filter(la, 0.9362)   # 0.17-0.25
    mb = gaussian_filter(lb, 0.6366) - gaussian_filter(lb, 0.9362)
    out = {}
    qs = {"top0.1%": 99.9, "top1%": 99.0, "top10%": 90.0}
    for name, q in qs.items():
        t = np.percentile(sel, q)
        m = sel >= t
        out[name] = {
            "n_px": int(m.sum()),
            "fine_A": float(np.sqrt((fa[m] ** 2).mean())),
            "fine_B": float(np.sqrt((fb[m] ** 2).mean())),
            "mid_A": float(np.sqrt((ma[m] ** 2).mean())),
            "mid_B": float(np.sqrt((mb[m] ** 2).mean())),
        }
    t50 = np.percentile(sel, 50.0)
    m = sel < t50
    out["bottom50%"] = {
        "n_px": int(m.sum()),
        "fine_A": float(np.sqrt((fa[m] ** 2).mean())),
        "fine_B": float(np.sqrt((fb[m] ** 2).mean())),
        "mid_A": float(np.sqrt((ma[m] ** 2).mean())),
        "mid_B": float(np.sqrt((mb[m] ** 2).mean())),
    }
    for k in out:
        out[k]["fine_ratio"] = out[k]["fine_B"] / out[k]["fine_A"]
        out[k]["mid_ratio"] = out[k]["mid_B"] / out[k]["mid_A"]
    # how much of a 256px EDGE tile is actually edge?  the dilution number.
    ny, nx = bp.grid(la.shape)
    g = np.hypot(*np.gradient(gaussian_filter(la, 2.0)))
    tg = bp.tile_means(g, ny, nx).ravel()
    top = np.argsort(tg)[-12:]
    t99 = np.percentile(sel, 99.0)
    fr = []
    for f in top:
        ty, tx = divmod(int(f), nx)
        y, x = ty * bp.TILE, tx * bp.TILE
        fr.append(float((sel[y:y + bp.TILE, x:x + bp.TILE] >= t99).mean()))
    out["edge_px_frac"] = float(np.mean(fr))
    return out


def commission_structure(la):
    """The same two planted arms commission.py C4 uses, on THIS statistic."""
    rng = np.random.default_rng(19)
    h, w = la.shape
    sub = la[h // 2 - 768:h // 2 + 768, w // 2 - 768:w // 2 + 768]
    noisy = sub + rng.normal(0, 300.0, sub.shape)
    dn = structure_stats(noisy, sub)          # planted pure denoise
    bl = structure_stats(sub, gaussian_filter(sub, 0.55))   # planted pure blur
    nul = structure_stats(sub, sub.copy())
    ok0 = abs(nul["top1%"]["fine_ratio"] - 1.0) < 1e-12
    okd = dn["top0.1%"]["fine_ratio"] > 0.93
    okb = bl["top0.1%"]["fine_ratio"] < 0.75
    return {
        "C0_null": ok0, "C1_denoise": okd, "C2_blur": okb,
        "null_top1": nul["top1%"]["fine_ratio"],
        "denoise_top0.1": dn["top0.1%"]["fine_ratio"],
        "denoise_bottom50": dn["bottom50%"]["fine_ratio"],
        "blur_top0.1": bl["top0.1%"]["fine_ratio"],
        "blur_bottom50": bl["bottom50%"]["fine_ratio"],
    }


def main():
    name, A, B, outdir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    do_comm = "--commission" in sys.argv
    imA, imB = bp.load(A), bp.load(B)
    assert imA.shape == imB.shape, f"{name}: shape mismatch"
    la = bp.channels(imA)["L"]
    lb = bp.channels(imB)["L"]
    res = {"name": name}

    top = 65535
    res["clip_A"] = float((imA.max(axis=2) >= top).mean() * 100)
    res["clip_B"] = float((imB.max(axis=2) >= top).mean() * 100)
    res["black_A"] = float((imA.min(axis=2) <= 0).mean() * 100)
    res["black_B"] = float((imB.min(axis=2) <= 0).mean() * 100)
    res["median_A"] = float(np.median(la))
    res["median_B"] = float(np.median(lb))
    res["mean_A"] = float(la.mean())
    res["mean_B"] = float(lb.mean())

    if do_comm:
        res["commission"] = commission_structure(la)

    res["structure"] = structure_stats(la, lb)

    nx, sites = coh.sites_of(la)
    ny = bp.grid(la.shape)[0]
    g = np.hypot(*np.gradient(gaussian_filter(la, 2.0)))
    tg = bp.tile_means(g, ny, nx)
    tclip = bp.tile_means((imA.max(axis=2) >= top).astype(float), ny, nx).ravel() * 100
    tblk = bp.tile_means((imA.min(axis=2) <= 0).astype(float), ny, nx).ravel() * 100
    tlev = bp.tile_means(la, ny, nx).ravel()
    res["sites"] = {}
    for sname, idx in sites.items():
        rho, gg, D = coh.pooled(la, lb, idx, nx)
        res["sites"][sname] = {
            "n": int(len(idx)),
            "clip_pct": float(tclip[idx].mean()),
            "black_pct": float(tblk[idx].mean()),
            "level": float(tlev[idx].mean()),
            "rho": rho.tolist(), "g": gg.tolist(), "D": D.tolist(),
        }
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, f"{name}.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"{name}: done  medianA={res['median_A']:.0f} clipA={res['clip_A']:.2f}% "
          f"fine top0.1%={res['structure']['top0.1%']['fine_ratio']:.4f} "
          f"bottom50%={res['structure']['bottom50%']['fine_ratio']:.4f}", flush=True)


if __name__ == "__main__":
    main()
