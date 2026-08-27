"""How much of a comparator's fine-scale power is 8-BIT QUANTISATION NOISE?

MEASURED FIRST, and it is why this file exists: focus-stack 1.5 writes 8 bits
per channel in every output format tried (.tif -> uint8, .png -> uint8).  The
inputs it is being given here are LINEAR develops whose median is 1112/65535 =
1.7%, so the median lands on 8-bit level 4.  A linear encoding of this scene
does not fit in 8 bits.

WHY THIS MATTERS AND WHICH WAY IT CUTS.  Quantisation error is white: it adds
roughly equal power to every band in ABSOLUTE terms.  The head-to-head statistic
(h2h2b.py) divides each ROI by its OWN 0.05-0.10 band, and the coarse band
carries far more signal power than the fine one.  So white noise inflates the
NORMALISED fine band much more than it inflates the reference band, and the
comparator's fine/coarse ratio comes out HIGH.  That is the same one-sidedness
h2h2b already discloses for sensor noise, and it points the same way:

    it flatters the COMPARATOR, so it is conservative against a "strehl wins"
    claim and DANGEROUS for a "strehl loses" claim.

That asymmetry is the whole reason to put a number on it before reading any
band table.  If the quantisation floor alone is comparable to the arm-to-arm
difference, the focus-stack arm is measuring bit depth and must not be reported
as resolution.

THE TEST.  Take strehl's own 16-bit linear output -- one image, so no alignment,
no registration, no second program -- and truncate it exactly the way an 8-bit
consumer does, `x >> 8`.  Compare band power and normalised spectral shape
before and after, over the same ROI grid the head-to-head uses.  Nothing else
changes, so every difference is quantisation.

FALSIFIER (rule 20): if the normalised fine bands barely move, 8-bit output is
not a confound here and the focus-stack arm can be read at face value.

INVOCATION (rule 47).  Reads only
    C:\\dev\\strehl-out\\V-H2H2\\lin\\113-full-g1.tiff
        197,798,923 bytes, 7032x4688 u16 RGB, made by
        experiments/V-HEADTOHEAD2/render_linear.ps1:
        `strehl stack D:\\personal\\macro\\113MSDCF --merge pyramid
         --pyramid-gate 4.5 --linear-srgb --demosaic`,
        STREHL_FULLRES_GATHER=1, pinned binary 740e7056.
Writes nothing.  Prints only.

    python quantfloor.py [nroi=64]
"""
import os
import sys

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
from h2h2b import band_power, REF                                # noqa: E402

STREHL = r"C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff"
T, PAD, MARGIN = 256, 32, 600
NAMES = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
LO = np.array([b[0] for b in h2.BANDS])
HI = np.array([b[1] for b in h2.BANDS])


def main():
    nroi = int(sys.argv[1]) if len(sys.argv) > 1 else 64
    a = tifffile.imread(STREHL)
    g16 = h2.luma709(np.asarray(a[:, :, :3], np.float64))
    # exactly what an 8-bit consumer keeps, put back on the 16-bit scale so the
    # two are directly comparable.  focus-stack's observed median (4 from an
    # input median 1112) is consistent with this plain right-shift.
    g8 = np.asarray((np.asarray(a[:, :, :3], np.uint16) >> 8).astype(np.float64)
                    * 256.0)
    g8 = h2.luma709(g8)
    del a

    H, W = g16.shape
    n = int(np.ceil(np.sqrt(nroi)))
    ys = np.linspace(MARGIN, H - MARGIN - T, n).astype(int)
    xs = np.linspace(MARGIN, W - MARGIN - T, n).astype(int)

    P16, P8 = [], []
    for y in ys:
        for x in xs:
            c16 = g16[y:y + T, x:x + T]
            c8 = g8[y:y + T, x:x + T]
            p1 = band_power(c16, LO, HI)
            p2 = band_power(c8, LO, HI)
            if p1 is None or p2 is None:
                continue
            P16.append(p1)
            P8.append(p2)
    P16 = np.array(P16)
    P8 = np.array(P8)
    print(f"strehl 113-full-g1, {len(P16)} ROIs of {T}px, 16-bit vs its own "
          f"8-bit truncation\n")

    print(f"  {'band':>11} {'P8/P16 raw':>12} {'shape8/shape16':>16}")
    n16 = P16 / P16[:, REF][:, None]
    n8 = P8 / P8[:, REF][:, None]
    for i, nm in enumerate(NAMES):
        raw = P8[:, i].sum() / P16[:, i].sum()
        shp = n8[:, i].mean() / n16[:, i].mean()
        print(f"  {nm:>11} {raw:12.4f} {shp:16.4f}")

    fine = NAMES.index("0.20-0.25")
    infl = n8[:, fine].mean() / n16[:, fine].mean() - 1.0
    print(f"\n  At the pre-registered comparison band 0.20-0.25, 8-bit "
          f"truncation alone\n  changes the normalised (shape) statistic by "
          f"{infl * 100:+.1f}%.")
    if abs(infl) < 0.05:
        print("  -> below the 5% LEVEL threshold: 8-bit output is not a "
              "confound at this band.")
    else:
        print("  -> AT OR ABOVE the 5% threshold: an 8-bit comparator arm is "
              "reporting bit depth,\n     not resolution, and must be labelled "
              "as such.  Sign is what matters:\n     positive = the 8-bit arm "
              "is FLATTERED, so it is conservative against strehl.")


if __name__ == "__main__":
    main()
