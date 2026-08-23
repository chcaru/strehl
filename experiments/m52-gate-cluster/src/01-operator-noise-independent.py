"""M52 step 1 - independent re-measurement of the operator noise constants.

INDEPENDENT of experiments/m43-plugin-seam/02b and 03. Nothing is imported from
them and no primitive is copied. Differences on purpose:

  * box mean: separable DIRECT SUMMATION over 2r+1 shifted slices, not a
    cumulative-sum difference. A cumsum box filter and a shift-sum box filter
    fail in different ways (cancellation vs none), so agreeing is evidence.
  * Sobel: explicit edge-padded slicing, not np.roll with hand-patched borders.
  * RNG: Philox, not PCG64, and different seeds. The m43 scripts use
    np.random.default_rng(20260810 + s).
  * a third route (autocovariance contraction) that never filters the field at
    all: Var(K*f) = sum_d R_K(d) C_f(d) with R_K the kernel autocorrelation and
    C_f the operator output's autocovariance.

Calibration (rule 20 / AGENTS 'loader check'): the instrument must reproduce
BOTH crate constants in BOTH of their own configurations before anything else
is printed.

    FOCUS_NOISE_SD      = SD( box_mean(box_mean(|grad|,13), 8) )   crate 0.015214
    FINE_FOCUS_NOISE_SD = SD( box_mean(|grad|,2) )                 crate 0.090400

Placebos (rule 11): a set of operators that are mathematically THE SAME operator
implemented five different ways must span k = 1.000x. If that set spans as much
as the seven-operator survey, the survey measures the instrument, not operators.
"""

import json
import pathlib
import sys

import numpy as np

FOCUS_NOISE_SD = 0.015214       # crates/strehl-core/src/merge.rs
FINE_FOCUS_NOISE_SD = 0.090400  # crates/strehl-core/src/through_focus.rs
WINDOW_RADIUS = 13
FINE_WINDOW_RADIUS = 2
REGULARISER_RADIUS = 8

SIDE = 2048
SEEDS = 8
# Deliberately different from m43's 20260810 + s.
SEED_BASE = 52_000_017


# ---------------------------------------------------------------- primitives
def box_mean(a, r):
    """Separable box mean by direct summation of 2r+1 replicate-padded shifts."""
    if r == 0:
        return np.asarray(a, dtype=np.float64).copy()
    x = np.asarray(a, dtype=np.float64)
    n = 2 * r + 1
    p = np.pad(x, ((r, r), (0, 0)), mode="edge")
    acc = np.zeros_like(x)
    for k in range(n):
        acc += p[k : k + x.shape[0], :]
    x = acc / n
    p = np.pad(x, ((0, 0), (r, r)), mode="edge")
    acc = np.zeros_like(x)
    for k in range(n):
        acc += p[:, k : k + x.shape[1]]
    return acc / n


def sh(a, dy, dx):
    """a[y+dy, x+dx] with replicate (edge) extension. Padded-slice, not roll."""
    p = np.pad(a, ((1, 1), (1, 1)), mode="edge")
    return p[1 + dy : 1 + dy + a.shape[0], 1 + dx : 1 + dx + a.shape[1]]


def sobel_xy(a):
    gx = (sh(a, -1, 1) + 2.0 * sh(a, 0, 1) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2.0 * sh(a, 0, -1) - sh(a, 1, -1)) * 0.125
    gy = (sh(a, 1, -1) + 2.0 * sh(a, 1, 0) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2.0 * sh(a, -1, 0) - sh(a, -1, 1)) * 0.125
    return gx, gy


# ---------------------------------------------------------------- operators
def op_tenengrad(a):
    gx, gy = sobel_xy(a)
    return np.hypot(gx, gy)


def op_tenengrad_sq(a):
    gx, gy = sobel_xy(a)
    return gx * gx + gy * gy


def op_brenner(a):
    p = np.pad(a, ((0, 0), (0, 2)), mode="edge")
    return np.abs(p[:, 2 : 2 + a.shape[1]] - a)


