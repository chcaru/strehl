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


def main() -> int:
    # Isolate the corpus gate: silence the unit-level commissioning so that a
    # failure here can only have come from the gate running on real rows.
    triage.commission_wording = lambda: None

    # Reintroduce the defect exactly as it shipped.
    triage.noise_phrase = triage._legacy_noise_phrase

    print("mutation: noise_phrase -> _legacy_noise_phrase (the shipped form)")
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
        print("MUTATION KILLED -- the gate fired on real rows.")
        print(f"violations flagged: {n} across {len(subj)} subjects: "
              f"{', '.join(subj)}")
        print(head)
        print("\nOK: the shipped defect cannot pass the gate.")
        return 0

    print(f"MUTATION SURVIVED (main returned {rc}).")
    print("FAIL: the gate is blind -- it did not audit the emitted strings.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
