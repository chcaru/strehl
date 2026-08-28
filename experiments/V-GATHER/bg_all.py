r"""Rim + structure-split across every subject V-BANDFLOOR rendered the pair for.

WHY SIX AND NOT ONE. The knob's actual potency varies 60-fold across these
subjects, measured from the renders' own banners at band 1:

    coffee-bubbles 60.6%   119MSDCF 57.1%   dry-erase 45.7%
    bee-2-cpl 33.3%        leaf-2-cpl 19.4%  wrapped-text-1 1.0%

so this is a DOSE-RESPONSE, not a single A/B. If the knob moves rim, the
subjects where the gate actually changed behaviour must move more than
wrapped-text-1, where it barely fired at all. wrapped-text-1 is a NATURAL null:
the treatment was applied and did almost nothing, so any rim change there is a
bound on what the instrument reports when the mechanism is absent. A constructed
null answers a question you designed; a natural one answers the subject's.

ARMS PER SUBJECT. NULL where a byte-identical render exists, USM as the
per-subject potency arm (a gauge must be shown to see a rim ON THIS SUBJECT
before its silence on that subject means anything), then the treatment.

The width column is NOT reported: bg_width.py showed rimv6's edge_width fails to
recover a planted blur at every rung from sigma 0.4 to 3.0 and is non-monotonic
below sigma 2. Softening is measured instead by the independent structure split,
which is commissioned on a planted denoise AND a planted softening.
"""
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bg_ab                                                       # noqa: E402
import gf_discriminate as GFD                                      # noqa: E402

D = r"C:\dev\strehl-out\V-BANDFLOOR"
SUBS = ["leaf-2-cpl", "119MSDCF", "coffee-bubbles",
        "dry-erase-marker-head-cpl", "bee-2-cpl", "wrapped-text-1"]
HERE = os.path.dirname(os.path.abspath(__file__))


def rim_all():
    for s in SUBS:
        A = os.path.join(D, s + "__A-unset.tiff")
        B = os.path.join(D, s + "__B-coarse8.tiff")
        N = os.path.join(D, s + "__N-null.tiff")
        if not (os.path.exists(A) and os.path.exists(B)):
            print("%-28s SKIP (missing pair)" % s)
            continue
        print("\n" + "=" * 80)
        print("RIM  %s" % s)
        print("=" * 80)
        arms = []
        if os.path.exists(N):
            arms.append(("NULL byte-identical", N))
        arms.append(("USM 1.4 potency", lambda g: np.clip(
            g + 1.4 * (g - gaussian_filter(g, 1.2)), 0, 1).astype(np.float32)))
        arms.append(("B coarse8 TREATMENT", B))
        try:
            bg_ab.run(A, arms, s, os.path.join(HERE, "bg_%s.json" % s))
        except Exception as exc:                                   # noqa: BLE001
            print("  ERROR: %r" % (exc,))
        sys.stdout.flush()


def split_all():
    print("\n" + "=" * 80)
    print("STRUCTURE SPLIT -- is any acuity change removed NOISE or removed DETAIL?")
    print("=" * 80)
    if not GFD.commission():
        print("discriminator failed commissioning; no split verdict")
        return
    print("%-28s %8s %8s %10s %10s  %s"
          % ("subject", "flat", "detail", "POT flat", "POT det", "reading"))
    print("-" * 84)
    for s in SUBS:
        A = os.path.join(D, s + "__A-unset.tiff")
        B = os.path.join(D, s + "__B-coarse8.tiff")
        if not (os.path.exists(A) and os.path.exists(B)):
            continue
        ga = bg_ab.lum(A)[0].astype(np.float64)
        gb = bg_ab.lum(B)[0].astype(np.float64)
        ref = gaussian_filter(0.5 * (ga + gb), 1.5)
        rf, rd, nf, nd = GFD.split_ratio(ga, gb, ref)
        # PER-SUBJECT POTENCY: a planted softening on this subject's own pixels.
        # Silence from the split means nothing until it has spoken here.
        pf, pd, _, _ = GFD.split_ratio(ga, gaussian_filter(ga, 1.2), ref)
        if not np.isfinite(rd):
            reading = "REFUSED (no detail territory)"
        elif not (np.isfinite(pd) and pd < 0.90):
            reading = "REFUSED (potency arm failed on this subject)"
        elif rd < 0.98:
            reading = "DETAIL LOST"
        elif rf < 0.98:
            reading = "denoise only"
        else:
            reading = "inert"
        print("%-28s %8.4f %8.4f %10.4f %10.4f  %s"
              % (s, rf, rd, pf, pd, reading))
        sys.stdout.flush()
        del ga, gb, ref


if __name__ == "__main__":
    rim_all()
    split_all()