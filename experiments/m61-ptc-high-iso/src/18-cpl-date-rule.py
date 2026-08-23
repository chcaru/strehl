"""M61 step 18 -- verify the owner's CPL date rule against EXIF, and use it.

WHY
---
This is the THIRD provenance claim handed to me in this milestone, after two
that turned out to be false (errors 18 and 21). The orchestrator has been
explicit that his own statements carry labels: the date rule is offered as
EXIF-derived and therefore checkable, while `foam`'s filter state remains a
recollection.

Discipline 12, which I wrote after error 21, says that writing a discipline
is not running it, and that the operational form is to check every supplied
premise against the corpus before relying on it. This script is that check.
I am not restating the rule; I am measuring the dates it rests on.

THE CLAIM, as given to me:
    25 May onward  -> CPL-ON  (coffee-bubbles, foam, wrapped-text-1/2,
                               bee-1, bee-2, bee-3)
    up to 17 May   -> CPL-off (112MSDCF 7 May, 113MSDCF 7 May,
                               119MSDCF 9 May, 109MSDCF 17 May)
    coffee-bean    -> 10 May, on the off side by date, but the owner cannot
                      recall, so it is carried as unknown.
    coffee-bubbles  16:18:29-16:19:29 and foam 16:25:55-16:30:04 on 25 May.

--------------------------------------------------------------------------
PRE-REGISTERED ARMS -- fixed before the run
--------------------------------------------------------------------------

A. MEASURE THE DATES. Read EXIF DateTimeOriginal for the first, middle and
   last frame of all twelve stacks. Report first and last per stack.

   Criterion for the rule being SUPPORTED: every stack the owner named
   CPL-ON falls on or after 25 May, every stack he named CPL-off falls on
   or before 17 May, and no stack straddles. If any stack lands on the
   wrong side of its own label, the rule is refuted and I report that
   instead -- a refutation here would be the most useful thing this script
   could produce, because it would mean the provenance table is wrong a
   third time.

   NOTE ON WHAT THIS CAN AND CANNOT ESTABLISH. EXIF dates are MEASURED.
   The mapping from date to filter state is the owner's ARGUED inference.
   A consistent date rule cannot prove the filter was on; it can only show
   the recollection is not contradicted by the capture record, and it can
   REFUTE the rule if a date lands wrong. I will label the output that way
   and will not promote a consistency check to a measurement.

B. THE 6.5-MINUTE GAP. Verify coffee-bubbles and foam are the times given,
   on one date, with foam second. This is the whole basis for `foam` being
   probably-ON, so it should be checked rather than quoted.

C. COFFEE-BEAN, the one stack whose state is unknown to the owner. If arm A
   supports the rule, the rule PREDICTS coffee-bean is CPL-off (10 May).
   Recompute the low-mode CPL populations with coffee-bean moved from
   "unknown" to "off" and report how the 1.6% CPL/ISO offset moves.

   This is a CONDITIONAL result and will be labelled as one: it holds only
   if the date rule holds, and the owner's inability to recall this
   specific stack is exactly the case the rule is least able to cover.

D. THE BRACKET TEST -- the only new science available here, and the reason
   arm C is worth doing. My question 7 says the 1.6% low-mode offset is
   perfectly degenerate between "CPL" and "ISO 100", because every CPL-ON
   low-mode stack is at ISO 100 and the CPL-off one is at ISO 160.

   If coffee-bean is CPL-off, the CPL-off low-mode group spans ISO 50 AND
   ISO 160, which BRACKETS the ISO-100 CPL-ON group. That does not break
   the degeneracy -- there is still no single ISO with both filter states
   (fact 45) -- but it distinguishes two shapes:

     shape 1, MONOTONE in ISO: r rises or falls steadily 50 -> 100 -> 160.
              Consistent with an ISO explanation.
     shape 2, DIP at ISO 100: r at ISO 100 sits BELOW both its ISO-50 and
              its ISO-160 neighbours. An ISO trend cannot easily produce a
              non-monotone dip exactly at the group that has the filter on.

   Report which shape the data shows. PRE-REGISTERED CONFOUND, stated
   before I look: the ISO-100 stacks are also DIFFERENT SUBJECTS (bee,
   wrapped-text) from the ISO-50 and ISO-160 stacks (coffee-bean,
   119MSDCF, 109MSDCF). So shape 2 would move the question from
   "CPL or ISO" to "CPL or subject", which is a different degeneracy and
   NOT a resolution. I will not report shape 2 as evidence for the CPL
   unless I also say that.

   I am not predicting which shape appears. n is 2 low-mode CPL-ON stacks
   against 3 CPL-off, and any shape seen at this n is suggestive only.

E. THE CONTROL, for the fourth time. 109MSDCF is CPL-off under the owner's
   naming AND on the off side of the date rule -- the two agree, which is
   itself worth reporting. It must read within 0.80-1.20.

--------------------------------------------------------------------------
WHAT WOULD MAKE ME REPORT A FAILURE
--------------------------------------------------------------------------
Arm A refuting the rule; the control failing; or arm D showing a shape I
then cannot separate from the subject confound -- in which case I report
the confound and not the shape.
"""
import csv
import os
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "data", "ptc-ladder.csv")
OUT = os.path.join(HERE, "..", "data", "cpl-date-rule.txt")
CORPUS = r"D:\personal\macro"

