"""Veil-or-light: does a veiling fix REMOVE VEIL or ADD LIGHT?

The problem this exists to solve
--------------------------------
The veiling defect is a DARKENING of the backdrop near a subject.  A candidate fix
replaces a gated mean with an upper envelope / high percentile across frames.  An
order statistic is not an unbiased estimator of a level: over n samples of noise
with sd sigma the maximum sits ABOVE the mean by a factor that grows like
sqrt(2 ln n), and `ordstat.py` measures +0.845 sigma for the mean-of-top-3.

That bias is UPWARD and the defect is a DARKENING, so an undebiased envelope
brightens the backdrop whether or not any veil was removed.  It will therefore
satisfy the veiling number, satisfy the aura number, and satisfy any ratio -- every
metric goes green whether the fix works or not.

Only one quantity distinguishes the two explanations:

    THE ABSOLUTE BACKDROP LEVEL, IN DN, ON A SUBJECT THAT HAS NO VEIL.

Everything here is therefore reported in absolute DN.  Nothing is normalised to its
own arm's far field -- that convention is exactly what hides an additive bias, since
a uniform brightening cancels out of it.

Three signatures, measured together
-----------------------------------
1. FAR-FIELD LEVEL SHIFT (DN).  On a veil-free placebo, or far from the subject on
   any stack, a genuine veil repair does nothing and a biased estimator adds light.
   This is the discriminator.
2. BACKGROUND NOISE SD RATIO.  An envelope of 3 is predicted 9.7x noisier than a
   mean over 166.8 frames.  A large noise increase is the fingerprint of an order
   statistic even if someone has debiased the level.
3. NEAR-FIELD RECOVERY (DN).  The intended effect, reported last, because on its
   own it cannot distinguish the two explanations.

Signature 2 also CLOSES THE PREDICTION.  If the shipped arm is a mean over n_admit
frames then sigma_frame = sd_baseline * sqrt(n_admit), so the bias an undebiased
envelope would produce is predictable in DN from the baseline arm alone, with no
extra data and no free parameter.  Predicted bias is printed next to measured
far-field shift so the two can be compared directly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from scipy.ndimage import binary_closing, binary_opening, distance_transform_edt, label

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from halfspec import load  # noqa: E402

# Mean of the top k of n standard normals, by Monte Carlo, cached.
_TOPK: dict[tuple[int, int], float] = {}


def topk_bias(k: int, n: int, trials: int = 200_000) -> float:
    key = (k, n)
    if key not in _TOPK:
        rng = np.random.default_rng(7)
        x = rng.normal(0.0, 1.0, (trials, n))
        x.sort(axis=1)
        _TOPK[key] = float(x[:, -k:].mean(axis=1).mean())
    return _TOPK[key]


def subject_mask(base: np.ndarray, frac: float) -> np.ndarray:
    """Subject = the large dark object, found on the BASELINE arm only.

    The mask must never be derived from the arm under test, or the fix could move
    the very geometry the measurement is defined against.
    """
    g = base.mean(axis=2)
    lo, hi = np.percentile(g, 2), np.percentile(g, 98)
    thr = lo + frac * (hi - lo)
    m = g < thr
    m = binary_opening(m, np.ones((9, 9)))
    m = binary_closing(m, np.ones((15, 15)))
    lab, n = label(m)
    if n == 0:
        raise SystemExit("no subject found; adjust --mask-frac")
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    return lab == int(sizes.argmax())


def band_levels(img: np.ndarray, dist: np.ndarray, edges: list[float],
                valid: np.ndarray) -> list[dict]:
    out = []
    g = img.mean(axis=2)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (dist >= a) & (dist < b) & valid
        n = int(m.sum())
        out.append({
            "d_lo": a, "d_hi": b, "n_px": n,
            "level_dn": float(g[m].mean()) if n else float("nan"),
            "sd_dn": float(g[m].std()) if n else float("nan"),
        })
    return out


def flat_far_sd(img: np.ndarray, dist: np.ndarray, d_min: float,
                tile: int = 128) -> tuple[float, float, float, int]:
    """Level and noise sd in far-field tiles, using the local high-pass so that a
    slow backdrop gradient is not counted as noise.

    TWO noise numbers are returned and both are needed.  The first is measured on
    the channel mean; the second is the mean of the three per-channel sds.  They
    differ by up to sqrt(3), because averaging three channels attenuates any noise
    that is uncorrelated between them while leaving chroma-correlated noise alone.
    Reporting only the channel-mean sd would under-read a chroma-independent noise
    increase by exactly that factor -- commissioning case 5b measures 5.662x for a
    planted 9.7x, against a predicted 5.660x.  Reporting both brackets the true
    ratio without having to assume anything about chroma correlation.
    """
    g = img.mean(axis=2)
    h, w = g.shape
    yy, xx = np.mgrid[0:tile, 0:tile]
    A = np.c_[np.ones(tile * tile), yy.ravel(), xx.ravel()]
    lvls, sds, csds = [], [], []
    for y in range(0, h - tile + 1, tile):
        for x in range(0, w - tile + 1, tile):
            dsub = dist[y:y + tile, x:x + tile]
            if dsub.min() < d_min:
                continue
            t = g[y:y + tile, x:x + tile]
            cube = img[y:y + tile, x:x + tile, :].reshape(tile * tile, -1)
            # high-pass: subtract a plane fit, leaving noise.  Solve the channel
            # mean and the individual channels in one least-squares call.
            B = np.c_[t.ravel(), cube]
            coef, *_ = np.linalg.lstsq(A, B, rcond=None)
            resid = B - A @ coef
            lvls.append(float(t.mean()))
            sds.append(float(resid[:, 0].std()))
            csds.append(float(resid[:, 1:].std(axis=0).mean()))
    if not lvls:
        return float("nan"), float("nan"), float("nan"), 0
    return (float(np.mean(lvls)), float(np.median(sds)),
            float(np.median(csds)), len(lvls))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True, help="arm WITHOUT the fix")
    ap.add_argument("--fixed", help="arm WITH the fix (omit to characterise only)")
    ap.add_argument("--label-baseline", default="baseline")
    ap.add_argument("--label-fixed", default="fixed")
    ap.add_argument("--mask-frac", type=float, default=0.5)
    ap.add_argument("--far", type=float, default=400.0,
                    help="distance beyond which the veil is taken to be spent")
    ap.add_argument("--n-admit", type=float, default=166.8,
                    help="frames the shipped gate averages, for sigma_frame")
    ap.add_argument("--envelope-k", type=int, default=3)
    ap.add_argument("--envelope-n", type=int, default=205)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = load(args.baseline)
    rep: dict = {"baseline": args.baseline, "fixed": args.fixed}

    mask = subject_mask(base, args.mask_frac)
    dist = distance_transform_edt(~mask)
    rep["subject_px"] = int(mask.sum())
    frac = 100.0 * mask.sum() / mask.size
    print(f"subject mask: {mask.sum():,} px ({frac:.2f}% of frame)")
    if frac < 0.05 or frac > 80.0:
        print("  WARNING: implausible subject fraction; check --mask-frac")

    edges = [4, 12, 30, 60, 120, 200, 300, 450, 700, 1200]
    valid = ~mask
    arms = {args.label_baseline: base}
    if args.fixed:
        arms[args.label_fixed] = load(args.fixed)

    rep["bands"] = {}
    for name, img in arms.items():
        rep["bands"][name] = band_levels(img, dist, edges, valid)

    print("\nABSOLUTE backdrop level by distance from the subject, in DN.")
    print("Not normalised to any arm's own far field -- that would hide a bias.\n")
    hdr = f"  {'d (px)':>12}"
    for name in arms:
        hdr += f"  {name:>14}"
    if args.fixed:
        hdr += f"  {'delta DN':>10}"
    print(hdr)
    for i, band in enumerate(rep["bands"][args.label_baseline]):
        row = f"  {band['d_lo']:5.0f}-{band['d_hi']:<6.0f}"
        vals = []
        for name in arms:
            v = rep["bands"][name][i]["level_dn"]
            vals.append(v)
            row += f"  {v:14.1f}"
        if args.fixed:
            row += f"  {vals[1]-vals[0]:+10.1f}"
        print(row)

    print("\nFAR-FIELD (d >= "
          f"{args.far:.0f} px) -- the discriminator:")
    rep["far"] = {}
    for name, img in arms.items():
        lvl, sd, csd, n = flat_far_sd(img, dist, args.far)
        rep["far"][name] = {"level_dn": lvl, "noise_sd_dn": sd,
                            "noise_sd_chan_dn": csd, "n_tiles": n}
        print(f"  {name:>14}: level {lvl:10.1f} DN   noise sd {sd:8.2f} DN"
              f"   per-chan {csd:8.2f} DN   ({n} tiles)")

    b = rep["far"][args.label_baseline]
    # sigma_frame must come from the PER-CHANNEL sd, not the channel mean.  The
    # quantity being predicted is a LEVEL SHIFT, and a level shift does not
    # average down across channels the way noise does; deriving sigma_frame from
    # the channel mean would under-predict the bias by sqrt(3) -- i.e. it would
    # understate exactly the effect this instrument exists to catch.
    sigma_frame = b["noise_sd_chan_dn"] * np.sqrt(args.n_admit)
    bias_sigma = topk_bias(args.envelope_k, args.envelope_n)
    predicted = bias_sigma * sigma_frame
    rep["sigma_frame_dn"] = sigma_frame
    rep["envelope_bias_sigma"] = bias_sigma
    rep["predicted_bias_dn"] = predicted
    print(f"\n  implied sigma_frame          = {b['noise_sd_chan_dn']:.2f} "
          f"(per channel) * sqrt({args.n_admit:g}) = {sigma_frame:.1f} DN")
    print(f"  mean-of-top-{args.envelope_k} of {args.envelope_n} bias  "
          f"= {bias_sigma:+.3f} sigma")
    print(f"  => an UNDEBIASED envelope would raise the far field by "
          f"{predicted:+.1f} DN")

    if args.fixed:
        f = rep["far"][args.label_fixed]
        shift = f["level_dn"] - b["level_dn"]
        noise_ratio = f["noise_sd_dn"] / max(b["noise_sd_dn"], 1e-9)
        chan_ratio = f["noise_sd_chan_dn"] / max(b["noise_sd_chan_dn"], 1e-9)
        rep["far_shift_dn"] = shift
        rep["noise_ratio"] = noise_ratio
        rep["noise_ratio_chan"] = chan_ratio
        print(f"\n  MEASURED far-field shift     = {shift:+.1f} DN")
        print(f"  MEASURED noise sd ratio      = {noise_ratio:.2f}x "
              f"(channel mean), {chan_ratio:.2f}x (per channel)")
        print("    The true ratio lies between these two.  They coincide for")
        print("    chroma-correlated noise and differ by sqrt(3) for independent.")
        print("\n  VERDICT")
        frac_expl = shift / predicted if predicted else float("nan")
        if abs(shift) < 0.15 * abs(predicted):
            print("    Far field is unmoved: the fix is NOT an undebiased order")
            print("    statistic.  Near-field recovery can be read as real.")
        else:
            print(f"    Far field moved {shift:+.1f} DN, which is "
                  f"{100*frac_expl:.0f}% of the {predicted:+.1f} DN an undebiased")
            print("    envelope predicts.  Backdrop 'recovery' on this stack is")
            print("    NOT separable from added light by this measurement.")
        if noise_ratio > 2.0:
            print(f"    Noise rose {noise_ratio:.2f}x -- an order statistic is in")
            print("    the path even if the level was debiased.")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
