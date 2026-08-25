"""M120b step 16 -- P2, P3, P4 and the B-vs-C agreement.

P2  Separate the two quantities ORCH's wording conflates:
      response LEVEL (the data term)  -- ORCH says it vanishes into the noise
      MARGIN (winner - runner-up)     -- M120 says this is what is small
    Measured in background and in subject, in units of the pipeline's own noise.

P3  Regress blob size on local margin.
      ORCH predicts rho < -0.3, monotone across deciles (less data => bigger blobs).
      M120b predicts |rho| < 0.2, size pinned near the window scale.

P4  Subject-region control, with the confound from step 15 FIXED: components are
    truncated by mask shape, and the subject mask was 1.6% of the plane against
    the background's 40.8%, which biases the subject's sizes DOWN for free.
    Fixed by comparing equal-area compact rectangles.

Also: how much of the shipped index field survives turning the regulariser off?
"""
import json
import numpy as np
from scipy import ndimage as ndi, stats
from skimage import measure
from pathlib import Path

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")

WINDOW_RADIUS, REG_R = 13, 8
DN_PER_E, READ_E, BLACK = 0.229, 1.47, 100.0
FOCUS_NOISE_SD = 0.015214          # merge.rs:187
UNIT = np.sqrt(2.0) * FOCUS_NOISE_SD


def sigma_luma(dn):
    e = np.maximum((dn - BLACK) / DN_PER_E, 0.0)
    return (DN_PER_E * np.sqrt(e + READ_E * READ_E)) / np.sqrt(2.0)


def box(a, r):
    return ndi.uniform_filter(a, size=2 * r + 1, mode="nearest")


def grad_mag(a):
    return np.hypot(ndi.sobel(a, axis=1, mode="nearest"),
                    ndi.sobel(a, axis=0, mode="nearest"))


def comp_area_per_pixel(idx):
    lab = measure.label(idx, connectivity=1)
    areas = np.bincount(lab.ravel())
    return areas[lab]