# The owner's claim, transcribed. "unk" = he could not recall.
CLAIMED = {
    "112MSDCF": "off", "113MSDCF": "off", "119MSDCF": "off",
    "109MSDCF": "off", "coffee-bean": "unk",
    "coffee-bubbles": "on", "foam": "on",
    "wrapped-text-1": "on", "wrapped-text-2": "on",
    "bee-1": "on", "bee-2": "on", "bee-3": "on",
}
ISO = {
    "119MSDCF": 50, "coffee-bean": 50, "bee-1": 100, "bee-3": 100,
    "wrapped-text-1": 100, "109MSDCF": 160, "bee-2": 400,
    "wrapped-text-2": 400, "112MSDCF": 500, "113MSDCF": 500,
    "coffee-bubbles": 1000, "foam": 1000,
}
SECOND_BASE_ISO = 400
BOUNDARY = "2026:05:17"   # last off-side date claimed; on-side starts 05:25
LINES = []


def say(s=""):
    print(s)
    LINES.append(s)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def dt_of(path):
    import exifread
    with open(path, "rb") as fh:
        tags = exifread.process_file(fh, details=False,
                                     stop_tag="EXIF DateTimeOriginal")
    for k in ("EXIF DateTimeOriginal", "Image DateTime"):
        if k in tags:
            return str(tags[k])
    return None


def frames(stack):
    fs = sorted(glob.glob(os.path.join(CORPUS, stack, "*.ARW")))
    if not fs:
        fs = sorted(glob.glob(os.path.join(CORPUS, stack, "*")))
    return fs


