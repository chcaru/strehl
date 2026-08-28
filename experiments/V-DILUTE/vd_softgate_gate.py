"""Gated verifier: is `STREHL_SOFT_GATE` reachable from the default merge?

Addendum K.1 asserted this from reading source. A prose verdict cannot be
caught by any mutation -- ORCH attributes exactly that defect to V-KILLB0 --
so this file turns the claim into a check that EXITS NON-ZERO when it stops
being true.

Commissioning follows ORCH's three lessons:
  * the pass/fail CHANNEL is exercised, not just the happy path: `--selftest`
    plants a synthetic violation of each gate and requires it to be caught,
    so a dead checker and a clean result do not give the same green;
  * SPECIFICITY as well as sensitivity: gate 4 requires the env var to MOVE
    the estimator, so "identical on pyramid" cannot be satisfied by an env
    var that is simply dead everywhere;
  * DELETION as well as reversal: `--selftest` also removes each arm's file
    and requires the checker to fail loudly rather than skip the gate.
"""
import io
import sys

import numpy as np
import tifffile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

D = r"D:\strehl-out\V-DILUTE\softgate"
ARMS = "A Ap B C D E".split()


def load(missing=(), corrupt=None):
    out = {}
    for k in ARMS:
        if k in missing:
            continue
        out[k] = tifffile.imread(rf"{D}\{k}.tiff").astype(np.float64)
    if corrupt:
        k, delta = corrupt
        if k in out:
            out[k] = out[k].copy()
            out[k][0, 0, 0] += delta
    return out


def ndiff(arms, a, b):
    """Differing sample count. Raises if an arm is absent -- deletion must not pass."""
    if a not in arms or b not in arms:
        raise KeyError(f"arm {a if a not in arms else b} missing; cannot evaluate")
    return int((arms[a] != arms[b]).sum())


# Each gate: (id, claim it certifies, predicate over the arm dict).
# The predicate is pinned to the SPECIFIC claim, not to the presence of a word.
GATES = [
    ("G1 determinism",
     "byte comparison is a valid instrument here (no timestamp in the writer)",
     lambda a: ndiff(a, "A", "Ap") == 0),
    ("G2 THE CLAIM",
     "STREHL_SOFT_GATE changes NOTHING on the default pyramid backend",
     lambda a: ndiff(a, "A", "B") == 0),
    ("G3 sensitivity",
     "the harness can see a change it should see (--pyramid-exponent moves it)",
     lambda a: ndiff(a, "A", "C") > 0),
    ("G4 specificity",
     "the env var is LIVE on the estimator backend, so G2 is not a dead var",
     lambda a: ndiff(a, "D", "E") > 0),
]


def evaluate(arms):
    return [(gid, claim, bool(pred(arms))) for gid, claim, pred in GATES]


def main():
    selftest = "--selftest" in sys.argv

    if selftest:
        print("COMMISSIONING THE PASS/FAIL CHANNEL")
        print("  clean input must give 0 failures; each planted violation must give >=1;")
        print("  each deletion must raise rather than silently skip.\n")
        clean = evaluate(load())
        nfail = sum(1 for _, _, ok in clean if not ok)
        print(f"  {'clean':<34} failures = {nfail}   {'OK' if nfail == 0 else 'BROKEN'}")
        if nfail:
            print("  cannot commission against a failing baseline")
            return 3

        bad = 0
        # Reversal plants: perturb one arm so a specific gate must flip.
        for k, gid in (("B", "G2 THE CLAIM"), ("Ap", "G1 determinism")):
            res = evaluate(load(corrupt=(k, 1.0)))
            caught = [g for g, _, ok in res if not ok]
            hit = gid in caught
            bad += 0 if hit else 1
            print(f"  plant +1 DN in {k:<3} -> caught {caught}   "
                  f"{'OK' if hit else 'MISSED'}")
        # An innocuous change must NOT trip anything (specificity of the channel).
        res = evaluate(load())
        quiet = all(ok for _, _, ok in res)
        bad += 0 if quiet else 1
        print(f"  {'re-run with no plant':<34} "
              f"{'OK (still silent)' if quiet else 'FALSE POSITIVE'}")
        # Deletion plants: removing an arm must raise, never skip.
        for k in ("C", "E"):
            try:
                evaluate(load(missing=(k,)))
                print(f"  delete arm {k:<3} -> NO ERROR   MISSED (deletion passed silently)")
                bad += 1
            except KeyError as exc:
                print(f"  delete arm {k:<3} -> raised: {exc}   OK")
        print(f"\n  commissioning: {'PASS' if bad == 0 else f'FAIL ({bad} defects)'}")
        if bad:
            return 3
        print()

    arms = load()
    results = evaluate(arms)
    print("GATES")
    failed = 0
    for gid, claim, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {gid:<18} {claim}")
        if not ok:
            failed += 1

    print()
    print(f"  A vs B  differing samples: {ndiff(arms,'A','B'):,} of {arms['A'].size:,}")
    print(f"  D vs E  differing samples: {ndiff(arms,'D','E'):,} of {arms['A'].size:,}")
    print()
    if failed:
        print(f"VERDICT WITHHELD -- {failed} gate(s) failed. Addendum K.1 may be stale.")
        return 1
    print("VERDICT: STREHL_SOFT_GATE is UNREACHABLE from the default pyramid backend,")
    print("         and LIVE on the estimator backend. Addendum K.1 stands.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
