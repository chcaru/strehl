"""
M71 step 11 — follow-up demanded by the orchestrator's retraction of M68's
"partial correction is worse than none" claim.

Three questions, none of which need new pixels; everything here is computed from
data/03-ptc.json and data/05-kappa.json plus closed-form algebra.

  Q1  The AMENDED instruction. Not "is adding kappa alone worse than none" but:
      does adding kappa alone FLIP the sign of the residual error from
      conservative to over-confident, and if so at what signal levels?
      State the regime, not just the magnitude.

  Q2  M68 fact 39 volunteers that gain x 0.8396 is M61's number, never
      re-measured, and that "PRNU leakage into M61's tile variances remains
      unchecked by me". I measured kappa per plane, so I can check it. First
      structurally (what estimator did M61 use), then numerically (bound the
      leakage using my own kappa).

  Q3  If Q2 clears M61, my own g(B)/g(green) = 0.8699 vs M61's 0.8396 +- 0.0112
      is a 2.7 sigma tension with no PRNU explanation. Which of the two numbers
      is the fragile one? Test MY number's robustness to its own post-hoc
      level exclusions before pointing at anyone else's.

Sign convention used throughout:
    err = predicted_sigma / true_sigma - 1
    err > 0  => model predicts MORE noise than exists  => CONSERVATIVE
    err < 0  => model predicts LESS noise than exists  => OVER-CONFIDENT
"""
import json
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = HERE / "data"
OUT = DATA / "11-regime-and-m61.json"

# ---- inputs, all previously measured and committed -------------------------
ptc = json.load(open(DATA / "03-ptc.json"))
kap = json.load(open(DATA / "05-kappa.json"))

G_PROFILE = 0.2289377      # profile.rs ISO-100 green gain, DN/e-  (INHERITED)
SIGMA0 = 0.961538          # profile.rs (RN*g) in DN               (INHERITED)

g_G1, g_G2 = ptc["G1"]["g"], ptc["G2"]["g"]
G_MEAS = 0.5 * (g_G1 + g_G2)
G_ERR = 0.5 * np.hypot(ptc["G1"]["g_err"], ptc["G2"]["g_err"])

KAPPA = kap["kappa"] if "kappa" in kap else None
if KAPPA is None:  # tolerate either key spelling
    for k in ("kappa_headline", "kappa_green", "headline"):
        if k in kap:
            KAPPA = kap[k]
            break
KAPPA = float(KAPPA)
KAPPA_ERR = float(kap.get("kappa_spread", kap.get("kappa_err", 0.0)))

res = {"inputs": {"g_profile": G_PROFILE, "sigma0": SIGMA0,
                  "g_measured": G_MEAS, "g_measured_err": float(G_ERR),
                  "kappa": KAPPA, "kappa_spread": KAPPA_ERR,
                  "g_ratio_profile_over_measured": G_PROFILE / G_MEAS}}

print("=" * 78)
print("Q1  Does adding kappa alone flip the sign of the residual error?")
print("=" * 78)
print(f"profile gain {G_PROFILE:.7f} vs measured {G_MEAS:.7f} "
      f"-> profile is {100*(G_PROFILE/G_MEAS-1):+.3f}% HIGH")
print(f"kappa = {100*KAPPA:.4f}%")


def sig_ship(S, gp=G_PROFILE, s0=SIGMA0):
    """The model as shipped: shot + read, no PRNU."""
    return np.sqrt(gp * S + s0 ** 2)


def sig_ship_k(S, k, gp=G_PROFILE, s0=SIGMA0):
    """Shipped model with the PRNU term added and NOTHING else changed."""
    return np.sqrt(gp * S + s0 ** 2 + (k * S) ** 2)


def sig_true(S, k, gm=G_MEAS, s0=SIGMA0):
    """Best available truth: measured gain, measured PRNU."""
    return np.sqrt(gm * S + s0 ** 2 + (k * S) ** 2)


# kappa enters green LUMA reduced by sqrt(2): PRNU is independent between the
# two greens (M71 proved var(D) = 2 kappa^2), so averaging them halves its
# variance while the shot term also halves. Report both.
CASES = {"photosite": KAPPA, "green_luma": KAPPA / np.sqrt(2.0)}

S_grid = np.array([0, 50, 100, 200, 504, 1000, 2000, 4000, 8000, 12000, 15000],
                  float)

