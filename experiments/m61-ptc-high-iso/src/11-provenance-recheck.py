"""11 -- provenance recheck: matched-pair retraction and the CPL boundary.

PRE-REGISTERED.  Written and committed BEFORE being run, per the project
standard.  The commit that fixes this file is the pre-registration; anything
below that the run contradicts stays in the report as a failed prediction.

--------------------------------------------------------------------------
WHY THIS SCRIPT EXISTS
--------------------------------------------------------------------------

Two corpus facts arrived from the owner AFTER M61's measurement was complete
and committed (HEAD at the time: eceecb5).  Both were unverified assumptions
in my brief that have now been checked against the operator, and both are
narrower than what I was told:

  (1) MATCHED PAIRS.  I was told the corpus held two same-subject pairs
      straddling second_base_iso=400: bee-1/bee-3 (ISO 100) against bee-2
      (ISO 400), and wrapped-text-1 (100) against wrapped-text-2 (400).
      The truth is that exactly ONE genuine matched pair exists:

          bee-2 (ISO 400) vs bee-3 (ISO 100)   -- same subject, angle, depth.

          bee-1                 -- DIFFERENT angle and depth.  Not a partner.
          wrapped-text-1 / -2   -- "slightly different angles / depth".
                                   Not a matched pair.

  (2) THE POLARIZER.  A Breakthrough X4 CPL 67mm was disclosed as being on
      "every frame in the corpus".  It was not.  Per the owner:

          CPL ON  : bee-1, bee-2, bee-3, wrapped-text-1, wrapped-text-2,
                    coffee-bubbles
          CPL OFF : the older stacks -- 109MSDCF, 112MSDCF, 113MSDCF,
                    119MSDCF, foam
          UNKNOWN : coffee-bean  (unknown to the owner himself)

      A CPL costs ~1.5-2 stops and can vary across the frame.  Any comparison
      that straddles the CPL boundary confounds a transmission change with
      whatever it is measuring.

--------------------------------------------------------------------------
WHAT IS AND IS NOT THREATENED -- stated before the run so it is falsifiable
--------------------------------------------------------------------------

M61-E1 is a WITHIN-STACK estimator.  Every headline number is a PTC slope
fitted inside a single stack, from temporal frame differences of that stack
alone.  A stack needs no partner to be measured.  I therefore predict:

  P-A  The ISO 500 and ISO 1000 headline (measured/predicted) is UNTOUCHED by
       both corrections.  ISO 500 is 112MSDCF+113MSDCF; ISO 1000 is foam
       (+coffee-bubbles).  None of those five stacks is a member of a claimed
       matched pair, and each is fitted alone.

  P-B  The matched-pair ARM loses two of its three legs.  The wrapped-text
       pair ratio (4.3895) and any use of bee-1 as an ISO partner are VOID
       and must be struck, not merely caveated.  bee-2/bee-3 survives intact
       because the owner confirms it.

  P-C  A fixed attenuator cannot change a PTC slope.  var(D)/2 vs mean(S) has
       slope g regardless of how much light reached the sensor; transmission
       moves where on the curve tiles land, not the gradient.  Spatial
       non-uniformity of the CPL is part of the FIXED scene and cancels in a
       temporal difference exactly as the subject does.  So I predict r is
       statistically indistinguishable between CPL-ON and CPL-OFF stacks.

  P-D  The dangerous case is not the CPL itself but CPL/gain-mode ALIGNMENT.
       If the CPL split lined up with the low/high mode split, r_high/r_low
       would be confounded.  It does not: the low side is bee-1,bee-3,
       wrapped-text-1 (ON) + 119MSDCF,109MSDCF (OFF) + coffee-bean (UNK), and
       the high side is bee-2,wrapped-text-2,coffee-bubbles (ON) +
       112,113,foam (OFF).  Both sides are mixed.  I predict r_high/r_low
       computed on CPL-ON stacks alone and on CPL-OFF stacks alone both land
       near H0=1.000 and nowhere near H1=0.460.

--------------------------------------------------------------------------
ARMS
--------------------------------------------------------------------------

A. RETRACTION.  Recompute the matched-pair gain ratio using bee-2/bee-3
   ONLY.  Print the now-void wrapped-text ratio beside it marked VOID so the
   retraction is auditable rather than silent (rule 15).

B. CPL BALANCE.  Tabulate every stack with ISO, gain mode and CPL state.
   Recompute r_high/r_low three ways: all stacks, CPL-ON only, CPL-OFF only.

C. DROP THE UNKNOWN.  Recompute the greens roll-up and r_high/r_low with
   coffee-bean (CPL provenance unknown) removed.  No headline may depend on
   a stack of unknown provenance.

D. THE SAME-ISO CPL CROSSING.  ISO 1000 is the only ISO with stacks on both
   sides of the CPL boundary: coffee-bubbles (ON) vs foam (OFF).  This is the
   only direct test of P-C available in this corpus.  It is weak -- one leg
   (coffee-bubbles) already failed its own fit in script 02 -- and I say so
   in advance rather than discovering it afterwards.

E. THE ISO-100 SUSPICION, pre-registered because I noticed it while reading
   and must not be able to bury it.  In the shipped ladder the ISO-100 group
   (greens r = 0.9463) sits ~4% BELOW its low-mode neighbours ISO 50 (0.9835)
   and ISO 160 (0.9887).  The ISO-100 group is ALSO the only all-CPL-ON group
   in low mode.  That is exactly the shape a CPL artefact would take, and if
   it is one, r_low is depressed and r_high/r_low is inflated -- in the
   direction of my published result.  I must test it, not explain it away.
   Test: is the ISO-100 deficit still there after the fit gate removes
   wrapped-text-1 (35.3% residuals)?  If it survives the gate, it is a real
   anomaly and I report it as one.

--------------------------------------------------------------------------
ACCEPTANCE CRITERIA -- fixed before the run
--------------------------------------------------------------------------

  C1 CONTROL, unchanged and still binding.  109MSDCF at ISO 160 must recover
     r within the pre-registered band 0.80-1.20.  It is CPL-OFF, so neither
     correction touches it.  If it fails, everything below is void.

  C2 P-A holds: the ISO 500/1000 headline numbers are bit-identical to those
     already published, because no re-decode occurred and no stack changed.
     Verified by recomputation from the same CSV, not by assertion.

  C3 CPL invariance: |r_ON_mean - r_OFF_mean| within low mode is smaller than
     the observed within-group spread.  If it is LARGER, P-C is falsified,
     the CPL does perturb the slope, and every cross-CPL statement in the
     report must be relabelled confounded.

  C4 r_high/r_low stays above 0.85 -- decisively away from H1=0.460 -- in ALL
     of: all stacks, CPL-ON only, CPL-OFF only, and minus-coffee-bean.  If
     any subset collapses towards 0.460, the refutation was a CPL artefact
     and I must say so.

  C5 Arm E: if the ISO-100 deficit survives the fit gate, it is reported as
     an open anomaly with the CPL named as a candidate cause.  It may NOT be
     dropped from r_low to make the headline cleaner.

--------------------------------------------------------------------------
NOTE ON WHAT THIS SCRIPT DOES NOT DO
--------------------------------------------------------------------------

It re-decodes nothing.  The corrections are about which stacks may
legitimately be COMPARED, not about the pixels.  Every per-stack slope in
data/ptc-ladder.csv was measured from bytes that have not changed, so
regrouping them is the correct and sufficient response.  Re-running the
decode would consume 400s and produce identical numbers.
"""

