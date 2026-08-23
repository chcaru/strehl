"""M61 step 17 -- re-run the polariser arm with `foam` corrected to CPL-ON.

WHY THIS SCRIPT EXISTS
----------------------
After M61 was committed (2d7c7c9), the orchestrator routed a correction at
SYNTHESIS fact 925: my committed provenance table puts `foam` under CPL-off,
and that contradicts fact 849. The owner, asked directly about `foam`, said
"probably. i doubt i would've removed it. but don't recall specifically."
`coffee-bubbles` (named CPL-on) and `foam` are 6.5 minutes apart in one
session on 25 May, and a filter is unlikely to be unscrewed in between.

So the corpus currently carries TWO provenance tables and mine is the wrong
one. This script corrects it at source and re-runs every claim that depended
on the membership.

Note the provenance grade: `foam` CPL-ON is PROBABLE (owner recollection,
explicitly hedged), not MEASURED. It is carried as probable below, and the
sensitivity arm exists precisely because it is not certain.

--------------------------------------------------------------------------
PRE-REGISTERED ARMS -- fixed before the run
--------------------------------------------------------------------------

A. ALIGNMENT, recomputed. With `foam` moved ON, recount both sides of the
   dual-gain switch and recompute the switch ratio r_high/r_low WITHIN each
   CPL population under the CONSIST gate. My committed fact 35 reported
   CPL-ON 1.0100, CPL-off 1.0229, all 1.0189. Those numbers must change,
   because the membership changed.

   Criterion: the DESIGN claim -- "the polariser is not aligned with the
   gain split, so it cannot manufacture a step" -- survives if and only if
   BOTH sides of the switch still contain both CPL states. If the correction
   makes the CPL population coincide with a gain mode, the claim fails and I
   must withdraw it, not soften it.

B. IS THE SAME-ISO CPL CROSSING TEST STRUCTURALLY AVAILABLE AT ALL? My
   committed fact 37 says the direct "does a CPL perturb a slope" test was
   void because both legs failed the fit gate. Fact 925 asserts something
   stronger: that after the correction NO ISO in the corpus has stacks on
   both sides of the polariser boundary, so the test is unavailable by
   construction rather than spoiled by data quality.

   This arm enumerates, per ISO, the CPL states present. It is a counting
   exercise with a definite answer and I am checking the orchestrator's
   claim rather than adopting it. Report the table either way.

C. SENSITIVITY -- the arm that matters, because `foam`'s state is a
   recollection. Recompute arm A under THREE assignments of `foam`:
   ON (the correction), off (my committed table), and dropped entirely.
   Report the spread of the switch ratio across all three.

   Criterion: if the H0/H1 verdict is the same under all three, then
   `foam`'s polariser state does not matter to this milestone's conclusion
   and I say so plainly. If it flips under any assignment, the ISO-1000 arm
   depends on an unmeasured recollection and must be labelled that way.

D. THE ISO-1000 PAIR. My committed fact 36 treats "the two ISO-1000 stacks
   straddle the CPL boundary" as a SECOND independent reason to distrust
   ISO 1000. Under the correction both legs are CPL-ON and that reason
   evaporates. Report the ISO-1000 ratio and state explicitly which of my
   published reasons for doubting it survive:
     - gate dependence (survives: coffee-bubbles fails CONSIST regardless)
     - CPL straddle (evaporates if the correction holds)
   Direction matters and I will state it: correcting this REMOVES a reason
   to doubt ISO 1000. I am recording that before I run, so that nobody --
   including me -- can read the outcome as motivated.

E. THE CONTROL, unchanged and re-run for the third time. 109MSDCF is
   CPL-off under every version of the table and is untouched by this
   correction. It must still read within 0.80-1.20 of prediction. If it
   does not, nothing else in this file means anything.

--------------------------------------------------------------------------
WHAT I EXPECT TO BE WRONG ABOUT
--------------------------------------------------------------------------
I predict arm B confirms the orchestrator: no ISO has both CPL states.
I predict arm C shows the verdict is insensitive to `foam`.
Both are checkable and both are recorded here before the run. If either
fails I report the failure rather than the prediction.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "data", "ptc-ladder.csv")
OUT = os.path.join(HERE, "..", "data", "cpl-recorrect.txt")

# ISO per stack, and the CPL provenance AFTER the fact-925 correction.
# grade: "named" = owner named it; "probable" = owner recollection, hedged;
# "unknown" = owner does not know.
STACKS = {
    "119MSDCF":      (50,   "off", "named"),
    "coffee-bean":   (50,   "unk", "unknown"),
    "bee-1":         (100,  "on",  "named"),
    "bee-3":         (100,  "on",  "named"),
    "wrapped-text-1": (100, "on",  "named"),
    "109MSDCF":      (160,  "off", "named"),
    "bee-2":         (400,  "on",  "named"),
    "wrapped-text-2": (400, "on",  "named"),
    "112MSDCF":      (500,  "off", "named"),
    "113MSDCF":      (500,  "off", "named"),
    "coffee-bubbles": (1000, "on", "named"),
    "foam":          (1000, "on",  "probable"),   # <-- the correction
}
SECOND_BASE_ISO = 400
LINES = []


def say(s=""):
    print(s)
    LINES.append(s)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def spread(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def main() -> int:
    with open(CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    by = {}
    for r in rows:
        by.setdefault(r["stack"], {})[r["plane"]] = r

    def r_greens(s):
        g = [float(by[s][p]["ratio"]) for p in ("G1", "G2") if p in by[s]]
        return mean(g)

    def consist(s):
        d = by[s]["G1"]
        return float(d["half_pct"]) < 5.0 and float(d["ac_pct"]) < 10.0

    gated = [s for s in STACKS if s in by and consist(s)]

    say("=" * 74)
    say("M61 step 17 -- polariser arm re-run with `foam` corrected to CPL-ON")
    say("SYNTHESIS fact 925 / 849; owner: 'probably. i doubt i would've removed it.'")
    say("=" * 74)
    say()
    say("CORRECTED PROVENANCE TABLE (grade in brackets)")
    say(f"  {'stack':<16}{'ISO':>6}{'mode':>7}{'CPL':>6}  grade")
    for s, (iso, cpl, grade) in sorted(STACKS.items(), key=lambda kv: kv[1][0]):
        mode = "high" if iso >= SECOND_BASE_ISO else "low"
        say(f"  {s:<16}{iso:>6}{mode:>7}{cpl:>6}  {grade}")
    say()

    # ---------------- arm E: the control, first ----------------
    say("-" * 74)
    say("ARM E -- THE CONTROL (109MSDCF, ISO 160, CPL-off under every table)")
    say("-" * 74)
    ctrl = r_greens("109MSDCF")
    ok = 0.80 <= ctrl <= 1.20
    say(f"  measured/predicted, greens = {ctrl:.4f}")
    say(f"  band 0.80-1.20            -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        say("  CONTROL FAILED -- nothing below is meaningful.")
        _write()
        return 1
    say()

    # ---------------- arm A: alignment ----------------
    say("-" * 74)
    say("ARM A -- IS THE POLARISER ALIGNED WITH THE GAIN SPLIT?")
    say("-" * 74)
    for label, pool in (("all stacks", list(STACKS)), ("CONSIST-gated", gated)):
        say(f"  {label}:")
        for mode, lo, hi in (("low ", 0, SECOND_BASE_ISO),
                             ("high", SECOND_BASE_ISO, 10 ** 9)):
            got = {"on": [], "off": [], "unk": []}
            for s in pool:
                iso, cpl, _ = STACKS[s]
                if lo <= iso < hi:
                    got[cpl].append(s)
            say(f"    {mode} mode: on={len(got['on'])} off={len(got['off'])} "
                f"unk={len(got['unk'])}   "
                f"on={sorted(got['on'])} off={sorted(got['off'])}")
        say()

    def switch_ratio(pool):
        lo = [r_greens(s) for s in pool if STACKS[s][0] < SECOND_BASE_ISO]
        hi = [r_greens(s) for s in pool if STACKS[s][0] >= SECOND_BASE_ISO]
        if not lo or not hi:
            return None, len(lo), len(hi)
        return mean(hi) / mean(lo), len(lo), len(hi)

    say("  switch ratio r_high/r_low within each CPL population (CONSIST gate):")
    say(f"    {'population':<20}{'ratio':>9}{'n_low':>7}{'n_high':>8}")
    for label, pool in (
            ("CPL-ON", [s for s in gated if STACKS[s][1] == "on"]),
            ("CPL-off", [s for s in gated if STACKS[s][1] == "off"]),
            ("all gated", gated)):
        v, nl, nh = switch_ratio(pool)
        vs = f"{v:.4f}" if v is not None else "n/a"
        say(f"    {label:<20}{vs:>9}{nl:>7}{nh:>8}")
    say()
    say("  H0 (no gain step) predicts 1.0; H1 (M48c's 2.174x step) predicts 1.840.")
    say("  DESIGN CRITERION: both sides of the switch must still contain both")
    say("  CPL states, or the 'not aligned' claim is withdrawn.")
    lo_states = {STACKS[s][1] for s in STACKS if STACKS[s][0] < SECOND_BASE_ISO}
    hi_states = {STACKS[s][1] for s in STACKS if STACKS[s][0] >= SECOND_BASE_ISO}
    mixed = {"on", "off"} <= lo_states and {"on", "off"} <= hi_states
    say(f"  low-mode CPL states  = {sorted(lo_states)}")
    say(f"  high-mode CPL states = {sorted(hi_states)}")
    say(f"  both sides mixed     -> {'YES, claim survives' if mixed else 'NO, WITHDRAW'}")
    say()

    # ---------------- arm B: is the crossing test available ----------------
    say("-" * 74)
    say("ARM B -- IS A SAME-ISO CPL CROSSING AVAILABLE ANYWHERE IN THE CORPUS?")
    say("-" * 74)
    say(f"  {'ISO':>6}  {'CPL states present':<26} usable crossing?")
    any_cross = False
    for iso in sorted({v[0] for v in STACKS.values()}):
        here = [(s, STACKS[s][1]) for s in STACKS if STACKS[s][0] == iso]
        states = sorted({c for _, c in here})
        cross = "on" in states and "off" in states
        any_cross = any_cross or cross
        desc = ", ".join(f"{s}({c})" for s, c in sorted(here))
        say(f"  {iso:>6}  {str(states):<26} {'YES' if cross else 'no'}   {desc}")
    say()
    say(f"  any ISO with both states -> {'YES' if any_cross else 'NO'}")
    say("  If NO: the direct 'does a CPL perturb a slope' test is STRUCTURALLY")
    say("  UNAVAILABLE in this corpus, not merely spoiled by fit quality.")
    say("  That is a stronger and more useful statement than the one I published.")
    say()

    # ---------------- arm C: sensitivity ----------------
    say("-" * 74)
    say("ARM C -- SENSITIVITY OF THE VERDICT TO `foam`'s POLARISER STATE")
    say("-" * 74)
    say("  `foam` CPL-ON is a hedged recollection, so the verdict must be")
    say("  checked under every assignment it could take.")
    say()
    say(f"  {'assumption':<22}{'CPL-ON':>9}{'CPL-off':>9}{'all':>9}")
    verdicts = []
    for label, state in (("foam ON (corrected)", "on"),
                         ("foam off (published)", "off"),
                         ("foam dropped", None)):
        pool = [s for s in gated if not (s == "foam" and state is None)]
        assign = dict((s, STACKS[s][1]) for s in pool)
        if state is not None and "foam" in assign:
            assign["foam"] = state
        cells = []
        for want in ("on", "off", None):
            sub = [s for s in pool if want is None or assign[s] == want]
            v, _, _ = switch_ratio(sub)
            cells.append(v)
            if want is None:
                verdicts.append((label, v))
        say(f"  {label:<22}" + "".join(
            f"{(f'{c:.4f}' if c is not None else 'n/a'):>9}" for c in cells))
    say()
    say("  distance to H0 (1.000) and to H1 (1.840), 'all gated' column:")
    flip = False
    for label, v in verdicts:
        if v is None:
            continue
        d0, d1 = abs(v - 1.0), abs(v - 1.840)
        closer = "H0" if d0 < d1 else "H1"
        flip = flip or closer == "H1"
        say(f"    {label:<22} ratio={v:.4f}  |d(H0)|={d0:.4f}  "
            f"|d(H1)|={d1:.4f}  -> closer to {closer}")
    say()
    say(f"  verdict flips under any assignment -> {'YES' if flip else 'NO'}")
    say()

    # ---------------- arm D: the ISO-1000 pair ----------------
    say("-" * 74)
    say("ARM D -- WHICH REASONS TO DOUBT ISO 1000 SURVIVE THE CORRECTION?")
    say("-" * 74)
    for s in ("coffee-bubbles", "foam"):
        d = by[s]["G1"]
        say(f"  {s:<16} r_greens={r_greens(s):.4f}  half={float(d['half_pct']):.1f}%  "
            f"ac={float(d['ac_pct']):.1f}%  CONSIST={'keep' if consist(s) else 'DROP'}  "
            f"CPL={STACKS[s][1]}({STACKS[s][2]})")
    say()
    say("  reason 1, gate dependence: coffee-bubbles fails CONSIST on its own")
    say("    internal replicates (split-half), which has nothing to do with the")
    say("    polariser. SURVIVES the correction.")
    say("  reason 2, CPL straddle: under the correction both ISO-1000 legs are")
    say("    CPL-ON, so there is no straddle. EVAPORATES.")
    say("  Net direction: the correction REMOVES a reason to doubt ISO 1000.")
    say("  Pre-registered above, before the run, so it cannot be read as motivated.")
    say()
    say("=" * 74)
    say("Every number above is a re-grouping of the committed ptc-ladder.csv.")
    say("No frame was re-decoded; the correction concerns provenance, not pixels.")
    say("=" * 74)
    _write()
    return 0


def _write():
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"\n[wrote {OUT}]")


if __name__ == "__main__":
    sys.exit(main())
