"""MUTATION TEST of my own commissioning harness (ORCH correction #5 postscript).

V-LINEAR found four conclusion-flip arms all MISSED at 88/88 green. The weak
check is to grep for presence-tests; the strong check is to actually mutate the
instrument so a CONCLUSION reverses while the machinery still runs and the
numbers stay plausible, then ask whether the harness fails.

Each arm below flips what sigref would CONCLUDE. None of them perturbs a
threshold or breaks an import. Arm SELFPAIR is the one that matters most: it is
the mutation that would have made bee-1-cpl's flat-site signal fraction read
1.000 instead of 0.001 -- i.e. it would have reversed the verdict I delivered.

CAUGHT = commission() returns non-zero (at least one planted arm fails).
MISSED = commission() returns 0, i.e. my harness certifies a broken instrument.

Writes nothing. Mutates nothing on disk -- sigref.py is monkey-patched in
memory and restored between arms.
"""
import io, os, sys, contextlib
import numpy as np
import sigref as SR
import splithalf as sh

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"
PE = os.path.join(OUT, "119MSDCF__EVEN__A-unset.tiff")
PO = os.path.join(OUT, "119MSDCF__ODD__A-unset.tiff")
ORIG_DECOMP, ORIG_RATIO = SR.decomp, SR.ratio


def base(ge, go, sel, y0, x0, ty, tx):
    X = sh.tiles_of(sh.band0(ge), y0, x0, ty, tx)[sel]
    Y = sh.tiles_of(sh.band0(go), y0, x0, ty, tx)[sel]
    return X, Y


def m_swap(ge, go, sel, y0, x0, ty, tx):
    """SIGNAL and NOISE exchanged: a blur now reads as a denoise."""
    s, n = ORIG_DECOMP(ge, go, sel, y0, x0, ty, tx)
    return n, s


def m_selfpair(ge, go, sel, y0, x0, ty, tx):
    """Both halves taken from EVEN: cov==var, so noise==0 and EVERYTHING
    reads as pure reproducible signal. Flat-site sf would read 1.000."""
    return ORIG_DECOMP(ge, ge, sel, y0, x0, ty, tx)


def m_nodemean(ge, go, sel, y0, x0, ty, tx):
    """Tile-mean not removed: DC dominates covariance, all reads as signal."""
    X, Y = base(ge, go, sel, y0, x0, ty, tx)
    cov = (X * Y).mean(1)
    var = 0.5 * ((X * X).mean(1) + (Y * Y).mean(1))
    return cov, var - cov


def m_abscov(ge, go, sel, y0, x0, ty, tx):
    """|cov|: a statistic bounded below by zero -- the exact failure ORCH
    warned about in the opening brief."""
    s, n = ORIG_DECOMP(ge, go, sel, y0, x0, ty, tx)
    return np.abs(s), n


def m_deadratio(num, den, seed=7, nboot=4000):
    """Instrument reports 'no change' for every arm."""
    return 1.0, 1.0, 1.0


ARMS = [("NULL (unmutated control)", None, None),
        ("SWAP signal<->noise", m_swap, None),
        ("SELFPAIR (EVEN vs EVEN)", m_selfpair, None),
        ("NODEMEAN (DC left in)", m_nodemean, None),
        ("ABSCOV (bounded below by 0)", m_abscov, None),
        ("DEADRATIO (inert instrument)", None, m_deadratio)]

print("MUTATION TEST of sigref.commission(), subject 119MSDCF")
print("expect: NULL passes (0/CAUGHT=no), every mutation CAUGHT\n")
rows = []
for name, dm, rm in ARMS:
    SR.decomp = dm if dm else ORIG_DECOMP
    SR.ratio = rm if rm else ORIG_RATIO
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = SR.commission(PE, PO, 25.0)
    except Exception as e:
        rc = "EXC:%s" % type(e).__name__
    SR.decomp, SR.ratio = ORIG_DECOMP, ORIG_RATIO
    txt = buf.getvalue()
    line = [l for l in txt.split("\n") if "COMMISSIONED" in l]
    got = line[0].strip() if line else "(no verdict line)"
    if name.startswith("NULL"):
        ok = (rc == 0)
        verdict = "PASS as expected" if ok else "*** NULL FAILED ***"
    else:
        ok = (rc != 0)
        verdict = "CAUGHT" if ok else "*** MISSED ***"
    rows.append(ok)
    print("  %-30s rc=%-6s %-22s %s" % (name, rc, got, verdict))

print("\n%d/%d arms behaved correctly" % (sum(rows), len(rows)))
print("VERDICT: %s" % ("harness detects conclusion-flips"
                       if all(rows) else "HARNESS DEFECTIVE -- at least one flip MISSED"))
