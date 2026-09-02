"""check_note.py -- verify every number in docs/research/M-PHASE0-QUINCUNX.md.

WHAT THIS CHECKS AND WHAT IT DOES NOT
-------------------------------------
Most checks here are DERIVED: this file re-bands M129's raw per-cell spectra with
its own independently written code and compares the result to the note. It does
not read q1-band.json for those. If the lane's banding were wrong, these checks
would disagree with the note and fail.

A minority are PINNED: read from the lane's own JSON. A PINNED check confirms the
note transcribes the run faithfully. It does NOT confirm the run was right. The
two classes are counted separately in the summary for exactly that reason -- a
report that was 100% PINNED would be a transcription check wearing a verifier's
clothes.

CLAIM checks assert a sentence is present and carry no arithmetic.

ANCHORING
---------
Prose wraps. Every phrase is compiled to a regex joining its tokens on \\s+ so a
line break inside an anchor cannot produce a spurious failure -- and, in the
commissioner, cannot produce a spurious pass. Short numeric tokens ('0.25', '6')
occur by chance, so every anchor carries neighbouring literal words rather than
standing alone.

SUMMARY PARTITION
-----------------
Every check lands in exactly one of passed / failed / skipped and the three sum
to the total. A count that does not move must not be readable as either "nothing
was wrong" or "nothing was examined".
"""

import json
import math
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(HERE))
NOTE = os.environ.get("NOTE_PATH",
                      os.path.join(ROOT, "docs", "research",
                                   "M-PHASE0-QUINCUNX.md"))
SNR_W2 = os.path.join(ROOT, "experiments", "M129-fabric-spectral-ladder",
                      "out", "snr-w2.json")
Q1 = os.environ.get("Q1_PATH", os.path.join(HERE, "out", "q1-band.json"))
Q2 = os.environ.get("Q2_PATH", os.path.join(HERE, "out", "q2-bhyp.json"))

PITCH_UM = 5.12
LAMBDA_UM = 0.550
B_HYP = {"H1": 3.732, "H2": 3.076, "H3": 2.402}
TAGS = ["f5.6", "f8", "f11", "f14", "f18"]

RAW = open(NOTE, encoding="utf-8").read()

PASS, FAIL, SKIP = [], [], []


def wrap_re(phrase):
    return re.compile(r"\s+".join(re.escape(t) for t in phrase.split()))


def um(s):
    """ASCII hyphen-minus -> U+2212, matching the note's typography."""
    return s.replace("-", "\u2212")


def has(phrase):
    return wrap_re(phrase).search(RAW) is not None


def ck(label, cls, phrase, why=""):
    """cls in {DERIVED, PINNED, CLAIM}. `phrase` must appear in the note."""
    if has(phrase):
        PASS.append((cls, label))
    else:
        FAIL.append((cls, label, phrase, why))


# ------------------------------------------------------- independent re-banding
D = json.load(open(SNR_W2, encoding="utf-8"))
BANDS = D["bands"]
HI_LO, HI_HI = BANDS["high"]
recs = D["records"]

if len(recs) != 30:
    print("FATAL: expected 30 records in snr-w2.json, found %d" % len(recs))
    sys.exit(2)


def reband(r, lo, hi):
    """Mean PSD in the closed interval [lo,hi], minus this cell's noise floor.

    The interval is CLOSED and the mean is UNWEIGHTED. Both choices are forced
    by the stored data, not preferred: an earlier revision of this checker used
    a half-open interval and count-weighting, and disagreed with the stored band
    summaries by ~7%. snr_survey.py is the authority for these semantics and
    control C1 in q1_band.py confirms they reproduce the stored values.
    """
    sel = [p for f, p in zip(r["f"], r["psd"]) if lo <= f <= hi]
    if not sel:
        return None
    mean = sum(sel) / len(sel)
    return (mean - r["floor"]) / r["floor"]


by = {t: [] for t in TAGS}
floors = {t: [] for t in TAGS}
trans = {t: [] for t in TAGS}
for r in recs:
    t = r["aperture"]
    by[t].append(reband(r, HI_LO, HI_HI))
    floors[t].append(r["floor"])
    lowm = reband(r, *BANDS["low"])
    him = reband(r, HI_LO, HI_HI)
    trans[t].append(him / lowm)

med = {t: st.median(by[t]) for t in TAGS}
medfl = {t: st.median(floors[t]) for t in TAGS}
medtr = {t: st.median(trans[t]) for t in TAGS}

null_mean = st.mean(by["f18"])
null_sd = st.stdev(by["f18"])
thresh = abs(null_mean) + 3 * null_sd
ndet = {t: sum(1 for v in by[t] if v > thresh) for t in TAGS}
mult = {t: med[t] / thresh for t in TAGS}
rel = {t: medtr[t] / medtr["f5.6"] for t in TAGS}

EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}


def f_c(N, B, lam=LAMBDA_UM):
    return PITCH_UM / (lam * B * N)


