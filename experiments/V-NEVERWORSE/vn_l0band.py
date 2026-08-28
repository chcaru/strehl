"""Qualify the band that this lane's `sharpness` statistic actually reads.

WHY THIS FILE EXISTS.  ORCH is pricing a merge fix with a three-arm bar whose
second column -- shipping 0.755, plain mean 0.217, flat exponent 1 0.685 --
comes from `vn_plateau.sharpness`, which is the RMS of the FINEST LAPLACIAN
LEVEL (L0).  ORCH's CORRECTION #4 (V-LINEAR, 31eda43a) established that the
signal/noise boundary is a property of the SUBJECT -- 0.17 to 0.48 cyc/px --
and that no lane may score on a fixed band.  Section 9.24 of this lane's
RESULT.md places 0.30-0.35 cyc/px at 99.7-99.9% L0, and both subjects this
lane holds frames for have boundaries BELOW that: coffee-bubbles 0.25,
112MSDCF 0.20.

That is a statement about where L0 LIVES, not about what it MEASURES.  This
file measures what it measures, by applying V-LINEAR's own focus
discriminability -- R = P(tile at its best frame) / P(same tile `far` frames
away) -- to the L0 band itself, within one subject.

  If R ~ 1, L0 is focus-invariant.  The statistic is then pricing GRAIN, and a
  "sharpness cost" quoted from it is a noise number wearing an acuity label.
  If R is large, the column is a real acuity measure and the pricing stands.

Note that BOTH answers are useful and the file is built to be able to return
either: the null plant below establishes that R can read ~1, and the positive
plant establishes that this same code can read R >> 1 on the same pixels.  A
gate that could only confirm one direction would be worthless here.

THE CROSS-CHECK THAT MAKES THE ANSWER TRUSTWORTHY.  This is a reimplementation
of another lane's procedure, on different pixels (this lane's source bundles;
V-LINEAR's linear develops are no longer on disk) and on a different plane
(green, because that is the plane `vn_plateau.sharpness` reads, versus
V-LINEAR's luma709).  Either change could move a boundary, and this project
has already watched one gauge mismatch invert a headline.  So the run FIRST
reproduces V-LINEAR's published per-subject boundary from THESE frames on THIS
plane and reports whether it agrees.  Disagreement there invalidates the L0
verdict and is reported as such rather than explained away.

DECIMATION, AND WHICH WAY IT BIASES.  These bundles are a decimated subset of
the real stack, so a `far` of n/6 bundle-frames spans MORE real frames than
V-LINEAR's did: the defocused reference is further out of focus than theirs.
That INFLATES R.  It is the conservative direction for a FAIL(noise) verdict
and the dangerous direction for a PASS -- so a PASS from this file is not
licensed to overturn a V-LINEAR FAIL, while a FAIL here is strengthened by it.

POWER VS AMPLITUDE.  V-LINEAR's R is a ratio of POWER.  `sharpness` is an
amplitude (a standard deviation).  L0 is therefore scored here as variance so
the verdict thresholds transfer, and the amplitude ratio is printed alongside
as sqrt(R) so the number can be read against the statistic it qualifies.
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "V-LINEAR2"))
sys.path.insert(0, os.path.join(_HERE, "..", "V-LINEAR"))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))

import vn_pyr as VP                                              # noqa: E402
import bandsignal as BS                                          # noqa: E402
import bandsweep as BW                                           # noqa: E402
from h2h2b import band_power                                     # noqa: E402

T = 256
NX = NY = 6
OUT = r"C:\dev\strehl-out\V-NEVERWORSE\l0band"

# V-LINEAR's published boundaries, for the agreement check.  Quoted from
# docs/research/V-LINEAR-BANDS.md so a disagreement is visible rather than
# absorbed.
PUBLISHED = {"coffee-bubbles": 0.25, "112MSDCF": 0.20, "bee-2-cpl": 0.48}


def l0_var(g):
    """Variance of the finest Laplacian level -- the band `sharpness` reads.

    `vn_plateau.sharpness` is lap[0].std() / mean.  Variance is used here so
    the ratio is a POWER ratio and V-LINEAR's PASS/MARGINAL/FAIL thresholds,
    which are defined on power, transfer without reinterpretation.
    """
    lap, _ = VP.lap_pyr(np.asarray(g, np.float64), 1)
    return float(lap[0].var())


def _c3(a):
    return np.repeat(np.asarray(a, np.float64)[:, :, None], 3, axis=2)


def measure(frames, far=None, label=""):
    """Per-tile focus discriminability for every FINE band and for L0.

    Follows V-LINEAR's bandsweep.sweep: pick each tile's best frame by the
    PREREGISTERED selection band 0.05-0.20, then compare against that tile at
    best +/- far.  Selection and scoring use the same plane, which is the
    gauge point -- a selection made on one plane and scored on another is the
    mismatched-gauge defect that inverted this project's sharpness metric.
    """
    n = len(frames)
    H, W = frames[0].shape[:2]
    if far is None:
        far = max(2, round(n / 6))
    margin = int(min(700, max(0, (min(H, W) - T) // 4)))
    ys = np.linspace(margin, H - margin - T, NY).astype(int)
    xs = np.linspace(margin, W - margin - T, NX).astype(int)
    pos = [(int(y), int(x)) for y in ys for x in xs]

    bands = list(BS.FINE)
    lo = np.array([b[0] for b in bands] + [BS.SEL_LO])
    hi = np.array([b[1] for b in bands] + [BS.SEL_HI])
    nsel = len(bands)

    power = np.zeros((n, len(pos), len(bands) + 1))
    l0 = np.zeros((n, len(pos)))
    for a in range(n):
        f = frames[a]
        for i, (y, x) in enumerate(pos):
            crop = np.asarray(f[y:y + T, x:x + T, :3], np.float64)
            # GREEN PLANE, not luma709.  `band_power` takes a 2-D plane, and
            # V-LINEAR feeds it luma709.  This lane feeds it channel 1 because
            # that is the plane `vn_plateau.sharpness` and `vn_pyr.merge` both
            # read; selecting and scoring on the same plane is the whole
            # point.  The boundary agreement check is what proves the plane
            # swap did not move the answer.
            bp = band_power(crop[:, :, 1], lo, hi)
            power[a, i] = np.nan if bp is None else bp
            l0[a, i] = l0_var(crop[:, :, 1])
        if label:
            sys.stderr.write("\r  %s: frame %d/%d   " % (label, a + 1, n))
    if label:
        sys.stderr.write("\n")

    sel = power[:, :, nsel]
    best = np.nanargmax(sel, axis=0)

    pf, pd, pf0, pd0, kept = [], [], [], [], 0
    for i in range(len(pos)):
        b = int(best[i])
        if b < far // 4 + 1 or b > n - far // 4 - 2:
            continue
        ref = [r for r in (b - far, b + far) if 0 <= r < n]
        if not ref:
            continue
        kept += 1
        pf.append(power[b, i, :nsel])
        pd.append(power[ref, i, :nsel].mean(0))
        pf0.append(l0[b, i])
        pd0.append(l0[ref, i].mean())

    if kept < 4:
        return None

    pf = np.array(pf)
    pd = np.array(pd)
    out = {"n_frames": n, "far": int(far), "tiles_kept": kept,
           "tiles_total": len(pos), "bands": {}}
    for j, (a, b) in enumerate(bands):
        r, cl, ch = BS.ratio_ci(pf[:, j], pd[:, j])
        out["bands"]["%.2f-%.2f" % (a, b)] = {
            "R": r, "ci_lo": cl, "ci_hi": ch, "verdict": BS.verdict(r, cl)}
    r0, c0, h0 = BS.ratio_ci(np.array(pf0), np.array(pd0))
    out["L0"] = {"R": r0, "ci_lo": c0, "ci_hi": h0,
                 "verdict": BS.verdict(r0, c0), "R_amplitude": float(np.sqrt(r0))}
    out["boundary"] = BW.boundary(out)
    return out


# ------------------------------------------------------------- commissioning

def _scene(rng, h, w):
    """Broadband texture with real content at every scale L0 can see."""
    s = np.zeros((h, w))
    for k, amp in ((1, 60.0), (2, 90.0), (4, 120.0), (8, 160.0), (16, 200.0)):
        c = rng.normal(0, amp, (max(2, h // k), max(2, w // k)))
        s += np.kron(c, np.ones((k, k)))[:h, :w]
    return s - s.min() + 2000.0


def _blur(a, sigma):
    if sigma <= 0:
        return a.copy()
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, sigma)


def _stack_focus(rng, n, h, w, noise):
    """A genuine through-focus stack: L0 content really does peak at focus."""
    base = _scene(rng, h, w)
    out = []
    for i in range(n):
        sigma = abs(i - (n - 1) / 2.0) * 0.55
        f = _blur(base, sigma) + rng.normal(0, noise, (h, w))
        out.append(_c3(f))
    return out


def _stack_grain(rng, n, h, w, noise):
    """Grain only: ONE fixed scene, no focus variation, independent noise.

    The selection band still picks a 'best' frame for every tile, but it is
    picking on noise.  If this reads R >> 1 at L0, the statistic is measuring
    its own selection rather than focus, and the real-data verdict would be
    uninterpretable -- which is exactly why this arm gates the run.
    """
    base = _scene(rng, h, w)
    return [_c3(base + rng.normal(0, noise, (h, w))) for _ in range(n)]


def commission():
    rng = np.random.default_rng(20260828)
    n, h, w = 21, 1024, 1024
    ok = True

    foc = _stack_focus(rng, n, h, w, 30.0)
    gra = _stack_grain(rng, n, h, w, 30.0)

    # INERTNESS GUARD.  A plant that did not land looks exactly like a plant
    # that had no effect.  These two stacks must differ in the one property
    # under test -- through-focus variation of L0 -- or the gate below is
    # measuring nothing.
    v_foc = [l0_var(f[:, :, 1]) for f in foc]
    v_gra = [l0_var(f[:, :, 1]) for f in gra]
    spread_foc = max(v_foc) / min(v_foc)
    spread_gra = max(v_gra) / min(v_gra)
    if not (spread_foc > 3.0 and spread_gra < 1.5):
        raise AssertionError(
            "PLANT IS INERT: L0 spread focus=%.4f grain=%.4f -- the focus "
            "stack must vary L0 across frames and the grain stack must not"
            % (spread_foc, spread_gra))
    print("  plant landed: L0 frame-to-frame spread  focus %.3fx  grain %.3fx"
          % (spread_foc, spread_gra))

    r_foc = measure(foc, label="commission focus")
    r_gra = measure(gra, label="commission grain")

    a = r_foc["L0"]
    print("  POSITIVE (real through-focus L0): R = %.4f  [%.4f, %.4f]  %s"
          % (a["R"], a["ci_lo"], a["ci_hi"], a["verdict"]))
    if a["verdict"] != "PASS":
        print("    FAIL: this code cannot detect focus-dependent L0 at all")
        ok = False

    b = r_gra["L0"]
    print("  NULL (grain only, no focus variation): R = %.4f  [%.4f, %.4f]  %s"
          % (b["R"], b["ci_lo"], b["ci_hi"], b["verdict"]))
    if b["R"] >= 1.3:
        print("    FAIL: selection on noise alone reaches the MARGINAL "
              "threshold -- a real-data R could not be attributed to focus")
        ok = False

    # SEPARATION.  Both arms individually landing is not enough; the
    # instrument must SEPARATE them, or a real subject sitting between the two
    # could not be assigned to either.
    sep = a["R"] / b["R"]
    print("  SEPARATION positive/null: %.4fx" % sep)
    if sep < 3.0:
        print("    FAIL: arms not separated")
        ok = False

    print("  COMMISSIONING: %s" % ("PASS" if ok else "REFUSED"))
    return ok


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] == "--commission":
        sys.exit(0 if commission() else 1)

    subj = argv[0]
    green = "--green" in argv
    if not commission():
        print("refusing to measure: commissioning failed")
        sys.exit(1)

    import vn_qband as QB
    frames, gauge = QB.load_frames(subj, force_green=green)
    print("\n%s: %d frames  gauge=%s" % (subj, len(frames), gauge))

    rec = measure(frames, label=subj)
    if rec is None:
        print("refusing: too few usable tiles")
        sys.exit(1)
    rec["subject"] = subj
    rec["gauge"] = gauge

    print("\n  per-band focus discriminability (this lane's pixels, green "
          "plane):")
    for k, v in rec["bands"].items():
        print("    %-12s R=%8.4f  [%7.4f, %8.4f]  %s"
              % (k, v["R"], v["ci_lo"], v["ci_hi"], v["verdict"]))

    pub = PUBLISHED.get(subj)
    mine = rec["boundary"]
    agree = (pub is not None and abs(mine - pub) < 1e-9)
    rec["published_boundary"] = pub
    rec["boundary_agrees"] = bool(agree)
    print("\n  BOUNDARY  mine %.2f   V-LINEAR published %s   %s"
          % (mine, "%.2f" % pub if pub else "n/a",
             "AGREE" if agree else "DISAGREE"))

    a = rec["L0"]
    print("\n  L0 (the band `vn_plateau.sharpness` reads):")
    print("    R(power) = %.4f  [%.4f, %.4f]   R(amplitude) = %.4f   %s"
          % (a["R"], a["ci_lo"], a["ci_hi"], a["R_amplitude"], a["verdict"]))

    if not agree:
        print("\n  VERDICT WITHHELD: this reimplementation does not reproduce "
              "V-LINEAR's published boundary on this subject, so its L0 "
              "reading is not licensed either.")
    elif a["verdict"] == "FAIL(noise)":
        print("\n  VERDICT: L0 is NOT focus-discriminable on this subject. "
              "`sharpness` prices GRAIN here, not acuity.")
    else:
        print("\n  VERDICT: L0 carries focus-dependent signal on this "
              "subject (%s)." % a["verdict"])

    os.makedirs(OUT, exist_ok=True)
    tag = subj + ("-green" if green else "")
    p = os.path.join(OUT, tag + ".json")
    with open(p, "w") as fh:
        json.dump(rec, fh, indent=1)
    print("\nwrote %s" % p)


if __name__ == "__main__":
    main()
