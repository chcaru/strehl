"""M120b step 19 -- gate-4 operator price, done on the PIPELINE'S OWN field.

Step 18 refused its own output and was right to: the gate threshold is an
ABSOLUTE offset (gate * sqrt(2) * FOCUS_NOISE_SD) on the normalised response, so
it is only meaningful on a response of the pipeline's scale. Step 18 rebuilt the
response from luma with scipy's Sobel and got a scale ~12.8x too large, which
made gate 4 admit 3.4 frames where the pipeline admits ~167. NCC against the real
render was 0.729 and the run aborted.

Fixed here:
  * arm C4 gates on the CACHED regularised field `bee3-leg-field.npy`, which is
    the pipeline's own output (step 14: argmax(field) == shipped argbest, 100.00%).
  * the reg-OFF arm is calibrated onto that scale by alpha = median(field / my
    regularised replication). A box mean does not change the mean scale, so the
    same alpha carries the pre-regulariser field onto the pipeline's units.
  * the validation gate against armM4-gate4-binlin.tif is kept and is fatal.
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
Y0, Y1, X0, X1 = 476, 604, 442, 570
PAD = WINDOW_RADIUS + REG_R + 4


def sigma_luma(dn):
    e = np.maximum((dn - BLACK) / DN_PER_E, 0.0)
    return (DN_PER_E * np.sqrt(e + READ_E * READ_E)) / np.sqrt(2.0)


def box(a, r):
    return ndi.uniform_filter(a, size=2 * r + 1, mode="nearest")


def grad(a):
    return np.hypot(ndi.sobel(a, axis=1, mode="nearest"),
                    ndi.sobel(a, axis=0, mode="nearest"))


def contrast(a):
    a = np.asarray(a, np.float32)
    bp = ndi.gaussian_filter(a, 2.0) - ndi.gaussian_filter(a, 8.0)
    return float(np.sqrt((bp * bp).mean()) / a.mean())


def gate_merge(resp, cube, gate):
    """Equal-weight (top-hat) mean of every frame within `gate` units of the winner."""
    best = resp.max(axis=0)
    adm = resp >= (best - gate * UNIT)
    n = adm.sum(axis=0).astype(np.float32)
    return (np.where(adm, cube, 0.0).sum(axis=0) / np.maximum(n, 1)), n


def main():
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    fieldm = np.load(C / "bee3-leg-field.npy", mmap_mode="r")
    K = luma.shape[0]
    ys, ye, xs, xe = Y0 - PAD, Y1 + PAD, X0 - PAD, X1 + PAD

    cube = np.array(luma[:, Y0:Y1, X0:X1], np.float32)
    field_c = np.array(fieldm[:, Y0:Y1, X0:X1], np.float32)     # pipeline, regularised
    den = max(contrast(cube[k]) for k in range(K))
    m = cube.mean(axis=(1, 2))
    qbound = float(m.max() / m.min())

    # ---- my replication, on the pad slice, for the reg-OFF arm --------------
    pre = np.empty((K, ye - ys, xe - xs), np.float32)
    for k in range(K):
        f = np.array(luma[k, ys:ye, xs:xe], np.float32)
        pre[k] = box(grad(f), WINDOW_RADIUS) / sigma_luma(f)
    myreg = np.empty_like(pre)
    for k in range(K):
        myreg[k] = box(pre[k], REG_R)
    core = (slice(PAD, PAD + (Y1 - Y0)), slice(PAD, PAD + (X1 - X0)))
    alpha = float(np.median(field_c / myreg[:, core[0], core[1]]))
    corr = float(np.corrcoef(field_c.ravel(), myreg[:, core[0], core[1]].ravel())[0, 1])
    print(f"scale calibration of the replication onto the pipeline's field")
    print(f"  alpha = {alpha:.6f}  (1/alpha = {1/alpha:.2f})   corr = {corr:.6f}")
    pre_cal = pre[:, core[0], core[1]] * alpha

    # ---- validation, fatal -------------------------------------------------
    c4, n4 = gate_merge(field_c, cube, GATE)
    real = tifffile.imread(M93 / "armM4-gate4-binlin.tif")
    assert real.dtype == np.uint16, real.dtype
    rroi = real[BOX[0] + Y0:BOX[0] + Y1, BOX[2] + X0:BOX[2] + X1, 1].astype(np.float32)
    gain = float(np.median(rroi / c4))
    ncc = float(np.corrcoef(rroi.ravel(), c4.ravel())[0, 1])
    resid = float(np.abs(rroi - gain * c4).mean() / rroi.mean())
    print(f"\nVALIDATION vs armM4-gate4-binlin.tif: gain {gain:.4f}  NCC {ncc:.6f}  "
          f"resid {100*resid:.3f}%  mean n_eff {n4.mean():.1f}/{K}")
    if ncc < 0.99:
        raise SystemExit("reconstruction does not match the shipped render -- refusing to report")
    print("  PASS")

    # ---- arms --------------------------------------------------------------
    arms = {"C4  window ON  reg ON   gate 4 (SHIPPED)": (c4, n4)}
    b4, nb4 = gate_merge(pre_cal, cube, GATE)
    arms["B4  window ON  reg OFF  gate 4"] = (b4, nb4)
    target = float(n4.mean())
    lo, hi = 0.05, 200.0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        nn = (pre_cal >= (pre_cal.max(axis=0) - mid * UNIT)).sum(axis=0).mean()
        if nn < target:
            lo = mid
        else:
            hi = mid
    b4n, nb4n = gate_merge(pre_cal, cube, mid)
    arms[f"B4n window ON  reg OFF  gate {mid:.2f} (n_eff matched)"] = (b4n, nb4n)

    print(f"\nROI box rows {Y0}:{Y1} cols {X0}:{X1} | denom {den:.6f} | Q_bound {qbound:.3f}")
    print(f"\n{'arm':48}{'n_eff':>9}{'Q':>9}{'vs bound':>11}{'verdict':>12}")
    res = {}
    for nm, (im, nn) in arms.items():
        q = contrast(im) / den
        res[nm] = dict(Q=float(q), n_eff=float(nn.mean()), passes=bool(q <= qbound))
        print(f"{nm:48}{nn.mean():>9.1f}{q:>9.3f}{q/qbound:>10.2f}x"
              f"{'  ok' if q <= qbound else '  VIOLATES':>12}")
    for nm, im, nn in (("NULL-1 plain mean", cube.mean(axis=0), K),
                       ("NULL-2 single input frame", cube[K // 2], 1)):
        res[nm] = dict(Q=float(contrast(im) / den), n_eff=float(nn))
        print(f"{nm:48}{nn:>9}{contrast(im)/den:>9.3f}")

    qc = res["C4  window ON  reg ON   gate 4 (SHIPPED)"]["Q"]
    qb = res["B4  window ON  reg OFF  gate 4"]["Q"]
    qbn = [v for k, v in res.items() if k.startswith("B4n")][0]["Q"]
    print(f"\nTHE REGULARISER'S PRICE AT THE SHIPPED GATE (gate 4, DEFAULT_GATE)")
    print(f"  shipped                              Q = {qc:.3f}")
    print(f"  regulariser OFF, gate constant kept  Q = {qb:.3f}   ({100*(qb-qc)/qc:+.1f}%)")
    print(f"  regulariser OFF, admission matched   Q = {qbn:.3f}   ({100*(qbn-qc)/qc:+.1f}%)")
    print(f"  invariant bound                      Q = {qbound:.3f}")
    print(f"\n  gate 0 (negative control) for reference: 7.166 -> 6.902 (-3.7%)")

    json.dump({"alpha": alpha, "corr": corr, "gain": gain, "ncc": ncc, "resid": resid,
               "q_bound": qbound, "den": den, "arms": res},
              open("m5_gate4_price.json", "w"), indent=1)
    np.save(OUT / "m5_n_eff_gate4.npy", n4)

    lo_, hi_ = np.percentile(c4, [1, 99])
    for nm, (im, _) in arms.items():
        v = np.clip((im - lo_) / (hi_ - lo_), 0, 1)
        Image.fromarray((v * 255).astype(np.uint8)).resize((512, 512), Image.NEAREST) \
            .save(OUT / f"M5-gate4-{nm.split()[0]}.png")
    print(f"\nwrote M5-gate4-*.png (common stretch {lo_:.0f}-{hi_:.0f})")


if __name__ == "__main__":
    main()
