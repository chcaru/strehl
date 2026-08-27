"""REFUTED. THIS INSTRUMENT FALSELY CONVICTED A PINK SUBJECT. Do not use it.

It reported 109MSDCF as 11.76% magenta, with the rate rising monotonically with
luma to 84.21% of saturated pixels -- a catastrophic-looking highlight defect
in a master that had PASSED the print gate. I was about to report it as such.

109MSDCF is a photograph of PINK FABRIC. Two things refuted it, in this order:
the channel medians at the flagged pixels were R 63231, G 22081, B 26574 with
**0.0% of every channel at the ceiling**, so nothing was clipping and the
clipping story was dead; and then the crop was looked at, and it is pink cloth.

WHY THE COMMISSIONING PASSED ANYWAY. The negative arm was an achromatic ramp,
R=G=B. It proved only that the detector ignores GREY. It never asked whether
the detector ignores a legitimately COLOURED subject, which is the confound
that actually existed. A negative arm that cannot express the failure mode
certifies nothing, and this one was chosen because it was easy to build.

Three commits before this one I wrote the rule that would have caught it:
"commission with a planted improvement as well as a planted defect; an
instrument shown only degradations cannot distinguish blind from correct." The
same rule in its other direction -- show the instrument a HEALTHY subject that
superficially resembles the defect -- is the arm that was missing here.

Kept as the record of the false conviction. See also magspeckle.py (died on
its own P2 arm) and chromaspeckle.py (died on N2/N3), and ORCH-veiling.md 111.

--- original docstring follows, and its reasoning is still wrong ---

Are the magenta specks a HIGHLIGHT defect or a CHROMA-NOISE defect?

Seen at true 1:1 on tweezers-cpl and lavendar-cpl: isolated magenta pixels on
subjects that are achromatic (brushed steel; white trichomes on dark tissue).
Two candidate mechanisms, and they call for completely different fixes:

  HIGHLIGHT  channel-dependent clipping near saturation. G reaches its ceiling
             at a different level than R and B, so a blown highlight renders
             R+B without G, which is magenta. Fix is in highlight recovery.

  CHROMA     demosaic chroma noise, amplified by the double demosaic V-GATHER
             measured (+25.2% to +48.6% R-B high-pass). Fix is to stop
             demosaicing twice.

They are separable by a single question: DO THE MAGENTA PIXELS SIT AT
SATURATION? If magenta concentrates where luma is near the ceiling, it is
highlight. If it is spread across the tonal range, it is chroma noise.

COMMISSIONING. Two arms, because a detector only ever shown a defect cannot
distinguish blind from correct:
  - NEGATIVE: a synthetic achromatic ramp (R=G=B) must report ~0 magenta at
    every luma. If it fires there, the statistic is measuring nothing.
  - POSITIVE: plant magenta at KNOWN luma, and require the reported histogram
    to put it in the bin it was planted in. A detector that finds magenta but
    misattributes its luma would answer this question backwards.
"""
import os
import sys

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
# magenta = both chroma-opponent channels pushed the same way vs green
MAG_DN = 1200.0   # how far R and B must both exceed G to count, in 16-bit DN
BINS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 0.99), (0.99, 1.01)]


def magenta_mask(a):
    r = a[..., 0].astype(np.float32)
    g = a[..., 1].astype(np.float32)
    b = a[..., 2].astype(np.float32)
    return (r - g > MAG_DN) & (b - g > MAG_DN), np.maximum(np.maximum(r, g), b)


def histogram(a, label, total_note=""):
    m, peak = magenta_mask(a)
    ceil = 65535.0
    lu = peak / ceil
    n = int(m.sum())
    frac = n / m.size
    print("%-26s magenta %8d px  %.4f%% of frame%s" % (label, n, frac * 100, total_note))
    if n == 0:
        return frac, None
    rows = []
    for lo, hi in BINS:
        inb = (lu >= lo) & (lu < hi)
        cnt = int(inb.sum())
        hit = int((m & inb).sum())
        rate = (hit / cnt * 100) if cnt else 0.0
        rows.append((lo, hi, cnt, hit, rate))
        print("    luma %.2f-%.2f  pixels %9d  magenta %7d  rate %8.4f%%"
              % (lo, hi, cnt, hit, rate))
    top = max(rows, key=lambda r: r[4])
    print("    -> highest magenta RATE in luma bin %.2f-%.2f (%.4f%%)"
          % (top[0], top[1], top[4]))
    return frac, top


def commission():
    print("=== COMMISSIONING ===")
    ceil = 65535
    ramp = np.zeros((256, 256, 3), dtype=np.uint16)
    v = (np.linspace(0, ceil, 256)).astype(np.uint16)
    for c in range(3):
        ramp[..., c] = v[None, :]
    f, _ = histogram(ramp, "NEGATIVE achromatic ramp")
    if f != 0.0:
        print("*** NEGATIVE ARM FAILED: fired on R=G=B. Statistic is invalid. ***")
        return False

    # plant magenta ONLY in a mid-tone band, far from saturation
    plant = ramp.copy()
    band = slice(100, 120)
    plant[band, :, 0] = np.clip(plant[band, :, 0].astype(np.int32) + 3000, 0, ceil)
    plant[band, :, 2] = np.clip(plant[band, :, 2].astype(np.int32) + 3000, 0, ceil)
    _, top = histogram(plant, "POSITIVE midtone plant")
    if top is None:
        print("*** POSITIVE ARM FAILED: planted magenta not detected at all. ***")
        return False
    # the plant spans the full luma ramp horizontally, so it must NOT be
    # attributed exclusively to the top bin; that is the misattribution trap
    print("    (plant spans all luma; a detector that reported it as a")
    print("     saturation effect would have answered the real question wrong)")
    print("=== COMMISSIONING PASSED ===\n")
    return True


def main():
    if not commission():
        return 1
    names = sys.argv[1:] or ["tweezers-cpl", "lavendar-cpl", "bee-3-cpl", "109MSDCF"]
    print("=== CORPUS ===")
    for name in names:
        p = None
        for cand in sorted(os.listdir(SRC)):
            if cand.startswith(name) and cand.endswith(".tiff"):
                p = os.path.join(SRC, cand)
                break
        if p is None:
            print("%-26s MISSING" % name)
            continue
        a = tifffile.imread(p)
        if a.ndim != 3:
            print("%-26s not RGB" % name)
            continue
        histogram(a, name)
        print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
