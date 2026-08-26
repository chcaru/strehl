"""V-bestframe analysis. Reads the cached per-tile numbers; decodes nothing.

PRE-REGISTERED DECISION RULE (fixed before any subject was analysed):
  per tile, ratio = merge_corrected / bestframe_corrected
  FLAGGED  <=> ratio < 0.80  AND  bestframe_corrected > 2 * that image's noise
               floor at that tile's level   (the second clause stops a tile with
               no detail in ANY arm from being called a merge failure)
  H2 for a subject <=> flagged fraction materially exceeds the calibration
               subject's, on BOTH bands.

Note on bias: bestframe = max over sampled frames, and a max over N noisy
values is biased upward. That bias favours the FRAME side, i.e. it makes H2
easier to declare. Every remaining choice below is set the same way.
"""
import argparse, json
import numpy as np
from pathlib import Path
import bestframe as B

OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
RATIO_FLAG = 0.80
CONTENT_MULT = 2.0


def load(subj, tag="base"):
    z = np.load(OUT / f"{subj}__{tag}.npz", allow_pickle=False)
    return {k: z[k] for k in z.files}


def analyse(d, band):
    """band: 1 = FINE, 2 = MID."""
    mt = d["merge_tiles"]; ft = d["frame_tiles"]
    m_raw = mt[:, :, band]; m_lv = mt[:, :, 0]
    m_cor, m_fl = B.corrected(m_lv, m_raw)
    nf = ft.shape[0]
    f_cor = np.full(ft.shape[:3], np.nan); f_fl = np.full(ft.shape[:3], np.nan)
    for n in range(nf):
        c, fl = B.corrected(ft[n, :, :, 0], ft[n, :, :, band])
        f_cor[n] = c; f_fl[n] = fl
    with np.errstate(invalid="ignore"):
        best = np.nanmax(f_cor, axis=0)
        arg = np.nanargmax(np.where(np.isfinite(f_cor), f_cor, -np.inf), axis=0)
        best_raw = np.nanmax(ft[:, :, :, band], axis=0)
        best_fl = np.take_along_axis(f_fl, arg[None], 0)[0]
    ratio = np.where(best > 0, m_cor / np.maximum(best, 1e-9), np.nan)
    content = best > CONTENT_MULT * best_fl
    flagged = (ratio < RATIO_FLAG) & content
    return dict(m_raw=m_raw, m_cor=m_cor, m_fl=m_fl, best=best, best_raw=best_raw,
                best_fl=best_fl, arg=arg, ratio=ratio, content=content, flagged=flagged,
                deficit=best - m_cor)


def summarise(subj, d, band, label):
    r = analyse(d, band)
    n = r["ratio"].size
    fin = np.isfinite(r["ratio"])
    worse = fin & (r["ratio"] < 1.0)
    q = np.nanpercentile(r["ratio"][fin], [5, 25, 50, 75, 95]) if fin.any() else [np.nan]*5
    dq = np.nanpercentile(r["deficit"][fin], [50, 90, 99]) if fin.any() else [np.nan]*3
    s = dict(
        subject=subj, band=label, tiles=int(n),
        tiles_measured=int(fin.sum()), tiles_skipped=int(n - fin.sum()),
        tiles_with_content=int(r["content"].sum()),
        tiles_no_content_in_any_arm=int((~r["content"] & fin).sum()),
        frac_merge_below_bestframe=float(worse.sum() / max(fin.sum(), 1)),
        frac_flagged=float(r["flagged"].sum() / max(fin.sum(), 1)),
        n_flagged=int(r["flagged"].sum()),
        ratio_p05=float(q[0]), ratio_p25=float(q[1]), ratio_med=float(q[2]),
        ratio_p75=float(q[3]), ratio_p95=float(q[4]),
        deficit_med_DN=float(dq[0]), deficit_p90_DN=float(dq[1]), deficit_p99_DN=float(dq[2]),
        merge_cor_med_DN=float(np.nanmedian(r["m_cor"])),
        best_cor_med_DN=float(np.nanmedian(r["best"])),
        merge_raw_med_DN=float(np.nanmedian(r["m_raw"])),
        best_raw_med_DN=float(np.nanmedian(r["best_raw"])),
        frac_merge_below_bestframe_RAW=float(
            np.nanmean(r["m_raw"] < r["best_raw"])),
    )
    return s, r


