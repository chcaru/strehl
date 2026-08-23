"""M27 step 5: close the confound in step 4.

`nwide` counts frames within 50% of (peak - min). Decimating the stack estimates
`min` from fewer samples, which would RAISE min, RAISE the half-height threshold
and SHRINK nwide -- reproducing step 4's trend with no change in peak width at
all. Rule 17: name the shared mechanism and break it.

Break it by holding the half-height threshold fixed at the FULL-stack min, so
the only thing varying between rows is the sampling of the peak itself.
"""
import numpy as np, os

SESS = r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
vol = np.load(os.path.join(SESS, "cb_vol.npy"))
n = vol.shape[0]
fmin_full = vol.min(0)

k_full = vol.argmax(0)
fk_full = np.take_along_axis(vol, k_full[None], 0)[0]
c_full = (fk_full - fmin_full) / np.maximum(fk_full, 1e-6)
rel = (c_full > 0.6) & (k_full > 2) & (k_full < n - 3) & (fk_full > np.percentile(fk_full, 50))

print(f"{'step':>5}{'frames':>8}{'median min':>12}{'min/full':>10}"
      f"{'nwide (own min)':>17}{'nwide (FULL min)':>18}")
for step in (1, 2, 3, 4, 6):
    sub = vol[::step]
    fk = sub.max(0)
    own_min = sub.min(0)
    nw_own = (sub >= (own_min + 0.5 * (fk - own_min))[None]).sum(0).astype(np.float32)
    nw_fix = (sub >= (fmin_full + 0.5 * (fk - fmin_full))[None]).sum(0).astype(np.float32)
    print(f"{step:>5}{sub.shape[0]:>8}{float(np.median(own_min[rel])):>12.2f}"
          f"{float(np.median(own_min[rel]))/float(np.median(fmin_full[rel])):>10.4f}"
          f"{float(np.median(nw_own[rel])):>17.2f}{float(np.median(nw_fix[rel])):>18.2f}")

print()
print("If 'min/full' stays ~1.00 the confound is absent and step 4's trend is")
print("real peak under-sampling. The FULL-min column is the confound-free")
print("version regardless.")
print()
print("Fraction of reliable pixels whose peak is resolved by ONE sample or fewer")
print("(the actionable reshoot criterion), using the confound-free threshold:")
for step in (1, 2, 3, 4, 6):
    sub = vol[::step]
    fk = sub.max(0)
    nw_fix = (sub >= (fmin_full + 0.5 * (fk - fmin_full))[None]).sum(0)
    print(f"   step {step} ({sub.shape[0]:>2} frames): {100*float((nw_fix[rel] <= 1).mean()):>6.2f}%")
