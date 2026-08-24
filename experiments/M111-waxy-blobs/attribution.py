"""M111 -- attribution: what did SELECTION add, and where?

The coincidence statistic is confounded and I caught it with my own arm. At
`--gate 100000` every output pixel is the plain mean of all 299 frames, so the
election has no influence on the output whatsoever -- yet election boundaries
still score 1.686 against a 1.048 null there. Election boundaries sit where the
frames' focus responses cross, and that is genuinely correlated with scene
structure. So "the blob edge coincides with an election boundary" is NOT
evidence that the election drew it, and any report that stopped at the
coincidence number would have been wrong.

The registered, unconfounded test is a difference image:

    D = luma(gate 4) - luma(gate 100000)

Both arms are the same frames, the same alignment, the same colour pipeline and
the same exposure; they differ only in how many frames the gate admitted. D is
therefore exactly what SELECTION added, and it contains no scene content that
the mean does not already carry. If selection is drawing hard edges in flat
regions, |grad D| is larger across election boundaries than away from them --
and the translated-election null (NC5) says how large that is by chance.

Arms and controls:
  low   flat & n_eff<=8   -- where the merge elected. The claim.
  high  flat & n_eff>=64  -- where the merge averaged. Must not fire.
  rough textured          -- where selection SHOULD draw edges. Expected to
                             fire; if it did not, the instrument is broken.
  NC3   a planted patchwork of known DN amplitude in the same population,
        through the identical detector, to price the real effect in DN.

Usage:  python attribution.py
"""

import json
import os

import numpy as np
import tifffile
from scipy import ndimage

ROOT = r"C:\dev\strehl-out\M111"
RENDER = os.path.join(ROOT, "render")
FLAT_SD = 300.0
LOW_N, HIGH_N, MARGIN = 8, 64, 64
SHIFTS = [(137, 211), (-263, 89), (451, -337)]
RNG = np.random.default_rng(1110)


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def plane_luma(path):
    y = luma(tifffile.imread(path))
    return 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndimage.uniform_filter(y, k, mode="nearest")
    m2 = ndimage.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def step_on_off(idx, f, mask):
    dh = idx[:, 1:] != idx[:, :-1]
    dv = idx[1:, :] != idx[:-1, :]
    mh = mask[:, 1:] & mask[:, :-1]
    mv = mask[1:, :] & mask[:-1, :]
    step = np.concatenate([np.abs(f[:, 1:] - f[:, :-1])[mh], np.abs(f[1:, :] - f[:-1, :])[mv]])
    on = np.concatenate([dh[mh], dv[mv]])
    if step.size < 5000 or on.sum() < 500 or (~on).sum() < 500:
        return None
    a, b = float(np.median(step[on])), float(np.median(step[~on]))
    return {"n": int(step.size), "bdens": float(on.mean()), "on_dn": a, "off_dn": b,
            "excess_dn": a - b, "ratio": a / max(b, 1e-9),
            "on_p90": float(np.percentile(step[on], 90))}


def with_null(idx, f, mask, tag):
    real = step_on_off(idx, f, mask)
    nulls = [step_on_off(np.roll(idx, s, (0, 1)), f, mask) for s in SHIFTS]
    nulls = [n for n in nulls if n]
    nr = float(np.mean([n["ratio"] for n in nulls]))
    ns = float(np.std([n["ratio"] for n in nulls], ddof=1))
    ne = float(np.mean([n["excess_dn"] for n in nulls]))
    nes = float(np.std([n["excess_dn"] for n in nulls], ddof=1))
    return {"tag": tag, "real": real, "null_ratio": nr, "null_ratio_sd": ns,
            "null_excess_dn": ne, "null_excess_sd": nes,
            "sigma_ratio": (real["ratio"] - nr) / max(ns, 1e-9),
            "sigma_excess": (real["excess_dn"] - ne) / max(nes, 1e-9)}


