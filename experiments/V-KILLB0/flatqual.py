"""V-KILLB0 FLAT-SITE band qualification (ORCH's falsification target).

ORCH's defence of the bee-1-cpl gate-floor result is that V-LINEAR's boundary
is a whole-frame aggregate while his 0.0812 was measured at FLAT sites, and
flat-site content can be noise even on a subject whose frame-wide band 0
qualifies.  This tests that defence instead of granting it.

The DECISION RULE IS NOT MINE.  band_power, ratio_ci and verdict are imported
unmodified from V-LINEAR2/bandsignal.py and V-HEADTOHEAD2/h2h2b.py, so a band
that passes here passes by exactly the pre-registered criterion
(R >= 2.0 and CI low >= 1.5).  The ONLY thing I change is which tiles are
scored.  Tiles are a dense grid; FLAT is the bottom quartile of in-focus
selection-band (0.05-0.20 cyc/px) power and STRUCTURED the top quartile, so
"flat" means low structure measured on the source frames themselves.

THE CONTROL THAT MAKES THE FLAT NUMBER READABLE.  At a flat tile, `pf` is a
MAXIMUM over ~75 frames and `pd` a mean of 2, so even pure noise gives R > 1 by
selection alone.  Two nulls measure that floor:
  * PERMUTED  -- the real per-tile power series with frame order shuffled.
    This destroys any focus response while preserving the noise distribution
    exactly, so whatever R survives is pure selection bias.
  * SYNTHETIC -- i.i.d. noise with matched per-tile mean power.
A flat-site R is only evidence of signal if it clears these.
"""
import os
import sys

import numpy as np
import tifffile

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(_E, "V-LINEAR2"))
sys.path.insert(0, os.path.join(_E, "V-HEADTOHEAD2"))
import bandsignal as BS                                            # noqa: E402
import h2                                                          # noqa: E402
from h2h2b import band_power                                       # noqa: E402

T, MARGIN = BS.T, BS.MARGIN
ALLB = BS.FINE
LO = np.array([b[0] for b in ALLB])
HI = np.array([b[1] for b in ALLB])
SEL = np.array([BS.SEL_LO]), np.array([BS.SEL_HI])
NY, NX = 10, 13


def main():
    d, key, far_real = sys.argv[1], sys.argv[2], int(sys.argv[3])
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".tif"))
    n = len(files)
    far = max(2, round(far_real / 4))          # develops are every 4th real frame
    m0 = tifffile.memmap(os.path.join(d, files[0]), mode="r")
    H, W = m0.shape[0], m0.shape[1]
    del m0
    ys = np.linspace(MARGIN, H - MARGIN - T, NY).astype(int)
    xs = np.linspace(MARGIN, W - MARGIN - T, NX).astype(int)
    pos = [(int(y), int(x)) for y in ys for x in xs]

    power = np.zeros((n, len(pos), len(ALLB)))
    selp = np.zeros((n, len(pos)))
    for a, f in enumerate(files):
        mm = tifffile.memmap(os.path.join(d, f), mode="r")
        for i, (y, x) in enumerate(pos):
            crop = h2.luma709(np.asarray(mm[y:y + T, x:x + T, :3], np.float64))
            bp = band_power(crop, LO, HI)
            sp = band_power(crop, SEL[0], SEL[1])
            power[a, i] = np.nan if bp is None else bp
            selp[a, i] = np.nan if sp is None else sp[0]
        del mm
        sys.stderr.write(f"\r  {key}: {a+1}/{n}   ")
    sys.stderr.write("\n")
    np.save(f"C:\\dev\\strehl-out\\V-KILLB0\\{key}-power.npy", power)
    np.save(f"C:\\dev\\strehl-out\\V-KILLB0\\{key}-selp.npy", selp)
    print(f"saved {key} power{power.shape} selp{selp.shape} far={far} n={n}")


if __name__ == "__main__":
    main()
