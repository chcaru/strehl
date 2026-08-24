"""M66 control K7 (POST-HOC) - does my burst pipeline reproduce FOCUS_NOISE_SD?

Arm B measured the temporal SD of the regularised response on REAL scene content
and got rho = 1.21 against the crate's FOCUS_NOISE_SD. That number only means
something if the same pipeline recovers rho = 1.00 on the plant the crate's own
constant was measured on: a pure-noise plane with no scene.

This is the control that decides between "the crate constant is the wrong scale
on real content" and "my burst pipeline is miscalibrated". It can fail.

Three plants, same operator, same noise model:
  FLAT      constant latent + sensor noise      -> must reproduce FOCUS_NOISE_SD
  SMOOTH    M62's latent, 4x4-box pre-smoothed  -> scene texture with the
            latent's own per-sample noise suppressed
  REAL      M62's latent as-is                  -> arm B's plant
"""

import json
import pathlib
import sys

import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import importlib  # noqa: E402

fields = importlib.import_module("02-fields")
burst = importlib.import_module("04-burst")
from m66 import BLACK, FOCUS_NOISE_SD, OUT, banner  # noqa: E402

NREP = 64


def response_cube(latent, n, seed):
    sd, _, _ = burst.noise_sd(latent)
    rng = np.random.default_rng(seed)
    out = np.empty((n, latent.shape[0] // 2, latent.shape[1] // 2), dtype=np.float32)
    for k in range(n):
        frame = latent + sd * rng.standard_normal(latent.shape)
        g1 = np.maximum(frame[0::2, 1::2] - BLACK, 0.0)
        g2 = np.maximum(frame[1::2, 0::2] - BLACK, 0.0)
        luma = 0.5 * (g1 + g2)
        f = fields.clamped_box(fields.sobel_mag(luma), fields.WINDOW_RADIUS)
        f /= np.maximum(fields.green_luma_sigma(luma, burst.ISO), fields.SIGMA_EPS)
        out[k] = fields.clamped_box(f, fields.REGULARISER_RADIUS).astype(np.float32)
    return out.reshape(n, -1)


banner("M66 control K7 (post-hoc) - response temporal SD by plant")
real = burst.read_latent()
mean_dn = float(real.mean())
flat = np.full_like(real, mean_dn)
smooth = uniform_filter(real, size=4, mode="nearest")

# Interior only, so the clamped-box border policy does not enter the SD.
inset = fields.WINDOW_RADIUS + fields.REGULARISER_RADIUS + 2
side = real.shape[0] // 2

rows = {}
print(f"  {'plant':<8} {'mean DN':>9}  {'SD mean':>10}  {'SD median':>10}"
      f"  {'p05':>9}  {'p95':>9}  {'rho=mean/crate':>15}")
for name, lat in (("FLAT", flat), ("SMOOTH", smooth), ("REAL", real)):
    cube = response_cube(lat, NREP, seed=7)
    sd = cube.std(axis=0, ddof=1).reshape(side, side)[inset:-inset, inset:-inset]
    rho = float(sd.mean() / FOCUS_NOISE_SD)
    rows[name] = {
        "latent_mean_dn": float(lat.mean()),
        "sd_mean": float(sd.mean()),
        "sd_median": float(np.median(sd)),
        "p05": float(np.percentile(sd, 5)),
        "p95": float(np.percentile(sd, 95)),
        "rho": rho,
        "frames": NREP,
        "interior_inset": inset,
    }
    print(f"  {name:<8} {lat.mean():>9.1f}  {sd.mean():>10.6f}  {np.median(sd):>10.6f}"
          f"  {np.percentile(sd, 5):>9.6f}  {np.percentile(sd, 95):>9.6f}  {rho:>15.4f}")
    del cube

print(f"\n  crate FOCUS_NOISE_SD = {FOCUS_NOISE_SD:.6f}")
ok = abs(rows["FLAT"]["rho"] - 1.0) <= 0.05
print(f"  K7 {'PASS' if ok else 'NOT MET'}: FLAT rho = {rows['FLAT']['rho']:.4f}, "
      f"criterion |rho - 1| <= 0.05")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "07-response-sd.json").write_text(
    json.dumps({"rows": rows, "crate": FOCUS_NOISE_SD, "k7_pass": bool(ok)}, indent=2),
    encoding="utf-8",
)
print(f"\nwrote {OUT / '07-response-sd.json'}")
