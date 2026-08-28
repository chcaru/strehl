r"""Measure the hull-strength sweep. Closes the 'configured too soft' escape.

`pl-from5` is the internal negative control: it confines the per-level bound to
levels coarser than any scale this gauge can see, so it MUST read near 1.0. If
it did not, the sweep would be measuring something other than the bound. And if
every arm reads 1.0 including a hard projection, the null is a property of the
mechanism rather than of the setting.
"""
import os
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hul_measure as hm                                           # noqa: E402
import sharpaxis as sa                                             # noqa: E402
from lad_measure import band, finite                               # noqa: E402

ARMS = ["perlevel", "pl-lambda0", "pl-lambda0p5", "pl-from5", "unclamped"]
NOTE = {"perlevel": "hull_lambda 2.0 (shipping default for the mode)",
        "pl-lambda0": "HARD per-level projection",
        "pl-lambda0p5": "lambda 0.5",
        "pl-from5": "bound confined to levels >= 5  [INTERNAL NULL]",
        "unclamped": "no hull at all  [POTENCY]"}


def main():
    for sub in (sys.argv[1:] or ["foam", "coffee-bubbles"]):
        ref_p = hm.arm_path(sub, "inputrange")
        if not os.path.exists(ref_p):
            print("== %-18s no reference arm" % sub)
            continue
        ref, _ = hm.load_lum(ref_p)
        sites = hm.pick_sites(ref, n=48)
        base = hm.measure(ref, sites)
        gref = band(ref)
        print("== %-18s %d sites   (ratios vs inputrange; 1.0000 = no change)" % (sub, len(sites)))
        print("   %-14s %10s %10s   %10s   %s" % ("arm", "band", "acuity", "GLOBAL band", "note"))
        for arm in ARMS:
            p = hm.arm_path(sub, arm)
            if not os.path.exists(p):
                print("   %-14s %10s" % (arm, "not rendered"))
                continue
            lum, _ = hm.load_lum(p)
            rows = hm.measure(lum, sites)
            rb, _ = hm.ratios(base, rows, "band")
            ra, _ = hm.ratios(base, rows, "acuity")
            g = band(lum)
            gr = g / gref if finite(g, gref) and gref > 0 else float("nan")
            mb = float(np.median(rb)) if rb.size else float("nan")
            ma = float(np.median(ra)) if ra.size else float("nan")
            print("   %-14s %10.5f %10.5f   %10.5f   %s" % (arm, mb, ma, gr, NOTE[arm]))
            del lum
        del ref


if __name__ == "__main__":
    main()
