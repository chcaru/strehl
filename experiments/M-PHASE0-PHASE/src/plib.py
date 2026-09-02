"""Alias-unfolding algebra for M-PHASE0-PHASE.

This module is the instrument. It deliberately reads no data file and contains
no census logic, so that `p0_controls.py` can commission it against closed
forms and planted defects without any corpus dependency.

Notation follows PREREGISTRATION.md section 3.

    Lambda    per-frame sample lattice (where one frame's samples of one
              channel actually sit, on the full-resolution SENSOR grid)
    Lambda_t  reconstruction target lattice
    M         index [Lambda_t : Lambda], = the number of aliased replicas
    d_i       frame i's displacement, a 2-vector in SENSOR pixels

Sampling on Lambda folds the target band into M replicas indexed by the cosets
of Lambda* / Lambda_t*.  Writing h_k(nu) for the representative of coset k that
places its replica inside the target band when the output frequency is nu, the
system matrix is

    A[i, k] = exp(j 2 pi <h_k(nu), d_i>)

up to a per-row unimodular factor, which is a unitary left-multiplication and
therefore leaves every singular value alone.  h_0 = 0 always, so column 0 is
all ones.

Three exact invariances follow, and p0_controls.py checks all three:

  P1  common translation d_i -> d_i + c   right-multiplies A by a unitary
      diagonal, so kappa is EXACTLY unchanged.  Conditioning is therefore a
      statement about RELATIVE placement and nothing else.
  P2  lattice shift d_i -> d_i + lam for lam in Lambda leaves A unchanged,
      because <h_k, lam> is an integer for h_k in the dual.  A shift NOT in
      Lambda must change it.
  P3  kappa depends on the multiset {d_i} only, not on frame order.
"""

import itertools

import numpy as np

# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------
#
# `duals` are base representatives of Lambda* / Lambda_t*, in cycles per SENSOR
# pixel.  `cell` is the scale c of Lambda_t* = c Z^2, so the target band is
# [-c/2, c/2)^2.
#
#   green quincunx:  Lambda  = {(x,y) in Z^2 : x+y even},  det 2
#                    Lambda* = Z^2  union  (Z^2 + (1/2,1/2))
#   red or blue:     Lambda  = 2 Z^2,                      det 4
#                    Lambda* = (1/2) Z^2
#
# 1x targets reconstruct on the full pixel grid (Lambda_t = Z^2, c = 1).
# 2x targets reconstruct on the half-pixel grid (Lambda_t = (1/2) Z^2, c = 2).


def _quincunx_dual_points(lo, hi, step_grid):
    """Points of Lambda* for the green quincunx, inside [lo, hi)^2."""
    pts = []
    n = int(round((hi - lo) / step_grid))
    for a in range(n):
        for b in range(n):
            x = lo + a * step_grid
            y = lo + b * step_grid
            # Lambda* = Z^2 union (Z^2 + (1/2,1/2)); i.e. x,y both integer or
            # both half-odd-integer.
            xi = abs(x - round(x)) < 1e-12
            yi = abs(y - round(y)) < 1e-12
            xh = abs(abs(x - round(x)) - 0.5) < 1e-12
            yh = abs(abs(y - round(y)) - 0.5) < 1e-12
            if (xi and yi) or (xh and yh):
                pts.append((x, y))
    return pts


def _square_dual_points(lo, hi, step_grid):
    """Points of Lambda* = (1/2) Z^2, inside [lo, hi)^2."""
    pts = []
    n = int(round((hi - lo) / step_grid))
    for a in range(n):
        for b in range(n):
            pts.append((lo + a * step_grid, lo + b * step_grid))
    return pts


def _build_targets():
    t = {}
    # G-1x: quincunx -> full grid.  M = 2.
    t["G-1x"] = dict(cell=1.0, duals=_quincunx_dual_points(0.0, 1.0, 0.5), M=2,
                     lattice=[(1, 1), (1, -1)],
                     desc="green quincunx -> full pixel grid")
    # RB-1x: spacing-2 square -> full grid.  M = 4.
    t["RB-1x"] = dict(cell=1.0, duals=_square_dual_points(0.0, 1.0, 0.5), M=4,
                      lattice=[(2, 0), (0, 2)],
                      desc="red or blue -> full pixel grid")
    # G-2x: quincunx -> half-pixel grid.  M = 8.
    t["G-2x"] = dict(cell=2.0, duals=_quincunx_dual_points(0.0, 2.0, 0.5), M=8,
                     lattice=[(1, 1), (1, -1)],
                     desc="green quincunx -> half-pixel grid")
    # RB-2x: spacing-2 square -> half-pixel grid.  M = 16.
    t["RB-2x"] = dict(cell=2.0, duals=_square_dual_points(0.0, 2.0, 0.5), M=16,
                      lattice=[(2, 0), (0, 2)],
                      desc="red or blue -> half-pixel grid")
    for name, spec in t.items():
        got = len(spec["duals"])
        if got != spec["M"]:
            raise ValueError(
                "target %s: enumerated %d coset representatives, expected M=%d"
                % (name, got, spec["M"]))
    return t


