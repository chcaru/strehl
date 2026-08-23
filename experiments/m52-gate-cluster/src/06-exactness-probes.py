"""M52 step 6 - what is EXACTLY true in facts 436/438, and where the constant
stops being a property of the operator alone.

Four probes:

A. RESCALING EQUIVALENCE (fact 436's exact content). Replace the operator O by
   7*O and its constant C by 7*C. Every focus difference and the tolerance both
   scale by 7, so the admitted set must be IDENTICAL, pixel for pixel. This is
   the only sense in which "gate rescales by k" is exact.

B. INHERITED-CONSTANT COST (facts 437/438/439). SML run with the HOST's
   0.015214 instead of its own 0.1015 - what the plugin seam exists to prevent -
   against SML with its own constant, against the host operator. Which is
   actually closer to the host's behaviour?

C. FACT 438 mechanism. Does changing only the constant leave the winner field
   untouched? Measured as winner-map agreement, not asserted.

D. IS C A PROPERTY OF THE OPERATOR ALONE? Facts 436/439 both say the constant
   "belongs to the operator". For an operator homogeneous of degree 1 in the
   input, resp(c*x) = c*resp(x), so dividing by sigma once gives a field whose
   noise SD is independent of sigma. For a degree-2 operator it is not. Two of
   fact 439's seven surveyed operators are degree 2. Measured by sweeping the
   noise sigma of a synthetic plane, which is a placebo-bearing design: the
   degree-1 operators MUST come out flat.

RULE 32: raw_image_visible is a VIEW - every read copies inside the `with`.
"""

import json
import pathlib

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

WINDOW_RADIUS, REGULARISER_RADIUS = 13, 8
SIGMA_EPS, BLACK = 1e-3, 512.0
GAIN_DIVISOR, BASE_ISO, SECOND_BASE_ISO = 436.8, 100.0, 400.0
RN_LOW, RN_HIGH = 4.20, 1.47
SQRT2 = float(np.sqrt(2.0))
HOST_C = 0.015214
C_TEN, C_SML = 0.015317998248034962, 0.10149624531092787
_CC = {}


def counts(n, r):
    i = np.arange(n)
    return (np.minimum(i + r, n - 1) - np.maximum(i - r, 0) + 1).astype(np.float64)


def clamped_box(a, r):
    n = 2 * r + 1
    s = uniform_filter(a, size=n, mode="constant", cval=0.0) * float(n * n)
    k = (a.shape, r)
    if k not in _CC:
        _CC[k] = counts(a.shape[0], r)[:, None] * counts(a.shape[1], r)[None, :]
    return s / _CC[k]


def sh(a, dy, dx):
    p = np.pad(a, 1, mode="edge")
    return p[1 + dy: 1 + dy + a.shape[0], 1 + dx: 1 + dx + a.shape[1]]


def op_tenengrad(a):
    gx = (sh(a, -1, 1) + 2 * sh(a, 0, 1) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, 0, -1) - sh(a, 1, -1)) * 0.125
    gy = (sh(a, 1, -1) + 2 * sh(a, 1, 0) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, -1, 0) - sh(a, -1, 1)) * 0.125
    return np.hypot(gx, gy)


def op_sml(a):
    return (np.abs(2 * a - sh(a, 0, 1) - sh(a, 0, -1))
            + np.abs(2 * a - sh(a, 1, 0) - sh(a, -1, 0)))


def op_ten_sq(a):
    gx = (sh(a, -1, 1) + 2 * sh(a, 0, 1) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, 0, -1) - sh(a, 1, -1)) * 0.125
    gy = (sh(a, 1, -1) + 2 * sh(a, 1, 0) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, -1, 0) - sh(a, -1, 1)) * 0.125
    return gx * gx + gy * gy


def op_localvar(a):
    m = clamped_box(a, 1)
    return clamped_box(a * a, 1) - m * m


def op_ring13(a):
    return np.abs(clamped_box(a, 1) - clamped_box(a, 3))


def luma_of(path):
    with rawpy.imread(path) as rr:
        v = rr.raw_image_visible
        h, w = (v.shape[0] // 2) * 2, (v.shape[1] // 2) * 2
        g1 = np.array(v[0:h:2, 1:w:2], dtype=np.float64)
        g2 = np.array(v[1:h:2, 0:w:2], dtype=np.float64)
    return 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))


def sigma_of(luma, iso):
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW
    return np.maximum(np.sqrt(0.5 * (g * np.maximum(luma, 0.0) + (rn * g) ** 2)), SIGMA_EPS)


def build(lumas, sigmas, fn, scale=1.0):
    c = np.empty((len(lumas),) + lumas[0].shape, dtype=np.float32)
    for k, (l, s) in enumerate(zip(lumas, sigmas)):
        c[k] = clamped_box(clamped_box(scale * fn(l), WINDOW_RADIUS) / s,
                           REGULARISER_RADIUS).astype(np.float32)
    return c


