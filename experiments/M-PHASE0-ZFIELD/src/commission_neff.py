"""Commission the n_eff truncation guard in zflib.n_eff.

The guard exists because of a real defect: noise_autocorr ran to lag 24 while the
widest window in the census is 33, and n_eff silently substituted 0 for every
unmeasured lag. Substituting 0 for a positive tail correlation understates
S = sum (w - |d|) rho(|d|), which overstates n_eff and the pooling gain -- the
direction that flatters A5. It read 2.46 at w = 33 against a true 2.19.

A guard that has never fired may be a no-op, so this plants the exact defect it
targets (rho truncated at lag 24, the historical value), and separately checks
that it stays silent on a rho of exactly sufficient length and fires on the
off-by-one below it. Run from projects/strehl after z1_census.py.
"""
import sys, json, math
sys.path.insert(0, "experiments/M-PHASE0-ZFIELD/src")
from zflib import n_eff

nc = json.load(open("experiments/M-PHASE0-ZFIELD/out/z1-census.json", encoding="utf-8"))
nc = nc["stacks"]["113MSDCF"]["1"]["noise_corr"]
rx, ry = nc["rho_x"], nc["rho_y"]
print("stored rho length:", len(rx))

ok = n_eff(rx, ry, 33)
print("PASS full rho     w=33 n_eff %.4f gain %.4f" % (ok, math.sqrt(ok)))

# the exact defect the guard targets: rho truncated at lag 24
try:
    bad = n_eff(rx[:25], ry[:25], 33)
    print("FAIL guard did not fire; returned", bad)
    sys.exit(1)
except ValueError as e:
    print("GUARD FIRED:", e)

# and it must NOT fire where the data is long enough
for w in (3, 5, 9, 17, 33):
    print("  w=%2d gain %.4f" % (w, math.sqrt(n_eff(rx, ry, w))))

# null control: the guard must be silent on an exactly-sufficient rho
print("exact-length rho w=33:", "%.4f" % n_eff(rx[:33], ry[:33], 33))
try:
    n_eff(rx[:32], ry[:32], 33)
    print("FAIL off-by-one boundary not caught"); sys.exit(1)
except ValueError:
    print("boundary lag 31 correctly rejected for w=33")
print("ALL GUARD CHECKS PASS")
