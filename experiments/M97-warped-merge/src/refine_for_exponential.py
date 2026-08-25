"""Refine the gate ladder where the EXPONENTIAL kernel has support.

M111 built its ladder for the Gaussian and said so: "Beyond z = 4.71 the kernel
is truncated to zero, so gate 16 already closes the support and no sample above
it is needed." That is correct for the Gaussian and wrong for the exponential,
and pricing one kernel on the other's ladder is not a comparison.

The maps are the gap CDF sampled at z = gate / DEFAULT_GATE = gate / 4. The two
cutoffs, both at the same WEIGHT_FLOOR = 2^-16:

    gaussian     z = sqrt(32 ln 2) =  4.7096  ->  gate 18.84
    exponential  z = 16 ln 2       = 11.0904  ->  gate 44.36

M111's rungs above 16 are 64 and 100000. So for the exponential the whole
interval z = 4 .. 16 is ONE BIN, across which the kernel falls from
exp(-4) = 1.83e-2 to below the floor -- a factor of about 1200 in weight.

That is the SAME DEFECT M111 diagnosed in its own first run, where a single bin
spanning a factor of 1800 "bounded nothing" and produced overlapping intervals
that its verdict code initially called FAILED. M111 refined the ladder rather
than reporting the overlap, and the refined intervals nested inside the coarse
ones. The exponential is owed exactly the same treatment; reporting its overlap
as "the Gaussian wins" would be reporting my instrument's blind spot as a
property of the kernel.

New rungs: gates 18, 20, 24, 28, 32, 36, 40, 44  ->  z = 4.5, 5, 6, 7, 8, 9,
10, 11, which brackets the exponential's cutoff at z = 11.0904.

TWO THINGS THIS SCRIPT IS CAREFUL ABOUT
---------------------------------------
1. It uses M111'S BINARY, not a fresh build. A ladder is one distribution
   sampled at many gates; if half the rungs come from different code the
   Stieltjes sum is over two distributions and every bound is meaningless.
   `softgate_prediction.py` already carries the guard that would catch it --
   the monotonicity check, since the gap CDF must be non-decreasing in gate --
   and that check is the reason to trust mixing my rungs with M111's at all.

2. It writes into MY output tree, never M111's. M111 may still be running.

Gating is on `subprocess.run().returncode` throughout (fact 1490).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

M111 = Path(r"C:\dev\strehl-out\M111")
EXE = M111 / ".cargo-nc8" / "release" / "strehl.exe"
WARPMAP = M111 / "marker-warpmap.txt"
STACK = r"D:\personal\macro\dry-erase-marker-head-cpl"  # STRICTLY READ-ONLY
OUT = Path(r"C:\dev\strehl-out\M97\render")

GATES = [18, 20, 24, 28, 32, 36, 40, 44]

# The second refinement, and it is aimed at the opposite end from the first.
# `width_decomp.py` MEASURED that 100% of the exponential's bound width in both
# populations comes from the FIRST bin, z = 0 .. 0.0625, and 0.0% from the eight
# tail rungs above -- because a textured pixel is sharp in one frame, that frame
# is the winner, and the winner sits at gap exactly 0 where both kernels read
# exactly 1.0. The ladder cannot see that it sits at 0 rather than at 0.0625,
# and across that stretch the exponential falls by 0.0606 against the Gaussian's
# 0.0020: 31x looser, entirely because exp(-z) has a CUSP at the origin where
# exp(-0.5 z^2) is FLAT.
#
# So the first eight rungs were aimed at the wrong end. This is recorded rather
# than quietly corrected: the tail refinement is what proved the tail was not
# the problem, and a refinement that finds nothing is still a measurement.
LOW_GATES = [0.03, 0.06, 0.12]

# Every variable M111's refine_ladder.ps1 clears, plus STREHL_SOFT_GATE, which
# did not exist when that script was written and which this session has been
# setting. A stale soft-gate setting inherited from the shell would put one rung
# on a different estimator from the rest.
CLEAR = ["STREHL_ALIGN", "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
         "STREHL_DUMP_ELECTION", "STREHL_M111_REG_RADIUS", "STREHL_SOFT_GATE",
         "STREHL_FIX_CA"]


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "tail"
    if which == "tail":
        gates = GATES
    elif which == "low":
        gates = LOW_GATES
    else:
        raise SystemExit("usage: refine_for_exponential.py [tail | low]")

    for p, what in ((EXE, "binary"), (WARPMAP, "warpmap")):
        if not p.exists():
            raise SystemExit(f"HARNESS ERROR: no {what} at {p}")
    if not Path(STACK).is_dir():
        raise SystemExit(f"HARNESS ERROR: no stack at {STACK}")
    OUT.mkdir(parents=True, exist_ok=True)

    before = sorted(os.listdir(STACK))

    for g in gates:
        tag = f"{g:g}".replace(".", "p")
        d = OUT / f"state-g{tag}"
        npy = d / f"n_eff_gate{g:.2f}.npy"
        if npy.exists():
            print(f"  gate {g:<7}: already present, skipping")
            continue
        d.mkdir(parents=True, exist_ok=True)

        env = dict(os.environ)
        for k in CLEAR:
            env.pop(k, None)
        env["STREHL_WARPMAP"] = str(WARPMAP)
        env["STREHL_DUMP_MERGE_STATE"] = str(d)
        tif = OUT / f"marker-g{tag}.tif"

        t0 = time.time()
        p = subprocess.run(
            [str(EXE), "stack", STACK, "--srgb", "--auto-exposure",
             "--gate", f"{g:g}", "--out", str(tif)],
            capture_output=True, env=env,
        )
        secs = int(time.time() - t0)
        if p.returncode != 0:
            log = (p.stdout + p.stderr).decode("utf-8", "replace")
            print("\n".join(log.splitlines()[-15:]))
            raise SystemExit(f"render failed at gate {g}: exit {p.returncode}")

        # The owner's library is irreplaceable and read-only (rule 45). A render
        # that dropped a sidecar into it would also mean STREHL_WARPMAP was not
        # honoured, so this checks the constraint and the pinning at once.
        if sorted(os.listdir(STACK)) != before:
            raise SystemExit(f"HERMETICITY FAILURE: `{STACK}` changed during gate {g}")

        if not npy.exists():
            got = sorted(x.name for x in d.iterdir())
            raise SystemExit(f"gate {g} produced no {npy.name}; got {got}")
        print(f"  gate {g:<7}: {secs:>4}s  ->  {npy.name}")
        tif.unlink(missing_ok=True)  # only the state maps are the artefact

    print("ladder refinement complete")


if __name__ == "__main__":
    sys.exit(main())
