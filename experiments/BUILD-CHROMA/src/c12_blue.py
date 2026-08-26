"""Blue's arm: is eps_b signal or noise, and what does the correction actually cost?

Two questions, deliberately kept apart because they have different failure modes.

(a) IS eps_b REAL? ORCH's radial/tangential reading put blue at 0.039 radial and
    0.030 tangential against green's 0.015/0.011 -- both ~2.6x green, i.e. they
    scale TOGETHER. A radial warp cannot raise the tangential component, so the
    parsimonious reading is that blue's estimator is simply noisier than green's
    and the ratio is the right normalised statistic. ORCH asserted that rather
    than measuring it and asked for the measurement.

    THE TEST: split the tiles in half at random, fit eps independently on each
    half, and let the half-to-half disagreement BE the noise floor. This is a
    resampling estimate of the estimator's own scatter that assumes nothing about
    the noise model. If blue's halves agree tightly, eps_b is signal. If they
    scatter at the level of eps_b itself, blue is fitting noise.

    Green (G1-G2) is carried as the null throughout: same instrument, same tiles,
    no chromatic content, so whatever it reports is the floor.

(b) WHAT DOES THE CORRECTION ACTUALLY SHIFT BLUE BY? BUILD-SHARP refuted the
    "wasted resample" mechanism by pricing the cost at blue's 0.039 px. But the
    correction does not apply 0.039 px. It applies eps_b * r, which is ZERO on
    axis and 0.368 plane px at the corner. Pricing a radially-varying shift at a
    single small value is the error this script checks for.

    Cross-check on my own kernel code: restore.rs independently records the
    phase-averaged Catmull-Rom MTF as 0.9402 / 0.7425 / 0.6251. If I cannot
    reproduce those three numbers I do not trust anything else here.
"""

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import lateral

RNG = np.random.default_rng(20260826)
N_SPLIT = 400
CORNER_R = 2112.0          # plane px at normalised field height 1.0
EPS_B = 174.4e-6           # the shipped coefficient
EPS_R = -704.5e-6


# ----------------------------------------------------------------- (b) kernel
def keys_taps(t, a=-0.5):
    """Keys cubic weights, transcribed from image_out.rs::keys_weights."""
    t2, t3 = t * t, t * t * t
    return np.array([
        a * (t3 - 2 * t2 + t),
        (a + 2) * t3 - (a + 3) * t2 + 1.0,
        -(a + 2) * t3 + (2 * a + 3) * t2 - a * t,
        -a * (t3 - t2),
    ])


def keys_mtf(t, f):
    """|H(f)| for a Keys resample of phase t. Taps sit at -1, 0, +1, +2."""
    w = keys_taps(t)
    k = np.array([-1.0, 0.0, 1.0, 2.0])
    return abs(np.sum(w * np.exp(-2j * np.pi * f * k)))


def phase_averaged_mtf(f, n=2001):
    return float(np.mean([keys_mtf(t, f) for t in np.linspace(0, 1, n, endpoint=False)]))


def commission_kernel():
    print("=" * 96)
    print("(b0) KERNEL CROSS-CHECK -- can I reproduce restore.rs's own recorded numbers?")
    print("=" * 96)
    # Structural controls first: if these are not exact, the kernel is wrong.
    ident = keys_taps(0.0)
    print(f"  taps at phase 0            {ident}   identity: "
          f"{np.array_equal(ident, [0, 1, 0, 0])}")
    print(f"  taps sum to one at t=0.25  {keys_taps(0.25).sum():.12f}")
    print(f"  MTF at f=0 (DC)            {keys_mtf(0.37, 0.0):.12f}")
    print()
    # NOTE: the brief quotes these three as 0.25 / 0.35 / 0.50. That is wrong and
    # I checked it rather than adopting it: restore.rs:573 records the middle one
    # at f = 0.40, not 0.35. My first run reported a MISMATCH at 0.35 (0.8211 vs
    # 0.7425) and matched exactly at 0.25 and 0.50, which is the signature of a
    # mislabelled abscissa rather than a wrong kernel.
    print(f"  {'f cyc/px':>9} {'phase-avg MTF':>14} {'restore.rs':>11}")
    for f, want in ((0.25, 0.9402), (0.40, 0.7425), (0.50, 0.6251)):
        got = phase_averaged_mtf(f)
        ok = "MATCH" if abs(got - want) < 5e-4 else "*** MISMATCH ***"
        print(f"  {f:9.2f} {got:14.4f} {want:11.4f}   {ok}")
    print()
    # Second, independent cross-check: reproduce BUILD-SHARP's own headline
    # number rather than re-deriving it. They state that losing 9.36% AMPLITUDE
    # at f=0.35 requires 0.1731 px. If my kernel returns that, it is the same
    # kernel they used and the disagreement above really was only the label.
    lo, hi = 0.0, 0.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if keys_mtf(mid, 0.35) > 1 - 0.0936:
            lo = mid
        else:
            hi = mid
    got = (lo + hi) / 2
    print(f"  BUILD-SHARP: 9.36% amplitude at f=0.35 needs 0.1731 px. "
          f"I get {got:.4f} px  "
          f"{'MATCH' if abs(got - 0.1731) < 5e-4 else '*** MISMATCH ***'}")
    print()


