"""Commission the gradient-kurtosis statistic BEFORE letting it vote.

Four plants, on real merge tiles:

 K1 IDENTITY      ratio must be exactly 1.000.
 K2 NOISE NULL    add Gaussian noise to one arm at the measured sigma gap.
                  Pure Gaussian noise has gradient kurtosis 3.245 (Rayleigh),
                  so a noisier arm should be pulled DOWN, not up. If the ratio
                  RISES the statistic is just re-reading the noise gap.
 K3 PLATEAU PLANT quantise one arm into piecewise-constant patches, i.e. plant
                  exactly the artefact the statistic is meant to catch. If the
                  ratio does not rise sharply, the statistic is not evidence.
 K4 RESAMPLE CONFOUND -- the load-bearing one. The merge arm is produced by
                  cropping the field to s and resampling BACK to full size, so
                  its pixels are an interpolation of a coarser grid and are
                  intrinsically smoother at the pixel scale. argmax gets no
                  such treatment. Put the argmax arm through that same
                  geometric round trip alone, with NO merging, and see how much
                  of the 4x it reproduces. Anything it reproduces is not
                  invented structure, it is resampling.
"""
import pathlib, sys
import numpy as np, tifffile, cv2

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import sigma_immerkaer  # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
rng = np.random.default_rng(20240611)


def gk(a):
    gx = np.diff(a, axis=1)[:-1, :]; gy = np.diff(a, axis=0)[:, :-1]
    g = np.hypot(gx, gy).ravel()
    return float((((g - g.mean()) / g.std()) ** 4).mean())


def roundtrip(a, s):
    """Exactly the merge's geometry: crop field to s, resample back to size."""
    h, w = a.shape
    small = cv2.resize(a, (int(round(w*s)), int(round(h*s))), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)


def plateaus(a, n=24):
    """Piecewise-constant Voronoi patches: the artefact, planted."""
    h, w = a.shape
    cy = rng.integers(0, h, n); cx = rng.integers(0, w, n)
    yy, xx = np.mgrid[0:h, 0:w]
    d = (yy[None]-cy[:, None, None])**2 + (xx[None]-cx[:, None, None])**2
    lab = d.argmin(0)
    out = np.empty_like(a)
    for k in range(n):
        m = lab == k
        if m.any(): out[m] = a[m].mean()
    return out


SUBJ = {"bee-3-cpl": 0.9355, "tweezers-cpl": 0.9792, "flat-on-ruler-cpl": 0.9707}
print(f"{'subject':<19}{'K1 ident':>10}{'K2 noise':>10}{'K3 plate':>10}"
      f"{'K4 resamp':>11}{'OBSERVED':>10}")
print("-" * 70)
for subj, s in SUBJ.items():
    gm = tifffile.imread(str(R/subj/"merge.tif"))[:, :, 1].astype(np.float64)
    ga = tifffile.imread(str(R/subj/"argmax.tif"))[:, :, 1].astype(np.float64)
    t  = gm[1400:2200, 800:1600]
    ta = ga[1400:2200, 800:1600]
    sm, sa = sigma_immerkaer(t), sigma_immerkaer(ta)
    extra = np.sqrt(max(sa**2 - sm**2, 0.0))
    k0 = gk(t)
    k1 = gk(t) / k0
    k2 = gk(t + rng.normal(0, extra, t.shape)) / k0
    k3 = gk(plateaus(t)) / k0
    k4 = k0 / gk(roundtrip(ta, s))          # argmax native / argmax round-tripped
    print(f"{subj:<19}{k1:>10.3f}{k2:>10.3f}{k3:>10.3f}{k4:>11.3f}", end="")
    print(f"{gk(ta)/gk(t):>10.3f}")
print("-" * 70)
print("K4 column: gk(argmax native) / gk(argmax after the merge's OWN geometric")
print("round trip). This is the argmax-vs-argmax ratio the resampling alone buys.")
