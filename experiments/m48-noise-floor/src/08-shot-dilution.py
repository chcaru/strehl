r"""M48 script 08 -- why the read-noise fix did NOT move the merge gate.

Context. Scripts 01-07 established `read_noise_e_high` 1.47 -> 1.2392, and
script 07 measured the consequence for the gate calibration AT S = 0 (dark
frames): a 17.4% spread in effective response SD across ISO, and a predicted
18.6% rescaling of every normalised focus response in the high-gain mode.

That prediction was REFUTED end to end. Running `strehl merge` on the real
ISO-1000 stack `D:\personal\macro\coffee-bubbles` under both constants moved
mean n_eff by 0.08%-0.34%, not 18.6%. This script measures the mechanism.

The model is sigma_DN(S) = sqrt(g*S + (RN_e*g)^2) with g = max(iso,base)/436.8
(noise.rs `PlaneNoise::variance`), so the read-noise change is diluted by the
shot term at every pixel carrying signal. The observable is the per-pixel ratio

    r(S) = sigma_new(S) / sigma_old(S)

whose deviation from 1 bounds the shift in that pixel's gate decision, since a
normalised focus response is R/sigma and the gate compares differences of it.

Read-only: opens frames under D:\personal\macro and C:\dev\macro, writes only
to this experiment's data/ directory.
"""

import json
import os

import numpy as np
import rawpy

GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
RN_LOW = 4.20
RN_OLD_HIGH = 1.47
RN_NEW_HIGH = 1.2392

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "shot-dilution.json")

# (label, directory, iso, how many frames to sample)
STACKS = [
    ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles", 1000.0, 3),
    ("113MSDCF", r"D:\personal\macro\113MSDCF", 500.0, 3),
    ("119MSDCF-placebo", r"C:\dev\macro\test\119MSDCF", 50.0, 2),
]


def gain(iso):
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def read_noise(iso, high_value):
    return high_value if iso >= SECOND_BASE_ISO else RN_LOW


def sigma(signal_dn, g, rn_e):
    """noise.rs PlaneNoise::variance, then sqrt. Signal is clamped at 0."""
    s = np.maximum(signal_dn, 0.0)
    read_dn = rn_e * g
    return np.sqrt(g * s + read_dn * read_dn)


def green_luma(path):
    """Black-subtracted green luma L = (G1+G2)/2 per 2x2 site, in DN."""
    with rawpy.imread(path) as raw:
        img = raw.raw_image_visible.astype(np.float64)
        colors = raw.raw_colors_visible
        black = np.array(raw.black_level_per_channel, dtype=np.float64)
    # Sony ARW is RGGB: colour index 1 is G1, 3 is G2 (rawpy splits the greens).
    h, w = img.shape
    h -= h % 2
    w -= w % 2
    img = img[:h, :w]
    colors = colors[:h, :w]
    sub = img - black[colors]
    # The two greens of each 2x2 site, averaged.
    q = sub.reshape(h // 2, 2, w // 2, 2)
    qc = colors.reshape(h // 2, 2, w // 2, 2)
    g_mask = (qc == 1) | (qc == 3)
    n = g_mask.sum(axis=(1, 3))
    tot = (q * g_mask).sum(axis=(1, 3))
    return np.where(n > 0, tot / np.maximum(n, 1), 0.0)


def main():
    results = []
    for label, d, iso, nframes in STACKS:
        files = sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))[:nframes]
        if not files:
            results.append({"stack": label, "error": "no ARW"})
            continue
        g = gain(iso)
        high = iso >= SECOND_BASE_ISO
        rn_old = read_noise(iso, RN_OLD_HIGH)
        rn_new = read_noise(iso, RN_NEW_HIGH)

        lumas = [green_luma(os.path.join(d, f)) for f in files]
        s = np.concatenate([x.ravel() for x in lumas])

        s_old = sigma(s, g, rn_old)
        s_new = sigma(s, g, rn_new)
        r = s_new / s_old
        # A pixel's normalised response scales by 1/r; the gate decision at that
        # pixel shifts by the same factor.
        shift = np.abs(1.0 / r - 1.0)

        pct = [0.1, 1, 5, 25, 50, 75, 95, 99]
        results.append(
            {
                "stack": label,
                "iso": iso,
                "high_gain_mode": bool(high),
                "frames": files,
                "gain_dn_per_e": g,
                "read_noise_old_e": rn_old,
                "read_noise_new_e": rn_new,
                "n_pixels": int(s.size),
                "signal_dn_percentiles": {
                    str(p): float(np.percentile(s, p)) for p in pct
                },
                "signal_dn_median": float(np.median(s)),
                "sigma_ratio_at_zero_signal": float(rn_new / rn_old) if high else 1.0,
                "sigma_ratio_percentiles": {
                    str(p): float(np.percentile(r, p)) for p in pct
                },
                "sigma_ratio_mean": float(r.mean()),
                "response_shift_mean_pct": float(shift.mean() * 100.0),
                "response_shift_median_pct": float(np.median(shift) * 100.0),
                "response_shift_p99_pct": float(np.percentile(shift, 99) * 100.0),
                "frac_pixels_shift_over_1pct": float((shift > 0.01).mean()),
                "frac_pixels_shift_over_5pct": float((shift > 0.05).mean()),
                "frac_pixels_shift_over_10pct": float((shift > 0.10).mean()),
                # Where the dilution crosses over: signal at which the shot term
                # equals the OLD read term, i.e. g*S = (rn_old*g)^2.
                "shot_equals_read_at_dn": float(rn_old * rn_old * g),
                "frac_pixels_below_crossover": float((s < rn_old * rn_old * g).mean()),
            }
        )
        print(
            f"{label:18} ISO {iso:6.0f}  median S = {np.median(s):8.1f} DN  "
            f"r(S=0) = {(rn_new/rn_old if high else 1.0):.5f}  "
            f"mean |1/r-1| = {shift.mean()*100:6.3f}%  "
            f"median = {np.median(shift)*100:6.3f}%  "
            f">1%: {(shift>0.01).mean()*100:5.2f}%"
        )

    payload = {
        "_meta": {
            "script": "08-shot-dilution.py",
            "purpose": "measure why the read_noise_e_high fix did not move the "
            "merge gate on real frames: shot-noise dilution",
            "model": "sigma_DN = sqrt(g*S + (RN_e*g)^2), noise.rs variance()",
        },
        "stacks": results,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