def main():
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    argbest = np.load(C / "bee3-leg-argbest.npy")
    bg = np.load(OUT / "m1_bg_mask.npy")
    subj = np.load(OUT / "m1_subj_mask.npy")
    bestiB = np.load(OUT / "m1_besti_B.npy")
    K, H, W = luma.shape
    res = {}

    # ---- B vs C: does turning the regulariser off change WHICH frame wins? --
    same = float(np.mean(bestiB[bg] == argbest[bg]))
    near = float(np.mean(np.abs(bestiB[bg].astype(int) - argbest[bg].astype(int)) <= 3))
    # and after a light clean-up of B's speckle, to isolate "macro-layout"
    Bmed = ndi.median_filter(bestiB, size=5)
    same_med = float(np.mean(Bmed[bg] == argbest[bg]))
    near_med = float(np.mean(np.abs(Bmed[bg].astype(int) - argbest[bg].astype(int)) <= 3))
    res["B_vs_C"] = dict(exact=same, within3=near, exact_med5=same_med, within3_med5=near_med)
    print("Does removing the regulariser change WHICH frame is elected?")
    print(f"  arm B vs shipped, background: exact {100*same:.1f}%  within +-3 frames {100*near:.1f}%")
    print(f"  arm B after a 5px median     : exact {100*same_med:.1f}%  within +-3 frames {100*near_med:.1f}%")

    # ---- top-2 of the shipped response, for margin --------------------------
    best1 = np.full((H, W), -np.inf, np.float32)
    best2 = np.full((H, W), -np.inf, np.float32)
    for k in range(K):
        f = np.array(luma[k], np.float32)
        r = box(box(grad_mag(f), WINDOW_RADIUS) / sigma_luma(f), REG_R)
        hi = r > best1
        best2 = np.where(hi, best1, np.maximum(best2, r))
        best1 = np.where(hi, r, best1)
        if k % 100 == 0:
            print(f"  margin pass frame {k}/{K}", flush=True)
    margin = (best1 - best2) / UNIT           # in gate units
    resp = best1 / FOCUS_NOISE_SD             # winner level, in noise sigmas
    np.save(OUT / "m1_margin.npy", margin)
    np.save(OUT / "m1_resp.npy", best1)

    # ---- P2 -----------------------------------------------------------------
    print("\nP2  response level vs margin, in the pipeline's own noise units")
    print(f"{'region':12}{'winner resp':>14}{'/noise sd':>12}{'margin':>12}{'gate units':>12}")
    for nm, m in (("background", bg), ("subject", subj)):
        r = dict(resp_med=float(np.median(best1[m])),
                 resp_sigmas=float(np.median(resp[m])),
                 margin_med=float(np.median((best1 - best2)[m])),
                 margin_units=float(np.median(margin[m])),
                 frac_margin_below_1=float(np.mean(margin[m] < 1.0)),
                 frac_resp_below_3=float(np.mean(resp[m] < 3.0)))
        res[f"P2_{nm}"] = r
        print(f"{nm:12}{r['resp_med']:>14.4f}{r['resp_sigmas']:>12.1f}"
              f"{r['margin_med']:>12.5f}{r['margin_units']:>12.3f}")
    print(f"  background: margin < 1 gate unit on {100*res['P2_background']['frac_margin_below_1']:.1f}% "
          f"of px;  winner response below 3 noise sd on "
          f"{100*res['P2_background']['frac_resp_below_3']:.2f}%")
    print(f"  subject   : margin < 1 gate unit on {100*res['P2_subject']['frac_margin_below_1']:.1f}% of px")

    # ---- P3 -----------------------------------------------------------------
    area_px = comp_area_per_pixel(argbest)
    a, mg = area_px[bg].astype(np.float64), margin[bg].astype(np.float64)
    rho = stats.spearmanr(mg, a)
    res["P3"] = dict(spearman=float(rho.statistic), p=float(rho.pvalue), n=int(a.size))
    print(f"\nP3  blob size vs local margin over background (n={a.size:,})")
    print(f"  Spearman rho = {rho.statistic:+.4f}  (p = {rho.pvalue:.3g})")
    q = np.quantile(mg, np.linspace(0, 1, 11))
    print(f"  {'margin decile':>14}{'margin':>10}{'median area':>13}{'eq diam':>10}")
    dec = []
    for i in range(10):
        s = (mg >= q[i]) & (mg <= q[i + 1])
        ma, mm = float(np.median(a[s])), float(np.median(mg[s]))
        dec.append(dict(decile=i + 1, margin=mm, median_area=ma,
                        eq_diam=float(np.sqrt(4 * ma / np.pi))))
        print(f"{i+1:>14}{mm:>10.3f}{ma:>13.0f}{np.sqrt(4*ma/np.pi):>10.1f}")
    res["P3_deciles"] = dec
    lo, hi = dec[0]["eq_diam"], dec[-1]["eq_diam"]
    print(f"  lowest-margin decile {lo:.1f} px vs highest-margin decile {hi:.1f} px")
    v = ("ORCH CONFIRMED" if rho.statistic < -0.3 else
         "ORCH REFUTED (M120b predicted |rho|<0.2)" if abs(rho.statistic) < 0.2 else "PARTIAL")
    print(f"  PRE-REGISTERED VERDICT: {v}")

    # ---- P4, with matched geometry -----------------------------------------
    print("\nP4  subject control with EQUAL-AREA COMPACT RECTANGLES (confound fixed)")
    def best_rect(mask, side):
        ii = np.cumsum(np.cumsum(mask.astype(np.int32), 0), 1)
        best, at = -1, None
        for y in range(0, H - side, 8):
            for x in range(0, W - side, 8):
                s = (ii[y + side, x + side] - ii[y, x + side]
                     - ii[y + side, x] + ii[y, x])
                if s > best:
                    best, at = s, (y, x)
        return at, best / (side * side)
    for side in (96, 128):
        (by, bx), bfill = best_rect(bg, side)
        (sy, sx), sfill = best_rect(subj, side)
        rows = []
        for nm, (y, x), fill in (("background", (by, bx), bfill), ("subject", (sy, sx), sfill)):
            sub = argbest[y:y + side, x:x + side]
            lab = measure.label(sub, connectivity=1)
            ar = np.bincount(lab.ravel())[1:]
            ar = ar[ar > 0]
            aw = float((ar.astype(np.float64) ** 2).sum() / ar.sum())
            rows.append(dict(region=nm, side=side, at=[int(y), int(x)], fill=float(fill),
                             n=int(ar.size), aw_area=aw,
                             eq_diam=float(np.sqrt(4 * aw / np.pi)),
                             margin=float(np.median(margin[y:y+side, x:x+side]))))
            print(f"  {side}px {nm:11} at ({y:4d},{x:4d}) mask-fill {100*fill:5.1f}%  "
                  f"#comp {ar.size:5d}  eq diam {np.sqrt(4*aw/np.pi):6.1f} px  "
                  f"median margin {rows[-1]['margin']:7.3f} units")
        res[f"P4_{side}"] = rows
        r = rows[0]["eq_diam"] / rows[1]["eq_diam"]
        print(f"    background/subject blob-diameter ratio = {r:.2f}x")

    json.dump(res, open("m2_p234.json", "w"), indent=1)
    print("\nwrote m2_p234.json")


if __name__ == "__main__":
    main()
