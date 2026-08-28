"""Why does -500 recover -368 while +500 recovers +528?
Prime suspect: median(planted) - median(base) is NOT paired. If different sites
survive the correlation gate in each arm, the two medians describe different
populations and their difference is biased. Test: compute PER-SITE deltas."""
import numpy as np, vc_ca
from vc_commission import plant_radial, OLD, CAP

sub = "dry-erase-marker-head-cpl"
img = vc_ca.load(OLD % sub)
H, W = img.shape[:2]; centre = (H/2.0, W/2.0)
S = vc_ca.sites(img[:, :, 1], centre)
S = S[::max(1, len(S)//CAP)][:CAP]

def per_site(im):
    """ppmR keyed by site index, so arms can be paired exactly."""
    out = {}
    for i, (py, px, nx, ny, r, m, al) in enumerate(S):
        pg = vc_ca.profile(im[:, :, 1], py, px, nx, ny)
        pr = vc_ca.profile(im[:, :, 0], py, px, nx, ny)
        if pg is None or pr is None: continue
        s = vc_ca.shift(pr, pg)
        if s is None: continue
        out[i] = (s/al) / r * 1e6
    return out

base = per_site(img)
print("baseline sites surviving: %d of %d" % (len(base), len(S)))
for eps in (+500.0, -500.0):
    p = per_site(plant_radial(img, 0, eps*1e-6, centre))
    common = sorted(set(base) & set(p))
    unpaired = np.median([p[i] for i in p]) - np.median([base[i] for i in base])
    paired = np.median([p[i] - base[i] for i in common])
    print("\nplant %+.0f ppm" % eps)
    print("  surviving sites : %d   common with baseline: %d   dropped: %d"
          % (len(p), len(common), len(base) - len(common)))
    print("  UNPAIRED median-of-medians delta : %+8.1f ppm" % unpaired)
    print("  PAIRED   median of per-site delta: %+8.1f ppm" % paired)
    d = np.array([p[i] - base[i] for i in common])
    print("  paired delta quartiles: %+.1f / %+.1f / %+.1f" %
          (np.percentile(d,25), np.percentile(d,50), np.percentile(d,75)))