def main():
    import sys

    if len(sys.argv) >= 4:
        st8 = sys.argv[1]
        f4, fm = sys.argv[2], sys.argv[3]
        label = sys.argv[4] if len(sys.argv) > 4 else "arg"
    else:
        st8 = os.path.join(RENDER, "state-r8")
        f4 = os.path.join(RENDER, "marker-dump.tif")
        fm = os.path.join(RENDER, "marker-g100000.tif")
        label = "marker"
    print(f"=== attribution: {label} ===")
    y4 = plane_luma(f4)
    ym = plane_luma(fm)
    idx = np.load(os.path.join(st8, "best_index.npy"))
    nef = [f for f in os.listdir(st8) if f.startswith("n_eff_gate")]
    ne = np.load(os.path.join(st8, sorted(nef)[0]))
    d = y4 - ym

    inner = np.zeros(y4.shape, bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
    sd = local_sd(y4)
    flat = (sd < FLAT_SD) & inner
    masks = {"low  (flat, n_eff<=8)": flat & (ne <= LOW_N),
             "high (flat, n_eff>=64)": flat & (ne >= HIGH_N),
             "rough (textured)": (sd >= FLAT_SD * 4) & inner}

    res = {"arms": [], "nc3": []}
    print("--- attribution on D = luma(gate 4) - luma(gate 1e5) : what SELECTION added ---")
    print(f"{'population':>24} {'on DN':>8} {'off DN':>8} {'excess':>8} {'ratio':>7}"
          f" {'null ratio':>16} {'sigma':>8}")
    for name, m in masks.items():
        if m.sum() < 20000:
            print(f"{name:>24}   too small ({int(m.sum())})")
            continue
        r = with_null(idx, d, m, name)
        res["arms"].append(r)
        print(f"{name:>24} {r['real']['on_dn']:8.2f} {r['real']['off_dn']:8.2f}"
              f" {r['real']['excess_dn']:8.2f} {r['real']['ratio']:7.3f}"
              f" {r['null_ratio']:9.3f}+-{r['null_ratio_sd']:.3f} {r['sigma_ratio']:8.1f}")

    print("\n--- the same detector on the SHIPPED image itself (not the difference) ---")
    for name, m in masks.items():
        if m.sum() < 20000:
            continue
        r = with_null(idx, y4, m, name + " [shipped]")
        res["arms"].append(r)
        print(f"{name:>24} {r['real']['on_dn']:8.2f} {r['real']['off_dn']:8.2f}"
              f" {r['real']['excess_dn']:8.2f} {r['real']['ratio']:7.3f}"
              f" {r['null_ratio']:9.3f}+-{r['null_ratio_sd']:.3f} {r['sigma_ratio']:8.1f}")

    print("\n--- NC3: plant a patchwork of known DN ON TOP OF D, in the SAME low population ---")
    print("    (planted into D itself, not into a zero field, so the ratio is comparable to")
    print("     the real number above rather than divided by an identically-zero off-step)")
    low = masks["low  (flat, n_eff<=8)"]
    src = np.roll(idx, (911, 577), (0, 1))
    print(f"{'amp DN':>8} {'excess DN':>11} {'ratio':>8} {'sigma vs null':>14}")
    for amp in (0.0, 2.0, 4.0, 8.0, 16.0):
        offs = RNG.normal(0.0, amp, size=int(src.max()) + 1).astype(np.float32)
        planted = d.copy()
        planted[low] += offs[src[low]]
        r = with_null(src, planted, low, f"nc3 amp={amp}")
        res["nc3"].append({"amp": amp, **r})
        print(f"{amp:8.1f} {r['real']['excess_dn']:11.3f} {r['real']['ratio']:8.3f}"
              f" {r['sigma_ratio']:14.1f}")

    # How much of the shipped image's local variation in the low population is
    # attributable to selection at all?
    print("\n--- energy accounting in the low population ---")
    for name, m in masks.items():
        if m.sum() < 20000:
            continue
        print(f"{name:>24}  sd(shipped) {y4[m].std():8.1f}   sd(mean-arm) {ym[m].std():8.1f}"
              f"   sd(D) {d[m].std():8.1f}   |D| median {np.median(np.abs(d[m])):8.1f}")

    with open(os.path.join(ROOT, f"attribution-{label}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=float)
    print(f"\nwrote {os.path.join(ROOT, f'attribution-{label}.json')}")


if __name__ == "__main__":
    main()