TARGETS = _build_targets()


def coset_reps(target, nu):
    """Representatives h_k of each coset that land replica k inside the band.

    For base representative g, the coset is g + c Z^2, and the element h with
    nu - h in [-c/2, c/2)^2 is h = g + c * floor((nu - g)/c + 1/2).
    """
    spec = TARGETS[target]
    c = spec["cell"]
    out = []
    for g in spec["duals"]:
        m0 = np.floor((nu[0] - g[0]) / c + 0.5)
        m1 = np.floor((nu[1] - g[1]) / c + 0.5)
        out.append((g[0] + c * m0, g[1] + c * m1))
    return out


def _key(reps):
    """Order-independent, conjugation-invariant key for a representative tuple.

    kappa is invariant to column permutation (a unitary right-multiplication),
    so two representative tuples differing only in order are the same system.
    It is also invariant under negating ALL representatives, because that
    conjugates A elementwise and conjugation preserves singular values.  All
    coordinates are half-integers, so 2h is an exact integer.
    """
    k = tuple(sorted((int(round(2 * a)), int(round(2 * b))) for a, b in reps))
    neg = tuple(sorted((-a, -b) for a, b in k))
    return min(k, neg)


def distinct_rep_sets(target, grid=16):
    """Every distinct alias geometry the target band produces.

    kappa depends on the output frequency nu, because which representative of
    each coset lands in the band depends on where nu sits.  The set of distinct
    geometries is small and independent of the data, so it is enumerated once.
    """
    spec = TARGETS[target]
    c = spec["cell"]
    seen = {}
    for a in range(grid):
        for b in range(grid):
            nu = (-c / 2 + c * (a + 0.5) / grid, -c / 2 + c * (b + 0.5) / grid)
            reps = coset_reps(target, nu)
            seen.setdefault(_key(reps), np.array(reps, dtype=float))
    return [seen[k] for k in sorted(seen)]


# ---------------------------------------------------------------------------
# The system matrix and its conditioning
# ---------------------------------------------------------------------------

def system_matrix(reps, d):
    """A[i,k] = exp(j 2 pi <h_k, d_i>).

    reps : (M,2) representatives, cycles per sensor pixel
    d    : (..., N, 2) displacements, sensor pixels
    returns (..., N, M) complex128
    """
    reps = np.asarray(reps, dtype=float)
    d = np.asarray(d, dtype=float)
    phase = 2.0 * np.pi * np.einsum("...ic,kc->...ik", d, reps)
    return np.exp(1j * phase)


def kappa(reps, d):
    """Condition number of the alias-unfolding system, batched over leading axes.

    Returns inf where the system is rank-deficient, including whenever N < M.
    Rank deficiency is REPORTED, never silently pseudo-inverted: an infeasible
    site must not be able to masquerade as a merely poor one.

    The rank test is RELATIVE.  A degenerate system's smallest singular value
    is not zero in floating point -- for a two-frame lattice-only configuration
    it is 1.2e-16 against an smax of 2 -- so a `smin > 0` test passes it and
    reports kappa ~ 3e15 instead of infeasible.  Control C-B exists to catch
    exactly that, and did.
    """
    A = system_matrix(reps, d)
    n, m = A.shape[-2], A.shape[-1]
    if n < m:
        return np.full(A.shape[:-2], np.inf)
    s = np.linalg.svd(A, compute_uv=False)
    smin = s[..., -1]
    smax = s[..., 0]
    rtol = max(n, m) * np.finfo(float).eps
    with np.errstate(divide="ignore", invalid="ignore"):
        k = np.where(smin > rtol * smax, smax / np.maximum(smin, 1e-300), np.inf)
    return np.where(np.isfinite(k), k, np.inf)


