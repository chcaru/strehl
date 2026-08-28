"""halo3 -- edge-normal overshoot. Measures a halo the way a halo is defined.

WHY NOT A RADIAL PROFILE. Measured and refuted twice: halo_profile's band walk
cannot see a rim near a steep penumbra (its own header says so), and my
residual-from-trend replacement failed commissioning -- at every stiffness an
UNPLANTED clean subject produced a residual as large as a planted 3200 DN rim
(best separation 1.26x). The defect is azimuthal averaging: one radial profile
pools edges whose penumbra depth and local contrast differ by tens of thousands
of DN, and the rim is buried in that spread.

WHAT THIS DOES INSTEAD. A halo is a local overshoot at an edge: crossing out of
the subject, the background rises ABOVE its own local level before settling. So
sample along the OUTWARD NORMAL at many boundary points, and score each edge
against ITS OWN plateau. Penumbra depth cancels because it is common to the
profile and the plateau; only an excursion above the plateau scores.

The normal comes from the distance transform's gradient, so it is outward by
construction. Profiles are smoothed along s before the max is taken, and the
aggregate is a MEDIAN over edges, so neither pixel noise nor a few bright scene
features can carry the number.
"""
import argparse, glob, json, os, sys
import numpy as np, tifffile
from scipy.ndimage import (distance_transform_edt, label, gaussian_filter,
                           map_coordinates, uniform_filter1d)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "ORCH-drift-check"))
import halo_profile as H

R = 200          # px sampled outward along the normal
NPTS = 4000      # boundary points sampled
PLATEAU = (0.70, 1.00)
SMOOTH = 5
MIN_EDGE_PTS = 300
MAX_RIM_WIDTH = 150.0   # px a rim may take to fall back; a gradient takes more


