"""Truth-referenced synthetic focus stacks folded by the production BandMerge.

usage: synth-stack.py TRUTH_LIN.tif OUT_DIR y x size N SCENE [--run ARM_ENV...]

TRUTH is a near-noise-free real image (the mean of 24 frames of a fixed-focus
burst, scene-linear). Its luma crop, scaled to sensor DN, is the all-in-focus
truth T. SCENE sets the depth map d(x) in frame units:
  tilt  : d rises linearly left to right across the stack
  flat  : d = N/2 everywhere (detail seen by several frames: the plateau case)
  step  : tilt background with a nearer square occluder at depth N/5
Frame i is T blurred by a Gaussian of sigma = sqrt(0.7^2 + (0.8*|i - d|)^2)
(depth-varying, interpolated between precomputed blur levels in log sigma),
plus Gaussian noise of variance gain*S + read^2 (gain 1.0 DN/e, read 3 DN).
The step occluder is composited as a layer: in each frame it is blurred by its
own sigma and alpha-blended over the blurred background with a blurred mask.

Each arm (an environment assignment such as STREHL_PYRAMID_ENSEMBLE=1) folds
the same frames through iq-synth-merge. Reported: error power against T in
fine / mid / coarse bands, over flat and textured truth tiles, plus the best
single frame per pixel (oracle) and the plain mean as references.
"""
import os
import subprocess
import sys
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, uniform_filter

HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "target",
                       "iq-synth", "release", "iq-synth-merge.exe")
SIGMAS = np.array([0.7, 1.0, 1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0, 22.0, 32.0])
GAIN, READ = 1.0, 3.0


def blur_levels(img):
    return np.stack([gaussian_filter(img, s) for s in SIGMAS])


def at_sigma(levels, sig):
    ls = np.log(SIGMAS)
    t = np.clip(np.interp(np.log(np.clip(sig, SIGMAS[0], SIGMAS[-1])), ls, np.arange(len(SIGMAS))),
                0, len(SIGMAS) - 1)
    lo = np.floor(t).astype(int)
    hi = np.minimum(lo + 1, len(SIGMAS) - 1)
    f = t - lo
    yy, xx = np.indices(sig.shape)
    return (1 - f) * levels[lo, yy, xx] + f * levels[hi, yy, xx]


def sigma_of(i, d):
    return np.sqrt(0.7 ** 2 + (0.8 * np.abs(i - d)) ** 2)


def bands(y):
    b3, b9, b33 = (uniform_filter(y, k) for k in (3, 9, 33))
    return {"fine": y - b3, "mid": b3 - b9, "coarse": b9 - b33}


def tiles(x, t=32):
    h, w = x.shape[0] // t * t, x.shape[1] // t * t
    return x[:h, :w].reshape(h // t, t, w // t, t).mean(axis=(1, 3))


def main():
    truth_path, out = sys.argv[1], sys.argv[2]
    y0, x0, size, n = (int(v) for v in sys.argv[3:7])
    scene = sys.argv[7]
    arms = sys.argv[sys.argv.index("--run") + 1:] if "--run" in sys.argv else []
    os.makedirs(out, exist_ok=True)
    a = tifffile.imread(truth_path).astype(np.float64)[y0:y0 + size, x0:x0 + size]
    T = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])
    T = T / np.quantile(T, 0.99) * 3000.0
    # Texture contrast (CONTRAST env, default 1) about a smooth base, and a
    # genuinely smooth top third (no texture at all) for the noise-only case.
    smooth = gaussian_filter(T, 24)
    T = smooth + float(os.environ.get("CONTRAST", "1")) * (T - smooth)
    T[: T.shape[0] // 3] = smooth[: T.shape[0] // 3]
    h, w = T.shape
    xx = np.arange(w)[None, :].repeat(h, 0)
    rng = np.random.default_rng(11)
    if scene == "flat":
        d = np.full((h, w), n / 2.0)
    else:
        d = (n - 1) * xx / (w - 1)
    lev = blur_levels(T)
    mask = None
    if scene == "step":
        mask = np.zeros((h, w))
        mask[h // 4:3 * h // 4, w // 4:w // 2] = 1.0
        dn = n / 5.0
        fg = np.roll(T, (h // 3, w // 3), (0, 1))  # a different texture for the occluder
        flev = blur_levels(fg)
        mlev = blur_levels(mask)
        Ttrue = np.where(mask > 0.5, fg, T)
    else:
        Ttrue = T
    oracle = np.zeros((h, w))
    best = np.full((h, w), np.inf)
    total = np.zeros((h, w))
    for i in range(n):
        f = at_sigma(lev, sigma_of(i, d))
        if mask is not None:
            s = np.full((h, w), sigma_of(i, dn))
            al = at_sigma(mlev, s)
            f = al * at_sigma(flev, s) + (1 - al) * f
            dist = np.where(mask > 0.5, abs(i - dn), np.abs(i - d))
        else:
            dist = np.abs(i - d)
        var = GAIN * np.maximum(f, 0) + READ ** 2
        noisy = f + rng.normal(0, 1, f.shape) * np.sqrt(var)
        noisy.astype("<f4").tofile(os.path.join(out, f"frame-{i:03d}.f32"))
        var.astype("<f4").tofile(os.path.join(out, f"var-{i:03d}.f32"))
        take = dist < best
        oracle[take] = noisy[take]
        best = np.minimum(best, dist)
        total += noisy
    refs = {"oracle-frame": oracle, "plain-mean": total / n}
    tb = bands(Ttrue)
    tex = tiles(tb["mid"] ** 2)
    smooth_rows = np.zeros(tex.shape, bool)
    smooth_rows[: tex.shape[0] // 3 - 2] = True
    rest = ~smooth_rows
    q50 = np.quantile(tex[rest], 0.5)
    cls = {"smooth": smooth_rows, "weaktex": rest & (tex <= q50), "strongtex": rest & (tex > q50)}
    if mask is not None:
        near = tiles((np.abs(uniform_filter(mask, 41) - 0.5) < 0.45).astype(float)) > 0.5
        cls["boundary"] = near

    def score(name, est):
        eb = bands(est)
        parts = []
        for band in ("fine", "mid", "coarse"):
            err = tiles((eb[band] - tb[band]) ** 2)
            parts.append(band + " " + " ".join(f"{c}={err[m].mean():9.3f}" for c, m in cls.items()))
        print(f"  {name:34s} " + " | ".join(parts))

    print(f"scene {scene} N {n} size {size}  (error power vs truth, DN^2)")
    for name, est in refs.items():
        score(name, est)
    for arm in arms:
        env = dict(os.environ)
        for kv in arm.split():
            if "=" in kv:
                k, v = kv.split("=", 1)
                env[k] = v
        subprocess.run([HARNESS, out, str(w), str(h), str(n)], env=env, check=True,
                       stderr=subprocess.DEVNULL)
        est = np.fromfile(os.path.join(out, "merged.f32"), "<f4").reshape(h, w)
        score(arm, est)


if __name__ == "__main__":
    main()
