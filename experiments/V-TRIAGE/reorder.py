"""Independent re-driving of BUILD-TRIAGE's mutation harness.

Does NOT edit their files.  Imports the harness and calls its mutations in
orders the author did not use, to test whether each mutation is killed by its
OWN gate rather than by whichever gate happened to run first.
"""
import os, sys, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "BUILD-TRIAGE"))
import triage, mutatetest

ORIGINAL_NOISE_PHRASE = triage.noise_phrase
ORIGINAL_FIELD_DEFS = dict(triage.FIELD_DEFS)

def run(fn, label):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn()
    out = buf.getvalue()
    keep = [l for l in out.splitlines()
            if any(k in l for k in ("MUTATION", "FAIL", "mutation:", "mutation 1",
                                    "gate OK", "violations flagged"))]
    print("--- %s -> rc=%d" % (label, rc))
    for l in keep:
        print("    " + l.strip())
    return rc, out

print("=" * 72)
print("TEST 1: definition mutations ALONE (no wording mutation first)")
print("=" * 72)
rc1, out1 = run(mutatetest.mutate_definitions, "mutate_definitions() alone")
assert "UNDEFINED (ships with no definition): noise_flat" in out1, \
    "ANCHOR MISS: undefined mutation not killed by its own message"
assert "ORPHANED (defined but never emitted): snr_margin_db" in out1, \
    "ANCHOR MISS: orphaned mutation not killed by its own message"
assert "noise wording disagrees" not in out1, \
    "CONTAMINATION: a definition mutation was killed by the WORDING gate"
print("    [OK] both killed by the DEFINITION gate; wording gate never fired")

print()
print("=" * 72)
print("TEST 2: restoration of noise_phrase after mutate_wording()")
print("=" * 72)
rc2, out2 = run(mutatetest.mutate_wording, "mutate_wording()")
print("    noise_phrase is original after return : %s"
      % (triage.noise_phrase is ORIGINAL_NOISE_PHRASE))
assert triage.noise_phrase is ORIGINAL_NOISE_PHRASE, "finally did NOT restore"
print("    FIELD_DEFS unchanged after definitions : %s"
      % (dict(triage.FIELD_DEFS) == ORIGINAL_FIELD_DEFS))
assert dict(triage.FIELD_DEFS) == ORIGINAL_FIELD_DEFS, "FIELD_DEFS not restored"
print("    commission_wording restored           : %s"
      % (triage.commission_wording.__name__ != "<lambda>"))

print()
print("=" * 72)
print("TEST 3: REVERSE order -- definitions first, then wording")
print("=" * 72)
rc3, out3 = run(mutatetest.mutate_definitions, "definitions (2nd time)")
rc4, out4 = run(mutatetest.mutate_wording, "wording (after definitions)")
assert "noise wording disagrees" in out4, "wording mutation not killed by wording gate"
print("    [OK] reverse order: each mutation still killed by its own gate")

print()
print("all rc: %d %d %d %d (0 = killed)" % (rc1, rc2, rc3, rc4))