# =============================================================== §0/§2 headline
ck("band edges", "DERIVED",
   "**(%.3f, %.3f) sensor cyc/px**" % (HI_LO, HI_HI))
ck("apertures detected", "DERIVED",
   "detected at **%d of 5** corpus apertures"
   % sum(1 for t in TAGS if ndet[t] > 0))
ck("headline multiples", "DERIVED",
   "**%.1f\u00d7, %.1f\u00d7, %.1f\u00d7 and %.1f\u00d7** a detection threshold"
   % (mult["f5.6"], mult["f8"], mult["f11"], mult["f14"]))
ck("f11 strongest vs f5.6", "DERIVED",
   "median power SNR %.3f against f/5.6's %.3f" % (med["f11"], med["f5.6"]))

# ==================================================================== §1 lattice
for name, pitch in (("full sensor", PITCH_UM),
                    ("GQ quincunx", PITCH_UM * math.sqrt(2)),
                    ("G1 or G2 alone", PITCH_UM * 2)):
    nyq_cymm = 1000.0 / (2 * pitch)
    cycpx = PITCH_UM / (2 * pitch)
    ck("lattice %s" % name, "DERIVED",
       "| %s | %.4f | %.2f | %.5f |" % (name, pitch, nyq_cymm, cycpx))

ck("quincunx reach", "DERIVED",
   "reaches only **%.5f**, the inscribed diagonal limit" % (math.sqrt(2) / 4))
ck("cell count", "DERIVED",
   "for %d cells \u2014 %d apertures \u00d7 %d ROIs \u2014 and banded it."
   % (len(recs), len(TAGS), len(by["f5.6"])))
ck("units line ref", "CLAIM",
   "line 67 states the bands are in sensor cyc/px")

# ================================================================ §2 null + table
ck("null mean/sd", "DERIVED",
   um("mean **%+.4f**, sd **%.4f** over 6 cells" % (null_mean, null_sd)))
ck("threshold", "DERIVED",
   "= **%.4f**" % thresh)

for t, lbl in zip(TAGS, ["f/5.6", "f/8", "f/11", "f/14", "f/18"]):
    ck("row %s" % lbl, "DERIVED",
       um("| %s | %.3f | %d/6 | %+.3f | %.1f |"
          % (lbl, EXACT_N[t], ndet[t], med[t], mult[t])))

ck("floor extremes", "DERIVED",
   "(%.1f against f/5.6's %.1f)" % (medfl["f18"], medfl["f5.6"]))
ck("n_above_1 framing", "DERIVED",
   "only %d of 30 cells clear it"
   % sum(1 for t in TAGS for v in by[t] if v > 1.0))

# ================================================================ §3 cutoff table
for t, lbl in zip(TAGS, ["f/5.6", "f/8", "f/11", "f/14", "f/18"]):
    ck("cutoff row %s" % lbl, "DERIVED",
       "| %s | %.3f | %.4f | %.4f | %.4f |"
       % (lbl, EXACT_N[t], f_c(EXACT_N[t], B_HYP["H1"]),
          f_c(EXACT_N[t], B_HYP["H2"]), f_c(EXACT_N[t], B_HYP["H3"])))
ck("cut location", "CLAIM",
   "the cut falls between f/14 and f/18**, not between")
ck("M88 attribution", "CLAIM",
   "attributing that to M88. Measured, **f/11 is the")
ck("kill gate only", "CLAIM",
   "**This lane answers C12's kill gate and only its kill gate.**")
ck("three items open", "CLAIM",
   "**None of those three is answered here.** They need per-frame G1/G2 planes")

# ==================================================================== §4 transfer
ck("transfer swing", "DERIVED",
   um("by a factor of **%.1f** from f/5.6 to f/18" % (1.0 / rel["f18"])))

# ===================================================================== §5 anomaly
ck("f5.6->f8 rise", "DERIVED",
   "rises %.3f\u00d7** from f/5.6 to f/8" % rel["f8"])

# ================================================================== §6 bracket
lo = PITCH_UM / (LAMBDA_UM * EXACT_N["f18"] * HI_LO)
hi = PITCH_UM / (LAMBDA_UM * EXACT_N["f14"] * HI_LO)
ck("bracket hi line", "DERIVED",
   "detected at f/14 => f_c(%.3f) > %.2f => B < %.4f"
   % (EXACT_N["f14"], HI_LO, hi))
ck("bracket lo line", "DERIVED",
   "absent at f/18 => f_c(%.3f) < %.2f => B > %.4f"
   % (EXACT_N["f18"], HI_LO, lo))
ck("bracket headline", "DERIVED",
   "**%.3f \u2013 %.3f**, excluding two" % (lo, hi))
for h in ("H1", "H2", "H3"):
    ck("hyp row %s" % h, "DERIVED",
       "| %s | %.3f | %s |"
       % (h, B_HYP[h],
          "yes" if lo < B_HYP[h] < hi else "no \u2014 excluded"))
