"""Negative control for the section 12-14 report verifiers.

ORCH's broadcast: V-NEVERWORSE's verifier tested for the PRESENCE of the string
"refuted" in a section; flipping that section's verdict to "confirmed" while
leaving every number intact passed 712 green checks. He asked every lane to
check its own verifiers for that shape. This is that check, run as an experiment
rather than answered from memory.

The design point, which is the whole reason this file exists: a suite that plants
only NUMBER perturbations cannot distinguish a verifier that certifies a
document's claims from one that merely certifies its arithmetic. So the arms
below are deliberately of two kinds --

  ARITHMETIC arms (T1-T3) perturb, transpose or relocate a VALUE. A verifier
  pinned to the JSON must catch all of these, and if it does not, its numeric
  coverage has a hole.

  CONCLUSION arms (C1-C2) change no digit anywhere. They reverse what the
  document CLAIMS -- a recommendation and a disclosure of a hole. A purely
  numeric verifier is structurally incapable of catching these, and reporting
  GREEN on them is not a bug in the implementation, it is the boundary of what
  the instrument measures. The point of running them is to find out where that
  boundary sits and then to state it, or move it.

  DELETION arms (D1-D2) remove a finding rather than misstating it. ORCH, after
  six lanes had each found this class in their own harness: "Commission DELETION
  as well as reversal. Deleting a finding is cheaper than stating it wrongly."
  A verifier built from positive checks -- assert this cell equals that value --
  can be fully satisfied by a document with the row removed, because the check
  that would have failed is the one that no longer runs. D1 deletes a disclosed
  hole; D2 deletes a whole measured row.

  PROSE arm (P1) is the SPECIFICITY control and it is the only arm that must
  come back GREEN. ORCH: "Commissioning sensitivity is not commissioning
  specificity. Planting a signal and confirming detection says nothing about
  whether noise is rejected. Plant noise too." A verifier that goes RED on any
  edit at all would catch every arm above while certifying nothing, and it would
  be indistinguishable from a sound one on a sensitivity-only suite. P1 changes
  "needs" to "requires" in a narrative sentence: no claim moves, no digit moves,
  and the suite must not fire.

  The NULL arm and P1 together answer the other half of ORCH's warning, that
  "an inert plant and a dead instrument give the identical green": NULL shows
  the suite is not permanently RED, P1 shows it is not RED-on-contact, and the
  five planted arms show it is not permanently GREEN.

Every mutation is anchored on a UNIQUE FULL-LINE string and hard-errors if it
does not land. A mutation that silently fails to apply produces a GREEN that
looks exactly like a verifier correctly passing a clean document, which would
invert this file's conclusion. (Learned the hard way: a control anchored on a
bare substring hit an earlier line than intended and read GREEN.)

The document is restored from a copy taken in TEMP, never with `git checkout`,
because this tree is shared with nine other lanes and a checkout would discard
their uncommitted work along with the mutation.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "research" / "BUILD-OUTPUT.md"
VERIFIERS = ["verify_s12.py", "verify_s13.py", "verify_s14.py"]
HERE = Path(__file__).resolve().parent

# (id, kind, old, new, expectation, why)
# `expectation` is what a verifier suite that certifies CLAIMS should do.
ARMS = [
    ("T1", "arithmetic",
     "| `119MSDCF` | 0.9623 | 0.7821 | 3.8 | 21.8 | 5.79 |",
     "| `119MSDCF` | 0.9624 | 0.7821 | 3.8 | 21.8 | 5.79 |",
     "RED", "last-digit perturbation of one table cell"),
    ("T2", "arithmetic",
     "| `109MSDCF` | 0.9677 | 0.7829 | 3.2 | 21.7 | **6.71** worst |",
     "| `109MSDCF` | 0.7829 | 0.9677 | 3.2 | 21.7 | **6.71** worst |",
     "RED", "transposition: two cells swapped, both values still present in row"),
    ("T3", "arithmetic",
     "| `foam` | 0.7662 | 0.8887 | 23.4 | 11.1 | 0.48 |",
     "| `foam` | 0.8887 | 0.7662 | 23.4 | 11.1 | 0.48 |",
     "RED", "transposition on the row whose old anchor contained its own value"),
    ("C1", "conclusion",
     "## 12.9 Recommendation: do not move the default constant tonight",
     "## 12.9 Recommendation: move the default constant tonight",
     "RED", "the section's RECOMMENDATION is reversed; no digit changes"),
    ("C2", "conclusion",
     "## 12.8 The hull axis is NOT MEASURED, and that is a hole in this recommendation",
     "## 12.8 The hull axis is MEASURED, and that is not a hole in this recommendation",
     "RED", "a disclosed hole is un-disclosed; no digit changes"),
    ("D1", "deletion",
     "## 12.8 The hull axis is NOT MEASURED, and that is a hole in this recommendation",
     "",
     "RED", "the disclosed hole is DELETED outright rather than reversed"),
    ("D2", "deletion",
     "| `foam` | 0.7662 | 0.8887 | 23.4 | 11.1 | 0.48 |",
     "",
     "RED", "an entire measured row is deleted; nothing left says it is missing"),
    ("P1", "prose",
     "BUILD-HULL's instrument needs a per-frame basis to compare the merge against.",
     "BUILD-HULL's instrument requires a per-frame basis to compare the merge against.",
     "GREEN", "specificity: innocuous wording change, no claim and no digit moves"),
]


def run_suite():
    """Return (verdict, per-verifier detail). RED if ANY verifier exits non-zero."""
    detail = []
    worst = "GREEN"
    for v in VERIFIERS:
        p = subprocess.run([sys.executable, str(HERE / v)],
                           capture_output=True, text=True)
        tail = (p.stdout.strip().splitlines() or ["<no output>"])[-1]
        detail.append(f"{v} rc={p.returncode} {tail.strip()}")
        if p.returncode != 0:
            worst = "RED"
    return worst, detail


def main():
    backup = Path(tempfile.gettempdir()) / "BUILD-OUTPUT.md.negctl"
    shutil.copy2(DOC, backup)
    print(f"backup: {backup}")

    results = []
    try:
        base, detail = run_suite()
        print(f"\n[NULL] unmutated document -> {base}")
        for d in detail:
            print(f"        {d}")
        if base != "GREEN":
            print("\nABORT: the suite is not GREEN before any mutation, so no "
                  "RED below could be attributed to a planted defect.")
            return 2
        results.append(("NULL", "control", "GREEN", base, True, "unmutated"))

        original = DOC.read_text(encoding="utf-8")
        for aid, kind, old, new, expect, why in ARMS:
            n = original.count(old)
            if n != 1:
                print(f"\nABORT: mutation {aid} target occurs {n}x, need exactly 1.")
                print("A mutation that does not land reads GREEN exactly like a "
                      "clean pass, which would invert this file's conclusion.")
                return 2
            DOC.write_text(original.replace(old, new, 1), encoding="utf-8")
            got, detail = run_suite()
            results.append((aid, kind, expect, got, got == expect, why))
            print(f"\n[{aid}] {kind}: {why}")
            print(f"        expected {expect}, got {got}")
            for d in detail:
                print(f"        {d}")
            DOC.write_text(original, encoding="utf-8")
    finally:
        shutil.copy2(backup, DOC)
        print(f"\nrestored {DOC.name} from {backup}")

    print("\n" + "=" * 78)
    w = max(len(r[5]) for r in results)
    for aid, kind, expect, got, ok, why in results:
        print(f"  {aid:<5}{kind:<11}{why:<{w}}  want {expect:<5} got {got:<5} "
              f"{'ok' if ok else 'MISSED'}")

    arith = [r for r in results if r[1] == "arithmetic"]
    concl = [r for r in results if r[1] == "conclusion"]
    dele = [r for r in results if r[1] == "deletion"]
    prose = [r for r in results if r[1] == "prose"]
    a_ok = sum(1 for r in arith if r[4])
    c_ok = sum(1 for r in concl if r[4])
    d_ok = sum(1 for r in dele if r[4])
    p_ok = sum(1 for r in prose if r[4])
    print(f"\n  arithmetic defects caught : {a_ok}/{len(arith)}")
    print(f"  conclusion flips caught   : {c_ok}/{len(concl)}")
    print(f"  deletions caught          : {d_ok}/{len(dele)}")
    print(f"  specificity (must NOT fire): {p_ok}/{len(prose)}")

    # Every count is conditioned on. Partitioning them is the point: an
    # aggregate "7 of 8 caught" would let a total blindness to one whole class
    # hide behind strong coverage of another.
    if p_ok != len(prose):
        print("\n  VERDICT: RED -- the suite fires on an innocuous wording "
              "change, so its REDs above certify nothing. A verifier that "
              "cannot stay quiet cannot speak.")
        return 4
    if a_ok != len(arith):
        print("\n  VERDICT: RED -- the numeric coverage has a hole.")
        return 1
    if d_ok != len(dele):
        print("\n  VERDICT: RED -- a finding can be DELETED without the suite "
              "noticing. Positive checks do not run on rows that are gone.")
        return 5
    if c_ok != len(concl):
        print("\n  VERDICT: the verifiers certify ARITHMETIC but not CLAIMS. A "
              "reversed recommendation passes every check. This is the exact "
              "shape ORCH reported in V-NEVERWORSE's verifier.")
        return 3
    print("\n  VERDICT: GREEN -- arithmetic, conclusions and deletions are "
          "pinned, and the suite stays quiet on innocuous prose.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