def op_laplacian(a):
    return np.abs(4.0 * a - sh(a, 0, 1) - sh(a, 0, -1) - sh(a, 1, 0) - sh(a, -1, 0))


def op_sml(a):
    return (np.abs(2.0 * a - sh(a, 0, 1) - sh(a, 0, -1))
            + np.abs(2.0 * a - sh(a, 1, 0) - sh(a, -1, 0)))


def op_ring13(a):
    return np.abs(box_mean(a, 1) - box_mean(a, 3))


def op_local_variance(a):
    m = box_mean(a, 1)
    return box_mean(a * a, 1) - m * m


SURVEY = [
    ("ring(1,3)", op_ring13),
    ("tenengrad |grad|  (SHIPPED)", op_tenengrad),
    ("tenengrad-squared", op_tenengrad_sq),
    ("brenner", op_brenner),
    ("local variance (3x3)", op_local_variance),
    ("laplacian |4I-N4|", op_laplacian),
    ("sum-modified-laplacian", op_sml),
]


# ------------------------------------------------- placebo: same op, 5 ways
def ten_hypot(a):
    gx, gy = sobel_xy(a)
    return np.hypot(gx, gy)


def ten_sqrt(a):
    gx, gy = sobel_xy(a)
    return np.sqrt(gx * gx + gy * gy)


def ten_transposed(a):
    """Compute on the transpose and transpose back. Gx and Gy swap roles."""
    gx, gy = sobel_xy(a.T)
    return np.sqrt(gx * gx + gy * gy).T


def ten_via_conv(a):
    """Same Sobel by explicit 3x3 correlation over padded slices, unrolled."""
    kx = np.array([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]])
    ky = np.array([[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]])
    p = np.pad(a, 1, mode="edge")
    gx = np.zeros_like(a)
    gy = np.zeros_like(a)
    for j in range(3):
        for i in range(3):
            w = p[j : j + a.shape[0], i : i + a.shape[1]]
            gx += kx[j, i] * w
            gy += ky[j, i] * w
    return np.hypot(gx * 0.125, gy * 0.125)


def ten_scaled_then_unscaled(a):
    """Scale the input by 7, run, divide by 7. Exactly homogeneous."""
    gx, gy = sobel_xy(7.0 * a)
    return np.hypot(gx, gy) / 7.0


PLACEBO = [
    ("tenengrad via hypot", ten_hypot),
    ("tenengrad via sqrt(gx^2+gy^2)", ten_sqrt),
    ("tenengrad on the transpose", ten_transposed),
    ("tenengrad by 3x3 correlation", ten_via_conv),
    ("tenengrad scaled 7x then /7", ten_scaled_then_unscaled),
]


# ---------------------------------------------------------------- machinery
def plane(seed, side=SIDE):
    return np.random.Generator(np.random.Philox(seed)).standard_normal((side, side))


def one(seed, op, radius, regularise, side=SIDE):
    a = plane(seed, side)
    f = box_mean(op(a), radius)
    m = radius + 2
    if regularise:
        f = box_mean(f, REGULARISER_RADIUS)
        m += REGULARISER_RADIUS
    core = f[m:-m, m:-m]
    return float(np.std(core, ddof=1)), float(np.mean(core))


def measure(op, radius, regularise, seeds=SEEDS, side=SIDE):
    vals = [one(SEED_BASE + 1000 * s, op, radius, regularise, side) for s in range(seeds)]
    sds = np.array([v[0] for v in vals])
    means = np.array([v[1] for v in vals])
    return (float(sds.mean()), float(sds.std(ddof=1) / np.sqrt(len(sds))),
            float(means.mean()))


def pct(a, b):
    return (a - b) / b


out = {}
print("=" * 78)
print("M52 STEP 1 - independent instrument, calibrated against BOTH crate constants")
print("=" * 78)
print(f"  {SEEDS} seeds x {SIDE}^2 Philox standard normals, seed base {SEED_BASE}\n")

