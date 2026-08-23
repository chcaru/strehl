"""M27 step 4: is UNIFORM under-sampling detectable within-stack?

Steps 1-3 removed a contiguous block -- a HOLE in the bracket. The commoner real
failure is different: focus steps that are uniformly too coarse. Then the whole
axis is compressed and there is no well-sampled region to compare against.

If the blind detectors cannot see uniform under-sampling, the reshoot advisor
cannot be built from the stack alone: it needs a PHYSICAL prediction of the
peak width, i.e. the optical model.
"""
import numpy as np, os

SESS = r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
vol = np.load(os.path.join(SESS, "cb_vol.npy"))
n = vol.shape[0]


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
    curv = (2 * fk - fm - fp) / np.maximum(fk - fmin, 1e-6)
    half = fmin + 0.5 * (fk - fmin)
    nwide = (v >= half[None]).sum(0).astype(np.float32)
    return k, delta, curv, fk, nwide


k_full, _, _, fk_full, _ = stats(vol)
c_full = (fk_full - vol.min(0)) / np.maximum(fk_full, 1e-6)
rel = (c_full > 0.6) & (k_full > 2) & (k_full < n - 3) & (fk_full > np.percentile(fk_full, 50))
print(f"reliable: {int(rel.sum()):,}")
print()
print("Decimating the WHOLE stack -- uniform under-sampling, no hole.")
print("Every pixel is equally affected, so there is no internal control by")
print("construction. The question is whether the ABSOLUTE detector value moves.")
print()
print(f"{'step':>5}{'frames':>8}{'median curv':>13}{'median |d|':>12}{'median nwide':>14}"
      f"{'orig-frame gap':>16}")
for step in (1, 2, 3, 4, 6):
    sub = vol[::step]
    _, d, cv, _, nw = stats(sub)
    print(f"{step:>5}{sub.shape[0]:>8}{float(np.median(cv[rel])):>13.4f}"
          f"{float(np.median(np.abs(d[rel]))):>12.4f}{float(np.median(nw[rel])):>14.2f}"
          f"{step*2:>16d}")

print()
print("(orig-frame gap = focus steps between retained frames, in original")
print(" coffee-bean frame units; the volume was already every-2nd-frame.)")
