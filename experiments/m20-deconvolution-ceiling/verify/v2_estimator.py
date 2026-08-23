"""M20 verification -- Gate 2: the estimator algebra, derived independently.

Route 1: analytic (Sherman-Morrison / matrix inversion lemma) checked against a brute
         numerical matrix inverse at random complex h -- no Monte Carlo involved.
Route 2: my own Monte Carlo with empirical normal equations.
Route 3: a gradient-based optimiser (L-BFGS-B on the 2K real parameters), which is a
         different family from the author's Nelder-Mead.

Then the gain-over-selection shorthand, solved in closed form rather than measured.
"""
import numpy as np
from scipy.optimize import minimize

rng = np.random.default_rng(987654321)


def wiener_closed(h, S, sigma2):
    """L_hat = sum_k conj(h_k) y_k / (sum|h|^2 + sigma^2/S).  Returned as the vector a
    with L_hat = a @ y."""
    return np.conj(h) / ((np.abs(h) ** 2).sum() + sigma2 / S)


def wiener_bruteforce(h, S, sigma2):
    """a = (R_yy^-1 r)^H via an explicit numerical inverse of R_yy = S h h^H + sigma^2 I."""
    K = h.size
    R = S * np.outer(h, np.conj(h)) + sigma2 * np.eye(K)
    r = S * h                       # E[y L*]
    w = np.linalg.solve(R, r)       # L_hat = w^H y
    return np.conj(w)               # as a @ y


def mmse_closed(h, S, sigma2):
    return 1.0 / (1.0 / S + (np.abs(h) ** 2).sum() / sigma2)


