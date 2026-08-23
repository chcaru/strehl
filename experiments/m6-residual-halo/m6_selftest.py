"""Unit-level proofs of the M6 estimator. Run this before believing any number.

Nothing here touches the camera. Every case has a closed-form or planted answer
and the test asserts the estimator recovers it. If this file does not print
`ALL PASS`, no number produced by `m6_measure.py` should be quoted.

    python m6_selftest.py
"""

from __future__ import annotations

import sys

import numpy as np

import m6_lib as L

FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def close(a, b, tol):
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# 1. The two-way fixed-effects fit must equal the explicit dummy regression
# ---------------------------------------------------------------------------


def dummy_reference(y, tile, pair, x):
    tiles, pairs = np.unique(tile), np.unique(pair)
    ti = np.searchsorted(tiles, tile)
    pi = np.searchsorted(pairs, pair)
    X = np.zeros((len(y), len(tiles) + len(pairs) - 1 + x.shape[1]))
    X[np.arange(len(y)), ti] = 1.0
    nz = pi > 0
    X[np.arange(len(y))[nz], len(tiles) + pi[nz] - 1] = 1.0
    X[:, len(tiles) + len(pairs) - 1 :] = x
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta[len(tiles) + len(pairs) - 1 :]


def test_fe_matches_dummies():
    print("\n1. two-way FE by demeaning == explicit dummy regression")
    rng = np.random.default_rng(1)
    nt, npair = 17, 23
    tile = np.repeat(np.arange(nt), npair)
    pair = np.tile(np.arange(npair), nt)
    alpha = rng.normal(0, 2, nt)
    beta_p = rng.normal(0, 3, npair)
    x = rng.normal(0, 1, len(tile))
    z = rng.normal(0, 1, len(tile))
    gamma_true = 0.37
    y = alpha[tile] + beta_p[pair] + gamma_true * x + 0.11 * z + rng.normal(0, 0.05, len(tile))
    ref = dummy_reference(y, tile, pair, np.column_stack([x, z]))
    got, _, _, gi, _ = L._twoway_fe(y, tile, pair, np.column_stack([x, z]))
    check(
        "coefficients agree to 1e-9",
        np.allclose(ref, got[gi:], atol=1e-9),
        f"dummy={ref[0]:+.9f} demeaned={got[gi]:+.9f}",
    )
    check("planted gamma recovered", close(got[gi], gamma_true, 0.01), f"{got[gi]:+.4f} vs {gamma_true:+.4f}")


# ---------------------------------------------------------------------------
# 2. gamma must be zero when there is no coupling, and positive when there is
# ---------------------------------------------------------------------------


