"""Diagnostic: how much depth information does the per-tile focus label carry?

The planted-cause controls showed S1 firing on `P0-depth-only`, a stack with no
blur planted at all. That is only a defect of the *statistic* if the depth label
it was given was a real one. This prints the peakiness of every case's focus
profile so the two explanations can be told apart:

  * a stack with no depth-dependent blur has no focus peak to find, so its
    "winner index" is noise and S1 is being fed a meaningless regressor;
  * a real focus stack has a strong per-tile focus peak by construction.

    python m6_peakiness.py
"""

from __future__ import annotations

import numpy as np

import m6_lib as L

CASES = [
    ("data/control", "N1-null"),
    ("data/control", "P0-depth-only"),
    ("data/control", "P2-blur-only"),
    ("data/control", "P1-both"),
    ("data/109MSDCF", "109MSDCF"),
    ("data/119MSDCF", "119MSDCF"),
    ("data/coffee-bean", "coffee-bean"),
]

HDR = f"{'case':<16}{'tiles':>6}{'frames':>7}{'pk med':>9}{'pk p10':>9}{'pk p90':>9}{'w sd':>8}{'frac>gate':>11}"


def main():
    print("Per-tile focus-profile peakiness  (max-min)/max of the ring measure")
    print(f"gate = PEAKINESS_MIN = {L.PEAKINESS_MIN}")
    print(HDR)
    print("-" * len(HDR))
    for prefix, case in CASES:
        focus = L.load_focus(prefix, case)
        w, pk, prof = L.winner_index(focus)
        g = np.isfinite(pk)
        nfr = prof.shape[1]
        print(
            f"{case:<16}{int(g.sum()):>6}{nfr:>7}"
            f"{np.nanmedian(pk[g]):>9.3f}{np.nanpercentile(pk[g], 10):>9.3f}"
            f"{np.nanpercentile(pk[g], 90):>9.3f}{np.nanstd(w[g]):>8.2f}"
            f"{float(np.mean(pk[g] > L.PEAKINESS_MIN)):>11.3f}"
        )
    print()
    print("A case whose peakiness sits at the noise floor has no depth label to")
    print("regress against; any S1 result on it is uninterpretable, not a false")
    print("alarm about blur.")


if __name__ == "__main__":
    main()