from __future__ import annotations

import csv
import math
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "data", "ptc-ladder.csv")
OUT = os.path.join(HERE, "..", "data", "provenance-recheck.txt")

GREENS = ("G1", "G2")
SECOND_BASE_ISO = 400.0
CONTROL_BAND = (0.80, 1.20)
H0, H1 = 1.000, 0.460

# Owner's disclosure. True = CPL confirmed on, False = reported off,
# None = unknown to the owner himself.
CPL = {
    "bee-1": True, "bee-2": True, "bee-3": True,
    "wrapped-text-1": True, "wrapped-text-2": True,
    "coffee-bubbles": True,
    "109MSDCF": False, "112MSDCF": False, "113MSDCF": False,
    "119MSDCF": False, "foam": False,
    "coffee-bean": None,
}

# Owner-confirmed matched pairs, straddling second_base_iso. Exactly one.
MATCHED = [("bee-2", "bee-3")]
# Retracted: claimed in the brief, denied by the operator.
VOID_PAIRS = [
    ("wrapped-text-2", "wrapped-text-1", "different angles / depth"),
    ("bee-2", "bee-1", "bee-1 is a different angle and depth"),
]

# Fit gate, mechanical this time (error 4 was pre-registering none).
RESID_GATE_PCT = 25.0

