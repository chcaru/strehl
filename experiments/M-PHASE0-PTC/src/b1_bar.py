"""
M-PHASE0-PTC, step 3: what acceptance bar is actually achievable for B1?

WHY THIS STEP EXISTS
--------------------
Step 1 showed B1's stated bar (M90's +/-0.0642% CI) is unreachable: the two best
independent measurements of that same g disagree by 1.33%, and M90 declines to
narrow g beyond a 1.2 pp band. Step 2 measured the per-stack reality: 5 of 6
low-mode stacks inside M90's band, spread -7.53% to +2.37%, and an external
scatter 44x the instrument's own internal precision.

A finding that a bar is wrong is only half a deliverable. This step proposes the
replacement, and does it with M61's OWN established gate rather than a metric
chosen here to make the numbers look good.

THE GATE IS NOT MINE AND THAT IS THE POINT
------------------------------------------
My instinct was to gate on fit residual. M61 MEASURED that this is wrong
(fact 33, and errors 15-16 which record the falsified predictions on the way):

    "it must NOT rest on max residual, because the control (18.2%) and
     119MSDCF (44.7%) score badly there while being clean on every other metric"

M61's surviving gate is CONSIST = `half_pct < 5%` AND `ac_pct < 10%`, chosen by
what a gate must do (reject a stack whose own halves disagree; retain the known-
accurate control) rather than by rank correlation. It is a CONSISTENCY gate: it
asks whether the stack reproduces itself, never whether it agrees with an answer.
That is what makes it legal to apply here -- it cannot select for proximity to
M90 because it never looks at M90.

  half_pct = |g_half0 - g_half1| / mean * 100      (internal replicate spread)
  ac_pct   = |gA - gC|           / mean * 100      (variant spread, A vs C)

CONTROL ON MY IMPLEMENTATION OF SOMEONE ELSE'S GATE
---------------------------------------------------
  C7  CONSIST as implemented here must drop EXACTLY {coffee-bubbles,
      wrapped-text-1} and retain the other ten, reproducing M61 fact 33.

      This is calibration against a published answer, not tuning: the drop list
      was fixed by M61 before this lane existed, and if my aggregation of the
      per-plane columns to a per-stack number is wrong, the list will differ.
      Two aggregations are tried and BOTH are reported. Choosing the one that
      reproduces an independently published list is a control; choosing one that
      improved MY result would not be, and no result below is used to select it.

REGISTERED QUESTION AND DIRECTION
---------------------------------
  R4  Does CONSIST collapse the per-stack accuracy spread toward the internal
      precision?
      REGISTERED DIRECTION: YES, substantially. If the external scatter is
      driven by badly-conditioned fits rather than by a real per-scene gain
      difference, then removing stacks that fail their own internal replicates
      should remove most of the spread. If it does NOT collapse, the scatter is
      physical (real scene-dependent bias) and B1 cannot be rescued by gating --
      that outcome would be the more interesting one and is not being steered
      away from.

  R5  What bar does the surviving evidence support?
      Stated as: the half-width that contains every CONSIST-passing low-mode
      stack, reported alongside M90's band so the two are comparable.
      NO DIRECTION REGISTERED -- this is a readout, not a test.
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(LANE))
CSV_PATH = os.path.join(ROOT, "experiments", "m61-ptc-high-iso", "data", "ptc-ladder.csv")
OUT = os.path.join(LANE, "out")

M90_G_ISO100 = 0.221113
M90_CI_REL_PCT = 0.000142 / 0.221113 * 100.0
M61_DROPS = {"coffee-bubbles", "wrapped-text-1"}          # M61 fact 33

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


def spread_pct(a, b):
    m = (a + b) / 2.0
    return abs(a - b) / m * 100.0 if m else float("inf")


def metrics(planes, how):
    """how='greens' averages G1,G2 first; how='worst' takes the worst plane."""
    if how == "greens":
        keys = ["G1", "G2"]
        h0 = sum(planes[k]["g_half0"] for k in keys) / 2.0
        h1 = sum(planes[k]["g_half1"] for k in keys) / 2.0
        gA = sum(planes[k]["gA"] for k in keys) / 2.0
        gC = sum(planes[k]["gC"] for k in keys) / 2.0
        return spread_pct(h0, h1), spread_pct(gA, gC)
    worst_h, worst_ac = 0.0, 0.0
    for p in planes.values():
        worst_h = max(worst_h, spread_pct(p["g_half0"], p["g_half1"]))
        worst_ac = max(worst_ac, spread_pct(p["gA"], p["gC"]))
    return worst_h, worst_ac


say("M-PHASE0-PTC step 3 -- the achievable bar, under M61's own CONSIST gate")
say("=" * 78)
say("")
say("C7  IMPLEMENTATION CONTROL: reproduce M61 fact 33's drop list")
say("-" * 78)
say("    M61 CONSIST = half_pct < 5%% AND ac_pct < 10%%; drops exactly %s"
    % sorted(M61_DROPS))
say("")

impl = {}
for how in ("greens", "worst"):
    dropped = set()
    per = {}
    for (name, iso), planes in stacks.items():
        h, ac = metrics(planes, how)
        passes = (h < 5.0) and (ac < 10.0)
        per[name] = {"iso": iso, "half_pct": h, "ac_pct": ac, "pass": passes}
        if not passes:
            dropped.add(name)
    match = (dropped == M61_DROPS)
    impl[how] = {"dropped": sorted(dropped), "match": match, "per": per}
    say("    aggregation %-7s -> drops %-40s %s"
        % (how, str(sorted(dropped)), "REPRODUCES M61" if match else "does not match"))

chosen = None
for how in ("greens", "worst"):
    if impl[how]["match"]:
        chosen = how
        break

say("")
if chosen is None:
    say("    C7 FAIL -- neither aggregation reproduces M61's published drop list.")
    say("    No R4/R5 claim is made; the gate is not faithfully implemented here.")
else:
    say("    C7 PASS -- using aggregation '%s'." % chosen)
say("")

result = {"c7": {"impl": {k: {"dropped": v["dropped"], "match": v["match"]}
                          for k, v in impl.items()},
                 "chosen": chosen}}

if chosen is not None:
    per = impl[chosen]["per"]
    say("    per-stack consistency metrics (%s):" % chosen)
    say("      %-16s %6s %10s %9s  %s" % ("stack", "ISO", "half_pct", "ac_pct", "CONSIST"))
    for name in sorted(per, key=lambda n: (per[n]["iso"], n)):
        d = per[name]
        say("      %-16s %6.0f %10.3f %9.3f  %s"
            % (name, d["iso"], d["half_pct"], d["ac_pct"], "pass" if d["pass"] else "DROP"))
    say("")

    # ------------------------------------------------------------------ R4
    say("R4  DOES CONSIST COLLAPSE THE PER-STACK ACCURACY SPREAD?")
    say("-" * 78)
    g_model_100 = stacks[("bee-1", 100.0)]["G1"]["g_model"]
    low = []
    for (name, iso), planes in sorted(stacks.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if iso >= 400:
            continue
        gA = (planes["G1"]["gA"] + planes["G2"]["gA"]) / 2.0
        base = M90_G_ISO100 * (planes["G1"]["g_model"] / g_model_100)
        low.append({"stack": name, "iso": iso, "g": gA,
                    "delta_pct": (gA / base - 1.0) * 100.0,
                    "pass": per[name]["pass"]})

    alld = [x["delta_pct"] for x in low]
    gated = [x["delta_pct"] for x in low if x["pass"]]
    say("    %-16s %6s %9s  %s" % ("stack", "ISO", "delta %", "CONSIST"))
    for x in low:
        say("    %-16s %6.0f %+9.3f  %s" % (x["stack"], x["iso"], x["delta_pct"],
                                            "pass" if x["pass"] else "DROP"))
    say("")
    w_all = max(alld) - min(alld)
    w_gat = max(gated) - min(gated)
    say("    ungated  n=%d  spread %+.3f%% to %+.3f%%   width %.3f pp"
        % (len(alld), min(alld), max(alld), w_all))
    say("    CONSIST  n=%d  spread %+.3f%% to %+.3f%%   width %.3f pp"
        % (len(gated), min(gated), max(gated), w_gat))
    collapse = w_all / w_gat if w_gat else float("inf")
    say("    collapse factor: %.1fx" % collapse)
    verdict_r4 = "CONFIRMED" if collapse > 2.0 else "NOT CONFIRMED"
    say("    registered direction (substantial collapse): %s" % verdict_r4)
    say("")
    if collapse > 2.0:
        say("    => the external scatter was dominated by badly-conditioned fits,")
        say("       not by a real per-scene gain difference. B1 IS rescuable by a")
        say("       consistency gate -- and the gate is one M61 already validated.")
    result["r4"] = {"rows": low, "width_all_pp": w_all, "width_gated_pp": w_gat,
                    "collapse": collapse, "verdict": verdict_r4,
                    "n_all": len(alld), "n_gated": len(gated)}

    # ------------------------------------------------------------------ R5
    say("R5  THE BAR THE EVIDENCE SUPPORTS  (readout, no direction registered)")
    say("-" * 78)
    half_width = max(abs(min(gated)), abs(max(gated)))
    say("    every CONSIST-passing low-mode stack lies within +/-%.3f%% of M90" % half_width)
    say("    B1's stated bar (M90's fit CI):              +/- %.4f%%" % M90_CI_REL_PCT)
    say("    M90's own stated band of ignorance on g:     2.2% to 3.4%")
    say("    ratio, achievable to stated:                 %.0fx" % (half_width / M90_CI_REL_PCT))
    say("")
    say("    PROPOSED REPLACEMENT ACCEPTANCE FOR B1")
    say("    --------------------------------------")
    say("    'On CONSIST-passing stacks (half_pct < 5% AND ac_pct < 10%), the")
    say("     in-stack g agrees with M90's independent value to within +/-%.0f%%," % (half_width + 0.5))
    say("     per stack, from subject frames alone; stacks failing CONSIST are")
    say("     reported as UNMEASURED rather than given a value.'")
    say("")
    say("    Rationale: %.0f%% is inside M90's own 2.2-3.4%% band of ignorance about" % (half_width + 0.5))
    say("    g, so the bar cannot demand more accuracy than the reference itself")
    say("    possesses -- which is exactly the defect in the stated bar.")
    result["r5"] = {"half_width_pct": half_width,
                    "proposed_bar_pct": half_width + 0.5,
                    "stated_bar_pct": M90_CI_REL_PCT,
                    "ratio": half_width / M90_CI_REL_PCT}

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "b1-bar.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
with open(os.path.join(OUT, "b1-bar.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\nwrote out/b1-bar.json and out/b1-bar.txt")
