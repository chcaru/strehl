"""Yield probe: how many sharp, isolated silhouette edges does each setting give?

Not a result -- a design step.  The E2 acceptance chain (plateau flatness on
BOTH sides, profile isolation, and the N3 rise envelope) is deliberately harsh,
and on a bee most edges fail it.  This finds a setting with enough n for the
bootstrap to mean anything, BEFORE any verdict is read.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from m121_io import arm_path, load_u16, luma  # noqa: E402
from runner import scan  # noqa: E402

MAX_RISE = 7.75   # n3-plant.json envelope.rise_p90_full


def main():
    img = luma(load_u16(arm_path("armM4-gate4-binlin")))
    for pct, flat, iso in ((99.0, 0.06, 0.30),
                           (97.0, 0.08, 0.35),
                           (95.0, 0.10, 0.40),
                           (90.0, 0.12, 0.45)):
        r = scan(img, label=f"pct{pct} flat{flat} iso{iso}", grad_percentile=pct,
                 max_edges=60000, isolation_frac=iso, flat_tol=flat,
                 max_rise=MAX_RISE, verbose=False)
        print(f"  pct={pct:5.1f} flat={flat:.2f} iso={iso:.2f} -> "
              f"seeds={r['seeds']:6d} measured={r['edges_measured']:6d} "
              f"pair={r['n_pair']:5d} bright={r['n_bright']:5d} dark={r['n_dark']:5d} "
              f"rise med={r['rise_median']:.2f} p90={r['rise_p90']:.2f}")


if __name__ == "__main__":
    main()
