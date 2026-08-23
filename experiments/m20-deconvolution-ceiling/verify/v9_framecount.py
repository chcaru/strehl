"""M20 verification -- is the headline statistic frame-count biased?

The report defines each pixel's "best frame" as the argmin over frames of
sigma_local/signal_local.  A minimum over K noisy estimates falls with K, so a 105-frame
stack scores better than a 22-frame stack for no optical reason.  v7 shows the effect is
large (coffee-bean: 47.2% at 22 frames -> 65.8% at 105).

This selects the best frame by a DECOUPLED criterion -- the largest box-smoothed
noise-subtracted local signal over a 27-wide window, which is the shipped focus-measure
shape -- and then evaluates sigma_rel at that frame with the W=9 window.  Selection noise
and estimation noise no longer share a window, so the statistic should be far less
K-dependent.
"""
import os
import glob
import numpy as np
import rawpy
import exifread
from scipy.ndimage import uniform_filter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
W, WSEL, BLACK = 9, 27, 512

STACKS = [
    ("109MSDCF", r"C:\dev\macro\test\109MSDCF"),
    ("119MSDCF", r"C:\dev\macro\test\119MSDCF"),
    ("113MSDCF", r"D:\personal\macro\113MSDCF"),
    ("coffee-bean", r"C:\dev\macro\test\coffee-bean"),
]
CROSS = {"report est-sel": 0.3440, "verifier est-sel": 0.2996,
         "report oracle": 0.5734, "verifier oracle": 0.6703}


def exif(path):
    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    iso = None
    for k in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if k in t:
            iso = int(str(t[k]).split(",")[0].strip("[] "))
    return iso


def run(files, decoupled=True):
    iso = exif(files[0])
    g = iso / 436.8
    rn = 1.47 if iso >= 400 else 4.20
    best_score = None
    best_rel = None
    for f in files:
        with rawpy.imread(f) as r:
            gp = r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK
        m = uniform_filter(gp, W)
        v = np.maximum(uniform_filter(gp * gp, W) - m * m, 0.0)
        nvar = g * np.maximum(m, 0.0) + (rn * g) ** 2
        sig = np.sqrt(np.maximum(v - nvar, 0.0))
        rel = np.sqrt(nvar) / np.maximum(sig, 1e-6)
        score = uniform_filter(sig, WSEL) if decoupled else -rel
        if best_score is None:
            best_score, best_rel = score, rel
        else:
            take = score > best_score
            best_score = np.where(take, score, best_score)
            best_rel = np.where(take, rel, best_rel)
        del gp, m, v, nvar, sig, rel, score
    return best_rel, iso


def main():
    print("=" * 108)
    print("FRAME-COUNT BIAS CONTROL -- best frame chosen by a DECOUPLED 27-px sharpness score")
    print("=" * 108)
    hdr = f"{'stack':>13} {'K':>5} {'sel':>10} | {'p25':>8} {'p50':>8} {'p75':>8} | "
    hdr += " ".join(f"{k:>18}" for k in CROSS)
    print(hdr)
    for name, d in STACKS:
        files = sorted(glob.glob(os.path.join(d, "*.ARW")))
        subsets = [("22", files[:22]), ("all", files)]
        if len(files) <= 22:
            subsets = [("all", files)]
        for mode, dec in (("decoupled", True), ("argmin-rel", False)):
            for tag, fs in subsets:
                b, iso = run(fs, decoupled=dec)
                cells = " ".join(f"{float(np.mean(b<c))*100:>17.1f}%" for c in CROSS.values())
                print(f"{name:>13} {len(fs):>5} {mode:>10} | {np.percentile(b,25):>8.4f} "
                      f"{np.percentile(b,50):>8.4f} {np.percentile(b,75):>8.4f} | {cells}")
                np.save(os.path.join(OUT, f"dec_{name}_{len(fs)}_{mode}.npy"), b.astype(np.float32))
                del b
        print()


if __name__ == "__main__":
    main()
