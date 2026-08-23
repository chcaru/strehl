"""M48 step 7 - what FOCUS_NOISE_SD actually depends on, and what it does not.

The question this answers: `read_noise_e_high` moved 1.47 -> 1.2392 in commit
f95f6f4. Does `FOCUS_NOISE_SD = 0.015214` (crates/strehl-core/src/merge.rs:173)
need to move with it?

Three measurements, in increasing order of how much they matter.

A. THE SCALING LAW. The focus response is
   `box_mean_r8(box_mean_r13(|grad L|) / sigma_model)`, so it is exactly linear
   in `1/sigma_model`. If the noise model over-predicts by a factor k, every
   response and therefore the response SD is divided by k. That is algebra;
   this measures it, on the operator, because discipline 305 says measure the
   observable rather than assert the sign.

B. WHAT THE IN-CRATE MEASUREMENT ACTUALLY MEASURES. The shipped constant is
   measured by `merge.rs::the_focus_noise_constant_is_the_measured_one` against
   `unit_sigma_model()` - a hand-built PlaneNoise with gain 1e-4 and
   read_noise_e sqrt(2)/gain. The plant draws noise of sd 1 and the operator
   divides by a model that says sd 1. k == 1 by construction. This reproduces
   that number and then shows what the plant CANNOT see.

C. THE NUMBER THAT ACTUALLY MATTERS. On real frames sigma_model is the camera
   profile's and sigma_true is the sensor's, so k = model/measured, which M48
   measured at 11 ISOs. The response SD on real data is FOCUS_NOISE_SD / k, and
   it is not one number - it varies with ISO by more than the constant's own
   error bar. Reported for the old constant, the new one, and the M1 shared-floor
   model, so the question "should it be a constant at all" has a measured answer.

Operator model: M43's `02b-operator-noise-spread.py`, which reproduced the
shipped FOCUS_NOISE_SD to within 0.5%. Reused deliberately rather than rewritten
- if it is wrong, it is wrong the same way it was wrong when M43 published, and
that is checkable.
"""

import json
import pathlib

import numpy as np

# crates/strehl-core/src/merge.rs:173, and its published error bar (fact 313).
FOCUS_NOISE_SD = 0.015214
FOCUS_NOISE_SEM = 0.000075
WINDOW_RADIUS = 13
REGULARISER_RADIUS = 8
SUPPORT_RADIUS = WINDOW_RADIUS + 1  # Sobel stencil inside the box

SIDE = 512  # the size merge.rs settled on after its size-drift check
SEEDS = 12  # merge.rs uses 12 seeds

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "focus-noise-basis.json"

# M48's measured dark table (pooled RMS, 4-plane mean) and the model at each of
# the three candidate high-mode constants. Straight from
# crates/strehl-core/src/profile.rs::DARK_SIGMA_RMS_DN and read-noise-fit.json.
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
ISOS = [50, 100, 200, 250, 400, 500, 640, 800, 1000, 1600, 2000]
MEASURED_DN = {
    50: 0.986524,
    100: 0.984440,
    200: 1.741494,
    250: 2.162736,
    400: 1.198538,
    500: 1.467830,
    640: 1.807805,
    800: 2.246382,
    1000: 2.808366,
    1600: 4.405162,
    2000: 5.532721,
}
# M1 (shared additive DN floor), fitted across all 11 ISOs in 05-read-noise-fit.py.
M1_RN_LO, M1_RN_HI, M1_FLOOR = 3.665707757812649, 1.1960058379650838, 0.509925652718645


def replicate(a, dy, dx):
    """Edge-replicating shift, matching PlaneGeometry's clamp-to-edge."""
    out = a
    if dy:
        out = np.roll(out, -dy, axis=0)
        if dy > 0:
            out[-dy:, :] = a[-1, :]
        else:
            out[:-dy, :] = a[0, :]
    if dx:
        s = np.roll(out, -dx, axis=1)
        if dx > 0:
            s[:, -dx:] = out[:, -1][:, None]
        else:
            s[:, :-dx] = out[:, 0][:, None]
        out = s
    return out


def box_mean(a, r):
    if r == 0:
        return a.copy()
    pad = np.pad(a, ((r, r), (r, r)), mode="edge")
    c = np.cumsum(pad, axis=0)
    c = np.vstack([np.zeros((1, c.shape[1])), c])
    a = (c[2 * r + 1 :, :] - c[: -(2 * r + 1), :]) / (2 * r + 1)
    c = np.cumsum(a, axis=1)
    c = np.hstack([np.zeros((c.shape[0], 1)), c])
    return (c[:, 2 * r + 1 :] - c[:, : -(2 * r + 1)]) / (2 * r + 1)


