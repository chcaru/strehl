#!/usr/bin/env python3
"""How much power does PREREG clause (c) actually have?

Clause (c) reads: "Zero subjects move PASS -> FAIL on blotch, rim or sharp."

A no-regression clause can only observe a regression on a subject that is
currently PASS.  A subject already FAILing an axis cannot move PASS -> FAIL on
it no matter how much the candidate damages it, so every already-FAIL subject is
a place where clause (c) is blind BY CONSTRUCTION.

ORCH withdrew the 17 PASS / 5 FAIL / 4 REFUSED baseline and warned that the
replacement gate is "insensitive to success by construction" on the six mottle
subjects.  That warning was about orch_printready.py.  Clause (c) grades a
DIFFERENT instrument -- printcert4.py, axes blotch/rim/sharp -- so the warning
does not transfer automatically.  This script measures whether the same
structural blindness is present here, instead of assuming either way.

It calls printcert4's own verdict functions.  It writes nothing outside this
lane's tree and does not re-run any axis measurement.

PARTITION
---------
Every subject is resolved into exactly one state per axis and the states are
counted so they sum to the subject count.  A subject whose axis record is
missing reads MISSING, never PASS.
"""

from __future__ import annotations

import collections
import json
import os
import sys

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
os.chdir(r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")

import printcert4 as pc  # noqa: E402

GRADABLE = ("blotch", "rim", "sharp")


def main() -> int:
    # `load` takes the filename WITH its extension and returns {} for a missing
    # path. Calling it as load("delivered") therefore yields an empty dict and
    # every downstream partition sums trivially -- 0 == 0. That is the
    # "examined: 0 reads as corrected: 0" failure, and it produced a clean-
    # looking census here before the guard below was added.
    deliv, cert = pc.load("delivered.json"), pc.load("cert.json")
    rim, sharp, dust = pc.load("rim.json"), pc.load("sharp.json"), pc.load("dust.json")
    for name, d in (("delivered", deliv), ("cert", cert), ("rim", rim),
                    ("sharp", sharp), ("dust", dust)):
        if not d:
            raise SystemExit("ABORT: %s.json loaded empty -- a census over an empty "
                             "population sums perfectly and means nothing" % name)

    # Subjects come from the seal directory, not from the axis JSONs. An axis
    # file that is short (sharp.json carries 19 of 26) must show up as subjects
    # MISSING that axis, not as a smaller population that passes completely.
    seals = sorted(f[:-len("--SHIP-V4.tiff")] for f in os.listdir(pc.pc.SEAL_DIR)
                   if f.endswith("--SHIP-V4.tiff"))
    okseals = [f for f in os.listdir(pc.pc.SEAL_DIR) if f.endswith(".tiff.ok")]
    if len(okseals) != len(seals):
        raise SystemExit("POPULATION DISAGREES WITH SEALS: %d masters, %d seals"
                         % (len(seals), len(okseals)))
    subjects = seals
    margin, _ = pc.pc.price_sampling_bias(cert)

    print("=" * 96)
    print("CLAUSE (c) POWER CENSUS -- instrument: printcert4.py (blotch/rim/sharp/dust)")
    print("=" * 96)
    print("subjects: %d (from %d sealed masters, cross-checked against %d .ok seals)"
          % (len(subjects), len(seals), len(okseals)))
    print("axis record coverage: delivered %d, cert %d, rim %d, sharp %d, dust %d"
          % (len(deliv), len(cert), len(rim), len(sharp), len(dust)))
    print()

    per_axis: dict[str, collections.Counter] = {a: collections.Counter() for a in pc.AXES}
    rows: dict[str, dict[str, str]] = {}
    for s in subjects:
        try:
            v = {
                "blotch": pc.blotch_verdict(s, deliv, cert, margin),
                "rim": pc.rim_verdict(s, rim),
                "sharp": pc.sharp_verdict(s, sharp),
                "dust": pc.dust_verdict(s, dust),
            }
        except Exception as exc:  # noqa: BLE001
            v = {a: "ERROR(%s)" % type(exc).__name__ for a in pc.AXES}
        rows[s] = {a: (v[a][0] if isinstance(v[a], (tuple, list)) else str(v[a])) for a in pc.AXES}
        for a in pc.AXES:
            per_axis[a][rows[s][a]] += 1

    print("%-8s %s" % ("axis", "verdict census"))
    print("-" * 96)
    for a in pc.AXES:
        c = per_axis[a]
        total = sum(c.values())
        assert total == len(subjects), "axis %s: %d verdicts != %d subjects" % (a, total, len(subjects))
        parts = ", ".join("%d %s" % (n, k) for k, n in sorted(c.items(), key=lambda kv: -kv[1]))
        print("%-8s %s   (sums to %d)" % (a, parts, total))
    print()

    print("CLAUSE (c) OBSERVABILITY -- only a currently-PASS subject can move PASS -> FAIL")
    print("-" * 96)
    at_risk = set()
    for a in GRADABLE:
        p = per_axis[a].get("PASS", 0)
        blind = len(subjects) - p
        print("  %-7s  %2d PASS observable, %2d NOT observable (%.0f%% of subjects blind on this axis)"
              % (a, p, blind, 100.0 * blind / len(subjects)))
        for s in subjects:
            if rows[s][a] == "PASS":
                at_risk.add(s)
    print()
    never = [s for s in subjects if s not in at_risk]
    print("  subjects PASSing at least one gradable axis (clause (c) can see them) : %d" % len(at_risk))
    print("  subjects PASSing NO gradable axis (clause (c) is blind to them entirely): %d" % len(never))
    if never:
        for s in never:
            print("      %-28s blotch=%-8s rim=%-8s sharp=%-8s"
                  % (s, rows[s]["blotch"], rows[s]["rim"], rows[s]["sharp"]))
    print()
    assert len(at_risk) + len(never) == len(subjects), "observability partition does not sum"
    print("partition: %d observable + %d blind = %d subjects" % (len(at_risk), len(never), len(subjects)))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out",
                       "75-clause-c-power.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"n_subjects": len(subjects),
                   "per_axis": {a: dict(per_axis[a]) for a in pc.AXES},
                   "observable": sorted(at_risk), "blind": sorted(never),
                   "rows": rows}, fh, indent=2)
    print("wrote %s" % os.path.normpath(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
