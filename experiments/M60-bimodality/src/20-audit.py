"""M60 — the audits that decide the verdict.

  A  per-pixel texture audit. The class-level audit in 19-entropy aggregated by
     taking the median profile FIRST, which flattens any region whose pixels peak
     at different frames. Redo it per pixel: max_k f_k at each pixel, then
     aggregate. This is the number that says whether a background could be
     veiled at all.

  B  rank-matched replicate agreement. 19-entropy compared bee-2 against bee-3
     using bee-3's threshold, and bee-2 is a different ISO, so the flag rates
     were not matched. Flag the same FRACTION of pixels in each capture instead,
     and report Cohen's kappa. No threshold mismatch can survive that.

  C  the distance profile by class, from 16-distance.json.

  D  the peak separation against the focus-step geometry: the measured
     through-focus FWHM of the primary peak, in frames, per class.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cells import CELLS  # noqa: E402
import importlib
A = importlib.import_module("12-analyse")
D16 = importlib.import_module("16-distance")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))


def kappa(a, b):
    """Cohen's kappa for two binary flags on the same pixels."""
    n = len(a)
    po = float((a == b).mean())
    pe = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    return (po - pe) / (1 - pe) if pe < 1 else float("nan"), po, pe


if __name__ == "__main__":
    out = {}

    print("=" * 78)
    print("A  per-pixel texture audit: can this background be veiled at all?")
    print("   ratio = median_p(max_k f) / median_p(median_k f)  -- a pixel with no")
    print("   focusable texture has ratio near 1")
    print("=" * 78)
    tex = []
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        d = A.load(stack, name)
        if d is None:
            continue
        F, lab = d["F"], d["lab"]
        rec = dict(stack=stack, cell=name, cls=cls)
        for key, j in (("band", 0), ("fg", 1), ("bg", 2)):
            m = lab == j
            if m.sum() < 50:
                continue
            pk = F[:, m].max(axis=0)
            fl = np.median(F[:, m], axis=0)
            rec[key + "_peak"] = float(np.median(pk))
            rec[key + "_ratio"] = float(np.median(pk) / max(np.median(fl), 1e-9))
        tex.append(rec)
        print("  %-18s %-8s  bg peak %8.2f ratio %5.2f | fg peak %8.2f ratio %5.2f | "
              "band peak %8.2f ratio %5.2f"
              % (name, cls, rec.get("bg_peak", np.nan), rec.get("bg_ratio", np.nan),
                 rec.get("fg_peak", np.nan), rec.get("fg_ratio", np.nan),
                 rec.get("band_peak", np.nan), rec.get("band_ratio", np.nan)))
    out["texture"] = tex
    print()
    for cls in ("occ", "occ_flat", "ctl"):
        for key in ("bg", "band"):
            v = [r[key + "_ratio"] for r in tex if r["cls"] == cls and key + "_ratio" in r]
            p = [r[key + "_peak"] for r in tex if r["cls"] == cls and key + "_peak" in r]
            print("  %-9s %-5s  peak/floor ratio median %5.2f (range %5.2f-%5.2f)   "
                  "peak response median %7.2f" % (cls, key, np.median(v), min(v), max(v),
                                                  np.median(p)))

    print()
    print("=" * 78)
    print("B  replicate agreement at MATCHED flag rate -- bee-2 vs bee-3, same scene")
    print("=" * 78)
    rep = []
    for stack, name, cls, y0, y1, x0, x1 in [c for c in CELLS if c[0] == "bee-3"]:
        a, b = A.load("bee-3", name), A.load("bee-2", name)
        na = A.load("bee-3", name, A.NUL)
        if a is None or b is None or na is None:
            continue
        ra, rb = A.detect(a["F"], a["S"]), A.detect(b["F"], b["S"])
        nu = A.detect(na["F"], na["S"])
        band = a["lab"] == 0
        zst = float(np.percentile(nu["z"][band], 99))
        q = float(np.mean(ra["z"][band] > zst))         # bee-3's own hit rate
        za, zb = ra["z"][band], rb["z"][band]
        fa = za > np.quantile(za, 1 - q)
        fb = zb > np.quantile(zb, 1 - q)
        k, po, pe = kappa(fa, fb)
        # separation agreement among pixels flagged in BOTH
        both = fa & fb
        sa = np.abs(ra["k2"][band].astype(float) - ra["k1"][band])[both]
        sb = np.abs(rb["k2"][band].astype(float) - rb["k1"][band])[both]
        r = float(np.corrcoef(sa, sb)[0, 1]) if both.sum() > 50 else float("nan")
        k2a = ra["k2"][band].astype(float)[both]
        k2b = rb["k2"][band].astype(float)[both]
        agree6 = float(np.mean(np.abs(k2a - k2b) <= 6))
        rec = dict(cell=name, cls=cls, q=q, kappa=k, p_obs=po, p_chance=pe,
                   sep_corr=r, k2_agree6=agree6, n_both=int(both.sum()),
                   npx=int(band.sum()))
        rep.append(rec)
        print("  %-18s %-8s  flag rate %5.1f%% in both | agree %5.1f%% vs chance %5.1f%% "
              "| kappa %+6.3f | among agreed: corr(sep) %+.3f, k2 within 6 frames %5.1f%%"
              % (name, cls, 100 * q, 100 * po, 100 * pe, k, r, 100 * agree6), flush=True)
    out["replicate_matched"] = rep
    ks = [r["kappa"] for r in rep]
    print("\n  Cohen's kappa across %d cells: median %+.3f  range %+.3f to %+.3f"
          % (len(ks), np.median(ks), min(ks), max(ks)))
    print("  (kappa 0 = the flag agrees with itself no better than chance;")
    print("   1 = perfect agreement. The two captures are the same scene.)")

    print()
    print("=" * 78)
    print("C  distance profile by class -- side-lobe law vs fixed depth step")
    print("=" * 78)
    with open(os.path.join(DATA, "16-distance.json"), encoding="utf-8") as fh:
        dd = json.load(fh)
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r for r in dd if r["cls"] == cls]
        sl = [r["slope_frames_per_px"] for r in v
              if r.get("slope_frames_per_px") is not None
              and r.get("slope_frames_per_px") == r.get("slope_frames_per_px")]
        rg = [r["sep_range"] for r in v if "sep_range" in r]
        print("  %-9s  n=%2d  Theil-Sen slope of |k2-k1| on distance: median %+6.3f fr/px"
              "  (range %+.3f to %+.3f)   spread of sep across distance bins: median %5.1f fr"
              % (cls, len(v), np.median(sl), min(sl), max(sl), np.median(rg)))

    print()
    print("=" * 78)
    print("D  separation vs the focus-step geometry")
    print("=" * 78)
    geo = []
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        d = A.load(stack, name)
        if d is None:
            continue
        F, S, lab = d["F"], d["S"], d["lab"]
        band = lab == 0
        r = A.detect(F, S)
        w = A.peak_width(F[:, band], r["k1"][band])
        sep = np.abs(r["k2"][band].astype(float) - r["k1"][band])
        kbg = float(np.median(r["k1"][lab == 2])) if (lab == 2).any() else np.nan
        kfg = float(np.median(r["k1"][lab == 1])) if (lab == 1).any() else np.nan
        rec = dict(cell=name, cls=cls, n=int(F.shape[0]),
                   fwhm=float(np.median(w)), sep=float(np.median(sep)),
                   step=float(abs(kfg - kbg)),
                   sep_over_fwhm=float(np.median(sep) / max(np.median(w), 1e-9)))
        geo.append(rec)
        print("  %-18s %-8s n=%3d  primary-peak FWHM %5.1f fr | median |k2-k1| %5.1f fr"
              " (%4.1f x FWHM) | reference depth step |k_fg-k_bg| %5.1f fr"
              % (name, cls, rec["n"], rec["fwhm"], rec["sep"], rec["sep_over_fwhm"],
                 rec["step"]))
    out["geometry"] = geo
    print()
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r for r in geo if r["cls"] == cls]
        print("  %-9s  FWHM median %5.1f fr   |k2-k1| median %5.1f fr   ratio median %4.1f"
              % (cls, np.median([r["fwhm"] for r in v]),
                 np.median([r["sep"] for r in v]),
                 np.median([r["sep_over_fwhm"] for r in v])))

    with open(os.path.join(DATA, "20-audit.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote data/20-audit.json")
