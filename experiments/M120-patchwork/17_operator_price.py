"""M120b step 17 -- price each operator against the VISIBLE defect.

Step 15 measured blob geometry in the index field. That is not yet a statement
about the render. This gathers the actual merged luma under each arm's index
field and applies M120's shipped patchwork metric

    C(I) = || gaussian(I,2) - gaussian(I,8) ||_ROI / mean(I)_ROI
    Q    = C(merge) / max_k C(f_k)          (unit-free; Q<=Q_bound is the invariant)

so each operator's contribution to the artifact ORCH can see is priced in the
same units as fact 1617.

This is NOT the soft-gate A/B -- that is M116's. This toggles the focus WINDOW
and the REGULARISER, which nothing else is touching.
"""
import json
import numpy as np
from scipy import ndimage as ndi
from pathlib import Path
from PIL import Image

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
WINDOW_RADIUS, REG_R = 13, 8
DN_PER_E, READ_E, BLACK = 0.229, 1.47, 100.0


def sigma_luma(dn):
    e = np.maximum((dn - BLACK) / DN_PER_E, 0.0)
    return (DN_PER_E * np.sqrt(e + READ_E * READ_E)) / np.sqrt(2.0)


def box(a, r):
    return ndi.uniform_filter(a, size=2 * r + 1, mode="nearest")


def grad_mag(a):
    return np.hypot(ndi.sobel(a, axis=1, mode="nearest"),
                    ndi.sobel(a, axis=0, mode="nearest"))


def contrast(a):
    a = np.asarray(a, np.float32)
    bp = ndi.gaussian_filter(a, 2.0) - ndi.gaussian_filter(a, 8.0)
    return float(np.sqrt((bp * bp).mean()) / a.mean())


def main():
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    argbest = np.load(C / "bee3-leg-argbest.npy")
    bestiB = np.load(OUT / "m1_besti_B.npy")
    K, H, W = luma.shape

    # M120's established pure-background ROI, M87-box coords (roi_final.json)
    Y0, Y1, X0, X1 = 476, 604, 442, 570
    print(f"ROI = M87-box rows {Y0}:{Y1} cols {X0}:{X1}  (M120's registered background ROI)")

    # rebuild arms A and A' index fields over the ROI only (cheap)
    pad = WINDOW_RADIUS + REG_R + 4
    ys, ye, xs, xe = Y0 - pad, Y1 + pad, X0 - pad, X1 + pad
    bA = np.full((ye - ys, xe - xs), -np.inf, np.float32)
    iA = np.zeros((ye - ys, xe - xs), np.int32)
    bAp, iAp = bA.copy(), iA.copy()
    for k in range(K):
        f = np.array(luma[k, ys:ye, xs:xe], np.float32)
        rA = grad_mag(f) / sigma_luma(f)
        for r, (bb, ii) in ((rA, (bA, iA)), (box(rA, REG_R), (bAp, iAp))):
            h = r > bb
            bb[h] = r[h]
            ii[h] = k
    idx = {
        "A  window OFF reg OFF": iA[pad:-pad, pad:-pad],
        "A' window OFF reg ON": iAp[pad:-pad, pad:-pad],
        "B  window ON  reg OFF": bestiB[Y0:Y1, X0:X1],
        "C  window ON  reg ON (SHIPPED)": argbest[Y0:Y1, X0:X1],
    }

    roi_cube = np.array(luma[:, Y0:Y1, X0:X1], np.float32)
    den = max(contrast(roi_cube[k]) for k in range(K))
    means = roi_cube.mean(axis=(1, 2))
    qbound = float(means.max() / means.min())
    print(f"denominator max_k C(f_k) over all {K} frames = {den:.6f}")
    print(f"Q_bound for spatially constant convex weights  = {qbound:.3f}")

    res, imgs = {}, {}
    print(f"\n{'arm':34}{'C(merge)':>11}{'Q':>9}{'vs bound':>11}{'verdict':>12}")
    for nm, ix in idx.items():
        sel = np.take_along_axis(roi_cube, ix[None].astype(np.intp), 0)[0]
        c = contrast(sel)
        q = c / den
        res[nm] = dict(contrast=c, Q=float(q), passes=bool(q <= qbound))
        imgs[nm] = sel
        print(f"{nm:34}{c:>11.6f}{q:>9.3f}{q/qbound:>10.2f}x"
              f"{'  ok' if q <= qbound else '  VIOLATES':>12}")

    # controls, same ROI, same metric
    plain = roi_cube.mean(axis=0)
    res["NULL-1 plain mean"] = dict(contrast=contrast(plain), Q=float(contrast(plain) / den))
    one = roi_cube[K // 2]
    res["NULL-2 single frame"] = dict(contrast=contrast(one), Q=float(contrast(one) / den))
    print(f"{'NULL-1 plain mean':34}{res['NULL-1 plain mean']['contrast']:>11.6f}"
          f"{res['NULL-1 plain mean']['Q']:>9.3f}")
    print(f"{'NULL-2 single input frame':34}{res['NULL-2 single frame']['contrast']:>11.6f}"
          f"{res['NULL-2 single frame']['Q']:>9.3f}")

    qc = res["C  window ON  reg ON (SHIPPED)"]["Q"]
    qb = res["B  window ON  reg OFF"]["Q"]
    qa = res["A  window OFF reg OFF"]["Q"]
    qap = res["A' window OFF reg ON"]["Q"]
    print(f"\nHOW MUCH OF THE VISIBLE DEFECT DOES EACH OPERATOR OWN?")
    print(f"  shipped                          Q = {qc:.3f}")
    print(f"  turn the REGULARISER off         Q = {qb:.3f}   ({100*(qb-qc)/qc:+.1f}%)")
    print(f"  turn the WINDOW off              Q = {qap:.3f}   ({100*(qap-qc)/qc:+.1f}%)")
    print(f"  turn BOTH off                    Q = {qa:.3f}   ({100*(qa-qc)/qc:+.1f}%)")
    print(f"  invariant bound                  Q = {qbound:.3f}")
    for nm, q in (("regulariser off", qb), ("window off", qap), ("both off", qa)):
        print(f"    {nm:18s} -> {'STILL VIOLATES' if q > qbound else 'passes'} the invariant")

    json.dump({"roi": [Y0, Y1, X0, X1], "den": den, "q_bound": qbound, "arms": res},
              open("m3_operator_price.json", "w"), indent=1)

    lo, hi = np.percentile(imgs["C  window ON  reg ON (SHIPPED)"], [1, 99])
    for nm, im in imgs.items():
        v = np.clip((im - lo) / (hi - lo), 0, 1)
        tag = nm.split()[0].replace("'", "p")
        Image.fromarray((v * 255).astype(np.uint8)).resize((512, 512), Image.NEAREST) \
            .save(OUT / f"M3-render-{tag}.png")
    v = np.clip((one - lo) / (hi - lo), 0, 1)
    Image.fromarray((v * 255).astype(np.uint8)).resize((512, 512), Image.NEAREST) \
        .save(OUT / "M3-render-NULL2-single-frame.png")
    print(f"\nwrote M3-render-*.png to {OUT} (common stretch {lo:.0f}-{hi:.0f})")


if __name__ == "__main__":
    main()
