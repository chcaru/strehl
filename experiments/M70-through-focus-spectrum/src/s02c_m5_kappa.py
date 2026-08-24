"""M70 s02c - why the committed M5 harness returns 0.2375 today and the report
says 0.2762.

Not in M70's charter. Recorded because fact 27's `f_sig = 0.2762 cyc/px` is the
anchor this milestone was dispatched on, and re-running M5's own committed
driver unmodified on the same 22 files returns 0.2375 with `B_max <= 3.563`.
AGENTS.md: "reproduce one published number from the original data before
extending anyone's experiment ... If it does not, stop - nothing downstream is
a valid comparison."

The candidate mechanism is `m5_lib.reference_kappa`, the Monte-Carlo floor on
the per-bin scatter that M5 section 2.6 says was added during the milestone.
M5's published block prints `kappa 0.056`; the committed code floors kappa at
the white-noise reference for the tiling geometry, which is much larger.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
from m70lib import L  # noqa: E402

STACK = r"D:\personal\macro\109MSDCF"
ROI_SIZE, TILE = 512, 256


def main() -> None:
    kref = L.reference_kappa(TILE, ROI_SIZE, "GQ", "hann", "iso")
    print(f"reference_kappa(tile={TILE}, roi={ROI_SIZE}, GQ, hann, iso) = {kref:.4f}")
    print("M5 report section 4.1 prints `kappa 0.056` for the same geometry.")
    print()

    rc, cc = 2344, 3514
    frames = sorted(f for f in os.listdir(STACK) if f.lower().endswith(".arw"))
    # M5's headline is a per-tile composite over frames; reproduce that shape
    # by keeping, per tile position, the periodogram of the frame with the
    # largest 0.05-0.14 band score (m5_lib.focus_score's band).
    best_sc, best_ps = None, None
    for name in frames:
        a = L.load_active(os.path.join(STACK, name))
        p = L.crop_lattice(a, "GQ", rc, cc, ROI_SIZE)
        ps = L.tile_psd2_stack(p, TILE, "hann")
        masks = L.band_masks(TILE, "GQ", "iso")
        sc = L.focus_score_2d(ps, masks)
        if best_sc is None:
            best_sc, best_ps = sc.copy(), ps.copy()
        else:
            upd = sc > best_sc
            best_ps[upd] = ps[upd]
            best_sc[upd] = sc[upd]
        del a
    psd2 = best_ps.mean(axis=0)
    f, p, c = L.radial_psd(psd2, "GQ", "iso")

    for kfl, label in ((kref, "committed (kappa floored at the MC reference)"),
                       (0.0, "kappa floor DISABLED (pre-section-2.6 behaviour)")):
        kn = L.knee_floor_crossing(f, p, c, kappa_floor=kfl)
        print(
            f"{label:52s} f_sig = {kn['f_c']}  kappa {kn['kappa']:.4f}  "
            f"dyn {kn['dynamic_range']:.0f}  floor sd {np.sqrt(kn['floor']):.2f}"
        )
        if kn["f_c"]:
            b = L.bellows_from_fc(kn["f_c"], 11.0)
            print(f"{'':52s} B_max = {b:.3f}")
    print()
    print("PUBLISHED (M5 section 4.1): f_sig 0.2762, kappa 0.056, dyn 1297, floor 0.950x model, B_max 3.064")


if __name__ == "__main__":
    main()
