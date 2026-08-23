"""
M29 / 02 -- Script 01 used the wrong statistic. This is the right one.

Script 01 correlated whole static maps across stacks and found nothing above the
shift null. That result is uninterpretable as written, for two reasons I did not
see until the numbers were in front of me:

  (a) THE POSITIVE CONTROL VALIDATED A STATISTIC I DO NOT USE. The planted 4%
      shadow was recovered at 259.6 sigma -- but against the rms of the
      DIFFERENCE between the planted and unplanted maps of the same stack, which
      is an oracle nobody has. Against the quantity actually available -- the
      map's own rms of 0.1475 -- the same plant is 1.096% deep, i.e. 0.074
      sigma. Invisible. Discipline 121 in a second costume: I proved a detector
      works using an input the detector never gets.

  (b) A GLOBAL CORRELATION CANNOT SEE A SPARSE LOCALISED DEFECT. If dust of
      depth A covers a fraction f of the sensor and everything else is
      independent, the induced correlation is r ~ f*A^2/sigma_map^2. For a
      generous f = 0.0017 and A = 0.04 that is 1.3e-4, more than an order of
      magnitude below the measured shift nulls of 0.001-0.008. Reaching the null
      level would need a 32% shadow, or 11% of the sensor covered. The
      instrument was never capable of answering the question.

The right statistic is the one M22 used for hot pixels, which are sparse and
localised in the same way: PER-LOCATION CONJUNCTION. Dust is a shadow, so it is
negative in EVERY stack at the SAME sensor coordinate. Standardise each map by
its own rms, take the per-pixel minimum across stacks, smooth at the scale dust
occupies, and read the tail.

CALIBRATED PLANT. Planting in the frame domain costs a full 720-frame recompute
per depth, so the plant is injected into the map domain using the map-domain
response script 01 measured directly: a 4.0% frame-domain shadow of sigma 6 px
produced a 1.096% map-domain trough, an attenuation of 0.274. That factor is
MEASURED, not assumed, and it is the only thing standing between the depths
quoted below and a frame-domain plant.

CONTROLS:
  shift null      roll each map by a DIFFERENT large even offset. Preserves CFA
                  phase and every spatial statistic, destroys the one thing dust
                  has: common location.
  planted dust    the same shadow in all six stacks at the same coordinate, over
                  a sweep of depths. The depth at which the plant stops beating
                  the shift null IS the detection limit -- the number script 01
                  should have produced instead of a bare null result.

PRE-REGISTERED PREDICTIONS:

  Q4  A common plant of a few percent lands in the extreme tail of the
      conjunction statistic while the shift null does not.
  Q5  There is a depth below which it does not, and that depth is the honest
      sensitivity of this corpus to dust.
  Q6  With the limit in hand the unplanted tail is either populated -- dust
      exists and is now localised -- or it is bounded below the limit. Either
      answer is publishable; only an unbounded "we looked and saw nothing" is
      not.
"""
import glob, os, json
import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter

BLACK, SIG, MAXF, RDUST = 512.0, 24.0, 20, 6.0
ATTEN = 0.274                      # measured in script 01
DEPTHS = [0.0, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16]
PY, PX = 900, 1200
STACKS = [("109MSDCF", r"D:\personal\macro\109MSDCF"),
          ("119MSDCF", r"D:\personal\macro\119MSDCF"),
          ("112MSDCF", r"D:\personal\macro\112MSDCF"),
          ("113MSDCF", r"D:\personal\macro\113MSDCF"),
          ("coffee-bean", r"D:\personal\macro\coffee-bean"),
          ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles")]
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")


def static_map(folder):
    files = sorted(glob.glob(os.path.join(folder, "*.ARW")))
    files = files[::max(1, len(files) // MAXF)][:MAXF]
    acc = None
    for f in files:
        with rawpy.imread(f) as r:
            g = r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK
        rr = g / np.maximum(gaussian_filter(g, SIG), 1.0)
        acc = rr if acc is None else acc + rr
    m = acc / len(files) - 1.0
    return (m - gaussian_filter(m, SIG)).astype(np.float32)


def get(name, folder):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"static-{name}.npy")
    if not os.path.exists(p):
        np.save(p, static_map(folder))
    return np.load(p)


raws, names = [], [n for n, _ in STACKS]
for name, folder in STACKS:
    m = get(name, folder)
    raws.append(m)
    print(f"{name:16s} rms {m.std():.5f}", flush=True)
h = min(m.shape[0] for m in raws)
w = min(m.shape[1] for m in raws)
raws = [m[:h, :w] for m in raws]
sd = [float(m.std()) for m in raws]

yy, xx = np.mgrid[0:h, 0:w]
shape = np.exp(-(((yy - PY) ** 2 + (xx - PX) ** 2)
                 / (2 * RDUST ** 2))).astype(np.float32)
del yy, xx
sl = (slice(PY - 30, PY + 30), slice(PX - 30, PX + 30))


def conj(stack_list):
    """Standardise each map, take the common (minimum) excursion, smooth."""
    A = np.stack([(m - m.mean()) / s for m, s in zip(stack_list, sd)])
    return gaussian_filter(A.min(axis=0), RDUST / 2.0)


rolls = [(0, 0), (211, 307), (-401, 149), (523, -263), (-97, 631), (359, 421)]
null = conj([np.roll(raws[i], rolls[i], axis=(0, 1)) for i in range(len(names))])
nthr = {p: float(np.percentile(null, p)) for p in (1.0, 0.1, 0.01, 0.001)}
base = conj(raws)
bthr = {p: float(np.percentile(base, p)) for p in (1.0, 0.1, 0.01, 0.001)}
cols = (1.0, 0.1, 0.01, 0.001)
print(f"\n{'tail percentile':>18s}" + "".join(f"{'p'+str(p):>10s}" for p in cols))
print(f"{'shift null':>18s}" + "".join(f"{nthr[p]:10.3f}" for p in cols))
print(f"{'unplanted':>18s}" + "".join(f"{bthr[p]:10.3f}" for p in cols))
print(f"{'Q6 excess':>18s}" + "".join(f"{bthr[p]-nthr[p]:+10.3f}" for p in cols))

print(f"\nQ4/Q5  common plant at ({PY},{PX}), sigma {RDUST:.0f} green px "
      f"({2*RDUST:.0f} sensor px), map-domain attenuation {ATTEN}")
print(f"{'frame depth':>12s} {'plant value':>12s} {'beats null':>12s} "
      f"{'null locations below':>21s}")
rows = []
for dep in DEPTHS:
    P = conj([m - ATTEN * dep * shape for m in raws])
    v = float(P[sl].min())
    below = int((null < v).sum())
    frac = 100.0 * below / null.size
    beats = v < nthr[0.001]
    rows.append(dict(depth=dep, value=v, null_below=below, null_frac=frac,
                     beats=bool(beats)))
    print(f"{100*dep:11.1f}% {v:12.3f} {'YES' if beats else 'no':>12s} "
          f"{below:21d}  ({frac:.5f}%)")

with open(os.path.join(OUT, "02-conjunction.json"), "w") as fh:
    json.dump(dict(null_tail=nthr, base_tail=bthr, sweep=rows, atten=ATTEN,
                   rms=sd), fh, indent=1)

det = [r["depth"] for r in rows if r["beats"] and r["depth"] > 0]
print(f"\nQ5  detection limit: "
      + (f"{100*min(det):.1f}% shadow depth" if det
         else "NOT DETECTED at any depth up to 16%"))
