"""M73 step 04 — diagnose the registered `H_ax` rule, repair it as a DECLARED
DEVIATION, and strengthen C3's null.

The pre-registration (700f87b, section 4.4) defined the axial hit rate as

    H_ax = P( lo_adm <= w_hat <= hi_adm )

with `w_hat` the per-column OLS line. `lo_adm` and `hi_adm` are **integers** and
`w_hat` is a **real number**, so for a singleton admitted set (`lo == hi == w`)
the clause requires `w_hat == w` exactly, which for a continuous fit happens on a
set of measure zero. The measured mean `n_eff` is 1.238 and 1.766 frames, and the
median admitted span is 1, so the registered rule is bounded above by
`P(span >= 2)` and is measuring **span width**, not admission correctness.

That is a defect in the pre-registration, not in the data, and it is provable
without looking at which way the result fell. This file:

1. proves the diagnosis, by showing `H_ax <= P(span >= 2)` and how tight it is;
2. reports the repaired rule `P(lo - 0.5 <= w_hat <= hi + 0.5)`, identical to
   `P(lo <= round(w_hat) <= hi)`, as a **post-hoc** statistic carrying less
   evidential weight than the registered one;
3. replaces C3's single incommensurate-pitch null with a null *distribution*
   over many pitches;
4. quantifies ink density inside one focus-operator support window, which is
   what decides whether C4's texture stratification has anything to stratify;
5. prints `n_eff/N` beside every hit rate, which M67's fact 14 requires.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import numpy as np
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
SEED = 0x5CA1AB1E

spec = importlib.util.spec_from_file_location("score03", ROOT / "src" / "03-score.py")
s3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s3)

# Focus operator support: SOBEL_RADIUS + WINDOW_RADIUS = 13 + 1 = 14 in
# strehl-core/src/focus.rs, so the operator reads a 27x27 neighbourhood, and the
# 17x17 regulariser widens the effective support to 43x43.
SUPPORT = 27
EFFECTIVE = 43


def main() -> int:
    geom = json.loads((OUT / "01-geometry.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(SEED)
    out: dict = {}
    for tag, stack in (("s1", "wrapped-text-1"), ("s2", "wrapped-text-2")):
        d = s3.load(OUT / tag)
        h, w, k = d["height"], d["width"], d["frames"]
        rows = np.arange(s3.MARGIN, h - s3.MARGIN)
        cols = np.arange(s3.MARGIN, w - s3.MARGIN)
        sub = np.ix_(rows, cols)
        ref = s3.column_line_fit(d["win_E"][:, cols], rows)
        ref_a = s3.column_line_fit(d["win_A"][:, cols], rows)
        ve, va = d["win_E"][sub], d["win_A"][sub]
        lo, hi = d["lo_E"][sub], d["hi_E"][sub]
        loa, hia = d["lo_A"][sub], d["hi_A"][sub]
        span = hi - lo + 1.0
        n_eff = float(d["mean_n_eff_E"])

        print(f"\n{'=' * 78}\n{stack}: K = {k}\n{'=' * 78}")
        print(f"n_eff       : {n_eff:.5f}   n_eff/N = {n_eff / k:.5f}")
        print("              (M67 fact 14a: the corpus range M64 PR3 measured is 0.014-0.30,")
        print("               with foam at 0.0136; M67's own plant sat at 6.84/25 = 0.2736)")

        # ---- 1. the diagnosis --------------------------------------------
        p_span1 = float((span == 1).mean())
        p_span2 = float((span >= 2).mean())
        h_reg = float(((lo <= ref) & (ref <= hi)).mean())
        print(f"\nspan == 1   : {100.0 * p_span1:.3f}% of scored pixels")
        print(f"span >= 2   : {100.0 * p_span2:.3f}%   <-- the ceiling on the REGISTERED rule")
        print(f"H_ax as REGISTERED : {100.0 * h_reg:.3f}%   ratio to the ceiling "
              f"{h_reg / max(p_span2, 1e-12):.4f}")

        # ---- 2. the repaired rule (DECLARED DEVIATION, post-hoc) ----------
        h_rep = float(((lo - 0.5 <= ref) & (ref <= hi + 0.5)).mean())
        h_rep_a = float(((loa - 0.5 <= ref) & (ref <= hia + 0.5)).mean())
        width = span
        start = rng.random(width.shape) * (k - width)
        h_rep_null = float(((start - 0.5 <= ref) & (ref <= start + width - 0.5)).mean())
        print(f"\nH repaired  : E  {100.0 * h_rep:.3f}%   A' {100.0 * h_rep_a:.3f}%   "
              f"shape-matched null {100.0 * h_rep_null:.3f}%")
        print(f"              margin over null {100.0 * (h_rep - h_rep_null):+.3f} pp")
        print(f"              (M67's plant, for scale: H(E) 99.955% at n_eff/N 0.2736)")

        # The reference above is fitted to E's own winner map and therefore
        # favours E. Repeat every ordering claim against A's, which favours A.
        h_rep_e_ra = float(((lo - 0.5 <= ref_a) & (ref_a <= hi + 0.5)).mean())
        h_rep_a_ra = float(((loa - 0.5 <= ref_a) & (ref_a <= hia + 0.5)).mean())
        ex_e_re = float((np.abs(ve - ref) < 0.5).mean())
        ex_a_re = float((np.abs(va - ref) < 0.5).mean())
        ex_e_ra = float((np.abs(ve - ref_a) < 0.5).mean())
        ex_a_ra = float((np.abs(va - ref_a) < 0.5).mean())
        print(f"  under refA: E  {100.0 * h_rep_e_ra:.3f}%   A' {100.0 * h_rep_a_ra:.3f}%   "
              f"(the reference that favours A)")
        print(f"\nelection    : exact-index E {100.0 * ex_e_re:.2f}% / A {100.0 * ex_a_re:.2f}% "
              f"under refE;  E {100.0 * ex_e_ra:.2f}% / A {100.0 * ex_a_ra:.2f}% under refA")
        print(f"gate lift   : {100.0 * (h_rep - ex_e_re):+.2f} pp over the election "
              f"(M67's plant: 39.70% -> 99.96%, a +60.26 pp lift)")

        # ---- 3. residual CDF ---------------------------------------------
        cdf = {}
        for nm, v in (("E", ve), ("A", va)):
            r = np.abs(v - ref)
            cdf[nm] = {f"le_{t}": float((r <= t).mean()) for t in (0.5, 1.0, 2.0, 5.0)}
            print(f"|r| {nm:<2}      : <=0.5 {100 * cdf[nm]['le_0.5']:6.2f}%   "
                  f"<=1 {100 * cdf[nm]['le_1.0']:6.2f}%   <=2 {100 * cdf[nm]['le_2.0']:6.2f}%   "
                  f"<=5 {100 * cdf[nm]['le_5.0']:6.2f}%")

        # ---- 4. C3 with a null DISTRIBUTION over incommensurate pitches ---
        pitch = geom[stack]["text_row_pitch_px"]
        r_signed = ve - ref
        a_true = float(np.ptp(s3.phase_profile(r_signed, rows, pitch)))
        nulls = []
        for f in np.linspace(0.55, 1.85, 120):
            if abs(f - 1.0) < 0.06 or abs(f - 0.5) < 0.04 or abs(f - 1.5) < 0.04:
                continue  # skip the true pitch and its low harmonics
            nulls.append(float(np.ptp(s3.phase_profile(r_signed, rows, pitch * f))))
        nulls = np.array(nulls)
        z = (a_true - nulls.mean()) / nulls.std(ddof=1)
        pct = float((nulls >= a_true).mean())
        print(f"\nC3 A_P      : {a_true:.5f} frames at the text pitch {pitch:.1f} px")
        print(f"   null dist: mean {nulls.mean():.5f}  sd {nulls.std(ddof=1):.5f}  "
              f"n = {len(nulls)}")
        print(f"   z = {z:+.2f}   P(null >= observed) = {pct:.3f}   "
              f"{'NO ink-locked signature' if pct > 0.05 else 'SIGNATURE PRESENT'}")
        power = float(nulls.mean() + 3.0 * nulls.std(ddof=1))
        print(f"   power    : excludes an ink-phase-locked bias of amplitude > {power:.3f} "
              f"frames at 3 sd")

        # ---- 5. ink density inside one operator support window ------------
        ink = np.load(OUT / f"ink-{stack}.npy")
        ih, iw = ink.shape
        dens_sup = ndimage.uniform_filter(ink.astype(np.float32), SUPPORT, mode="nearest")
        dens_eff = ndimage.uniform_filter(ink.astype(np.float32), EFFECTIVE, mode="nearest")
        empty_sup = float((dens_sup < 0.005).mean())
        empty_eff = float((dens_eff < 0.005).mean())
        print(f"\nink density : global {ink.mean():.4f}")
        print(f"   pixels with <0.5% ink in a {SUPPORT}x{SUPPORT} operator window : "
              f"{100.0 * empty_sup:.3f}%")
        print(f"   pixels with <0.5% ink in the {EFFECTIVE}x{EFFECTIVE} effective support : "
              f"{100.0 * empty_eff:.3f}%")
        print("   -> most of the plane carries no printed glyph at the operator's scale, yet")
        print("      C4's low-gradient tercile is only modestly worse than its high-gradient")
        print("      one, so the label STOCK's own texture is carrying the focus signal there")

        out[stack] = {
            "K": k,
            "n_eff": n_eff,
            "n_eff_over_N": n_eff / k,
            "p_span_eq_1": p_span1,
            "p_span_ge_2": p_span2,
            "H_registered": h_reg,
            "H_registered_over_ceiling": h_reg / max(p_span2, 1e-12),
            "H_repaired_E": h_rep,
            "H_repaired_A": h_rep_a,
            "H_repaired_null": h_rep_null,
            "H_repaired_E_refA": h_rep_e_ra,
            "H_repaired_A_refA": h_rep_a_ra,
            "exact_E_refE": ex_e_re,
            "exact_A_refE": ex_a_re,
            "exact_E_refA": ex_e_ra,
            "exact_A_refA": ex_a_ra,
            "gate_lift_pp": 100.0 * (h_rep - ex_e_re),
            "residual_cdf": cdf,
            "C3_A_P": a_true,
            "C3_null_mean": float(nulls.mean()),
            "C3_null_sd": float(nulls.std(ddof=1)),
            "C3_z": float(z),
            "C3_p": pct,
            "C3_power_3sd": power,
            "ink_global": float(ink.mean()),
            "ink_empty_support_frac": empty_sup,
            "ink_empty_effective_frac": empty_eff,
            "plane_note": [int(iw), int(ih)],
        }

    (OUT / "04-repair.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote", OUT / "04-repair.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
