"""M73 step 03 — score the cylinder invariant against the criteria in
`experiments/M73-cylinder/PREREGISTRATION.md`, committed at 700f87b.

Nothing here chooses a threshold. Every number this file compares against was
fixed before the dumps existed. The file is deliberately verbose about which
registered clause each block implements, because a scoring layer that drifts
toward the answer is the failure mode this milestone was created to avoid.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"

MARGIN = 22  # SUPPORT_RADIUS + REGULARISER_RADIUS, from the dump header
SEED = 0x5CA1AB1E

# --- registered thresholds, quoted from the pre-registration ----------------
M67_E = 0.71747  # M67 section 6: mean |win - k*| for the estimating merge
M67_A = 0.81473  # M67 section 6: mean |win - k*| for ArgmaxBaseline
M67_RATIO = M67_E / M67_A  # 0.88063
T2_LO, T2_HI = 0.761, 0.940  # tightening within [0.5x, 2x] of 11.94%
C1_MIN = 3.0  # S_swap / S must exceed this
C2_MIN = 10.0  # S_perm / S must exceed this
C3_MULT = 3.0  # A_P over its incommensurate null
H_AX_PASS, H_AX_FAIL = 0.95, 0.80
H_MARGIN_PP = 10.0  # percentage points over the shape-matched null
MASK_MIN = 0.20  # scored mask as a fraction of the plane


def load(prefix: pathlib.Path) -> dict:
    hdr = json.loads((prefix.with_suffix(".json")).read_text(encoding="utf-8"))
    w, h = hdr["width"], hdr["height"]

    def rd(name: str, dt) -> np.ndarray:
        return np.fromfile(prefix.with_suffix(f".{name}.bin"), dtype=dt).reshape(h, w)

    hdr["win_E"] = rd("win_E", np.uint16).astype(np.float64)
    hdr["win_A"] = rd("win_A", np.uint16).astype(np.float64)
    hdr["lo_E"] = rd("lo_E", np.uint16).astype(np.float64)
    hdr["hi_E"] = rd("hi_E", np.uint16).astype(np.float64)
    hdr["n_E"] = rd("nadm_E", np.uint16).astype(np.float64)
    hdr["lo_A"] = rd("lo_A", np.uint16).astype(np.float64)
    hdr["hi_A"] = rd("hi_A", np.uint16).astype(np.float64)
    hdr["n_A"] = rd("nadm_A", np.uint16).astype(np.float64)
    hdr["luma"] = rd("meanluma", np.float32).astype(np.float64)
    return hdr


def column_line_fit(field: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """Per-column OLS fit `a(x) + b(x) * y`, evaluated at every scored row.

    `rows` is the 1-D array of row indices in the scored band. Returns an array
    the same shape as `field[rows]`.
    """
    y = rows.astype(np.float64)
    yc = y - y.mean()
    syy = float(np.dot(yc, yc))
    v = field[rows]  # (nrows, ncols)
    a = v.mean(axis=0)
    b = (yc[:, None] * v).sum(axis=0) / syy
    return a[None, :] + b[None, :] * yc[:, None]


def row_line_fit(field: np.ndarray, cols: np.ndarray) -> np.ndarray:
    """C1's axis swap: the same fit with `x` and `y` exchanged."""
    x = cols.astype(np.float64)
    xc = x - x.mean()
    sxx = float(np.dot(xc, xc))
    v = field[:, cols]  # (nrows, ncols)
    a = v.mean(axis=1)
    b = (xc[None, :] * v).sum(axis=1) / sxx
    return a[:, None] + b[:, None] * xc[None, :]


def stats(r: np.ndarray) -> dict:
    ar = np.abs(r)
    return {
        "mean_abs": float(ar.mean()),
        "rms": float(np.sqrt((r * r).mean())),
        "median_abs": float(np.median(ar)),
        "p99_abs": float(np.percentile(ar, 99)),
    }


