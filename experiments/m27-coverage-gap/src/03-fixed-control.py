"""M27 step 3: fixed control population + continuous blind detectors.

Step 2's defects, again mine: `nwide` is an integer so its median quantises to
2/3/4/8/14 and the ratios are unreadable; and the control group was defined
relative to the gap, so it drifted to a different (flatter-peaked) population as
the band widened -- its own nwide went 3 -> 14.

Fixed here: one control band, defined once, used for every gap width; and two
continuous blind detectors.
"""
import numpy as np, os

SESS = r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
vol = np.load(os.path.join(SESS, "cb_vol.npy"))
n = vol.shape[0]
K0 = 12           # gap start
CTL_LO, CTL_HI = 26, 34   # fixed control band, never touched by any gap tested


def stats(v):
    k = v.argmax(0)
    fk = np.take_along_axis(v, k[None], 0)[0]
    fmin = v.min(0)
    km1, kp1 = np.clip(k - 1, 0, v.shape[0] - 1), np.clip(k + 1, 0, v.shape[0] - 1)
    fm = np.take_along_axis(v, km1[None], 0)[0]
    fp = np.take_along_axis(v, kp1[None], 0)[0]
    den = fm - 2 * fk + fp
    ok = np.abs(den) > 1e-6
    delta = np.clip(np.where(ok, 0.5 * (fm - fp) / np.where(ok, den, 1), 0.0), -0.5, 0.5)
    # continuous, blind: curvature at the peak normalised by the peak's own height
    curv = (2 * fk - fm - fp) / np.maximum(fk - fmin, 1e-6)
    return k, delta, curv


k_full, _, _ = stats(vol)
fk_full = np.take_along_axis(vol, k_full[None], 0)[0]
c_full = (fk_full - vol.min(0)) / np.maximum(fk_full, 1e-6)
reliable = (c_full > 0.6) & (k_full > 2) & (k_full < n - 3) & (fk_full > np.percentile(fk_full, 50))

ctl = reliable & (k_full >= CTL_LO) & (k_full < CTL_HI)
print(f"reliable: {int(reliable.sum()):,}   FIXED control band [{CTL_LO},{CTL_HI}): "
      f"{int(ctl.sum()):,} px (same for every row)")
print()
print(f"{'gapW':>5}{'pos n':>9}"
      f"{'curv pos':>10}{'curv ctl':>10}{'ratio':>8}{'null':>8}{'excess':>9}   "
      f"{'|d| pos':>8}{'|d| ctl':>8}{'ratio':>8}{'null':>8}{'excess':>9}")
for gapW in (1, 2, 4, 6, 8, 12):
    pos = reliable & (k_full >= K0) & (k_full < K0 + gapW)
    if pos.sum() < 500:
        print(f"{gapW:>5}{int(pos.sum()):>9,}  too few"); continue
    keep = np.ones(n, bool); keep[K0:K0 + gapW] = False
    _, d_g, cv_g = stats(vol[keep])
    keepN = np.ones(n, bool); keepN[n - gapW:] = False       # same n removed, harmless region
    _, d_0, cv_0 = stats(vol[keepN])

    def med(a, m):
        return float(np.median(a[m]))
    cg = med(cv_g, pos) / med(cv_g, ctl)
    c0 = med(cv_0, pos) / med(cv_0, ctl)
    dg = med(np.abs(d_g), pos) / med(np.abs(d_g), ctl)
    d0 = med(np.abs(d_0), pos) / med(np.abs(d_0), ctl)
    print(f"{gapW:>5}{int(pos.sum()):>9,}"
          f"{med(cv_g,pos):>10.4f}{med(cv_g,ctl):>10.4f}{cg:>8.4f}{c0:>8.4f}{cg-c0:>9.4f}   "
          f"{med(np.abs(d_g),pos):>8.4f}{med(np.abs(d_g),ctl):>8.4f}{dg:>8.4f}{d0:>8.4f}{dg-d0:>9.4f}")

print()
print("curv = (2f[k]-f[k-1]-f[k+1]) / (f[k]-f_min): peak sharpness, blind, continuous.")
print("|d|  = |parabola vertex offset| from the argmax sample, blind, in [0,0.5].")
print("null = same number of frames removed from the far end of the stack, where")
print("       no pixel in either group peaks -- isolates 'frames removed' from")
print("       'YOUR frames removed'. excess = ratio - null.")
