"""E2 -- hypothesis (a), lateral chromatic aberration, from the E1 edge fits.

Two things happen here.

1. THE DECLARED FIT-QUALITY GATE is applied.  It was written down in
   PRE-REGISTRATION.md before E1 was analysed and it is applied unchanged:

        every plane   w_abs in [0.4, 8.0] sensel
        every plane   rms/amp <= 0.12
        |null_dG|     <= 0.10 sensel      <- the principled one: an ROI where
                                             the two GREENS disagree has not
                                             been measured, whatever it says
                                             about red and blue
        |dR|,|dB|     <= 8.0 sensel       (fit blow-up guard)

   The ungated E1 medians are reported alongside so the gate's effect is visible
   rather than hidden.

2. THE RADIAL MODEL IS FITTED.  Lateral CA is a per-channel magnification
   error: channel c is displaced from green by eps_c * (r - r0), where r is
   sensel position and r0 the optical centre.  An ESF measures only the
   component along the edge normal n, so the prediction for ROI i is

        d_i = eps_c * ((r_i - r0) . n_i)

   which is linear in (eps, eps*cx, eps*cy):

        d = eps*(rx*nx + ry*ny)  -  (eps*cx)*nx  -  (eps*cy)*ny

   Three free parameters against however many gated ROIs survive.  This uses
   each edge's OWN normal, so it does not require comparable edges at matched
   radii the way a binned radius sweep does -- an edge whose normal is
   tangential simply contributes a small predictor and cannot masquerade as
   signal.

   FALSIFICATION.  A radial model that fits no better than chance is not
   evidence of lateral CA, so the fit is compared against a permutation null
   in which the normals are shuffled between ROIs, destroying the geometric
   pairing while preserving both marginal distributions.  Bar: the real R^2
   must exceed the 95th percentile of 2000 permutations.
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump

GATE = dict(w_lo=0.4, w_hi=8.0, rms_amp=0.12, null_dG=0.10, d_max=8.0)


def gated(rows):
    keep, why = [], {"w": 0, "rmsamp": 0, "null": 0, "blowup": 0}
    for r in rows:
        w = r["w_abs"]
        if any(not (GATE["w_lo"] <= abs(w[c]) <= GATE["w_hi"]) for c in w):
            why["w"] += 1; continue
        if any(r["rms"][c] / max(abs(r["amp"][c]), 1e-9) > GATE["rms_amp"] for c in r["rms"]):
            why["rmsamp"] += 1; continue
        if abs(r["null_dG"]) > GATE["null_dG"]:
            why["null"] += 1; continue
        if abs(r["dR"]) > GATE["d_max"] or abs(r["dB"]) > GATE["d_max"]:
            why["blowup"] += 1; continue
        keep.append(r)
    return keep, why


def fit_radial(rows, key):
    d = np.array([r[key] for r in rows], float)
    nx = np.array([r["normal"][0] for r in rows], float)
    ny = np.array([r["normal"][1] for r in rows], float)
    rx = np.array([r["rx"] for r in rows], float)
    ry = np.array([r["ry"] for r in rows], float)
    A = np.column_stack([rx * nx + ry * ny, -nx, -ny])
    coef, *_ = np.linalg.lstsq(A, d, rcond=None)
    pred = A @ coef
    ss_res = float(np.sum((d - pred) ** 2))
    ss_tot = float(np.sum((d - d.mean()) ** 2))
    r2 = 1.0 - ss_res / max(ss_tot, 1e-12)
    eps = float(coef[0])
    cx = float(coef[1] / eps) if abs(eps) > 1e-12 else float("nan")
    cy = float(coef[2] / eps) if abs(eps) > 1e-12 else float("nan")

    rng = np.random.default_rng(107)
    null = []
    for _ in range(2000):
        p = rng.permutation(len(rows))
        Ap = np.column_stack([rx * nx[p] + ry * ny[p], -nx[p], -ny[p]])
        c2, *_ = np.linalg.lstsq(Ap, d, rcond=None)
        pr = Ap @ c2
        null.append(1.0 - np.sum((d - pr) ** 2) / max(ss_tot, 1e-12))
    null = np.array(null)
    p95 = float(np.percentile(null, 95))
    pval = float(np.mean(null >= r2))
    return {"key": key, "n": len(rows), "eps": eps, "eps_ppm": eps * 1e6,
            "centre_sensel": [cx, cy], "r2": r2,
            "perm_null_p95_r2": p95, "perm_p_value": pval,
            "beats_perm_null": bool(r2 > p95), "rms_resid_sensel":
            float(np.sqrt(ss_res / len(rows)))}


def b2_as_registered(rows):
    """B2 exactly as pre-registered, before the upgrade.

    Registered form: the RADIAL component of (d0_R - d0_B) is linear in radius,
    R^2 >= 0.5, |intercept| < 0.15 sensel, corner extrapolation >= 0.30 sensel.
    Reported alongside the per-normal fit because the analysis I actually ran is
    not the one I registered, and a bar is only a bar if it is scored as written.
    """
    r = np.array([x["radius"] for x in rows], float)
    sgn = np.sign([np.dot(np.array(x["normal"]), np.array([x["rx"], x["ry"]]))
                   for x in rows])
    d = (np.array([x["dR"] for x in rows]) -
         np.array([x["dB"] for x in rows])) * sgn
    A = np.column_stack([r, np.ones_like(r)])
    (m, c), *_ = np.linalg.lstsq(A, d, rcond=None)
    pred = A @ (np.array([m, c]))
    ss_tot = float(np.sum((d - d.mean()) ** 2))
    r2 = 1.0 - float(np.sum((d - pred) ** 2)) / max(ss_tot, 1e-12)
    rmax = float(r.max())
    inner = np.abs(d[r < 0.35 * rmax]); outer = np.abs(d[r > 0.75 * rmax])
    return {"slope_per_sensel": float(m), "intercept_sensel": float(c),
            "r2": r2, "corner_extrap_sensel": float(m * rmax + c),
            "mean_abs_inner": float(inner.mean()) if inner.size else None,
            "mean_abs_outer": float(outer.mean()) if outer.size else None,
            "inner_over_outer": (float(inner.mean() / outer.mean())
                                 if inner.size and outer.size else None),
            "n_inner": int(inner.size), "n_outer": int(outer.size),
            "confirmed": bool(r2 >= 0.5 and abs(c) < 0.15
                              and abs(m * rmax + c) >= 0.30)}


if __name__ == "__main__":
    src = json.load(open(os.path.join(OUT, "json", "e1_raw_edges.json")))
    rows = src["rows"]
    out = {"gate": GATE, "per_stack": {}, "radial": {}}
    print(f"E1 rows total: {len(rows)}")
    keep, why = gated(rows)
    print(f"gated: {len(keep)} kept, {len(rows)-len(keep)} rejected "
          f"(width {why['w']}, rms/amp {why['rmsamp']}, "
          f"green-null {why['null']}, blow-up {why['blowup']})")

    for lbl, sel in (("ALL-ungated", rows), ("ALL-gated", keep)):
        if not sel:
            continue
        a = {k: np.array([r[k] for r in sel], float)
             for k in ("dR", "dB", "null_dG", "cos_radial", "radius")}
        rec = {"n": len(sel),
               "median_absdR": float(np.median(np.abs(a["dR"]))),
               "median_absdB": float(np.median(np.abs(a["dB"]))),
               "median_absnull": float(np.median(np.abs(a["null_dG"])))}
        out["per_stack"][lbl] = rec
        print(f"  {lbl:12s} n={rec['n']:3d}  |dR| {rec['median_absdR']:.4f}  "
              f"|dB| {rec['median_absdB']:.4f}  |NULL| {rec['median_absnull']:.4f} sensel")

    for st in sorted({r["stack"] for r in keep}):
        sel = [r for r in keep if r["stack"] == st]
        a = {k: np.array([r[k] for r in sel], float) for k in ("dR", "dB", "null_dG")}
        rec = {"n": len(sel),
               "median_absdR": float(np.median(np.abs(a["dR"]))),
               "median_absdB": float(np.median(np.abs(a["dB"]))),
               "median_absnull": float(np.median(np.abs(a["null_dG"])))}
        out["per_stack"][st] = rec
        print(f"  {st:16s} n={rec['n']:3d}  |dR| {rec['median_absdR']:.4f}  "
              f"|dB| {rec['median_absdB']:.4f}  |NULL| {rec['median_absnull']:.4f} sensel")

    print("\nradial model  d = eps * ((r - r0) . n)")
    for key in ("dR", "dB", "null_dG"):
        if len(keep) < 6:
            print(f"  {key}: only {len(keep)} gated ROIs, refusing to fit 3 parameters")
            break
        f = fit_radial(keep, key)
        out["radial"][key] = f
        tag = "NULL" if key == "null_dG" else "signal"
        print(f"  {key:8s} ({tag:6s}) eps = {f['eps_ppm']:+9.1f} ppm   "
              f"R2 = {f['r2']:+.4f}   perm-null p95 R2 = {f['perm_null_p95_r2']:+.4f}   "
              f"p = {f['perm_p_value']:.4f}  "
              f"{'BEATS NULL' if f['beats_perm_null'] else 'does not beat null'}")
        print(f"           implied optical centre {f['centre_sensel'][0]:+.0f}, "
              f"{f['centre_sensel'][1]:+.0f} sensel from frame centre; "
              f"residual rms {f['rms_resid_sensel']:.3f} sensel")

    b2 = b2_as_registered(keep)
    out["b2_as_registered"] = b2
    print("\nB2 exactly as pre-registered: radial (d0_R - d0_B) vs radius")
    print(f"  slope {b2['slope_per_sensel']*1e6:+.1f} ppm   "
          f"intercept {b2['intercept_sensel']:+.4f} sensel   R2 {b2['r2']:+.4f}")
    print(f"  corner extrapolation {b2['corner_extrap_sensel']:+.4f} sensel")
    print(f"  mean|d| inner (r<0.35rmax, n={b2['n_inner']}) "
          f"{b2['mean_abs_inner']}, outer (r>0.75rmax, n={b2['n_outer']}) "
          f"{b2['mean_abs_outer']}, ratio {b2['inner_over_outer']}")
    print(f"  registered CONFIRMED clause: {b2['confirmed']}")
    dump("e2_lateral", out)