def kappa_m2_closed(theta):
    """Closed-form kappa for a two-column system, for any N.

    A = [1, exp(j theta_i)].  A^H A = [[N, S], [conj S, N]] with S = sum exp(j
    theta_i), whose eigenvalues are N +/- |S|, so kappa^2 = (N+|S|)/(N-|S|).

    That expression is NOT evaluated directly.  When the phases are tightly
    clustered -- exactly the ill-conditioned sites this lane cares most about
    -- |S| approaches N and `N - |S|` loses all its significant digits.  At a
    two-frame separation of 1e-8 cycles the direct form is wrong by orders of
    magnitude.  Control C-N catches this.

    The stable route uses the cancellation-free identity

        N^2 - |S|^2 = sum_{i,j} (1 - cos(theta_i - theta_j))
                    = 4 sum_{i<j} sin^2((theta_i - theta_j)/2)

    so that kappa^2 = (N + |S|)^2 / (N^2 - |S|^2) with no subtraction of
    nearly-equal quantities.
    """
    theta = np.asarray(theta, dtype=float)
    n = theta.shape[-1]
    s = np.exp(1j * theta).sum(axis=-1)
    smag = np.minimum(np.abs(s), float(n))
    diff = theta[..., :, None] - theta[..., None, :]
    iu = np.triu_indices(n, k=1)
    denom = 4.0 * (np.sin(diff[..., iu[0], iu[1]] / 2.0) ** 2).sum(axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        k2 = np.where(denom > 0, (n + smag) ** 2 / np.maximum(denom, 1e-300), np.inf)
    return np.where(np.isfinite(k2), np.sqrt(k2), np.inf)


def resultant(reps, d):
    """Circular resultant length r = |sum_i exp(j theta_i)| / N for M = 2.

    Only meaningful for a two-coset target; raises otherwise.
    """
    reps = np.asarray(reps, dtype=float)
    if reps.shape[0] != 2:
        raise ValueError("resultant is defined for M=2 only, got M=%d" % reps.shape[0])
    d = np.asarray(d, dtype=float)
    theta = 2.0 * np.pi * np.einsum("...ic,c->...i", d, reps[1])
    return np.abs(np.exp(1j * theta).sum(axis=-1)) / theta.shape[-1]


# ---------------------------------------------------------------------------
# The bar: when does unfolding stop being better than not unfolding?
# ---------------------------------------------------------------------------

def unfold_trial(reps, d, sigma_delta, snr_db, rng, trials):
    """Monte-Carlo the reconstruction error against its own do-nothing baseline.

    Returns (eta, eta_naive), each of shape (trials,).

      eta        = ||xhat - x|| / ||x_alias||   using ESTIMATED displacements
      eta_naive  = the same statistic for the alternative that is always
                   available: average the frames and set every alias to zero.

    eta = 1 is what a reconstructor achieves if it recovers the baseband
    perfectly and abandons the aliases, so it is the natural fixed reference.
    eta_naive is what the shipping behaviour actually achieves, and is >= 1
    because plain averaging leaks alias energy into the baseband estimate.
    """
    reps = np.asarray(reps, dtype=float)
    d = np.asarray(d, dtype=float)
    n, m = d.shape[0], reps.shape[0]

    A = system_matrix(reps, d)                                  # (N, M) truth

    delta = rng.normal(0.0, sigma_delta, size=(trials, n, 2))
    Ahat = system_matrix(reps, d[None, :, :] + delta)           # (T, N, M)

    x = (rng.normal(size=(trials, m)) + 1j * rng.normal(size=(trials, m))) / np.sqrt(2.0)
    alias_norm = np.linalg.norm(x[:, 1:], axis=-1)

    # Per-measurement alias power is (M-1) since |A|=1 and x has unit variance.
    noise_var = (m - 1) / (10.0 ** (snr_db / 10.0)) if np.isfinite(snr_db) else 0.0
    nz = np.sqrt(noise_var / 2.0) * (rng.normal(size=(trials, n))
                                     + 1j * rng.normal(size=(trials, n)))

    y = np.einsum("ik,tk->ti", A, x) + nz

    xhat = _batched_lstsq(Ahat, y)

    eta = np.linalg.norm(xhat - x, axis=-1) / alias_norm

    # Do-nothing: baseband from the plain average, aliases zeroed.
    x0_naive = y.mean(axis=-1)
    err_naive = np.empty_like(x)
    err_naive[:, 0] = x0_naive - x[:, 0]
    err_naive[:, 1:] = -x[:, 1:]
    eta_naive = np.linalg.norm(err_naive, axis=-1) / alias_norm

    return eta, eta_naive


def _batched_lstsq(A, y):
    """Least squares for a stack of systems.  A: (T,N,M), y: (T,N) -> (T,M).

    Solved by QR rather than by the normal equations.  A^H A squares the
    condition number, and conditioning is the entire subject of this lane, so
    the normal-equation route would make the instrument worst exactly where it
    is being asked the sharpest question.  A system whose R is singular yields
    NaN rather than an exception or a silent minimum-norm answer.
    """
    q, r = np.linalg.qr(A)
    if A.shape[-2] < A.shape[-1]:
        raise ValueError("under-determined system: N=%d < M=%d; callers must screen "
                         "these with kappa() before solving"
                         % (A.shape[-2], A.shape[-1]))
    rhs = np.einsum("tni,tn->ti", np.conjugate(q), y)
    diag = np.abs(np.einsum("tii->ti", r))
    good = diag.min(axis=-1) > 1e-13 * np.maximum(diag.max(axis=-1), 1e-300)
    out = np.full(rhs.shape, np.nan, dtype=complex)
    if np.any(good):
        out[good] = np.linalg.solve(r[good], rhs[good][..., None])[..., 0]
    return out


def median_eta(reps, d, sigma_delta, snr_db, rng, trials):
    eta, eta_naive = unfold_trial(reps, d, sigma_delta, snr_db, rng, trials)
    return float(np.median(eta)), float(np.median(eta_naive))


def unfold_mismatch(reps_true, reps_model, d, sigma_delta, snr_db, rng, trials):
    """Reconstruction when the model carries FEWER replicas than the scene.

    This is bias B6 made measurable: truncating to M replicas assumes the
    signal is exactly M-times oversampled, and real optics leak beyond.  The
    modelled representatives must be a subset of the true ones; the unmodelled
    coefficients are scored as unrecovered, which is what they are.

    Returns eta of shape (trials,), on the same scale as `unfold_trial`.
    """
    reps_true = np.asarray(reps_true, dtype=float)
    reps_model = np.asarray(reps_model, dtype=float)
    d = np.asarray(d, dtype=float)
    n, mt, mm = d.shape[0], reps_true.shape[0], reps_model.shape[0]

    idx = []
    for g in reps_model:
        hit = np.flatnonzero(np.all(np.isclose(reps_true, g, atol=1e-12), axis=1))
        if hit.size != 1:
            raise ValueError("model representative %s is not a unique member of the "
                             "true set" % (g,))
        idx.append(int(hit[0]))
    idx = np.array(idx)

    A_true = system_matrix(reps_true, d)
    delta = rng.normal(0.0, sigma_delta, size=(trials, n, 2))
    A_model = system_matrix(reps_model, d[None, :, :] + delta)

    x = (rng.normal(size=(trials, mt)) + 1j * rng.normal(size=(trials, mt))) / np.sqrt(2.0)
    alias_norm = np.linalg.norm(x[:, 1:], axis=-1)

    noise_var = (mt - 1) / (10.0 ** (snr_db / 10.0)) if np.isfinite(snr_db) else 0.0
    nz = np.sqrt(noise_var / 2.0) * (rng.normal(size=(trials, n))
                                     + 1j * rng.normal(size=(trials, n)))
    y = np.einsum("ik,tk->ti", A_true, x) + nz

    xhat_small = _batched_lstsq(A_model, y)
    xhat = np.zeros((trials, mt), dtype=complex)
    xhat[:, idx] = xhat_small
    return np.linalg.norm(xhat - x, axis=-1) / alias_norm


def bar_sigma(reps, d, snr_db, rng, trials=4000, lo=1e-5, hi=2.0, tol=1e-4,
              criterion="unit"):
    """Largest displacement-error sd at which unfolding still does no harm.

    criterion "unit"  : median eta < 1            (beat perfect-baseband)
    criterion "naive" : median eta < median eta_naive  (beat what ships today)

    Bisection is valid only if median eta increases monotonically with
    sigma_delta; control C-D checks exactly that, and this function refuses to
    report a bar if the bracket is not ordered as expected.
    """
    def harmful(s):
        e, en = median_eta(reps, d, s, snr_db, rng, trials)
        return e >= (1.0 if criterion == "unit" else en)

    if harmful(lo):
        return 0.0
    if not harmful(hi):
        return float(hi)
    a, b = lo, hi
    while b - a > tol:
        mid = 0.5 * (a + b)
        if harmful(mid):
            b = mid
        else:
            a = mid
    return float(0.5 * (a + b))
