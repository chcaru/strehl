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
from scipy.ndimage import (binary_closing, binary_fill_holes, binary_opening,
                           distance_transform_edt, label)

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


def subject_mask(base: np.ndarray, s_thr: float = 0.10,
                 g_frac: float = 0.60, min_frac: float = 0.0002) -> np.ndarray:
    """Subject = everything that is NOT the bright neutral backdrop.

    The obvious rule -- "the subject is the large dark object" -- fails on two of
    the four verification subjects, and both failures were found by looking at the
    mask rather than at its area:

      * `coffee-bean`: a shaded region of the white paper is darker than the
        threshold and touches the bean, so the largest-connected-component rule
        swallowed a big piece of BACKDROP into the subject.  Every distance in
        that region was then wrong.
      * `109MSDCF`: the subject is several paint strokes of different luminance,
        so a single luminance threshold selects a different subset at every
        threshold and the largest component keeps only one stroke.

    Defining the BACKDROP instead fixes both, because on these captures the
    backdrop is one thing -- bright and neutral -- while the subject is merely
    "not that", and need be neither dark, nor connected, nor of one tone.  All
    components above `min_frac` are kept, so a multi-part subject stays whole.
    """
    g = base.mean(axis=2)
    mx = base.max(axis=2)
    mn = base.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1.0)
    paper = (sat < s_thr) & (g > g_frac * np.percentile(g, 99))
    m = ~paper
    m = binary_opening(m, np.ones((9, 9)))
    m = binary_closing(m, np.ones((15, 15)))
    m = binary_fill_holes(m)
    lab, n = label(m)
    if n == 0:
        raise SystemExit("no subject found; adjust --sat-thr / --bg-frac")
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    return np.isin(lab, np.flatnonzero(sizes >= min_frac * m.size))


def mask_stability(base: np.ndarray) -> tuple[float, float]:
    """Area fraction of the mask over a grid of thresholds, as (min, max).

    A real subject/backdrop separation is insensitive to where exactly the
    threshold sits; an imaginary one is not.  Measured: flower-bud 1.20x over the
    grid, 109MSDCF 1.03x, coffee-bean 1.18x -- against 21x for the old
    luminance rule on `couch-fibers-cpl`, which has no backdrop at all.
    """
    fr = [float(subject_mask(base, st, gf).mean())
          for st in (0.08, 0.10, 0.12) for gf in (0.50, 0.60, 0.70)]
    return min(fr), max(fr)


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
        return float("nan"), float("nan"), float("nan"), float("nan"), 0
    # The 10th percentile of tile residual sds is the LOWER ENVELOPE of the noise,
    # justified because scene structure is strictly ADDITIVE to noise in a tile's
    # high-pass residual: a tile can be contaminated upward, never downward.  The
    # ratio median/p10 is therefore a contamination index for the far field.
    return (float(np.mean(lvls)), float(np.median(sds)),
            float(np.median(csds)), float(np.percentile(sds, 10)), len(lvls))


