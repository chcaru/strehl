"""M-PHASE0-ZFIELD -- Z1/Z2/Z3/Z4 census over the eight M66 response cubes.

Registered in PREREGISTRATION.md section 5, with the sigma_z estimator replaced
by Amendment A1.2's parametric bootstrap. Nothing here was tuned after looking at
a result; the verdict bar in section 2 was fixed before this file existed.

Read-only with respect to D:\\personal\\macro. Writes only to ../out/.
"""

import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import zflib  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
M66 = ROOT / "experiments" / "M66-gate-n-dependence" / "data"
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"

# Registered in section 2. Two from the recommended step, two from corpus density.
HALF_WIDTHS = [0.65, 0.75, 1.5, 3.0]
# Corpus density is the native state of these cubes, so this is the pair that
# applies at decimation m = 1; section 5's ladder divides it by m.
CORPUS_HALF = [1.5, 3.0]
WINDOWS = [3, 5, 9, 17, 33]
DECIMATIONS = [1, 2, 3]
N_SAMPLE = 30000
Y_BLOCK = 64
SIGNAL_MIN = 3.0  # (peak - floor) / sigma_r for a pixel to have any focus signal


def blocked_fields(cube):
    """sigma_r, D, zhat, interior, signal-to-noise of peak prominence, full field."""
    n, h, w = cube.shape
    sr = np.empty((h, w), np.float64)
    D = np.empty((h, w), np.float64)
    zh = np.empty((h, w), np.float64)
    inter = np.empty((h, w), bool)
    prom = np.empty((h, w), np.float64)
    for y0 in range(0, h, Y_BLOCK):
        y1 = min(y0 + Y_BLOCK, h)
        blk = np.asarray(cube[:, y0:y1, :], dtype=np.float32)
        s = zflib.sigma_r(blk)
        k, d, z, it = zflib.peak_stats(blk)
        sr[y0:y1] = s
        D[y0:y1] = d
        zh[y0:y1] = z
        inter[y0:y1] = it
        with np.errstate(divide="ignore", invalid="ignore"):
            prom[y0:y1] = (blk.max(axis=0) - np.median(blk, axis=0)) / np.maximum(s, 1e-30)
    return sr, D, zh, inter, prom


def plane_r2(zh, valid, n_win=2000, w=9, seed=5, min_valid=60):
    """Median R^2 of a local plane fit to zhat over w x w windows.

    Section 5 Z3(c): the fraction of local zhat variance that is a coherent
    gradient rather than salt-and-pepper. A surface can only help where this is
    high; where it is low, pooling is smoothing.
    """
    h, wd = zh.shape
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:w, 0:w].astype(np.float64)
    out = []
    tries = 0
    while len(out) < n_win and tries < n_win * 40:
        tries += 1
        y0 = int(rng.integers(0, h - w))
        x0 = int(rng.integers(0, wd - w))
        m = valid[y0:y0 + w, x0:x0 + w]
        if m.sum() < min_valid:
            continue
        z = zh[y0:y0 + w, x0:x0 + w][m]
        if z.std() <= 0:
            continue
        A = np.column_stack([np.ones(m.sum()), yy[m], xx[m]])
        coef, *_ = np.linalg.lstsq(A, z, rcond=None)
        resid = z - A @ coef
        ss_tot = float(((z - z.mean()) ** 2).sum())
        if ss_tot <= 0:
            continue
        out.append(1.0 - float((resid ** 2).sum()) / ss_tot)
    return (float(np.median(out)) if out else None), len(out)


def zhat_autocorr(zh, valid, max_lag=48):
    """Autocorrelation of zhat along x and y, over pixels valid at both ends."""
    z = np.where(valid, zh, np.nan)
    z = z - np.nanmean(z)
    var = float(np.nanmean(z * z))
    out = []
    for axis in (1, 0):
        rho = [1.0]
        for L in range(1, max_lag + 1):
            a = np.take(z, range(0, z.shape[axis] - L), axis=axis)
            b = np.take(z, range(L, z.shape[axis]), axis=axis)
            rho.append(float(np.nanmean(a * b)) / var)
        out.append(rho)
    return out[0], out[1]