q1 = {}
for name, k in CASES.items():
    e_ship = sig_ship(S_grid) / sig_true(S_grid, k) - 1.0
    e_ship_k = sig_ship_k(S_grid, k) / sig_true(S_grid, k) - 1.0
    # analytic crossover of the SHIPPED model: where the missing PRNU term
    # exactly cancels the inflated gain.  (gp-gm)S = (kS)^2  ->  S = (gp-gm)/k^2
    S_cross = (G_PROFILE - G_MEAS) / (k * k)
    q1[name] = {"kappa_eff": k, "S_crossover_shipped": float(S_cross),
                "grid": [float(x) for x in S_grid],
                "err_shipped_pct": [float(100 * x) for x in e_ship],
                "err_shipped_plus_kappa_pct": [float(100 * x) for x in e_ship_k]}
    print(f"\n--- {name}: kappa_eff = {100*k:.4f}%,  "
          f"shipped model crosses to OVER-CONFIDENT at S = {S_cross:.0f} DN")
    print(f"{'S (DN)':>8} {'shipped':>12} {'shipped+kappa':>15}   regime")
    for S, a, b in zip(S_grid, e_ship, e_ship_k):
        reg = "conservative" if a >= 0 else "OVER-CONFIDENT"
        print(f"{S:8.0f} {100*a:+11.3f}% {100*b:+14.3f}%   shipped {reg}")

    # does shipped+kappa EVER go negative?  numerator-denominator = (gp-gm)*S,
    # so it is >= 0 for all S iff gp >= gm.  Verify numerically too.
    S_dense = np.linspace(0, 20000, 200001)
    worst = float((sig_ship_k(S_dense, k) / sig_true(S_dense, k) - 1.0).min())
    q1[name]["worst_err_shipped_plus_kappa_pct"] = 100 * worst
    q1[name]["shipped_plus_kappa_ever_overconfident"] = bool(worst < -1e-12)
    print(f"    worst-case error of shipped+kappa over S in [0,20000]: "
          f"{100*worst:+.4f}%  -> "
          f"{'FLIPS' if worst < -1e-12 else 'NEVER flips sign'}")

res["Q1"] = q1

# Sensitivity: the crossover depends on the gain error, which is the one thing
# a sceptic would attack. Recompute S_cross for a range of assumed gain errors,
# including 0 (profile gain exactly right) and fact 29's implied 5.0%.
sens = {}
for label, gm in (("profile_exact", G_PROFILE),
                  ("M71_measured_2.16pct_high", G_MEAS),
                  ("fact29_implied_5.0pct_high", G_PROFILE * 0.950)):
    row = {}
    for name, k in CASES.items():
        d = G_PROFILE - gm
        row[name] = float(d / (k * k)) if d > 0 else 0.0
    sens[label] = {"g_true": gm, "S_crossover": row}
    print(f"\n  sensitivity {label:>28}: g_true={gm:.6f} -> "
          + ", ".join(f"S*({n})={v:.0f} DN" for n, v in row.items()))
res["Q1_sensitivity"] = sens

print()
print("=" * 78)
print("Q2  Can PRNU leak into M61-E1's slope?  (M68 fact 39 left this unchecked)")
print("=" * 78)
# M61-E1 (M61 report L158-181): d = F_k - F_{k+1};  v = var(d)/2 per 8x8 tile.
# A fixed multiplicative pattern p cancels in d EXACTLY when the two frames sit
# at the same level. With a fractional photometric drift eps between adjacent
# frames the surviving PRNU term is eps*S*p, whose variance is (eps*S*kappa)^2.
# M61 reports v = var(d)/2, and the quantity it should equal is g*S. So:
#     relative bias of v  =  (eps*S*kappa)^2 / (2*g*S)  =  eps^2 * S * kappa^2/(2g)
S_ref = 2000.0
leak = {}
for eps in (0.001, 0.01, 0.05, 0.10, 0.50):
    b = eps ** 2 * S_ref * KAPPA ** 2 / (2 * G_MEAS)
    leak[f"eps_{eps}"] = float(100 * b)
    print(f"  adjacent-frame drift {100*eps:5.1f}%  ->  slope bias "
          f"{100*b:.6f}%  at S={S_ref:.0f} DN")
eps_for_1pct = float(np.sqrt(0.01 * 2 * G_MEAS / (S_ref * KAPPA ** 2)))
print(f"\n  drift required to bias M61's slope by 1%: eps = {100*eps_for_1pct:.0f}%")
print("  -> structurally impossible for adjacent frames in a stack.")
res["Q2"] = {"estimator": "M61-E1 temporal adjacent-frame difference, v=var(d)/2",
             "prnu_cancels_exactly_at_zero_drift": True,
             "S_ref": S_ref, "leak_pct_by_drift": leak,
             "drift_for_1pct_bias": eps_for_1pct,
             "verdict": "PRNU leakage cannot explain any part of M61's ratio"}

print()
print("=" * 78)
print("Q3  Is MY g(B) robust to its own level exclusions?")
print("=" * 78)


