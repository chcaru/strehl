"""M113-ca C13 -- audit the ring bootstrap that produced the +/- column in c10.

ORCH is quoting c10's 80.0 ppm as the authoritative bootstrap sd at the r=0.11
ring, in a retraction of a tighter figure. Before that number is relied on, two
things need testing, and only one of them is the one I went looking for.

DEFECT UNDER TEST (found by reading, not by suspicion). c10_rings.py:58-61 is

    bs = [median( d_r[idx[rng.integers(...)]] / rad[idx[rng.integers(...)]] ) ...]

TWO separate rng.integers draws. The numerator and the denominator are resampled
with DIFFERENT indices, so every replicate divides window i's radial
displacement by window j's radius. The pairing between a displacement and the
radius it occurred at is destroyed. The POINT estimate at c10:55 is correctly
paired -- only the +/- column is affected.

ORCH's CONCERN, which is a different one. Quantisation error is deterministic in
pixel value and therefore correlated between samples that share values. A naive
bootstrap assumes the resampled units are independent. If windows are spatially
correlated, a naive bootstrap UNDERSTATES the sd. So the two effects push in
OPPOSITE directions and the net is not predictable by argument. Measure it.

THREE ESTIMATORS, same data, same rings:
  broken : shipped two-draw version (reproduces c10 exactly -- this is the check
           that I am auditing the code that actually ran)
  paired : one index draw applied to both arrays. The textbook bootstrap.
  block  : resample contiguous SPATIAL BLOCKS of windows with replacement, which
           respects correlation between neighbouring windows. This is the one
           that answers ORCH.

COMMISSIONING FIRST. A bootstrap audit that cannot detect a known pairing loss
is not evidence. Part 0 plants both conditions on synthetic data where the right
answer is known analytically, and requires the three estimators to separate.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c4_globalfit as c4g                                    # noqa: E402
from c4_globalfit import cs, measure, fit_eps                  # noqa: E402

LIN = r"C:\dev\strehl-out\M113-ca\lin"
OUT = r"C:\dev\strehl-out\M113-ca"
EDGES = [0.0, 0.15, 0.30, 0.45, 0.60, 0.72, 0.85, 1.00]
NBOOT = 400
BLOCK = 400.0          # px, spatial block side for the block bootstrap


def boot_broken(num, den, seed=7, nboot=NBOOT):
    rng = np.random.default_rng(seed)
    n = len(num)
    return np.std([np.median(num[rng.integers(0, n, n)] / den[rng.integers(0, n, n)])
                   for _ in range(nboot)])


def boot_paired(num, den, seed=7, nboot=NBOOT):
    rng = np.random.default_rng(seed)
    n = len(num)
    return np.std([np.median((lambda i: num[i] / den[i])(rng.integers(0, n, n)))
                   for _ in range(nboot)])


def boot_block(num, den, bx, by, seed=7, nboot=NBOOT):
    """Resample whole spatial blocks with replacement, preserving pairing."""
    rng = np.random.default_rng(seed)
    keys = (bx.astype(np.int64) << 20) + by.astype(np.int64)
    uniq, inv = np.unique(keys, return_inverse=True)
    members = [np.flatnonzero(inv == k) for k in range(len(uniq))]
    nb = len(uniq)
    out = []
    for _ in range(nboot):
        pick = rng.integers(0, nb, nb)
        idx = np.concatenate([members[p] for p in pick])
        out.append(np.median(num[idx] / den[idx]))
    return np.std(out), nb


def commission():
    print("=" * 96)
    print("PART 0 -- COMMISSIONING. Can these three estimators tell the two conditions apart?")
    print("=" * 96)
    rng = np.random.default_rng(0)
    n = 400
    # independent windows: radius spread over a realistic ring, ratio ~ constant
    rad = rng.uniform(300.0, 500.0, n)
    truth = 500e-6
    num_ind = truth * rad + rng.normal(0, 0.02, n)
    bx = np.arange(n) // 1          # every window its own block -> block == paired
    by = np.zeros(n)
    sb = boot_broken(num_ind, rad, nboot=600)
    sp = boot_paired(num_ind, rad, nboot=600)
    sk, nbk = boot_block(num_ind, rad, bx, by, nboot=600)
    print("\nC0a INDEPENDENT windows (truth 500.0 ppm, ratio nearly constant):")
    print("    broken %8.1f ppm   paired %8.1f ppm   block %8.1f ppm (%d blocks)"
          % (sb * 1e6, sp * 1e6, sk * 1e6, nbk))
    infl = sb / sp
    print("    broken/paired inflation = %.2fx" % infl)
    ok_a = infl > 3.0
    print("    EXPECT broken >> paired, because breaking the pairing turns a nearly"
          "\n    constant ratio into a ratio of unrelated radii.  %s"
          % ("PASS" if ok_a else "FAIL -- audit cannot see the defect"))
    # correlated windows: 20 blocks whose members share an offset
    nb2 = 20; per = 20
    off = rng.normal(0, 0.05, nb2)
    rad2 = rng.uniform(300.0, 500.0, nb2 * per)
    num2 = truth * rad2 + np.repeat(off, per) * rad2 + rng.normal(0, 0.005, nb2 * per)
    bx2 = np.repeat(np.arange(nb2), per); by2 = np.zeros(nb2 * per)
    sp2 = boot_paired(num2, rad2, nboot=600)
    sk2, nbk2 = boot_block(num2, rad2, bx2, by2, nboot=600)
    print("\nC0b CORRELATED windows (20 blocks sharing a per-block offset):")
    print("    paired %8.1f ppm   block %8.1f ppm (%d blocks)" % (sp2 * 1e6, sk2 * 1e6, nbk2))
    rat = sk2 / sp2
    print("    block/paired = %.2fx" % rat)
    ok_b = rat > 1.5
    print("    EXPECT block >> paired, because the naive bootstrap treats correlated"
          "\n    windows as independent and understates the spread.  %s"
          % ("PASS" if ok_b else "FAIL -- audit cannot see correlation"))
    print("\nCOMMISSIONED: %s" % ("YES, both conditions detectable" if (ok_a and ok_b)
                                  else "NO -- do not trust part 1"))
    return bool(ok_a and ok_b)


def main():
    ok = commission()
    c4g.STEP = 100
    res = {}
    for name in ("bee-3-cpl", "couch-fibers-cpl"):
        path = os.path.join(LIN, "%s-binned-off.tif" % name)
        if not os.path.exists(path):
            print("\nMISSING %s -- skipping" % path); continue
        img, W, H = cs.load_tiff_u16(path)
        cx, cy = W / 2.0, H / 2.0
        hd = float(np.hypot(cx, cy))
        ws = c4g.grid(img, W, H)
        m = measure(img, ws, "lk", cx=cx, cy=cy)
        eps_g, tx, ty, n, rms = fit_eps(m, cx, cy)
        dx = m[:, 2] - tx; dy = m[:, 3] - ty
        px = m[:, 0] - cx; py = m[:, 1] - cy
        rad = np.hypot(px, py)
        okr = rad > 1e-6
        d_r = dx * (px / np.where(okr, rad, 1)) + dy * (py / np.where(okr, rad, 1))
        rn = rad / hd
        bx = np.floor(m[:, 0] / BLOCK); by = np.floor(m[:, 1] / BLOCK)
        print("\n" + "=" * 96)
        print("PART 1 -- %s  BINNED OFF   %d windows   global eps %+.1f ppm" % (name, len(m), eps_g * 1e6))
        print("=" * 96)
        print("%-12s %5s %7s %11s %11s %11s %11s %9s"
              % ("ring r", "n", "r_bar", "eps ppm", "sd BROKEN", "sd paired", "sd block", "blocks"))
        rows = []
        for lo, hi in zip(EDGES[:-1], EDGES[1:]):
            s = okr & (rn >= lo) & (rn < hi)
            if s.sum() < 6:
                continue
            num = d_r[s]; den = rad[s]
            eps = float(np.median(num / den))
            sb = boot_broken(num, den)
            sp = boot_paired(num, den)
            sk, nbk = boot_block(num, den, bx[s], by[s])
            rows.append(dict(lo=lo, hi=hi, n=int(s.sum()), rbar=float(np.median(rn[s])),
                             eps=eps, sd_broken=float(sb), sd_paired=float(sp),
                             sd_block=float(sk), nblocks=int(nbk)))
            print("%-12s %5d %7.3f %11.1f %11.1f %11.1f %11.1f %9d"
                  % ("%.2f-%.2f" % (lo, hi), s.sum(), np.median(rn[s]), eps * 1e6,
                     sb * 1e6, sp * 1e6, sk * 1e6, nbk))
        if rows:
            r0 = rows[0]
            print("-" * 96)
            print("INNERMOST RING (the one ORCH is quoting):")
            print("   shipped (BROKEN pairing) : %.1f ppm   <-- the published 80.0" % (r0["sd_broken"] * 1e6))
            print("   correct paired bootstrap : %.1f ppm   (%.2fx the shipped value)"
                  % (r0["sd_paired"] * 1e6, r0["sd_paired"] / r0["sd_broken"]))
            print("   block bootstrap (ORCH)   : %.1f ppm   (%.2fx the paired value)"
                  % (r0["sd_block"] * 1e6, r0["sd_block"] / r0["sd_paired"]))
        res[name] = dict(rows=rows, eps_global=float(eps_g), n=int(len(m)))
        del img
    res["_commissioned"] = ok
    with open(os.path.join(OUT, "c13_bootaudit.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote c13_bootaudit.json")


if __name__ == "__main__":
    main()