def measure(y, rng=None):
    rng = rng or np.random.default_rng(0)
    ys = y[::4, ::4]
    t, subj = H.segment(ys)
    frac = float(subj.mean())
    if frac < H.MIN_SUBJ:
        return None, "no dark subject (%.1f%% of frame)" % (frac * 100)
    if float((ys > t).mean()) < 0.05:
        return None, "backdrop too small (%.1f%% of frame)" % (float((ys > t).mean()) * 100)
    big = np.repeat(np.repeat(subj, 4, 0), 4, 1)[:y.shape[0], :y.shape[1]]
    d = distance_transform_edt(~big).astype(np.float32)
    ds = gaussian_filter(d, 3.0)
    gy, gx = np.gradient(ds)
    n = np.hypot(gy, gx) + 1e-6
    gy, gx = gy / n, gx / n

    # boundary = background pixels within 2 px of the subject
    by, bx = np.nonzero((d > 0) & (d <= 2.0))
    if by.size < MIN_EDGE_PTS:
        return None, "silhouette perimeter too short (%d px)" % by.size
    # keep only points whose outward ray stays inside the frame
    s = np.arange(0, R + 1, dtype=np.float32)
    ok = ((by + gy[by, bx] * R > 1) & (by + gy[by, bx] * R < y.shape[0] - 2) &
          (bx + gx[by, bx] * R > 1) & (bx + gx[by, bx] * R < y.shape[1] - 2))
    by, bx = by[ok], bx[ok]
    if by.size < MIN_EDGE_PTS:
        return None, ("only %d boundary points have a %d px outward run inside "
                      "the frame (subject touches the edge)" % (by.size, R))
    idx = rng.choice(by.size, size=min(NPTS, by.size), replace=False)
    by, bx = by[idx], bx[idx]
    ny, nx = gy[by, bx], gx[by, bx]
    cy = by[:, None] + ny[:, None] * s[None, :]
    cx = bx[:, None] + nx[:, None] * s[None, :]
    prof = map_coordinates(y, [cy.ravel(), cx.ravel()], order=1,
                           mode="nearest").reshape(cy.shape)
    prof = uniform_filter1d(prof, SMOOTH, axis=1, mode="nearest")

    # KEEP ONLY RAYS THAT STAY IN OPEN BACKGROUND. If a ray re-enters the
    # subject or crosses another part, its samples are not background and its
    # plateau is meaningless. The distance transform along the ray must keep
    # up with s; a ray that grazes other structure falls behind.
    dr = map_coordinates(d, [cy.ravel(), cx.ravel()], order=1,
                         mode="nearest").reshape(cy.shape)
    good = np.all(dr[:, 5:] >= 0.6 * s[None, 5:], axis=1)
    if int(good.sum()) < MIN_EDGE_PTS:
        return None, ("only %d of %d normals stay in open background for %d px; "
                      "the silhouette has no clear run to measure against"
                      % (int(good.sum()), prof.shape[0], R))
    prof = prof[good]

    # AVERAGE THE ALIGNED PROFILES BEFORE TAKING ANY MAXIMUM.
    # Taking the max per-edge first is a search that cannot fail: the max of
    # noise over 135 samples is always positive, and it read HALO 7745 DN on a
    # known-clean subject. Averaging first makes noise fall as 1/sqrt(n) while
    # a rim, which sits at a consistent distance from every edge, survives.
    esf = np.median(prof, axis=0)
    a, b = int(PLATEAU[0] * R), int(PLATEAU[1] * R)
    plateau = float(np.median(esf[a:b + 1]))

    # A HALO IS A LOCAL BRIGHTENING, NOT A GLOBAL ONE.
    # Measured and refuted: scoring the excursion ABOVE THE FAR PLATEAU cannot
    # detect a rim inside a deep penumbra -- 30 px from a bee's edge the scene
    # is genuinely ~15000 DN dark, so a 3200 DN rim never clears the plateau
    # and read CLEAN -- while a broad scene gradient DOES clear it and read
    # HALO at 6000 DN. The reference was wrong in both directions.
    # The right reference is the profile's own running maximum: crossing out of
    # the subject the level must rise monotonically. A rim makes it rise and
    # then FALL BACK. That drawdown is local, so penumbra depth is irrelevant.
    run = np.maximum.accumulate(esf)
    dd = run - esf
    kt = int(np.argmax(dd))
    amp = float(dd[kt])
    kp = int(np.argmax(esf[:kt + 1])) if kt > 0 else 0
    width = float(kt - kp)
    # NOISE FLOOR OF THIS VERY STATISTIC, measured per subject, taken over the
    # plateau where no rim can live.
    floor = float(np.max(np.maximum.accumulate(esf[a:b + 1]) - esf[a:b + 1]))
    # A DECLINE STILL RUNNING WHEN THE WINDOW ENDS IS NOT A LOCAL RIM.
    # Measured: a synthetic backdrop gradient is still falling at 200 px, so
    # its drawdown only LOOKS narrow because the window truncates it. A rim
    # falls back to the background well inside the window.
    return dict(overshoot=amp, at_px=float(kp), width=width, floor=floor,
                trough_px=float(kt),
                n_edges=int(prof.shape[0]), plateau=plateau,
                esf=esf.tolist()), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("--only", default=None)
    ap.add_argument("--thresh", type=float, default=200.0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.src, "*.tif")) +
                   glob.glob(os.path.join(a.src, "*.tiff")))
    if a.only:
        files = [f for f in files if a.only in os.path.basename(f)]
    print("halo3: median over-plateau excursion along the outward edge normal.")
    print("Each edge is scored against ITS OWN plateau, so penumbra depth cancels.")
    print("UNSCORED is NOT a pass: the instrument could not look.\n")
    print("%-36s %-9s %9s %9s %7s %7s  %s" % ("subject","verdict","overshoot",
          "noisefloor","at px","edges","note"))
    print("-" * 108)
    part = {"HALO":0,"CLEAN":0,"UNSCORED":0}; out={}
    for f in files:
        s = os.path.basename(f).rsplit(".",1)[0]
        r, why = measure(H.luma(tifffile.imread(f)).astype(np.float32))
        if r is None:
            part["UNSCORED"] += 1; out[s]=dict(verdict="UNSCORED",why=why)
            print("%-36s %-9s %9s %9s %7s %7s  %s" % (s,"UNSCORED","-","-","-","-",why))
            continue
        # a reading must beat BOTH the absolute threshold and this subject's
        # own measured noise floor for the identical statistic
        # amplitude must beat the threshold AND this subject's own measured
        # noise floor; width rejects a broad scene gradient, which falls off
        # over hundreds of px rather than the tens a rim occupies.
        v = ("HALO" if (r["overshoot"] > a.thresh and
                        r["overshoot"] > 2.0 * max(r["floor"], 1.0) and
                        r["width"] <= MAX_RIM_WIDTH and
                        r["trough_px"] <= R - 30) else "CLEAN")
        part[v] += 1; r["verdict"]=v; out[s]=r
        print("%-36s %-9s %9.1f %9.1f %7.0f %7d  width %.0f px" % (
            s, v, r["overshoot"], r["floor"], r["at_px"], r["n_edges"],
            r["width"]))
    print("\nPARTITION (must sum to %d)" % len(files))
    for k in ("HALO","CLEAN","UNSCORED"): print("  %-9s %d" % (k, part[k]))
    print("  %-9s %d" % ("total", sum(part.values())))
    assert sum(part.values()) == len(files)
    if a.json: json.dump(out, open(a.json,"w"), indent=1, default=float)

if __name__ == "__main__":
    main()
