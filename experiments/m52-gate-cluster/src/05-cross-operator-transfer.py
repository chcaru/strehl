"""M52 step 5 - does the gate transfer ACROSS OPERATORS on real frames?

Facts 436/439 say the gate's tolerance is linear in a constant that belongs to
the operator, and that constant spans 10.4x across seven textbook operators.
The seam's design consequence is that each operator carries its OWN measured
constant, so `--gate t` means "t sigmas of THIS operator's noise" and is
therefore supposed to be portable.

That last step is an ARGUED inference, never measured. This measures it.

For each operator the shipped host pipeline is reproduced exactly:

    luma  = 0.5*(max(G1-black,0) + max(G2-black,0))
    resp  = <operator stencil>, replicate-clamped
    focus = clamped_box(resp, 13) / max(green_luma_sigma(luma), 1e-3)
    reg   = clamped_box(focus, 8)
    best  = max over frames                        (pass one - no constant used)
    n_eff = #{k : best - reg_k <= t*sqrt(2)*C_op}  (pass two - C_op is per-operator)

C_op is MY measured response SD from step 01 (unit-sigma white noise, w13+r8),
not the published one.

Only degree-1 homogeneous operators are used, so that dividing by sigma once
really does produce a unit-noise field and C_op transfers exactly. (tenengrad-sq
and local-variance are degree 2 and are handled in the separate probe at the
end.)

PLACEBO (rule 11): `tenengrad-alt` is the identical operator by a different code
path. If the cross-operator spread is real, this row must show spread 1.000.

RULE 32: raw_image_visible is a VIEW - every read copies inside the `with`.
"""

import json
import pathlib
import time

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

WINDOW_RADIUS = 13
REGULARISER_RADIUS = 8
SIGMA_EPS = 1e-3
BLACK = 512.0
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
RN_LOW, RN_HIGH = 4.20, 1.47
SQRT2 = float(np.sqrt(2.0))
GATES = [0.5, 1.0, 2.0, 4.0]

# step 01, measured by me on unit-sigma noise at w13 + r8 (8 seeds x 2048^2)
C_OP = {
    "ring(1,3)": 0.00983480134009183,
    "tenengrad": 0.015317998248034962,
    "tenengrad-alt": 0.015317998248034962,
    "brenner": 0.029983272387236935,
    "laplacian": 0.10024627834964879,
    "sml": 0.10149624531092787,
}

STACKS = [("109MSDCF", r"D:\personal\macro\109MSDCF", 160.0),
          ("113MSDCF", r"D:\personal\macro\113MSDCF", 500.0)]

_CC = {}


def counts(n, r):
    i = np.arange(n)
    return (np.minimum(i + r, n - 1) - np.maximum(i - r, 0) + 1).astype(np.float64)


def clamped_box(a, r):
    n = 2 * r + 1
    s = uniform_filter(a, size=n, mode="constant", cval=0.0) * float(n * n)
    key = (a.shape, r)
    d = _CC.get(key)
    if d is None:
        d = counts(a.shape[0], r)[:, None] * counts(a.shape[1], r)[None, :]
        _CC[key] = d
    return s / d


def sh(a, dy, dx):
    p = np.pad(a, 1, mode="edge")
    return p[1 + dy: 1 + dy + a.shape[0], 1 + dx: 1 + dx + a.shape[1]]


def op_tenengrad(a):
    gx = (sh(a, -1, 1) + 2 * sh(a, 0, 1) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, 0, -1) - sh(a, 1, -1)) * 0.125
    gy = (sh(a, 1, -1) + 2 * sh(a, 1, 0) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, -1, 0) - sh(a, -1, 1)) * 0.125
    return np.hypot(gx, gy)


def op_tenengrad_alt(a):
    """Same operator, different arithmetic: 3x3 correlation on the transpose."""
    kx = np.array([[-1.0, 0, 1], [-2, 0, 2], [-1, 0, 1]]) * 0.125
    t = a.T
    p = np.pad(t, 1, mode="edge")
    gx = np.zeros_like(t)
    gy = np.zeros_like(t)
    for j in range(3):
        for i in range(3):
            w = p[j: j + t.shape[0], i: i + t.shape[1]]
            gx += kx[j, i] * w
            gy += kx[i, j] * w
    return np.sqrt(gx * gx + gy * gy).T


def op_brenner(a):
    p = np.pad(a, ((0, 0), (0, 2)), mode="edge")
    return np.abs(p[:, 2: 2 + a.shape[1]] - a)


def op_laplacian(a):
    return np.abs(4 * a - sh(a, 0, 1) - sh(a, 0, -1) - sh(a, 1, 0) - sh(a, -1, 0))


