"""M120b step 18 -- REDO the operator price at the SHIPPED gate.

M120b section 17 toggled the regulariser at gate 0, which merge.rs:3027 labels a
negative control. DEFAULT_GATE = 4.0 (merge.rs:298). At gate 4 the merge averages
the admitted SET, so the regularised field decides admission rather than just the
argmax, and the regulariser could matter more, or less, than it did at gate 0.
Re-priced here, and validated against the real Rust render.

Arms, all at gate 4 unless stated:
  C4   window ON,  reg ON            shipped
  B4   window ON,  reg OFF           literal toggle, gate constant unchanged
  B4n  window ON,  reg OFF           gate RESCALED to match C4's mean n_eff.
                                     This is the fair arm: the regulariser also
                                     de-noises the response, which changes how
                                     many frames clear a fixed threshold, so a
                                     literal toggle confounds "spatial smoothing"
                                     with "admission width". B4n isolates the
                                     spatial part.
  A4   window OFF, reg OFF
"""
import json
import numpy as np
import tifffile
from scipy import ndimage as ndi
from pathlib import Path
from PIL import Image

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
M93 = Path(r"C:\dev\strehl-out\M93-out")
OUT = Path(r"C:\dev\strehl-out\M120")
WINDOW_RADIUS, REG_R = 13, 8
DN_PER_E, READ_E, BLACK = 0.229, 1.47, 100.0
FOCUS_NOISE_SD = 0.015214
UNIT = np.sqrt(2.0) * FOCUS_NOISE_SD
GATE = 4.0
BOX = (1178, 1922, 278, 1422)
Y0, Y1, X0, X1 = 476, 604, 442, 570      # M120's registered background ROI, box coords


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


def responses(luma, k, pad_slice, reg):
    f = np.array(luma[k][pad_slice], np.float32)
    r = box(grad_mag(f), WINDOW_RADIUS) / sigma_luma(f)
    return (box(r, REG_R) if reg else r), f


def merge_at_gate(luma, K, sl, reg, window, gate):
    """Two passes: winner response, then equal-weight mean of the admitted set."""
    best = None
    for k in range(K):
        f = np.array(luma[k][sl], np.float32)
        g = grad_mag(f) / sigma_luma(f) if not window else \
            box(grad_mag(f), WINDOW_RADIUS) / sigma_luma(f)
        r = box(g, REG_R) if reg else g
        best = r if best is None else np.maximum(best, r)
    thr = best - gate * UNIT
    acc = np.zeros_like(best)
    cnt = np.zeros_like(best)
    for k in range(K):
        f = np.array(luma[k][sl], np.float32)
        g = grad_mag(f) / sigma_luma(f) if not window else \
            box(grad_mag(f), WINDOW_RADIUS) / sigma_luma(f)
        r = box(g, REG_R) if reg else g
        m = r >= thr
        acc += np.where(m, f, 0.0)
        cnt += m
    return acc / np.maximum(cnt, 1), cnt


