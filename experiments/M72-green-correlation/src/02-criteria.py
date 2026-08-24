"""M72 step 2 -- apply the pre-registered criteria C0-C6.

Committed while 01 is still decoding, so the classifier cannot be tuned to
the answer.  Every band here is copied from 01's docstring; nothing is
introduced.

Run: python 02-criteria.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

spec = importlib.util.spec_from_file_location("m72", HERE / "01-green-correlation.py")
m72 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m72)

# crates/strehl-core/src/profile.rs: "Gain is max(iso, base_iso) / gain_divisor
# DN per electron", with base_iso 100.0, gain_divisor 436.8, dual-gain switch
# at second_base_iso 400.0.  Read, not modified.
BASE_ISO = 100.0
GAIN_DIVISOR = 436.8
SECOND_BASE_ISO = 400.0
READ_NOISE_E_LOW = 4.20
READ_NOISE_E_HIGH = 1.2392


def gain(iso: float) -> float:
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def mode(iso: float) -> int:
    return 1 if iso >= SECOND_BASE_ISO else 0


def rule(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def fit_alpha_delta(g: np.ndarray, md: np.ndarray, y: np.ndarray) -> dict:
    """y = alpha[mode] * g^2 + delta, least squares, shared delta."""
    cols = [np.where(md == 0, g * g, 0.0), np.where(md == 1, g * g, 0.0),
            np.ones_like(g)]
    a = np.stack(cols, axis=1)
    sol, *_ = np.linalg.lstsq(a, y, rcond=None)
    resid = y - a @ sol
    return {"alpha_low": float(sol[0]), "alpha_high": float(sol[1]),
            "delta": float(sol[2]), "resid_rms": float(np.sqrt((resid ** 2).mean()))}


def jackknife_fit(g: np.ndarray, md: np.ndarray, y: np.ndarray) -> dict:
    n = len(g)
    keys = ("alpha_low", "alpha_high", "delta")
    full = fit_alpha_delta(g, md, y)
    reps = []
    for i in range(n):
        k = np.ones(n, bool)
        k[i] = False
        reps.append(fit_alpha_delta(g[k], md[k], y[k]))
    out = dict(full)
    for key in keys:
        vals = np.array([r[key] for r in reps])
        out[f"{key}_se"] = float(np.sqrt((n - 1) / n * ((vals - vals.mean()) ** 2).sum()))
    return out


def main() -> int:
    payload = json.loads((DATA / "01-green-correlation.json").read_text(encoding="utf-8"))
    groups = sorted(payload["groups"], key=lambda r: r["iso"])
    isos = np.array([r["iso"] for r in groups], float)
    verdicts: dict[str, str] = {}

    print("M72 -- criteria C0-C6, bands quoted from the pre-registration")
    print(f"groups: {len(groups)}   ISO {isos.min():.0f} to {isos.max():.0f}")
    print("  " + "  ".join(f"{r['group']}={r['iso']}" for r in groups))

    # ---------------------------------------------------------------- C0
    rule("C0 -- INSTRUMENT (void-on-fail).  |rho| <= 0.005 on both nulls")
    s = payload["synthetic_null"]
    print(f"\n  synthetic null   raw {s['rho_raw']:+.6f}   shep {s['rho_shep']:+.6f}"
          f"   perm {s['rho_perm']:+.6f}   cells {s['cells']}")
    worst = max(abs(s["rho_raw"]), abs(s["rho_shep"]), abs(s["rho_perm"]))
    print("\n  real-data frame-permutation null, arm k6, every pair, every ISO:")
    print(f"    {'ISO':>5}  " + "  ".join(f"{a}-{b}".rjust(8) for a, b, _ in m72.PAIRS))
    worst_perm = 0.0
    for r in groups:
        pr = r["arms"]["k6"]["pairs"]
        row = "  ".join(f"{pr[f'{a}-{b}']['rho_perm']:+8.5f}" for a, b, _ in m72.PAIRS)
        print(f"    {r['iso']:5.0f}  {row}")
        for a, b, _ in m72.PAIRS:
            worst_perm = max(worst_perm, abs(pr[f"{a}-{b}"]["rho_perm"]))
    print(f"\n  worst synthetic |rho| {worst:.6f}   worst permutation |rho| {worst_perm:.6f}"
          f"   band {m72.C0_BAND}")
    c0 = worst <= m72.C0_BAND and worst_perm <= m72.C0_BAND
    verdicts["C0"] = "PASS" if c0 else "FAIL"
    print(f"  C0: {verdicts['C0']}")
    if not c0:
        print("  CONSEQUENCE (pre-registered): no rho in this report stands.")

    # ---------------------------------------------------------------- C1
    rule("C1 -- REPLICATION of fact 895 at ISO 100, group 118MSDCF, G1-G2")
    tgt = next(r for r in groups if r["group"] == m72.M62_GROUP)
    print(f"\n  target group {tgt['group']}, ISO {tgt['iso']}, M62's own group")
    print(f"\n    {'arm':>5} {'retained':>9} {'var G1':>9} {'var G2':>9} "
          f"{'cov':>10} {'rho_raw':>9} {'rho_shep':>9}")
    for arm in ("k6", "k3", "none"):
        e = tgt["arms"][arm]["pairs"]["G1-G2"]
        print(f"    {arm:>5} {tgt['arms'][arm]['retained']:9.5f} {e['var_a']:9.5f} "
              f"{e['var_b']:9.5f} {e['cov']:10.6f} {e['rho_raw']:+9.5f} {e['rho_shep']:+9.5f}")
    rho = tgt["arms"]["k6"]["pairs"]["G1-G2"]["rho_shep"]
    print(f"\n  M62 P17 published rho = {m72.RHO_M62:+.4f} "
          f"(cov 0.0721, var(green) 0.53229, from a difference of variances)")
    print(f"  M72 direct     measured rho = {rho:+.5f}   difference "
          f"{rho - m72.RHO_M62:+.5f}")
    if abs(rho - m72.RHO_M62) <= m72.C1_REPLICATE:
        verdicts["C1"] = "REPLICATED"
    elif abs(rho) <= m72.C1_REFUTE:
        verdicts["C1"] = "REFUTED"
    else:
        verdicts["C1"] = "PARTIAL"
    print(f"\n  bands: |rho-0.073| <= {m72.C1_REPLICATE} REPLICATED, "
          f"|rho| <= {m72.C1_REFUTE} REFUTED, else PARTIAL")
    print(f"  C1: {verdicts['C1']}")
    if verdicts["C1"] == "REFUTED":
        print("  CONSEQUENCE (pre-registered): fact 895 withdrawn, item closes.")

    # ---------------------------------------------------------------- C2
    rule("C2 -- GREEN-SPECIFICITY.  R-B is the other diagonal pair: the control")
    print("\n  All six pairs, arm k6, Sheppard-corrected, every ISO.")
    print("  Geometry classes were fixed in the pre-registration, not here.\n")
    hdr = "  ".join(f"{a}-{b}".rjust(8) for a, b, _ in m72.PAIRS)
    cls = "  ".join(c[:8].rjust(8) for _, _, c in m72.PAIRS)
    print(f"    {'ISO':>5}  {hdr}")
    print(f"    {'':>5}  {cls}")
    for r in groups:
        pr = r["arms"]["k6"]["pairs"]
        print(f"    {r['iso']:5.0f}  " +
              "  ".join(f"{pr[f'{a}-{b}']['rho_shep']:+8.5f}" for a, b, _ in m72.PAIRS))
    g_rho = tgt["arms"]["k6"]["pairs"]["G1-G2"]["rho_shep"]
    d_rho = tgt["arms"]["k6"]["pairs"]["R-B"]["rho_shep"]
    print(f"\n  at ISO 100:  rho(G1,G2) = {g_rho:+.5f}   rho(R,B) = {d_rho:+.5f}"
          f"   difference {d_rho - g_rho:+.5f}")
    if verdicts["C1"] == "REFUTED":
        verdicts["C2"] = "NOT EVALUATED (C1 REFUTED)"
    elif abs(d_rho - g_rho) <= m72.C2_SAME:
        verdicts["C2"] = "NOT GREEN-SPECIFIC (H3)"
    elif g_rho != 0 and d_rho <= m72.C2_SPECIFIC * g_rho:
        verdicts["C2"] = "GREEN-SPECIFIC (H2)"
    else:
        verdicts["C2"] = "INTERMEDIATE"
    print(f"  bands: |d-r| <= {m72.C2_SAME} not-specific, d <= {m72.C2_SPECIFIC}*r specific")
    print(f"  C2: {verdicts['C2']}")

    # ---------------------------------------------------------------- C3
    rule("C3 -- COMMON-MODE SHARE.  f = cov(frame means) / cov(per cell)")
    print("\n  cov(frame means) measures a spatially UNIFORM per-frame term")
    print("  directly (H1).  Per-frame plane-mean span is shown as a sanity")
    print("  check against M62 P14's 0.079 DN.\n")
    print(f"    {'ISO':>5} {'span G1':>9} {'span G2':>9} {'cm cov':>11} "
          f"{'cell cov':>11} {'f_uniform':>10} {'rho_disp':>9}")
    fs = []
    for r in groups:
        e = r["arms"]["k6"]["pairs"]["G1-G2"]
        cmv = r["frame_mean_cov"]["G1-G2"]
        f = cmv / e["cov"] if e["cov"] != 0 else float("nan")
        fs.append(f)
        print(f"    {r['iso']:5.0f} {r['frame_mean_span']['G1']:9.4f} "
              f"{r['frame_mean_span']['G2']:9.4f} {cmv:11.6f} {e['cov']:11.6f} "
              f"{f:10.4f} {e['rho_disp']:+9.5f}")
    f_iso100 = fs[[r["group"] for r in groups].index(m72.M62_GROUP)]
    print(f"\n  f at ISO 100 = {f_iso100:.4f}")
    if verdicts["C1"] == "REFUTED":
        verdicts["C3"] = "NOT EVALUATED (C1 REFUTED)"
    elif f_iso100 >= m72.C3_UNIFORM:
        verdicts["C3"] = "UNIFORM COMMON MODE (H1)"
    elif f_iso100 <= m72.C3_LOCAL:
        verdicts["C3"] = "LOCAL"
    else:
        verdicts["C3"] = "MIXED"
    print(f"  bands: f >= {m72.C3_UNIFORM} uniform, f <= {m72.C3_LOCAL} local, else mixed")
    print(f"  C3: {verdicts['C3']}")

    # ---------------------------------------------------------------- C4
    rule("C4 -- GEOMETRY.  M61 section 4.13's pairing, fixed in advance")
    print("\n  Local covariance = per-cell cov minus the uniform part, by class.\n")
    print(f"    {'ISO':>5}  {'row':>10} {'column':>10} {'diagonal':>10}  "
          f"{'spread':>9}")
    spreads = []
    for r in groups:
        pr = r["arms"]["k6"]["pairs"]
        by = {}
        for a, b, c in m72.PAIRS:
            loc = pr[f"{a}-{b}"]["cov"] - r["frame_mean_cov"][f"{a}-{b}"]
            by.setdefault(c, []).append(loc)
        mrow, mcol, mdia = (float(np.mean(by[c])) for c in ("row", "column", "diagonal"))
        sp = max(mrow, mcol, mdia) - min(mrow, mcol, mdia)
        spreads.append(sp)
        print(f"    {r['iso']:5.0f}  {mrow:10.6f} {mcol:10.6f} {mdia:10.6f}  {sp:9.6f}")
    print("\n  O5 -- within-plane, same sensor ROW vs same sensor COLUMN, arm k6:\n")
    print(f"    {'ISO':>5}  " + "  ".join(f"{p} row/col".rjust(17) for p in m72.PLANES))
    for r in groups:
        w = r["arms"]["k6"]["within"]
        print(f"    {r['iso']:5.0f}  " +
              "  ".join(f"{w[p]['same_row']:+8.5f}/{w[p]['same_col']:+8.5f}"
                        for p in m72.PLANES))
    sp100 = spreads[[r["group"] for r in groups].index(m72.M62_GROUP)]
    if verdicts["C1"] == "REFUTED":
        verdicts["C4"] = "NOT EVALUATED (C1 REFUTED)"
    elif sp100 <= m72.C4_AGREE:
        verdicts["C4"] = "GEOMETRY DOES NOT DISCRIMINATE"
    else:
        verdicts["C4"] = "CLASSES DIFFER"
    print(f"\n  class spread at ISO 100 = {sp100:.6f}   band {m72.C4_AGREE}")
    print(f"  C4: {verdicts['C4']}")

    # ---------------------------------------------------------------- C5
    rule("C5 -- MECHANISM LOCATION.  cov(ISO) = alpha_c G^2 + delta_c")
    g = np.array([gain(i) for i in isos])
    md = np.array([mode(i) for i in isos])
    print("\n  Trend of rho with ISO, corrected and uncorrected.  Section 4 of")
    print("  the derivation: flat means the covariance has the SAME upstream/")
    print("  downstream split as the variance; any departure locates it.\n")
    print(f"    {'ISO':>5} {'G':>8} {'var G1':>9} {'cov':>10} "
          f"{'rho_raw':>9} {'rho_shep':>9}")
    covs, rr, rs = [], [], []
    for r, gg in zip(groups, g):
        e = r["arms"]["k6"]["pairs"]["G1-G2"]
        covs.append(e["cov"])
        rr.append(e["rho_raw"])
        rs.append(e["rho_shep"])
        print(f"    {r['iso']:5.0f} {gg:8.5f} {e['var_a']:9.5f} {e['cov']:10.6f} "
              f"{e['rho_raw']:+9.5f} {e['rho_shep']:+9.5f}")
    covs, rr, rs = np.array(covs), np.array(rr), np.array(rs)
    lg = np.log(g)
    sr = float(np.polyfit(lg, rr, 1)[0])
    ss = float(np.polyfit(lg, rs, 1)[0])
    cr = float(np.corrcoef(lg, rr)[0, 1])
    cs = float(np.corrcoef(lg, rs)[0, 1])
    print(f"\n  slope of rho against log G:  raw {sr:+.6f} (r={cr:+.3f})   "
          f"shep {ss:+.6f} (r={cs:+.3f})")
    agree = np.sign(sr) == np.sign(ss)
    print(f"  corrected and uncorrected agree on direction: {agree}")
    fit = jackknife_fit(g, md, covs)
    print(f"\n  cov fit:  alpha_low {fit['alpha_low']:+.5f} +/- {fit['alpha_low_se']:.5f}"
          f"   alpha_high {fit['alpha_high']:+.5f} +/- {fit['alpha_high_se']:.5f}")
    print(f"            delta     {fit['delta']:+.6f} +/- {fit['delta_se']:.6f}"
          f"   resid rms {fit['resid_rms']:.6f}")
    spans = {k: abs(fit[k]) <= fit[f"{k}_se"] for k in ("alpha_low", "alpha_high", "delta")}
    print(f"  jackknife bar spans zero:  {spans}")
    if verdicts["C1"] == "REFUTED":
        verdicts["C5"] = "NOT EVALUATED (C1 REFUTED)"
    elif not agree or (spans["alpha_low"] and spans["delta"]):
        verdicts["C5"] = "INSTRUMENT-LIMITED, NO MECHANISM NAMED"
    else:
        up = fit["alpha_low"] * gain(100.0) ** 2
        tot = up + fit["delta"]
        verdicts["C5"] = f"upstream fraction at base ISO {up / tot:+.3f}" if tot else "DEGENERATE"
    print(f"  C5: {verdicts['C5']}")

    # ---------------------------------------------------------------- C6
    rule("C6 -- OPERATIONAL REGIME.  State the regime, not just the magnitude")
    print("\n  green_luma_sigma (noise.rs:126) computes var(L) = (var G1 + var G2)/4,")
    print("  i.e. rho = 0.  Truth is var(L) = (var G1 + var G2 + 2 cov)/4.")
    print("  Under H-read the covariance is fixed in DN^2 and rho falls as the")
    print("  shot term grows.  Using the measured dark covariance per ISO:\n")
    print(f"    {'ISO':>5} {'cov DN^2':>10}  " +
          "  ".join(f"S={s:.0f}".rjust(9) for s in (0, 10, 100, 1000, 4000)))
    worst_err = 0.0
    for r, gg in zip(groups, g):
        e = r["arms"]["k6"]["pairs"]["G1-G2"]
        cov = e["cov"]
        rn = READ_NOISE_E_LOW if r["iso"] < SECOND_BASE_ISO else READ_NOISE_E_HIGH
        cells = []
        for sig in (0.0, 10.0, 100.0, 1000.0, 4000.0):
            var = gg * sig + (rn * gg) ** 2
            err = np.sqrt(1.0 + cov / var) - 1.0
            worst_err = max(worst_err, abs(err))
            cells.append(f"{100 * err:+8.3f}%")
        print(f"    {r['iso']:5.0f} {cov:10.6f}  " + "  ".join(c.rjust(9) for c in cells))
    print(f"\n  worst |sigma error| anywhere in the table: {100 * worst_err:.3f} %")
    print(f"  M69's FOCUS_NOISE_SD error on real texture: {100 * M69_FOCUS_NOISE_SD_ERROR:.0f} %")
    thresh = m72.C6_MATERIAL_FRACTION * M69_FOCUS_NOISE_SD_ERROR
    print(f"  pre-registered materiality threshold: {100 * thresh:.2f} %")
    verdicts["C6"] = ("IMMATERIAL IN PRACTICE" if worst_err < thresh
                      else "MATERIAL")
    print(f"  C6: {verdicts['C6']}")

    rule("VERDICTS")
    for k in ("C0", "C1", "C2", "C3", "C4", "C5", "C6"):
        print(f"  {k}: {verdicts[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
