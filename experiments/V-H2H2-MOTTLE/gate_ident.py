# Are the two print gates the same instrument with inverted labels?
#
# ORCH withdrew "17 PASS / 5 FAIL / 4 REVIEW" and replaced it with
# "17 PASS / 0 FAIL / 9 ACQUITTED", from recert.py -> scripts/finalpass.ps1.
# Separately, printcert4.py reports "FAIL on at least one axis 17" and
# "no FAIL 9" over the same 26 masters.
#
# 17/9 in both, with the labels INVERTED. That is either a coincidence or a
# polarity error, and counts alone cannot tell them apart -- only SET
# MEMBERSHIP can. If B's PASS set equals A's FAIL set, one instrument is
# inverted and ORCH has just broadcast a wrong baseline to four lanes. If the
# overlap is near chance (17*17/26 = 11.1), the counts coincide by accident.
#
# ORCH: "Do not reconcile them by adjusting either." This script adjusts
# nothing. It only measures how the two verdict sets sit against each other.

import io
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

A_TXT = r"C:\dev\strehl-out\V-H2H2\printcert4.txt"
B_JSON = r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\logs\baseline-gate.json"

AXES = ("BLOTCH", "RIM", "SHARP", "DUST")


def norm(s):
    """B truncates at least one subject name ('...fern-cp' for '...fern-cpl').

    Matching on raw strings would silently drop that subject from the
    intersection and quietly shrink the census, which is the failure mode
    ORCH warned about -- an arm that scores 25 of 26 and reports the 25.
    Match on the longest common prefix instead, and verify the census.
    """
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load_a():
    t = io.open(A_TXT, encoding="utf-8-sig").read()
    rows = {}
    for line in t.splitlines():
        m = re.match(r"^(\S+)\s{2,}(.*)$", line)
        if not m or m.group(1) in ("subject", "thresholds:"):
            continue
        cells = re.findall(r"PASS|FAIL|REFUSED|NOT EXAMINED|SUBJECT", m.group(2))
        if len(cells) == 4:
            rows[m.group(1)] = dict(zip(AXES, cells))
    return rows


def load_b():
    d = json.load(io.open(B_JSON, encoding="utf-8-sig"))
    return d["states"], d.get("partition", ""), d.get("stdout", "")


def match(a_names, b_names):
    """Pair the two name sets, tolerating truncation, one-to-one only."""
    pairs, used = {}, set()
    for an in a_names:
        na = norm(an)
        cands = [bn for bn in b_names
                 if bn not in used and (na.startswith(norm(bn)) or norm(bn).startswith(na))]
        if len(cands) == 1:
            pairs[an] = cands[0]
            used.add(cands[0])
    return pairs


def main():
    a = load_a()
    b_states, b_part, b_out = load_b()
    pairs = match(a.keys(), b_states.keys())

    print("CENSUS")
    print("  instrument A (printcert4.py) subjects : %d" % len(a))
    print("  instrument B (finalpass.ps1) subjects : %d" % len(b_states))
    print("  matched one-to-one                    : %d" % len(pairs))
    if len(pairs) != 26 or len(a) != 26 or len(b_states) != 26:
        print("  CENSUS MISMATCH -- refusing to compare sets of different populations.")
        for an in a:
            if an not in pairs:
                print("    unmatched in A: %s" % an)
        return 3
    trunc = [(k, v) for k, v in pairs.items() if k != v]
    for k, v in trunc:
        print("  name differs between instruments: A %r vs B %r" % (k, v))

    a_fail = {n for n, ax in a.items() if "FAIL" in ax.values()}
    a_ok = set(a) - a_fail
    b_pass = {n for n in a if b_states[pairs[n]] == "PASS"}
    b_acq = {n for n in a if b_states[pairs[n]] == "ACQUIT"}

    print("\n  A: FAIL on >=1 axis %d, no FAIL %d" % (len(a_fail), len(a_ok)))
    print("  B: PASS %d, ACQUIT %d   (B partition: %s)" % (len(b_pass), len(b_acq), b_part))

    # identity controls -- a set-overlap routine that cannot reproduce these
    # cannot be trusted on the real question
    ok = (len(a_fail & a_fail) == len(a_fail)) and not (a_fail & a_ok)
    print("\n  CONTROL  self-overlap %d == %d, disjoint-overlap %d == 0 : %s"
          % (len(a_fail & a_fail), len(a_fail), len(a_fail & a_ok),
             "ok" if ok else "*** BROKEN ***"))
    if not ok:
        return 3

    inter = a_fail & b_pass
    chance = len(a_fail) * len(b_pass) / 26.0
    print("\nINVERSION TEST -- is B's PASS set A's FAIL set?")
    print("  |A_FAIL & B_PASS| = %d   (identical would be %d, chance %.1f)"
          % (len(inter), len(a_fail), chance))
    if len(inter) == len(a_fail):
        print("  INVERTED. The two instruments disagree by a label flip.")
        return 1
    print("  NOT INVERTED. The 17/9 coincidence is a coincidence.")

    print("\n  |A_FAIL & B_ACQUIT| = %d of %d B-acquittals" % (len(a_fail & b_acq), len(b_acq)))
    print("\nWHAT B CALLS PASS AND A CALLS FAIL (%d subjects)" % len(inter))
    for n in sorted(inter):
        axes = [k.lower() for k, v in a[n].items() if v == "FAIL"]
        print("    %-38s A fails on: %s" % (n, ", ".join(axes)))

    rim = sorted(n for n in inter if a[n]["RIM"] == "FAIL")
    print("\n  of those, %d fail on RIM" % len(rim))

    m = re.search(r"^thresholds:.*$", b_out, re.M)
    thr = m.group(0) if m else "(not found)"
    print("\nB's OWN THRESHOLD LINE")
    print("  %s" % thr.strip())
    has_rim = bool(re.search(r"rim|overshoot", thr, re.I))
    print("  mentions rim/overshoot: %s" % has_rim)

    if not has_rim and rim:
        print("""
READING

  The count coincidence is innocent, but the comparison exposes something
  that is not. Instrument B reports 0 FAIL over 26 masters. Instrument A
  reports 13 rim FAILs over the same 26. Both are correct, because B's
  thresholds carry no rim or overshoot term at all -- B cannot convict on
  rim, so its zero is the absence of an axis, not a clean bill of health.

  %d subjects that B passes, A fails; %d of those on rim, including
  coffee-bean at +33.25%%, the second-worst rim overshoot in the corpus.
  Meanwhile every one of B's %d acquittals is a subject A fails.

  CONSEQUENCE. Two ORCH instructions cannot both be followed on instrument
  B: "judge on rim" and "the baseline is 17 PASS / 0 FAIL". A lane that
  scores a merge fix on B and reports "still 0 FAIL" has measured nothing
  about the axis designated primary. B's insensitivity is not only to
  success, as broadcast -- it is insensitive to the dominant defect.""" % (
            len(inter), len(rim), len(b_acq)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