def main():
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    K, H, W = luma.shape
    pad = WINDOW_RADIUS + REG_R + 4
    sl = (slice(Y0 - pad, Y1 + pad), slice(X0 - pad, X1 + pad))
    core = (slice(pad, -pad), slice(pad, -pad))

    roi_cube = np.array(luma[:, Y0:Y1, X0:X1], np.float32)
    den = max(contrast(roi_cube[k]) for k in range(K))
    means = roi_cube.mean(axis=(1, 2))
    qbound = float(means.max() / means.min())

    # ---- validate the gate-4 reconstruction against the real Rust render ----
    real = tifffile.imread(M93 / "armM4-gate4-binlin.tif")
    assert real.dtype == np.uint16, real.dtype
    real_roi = real[BOX[0] + Y0:BOX[0] + Y1, BOX[2] + X0:BOX[2] + X1, 1].astype(np.float32)
    c4, n4 = merge_at_gate(luma, K, sl, reg=True, window=True, gate=GATE)
    c4, n4 = c4[core], n4[core]
    gain = float(np.median(real_roi / c4))
    resid = float(np.abs(real_roi - gain * c4).mean() / real_roi.mean())
    ncc = float(np.corrcoef(real_roi.ravel(), c4.ravel())[0, 1])
    print("VALIDATION of the gate-4 reconstruction against armM4-gate4-binlin.tif")
    print(f"  gain {gain:.4f}  NCC {ncc:.6f}  mean |resid| {100*resid:.3f}% of level")
    print(f"  mean n_eff {n4.mean():.1f} of {K} frames")
    if ncc < 0.99:
        print("  *** reconstruction does not match; downstream arms are not trustworthy")

    arms = {}
    arms["C4  window ON  reg ON  gate 4 (SHIPPED)"] = (c4, n4)
    b4, nb4 = merge_at_gate(luma, K, sl, reg=False, window=True, gate=GATE)
    arms["B4  window ON  reg OFF gate 4"] = (b4[core], nb4[core])
    a4, na4 = merge_at_gate(luma, K, sl, reg=False, window=False, gate=GATE)
    arms["A4  window OFF reg OFF gate 4"] = (a4[core], na4[core])

    # matched-admission arm: find the gate that reproduces C4's mean n_eff
    target = float(n4.mean())
    lo, hi = 0.05, 40.0
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        _, nn = merge_at_gate(luma, K, sl, reg=False, window=True, gate=mid)
        if nn[core].mean() < target:
            lo = mid
        else:
            hi = mid
    b4n, nb4n = merge_at_gate(luma, K, sl, reg=False, window=True, gate=mid)
    arms[f"B4n window ON  reg OFF gate {mid:.2f} (n_eff-matched)"] = (b4n[core], nb4n[core])

    print(f"\nROI = box rows {Y0}:{Y1} cols {X0}:{X1} | denominator {den:.6f} | "
          f"Q_bound {qbound:.3f}")
    print(f"\n{'arm':46}{'mean n_eff':>12}{'Q':>9}{'vs bound':>11}{'verdict':>12}")
    res = {}
    for nm, (im, nn) in arms.items():
        q = contrast(im) / den
        res[nm] = dict(Q=float(q), n_eff=float(nn.mean()), passes=bool(q <= qbound))
        print(f"{nm:46}{nn.mean():>12.1f}{q:>9.3f}{q/qbound:>10.2f}x"
              f"{'  ok' if q <= qbound else '  VIOLATES':>12}")
    plain = roi_cube.mean(axis=0)
    print(f"{'NULL-1 plain mean (all 299, equal weight)':46}{K:>12}"
          f"{contrast(plain)/den:>9.3f}")
    print(f"{'NULL-2 single input frame':46}{1:>12}{contrast(roi_cube[K//2])/den:>9.3f}")

    qc = res["C4  window ON  reg ON  gate 4 (SHIPPED)"]["Q"]
    qb = res["B4  window ON  reg OFF gate 4"]["Q"]
    qbn = [v for k, v in res.items() if k.startswith("B4n")][0]["Q"]
    print(f"\nTHE REGULARISER'S PRICE AT THE SHIPPED GATE")
    print(f"  shipped gate 4                       Q = {qc:.3f}")
    print(f"  regulariser OFF, gate 4 unchanged    Q = {qb:.3f}  ({100*(qb-qc)/qc:+.1f}%)")
    print(f"  regulariser OFF, admission matched   Q = {qbn:.3f}  ({100*(qbn-qc)/qc:+.1f}%)")
    print(f"  bound                                Q = {qbound:.3f}")
    print(f"\n  for comparison, M120b s.17 measured the same toggle at gate 0: "
          f"7.166 -> 6.902 ({-3.7:+.1f}%)")

    json.dump({"validation": dict(gain=gain, ncc=ncc, resid=resid),
               "q_bound": qbound, "den": den, "arms": res},
              open("m4_gate4_price.json", "w"), indent=1)

    lo_, hi_ = np.percentile(arms["C4  window ON  reg ON  gate 4 (SHIPPED)"][0], [1, 99])
    for nm, (im, _) in arms.items():
        v = np.clip((im - lo_) / (hi_ - lo_), 0, 1)
        Image.fromarray((v * 255).astype(np.uint8)).resize((512, 512), Image.NEAREST) \
            .save(OUT / f"M4-gate4-{nm.split()[0]}.png")
    print(f"\nwrote M4-gate4-*.png (common stretch {lo_:.0f}-{hi_:.0f})")


if __name__ == "__main__":
    main()
