"""
M28 / 03 -- Close two confounds script 02 opened.

CONFOUND A -- the gradient normalisation may be an artefact of its own divisor.
Script 02 divided |z| by local |grad| to test whether the radial rise is
geometric. But |z| has a floor of ~1 from noise, and |grad| falls toward the
frame edge where there is less subject, so z/|grad| must rise with radius
whether or not anything geometric is happening. The evidence that it IS an
artefact is already in the output: on `coffee-bubbles` the raw radial profile
FALLS 0.21x while the gradient-normalised one RISES 9.25x. Both cannot be right.

The correct test is the breathing PREDICTION, not a normalisation. A scale drift
of s per frame displaces a pixel at radius r by s*r, and a displacement dx
produces a residual |grad|*dx. So breathing predicts

        |z| proportional to |grad| * r

and the falsifiable statement is that z / (|grad| * r) is FLAT in r. Restricting
each radial bin to its own high-gradient pixels keeps the populations comparable
and keeps the divisor away from zero.

CONFOUND B -- my per-frame gain fit disagrees with M24 by 4.7x.
Script 01 fitted 4.28% peak-to-peak gain on `109MSDCF`; M24 measured 0.91% on the
same stack. M24 used the full-frame green mean; script 01 used the median of a
centred 3072 px crop of one green sublattice. The crop is where the SUBJECT is,
so as focus sweeps, subject contrast changes and a median over that crop absorbs
FOCUS signal into what it calls gain. If so, the merge's photometric fit must be
estimated on low-gradient regions, which is a design constraint M24 did not
state -- M24 established THAT gain must be fitted, not HOW.

PRE-REGISTERED PREDICTIONS:

  P8   z / (|grad| * r) is flat within +/-30% on the negative control.
       If it is, breathing accounts for the residual and the architectural
       consequence stands: no robustness mask before alignment.
  P9   Fitting gain on low-gradient pixels only moves 109MSDCF's peak-to-peak
       toward M24's 0.91%. If it does, the fit estimator is the confound.
"""
import glob, os, json
import numpy as np
import rawpy

BLACK, CROP, D = 512.0, 3072, 8
CACHE = os.path.join(os.path.dirname(__file__), "..", "out", "cache")
STACKS = [
    ("109MSDCF",       r"D:\personal\macro\109MSDCF",       1, "negative",     160.0),
    ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles", 1, "intermediate", 1000.0),
    ("foam",           r"D:\personal\macro\foam",           2, "positive",     1000.0),
]


def noise_params(iso):
    g = iso / 436.8
    return g, ((4.20 if iso < 400 else 1.47) * g) ** 2


def get_stack(name):
    return np.load(os.path.join(CACHE, f"{name}.npy"))


def area_mean(a, d):
    n, h, w = a.shape
    h2, w2 = (h // d) * d, (w // d) * d
    return a[:, :h2, :w2].reshape(n, h2 // d, d, w2 // d, d).mean(axis=(2, 4))


for name, folder, step, role, iso in STACKS:
    g, rn2 = noise_params(iso)
    raw = get_stack(name)
    n = len(raw)
    print(f"\n=== {name}  ({role})  {n} frames ===")

    # ---- CONFOUND B: three gain estimators -----------------------------------
    flat = raw.reshape(n, -1)
    ref0 = np.median(raw, axis=0)
    gy0, gx0 = np.gradient(ref0)
    grad0 = np.sqrt(gy0 ** 2 + gx0 ** 2)
    lowg = (grad0 < np.percentile(grad0, 25)).ravel()
    ests = {
        "median, all px":  np.median(flat, axis=1),
        "mean,   all px":  flat.mean(axis=1),
        "median, low-grad": np.median(flat[:, lowg], axis=1),
        "mean,   low-grad": flat[:, lowg].mean(axis=1),
    }
    print("    gain estimator          p-p %    max step %")
    gains = {}
    for k, v in ests.items():
        gg = v / np.median(v)
        gains[k] = gg
        print(f"      {k:20s} {100*(gg.max()-gg.min()):7.2f}  {100*np.abs(np.diff(gg)).max():9.3f}")

    # ---- CONFOUND A: the breathing prediction --------------------------------
    gain = gains["mean,   low-grad"]
    a = area_mean(raw / gain[:, None, None], D)
    del raw
    ref = np.median(a, axis=0)
    sig = np.sqrt(np.maximum(g * np.maximum(ref, 0) + rn2, 1e-6)) / D
    zmed = np.median(np.abs(a - ref) / sig, axis=0)

    gy, gx = np.gradient(ref)
    grad = np.sqrt(gy ** 2 + gx ** 2)
    h, w = ref.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - (h - 1) / 2.0) ** 2 + (xx - (w - 1) / 2.0) ** 2)
    edges = np.linspace(0, r.max(), 9)

    print("    bin        r     n_hi    |z|   |grad|   z/(grad*r)")
    prof = []
    for i in range(8):
        m = (r >= edges[i]) & (r < edges[i + 1])
        if m.sum() < 50:
            continue
        gm = grad[m]
        hi = gm >= np.percentile(gm, 60)          # comparable populations per bin
        rr = max(np.median(r[m][hi]), 1e-6)
        zz = np.median(zmed[m][hi])
        gg = np.median(gm[hi])
        prof.append(float(zz / (gg * rr)))
        print(f"     {i}   {rr:7.1f}  {hi.sum():6d} {zz:7.2f}  {gg:7.2f}   {prof[-1]:10.5f}")
    p = np.array(prof[1:])                        # bin 0 has r ~ 0; ratio undefined
    print(f"    z/(grad*r) over bins 1-7:  max/min {p.max()/p.min():5.2f}   "
          f"spread about median {100*np.abs(p/np.median(p)-1).max():5.1f}%")
    print(f"    P8 predicts flat within +/-30%: "
          f"{'HOLDS' if np.abs(p/np.median(p)-1).max() <= 0.30 else 'FAILS'}")
