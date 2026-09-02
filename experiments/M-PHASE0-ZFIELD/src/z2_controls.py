"""M-PHASE0-ZFIELD -- controls. Run and pass before any census number is quoted.

Registered in PREREGISTRATION.md section 7. Each control prints PASS or FAIL and
the script exits non-zero if any fails.

  C1a  planted-sigma recovery on synthetic smooth focus curves      (<=10%)
  C1b  planted-sigma recovery on a real M66 cube, s = 2*sigma_r     (<=10%)
  C2   planted-zhat recovery: bias, and sigma_z vs empirical sd     (<=20%)
  C3   sigma_r cross-check against M69's two estimators             (<=1.5x)
  C4   null: a pure-noise cube must not be called placeable
  C5   easy saturation: high curvature must exhaust into EASY not LOST
  C6   noise correlation length > 1 px, so the n_eff deflation fires
"""

import json
import os
import pathlib
import sys

import numpy as np
from scipy.signal import savgol_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import zflib  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
M66 = ROOT / "experiments" / "M66-gate-n-dependence" / "data"
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"

SG_WIN, SG_ORD, TAU_MAX = 11, 3, 6


def sg_leverage(win, order):
    imp = np.zeros(4 * win + 1)
    imp[2 * win] = 1.0
    return float(savgol_filter(imp, win, order, mode="interp")[2 * win])


LEV = sg_leverage(SG_WIN, SG_ORD)


def m69_sg_sigma(cube):
    sm = savgol_filter(cube.astype(np.float64), SG_WIN, SG_ORD, axis=0, mode="interp")
    res = cube - sm
    return np.sqrt(np.mean(res * res, axis=0) / (1.0 - LEV))


def m69_structure_sigma(cube, tau_max=TAU_MAX):
    taus = np.arange(1, tau_max + 1, dtype=np.float64)
    u = taus**2
    d = np.empty((tau_max,) + cube.shape[1:], dtype=np.float64)
    for i, t in enumerate(taus.astype(int)):
        diff = cube[t:].astype(np.float64) - cube[:-t].astype(np.float64)
        d[i] = 0.5 * np.mean(diff * diff, axis=0)
    ub, db = u.mean(), d.mean(axis=0)
    b = np.tensordot(u - ub, d - db, axes=(0, 0)) / np.sum((u - ub) ** 2)
    return np.sqrt(np.maximum(db - b * ub, 0.0))


RESULTS = []


def record(name, ok, detail):
    RESULTS.append({"control": name, "pass": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}]  {name}: {detail}", flush=True)


def gauss_cube(n, shape, z0, width, amp, sigma, seed):
    rng = np.random.default_rng(seed)
    k = np.arange(n, dtype=np.float64)[:, None, None]
    clean = amp * np.exp(-0.5 * ((k - z0[None]) / width) ** 2)
    return clean + sigma * rng.standard_normal((n,) + shape), clean


def c1a():
    shape = (64, 64)
    rng = np.random.default_rng(11)
    z0 = 20.0 + 4.0 * rng.random(shape)
    worst = 0.0
    for sigma in (0.05, 0.2, 1.0):
        cube, _ = gauss_cube(41, shape, z0, 3.0, 10.0, sigma, seed=101)
        rec = float(np.median(zflib.sigma_r(cube)))
        worst = max(worst, abs(rec / sigma - 1.0))
    record("C1a planted-sigma, synthetic", worst <= 0.10,
           f"worst relative error {worst * 100:.2f}% over sigma in 0.05/0.2/1.0")


def c1b(cube):
    sm = savgol_filter(cube.astype(np.float64), 21, 3, axis=0, mode="interp")
    base = float(np.median(zflib.sigma_r(cube)))
    rng = np.random.default_rng(202)
    s = 2.0 * base
    planted = sm + s * rng.standard_normal(sm.shape)
    # The smoothed cube retains some of its own noise; predict the sum in
    # quadrature rather than pretending the truth is exactly smooth.
    resid = float(np.median(zflib.sigma_r(sm)))
    pred = np.sqrt(s * s + resid * resid)
    rec = float(np.median(zflib.sigma_r(planted)))
    err = abs(rec / pred - 1.0)
    record("C1b planted-sigma, real cube", err <= 0.10,
           f"recovered {rec:.4f} vs predicted {pred:.4f} ({err * 100:.2f}%), "
           f"base sigma_r {base:.4f}, smoothed residual {resid:.4f}")


def c2():
    shape = (48, 48)
    rng = np.random.default_rng(303)
    yy = np.arange(shape[0])[:, None] * np.ones((1, shape[1]))
    z0 = 20.0 + 0.06 * yy + 0.31 * rng.random(shape)
    z0[:, 24:] += 2.0  # a real depth step, so this is not a pure ramp
    amp, width, sigma, reps = 10.0, 3.0, 0.30, 96
    zs = np.empty((reps,) + shape)
    an_sym = np.empty((reps,) + shape)
    an_gen = np.empty((reps,) + shape)
    for r in range(reps):
        cube, _ = gauss_cube(41, shape, z0, width, amp, sigma, seed=1000 + r)
        _, D, zhat, interior = zflib.peak_stats(cube)
        sr = zflib.sigma_r(cube)
        zs[r] = np.where(interior, zhat, np.nan)
        an_sym[r] = zflib.sigma_z(sr, D)
        an_gen[r] = zflib.sigma_z(sr, D, off=zhat - np.clip(np.argmax(cube, axis=0), 1, 39))
    bias = float(np.nanmedian(zs - z0[None]))
    emp = float(np.nanmedian(np.nanstd(zs, axis=0)))

    cube0, _ = gauss_cube(41, shape, z0, width, amp, sigma, seed=1000)
    flat = cube0.reshape(41, -1)
    boot = float(np.median(zflib.bootstrap_sigma_z(flat, zflib.sigma_r(cube0).ravel())))

    ratio = boot / emp
    ok = abs(ratio - 1.0) <= 0.20 and abs(bias) <= 0.10
    record("C2 planted-zhat (bootstrap)", ok,
           f"bias {bias:+.4f} frames, empirical sd {emp:.4f}, bootstrap {boot:.4f} "
           f"(ratio {ratio:.3f}); retired analytic forms: symmetric-point "
           f"{float(np.nanmedian(an_sym)):.4f} (ratio {float(np.nanmedian(an_sym)) / emp:.3f}), "
           f"general-offset {float(np.nanmedian(an_gen)):.4f} "
           f"(ratio {float(np.nanmedian(an_gen)) / emp:.3f})")


