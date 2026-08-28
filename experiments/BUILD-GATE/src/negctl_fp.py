"""Negative control for floor_predict.decoy()'s new RELATIVE gate.

The gate must PASS on the real data and FAIL when band 0 fits no better
than the decoy. A gate that cannot fail is not a gate.
"""
import sys, io, contextlib
sys.path.insert(0, ".")
import floor_predict as fp

def run(rows):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fp.decoy(rows)
    return rc, buf.getvalue()

# real rows, rebuilt exactly as main() does
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    fp.main()
real = fp.LAST_ROWS
rc, out = run(real)
print("ARM 1 real data                 rc=%d  %s" % (rc, "PASS" if rc == 0 else "FAIL"))
assert rc == 0, "real data must pass"

# planted: band 0 fits as badly as the decoy (err 0.25 on every subject)
bad = [(s, xw, kp, ko, 0.25) for (s, xw, kp, ko, _) in real]
rc, out = run(bad)
print("ARM 2 b0 err planted to 25%%     rc=%d  %s" % (rc, "PASS" if rc == 0 else "FAIL"))
assert rc == 1, "gate must FAIL when b0 is no better than the decoy"
assert "DECOY FITS AS WELL AS BAND 0" in out, out[-400:]

# planted: b0 err just over half the decoy's worst -> still must fail
half = [(s, xw, kp, ko, 0.226 / 2 + 1e-4) for (s, xw, kp, ko, _) in real]
rc, out = run(half)
print("ARM 3 b0 err at decoy/2 (margin) rc=%d  %s" % (rc, "PASS" if rc == 0 else "FAIL"))
assert rc == 1, "2x margin boundary must FAIL"

print("\nCOMMISSIONED: gate passes real data and fails both planted arms.")