RAYLEIGH_MEAN = 0.125 * np.sqrt(12.0) * np.sqrt(np.pi / 2.0)
ok = True
cal = {}
for label, radius, reg, target in [
    ("FOCUS_NOISE_SD", WINDOW_RADIUS, True, FOCUS_NOISE_SD),
    ("FINE_FOCUS_NOISE_SD", FINE_WINDOW_RADIUS, False, FINE_FOCUS_NOISE_SD),
]:
    sd, sem, mean = measure(op_tenengrad, radius, reg)
    dev = pct(sd, target)
    # The crate's own test tolerance is 4 SEM on a relative SEM of ~0.49%,
    # i.e. about +-2%. Use 2% here, stated before the number was printed.
    hit = abs(dev) <= 0.02
    mean_ok = abs(mean / RAYLEIGH_MEAN - 1.0) < 0.03
    ok &= hit and mean_ok
    cal[label] = {"crate": target, "python": sd, "sem": sem, "dev": dev,
                  "mean": mean, "mean_over_rayleigh": mean / RAYLEIGH_MEAN}
    cfg = f"w{radius}" + (f" + reg{REGULARISER_RADIUS}" if reg else ", no reg")
    print(f"  {label:<22}{cfg:>16}  crate {target:.6f}  mine {sd:.6f} +/- {sem:.6f}"
          f"  dev {dev:+.2%}  {'MATCH' if hit else 'MISMATCH'}")
    print(f"  {'':<22}{'':>16}  response mean {mean:.5f} = "
          f"{mean / RAYLEIGH_MEAN:.4f}x closed-form Rayleigh {RAYLEIGH_MEAN:.5f}"
          f"  {'OK' if mean_ok else 'BAD'}")
out["calibration"] = cal
if not ok:
    print("\n  CALIBRATION FAILED - refusing to report anything else.")
    sys.exit(1)
print("\n  CALIBRATED.\n")

# ------------------------------------------------------------- placebo arms
print("=" * 78)
print("PLACEBO A (rule 11) - five implementations of ONE operator. Must span 1.00x")
print("=" * 78)
pl = []
for name, op in PLACEBO:
    sd, sem, _ = measure(op, WINDOW_RADIUS, True)
    pl.append({"name": name, "sd": sd, "sem": sem, "k": sd / FOCUS_NOISE_SD})
    print(f"  {name:<32}{sd:>12.6f}{sd / FOCUS_NOISE_SD:>10.4f}")
pk = [r["k"] for r in pl]
print(f"\n  placebo span = {max(pk) / min(pk):.4f}x   (survey below claims 10.4x)\n")
out["placebo_same_operator"] = {"rows": pl, "span": max(pk) / min(pk)}

print("=" * 78)
print("PLACEBO B - seed-to-seed spread of the shipped arm. Must also span ~1.00x")
print("=" * 78)
per_seed = [one(SEED_BASE + 1000 * s, op_tenengrad, WINDOW_RADIUS, True)[0]
            for s in range(SEEDS)]
print("  " + "  ".join(f"{v:.6f}" for v in per_seed))
print(f"\n  seed span = {max(per_seed) / min(per_seed):.4f}x\n")
out["placebo_seeds"] = {"sds": per_seed, "span": max(per_seed) / min(per_seed)}

# ------------------------------------------------------------- fact 439
print("=" * 78)
print("FACT 439 - k across seven textbook operators, shipped config (op->w13->r8)")
print("=" * 78)
rows = []
for name, op in SURVEY:
    sd, sem, _ = measure(op, WINDOW_RADIUS, True)
    rows.append({"operator": name, "sd": sd, "sem": sem, "k": sd / FOCUS_NOISE_SD,
                 "eff_gate": FOCUS_NOISE_SD / sd})
    print(f"  {name:<30}{sd:>12.6f}{sd / FOCUS_NOISE_SD:>10.3f}"
          f"{FOCUS_NOISE_SD / sd:>14.4f}")
ks = [r["k"] for r in rows]
print(f"\n  k spans {min(ks):.3f} to {max(ks):.3f} = {max(ks) / min(ks):.2f}x  "
      f"(fact 439 says 10.4x)\n")
out["fact439"] = {"rows": rows, "span": max(ks) / min(ks)}

