r"""Commission vc_ca.py BEFORE it scores anything. Five arms, per PREREG-v6ca.md
section 6. Reports a detection floor in ppm AND in sensels.

The arm that matters most is BLUR-ONLY: old and new masters come from different
builds, so if equal blur on all channels moves the CA statistic, I cannot
separate a CA finding from the build-difference confound.
"""
import numpy as np, tifffile, sys, json
from scipy.ndimage import map_coordinates, gaussian_filter
import vc_ca

OLD = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\%s.tiff"
CAP = 260          # deterministic site cap, for runtime


def plant_radial(img, ch, eps, centre):
    """planted(p) = original(centre + (p-centre)/(1+eps)); feature at r moves to r(1+eps)."""
    H, W = img.shape[:2]
    cy, cx = centre
    src = img[:, :, ch].astype(np.float32)
    out = img.copy()
    step = 512
    for y0 in range(0, H, step):
        y1 = min(y0 + step, H)
        Y, X = np.mgrid[y0:y1, 0:W].astype(np.float32)
        ys = cy + (Y - cy) / (1.0 + eps)
        xs = cx + (X - cx) / (1.0 + eps)
        out[y0:y1, :, ch] = np.clip(
            map_coordinates(src, [ys, xs], order=3, mode="nearest"), 0, 65535
        ).astype(np.uint16)
    return out


def run(subject):
    print("=" * 96)
    print("COMMISSION  subject = %s" % subject)
    print("=" * 96)
    img = vc_ca.load(OLD % subject)
    H, W = img.shape[:2]
    centre = (H / 2.0, W / 2.0)
    S = vc_ca.sites(img[:, :, 1], centre)
    print("qualifying sites found: %d  (floors: grad>=%.0f DN, coh>=%.2f, |n.rhat|>=%.2f, r>=%.0f%% rmax)"
          % (len(S), vc_ca.GRAD_FLOOR, vc_ca.COH_MIN, vc_ca.ALIGN_MIN, 100*vc_ca.R_MIN_FRAC))
    if len(S) < vc_ca.MIN_SITES:
        print("  UNSCORED -- picker correctly refuses this subject")
        return None
    S = S[::max(1, len(S)//CAP)][:CAP]
    print("using %d sites (deterministic stride)" % len(S))

    base = vc_ca.summarise(vc_ca.measure(img, centre, S))
    print("\nbaseline  ppmR=%+8.1f (mad %5.1f)   ppmB=%+8.1f   n_used=%d"
          % (base["ppmR"], base["ppmR_mad"], base["ppmB"], base["n_used"]))

    rows = []
    # ARM 1 NULL -- determinism
    b2 = vc_ca.summarise(vc_ca.measure(img, centre, S))
    ok = abs(b2["ppmR"] - base["ppmR"]) < 1e-9
    rows.append(("NULL       re-measure, no change", "delta 0.000 ppm",
                 "%+.6f ppm" % (b2["ppmR"] - base["ppmR"]), ok))

    # ARM 2 ZERO-PLANT -- isolates resampling bias from the plant path
    z = vc_ca.summarise(vc_ca.measure(plant_radial(img, 0, 0.0, centre), centre, S))
    dz = z["ppmR"] - base["ppmR"]
    ok = abs(dz) < 40.0
    rows.append(("ZERO-PLANT resample R by 0 ppm", "|delta| < 40 ppm",
                 "%+.1f ppm" % dz, ok))

    # ARMS 3/4 POSITIVE and SIGN
    for eps_ppm in (+500.0, -500.0):
        p = vc_ca.summarise(vc_ca.measure(
            plant_radial(img, 0, eps_ppm * 1e-6, centre), centre, S))
        d = p["ppmR"] - base["ppmR"]
        ok = abs(d - eps_ppm) <= max(0.20 * abs(eps_ppm), 40.0)
        tag = "POSITIVE  " if eps_ppm > 0 else "SIGN      "
        rows.append(("%s plant R %+.0f ppm" % (tag, eps_ppm),
                     "recovers %+.0f +/-20%%" % eps_ppm, "%+.1f ppm" % d, ok))

    # ARM 5 BLUR-ONLY -- the confound control
    bl = img.copy()
    for c in range(3):
        bl[:, :, c] = gaussian_filter(img[:, :, c].astype(np.float32), 1.2).astype(np.uint16)
    b = vc_ca.summarise(vc_ca.measure(bl, centre, S))
    db = b["ppmR"] - base["ppmR"]
    ok = abs(db) < 60.0
    rows.append(("BLUR-ONLY  equal blur all channels", "|delta| < 60 ppm (no CA)",
                 "%+.1f ppm" % db, ok))

    print()
    bad = 0
    for name, want, got, ok in rows:
        print("  %-38s want %-26s got %-16s %s" % (name, want, got, "ok" if ok else "*** FAIL ***"))
        if not ok: bad += 1

    # FLOOR sweep
    print("\n  detection floor sweep (planted -> recovered):")
    floor_ppm = None
    for a in (1000.0, 500.0, 200.0, 100.0, 50.0, 25.0):
        p = vc_ca.summarise(vc_ca.measure(
            plant_radial(img, 0, a * 1e-6, centre), centre, S))
        d = p["ppmR"] - base["ppmR"]
        good = abs(d - a) <= max(0.25 * a, 25.0)
        print("     %+7.0f ppm -> %+8.1f ppm  (%.3f sensel at r=2000)  %s"
              % (a, d, a * 1e-6 * 2000, "ok" if good else "below floor"))
        if good: floor_ppm = a
    print("\n  DETECTION FLOOR: %s" %
          ("%.0f ppm  =  %.3f sensel at r=2000, %.3f at r=4000"
           % (floor_ppm, floor_ppm*1e-6*2000, floor_ppm*1e-6*4000) if floor_ppm else "NOT ESTABLISHED"))
    print("\n  COMMISSION %s  (%d/%d arms)" %
          ("PASSED" if bad == 0 else "FAILED", len(rows)-bad, len(rows)))
    return bad == 0


if __name__ == "__main__":
    subs = sys.argv[1:] or ["dry-erase-marker-head-cpl"]
    allok = True
    for s in subs:
        r = run(s)
        allok = allok and bool(r)
    print("\nOVERALL: %s" % ("PASSED" if allok else "FAILED"))
    sys.exit(0 if allok else 1)
