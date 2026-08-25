"""M121 -- the single scan routine every arm and every control goes through.

`scan()` is the whole of E2.  N1 (single unmerged frame), N2 (soft background
edge) and N3 (planted halo) call THIS function, not a variant of it, so a
control cannot pass by exercising different code from the treatment.
"""

from __future__ import annotations

import numpy as np

from halo_lib import (
    BANDS, DMAX, NEAR, PLATEAU, band_mean, edge_seeds, gradient, measure_edge,
    outer_cutoff, overshoot_curves, peak_in_near, settle_distance, width_at_frac,
)


def _boot_ci(values: np.ndarray, reps: int = 2000, seed: int = 11) -> tuple[float, float, float]:
    """Median of a per-edge statistic, with a bootstrap 95% interval and SE.

    Rule 39: a separation quoted without the spread it is measured against is
    not a number.
    """
    v = values[np.isfinite(values)]
    if v.size < 3:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(reps, v.size))
    meds = np.median(v[idx], axis=1)
    return float(np.median(v)), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def scan(img: np.ndarray, *, label: str, grad_percentile: float = 99.0,
         stride: int = 1, max_edges: int = 4000, seed: int = 20260824,
         isolation_frac: float = 0.35, min_amplitude: float = 0.0,
         flat_tol: float = 0.10, roi_mask: np.ndarray | None = None,
         classify=None, smooth: int = 2, verbose: bool = True,
         edges: np.ndarray | None = None, collect_edges: bool = False,
         max_rise: float | None = None, min_rise: float | None = None,
         extra=None, sat_level: float | None = None):
    """Scan one image for step edges and return the pooled overshoot curves.

    `isolation_frac`: a side is rejected when the profile on that side contains
    another gradient peak comparable to the edge's own -- measured on the
    profile itself, so it needs no second detector.
    `classify`: optional callable `f(e) -> +1 | -1 | 0`, where +1 means the
    BRIGHT side of this edge is the object.
    `edges`: optional (N, 4) array of `(y, x, gx, gy)` to measure instead of
    detecting.  This is how a reference image is scored AT THE MERGED ARM'S OWN
    EDGES -- same pixels, same normals, same acceptance code -- so a
    merged-minus-reference difference is not comparing two different edge sets.
    `collect_edges`: also return the accepted `(y, x, gx, gy)` list.
    """
    rng = np.random.default_rng(seed)
    border = int(DMAX) + 8
    gx, gy, mag = gradient(img, smooth=smooth)
    if edges is not None:
        seeds = edges
    else:
        s = edge_seeds(mag, grad_percentile, border, stride, rng)
        if roi_mask is not None:
            s = s[roi_mask[s[:, 0], s[:, 1]]]
        if s.shape[0] > max_edges:
            s = s[:max_edges]
        seeds = np.stack([s[:, 0], s[:, 1],
                          gx[s[:, 0], s[:, 1]], gy[s[:, 0], s[:, 1]]], axis=1).astype(np.float64)

    dist = None
    acc = {"bright": [], "dark": [], "S": [], "C": []}
    meta = []
    meta_side = {"bright": [], "dark": []}
    settles = []
    rises = []
    kept_edges = []
    n_seen = 0
    for row in seeds:
        y, x, egx, egy = float(row[0]), float(row[1]), float(row[2]), float(row[3])
        e = measure_edge(img, y, x, egx, egy, flat_tol=flat_tol)
        if e is None:
            continue
        if e["A"] < min_amplitude:
            continue
        # CLIPPING.  A plateau sitting on the sensor ceiling is not a plateau:
        # `hi` is wherever the clip is, `A` is wrong, and every normalised
        # statistic divided by it is wrong with it.  Found on tweezers-cpl,
        # whose bright metal reaches the 16-bit ceiling and drove one class to
        # read +1.47 -- twenty times the edge amplitude, which is nonsense.
        if sat_level is not None and (e["hi"] >= sat_level or e["lo"] >= sat_level):
            continue
        if sat_level is not None:
            seg = e["p"]
            if float(np.mean(seg >= sat_level)) > 0.02:
                continue
        n_seen += 1
        dd, br, dk, S, C = overshoot_curves(e)
        if dist is None:
            dist = dd
        if not (max_rise is None or (np.isfinite(e["rise"]) and e["rise"] <= max_rise)):
            continue
        if not (min_rise is None or (np.isfinite(e["rise"]) and e["rise"] >= min_rise)):
            continue
        # isolation: the profile's own derivative must not carry another step of
        # comparable size out in the plateau region.
        dp = np.abs(np.diff(e["p"])) / e["A"]
        d_mid = 0.5 * (e["d"][1:] + e["d"][:-1])
        far_hi = dp[(d_mid > NEAR[1]) & (d_mid <= PLATEAU[1])].max(initial=0.0)
        far_lo = dp[(d_mid < -NEAR[1]) & (d_mid >= -PLATEAU[1])].max(initial=0.0)
        step = float(np.abs(np.diff(e["p"])).max()) / e["A"]

        ok_hi = e["flat_hi"] and far_hi < isolation_frac * step
        ok_lo = e["flat_lo"] and far_lo < isolation_frac * step
        obj = 0
        if classify is not None:
            obj = int(classify(e))   # +1 bright side is object, -1 dark side
        xtra = float(extra(e)) if extra is not None else np.nan

        # S and C mix the two sides, so BOTH sides must be clean to use them.
        # The per-side statistics need only their own side, and on a real
        # subject that matters enormously: for a dark object on a bright
        # surround the SURROUND is flat and passes while the OBJECT side is
        # textured and fails, so requiring pairs throws away most of exactly
        # the edges the rim lives at.
        if ok_hi or ok_lo:
            rises.append(e["rise"])
        if ok_hi:
            acc["bright"].append(br)
            meta_side["bright"].append((e["A"], e["y"], e["x"], obj, e["lo"], e["hi"], xtra))
        if ok_lo:
            acc["dark"].append(dk)
            meta_side["dark"].append((e["A"], e["y"], e["x"], obj, e["lo"], e["hi"], xtra))
        if ok_hi and ok_lo:
            acc["S"].append(S)
            acc["C"].append(C)
            settles.append(settle_distance(e))
            meta.append((e["A"], e["y"], e["x"], obj, e["lo"], e["hi"], xtra))
            if collect_edges:
                kept_edges.append((y, x, egx, egy))

    out = {"label": label, "seeds": int(seeds.shape[0]), "edges_measured": n_seen,
           "n_bright": len(acc["bright"]), "n_dark": len(acc["dark"]),
           "n_pair": len(acc["S"]), "dist": dist,
           "settle_median": float(np.median(settles)) if settles else np.nan,
           "settle_p90": float(np.percentile(settles, 90)) if settles else np.nan,
           "rise_median": float(np.nanmedian(rises)) if rises else np.nan,
           "rise_p90": float(np.nanpercentile(rises, 90)) if rises else np.nan,
           "amplitudes": np.array([m[0] for m in meta]),
           "obj": np.array([m[3] for m in meta], dtype=int),
           "ys": np.array([m[1] for m in meta]), "xs": np.array([m[2] for m in meta]),
           "kept_edges": np.array(kept_edges, dtype=np.float64) if collect_edges
                         else np.zeros((0, 4)),
           "S_stack": np.stack(acc["S"]) if acc["S"] else None,
           "C_stack": np.stack(acc["C"]) if acc["C"] else None}

    # The edge TRANSITION contaminates `bright`, `dark` and `C` alike: inside
    # it the profile has reached neither plateau, so all three read strongly
    # negative on a perfectly artifact-free edge.  All three are read beyond
    # it.  The exclusion is set by the 10-90% rise, not by `settle_distance`,
    # because a smooth rim keeps the slope non-zero and would exclude itself.
    # A Gaussian edge is >99% settled by 1.6x its 10-90 rise.  `S` is
    # transition-immune by construction and is read from NEAR[0].
    r90 = out["rise_p90"]
    c0 = max(NEAR[0], 1.6 * r90) if np.isfinite(r90) else 4.0
    out["C_d0"] = c0
    d0 = {"bright": c0, "dark": c0, "S": NEAR[0], "C": c0}
    for key in ("bright", "dark", "S", "C"):
        if not acc[key]:
            out[key] = None
            continue
        M = np.stack(acc[key])
        med = np.median(M, axis=0)
        start = d0[key]
        pk, at = peak_in_near(dist, med, near=(start, NEAR[1]))
        w50 = width_at_frac(dist, med, pk, 0.50, d0=start)
        # The per-edge statistic is the signed mean over the rim's own
        # half-maximum support, [d0, w50], taken from the POOLED curve.  A
        # per-edge argmax|.| would be an argmax statistic and rule 4 bans those
        # in analysis scripts too; and a fixed window straddling the rim's
        # outer cutoff dilutes the amplitude by whatever fraction of the window
        # sits outside the rim -- which is exactly how the first version of
        # this band under-read the 13 px plant by 35%.
        pb_lo = start
        pb_hi = max(start + 2.0, w50 if np.isfinite(w50) else start + 8.0)
        per_edge = np.array([band_mean(dist, c, pb_lo, pb_hi) for c in M])
        b_med, b_lo, b_hi = _boot_ci(per_edge)
        out[key] = {
            "median_curve": med,
            "mean_curve": M.mean(axis=0),
            "n": M.shape[0],
            "d0": start,
            "peak": pk, "peak_at": at,
            "w50": w50,
            "w10": width_at_frac(dist, med, pk, 0.10, d0=start),
            "cutoff": outer_cutoff(dist, med, pk, start, 0.10),
            "bands": {f"{a:g}-{b:g}": band_mean(dist, med, a, b) for a, b in BANDS},
            "boot_band": (pb_lo, pb_hi),
            "boot_median": b_med, "boot_lo95": b_lo, "boot_hi95": b_hi,
            "frac_positive": float(np.mean(per_edge > 0)),
            "per_edge_band": per_edge,
            "obj": (np.array([m[3] for m in meta_side[key]], dtype=int)
                    if key in meta_side else np.array([m[3] for m in meta], dtype=int)),
            "amps": (np.array([m[0] for m in meta_side[key]])
                     if key in meta_side else np.array([m[0] for m in meta])),
            "lo": (np.array([m[4] for m in meta_side[key]])
                   if key in meta_side else np.array([m[4] for m in meta])),
            "hi": (np.array([m[5] for m in meta_side[key]])
                   if key in meta_side else np.array([m[5] for m in meta])),
            "dz": (np.array([m[6] for m in meta_side[key]])
                   if key in meta_side else np.array([m[6] for m in meta])),
            "stack": M,
        }
    if verbose:
        print(f"[{label}] seeds={out['seeds']} measured={n_seen} "
              f"bright={out['n_bright']} dark={out['n_dark']} pair={out['n_pair']} "
              f"rise med={out['rise_median']:.2f} p90={out['rise_p90']:.2f} px "
              f"-> C read from d>={out['C_d0']:.2f}")
        for key in ("bright", "dark", "S", "C"):
            s = out[key]
            if s is None:
                print(f"    {key}: no usable sides")
                continue
            bb = "  ".join(f"{k}:{v:+.4f}" for k, v in s["bands"].items())
            print(f"    {key:6s}: ext={s['peak']:+.5f} at d={s['peak_at']:.2f}  "
                  f"w50={s['w50']:.2f} w10={s['w10']:.2f} cut={s['cutoff']:.2f}  n={s['n']}")
            print(f"            boot {s['boot_median']:+.5f} "
                  f"[{s['boot_lo95']:+.5f},{s['boot_hi95']:+.5f}] over d "
                  f"{s['boot_band'][0]:.1f}-{s['boot_band'][1]:.1f}, "
                  f"{100*s['frac_positive']:.0f}% edges +ve")
            print(f"            bands {bb}")
    return out


