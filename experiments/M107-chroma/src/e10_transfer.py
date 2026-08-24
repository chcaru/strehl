"""E10 -- what the "centre offset" actually is, and does the profile transfer?

Two questions, one script, because they share the same rows.

## 1. The centre term is degenerate with a uniform channel translation

E9 found the fitted centre is REAL for red -- forcing it to the plane centre costs
5.37x in residual rms and biases eps by 14%. But before shipping a 1077 px
decentring as a *lens* property, note what those two parameters actually are.

The model is

    d = eps * ((r - c) . n) = eps*(r.n)  -  (eps*c) . n

The second term is a CONSTANT VECTOR projected on each edge normal. That is
exactly a uniform translation of the channel. So "the optical centre is at c" and
"red is translated by -eps*c relative to green" are the SAME TWO PARAMETERS, not
two competing hypotheses that this parameterisation could ever separate.

That matters because there is a known, non-optical source of a uniform red-green
translation on this instrument: **CFA co-siting**. Red sits at quad corner (0,0)
and the two greens at (1,0) and (0,1), so a green built from both sits half a
quad away from red in each axis. The expected co-siting translation is therefore
of order 0.5 plane px per axis.

So this computes the implied translation and compares its MAGNITUDE against that
0.5 px expectation. If it lands near 0.5 px per axis, a large part of what the
3-parameter fit calls "optical centre" is lattice, not lens, and shipping it as
an optical profile would be shipping a co-siting error as a lens property.

I cannot separate them with this parameterisation -- that is a statement about
the model, not about effort -- and the report says so.

## 2. Bar L4: does the profile transfer out of sample?

Fit on one stack, apply to the other, and measure the residual on the held-out
stack. This is the arm that can kill the profile idea, and it needs no re-render:
the residual of a model applied to held-out rows IS the corrected displacement.

The `null_dG` channel is carried through every arm as a control. Correcting a
null must not improve it, because there is nothing there to correct.
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump
from e2_lateral import gated

ROWS = json.load(open(os.path.join(OUT, "json", "e1_raw_edges.json")))["rows"]

# Plane geometry, from the render logs: 3516 x 2344 per CFA plane.
PLANE_W, PLANE_H = 3516.0, 2344.0
HALF_DIAG = float(np.hypot(PLANE_W, PLANE_H) / 2.0)


def parts(rows):
    return (
        np.array([r["normal"][0] for r in rows], float),
        np.array([r["normal"][1] for r in rows], float),
        np.array([r["rx"] for r in rows], float),
        np.array([r["ry"] for r in rows], float),
    )


def fit3(rows, key):
    """eps, and the constant translation, from the 3-parameter model."""
    nx, ny, rx, ry = parts(rows)
    d = np.array([r[key] for r in rows], float)
    A = np.column_stack([rx * nx + ry * ny, -nx, -ny])
    coef, *_ = np.linalg.lstsq(A, d, rcond=None)
    eps = float(coef[0])
    # d = eps*(r.n) - (eps*c).n , so the constant displacement vector is -eps*c,
    # which the fit stores as (coef[1], coef[2]) already multiplied by -1 in A.
    tx, ty = -float(coef[1]), -float(coef[2])
    return {"eps": eps, "tx": tx, "ty": ty,
            "centre": [float(coef[1] / eps), float(coef[2] / eps)] if abs(eps) > 1e-12 else None}


def predict(model, rows):
    nx, ny, rx, ry = parts(rows)
    return model["eps"] * (rx * nx + ry * ny) + model["tx"] * nx + model["ty"] * ny


def med_abs(v):
    return float(np.median(np.abs(np.asarray(v, float))))


def main():
    keep, _ = gated(ROWS)
    by_stack = {}
    for r in keep:
        by_stack.setdefault(r["stack"], []).append(r)
    stacks = sorted(by_stack)
    print(f"gated {len(keep)} ROIs across {stacks}")

    out = {"n_gated": len(keep), "stacks": {k: len(v) for k, v in by_stack.items()}}

    # ---- 1. the degeneracy readout -------------------------------------
    m = fit3(keep, "dR")
    trans_mag = float(np.hypot(m["tx"], m["ty"]))
    out["degeneracy"] = {
        "eps_ppm": m["eps"] * 1e6,
        "implied_translation_planepx": [m["tx"], m["ty"]],
        "implied_translation_magnitude": trans_mag,
        "cfa_cositing_expectation_per_axis": 0.5,
        "centre_planepx": m["centre"],
        "centre_distance_planepx": float(np.hypot(*m["centre"])),
        "half_diagonal_planepx": HALF_DIAG,
    }
    print("\n=== centre/translation degeneracy (dR) ===")
    print(f"  eps            = {m['eps']*1e6:.2f} ppm")
    print(f"  implied uniform translation = ({m['tx']:+.4f}, {m['ty']:+.4f}) plane px"
          f"   |t| = {trans_mag:.4f}")
    print(f"  CFA co-siting expectation   = ~0.5 plane px per axis")
    print(f"  equivalent centre           = ({m['centre'][0]:.1f}, {m['centre'][1]:.1f}), "
          f"{np.hypot(*m['centre']):.0f} px from plane centre "
          f"({100*np.hypot(*m['centre'])/HALF_DIAG:.0f}% of half-diagonal)")

    # ---- 2. L4 transfer -------------------------------------------------
    out["transfer"] = {}
    print("\n=== L4 out-of-sample transfer ===")
    for key in ("dR", "null_dG"):
        out["transfer"][key] = {}
        for a in stacks:
            for b in stacks:
                if a == b:
                    continue
                rows_a, rows_b = by_stack[a], by_stack[b]
                if len(rows_a) < 4 or len(rows_b) < 4:
                    continue
                model_a = fit3(rows_a, key)
                model_b = fit3(rows_b, key)

                d_b = np.array([r[key] for r in rows_b], float)
                base = med_abs(d_b)
                resid_oos = med_abs(d_b - predict(model_a, rows_b))
                resid_ins = med_abs(d_b - predict(model_b, rows_b))

                red_oos = 1.0 - resid_oos / max(base, 1e-12)
                red_ins = 1.0 - resid_ins / max(base, 1e-12)
                frac = red_oos / red_ins if red_ins > 1e-9 else float("nan")

                rec = {
                    "fit_on": a, "applied_to": b,
                    "n_fit": len(rows_a), "n_applied": len(rows_b),
                    "eps_fit_ppm": model_a["eps"] * 1e6,
                    "eps_target_ppm": model_b["eps"] * 1e6,
                    "median_abs_uncorrected": base,
                    "median_abs_after_oos": resid_oos,
                    "median_abs_after_insample": resid_ins,
                    "reduction_oos": red_oos,
                    "reduction_insample": red_ins,
                    "frac_of_insample": frac,
                }
                out["transfer"][key][f"{a}->{b}"] = rec
                print(f"  [{key:8s}] fit {a:13s} -> apply {b:13s} "
                      f"| uncorr {base:.4f} -> oos {resid_oos:.4f} "
                      f"({100*red_oos:5.1f}% removed) ; in-sample {resid_ins:.4f} "
                      f"({100*red_ins:5.1f}%) ; frac {frac:.3f}")

    # ---- 3. L3 in-sample, all stacks pooled -----------------------------
    print("\n=== L3 in-sample (pooled) ===")
    out["insample"] = {}
    for key in ("dR", "null_dG"):
        mk = fit3(keep, key)
        d = np.array([r[key] for r in keep], float)
        base = med_abs(d)
        after = med_abs(d - predict(mk, keep))
        out["insample"][key] = {
            "median_abs_uncorrected": base,
            "median_abs_corrected": after,
            "reduction": 1.0 - after / max(base, 1e-12),
        }
        print(f"  [{key:8s}] {base:.4f} -> {after:.4f} "
              f"({100*(1-after/max(base,1e-12)):.1f}% removed)")

    dump("e10_transfer", out)


if __name__ == "__main__":
    main()
