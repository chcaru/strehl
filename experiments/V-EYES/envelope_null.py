"""Does the ceiling rise with n because the master is soft, or because max does?

THE PROBLEM. The density sweep shows the ratio falling hard as the reference gets
denser -- flower-bud-alone-cpl 1.906 -> 1.369 -> 1.147 -> 0.974 at n = 13, 26, 52,
104 -- and the three subjects whose brackets are short enough to sample
exhaustively all land below 1.0. Read naively that says the master is softer than
the true per-site best frame and the corpus headline is a sampling artifact.

But there is a rival explanation that predicts the same curve and has nothing to
do with sharpness. The envelope is a MAXIMUM over n per-block estimates, and each
estimate carries noise. The expected maximum of n noisy draws grows with n like
sqrt(2 ln n) whatever the truth is. So a ratio built against a max-over-n ceiling
must fall as n rises even when subject and reference are identical. Distinguishing
"the master is soft" from "max is an order statistic" is the whole question, and
no amount of extra rendering answers it, because both hypotheses predict the same
monotone fall.

THE NULL. Build a reference whose true ratio is 1.0 BY CONSTRUCTION: n copies of
the master, each with independent noise at the real frames' measured noise level,
and nothing else different. Every copy has exactly the master's detail, so an
unbiased instrument must report 1.0 at every n. Whatever it actually reports is
the order-statistic inflation, measured rather than assumed, on this subject's own
data at this subject's own noise level.

The corrected ratio is then observed(n) / null(n), and the verdict is whether
THAT is below 1.0. This is the same discipline as the seven arms: a term the
verdict depends on -- here the n-dependence of the reference -- gets its own
control, because the sweep alone cannot tell a soft master from a rising ceiling.

The noise is calibrated empirically rather than analytically: white noise passed
through the instrument's own high-pass has an energy that depends on the kernel,
so unit noise is generated, its block high-pass energy measured, and the
amplitude scaled to land on the target floor. Assuming a closed form here would
be one more untested term.

Usage:
  python envelope_null.py <subject> <n1,n2,...>
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from softness_verdict3 import (  # noqa: E402
    luma_linear, detail, contrast, build_envelope, boot_ci,
)
from corpus_softness import SCRATCH, BLOCK, TILE, pick_tile  # noqa: E402


def calibrate_noise(shape, target_energy, seed=0):
    """Amplitude of white noise whose block high-pass energy equals target."""
    rng = np.random.default_rng(seed)
    probe = rng.normal(0, 1.0, shape)
    e = float(np.mean(detail(probe, BLOCK)[0])) + float(detail(probe, BLOCK)[1])
    return float(np.sqrt(max(target_energy, 0) / max(e, 1e-12)))


def main():
    subject = sys.argv[1]
    ns = [int(v) for v in sys.argv[2].split(",")]
    out = SCRATCH / subject
    mtif = out / "MASTER.tiff"
    if not mtif.exists():
        print(f"no cached master for {subject}; run corpus_softness.py --keep first")
        return

    mfull = luma_linear(tifffile.imread(str(mtif)))
    tx, ty = pick_tile(mfull, TILE)
    master = mfull[ty:ty + TILE, tx:tx + TILE].copy()
    del mfull

    ftifs = sorted(out.glob("frame-*.tiff"))
    floors = []
    for ft in ftifs[:13]:
        t = luma_linear(tifffile.imread(str(ft)))[ty:ty + TILE, tx:tx + TILE]
        floors.append(detail(t, BLOCK)[1])
    target = float(np.median(floors))
    amp = calibrate_noise(master.shape, target, seed=7)

    cm = contrast(master, BLOCK)
    cfloor = float(np.percentile(cm, 65))
    md, mfloor = detail(master, BLOCK)

    print(f"{subject}  tile ({tx},{ty}) {TILE}x{TILE} block {BLOCK}")
    print(f"  real frame noise floor (median of {len(floors)}): {target:.1f}")
    print(f"  master noise floor: {mfloor:.1f}")
    print(f"  calibrated noise amplitude: {amp:.1f} DN/px\n")
    print("  NULL: reference = n noised copies of the master. True ratio = 1.000")
    print(f"  {'n':>6}  {'null ratio':>11}  {'95% CI':>18}  {'inflation':>10}")
    print("  " + "-" * 54)

    rng = np.random.default_rng(11)
    results = {}
    for n in ns:
        tiles = [master + rng.normal(0, amp, master.shape) for _ in range(n)]
        env, _, valid = build_envelope(tiles, BLOCK, cfloor)
        live = (cm > cfloor) & valid
        vals = (md / np.maximum(env, 1e-12))[live]
        med = float(np.median(vals))
        lo, hi = boot_ci(vals)
        results[n] = med
        print(f"  {n:>6}  {med:>11.4f}  [{lo:>7.4f},{hi:>8.4f}]  "
              f"{1 / max(med, 1e-9):>9.3f}x")

    print("\n  A value below 1.000 is the instrument reading a soft master where")
    print("  none exists. Divide any observed ratio at the same n by it.")
    print("\n  CORRECTION TABLE")
    print(f"  {'n':>6}  {'divide observed by':>20}")
    for n, v in results.items():
        print(f"  {n:>6}  {v:>20.4f}")


if __name__ == "__main__":
    main()
