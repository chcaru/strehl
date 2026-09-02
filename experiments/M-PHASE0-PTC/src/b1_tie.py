"""
M-PHASE0-PTC, step 4: an unregistered observation, reported as such.

WHAT PROMPTED IT
----------------
Step 3 gated the low-mode stacks with M61's CONSIST rule and found the spread
collapse 5.9x. But it also left every surviving stack on the SAME SIDE of M90:
+0.691, +0.765, +1.391, +2.270, +2.365 percent. Five of five positive.

Scatter straddles. A one-sided result is an offset. That was not predicted by
anything registered in this lane, and I noticed it only after step 3 printed.

WHY THIS MATTERS BEYOND B1
--------------------------
M90 section 8.2 records an UNRESOLVED disagreement:

    "my g does not reconcile with M71's. 0.221113 vs 0.224103 is -1.33%, i.e.
     3.6x M71's quoted 1 sigma ... The honest statement is: the true shipped-gain
     error is somewhere in -2.2% to -3.4%, and this milestone cannot narrow it
     further."

Two methods, one body, 1.33% apart, tie unbroken. The in-stack temporal PTC is a
THIRD method with different scenes, different tile selection, and a different
variance estimator. Where it lands is evidence about that tie.

THE DISCIPLINE THAT APPLIES HERE
--------------------------------
This is post-hoc. I registered no direction and will not manufacture one now. A
prediction made after seeing the answer is not evidence, and this file exists to
keep that boundary visible rather than to argue past it.

So the output below is labelled OBSERVATION throughout, carries no pass/fail,
and ends with the registered test that WOULD settle it -- to be run in a future
lane, against data this one has not touched.

THE ONE METHODOLOGICAL CARE THAT IS NOT OPTIONAL
------------------------------------------------
Comparing a stack at ISO 50 or 160 to M90's ISO-100 measurement requires the
model's own ISO scaling to be correct. If that scaling is even slightly wrong it
contaminates the comparison, and it is exactly the kind of assumption that
produced this script's sibling's run-1 error.

So the observation is split in two and BOTH are reported:

  ARM A -- ISO 100 only. No scaling of any kind. bee-1 and bee-3 are compared to
           M90 directly, like against like. This arm is clean.
  ARM B -- all CONSIST-passing low-mode stacks, which requires the g_model ratio.
           Reported second, and explicitly marked as assuming the ISO scaling.

If the two arms disagree, ARM A is the one that means anything.
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(LANE))
CSV_PATH = os.path.join(ROOT, "experiments", "m61-ptc-high-iso", "data", "ptc-ladder.csv")
OUT = os.path.join(LANE, "out")

M90_G = 0.221113          # M90 section 2.2, ISO 100 green
M71_G = 0.224103          # M90 section 2.2, ISO 100 green
SHIPPED_G = 0.228938      # M90 section 2.2

lines = []


def say(s=""):
    lines.append(s)
    print(s)


rows = []
with open(CSV_PATH, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        r["iso"] = float(r["iso"])
        for k in ("g_model", "gA", "gC", "g_half0", "g_half1"):
            r[k] = float(r[k])
        rows.append(r)

stacks = {}
for r in rows:
    stacks.setdefault((r["stack"], r["iso"]), {})[r["plane"]] = r


def sp(a, b):
    m = (a + b) / 2.0
    return abs(a - b) / m * 100.0 if m else float("inf")


def consist(planes):
    h = sp((planes["G1"]["g_half0"] + planes["G2"]["g_half0"]) / 2.0,
           (planes["G1"]["g_half1"] + planes["G2"]["g_half1"]) / 2.0)
    ac = sp((planes["G1"]["gA"] + planes["G2"]["gA"]) / 2.0,
            (planes["G1"]["gC"] + planes["G2"]["gC"]) / 2.0)
    return (h < 5.0) and (ac < 10.0)


def greens_g(planes):
    return (planes["G1"]["gA"] + planes["G2"]["gA"]) / 2.0


say("M-PHASE0-PTC step 4 -- OBSERVATION (not registered, no pass/fail)")
say("=" * 78)
say("")
say("The M90 / M71 tie, and where a third method lands.")
say("  M90 (flats, temporal PTC)   g = %.6f DN/e-" % M90_G)
say("  M71 (profile fit)           g = %.6f DN/e-   (%+.3f%% vs M90)"
    % (M71_G, (M71_G / M90_G - 1) * 100))
say("  shipped constant            g = %.6f DN/e-   (%+.3f%% vs M90)"
    % (SHIPPED_G, (SHIPPED_G / M90_G - 1) * 100))
say("  M90 could not break its tie with M71 and said so (section 8.2).")
say("")

g_model_100 = stacks[("bee-1", 100.0)]["G1"]["g_model"]
result = {}

# ------------------------------------------------------------------ ARM A
say("ARM A -- ISO 100 ONLY.  No scaling. Like against like.")
say("-" * 78)
armA = []
for (name, iso), planes in sorted(stacks.items()):
    if iso != 100.0 or not consist(planes):
        continue
    g = greens_g(planes)
    armA.append({"stack": name, "g": g,
                 "vs_m90": (g / M90_G - 1) * 100,
                 "vs_m71": (g / M71_G - 1) * 100})
say("    %-16s %10s %10s %10s" % ("stack", "g greens", "vs M90 %", "vs M71 %"))
for x in armA:
    say("    %-16s %10.6f %+10.3f %+10.3f" % (x["stack"], x["g"], x["vs_m90"], x["vs_m71"]))
if armA:
    mean_g = sum(x["g"] for x in armA) / len(armA)
    agree = max(abs(a["g"] - b["g"]) / ((a["g"] + b["g"]) / 2) * 100
                for a in armA for b in armA)
    v90 = (mean_g / M90_G - 1) * 100
    v71 = (mean_g / M71_G - 1) * 100
    say("")
    say("    mean of %d CONSIST-passing ISO-100 stacks: g = %.6f" % (len(armA), mean_g))
    say("    the two stacks agree with each other to %.3f pp" % agree)
    say("    vs M90: %+.3f%%      vs M71: %+.3f%%" % (v90, v71))
    span = abs(M71_G - M90_G)
    frac = (mean_g - M90_G) / span * 100 if span else float("nan")
    say("    position in the M90->M71 interval: %.0f%% of the way from M90 to M71" % frac)
    say("")
    closer = "M90" if abs(v90) < abs(v71) else "M71"
    say("    OBSERVATION: the in-stack temporal PTC lands BETWEEN the two")
    say("    disputed values, %.0f%% of the way across, closer to %s." % (frac, closer))
    say("    It does NOT break the tie. It is consistent with both to within")
    say("    less than the width of their disagreement.")
    result["armA"] = {"rows": armA, "mean_g": mean_g, "agree_pp": agree,
                      "vs_m90": v90, "vs_m71": v71, "frac_to_m71": frac,
                      "closer": closer, "n": len(armA)}
say("")

# ------------------------------------------------------------------ ARM B
say("ARM B -- all CONSIST-passing low-mode stacks.  ASSUMES the model's ISO scaling.")
say("-" * 78)
armB = []
for (name, iso), planes in sorted(stacks.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    if iso >= 400 or not consist(planes):
        continue
    g = greens_g(planes)
    scale = planes["G1"]["g_model"] / g_model_100
    armB.append({"stack": name, "iso": iso, "g_at_iso100_equiv": g / scale,
                 "vs_m90": (g / (M90_G * scale) - 1) * 100,
                 "vs_m71": (g / (M71_G * scale) - 1) * 100})
say("    %-16s %6s %14s %10s %10s" % ("stack", "ISO", "g @ISO100-eq", "vs M90 %", "vs M71 %"))
for x in armB:
    say("    %-16s %6.0f %14.6f %+10.3f %+10.3f"
        % (x["stack"], x["iso"], x["g_at_iso100_equiv"], x["vs_m90"], x["vs_m71"]))
if armB:
    mB = sum(x["g_at_iso100_equiv"] for x in armB) / len(armB)
    vB90 = (mB / M90_G - 1) * 100
    vB71 = (mB / M71_G - 1) * 100
    say("")
    say("    mean of %d stacks: g(ISO100-equivalent) = %.6f" % (len(armB), mB))
    say("    vs M90: %+.3f%%      vs M71: %+.3f%%" % (vB90, vB71))
    pos = sum(1 for x in armB if x["vs_m90"] > 0)
    say("    sign vs M90: %d of %d positive" % (pos, len(armB)))
    result["armB"] = {"rows": armB, "mean_g": mB, "vs_m90": vB90, "vs_m71": vB71,
                      "n_positive": pos, "n": len(armB)}
say("")

if "armA" in result and "armB" in result:
    say("DO THE ARMS AGREE?")
    say("-" * 78)
    d = abs(result["armA"]["vs_m90"] - result["armB"]["vs_m90"])
    say("    ARM A says %+.3f%% vs M90; ARM B says %+.3f%%. They differ by %.3f pp."
        % (result["armA"]["vs_m90"], result["armB"]["vs_m90"], d))
    if d > 0.5:
        say("    THEY DISAGREE by more than half a point. ARM B's extra offset is")
        say("    carried by the ISO 50 and ISO 160 stacks, i.e. by the model's ISO")
        say("    scaling -- NOT by the gain measurement. ARM A is the arm that means")
        say("    something, and ARM B's larger number must not be quoted as if it")
        say("    were a cleaner measurement of the same thing.")
    else:
        say("    They agree to within half a point, so the ISO scaling is not")
        say("    visibly contaminating the comparison.")
    result["arms_differ_pp"] = d
say("")

say("WHAT WOULD ACTUALLY SETTLE IT  (registered here, to be run elsewhere)")
say("-" * 78)
say("  The tie between M90 and M71 is 1.33% wide. ARM A's two stacks agree with")
say("  each other to %.3f pp, so the in-stack method has the PRECISION to resolve"
    % (result["armA"]["agree_pp"] if "armA" in result else float("nan")))
say("  a 1.33% difference -- but two stacks is not a measurement of a systematic.")
say("")
say("  The test: run the in-stack temporal PTC on EVERY ISO-100 subject stack in")
say("  the corpus that passes CONSIST, n >= 6, and ask whether the mean offset")
say("  from M90 exceeds its own stack-to-stack standard error. Register the")
say("  direction BEFORE running: on the evidence here it would be POSITIVE, i.e.")
say("  in-stack reads above M90, toward M71.")
say("")
say("  Stating that direction now is what makes the future test falsifiable.")
say("  It is a prediction, not a result, and nothing in this lane rests on it.")

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "b1-tie.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
with open(os.path.join(OUT, "b1-tie.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\nwrote out/b1-tie.json and out/b1-tie.txt")
