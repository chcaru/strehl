"""M69 arm A5 -- response noise measured on real stacks, with no synthetic noise.

Every earlier estimate of the response noise in this project (the crate's own
calibration, M65's K1, M66's K7, M69's A2) injects synthetic noise into a frozen
latent. This arm does not. It reads the shipped operator's response along the
real focus sequence and separates the smooth focus signal from the frame-to-frame
scatter.

Primary estimator (pre-registered): the lag structure function

    D_p(tau) = 0.5 * mean_k (X_{k+tau}(p) - X_k(p))^2 = sigma_F^2 + b tau^2 + ...

fitted as a + b*tau^2 over tau = 1..TAU_MAX, intercept a -> sigma_F^2(p).

Secondary estimator: Savitzky-Golay residual scatter with the exact centre-point
leverage correction.

K3 decides whether either estimator may be quoted: a planted sigma_F laid on the
measured focus curves must be recovered within 5%.
K4 audits the drift that would inflate both: per-frame photometric level.
"""

import json
import pathlib
import sys
import time

import numpy as np
from scipy.signal import savgol_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

CROP = 2816
DECIM = 4
TAU_MAX = 6
SG_WIN = 11
SG_ORD = 3


def sg_leverage(win, order):
    """Centre-point leverage of the local polynomial fit, so the residual
    scatter can be turned into an unbiased sigma."""
    imp = np.zeros(4 * win + 1)
    imp[2 * win] = 1.0
    sm = savgol_filter(imp, win, order, mode="interp")
    return float(sm[2 * win])


LEV = sg_leverage(SG_WIN, SG_ORD)


def response_cube(stack, limit=None):
    files = m69.stack_files(stack)
    if limit:
        files = files[:limit]
    iso = m69.iso_of(files[0])
    cube = None
    levels = []
    t0 = time.time()
    for k, path in enumerate(files):
        v = m69.raw_visible(path)
        y = (v.shape[0] - CROP) // 2
        x = (v.shape[1] - CROP) // 2
        y -= y % 2
        x -= x % 2
        lat = v[y : y + CROP, x : x + CROP]
        luma = m69.luma_from_raw(lat)
        levels.append(float(luma.mean()))
        reg = m69.interior(m69.regularised(luma, iso))[::DECIM, ::DECIM]
        if cube is None:
            cube = np.empty((len(files), reg.shape[0], reg.shape[1]), dtype=np.float32)
        cube[k] = reg
        if k == 0:
            print(f"    frame grid {reg.shape}, {time.time() - t0:.1f}s for frame 0", flush=True)
    print(f"    {len(files)} frames in {time.time() - t0:.0f}s   ISO {iso:.0f}", flush=True)
    return cube, np.array(levels), iso, files


def structure_intercept(cube, tau_max=TAU_MAX):
    """Per-pixel a from D(tau) = a + b tau^2 fitted over tau = 1..tau_max."""
    taus = np.arange(1, tau_max + 1, dtype=np.float64)
    u = taus**2
    d = np.empty((tau_max,) + cube.shape[1:], dtype=np.float64)
    for i, t in enumerate(taus.astype(int)):
        diff = cube[t:].astype(np.float64) - cube[:-t].astype(np.float64)
        d[i] = 0.5 * np.mean(diff * diff, axis=0)
    ub, db = u.mean(), d.mean(axis=0)
    suu = np.sum((u - ub) ** 2)
    sud = np.tensordot(u - ub, d - db, axes=(0, 0))
    b = sud / suu
    a = db - b * ub
    return a, b


def sg_sigma(cube):
    sm = savgol_filter(cube.astype(np.float64), SG_WIN, SG_ORD, axis=0, mode="interp")
    res = cube - sm
    return np.sqrt(np.mean(res * res, axis=0) / (1.0 - LEV))


def k3(cube, planted_rel):
    """Plant a known sigma_F on the measured focus curves and try to recover it."""
    truth = savgol_filter(cube.astype(np.float64), 21, 3, axis=0, mode="interp")
    sigma = planted_rel * m69.FOCUS_NOISE_SD
    rng = np.random.default_rng(606)
    synth = (truth + sigma * rng.standard_normal(truth.shape)).astype(np.float32)
    a, _ = structure_intercept(synth)
    s_sf = np.sqrt(np.maximum(a, 0.0)).mean() / sigma
    s_sg = sg_sigma(synth).mean() / sigma
    return float(s_sf), float(s_sg)


def run(stack, limit=None):
    m69.banner(f"A5 -- {stack}")
    cube, levels, iso, files = response_cube(stack, limit)
    n = cube.shape[0]

    drift = float(np.std(np.diff(levels) / levels[:-1]))
    span = float((levels.max() - levels.min()) / levels.mean())
    print(f"    K4 photometric: frame-to-frame relative level SD {drift:.4%},"
          f" full span {span:.4%}")

    rec_sf, rec_sg = k3(cube, 1.0)
    ok_sf = abs(rec_sf - 1.0) <= 0.05
    ok_sg = abs(rec_sg - 1.0) <= 0.05
    print(f"    K3 recovery of a planted sigma_F: structure-function {rec_sf:.4f}"
          f" ({'MET' if ok_sf else 'NOT MET'}), Savitzky-Golay {rec_sg:.4f}"
          f" ({'MET' if ok_sg else 'NOT MET'})   bar +-5%")

    a, b = structure_intercept(cube)
    sf = np.sqrt(np.maximum(a, 0.0))
    sg = sg_sigma(cube)
    s1 = m69.summarise(sf, f"{stack}/structure")
    s2 = m69.summarise(sg, f"{stack}/savgol")
    m69.print_header()
    m69.print_row(s1)
    m69.print_row(s2)
    return {
        "n": n,
        "iso": iso,
        "grid": list(cube.shape[1:]),
        "drift_sd": drift,
        "level_span": span,
        "k3_structure": rec_sf,
        "k3_savgol": rec_sg,
        "k3_structure_met": bool(ok_sf),
        "k3_savgol_met": bool(ok_sg),
        "structure": s1,
        "savgol": s2,
        "slope_b_median": float(np.median(b)),
    }


def main():
    stacks = sys.argv[1:] or ["coffee-bean"]
    m69.banner("M69 arm A5 -- response noise on real stacks, no synthetic noise")
    m69.dump_constants()
    print(f"\n  crop {CROP} raw px, decimation {DECIM}, tau_max {TAU_MAX},"
          f" SG window {SG_WIN} order {SG_ORD}, centre leverage {LEV:.4f}")
    out = {}
    for s in stacks:
        out[s] = run(s)
    tag = "-".join(stacks)
    (m69.OUT / f"50-a5-{tag}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n  wrote out/50-a5-{tag}.json")


if __name__ == "__main__":
    main()
