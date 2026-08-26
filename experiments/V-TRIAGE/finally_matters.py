"""Prove the `finally` in mutate_wording() is load-bearing.

Simulates the PRE-FIX state: leave noise_phrase monkeypatched (exactly what a
missing `finally` would do) and then run the definition mutations.  If the
author's account is right, both definition mutations get killed by the WORDING
gate and the harness reports the wrong diagnosis.
"""
import os, sys, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "BUILD-TRIAGE"))
import triage, mutatetest

# ANCHOR CHECK: the real `finally` line must exist in their source, else this
# whole probe is testing something that is not there.
src = open(os.path.join(HERE, "..", "BUILD-TRIAGE", "mutatetest.py"),
           encoding="utf-8").read()
ANCHOR = "        triage.noise_phrase = good_phrase"
if ANCHOR not in src:
    raise SystemExit("ANCHOR MISS: restoration line not found in mutatetest.py")
print("anchor found in mutatetest.py: %r" % ANCHOR.strip())
print("occurrences: %d (must be 1 for the anchor to be unique)"
      % src.count(ANCHOR))

# Recreate the pre-fix leak by hand.
triage.noise_phrase = triage._legacy_noise_phrase
print("\nsimulating the leak: noise_phrase left patched to _legacy_noise_phrase")

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = mutatetest.mutate_definitions()
out = buf.getvalue()
print("mutate_definitions() rc = %d  (0 would mean 'all green')" % rc)
for l in out.splitlines():
    if any(k in l for k in ("MUTATION", "FAIL", "mutation:")):
        print("    " + l.strip()[:150])

wrong_gate = "not by the definition gate" in out
print("\nkilled by the WRONG gate: %s" % wrong_gate)
print("-> the `finally` IS load-bearing: %s" % wrong_gate)
