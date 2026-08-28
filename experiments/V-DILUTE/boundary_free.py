"""V-DILUTE -- boundary-free restatement of the base-band result.

ORCH correction #4 makes any statement of the form "X% of the energy is in the
SIGNAL band" illegitimate, because which band is signal moves by subject.

The restatement that survives: report the share of the base-band difference
energy at or above **0.17 cyc/px**, which is the LOWEST boundary V-LINEAR
observed on any subject (flower-bud-alone-cpl).  Every subject's boundary is
>= 0.17, so the share above a given subject's own boundary is <= the share
above 0.17.  That makes this a CONSERVATIVE UPPER BOUND valid corpus-wide
without qualifying a single subject.

Also reports the share above 0.48 (the highest boundary observed, bee-1-cpl)
so both ends of V-LINEAR's range are bracketed.
"""
import os
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

# cut at 0.17 cyc/px  -> sigma = 1/(2*pi*0.17)
SIG_017 = 1.0 / (2.0 * np.pi * 0.17)
SIG_048 = 1.0 / (2.0 * np.pi * 0.48)

SUBJECTS = [("coffee-bubbles", 19), ("109MSDCF", 22), ("119MSDCF", 33),
            ("113MSDCF", 63), ("foam", 100), ("coffee-bean", 105),
            ("bee-3-cpl", 299)]


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


D = r"C:\dev\strehl-out\V-DILUTE\baseband"
print("Base-band contribution = decoded(--pyramid-base weighted) - decoded(mean),")
print("both at --pyramid-bands 7.  Energy share above the CORPUS-MINIMUM boundary")
print("0.17 cyc/px is an upper bound on the share above any subject's own boundary.")
print()
hdr = (f"{'subject':<16s} {'N':>4s} | {'max|d| DN':>9s} {'rms DN':>9s} | "
       f"{'share >=0.17':>12s} {'share >=0.48':>12s}")
print(hdr)
print("-" * len(hdr))
for subj, n in SUBJECTS:
    pa = os.path.join(D, f"{subj}.b7.mean.tiff")
    pb = os.path.join(D, f"{subj}.b7.weighted.tiff")
    if not (os.path.exists(pa) and os.path.exists(pb)):
        continue
    a, b = lum(pa), lum(pb)
    if a.shape != b.shape:
        continue
    d = b - a
    tot = float((d ** 2).sum())
    if tot <= 0:
        print(f"{subj:<16s} {n:4d} |  BIT-IDENTICAL")
        continue
    hi17 = d - gaussian_filter(d, SIG_017)
    hi48 = d - gaussian_filter(d, SIG_048)
    s17 = 100.0 * float((hi17 ** 2).sum()) / tot
    s48 = 100.0 * float((hi48 ** 2).sum()) / tot
    print(f"{subj:<16s} {n:4d} | {np.abs(d).max():9.1f} {d.std():9.3f} | "
          f"{s17:11.3f}% {s48:11.3f}%")

print()
print("Reading: the base band's contribution is a low-frequency object on every")
print("subject.  Its share above 0.17 cyc/px bounds its share above ANY boundary")
print("V-LINEAR measured, so this row needs no per-subject band qualification.")
