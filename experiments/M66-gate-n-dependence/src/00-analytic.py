"""M66 arm A - the analytic null, and the candidate corrected tolerances.

f_N(t) = integral phi(x) Phi(x+t)^(N-1) dx  is the probability that one frame of
N iid N(0,1) responses sits within t of the maximum. mean n_eff = N * f_N(t).

Exact anchors this must hit, used as the quadrature's own control:
  f_N(0)        = 1/N exactly       (only the argmax is within 0 of the max)
  N * f_N(0)    = 1 exactly         (this is gate 0, control K1, analytically)
  f_1(t)        = 1 for all t >= 0
"""

import json
import sys

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from m66 import GATES, N_GRID, OUT, banner, dump_constants  # noqa: E402

SQRT2 = float(np.sqrt(2.0))


def f_N(n, t):
    """P(max_j eps_j - eps_1 <= t) for n iid standard normals."""
    if n == 1:
        return 1.0
    val, err = quad(
        lambda x: norm.pdf(x) * np.exp((n - 1) * norm.logcdf(x + t)),
        -np.inf,
        np.inf,
        limit=400,
        epsabs=1e-13,
        epsrel=1e-13,
    )
    return float(val), float(err)


def f(n, t):
    r = f_N(n, t)
    return r if isinstance(r, float) else r[0]


def c_N(n):
    """E[max of n standard normals]."""
    val, _ = quad(
        lambda x: x * n * norm.pdf(x) * np.exp((n - 1) * norm.logcdf(x)),
        -np.inf,
        np.inf,
        limit=400,
        epsabs=1e-12,
        epsrel=1e-12,
    )
    return float(val)


def q_alpha(n, alpha):
    """Tolerance in sigma units giving null admission fraction 1 - alpha at N."""
    if n == 1:
        return 0.0
    target = 1.0 - alpha
    lo, hi = 0.0, 60.0
    if f(n, hi) < target:
        return float("inf")
    if f(n, lo) > target:
        return 0.0
    return float(brentq(lambda t: f(n, t) - target, lo, hi, xtol=1e-10, rtol=1e-12))


def monte_carlo(n, ts, draws, rng):
    """Independent check on the quadrature: fraction within t of the max."""
    out = {t: 0.0 for t in ts}
    block = max(1, int(4_000_000 // n))
    done = 0
    while done < draws:
        b = min(block, draws - done)
        e = rng.standard_normal((b, n))
        gap = e.max(axis=1, keepdims=True) - e
        for t in ts:
            out[t] += float((gap <= t).sum())
        done += b
    return {t: out[t] / (draws * n) for t in ts}


banner("M66 arm A - the analytic null. Constants parsed from the crate:")
dump_constants()

print("\nQuadrature control: f_N(0) must equal 1/N exactly (gate 0 admits the argmax only)")
worst0 = 0.0
for n in N_GRID:
    got = f(n, 0.0)
    worst0 = max(worst0, abs(got * n - 1.0))
print(f"  worst |N*f_N(0) - 1| over the N grid = {worst0:.3e}")
if worst0 > 1e-9:
    print("  QUADRATURE CONTROL FAILED - refusing to report anything else.")
    sys.exit(1)
print("  quadrature OK.\n")

rows = {}
banner("f_N(T*sqrt(2)) - null admitted FRACTION, and N*f_N - null admitted COUNT")
hdr = "  N    " + "".join(f"{'T=' + str(g):>22}" for g in GATES)
print(hdr)
for n in N_GRID:
    rec = {}
    line = f"  {n:<5}"
    for g in GATES:
        t = g * SQRT2
        frac = f(n, t)
        rec[g] = {"t_sigma": t, "frac": frac, "count": n * frac}
        line += f"  {frac:>9.6f} /{n * frac:>9.4f}"
    rows[n] = rec
    print(line)

print("\n  (each cell is  fraction / count)")

banner("E[max of N standard normals], and the tolerance that fixes the null rate")
print("  N      c_N=E[max]   q(alpha=.015)  q(alpha=.05)   q(alpha=.001)")
cn = {}
qa = {}
for n in N_GRID:
    c = c_N(n)
    cn[n] = c
    qa[n] = {a: q_alpha(n, a) for a in (0.015, 0.05, 0.001)}
    print(
        f"  {n:<6} {c:>10.5f}   {qa[n][0.015]:>12.5f}  {qa[n][0.05]:>12.5f}  {qa[n][0.001]:>12.5f}"
    )

banner("Monte Carlo cross-check of the quadrature (independent implementation)")
rng = np.random.default_rng(20260823)
mc = {}
DRAWS = 2_000_000
for n in (19, 30, 105, 299):
    ts = [g * SQRT2 for g in GATES]
    got = monte_carlo(n, ts, DRAWS, rng)
    mc[n] = {}
    for g in GATES:
        t = g * SQRT2
        pred = rows[n][g]["frac"]
        se = float(np.sqrt(max(pred * (1 - pred), 1e-12) / (DRAWS)))
        mc[n][g] = {"mc": got[t], "quad": pred, "se_per_draw": se}
        print(
            f"  N={n:<4} T={g:<4} quad {pred:.6f}   MC {got[t]:.6f}   "
            f"diff {got[t] - pred:+.6f}   (MC SE ~{se:.6f})"
        )

payload = {
    "gates": GATES,
    "n_grid": N_GRID,
    "quadrature_control_worst_abs_err": worst0,
    "rows": {str(k): {str(g): v for g, v in r.items()} for k, r in rows.items()},
    "c_N": {str(k): v for k, v in cn.items()},
    "q_alpha": {str(k): {str(a): b for a, b in v.items()} for k, v in qa.items()},
    "monte_carlo": {str(k): {str(g): v for g, v in r.items()} for k, r in mc.items()},
    "mc_draws": DRAWS,
}
OUT.mkdir(parents=True, exist_ok=True)
p = OUT / "00-analytic.json"
p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"\nwrote {p}")