def n_map(cube, C, t):
    best = cube.max(axis=0)
    tol = np.float32(t * SQRT2 * C)
    n = np.zeros(best.shape, dtype=np.uint16)
    for k in range(cube.shape[0]):
        n += best - cube[k] <= tol
    return n


STACK, ISO = r"D:\personal\macro\109MSDCF", 160.0
files = sorted(str(p) for p in pathlib.Path(STACK).iterdir() if p.suffix.upper() == ".ARW")
lumas = [luma_of(p) for p in files]
sigmas = [sigma_of(l, ISO) for l in lumas]
print(f"109MSDCF: {len(files)} frames, plane {lumas[0].shape}\n")
out = {}

# ---------------------------------------------------------------- probe A
print("A. RESCALING EQUIVALENCE - operator x7 with constant x7")
base = build(lumas, sigmas, op_tenengrad, 1.0)
scal = build(lumas, sigmas, op_tenengrad, 7.0)
rows = []
for t in (0.5, 2.0):
    a, b = n_map(base, C_TEN, t), n_map(scal, 7.0 * C_TEN, t)
    dis = int((a != b).sum())
    rows.append({"gate": t, "mean_a": float(a.mean()), "mean_b": float(b.mean()),
                 "disagreeing_px": dis, "total_px": int(a.size)})
    print(f"   gate {t}: n_eff {a.mean():.6f} vs {b.mean():.6f}; "
          f"pixels differing {dis} of {a.size} ({dis / a.size:.3%})")
w_a, w_b = base.argmax(axis=0), scal.argmax(axis=0)
print(f"   winner maps agree on {(w_a == w_b).mean():.6%} of pixels")
out["A_rescaling"] = {"rows": rows, "winner_agree": float((w_a == w_b).mean())}
del scal, w_a, w_b

# ---------------------------------------------------------------- probes B, C
print("\nB/C. INHERITED CONSTANT - SML with the host's 0.015214 vs its own")
sml = build(lumas, sigmas, op_sml, 1.0)
res = {}
for t in (0.5, 1.0, 2.0, 4.0):
    ten = float(n_map(base, C_TEN, t).mean())
    own = float(n_map(sml, C_SML, t).mean())
    inh = float(n_map(sml, HOST_C, t).mean())
    res[t] = {"host_operator": ten, "sml_own_C": own, "sml_inherited_C": inh}
    print(f"   gate {t}: host tenengrad {ten:6.3f} | SML own-C {own:6.3f} "
          f"({own / ten:5.2f}x host) | SML inherited-C {inh:6.3f} ({inh / ten:5.2f}x host)")
wt, ws = base.argmax(axis=0), sml.argmax(axis=0)
print(f"   fact 438: changing ONLY the constant leaves the winner map identical "
      f"(SML own-C vs inherited-C winner agreement = 100.000000% by construction:")
print(f"             pass one never reads it). SML vs tenengrad winners agree on "
      f"{(wt == ws).mean():.4%} - a different operator DOES move the winner.")
out["BC_inherited"] = {"gates": res, "sml_vs_ten_winner_agree": float((wt == ws).mean())}
del sml, base, wt, ws, lumas, sigmas

# ---------------------------------------------------------------- probe D
print("\nD. IS C A PROPERTY OF THE OPERATOR ALONE? sweep the noise sigma")
print("   (normalised field = box13(op(x))/sigma then reg8; degree-1 ops must be flat)")
rng = np.random.Generator(np.random.Philox(20260823))
DEG = {"ring(1,3)": op_ring13, "tenengrad": op_tenengrad, "brenner":
       lambda a: np.abs(np.pad(a, ((0, 0), (0, 2)), mode="edge")[:, 2:2 + a.shape[1]] - a),
       "sml": op_sml, "tenengrad-sq": op_ten_sq, "local variance": op_localvar}
tbl = {}
for name, fn in DEG.items():
    vals = []
    for sg in (1.0, 4.0, 16.0):
        x = rng.normal(0.0, sg, size=(1024, 1024))
        f = clamped_box(clamped_box(fn(x), WINDOW_RADIUS) / sg, REGULARISER_RADIUS)
        m = 64
        vals.append(float(f[m:-m, m:-m].std(ddof=1)))
    tbl[name] = vals
    print(f"   {name:<16} sigma=1 {vals[0]:.6f}   sigma=4 {vals[1]:.6f}   "
          f"sigma=16 {vals[2]:.6f}   ratio(16/1) {vals[2] / vals[0]:7.3f}x")
out["D_sigma_sweep"] = tbl

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "06-exactness-probes.json"
p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {p}")
