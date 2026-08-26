import os, sys, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "BUILD-TRIAGE"))
import mutatetest
J = r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json"
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = mutatetest.mutate_definitions()
print("mutate_definitions rc = %d (0 = both killed)" % rc)
for l in buf.getvalue().splitlines():
    if "MUTATION" in l or "FAIL" in l:
        print("   " + l.strip()[:120])
print("triage.json recreated while gate was firing: %s" % os.path.exists(J))
