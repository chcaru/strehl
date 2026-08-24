"""M70 s14 - controls for the through-focus SYMMETRY question, run before any
corpus curve is looked at.

Commissioned after the primary result, by the owner, on the strength of M67
section 7.3. M67 withdrew its own claim that real through-focus curves are
"measured asymmetric" - no corpus fact establishes it - and named three things
to know before measuring:

  (a) fact 274 already measured a SYMMETRIC shape deviation (heavier shoulders
      than a Gaussian). Any skew estimator must report both moments so the two
      are not confused.
  (b) M25 question 33's confound is live: on one stack, depth range and
      defocus-rate non-linearity are not separable. A second stack with a
      different depth range is the minimum.
  (c) fact 471's FWHM agrees with the model on two stacks, so a deviation, if
      present, is in the TAILS rather than the core. An estimator that only
      fits near the peak will not see it.

This script fixes the estimator and measures its null and its power. It touches
no corpus stack. The corpus run is s15, and the criteria are pre-registered in
PREREGISTRATION-B.md, written after this script's numbers and before s15.

Four controls, each with the failure it can express:

  NULL-SYM     a symmetric plant. Blur radius |k-k0|*delta, identical on both
               sides by construction. The estimator MUST return ~0. Anything
               else is manufactured asymmetry, and its sd sets the null band.
  NULL-NOISE   flat latent, calibrated noise only. No curve at all. Bounds what
               the statistic does when there is nothing to measure.
  POWER-ASYM   an asymmetric plant: delta_near != delta_far. The estimator MUST
               recover the sign and a usable fraction of the magnitude, or the
               SYMMETRIC branch of the criterion is unsupportable (rule 20).
  CONFOUND     a two-depth superposition with unequal weights and a SYMMETRIC
               PSF. This produces asymmetry from scene geometry alone. It is
               M25 question 33 made concrete, and it bounds how much of any
               corpus reading could be scene rather than optics.

Plus one placebo that runs on everything, including the corpus in s15:

  REVERSAL     reverse the frame order. Every asymmetry statistic must flip
               sign exactly. An estimator that does not is producing a sign
               from something other than the data's order.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
import s03_plant as P3  # noqa: E402
import s05_analyse as A5  # noqa: E402

OUT = A5.OUT
FALL = (0.50, 0.25, 0.10)
MOMENT_WINDOW = 10


# ---------------------------------------------------------------------------
# The estimator
# ---------------------------------------------------------------------------
def half_widths(s: np.ndarray, frac: float, smooth: bool = True):
    """Interpolated offsets, in frames, at which the curve first falls to
    `frac` x peak on the low-index and high-index sides of the peak.

    Returns (w_near, w_far, censored_near, censored_far). `w_near` is the
    low-index side. A side is CENSORED when the curve never falls to the
    threshold before the stack ends; censoring is returned, never imputed,
    because a right-censored width is what killed M41's detail metric.

    Peak location uses the [1,2,1]-smoothed curve (rule 4: this is an argmax on
    a noisy response and it is being said so). The smoothing kernel is
    symmetric, so it cannot itself create a sign - NULL-SYM below measures
    whether that holds in practice rather than assuming it.
    """
    s = np.asarray(s, dtype=np.float64)
    k = s.size
    c = M.smooth3(s) if smooth else s
    i = int(np.argmax(c))
    pk = float(c[i])
    if pk <= 0:
        return np.nan, np.nan, True, True
    thr = frac * pk
    out = []
    for step in (-1, +1):
        j, w, cens = i, np.nan, True
        while 0 <= j + step < k:
            a, b = float(c[j]), float(c[j + step])
            if b <= thr:
                t = 1.0 if a == b else (a - thr) / (a - b)
                w = abs(j + step * t - i)
                cens = False
                break
            j += step
        out.append((w, cens))
    return out[0][0], out[1][0], out[0][1], out[1][1]


def asym(s: np.ndarray, frac: float, smooth: bool = True) -> float:
    """(w_far - w_near) / (w_far + w_near). Zero is symmetric, positive means
    the curve decays more slowly on the HIGH frame-index side. Range [-1, 1]."""
    wn, wf, cn, cf = half_widths(s, frac, smooth)
    if cn or cf or not np.isfinite(wn) or not np.isfinite(wf) or (wn + wf) <= 0:
        return np.nan
    return float((wf - wn) / (wf + wn))


def moments(s: np.ndarray, window: int = MOMENT_WINDOW):
    """Standardised third (skew) and excess fourth (kurtosis) moments of the
    weight distribution w_k = max(S_k, 0) over +-window frames about the peak.

    The clip is REQUIRED here - a weight must be non-negative - unlike in
    section 4.2's sum, where it was the defect. Its bias is measured by
    NULL-NOISE below rather than assumed away.
    """
    s = np.asarray(s, dtype=np.float64)
    k = s.size
    c = M.smooth3(s)
    i = int(np.argmax(c))
    lo, hi = max(0, i - window), min(k, i + window + 1)
    w = np.clip(s[lo:hi], 0.0, None)
    x = np.arange(lo, hi, dtype=np.float64)
    tot = w.sum()
    if tot <= 0 or (hi - lo) < 5:
        return np.nan, np.nan, (lo <= 0) or (hi >= k)
    mu = float((w * x).sum() / tot)
    m2 = float((w * (x - mu) ** 2).sum() / tot)
    if m2 <= 0:
        return np.nan, np.nan, (lo <= 0) or (hi >= k)
    m3 = float((w * (x - mu) ** 3).sum() / tot)
    m4 = float((w * (x - mu) ** 4).sum() / tot)
    return m3 / m2 ** 1.5, m4 / m2 ** 2 - 3.0, (lo <= 0) or (hi >= k)


def all_stats(s: np.ndarray) -> dict:
    o = {f"A{int(100 * f):02d}": asym(s, f) for f in FALL}
    g1, g2, trunc = moments(s)
    o["g1"] = g1
    o["g2"] = g2
    o["trunc"] = trunc
    return o


def nanmed(x):
    x = [v for v in x if np.isfinite(v)]
    return float(np.median(x)) if x else np.nan


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
def ladder(K, d_near, d_far):
    k0 = K // 2
    return [(k0 - k) * d_near if k < k0 else (k - k0) * d_far for k in range(K)]


def two_depth(K, delta, sep, w_far):
    """Superposition of two depths, SYMMETRIC PSF, unequal weights. Returns the
    per-frame radii for each layer and the layer weights."""
    k0, k1 = K // 2, K // 2 + sep
    return ([abs(k - k0) * delta for k in range(K)],
            [abs(k - k1) * delta for k in range(K)], w_far)


def run_controls(reps: int = 24) -> dict:
    rng = np.random.default_rng(7014)
    latent, mean_dn = P3.load_latent()
    flat = np.full_like(latent, float(latent.mean()))
    K = 41
    out = {}

    print("=" * 116)
    print("NULL-SYM - a plant that is SYMMETRIC BY CONSTRUCTION. The estimator must return 0.")
    print("=" * 116)
    print(f"{'delta px/step':>14s} {'band':>8s} {'A50':>9s} {'A25':>9s} {'A10':>9s} "
          f"{'g1':>9s} {'g2':>9s} {'n':>4s}")
    acc = {k: [] for k in ("A50", "A25", "A10", "g1", "g2")}
    for delta in (0.25, 0.5, 1.0):
        per = {k: [] for k in acc}
        for _ in range(reps):
            fr = P3.make_frames(latent, ladder(K, delta, delta), P3.LATENT_ISO, rng, noise=True)
            m = P3.measure_frames(fr, P3.LATENT_ISO, subtract_noise=True)
            for b in M.MID_BANDS:
                st = all_stats(np.array([r[b] for r in m]))
                for k in per:
                    per[k].append(st[k])
        for k in acc:
            acc[k].extend(per[k])
        print(f"{delta:14.3f} {'mid(3)':>8s} " + " ".join(
            f"{nanmed(per[k]):9.4f}" for k in ("A50", "A25", "A10", "g1", "g2"))
            + f" {reps * 3:4d}")
    sd = {k: float(np.nanstd([v for v in acc[k] if np.isfinite(v)])) for k in acc}
    bias = {k: nanmed(acc[k]) for k in acc}
    print()
    print("  pooled bias   " + "  ".join(f"{k} {bias[k]:+.4f}" for k in
                                         ("A50", "A25", "A10", "g1", "g2")))
    print("  pooled sd     " + "  ".join(f"{k} {sd[k]:.4f}" for k in
                                         ("A50", "A25", "A10", "g1", "g2")))
    out["null_sym"] = {"bias": bias, "sd": sd, "n": len(acc["A50"])}

    print()
    print("=" * 116)
    print("NULL-NOISE - flat latent, calibrated noise only. There is no curve to be asymmetric about.")
    print("=" * 116)
    acc = {k: [] for k in ("A50", "A25", "A10", "g1", "g2")}
    ncens = 0
    for _ in range(reps * 2):
        fr = P3.make_frames(flat, [0.0] * K, P3.LATENT_ISO, rng, noise=True)
        m = P3.measure_frames(fr, P3.LATENT_ISO, subtract_noise=True)
        for b in M.MID_BANDS:
            st = all_stats(np.array([r[b] for r in m]))
            ncens += int(not np.isfinite(st["A50"]))
            for k in acc:
                acc[k].append(st[k])
    print("  median        " + "  ".join(f"{k} {nanmed(acc[k]):+.4f}" for k in
                                         ("A50", "A25", "A10", "g1", "g2")))
    print("  sd            " + "  ".join(
        f"{k} {np.nanstd([v for v in acc[k] if np.isfinite(v)]):.4f}" for k in
        ("A50", "A25", "A10", "g1", "g2")))
    print(f"  A50 undefined (censored or no peak) in {ncens}/{reps * 2 * 3} draws")
    out["null_noise"] = {"median": {k: nanmed(acc[k]) for k in acc},
                         "sd": {k: float(np.nanstd([v for v in acc[k] if np.isfinite(v)]))
                                for k in acc},
                         "censored": ncens, "n": reps * 2 * 3}

    print()
    print("=" * 116)
    print("POWER-ASYM (rule 20) - a plant that IS asymmetric. The estimator must find it.")
    print("  d_near / d_far are blur growth rates in px/step on the two sides of focus.")
    print("=" * 116)
    print(f"{'d_near':>8s} {'d_far':>8s} {'predicted sign':>15s} {'A50':>9s} {'A25':>9s} "
          f"{'A10':>9s} {'g1':>9s} {'g2':>9s}")
    rows = []
    for dn, df in ((0.5, 1.0), (1.0, 0.5), (0.5, 0.75), (0.75, 0.5), (0.5, 2.0)):
        per = {k: [] for k in ("A50", "A25", "A10", "g1", "g2")}
        for _ in range(reps):
            fr = P3.make_frames(latent, ladder(K, dn, df), P3.LATENT_ISO, rng, noise=True)
            m = P3.measure_frames(fr, P3.LATENT_ISO, subtract_noise=True)
            for b in M.MID_BANDS:
                st = all_stats(np.array([r[b] for r in m]))
                for k in per:
                    per[k].append(st[k])
        sign = "far slower (+)" if df < dn else "far faster (-)"
        v = {k: nanmed(per[k]) for k in per}
        print(f"{dn:8.2f} {df:8.2f} {sign:>15s} " + " ".join(
            f"{v[k]:9.4f}" for k in ("A50", "A25", "A10", "g1", "g2")))
        rows.append({"d_near": dn, "d_far": df, **v})
    out["power_asym"] = rows

    print()
    print("  Ideal A50 for a scale-family curve is (d_near - d_far)/(d_near + d_far):")
    for dn, df in ((0.5, 1.0), (1.0, 0.5), (0.5, 0.75), (0.75, 0.5), (0.5, 2.0)):
        print(f"    d_near {dn:.2f} d_far {df:.2f}  ->  ideal A = "
              f"{(dn - df) / (dn + df):+.4f}")

    print()
    print("=" * 116)
    print("CONFOUND - two depths, UNEQUAL weights, SYMMETRIC PSF (M25 question 33, made concrete)")
    print("  Any asymmetry here comes from scene geometry alone. The PSF is symmetric by construction.")
    print("=" * 116)
    print(f"{'sep frames':>11s} {'w_far':>7s} {'A50':>9s} {'A25':>9s} {'A10':>9s} "
          f"{'g1':>9s} {'g2':>9s}")
    rows = []
    for sep, wf in ((3, 0.30), (6, 0.30), (6, 0.15), (10, 0.30), (10, 0.15)):
        per = {k: [] for k in ("A50", "A25", "A10", "g1", "g2")}
        for _ in range(reps):
            r0, r1, w = two_depth(K, 0.5, sep, wf)
            f0 = P3.make_frames(latent, r0, P3.LATENT_ISO, rng, noise=False)
            f1 = P3.make_frames(latent, r1, P3.LATENT_ISO, rng, noise=False)
            mix = [(1 - w) * a + w * b for a, b in zip(f0, f1)]
            m = P3.measure_frames(mix, P3.LATENT_ISO, subtract_noise=False)
            for b in M.MID_BANDS:
                st = all_stats(np.array([r[b] for r in m]))
                for k in per:
                    per[k].append(st[k])
        v = {k: nanmed(per[k]) for k in per}
        print(f"{sep:11d} {wf:7.2f} " + " ".join(
            f"{v[k]:9.4f}" for k in ("A50", "A25", "A10", "g1", "g2")))
        rows.append({"sep": sep, "w_far": wf, **v})
    out["confound"] = rows

    print()
    print("=" * 116)
    print("REVERSAL PLACEBO - reverse the frame order; every statistic must flip sign exactly")
    print("=" * 116)
    worst = 0.0
    for dn, df in ((0.5, 1.0), (0.75, 0.5)):
        fr = P3.make_frames(latent, ladder(K, dn, df), P3.LATENT_ISO, rng, noise=True)
        m = P3.measure_frames(fr, P3.LATENT_ISO, subtract_noise=True)
        for b in M.MID_BANDS:
            s = np.array([r[b] for r in m])
            f, r = all_stats(s), all_stats(s[::-1])
            for k in ("A50", "A25", "A10", "g1"):
                if np.isfinite(f[k]) and np.isfinite(r[k]):
                    worst = max(worst, abs(f[k] + r[k]))
            print(f"  d_near {dn:.2f} d_far {df:.2f} {b:>8s}  "
                  + "  ".join(f"{k} {f[k]:+.4f}/{r[k]:+.4f}" for k in ("A50", "g1")))
    print(f"\n  worst |forward + reversed| over A50/A25/A10/g1: {worst:.5f}"
          f"   (exact antisymmetry would be 0)")
    out["reversal_worst"] = float(worst)
    return out


def main() -> None:
    out = run_controls()
    with open(os.path.join(OUT, "s14_asym_controls.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote out/s14_asym_controls.json")


if __name__ == "__main__":
    main()
