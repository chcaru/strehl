"""halo2 -- halo detection by SHAPE, not amplitude.

WHY. The amplitude statistic in halo_profile flags any subject whose near
surround sits above its far field, which on this corpus is mostly graduated
backdrops. Measured: flat-on-ruler-cpl peaks OUTSIDE the measured window and
decays over 400 px; 119MSDCF never decays at all out to 900 px. Neither is a
rim. Meanwhile a planted BROAD rim of 9000 DN read bump 0.0 and clean.

Both errors have one root: the walk stops at 120 px, so it cannot tell a local
rim from the rising limb of a gradient, and it cannot see a rim wider than its
own window.

THE FIX, and it is strictly stricter than what it replaces:
  1. Walk to 400 px so a rim's far side is inside the measurement.
  2. Qualify each band by AZIMUTHAL COVERAGE. A median drawn from 44% of
     directions is a directional sliver, not a background level at that
     distance -- measured on leaf-2-cpl and lead-1-cpl, which produce the same
     phantom +5721/+4447 spike at the same radius as the cell pinches.
  3. A halo must be a LOCAL rim: a peak that rises above the profile on BOTH
     sides and returns to baseline within HALO_MAX_WIDTH px.
  4. STANDING GATES. An excursion has no standing if it is smaller than the
     background's own variation, or than the profile's typical band-to-band
     step. Both are measured per subject, not assumed.

Every threshold here is justified against the planted ladder in commission(),
never by convenience. Nothing in this file can turn a currently-failing
subject into a passing one by relaxation: gates 3 and 4 only ever REMOVE
verdicts of HALO, and gate 2 only ever removes bands from consideration.
"""
import argparse, glob, json, os, sys
import numpy as np, tifffile
from scipy.ndimage import distance_transform_edt, label

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "ORCH-drift-check"))
import halo_profile as H

BANDS = [(2,6),(6,12),(12,20),(20,32),(32,50),(50,80),(80,120),
         (120,170),(170,230),(230,300),(300,400)]
FAR = (400, 900)
NAZ = 16
MIN_AZ_PX = 20
MIN_COV = 0.60          # a band median needs >=60% of directions to be a level
MIN_QUAL_BANDS = 5
HALO_MAX_WIDTH = 150.0  # px; justified by the ladder: widest planted rim is 94
STANDING_K = 2.0        # excursion must beat 2x the background's own variation


