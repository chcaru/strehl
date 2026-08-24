"""M66 arm B - the operator null, and control K6.

A synthetic static burst on M62's plant: the 2048x2048 RGGB crop of
`109MSDCF/DSC00020.ARW` at (y=1024, x=4096), ISO 160, plus INDEPENDENT sensor
noise per frame from the crate's own model. Every frame is a sample of the same
latent, so every frame has the same TRUE focus response and H0 holds exactly at
every pixel. Subsetting therefore varies N and nothing else - the frames are
exchangeable by construction.

This is deliberately NOT used for blast radius. A static burst is degenerate for
focus (M62 section 4, M64 section 2.4) and cannot speak for a real stack. It is
here because H0 is the regime in which the winner's-curse mechanism is DEFINED,
which makes it the cleanest instrument for the mechanism and a useless one for
consequences.

Also measures the thing arm A has to assume: the ACTUAL temporal standard
deviation of the regularised response on real scene content, against the crate's
FOCUS_NOISE_SD, which was measured on a pure-noise plane.
"""

import json
import pathlib
import sys
import time

import numpy as np
import rawpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import importlib  # noqa: E402

fields = importlib.import_module("02-fields")
from kernel import n_eff, subset  # noqa: E402
from m66 import (  # noqa: E402
    BASE_ISO,
    BLACK,
    CORPUS,
    FOCUS_NOISE_SD,
    GAIN_DIVISOR,
    GATES,
    N_GRID,
    OUT,
    READ_NOISE_E_HIGH,
    READ_NOISE_E_LOW,
    SECOND_BASE_ISO,
    banner,
)

LATENT_FILE = pathlib.Path(CORPUS) / "109MSDCF" / "DSC00020.ARW"
CROP_Y, CROP_X, CROP = 1024, 4096, 2048
ISO = 160.0
NMAX = max(N_GRID)


def read_latent():
    with rawpy.imread(str(LATENT_FILE)) as rr:
        v = rr.raw_image_visible
        lat = np.array(
            v[CROP_Y : CROP_Y + CROP, CROP_X : CROP_X + CROP], dtype=np.float64
        )
    return lat


def noise_sd(latent):
    g = max(ISO, BASE_ISO) / GAIN_DIVISOR
    rn = READ_NOISE_E_HIGH if ISO >= SECOND_BASE_ISO else READ_NOISE_E_LOW
    read_dn = rn * g
    var = g * np.maximum(latent - BLACK, 0.0) + read_dn * read_dn
    return np.sqrt(var), g, read_dn


def build_burst(seed, n):
    latent = read_latent()
    sd, g, read_dn = noise_sd(latent)
    rng = np.random.default_rng(seed)
    cube = np.empty((n, CROP // 2, CROP // 2), dtype=np.float32)
    temporal = []
    for k in range(n):
        frame = latent + sd * rng.standard_normal(latent.shape)
        g1 = np.maximum(frame[0::2, 1::2] - BLACK, 0.0)
        g2 = np.maximum(frame[1::2, 0::2] - BLACK, 0.0)
        luma = 0.5 * (g1 + g2)
        f = fields.clamped_box(fields.sobel_mag(luma), fields.WINDOW_RADIUS)
        f /= np.maximum(fields.green_luma_sigma(luma, ISO), fields.SIGMA_EPS)
        cube[k] = fields.clamped_box(f, fields.REGULARISER_RADIUS).astype(np.float32)
        if k < 4:
            temporal.append(float(np.sqrt(((frame - latent) ** 2).mean())))
    return cube.reshape(n, -1), {
        "gain_dn_per_e": g,
        "read_dn": read_dn,
        "model_pooled_sd_dn": float(np.sqrt((sd**2).mean())),
        "empirical_frame_sd_dn": temporal,
        "latent_green_signal_dn": float(
            (0.5 * (latent[0::2, 1::2] + latent[1::2, 0::2]) - BLACK).mean()
        ),
    }


banner("M66 arm B - synthetic static burst through the real operator")
print(f"  latent {LATENT_FILE}  crop {CROP}^2 at (y={CROP_Y}, x={CROP_X}), ISO {ISO:.0f}")
t0 = time.time()
out = {"plant": {}, "seeds": {}, "focus_noise_sd_crate": FOCUS_NOISE_SD}

for seed in (0, 1):
    cube, plant = build_burst(seed, NMAX)
    out["plant"][str(seed)] = plant
    print(
        f"\n  seed {seed}: N={NMAX}, plane {int(np.sqrt(cube.shape[1]))}^2, "
        f"model pooled sd {plant['model_pooled_sd_dn']:.4f} DN, "
        f"empirical first frames {['%.4f' % x for x in plant['empirical_frame_sd_dn']]} DN"
        f"  [{time.time() - t0:.0f}s]"
    )

    # The quantity arm A has to assume: temporal SD of the regularised response
    # on real scene content, against the crate constant measured on pure noise.
    sd_resp = cube.std(axis=0, ddof=1)
    rho = float(sd_resp.mean() / FOCUS_NOISE_SD)
    out["seeds"].setdefault(str(seed), {})["response_sd"] = {
        "mean": float(sd_resp.mean()),
        "median": float(np.median(sd_resp)),
        "p05": float(np.percentile(sd_resp, 5)),
        "p95": float(np.percentile(sd_resp, 95)),
        "crate_FOCUS_NOISE_SD": FOCUS_NOISE_SD,
        "rho_mean_over_crate": rho,
    }
    print(
        f"    response temporal SD: mean {sd_resp.mean():.6f}  median "
        f"{np.median(sd_resp):.6f}  p05 {np.percentile(sd_resp, 5):.6f}  "
        f"p95 {np.percentile(sd_resp, 95):.6f}   vs crate {FOCUS_NOISE_SD:.6f}"
        f"   rho = {rho:.4f}"
    )

    rows = {}
    for n in N_GRID:
        if n > NMAX:
            continue
        r = {}
        for mode in ("prefix", "stride", "random"):
            reps = 1 if (n == NMAX or mode != "random") else 4
            vals = []
            for rep in range(reps):
                idx = subset(mode, NMAX, n, rep)
                st, _ = n_eff(cube, idx, GATES)
                vals.append(st)
            r[mode] = {
                str(g): {
                    "mean_n_eff": float(np.mean([v[g]["mean_n_eff"] for v in vals])),
                    "n_eff_over_N": float(np.mean([v[g]["n_eff_over_N"] for v in vals])),
                    "sd_over_reps": float(
                        np.std([v[g]["n_eff_over_N"] for v in vals], ddof=1)
                    )
                    if reps > 1
                    else 0.0,
                    "frac_n1": float(np.mean([v[g]["frac_n1"] for v in vals])),
                    "reps": reps,
                }
                for g in GATES
            }
        rows[str(n)] = r
    out["seeds"][str(seed)]["rows"] = rows
    del cube

    print(f"\n    admitted FRACTION n_eff/N, stride subsets, seed {seed}:")
    print("      N    " + "".join(f"{'T=' + str(g):>12}" for g in GATES))
    for n in N_GRID:
        if n > NMAX:
            continue
        line = f"      {n:<5}"
        for g in GATES:
            line += f"  {rows[str(n)]['stride'][str(g)]['n_eff_over_N']:>10.6f}"
        print(line)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "04-burst.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {OUT / '04-burst.json'}   [{time.time() - t0:.0f}s total]")
