import numpy as np
from scipy.optimize import minimize
rng = np.random.default_rng(20260808)

print("=== Estimator check, redone. Three INDEPENDENT routes to the optimal weights. ===")
for trial in range(3):
    K = 5
    h = (rng.normal(size=K) + 1j*rng.normal(size=K)) * 0.5
    S = 3.7; sigma2 = 0.9
    N = 300000
    L  = np.sqrt(S/2)*(rng.normal(size=N) + 1j*rng.normal(size=N))
    nz = np.sqrt(sigma2/2)*(rng.normal(size=(K,N)) + 1j*rng.normal(size=(K,N)))
    Y  = h[:,None]*L[None,:] + nz

    def mse_of(w):                       # Lhat = w^H y
        return float(np.mean(np.abs(np.conj(w) @ Y - L)**2))

    # route A: the estimator under test
    wA = np.conj(h) / ((np.abs(h)**2).sum() + sigma2/S)
    wA = np.conj(wA)                     # express as w with Lhat = w^H y
    # route B: normal equations from EMPIRICAL moments (no model assumed)
    Ryy = (Y @ Y.conj().T)/N             # E[y y^H]
    r   = (Y @ np.conj(L))/N             # E[y L*]
    wB  = np.linalg.solve(Ryy, r)
    # route C: black-box numerical minimisation over the 2K real parameters
    def obj(v):
        w = v[:K] + 1j*v[K:]
        return mse_of(w)
    v0 = np.concatenate([np.real(wB)*0.3, np.imag(wB)*0.3])
    res = minimize(obj, v0, method="Nelder-Mead",
                   options=dict(maxiter=200000, maxfev=200000, xatol=1e-10, fatol=1e-12))
    wC = res.x[:K] + 1j*res.x[K:]

    eA, eB, eC = mse_of(wA), mse_of(wB), mse_of(wC)
    theory = 1.0/(1.0/S + (np.abs(h)**2).sum()/sigma2)
    print(f"  trial {trial}: A(proposed)={eA:.6f}  B(empirical normal eq)={eB:.6f}  "
          f"C(Nelder-Mead)={eC:.6f}  closed-form={theory:.6f}")
    print(f"            max|wA-wB| = {np.max(np.abs(wA-wB)):.3e}   A/B = {eA/eB:.8f}   A/C = {eA/eC:.8f}")

print()
print("=== POSITIVE CONTROL: a deliberately wrong estimator must lose ===")
K = 5
h = np.array([0.9, 0.7, 0.7, 0.4, 0.4]) + 0j
S, sigma2, N = 1.0, 0.05, 300000
L  = np.sqrt(S/2)*(rng.normal(size=N) + 1j*rng.normal(size=N))
nz = np.sqrt(sigma2/2)*(rng.normal(size=(K,N)) + 1j*rng.normal(size=(K,N)))
Y  = h[:,None]*L[None,:] + nz
def mse_of(w): return float(np.mean(np.abs(np.conj(w) @ Y - L)**2))
wW = np.conj(np.conj(h)/((np.abs(h)**2).sum() + sigma2/S))
wSel = np.zeros(K, complex); wSel[0] = np.conj(1.0/h[0])          # pure selection of the best frame
wMean = np.conj(np.ones(K)/ (h.sum()))                            # naive equal-weight mean, gain-matched
print(f"  Wiener multi-frame : {mse_of(wW):.6f}")
print(f"  selection (best frame only, inverse-filtered): {mse_of(wSel):.6f}   ratio {mse_of(wSel)/mse_of(wW):.3f}x worse")
print(f"  naive mean          : {mse_of(wMean):.6f}   ratio {mse_of(wMean)/mse_of(wW):.3f}x worse")
print(f"  amplitude gain of Wiener over selection = {np.sqrt(mse_of(wSel)/mse_of(wW)):.4f}")
print(f"  sqrt(sum|H|^2)/max|H| predicts            = {np.sqrt((np.abs(h)**2).sum())/np.abs(h).max():.4f}")
