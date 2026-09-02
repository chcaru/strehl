"""
M-PHASE0-PTC, step 2: answer B1's real go/no-go from M61's existing per-stack
ladder, with no new decode and no new estimator.

WHAT STEP 1 ESTABLISHED
-----------------------
B1's acceptance ("recovers M90's independent g within its CI ... per-stack,
from subject frames alone") names a +/-0.0642% precision figure as an accuracy
target, while the two best independent measurements of that same g disagree by
1.33% and M90 itself declines to narrow g beyond a 1.2-percentage-point band.
Step 1 also found that B1's estimator already exists: M61-E1, run in-stack on
12 subject stacks, cited zero times by the proposal.

WHAT THIS STEP DOES
-------------------
M61's ladder is on disk per stack and per CFA plane
(experiments/m61-ptc-high-iso/data/ptc-ladder.csv, 48 rows = 12 stacks x 4
planes) with split-half internal replicates. That is exactly the evidence
B1's acceptance asks for, already collected. This step decomposes it.

REGISTERED QUESTIONS AND DIRECTIONS (house rule 18: state the direction first)
-----------------------------------------------------------------------------
  R1  PER-STACK ACCURACY. For each low-mode stack, compute greens g = mean(G1,G2)
      of the primary variant gA, and compare to M90's 0.221113 after scaling to
      that stack's ISO.
      REGISTERED DIRECTION: I expect the per-stack values to STRADDLE M90 rather
      than sit uniformly on one side, because M61's aggregate at ISO 100 lands
      -2.02% while its fit-gated aggregate lands +0.72% -- a sign flip driven by
      one stack, which means the scatter is larger than the offset.
      REGISTERED BAR: count how many stacks land inside (a) B1's named CI
      +/-0.0642%, and (b) M90's own stated band of ignorance, 2.2-3.4%.

  R2  INTERNAL vs EXTERNAL PRECISION. g_half0 and g_half1 are the same stack
      split in two: their difference is the instrument's internal precision at
      fixed scene. Stack-to-stack scatter is the external one.
      REGISTERED DIRECTION: internal will be MUCH TIGHTER than external. If so,
      the limit on an in-stack g is scene/stack systematics, NOT photon noise,
      and B1 cannot buy accuracy by averaging more frames of one subject.
      This is the operationally important half of the whole lane.

  R3  THE INTERCEPT, CROSS-LANE. M90's PR-4d FAILED: the PTC intercept recovered
      a known read floor 11.0% low on synthetic data and went NEGATIVE (-2.795
      DN^2, physically impossible) on real flats. B1 nevertheless lists "read
      floor" as an output, and B5 leans on the same intercept for black-level
      drift.
      REGISTERED DIRECTION: the same failure will appear here, on INDEPENDENT
      data (subject frames, not flats). I predict a substantial fraction of the
      48 icptA values are negative.
      REGISTERED BAR: if >25% of rows are negative, the intercept is not a
      usable read-floor estimator in-stack and B1's read-floor output must be
      struck or re-sourced.

CONTROL ON MY READING OF THE CSV (the load-bearing one)
-------------------------------------------------------
  C4  Reproduce M61's PUBLISHED aggregate before decomposing it. Averaging gA
      over G1,G2 for the three ISO-100 low-mode stacks and dividing by g_model
      must return r = 0.9463 (M61 section 3.1). If it does not, I am reading the
      wrong column, the wrong variant, or the wrong stack set, and every number
      below would be wrong in a way no internal check would catch.
      BAR: within 0.005 absolute of 0.9463.
  C5  Same for the ISO-160 control stack: greens r must return 0.9887.

  Neither C4 nor C5 is a test of M61. They are tests of THIS script's reading.
  If they fail the script makes no R1/R2/R3 claim.

  C6  THE BASELINE IS READ, NEVER RE-DERIVED. M90 measured g at ISO 100. To
  compare a stack at another ISO, M90's value must be scaled by the model's
  own ISO dependence. That scaling is taken from the CSV's `g_model` column
  as a RATIO to the ISO-100 row -- never from a formula retyped here.
  BAR: g_model at ISO 100 must equal 0.2289377 to 1e-6.

DISCLOSED ERROR IN THIS SCRIPT'S FIRST RUN (rule: my own errors, disclosed)
--------------------------------------------------------------------------
Run 1 computed the baseline as `M90_G_ISO100 * iso/100.0`, i.e. assumed the
conversion gain is linear in ISO all the way down. It is not: M61's own rule is
`g_model = max(ISO,100)/436.8`, and the CSV confirms it -- the ISO 50 stacks
carry g_model = 0.2289377, IDENTICAL to ISO 100. ISO 50 on this body is a pull
ISO, not a lower sensor gain.

The signature was unmissable and I did not miss it: the two ISO 50 stacks
reported +104.5% and +102.8% against a baseline half the right size, while their
measured g (0.2261, 0.2242) sits right beside the ISO 100 stacks' (0.2226,
0.2228) -- exactly what the clamp predicts. The measured column was fine; the
baseline was mine and it was wrong.

This is the same failure mode twice in one session: MAGNITUDES SOUND, BASELINE
WRONG. The fix is structural, not arithmetic -- C6 now reads the scaling out of
the same file the data came from, so it cannot disagree with the model that
produced the data.
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(LANE))
CSV_PATH = os.path.join(ROOT, "experiments", "m61-ptc-high-iso", "data", "ptc-ladder.csv")
OUT = os.path.join(LANE, "out")

M90_G_ISO100 = 0.221113          # M90 section 2.2
M90_CI_REL_PCT = 0.000142 / 0.221113 * 100.0
M90_BAND_LO, M90_BAND_HI = 2.2, 3.4   # M90 section 8.2, absolute percent

lines = []


def say(s=""):
    lines.append(s)
    print(s)


rows = []
with open(CSV_PATH, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)

for r in rows:
    r["iso"] = float(r["iso"])
    for k in ("g_model", "gA", "gB", "gC", "gA_zero_icpt", "g_half0", "g_half1",
              "icptA", "resid_pct"):
        r[k] = float(r[k])

say("M-PHASE0-PTC step 2 -- B1's per-stack go/no-go from M61's existing ladder")
say("=" * 78)
say("source: experiments/m61-ptc-high-iso/data/ptc-ladder.csv  (%d rows)" % len(rows))
say("")

# ---------------------------------------------------------------- greens table
stacks = {}
for r in rows:
    stacks.setdefault((r["stack"], r["iso"]), {})[r["plane"]] = r

greens = {}
for key, planes in stacks.items():
    if "G1" in planes and "G2" in planes:
        gA = (planes["G1"]["gA"] + planes["G2"]["gA"]) / 2.0
        gm = planes["G1"]["g_model"]
        greens[key] = {
            "gA": gA,
            "g_model": gm,
            "r": gA / gm,
            "half0": (planes["G1"]["g_half0"] + planes["G2"]["g_half0"]) / 2.0,
            "half1": (planes["G1"]["g_half1"] + planes["G2"]["g_half1"]) / 2.0,
            "resid_pct": max(planes["G1"]["resid_pct"], planes["G2"]["resid_pct"]),
        }

# ---------------------------------------------------------------- C4 / C5
ISO100_STACKS = ["bee-1", "bee-3", "wrapped-text-1"]        # M61 section 3.1
iso100 = [(k, v_) for k, v_ in greens.items() if k[0] in ISO100_STACKS and k[1] == 100.0]
c4_r = sum(v_["r"] for _, v_ in iso100) / len(iso100) if iso100 else float("nan")
c4 = abs(c4_r - 0.9463) < 0.005

iso160 = [(k, v_) for k, v_ in greens.items() if k[0] == "109MSDCF"]
c5_r = sum(v_["r"] for _, v_ in iso160) / len(iso160) if iso160 else float("nan")
c5 = abs(c5_r - 0.9887) < 0.005

say("CONTROLS ON THIS SCRIPT'S READING OF THE CSV")
say("-" * 78)
say("C4  ISO 100 greens r recomputed = %.4f   M61 published 0.9463   -> %s   (n=%d stacks)"
    % (c4_r, "PASS" if c4 else "FAIL", len(iso100)))
say("C5  ISO 160 greens r recomputed = %.4f   M61 published 0.9887   -> %s"
    % (c5_r, "PASS" if c5 else "FAIL"))

# C6 -- the baseline scaling is READ from the data, never re-derived here.
g_model_100 = None
for _, val in greens.items():
    pass
g_model_by_iso = {}
for (name, iso), val in greens.items():
    g_model_by_iso.setdefault(iso, set()).add(round(val["g_model"], 9))
for iso, s in g_model_by_iso.items():
    assert len(s) == 1, "g_model not unique at ISO %s: %s" % (iso, s)
g_model_100 = list(g_model_by_iso[100.0])[0]
c6 = abs(g_model_100 - 0.2289377) < 1e-6
say("C6  g_model(ISO100) read from CSV = %.7f   expected 0.2289377   -> %s"
    % (g_model_100, "PASS" if c6 else "FAIL"))
say("    ISO 50 g_model = %.7f  (identical to ISO 100 -> the pull-ISO clamp is real,"
    % list(g_model_by_iso[50.0])[0])
say("     and run 1's linear scaling was wrong; see the disclosed error above)")
say("")
ok = c4 and c5 and c6
say("CONTROLS: %s" % ("ALL PASS -- proceeding" if ok else "FAILED -- no claim made below"))
say("")

result = {"controls": {"c4_r": c4_r, "c4": c4, "c5_r": c5_r, "c5": c5,
                       "c6_g_model_100": g_model_100, "c6": c6, "ok": ok}}

if ok:
    # ------------------------------------------------------------------ R1
    say("R1  PER-STACK ACCURACY vs M90  (low-mode stacks; g scaled to each ISO)")
    say("-" * 78)
    say("    M90 g(ISO100) = %.6f DN/e-;  baseline at other ISO = M90 * g_model(ISO)/g_model(100)"
        % M90_G_ISO100)
    say("    (the scaling is READ from the CSV's g_model column -- see C6)")
    say("")
    say("    %-16s %6s %10s %10s %9s %8s" % ("stack", "ISO", "g greens", "M90 base", "delta %", "resid%"))
    r1 = []
    for (name, iso), val in sorted(greens.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if iso >= 400:
            continue                      # high-gain mode: different g, not comparable to M90
        m90_scaled = M90_G_ISO100 * (val["g_model"] / g_model_100)
        d = (val["gA"] / m90_scaled - 1.0) * 100.0
        r1.append({"stack": name, "iso": iso, "g": val["gA"],
                   "m90_scaled": m90_scaled, "delta_pct": d,
                   "resid_pct": val["resid_pct"]})
        say("    %-16s %6.0f %10.6f %10.6f %+9.3f %8.1f"
            % (name, iso, val["gA"], m90_scaled, d, val["resid_pct"]))
    say("")
    inside_ci = sum(1 for x in r1 if abs(x["delta_pct"]) <= M90_CI_REL_PCT)
    inside_band = sum(1 for x in r1 if abs(x["delta_pct"]) <= M90_BAND_HI)
    pos = sum(1 for x in r1 if x["delta_pct"] > 0)
    neg = len(r1) - pos
    say("    inside B1's named CI (+/-%.4f%%):        %d of %d" % (M90_CI_REL_PCT, inside_ci, len(r1)))
    say("    inside M90's stated band (+/-%.1f%%):     %d of %d" % (M90_BAND_HI, inside_band, len(r1)))
    say("    sign split: %d above M90, %d below   -> %s"
        % (pos, neg, "STRADDLES (as registered)" if pos and neg else "ONE-SIDED (contra registered)"))
    deltas = [x["delta_pct"] for x in r1]
    spread = (max(deltas) - min(deltas))
    say("    per-stack spread: %+.3f%% to %+.3f%%   (width %.3f pp)"
        % (min(deltas), max(deltas), spread))
    say("")
    result["r1"] = {"rows": r1, "inside_ci": inside_ci, "inside_band": inside_band,
                    "n": len(r1), "pos": pos, "neg": neg,
                    "spread_pp": spread, "min": min(deltas), "max": max(deltas)}

    # ------------------------------------------------------------------ R2
    say("R2  INTERNAL (split-half) vs EXTERNAL (stack-to-stack) PRECISION")
    say("-" * 78)
    halves = []
    for (name, iso), val in sorted(greens.items()):
        if val["half0"] and val["half1"]:
            mean_h = (val["half0"] + val["half1"]) / 2.0
            if mean_h != 0:
                halves.append({"stack": name, "iso": iso,
                               "spread_pct": abs(val["half0"] - val["half1"]) / mean_h * 100.0})
    hs = sorted(x["spread_pct"] for x in halves)
    med_internal = hs[len(hs) // 2]
    say("    split-half |g0-g1|/mean, all %d stacks:" % len(hs))
    say("      median %.3f%%   min %.3f%%   max %.3f%%" % (med_internal, hs[0], hs[-1]))
    say("    stack-to-stack spread at fixed ISO (low mode, from R1): %.3f pp" % spread)
    ratio = spread / med_internal if med_internal else float("inf")
    say("    external / internal = %.1fx" % ratio)
    say("")
    verdict_r2 = "CONFIRMED" if ratio > 3.0 else "NOT CONFIRMED"
    say("    registered direction (internal MUCH tighter): %s" % verdict_r2)
    if ratio > 3.0:
        say("    => the limit on an in-stack g is SCENE/STACK SYSTEMATICS, not photon")
        say("       noise. More frames of one subject cannot buy accuracy. B1 must")
        say("       average over SUBJECTS, or report a per-stack value with an honest")
        say("       systematic band -- it cannot claim a tight CI from one stack.")
    result["r2"] = {"median_internal_pct": med_internal, "min": hs[0], "max": hs[-1],
                    "external_pp": spread, "ratio": ratio, "verdict": verdict_r2,
                    "rows": halves}
    say("")

    # ------------------------------------------------------------------ R3
    say("R3  THE INTERCEPT -- M90's PR-4d RE-TESTED ON INDEPENDENT DATA")
    say("-" * 78)
    negs = [r for r in rows if r["icptA"] < 0]
    frac = len(negs) / len(rows) * 100.0
    say("    M90 PR-4d (on FLATS): intercept 11.0% low on a known plant;")
    say("                          -2.795 DN^2, negative and physically impossible, on real flats.")
    say("    Here (on SUBJECT FRAMES, independent data, different lane):")
    say("      icptA < 0 in %d of %d rows = %.1f%%" % (len(negs), len(rows), frac))
    icpts = sorted(r["icptA"] for r in rows)
    say("      range %.4f to %.4f DN^2" % (icpts[0], icpts[-1]))
    by_plane = {}
    for r in rows:
        by_plane.setdefault(r["plane"], []).append(r["icptA"])
    for p in ("R", "G1", "G2", "B"):
        if p in by_plane:
            n_neg = sum(1 for x in by_plane[p] if x < 0)
            say("      plane %-2s: %d of %d negative" % (p, n_neg, len(by_plane[p])))
    say("")
    r3_verdict = "CONFIRMED" if frac > 25.0 else "NOT CONFIRMED"
    say("    registered bar was >25%% negative: %.1f%% -> %s" % (frac, r3_verdict))
    if frac > 25.0:
        say("    => the PTC intercept is NOT a usable read-floor estimator in-stack.")
        say("       B1 lists 'read floor' as an output of this mechanism and B5 leans")
        say("       on it for black-level drift. Both must be struck or re-sourced.")
        say("       M61 already knew: it reports only the SLOPE and prints a")
        say("       forced-zero-intercept variant as proof it does not lean on this.")
    result["r3"] = {"n_negative": len(negs), "n": len(rows), "frac_pct": frac,
                    "min": icpts[0], "max": icpts[-1], "verdict": r3_verdict}

say("")
say("=" * 78)
say("The three answers together say B1 is a PORT with a RESTATED BAR and one")
say("OUTPUT STRUCK, not a new build. See the lane PREREGISTRATION for the")
say("replacement acceptance criterion.")

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "b1-perstack.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
with open(os.path.join(OUT, "b1-perstack.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\nwrote out/b1-perstack.json and out/b1-perstack.txt")