def sign_table(res: dict, thresh: float = 0.004, rel: float = 0.25) -> str:
    """The one-line verdict, read off the ADDITIVE/CONTRAST decomposition.

    `S` (additive: both sides lifted) is transition-immune, so it decides
    first.  `C` (contrast: both sides pushed outward) is read beyond the
    transition exclusion.  A component counts as PRESENT only if it clears both
    an absolute floor `thresh` (a dimensionless fraction of the edge amplitude;
    the N3 null plant fixes what "zero" looks like) AND a relative floor `rel`
    against the larger component -- otherwise the few-per-cent crosstalk that
    N3 measures would be reported as a genuine mixture.
    """
    S = res["S"]["boot_median"] if res.get("S") else np.nan
    C = res["C"]["boot_median"] if res.get("C") else np.nan
    if not (np.isfinite(S) and np.isfinite(C)):
        return "INDETERMINATE"
    big = max(abs(S), abs(C))
    s_on = abs(S) > thresh and abs(S) >= rel * big
    c_on = abs(C) > thresh and abs(C) >= rel * big
    if not s_on and not c_on:
        return "NULL (no rim)"
    if c_on and not s_on:
        return ("CONTRAST-ENHANCING (both sides pushed outward)" if C > 0
                else "CONTRAST-REDUCING (both sides pulled inward)")
    if s_on and not c_on:
        return ("ADDITIVE-BRIGHT (both sides lifted)" if S > 0
                else "ADDITIVE-DARK (both sides lowered)")
    dom = "ADDITIVE" if abs(S) > abs(C) else "CONTRAST"
    sgn_s = "BRIGHT" if S > 0 else "DARK"
    sgn_c = "ENHANCING" if C > 0 else "REDUCING"
    return f"MIXED ({dom}-dominant; additive {sgn_s} S={S:+.4f}, contrast {sgn_c} C={C:+.4f})"