# ------------------------------------------------------------- fact 500/501
print("=" * 78)
print("FACTS 500 / 501 - the units correction and the two-target diagnosis")
print("=" * 78)
fine_reg_sd, fine_reg_sem, _ = measure(op_tenengrad, FINE_WINDOW_RADIUS, True)
coarse_unreg_sd, coarse_unreg_sem, _ = measure(op_tenengrad, WINDOW_RADIUS, False)
k_claimed = FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD
k_honest = fine_reg_sd / FOCUS_NOISE_SD
print(f"  fact 437 pair          k = {k_claimed:.4f}  (0.090400 / 0.015214)")
print(f"  SD(reg8(box2(|grad|)))   = {fine_reg_sd:.6f} +/- {fine_reg_sem:.6f}"
      f"   fact 500 says 0.027613")
print(f"  honest k               = {k_honest:.4f}          fact 500 says 1.815")
print(f"  overstatement          = {k_claimed / k_honest:.3f}x  fact 500 says 3.27x")
print()
print(f"  one-target instrument: SD(box13(|grad|)) unregularised = "
      f"{coarse_unreg_sd:.6f}")
print(f"    vs FOCUS_NOISE_SD  {pct(coarse_unreg_sd, FOCUS_NOISE_SD):+.2%}"
      f"   (fact 501 says +24.26%)")
print(f"    vs FINE_FOCUS_NOISE_SD target matched at "
      f"{cal['FINE_FOCUS_NOISE_SD']['dev']:+.2%}   (fact 501 says +0.20%)\n")
out["fact500"] = {"fine_reg_sd": fine_reg_sd, "fine_reg_sem": fine_reg_sem,
                  "k_honest": k_honest, "k_claimed": k_claimed,
                  "overstatement": k_claimed / k_honest}
out["fact501"] = {"coarse_unreg_sd": coarse_unreg_sd,
                  "dev_vs_focus": pct(coarse_unreg_sd, FOCUS_NOISE_SD),
                  "dev_vs_fine": cal["FINE_FOCUS_NOISE_SD"]["dev"]}

# ------------------------------------------------------------- facts 509/510
print("=" * 78)
print("FACTS 509 / 510 - the pending M17+M42 triple, arm by arm, all under reg8")
print("=" * 78)
arms = {}
for label, op, radius in [
    ("|grad|   w13 (shipped)", op_tenengrad, 13),
    ("|grad|   w11 (radius alone)", op_tenengrad, 11),
    ("|grad|^2 w13 (operator alone)", op_tenengrad_sq, 13),
    ("|grad|^2 w11 (the joint edit)", op_tenengrad_sq, 11),
]:
    sd, sem, _ = measure(op, radius, True)
    arms[label] = {"sd": sd, "sem": sem, "k": sd / FOCUS_NOISE_SD}
    print(f"  {label:<32}{sd:>12.6f} +/- {sem:.6f}   k = {sd / FOCUS_NOISE_SD:.4f}")
base = arms["|grad|   w13 (shipped)"]["sd"]
kr = arms["|grad|   w11 (radius alone)"]["sd"] / base
ko = arms["|grad|^2 w13 (operator alone)"]["sd"] / base
kj = arms["|grad|^2 w11 (the joint edit)"]["sd"] / base
print()
print(f"  k measured against the SHIPPED ARM (not the crate constant), which is")
print(f"  the ratio fact 510 is about:")
print(f"    radius alone   {kr:.4f}   fact 510 says 1.125")
print(f"    operator alone {ko:.4f}   fact 510 says 1.364")
print(f"    joint          {kj:.4f}   fact 510 says 1.528")
print(f"    product/joint  {kr * ko / kj:+.4%}   fact 510 says +0.47%")
print()
print(f"  and against the crate constant 0.015214 (fact 509's k):")
print(f"    joint k = {arms['|grad|^2 w11 (the joint edit)']['k']:.4f}"
      f"   fact 509 says 1.528, SD 0.023249")
out["facts509_510"] = {"arms": arms, "radius_alone": kr, "operator_alone": ko,
                       "joint": kj, "product_over_joint": kr * ko / kj - 1.0}

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "01-operator-noise.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {p}")