def main():
    print("=" * 78)
    print("GATE 2.1 -- ANALYTIC derivation, no Monte Carlo")
    print("=" * 78)
    print("y = h L + n,  L ~ CN(0,S),  n ~ CN(0, sigma^2 I)")
    print("R_yy = S h h^H + sigma^2 I ;  r_yL = E[y L*] = S h")
    print("Sherman-Morrison: (sigma^2 I + S h h^H)^-1 = (1/sigma^2)[I - S h h^H/(sigma^2 + S|h|^2)]")
    print("  => w = R^-1 r = S h / (sigma^2 + S |h|^2)")
    print("  => L_hat = w^H y = sum_k h_k* y_k / (sum_k |h_k|^2 + sigma^2/S)   <-- the proposed form")
    print("  => MMSE  = S - r^H R^-1 r = 1/(1/S + sum|h|^2/sigma^2)")
    print()
    worst_w = 0.0
    worst_e = 0.0
    for t in range(200):
        K = int(rng.integers(2, 9))
        h = rng.normal(size=K) + 1j * rng.normal(size=K)
        S = float(np.exp(rng.normal(0, 1.5)))
        s2 = float(np.exp(rng.normal(0, 1.5)))
        a1 = wiener_closed(h, S, s2)
        a2 = wiener_bruteforce(h, S, s2)
        worst_w = max(worst_w, float(np.max(np.abs(a1 - a2)) / np.max(np.abs(a2))))
        # MMSE from the brute route: S - r^H R^-1 r
        R = S * np.outer(h, np.conj(h)) + s2 * np.eye(K)
        r = S * h
        e2 = float(np.real(S - np.conj(r) @ np.linalg.solve(R, r)))
        worst_e = max(worst_e, abs(mmse_closed(h, S, s2) - e2) / e2)
    print(f"  200 random (K, h, S, sigma^2): worst relative weight error {worst_w:.3e}")
    print(f"                                 worst relative MMSE error   {worst_e:.3e}")
    print("  VERDICT: the proposed estimator IS the MMSE linear estimator. Exact, not numeric.")
    print()

    print("=" * 78)
    print("GATE 2.2 -- my own Monte Carlo, three routes (2nd/3rd assume nothing)")
    print("=" * 78)
    print(f"{'trial':>5} | {'A closed form':>14} {'B normal eq':>12} {'C L-BFGS-B':>12} {'analytic MMSE':>14} | {'A/B':>10} {'A/C':>10}")
    for trial in range(3):
        K = 5
        h = (rng.normal(size=K) + 1j * rng.normal(size=K)) * 0.5
        S, s2, N = 3.7, 0.9, 400000
        L = np.sqrt(S / 2) * (rng.normal(size=N) + 1j * rng.normal(size=N))
        Y = h[:, None] * L[None, :] + np.sqrt(s2 / 2) * (
            rng.normal(size=(K, N)) + 1j * rng.normal(size=(K, N)))

        def mse(a):                       # L_hat = a @ y
            return float(np.mean(np.abs(a @ Y - L) ** 2))

        aA = wiener_closed(h, S, s2)
        Ryy = (Y @ Y.conj().T) / N
        rr = (Y @ np.conj(L)) / N
        aB = np.conj(np.linalg.solve(Ryy, rr))

        def obj(v):
            return mse(v[:K] + 1j * v[K:])

        res = minimize(obj, np.zeros(2 * K), method="L-BFGS-B",
                       options=dict(maxiter=50000, ftol=1e-16, gtol=1e-14))
        aC = res.x[:K] + 1j * res.x[K:]
        eA, eB, eC = mse(aA), mse(aB), mse(aC)
        print(f"{trial:>5} | {eA:>14.6f} {eB:>12.6f} {eC:>12.6f} {mmse_closed(h,S,s2):>14.6f} | "
              f"{eA/eB:>10.7f} {eA/eC:>10.7f}")
    print()

    print("=" * 78)
    print("GATE 2.3 -- the gain shorthand, SOLVED not measured")
    print("=" * 78)
    h = np.array([0.9, 0.7, 0.7, 0.4, 0.4])
    S, s2 = 1.0, 0.05
    sH2 = float((h ** 2).sum())
    mx = float(h.max())
    print(f"  h = {h},  S = {S},  sigma^2 = {s2}")
    print(f"  sum|H|^2 = {sH2:.4f}   max|H| = {mx:.4f}")
    mse_w = mmse_closed(h + 0j, S, s2)
    mse_sel_inv = s2 / mx ** 2                       # inverse-filtered best frame
    mse_sel_wie = 1.0 / (1.0 / S + mx ** 2 / s2)     # single-frame WIENER on best frame
    mse_mf = s2 / sH2                                # matched filter, no prior
    print(f"  MSE multi-frame Wiener      = {mse_w:.6f}")
    print(f"  MSE selection (inv-filter)  = {mse_sel_inv:.6f}")
    print(f"  MSE selection (1-frame Wie) = {mse_sel_wie:.6f}")
    print(f"  MSE matched filter (no prior)= {mse_mf:.6f}")
    print()
    print(f"  shorthand sqrt(sum|H|^2)/max|H|          = {np.sqrt(sH2)/mx:.6f}")
    print(f"  reviewer's sqrt(sum|H|^2)                = {np.sqrt(sH2):.6f}")
    print(f"  EXACT sqrt(MSE_sel_inv / MSE_wiener)     = {np.sqrt(mse_sel_inv/mse_w):.6f}   "
          f"(report measured 1.6294)")
    print(f"  EXACT sqrt(MSE_sel_wie / MSE_wiener)     = {np.sqrt(mse_sel_wie/mse_w):.6f}")
    print(f"  EXACT sqrt(MSE_sel_inv / MSE_mf)         = {np.sqrt(mse_sel_inv/mse_mf):.6f}   "
          f"<-- equals the shorthand EXACTLY")
    print()
    print("  Algebraic decomposition of the residual:")
    print("    sqrt(MSE_sel_inv/MSE_wiener) = sqrt( sum|H|^2/max|H|^2 + sigma^2/(S max|H|^2) )")
    lhs = np.sqrt(sH2 / mx ** 2 + s2 / (S * mx ** 2))
    print(f"    check: {lhs:.6f}  vs  {np.sqrt(mse_sel_inv/mse_w):.6f}")
    print(f"    excess over shorthand = {(lhs/(np.sqrt(sH2)/mx)-1)*100:+.3f}%   "
          f"(report attributes 0.95% to the baseline choice)")
    print()
    print("  Test of the report's attribution: if the residual were the inverse-filter")
    print("  baseline, then using a single-frame WIENER baseline should REMOVE it.")
    r_fair = np.sqrt(mse_sel_wie / mse_w) / (np.sqrt(sH2) / mx)
    print(f"    fair-baseline gain / shorthand = {r_fair:.6f}  ({(r_fair-1)*100:+.3f}%)")
    print("    -> it overshoots to the OTHER side. The residual is the finite prior S,")
    print("       not the baseline. Driving S -> inf should send it to exactly 0:")
    for Sv in (1.0, 10.0, 1e3, 1e6):
        g = np.sqrt((s2 / mx ** 2) / (1.0 / (1.0 / Sv + sH2 / s2)))
        print(f"      S = {Sv:>9.0e}: gain = {g:.6f}   excess {(g/(np.sqrt(sH2)/mx)-1)*100:+.4f}%")
    print()

    print("=" * 78)
    print("GATE 2.4 -- positive control: wrong estimators must lose")
    print("=" * 78)
    N = 400000
    L = np.sqrt(S / 2) * (rng.normal(size=N) + 1j * rng.normal(size=N))
    Y = (h + 0j)[:, None] * L[None, :] + np.sqrt(s2 / 2) * (
        rng.normal(size=(5, N)) + 1j * rng.normal(size=(5, N)))

    def mse(a):
        return float(np.mean(np.abs(a @ Y - L) ** 2))

    aW = wiener_closed(h + 0j, S, s2)
    aSel = np.zeros(5, complex); aSel[0] = 1.0 / h[0]
    aMean = np.ones(5) / h.sum() + 0j
    print(f"  Wiener multi-frame : {mse(aW):.6f}  (analytic {mse_w:.6f})")
    print(f"  selection inv-filt : {mse(aSel):.6f}  ratio {mse(aSel)/mse(aW):.3f}x worse "
          f"(report 2.655x; analytic {mse_sel_inv/mse_w:.3f}x)")
    print(f"  gain-matched mean  : {mse(aMean):.6f}  ratio {mse(aMean)/mse(aW):.3f}x worse "
          f"(report 1.124x)")


if __name__ == "__main__":
    main()
