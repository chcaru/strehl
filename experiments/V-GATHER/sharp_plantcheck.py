"""Are the planted arms real? The blur/sharpen arms multiply band powers by an
analytic transfer at band centres. That is a SIMULATION of a plant. Measure the
actual band-power transfer of a real pixel-space blur on the real master at the
real sites and compare, otherwise the commissioning is of an equation and not
of the instrument.
"""
import os, sys, numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, blur, usm, P
import sharp_bands as SB

subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
z = SB.build(subj)
sites = z["sites"]
my = luma(tifffile.imread(os.path.join(SB.ROOT, subj, "MASTER.tiff"))[..., :3].astype(np.float32))
fc = np.array([0.035, 0.085, 0.135, 0.175, 0.225, 0.275, 0.325, 0.385, 0.46])

def bp(img):
    return np.array([SB.bandpow(img[y:y+P, x:x+P]) for y, x in sites])

B0 = bp(my)
print("%-28s %s" % ("band centre cyc/px", "  ".join("%7.3f" % f for f in fc)))
for sg in (0.4, 0.8, 1.6):
    Bb = bp(blur(my, sg))
    meas = np.median(Bb / B0, axis=0)
    pred = np.exp(-4 * np.pi ** 2 * sg ** 2 * fc ** 2)
    print("\nreal pixel blur sigma %.1f" % sg)
    print("%-28s %s" % ("  MEASURED transfer", "  ".join("%7.4f" % v for v in meas)))
    print("%-28s %s" % ("  ANALYTIC (arm uses this)", "  ".join("%7.4f" % v for v in pred)))
    print("%-28s %s" % ("  ratio meas/analytic", "  ".join("%7.3f" % (m/p if p > 1e-9 else np.nan)
                                                           for m, p in zip(meas, pred))))
for am in (0.8,):
    Bu = bp(usm(my, am, 1.0))
    meas = np.median(Bu / B0, axis=0)
    pred = (1 + am * (1 - np.exp(-4 * np.pi ** 2 * 1.0 * fc ** 2))) ** 2
    print("\nreal pixel unsharp mask amount %.1f sigma 1.0" % am)
    print("%-28s %s" % ("  MEASURED transfer", "  ".join("%7.4f" % v for v in meas)))
    print("%-28s %s" % ("  ANALYTIC (arm uses this)", "  ".join("%7.4f" % v for v in pred)))
    print("%-28s %s" % ("  ratio meas/analytic", "  ".join("%7.3f" % (m/p) for m, p in zip(meas, pred))))
