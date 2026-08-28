"""Diagnose WHY each master skips halo_profile -- every guard, not just the first.

The shipped instrument returns on the FIRST guard that fires, so a subject
reported as "862 components" may also have no far field and a sloped
background.  Fixing only the reported cause would then buy nothing.  This
evaluates all guards independently and decomposes the component count, because
"574 components" does not distinguish one blob plus 573 dust specks from a
genuinely fragmented subject and those need different answers.
"""
import glob, json, os, sys
import numpy as np, tifffile
from scipy.ndimage import (binary_closing, binary_opening,
                           distance_transform_edt, label)

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

SRC = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
CACHE = r"D:\strehl-out\V-REVIEW\halo\cache"
os.makedirs(CACHE, exist_ok=True)


def plane(path):
    """Luma subsampled by 2, cached.  a[::2,::2][::2,::2] == a[::4,::4] exactly,
    so sub=4 (what the instrument uses) is derivable from this without reload."""
    c = os.path.join(CACHE, os.path.basename(path).split("--")[0] + ".npy")
    if os.path.exists(c):
        return np.load(c)
    y = H.luma(tifffile.imread(path))[::2, ::2].astype(np.float32)
    np.save(c, y)
    return y


def diag(y2):
    y = y2[::2, ::2]                      # == full[::4,::4], the instrument's grid
    sub = 4
    t = H.otsu(y.ravel())
    subj = binary_opening(y < t, np.ones((3, 3)))
    subj = binary_closing(subj, np.ones((5, 5)))
    r = {"otsu": float(t), "frac": float(subj.mean()),
         "backdrop": float((y > t).mean())}

    lab, nlab = label(subj)
    r["ncomp"] = int(nlab)
    if nlab:
        sizes = np.sort(np.bincount(lab.ravel())[1:])[::-1]
        tot = float(sizes.sum())
        r["largest_share"] = float(sizes[0]) / tot
        r["top5_share"] = float(sizes[:5].sum()) / tot
        # speckle = components under 0.5% of subject mass
        r["speckle_share"] = float(sizes[sizes < 0.005 * tot].sum()) / tot
        r["n_major"] = int((sizes >= 0.01 * tot).sum())
    else:
        r["largest_share"] = r["top5_share"] = r["speckle_share"] = 0.0
        r["n_major"] = 0

    d = distance_transform_edt(~subj) * sub
    r["dmax"] = float(d.max())
    far = (d >= H.FAR[0]) & (d < H.FAR[1])
    r["farpx"] = int(far.sum())
    r["farpx_need"] = H.MIN_FARPX // (sub * sub)
    mid = (H.FAR[0] + H.FAR[1]) // 2
    a1 = (d >= H.FAR[0]) & (d < mid); a2 = (d >= mid) & (d < H.FAR[1])
    r["spread"] = (abs(float(np.median(y[a1])) - float(np.median(y[a2])))
                   if a1.sum() > 200 and a2.sum() > 200 else None)
    r["nearpop"] = sum(1 for lo, hi in H.NEAR if int(((d >= lo) & (d < hi)).sum()) > 200)

    # every guard, independently
    r["g_subj_small"] = r["frac"] < H.MIN_SUBJ
    r["g_subj_big"] = r["frac"] > H.MAX_SUBJ
    r["g_backdrop"] = r["backdrop"] < 0.05
    r["g_far"] = r["farpx"] < r["farpx_need"]
    r["g_comp"] = nlab > 1 and r["largest_share"] < H.MIN_LARGEST
    r["g_uniform"] = r["spread"] is not None and r["spread"] > H.BG_UNIFORM
    r["g_nearband"] = r["nearpop"] == 0
    return r


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.tif"))
                   + glob.glob(os.path.join(SRC, "*.tiff")))
    out = {}
    print("%-38s %6s %6s %5s %6s %6s %5s %8s %7s  %s"
          % ("subject", "frac", "large", "ncmp", "speck", "major", "near",
             "farpx", "spread", "guards firing"))
    print("-" * 132)
    for f in files:
        stem = os.path.basename(f).split("--")[0].replace(".tiff", "").replace(".tif", "")
        r = diag(plane(f)); out[stem] = r
        g = [k[2:] for k in ("g_subj_small", "g_subj_big", "g_backdrop", "g_far",
                             "g_comp", "g_uniform", "g_nearband") if r[k]]
        print("%-38s %5.1f%% %5.0f%% %5d %5.0f%% %6d %5d %8d %7s  %s"
              % (stem, r["frac"] * 100, r["largest_share"] * 100, r["ncomp"],
                 r["speckle_share"] * 100, r["n_major"], r["nearpop"], r["farpx"],
                 "-" if r["spread"] is None else "%.0f" % r["spread"],
                 ",".join(g) if g else "none"))
    with open(r"D:\strehl-out\V-REVIEW\halo\diag.json", "w") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote diag.json")


if __name__ == "__main__":
    main()
