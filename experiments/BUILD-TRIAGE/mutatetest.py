"""Mutation tests for triage.py's shipping gates.

WHY THIS EXISTS
---------------
`triage.py` carries two gates:

  1. a WORDING gate -- every emitted `why` string is audited against that row's
     own `noise_flat`, so a sentence cannot contradict its own number;
  2. a DEFINITION gate -- every emitted field must have a definition and every
     definition must correspond to an emitted field.

Unit commissioning inside `triage.py` proves the auditors work on planted
strings. It does NOT prove either gate is wired to the real rows: a gate that
computes the right answer and never calls it would pass commissioning and still
ship the defect. That is close to the original failure -- a correct policy in a
comment, eight lines above code that did the other thing.

So each mutation here reintroduces a real defect into the live path and requires
the corresponding gate to stop the run on the actual 26 rows.

WHY EACH MUTATION GETS ITS OWN PROCESS
--------------------------------------
The first version of this file monkeypatched in-process and restored in a
`finally`. That was the minimum, not the pattern, and it failed exactly as
predicted: the wording mutation left `noise_phrase` patched, both later
mutations tripped the WORDING gate instead of their own, and the harness
reported "gate is blind" while both gates were working correctly.

A `finally` protects only the state the author knew to restore. It cannot see
module-level caches, in-place mutation inside `main()`, or a mutation added
later by someone who does not know which names the harness assumed. Indeed even
after that fix `commission_wording` was still being patched by two mutations and
restored by neither -- benign only because the process happened to exit.

A fresh process per mutation removes the whole class: nothing is load-bearing,
nothing needs restoring, and a mutation added later cannot contaminate one that
runs after it.

Note also that contamination is only *visible* when a later mutation must pass a
check an earlier one's residue breaks. A harness whose mutations share no
checkpoint cannot detect its own leakage at any size -- so isolation must be
structural, not inferred from the harness looking clean.

Run:  python experiments/BUILD-TRIAGE/mutatetest.py
"""
from __future__ import annotations
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


# name -> (human description, mutate(triage) -> bool landed, expected token)
def _mutate_wording(triage) -> bool:
    triage.commission_wording = lambda: None
    triage.noise_phrase = triage._legacy_noise_phrase
    return triage.noise_phrase is triage._legacy_noise_phrase


def _mutate_undefined(triage) -> bool:
    return triage.FIELD_DEFS.pop("noise_flat", None) is not None


def _mutate_orphaned(triage) -> bool:
    triage.FIELD_DEFS["snr_margin_db"] = "not emitted anywhere"
    return "snr_margin_db" in triage.FIELD_DEFS


MUTATIONS = {
    "wording": ("noise_phrase -> _legacy_noise_phrase (the form that shipped)",
                _mutate_wording, "noise wording disagrees"),
    "undefined": ("drop a definition for a field that ships",
                  _mutate_undefined, "UNDEFINED"),
    "orphaned": ("define a field that does not ship",
                 _mutate_orphaned, "ORPHANED"),
}


def run_child(name: str) -> int:
    """Apply exactly one mutation in this process and require its gate to fire.

    Fails SAFE by construction.  If the mutation does not land, or lands and
    the run succeeds anyway, this prints MUTATION SURVIVED and returns 1.  A
    harness whose anchors silently stop matching must get louder, not quieter.
    """
    import triage

    desc, mutate, token = MUTATIONS[name]
    print(f"[{name}] mutation: {desc}")

    if not mutate(triage):
        print(f"[{name}] MUTATION DID NOT LAND -- FAIL: the anchor no longer "
              f"matches triage.py; this test is measuring nothing.")
        return 1

    try:
        rc = triage.main()
    except SystemExit as exc:
        msg = str(exc)
        if token not in msg:
            print(f"[{name}] FAIL: run stopped, but not by the expected gate "
                  f"(no {token!r} in the message):\n{msg[:400]}")
            return 1
        hits = re.findall(r"(?m)^ {2}\S[^\n]*: ", msg)
        subj = sorted({h.split(":")[0].strip() for h in hits})
        line = next((l.strip() for l in msg.splitlines() if token in l), "")
        print(f"[{name}] MUTATION KILLED -- gate fired on the real rows.")
        if len(subj) > 1:
            print(f"[{name}]   {len(hits)} violations across {len(subj)} "
                  f"subjects: {', '.join(subj)}")
        else:
            print(f"[{name}]   {line}")
        return 0

    print(f"[{name}] MUTATION SURVIVED (main returned {rc}) -- FAIL: the gate "
          f"is blind; it did not act on the emitted output.")
    return 1


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--mutation":
        return run_child(sys.argv[2])

    print(f"running {len(MUTATIONS)} mutations, each in its own process\n")
    failed = []
    for name in MUTATIONS:
        p = subprocess.run([sys.executable, os.path.abspath(__file__),
                            "--mutation", name],
                           capture_output=True, text=True)
        for line in p.stdout.splitlines():
            if line.startswith(f"[{name}]"):
                print(line)
        if p.returncode != 0:
            failed.append(name)
            if p.stderr.strip():
                print(f"[{name}] stderr: {p.stderr.strip()[:400]}")
        print()

    if failed:
        print(f"FAIL: {len(failed)} of {len(MUTATIONS)} mutations survived or "
              f"errored: {', '.join(failed)}")
        return 1
    print(f"OK: all {len(MUTATIONS)} mutations killed by their own gate, each "
          f"in an isolated process -- no restoration is load-bearing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