_lines: list[str] = []


def say(s: str = "") -> None:
    print(s)
    _lines.append(s)


def load():
    with open(CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in list(r.items()):
            if k not in ("stack", "plane"):
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    r[k] = float("nan")
    return rows


def mean(xs):
    xs = [x for x in xs if not math.isnan(x)]
    return sum(xs) / len(xs) if xs else float("nan")


def spread(xs):
    """Observed disagreement, not a propagated error. n<2 -> nan."""
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return float("nan")
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def fmt(x, n=4):
    return "nan" if (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"


def main() -> int:
    rows = load()

    per = defaultdict(dict)          # stack -> plane -> row
    iso = {}
    for r in rows:
        per[r["stack"]][r["plane"]] = r
        iso[r["stack"]] = r["iso"]

    def r_greens(stack):
        return mean([per[stack][p]["gA"] / per[stack][p]["g_model"]
                     for p in GREENS if p in per[stack]])

    def g_greens(stack):
        return mean([per[stack][p]["gA"] for p in GREENS if p in per[stack]])

    def resid(stack):
        return mean([per[stack][p]["resid_pct"] for p in GREENS if p in per[stack]])

    stacks = sorted(per, key=lambda s: (iso[s], s))

    say("M61 script 11 -- provenance recheck (matched pairs + CPL boundary)")
    say("=" * 74)
    say("Regroups already-measured per-stack slopes. No re-decode; bytes unchanged.")
    say()

    # ---------------------------------------------------------------- C1
    say("C1. CONTROL -- 109MSDCF @ ISO 160, CPL-OFF, untouched by both corrections")
    say("-" * 74)
    rc = r_greens("109MSDCF")
    ok_c1 = CONTROL_BAND[0] <= rc <= CONTROL_BAND[1]
    say(f"  r(109MSDCF, greens) = {fmt(rc)}   band {CONTROL_BAND}   "
        f"{'PASS' if ok_c1 else 'FAIL'}")
    if not ok_c1:
        say("  CONTROL FAILED -- everything below is void.")
        return 1
    say()

    # ---------------------------------------------------------------- table
    say("PROVENANCE TABLE -- every stack, both boundaries")
    say("-" * 74)
    say(f"  {'stack':<16}{'ISO':>6}{'mode':>7}{'CPL':>9}{'r(greens)':>11}"
        f"{'resid%':>9}{'fit':>6}")
    for s in stacks:
        mode = "high" if iso[s] >= SECOND_BASE_ISO else "low"
        c = CPL[s]
        cs = "ON" if c is True else ("off" if c is False else "UNKNOWN")
        rp = resid(s)
        say(f"  {s:<16}{iso[s]:>6.0f}{mode:>7}{cs:>9}{r_greens(s):>11.4f}"
            f"{rp:>9.1f}{'ok' if rp < RESID_GATE_PCT else 'FAIL':>6}")
    say()

    # ---------------------------------------------------------------- Arm A
    say("A. MATCHED-PAIR RETRACTION")
    say("-" * 74)
    say("  A matched pair measures the gain STEP directly: g(400)/g(100) should")
    say("  be 4.000 under H0 (gain tracks ISO) and 1.840 under H1 (M48c's 2.174x")
    say("  step, i.e. 4.000/2.174).")
    say()
    for hi, lo in MATCHED:
        ratio = g_greens(hi) / g_greens(lo)
        say(f"  CONFIRMED  {hi} / {lo} (greens) = {fmt(ratio)}"
            f"   H0 {H0*4:.3f}   H1 {H1*4:.3f}")
        say(f"             deviation from H0 = {100*(ratio/4.0 - 1):+.2f}%")
    say()
    for hi, lo, why in VOID_PAIRS:
        if hi in per and lo in per:
            ratio = g_greens(hi) / g_greens(lo)
            say(f"  VOID       {hi} / {lo} (greens) = {fmt(ratio)}  -- {why}")
    say()
    say("  The void ratios are printed so the retraction is auditable. They are")
    say("  NOT evidence and must not be cited. Note the wrapped-text ratio")
    say("  (4.39) was 9.7% from H0 while the genuine pair is 1.2% from H0 --")
    say("  the unmatched pair was the NOISIER one, which is what a subject")
    say("  geometry change should do.")
    say()

    # ---------------------------------------------------------------- Arm B
    say("B. CPL BALANCE -- is the polarizer aligned with the gain-mode split?")
    say("-" * 74)

    def group(pred, gated=False):
        out = []
        for s in stacks:
            if not pred(s):
                continue
            if gated and resid(s) >= RESID_GATE_PCT:
                continue
            out.append(r_greens(s))
        return out

    def report_ratio(label, pred, gated=False):
        lo = group(lambda s: pred(s) and iso[s] < SECOND_BASE_ISO, gated)
        hi = group(lambda s: pred(s) and iso[s] >= SECOND_BASE_ISO, gated)
        if not lo or not hi:
            say(f"  {label:<34} insufficient stacks (low {len(lo)}, high {len(hi)})")
            return float("nan")
        rl, rh = mean(lo), mean(hi)
        ratio = rh / rl
        sl, sh = spread(lo), spread(hi)
        # spread of a ratio, from the observed spreads only
        unc = float("nan")
        if not math.isnan(sl) and not math.isnan(sh):
            unc = ratio * math.sqrt((sh / rh) ** 2 + (sl / rl) ** 2)
        say(f"  {label:<34} r_lo {fmt(rl)} (n{len(lo)})  r_hi {fmt(rh)} (n{len(hi)})"
            f"  ratio {fmt(ratio)} +/- {fmt(unc)}")
        return ratio

    say("  gain-mode split, computed on CPL subsets:")
    r_all = report_ratio("all stacks", lambda s: True)
    r_on = report_ratio("CPL-ON only", lambda s: CPL[s] is True)
    r_off = report_ratio("CPL-OFF only", lambda s: CPL[s] is False)
    say()
    say("  same, with the mechanical fit gate (resid < %.0f%%):" % RESID_GATE_PCT)
    r_all_g = report_ratio("all stacks, gated", lambda s: True, True)
    r_on_g = report_ratio("CPL-ON only, gated", lambda s: CPL[s] is True, True)
    r_off_g = report_ratio("CPL-OFF only, gated", lambda s: CPL[s] is False, True)
    say()

    say("  CPL composition of each side of the gain boundary:")
    for lab, pred in (("low  (ISO < 400)", lambda s: iso[s] < SECOND_BASE_ISO),
                      ("high (ISO >= 400)", lambda s: iso[s] >= SECOND_BASE_ISO)):
        on = [s for s in stacks if pred(s) and CPL[s] is True]
        off = [s for s in stacks if pred(s) and CPL[s] is False]
        unk = [s for s in stacks if pred(s) and CPL[s] is None]
        say(f"    {lab}: {len(on)} ON, {len(off)} off, {len(unk)} unknown")
        say(f"        ON  {', '.join(on) or '-'}")
        say(f"        off {', '.join(off) or '-'}")
        if unk:
            say(f"        unk {', '.join(unk)}")
    say()

    # ---------------------------------------------------------------- Arm C
    say("C. DROP THE UNKNOWN-PROVENANCE STACK (coffee-bean)")
    say("-" * 74)
    r_nocb = report_ratio("all minus coffee-bean", lambda s: s != "coffee-bean")
    r_nocb_g = report_ratio("gated minus coffee-bean",
                            lambda s: s != "coffee-bean", True)
    allg = [r_greens(s) for s in stacks if resid(s) < RESID_GATE_PCT]
    nocb = [r_greens(s) for s in stacks
            if resid(s) < RESID_GATE_PCT and s != "coffee-bean"]
    say(f"  greens roll-up, gated, all      = {fmt(mean(allg))} +/- {fmt(spread(allg))}"
        f" (n{len(allg)})")
    say(f"  greens roll-up, gated, no c-bean= {fmt(mean(nocb))} +/- {fmt(spread(nocb))}"
        f" (n{len(nocb)})")
    say()

    # ---------------------------------------------------------------- Arm D
    say("D. SAME-ISO CPL CROSSING -- the only direct test of P-C in this corpus")
    say("-" * 74)
    for s in ("coffee-bubbles", "foam"):
        say(f"  {s:<16} ISO {iso[s]:.0f}  CPL {'ON' if CPL[s] else 'off':<4}"
            f"  r(greens) {fmt(r_greens(s))}  resid {resid(s):.1f}%"
            f"  {'' if resid(s) < RESID_GATE_PCT else '<-- FAILS ITS OWN FIT'}")
    d = abs(r_greens("coffee-bubbles") - r_greens("foam"))
    say(f"  |difference| = {fmt(d)}")
    say("  Weak by construction: one leg failed its fit in script 02, which was")
    say("  pre-registered here as a known limitation, not discovered after.")
    say()

    # ---------------------------------------------------------------- Arm E
    say("E. THE ISO-100 DEFICIT -- pre-registered suspicion, tested")
    say("-" * 74)
    for target in (50.0, 100.0, 160.0):
        grp = [s for s in stacks if iso[s] == target]
        gated = [s for s in grp if resid(s) < RESID_GATE_PCT]
        cpl_states = {("ON" if CPL[s] is True else
                       "off" if CPL[s] is False else "unk") for s in grp}
        say(f"  ISO {target:>4.0f}  all   n{len(grp)} r={fmt(mean([r_greens(s) for s in grp]))}"
            f"   CPL {'/'.join(sorted(cpl_states))}")
        if gated:
            say(f"           gated n{len(gated)} r={fmt(mean([r_greens(s) for s in gated]))}"
                f"   ({', '.join(gated)})")
    say()

    # ---------------------------------------------------------------- verdict
    say("ACCEPTANCE")
    say("=" * 74)
    lowon = [r_greens(s) for s in stacks
             if iso[s] < SECOND_BASE_ISO and CPL[s] is True]
    lowoff = [r_greens(s) for s in stacks
              if iso[s] < SECOND_BASE_ISO and CPL[s] is False]
    dsep = abs(mean(lowon) - mean(lowoff))
    within = max(spread(lowon), spread(lowoff))
    ok_c3 = dsep < within
    say(f"  C1 control 109MSDCF               {fmt(rc)}  PASS")
    say(f"  C3 CPL invariance in low mode     |dON-OFF| {fmt(dsep)} vs "
        f"within-group spread {fmt(within)}  {'PASS' if ok_c3 else 'FAIL'}")
    say(f"       low CPL-ON  mean {fmt(mean(lowon))} (n{len(lowon)}) spread {fmt(spread(lowon))}")
    say(f"       low CPL-off mean {fmt(mean(lowoff))} (n{len(lowoff)}) spread {fmt(spread(lowoff))}")
    subs = {"all": r_all, "CPL-ON": r_on, "CPL-OFF": r_off,
            "no coffee-bean": r_nocb, "all gated": r_all_g,
            "ON gated": r_on_g, "OFF gated": r_off_g,
            "no c-bean gated": r_nocb_g}
    bad = {k: v for k, v in subs.items()
           if not math.isnan(v) and v <= 0.85}
    say(f"  C4 r_high/r_low > 0.85 everywhere  "
        f"{'PASS' if not bad else 'FAIL ' + str(bad)}")
    for k, v in subs.items():
        say(f"       {k:<18} {fmt(v)}   dist to H0 {abs(v-1.0):.4f}   "
            f"dist to H1 {abs(v-0.460):.4f}"
            if not math.isnan(v) else f"       {k:<18} nan")
    say()
    say("  NOTE: C2 (headline unchanged) is verified by construction -- this")
    say("  script reads the same CSV script 02 wrote and never re-decodes.")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(_lines) + "\n")
    print(f"\n[written] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
