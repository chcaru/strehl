"""
M29 / 01 -- Is there static multiplicative sensor structure (dust), and does the
            estimation thesis get dust suppression for free?

M22 measured the additive half of review item R11 (hot pixels). This is the
multiplicative half. The review's own observation is that dust "is fixed in
sensor coordinates and smears into trails under the warp", which is true and is
only half the story. The other half is a claim worth testing, because if it
holds it is a free, unclaimed advantage of this project's thesis:

  A SELECTOR copies one frame's pixel into the output, so a dust shadow arrives
  at full contrast. An ESTIMATOR averages n_eff frames, and because the warp
  displaces the dust relative to the scene by a different amount in every frame,
  the shadow lands in n_eff different places and is diluted.

  If that is real, every shipping stacker puts dust in the output at full
  strength and strehl suppresses it without doing anything.

DETECTION. Dust is a multiplicative shadow fixed in sensor coordinates, roughly
10-40 sensor px across. Dividing each frame by a blurred copy of itself removes
scene content at large scales and leaves small-scale multiplicative structure;
averaging that ratio over frames suppresses whatever MOVES (the scene, which
breathing displaces) and keeps whatever does not (the sensor).

CONTROLS, following M22's methodology because it was the thing that saved that
milestone from reporting a million false defects:

  shift null      roll one map by an even offset. Preserves CFA phase and every
                  spatial statistic; destroys per-pixel correspondence. Any
                  cross-stack agreement that survives the roll is agreement
                  about large-scale structure, not about sensor defects.
  planted dust    a synthetic Gaussian shadow of known depth and radius injected
                  into every frame of one stack at a known location. Recovery of
                  a plant with a known answer is what distinguishes a working
                  detector from a hopeful one.

PRE-REGISTERED PREDICTIONS:

  Q1  Cross-stack correlation of the static maps is well above the shift null.
  Q2  The planted shadow is recovered at its planted depth to within a factor
      of ~2, and at the right location.
  Q3  Correlation between two stacks of DIFFERENT subjects is comparable to the
      correlation between two stacks of the SAME subject -- because dust does
      not care what was photographed. If same-subject pairs correlate much more,
      the map is measuring residual scene structure and the result is dead.

Q3 is the one that can kill this. `109MSDCF` and `119MSDCF` are different
subjects; `112MSDCF` and `113MSDCF` are the same session; `coffee-bean` and
`coffee-bubbles` are both coffee.
"""
import glob, os, json
import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter

BLACK = 512.0
SIG = 24.0          # green-sublattice px; keeps structure finer than ~24 px
MAXF = 24           # frames per stack
PLANT = dict(y=900, x=1200, r=6.0, depth=0.04)   # 4% shadow, ~6 px sigma

STACKS = [
    ("109MSDCF",       r"D:\personal\macro\109MSDCF"),
    ("119MSDCF",       r"D:\personal\macro\119MSDCF"),
    ("112MSDCF",       r"D:\personal\macro\112MSDCF"),
    ("113MSDCF",       r"D:\personal\macro\113MSDCF"),
    ("coffee-bean",    r"D:\personal\macro\coffee-bean"),
    ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles"),
]
OUT = os.path.join(os.path.dirname(__file__), "..", "out")


def green(path):
    with rawpy.imread(path) as r:
        return r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK


def static_map(folder, plant=None):
    files = sorted(glob.glob(os.path.join(folder, "*.ARW")))
    step = max(1, len(files) // MAXF)
    files = files[::step][:MAXF]
    acc, n = None, 0
    for f in files:
        g = green(f)
        if plant is not None:
            h, w = g.shape
            yy, xx = np.mgrid[0:h, 0:w]
            sh = 1.0 - plant["depth"] * np.exp(
                -(((yy - plant["y"]) ** 2 + (xx - plant["x"]) ** 2)
                  / (2 * plant["r"] ** 2)))
            g = g * sh
        lo = gaussian_filter(g, SIG)
        r = g / np.maximum(lo, 1.0)
        acc = r if acc is None else acc + r
        n += 1
    m = acc / n - 1.0
    # A residual large-scale term survives the ratio; remove it so the statistic
    # is confined to the band dust actually occupies.
    return (m - gaussian_filter(m, SIG)).astype(np.float32), n, len(files)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    maps, meta = {}, {}
    for name, folder in STACKS:
        m, n, nf = static_map(folder)
        maps[name] = m
        meta[name] = dict(n=n, rms=float(m.std()), shape=list(m.shape))
        print(f"{name:16s} {n:3d} frames  map {m.shape}  rms {m.std():.5f}  "
              f"p1 {np.percentile(m,1):+.5f}  p99 {np.percentile(m,99):+.5f}",
              flush=True)

    names = [n for n, _ in STACKS]
    h = min(maps[n].shape[0] for n in names)
    w = min(maps[n].shape[1] for n in names)
    M = {n: maps[n][:h, :w] for n in names}

    def corr(a, b):
        a = a - a.mean(); b = b - b.mean()
        return float((a * b).mean() / (a.std() * b.std()))

    SAME = {("112MSDCF", "113MSDCF"), ("coffee-bean", "coffee-bubbles")}
    print(f"\ncross-stack correlation of static maps ({h}x{w})")
    print(f"{'pair':36s} {'r':>8s} {'shift null':>11s} {'excess':>8s}   subject")
    rows = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            r = corr(M[a], M[b])
            rn = corr(M[a], np.roll(M[b], (16, 16), axis=(0, 1)))
            same = (a, b) in SAME or (b, a) in SAME
            rows.append(dict(a=a, b=b, r=r, null=rn, same=same))
            print(f"{a+' x '+b:36s} {r:8.4f} {rn:11.4f} {r-rn:8.4f}   "
                  f"{'SAME-ish' if same else 'different'}")

    ds = [x["r"] for x in rows if not x["same"]]
    ss = [x["r"] for x in rows if x["same"]]
    nulls = [x["null"] for x in rows]
    print(f"\nQ1  median r {np.median([x['r'] for x in rows]):.4f}   "
          f"median shift null {np.median(nulls):.4f}   "
          f"{'HOLDS' if np.median([x['r'] for x in rows]) > 5*abs(np.median(nulls)) else 'WEAK'}")
    print(f"Q3  different-subject median {np.median(ds):.4f}   "
          f"same-ish median {np.median(ss):.4f}   ratio {np.median(ss)/max(np.median(ds),1e-9):.2f}"
          f"   {'HOLDS' if np.median(ss) < 2*np.median(ds) else 'FAILS -- map is scene structure'}")

    # ---- Q2: plant recovery -------------------------------------------------
    pm, _, _ = static_map(STACKS[0][1], plant=PLANT)
    base = maps["109MSDCF"]
    d = pm[:base.shape[0], :base.shape[1]] - base
    y, x, r = PLANT["y"], PLANT["x"], PLANT["r"]
    sl = (slice(int(y - 4 * r), int(y + 4 * r)), slice(int(x - 4 * r), int(x + 4 * r)))
    print(f"\nQ2  planted {100*PLANT['depth']:.1f}% shadow, sigma {r:.0f} px at ({y},{x})")
    print(f"    recovered min in window {100*d[sl].min():+.3f}%   "
          f"peak offset {np.unravel_index(np.argmin(d[sl]), d[sl].shape)} "
          f"vs centre ({int(4*r)},{int(4*r)})")
    print(f"    global rms of the difference {100*d.std():.4f}%   "
          f"ratio {abs(d[sl].min())/max(d.std(),1e-12):.1f} sigma")
    np.save(os.path.join(OUT, "static-109.npy"), base)
    with open(os.path.join(OUT, "01-static.json"), "w") as fh:
        json.dump(dict(meta=meta, pairs=rows,
                       plant=dict(depth=PLANT["depth"], r=PLANT["r"],
                                  recovered=float(d[sl].min()),
                                  sigma=float(abs(d[sl].min()) / max(d.std(), 1e-12)))),
                  fh, indent=1)
