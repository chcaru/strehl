r"""How fast does the CA estimate move with EQUAL blur on all channels?

This is the build-difference confound, quantified. eps_r = -508.4e-6 is the
coefficient change under test, so the question is not "is the sensitivity zero"
(it is not, on the ruler) but "is it small compared with ~508 ppm at a blur
difference two builds could plausibly produce".

Paired throughout: same sites voting in both arms.
"""
import numpy as np, sys
from scipy.ndimage import gaussian_filter
import vc_ca

OLD = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\%s.tiff"
CAP = 260
SIGMAS = [0.3, 0.6, 1.2, 2.0]

def keyed(res):
    return {(u[0], u[1]): res["ppmR"][i] for i, u in enumerate(res["used"])}

print("blur sensitivity, PAIRED per-site median delta in ppm")
print("(equal gaussian sigma on R,G,B -- introduces no CA by construction)")
print()
hdr = "%-34s %7s %8s" % ("subject", "n", "base")
for s in SIGMAS: hdr += "  %9s" % ("s=%.1f" % s)
print(hdr); print("-" * len(hdr))

for subject in sys.argv[1:]:
    img = vc_ca.load(OLD % subject)
    H, W = img.shape[:2]
    centre = (H / 2.0, W / 2.0)
    S = vc_ca.sites(img[:, :, 1], centre)
    if len(S) < vc_ca.MIN_SITES:
        print("%-34s  UNSCORED (%d sites)" % (subject, len(S))); continue
    S = S[::max(1, len(S)//CAP)][:CAP]
    ra = vc_ca.measure(img, centre, S); A = keyed(ra)
    sa = vc_ca.summarise(ra)
    row = "%-34s %7d %+8.1f" % (subject, sa["n_used"], sa["ppmR"])
    for sg in SIGMAS:
        bl = img.copy()
        for c in range(3):
            bl[:, :, c] = gaussian_filter(img[:, :, c].astype(np.float32), sg).astype(np.uint16)
        B = keyed(vc_ca.measure(bl, centre, S))
        both = sorted(set(A) & set(B))
        dif = np.array([B[k] - A[k] for k in both])
        row += "  %+9.1f" % np.median(dif)
    print(row)
    sys.stdout.flush()
print()
print("reference: the coefficient change under test is eps_r = -508.4 ppm")
