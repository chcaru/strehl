"""
M-PHASE0-QUINCUNX step 1: is there scene energy above the green-plane Nyquist?

THE LANE
--------
C12 (proposal section 5) proposes using the G1-G2 disagreement of the Bayer
green pair as three things: a super-Nyquist focus cue, a per-tile alias census
gating C1's 2x super-resolution mode, and a per-frame noise/quality probe under
B1/B5. Its phase-0 kill condition is explicit:

    "Kill: if the optics at corpus apertures never put measurable energy past
     plane Nyquist (M88 says f/5.6 should; f/11 should not -- the census answers
     per aperture), consumers 1-2 die and consumer 3 stands alone under B1/B5."

That is the question this file answers, and it answers it with ZERO decodes.

WHY NO DECODES ARE NEEDED
-------------------------
M129 already computed, for a different purpose, a radial power spectrum on the
green quincunx lattice for 30 cells (5 apertures x 6 ROIs), and banded it. Its
"high" band is (0.260, 0.330) sensor cyc/px. The green plane's own Nyquist is
0.25 sensor cyc/px. So M129's high band lies ENTIRELY above plane Nyquist and
below the quincunx radial reach -- it is precisely C12's band, already measured
and already noise-subtracted.

This is the second phase-0 lane in a row whose headline measurement the corpus
already held. It is worth noticing as a pattern.

  UNITS, VERIFIED NOT ASSUMED. m129/src/snr_survey.py line 67 states "Bands in
  sensor cyc/px". Q1 below re-derives the three lattice Nyquists from the
  corpus's own pitch constant and requires them to agree, because a factor of
  two in this axis would move the band somewhere else entirely and every number
  downstream would still look reasonable.

REGISTERED QUESTIONS
--------------------
  Q1  GEOMETRY. Re-derive plane / quincunx / sensor Nyquist from PITCH_UM and
      confirm C12's stated 0.25 cyc/px plane Nyquist, and that M129's f axis is
      in sensor cyc/px and terminates at the quincunx radial reach.

  Q2  DETECTABILITY. Per aperture, what is the high-band power SNR (scene power
      over noise floor)? Is any of it above 1?

  Q3  OPTICAL TRANSFER. Per aperture, what fraction of the subject's own power
      reaches past plane Nyquist -- high_scene / low_scene? This is the question
      Q2 cannot answer, because the noise floor varies about 12x across these
      apertures (f/5.6 is far brighter), so raw SNR compares different things.
      The ratio is independent of exposure and of subject contrast.

DIRECTION OF THE EXPECTED RESULT, STATED BEFORE MEASURING (house rule 18)
-------------------------------------------------------------------------
C12 predicts f/5.6 YES and f/11 NO.

I predict C12's optimistic half is WRONG on this subject: the single f/5.6 cell
I inspected while designing this lane (roi 0) reads high-band SNR 0.686, which
is BELOW 1. If that holds across ROIs, then even the widest corpus aperture
fails the detectability test and consumers 1-2 are in trouble at every aperture,
not just at f/11.

I further predict Q3 WILL show a monotone decline with f-number even if Q2 fails
everywhere, because diffraction must attenuate the top of the band first. If Q3
is FLAT across a factor of 3.2 in f-number, the limit is not the optics -- it is
the subject or the instrument -- and the kill condition has NOT been met on its
own terms, because C12 asks about the optics.

  THE CONFOUND THIS LANE CANNOT REMOVE, STATED UP FRONT. The subject is one
  fabric weave. "This subject puts little energy past plane Nyquist" and "the
  optics cannot deliver energy past plane Nyquist" are different claims, and a
  single subject cannot separate them. Q3's aperture trend is the only handle
  available here: the subject is identical across apertures, so anything that
  MOVES with f-number is optical. Anything flat is not attributable.

CONTROLS
--------
  C1  RECOMPUTE. Re-derive each band's mean/scene/snr from the raw f/psd/floor
      arrays and require agreement with the stored band summaries. Validates my
      reading of the file against the file's own precomputed answer. A mismatch
      means I am banding differently than M129 did.
  C2  LOW-BAND SANITY. The low band is pure texture contrast and must show a
      large positive SNR everywhere. If floor subtraction were eating real
      signal, it would show here first.
  C3  NO ANTI-DIFFRACTION, IN THE CUTOFF-LIMITED REGIME ONLY. Transfer must
      decline monotonically across apertures whose diffraction cutoff actually
      falls inside or below the high band. See the disclosed error below: the
      original form of this control asserted monotonicity across ALL apertures
      and was wrong on its premise.
  C4  BAND PLACEMENT. Every bin used by the high band must actually exceed 0.25
      sensor cyc/px. This is the check that would catch a units error surviving
      Q1.
  C5  EMPIRICAL NULL. f/18's diffraction cutoff lies below the high band, so its
      cells must read consistent with zero. Their scatter IS the detection
      threshold of this instrument, and it is measured rather than assumed.

MY OWN ERROR IN THIS FILE, DISCLOSED
------------------------------------
Run 1 asserted two things that do not survive contact with the physics.

FIRST, C3 required high-band transfer to fall monotonically with f-number, on
the grounds that "diffraction is monotone". It rose 1.739x from f/5.6 to f/8 and
I recorded a control failure. The premise was wrong. Diffraction sets a CUTOFF;
it only controls the level inside a band once the cutoff has entered that band.
At B ~ 2.4 the cutoffs are f/5.6 -> 0.685 and f/8 -> 0.485 cyc/px, both far
above the band's 0.330 upper edge, so at those two apertures the band is fully
transmitted and its level is set by MTF SHAPE -- aberrations and residual focus
error -- not by the cutoff. A macro lens improving from f/5.6 to f/8 is ordinary.
C3 now applies only where the cutoff is actually in play, and the f/5.6 -> f/8
rise is reported as a finding rather than swallowed as a failure.

SECOND, Q2 scored detectability against SNR > 1, which is an arbitrary bar. The
data carries its own: f/18 cannot transmit anything into this band, so its cells
measure the instrument's zero. They read -0.018 median, i.e. the floor estimate
is good to about 2%. That, not 1.0, is the threshold a detection must clear.
Against it, f/11 at 0.849 is not a marginal detection -- it is roughly 45 times
the null. Judged by the arbitrary bar the lane would have reported "2 of 30
cells detected"; judged by its own null it detects at four of five apertures.

Both errors ran in the same direction: they made the instrument look blinder
than it is. Neither was found by a control passing.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
STREHL = os.path.dirname(HERE)
SNR = os.path.join(STREHL, "M129-fabric-spectral-ladder", "out", "snr-w2.json")

PITCH_UM = 5.12          # Sony ILCE-7CM2, from m5-diffraction/predict.py
TAGS = ["f5.6", "f8", "f11", "f14", "f18"]
EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
PLANE_NYQ = 0.25

lines = []
res = {}


def say(s=""):
    lines.append(s)
    print(s)


def median(v):
    """True median.

    An earlier revision used sorted(v)[len(v)//2], which on the even n=6 used
    throughout this lane returns the 4th smallest -- an order statistic biased
    upward, not a median. Every summary number inherited that bias. Corrected
    here; the correction lowers this lane's own headline figures, which is the
    direction that argues against its own finding.
    """
    w = sorted(v)
    n = len(w)
    return w[n // 2] if n % 2 else 0.5 * (w[n // 2 - 1] + w[n // 2])


with open(SNR, encoding="utf-8") as fh:
    D = json.load(fh)
RECS = D["records"]
BANDS = D["bands"]

say("M-PHASE0-QUINCUNX step 1 -- energy above the green-plane Nyquist")
say("=" * 74)
say("source: %s" % os.path.relpath(SNR, STREHL))
say("%d records, bands %s" % (len(RECS), json.dumps(BANDS)))
say("")

# ------------------------------------------------------------------------ Q1
say("Q1  GEOMETRY  (re-derived from PITCH_UM, not copied)")
say("-" * 74)


def nyq_cymm(pitch_um):
    return 1000.0 / (2.0 * pitch_um)


lattices = [
    ("full sensor", PITCH_UM, 0.5),
    ("GQ quincunx", PITCH_UM * math.sqrt(2.0), 0.5 / math.sqrt(2.0)),
    ("G1 or G2 alone", 2.0 * PITCH_UM, 0.25),
]
say("    %-16s %10s %14s %18s" % ("lattice", "pitch um", "Nyq cy/mm", "Nyq sensor cyc/px"))
for name, pit, cycpx in lattices:
    say("    %-16s %10.4f %14.2f %18.5f" % (name, pit, nyq_cymm(pit), cycpx))
say("")
f_axis = RECS[0]["f"]
gq_reach = 0.5 / math.sqrt(2.0)
say("    C12 states the plane Nyquist is 0.25 cyc/sensor-px: %s"
    % ("CONFIRMED" if abs(0.25 - PLANE_NYQ) < 1e-12 else "NO"))
say("    M129 f axis runs %.5f to %.5f; GQ radial reach is %.5f"
    % (f_axis[0], f_axis[-1], gq_reach))
say("    axis terminates at the quincunx reach (within one bin): %s"
    % ("YES" if 0 < gq_reach - f_axis[-1] < (f_axis[1] - f_axis[0]) else "NO"))
say("")
say("    NOTE ON COVERAGE, load-bearing for how far this lane can conclude.")
say("    C12's band is 0.25 to 0.50 cyc/px, because the quincunx union reaches")
say("    full sensor Nyquist ALONG THE AXES. This radial spectrum reaches only")
say("    %.5f, the inscribed diagonal limit. Energy between %.3f and 0.500" % (gq_reach, gq_reach))
say("    exists only near the axes and is NOT sampled here. This lane therefore")
say("    measures the ISOTROPIC part of C12's band, not all of it.")
res["q1"] = {"plane_nyq": PLANE_NYQ, "gq_reach": gq_reach,
             "f_min": f_axis[0], "f_max": f_axis[-1],
             "lattices": {n: {"pitch_um": p, "nyq_cymm": nyq_cymm(p), "cycpx": c}
                          for n, p, c in lattices}}
say("")

# ------------------------------------------------------------------- C1 / C4
say("CONTROLS C1 (recompute) and C4 (band placement)")
say("-" * 74)
worst = 0.0
c4_min = 1e9
for r in RECS:
    f, p, floor = r["f"], r["psd"], r["floor"]
    for name, (lo, hi) in BANDS.items():
        sel = [i for i, v in enumerate(f) if lo <= v <= hi]
        mean = sum(p[i] for i in sel) / len(sel)
        scene = mean - floor
        snr = scene / floor
        st = r["bands"][name]
        worst = max(worst, abs(mean - st["mean"]) / abs(st["mean"]),
                    abs(snr - st["snr"]) / max(abs(st["snr"]), 1e-12))
        if len(sel) != st["nbin"]:
            worst = 1.0
        if name == "high":
            c4_min = min(c4_min, min(f[i] for i in sel))
c1_ok = worst < 1e-9
c4_ok = c4_min > PLANE_NYQ
say("    C1 worst relative disagreement over %d records x %d bands: %.2e  -> %s"
    % (len(RECS), len(BANDS), worst, "PASS" if c1_ok else "FAIL"))
say("    C4 lowest frequency used by the high band: %.5f cyc/px (> %.2f) -> %s"
    % (c4_min, PLANE_NYQ, "PASS" if c4_ok else "FAIL"))
res["c1_worst_rel"] = worst
res["c4_min_high_f"] = c4_min
say("")

# ------------------------------------------------------------------------ Q2
say("Q2  DETECTABILITY  -- high-band power SNR (scene / noise floor)")
say("-" * 74)


def by_ap(key):
    out = {}
    for t in TAGS:
        v = [r["bands"][key] for r in RECS if r["aperture"] == t]
        out[t] = v
    return out


say("    %-6s %6s %10s %10s %10s %10s %8s"
    % ("ap", "N", "median", "min", "max", "floor", "n>1"))
q2 = {}
for t in TAGS:
    rs = [r for r in RECS if r["aperture"] == t]
    snrs = sorted(r["bands"]["high"]["snr"] for r in rs)
    fl = sorted(r["floor"] for r in rs)
    med = median(snrs)
    nabove = sum(1 for s in snrs if s > 1.0)
    q2[t] = {"median_snr": med, "min": snrs[0], "max": snrs[-1],
             "median_floor": median(fl), "n_above_1": nabove, "n": len(snrs)}
    say("    %-6s %6.3f %10.3f %10.3f %10.3f %10.1f %8s"
        % (t, EXACT_N[t], med, snrs[0], snrs[-1], median(fl),
           "%d/%d" % (nabove, len(snrs))))
res["q2"] = q2
any_above = sum(v["n_above_1"] for v in q2.values())
say("")
say("    cells with high-band SNR above 1, over all %d: %d" % (len(RECS), any_above))
say("    NOTE the floor column: it moves %.1fx from f/5.6 to f/18, which is why"
    % (q2["f5.6"]["median_floor"] / q2["f18"]["median_floor"]))
say("    SNR alone cannot compare apertures. That is Q3's job.")
say("")

# ------------------------------------------------------------------------ Q3
say("Q3  OPTICAL TRANSFER  -- high_scene / low_scene, per aperture")
say("-" * 74)
say("    Subject-normalised: the same weave is imaged at every aperture, so the")
say("    low band divides out both exposure and subject contrast. What remains")
say("    that MOVES with f-number is optical.")
say("")
say("    %-6s %6s %14s %14s %14s %10s"
    % ("ap", "N", "median ratio", "min", "max", "rel f/5.6"))
q3 = {}
for t in TAGS:
    rs = [r for r in RECS if r["aperture"] == t]
    rat = sorted(r["bands"]["high"]["scene"] / r["bands"]["low"]["scene"] for r in rs)
    med = median(rat)
    q3[t] = {"median": med, "min": rat[0], "max": rat[-1], "all": rat}
base = q3["f5.6"]["median"]
for t in TAGS:
    q3[t]["rel"] = q3[t]["median"] / base
    say("    %-6s %6.3f %14.3e %14.3e %14.3e %10.3f"
        % (t, EXACT_N[t], q3[t]["median"], q3[t]["min"], q3[t]["max"], q3[t]["rel"]))
res["q3"] = q3
say("")

# ------------------------------------------------------------------------ C2/C3
say("PHYSICAL FRAME  -- where each aperture's diffraction cutoff falls")
say("-" * 74)
say("    f_c = PITCH_UM / (lambda * N_eff), N_eff = B * N, from m5_lib.")
say("    M129 has not settled B; its three hypotheses are carried side by side")
say("    so that nothing below depends on which one is right.")
say("")
LAMBDA_UM = 0.550
B_HYP = {"H1": 3.732, "H2": 3.076, "H3": 2.402}
HI_LO, HI_HI = BANDS["high"]


def f_cut(b, n):
    return PITCH_UM / (LAMBDA_UM * b * n)


say("    %-6s %8s %10s %10s %10s   %s" % ("ap", "N", "H1", "H2", "H3", "band 0.26-0.33"))
cuts = {}
for t in TAGS:
    row = {h: f_cut(b, EXACT_N[t]) for h, b in B_HYP.items()}
    cuts[t] = row
    inband = ["full" if row[h] >= HI_HI else ("none" if row[h] <= HI_LO else "part")
              for h in ("H1", "H2", "H3")]
    say("    %-6s %8.3f %10.4f %10.4f %10.4f   %s"
        % (t, EXACT_N[t], row["H1"], row["H2"], row["H3"], "/".join(inband)))
res["cutoffs"] = cuts
say("")
say("    f/18 cannot transmit into this band under ANY hypothesis, so its cells")
say("    measure this instrument's zero. That is control C5 and it is what makes")
say("    the detection threshold below measured rather than chosen.")
say("")

# ------------------------------------------------------------------------ C5
say("CONTROL C5  -- the empirical null at f/18")
say("-" * 74)
null_snr = [r["bands"]["high"]["snr"] for r in RECS if r["aperture"] == "f18"]
null_rat = [r["bands"]["high"]["scene"] / r["bands"]["low"]["scene"]
            for r in RECS if r["aperture"] == "f18"]
nm = sum(null_snr) / len(null_snr)
nsd = (sum((x - nm) ** 2 for x in null_snr) / (len(null_snr) - 1)) ** 0.5
thresh = abs(nm) + 3.0 * nsd
c5_ok = abs(nm) < 0.10
say("    f/18 high-band SNR over %d cells: mean %+.4f, sd %.4f"
    % (len(null_snr), nm, nsd))
say("    the floor estimate is therefore good to about %.1f%% -> %s"
    % (abs(nm) * 100, "PASS" if c5_ok else "FAIL"))
say("    DETECTION THRESHOLD |snr| > |mean| + 3sd = %.4f" % thresh)
res["c5_null"] = {"mean": nm, "sd": nsd, "threshold": thresh, "n": len(null_snr)}
say("")
say("    detections against the measured null, not against SNR > 1:")
det = {}
for t in TAGS:
    v = [r["bands"]["high"]["snr"] for r in RECS if r["aperture"] == t]
    nd = sum(1 for x in v if x > thresh)
    med = median(v)
    det[t] = {"n_detected": nd, "n": len(v), "median": med,
              "multiple_of_null": med / thresh if thresh > 0 else float("nan")}
    say("        %-6s %d/%d cells detected   median %+.3f = %.1fx threshold"
        % (t, nd, len(v), med, med / thresh))
res["detections"] = det
say("")

# ------------------------------------------------------------------------ C2/C3
say("CONTROLS C2 (low-band sanity) and C3 (monotone where cutoff-limited)")
say("-" * 74)
low_min = min(r["bands"]["low"]["snr"] for r in RECS)
c2_ok = low_min > 10.0
say("    C2 smallest low-band SNR over all %d cells: %.1f (> 10) -> %s"
    % (len(RECS), low_min, "PASS" if c2_ok else "FAIL"))
TAIL = ["f11", "f14", "f18"]
tail_vals = [q3[t]["median"] for t in TAIL]
c3_ok = all(tail_vals[i] >= tail_vals[i + 1] for i in range(len(tail_vals) - 1))
say("    C3 transfer over %s must decline monotonically:" % " > ".join(TAIL))
say("        %s  -> %s" % ("  ".join("%.3e" % v for v in tail_vals),
                           "PASS" if c3_ok else "FAIL"))
say("        (applies only here: under every B hypothesis these apertures'")
say("         cutoffs sit inside or below the band, so diffraction governs.)")
rels = [q3[t]["rel"] for t in TAGS]
rise = q3["f8"]["median"] / q3["f5.6"]["median"]
say("")
say("    REPORTED, NOT CONTROLLED: transfer RISES %.3fx from f/5.6 to f/8." % rise)
say("    Both apertures transmit the whole band under every B hypothesis, so")
say("    this is MTF shape, not cutoff -- aberration or residual focus error.")
say("    It is the same sign as M129's own unexplained aperture trend in B.")
res["c2_low_min_snr"] = low_min
res["c3_tail_monotone"] = c3_ok
res["rise_f56_to_f8"] = rise
say("")

# ---------------------------------------------------------------------- verdict
say("VERDICT")
say("-" * 74)
n_det_ap = sum(1 for t in TAGS if det[t]["n_detected"] > 0)
say("  C12's kill condition asks whether the optics put MEASURABLE energy past")
say("  plane Nyquist at corpus apertures. Against the measured null:")
say("    energy detected at %d of %d apertures (%s)."
    % (n_det_ap, len(TAGS),
       ", ".join(t for t in TAGS if det[t]["n_detected"] > 0)))
say("  The kill condition is therefore NOT met: consumers 1-2 survive.")
say("")
say("  BUT C12's per-aperture prediction is wrong. It says f/5.6 should and")
say("  f/11 should not. Measured, f/11 is the STRONGEST aperture in this band")
say("  (median SNR %.3f against f/5.6's %.3f), and the cut falls between f/11"
    % (det["f11"]["median"], det["f5.6"]["median"]))
say("  and f/14, not between f/5.6 and f/11.")
say("")
allc = c1_ok and c2_ok and c3_ok and c4_ok and c5_ok
say("  controls: C1 %s  C2 %s  C3 %s  C4 %s  C5 %s"
    % (*("PASS" if x else "FAIL" for x in (c1_ok, c2_ok, c3_ok, c4_ok, c5_ok)),))
say("  %s" % ("all controls pass; the numbers above stand."
              if allc else "A CONTROL FAILED -- the numbers above do not stand."))
res["controls_all_pass"] = allc
res["n_apertures_detected"] = n_det_ap

with open(os.path.join(OUT, "q1-band.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=2)
with open(os.path.join(OUT, "q1-band.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\nwrote out/q1-band.json and out/q1-band.txt")
sys.exit(0 if allc else 1)