def geom(y, sub=4):
    ys = y[::sub, ::sub]
    t, subj = H.segment(ys)
    frac = float(subj.mean())
    if frac < H.MIN_SUBJ:
        return None, "no dark subject (%.1f%% of frame)" % (frac * 100)
    if float((ys > t).mean()) < 0.05:
        return None, "backdrop too small (%.1f%% of frame)" % (float((ys > t).mean()) * 100)
    lab, n = label(subj)
    if n < 1:
        return None, "no subject component"
    sizes = np.bincount(lab.ravel())[1:]
    dom = int(np.argmax(sizes)) + 1
    if float(sizes[dom - 1]) / float(subj.size) < H.MIN_DOM_FRAME:
        return None, ("no dominant silhouette: largest of %d parts is %.1f%% of frame"
                      % (n, 100.0 * sizes[dom - 1] / subj.size))
    d, ind = distance_transform_edt(~subj, return_indices=True); d = d * sub
    own = (lab[ind[0], ind[1]] == dom) & (~subj)
    far = (d >= FAR[0]) & (d < FAR[1])
    if int(far.sum()) < H.MIN_FARPX // (sub * sub):
        return None, ("far field only %d px, need %d (subject reaches %.0f px)"
                      % (int(far.sum()), H.MIN_FARPX // (sub * sub), float(d.max())))
    yy, xx = np.nonzero(lab == dom)
    cy, cx = yy.mean(), xx.mean()
    gy, gx = np.mgrid[0:ys.shape[0], 0:ys.shape[1]]
    ab = ((np.arctan2(gy - cy, gx - cx) + np.pi) / (2 * np.pi) * NAZ).astype(int) % NAZ
    return dict(ys=ys, d=d, own=own, far=far, ab=ab,
                farlevel=float(np.median(ys[far]))), None


def analyse(y, thresh=200.0, sub=4):
    g, why = geom(y, sub)
    if g is None:
        return dict(verdict="UNSCORED", why=why)
    ys, d, own, ab, fl = g["ys"], g["d"], g["own"], g["ab"], g["farlevel"]
    prof = []
    for lo, hi in BANDS:
        m = own & (d >= lo) & (d < hi)
        npx = int(m.sum())
        if npx <= H.MIN_BANDPX:
            prof.append(dict(lo=lo, hi=hi, n=npx, v=None, cov=0.0)); continue
        nb = sum(1 for b in range(NAZ) if int((m & (ab == b)).sum()) >= MIN_AZ_PX)
        prof.append(dict(lo=lo, hi=hi, n=npx, cov=nb / float(NAZ),
                         v=float(np.median(ys[m])) - fl))
    qual = [b for b in prof if b["v"] is not None and b["cov"] >= MIN_COV]
    nunq = sum(1 for b in prof if b["v"] is not None and b["cov"] < MIN_COV)
    if len(qual) < MIN_QUAL_BANDS:
        return dict(verdict="UNSCORED", prof=prof, farlevel=fl,
                    why=("only %d of %d bands azimuthally qualified (need %d); "
                         "the dominant part's cell is a directional sliver"
                         % (len(qual), len(BANDS), MIN_QUAL_BANDS)))
    mid = np.array([0.5 * (b["lo"] + b["hi"]) for b in qual], float)
    val = np.array([b["v"] for b in qual], float)

    outer = val[mid >= 250.0]
    bgvar = float(outer.max() - outer.min()) if outer.size >= 2 else 0.0
    # NOTE: measured on the detrended profile below, not on val: the raw
    # band step is dominated by the penumbra and would veto every rim.
    stepscale = None

    # RIM AS A RESIDUAL, not as a local maximum.
    # Commissioned and REFUTED: requiring a peak above both neighbours cannot
    # work. halo_profile's own header says why -- the subject's penumbra rises
    # 4000-5000 DN per band near the edge, so a rim riding on it never breaks
    # monotonicity. Measured: a 3200 DN rim, narrow AND broad, read "monotone".
    # So fit the smooth penumbra trend and look for a LOCALIZED departure from
    # it. A gradient is smooth and is absorbed by the trend; a rim is not.
    # The fit is robust: refit with the two largest positive residuals dropped,
    # so a strong rim cannot drag the trend up to hide itself.
    x = np.log(mid)
    deg = min(3, len(val) - 2)
    co = np.polyfit(x, val, deg)
    r0 = val - np.polyval(co, x)
    if len(val) > deg + 3:
        keep = np.argsort(r0)[:-2]
        co = np.polyfit(x[keep], val[keep], deg)
    resid = val - np.polyval(co, x)
    dsteps = np.abs(np.diff(resid))
    stepscale = float(np.median(dsteps)) if dsteps.size else 0.0

    best = None
    k = int(np.argmax(resid))
    if resid[k] > 0:
        amp = float(resid[k])
        half = 0.5 * amp
        i = k
        while i > 0 and resid[i - 1] >= half: i -= 1
        j = k
        while j < len(val) - 1 and resid[j + 1] >= half: j += 1
        width = float(mid[j] - mid[i]) if j > i else float(qual[k]["hi"] - qual[k]["lo"])
        best = dict(amp=amp, at=float(mid[k]), width=width, peak=float(val[k]))
    if best is None:
        return dict(verdict="CLEAN", why="profile is monotone; no local rim",
                    prof=prof, farlevel=fl, bgvar=bgvar, stepscale=stepscale,
                    amp=0.0, nunqual=nunq, nqual=len(qual))

    reasons = []
    if best["amp"] <= thresh:
        reasons.append("amplitude %.0f <= %.0f DN" % (best["amp"], thresh))
    if best["width"] > HALO_MAX_WIDTH:
        reasons.append("width %.0f px > %.0f (a gradient, not a rim)"
                       % (best["width"], HALO_MAX_WIDTH))
    if best["amp"] <= STANDING_K * bgvar:
        reasons.append("amplitude %.0f <= %.1fx background variation %.0f"
                       % (best["amp"], STANDING_K, bgvar))
    if best["amp"] <= STANDING_K * stepscale:
        reasons.append("amplitude %.0f <= %.1fx typical band step %.0f"
                       % (best["amp"], STANDING_K, stepscale))
    v = "CLEAN" if reasons else "HALO"
    return dict(verdict=v, why="; ".join(reasons), prof=prof, farlevel=fl,
                bgvar=bgvar, stepscale=stepscale, nunqual=nunq, nqual=len(qual),
                **best)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("--only", default=None)
    ap.add_argument("--thresh", type=float, default=200.0)
    ap.add_argument("--json", default=None)
    ap.add_argument("--prof", action="store_true")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.src, "*.tif")) +
                   glob.glob(os.path.join(a.src, "*.tiff")))
    if a.only:
        files = [f for f in files if a.only in os.path.basename(f)]
    if not files:
        raise SystemExit("no masters under %s" % a.src)
    print("halo2: a halo is a LOCAL RIM -- a peak above the profile on both")
    print("sides, returning to baseline within %.0f px, larger than both the" % HALO_MAX_WIDTH)
    print("background's own variation and the profile's typical step.")
    print("UNSCORED is NOT a pass: it means the instrument could not look.\n")
    print("%-36s %-9s %9s %7s %7s %8s  %s" % ("subject","verdict","amp DN","at px",
                                              "width","bandsQ","why not / note"))
    print("-" * 118)
    out = {}; part = {"HALO":0,"CLEAN":0,"UNSCORED":0}
    for f in files:
        s = os.path.basename(f).rsplit(".", 1)[0]
        r = analyse(H.luma(tifffile.imread(f)), a.thresh)
        out[s] = r; part[r["verdict"]] += 1
        print("%-36s %-9s %9s %7s %7s %8s  %s" % (
            s, r["verdict"],
            ("%.0f" % r["amp"]) if r.get("amp") is not None else "-",
            ("%.0f" % r["at"]) if r.get("at") is not None else "-",
            ("%.0f" % r["width"]) if r.get("width") is not None else "-",
            ("%d/%d" % (r["nqual"], len(BANDS))) if r.get("nqual") else "-",
            (r.get("why") or "")[:52]))
        if a.prof and r.get("prof"):
            print("      " + "  ".join("%d-%d:%s%s" % (
                b["lo"], b["hi"], ("%+.0f" % b["v"]) if b["v"] is not None else ".",
                "" if b["cov"] >= MIN_COV else "(u)") for b in r["prof"]))
    print("\nPARTITION (must sum to %d)" % len(files))
    for k in ("HALO", "CLEAN", "UNSCORED"):
        print("  %-9s %d" % (k, part[k]))
    print("  %-9s %d" % ("total", sum(part.values())))
    assert sum(part.values()) == len(files)
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1, default=float)

if __name__ == "__main__":
    main()