def synth_tiles(n_tiles, frames, deltas, gamma_true, seed, depth_res=0.0):
    """Build a synthetic Tiles record with a planted defocus coupling.

    `gamma_true` couples the residual to |pair midpoint - tile winner|.
    `depth_res` instead couples it to the winner itself, which is a *pure tile
    effect* the tile fixed effect must absorb completely.
    """
    rng = np.random.default_rng(seed)
    w = rng.uniform(0, frames - 1, n_tiles)
    rows = []
    alpha = rng.normal(1.0, 0.3, n_tiles)
    for d in deltas:
        for j in range(frames - d):
            beta_p = 0.02 * d + rng.normal(0, 0.05)
            for i in range(n_tiles):
                c = j + d / 2.0
                res = (
                    alpha[i]
                    + beta_p
                    + gamma_true * abs(c - w[i])
                    + depth_res * w[i]
                    + rng.normal(0, 0.1)
                )
                rows.append((j, j + d, d, i, res))
    ref = np.array([r[0] for r in rows])
    mov = np.array([r[1] for r in rows])
    dl = np.array([r[2] for r in rows])
    tid = np.array([r[3] for r in rows])
    res = np.array([r[4] for r in rows])
    ang = rng.uniform(0, 2 * np.pi, len(res))
    n = len(res)
    return (
        L.Tiles(
            case=np.array(["synth"] * n),
            ref=ref,
            mov=mov,
            delta=dl,
            tile_id=tid,
            tx=np.zeros(n, int),
            ty=np.zeros(n, int),
            ux=(tid % 12) * 128.0 - 700,
            uy=(tid // 12) * 128.0 - 400,
            dx=np.zeros(n),
            dy=np.zeros(n),
            ex=res * np.cos(ang),
            ey=res * np.sin(ang),
            peak=np.full(n, 0.5),
            contrast=np.full(n, 100.0),
            status=np.array(["ok"] * n),
            kept=np.ones(n, bool),
        ),
        w,
    )


def test_gamma_null_and_positive():
    print("\n2. S1 gamma: null centred at zero, planted value recovered")
    t, w = synth_tiles(96, 16, (1, 2, 4), gamma_true=0.0, seed=2)
    r0 = L.s1_gamma(t, w, n_perm=199)
    check(
        "no coupling -> gamma ~ 0",
        abs(r0.gamma) < 3 * r0.se_cluster,
        f"gamma={r0.gamma:+.5f} +/- {r0.se_cluster:.5f}",
    )
    check("no coupling -> permutation null not rejected", r0.p_perm > 0.02, f"p_perm={r0.p_perm:.3f}")
    check("permutation null is centred", abs(r0.perm_mean) < 3 * r0.perm_sd, f"mean={r0.perm_mean:+.5f}")

    t, w = synth_tiles(96, 16, (1, 2, 4), gamma_true=0.02, seed=3)
    r1 = L.s1_gamma(t, w, n_perm=199)
    check("planted gamma=0.02 recovered", close(r1.gamma, 0.02, 0.003), f"gamma={r1.gamma:+.5f}")
    check("planted gamma rejects permutation null", r1.p_perm <= 0.005, f"p_perm={r1.p_perm:.4f}")
    check("planted gamma rejects torus null", r1.p_torus <= 0.02, f"p_torus={r1.p_torus:.4f}")


def test_gamma_immune_to_pure_depth_effect():
    print("\n3. S1 gamma must NOT fire on a pure per-tile depth effect")
    # A residual that depends on depth but not on which pair is being aligned is
    # exactly what cause (a) looks like: the tile fixed effect must eat it whole.
    t, w = synth_tiles(96, 16, (1, 2, 4), gamma_true=0.0, seed=4, depth_res=0.05)
    r = L.s1_gamma(t, w, n_perm=199)
    check(
        "pure depth effect -> gamma ~ 0",
        abs(r.gamma) < 3 * max(r.se_cluster, 1e-6),
        f"gamma={r.gamma:+.5f} +/- {r.se_cluster:.5f}",
    )
    check("pure depth effect -> null not rejected", r.p_perm > 0.02, f"p_perm={r.p_perm:.3f}")


def test_cluster_se_exceeds_naive():
    print("\n4. cluster-robust SE must exceed the naive OLS SE on clustered data")
    # Two-way FE already absorb a pure tile intercept, so a tile intercept alone
    # leaves nothing for the cluster correction to find. What survives the FE is
    # a tile-specific *slope*: some tiles respond to defocus more than others, so
    # their residuals stay correlated across every pair they appear in. That is
    # the real situation here and it is what the cluster SE exists for.
    rng = np.random.default_rng(5)
    n_tiles, frames = 96, 16
    t, w = synth_tiles(n_tiles, frames, (1, 2, 4), gamma_true=0.0, seed=6)
    slope = rng.normal(0, 0.05, n_tiles)
    c = 0.5 * (t.ref + t.mov)
    d = np.abs(c - w[t.tile_id])
    y = t.res + slope[t.tile_id] * d
    tw = L.TwoWay(t.tile_id, t.ref * 10000 + t.mov)
    yd, Xd = tw.demean(y), tw.demean(d)[:, None]
    beta, resid = tw.fit(yd, Xd)
    se_c = tw.cluster_se(Xd, resid, 0)
    dof = len(y) - tw.n_absorbed - 1
    se_naive = float(np.sqrt(np.sum(resid**2) / dof / np.sum(Xd[:, 0] ** 2)))
    check("cluster SE > naive SE", se_c > se_naive, f"cluster={se_c:.6f} naive={se_naive:.6f}")

    # And on genuinely independent residuals the two must be close, or the
    # cluster estimator is simply inflating everything.
    tw2 = L.TwoWay(t.tile_id, t.ref * 10000 + t.mov)
    yd2, Xd2 = tw2.demean(t.res), tw2.demean(d)[:, None]
    b2, r2 = tw2.fit(yd2, Xd2)
    se_c2 = tw2.cluster_se(Xd2, r2, 0)
    se_n2 = float(np.sqrt(np.sum(r2**2) / dof / np.sum(Xd2[:, 0] ** 2)))
    check("independent residuals -> cluster ~ naive", abs(se_c2 / se_n2 - 1) < 0.25,
          f"ratio={se_c2 / se_n2:.3f}")


# ---------------------------------------------------------------------------
# 5. Spearman
# ---------------------------------------------------------------------------


def test_spearman():
    print("\n5. Spearman rank correlation")
    check("perfect monotone -> +1", close(L._spearman(np.arange(10.0), np.arange(10.0) ** 3), 1.0, 1e-12))
    check("perfect antitone -> -1", close(L._spearman(np.arange(10.0), -np.arange(10.0)), -1.0, 1e-12))
    try:
        from scipy.stats import spearmanr

        rng = np.random.default_rng(7)
        a, b = rng.normal(size=40), rng.normal(size=40)
        check("matches scipy", close(L._spearman(a, b), float(spearmanr(a, b).statistic), 1e-12))
    except ImportError:
        print("  [SKIP] scipy not available")


# ---------------------------------------------------------------------------
# 6. Winner index: parabolic refinement of a planted sub-frame peak
# ---------------------------------------------------------------------------


def test_winner_index():
    print("\n6. winner_index recovers a planted sub-frame focus peak")
    frames, tiles = 25, 12
    true_w = np.linspace(3.4, 20.7, tiles)
    rows = {"tile_id": [], "frame": [], "tx": [], "ty": [], "ring": [], "hp": []}
    for i in range(tiles):
        for k in range(frames):
            v = 10.0 * np.exp(-0.5 * ((k - true_w[i]) / 3.0) ** 2) + 1.0
            rows["tile_id"].append(i)
            rows["frame"].append(k)
            rows["tx"].append(0)
            rows["ty"].append(0)
            rows["ring"].append(v)
            rows["hp"].append(v)
    focus = {k: np.array(v) for k, v in rows.items()}
    w, pk, prof = L.winner_index(focus)
    err = np.abs(w[:tiles] - true_w)
    check("sub-frame peak within 0.25 frame", err.max() < 0.25, f"max err {err.max():.3f} frames")
    check("peakiness sensible", np.all(pk[:tiles] > 0.5), f"min {np.nanmin(pk[:tiles]):.3f}")
    # A flat profile carries no depth: peakiness must say so.
    flat = {
        "tile_id": np.zeros(frames, int),
        "frame": np.arange(frames),
        "tx": np.zeros(frames, int),
        "ty": np.zeros(frames, int),
        "ring": np.ones(frames) * 4.0,
        "hp": np.ones(frames) * 4.0,
    }
    _, pkf, _ = L.winner_index(flat)
    check("flat profile -> peakiness 0", close(float(pkf[0]), 0.0, 1e-9), f"{pkf[0]:.6f}")


# ---------------------------------------------------------------------------
# 7. Halo arithmetic against closed form
# ---------------------------------------------------------------------------


def _fits_from(rows, w=L.PLANE_W, h=L.PLANE_H):
    n = len(rows)
    return L.Fits(
        case=np.array(["x"] * n),
        grid=np.array(["m6"] * n),
        ref=np.zeros(n, int),
        mov=np.arange(1, n + 1),
        delta=np.arange(1, n + 1),
        g=np.array([r[0] for r in rows]),
        rot=np.array([r[1] for r in rows]),
        ax=np.array([r[2] for r in rows]),
        ay=np.array([r[3] for r in rows]),
        rms=np.zeros(n),
        used=np.full(n, 96),
        plane_w=np.full(n, w),
        plane_h=np.full(n, h),
    )


def test_halo_closed_form():
    print("\n7. halo arithmetic against closed form")
    g = -0.02
    fits = _fits_from([(g, 0.0, 0.0, 0.0)])
    tile = 128
    w, h = L.PLANE_W, L.PLANE_H
    cx, cy = w / 2.0, h / 2.0
    tcx, tcy, halo = L.tile_halo(fits, tile, cx, cy, w, h)
    # F(p) - c = (1+g)(p - c), so with g < 0 everything contracts towards the
    # scale centre. The side of a tile that faces *away* from the centre is the
    # one whose source pixels move inwards past the tile edge, so that is the
    # side that needs the halo:
    #     low-x side:  x0 - F(x0) = -a_x - g*(x0 - cx)
    #     high-x side: F(x1) - x1 = +a_x + g*(x1 - cx)
    ok = True
    worst = 0.0
    nx, ny = -(-w // tile), -(-h // tile)
    k = 0
    for j in range(ny):
        for i in range(nx):
            x0, y0 = i * tile, j * tile
            x1, y1 = min(x0 + tile, w), min(y0 + tile, h)
            pred = max(
                0.0,
                -g * (x0 - cx),
                g * (x1 - cx),
                -g * (y0 - cy),
                g * (y1 - cy),
            )
            worst = max(worst, abs(pred - halo[k]))
            ok &= abs(pred - halo[k]) < 1e-6
            k += 1
    check("pure scale halo matches closed form", ok, f"max deviation {worst:.2e} px")

    check("halo is zero at the scale centre", halo.min() < 0.75 * tile * abs(g) + 1e-9,
          f"min halo {halo.min():.3f} px")
    corner = float(halo[np.argmax(np.hypot(tcx - cx, tcy - cy))])
    # Corner tile centre sits at about (w/2 - 64, h/2 - 64) from the centre.
    check("corner halo ~ |g| * corner radius component", corner > 0.9 * abs(g) * (w / 2 - tile),
          f"corner halo {corner:.2f} px")

    # A pure translation needs the same halo everywhere.
    fits2 = _fits_from([(0.0, 0.0, 7.0, -3.0)])
    _, _, h2 = L.tile_halo(fits2, tile, cx, cy, w, h)
    check("pure translation -> constant halo = |a|_inf", close(float(h2.max()), 7.0, 1e-6) and close(float(h2.min()), 7.0, 1e-6),
          f"min {h2.min():.3f} max {h2.max():.3f}")

    # Identity needs none.
    fits3 = _fits_from([(0.0, 0.0, 0.0, 0.0)])
    _, _, h3 = L.tile_halo(fits3, tile, cx, cy, w, h)
    check("identity -> zero halo", float(h3.max()) < 1e-9, f"max {h3.max():.2e}")

    # The corner-point halo must equal |g| * (half-diagonal component) exactly.
    cp = L.corner_halo_point(fits, w, h)
    check("corner-point halo == |g| * max(w,h)/2", close(cp, abs(g) * max(w, h) / 2, 1e-6),
          f"{cp:.3f} vs {abs(g) * max(w, h) / 2:.3f}")

    # The grid must tile the whole plane, not a truncated part of it.
    nx, ny = -(-w // tile), -(-h // tile)
    check("halo grid covers the whole plane", len(halo) == nx * ny, f"{len(halo)} tiles, expected {nx * ny}")


def test_halo_monotone_in_radius():
    print("\n8. halo grows with radius under a pure scale")
    fits = _fits_from([(-0.018353, 0.0, 0.0, 0.0)])
    tab = L.halo_table(fits, 128, 0.0, 0.0)
    rho = L._spearman(tab["radius"], tab["halo"])
    check("Spearman(radius, halo) > 0.9", rho > 0.9, f"rho={rho:.4f}")
    check("corner:centre ratio is large", tab["ratio_corner_centre"] > 5,
          f"ratio={tab['ratio_corner_centre']:.3g}")
    check("max:median ratio is a bounded restatement", 1.5 < tab["ratio_max_median"] < 10,
          f"max/median={tab['ratio_max_median']:.2f}")


# ---------------------------------------------------------------------------
# 9. Scale centre recovery
# ---------------------------------------------------------------------------


def test_scale_centre():
    print("\n9. scale centre recovered from translation-vs-scale regression")
    ox, oy = -11.0, -56.0
    rows = []
    for k in range(1, 22):
        g = -0.0008 * k
        rows.append((g, 0.0, -g * ox, -g * oy))
    fits = _fits_from(rows)
    gx, gy = L.scale_centre(fits)
    check("ox recovered", close(gx, ox, 1e-6), f"{gx:.4f} vs {ox}")
    check("oy recovered", close(gy, oy, 1e-6), f"{gy:.4f} vs {oy}")


# ---------------------------------------------------------------------------
# 10. Radial/tangential split
# ---------------------------------------------------------------------------


def test_radial_tangential():
    print("\n10. radial/tangential decomposition")
    ux = np.array([100.0, 0.0, -100.0, 70.71])
    uy = np.array([0.0, 100.0, 0.0, 70.71])
    ex, ey = 0.03 * ux, 0.03 * uy  # purely radial
    er, et, r = L.radial_tangential(ex, ey, ux, uy)
    check("pure radial -> tangential 0", np.allclose(et, 0, atol=1e-9), f"max |et| {np.abs(et).max():.2e}")
    check("radial magnitude right", np.allclose(er, 0.03 * r, atol=1e-9))
    ex2, ey2 = -0.03 * uy, 0.03 * ux  # purely tangential
    er2, et2, _ = L.radial_tangential(ex2, ey2, ux, uy)
    check("pure tangential -> radial 0", np.allclose(er2, 0, atol=1e-9), f"max |er| {np.abs(er2).max():.2e}")


def test_s5_infocus():
    print("\n11. S5 in-focus/out-of-focus residual gap")
    # No coupling: the gap must be ~0 and the torus null must not be rejected.
    t, w = synth_tiles(96, 24, (1, 2, 4), gamma_true=0.0, seed=11)
    r0 = L.s5_infocus_residual(t, w)
    check("no coupling -> gap ~ 0", abs(r0["gap_px"]) < 0.03, f"gap={r0['gap_px']:+.4f} px")
    check("no coupling -> torus null not rejected", r0["p_torus"] > 0.05, f"p={r0['p_torus']:.3f}")
    # Planted coupling: the gap must be positive and significant, and roughly
    # gamma * (far - near) by construction.
    t, w = synth_tiles(96, 24, (1, 2, 4), gamma_true=0.03, seed=12)
    r1 = L.s5_infocus_residual(t, w)
    check("planted coupling -> positive gap", r1["gap_px"] > 0.1, f"gap={r1['gap_px']:+.4f} px")
    check("planted coupling -> torus null rejected", r1["p_torus"] <= 0.05, f"p={r1['p_torus']:.3f}")


def synth_signed(n_tiles, frames, deltas, bias_true, noise_gain, seed):
    """Tiles whose residual vector has a *directed* radial part and/or an
    inflated *undirected* scatter, both driven by the signed blur asymmetry.

    `bias_true`  -> radial component proportional to a[i,j] = |mov-w| - |ref-w|.
                    This is the asymmetric-PSF hypothesis: the peak MOVES.
    `noise_gain` -> isotropic random error scaled by |a|. This is the symmetric-
                    PSF hypothesis: the peak gets NOISIER but has no direction.

    S6 must fire on the first and stay quiet on the second. If it cannot tell
    them apart it is measuring nothing that decides the architecture.
    """
    rng = np.random.default_rng(seed)
    w = rng.uniform(0, frames - 1, n_tiles)
    ux = (np.arange(n_tiles) % 12) * 128.0 - 700.0
    uy = (np.arange(n_tiles) // 12) * 128.0 - 400.0
    rr = np.hypot(ux, uy)
    rows = []
    for d in deltas:
        for j in range(frames - d):
            for i in range(n_tiles):
                a = abs(j + d - w[i]) - abs(j - w[i])
                mag = bias_true * a
                hx, hy = ux[i] / rr[i], uy[i] / rr[i]
                sig = 0.05 + noise_gain * abs(a)
                ex = mag * hx + rng.normal(0, sig)
                ey = mag * hy + rng.normal(0, sig)
                rows.append((j, j + d, d, i, ex, ey))
    arr = lambda k, ty=float: np.array([r[k] for r in rows], ty)  # noqa: E731
    ex, ey = arr(4), arr(5)
    tid = arr(3, int)
    n = len(rows)
    return (
        L.Tiles(
            case=np.array(["synth"] * n),
            ref=arr(0, int),
            mov=arr(1, int),
            delta=arr(2, int),
            tile_id=tid,
            tx=np.zeros(n, int),
            ty=np.zeros(n, int),
            ux=ux[tid],
            uy=uy[tid],
            dx=np.zeros(n),
            dy=np.zeros(n),
            ex=ex,
            ey=ey,
            peak=np.full(n, 0.5),
            contrast=np.full(n, 100.0),
            status=np.array(["ok"] * n),
            kept=np.ones(n, bool),
        ),
        w,
    )


def test_s6_bias_vs_variance():
    print("\n12. S6 separates a directed peak bias from an undirected variance increase")
    # (i) planted radial bias, no extra scatter -> must fire on b_rad only.
    t, w = synth_signed(96, 16, (1, 2, 4), bias_true=0.02, noise_gain=0.0, seed=21)
    r = L.s6_signed_bias(t, w, 0.0, 0.0, n_torus=95)
    check("planted bias recovered", close(r["b_rad"], 0.02, 0.004), f"b_rad={r['b_rad']:+.5f}")
    check("planted bias -> torus null rejected", r["p_torus_rad"] <= 0.05, f"p={r['p_torus_rad']:.3f}")
    check(
        "tangential placebo stays quiet",
        abs(r["b_tan"]) < 3 * r["se_tan"] + 1e-9,
        f"b_tan={r['b_tan']:+.5f} +/- {r['se_tan']:.5f}",
    )
    # (ii) pure variance inflation, no direction -> S6 must NOT fire.
    t, w = synth_signed(96, 16, (1, 2, 4), bias_true=0.0, noise_gain=0.05, seed=22)
    r = L.s6_signed_bias(t, w, 0.0, 0.0, n_torus=95)
    check(
        "variance-only -> b_rad consistent with zero",
        abs(r["b_rad"]) < 3 * r["se_rad"],
        f"b_rad={r['b_rad']:+.5f} +/- {r['se_rad']:.5f}",
    )
    check("variance-only -> torus null not rejected", r["p_torus_rad"] > 0.05, f"p={r['p_torus_rad']:.3f}")
    # (iii) S7 must see the variance case as scatter, not as bias.
    rows = L.s7_bias_variance(t, w)
    check("S7 ran", len(rows) >= 2, f"{len(rows)} bins")
    worst = max(r6[5] for r6 in rows)
    check("variance-only -> S7 bias/scatter small", worst < 0.6, f"max ratio {worst:.3f}")
    t, w = synth_signed(96, 16, (1, 2, 4), bias_true=0.05, noise_gain=0.0, seed=23)
    rows = L.s7_bias_variance(t, w)
    best = max(r6[5] for r6 in rows)
    check("planted bias -> S7 bias/scatter large", best > 1.0, f"max ratio {best:.3f}")


def main():
    test_fe_matches_dummies()
    test_gamma_null_and_positive()
    test_gamma_immune_to_pure_depth_effect()
    test_cluster_se_exceeds_naive()
    test_spearman()
    test_winner_index()
    test_halo_closed_form()
    test_halo_monotone_in_radius()
    test_scale_centre()
    test_radial_tangential()
    test_s5_infocus()
    test_s6_bias_vs_variance()
    print()
    if FAILS:
        print(f"FAILED {len(FAILS)}: " + ", ".join(FAILS))
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