def sobel_mag(a):
    gx = 0.125 * (
        replicate(a, -1, 1)
        + 2.0 * replicate(a, 0, 1)
        + replicate(a, 1, 1)
        - replicate(a, -1, -1)
        - 2.0 * replicate(a, 0, -1)
        - replicate(a, 1, -1)
    )
    gy = 0.125 * (
        replicate(a, 1, -1)
        + 2.0 * replicate(a, 1, 0)
        + replicate(a, 1, 1)
        - replicate(a, -1, -1)
        - 2.0 * replicate(a, -1, 0)
        - replicate(a, -1, 1)
    )
    return np.sqrt(gx * gx + gy * gy)


def response(luma, sigma_model):
    """The shipped chain: |grad| -> box r13 -> /sigma -> regularise r8.

    focus.rs normalises AFTER the window (normalise_by_luma_sigma is applied to
    the windowed field), and merge.rs regularises after that.
    """
    windowed = box_mean(sobel_mag(luma), WINDOW_RADIUS)
    return box_mean(windowed / sigma_model, REGULARISER_RADIUS)


def interior_sd(field):
    m = SUPPORT_RADIUS + REGULARISER_RADIUS
    v = field[m:-m, m:-m].ravel()
    return float(v.std(ddof=1)), float(v.mean()), int(v.size)


def model_sigma_dn(iso, rn_lo, rn_hi, floor=0.0):
    """profile.rs's relation at S = 0 (a dark frame), optionally with M1's floor."""
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = rn_lo if iso < SECOND_BASE_ISO else rn_hi
    return float(np.hypot(rn * g, floor))


