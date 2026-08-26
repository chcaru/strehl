"""Answer BUILD-SHARP 21.6 with numbers instead of a category.

The reference arm IS the unwarped original, so the objection's PREMISE holds and
the merge does pay resamples the frame does not. The objection's CONCLUSION --
that this alone could produce 4.5% -- is a separate claim, and it is quantitative.

Rather than argue, invert it. The handicap enters as a pure multiplicative
amplitude factor R on the merge's band, so a corrected ratio is exactly
ratio / R. Sweep R and read off what it would have to be. R = 1.0 is no
handicap; R = 0.698 is BUILD-SHARP 21.5's green figure at f = 0.35; R = 0.468
is their red/blue figure. boundary.py MEASURED R at this instrument's own band.

The number that settles it is "R needed for 50%": the value the handicap would
have to take for the median detail tile to break even. If that is far below
anything the kernel can produce, the deficit is not a resampling artefact.
"""
import os, importlib, warnings, json
import numpy as np
from pathlib import Path

warnings.filterwarnings("ignore")
GALS = {"GAL": r"C:\dev\strehl-out\GALLERY-FIXED-SRGB",
        "SHIP": r"C:\dev\strehl-out\SHIP-V1"}
OUTS = {"GAL": r"C:\dev\strehl-out\V-BESTFRAME",
        "SHIP": r"C:\dev\strehl-out\V-BESTFRAME-SHIP"}
RAW = Path(r"D:\personal\macro")
GATE, FM_TOL, SNR_MIN, MIN_DETAIL = 0.80, 1.5, 3.0, 20
SWEEP = [1.000, 0.930, 0.900, 0.870, 0.800, 0.698]
# cfawarp.py: FINE band retention through the gather AT ITS REAL HALF-RESOLUTION
# CFA PLANE GEOMETRY, measured on real pixels, per subject. This SUPERSEDES the
# 0.961 that boundary.py produced by applying the kernel at full-resolution
# spacing, which was the wrong geometry and under-priced the loss ~3x.
RG = {"109MSDCF": 0.9188, "119MSDCF": 0.9264, "flower-bud-alone-cpl": 0.8669,
      "couch-fibers-cpl": 0.8773, "112MSDCF": 0.9316, "bee-1-cpl": 0.8838,
      "flowers-cpl": 0.8615, "flat-on-ruler-cpl": 0.9463}
# demosaic_spread.py: LibRaw's demosaic family spans 0.946 (LINEAR) to 1.00
# against AHD. Malvar-He-Cutler is bilinear plus a gradient term, so it cannot
# sit below LINEAR. 0.946 is therefore the WORST case for the merge.
R_DEMOSAIC = 0.946