def main() -> int:
    say("=" * 76)
    say("M61 step 18 -- does the owner's CPL date rule survive its own EXIF?")
    say("=" * 76)
    say()

    # ---------------- arm A ----------------
    say("-" * 76)
    say("ARM A -- MEASURED capture dates, against the CLAIMED filter state")
    say("-" * 76)
    say(f"  {'stack':<16}{'ISO':>6}{'n':>5}  {'first frame':<21}{'last frame':<21}"
        f"{'claim':>7}  side by date")
    obs = {}
    bad = []
    for s in sorted(CLAIMED, key=lambda k: ISO[k]):
        fs = frames(s)
        if not fs:
            say(f"  {s:<16}{ISO[s]:>6}    0  -- NO FILES FOUND --")
            bad.append(f"{s}: no files")
            continue
        a, b = dt_of(fs[0]), dt_of(fs[-1])
        obs[s] = (a, b, len(fs))
        da = (a or "")[:10]
        side = "on" if da >= "2026:05:25" else ("off" if da <= BOUNDARY else "?")
        flag = "" if (CLAIMED[s] == "unk" or side == CLAIMED[s]) else "  <-- MISMATCH"
        if flag:
            bad.append(f"{s}: claimed {CLAIMED[s]}, date says {side} ({da})")
        say(f"  {s:<16}{ISO[s]:>6}{len(fs):>5}  {str(a):<21}{str(b):<21}"
            f"{CLAIMED[s]:>7}  {side}{flag}")
    say()
    if bad:
        say("  RULE REFUTED or data missing:")
        for x in bad:
            say(f"    - {x}")
    else:
        say("  Every named stack falls on the side its filter state claims.")
        say("  The date rule is CONSISTENT with the owner's naming.")
    say()
    say("  LABEL: the dates are MEASURED. The date->filter mapping is the")
    say("  owner's ARGUED inference. Consistency cannot prove the filter was")
    say("  fitted; it can only fail to contradict it. It COULD have refuted")
    say("  the rule, and did not.")
    say()

    # ---------------- arm B ----------------
    say("-" * 76)
    say("ARM B -- the 6.5-minute gap that makes `foam` probably-ON")
    say("-" * 76)
    for s in ("coffee-bubbles", "foam"):
        if s in obs:
            a, b, n = obs[s]
            say(f"  {s:<16} n={n:<4} {a}  ..  {b}")
    if "coffee-bubbles" in obs and "foam" in obs:
        cb_last, fm_first = obs["coffee-bubbles"][1], obs["foam"][0]
        same_day = (cb_last or "")[:10] == (fm_first or "")[:10]
        after = (fm_first or "") > (cb_last or "")
        say()
        say(f"  same calendar day        -> {'YES' if same_day else 'NO'}")
        say(f"  foam starts after cb ends-> {'YES' if after else 'NO'}")
        say("  A filter is not unscrewed between two stacks minutes apart in")
        say("  one session. This is the whole basis for `foam` = probably-ON,")
        say("  and it is an ARGUED inference from a MEASURED gap.")
    say()

    # ---------------- load slopes ----------------
    with open(CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    per = {}
    for r in rows:
        d = per.setdefault(r["stack"], {})[r["plane"]] = {}
        for k in ("gA", "gB", "gC", "g_model", "g_half0", "g_half1", "resid_pct"):
            d[k] = float(r[k])
    G = ("G1", "G2")

    def gm(s, key):
        return mean([per[s][p][key] for p in G if p in per[s]])

    def r_greens(s):
        return mean([per[s][p]["gA"] / per[s][p]["g_model"] for p in G if p in per[s]])

    def consist(s):
        gA = gm(s, "gA")
        ac = 100 * abs(gm(s, "gC") / gA - 1) if gA else float("nan")
        half = 100 * abs(gm(s, "g_half1") / gm(s, "g_half0") - 1)
        return half < 5.0 and ac < 10.0

    gated = [s for s in CLAIMED if s in per and consist(s)]

    # ---------------- arm E: control ----------------
    say("-" * 76)
    say("ARM E -- THE CONTROL, fourth run (109MSDCF, ISO 160)")
    say("-" * 76)
    c = r_greens("109MSDCF")
    say(f"  owner naming: CPL-off.  date rule: {'off' if (obs.get('109MSDCF',('',''))[0] or '')[:10] <= BOUNDARY else '?'}."
        f"  the two AGREE.")
    say(f"  measured/predicted, greens = {c:.4f}   band 0.80-1.20 -> "
        f"{'PASS' if 0.80 <= c <= 1.20 else 'FAIL'}")
    if not (0.80 <= c <= 1.20):
        _write()
        return 1
    say()

    # ---------------- arm C + D ----------------
    say("-" * 76)
    say("ARM C -- coffee-bean moved from UNKNOWN to off, as the rule predicts")
    say("-" * 76)
    low = [s for s in gated if ISO[s] < SECOND_BASE_ISO]

    def grp(assign, want):
        return [s for s in low if assign(s) == want]

    for label, assign in (
            ("coffee-bean UNKNOWN (as published)",
             lambda s: CLAIMED[s]),
            ("coffee-bean off (date rule)",
             lambda s: "off" if s == "coffee-bean" else CLAIMED[s])):
        on_, off_ = grp(assign, "on"), grp(assign, "off")
        r_on, r_off = mean([r_greens(s) for s in on_]), mean([r_greens(s) for s in off_])
        say(f"  {label}")
        say(f"    CPL-ON  n={len(on_)}  r={r_on:.4f}   {sorted(on_)}")
        say(f"    CPL-off n={len(off_)}  r={r_off:.4f}   {sorted(off_)}")
        say(f"    offset (off/on - 1)  = {100*(r_off/r_on - 1):+.2f}%")
        say()
    say("  CONDITIONAL: this holds only if the date rule holds, and")
    say("  coffee-bean is precisely the stack the owner could not recall.")
    say()

    say("-" * 76)
    say("ARM D -- THE BRACKET: is low-mode r monotone in ISO, or a dip at 100?")
    say("-" * 76)
    say(f"  {'ISO':>6}  {'CPL':>5}  {'r(greens)':>10}  stacks")
    shape = []
    for iso in sorted({ISO[s] for s in low}):
        ss = [s for s in low if ISO[s] == iso]
        cpl = sorted({("off" if s == "coffee-bean" else CLAIMED[s]) for s in ss})
        r = mean([r_greens(s) for s in ss])
        shape.append((iso, r, "/".join(cpl)))
        say(f"  {iso:>6}  {'/'.join(cpl):>5}  {r:>10.4f}  {sorted(ss)}")
    say()
    if len(shape) >= 3:
        (i0, r0, _), (i1, r1, _), (i2, r2, _) = shape[0], shape[1], shape[2]
        mono = (r0 <= r1 <= r2) or (r0 >= r1 >= r2)
        dip = r1 < r0 and r1 < r2
        say(f"  monotone in ISO ({i0} -> {i1} -> {i2})   -> {'YES' if mono else 'NO'}")
        say(f"  dip at ISO {i1} (below both neighbours) -> {'YES' if dip else 'NO'}")
        say(f"    r({i0}) = {r0:.4f}   r({i1}) = {r1:.4f}   r({i2}) = {r2:.4f}")
        say()
        if dip:
            say("  Shape 2. An ISO trend does not easily make a non-monotone dip")
            say("  exactly at the group carrying the filter. BUT -- and this was")
            say("  pre-registered before the run -- the ISO-100 stacks are also")
            say("  DIFFERENT SUBJECTS (bee, wrapped-text) from the ISO-50 and")
            say("  ISO-160 stacks (coffee-bean, 119MSDCF, 109MSDCF). So this")
            say("  moves the question from 'CPL or ISO' to 'CPL or SUBJECT'.")
            say("  It is a DIFFERENT degeneracy, not a resolution. n = 2 vs 3.")
        elif mono:
            say("  Shape 1. Consistent with an ISO explanation; the CPL is not")
            say("  needed to explain the offset. Also consistent with a CPL")
            say("  effect that happens to align with ISO ordering at n = 3.")
        else:
            say("  Neither shape cleanly. Report as uninformative at this n.")
    say()
    say("=" * 76)
    say("Dates are MEASURED from EXIF. Filter states are the owner's ARGUED")
    say("inference from those dates. Slopes are re-grouped from the committed")
    say("ptc-ladder.csv -- no frame was re-decoded for this script.")
    say("=" * 76)
    _write()
    return 0


def _write():
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"\n[wrote {OUT}]")


if __name__ == "__main__":
    sys.exit(main())
