"""s07: the pre-registered analysis of the s06 scans.

Applies, in order and without deviation: the frame-selection rule of
PREREGISTRATION.md section 4.1, the validity gate of section 6.1, the
aggregation of 6.2, the bias correction of 6.3, and the verdict bars of
section 7.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"
FC_CLAIM = 86.30
NYQ = 97.65625
BINNED_NYQ = 48.828125

# instrument calibration frozen in PREREGISTRATION.md section 5 (table C1)
CAL_F = np.array([60.0, 86.3, 110.0, 140.0])
CAL_BIAS_PCT = np.array([0.34, 0.18, 1.61, 2.63])
CAL_SD_PCT = np.array([0.35, 0.31, 1.14, 1.94])
LAMBDA_SYS_PCT = 9.0


def load(stack, plane="G1"):
    return json.loads((OUT / f"s06_scan_{stack}_{plane}.json").read_text(
        encoding="utf-8"))


def gate(d):
    """Section 6.1 validity gate."""
    if "error" in d:
        return False, d["error"]
    if not (d["sigma_um"] < 3.0):
        return False, f"sigma_fit={d['sigma_um']:.2f}>=3"
    if not (d["resid_sd_px"] < 0.6):
        return False, f"resid={d['resid_sd_px']:.2f}>=0.6"
    if not (0.8 <= d["amp"] <= 1.25):
        return False, f"amp={d['amp']:.3f} out of [0.8,1.25]"
    return True, "pass"


def best_frame(recs, roi):
    """Section 4.1: argmax of a 3-frame moving average of MTF(40 cy/mm)."""
    r = sorted([d for d in recs if d["roi"] == roi], key=lambda d: d["frame"])
    m = np.array([d.get("mtf40", np.nan) for d in r], float)
    if np.all(~np.isfinite(m)):
        return None, r, m, None
    k = np.ones(3) / 3.0
    sm = np.convolve(np.nan_to_num(m, nan=0.0), k, mode="same")
    i = int(np.nanargmax(sm))
    return i, r, m, sm


def correct(fc):
    bias = np.interp(fc, CAL_F, CAL_BIAS_PCT)
    sd = np.interp(fc, CAL_F, CAL_SD_PCT)
    return fc / (1.0 + bias / 100.0), sd


def main():
    report = {}
    print("=" * 78)
    print("PER-ROI RESULT AT BEST FOCUS  (frame chosen by 3-frame smoothed "
          "MTF(40), section 4.1)")
    print("=" * 78)
    hdr = (f"{'stack':>14} {'pl':>3} {'roi':>3} {'frm':>4} {'mtf40':>6} "
           f"{'E1':>7} {'sig':>5} {'amp':>5} {'E2':>6} "
           f"{'M(48.8)':>8} {'M(86.3)':>8} {'M(97.7)':>8} {'flr97':>7} "
           f"{'gate':>16}")
    print(hdr)
    rows = []
    for stack, plane in [(s, p) for s in ("119MSDCF", "109MSDCF",
                                          "tweezers-cpl")
                         for p in ("G1", "G2")]:
        recs = load(stack, plane)
        for roi in sorted({d["roi"] for d in recs}):
            i, r, m, sm = best_frame(recs, roi)
            if i is None:
                print(f"{stack:>14} {plane:>3} {roi:>3}   -- all frames failed")
                continue
            d = r[i]
            ok, why = gate(d)
            rd = d["reads"]
            r48, r86, r97 = rd["48.83"], rd["86.30"], rd["97.66"]
            print(f"{stack:>14} {plane:>3} {roi:>3} {d['frame']:4d} "
                  f"{d['mtf40']:6.3f} {d['fc_cymm']:7.2f} "
                  f"{d['sigma_um']:5.2f} {d['amp']:5.3f} {d['bound']:6.1f} "
                  f"{r48['mtf']:8.4f} {r86['mtf']:8.4f} {r97['mtf']:8.4f} "
                  f"{r97['floor']:7.4f} {why:>16}")
            rows.append(dict(stack=stack, plane=plane, roi=roi,
                             frame=d["frame"], pass_gate=ok, why=why,
                             fc=d["fc_cymm"], sigma=d["sigma_um"],
                             amp=d["amp"], bound=d["bound"],
                             mtf40=d["mtf40"], angle=d["angle_deg"],
                             resid=d["resid_sd_px"], contrast=d["contrast"],
                             snr48=r48["snr"], snr86=r86["snr"],
                             snr97=r97["snr"], run3_97=r97["run3"],
                             mtf48=r48["mtf"], mtf86=r86["mtf"],
                             mtf97=r97["mtf"],
                             nbest=len(r)))
    report["rows"] = rows

    print()
    print("=" * 78)
    print("BAR 1 (model-free, one-sided): is MTF at sensor Nyquist "
          "97.66 cy/mm zero?")
    print("=" * 78)
    det = [r for r in rows if r["run3_97"] and r["snr97"] > 3.0]
    stacks_det = sorted({r["stack"] for r in det})
    rois_det = sorted({(r["stack"], r["roi"]) for r in det})
    print(f"  ROIs with MTF(97.66) > 3x floor AND 3 consecutive bins: "
          f"{len(det)}")
    print(f"  distinct ROIs: {len(rois_det)}   distinct stacks: "
          f"{len(stacks_det)} {stacks_det}")
    bar1 = len(rois_det) >= 2 and len(stacks_det) >= 2
    print(f"  pre-registered bar: >=2 ROIs from >=2 stacks  -> "
          f"{'REFUTED (MTF at Nyquist is NOT zero)' if bar1 else 'not refuted'}")
    if det:
        s = np.array([r["snr97"] for r in det])
        v = np.array([r["mtf97"] for r in det])
        print(f"  detected MTF(97.66) = {v.min():.4f} to {v.max():.4f}, "
              f"SNR {s.min():.1f} to {s.max():.1f}")
    report["bar1"] = dict(passed=bool(bar1), n_roi=len(rois_det),
                          stacks=stacks_det)

    print()
    print("=" * 78)
    print("BAR 2 (the number): aggregated f/5.6 cutoff vs the claimed "
          f"{FC_CLAIM} cy/mm")
    print("=" * 78)
    prim = [r for r in rows if r["pass_gate"]
            and r["stack"] in ("119MSDCF", "tweezers-cpl")
            and r["plane"] == "G1"]
    if not prim:
        print("  no ROI passes the validity gate -> UNIDENTIFIED")
        report["bar2"] = {"verdict": "UNIDENTIFIED"}
    else:
        fc = np.array([r["fc"] for r in prim])
        med = float(np.median(fc))
        mad = float(1.4826 * np.median(np.abs(fc - med)))
        corr_med, cal_sd_pct = correct(med)
        spread_pct = 100 * mad / med
        stat_pct = max(spread_pct, cal_sd_pct)
        tot_pct = float(np.hypot(stat_pct, LAMBDA_SYS_PCT))
        half = 1.96 * tot_pct / 100 * corr_med
        lo, hi = corr_med - half, corr_med + half
        print(f"  n = {len(prim)} passing ROI-frames from "
              f"{len(set(r['stack'] for r in prim))} stacks")
        print(f"  raw E1 median      = {med:.2f} cy/mm  "
              f"(range {fc.min():.2f} to {fc.max():.2f})")
        print(f"  robust spread      = {mad:.2f} cy/mm ({spread_pct:.2f}%)")
        print(f"  instrument bias    = {np.interp(med, CAL_F, CAL_BIAS_PCT):+.2f}% "
              f"-> corrected {corr_med:.2f} cy/mm")
        print(f"  statistical sd     = {stat_pct:.2f}%")
        print(f"  wavelength system. = {LAMBDA_SYS_PCT:.1f}%")
        print(f"  combined sd        = {tot_pct:.2f}%")
        print(f"  95% interval       = [{lo:.2f}, {hi:.2f}] cy/mm")
        if lo <= FC_CLAIM <= hi:
            verdict = "CONFIRMED"
        elif lo > FC_CLAIM:
            verdict = "REFUTED (upward)"
        else:
            verdict = "REFUTED (downward)"
        print(f"  -> fact 1149 f_c = {FC_CLAIM}: {verdict}")
        lam = 0.55e-3
        for nm, v in (("lo", lo), ("mid", corr_med), ("hi", hi)):
            neff = 1.0 / (lam * v)
            B = neff / 5.6
            p = 2.762 / (B - 1.0) if B > 1 else np.nan
            print(f"     {nm:>3}: f_c={v:7.2f} -> N_eff={neff:6.2f}  "
                  f"B={B:5.3f}  p(at m=2.762)={p:5.3f}")
        report["bar2"] = dict(verdict=verdict, n=len(prim), raw_median=med,
                              corrected=corr_med, lo=lo, hi=hi,
                              spread_pct=spread_pct, total_pct=tot_pct,
                              values=fc.tolist())

    print()
    print("=" * 78)
    print("BAR 3 (model form, free of m and p): f_c(f/5.6)/f_c(f/11) "
          "predicted 11/5.6 = 1.9643")
    print("=" * 78)
    a = [r["fc"] for r in rows if r["stack"] == "119MSDCF"
         and r["plane"] == "G1" and r["pass_gate"]]
    b = [r["fc"] for r in rows if r["stack"] == "109MSDCF"
         and r["plane"] == "G1" and r["pass_gate"]]
    if a and b:
        ra, rb = float(np.median(a)), float(np.median(b))
        ratio = ra / rb
        print(f"  f/5.6 (119MSDCF) median E1 = {ra:.2f} cy/mm  (n={len(a)})")
        print(f"  f/11  (109MSDCF) median E1 = {rb:.2f} cy/mm  (n={len(b)})")
        print(f"  measured ratio = {ratio:.3f}   predicted 1.9643   "
              f"bar [1.67, 2.26]")
        ok3 = 1.67 <= ratio <= 2.26
        print(f"  -> {'PASS' if ok3 else 'FAIL'}")
        report["bar3"] = dict(ratio=ratio, f56=ra, f11=rb, passed=bool(ok3))
    else:
        print(f"  f/5.6 passing: {len(a)}   f/11 passing: {len(b)}  "
              "-> ratio not computable from passing ROIs")
        af = [r["fc"] for r in rows if r["stack"] == "119MSDCF"
              and r["plane"] == "G1"]
        bf = [r["fc"] for r in rows if r["stack"] == "109MSDCF"
              and r["plane"] == "G1"]
        print(f"  ungated medians: f/5.6 {np.median(af):.2f}  "
              f"f/11 {np.median(bf):.2f}  ratio "
              f"{np.median(af)/np.median(bf):.3f}")
        report["bar3"] = dict(passed=None, ungated_ratio=float(
            np.median(af) / np.median(bf)))

    print()
    print("=" * 78)
    print("MODEL-FREE E2 LOWER BOUNDS (trap 3: these are NOT cutoffs)")
    print("=" * 78)
    for stack in ("119MSDCF", "109MSDCF", "tweezers-cpl"):
        v = np.array([r["bound"] for r in rows if r["stack"] == stack
                      and r["plane"] == "G1"], float)
        v = v[np.isfinite(v)]
        if v.size:
            print(f"  {stack:>14}: E2 median {np.median(v):6.1f} cy/mm, "
                  f"max {v.max():6.1f}   (binned-path Nyquist "
                  f"{BINNED_NYQ:.2f})")

    print()
    print("=" * 78)
    print("G1 vs G2 REPLICATE")
    print("=" * 78)
    for stack in ("119MSDCF", "109MSDCF", "tweezers-cpl"):
        for roi in sorted({r["roi"] for r in rows if r["stack"] == stack}):
            g = {p: [r for r in rows if r["stack"] == stack
                     and r["roi"] == roi and r["plane"] == p]
                 for p in ("G1", "G2")}
            if g["G1"] and g["G2"]:
                print(f"  {stack:>14} {roi}: G1 {g['G1'][0]['fc']:7.2f} "
                      f"(f{g['G1'][0]['frame']:3d})   G2 "
                      f"{g['G2'][0]['fc']:7.2f} (f{g['G2'][0]['frame']:3d})   "
                      f"ratio {g['G1'][0]['fc']/g['G2'][0]['fc']:.4f}")

    (OUT / "s07_verdict.json").write_text(
        json.dumps(report, indent=1, default=float), encoding="utf-8")
    print("\nwrote out/s07_verdict.json")


if __name__ == "__main__":
    main()
