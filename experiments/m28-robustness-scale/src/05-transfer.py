"""
M28 / 05 -- Does the plant-calibrated detector fire on the REAL outliers?

Script 04 measured sensitivity against a planted displacement. A plant can only
prove that a detector responds to the thing that was planted. This applies the
same detector, at a threshold calibrated ENTIRELY on the clean stack, to two
stacks with known-real disturbance, and reports how often it fires.

  109MSDCF        clean. Calibration source. Must fire at the nominal rate,
                  because that is the definition of the threshold.
  coffee-bubbles  bubbles drift and burst. Should fire above nominal.
  foam            rejected from the corpus because the scene visibly evolves.
                  Should fire far above nominal.

CONFOUND, stated up front: the three stacks differ in ISO, subject and contrast
as well as in stability, so this is a transfer test with a real scene confound.
It cannot separate "more disturbance" from "more contrast". The guard is that
|z| is noise-normalised, so ISO is handled by construction, and that the
DIRECTION of the ordering is predicted in advance from what the stacks are.

PRE-REGISTERED PREDICTION:

  P14  flagged(109) < flagged(coffee-bubbles) < flagged(foam), with 109 at the
       nominal rate. Any other ordering falsifies the detector as a transferable
       instrument.
"""
import os, json
import numpy as np

CACHE = os.path.join(os.path.dirname(__file__), "..", "out", "cache")
D, W = 8, 128
STACKS = [("109MSDCF", 160.0, "clean / calibration"),
          ("coffee-bubbles", 1000.0, "bubbles move"),
          ("foam", 1000.0, "scene evolves")]


def noise_params(iso):
    g = iso / 436.8
    return g, ((4.20 if iso < 400 else 1.47) * g) ** 2


def area_mean(a, d):
    n, h, w = a.shape
    h2, w2 = (h // d) * d, (w // d) * d
    return a[:, :h2, :w2].reshape(n, h2 // d, d, w2 // d, d).mean(axis=(2, 4))


def tiles(name, iso):
    raw = np.load(os.path.join(CACHE, f"{name}.npy"))
    n = len(raw)
    g, rn2 = noise_params(iso)
    gain = raw.reshape(n, -1).mean(axis=1)
    raw = raw / (gain / np.median(gain))[:, None, None]
    a = area_mean(raw, D)
    ref = (a[:-2] + a[2:]) / 2.0
    sig = np.sqrt(np.maximum(g * np.maximum(ref, 0) + rn2, 1e-6)) / D
    z = np.abs(a[1:-1] - ref) / (sig * np.sqrt(1.5))
    tb, nt = W // D, a.shape[1] // (W // D) // 1
    ny = z.shape[1] // tb
    t = z[:, :ny * tb, :ny * tb].reshape(z.shape[0], ny, tb, ny, tb)
    return np.median(t, axis=(2, 4)).ravel(), n


print(f"detector: adjacent-frame reference, scale d={D}, tile {W} green px "
      f"({W*2} sensor px)\n")
cal, n_cal = tiles("109MSDCF", 160.0)
print(f"pure-noise expectation for median|z| is 0.6745 (median of a half-normal)")
print(f"calibration stack 109MSDCF: {len(cal)} tiles over {n_cal-2} interior frames")
print(f"    median tile |z| {np.median(cal):.4f}  = {np.median(cal)/0.6745:.3f}x "
      f"the pure-noise expectation\n")
thr = {p: float(np.percentile(cal, 100 - p)) for p in (5.0, 1.0, 0.1)}
print("thresholds from the CLEAN stack only: "
      + "   ".join(f"FPR{p}% = {t:.3f}" for p, t in thr.items()) + "\n")

out = {"thr": thr, "stacks": {}}
print(f"{'stack':16s} {'frames':>7s} {'tiles':>7s} {'med|z|':>8s} {'/noise':>7s}"
      + "".join(f"{'flag@'+str(p)+'%':>12s}" for p in (5.0, 1.0, 0.1)))
for name, iso, why in STACKS:
    t, n = tiles(name, iso)
    rates = {p: float((t > v).mean()) for p, v in thr.items()}
    out["stacks"][name] = dict(why=why, n=n, tiles=len(t),
                               med=float(np.median(t)), rates=rates)
    print(f"{name:16s} {n:7d} {len(t):7d} {np.median(t):8.3f} "
          f"{np.median(t)/0.6745:7.3f}"
          + "".join(f"{100*rates[p]:11.2f}%" for p in (5.0, 1.0, 0.1))
          + f"   {why}")

with open(os.path.join(os.path.dirname(__file__), "..", "out",
                       "05-transfer.json"), "w") as fh:
    json.dump(out, fh, indent=1)

r = [out["stacks"][s]["rates"][1.0] for s, _, _ in STACKS]
print(f"\nP14 ordering 109 < bubbles < foam at FPR 1%: "
      f"{'HOLDS' if r[0] < r[1] < r[2] else 'FAILS'}   "
      f"({100*r[0]:.2f}% < {100*r[1]:.2f}% < {100*r[2]:.2f}%)")
