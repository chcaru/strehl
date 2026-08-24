"""M69 -- the corpus's own rho, per stack, from the derived predictor P2.

For each stack, three frames (first, middle, last) are read, and P2 is evaluated
on a central 2048 raw-pixel crop. Two columns are reported:

  rho_obs   P2 on the frame as captured. Comparable to the frozen-latent arms
            (M66 K7, M69 A2), which also treat the observed frame as the latent.
  rho_true  P2 with the deterministic gradient debiased by the noise floor,
            E|grad T|^2 = E|grad L|^2 - 2 s^2. This is the value that applies to
            a real frame, whose latent is the scene and whose noise is eta.

Both are dimensionless multipliers on FOCUS_NOISE_SD.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

a2 = __import__("importlib").import_module("20-a2-m66-replication")
p2m = __import__("importlib").import_module("40-p2-predictor")

S_SOBEL = 0.125 * np.sqrt(12.0)
CROP = 2048

STACKS = [
    "coffee-bubbles", "109MSDCF", "119MSDCF", "113MSDCF", "112MSDCF",
    "foam", "coffee-bean", "wrapped-text-2", "wrapped-text-1",
    "bee-1", "bee-2", "bee-3",
]


def rho_for(path):
    v = m69.raw_visible(path)
    y = (v.shape[0] - CROP) // 2
    x = (v.shape[1] - CROP) // 2
    y -= y % 2
    x -= x % 2
    luma = m69.luma_from_raw(v[y : y + CROP, x : x + CROP].copy())
    iso = m69.iso_of(path)
    sig = m69.green_luma_sigma(luma, iso)
    gx, gy = m69.sobel_components(luma)
    g2 = gx * gx + gy * gy
    s2 = (S_SOBEL * sig) ** 2
    scale = np.sqrt(np.maximum(g2 - 2.0 * s2, 0.0) / np.maximum(g2, 1e-30))
    obs = m69.interior(p2m.p2(luma, sig)) / m69.FOCUS_NOISE_SD
    true = m69.interior(p2m.p2_scaled(luma, sig, scale)) / m69.FOCUS_NOISE_SD
    z = np.sqrt(np.maximum(g2 - 2.0 * s2, 0.0) / np.maximum(s2, 1e-30))
    return iso, obs, true, float(np.median(z))


def main():
    m69.banner("M69 -- per-stack rho from P2")
    m69.dump_constants()
    print(f"\n  {'stack':<16} {'N':>4} {'ISO':>5} {'med z':>7} {'rho_obs':>9}"
          f" {'rho_true':>9} {'p05':>8} {'p95':>8} {'IQR/med':>8}")
    print("  " + "-" * 82)
    out = {}
    for st in STACKS:
        files = m69.stack_files(st)
        picks = [files[0], files[len(files) // 2], files[-1]]
        obs_all, true_all, zs, iso = [], [], [], None
        for p in picks:
            iso, obs, true, zmed = rho_for(p)
            obs_all.append(obs)
            true_all.append(true)
            zs.append(zmed)
        obs_c = np.concatenate([a.ravel() for a in true_all])
        rho_obs = float(np.mean([a.mean() for a in obs_all]))
        rho_true = float(np.mean([a.mean() for a in true_all]))
        q1, q2, q3 = np.percentile(obs_c, [25, 50, 75])
        rec = {
            "n": len(files),
            "iso": iso,
            "median_z": float(np.mean(zs)),
            "rho_obs": rho_obs,
            "rho_true": rho_true,
            "rho_true_per_frame": [float(a.mean()) for a in true_all],
            "p05": float(np.percentile(obs_c, 5)),
            "p95": float(np.percentile(obs_c, 95)),
            "iqr_rel": float((q3 - q1) / q2),
        }
        out[st] = rec
        print(f"  {st:<16} {rec['n']:>4} {iso:>5.0f} {rec['median_z']:>7.2f}"
              f" {rho_obs:>9.4f} {rho_true:>9.4f} {rec['p05']:>8.4f} {rec['p95']:>8.4f}"
              f" {rec['iqr_rel']:>8.4f}")
    r = np.array([v["rho_true"] for v in out.values()])
    print(f"\n  rho_true across the corpus: min {r.min():.4f}  max {r.max():.4f}"
          f"  span {r.max() / r.min():.3f}x  median {np.median(r):.4f}")
    (m69.OUT / "80-corpus-rho.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n  wrote out/80-corpus-rho.json")


if __name__ == "__main__":
    main()
