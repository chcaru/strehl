"""M118 arm 4 -- is the end-to-end band gain a measurement, or a kernel datasheet?

M113 section 11 found that its SYNTHETIC +0.1428 dex lands within 0.0036 dex of a
closed form computed with NO IMAGE AT ALL, and concluded the figure is "to 97.5%,
a restatement of the two kernels' transfer functions over two fixed bands."

That test has never been applied to the END-TO-END number -- the one measured
through the shipped 299-frame merge, which is the only number anyone would cite
to justify moving the default. This script applies it.

The prediction uses the weights transcribed from `crates/strehl-core/src/align.rs`
at the pinned SHA, and no pixel from any capture.

A gather at fractional phase `f` computes  y = sum_k w_k(f) * x[n + o_k].
For x[n] = exp(2*pi*i*v*n) the exact answer is exp(2*pi*i*v*(n+f)), so the
complex gain relative to truth is

    H(v, f) = sum_k w_k(f) * exp(2*pi*i*v*(o_k - f)).

Power gain is |H|^2, averaged over phase uniform on [0,1). The gather is
separable, so the 2-D gain is the outer product, evaluated on the SAME 128-point
FFT grid and the SAME radial band mask the measurement uses.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent.parent
ARMS = ["nearest", "bilinear", "catmull-rom", "lanczos2", "lanczos3"]
BASELINE = "catmull-rom"
TILE = 128
BAND = (0.30, 0.48)
NPHASE = 512


def sinc(x):
    x = np.asarray(x, dtype=np.float64)
    out = np.ones_like(x)
    m = np.abs(x) >= 1e-12
    p = np.pi * x[m]
    out[m] = np.sin(p) / p
    return out


def weights(arm: str, f: float):
    """(offsets, weights) exactly as align.rs computes them."""
    if arm == "nearest":
        return np.array([0.0 if f < 0.5 else 1.0]), np.array([1.0])
    if arm == "bilinear":
        return np.array([0.0, 1.0]), np.array([1.0 - f, f])
    if arm == "catmull-rom":
        f2, f3 = f * f, f * f * f
        w = np.array([-0.5 * f3 + f2 - 0.5 * f,
                      1.5 * f3 - 2.5 * f2 + 1.0,
                      -1.5 * f3 + 2.0 * f2 + 0.5 * f,
                      0.5 * f3 - 0.5 * f2])
        return np.array([-1.0, 0.0, 1.0, 2.0]), w
    if arm == "lanczos2":
        o = np.arange(4) - 1.0
        t = f - o
        w = sinc(t) * sinc(t / 2.0)
        return o, w / w.sum()
    if arm == "lanczos3":
        o = np.arange(6) - 2.0
        t = f - o
        w = sinc(t) * sinc(t / 3.0)
        return o, w / w.sum()
    raise ValueError(arm)


def power_gain_1d(arm: str, v: np.ndarray) -> np.ndarray:
    """Phase-averaged |H(v)|^2 for one axis."""
    acc = np.zeros_like(v, dtype=np.float64)
    for f in (np.arange(NPHASE) + 0.5) / NPHASE:
        o, w = weights(arm, f)
        h = np.zeros_like(v, dtype=np.complex128)
        for ok, wk in zip(o, w):
            h += wk * np.exp(2j * np.pi * v * (ok - f))
        acc += np.abs(h) ** 2
    return acc / NPHASE


def band_mask_and_freqs():
    f = np.fft.fftfreq(TILE)
    fy, fx = np.meshgrid(f, f, indexing="ij")
    fr = np.sqrt(fy ** 2 + fx ** 2)
    return fy, fx, (fr >= BAND[0]) & (fr < BAND[1])


def predict() -> dict:
    fy, fx, m = band_mask_and_freqs()
    uniq = np.unique(np.abs(np.fft.fftfreq(TILE)))
    out = {}
    for arm in ARMS:
        g1 = dict(zip(uniq, power_gain_1d(arm, uniq)))
        gy = np.vectorize(lambda t: g1[abs(t)])(fy)
        gx = np.vectorize(lambda t: g1[abs(t)])(fx)
        out[arm] = float((gy * gx)[m].mean())
    base = out[BASELINE]
    return {a: float(np.log10(out[a] / base)) for a in ARMS}


def main(subjects):
    pred = predict()
    print("\n=== CLOSED-FORM PREDICTION -- no image, no capture, no stack")
    print("    band gain vs catmull-rom, from align.rs's own weights\n")
    for a in ARMS:
        print(f"     {a:<12} {pred[a]:+.4f} dex")

    rows = []
    print("\n=== MEASURED end-to-end, against the prediction")
    for s in subjects:
        p = HERE / "out" / f"a1_{s}.json"
        if not p.exists():
            print(f"  (skipping {s}: no a1 json yet)")
            continue
        r = json.loads(p.read_text())
        print(f"\n  {s}  (detail-decile grad {r['grad_detail']:.0f} vs flat-decile "
              f"{r['grad_flat']:.0f} = {r['grad_detail']/r['grad_flat']:.2f}x separation)")
        print(f"     {'arm':<12} {'pred':>8} {'M1 detail':>10} {'M2 flat':>9} "
              f"{'|meas-pred|':>12}")
        for a in ARMS:
            m1 = r["arms"][a]["M1_detail_dex"]
            m2 = r["arms"][a]["M2_flat_dex"]
            d = abs(m1 - pred[a])
            rows.append({"subject": s, "arm": a, "pred": pred[a], "M1": m1, "M2": m2,
                         "abs_err": d})
            print(f"     {a:<12} {pred[a]:+8.4f} {m1:+10.4f} {m2:+9.4f} {d:12.4f}")

    non_base = [r for r in rows if r["arm"] != BASELINE]
    if non_base:
        err = np.array([r["abs_err"] for r in non_base])
        eff = np.array([abs(r["pred"]) for r in non_base])
        print(f"\n  Across {len(non_base)} subject x arm cells (baseline excluded):")
        print(f"    mean |measured - predicted| = {err.mean():.4f} dex")
        print(f"    max  |measured - predicted| = {err.max():.4f} dex")
        print(f"    mean |predicted effect|     = {eff.mean():.4f} dex")
        print(f"    => the photographs move the answer by {100*err.mean()/eff.mean():.1f}% "
              f"of the effect being claimed")

    res = {"prediction": pred, "rows": rows, "nphase": NPHASE, "tile": TILE, "band": BAND}
    (HERE / "out" / "a2_datasheet.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:] or ["flat-on-ruler-cpl", "wrapped-text-1", "bee-3-cpl"])
