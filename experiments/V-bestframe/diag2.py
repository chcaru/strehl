"""Distributions before thresholds. Do not guess a cut, look at the data.

Specifically: the pair-covariance estimator counts FIXED-PATTERN content (PRNU,
demosaic maze, hot pixels) as signal, because two exposures one focus step apart
share it exactly. bee-1-cpl's blown-out white backdrop is a region with provably
no scene detail, so whatever the frame arm reads there IS that floor. Measure it.
"""
import numpy as np
from pathlib import Path
OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
P = [1, 5, 10, 25, 50, 75, 90, 95, 99]


def q(a, lbl, unit="DN"):
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    print(f"    {lbl:<34}" + "  ".join(f"p{p:02d} {np.percentile(a,p):8.2f}" for p in P))


for subj in ("flowers-cpl", "bee-1-cpl"):
    z = np.load(OUT / f"{subj}__paircov_fine.npz")
    S, N = z["S"], z["N"]; V = S + N
    Sf = np.nanmax(S, 0); Vf = np.nanmedian(V, 0)
    Em = z["merge_tiles"][:, :, 1] ** 2
    lev = z["merge_tiles"][:, :, 0]
    print(f"\n=== {subj}  ({S.shape[0]} pairs, {S.shape[1]}x{S.shape[2]} tiles)")
    q(np.sqrt(Sf), "frame SIGNAL rms (max over pairs)")
    q(np.sqrt(np.nanmedian(S, 0)), "frame SIGNAL rms (median pair)")
    q(np.sqrt(Vf), "frame TOTAL rms (median pair)")
    q(np.sqrt(Em), "MERGE rms")
    q(lev, "merge tile level")
    q(np.sqrt(Sf) / np.maximum(np.sqrt(Em), 1e-9), "frameSignal / mergeRaw  (ratio)", "x")

    # the floor: brightest tiles of bee-1 are the blown white backdrop
    hi = lev > np.percentile(lev, 90)
    print(f"    -- {hi.sum()} brightest-decile tiles (level>{np.percentile(lev,90):.0f}): "
          f"frame signal rms med {np.sqrt(np.nanmedian(Sf[hi])):.2f} DN, "
          f"merge rms med {np.sqrt(np.nanmedian(Em[hi])):.2f} DN")
    lo = np.sqrt(Sf) < np.percentile(np.sqrt(Sf), 10)
    print(f"    -- bottom-decile frame-signal tiles: frame {np.sqrt(np.nanmedian(Sf[lo])):.2f} DN, "
          f"merge {np.sqrt(np.nanmedian(Em[lo])):.2f} DN")
    # merge vs frame-signal, binned by frame signal
    print("    -- merge rms vs frame-signal rms, binned:")
    edges = np.percentile(np.sqrt(Sf), [0, 20, 40, 60, 80, 90, 95, 100])
    fsr = np.sqrt(Sf)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (fsr >= a) & (fsr < b + (b == edges[-1]))
        if m.sum():
            print(f"       frameSig {a:7.1f}-{b:7.1f} DN  n={m.sum():3d}  "
                  f"merge med {np.sqrt(np.nanmedian(Em[m])):8.2f} DN  "
                  f"ratio merge/frameSig med {np.nanmedian(np.sqrt(Em[m])/fsr[m]):6.3f}")
