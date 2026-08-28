"""Is V-SPEED's sharpness column readable as acuity, or is it counting grain?

WHY THIS EXISTS.  ORCH warned that "raw band power counts noise as sharpness"
-- one lane read +0.142 sharper raw and -0.134 softer once noise-corrected, a
sign flip.  I flagged my own sharp.py as untrustworthy under that warning and
told ORCH so.  This file checks whether that self-flag was actually correct
rather than leaving a caveat standing on an assumption.

THE STRUCTURAL ARGUMENT, which is suggestive and not sufficient.  sharp.py is
not a band power.  It is the MEDIAN of |Laplacian| over the most textured
decile.  A band power is a sum of squares and accumulates noise power
linearly, so it rises with grain by construction.  A median over
high-signal sites is robust: it moves only if grain becomes comparable to the
signal AT those sites, and the sites were chosen to be the ones where signal
is largest.  So the two statistics have different failure modes and ORCH's
warning does not transfer automatically.  It might still bite, because the
discrete Laplacian's gain rises monotonically to Nyquist (|H| = 2.618 at 0.30
cyc/px, 4.000 at 0.50), so the operator weights most heavily exactly the
frequencies most likely to be grain.

THE MEASUREMENT, which is what actually settles it.  For each arm pair:
measure each arm's grain, then inject white noise into the quieter arm until
its grain MATCHES the noisier one, and re-measure sharpness on identical
sites.  The sharpness change produced by that injection is the part of the
observed gap that grain can account for.  If the observed gap is much larger,
it is acuity; if comparable, it is not readable.

Injection uses a binary search on grain rather than a calibrated formula, so
no assumption about how the high-pass residual scales has to be correct.

SUBJECT QUALIFICATION.  ORCH's rule: no sharpness claim without naming the
band and the subject's qualification at it.  sharp.py is a spatial-domain
operator and has no band, so what is named here instead is the operator's
frequency weighting (above) and the subject's qualification as measured by
V-LINEAR's depthqual.py at 0.30-0.40:

    bee-1-cpl                  N=299  R=4.732  PASS
    dry-erase-marker-head-cpl  N=300  R=4.877  PASS

Both are deep AND qualified, which is why ORCH named them as the two subjects
on which a depth claim may be scored.  They are the only two subjects audited
here for that reason.
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sharp import luma, sharpness, subject_mask, textured  # noqa: E402

ROOT = pathlib.Path(r"D:\strehl-out\V-SPEED-HALO\sweep")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")

# Subject -> (frame count, R at 0.30-0.40, verdict) from V-LINEAR depthqual.py
# at commit dc8c16b5.  Quoted, not re-derived here; this lane did not measure
# band qualification and does not claim to.
QUALIFIED = {
    "bee-1-cpl": (299, 4.732, "PASS"),
    "dry-erase-marker-head-cpl": (300, 4.877, "PASS"),
}

# Subjects this lane quotes sharpness on that V-LINEAR's table does not cover.
# Under ORCH's rule these are UNLICENSED as stated -- the qualification is not
# unknown-and-probably-fine, it is simply not measured, and this lane did not
# measure it.  They are audited anyway because the grain confound can be
# priced without knowing the band, and because the largest sharpness number
# this lane reports (-81.4% for the no-selection floor on tweezers-cpl) sits
# here and runs in the CONFOUNDABLE direction: a plain mean of N frames is
# roughly sqrt(N) times quieter, so a quieter arm reading softer is exactly
# the case the verdict rule refuses to clear on magnitude alone.
UNLICENSED = {
    "tweezers-cpl": (100, float("nan"), "UNKNOWN"),
    "lead-1-cpl": (123, float("nan"), "UNKNOWN"),
    "coffee-bean": (105, float("nan"), "UNKNOWN"),
    "leaf-2-cpl": (182, float("nan"), "UNKNOWN"),
}

ALL = dict(QUALIFIED)
ALL.update(UNLICENSED)

HP_SIGMA = 2.0     # high-pass scale for the grain estimator
GRAIN_TOL = 0.02   # binary search stops within 2% of the target grain


def grain(y, bg):
    """Robust high-frequency fluctuation over background pixels, in DN.

    MAD-based rather than std-based so that a few dust specks or a hot pixel
    in the background do not set the number.  Measured on the high-pass
    residual so that a lighting gradient across the background -- which this
    corpus demonstrably has, several subjects being lighting arches -- is not
    counted as grain.
    """
    r = y - gaussian_filter(y, HP_SIGMA)
    v = r[bg]
    return float(1.4826 * np.median(np.abs(v - np.median(v))))


def inject_to_match(y, bg, target, rng, iters=24):
    """Add white noise until grain(y) == target. Returns (noisy, sigma, got).

    Binary search on the injected sigma. No calibration constant is assumed:
    the loop measures the grain it actually produced.
    """
    g0 = grain(y, bg)
    if g0 >= target:
        return y, 0.0, g0
    lo, hi = 0.0, max(4.0 * target, 16.0)
    best, best_s, best_g = y, 0.0, g0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        cand = y + rng.normal(0.0, mid, y.shape).astype(np.float32)
        g = grain(cand, bg)
        best, best_s, best_g = cand, mid, g
        if abs(g - target) / target <= GRAIN_TOL:
            break
        if g < target:
            lo = mid
        else:
            hi = mid
    return best, best_s, best_g


def verdict(d_obs, d_grain):
    """Could the grain difference have MANUFACTURED the observed effect?

    A magnitude gate alone throws away the sign, and the sign is the whole
    question.  ORCH's warning is about a specific failure: a noisier arm being
    CREDITED with acuity it does not have.  That requires grain to push the
    observed effect in the SAME direction it was observed.  When grain pushes
    the opposite way, the observed effect cannot be a grain artifact no matter
    how small the margin -- the confound is opposing the finding, so the
    uncorrected number is the conservative one and correcting it strengthens
    the conclusion rather than threatening it.

    Three outcomes, and they partition every scored pair:
      OPPOSED    grain pushes against the observed effect. Safe; the
                 noise-corrected effect is LARGER than reported.
      CLEAN      grain pushes the same way but is too small to account for
                 the effect (< 1/3 of it).
      CONFOUNDED grain pushes the same way and is comparable. Not readable.
    """
    if d_obs == 0.0:
        return "CONFOUNDED"
    if d_obs * d_grain < 0.0:
        return "OPPOSED"
    return "CLEAN" if abs(d_obs) > 3.0 * abs(d_grain) else "CONFOUNDED"


def commission_verdict():
    """The verdict logic must survive cases that flip its CONCLUSION.

    Commissioning the estimator is not enough: the estimator can be perfect
    and the rule that turns its number into a verdict still wrong.  These
    arms plant known (observed, grain) pairs and require the verdict, so a
    change that reverses the rule is caught rather than merely perturbing a
    printed value.
    """
    cases = [
        # d_obs, d_grain, want, why
        (-2.868, +0.529, "OPPOSED",
         "bee-1-cpl as measured: noisier arm reads SOFTER"),
        (-1.593, +0.813, "OPPOSED",
         "dry-erase as measured: same, smaller margin"),
        (+3.000, +0.100, "CLEAN",
         "same sign, grain 30x too small to account for it"),
        (+1.000, +0.900, "CONFOUNDED",
         "same sign, grain nearly the whole effect -- the ORCH failure"),
        (+2.000, +0.800, "CONFOUNDED",
         "same sign, grain 40% of it -- inside the 3x gate"),
        (-3.000, -1.500, "CONFOUNDED",
         "both negative: a QUIETER arm reading softer IS confoundable"),
        (0.000, +0.500, "CONFOUNDED", "no observed effect to defend"),
    ]
    ok, fail = 0, []
    print("commissioning noiseaudit.py verdict rule\n")
    for d_obs, d_grain, want, why in cases:
        got = verdict(d_obs, d_grain)
        good = got == want
        print("  [%s] obs=%+7.3f grain=%+6.3f -> %-11s want %-11s  %s"
              % ("PASS" if good else "FAIL", d_obs, d_grain, got, want, why))
        if good:
            ok += 1
        else:
            fail.append(why)
    print("\nverdict commission: %d/%d %s"
          % (ok, len(cases), "PASS" if not fail else "FAIL"))
    return 0 if not fail else 1


def commission():
    """The grain estimator must recover a known sigma and ignore texture."""
    rng = np.random.default_rng(11)
    n = 700
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    flat = np.full((n, n), 30000.0, np.float32)
    bg = np.ones((n, n), bool)

    ok, fail = 0, []

    def arm(name, got, want, lo, hi):
        nonlocal ok
        good = lo <= got <= hi
        print("  [%s] %-46s %8.2f  want %s"
              % ("PASS" if good else "FAIL", name, got, want))
        if good:
            ok += 1
        else:
            fail.append(name)

    print("commissioning noiseaudit.py grain estimator\n")

    # 1-3. Recovery of a known injected sigma. The high-pass residual of white
    # noise is a fixed fraction of the input sigma, so this checks LINEARITY
    # and that the fraction is stable, not that it equals 1.
    ratios = []
    for sg in [10.0, 40.0, 160.0]:
        g = grain(flat + rng.normal(0.0, sg, flat.shape).astype(np.float32), bg)
        ratios.append(g / sg)
        arm("recovers sigma %5.1f DN (ratio to input)" % sg, g / sg,
            "0.5..1.0", 0.5, 1.0)
    spread = max(ratios) / min(ratios)
    arm("recovery ratio is stable across 16x sigma", spread,
        "< 1.05", 0.0, 1.05)

    # 4. Zero noise must read ~zero, or every comparison is offset.
    arm("noiseless flat field reads ~0 DN", grain(flat, bg), "< 1.0", -1e9, 1.0)

    # 5. THE ONE THAT MATTERS. A lighting gradient is not grain. Several
    # subjects in this corpus are lighting arches; if the estimator counted a
    # gradient it would report those as noisy and the audit would be wrong in
    # exactly the place it is being applied.
    ramp = 30000.0 + 4000.0 * (xx / n)
    arm("a 4000 DN lighting ramp is not counted as grain",
        grain(ramp.astype(np.float32), bg), "< 1.0", -1e9, 1.0)

    # 6. Coarse texture is not grain either.
    tex = (30000.0 + 2000.0 * np.sin(xx / 9.0) * np.sin(yy / 9.0)).astype(np.float32)
    arm("coarse texture is largely not counted as grain",
        grain(tex, bg), "< 60", -1e9, 60.0)

    # 7. The search must actually hit its target.
    noisy_ref = flat + rng.normal(0.0, 55.0, flat.shape).astype(np.float32)
    tgt = grain(noisy_ref, bg)
    _, s_used, got = inject_to_match(flat.copy(), bg, tgt, rng)
    arm("injection reaches the target grain (rel. err)",
        abs(got - tgt) / tgt, "<= 0.02", -1e9, GRAIN_TOL)

    print("\ngrain commission: %d/8 %s" % (ok, "PASS" if not fail else "FAIL"))
    if fail:
        print("FAILED: " + ", ".join(fail))
    return 0 if not fail else 1


def audit(subject, arm_a="baseline", arm_b="bands5"):
    pa, pb = ROOT / subject / f"{arm_a}.tiff", ROOT / subject / f"{arm_b}.tiff"
    if not pa.exists() or not pb.exists():
        return {"subject": subject, "status": "SKIPPED",
                "why": f"missing {arm_a}.tiff or {arm_b}.tiff"}

    ya, yb = luma(tifffile.imread(str(pa))), luma(tifffile.imread(str(pb)))
    if ya.shape != yb.shape:
        return {"subject": subject, "status": "SKIPPED", "why": "shape mismatch"}

    # Sites and background from arm A ONLY, then reused. Re-segmenting per arm
    # would let an arm move its own measurement window, so a change in the
    # number could be a change in acuity or a change in where it was read.
    subj = subject_mask(ya)
    sites = textured(ya, subj)
    bg = ~subj

    sa, sb = sharpness(ya, sites), sharpness(yb, sites)
    ga, gb = grain(ya, bg), grain(yb, bg)
    d_obs = 100.0 * (sb - sa) / sa

    # Bring the quieter arm up to the noisier arm's grain and re-measure.
    rng = np.random.default_rng(3)
    if ga < gb:
        noisy, sig, got = inject_to_match(ya, bg, gb, rng)
        d_grain = 100.0 * (sharpness(noisy, sites) - sa) / sa
        who = arm_a
    else:
        noisy, sig, got = inject_to_match(yb, bg, ga, rng)
        d_grain = 100.0 * (sb - sharpness(noisy, sites)) / sa
        who = arm_b

    readable = verdict(d_obs, d_grain)
    return {"subject": subject, "status": "SCORED",
            "n": ALL[subject][0], "R": ALL[subject][1],
            "qual": ALL[subject][2],
            "sharp_a": round(sa, 2), "sharp_b": round(sb, 2),
            "grain_a": round(ga, 2), "grain_b": round(gb, 2),
            "noised": who, "sigma_injected": round(sig, 2),
            "grain_reached": round(got, 2),
            "d_obs_pct": round(d_obs, 3), "d_grain_pct": round(d_grain, 3),
            "d_corrected_pct": round(d_obs - d_grain, 3),
            "verdict": readable}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    ap.add_argument("--arms", nargs=2, default=["baseline", "bands5"])
    ap.add_argument("--subjects", nargs="*")
    a = ap.parse_args()
    if a.commission:
        return commission() | commission_verdict()

    rows = [audit(s, *a.arms) for s in (a.subjects or list(ALL))]
    print("grain-vs-acuity audit: %s vs %s" % (a.arms[0], a.arms[1]))
    print("sharp.py has NO band; operator gain 2.618 at 0.30 cyc/px, 4.000 at "
          "Nyquist.\nQualification quoted from V-LINEAR depthqual.py "
          "(dc8c16b5) at band 0.30-0.40.\n")
    hdr = ("subject", "N", "R", "qual", "grain A", "grain B",
           "d obs %", "d grain %", "d corr %", "verdict")
    print("| %-26s | %4s | %6s | %5s | %7s | %7s | %8s | %9s | %8s | %-10s |" % hdr)
    print("|" + "|".join(["-" * w for w in
                          [28, 6, 8, 7, 9, 9, 10, 11, 10, 12]]) + "|")
    counts = {"OPPOSED": 0, "CLEAN": 0, "CONFOUNDED": 0}
    skipped = 0
    for r in rows:
        if r["status"] != "SCORED":
            skipped += 1
            print("| %-26s | SKIPPED: %s" % (r["subject"], r["why"]))
            continue
        counts[r["verdict"]] += 1
        print("| %-26s | %4d | %6s | %7s | %7.2f | %7.2f | %+8.3f | %+9.3f | %+8.3f | %-10s |"
              % (r["subject"], r["n"], ("%.3f" % r["R"] if r["R"] == r["R"] else "n/a"), r["qual"], r["grain_a"],
                 r["grain_b"], r["d_obs_pct"], r["d_grain_pct"],
                 r["d_corrected_pct"], r["verdict"]))
    print("\n%d opposed + %d clean + %d confounded + %d skipped = %d subjects"
          % (counts["OPPOSED"], counts["CLEAN"], counts["CONFOUNDED"],
             skipped, len(rows)))
    print("OPPOSED means the grain difference pushes AGAINST the observed "
          "effect,\nso the effect cannot be a grain artifact and 'd corr' is "
          "the larger, truer number.")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "noiseaudit.json").write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

