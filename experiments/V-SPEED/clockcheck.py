"""Commission the clock the harness uses, against a child of known duration.

runner.py's time_stage() measures time.perf_counter() around subprocess.run().
This asks whether that construction reports the true wall clock of a child.

FIRST ATTEMPT FAILED, AND THE FAILURE IS THE INTERESTING PART. Timing a single
`python -c "time.sleep(T)"` child and comparing the absolute result against T
gives +0.48 s error at T=1 and +0.26 s at T=5, with a run-to-run SPREAD of
0.91-1.30 s. None of that is the clock. It is Python interpreter startup on a
box running nine agents, and startup contention is ONE-SIDED noise: it can only
add time, never remove it.

So the test is built the way the harness is actually read:

  DIFFERENTIAL -- t(T) - t(0), so the child's startup cost cancels instead of
                  being charged to the clock.
  MINIMUM      -- AGENTS.md rule 16. Against one-sided contention noise the
                  minimum over repeats is the estimator of the true duration;
                  the mean and the median both inherit the contention.

The input that would make this FAIL (AGENTS.md rule 20) exists and is cheap:
a harness that timed subprocess.Popen() without waiting reports a delta of
~0.00 s for every T, and a harness that double-counted would report 2T.
"""

import statistics
import subprocess
import sys
import time

TARGETS = [1.0, 5.0]
TOL = 0.10
REPEATS = 5


def timed(seconds):
    t0 = time.perf_counter()
    subprocess.run(
        [sys.executable, "-c", f"import time; time.sleep({seconds})"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return time.perf_counter() - t0


def sample(seconds):
    obs = [timed(seconds) for _ in range(REPEATS)]
    return min(obs), statistics.median(obs), max(obs) - min(obs)


def main():
    base_min, base_med, base_spread = sample(0.0)
    print(
        f"child startup baseline (sleep 0): min {base_min:.4f} s, "
        f"median {base_med:.4f} s, spread {base_spread:.4f} s"
    )
    print(f"\n{'target_s':>9}{'min_s':>10}{'delta_s':>10}{'error_s':>10}{'spread_s':>10}  verdict")
    fail = False
    for t in TARGETS:
        mn, med, spread = sample(t)
        delta = mn - base_min
        err = delta - t
        ok = abs(err) <= TOL
        fail |= not ok
        print(
            f"{t:>9.2f}{mn:>10.4f}{delta:>10.4f}{err:>+10.4f}{spread:>10.4f}"
            f"  {'PASS' if ok else 'FAIL'}"
        )
    print("\nCLOCK-CHECK:", "PASS" if not fail else "FAIL")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