def worst_tiles(r, d, k=10):
    rr = np.where(r["content"], r["ratio"], np.nan)
    fl = rr.ravel()
    order = np.argsort(np.where(np.isfinite(fl), fl, np.inf))[:k]
    names = d["frame_names"]; idx = d["frame_index"]
    out = []
    for o in order:
        i, j = np.unravel_index(o, rr.shape)
        if not np.isfinite(rr[i, j]):
            continue
        n = int(r["arg"][i, j])
        out.append(dict(ti=int(i), tj=int(j), ratio=float(r["ratio"][i, j]),
                        merge=float(r["m_cor"][i, j]), best=float(r["best"][i, j]),
                        deficit=float(r["deficit"][i, j]), frame_n=n,
                        frame_k=int(idx[n]), frame=str(names[n])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--tag", default="base")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    allout = []
    for subj in a.subjects:
        d = load(subj, a.tag)
        nfr = d["frame_tiles"].shape[0]
        print(f"\n{'='*76}\n{subj}   tag={a.tag}   {nfr} of {int(d['n_on_disk'])} frames read"
              f"   grid {B.NTY}x{B.NTX}   plant_sigma={float(d['plant_sigma'])}")
        print(f"  registration: {int(d['reg_direct'].sum())}/{nfr} placed directly, "
              f"{nfr-int(d['reg_direct'].sum())} by model;  s in "
              f"[{d['reg_used'][:,0].min():.4f},{d['reg_used'][:,0].max():.4f}];  "
              f"tiles clipped at frame edge: {int(d['oob'].sum())} tile-frames")
        for band, label in ((1, "FINE(1,2)"), (2, "MID(2.5,5)")):
            s, r = summarise(subj, d, band, label)
            allout.append(s)
            print(f"  --- {label}")
            print(f"      tiles: {s['tiles_measured']} measured, {s['tiles_skipped']} "
                  f"unmeasurable, {s['tiles_with_content']} with content, "
                  f"{s['tiles_no_content_in_any_arm']} with no detail in ANY arm")
            print(f"      merge < best frame        : {100*s['frac_merge_below_bestframe']:6.2f}% "
                  f"of measured   (raw, uncorrected: {100*s['frac_merge_below_bestframe_RAW']:6.2f}%)")
            print(f"      FLAGGED (ratio<0.8 & content): {s['n_flagged']:4d} tiles "
                  f"= {100*s['frac_flagged']:6.2f}%")
            print(f"      ratio merge/best  p05 {s['ratio_p05']:.3f}  p25 {s['ratio_p25']:.3f}  "
                  f"med {s['ratio_med']:.3f}  p75 {s['ratio_p75']:.3f}  p95 {s['ratio_p95']:.3f}")
            print(f"      median band RMS (DN)  merge {s['merge_cor_med_DN']:8.2f}   "
                  f"best frame {s['best_cor_med_DN']:8.2f}   deficit p50/p90/p99 "
                  f"{s['deficit_med_DN']:+.2f}/{s['deficit_p90_DN']:+.2f}/{s['deficit_p99_DN']:+.2f}")
            if band == 1:
                for w in worst_tiles(r, d, 5):
                    print(f"        worst tile ({w['ti']:2d},{w['tj']:2d}) ratio {w['ratio']:.3f} "
                          f"merge {w['merge']:7.2f} best {w['best']:7.2f} from k={w['frame_k']} "
                          f"{w['frame']}")
    if a.json:
        Path(a.json).write_text(json.dumps(allout, indent=1))
        print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
