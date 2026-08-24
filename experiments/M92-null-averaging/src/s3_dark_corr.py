"""M92 S3 -- the crux: are the per-ROI estimates actually independent?

S2's injection is synthetic and i.i.d. per ROI BY CONSTRUCTION, so its rbar is a
control on the correlation estimator, not a measurement of the sensor.  This
script injects noise that carries real sensor-coordinate structure and measures
whether the per-ROI estimates couple.

ARMS
  A2   real dark-frame noise.  Per draw, four DISTINCT darks give
       na = (d_k - d_l)/sqrt(2) and nb = (d_m - d_n)/sqrt(2), each a
       FULL-PLANE field cropped at every ROI's true sensor coordinates and
       rescaled by ONE global robust (MAD) sd to mult*sm_i.  Four distinct
       darks keep the two halves' injections independent, so the null's truth
       stays exactly 0 px; a shared dark would give the noise cross-power a
       non-zero mean and turn the null into a pedestal.
       Differencing removes the fixed pattern deliberately: FPN is identical in
       every frame, so in the real comparison (gate 0.50 vs gate 0.99 on the
       SAME frames) it is common to both configurations and cancels in the log
       ratio.  What does not cancel is temporally varying row/column banding,
       and that is what a difference of two darks keeps.
  OV   the SAME field cropped at the OVERLAP grid (stride 128, 75% shared).
       Positive control: overlapping ROIs share noise, so rbar must RISE and
       alpha must FALL relative to the disjoint grid.  If it does not, the
       instrument is not measuring what it is claimed to measure.
  SYN  a synthetic full-plane Gaussian cropped the same two ways.  It isolates
       the geometry with a known mechanism: disjoint crops are independent by
       construction, overlapping crops share 75% of their samples.

RULE 20.  What would make this fail: A2-disjoint returning rbar >= 0.10 with a
bootstrap interval clear of zero.  That is material common mode and it implies a
floor at Null(1)*sqrt(rbar) that no number of ROIs beats.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import m57lib as K    # noqa: E402

R = int(os.environ.get("M92_R", "128"))
MULT = 2.0
E_M82 = 0.1754
TAG = os.environ.get("M92_TAG", "")
NBOOT = int(os.environ.get("M92_NBOOT", "1500"))
ONLY = [s for s in os.environ.get("M92_STACKS", "").split(",") if s]

# EXIF-verified dark sets (src/s0_darks.py).  Matched on ISO where an exact
# match exists; 109MSDCF is ISO 160 and the nearest available dark is ISO 200.
DARKS = {"112MSDCF": ("125MSDCF", 500), "109MSDCF": ("123MSDCF", 200),
         "wrapped-text-1": ("118MSDCF", 100)}


def load_dark_planes(name, log):
    import glob
    fs = sorted(glob.glob(os.path.join(M92.DARKS, name, "*.ARW")))
    out = []
    for f in fs:
        out.append(M92.quad_plane(f))
    a = np.stack(out)
    log(f"    {name}: {a.shape[0]} darks, plane {a.shape[1]}x{a.shape[2]}, "
        f"mean {a.mean():+.4f} DN")
    return a


def robust_sd(a):
    """MAD-based, because darks carry hot pixels (M22) and a plain sd would be
    set by them rather than by the pattern being probed."""
    m = np.median(a)
    return float(1.4826 * np.median(np.abs(a - m)))


def crops(field, rows, keep):
    return [field[r["y"]:r["y"] + M92.ROI_N, r["x"]:r["x"] + M92.ROI_N]
            for r in (rows[k] for k in keep)]


def run_arm(cells, rows, keep, iso, field_fn, log, label, seed=92):
    rs1 = [K.RingStats(*cells[k]) for k in keep]
    sms = [M92.merged_sigma(rows[k]["level"], iso, rows[k]["n_eff"])[0]
           for k in keep]
    px = np.full((len(keep), R), np.nan)
    sl = np.full((len(keep), R), np.nan)
    js = np.full((len(keep), R), np.nan)
    for r in range(R):
        fa, fb = field_fn(r)
        ca, cb = crops(fa, rows, keep), crops(fb, rows, keep)
        for j, k in enumerate(keep):
            ma, mb = cells[k]
            add = MULT * sms[j]
            d = K.dsig(rs1[j], K.RingStats(ma + ca[j] * add, mb + cb[j] * add))
            px[j, r], sl[j, r], js[j, r] = d["px"], d["slope"], d["se_px"]
    return px, sl, js


def main():
    t0 = time.time()
    meta = json.load(open(os.path.join(M92.OUT, "s1_cells.json")))
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    out = {}
    log("=" * 78)
    log(f"M92 S3 -- cross-ROI correlation under REAL sensor noise.  R = {R}, "
        f"level x{MULT:.0f}")
    log("  rbar >= 0.10 with an interval clear of 0 = material common mode,")
    log("  implying a floor at Null(1)*sqrt(rbar) that no N beats.")
    log("=" * 78)

    for stack in (ONLY or list(M92.STACKS)):
        iso = meta[stack]["iso"]
        dname, diso = DARKS[stack]
        log("\n" + "=" * 78)
        log(f"{stack}  (EXIF ISO {iso})   darks: {dname} (ISO {diso})")
        log("=" * 78)
        darks = load_dark_planes(dname, log)
        nd = darks.shape[0]
        s_global = robust_sd(darks[0] - darks[1]) / np.sqrt(2.0)
        log(f"    global robust sd of (d_k - d_l)/sqrt(2) = {s_global:.4f} DN "
            f"(plain sd {float((darks[0]-darks[1]).std()/np.sqrt(2)):.4f} DN --"
            f" the gap is hot pixels)")
        sres = {"dark_set": dname, "dark_iso": diso, "arms": {}}

        for kind in ("disjoint", "overlap"):
            z = np.load(os.path.join(M92.CACHE, f"cells_{stack}_{kind}.npz"))
            g = f"{M92.GATE_SHIPPED:.2f}"
            n = sum(1 for kk in z.files if kk.endswith(f"_{g}_a"))
            cells = [(z[f"{i:02d}_{g}_a"], z[f"{i:02d}_{g}_b"]) for i in range(n)]
            rows = meta[stack][kind]
            keep = []
            for k, (ma, mb) in enumerate(cells):
                d = K.dsig(K.RingStats(ma, mb),
                           K.RingStats(K.M.blur(ma, 0.10), K.M.blur(mb, 0.10)))
                if np.isfinite(d["px"]):
                    keep.append(k)
            idxmap = M92.subset_index(len(keep), seed=92)
            log(f"\n  --- {kind} grid, {len(keep)}/{len(cells)} ROIs retained ---")
            log("      origins: " + ", ".join(
                f"({rows[k]['x']},{rows[k]['y']})" for k in keep))

            rng_d = np.random.default_rng(555)
            picks = [rng_d.choice(nd, 4, replace=False) for _ in range(R)]

            def dark_field(r, picks=picks):
                a, b, c, e = picks[r]
                return ((darks[a] - darks[b]) / (np.sqrt(2.0) * s_global),
                        (darks[c] - darks[e]) / (np.sqrt(2.0) * s_global))

            rng_s = np.random.default_rng(777)
            shp = darks.shape[1:]

            def syn_field(r, rng_s=rng_s, shp=shp):
                return (rng_s.standard_normal(shp).astype(np.float32),
                        rng_s.standard_normal(shp).astype(np.float32))

            for tag, fn in (("A2 dark", dark_field), ("SYN plane", syn_field)):
                lbl = f"{tag} / {kind}"
                px, sl, js = run_arm(cells, rows, keep, iso, fn, log, lbl)
                sres["arms"][lbl] = S2A.analyse(px, sl, js, idxmap, log, lbl)
                cw = M92.pair_corr_pairwise(px)
                cb = M92.corr_boot(px, nboot=800)
                log(f"    PAIRWISE-COMPLETE rbar = {cw['rbar']:+.5f} over "
                    f"{cw['n_pair']} pairs ({cw.get('n_skipped', 0)} skipped);"
                    f" draw-bootstrap 95% CI [{cb['lo']:+.5f}, {cb['hi']:+.5f}]")
                sres["arms"][lbl]["corr_pairwise"] = cw
                sres["arms"][lbl]["corr_boot"] = cb
                np.savez_compressed(os.path.join(
                    M92.CACHE, f"d3_{stack}_{tag.split()[0]}_{kind}.npz"),
                    px=px, slope=sl, jack=js, keep=np.array(keep))
                log(f"    ({time.time()-t0:.0f}s)")

        # ---- the positive control's acceptance test ----------------------
        log("\n  --- OV positive control (overlap must be WORSE) ---")
        for tag in ("A2 dark", "SYN plane"):
            dj = sres["arms"][f"{tag} / disjoint"]
            ov = sres["arms"][f"{tag} / overlap"]
            ok = (ov["alpha"] < dj["alpha"]) and (ov["corr"]["rbar"] > dj["corr"]["rbar"])
            log(f"    {tag:10s}  alpha {dj['alpha']:.4f} (disjoint) vs "
                f"{ov['alpha']:.4f} (overlap)   rbar {dj['corr']['rbar']:+.4f} vs "
                f"{ov['corr']['rbar']:+.4f}   -> {'PASS' if ok else 'FAIL'}")
            sres["arms"][f"OV control {tag}"] = dict(
                alpha_disjoint=dj["alpha"], alpha_overlap=ov["alpha"],
                rbar_disjoint=dj["corr"]["rbar"], rbar_overlap=ov["corr"]["rbar"],
                passed=bool(ok))
        del darks
        out[stack] = sres
        with open(os.path.join(M92.OUT, f"s3_dark_corr{TAG}.json"), "w") as fh:
            json.dump(out, fh, indent=2, default=float)

    with open(os.path.join(M92.OUT, f"s3_dark_corr{TAG}.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote out/s3_dark_corr{TAG}.{{json,log}}  ({time.time()-t0:.0f}s)")


import s2_null_averaging as S2A  # noqa: E402  (reuse the identical analyser)

if __name__ == "__main__":
    S2A.NBOOT = NBOOT
    S2A.R = R
    main()