def c3(cube):
    """C3' per Amendment A1.4: a truth test, not an agreement test."""
    sm = savgol_filter(cube.astype(np.float64), 21, 3, axis=0, mode="interp")
    base = float(np.median(zflib.sigma_r(cube)))
    resid = float(np.median(zflib.sigma_r(sm)))
    worst = 0.0
    rows = []
    for mult in (1.0, 2.0, 4.0):
        s = mult * base
        pred = np.sqrt(s * s + resid * resid)
        planted = sm + s * np.random.default_rng(int(900 + mult)).standard_normal(sm.shape)
        mine = float(np.median(zflib.sigma_r(planted)))
        sg = float(np.median(m69_sg_sigma(planted)))
        st = float(np.median(m69_structure_sigma(planted)))
        worst = max(worst, abs(mine / pred - 1.0))
        rows.append(f"s={s:.4f}: mine {mine:.4f} ({mine / pred - 1.0:+.1%} vs truth), "
                    f"M69 sg {sg / pred:.2f}x, M69 structure {st / pred:.2f}x")
    record("C3' sigma_r truth test", worst <= 0.10,
           f"worst error {worst * 100:.2f}%; " + "; ".join(rows))


def c4():
    """Pure noise. Registered concern (A1.3): argmax conditions on a spike, so the
    first-order sigma_z looks confident where there is no peak at all."""
    rng = np.random.default_rng(404)
    for n in (22, 105):
        cube = rng.standard_normal((n, 96, 96))
        sr = zflib.sigma_r(cube)
        _, D, _, _ = zflib.peak_stats(cube)
        sz_an = zflib.sigma_z(sr, D)
        e_an, _, _, _ = zflib.partition(sz_an, 0.65, np.sqrt(9.0))
        boot = zflib.bootstrap_sigma_z(cube.reshape(n, -1), sr.ravel())
        e, w, l, _ = zflib.partition(boot, 0.65, np.sqrt(9.0))
        ok = e <= 0.02
        record(f"C4 null n={n}", ok,
               f"bootstrap median sigma_z {float(np.median(boot)):.3f} frames, "
               f"EASY {e * 100:.2f}% WINNABLE {w * 100:.2f}% LOST {l * 100:.2f}%; "
               f"retired analytic form called EASY {e_an * 100:.1f}% at median "
               f"sigma_z {float(np.nanmedian(sz_an[np.isfinite(sz_an)])):.4f}")


def c5():
    shape = (64, 64)
    rng = np.random.default_rng(505)
    z0 = 20.0 + 3.0 * rng.random(shape)
    cube, _ = gauss_cube(41, shape, z0, 1.2, 100.0, 0.02, seed=606)
    boot = zflib.bootstrap_sigma_z(cube.reshape(41, -1), zflib.sigma_r(cube).ravel())
    e, w, l, _ = zflib.partition(boot, 0.65, np.sqrt(9.0))
    ok = e >= 0.98 and l <= 0.02
    record("C5 easy saturation", ok,
           f"EASY {e * 100:.2f}% WINNABLE {w * 100:.2f}% LOST {l * 100:.2f}%, "
           f"median bootstrap sigma_z {float(np.median(boot)):.5f}")


def c6(cube, name):
    rx, ry = zflib.noise_autocorr(cube)
    lx = int(np.argmax(rx < 1.0 / np.e)) if np.any(rx < 1.0 / np.e) else len(rx)
    ly = int(np.argmax(ry < 1.0 / np.e)) if np.any(ry < 1.0 / np.e) else len(ry)
    ne9 = zflib.n_eff(rx, ry, 9)
    ok = lx > 1 and ly > 1 and ne9 < 81.0 * 0.9
    record("C6 noise correlation length", ok,
           f"{name}: 1/e lag x={lx} y={ly} px, n_eff(9x9)={ne9:.2f} of 81 "
           f"(deflation x{81.0 / ne9:.1f})")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("M-PHASE0-ZFIELD controls\n")
    path = M66 / "113MSDCF-d4.npy"
    full = np.load(path, mmap_mode="r")
    crop = np.array(full[:, 200:328, 300:428], dtype=np.float32)
    print(f"  real-cube arm: 113MSDCF-d4 crop {crop.shape}\n")

    c1a()
    c1b(crop)
    c2()
    c3(crop)
    c4()
    c5()
    c6(crop, "113MSDCF")

    n_fail = sum(1 for r in RESULTS if not r["pass"])
    print(f"\n  {len(RESULTS) - n_fail}/{len(RESULTS)} passed")
    (OUT / "z2-controls.json").write_text(
        json.dumps({"results": RESULTS, "n_fail": n_fail}, indent=1), encoding="utf-8")
    print("  RED -- controls failed" if n_fail else "  GREEN -- all controls passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