def phase_profile(r: np.ndarray, rows: np.ndarray, pitch: float, nbin: int = 24) -> np.ndarray:
    """Signed residual averaged by phase modulo `pitch` along `y`."""
    ph = np.mod(rows.astype(np.float64), pitch) / pitch
    b = np.minimum((ph * nbin).astype(np.int64), nbin - 1)
    prof = np.zeros(nbin)
    cnt = np.zeros(nbin)
    rowmean = r.mean(axis=1)
    for i, bi in enumerate(b):
        prof[bi] += rowmean[i]
        cnt[bi] += 1.0
    return prof / np.maximum(cnt, 1.0)


def score(prefix: pathlib.Path, pitch: float, label: str) -> dict:
    d = load(prefix)
    h, w, k = d["height"], d["width"], d["frames"]
    rows = np.arange(MARGIN, h - MARGIN)
    cols = np.arange(MARGIN, w - MARGIN)
    sub = np.ix_(rows, cols)
    print(f"\n{'=' * 78}\n{label}: {k} frames, plane {w} x {h}\n{'=' * 78}")
    print(f"mean n_eff  E {d['mean_n_eff_E']:.5f}   A' {d['mean_n_eff_A']:.5f}   of {k} frames")
    print(f"win_E != win_A : {100.0 * d['win_disagree_frac']:.4f}% of the plane")

    win_e = d["win_E"]
    win_a = d["win_A"]
    res: dict = {"frames": k, "plane": [w, h]}

    # ---- masks (registered 4.3) -------------------------------------------
    interior = np.ones((len(rows), len(cols)), dtype=bool)
    boundary = (win_e[sub] == 0) | (win_e[sub] == k - 1)
    col_boundary_frac = boundary.mean(axis=0)
    keep_cols = col_boundary_frac <= 0.20
    print(
        f"scored mask    : interior {interior.mean() * interior.size / (w * h):.3f} of the plane; "
        f"boundary-winner pixels {boundary.mean() * 100:.3f}%; "
        f"columns dropped by the secondary mask {100.0 * (~keep_cols).mean():.2f}%"
    )
    res["boundary_winner_frac"] = float(boundary.mean())
    res["secondary_cols_dropped_frac"] = float((~keep_cols).mean())
    res["scored_frac_of_plane"] = float(interior.size / (w * h))

    # ---- references (registered 4.2): two, each with its bias declared -----
    fit_e = column_line_fit(win_e[:, cols], rows)
    fit_a = column_line_fit(win_a[:, cols], rows)

    slopes = {}
    for nm, ref in (("E", fit_e), ("A", fit_a)):
        b = (ref[-1] - ref[0]) / (rows[-1] - rows[0])
        slopes[nm] = {
            "median_slope_frames_per_px": float(np.median(b)),
            "p95_abs_slope": float(np.percentile(np.abs(b), 95)),
        }
    print(
        f"column slopes  : ref E median {slopes['E']['median_slope_frames_per_px']:+.3e} "
        f"frames/px, p95 |b| {slopes['E']['p95_abs_slope']:.3e}"
    )
    res["column_slopes"] = slopes

    ve = win_e[sub]
    va = win_a[sub]
    out_masks = {"primary": interior, "secondary": np.broadcast_to(keep_cols, interior.shape)}

    res["arms"] = {}
    for mname, m in out_masks.items():
        entry = {}
        for refname, ref in (("refE", fit_e), ("refA", fit_a)):
            se = stats((ve - ref)[m])
            sa = stats((va - ref)[m])
            ratio = se["mean_abs"] / sa["mean_abs"]
            entry[refname] = {
                "E": se,
                "A": sa,
                "ratio": ratio,
                "ratio_rms": se["rms"] / sa["rms"],
                "ratio_median": se["median_abs"] / max(sa["median_abs"], 1e-12),
            }
            print(
                f"  [{mname}/{refname}] S(E) {se['mean_abs']:.5f}  S(A) {sa['mean_abs']:.5f}  "
                f"ratio {ratio:.5f}   (RMS ratio {se['rms'] / sa['rms']:.5f})"
            )
        res["arms"][mname] = entry

    prim = res["arms"]["primary"]
    s_e = prim["refE"]["E"]["mean_abs"]

    # ---- C1: axis swap, the positive control that MUST fail ---------------
    swap_ref = row_line_fit(win_e[rows, :], cols)
    s_swap = float(np.abs(win_e[sub] - swap_ref).mean())
    c1 = s_swap / s_e
    print(f"\nC1 axis swap   : S_swap {s_swap:.5f} / S {s_e:.5f} = {c1:.3f}x  "
          f"({'PASS' if c1 > C1_MIN else 'FAIL'}, registered > {C1_MIN})")
    res["C1"] = {"S_swap": s_swap, "ratio": c1, "pass": bool(c1 > C1_MIN)}

    # ---- C2: frame-label permutation placebo ------------------------------
    rng = np.random.default_rng(SEED)
    perm = rng.permutation(k).astype(np.float64)
    win_p = perm[win_e.astype(np.int64)]
    ref_p = column_line_fit(win_p[:, cols], rows)
    s_perm = float(np.abs(win_p[sub] - ref_p).mean())
    c2 = s_perm / s_e
    print(f"C2 placebo     : S_perm {s_perm:.5f} / S {s_e:.5f} = {c2:.3f}x  "
          f"({'PASS' if c2 > C2_MIN else 'FAIL'}, registered > {C2_MIN})")
    res["C2"] = {"S_perm": s_perm, "ratio": c2, "pass": bool(c2 > C2_MIN)}

    # ---- H_ax and its shape-matched null (registered 4.4) -----------------
    lo, hi = d["lo_E"][sub], d["hi_E"][sub]
    ref = fit_e
    h_ax = float(((lo <= ref) & (ref <= hi)).mean())
    span = hi - lo + 1.0
    width = span
    start = rng.random(width.shape) * (k - width)
    h_null = float(((start <= ref) & (ref <= start + width - 1.0)).mean())
    print(f"\nH_ax           : {100.0 * h_ax:.3f}%   shape-matched null {100.0 * h_null:.3f}%   "
          f"margin {100.0 * (h_ax - h_null):+.3f} pp")
    print(f"admitted span  : mean {float(span.mean()):.3f}  median {float(np.median(span)):.1f}  "
          f"p99 {float(np.percentile(span, 99)):.1f} frames")
    res["H_ax"] = h_ax
    res["H_null"] = h_null
    res["span"] = {
        "mean": float(span.mean()),
        "median": float(np.median(span)),
        "p99": float(np.percentile(span, 99)),
    }

    # An exact-index companion, directly comparable to M67's 39.70% / 35.71%.
    res["exact_E"] = float((np.abs(ve - ref) < 0.5).mean())
    res["exact_A"] = float((np.abs(va - ref) < 0.5).mean())
    print(f"exact index    : E {100.0 * res['exact_E']:.2f}%   A {100.0 * res['exact_A']:.2f}%   "
          f"(M67's plant: 39.70% / 35.71%)")

    # ---- C3: the ink-phase diagnostic -------------------------------------
    r_signed = ve - ref
    prof = phase_profile(r_signed, rows, pitch)
    null_prof = phase_profile(r_signed, rows, pitch * np.sqrt(2.0))
    a_p = float(prof.max() - prof.min())
    a_null = float(null_prof.max() - null_prof.min())
    # The ink template's own phase profile, from the frame-mean image: this is
    # what an ink-locked residual would have to align with.
    lum = d["luma"][sub]
    lum_prof = phase_profile(lum - lum.mean(), rows, pitch)
    corr = float(
        np.corrcoef(prof - prof.mean(), lum_prof - lum_prof.mean())[0, 1]
    )
    print(f"\nC3 ink phase   : A_P {a_p:.5f} frames   incommensurate null {a_null:.5f}   "
          f"{a_p / max(a_null, 1e-12):.2f}x (registered flag at > {C3_MULT}x)")
    print(f"   phase corr with the ink template : {corr:+.4f}")
    res["C3"] = {
        "A_P": a_p,
        "A_null": a_null,
        "ratio": a_p / max(a_null, 1e-12),
        "corr_with_ink": corr,
        "profile": prof.tolist(),
        "ink_profile": lum_prof.tolist(),
    }

    # ---- C4: texture stratification ---------------------------------------
    gy, gx = np.gradient(d["luma"])
    g = np.hypot(gx, gy)[sub]
    t1, t2 = np.percentile(g, [33.333, 66.667])
    blank, inky = g <= t1, g >= t2
    res["C4"] = {}
    for nm, msk in (("blank", blank), ("inky", inky)):
        se = float(np.abs(ve - ref)[msk].mean())
        sa = float(np.abs(va - ref)[msk].mean())
        hh = float(((lo <= ref) & (ref <= hi))[msk].mean())
        res["C4"][nm] = {"S_E": se, "S_A": sa, "ratio": se / sa, "H_ax": hh,
                         "frac": float(msk.mean())}
        print(f"C4 {nm:<6}     : S(E) {se:.5f}  S(A) {sa:.5f}  ratio {se / sa:.5f}  "
              f"H_ax {100.0 * hh:.3f}%  ({100.0 * msk.mean():.1f}% of the mask)")

    return res