def collect(tag):
    os.environ["VBF_GAL"] = GALS[tag]; os.environ["VBF_OUT"] = OUTS[tag]
    import paircov, peaks, curve
    importlib.reload(paircov); importlib.reload(peaks); importlib.reload(curve)
    assert str(curve.GAL) == GALS[tag], (curve.GAL, GALS[tag])
    assert str(curve.OUT) == OUTS[tag], (curve.OUT, OUTS[tag])
    out, skip = {}, {}
    for p in sorted(Path(GALS[tag]).glob("*.tiff")):
        s = p.stem
        if not (RAW / s).is_dir():
            skip[s] = "no source directory"; continue
        try:
            a = curve.arms(s, peak_min=GATE)
        except Exception as e:
            skip[s] = f"arms() raised {type(e).__name__}"; continue
        F = a["F"]
        fl = float(np.sqrt(np.nanmedian(F))) if np.any(np.isfinite(F)) else np.nan
        if not np.isfinite(fl):
            skip[s] = "floor undefined (unregistered merge)"; continue
        if not (5.0 <= fl <= 60.0):
            skip[s] = f"floor {fl:.2f} DN out of family"; continue
        real = np.isfinite(a["snr"]) & (a["snr"] >= SNR_MIN) & np.isfinite(a["ratio"])
        if int(real.sum()) < MIN_DETAIL:
            skip[s] = f"only {int(real.sum())} detail tiles"; continue
        # The CAPPED arm is section 11's headline column: it caps the merge floor at
        # the frame floor, because an N-frame average cannot be noisier than one
        # frame. Without it the two worst subjects fail the strict Fm precondition
        # and VANISH -- which is how 109MSDCF fell out of the first run of this
        # script. A skipped subject must not print like a passing one.
        Smt_c = np.maximum(a["Em"] - np.minimum(a["Fm"], F), 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            rc = np.sqrt(Smt_c) / np.sqrt(np.maximum(a["Sft"], 1e-12))
        out[s] = dict(cap=np.asarray(rc[real], float),
                      strict=np.asarray(a["ratio"][real], float),
                      ok_strict=bool(a["Fm"] <= FM_TOL * np.nanmedian(F)))
    return out, skip


def r_needed(r, frac):
    """R such that `frac` of tiles satisfy ratio/R >= 1, i.e. the (1-frac) quantile."""
    return float(np.nanquantile(r, 1.0 - frac))


def main():
    got = {t: collect(t) for t in ("GAL", "SHIP")}
    res = {t: {s: v["cap"] for s, v in got[t][0].items()} for t in got}
    for tag in ("GAL", "SHIP"):
        d = res[tag]
        n_tif = len(list(Path(GALS[tag]).glob("*.tiff")))
        sk = got[tag][1]
        print(f"\n### {tag} partition: {n_tif} rendered = {len(d)} measured + "
              f"{len(sk)} not measurable")
        for s, why in sorted(sk.items()):
            print(f"    NOT MEASURABLE  {s:<38} {why}")
        assert len(d) + len(sk) == n_tif, (len(d), len(sk), n_tif)
        nstrict = sum(1 for v in got[tag][0].values() if v["ok_strict"])
        print(f"    of the {len(d)} measured, {nstrict} also pass the strict merge-floor "
              f"precondition; all {len(d)} are shown on the CAPPED arm (an upper bound)")
        print(f"\n{'=' * 108}")
        print(f"{tag}  --  merge>=frame under a multiplicative handicap R "
              f"(corrected ratio = ratio / R), {len(d)} measurable subjects")
        print("=" * 108)
        hdr = "  ".join(f"R={r:.3f}" for r in SWEEP)
        print(f"  {'subject':<34} {'nDet':>5}  {hdr}   {'medR':>6} "
              f"{'Rneed50':>8} {'Rneed95':>8}")
        order = sorted(d, key=lambda s: np.mean(d[s] >= 1.0))
        for s in order:
            r = d[s]
            cells = "  ".join(f"{100 * np.mean(r >= R):6.1f}" for R in SWEEP)
            print(f"  {s:<34} {len(r):5d}  {cells}   {np.median(r):6.3f} "
                  f"{r_needed(r, 0.50):8.3f} {r_needed(r, 0.95):8.3f}")
        print(f"  {'-- at each subject''s OWN measured R --':<34} {'':>5}  "
              f"{'R_gather':>8} {'>=frm':>7} {'xR_demo':>8} {'>=frm':>7}")
        for s in order:
            if s not in RG:
                continue
            r = d[s]
            rw = RG[s] * R_DEMOSAIC
            print(f"  {s:<34} {len(r):5d}  {RG[s]:8.4f} {100*np.mean(r >= RG[s]):6.1f}% "
                  f"{rw:8.4f} {100*np.mean(r >= rw):6.1f}%")
        allr = np.concatenate([d[s] for s in order])
        cells = "  ".join(f"{100 * np.mean(allr >= R):6.1f}" for R in SWEEP)
        print(f"  {'ALL TILES POOLED':<34} {len(allr):5d}  {cells}   "
              f"{np.median(allr):6.3f} {r_needed(allr, 0.50):8.3f} "
              f"{r_needed(allr, 0.95):8.3f}")

    print(f"\n{'=' * 108}")
    print("THE DECIDING COMPARISON")
    print("=" * 108)
    print(f"  R measured on real pixels at the gather's REAL half-res CFA plane")
    print(f"    geometry (cfawarp.py)               R = {min(RG.values()):.4f} to "
          f"{max(RG.values()):.4f}, median {np.median(list(RG.values())):.4f}")
    print(f"  worst-case demosaic asymmetry (demosaic_spread.py)      R = {R_DEMOSAIC:.3f}")
    print(f"  combined worst case for the merge                       R = "
          f"{min(RG.values()) * R_DEMOSAIC:.4f} to {max(RG.values()) * R_DEMOSAIC:.4f}")
    print(f"  SUPERSEDED: boundary.py's full-res-spacing figure        R = 0.961")
    print(f"  R quoted by BUILD-SHARP 21.5 at f=0.35, green           R = 0.698")
    print()
    print("  ANTI-CORRELATION -- the handicap does not track the deficit:")
    for s in sorted(RG, key=lambda k: RG[k]):
        w = res["GAL"].get(s)
        if w is None:
            continue
        print(f"    {s:<24} R = {RG[s]:.4f} (handicap {1/RG[s]:.3f}x)  "
              f"raw merge>=frame {100*np.mean(w >= 1.0):5.1f}%")
    for tag in ("GAL", "SHIP"):
        for s in ("109MSDCF", "119MSDCF"):
            if s in res[tag]:
                r = res[tag][s]
                print(f"  {tag:<5} {s:<10} needs R = {r_needed(r, 0.50):.3f} for HALF its "
                      f"{len(r)} detail tiles to break even, and R = "
                      f"{r_needed(r, 0.95):.3f} for 95%")
    json.dump({t: {s: v.tolist() for s, v in res[t].items()} for t in res},
              open(r"C:\dev\strehl-out\V-BOUNDARY\corrected.json", "w"))


if __name__ == "__main__":
    main()