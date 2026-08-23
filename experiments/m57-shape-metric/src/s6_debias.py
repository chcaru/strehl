"""M57 S6 -- K6 / K7 against the null that killed K1.

POST-HOC.  Kill conditions PR14-PR18 are in PREREGISTRATION-2.md, committed at
a653adf BEFORE this file ran and before K6 or K7 had been evaluated on any data.

RULE 39.  The null is N1 (independent noise added to both half-merges, truth
exactly 0 px) and N2 (one half scaled, truth exactly 0 px).  The signal is the
planted 0.10 px blur.  The planted wrong answer is the claim that the fix works,
tested by requiring K6/K7 to still MOVE for the signal (PR15) -- a statistic
that reads zero for everything would pass the null and be worthless.

RULE 9.  Flat ROI of every stack first.
"""
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m57lib as K  # noqa: E402

ROOT = r"D:\personal\macro"
PAD = 32
G, RN_E = 1.14469, 1.47
PLANT_SB = 0.10
ISO = 500
THRESH = 0.02

STACKS = {
    "112MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "detail": (1671, 1373, 512, 512)}, lo=6, hi=68),
    "113MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=63),
    "foam":     dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=62),
    "109MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=22),
}
CANDS = (("K1 dsig", K.dsig), ("K7 dsig_db", K.dsig_db), ("K6 dsig_lin", K.dsig_lin))


