"""Mutation test for triage.py's noise-wording shipping gate.

WHY THIS EXISTS
---------------
`triage.py` gained two defences after the inverted-noise defect shipped:

  1. `commission_wording()` -- plants the defect in isolation and requires the
     auditor to catch it.
  2. a corpus-wide gate in `main()` -- audits every emitted `why` string
     against that row's own `noise_flat` before `triage.json` is written.

Defence (1) proves the auditor works on a planted string. It does NOT prove the
gate is wired to the real rows: a gate that computes the right answer and then
never calls it would pass (1) and still ship the defect. That is close to the
original failure -- a correct policy stated in a comment, eight lines above code
that did the other thing.

So this reintroduces the exact shipped defect (`_legacy_noise_phrase`) into the
live render path and requires the corpus gate to stop the run on real data.

A mutation that survives is a blind gate, and is reported as a failure.

Run:  python experiments/BUILD-TRIAGE/mutatetest.py
"""
from __future__ import annotations
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402


def mutate_wording() -> int:
    """Reintroduce the shipped noise-wording defect; the gate must stop it."""
    triage.commission_wording = lambda: None
    good_phrase = triage.noise_phrase
    triage.noise_phrase = triage._legacy_noise_phrase

    print("mutation 1: noise_phrase -> _legacy_noise_phrase (the shipped form)")
    print("expecting: corpus gate refuses to write triage.json\n")

    try:
        rc = triage.main()
    except SystemExit as exc:
        msg = str(exc)
        if "noise wording disagrees" not in msg:
            print(f"FAIL: run stopped, but not by the wording gate:\n{msg}")
            return 1
        n = len(re.findall(r"(?m)^ {2}\S[^\n]*: ", msg))
        subj = sorted({m.split(":")[0].strip()
                       for m in re.findall(r"(?m)^ {2}\S[^\n]*: ", msg)})
        head = "\n".join(msg.splitlines()[:7])
        print("MUTATION KILLED -- the wording gate fired on real rows.")
        print(f"violations flagged: {n} across {len(subj)} subjects: "
              f"{', '.join(subj)}")
        print(head)
        return 0
    finally:
        # Each mutation must be independent.  Leaving this patched made the
        # later definition mutations trip the WORDING gate instead, and the
        # test reported "gate is blind" when both gates were working.
        triage.noise_phrase = good_phrase

    print(f"MUTATION SURVIVED (main returned {rc}).")
    print("FAIL: the wording gate is blind -- it did not audit the strings.")
    return 1


def mutate_definitions() -> int:
    """Break FIELD_DEFS both ways; the definition gate must catch each.

    Both directions matter.  An undefined field is unreadable.  An orphaned
    definition is worse: it describes something the reader cannot find, and the
    reader will map it onto the nearest surviving name -- which is exactly the
    `noise_flat` / `noise_ratio_all_sites_diag` confusion that shipped.
    """
    triage.commission_wording = lambda: None
    ok = True

    for label, mutate, expect in (
            ("undefined field  (drop a definition that ships)",
             lambda d: d.pop("noise_flat", None), "UNDEFINED"),
            ("orphaned definition  (define a field that does not ship)",
             lambda d: d.update({"snr_margin_db": "not emitted anywhere"}),
             "ORPHANED")):
        good = dict(triage.FIELD_DEFS)
        broken = dict(good)
        mutate(broken)
        triage.FIELD_DEFS = broken
        print(f"\nmutation: {label}")
        try:
            triage.main()
            print(f"  MUTATION SURVIVED -- FAIL: gate missed {expect}.")
            ok = False
        except SystemExit as exc:
            msg = str(exc)
            if expect in msg:
                line = next(l.strip() for l in msg.splitlines() if expect in l)
                print(f"  MUTATION KILLED -- {line}")
            else:
                print(f"  FAIL: stopped, but not by the definition gate: {msg}")
                ok = False
        finally:
            triage.FIELD_DEFS = good

    return 0 if ok else 1


def main() -> int:
    rc = mutate_wording()
    rc |= mutate_definitions()
    print("\nOK: neither shipped defect can pass its gate." if not rc
          else "\nFAIL: at least one gate is blind.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