def far_tile_levels(img: np.ndarray, dist: np.ndarray, d_min: float,
                    tile: int = 128) -> np.ndarray:
    """Mean level of each far-field tile, in a fixed and reproducible order.

    Two arms of the SAME scene produce tiles in the same order, so differencing
    them tile-by-tile cancels the scene.  That is what makes the far-field shift
    measurable on a textured subject where no flat region exists at all: the
    error of the DIFFERENCE is set by what changed, not by how busy the picture
    is.  Taking each arm's own scatter and adding in quadrature instead would
    overstate the error of the difference by an order of magnitude.
    """
    g = img.mean(axis=2)
    h, w = g.shape
    out = []
    for y in range(0, h - tile + 1, tile):
        for x in range(0, w - tile + 1, tile):
            if dist[y:y + tile, x:x + tile].min() < d_min:
                continue
            out.append(float(g[y:y + tile, x:x + tile].mean()))
    return np.asarray(out, dtype=np.float64)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True, help="arm WITHOUT the fix")
    ap.add_argument("--fixed", help="arm WITH the fix (omit to characterise only)")
    ap.add_argument("--label-baseline", default="baseline")
    ap.add_argument("--label-fixed", default="fixed")
    ap.add_argument("--sat-thr", type=float, default=0.10,
                    help="backdrop saturation ceiling")
    ap.add_argument("--bg-frac", type=float, default=0.60,
                    help="backdrop luminance floor, as a fraction of p99")
    ap.add_argument("--far", type=float, default=400.0,
                    help="distance beyond which the veil is taken to be spent")
    ap.add_argument("--n-admit", type=float, default=None,
                    help="frames the shipped gate averages, for sigma_frame. "
                         "MUST be <= --frames; defaults to --frames if unset.")
    ap.add_argument("--frames", type=int, required=True,
                    help="frames in the stack, from the render log. Required: "
                         "sigma_frame = sd*sqrt(n_admit) and applying another "
                         "stack's n_admit to a short stack OVER-predicts the "
                         "bias, which makes a real bias look acceptable.")
    ap.add_argument("--envelope-k", type=int, default=3)
    ap.add_argument("--envelope-n", type=int, default=None,
                    help="pool the order statistic draws from; defaults to --frames")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.envelope_n is None:
        args.envelope_n = args.frames
    if args.n_admit is None:
        args.n_admit = float(args.frames)
    if args.n_admit > args.frames:
        print(f"  WARNING: --n-admit {args.n_admit:g} exceeds --frames "
              f"{args.frames}; clamping. A gate cannot average more frames than "
              f"the stack holds, and the excess would over-predict the bias.")
        args.n_admit = float(args.frames)

    base = load(args.baseline)
    rep: dict = {"baseline": args.baseline, "fixed": args.fixed}

    mask = subject_mask(base, args.sat_thr, args.bg_frac)
    dist = distance_transform_edt(~mask)
    rep["subject_px"] = int(mask.sum())
    frac = 100.0 * mask.sum() / mask.size
    lo_fr, hi_fr = mask_stability(base)
    instab = hi_fr / max(lo_fr, 1e-9)
    rep["mask_frac_pct"] = frac
    rep["mask_instability"] = instab
    print(f"subject mask: {mask.sum():,} px ({frac:.2f}% of frame), "
          f"threshold instability {instab:.2f}x over the grid")
    if frac > 90.0:
        raise SystemExit(
            f"  REFUSING: the mask covers {frac:.1f}% of the frame, so there is no\n"
            "  backdrop to measure. This harness measures a BACKDROP LEVEL near a\n"
            "  subject; on a subject that fills the frame edge to edge (couch-fibers\n"
            "  is pure fibre texture with no backdrop anywhere) the quantity does not\n"
            "  exist. Judge that subject with the do-no-harm instruments instead.\n"
            "  Returning a number here would be worse than returning nothing.")
    if instab > 1.5:
        print(f"  WARNING: mask area moves {instab:.2f}x across the threshold grid,")
        print("  so the subject/backdrop separation is not robust and the distance")
        print("  geometry should not be trusted. Look at the mask before reading on.")

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
        lvl, sd, csd, sd10, n = flat_far_sd(img, dist, args.far)
        contam = sd / max(sd10, 1e-9)
        rep["far"][name] = {"level_dn": lvl, "noise_sd_dn": sd,
                            "noise_sd_chan_dn": csd, "noise_sd_p10_dn": sd10,
                            "contamination": contam, "n_tiles": n}
        print(f"  {name:>14}: level {lvl:10.1f} DN   noise sd {sd:8.2f} DN"
              f"   per-chan {csd:8.2f} DN   ({n} tiles)")

    b = rep["far"][args.label_baseline]
    contam = b["contamination"]
    flat_ok = contam < 1.5
    rep["far_field_flat"] = bool(flat_ok)
    print(f"  far-field contamination index (median/p10 tile sd) = {contam:.2f}"
          f"  -> {'FLAT' if flat_ok else 'STRUCTURED'}")
    tb0 = far_tile_levels(base, dist, args.far)
    sem = float(np.std(tb0, ddof=1) / np.sqrt(tb0.size)) if tb0.size > 1 else float("nan")
    rep["far"][args.label_baseline]["level_sem_dn"] = sem
    print(f"  far-field level s.e. (across tiles) = {sem:.2f} DN")

    # sigma_frame must come from the PER-CHANNEL sd, not the channel mean.  The
    # quantity being predicted is a LEVEL SHIFT, and a level shift does not
    # average down across channels the way noise does; deriving sigma_frame from
    # the channel mean would under-predict the bias by sqrt(3) -- i.e. it would
    # understate exactly the effect this instrument exists to catch.
    #
    # This whole chain assumes the far field is FLAT.  Where it is not, the tile
    # residual sd is scene texture, sigma_frame is meaningless, and the harness
    # must say so rather than print a number.
    sigma_frame = b["noise_sd_chan_dn"] * np.sqrt(args.n_admit)
    # The estimator's exact form is not yet known, and the two readings of
    # "upper envelope of 3" differ by ~3x.  Report BOTH as a bracket rather than
    # picking one; picking one is how a prediction gets fitted to a result.
    lo_sigma = topk_bias(1, args.envelope_k)                    # max of k chosen
    hi_sigma = topk_bias(args.envelope_k, args.envelope_n)      # top k of all n
    rep["sigma_frame_dn"] = sigma_frame if flat_ok else float("nan")
    rep["envelope_bias_sigma_lo"] = lo_sigma
    rep["envelope_bias_sigma_hi"] = hi_sigma
    rep["predicted_bias_dn_lo"] = lo_sigma * sigma_frame if flat_ok else float("nan")
    rep["predicted_bias_dn_hi"] = hi_sigma * sigma_frame if flat_ok else float("nan")
    if flat_ok:
        print(f"\n  implied sigma_frame          = {b['noise_sd_chan_dn']:.2f} "
              f"(per channel) * sqrt({args.n_admit:g}) = {sigma_frame:.1f} DN")
        print("    n_admit defaults to the full frame count, which is an UPPER")
        print("    bound: the gate admits fewer. sigma_frame and therefore the")
        print("    predicted bias below are upper bounds too, and a large")
        print("    predicted bias makes a measured shift look like a small")
        print("    fraction of it. The verdict is NOT taken from this number --")
        print("    it is taken from the shift against zero and the pedestal shape,")
        print("    both of which are model-free. This is context only.")
        print("  undebiased-envelope bias, BRACKETED over the two readings:")
        print(f"    max of the {args.envelope_k} chosen frames     "
              f"{lo_sigma:+.3f} sigma = {lo_sigma*sigma_frame:+9.1f} DN")
        print(f"    mean of the top {args.envelope_k} of all {args.envelope_n:<5d}"
              f"  {hi_sigma:+.3f} sigma = {hi_sigma*sigma_frame:+9.1f} DN")
        print("    Which applies depends on how the fix is implemented; until that")
        print("    is known the prediction is the interval, not either endpoint.")
    else:
        print(f"\n  sigma_frame and the envelope-bias prediction are WITHHELD on")
        print(f"  this subject: contamination index {contam:.2f} means the far-field")
        print("  tile residual is scene texture, not noise, so sd*sqrt(n_admit)")
        print("  would not be a per-frame sigma. The MEASURED shift below is still")
        print("  valid -- it is a difference between two arms of the same scene,")
        print("  and the scene cancels out of it.")

    if args.fixed:
        f = rep["far"][args.label_fixed]
        shift = f["level_dn"] - b["level_dn"]
        # Error of the DIFFERENCE, from per-tile deltas, so the scene cancels.
        tb = far_tile_levels(base, dist, args.far)
        tf = far_tile_levels(arms[args.label_fixed], dist, args.far)
        d_tiles = tf - tb
        shift = float(d_tiles.mean())
        sem_d = float(np.std(d_tiles, ddof=1) / np.sqrt(d_tiles.size))
        rep["far_shift_n_tiles"] = int(d_tiles.size)
        noise_ratio = f["noise_sd_dn"] / max(b["noise_sd_dn"], 1e-9)
        chan_ratio = f["noise_sd_chan_dn"] / max(b["noise_sd_chan_dn"], 1e-9)
        rep["far_shift_dn"] = shift
        rep["far_shift_sem_dn"] = sem_d
        rep["noise_ratio"] = noise_ratio
        rep["noise_ratio_chan"] = chan_ratio
        z = shift / sem_d if sem_d > 0 else float("nan")
        print(f"\n  MEASURED far-field shift     = {shift:+.1f} DN "
              f"+/- {sem_d:.1f} ({z:+.1f} sigma from zero)")
        print(f"  MEASURED noise sd ratio      = {noise_ratio:.2f}x "
              f"(channel mean), {chan_ratio:.2f}x (per channel)")
        print("    The true ratio lies between these two.  They coincide for")
        print("    chroma-correlated noise and differ by sqrt(3) for independent.")
        print("\n  VERDICT")
        # A repair with a long tail also moves the far field, so a bare test
        # against zero is not enough.  SHAPE separates them: a repair tail keeps
        # decaying with distance, an additive bias is flat.  The outermost band
        # delta is therefore the pedestal, and the drop across the last three
        # bands is the tail.
        db = [rep["bands"][args.label_fixed][i]["level_dn"]
              - rep["bands"][args.label_baseline][i]["level_dn"]
              for i in range(len(edges) - 1)]
        pedestal = db[-1]
        tail = db[-3] - db[-1]
        rep["delta_bands_dn"] = db
        rep["pedestal_dn"] = pedestal
        rep["tail_drop_dn"] = tail
        print(f"    delta at d=300-450 / 450-700 / 700-1200 = "
              f"{db[-3]:+.1f} / {db[-2]:+.1f} / {db[-1]:+.1f} DN")
        print(f"    pedestal (outermost band) = {pedestal:+.1f} DN   "
              f"tail drop = {tail:+.1f} DN")
        if abs(z) < 3.0:
            print(f"    Far field is unmoved at {abs(z):.1f} sigma: no detectable")
            print("    added light. Near-field recovery can be read as real.")
        elif abs(pedestal) < 3.0 * sem_d and tail > 3.0 * sem_d:
            print("    The far field moved but the delta is STILL DECAYING and the")
            print("    outermost band is unmoved: that is a repair tail, not a")
            print("    pedestal. Near-field recovery can be read as real.")
        else:
            print(f"    Far field MOVED {shift:+.1f} DN at {abs(z):.1f} sigma with a")
            print(f"    FLAT pedestal of {pedestal:+.1f} DN out to the frame edge.")
            if flat_ok:
                lo_f = 100.0 * pedestal / (lo_sigma * sigma_frame)
                hi_f = 100.0 * pedestal / (hi_sigma * sigma_frame)
                print(f"    That is {hi_f:.0f}-{lo_f:.0f}% of the bias an undebiased")
                print("    envelope predicts.")
            print("    Backdrop 'recovery' on this stack is")
            print("    NOT separable from added light by this measurement.")
        if max(noise_ratio, chan_ratio) > 2.0:
            print(f"    Noise rose {noise_ratio:.2f}x / {chan_ratio:.2f}x -- an order")
            print("    statistic is in the path even if the level was debiased.")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
