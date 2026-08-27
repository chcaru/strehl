"""Read the 2x2 plant commissioning and return a hard verdict.

A timer that cannot see a planted 5 s cannot see a real 5 s. runner.py plants
exactly PLANT seconds inside the timed region of ONE named stage, on the
production code path. This requires, against the same unplanted control:

  the planted stage   moves by +PLANT within TOL
  the other stage     does not move by anything like PLANT

Both halves are load-bearing. A one-sided plant cannot distinguish "the timer
saw 5 s" from "the timer adds 5 s to everything", so the run is a 2x2: strehl
planted, focus-stack planted, each read against one control.

ESTIMATOR: the warm MINIMUM, not the median. Nine agents share this box and
their load is one-sided -- contention can only make a stage slower. AGENTS.md
rule 16 says take the per-setting minimum for exactly this reason. The median
is printed alongside so a reader can see the two agree.

Exit 0 = commissioned. Exit 1 = NOT commissioned, and the lane must then
refuse to report timings.
"""

import sys

from analyse import load, summarise

PLANT = 5.0
TOL = 0.5

CTRL = "commission-ctrl"
ARMS = [("commission-plant-strehl", "strehl"), ("commission-plant-fs", "focus-stack")]


def main():
    ctrl = summarise(load(CTRL))
    fail = False
    print(f"plant = {PLANT:.2f} s, tolerance +/- {TOL:.2f} s, estimator = warm minimum\n")
    hdr = (
        f"{'planted':<13}{'stage':<13}{'ctrl_min':>9}{'arm_min':>9}{'d_min':>8}"
        f"{'ctrl_med':>9}{'arm_med':>9}{'d_med':>8}{'expect':>8}  verdict"
    )
    print(hdr)
    print("-" * len(hdr))
    for tag, planted in ARMS:
        arm = summarise(load(tag))
        for key in sorted(ctrl):
            _subj, _mode, stage = key
            if key not in arm:
                continue
            cmin, amin = ctrl[key]["warm_min_s"], arm[key]["warm_min_s"]
            cmed, amed = ctrl[key]["warm_median_s"], arm[key]["warm_median_s"]
            dmin, dmed = amin - cmin, amed - cmed
            spread = max(ctrl[key]["warm_spread_s"], arm[key]["warm_spread_s"])
            if stage == planted:
                ok = abs(dmin - PLANT) <= TOL
                expect = f"+{PLANT:.2f}"
            else:
                ok = abs(dmin) < min(PLANT - TOL, max(spread, TOL))
                expect = "~0"
            fail |= not ok
            print(
                f"{planted:<13}{stage:<13}{cmin:>9.2f}{amin:>9.2f}{dmin:>+8.2f}"
                f"{cmed:>9.2f}{amed:>9.2f}{dmed:>+8.2f}{expect:>8}"
                f"  {'PASS' if ok else 'FAIL'}  (spread {spread:.2f} s)"
            )
    print()
    print("COMMISSIONING:", "PASS" if not fail else "FAIL")
    if fail:
        print("A timer that cannot see a planted 5 s cannot see a real 5 s.")
        print("REFUSING to report timings.")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
