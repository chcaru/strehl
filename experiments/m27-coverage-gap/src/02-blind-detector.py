"""M27 step 2: coverage-gap detection, with a properly matched null for every gap
width and a detector that uses ONLY the reduced stack.

Step 1 had two defects, both mine:
  * the peak-ratio detector divided by the full-stack peak, which does not exist
    at inference time -- an oracle, not a detector;
  * only the gapW=4 row had a band-width-matched null.
Both are fixed here.
"""
import numpy as np, os

SESS = r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
vol = np.load(os.path.join(SESS, "cb_vol.npy"))
n, H, W = vol.shape
K0 = 12


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
    # BLIND detector: how many retained frames sit within 50% of the peak height.
    # A well-sampled peak is resolved by several; an under-sampled one by ~1.
    half = fmin + 0.5 * (fk - fmin)
    nwide = (v >= half[None]).sum(0).astype(np.float32)
    return k, delta, fk, fmin, nwide


k_full, d_full, f_full, min_full, nw_full = stats(vol)
c_full = (f_full - min_full) / np.maximum(f_full, 1e-6)
reliable = (c_full > 0.6) & (k_full > 2) & (k_full < n - 3) & (f_full > np.percentile(f_full, 50))
print(f"reliable pixels: {int(reliable.sum()):,} ({100*reliable.mean():.1f}%)")
print()
print("Each row's NULL removes NO frames but uses the SAME band width, so the")
print("positive/control groups are identical between a row and its own null.")
print()
hdr = (f"{'gapW':>5}{'pos n':>9}{'ctl n':>9}"
       f"{'nwide pos':>11}{'nwide ctl':>11}{'ratio':>8}{'NULL ratio':>12}{'excess':>9}")
print(hdr)
for gapW in (1, 2, 4, 6, 8, 12):
    band = (k_full >= K0) & (k_full < K0 + gapW)
    pos = reliable & band
    ctl = reliable & ~band & (np.abs(k_full - (K0 + gapW / 2)) > gapW + 2)
    if pos.sum() < 500 or ctl.sum() < 500:
        print(f"{gapW:>5}{int(pos.sum()):>9,}{int(ctl.sum()):>9,}   too few"); continue

    keep = np.ones(n, bool); keep[K0:K0 + gapW] = False
    _, _, _, _, nw_gap = stats(vol[keep])
    # null: same number of frames removed, but from a region no pixel in either
    # group peaks in -- so the axis is shortened identically without touching
    # anyone's peak. This isolates "frames removed" from "YOUR frames removed".
    keepN = np.ones(n, bool); keepN[n - gapW:] = False
    _, _, _, _, nw_null = stats(vol[keepN])

    a = float(np.median(nw_gap[pos])) / float(np.median(nw_gap[ctl]))
    b = float(np.median(nw_null[pos])) / float(np.median(nw_null[ctl]))
    print(f"{gapW:>5}{int(pos.sum()):>9,}{int(ctl.sum()):>9,}"
          f"{float(np.median(nw_gap[pos])):>11.3f}{float(np.median(nw_gap[ctl])):>11.3f}"
          f"{a:>8.4f}{b:>12.4f}{a-b:>9.4f}")

print()
print("nwide = count of retained frames within 50% of the peak height (BLIND:")
print("uses only the reduced stack). Lower = the peak is resolved by fewer")
print("samples = under-sampled focus axis.")