lo5, hi5 = (PITCH_UM / (0.500 * EXACT_N[x] * HI_LO) for x in ("f18", "f14"))
lo6, hi6 = (PITCH_UM / (0.600 * EXACT_N[x] * HI_LO) for x in ("f18", "f14"))
ck("lambda 0.500 bracket", "DERIVED",
   "brackets %.3f\u2013%.3f at 0.500" % (lo5, hi5))
ck("lambda 0.600 bracket", "DERIVED",
   "and %.3f\u2013%.3f at 0.600" % (lo6, hi6))
ck("H3 not robust", "CLAIM", "This evidence does not elect H3.")

z14 = (med["f14"] - null_mean) / null_sd
ck("f14 z", "DERIVED", "**%.1f null sd** above the null mean" % z14)
ck("f14 floor ratio", "DERIVED",
   "within %.0f%% of f/18's" % (abs(medfl["f14"] / medfl["f18"] - 1) * 100))

# ================================================================= §7 disclosure
ck("C3 disclosure", "CLAIM",
   "The monotonicity control had a wrong premise.")
ck("median disclosure", "CLAIM",
   "Every reported \"median\" was biased upward, and no control caught it.")
ck("median found by checker", "CLAIM",
   "It was found by `check_note.py`, which re-derives the same quantities")
ck("median controls blind", "CLAIM",
   "None of the five controls could see it, because all five compare the lane to")
ck("banding was mine", "CLAIM",
   "A second discrepancy in the same run was my checker's fault, not the lane's.")
ck("bar disclosure", "CLAIM", "The detection bar was arbitrary.")
ck("blinder direction", "CLAIM",
   "they made the instrument look blinder than it is")

# ---- PINNED --------------------------------------------------------------
# These compare the lane's stored output to the independent re-derivation above.
# They are numeric agreements, not text presence: a PINNED check failing means
# the run and this checker disagree about the data, which is a different and
# more serious failure than a typo in the note.
J1 = json.load(open(Q1, encoding="utf-8"))
J2 = json.load(open(Q2, encoding="utf-8"))


def ckn(label, got, want, tol):
    if want == 0:
        ok = abs(got) <= tol
    else:
        ok = abs(got - want) / abs(want) <= tol
    if ok:
        PASS.append(("PINNED", label))
    else:
        FAIL.append(("PINNED", label,
                     "run=%r  independent=%r  (tol %g)" % (want, got, tol), ""))


ckn("run agrees: null mean", null_mean, J1["c5_null"]["mean"], 1e-9)
ckn("run agrees: null sd", null_sd, J1["c5_null"]["sd"], 1e-9)
ckn("run agrees: threshold", thresh, J1["c5_null"]["threshold"], 1e-9)
for t in TAGS:
    ckn("run agrees: median %s" % t, med[t], J1["q2"][t]["median_snr"], 1e-9)
    ckn("run agrees: floor %s" % t, medfl[t], J1["q2"][t]["median_floor"], 1e-9)
    ckn("run agrees: ndet %s" % t, ndet[t], J1["detections"][t]["n_detected"], 0)
ckn("run agrees: rise f5.6->f8", rel["f8"], J1["rise_f56_to_f8"], 1e-9)
ckn("run agrees: bracket lo", lo, J2["bracket"]["lo"], 1e-9)
ckn("run agrees: bracket hi", hi, J2["bracket"]["hi"], 1e-9)
ckn("run agrees: f14 z", z14, J2["c10_f14_z"], 1e-9)
ck("C1 agreement quoted", "PINNED",
   "to %.2e relative (control C1)" % J1["c1_worst_rel"])

# --------------------------------------------------------------------- report
total = len(PASS) + len(FAIL) + len(SKIP)
print("M-PHASE0-QUINCUNX note checker")
print("=" * 74)
print("note: %s" % NOTE)
print("")
for cls, label, phrase, why in FAIL:
    print("  FAIL [%s] %s" % (cls, label))
    print("        expected: %s" % phrase.replace("\n", " ")[:150])
    if why:
        print("        %s" % why)
if FAIL:
    print("")
byc = {}
for cls, _ in PASS:
    byc[cls] = byc.get(cls, 0) + 1
print("passed  %3d   (%s)"
      % (len(PASS), ", ".join("%s %d" % (k, byc[k]) for k in sorted(byc))))
print("failed  %3d" % len(FAIL))
print("skipped %3d" % len(SKIP))
print("-" * 30)
print("total   %3d   checks defined" % total)
print("")
print("DERIVED = recomputed here from M129's raw spectra + PITCH_UM.")
print("PINNED  = read from this lane's own JSON; confirms transcription only.")
print("CLAIM   = a stated sentence, no arithmetic.")
print("")
print("VERDICT: %s" % ("GREEN" if not FAIL else "RED"))
sys.exit(0 if not FAIL else 1)

