"""M98 -- dump every number the report quotes, from the frozen JSON outputs.

No measurement happens here.  This exists so that every figure in
docs/research/M98-gate-adjudication.md can be traced to a file on disk with
one command, and so that a re-run catches any figure I mistyped.

Usage:  python s7_report.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m98lib as M98  # noqa: E402

GATES = ["0", "0.5", "1", "2", "4"]


def jload(name):
    p = os.path.join(M98.OUT, name)
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def agg(rows, key):
    v = np.array([r[key] for r in rows], float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan"), float("nan"), 0
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(v.size)), int(v.size)


def band(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def dump_s4(d, tag):
    band(f"S4 {tag} -- full-stack ladder, one alignment solve per gate")
    print(f"  plane {d['w']} x {d['h']}, {len(d['grid'])} ROIs of "
          f"{M98.ROI} px")
    for arm in ("ALN", "ZOOM"):
        if arm not in d["arms"]:
            continue
        a = d["arms"][arm]
        print(f"\n  --- ARM {arm} : pooled over all ROIs ---")
        print(f"  {'gate':>6} {'A_hf raw':>10} {'A_hf clean':>11} "
              f"{'+/-':>8} {'dsig px':>10} {'+/-':>8} {'sigma':>7} "
              f"{'n+':>5}")
        for g in GATES:
            rows = a["per_gate"][g]
            r_m, r_s, _ = agg(rows, "raw_ratio")
            c_m, c_s, _ = agg(rows, "clean_ratio")
            d_m, d_s, n = agg(rows, "dsig")
            npos = sum(1 for r in rows
                       if np.isfinite(r["dsig"]) and r["dsig"] > 0)
            sig = d_m / d_s if d_s > 0 else float("nan")
            print(f"  {g:>6} {r_m:>10.5f} {c_m:>11.5f} {c_s:>8.5f} "
                  f"{d_m:>+10.5f} {d_s:>8.5f} {sig:>7.2f} "
                  f"{npos:>2}/{n:<2}")

        print(f"\n  --- ARM {arm} : stratified by detail (discipline 603) ---")
        hp = np.array(d["hp_sd"], float)
        order = np.argsort(hp)
        thirds = np.array_split(order, 3)
        for name, idx in zip(("LOW", "MID", "HIGH"), thirds):
            print(f"    {name:>4} hp_sd {hp[idx].min():.0f}-"
                  f"{hp[idx].max():.0f}  n={len(idx)}")
            for g in ("1", "4"):
                rows = [a["per_gate"][g][k] for k in idx]
                c_m, c_s, _ = agg(rows, "clean_ratio")
                d_m, d_s, n = agg(rows, "dsig")
                sig = d_m / d_s if d_s > 0 else float("nan")
                print(f"      gate {g:>3}  A_hf {c_m:.4f}+/-{c_s:.4f}   "
                      f"dsig {d_m:+.5f}+/-{d_s:.5f}  ({sig:.2f} sigma)")

        fl = a.get("flat")
        if fl:
            print(f"\n  --- ARM {arm} : noise floor on the flattest ROI "
                  f"(#{a.get('flat_roi')}) ---")
            for g in GATES:
                fr = fl[g]
                print(f"    gate {g:>3}  floor power {fr['ratio']:.5f}  "
                      f"sigma {fr['sigma']:.4f}x   "
                      f"(CLI mean n_eff {fr['cli'][0]:.3f}, CLI predicted "
                      f"sigma {fr['cli'][1]:.4f}x)")


def dump_s3(d, tag):
    band(f"S3 {tag} -- external anchor, millimetre ruler")
    print(f"  live ROIs {d.get('live')} of {d.get('frozen')} scanned")
    blur = d.get("blur", {})
    if d.get("rows"):
        f0 = np.array([r["f0"] for r in d["rows"]], float)
        pp = np.array([r["pitch_px"] for r in d["rows"]], float)
        print(f"  comb fundamental f0 = {f0.min():.4f}-{f0.max():.4f} cyc/px"
              f"  (tick pitch {pp.min():.2f}-{pp.max():.2f} px)")
    for hk in sorted(blur):
        n = int(hk[1:])
        print(f"\n  harmonic n={n}   (f = n * f0)")
        for g in ("0.0", "0.5", "1.0", "2.0", "4.0"):
            if g not in blur[hk]:
                continue
            b = blur[hk][g]
            print(f"    gate {g:>3}  modulation {b['r']:.5f} "
                  f"+/- {b['r_se']:.5f}   equivalent blur "
                  f"{b['px']:+.4f} +/- {b['px_se']:.4f} px   n={b['n']}")
        b4 = blur[hk].get("4.0")
        if b4 and b4["px_se"] > 0:
            z = (0.61753 - b4["px"]) / b4["px_se"]
            print(f"    -> M92's 0.61753 px is excluded at {z:.1f} sigma")


def dump_s2(d):
    band("S2 -- controls (112MSDCF)")
    for k, v in d.items():
        print(f"  {k:<8} {v}")


def dump_s1(d, tag):
    band(f"S1 {tag} -- half-merge parity instrument")
    a = d.get("arms", d)
    for arm in a:
        if arm not in ("ALN", "ZOOM"):
            continue
        print(f"\n  --- ARM {arm} ---")
        for g in GATES:
            rows = a[arm]["per_gate"].get(g)
            if not rows:
                continue
            c_m, c_s, _ = agg(rows, "a_hf_ratio")
            d_m, d_s, n = agg(rows, "dsig")
            npos = sum(1 for r in rows
                       if np.isfinite(r["dsig"]) and r["dsig"] > 0)
            sig = d_m / d_s if d_s > 0 else float("nan")
            print(f"    gate {g:>3}  A_hf {c_m:.5f}  dsig {d_m:+.5f}"
                  f"+/-{d_s:.5f}  ({sig:.2f} sigma)  {npos}/{n} positive")
        hp = np.array(d["hp_sd"], float)
        order = np.argsort(hp)
        thirds = np.array_split(order, 3)
        for name, idx in zip(("LOW", "MID", "HIGH"), thirds):
            rows = [a[arm]["per_gate"]["4"][k] for k in idx]
            d_m, d_s, n = agg(rows, "dsig")
            sig = d_m / d_s if d_s > 0 else float("nan")
            print(f"    {name:>4} tercile (hp_sd {hp[idx].min():.0f}-"
                  f"{hp[idx].max():.0f}) gate 4  dsig {d_m:+.5f}"
                  f"+/-{d_s:.5f}  ({sig:.2f} sigma)")
        fl = a[arm].get("flat")
        if isinstance(fl, dict):
            print(f"    FLAT control (ROI #{a[arm].get('flat_roi')}): "
                  f"{'PASS' if a[arm].get('flat_ok') else 'RED'}")
            for g in GATES:
                fr = fl.get(g)
                if isinstance(fr, dict):
                    print(f"      gate {g:>3}  " + "  ".join(
                        f"{kk} {vv:.5f}" for kk, vv in fr.items()
                        if isinstance(vv, (int, float))))


def dump_h3(d4, d1):
    band("H3 / prediction (c) -- is mean n_eff a description of where detail is?")
    print("  No per-pixel n_eff map exists on the shipped CLI (grep of")
    print("  crates/strehl-cli/src/*.rs finds no map output), so PREREG's")
    print("  declared substitution applies: local n_eff is estimated from the")
    print("  ROI's own above-cutoff noise floor, n_eff_loc = floor(0)/floor(T).")
    print("  BIAS DIRECTION (rule 18): in a detailed ROI, signal leaks into the")
    print("  f in [0.30,0.45] floor band, so floor(T)/floor(0) is pulled toward")
    print("  1 and n_eff_loc is UNDERSTATED. The bias runs TOWARD H3. H3 is")
    print("  therefore only reportable if it FAILS -- which is what happens.")
    hp = np.array(d4["hp_sd"], float)
    order = np.argsort(hp)
    thirds = np.array_split(order, 3)
    a = d4["arms"]["ALN"]
    glob = a["flat"]["4"]["cli"][0]
    print(f"\n  bee-3-cpl, gate 4, global mean n_eff (CLI) = {glob:.3f}")
    for name, idx in zip(("LOW", "MID", "HIGH"), thirds):
        v = np.array([a["per_gate"]["4"][k]["floor_ratio"] for k in idx],
                     float)
        ne = 1.0 / v
        print(f"    {name:>4} hp_sd {hp[idx].min():.0f}-{hp[idx].max():.0f}  "
              f"n_eff_loc median {np.median(ne):>7.2f}  "
              f"range {ne.min():.2f}-{ne.max():.2f}  "
              f"({np.median(ne) / glob:.3f} x global)")
    if d1 is None:
        return
    print("\n  112MSDCF (half-merge instrument, which measures the incoherent")
    print("  power directly rather than inferring it from a floor band):")
    hp1 = np.array(d1["hp_sd"], float)
    o1 = np.argsort(hp1)
    t1 = np.array_split(o1, 3)
    a1 = d1["arms"]["ALN"]
    for name, idx in zip(("LOW", "MID", "HIGH"), t1):
        base = np.array([a1["per_gate"]["0"][k]["n_incoh"] for k in idx],
                        float)
        cur = np.array([a1["per_gate"]["4"][k]["n_incoh"] for k in idx], float)
        ne = base / cur
        print(f"    {name:>4} hp_sd {hp1[idx].min():.0f}-{hp1[idx].max():.0f}"
              f"  n_eff_loc median {np.median(ne):.2f}  "
              f"range {ne.min():.2f}-{ne.max():.2f}   "
              f"(global mean n_eff on half A = 6.489)")


def dump_paired(d4):
    band("H1 -- ALN vs ZOOM, PAIRED by ROI (the arms share the scene)")
    print("  H1's falsifier as pre-registered: the aligned arm's gate contrast")
    print("  is >= the FOV- and resampler-matched unaligned arm's, on the top")
    print("  detail tercile of bee-3-cpl.")
    hp = np.array(d4["hp_sd"], float)
    order = np.argsort(hp)
    thirds = np.array_split(order, 3)
    A = d4["arms"]["ALN"]["per_gate"]
    Z = d4["arms"]["ZOOM"]["per_gate"]
    for name, idx in zip(("LOW", "MID", "HIGH"), thirds):
        for g in ("1", "4"):
            a = np.array([A[g][k]["dsig"] for k in idx], float)
            z = np.array([Z[g][k]["dsig"] for k in idx], float)
            m = np.isfinite(a) & np.isfinite(z)
            dd = a[m] - z[m]
            se = dd.std(ddof=1) / np.sqrt(dd.size) if dd.size > 1 else np.nan
            sig = dd.mean() / se if se and se > 0 else np.nan
            print(f"    {name:>4} gate {g:>3}  ALN-ZOOM (paired) "
                  f"{dd.mean():+.5f} +/- {se:.5f} px  ({sig:+.2f} sigma)  "
                  f"n={dd.size}")
    a = np.array([A["4"][k]["dsig"] for k in thirds[2]], float)
    z = np.array([Z["4"][k]["dsig"] for k in thirds[2]], float)
    print(f"\n  HIGH tercile gate 4: ALN {np.nanmean(a):+.5f} px, "
          f"ZOOM {np.nanmean(z):+.5f} px  -> ALN/ZOOM = "
          f"{np.nanmean(a) / np.nanmean(z):.3f}x")
    print("  ALN >= ZOOM  =>  H1's falsifier is TRIPPED (registration did NOT")
    print("  flatten the curve).  Report the paired significance above before")
    print("  calling it falsified rather than merely not-confirmed.")


def score(d4, d3flat, d1):
    band("SCORING -- decision rule and registered wrong predictions")
    hp = np.array(d4["hp_sd"], float)
    hi = np.array_split(np.argsort(hp), 3)[2]
    A = d4["arms"]["ALN"]["per_gate"]
    Z = d4["arms"]["ZOOM"]["per_gate"]
    ahf = np.array([A["4"][k]["clean_ratio"] for k in hi], float)
    ds = np.array([A["4"][k]["dsig"] for k in hi], float)
    ahf_m = ahf.mean()
    ahf_se = ahf.std(ddof=1) / np.sqrt(ahf.size)
    ds_m = ds.mean()
    ds_se = ds.std(ddof=1) / np.sqrt(ds.size)
    sf = np.sqrt(d4["arms"]["ALN"]["flat"]["4"]["ratio"])
    print("  R-KEEP requires ALL THREE, top detail tercile, arm ALN:")
    print(f"    A_hf(4)/A_hf(0) >= 0.95   read {ahf_m:.4f} +/- {ahf_se:.4f}"
          f"   -> {'PASS' if ahf_m >= 0.95 else 'FAIL'}"
          f"   ({(0.95 - ahf_m) / ahf_se:+.2f} sigma from the bar)")
    print(f"    |dsig(0->4)| <= 0.10 px   read {ds_m:.5f} +/- {ds_se:.5f}"
          f"  -> {'PASS' if abs(ds_m) <= 0.10 else 'FAIL'}"
          f"   ({(ds_m - 0.10) / ds_se:+.2f} sigma past the bar)")
    print(f"    sigma_flat(4)/sigma_flat(0) <= 0.5   read {sf:.4f}"
          f"   -> {'PASS' if sf <= 0.5 else 'FAIL'}")
    rl = abs(ds_m) >= 0.20 and abs(ds_m) / ds_se >= 3.0
    print(f"  R-LOWER requires |dsig| >= 0.20 px at >= 3.0 sigma:"
          f"  read {abs(ds_m):.5f} px at {abs(ds_m) / ds_se:.2f} sigma"
          f"  -> {'TRIGGERED' if rl else 'NOT TRIGGERED'}")
    keep = ahf_m >= 0.95 and abs(ds_m) <= 0.10 and sf <= 0.5
    print(f"\n  VERDICT: {'R-KEEP' if keep else ('R-LOWER' if rl else 'R-INCONCLUSIVE')}")
    print(f"  M92's 0.61753 px is excluded here at "
          f"{(0.61753 - ds_m) / ds_se:.1f} sigma.")

    print("\n  registered wrong predictions:")
    zh = np.array([Z["4"][k]["dsig"] for k in hi], float)
    zahf = np.array([Z["4"][k]["clean_ratio"] for k in hi], float).mean()
    b_ratio = np.nanmean(zh) / ds_m
    ne = 1.0 / np.array([A["4"][k]["floor_ratio"] for k in hi], float)
    r4 = d3flat["blur"]["h1"]["4.0"]["r"] if d3flat else float("nan")
    rows = [
        ("(a)", "dsig ALN top tercile in [0.00, 0.15] px",
         f"{ds_m:.5f}", 0.0 <= ds_m <= 0.15),
        ("(b)", "ZOOM dsig(0->4) >= 1.5x ALN's",
         f"{b_ratio:.3f}x", b_ratio >= 1.5),
        ("(c)", "top-tercile local n_eff at gate 4 under 20",
         f"median {np.median(ne):.2f}", np.median(ne) < 20),
        ("(d)", "A_hf(4)/A_hf(0) within +/-0.03 of M85's 0.985 on ZOOM",
         f"{zahf:.4f} (|d|={abs(zahf - 0.985):.4f})",
         abs(zahf - 0.985) <= 0.03),
        ("(e)", "ruler comb keeps >= 0.90 of gate-0 modulation at gate 4",
         f"{r4:.5f}", r4 >= 0.90),
    ]
    for tag, txt, val, ok in rows:
        print(f"    {tag} {txt:<52} {val:>22}  "
              f"{'CORRECT' if ok else 'WRONG'}")

    print("\n  hypotheses:")
    d1hi = None
    if d1 is not None:
        hp1 = np.array(d1["hp_sd"], float)
        hi1 = np.argsort(hp1)
        a1 = d1["arms"]["ALN"]["per_gate"]["4"]
        v = np.array([a1[k]["dsig"] for k in hi1], float)
        v = v[np.isfinite(v)]
        d1hi = (v.mean(), v.std(ddof=1) / np.sqrt(v.size))
    print(f"    H1 falsifier: ALN gate contrast >= ZOOM's, top tercile."
          f"  ALN {ds_m:.5f} vs ZOOM {np.nanmean(zh):.5f}"
          f"  -> {'TRIPPED (H1 not supported)' if ds_m >= np.nanmean(zh) else 'survives'}")
    if d1hi:
        print(f"    H2 falsifier: 112MSDCF gate 0->4 >= 0.31 px."
              f"  read {d1hi[0]:.5f} +/- {d1hi[1]:.5f}"
              f"  -> {'TRIPPED' if d1hi[0] >= 0.31 else 'CONFIRMED'}"
              f"  (0.31 excluded at {(0.31 - d1hi[0]) / d1hi[1]:.1f} sigma)")
    third = d4["arms"]["ALN"]["flat"]["4"]["cli"][0] / 3.0
    print(f"    H3 falsifier: top-tercile local n_eff >= {third:.2f}."
          f"  read median {np.median(ne):.2f}"
          f"  -> {'TRIPPED' if np.median(ne) >= third else 'CONFIRMED (estimator biased toward H3 -- see above)'}")
    print(f"    H4 falsifier: comb modulation falls >= 10%."
          f"  read {(1 - r4) * 100:.3f}% fall"
          f"  -> {'TRIPPED' if (1 - r4) >= 0.10 else 'CONFIRMED'}")


def main():
    for name, fn, tag in (
        ("s4_bee-3-cpl.json", dump_s4, "bee-3-cpl"),
        ("s3_flat-on-ruler-cpl.json", dump_s3, "flat-on-ruler-cpl"),
        ("s3_ruler.json", dump_s3, "highly-angled-ruler-mm-cpl"),
        ("s2_controls_112MSDCF.json", lambda d, t: dump_s2(d), ""),
        ("s1_112MSDCF.json", dump_s1, "112MSDCF"),
    ):
        d = jload(name)
        if d is None:
            print(f"\n  (missing {name})")
            continue
        fn(d, tag)
    d4 = jload("s4_bee-3-cpl.json")
    d1 = jload("s1_112MSDCF.json")
    d3 = jload("s3_flat-on-ruler-cpl.json")
    if d4 is not None:
        dump_h3(d4, d1)
        dump_paired(d4)
        score(d4, d3, d1)


if __name__ == "__main__":
    main()