def fit_linear_local(S, V, A1, A2, w):
    """Same Jensen-corrected WLS as 03-ptc.py: V = g*S*A1 + b*A2."""
    X = np.column_stack([S * A1, A2])
    W = np.diag(w)
    XtW = X.T @ W
    cov = np.linalg.inv(XtW @ X)
    beta = cov @ (XtW @ V)
    resid = V - X @ beta
    dof = max(len(S) - 2, 1)
    s2 = float((w * resid ** 2).sum() / dof / np.mean(w))
    err = np.sqrt(np.diag(cov) * s2 / np.mean(w) * np.mean(w))
    err = np.sqrt(np.diag(cov * s2))
    return beta, err


def refit(plane, keep_mask=None):
    pts = ptc[plane]["points"]
    S = np.array([p["S"] for p in pts])
    V = np.array([p["V"] for p in pts])
    A1 = np.array([p["A1"] for p in pts])
    A2 = np.array([p["A2"] for p in pts])
    if keep_mask is not None:
        S, V, A1, A2 = S[keep_mask], V[keep_mask], A1[keep_mask], A2[keep_mask]
    w = 1.0 / V ** 2
    beta, err = fit_linear_local(S, V, A1, A2, w)
    return float(beta[0]), float(err[0]), len(S), float(S.min()), float(S.max())


g_ref, e_ref, n_ref, _, _ = refit("B")
print(f"  B as published: g={g_ref:.6f} +- {e_ref:.6f} over {n_ref} levels")
print(f"  (03-ptc.json records g={ptc['B']['g']:.6f}, n={ptc['B']['n_levels']})")

Sb = np.array([p["S"] for p in ptc["B"]["points"]])
order = np.argsort(Sb)
variants = {}
for cut in (5000, 6000, 7000, 8000, 9000, 10000, 1e9):
    m = Sb <= cut
    if m.sum() >= 4:
        g_, e_, n_, s0_, s1_ = refit("B", m)
        variants[f"S<={cut:.0f}"] = {"g": g_, "g_err": e_, "n": n_,
                                     "S_max": s1_}
        print(f"    B, S<={cut:<10.0f} n={n_:2d}  g={g_:.6f} +- {e_:.6f}")
# drop the k highest levels
for k in (1, 2, 3, 4):
    m = np.ones(len(Sb), bool)
    m[order[-k:]] = False
    g_, e_, n_, s0_, s1_ = refit("B", m)
    variants[f"drop_top_{k}"] = {"g": g_, "g_err": e_, "n": n_, "S_max": s1_}
    print(f"    B, drop top {k}    n={n_:2d}  g={g_:.6f} +- {e_:.6f}")

gs = np.array([v["g"] for v in variants.values()])
spread = float(gs.max() - gs.min())
print(f"\n  g(B) spread across {len(gs)} exclusion choices: {spread:.6f} "
      f"({100*spread/g_ref:.2f}% of the value)")
print(f"  quoted statistical error on g(B):              {e_ref:.6f}")
print(f"  -> exclusion choice is {spread/e_ref:.1f}x the statistical error")

# the same test on green, as the control: green should be stable
gG1, eG1, nG1, _, _ = refit("G1")
varG = {}
SG = np.array([p["S"] for p in ptc["G1"]["points"]])
oG = np.argsort(SG)
for k in (0, 1, 2, 3):
    m = np.ones(len(SG), bool)
    if k:
        m[oG[-k:]] = False
    g_, e_, n_, _, _ = refit("G1", m)
    varG[f"drop_top_{k}"] = {"g": g_, "g_err": e_, "n": n_}
    print(f"    G1 control, drop top {k}: n={n_:2d} g={g_:.6f} +- {e_:.6f}")
gsG = np.array([v["g"] for v in varG.values()])
spreadG = float(gsG.max() - gsG.min())
print(f"  g(G1) spread across the same treatment: {spreadG:.6f} "
      f"({100*spreadG/gG1:.2f}%)  <-- control")

ratios = {}
for key, v in variants.items():
    ratios[key] = v["g"] / G_MEAS
rvals = np.array(list(ratios.values()))
print(f"\n  g(B)/g(green) across exclusion choices: "
      f"{rvals.min():.4f} .. {rvals.max():.4f}")
print(f"  M61 fact 921: 0.8396 +- 0.0112  -> "
      f"{'INSIDE' if (rvals.min() <= 0.8396+0.0112 and rvals.max() >= 0.8396-0.0112) else 'OUTSIDE'} "
      f"my exclusion envelope")

res["Q3"] = {"g_B_published": g_ref, "g_B_err": e_ref,
             "variants": variants, "spread": spread,
             "spread_over_stat_err": spread / e_ref,
             "green_control_variants": varG, "green_control_spread": spreadG,
             "ratio_range": [float(rvals.min()), float(rvals.max())],
             "m61_ratio": 0.8396, "m61_err": 0.0112}

OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(f"\nwrote {OUT}")