def main():
    t0 = time.time()
    res, verdict = {}, {n: dict(n1=[], sig=[], gain=[], split=[]) for n, _ in CANDS}
    print("=" * 78)
    print("M57 S6 -- K6/K7 vs the noise null that killed K1 (PR14-PR17)")
    print(f"  threshold PR14: |value| <= {THRESH} px under N1.  Truth is 0 px.")
    print("=" * 78)

    for sname, cfg in STACKS.items():
        files = sorted(glob.glob(os.path.join(ROOT, sname, "*.ARW")))
        files = files[cfg["lo"]:cfg["hi"]]
        for rname, roi in cfg["rois"].items():
            cube = K.load_cube(files, roi, pad=PAD)
            nf = cube.shape[0]
            fine, coarse, reg = K.L1.focus_fields(cube, G, RN_E)
            ia, ib = K.splits(nf)["parity"]
            ma, nea = K.merge_subset(cube, coarse, reg, ia, pad=PAD)
            mb, _ = K.merge_subset(cube, coarse, reg, ib, pad=PAD)
            lvl = float(np.median(ma))
            s1 = float(np.sqrt(K.M.noise_var_dn(lvl, K.gain_dn_per_e(ISO),
                                                K.read_noise_e(ISO))))
            sm = s1 / np.sqrt(nea)
            key = f"{sname}/{rname}"
            rs1 = K.RingStats(ma, mb)
            rs_b = K.RingStats(K.M.blur(ma, PLANT_SB), K.M.blur(mb, PLANT_SB))
            print("\n" + "=" * 78)
            print(f"{key}   {nf} frames   n_eff {nea:.3f}   merged sigma "
                  f"{sm:.3f} DN   ({time.time()-t0:.0f}s)")
            print("=" * 78)
            r = {}

            print(f"  PR15 SIGNAL -- planted {PLANT_SB} px blur "
                  f"(truth {PLANT_SB:.3f} px)")
            print("     candidate         value px    se(jack)     err %")
            for nm, fn in CANDS:
                d = fn(rs1, rs_b)
                e = 100.0 * (d["px"] - PLANT_SB) / PLANT_SB
                print(f"     {nm:15s} {K.fmt(d['px'])}   {d['se_px']:9.2e}"
                      f"  {e:+8.2f}")
                r[f"signal_{nm}"] = dict(px=d["px"], se=d["se_px"], err=e)
                verdict[nm]["sig"].append(abs(e))

            print("  PR14 NULL N1 -- independent noise on both halves."
                  "  TRUTH IS EXACTLY 0 px.")
            print("     candidate           1x sigma      2x sigma      3x sigma")
            rng = np.random.default_rng(57_000 + abs(hash(key)) % 1000)
            pairs = {}
            for mult in (1.0, 2.0, 3.0):
                add = sm * mult
                aa = ma + rng.standard_normal(ma.shape).astype(np.float32) * add
                bb = mb + rng.standard_normal(mb.shape).astype(np.float32) * add
                pairs[mult] = K.RingStats(aa, bb)
            for nm, fn in CANDS:
                row = [fn(rs1, pairs[m])["px"] for m in (1.0, 2.0, 3.0)]
                print(f"     {nm:15s}" + "".join(K.fmt(v, 14, 5) for v in row))
                r[f"n1_{nm}"] = row
                verdict[nm]["n1"] += [abs(v) for v in row if np.isfinite(v)]

            print("  PR16 GAIN -- one half scaled by 1.30."
                  "  TRUTH IS EXACTLY 0 px of MOVE.")
            print("     candidate         move px")
            g1 = K.RingStats(ma * 1.30, mb)
            g2 = K.RingStats(K.M.blur(ma, PLANT_SB) * 1.30, K.M.blur(mb, PLANT_SB))
            for nm, fn in CANDS:
                mv = abs(fn(g1, g2)["px"] - r[f"signal_{nm}"]["px"])
                print(f"     {nm:15s} {mv:14.3e}")
                r[f"gain_{nm}"] = mv
                verdict[nm]["gain"].append(mv)

            print("  PR17 SPLIT -- split common to both configurations."
                  f"  Truth {PLANT_SB:.3f} px for every rule.")
            print("     candidate        spread px    % of signal   measurable")
            sp = {nm: [] for nm, _ in CANDS}
            for k, (ja, jb) in K.splits(nf).items():
                if k == "contiguous":
                    continue
                sa, _ = K.merge_subset(cube, coarse, reg, ja, pad=PAD)
                sb2, _ = K.merge_subset(cube, coarse, reg, jb, pad=PAD)
                q1 = K.RingStats(sa, sb2)
                q2 = K.RingStats(K.M.blur(sa, PLANT_SB), K.M.blur(sb2, PLANT_SB))
                for nm, fn in CANDS:
                    sp[nm].append(fn(q1, q2)["px"])
            for nm, _ in CANDS:
                v = np.array(sp[nm], float)
                nf_ok = int(np.isfinite(v).sum())
                s = float(np.nanmax(v) - np.nanmin(v)) if nf_ok else np.nan
                print(f"     {nm:15s} {s:12.6f}   {100*s/PLANT_SB:12.3f}"
                      f"   {nf_ok:6d}/{len(v)}")
                r[f"split_{nm}"] = dict(spread=s, n=nf_ok)
                if np.isfinite(s):
                    verdict[nm]["split"].append(100 * s / PLANT_SB)
            res[key] = r
            del cube, fine, coarse, reg

    print("\n" + "=" * 78)
    print("VERDICTS (all eight real cells; no cell held out -- PR18)")
    print("=" * 78)
    print("  candidate         PR14 worst |null|   PR15 worst err %"
          "   PR16 worst move   PR17 worst %")
    summary = {}
    for nm, _ in CANDS:
        v = verdict[nm]
        w14 = max(v["n1"]) if v["n1"] else np.nan
        w15 = max(v["sig"]) if v["sig"] else np.nan
        w16 = max(v["gain"]) if v["gain"] else np.nan
        w17 = max(v["split"]) if v["split"] else np.nan
        print(f"  {nm:15s} {w14:17.5f}   {w15:16.2f}   {w16:15.3e}"
              f"   {w17:12.3f}")
        summary[nm] = dict(pr14=w14, pr15=w15, pr16=w16, pr17=w17,
                           pr14_pass=bool(w14 <= THRESH),
                           pr15_pass=bool(w15 <= 10.0),
                           pr16_pass=bool(w16 < 1e-4),
                           pr17_pass=bool(w17 < 5.0))
    print()
    for nm, s in summary.items():
        bad = [k.upper().replace("_PASS", "") for k in
               ("pr14_pass", "pr15_pass", "pr16_pass", "pr17_pass") if not s[k]]
        print(f"  {nm:15s} -> {'PASS all four' if not bad else 'FAIL ' + ', '.join(bad)}")
    res["_summary"] = summary
    with open(os.path.join(K.OUT, "s6_debias.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/s6_debias.json  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