def main():
    rng_seeds = [0xC0FFEE, 0x5EED, 0xBADF00D, 1, 2, 3, 0xDEADBEEF, 0x12345678,
                 99, 0xFACE, 0xA5A5A5A5, 7][:SEEDS]
    out = {}

    # --- A + B: reproduce the in-crate constant, then break its plant. -------
    # k is the factor by which the model over-predicts the true noise. The
    # in-crate measurement is pinned at k = 1 because its plant supplies its own
    # sigma. Real data is not.
    ks = [0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.1232, 1.20, 1.2223, 1.30]
    per_k = {f"{k:.4f}": [] for k in ks}
    means_at_1 = []
    for seed in rng_seeds:
        rng = np.random.default_rng(seed)
        luma = rng.standard_normal((SIDE, SIDE))
        # sigma_true = 1 by construction; sigma_model = k.
        windowed = box_mean(sobel_mag(luma), WINDOW_RADIUS)
        for k in ks:
            sd, mean, n = interior_sd(box_mean(windowed / k, REGULARISER_RADIUS))
            per_k[f"{k:.4f}"].append(sd)
            if k == 1.00:
                means_at_1.append(mean)

    sd1 = float(np.mean(per_k["1.0000"]))
    sem1 = float(np.std(per_k["1.0000"], ddof=1) / np.sqrt(SEEDS))
    rayleigh_mean = 0.125 * np.sqrt(12.0) * np.sqrt(np.pi / 2.0)
    out["A_scaling"] = {
        "sd_at_k1": sd1,
        "sem_at_k1": sem1,
        "vs_shipped_constant": sd1 / FOCUS_NOISE_SD,
        "response_mean_at_k1": float(np.mean(means_at_1)),
        "closed_form_rayleigh_mean": float(rayleigh_mean),
        "mean_vs_closed_form": float(np.mean(means_at_1)) / float(rayleigh_mean),
        "per_k": {
            kk: {
                "sd": float(np.mean(v)),
                "sd_times_k": float(np.mean(v)) * float(kk),
                "ratio_to_k1": float(np.mean(v)) / sd1,
                "predicted_ratio_1_over_k": 1.0 / float(kk),
            }
            for kk, v in per_k.items()
        },
    }

    # --- C: the effective response SD on the real sensor, per ISO. ----------
    variants = {
        "shipped_old_1.47": dict(rn_lo=4.20, rn_hi=1.47, floor=0.0),
        "shipped_new_1.2392": dict(rn_lo=4.20, rn_hi=1.2392, floor=0.0),
        "M1_shared_floor": dict(rn_lo=M1_RN_LO, rn_hi=M1_RN_HI, floor=M1_FLOOR),
    }
    out["C_effective"] = {}
    for name, p in variants.items():
        rows = {}
        for iso in ISOS:
            model = model_sigma_dn(iso, **p)
            k = model / MEASURED_DN[iso]
            rows[str(iso)] = {
                "model_dn": model,
                "measured_dn": MEASURED_DN[iso],
                "k_model_over_true": k,
                "effective_response_sd": FOCUS_NOISE_SD / k,
                "gate_error_pct": 100.0 * (k - 1.0),
            }
        eff = np.array([rows[str(i)]["effective_response_sd"] for i in ISOS])
        # Weight every ISO equally: the question is whether ONE number serves all.
        rows_summary = {
            "mean": float(eff.mean()),
            "min": float(eff.min()),
            "max": float(eff.max()),
            "spread_pct": float(100.0 * (eff.max() / eff.min() - 1.0)),
            "rms_rel_dev_from_shipped_const": float(
                np.sqrt(np.mean((eff / FOCUS_NOISE_SD - 1.0) ** 2))
            ),
            "max_abs_rel_dev_from_shipped_const": float(
                np.abs(eff / FOCUS_NOISE_SD - 1.0).max()
            ),
            # Best single scalar under relative least squares, and what it leaves.
            "best_single_scalar": float(
                np.sum(1.0 / eff) / np.sum(1.0 / eff**2)
            ),
        }
        best = rows_summary["best_single_scalar"]
        rows_summary["max_abs_rel_dev_from_best_scalar"] = float(
            np.abs(best / eff - 1.0).max()
        )
        # Is one scalar defensible? Compare the across-ISO spread against the
        # constant's OWN published measurement error (fact 313).
        rows_summary["spread_in_units_of_published_sem"] = float(
            (eff.max() - eff.min()) / FOCUS_NOISE_SEM
        )
        out["C_effective"][name] = {"per_iso": rows, "summary": rows_summary}

    out["_meta"] = {
        "side": SIDE,
        "seeds": SEEDS,
        "shipped_focus_noise_sd": FOCUS_NOISE_SD,
        "shipped_focus_noise_sem": FOCUS_NOISE_SEM,
        "operator_model_source": "experiments/m43-plugin-seam/02b-operator-noise-spread.py",
        "note": (
            "RNG is numpy PCG64, not merge.rs's SplitMix64+Box-Muller. M43 fact "
            "312 showed the generator matters (a plain LCG moved the constant "
            "1.30x across seeds); PCG64 is not an LCG and the 12-seed spread "
            "here is the check on that."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    # ---- console ----------------------------------------------------------
    print(f"A. in-crate reproduction at k=1: {sd1:.6e} +/- {sem1:.2e}")
    print(f"   shipped constant             : {FOCUS_NOISE_SD:.6e}")
    print(f"   ratio                        : {sd1 / FOCUS_NOISE_SD:.4f}")
    print(f"   response mean / Rayleigh     : {out['A_scaling']['mean_vs_closed_form']:.4f}")
    print()
    print("A. scaling law: response SD against model over-prediction factor k")
    print(f"   {'k':>8} {'sd':>12} {'sd*k':>12} {'sd/sd(k=1)':>11} {'pred 1/k':>10} {'err':>9}")
    for kk in [f"{k:.4f}" for k in ks]:
        d = out["A_scaling"]["per_k"][kk]
        err = d["ratio_to_k1"] / d["predicted_ratio_1_over_k"] - 1.0
        print(f"   {kk:>8} {d['sd']:>12.6e} {d['sd_times_k']:>12.6e} "
              f"{d['ratio_to_k1']:>11.5f} {d['predicted_ratio_1_over_k']:>10.5f} {err:>+9.2e}")
    print()
    for name in variants:
        s = out["C_effective"][name]["summary"]
        print(f"C. {name}")
        print(f"   {'ISO':>6} {'k':>9} {'eff sd':>12} {'vs const':>9}")
        for iso in ISOS:
            r = out["C_effective"][name]["per_iso"][str(iso)]
            print(f"   {iso:>6} {r['k_model_over_true']:>9.4f} "
                  f"{r['effective_response_sd']:>12.6e} "
                  f"{100 * (r['effective_response_sd'] / FOCUS_NOISE_SD - 1):>+8.2f}%")
        print(f"   spread across ISO: {s['spread_pct']:.2f}%  "
              f"= {s['spread_in_units_of_published_sem']:.1f} published SEMs")
        print(f"   worst vs shipped 0.015214 : {100 * s['max_abs_rel_dev_from_shipped_const']:+.2f}%")
        print(f"   best single scalar        : {s['best_single_scalar']:.6e}, "
              f"worst residual {100 * s['max_abs_rel_dev_from_best_scalar']:.2f}%")
        print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
