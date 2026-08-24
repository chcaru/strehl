"""E9 -- is the optical centre actually displaced, or is it just badly determined?

PRE-REGISTRATION-3 registered `centre_offset = (0, 0)` as an ASSUMPTION and
promised to bound it rather than assert it. Then E2's own output turned out to
fit the centre as free parameters, and it lands at (893.4, -601.9) plane px --
1077 px from the plane centre, which is half the half-diagonal. Taken at face
value that would mean the shipped record is badly wrong, because leaving the
centre at zero would strand `eps * 1077 = 0.76` px of the 1.43 px defect.

But a fitted centre is a RATIO, `coef[1] / eps`, and ratios blow up when the
denominator is small and the design is poorly conditioned. Two of the three
E2 fits already return centres far outside the sensor (dB at -5937, the null at
+1466), which is a strong hint that this parameter is not identified by 20 ROIs.

So the question is not "what is the centre" but "is the centre identified at
all", and the honest test is whether dropping it costs any fit quality.

Three things are computed here:

  1. The 3-parameter fit (eps, cx, cy), reproducing E2 exactly as a check that
     this script is talking to the same data.
  2. The 1-parameter fit with the centre FORCED to the plane centre. If this
     fits essentially as well, the centre is not identified and (0, 0) is a
     legitimate choice rather than a lucky one.
  3. A bootstrap over ROIs, giving the centre's actual spread. A parameter whose
     bootstrap spread covers the whole sensor is not a measurement.

The decision rule is written here BEFORE the numbers are seen:

  * If the 1-parameter fit's residual rms is within 25% of the 3-parameter fit's,
    the centre is not identified -> ship (0, 0) and record the bound.
  * If it is worse by more than 2x, the centre is real -> ship the fitted centre.
  * In between, report as indeterminate and ship (0, 0) with an explicit caveat,
    because an unidentified parameter defaults to the physically principled
    value, not to the fitted one.
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump
from e2_lateral import gated

ROWS = json.load(open(os.path.join(OUT, "json", "e1_raw_edges.json")))["rows"]


def design(rows, with_centre):
    nx = np.array([r["normal"][0] for r in rows], float)
    ny = np.array([r["normal"][1] for r in rows], float)
    rx = np.array([r["rx"] for r in rows], float)
    ry = np.array([r["ry"] for r in rows], float)
    radial = rx * nx + ry * ny
    if with_centre:
        return np.column_stack([radial, -nx, -ny])
    return np.column_stack([radial])


def fit(rows, key, with_centre):
    d = np.array([r[key] for r in rows], float)
    A = design(rows, with_centre)
    coef, *_ = np.linalg.lstsq(A, d, rcond=None)
    pred = A @ coef
    ss_res = float(np.sum((d - pred) ** 2))
    ss_tot = float(np.sum((d - d.mean()) ** 2))
    out = {
        "n": len(rows),
        "params": A.shape[1],
        "eps_ppm": float(coef[0]) * 1e6,
        "r2": 1.0 - ss_res / max(ss_tot, 1e-12),
        "rms_resid": float(np.sqrt(ss_res / len(rows))),
        "cond": float(np.linalg.cond(A)),
    }
    if with_centre:
        eps = float(coef[0])
        out["centre"] = [float(coef[1] / eps), float(coef[2] / eps)]
    return out


def bootstrap_centre(rows, key, n_boot=2000, seed=1107):
    rng = np.random.default_rng(seed)
    cx, cy, eps = [], [], []
    idx = np.arange(len(rows))
    for _ in range(n_boot):
        pick = rng.choice(idx, size=len(rows), replace=True)
        sub = [rows[i] for i in pick]
        d = np.array([r[key] for r in sub], float)
        A = design(sub, True)
        try:
            coef, *_ = np.linalg.lstsq(A, d, rcond=None)
        except np.linalg.LinAlgError:
            continue
        e = float(coef[0])
        if abs(e) < 1e-9:
            continue
        eps.append(e * 1e6)
        cx.append(float(coef[1] / e))
        cy.append(float(coef[2] / e))
    q = lambda v, p: float(np.percentile(v, p))
    return {
        "n_boot": len(cx),
        "eps_ppm_ci95": [q(eps, 2.5), q(eps, 97.5)],
        "cx_ci95": [q(cx, 2.5), q(cx, 97.5)],
        "cy_ci95": [q(cy, 2.5), q(cy, 97.5)],
        "cx_median": q(cx, 50),
        "cy_median": q(cy, 50),
        # The fraction of bootstrap centres that land outside the sensor at all.
        # A centre that is off the sensor in a large fraction of resamples is
        # not a location, it is a numerical artefact.
        "frac_offsensor": float(
            np.mean((np.abs(cx) > 1758.0) | (np.abs(cy) > 1172.0))
        ),
    }


def main():
    keep, why = gated(ROWS)
    print(f"gated {len(keep)} of {len(ROWS)} ROIs  rejected={why}")

    res = {"n_gated": len(keep), "keys": {}}
    for key in ("dR", "dB", "null_dG"):
        three = fit(keep, key, True)
        one = fit(keep, key, False)
        ratio = one["rms_resid"] / max(three["rms_resid"], 1e-12)
        if ratio <= 1.25:
            verdict = "CENTRE NOT IDENTIFIED -- ship (0,0)"
        elif ratio > 2.0:
            verdict = "CENTRE REAL -- ship fitted centre"
        else:
            verdict = "INDETERMINATE -- ship (0,0) with caveat"
        boot = bootstrap_centre(keep, key)
        res["keys"][key] = {
            "three_param": three,
            "one_param": one,
            "rms_ratio_1p_over_3p": ratio,
            "verdict": verdict,
            "bootstrap": boot,
        }
        print(f"\n=== {key} ===")
        print(f"  3-param: eps={three['eps_ppm']:9.2f} ppm  R2={three['r2']:.4f}  "
              f"resid={three['rms_resid']:.4f}  cond={three['cond']:.3g}  "
              f"centre=({three['centre'][0]:.1f}, {three['centre'][1]:.1f})")
        print(f"  1-param: eps={one['eps_ppm']:9.2f} ppm  R2={one['r2']:.4f}  "
              f"resid={one['rms_resid']:.4f}")
        print(f"  resid ratio 1p/3p = {ratio:.4f}  -> {verdict}")
        print(f"  bootstrap centre cx 95% CI [{boot['cx_ci95'][0]:.0f}, "
              f"{boot['cx_ci95'][1]:.0f}]  cy 95% CI [{boot['cy_ci95'][0]:.0f}, "
              f"{boot['cy_ci95'][1]:.0f}]")
        print(f"  bootstrap eps 95% CI [{boot['eps_ppm_ci95'][0]:.1f}, "
              f"{boot['eps_ppm_ci95'][1]:.1f}] ppm   "
              f"frac centres off-sensor = {boot['frac_offsensor']:.3f}")

    dump("e9_centre", res)


if __name__ == "__main__":
    main()