def op_sml(a):
    return (np.abs(2 * a - sh(a, 0, 1) - sh(a, 0, -1))
            + np.abs(2 * a - sh(a, 1, 0) - sh(a, -1, 0)))


def op_ring13(a):
    return np.abs(clamped_box(a, 1) - clamped_box(a, 3))


OPS = {"ring(1,3)": op_ring13, "tenengrad": op_tenengrad,
       "tenengrad-alt": op_tenengrad_alt, "brenner": op_brenner,
       "laplacian": op_laplacian, "sml": op_sml}


def green_luma_sigma(luma, iso):
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW
    var = g * np.maximum(luma, 0.0) + (rn * g) ** 2
    return np.sqrt(0.5 * var)


def luma_of(path):
    with rawpy.imread(path) as rr:
        v = rr.raw_image_visible
        h, w = (v.shape[0] // 2) * 2, (v.shape[1] // 2) * 2
        g1 = np.array(v[0:h:2, 1:w:2], dtype=np.float64)
        g2 = np.array(v[1:h:2, 0:w:2], dtype=np.float64)
    return 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))


def solve(ladder):
    for (g0, n0), (g1, n1) in zip(ladder, ladder[1:]):
        if n0 <= 3.0 <= n1:
            f = (np.log(3.0) - np.log(n0)) / (np.log(n1) - np.log(n0))
            return float(np.exp(np.log(g0) + f * (np.log(g1) - np.log(g0))))
    return None


out = {"C_op": C_OP, "gates": GATES, "stacks": {}}
for sname, sdir, iso in STACKS:
    files = sorted(str(p) for p in pathlib.Path(sdir).iterdir()
                   if p.suffix.upper() == ".ARW")
    print(f"\n=== {sname}  N={len(files)}  ISO {iso:.0f} ===", flush=True)
    t0 = time.time()
    lumas = [luma_of(p) for p in files]
    sigmas = [np.maximum(green_luma_sigma(l, iso), SIGMA_EPS) for l in lumas]
    print(f"  decoded in {time.time() - t0:.0f}s", flush=True)

    res = {}
    winners = {}
    for oname, fn in OPS.items():
        t1 = time.time()
        cube = np.empty((len(files),) + lumas[0].shape, dtype=np.float32)
        for k, (l, s) in enumerate(zip(lumas, sigmas)):
            cube[k] = clamped_box(clamped_box(fn(l), WINDOW_RADIUS) / s,
                                  REGULARISER_RADIUS).astype(np.float32)
        best = cube.max(axis=0)
        winners[oname] = cube.argmax(axis=0).astype(np.uint8)
        row = {}
        for t in GATES:
            tol = np.float32(t * SQRT2 * C_OP[oname])
            n = np.zeros(best.shape, dtype=np.uint16)
            for k in range(cube.shape[0]):
                n += best - cube[k] <= tol
            row[t] = {"mean_n_eff": float(n.mean()), "frac_n1": float((n == 1).mean())}
        row["gate_for_3"] = solve([(t, row[t]["mean_n_eff"]) for t in GATES])
        res[oname] = row
        del cube, best
        print(f"  {oname:<14} C={C_OP[oname]:.6f}  " +
              "  ".join(f"g{t}={row[t]['mean_n_eff']:6.3f}" for t in GATES) +
              f"  solve3={row['gate_for_3'] if row['gate_for_3'] is None else round(row['gate_for_3'], 4)}"
              f"  [{time.time() - t1:.0f}s]", flush=True)

    agree = {o: float((winners[o] == winners["tenengrad"]).mean()) for o in OPS}
    print("  winner-map agreement with tenengrad: " +
          "  ".join(f"{o}={agree[o]:.4f}" for o in OPS))
    real = [o for o in OPS if o != "tenengrad-alt"]
    for t in GATES:
        v = [res[o][t]["mean_n_eff"] for o in real]
        print(f"  gate {t}: n_eff across 5 DIFFERENT operators "
              f"{min(v):.3f}..{max(v):.3f}  spread {max(v) / min(v):.3f}x")
    pv = [res[o][2.0]["mean_n_eff"] for o in ("tenengrad", "tenengrad-alt")]
    print(f"  PLACEBO (same operator, two code paths) at gate 2.0: "
          f"{pv[0]:.4f} vs {pv[1]:.4f}  spread {max(pv) / min(pv):.5f}x")
    out["stacks"][sname] = {"iso": iso, "frames": len(files), "ops": res,
                            "winner_agreement": agree}
    del lumas, sigmas

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "05-cross-operator-transfer.json"
p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {p}")
