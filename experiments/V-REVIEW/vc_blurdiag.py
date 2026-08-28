r"""Diagnose the BLUR-ONLY failure on highly-angled-ruler-mm-cpl.

H1: the arm is UNPAIRED. Sites are fixed, but measure() skips a site when the
    profile or correlation gate refuses, so the voting set changes under blur
    and median(blurred) - median(base) compares two different populations.
H2: blur genuinely shifts this subject's per-site estimates (the mm ticks are
    periodic, so the lag search could lock onto a neighbouring tick).

Separated by the PAIRED median: paired ~ 0 => harness wrong, estimator fine.
"""
import numpy as np, sys
from scipy.ndimage import gaussian_filter
import vc_ca

OLD = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\%s.tiff"
CAP = 260

def keyed(res):
    return {(u[0], u[1]): res["ppmR"][i] for i, u in enumerate(res["used"])}

for subject in sys.argv[1:]:
    print("=" * 92)
    print("BLUR DIAGNOSTIC  %s" % subject)
    print("=" * 92)
    img = vc_ca.load(OLD % subject)
    H, W = img.shape[:2]
    centre = (H / 2.0, W / 2.0)
    S = vc_ca.sites(img[:, :, 1], centre)
    S = S[::max(1, len(S)//CAP)][:CAP]

    bl = img.copy()
    for c in range(3):
        bl[:, :, c] = gaussian_filter(img[:, :, c].astype(np.float32), 1.2).astype(np.uint16)

    ra = vc_ca.measure(img, centre, S)
    rb = vc_ca.measure(bl,  centre, S)
    A, B = keyed(ra), keyed(rb)
    both = sorted(set(A) & set(B)); onlyA = sorted(set(A) - set(B)); onlyB = sorted(set(B) - set(A))
    sa = vc_ca.summarise(ra); sb = vc_ca.summarise(rb)

    print("sites offered        : %d" % len(S))
    print("voted base / blurred : %d / %d   (both %d, dropped %d, gained %d)"
          % (len(A), len(B), len(both), len(onlyA), len(onlyB)))
    print("\nUNPAIRED (what the commission arm did):")
    print("  median base    ppmR = %+8.1f   n=%d" % (sa["ppmR"], sa["n_used"]))
    print("  median blurred ppmR = %+8.1f   n=%d" % (sb["ppmR"], sb["n_used"]))
    print("  delta               = %+8.1f  <-- the arm's number" % (sb["ppmR"] - sa["ppmR"]))

    pa = np.array([A[k] for k in both]); pb = np.array([B[k] for k in both])
    dif = pb - pa
    md = float(np.median(dif))
    mad = float(np.median(np.abs(dif - md)))
    se = 1.253 * 1.4826 * mad / max(1.0, np.sqrt(len(dif)))
    print("\nPAIRED (same %d sites, both arms):" % len(both))
    print("  median base    ppmR = %+8.1f" % np.median(pa))
    print("  median blurred ppmR = %+8.1f" % np.median(pb))
    print("  median per-site delta = %+8.1f ppm   <-- the honest null" % md)
    print("  mad per-site delta    = %8.1f ppm" % mad)
    print("  IQR per-site delta    = %+8.1f .. %+8.1f" % (np.percentile(dif,25), np.percentile(dif,75)))
    print("  approx SE of paired median = %6.1f ppm -> %.1f SE from zero"
          % (se, abs(md)/se if se > 0 else float("nan")))
    if onlyA:
        va = np.array([A[k] for k in onlyA])
        print("\n  STOPPED voting under blur: n=%d  median ppmR=%+.1f  (base pop median %+.1f)"
              % (len(va), np.median(va), sa["ppmR"]))
    if onlyB:
        vb = np.array([B[k] for k in onlyB])
        print("  STARTED voting under blur: n=%d  median ppmR=%+.1f" % (len(vb), np.median(vb)))
    print()
