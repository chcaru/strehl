"""M27 step 1: is a focus-bracket coverage gap detectable from the stack alone?

Ground truth by construction: remove a contiguous block of frames and the pixels
whose best frame was inside that block have provably lost their focus coverage.

The confound (rule 17): the positive group is defined by depth, so it is also a
specific *region* of the subject with its own texture. The null -- removing ZERO
frames and running the identical comparison on the identical groups -- measures
that confound directly. A gap is only detected if separation exceeds the null.
"""
import numpy as np, os

SESS = r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
vol = np.load(os.path.join(SESS, "cb_vol.npy"))
n, H, W = vol.shape
print(f"volume {vol.shape}")

def peak_stats(v):
    """argmax, parabola vertex offset delta in [-0.5,0.5], peak value, peak contrast."""
    k = v.argmax(0)
    idx = np.arange(v.shape[0])[:, None, None]
    fk = np.take_along_axis(v, k[None], 0)[0]
    km1 = np.clip(k - 1, 0, v.shape[0] - 1)
    kp1 = np.clip(k + 1, 0, v.shape[0] - 1)
    fm = np.take_along_axis(v, km1[None], 0)[0]
    fp = np.take_along_axis(v, kp1[None], 0)[0]
    den = (fm - 2 * fk + fp)
    delta = np.where(np.abs(den) > 1e-6, 0.5 * (fm - fp) / np.where(np.abs(den) > 1e-6, den, 1), 0.0)
    delta = np.clip(delta, -0.5, 0.5)
    contrast = (fk - v.min(0)) / np.maximum(fk, 1e-6)
    return k, delta, fk, contrast

k_full, d_full, f_full, c_full = peak_stats(vol)

# Restrict to pixels whose FULL-stack peak is reliable, so "true argmax" means something.
# Interior, high contrast, and a clear peak. This is the rule-17 guard: a noisy pixel
# would otherwise be assigned a random true-argmax and then flagged for noise reasons.
reliable = (c_full > 0.6) & (k_full > 2) & (k_full < n - 3) & (f_full > np.percentile(f_full, 50))
print(f"reliable pixels: {int(reliable.sum()):,} of {reliable.size:,} "
      f"({100*reliable.mean():.1f}%)")

K0 = 12   # gap starts here -- inside the dense argmax band
print()
print(f"{'gapW':>5}{'kept':>6}{'pos n':>9}{'ctl n':>9}"
      f"{'|d| pos':>9}{'|d| ctl':>9}{'sep':>7}"
      f"{'peak pos':>10}{'peak ctl':>10}{'ratio':>8}")
rows = []
for gapW in (0, 1, 2, 4, 6, 8):
    keep = np.ones(n, bool)
    if gapW:
        keep[K0:K0 + gapW] = False
    red = vol[keep]
    k_r, d_r, f_r, c_r = peak_stats(red)

    inblock = (k_full >= K0) & (k_full < K0 + gapW) if gapW else \
              (k_full >= K0) & (k_full < K0 + 4)      # null uses the same-sized band
    pos = reliable & inblock
    ctl = reliable & ~inblock & (np.abs(k_full - (K0 + max(gapW, 4) / 2)) > max(gapW, 4))
    if pos.sum() < 500 or ctl.sum() < 500:
        print(f"{gapW:>5}{int(keep.sum()):>6}{int(pos.sum()):>9,}{int(ctl.sum()):>9,}  too few")
        continue
    dp, dc = float(np.median(np.abs(d_r[pos]))), float(np.median(np.abs(d_r[ctl])))
    # peak value normalised by the pixel's own full-stack peak: how much was lost
    rp = float(np.median(f_r[pos] / f_full[pos]))
    rc = float(np.median(f_r[ctl] / f_full[ctl]))
    rows.append((gapW, dp, dc, rp, rc))
    print(f"{gapW:>5}{int(keep.sum()):>6}{int(pos.sum()):>9,}{int(ctl.sum()):>9,}"
          f"{dp:>9.4f}{dc:>9.4f}{dp-dc:>7.4f}"
          f"{rp:>10.4f}{rc:>10.4f}{rp/rc:>8.4f}")

print()
print("NULL is the gapW=0 row: identical groups, identical detector, no frames removed.")
print("Any separation there is the depth-band/texture confound, not gap detection.")
