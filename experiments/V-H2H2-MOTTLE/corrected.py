# V-H2H2: apply the commissioned correction to the real arms.
#
# commission_ms.py established, against planted arms with answers fixed before
# the run, that contrast_ms.py:
#   - removes a pure GAIN correctly            (1.0010 at every band)
#   - responds correctly to a real BLUR        (0.4757 / 0.6330 / 0.9857)
#   - responds correctly to a real SHARPEN     (1.3290 / 1.2189 / 1.0086)
#   - but reports its own rescale factor at EVERY band on a pure DC OFFSET
#     (0.9696 everywhere, where the true answer is exactly 1.000)
#
# The defect is therefore not "the instrument is wrong". It is exactly one
# thing: median-ratio normalisation multiplies B's PIXELS, so it multiplies
# every high-pass amplitude of B by the same factor. That correction is inert
# only if the arms genuinely differ by a gain. To the extent they do not, a
# uniform multiplicative bias of exactly `scale` enters every band.
#
# Because the bias is uniform and multiplicative it is exactly invertible:
# divide every band ratio by the printed scale. The OFFSET arm confirms the
# inversion recovers the truth exactly (0.9696 / 0.9696 = 1.0000).
#
# CAVEAT, STATED BEFORE THE NUMBERS. The two real arms differ by BOTH a real
# gain component (tone placed on each arm's own percentile) and a non-gain
# component (the merge actually behaved differently). Dividing by the full
# scale is the right correction for the non-gain part and an OVER-correction
# for the gain part. So neither the raw nor the corrected column is exactly
# right: the truth is bracketed between them. I report BOTH and treat the
# interval as the finding, rather than picking whichever end I prefer.

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
MS = ROOT / "experiments" / "ORCH-drift-check" / "contrast_ms.py"

DEFAULT_PAIRS = [
    ("112MSDCF srgb   A vs K",      r"vh2h2-2side\A.tif",  r"vh2h2-2side\K.tif"),
    ("112MSDCF srgb   A vs S1",     r"vh2h2-2side\A.tif",  r"vh2h2-2side\S1.tif"),
    ("112MSDCF srgb   A vs S1000",  r"vh2h2-2side\A.tif",  r"vh2h2-2side\S1000.tif"),
    ("112MSDCF linear A vs K",      r"vh2h2-lin\A.tif",    r"vh2h2-lin\K.tif"),
]
TMP = Path(r"C:\Users\chris\AppData\Local\Temp")
SCALE_RE = re.compile(r"B rescaled by\s+([0-9.]+)")

# DEFECT FOUND 2026-08-28, and it nearly cost a wrong report.
# This script used to hardcode DEFAULT_PAIRS and never look at sys.argv. Invoked
# as `corrected.py <bee A.tif> <bee K.tif>` it silently rendered the 112MSDCF
# table instead -- three different invocations produced three byte-identical
# tables, and only the subject name baked into the label stopped those numbers
# being reported as a 299-frame depth result. Identical output across differing
# inputs is the signature; a script that cannot see its arguments cannot fail.
# Arguments are now honoured, and an odd/unusable argv is a hard error rather
# than a silent fallback to the built-in list.
argv = sys.argv[1:]
if argv:
    if len(argv) % 2 != 0:
        sys.exit(f"need an even number of paths (A B [A B ...]); got {len(argv)}")
    PAIRS = []
    for i in range(0, len(argv), 2):
        a, b = Path(argv[i]).resolve(), Path(argv[i + 1]).resolve()
        PAIRS.append((f"{a.parent.name}  {a.stem} vs {b.stem}", a, b))
else:
    PAIRS = [(lab, TMP / ra, TMP / rb) for lab, ra, rb in DEFAULT_PAIRS]

print("RAW = contrast_ms.py as published.  CORR = raw / rescale, the correction")
print("commissioned on the OFFSET arm.  Truth is bracketed by the two.")
print(f"source: {'argv' if argv else 'built-in DEFAULT_PAIRS'}   {len(PAIRS)} pair(s)\n")

