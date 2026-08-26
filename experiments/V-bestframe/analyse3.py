"""Per-tile "never worse than the best single frame", with a MEASURED noise floor.

Both arms are floor-corrected using floors that were measured, not modelled:

  FRAME floor   C5 (fpn.py): covariance at EXACTLY ZERO SHIFT between frames 60
                apart, where focus breathing has displaced the scene by a median
                86 px. Scene content cannot survive that; sensor fixed pattern
                sits still and does. Per tile, so it tracks level.
  MERGE floor   median merge band rms over the tiles the FRAME arm independently
                says are empty. If no frame holds signal there the merge cannot
                either, so what the merge shows there is its own floor.

Detection threshold is calibrated on tiles that are KNOWN empty a priori -- the
blown-out white seamless backdrop of the control subject bee-1-cpl -- not on the
subject under test. MULT is the p99 of S_f/FPN over those tiles, so the
false-positive rate of "this tile has frame content" is 1% by construction.
"""
import argparse
import numpy as np
from pathlib import Path

OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
SUBPIX = 0.8126
RATIO_FLAG = 0.80
DISP_MIN = 20.0          # px of scene displacement required for a clean FPN read


def fpn_of(subj):
    g = sorted(OUT.glob(f"{subj}__fpn_k*.npz"))
    if not g:
        return None
    z = np.load(g[0])
    F = np.where(z["disp"] >= DISP_MIN, np.maximum(z["Z"], 0.0), np.nan)
    med = np.nanmedian(F)
    return np.where(np.isfinite(F), F, med)


def load(subj):
    z = np.load(OUT / f"{subj}__paircov_fine.npz")
    S = z["S"]
    Sf = np.nanmax(S, 0) / SUBPIX
    kbest = np.nanargmax(np.where(np.isnan(S), -np.inf, S), 0)
    Em = z["merge_tiles"][:, :, 1] ** 2
    return Sf, Em, z["merge_tiles"][:, :, 0], kbest, z["anchors"], int(z["n_on_disk"]), z


def calibrate(ctrl="bee-1-cpl", lev_pct=97.0, merge_max=12.0):
    """MULT from tiles that are empty by inspection, on the CONTROL subject only."""
    Sf, Em, lev, _, _, _, _ = load(ctrl)
    F = fpn_of(ctrl)
    known = (lev > np.percentile(lev, lev_pct)) & (np.sqrt(Em) < merge_max) & np.isfinite(F)
    r = (Sf / np.maximum(F, 1e-9))[known]
    return float(np.percentile(r, 99)), int(known.sum()), r


def analyse(subj, mult, verbose=True):
    Sf, Em, lev, kbest, anchors, ndisk, z = load(subj)
    F = fpn_of(subj)
    if F is None:
        return None
    ok = np.isfinite(Sf) & np.isfinite(Em) & np.isfinite(F)
    content = ok & (Sf > mult * F)
    empty = ok & ~content
    Fm = float(np.nanmedian(Em[empty])) if empty.sum() >= 8 else float(np.nanpercentile(Em[ok], 5))
    Sft = np.maximum(Sf - F, 0.0)
    Smt = np.maximum(Em - Fm, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.sqrt(Smt) / np.sqrt(np.maximum(Sft, 1e-12))
    worse = content & (ratio < RATIO_FLAG)
    r = dict(subj=subj, ntot=Sf.size, nok=int(ok.sum()), ncontent=int(content.sum()),
             nempty=int(empty.sum()), nworse=int(worse.sum()), ratio=ratio,
             content=content, worse=worse, Sft=Sft, Smt=Smt, F=F, Fm=Fm,
             kbest=kbest, anchors=anchors, ndisk=ndisk, lev=lev, Sf=Sf, Em=Em, z=z)
    if verbose:
        print(f"\n=== {subj}   {ndisk} frames on disk, {2*len(anchors)} READ "
              f"({len(anchors)} adjacent pairs)   MULT={mult:.3f}")
        print(f"    tiles {Sf.size} = measured {int(ok.sum())} + unmeasurable {int((~ok).sum())}")
        print(f"    frame fixed-pattern floor (C5, measured)  med {np.sqrt(np.nanmedian(F)):8.2f} DN")
        print(f"    merge floor (on frame-empty tiles)            {np.sqrt(Fm):8.2f} DN")
        print(f"    TILES WITH FRAME CONTENT above floor      {int(content.sum()):d}/{int(ok.sum())} "
              f"= {100*content.sum()/max(ok.sum(),1):5.1f}%     "
              f"[no frame content: {int(empty.sum())} = {100*empty.sum()/max(ok.sum(),1):.1f}%]")
        if content.any():
            rc = ratio[content]
            qq = np.nanpercentile(rc, [5, 25, 50, 75, 95])
            print(f"    on content tiles: best-frame detail med "
                  f"{np.sqrt(np.nanmedian(Sft[content])):8.2f} DN   merge detail med "
                  f"{np.sqrt(np.nanmedian(Smt[content])):8.2f} DN")
            print(f"    MERGE/BESTFRAME amplitude ratio  p05 {qq[0]:.3f}  p25 {qq[1]:.3f}  "
                  f"MED {qq[2]:.3f}  p75 {qq[3]:.3f}  p95 {qq[4]:.3f}")
            print(f"    merge >= best frame : {100*np.mean(rc >= 1.0):5.1f}% of content tiles")
            print(f"    merge <  0.80x      : {100*np.mean(rc < RATIO_FLAG):5.1f}%  "
                  f"({int(worse.sum())} tiles)   <-- H2 candidates")
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    a = ap.parse_args()
    mult, n, rr = calibrate()
    print(f"CALIBRATION on bee-1-cpl known-empty white backdrop: {n} tiles, "
          f"S_f/FPN  med {np.median(rr):.3f}  p90 {np.percentile(rr,90):.3f}  "
          f"p99 {np.percentile(rr,99):.3f}  max {rr.max():.3f}   -> MULT={mult:.3f}")
    for s in a.subjects:
        analyse(s, mult)