# ----------------------------------------------------------------- (a) split-half
def radial_tangential(u, d):
    """Decompose per-tile displacement into radial and tangential components."""
    r = np.hypot(u[:, 1], u[:, 0])
    ok = r > 1e-9
    uhat = np.zeros_like(u)
    uhat[ok] = u[ok] / r[ok, None]
    that = np.stack([-uhat[:, 1], uhat[:, 0]], axis=1)
    rad = np.einsum("ij,ij->i", d, uhat)
    tan = np.einsum("ij,ij->i", d, that)
    return rad, tan


def split_half(u, d, n=N_SPLIT):
    """Half-to-half disagreement in eps. THIS IS THE NOISE FLOOR."""
    m = len(u)
    out = []
    for _ in range(n):
        idx = RNG.permutation(m)
        a, b = idx[: m // 2], idx[m // 2:]
        try:
            fa = lateral.fit_model(u[a], d[a], robust=True)
            fb = lateral.fit_model(u[b], d[b], robust=True)
        except Exception:
            continue
        out.append((fa["eps"], fb["eps"]))
    out = np.array(out)
    diff = out[:, 0] - out[:, 1]
    # sd of a single half-fit is sd(diff)/sqrt(2); the full-sample estimator uses
    # twice the tiles, so its sd is that again over sqrt(2) -- i.e. sd(diff)/2.
    return {
        "n_splits": len(out),
        "sd_half": float(diff.std(ddof=1) / np.sqrt(2)) * 1e6,
        "sd_full": float(diff.std(ddof=1) / 2.0) * 1e6,
    }


def main():
    commission_kernel()

    stacks = sorted(os.path.basename(p)[len("c1_lateral_"):-len(".json")]
                    for p in glob.glob(os.path.join(common.OUT, "json",
                                                    "c1_lateral_*.json")))
    print("=" * 96)
    print("(a) IS eps_b SIGNAL OR NOISE?  split-half disagreement IS the noise floor")
    print("=" * 96)
    print(f"{'stack':>18} {'ch':>3} {'n':>4} {'eps ppm':>9} {'noise ppm':>10} "
          f"{'|eps|/noise':>12} {'rad px':>8} {'tan px':>8} {'r/t':>6}")
    rows = []
    for st in stacks:
        for ch in ("R", "B", "G2"):
            z = np.load(os.path.join(common.OUT, "json", f"c1_{st}_{ch}.npz"))
            u, d = z["u"], z["d"]
            f = lateral.fit_model(u, d, robust=True)
            sh = split_half(u, d)
            rad, tan = radial_tangential(u, d)
            rr, tt = float(np.sqrt((rad ** 2).mean())), float(np.sqrt((tan ** 2).mean()))
            eps = f["eps"] * 1e6
            snr = abs(eps) / sh["sd_full"] if sh["sd_full"] > 0 else float("nan")
            rows.append({"stack": st, "ch": ch, "n": len(u), "eps_ppm": eps,
                         "noise_ppm": sh["sd_full"], "snr": snr,
                         "rad_px": rr, "tan_px": tt})
            tag = "  <- NULL" if ch == "G2" else ""
            print(f"{st:>18} {ch:>3} {len(u):4d} {eps:9.1f} {sh['sd_full']:10.1f} "
                  f"{snr:12.1f} {rr:8.3f} {tt:8.3f} {rr / tt:6.2f}{tag}")
        print()

    print("  READING. |eps|/noise is how many of its OWN error bars the")
    print("  coefficient stands away from zero. Compare each channel against the")
    print("  G2 null on the same row-group: the null has no chromatic content, so")
    print("  its |eps|/noise is what 'nothing' scores on this instrument.")
    print()

    print("=" * 96)
    print("(b) WHAT THE CORRECTION ACTUALLY SHIFTS BLUE BY, ACROSS THE FIELD")
    print("=" * 96)
    print("  BUILD-SHARP priced the cost at a single 0.039 px. The correction")
    print("  applies eps*r -- zero on axis, largest in the corners.")
    print()
    print(f"  {'field r':>9} {'r plane px':>11} {'blue shift px':>14} "
          f"{'MTF f=.35':>10} {'MTF f=.40':>10} {'amp loss %':>11}")
    for fr in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        r = fr * CORNER_R
        s = EPS_B * r
        m35, m40 = keys_mtf(s % 1.0, 0.35), keys_mtf(s % 1.0, 0.40)
        print(f"  {fr:9.2f} {r:11.0f} {s:14.4f} {m35:10.4f} {m40:10.4f} "
              f"{(1 - m35) * 100:11.2f}")
    print()

    # What shift is needed to lose 9.36% of ENERGY (= 4.79% amplitude)?
    for label, target_amp in (("9.36% ENERGY (caprice)", np.sqrt(1 - 0.0936)),
                              ("9.36% AMPLITUDE", 1 - 0.0936)):
        lo, hi = 0.0, 0.5
        for _ in range(80):
            mid = (lo + hi) / 2
            if keys_mtf(mid, 0.35) > target_amp:
                lo = mid
            else:
                hi = mid
        shift = (lo + hi) / 2
        r_needed = shift / EPS_B
        print(f"  to lose {label:24} needs {shift:.4f} px "
              f"= field radius {r_needed:6.0f} plane px ({r_needed / CORNER_R:.2f} of corner)")

    print()
    print("=" * 96)
    print("(b2) HOW MANY TIMES IS A BLUE PIXEL RESAMPLED?  (read from the code)")
    print("=" * 96)
    cosite = keys_mtf(0.25, 0.35)
    print("  1. alignment gather (align_cmd.rs:1410) -- CA is COMPOSED into this")
    print("     transform, so it changes the PHASE of a resample that already")
    print("     happens. It does not add one.")
    print("  2. image_out.rs:956-957 develop_binned -- a SECOND Keys resample,")
    print("     red by (+0.25,+0.25) and blue by (-0.25,-0.25), for CFA co-siting.")
    print("     GREEN IS NOT RESAMPLED HERE AT ALL (image_out.rs:1293 calls green")
    print("     'the null: it is not resampled').")
    print()
    print(f"  green : 1 resample.   red, blue : 2 resamples.")
    print(f"  co-site phase 0.25 costs, per axis, at f=0.35: MTF {cosite:.4f} "
          f"= {(1 - cosite) * 100:.2f}% amplitude")
    print(f"  applied on BOTH axes: {cosite ** 2:.4f} = {(1 - cosite ** 2) * 100:.2f}% amplitude")
    print()
    print("  This second resample is present in BOTH CA arms, so it cannot by")
    print("  itself produce a CA-on-minus-CA-off difference. What it DOES do is")
    print("  attenuate red and blue but not green, which biases any blue-vs-green")
    print("  HF comparison before CA is considered at all.")
    print()
    print("=" * 96)
    print("(b3) THE HONEST BOUND -- a shift's cost depends on the phase it lands ON")
    print("=" * 96)
    print("  CA is COMPOSED into the alignment transform, so it does not add a")
    print("  resample; it moves an existing one from phase phi to phi+s. The cost")
    print("  is therefore MTF(phi+s) - MTF(phi), NOT MTF(s), and that difference")
    print("  depends entirely on how phi is distributed:")
    print()
    print(f"  {'field r':>9} {'shift px':>9} {'phi=0 (worst)':>15} {'phi~U[0,1) (null)':>19}")
    for fr in (0.2, 0.4, 0.6, 0.8, 1.0):
        s = EPS_B * fr * CORNER_R
        worst = (1 - keys_mtf(s % 1.0, 0.35)) * 100
        phis = np.linspace(0, 1, 501, endpoint=False)
        base = np.mean([keys_mtf(p, 0.35) for p in phis])
        shifted = np.mean([keys_mtf((p + s) % 1.0, 0.35) for p in phis])
        print(f"  {fr:9.2f} {s:9.4f} {worst:14.2f}% {(base - shifted) / base * 100:18.2f}%")
    print()
    print("  The right-hand column is identically zero by construction: shifting a")
    print("  uniform phase distribution gives back a uniform phase distribution.")
    print("  So the true cost lies BETWEEN these columns and is set by how tightly")
    print("  the elected frames' alignment phases cluster near zero. The reference")
    print("  frame is exactly phase 0, so the distribution is NOT uniform and the")
    print("  cost is NOT zero -- but I have not measured the distribution, and")
    print("  without it the left column is an UPPER BOUND, not a prediction.")

    common.dump("c12_blue", {"rows": rows,
                             "cosite_mtf_035": cosite,
                             "eps_b": EPS_B, "corner_r": CORNER_R})
    print("\nwrote c12_blue.json")


if __name__ == "__main__":
    main()