n_scored = n_skipped = n_failed = 0
for label, pa, pb in PAIRS:
    if not (pa.exists() and pb.exists()):
        print(f"{label}: SKIPPED (master missing: {pa if not pa.exists() else pb})\n")
        n_skipped += 1
        continue
    out = subprocess.run([sys.executable, str(MS), str(pa), str(pb)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print(f"{label}: instrument FAILED\n{out.stderr}")
        n_failed += 1
        continue
    m = SCALE_RE.search(out.stdout)
    assert m, f"{label}: could not read the rescale factor; refusing to guess"
    scale = float(m.group(1))

    # Band rows carry 9 tokens when the band has a kind label (NOISE/SIGNAL) and
    # 8 when it does not, so key off the LAST SIX fields, which are the same in
    # both: FLAT A, FLAT B, flat ratio, EDGE A, EDGE B, edge ratio.
    rows = []
    for line in out.stdout.splitlines():
        p = line.split()
        if len(p) >= 8 and p[0].isdigit():
            rows.append((int(p[0]), p[1], float(p[-6]), float(p[-4]),
                         float(p[-3]), float(p[-1])))
    assert rows, f"{label}: no band rows parsed"

    # A parse I have not checked is not a measurement. contrast_ms.py prints its
    # own three headline numbers; if my table disagrees with them, my column
    # mapping is wrong and every number below it is fiction. An earlier version
    # of this script silently captured 2 of 6 bands, collapsed the null onto the
    # acuity row, and printed a verdict regardless. Hard-error instead.
    def headline(pattern):
        m = re.search(pattern + r"\s*:\s*([0-9.]+)", out.stdout)
        assert m, f"{label}: instrument did not print '{pattern}'"
        return float(m.group(1))

    ncoarse = max(r[0] for r in rows)
    assert len(rows) == ncoarse + 1, (
        f"{label}: parsed {len(rows)} rows but highest band index is {ncoarse}; "
        "bands were dropped")
    checks = [
        ("band-0 FLAT ratio", next(r for r in rows if r[0] == 0)[3]),
        ("band-1 EDGE ratio", next(r for r in rows if r[0] == 1)[5]),
        ("INSTRUMENT NULL coarsest EDGE", next(r for r in rows if r[0] == ncoarse)[5]),
    ]
    for pat, mine in checks:
        theirs = headline(pat)
        assert abs(mine - theirs) < 1e-6, (
            f"{label}: parse disagrees with instrument on '{pat}': "
            f"mine {mine} vs printed {theirs}")

    print("=" * 86)
    print(f"{label}     rescale = {scale:.4f}   (bias injected into every band)")
    print(f"  A = {pa}")
    print(f"  B = {pb}")
    print(f"{'band':>4} {'cyc/px':>13} {'FLAT A':>9} {'FLAT raw':>9} {'FLAT corr':>10}"
          f" {'EDGE raw':>9} {'EDGE corr':>10}")
    for b, cyc, fa, fr, ea, er in rows:
        tag = ""
        if b == 0:
            tag = "  <- GRAIN (band-0 FLAT)"
        elif b == 1:
            tag = "  <- ACUITY (band-1 EDGE)"
        elif b == ncoarse:
            tag = "  <- NULL"
        print(f"{b:>4} {cyc:>13} {fa:9.2f} {fr:9.4f} {fr/scale:10.4f}"
              f" {er:9.4f} {er/scale:10.4f}{tag}")

    b0 = next(r for r in rows if r[0] == 0)
    b1 = next(r for r in rows if r[0] == 1)
    cn = next(r for r in rows if r[0] == ncoarse)
    print()
    print(f"  GRAIN  band-0 FLAT : raw {b0[3]:.4f}  corr {b0[3]/scale:.4f}")
    print(f"  ACUITY band-1 EDGE : raw {b1[5]:.4f}  corr {b1[5]/scale:.4f}   (want >= 0.98)")
    nraw, ncorr = abs(cn[5] - 1.0), abs(cn[5] / scale - 1.0)
    print(f"  NULL   coarse EDGE : raw {cn[5]:.4f} (|d|={nraw:.4f})  "
          f"corr {cn[5]/scale:.4f} (|d|={ncorr:.4f})   (tol 0.005)")
    verdict = []
    verdict.append("null PASSES corrected" if ncorr <= 0.005 else "null still FAILS corrected")
    verdict.append("acuity clears 0.98 corrected" if b1[5] / scale >= 0.98
                   else "acuity below 0.98 corrected")
    print(f"  -> {'; '.join(verdict)}")
    n_scored += 1

# Every input lands in exactly one counted outcome, and they sum to the number
# of pairs offered. A count that does not move looks the same whether nothing
# was wrong or nothing was examined.
print()
print("=" * 86)
print(f"PARTITION  offered {len(PAIRS)}  =  scored {n_scored} + "
      f"skipped {n_skipped} + instrument-failed {n_failed}")
assert n_scored + n_skipped + n_failed == len(PAIRS), "partition does not close"
if n_scored == 0:
    sys.exit("nothing was scored -- do not read any verdict above as a result")
    print()