def main() -> int:
    geom = json.loads((OUT / "01-geometry.json").read_text(encoding="utf-8"))
    out = {}
    for tag, stack in (("s1", "wrapped-text-1"), ("s2", "wrapped-text-2")):
        out[stack] = score(OUT / tag, geom[stack]["text_row_pitch_px"], stack)

    print(f"\n{'=' * 78}\nREGISTERED DECISIONS (thresholds fixed at 700f87b)\n{'=' * 78}")
    print(f"M67's plant ratio: {M67_E} / {M67_A} = {M67_RATIO:.5f}")
    verdicts = {}
    for stack, r in out.items():
        p = r["arms"]["primary"]
        t1 = p["refE"]["ratio"] < 1.000 and p["refA"]["ratio"] < 1.000
        t2 = all(T2_LO <= p[q]["ratio"] <= T2_HI for q in ("refE", "refA"))
        controls = r["C1"]["pass"] and r["C2"]["pass"]
        if not controls:
            d2 = "INCONCLUSIVE"
        elif p["refE"]["ratio"] >= 1.000 or p["refA"]["ratio"] >= 1.000:
            d2 = "REFUTED"
        elif t1 and t2:
            d2 = "REPRODUCES"
        else:
            d2 = "ORDERING TRANSFERS, MAGNITUDE DOES NOT"
        ink = r["C3"]["ratio"] > C3_MULT and abs(r["C3"]["corr_with_ink"]) > 0.5
        if not controls or r["scored_frac_of_plane"] < MASK_MIN:
            d1 = "INCONCLUSIVE"
        elif r["H_ax"] >= H_AX_PASS and 100.0 * (r["H_ax"] - r["H_null"]) >= H_MARGIN_PP and not ink:
            d1 = "ADMITS CORRECTLY"
        elif r["H_ax"] < H_AX_FAIL or ink:
            d1 = "DOES NOT ADMIT CORRECTLY"
        else:
            d1 = "INCONCLUSIVE"
        verdicts[stack] = {"D1": d1, "D2": d2, "T1": bool(t1), "T2": bool(t2),
                           "ink_locked": bool(ink)}
        print(f"\n{stack}")
        print(f"  ratio refE {p['refE']['ratio']:.5f}   refA {p['refA']['ratio']:.5f}")
        print(f"  T1 {'PASS' if t1 else 'FAIL'}   T2 {'PASS' if t2 else 'FAIL'}")
        print(f"  D1 {d1}")
        print(f"  D2 {d2}")
    out["verdicts"] = verdicts
    (OUT / "03-score.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote", OUT / "03-score.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
