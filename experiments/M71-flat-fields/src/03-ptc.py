"""M71 step 03 -- photon transfer curve from temporal variance. Deliverable 2.

PR-3a / PR-3b / PR-3c are scored here, against the thresholds fixed in
data/01-preregistration.json before any pixel was read.

Why this PTC is immune to the paper-texture confound
----------------------------------------------------
The statistic is the PER-PIXEL TEMPORAL variance across the 20 frames of a
group. PRNU and paper texture are both FIXED across those 20 frames, so both
cancel identically. Nothing about how much paper is resolved can move this
number. That is what makes deliverable 2 independent of deliverable 1, and it
is why PR-3c can use "is the temporal PTC quadratic?" as a drift detector
rather than as a PRNU measurement.

The Jensen correction, which is NOT optional on this data
---------------------------------------------------------
Every frame is divided by its own spatial mean m_f before the temporal
accumulation (mandatory drift normalisation). Write u_f = m_f / mbar, so
E[u] = 1. At a pixel whose signal at the group's mean level is S,

    Var_f( x_f / m_f ) * mbar^2  =  g*S*E[1/u] + (RN*g)^2 * E[1/u^2]

By Jensen E[1/u] >= 1, so normalisation BIASES THE FITTED GAIN UPWARD by
approximately CV^2(m). On this capture the illumination ramps by up to 39%
inside a single 20-frame group, so CV^2 reaches ~1.3% -- small against the
+-10% gate of PR-3a, but larger than the statistical error by two orders of
magnitude, and free to correct because m_f is recorded for every frame. The fit
below carries A1_k = E[1/u] and A2_k = E[1/u^2] per group as known
coefficients rather than absorbing them into the answer.

Error bars come from RE-DRAWING (discipline 375), not from subdividing one
measurement. The four independent draws available here are {CPL-on, CPL-off}
x {G1, G2}; M48c is the standing example of why tiles of one measurement give
an error bar that is too small by more than the effect being measured.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "out" / "cache"
OUT = HERE / "data" / "03-ptc.json"

PLANES = ("R", "G1", "G2", "B")
PRE = json.loads((HERE / "data" / "01-preregistration.json").read_text(encoding="utf-8"))
G_REF = PRE["constants"]["g_dn_per_e"]
RN_REF = PRE["constants"]["read_noise_e"]
N = 20


def tag_of(exp: float, half: str) -> str:
    # Must reproduce 02-decode-flats.py's naming exactly, including its
    # quirk that only exactly-representable unit fractions (0.125 -> 1/8)
    # collapse to a denominator.
    fr = Fraction(exp)
    return f"e{fr.denominator if fr.numerator == 1 else exp}-{half}"


def fit_linear(S, V, A1, A2, w):
    """Weighted LS of V = g*A1*S + b*A2. Linear in (g, b), so exact."""
    X = np.column_stack([A1 * S, A2])
    W = np.diag(w)
    XtW = X.T @ W
    beta = np.linalg.solve(XtW @ X, XtW @ V)
    resid = V - X @ beta
    dof = max(len(V) - 2, 1)
    cov = np.linalg.inv(XtW @ X) * (resid @ (W @ resid) / dof)
    return beta, np.sqrt(np.diag(cov)), resid


def fit_quadratic(S, V, A1, A2, w):
    """V = g*A1*S + b*A2 + c*S^2. c is a DRIFT detector, not PRNU (see header)."""
    X = np.column_stack([A1 * S, A2, S ** 2])
    W = np.diag(w)
    XtW = X.T @ W
    beta = np.linalg.solve(XtW @ X, XtW @ V)
    resid = V - X @ beta
    dof = max(len(V) - 3, 1)
    cov = np.linalg.inv(XtW @ X) * (resid @ (W @ resid) / dof)
    return beta, np.sqrt(np.diag(cov))


def main() -> None:
    frames = json.loads((HERE / "data" / "02-frames.json").read_text(encoding="utf-8"))
    exposures = sorted({r["exp"] for r in frames})

    # ---- per-group-half, per-plane bookkeeping from the frame scalars only
    groups = {}
    for exp in exposures:
        for half in ("A", "B"):
            g = [r for r in frames if r["exp"] == exp and r["half"] == half]
            assert len(g) == N
            groups[(exp, half)] = g

    results = {}
    for plane in PLANES:
        pts = []
        for (exp, half), g in sorted(groups.items()):
            if max(r[f"clip_{plane}"] for r in g) > 0:
                continue                      # any clipped pixel voids the group
            tag = tag_of(exp, half)
            m = np.array([r[f"mean_{plane}"] for r in g], np.float64)
            mbar = m.mean()
            u = m / mbar
            A1 = float(np.mean(1.0 / u))
            A2 = float(np.mean(1.0 / u ** 2))
            mu = np.load(CACHE / f"{tag}-{plane}-mean.npy").astype(np.float64)
            v = np.load(CACHE / f"{tag}-{plane}-var.npy").astype(np.float64)
            S = mu * mbar
            V = v * mbar * mbar
            pts.append({"exp": exp, "half": half, "tag": tag, "mbar": mbar,
                        "A1": A1, "A2": A2, "cv": float(u.std(ddof=1)),
                        "_S": S, "_V": V})

        # ---- defect mask: one mask per plane, built ONCE from the highest clean
        # level, then applied to every level. Pixels whose temporal variance is
        # not in [0.25, 4] x the plane median there are excluded as defective.
        top = max(pts, key=lambda p: p["mbar"])
        med = float(np.median(top["_V"]))
        keep = (top["_V"] > 0.25 * med) & (top["_V"] < 4.0 * med)
        excluded = 1.0 - float(keep.mean())

        for p in pts:
            p["S"] = float(p["_S"][keep].mean())
            p["V"] = float(p["_V"][keep].mean())
            p["V_med"] = float(np.median(p["_V"][keep]))
            del p["_S"], p["_V"]

        S = np.array([p["S"] for p in pts])
        V = np.array([p["V"] for p in pts])
        A1 = np.array([p["A1"] for p in pts])
        A2 = np.array([p["A2"] for p in pts])
        w = 1.0 / V ** 2                       # relative weighting

        beta, err, resid = fit_linear(S, V, A1, A2, w)
        g_fit, b_fit = beta
        rn_fit = np.sqrt(max(b_fit, 0.0)) / g_fit
        qbeta, qerr = fit_quadratic(S, V, A1, A2, w)

        # uncorrected fit, to show what the Jensen correction is worth
        beta_u, _, _ = fit_linear(S, V, np.ones_like(A1), np.ones_like(A2), w)

        # separate draws: CPL-on half and CPL-off half fitted independently
        draws = {}
        for half in ("A", "B"):
            idx = [i for i, p in enumerate(pts) if p["half"] == half]
            if len(idx) >= 3:
                bh, eh, _ = fit_linear(S[idx], V[idx], A1[idx], A2[idx], w[idx])
                draws[half] = {"g": float(bh[0]), "g_err": float(eh[0]),
                               "b": float(bh[1]), "n_levels": len(idx),
                               "S_min": float(S[idx].min()), "S_max": float(S[idx].max())}

        results[plane] = {
            "n_levels": len(pts),
            "S_range": [float(S.min()), float(S.max())],
            "S_span_x": float(S.max() / S.min()),
            "excluded_fraction": excluded,
            "g": float(g_fit), "g_err": float(err[0]),
            "b": float(b_fit), "b_err": float(err[1]),
            "read_noise_e": float(rn_fit),
            "g_uncorrected": float(beta_u[0]),
            "jensen_shift_pct": float(100 * (beta_u[0] / g_fit - 1)),
            "resid_rel": [float(x) for x in resid / V],
            "quad_c": float(qbeta[2]), "quad_c_err": float(qerr[2]),
            "quad_g": float(qbeta[0]),
            "draws": draws,
            "points": pts,
        }
        print(f"\n=== {plane}: {len(pts)} clean levels, S {S.min():.0f}..{S.max():.0f} DN "
              f"({S.max() / S.min():.0f}x), {excluded * 100:.3f}% pixels excluded")
        for p, rr in zip(pts, resid / V):
            print(f"   1/{1 / p['exp']:6.1f} {p['half']}  S={p['S']:9.1f}  "
                  f"V={p['V']:10.2f}  A1={p['A1']:.5f} A2={p['A2']:.5f}  "
                  f"resid={rr * 100:+6.2f}%")
        print(f"   g = {g_fit:.6f} +- {err[0]:.6f} DN/e-   "
              f"({100 * (g_fit / G_REF - 1):+.2f}% vs profile {G_REF:.6f})")
        print(f"   b = {b_fit:.4f} DN^2 -> RN = {rn_fit:.3f} e- "
              f"(profile {RN_REF:.2f})")
        print(f"   Jensen correction moved g by {100 * (beta_u[0] / g_fit - 1):+.3f}%")
        print(f"   quadratic term c = {qbeta[2]:.3e} +- {qerr[2]:.3e} "
              f"-> sqrt(c) = {np.sqrt(max(qbeta[2], 0)) * 100:.4f}% "
              f"({qbeta[2] / qerr[2]:+.2f} sigma)")
        for h, d in draws.items():
            print(f"   draw {h}: g = {d['g']:.6f} +- {d['g_err']:.6f} "
                  f"({d['n_levels']} levels, {d['S_min']:.0f}..{d['S_max']:.0f} DN)")

    # ---- PR-3b, the two-greens null
    print("\n=== PR-3b two-greens null")
    ratio_all = results["G2"]["g"] / results["G1"]["g"]
    print(f"   g(G2)/g(G1) pooled = {ratio_all:.6f}")
    per_half = {}
    for half in ("A", "B"):
        if half in results["G1"]["draws"] and half in results["G2"]["draws"]:
            r = results["G2"]["draws"][half]["g"] / results["G1"]["draws"][half]["g"]
            per_half[half] = r
            print(f"   g(G2)/g(G1) draw {half} = {r:.6f}")
    if len(per_half) == 2:
        vals = list(per_half.values())
        spread = abs(vals[0] - vals[1]) / 2
        print(f"   half-to-half spread (re-draw error, discipline 375) = +-{spread:.6f}")
        print(f"   M68's analogous null for reference: 0.99937 +- 0.00511")
    results["_null_G2_over_G1"] = {"pooled": ratio_all, "per_half": per_half}

    for plane in PLANES:
        for p in results[plane]["points"]:
            p.pop("_S", None)
            p.pop("_V", None)
    OUT.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
