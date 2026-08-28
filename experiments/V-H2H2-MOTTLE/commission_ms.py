# V-H2H2: commissioning ORCH's contrast_ms.py against planted, known answers.
#
# WHY. Under --linear-srgb on 112MSDCF the instrument returned a coarsest-band
# EDGE ratio of 0.9621 while its own printed rescale factor was 0.9684. Those
# two numbers being nearly equal is a specific, testable suspicion:
#
#   contrast_ms.py:64-68 sets scale = median(A)/median(B) and MULTIPLIES B's
#   PIXELS by it. A multiplicative rescale of an image multiplies every one of
#   its high-pass amplitudes by the same factor. So the correction is only
#   inert if the two arms really do differ by a pure gain. If they differ by
#   anything else -- an additive offset, say -- the instrument injects a
#   uniform multiplicative bias of exactly `scale` into EVERY band's ratio,
#   including the band it uses as its own null.
#
# This does not re-run the retracted band-power statistic and quote its new
# number. It asks whether the measuring device returns the KNOWN answer on
# inputs whose answer I fixed in advance.
#
# THE FOUR PLANTED ARMS. Every one has an answer known before the run:
#
#   GAIN   B = A * c            true ratio 1.000 at every band. A pure gain is
#                               precisely the confound the normaliser was built
#                               for, so this must come back 1.000. If it does
#                               not, the normaliser does not work at all.
#
#   OFFSET B = A + d            true ratio 1.000 at every band, EXACTLY -- a DC
#                               offset is annihilated by every high-pass filter
#                               in the bank, so it cannot change a band
#                               amplitude even in principle. Any deviation from
#                               1.000 here is manufactured by the instrument.
#                               d is chosen to move the median by the same
#                               fraction c does, so GAIN and OFFSET present the
#                               normaliser with an IDENTICAL median shift and
#                               differ only in whether that shift is real.
#
#   BLUR   B = gauss(A, 1.0)    a real degradation. Must score < 1, and worse
#                               at fine scales than coarse. Proves the
#                               instrument can respond at all -- a device that
#                               reads 1.000 on everything would pass both nulls
#                               above for the wrong reason.
#
#   SHARP  B = A + 0.5*(A-blur) a real IMPROVEMENT in fine-scale contrast. Must
#                               score > 1. This arm is here because a suite
#                               that plants only degradations cannot tell a
#                               statistic that is BLIND to an effect from one
#                               that is PERVERSE on it -- this project has
#                               already shipped a sharpness statistic bounded
#                               below by zero, which could never charge for a
#                               halo, because every arm ever put to it was a
#                               degradation.
#
# PASS/FAIL IS PRE-REGISTERED BELOW AND PRINTED AS SUCH. I am not entitled to
# choose the thresholds after seeing the table.

import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
MS = ROOT / "experiments" / "ORCH-drift-check" / "contrast_ms.py"
SRC = Path(r"C:\Users\chris\AppData\Local\Temp\vh2h2-lin\A.tif")
WORK = Path(r"C:\Users\chris\AppData\Local\Temp\vh2h2-commission")
WORK.mkdir(exist_ok=True)

# Pre-registered expectations. (label, description, band0 rule, band1 rule, null rule)
NULL_TOL = 0.005  # ORCH's own criterion-3 tolerance, reused verbatim.

a = tifffile.imread(SRC)
assert a.ndim == 3 and a.shape[2] >= 3, f"expected RGB, got {a.shape}"
a16 = a[..., :3].astype(np.float64)
med_a = float(np.median(a16 @ np.array([0.2126, 0.7152, 0.0722])))
print(f"source {SRC.name}  shape={a.shape} dtype={a.dtype}  luma median={med_a:.1f}")

C = 1.0327  # the median shift actually observed between the two real arms
d = med_a * (C - 1.0)
print(f"planted median shift: gain c={C:.4f}   equivalent offset d={d:.2f} DN")
print("(GAIN and OFFSET present the normaliser with the SAME median shift.)\n")

blur = np.stack([gaussian_filter(a16[..., k], 1.0) for k in range(3)], axis=-1)

arms = {
    "GAIN": a16 * C,
    "OFFSET": a16 + d,
    "BLUR": blur,
    "SHARP": a16 + 0.5 * (a16 - blur),
}

hi = np.iinfo(np.uint16).max
paths = {}
for name, arr in arms.items():
    clipped = int(np.sum((arr < 0) | (arr > hi)))
    frac = clipped / arr.size
    # A planted arm that clips is not the arm I planted.
    assert frac < 1e-4, f"{name}: {frac:.2%} of samples clipped; planted answer is void"
    p = WORK / f"{name}.tif"
    tifffile.imwrite(p, np.clip(arr, 0, hi).astype(np.uint16))
    paths[name] = p
    print(f"  wrote {name:7s} clipped={frac:.2e}")

# The source must also be re-written through the same uint16 path, so that any
# quantisation is common to both sides and cannot masquerade as a difference.
ref = WORK / "REF.tif"
tifffile.imwrite(ref, np.clip(a16, 0, hi).astype(np.uint16))

print()
results = {}
for name, p in paths.items():
    print("=" * 78)
    print(f"ARM {name}")
    out = subprocess.run(
        [sys.executable, str(MS), str(ref), str(p)],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        print(out.stdout)
        print(out.stderr)
        raise SystemExit(f"instrument failed on {name}")
    print(out.stdout.rstrip())
    rows = []
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 8 and parts[0].isdigit():
            rows.append((int(parts[0]), float(parts[-1])))
    assert rows, f"could not parse bands for {name}"
    results[name] = dict(rows)
    print()

print("=" * 78)
print("VERDICT vs PRE-REGISTERED EXPECTATIONS")
print("=" * 78)
nb = max(max(v) for v in results.values())
print(f"{'arm':8s} {'band0 EDGE':>11s} {'band1 EDGE':>11s} {'coarsest':>10s}   expectation")
fails = []
for name in ("GAIN", "OFFSET", "BLUR", "SHARP"):
    r = results[name]
    b0, b1, cn = r[0], r[1], r[nb]
    if name == "GAIN":
        exp = "all bands 1.000 (pure gain must be removed)"
        ok = all(abs(r[b] - 1.0) <= NULL_TOL for b in r)
    elif name == "OFFSET":
        exp = "all bands 1.000 (a DC offset cannot move a high-pass band)"
        ok = all(abs(r[b] - 1.0) <= NULL_TOL for b in r)
    elif name == "BLUR":
        exp = "band0 < band1 < coarsest, all < 1 (real degradation)"
        ok = b0 < b1 < cn and b0 < 1.0
    else:
        exp = "band0 > 1 (real improvement must score better)"
        ok = b0 > 1.0
    status = "PASS" if ok else "FAIL"
    if not ok:
        fails.append(name)
    print(f"{name:8s} {b0:11.4f} {b1:11.4f} {cn:10.4f}   [{status}] {exp}")

print()
print(f"commissioned arms: {len(results)}   passed: {len(results)-len(fails)}   FAILED: {len(fails)}")
if fails:
    print("FAILED ARMS: " + ", ".join(fails))
    print("An instrument that fails a planted arm cannot be quoted on the real ones.")
