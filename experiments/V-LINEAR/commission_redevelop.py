"""Positive control for sec.13.9's re-develop acceptance check.

The doc commissioning harness mutates the DOCUMENT, so it cannot reach a check
that compares two JSON records to each other.  An uncommissioned check is a
green light of unknown meaning, so it is exercised here instead.

Two arms:
  NULL      -- the real pair.  max |dR| must be exactly 0.
  POSITIVE  -- bee's canonical record against a DIFFERENT subject's record.
               The check must report a non-zero max |dR|, i.e. it must be
               capable of failing at all.

The positive arm matters more than the null.  A check hard-wired to return 0
would pass the null perfectly while being blind to everything.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def rec(fname, key):
    with open(os.path.join(HERE, fname)) as fh:
        for r in json.load(fh):
            if r["key"] == key:
                return r
    raise SystemExit(f"no record {key!r} in {fname}")


def max_dr(a, b):
    """The check as verify_bands_doc.py computes it."""
    return max(abs(v["R"] - b["bands"][band]["R"])
               for band, v in a["bands"].items() if band in b["bands"])


def main():
    canon = rec("bandsweep-far20.json", "bee-1-cpl")
    remade = rec("bandsweep-far20-bee-1-cpl.json", "bee-1-cpl")
    other = rec("bandsweep-far20.json", "leaf-2-cpl")

    rows = []

    d = max_dr(canon, remade)
    rows.append(("NULL      bee canonical vs bee re-developed", d, d == 0.0,
                 "expect exactly 0"))

    d = max_dr(canon, other)
    rows.append(("POSITIVE  bee canonical vs leaf-2-cpl", d, d > 0.0,
                 "expect > 0 -- proves the check can fail"))

    # A third arm: perturb ONE band by one ulp-ish amount.  A check written
    # with a tolerance instead of exact equality would pass this and should
    # not.
    import copy
    nudged = copy.deepcopy(remade)
    band = "0.30-0.40"
    nudged["bands"][band]["R"] += 1e-12
    d = max_dr(canon, nudged)
    rows.append((f"POSITIVE  one band nudged by 1e-12 ({band})", d, d > 0.0,
                 "expect > 0 -- exact equality, not a tolerance"))

    print(f"  {'arm':52s} {'max |dR|':>14s}  {'':4s} note")
    bad = 0
    for name, d, good, note in rows:
        if not good:
            bad += 1
        print(f"  {name:52s} {d:14.6g}  {'ok' if good else 'FAIL':4s} {note}")

    print()
    print(f"  {len(rows) - bad}/{len(rows)} arms as expected")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