def one_arm(cube, seed):
    """Every registered statistic for one (stack, decimation) arm."""
    n, h, w = cube.shape
    sr, D, zh, inter, prom = blocked_fields(cube)

    rng = np.random.default_rng(seed)
    ys = rng.integers(0, h, N_SAMPLE)
    xs = rng.integers(0, w, N_SAMPLE)
    curves = np.asarray(cube[:, ys, xs], dtype=np.float64)
    boot = zflib.bootstrap_sigma_z(curves, sr[ys, xs])
    sig_mask = prom[ys, xs] >= SIGNAL_MIN

    rho_x, rho_y = zflib.noise_autocorr(cube)
    lag_x = next((i for i, v in enumerate(rho_x) if v < 1 / np.e), len(rho_x))
    lag_y = next((i for i, v in enumerate(rho_y) if v < 1 / np.e), len(rho_y))
    gains = {str(W): float(np.sqrt(zflib.n_eff(rho_x, rho_y, W))) for W in WINDOWS}

    part = {}
    for half in HALF_WIDTHS:
        rows = {}
        for W in WINDOWS:
            g = np.sqrt(zflib.n_eff(rho_x, rho_y, W))
            e, wn, l, _ = zflib.partition(boot, half, g)
            es, wns, ls, _ = zflib.partition(boot[sig_mask], half, g) if sig_mask.any() \
                else (0.0, 0.0, 0.0, 0)
            rows[str(W)] = {"easy": e, "winnable": wn, "lost": l,
                            "easy_sig": es, "winnable_sig": wns, "lost_sig": ls}
        best = max(WINDOWS, key=lambda W: rows[str(W)]["winnable"])
        best_sig = max(WINDOWS, key=lambda W: rows[str(W)]["winnable_sig"])
        part[str(half)] = {"by_window": rows,
                           "best_window": best,
                           "winnable_best": rows[str(best)]["winnable"],
                           "best_window_sig": best_sig,
                           "winnable_best_sig": rows[str(best_sig)]["winnable_sig"]}

    valid = inter & np.isfinite(zh)
    r2, n_win = plane_r2(zh, valid)
    az_x, az_y = zhat_autocorr(zh, valid)

    return {
        "n_frames": int(n),
        "shape": [int(h), int(w)],
        "sigma_r_median": float(np.median(sr)),
        "curvature": {
            "frac_no_interior_max": float(1.0 - inter.mean()),
            "frac_D_nonneg": float((D >= 0).mean()),
            "frac_below_noise": float((np.abs(D) < 2.0 * sr).mean()),
            "absD_over_sigma_r_q": zflib.quantiles(np.abs(D) / np.maximum(sr, 1e-30)),
        },
        "prominence_q": zflib.quantiles(prom),
        "frac_with_signal": float(sig_mask.mean()),
        "sigma_z_q": zflib.quantiles(boot),
        "sigma_z_q_signal": zflib.quantiles(boot[sig_mask]) if sig_mask.any() else None,
        "noise_corr": {"lag_x_1e": int(lag_x), "lag_y_1e": int(lag_y),
                       "rho_x": [float(v) for v in rho_x],
                       "rho_y": [float(v) for v in rho_y],
                       "pool_gain": gains,
                       "n_eff_9": float(zflib.n_eff(rho_x, rho_y, 9))},
        "zhat_coherence": {"plane_r2_median": r2, "n_windows": n_win,
                           "autocorr_x": az_x[:24], "autocorr_y": az_y[:24]},
        "partition": part,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stacks = sorted(p.stem.replace("-d4", "") for p in M66.glob("*-d4.npy"))
    results = {}
    for i, s in enumerate(stacks):
        cube_full = np.load(M66 / f"{s}-d4.npy", mmap_mode="r")
        results[s] = {}
        for m in DECIMATIONS:
            sub = np.asarray(cube_full[::m], dtype=np.float32)
            if sub.shape[0] < zflib.BOOT_WIN:
                print(f"  {s} m={m}: only {sub.shape[0]} frames, "
                      f"below the bootstrap window {zflib.BOOT_WIN} -- skipped", flush=True)
                results[s][str(m)] = {"skipped": f"{sub.shape[0]} frames"}
                continue
            t0 = time.time()
            results[s][str(m)] = one_arm(sub, seed=1000 + 17 * i + m)
            print(f"  {s} m={m}: n={sub.shape[0]} "
                  f"sigma_z med {results[s][str(m)]['sigma_z_q']['50']:.3f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
            del sub
    payload = {
        "config": {"half_widths": HALF_WIDTHS, "corpus_half": CORPUS_HALF,
                   "windows": WINDOWS, "decimations": DECIMATIONS,
                   "n_sample": N_SAMPLE, "signal_min": SIGNAL_MIN,
                   "boot_reps": zflib.BOOT_REPS, "boot_win": zflib.BOOT_WIN},
        "stacks": results,
    }
    (OUT / "z1-census.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\n  wrote {OUT / 'z1-census.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

