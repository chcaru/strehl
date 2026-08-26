"""Per-tile "never worse than the best single frame", on model-free arms.

FRAME ARM   S_f(tile) = max over probed pairs of Cov(b_k, b_k+1).
            Directly measured signal power. Sensor noise is independent between
            two exposures so it has zero expectation in the cross term; the only
            positive bias is the best-of-441-shifts pick, measured at C3 = 0.0099
            of Var on pure noise. Divided by SUBPIX to undo the half-pixel
            alignment penalty measured at C4, which inflates the frame arm and is
            therefore the conservative direction for an H1 verdict.

MERGE ARM   S_m(tile) = max(E_m - N_m(level), 0). N_m is calibrated ON TILES THE
            FRAME ARM SAYS ARE EMPTY: if no frame carries signal there, the merge
            cannot either, so whatever the merge shows in those tiles is its own
            noise. p90 rather than the median, which over-states merge noise and
            under-states merge signal -- again conservative for H1.

Every discretionary choice above is set to favour H2. If H1 survives that, it
survives.
"""
import argparse
import numpy as np
from pathlib import Path

OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
SUBPIX = 0.8126      # C4: Cov/Var under a half-pixel residual
BIAS = 0.0099        # C3: best-of-441-shifts Cov/Var on pure noise
CONTENT = 5.0        # a tile has frame content if S_f > CONTENT * BIAS * Var_f
RATIO_FLAG = 0.80    # merge is "worse" if it holds <80% of the frame's signal
NLEV = 8


def load(subj, band="fine"):
    z = np.load(OUT / f"{subj}__paircov_{band}.npz")
    S = z["S"]; N = z["N"]                      # (npair, ny, nx) POWER
    V = S + N                                   # total band power of frame k
    Sf = np.nanmax(S, axis=0) / SUBPIX          # frame signal power, best pair
    kstar = np.nanargmax(np.where(np.isnan(S), -np.inf, S), axis=0)
    Vf = np.nanmedian(V, axis=0)
    Em = z["merge_tiles"][:, :, 1] ** 2 if band == "fine" else z["merge_tiles"][:, :, 2] ** 2
    lev = z["merge_tiles"][:, :, 0]
    return dict(Sf=Sf, Vf=Vf, Em=Em, lev=lev, kstar=kstar, anchors=z["anchors"],
                n_on_disk=int(z["n_on_disk"]), S=S, V=V, ye=z["ye"], xe=z["xe"],
                nsig=np.nansum(S / np.maximum(V, 1e-9) > CONTENT * BIAS, axis=0))


def merge_floor(Em, lev, empty):
    """Merge noise vs level, calibrated only where the frame arm found nothing."""
    edges = np.nanpercentile(lev, np.linspace(0, 100, NLEV + 1))
    edges = np.unique(edges)
    idx = np.clip(np.digitize(lev, edges[1:-1]), 0, len(edges) - 2)
    Nm = np.zeros_like(Em)
    for b in range(len(edges) - 1):
        sel = (idx == b)
        use = sel & empty & np.isfinite(Em)
        Nm[sel] = np.nanpercentile(Em[use], 90) if use.sum() >= 8 else \
            (np.nanpercentile(Em[sel & np.isfinite(Em)], 10) if sel.sum() else 0.0)
    return Nm


def analyse(subj, band="fine", verbose=True):
    d = load(subj, band)
    ok = np.isfinite(d["Sf"]) & np.isfinite(d["Em"])
    content = ok & (d["Sf"] > CONTENT * BIAS * d["Vf"])
    empty = ok & ~content
    Nm = merge_floor(d["Em"], d["lev"], empty)
    Sm = np.maximum(d["Em"] - Nm, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.sqrt(Sm) / np.sqrt(np.maximum(d["Sf"], 1e-12))   # AMPLITUDE ratio
    worse = content & (ratio < RATIO_FLAG)
    ntot = d["Sf"].size
    r = dict(subj=subj, band=band, ntot=ntot, nmeas=int(ok.sum()),
             nskip=int((~ok).sum()), ncontent=int(content.sum()),
             nempty=int(empty.sum()), nworse=int(worse.sum()),
             ratio=ratio, content=content, worse=worse, Sm=Sm, Sf=d["Sf"],
             Nm=Nm, d=d)
    if verbose:
        rc = ratio[content]
        print(f"\n=== {subj}  band={band}  {d['n_on_disk']} frames on disk, "
              f"{2*len(d['anchors'])} READ ({len(d['anchors'])} adjacent pairs at "
              f"k={list(map(int, d['anchors']))})")
        print(f"  tiles {ntot} = measured {int(ok.sum())} + unmeasurable {int((~ok).sum())}"
              f"   [measured = content {int(content.sum())} + no-frame-signal "
              f"{int(empty.sum())}]")
        print(f"  frame signal RMS  (best pair) med {np.sqrt(np.nanmedian(d['Sf'][ok])):8.2f} DN"
              f"   content-tiles med {np.sqrt(np.nanmedian(d['Sf'][content])) if content.any() else float('nan'):8.2f} DN")
        print(f"  frame TOTAL  RMS             med {np.sqrt(np.nanmedian(d['Vf'][ok])):8.2f} DN"
              f"   -> signal is {np.nanmedian(d['Sf'][ok]/d['Vf'][ok])*100:5.1f}% of frame band power")
        print(f"  merge  RMS   raw            med {np.sqrt(np.nanmedian(d['Em'][ok])):8.2f} DN"
              f"   merge noise floor med {np.sqrt(np.nanmedian(Nm[ok])):8.2f} DN"
              f"   merge signal med {np.sqrt(np.nanmedian(Sm[ok])):8.2f} DN")
        if content.any():
            q = np.nanpercentile(rc, [5, 25, 50, 75, 95])
            print(f"  MERGE/BESTFRAME amplitude ratio on {int(content.sum())} content tiles:"
                  f"  p05 {q[0]:.3f}  p25 {q[1]:.3f}  MED {q[2]:.3f}  p75 {q[3]:.3f}  p95 {q[4]:.3f}")
            print(f"  merge < best frame          : {np.mean(rc < 1.0)*100:5.2f}% of content tiles")
            print(f"  merge < {RATIO_FLAG:.2f} x best frame  : "
                  f"{np.mean(rc < RATIO_FLAG)*100:5.2f}%  ({int(worse.sum())} tiles)  <-- H2 candidates")
            print(f"  merge > best frame          : {np.mean(rc > 1.0)*100:5.2f}%"
                  f"   (median gain x{np.nanmedian(rc[rc>1.0]) if (rc>1.0).any() else float('nan'):.2f})")
        if worse.any():
            ij = np.argwhere(worse)
            order = np.argsort(ratio[worse])
            print("  worst content tiles (i=row, j=col):")
            for n in order[:8]:
                i, j = ij[n]
                print(f"    ({i:2d},{j:2d}) ratio {ratio[i,j]:.3f}  merge {np.sqrt(Sm[i,j]):7.2f} "
                      f"vs frame {np.sqrt(d['Sf'][i,j]):7.2f} DN  bestpair k="
                      f"{int(d['anchors'][d['kstar'][i,j]])}  level {d['lev'][i,j]:7.0f}")
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--band", default="fine")
    a = ap.parse_args()
    for s in a.subjects:
        analyse(s, a.band)
