"""
M28 / 02 -- What IS the deterministic residual in a clean focus stack?

Script 01 refuted both of its own predictions. At full resolution the negative
control's median |z| is 1.01 -- exactly the noise floor -- so the typical pixel's
frame-to-frame difference in a clean stack IS noise, and defocus disagreement is
confined to a textured minority (frac |z|>5 = 5.5%). And under progressive
lowpass |z| RISES rather than collapsing (1.01 -> 25.07 at d=64), because
averaging d^2 pixels divides the NOISE by d while leaving any DETERMINISTIC
residual in place. So z(d) grows roughly like d wherever a deterministic term
exists, and the sweep is an instrument for measuring that term rather than the
separator it was designed as.

That makes the identity of the deterministic term the question. Three candidates,
and they have different signatures:

  breathing   -1.0 to -1.8% scale drift, frames unaligned here. Displacement
              grows with RADIUS from the scale centre, and accumulates with
              frame SEPARATION.
  defocus     grows with frame separation too, but has no radial dependence.
  outliers    care about neither radius nor separation -- they are one-off.

PRE-REGISTERED PREDICTIONS (written before the first run):

  P5  On the negative control the radial profile of |z| RISES with radius.
      If it does, the deterministic residual is geometric, and the architectural
      consequence is that a robustness mask CANNOT run before alignment.
  P6  On the negative control pairwise |z| rises monotonically with frame
      separation, and does so faster than sqrt(2) (the noise-only expectation
      for differencing two frames).
  P7  On the positive control the separation profile is flatter or saturates,
      because scene evolution is not a smooth accumulating warp.

The pairwise test is the sharper of the two: it needs no estimate of the scale
centre, which fact 5 and M3 disagree about by ~200 px.
"""
import glob, os, json
import numpy as np
import rawpy

BLACK = 512.0
CROP = 3072
D = 8                       # the plateau scale found by script 01
CACHE = os.path.join(os.path.dirname(__file__), "..", "out", "cache")

STACKS = [
    ("109MSDCF",       r"D:\personal\macro\109MSDCF",       1, "negative",     160.0),
    ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles", 1, "intermediate", 1000.0),
    ("foam",           r"D:\personal\macro\foam",           2, "positive",     1000.0),
]


def noise_params(iso):
    g = iso / 436.8
    rn_e = 4.20 if iso < 400 else 1.47
    return g, (rn_e * g) ** 2


def load_green(path):
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        h, w = v.shape
        y0 = ((h - CROP) // 2) & ~1
        x0 = ((w - CROP) // 2) & ~1
        return v[y0:y0 + CROP, x0:x0 + CROP][0::2, 1::2].astype(np.float32) - BLACK


def get_stack(name, folder, step):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{name}.npy")
    if os.path.exists(p):
        return np.load(p)
    files = sorted(glob.glob(os.path.join(folder, "*.ARW")))[::step]
    a = np.stack([load_green(f) for f in files])
    np.save(p, a)
    return a


def area_mean(a, d):
    n, h, w = a.shape
    h2, w2 = (h // d) * d, (w // d) * d
    return a[:, :h2, :w2].reshape(n, h2 // d, d, w2 // d, d).mean(axis=(2, 4))


def run(name, folder, step, role, iso, out):
    g, rn2 = noise_params(iso)
    raw = get_stack(name, folder, step)
    n = len(raw)
    print(f"\n=== {name}  ({role})  {n} frames ===", flush=True)

    med = np.median(raw.reshape(n, -1), axis=1)
    gain = med / np.median(med)
    a = area_mean(raw / gain[:, None, None], D)
    del raw

    ref = np.median(a, axis=0)
    sig = np.sqrt(np.maximum(g * np.maximum(ref, 0) + rn2, 1e-6)) / D
    z = np.abs(a - ref) / sig

    # ---- P5: radial profile at the plateau scale -----------------------------
    h, w = ref.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - (h - 1) / 2.0) ** 2 + (xx - (w - 1) / 2.0) ** 2)
    rmax = r.max()
    edges = np.linspace(0, rmax, 9)
    zmed = np.median(z, axis=0)
    # Local gradient of the reference: breathing residual scales with |grad|*r,
    # so the radial trend must survive gradient normalisation to be geometric.
    gy, gx = np.gradient(ref)
    grad = np.sqrt(gy ** 2 + gx ** 2)
    radial, radial_n = [], []
    for i in range(8):
        m = (r >= edges[i]) & (r < edges[i + 1])
        radial.append(float(np.median(zmed[m])))
        radial_n.append(float(np.median(zmed[m] / np.maximum(grad[m], 1e-3))))
    print("    radial |z|      " + " ".join(f"{v:7.2f}" for v in radial))
    print("    per unit |grad| " + " ".join(f"{v:7.3f}" for v in radial_n))
    print(f"    outer/inner  raw {radial[-1]/radial[0]:6.2f}   "
          f"grad-normalised {radial_n[-1]/radial_n[0]:6.2f}")

    # ---- P6: pairwise |z| vs frame separation --------------------------------
    sig_pair = sig * np.sqrt(2.0)
    seps, pair = [], []
    for dk in [1, 2, 4, 8, 16]:
        if dk >= n:
            break
        d_ = np.abs(a[dk:] - a[:-dk]) / sig_pair
        seps.append(dk)
        pair.append(float(np.median(d_)))
    print("    separation      " + " ".join(f"{v:7d}" for v in seps))
    print("    pairwise |z|    " + " ".join(f"{v:7.2f}" for v in pair))
    print(f"    slope (last/first) {pair[-1]/pair[0]:6.2f}  over {seps[-1]}x separation")

    # ---- gain trajectory: monotone drift or spikes? --------------------------
    dg = np.abs(np.diff(gain))
    print(f"    gain p-p {100*(gain.max()-gain.min()):6.2f}%   "
          f"median step {100*np.median(dg):.3f}%   max step {100*dg.max():.3f}%   "
          f"max/median step {dg.max()/max(np.median(dg),1e-9):6.1f}")

    out[name] = dict(role=role, n=n, radial=radial, radial_grad=radial_n,
                     seps=seps, pair=pair,
                     gain=[round(float(x), 5) for x in gain])


if __name__ == "__main__":
    out = {}
    for name, folder, step, role, iso in STACKS:
        run(name, folder, step, role, iso, out)
    with open(os.path.join(os.path.dirname(__file__), "..", "out",
                           "02-identity.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("\n" + "=" * 78)
    print("P5: radial rise on the NEGATIVE control => residual is geometric")
    print("    => a robustness mask cannot run before alignment.")
    print("P6: pairwise |z| >> sqrt(2)-flat => accumulating warp, not noise.")
    print("=" * 78)
