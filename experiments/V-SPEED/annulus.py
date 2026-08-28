# Did the fix REMOVE the ring, or merely SCATTER it?
#
# THE PROBLEM THIS EXISTS TO SOLVE. aura.py scores a halo from per-band
# MEDIANS of a radial profile. A median over an annulus is a statement about
# the annulus's centre, not about its content. Two completely different things
# drive it down:
#
#   REMOVED   the bright rim is gone; the annulus now sits at background
#             level and its pixels are tightly clustered there.
#   SCATTERED the rim is still there in the same total amount, but it is no
#             longer radially uniform -- it has broken into patches, so at any
#             given radius roughly half the annulus is bright and half is not
#             and the MEDIAN comes back to background while the DEFECT DOES
#             NOT.
#
# Only the first is a fix. The second is arguably worse than the halo it
# replaces, because a smooth rim reads as a lighting choice and a broken one
# reads as an artifact. aura.py cannot tell them apart and would report a
# large improvement for either. This file tells them apart.
#
# THE DISCRIMINATOR. Report, inside the annulus at the measured halo radius,
# THREE offsets from the far field, all in DN:
#
#   median  what aura.py sees. Says where the middle of the annulus sits.
#   mean    the TOTAL EXCESS LIGHT per pixel. Conserved by construction when
#           a fixed amount of excess is rearranged within the annulus.
#   p90     the bright tail. Rises when the excess concentrates.
#
# Removal drives all three down together. Scattering drives the MEDIAN down
# while the MEAN does not move, because the light is still there. The two
# hypotheses are therefore separated by the RATIO mean/median, which is a
# single number and is falsifiable.
#
# WHY NOT MAD ABOUT THE MEDIAN, WHICH WAS THE FIRST DESIGN. It passed its own
# commission 4/4 and it is still wrong. With a 50% scatter it read 41.0 DN for
# a coherent ring against 314.0 for a scattered one -- a clean 7.7x
# separation. But a SPARSE scatter (30% of pixels at 3.3x amplitude, same
# total light) puts the annulus median back down on the unlit background, at
# which point 70% of the deviations are near zero and the MEDIAN of those
# deviations is near zero too. MAD would have read the sparse case as clean.
# The failure mode this file exists to catch is precisely the one that drives
# the median to background, so the first design was blind in exactly the
# region it was built for. The commission below plants the sparse case for
# that reason.
#
# COMMISSIONED, and the commission is the whole point of the file: a REMOVED
# plant and a SCATTERED plant of IDENTICAL total excess must read differently.
# If they do not, this file cannot do the job it was written for and its
# output must not be quoted.

import argparse
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from aura import SUB, luma, segment, prominence  # noqa

OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")

# Half-width of the annulus, in SENSOR px, either side of the halo radius.
# Wide enough to hold enough pixels for a stable median, narrow enough not to
# average the rim together with the background it is supposed to stand out
# from. The measured halo features are 22-68 px wide, so +/-8 (a 16 px
# annulus) sits inside even the narrowest of them.
HALF = 8.0
MIN_N = 200


def dist_px(subj, scale=SUB):
    """Distance from the subject, in SENSOR px, for a mask at `scale` spacing.

    The unit conversion happens HERE and nowhere else. aura.py records what
    the alternative costs: a scale factor that was right for one caller and
    silently wrong for the other put every planted ring 4x further out than
    its label and produced a FALSE CLEAN. One boundary, one line.
    """
    return distance_transform_edt(~subj) * scale


def annulus_stats(y, dist, r_px, far=(400.0, 900.0)):
    """Median, mean and p90 offsets from the far field, all in SENSOR px.

    Three statistics, not one, because the question is not "how much halo"
    but "was the halo removed or rearranged", and no single order statistic
    answers that. See the file header.
    """
    sel = (dist >= r_px - HALF) & (dist <= r_px + HALF)
    n = int(sel.sum())
    if n < MIN_N:
        return None
    a = y[sel].astype(np.float64)
    fsel = (dist >= far[0]) & (dist <= far[1])
    if int(fsel.sum()) < MIN_N:
        # No far field (small crop): fall back to the outermost decile of
        # whatever distance range exists, and SAY SO in the result.
        cut = np.percentile(dist, 90.0)
        fsel = dist >= cut
        far_ok = False
    else:
        far_ok = True
    f = y[fsel].astype(np.float64)
    med = float(np.median(a)) - float(np.median(f))
    mean = float(a.mean()) - float(f.mean())
    p90 = float(np.percentile(a, 90.0)) - float(np.percentile(f, 90.0))
    return {
        "n": n,
        "r_px": round(r_px, 1),
        "far_dn": round(float(np.median(f)), 1),
        "median_dn": round(med, 1),
        "mean_dn": round(mean, 1),
        "p90_dn": round(p90, 1),
        # mean/median > 1 means the excess is concentrated in a minority of
        # the annulus, i.e. rearranged rather than removed. Guarded against a
        # near-zero median, which is exactly the sparse-scatter case.
        "conc": round(mean / med, 2) if abs(med) > 50.0 else None,
        "far_ok": far_ok,
    }


def _plant(n=1200, r=200.0, amp=3000.0, mode="ring", frac=0.3, seed=7):
    """Background + subject disc + an excess of KNOWN TOTAL AMOUNT at radius r.

    `mode="ring"` puts the excess down as a uniform annulus. `mode="scatter"`
    puts down THE SAME TOTAL EXCESS over THE SAME ANNULUS, but concentrated
    into a fraction `frac` of the pixels at 1/frac the amplitude, chosen at
    random. Total light added is identical to within the random draw; radial
    uniformity is not.

    `frac=0.3` is the default and is chosen deliberately: below 0.5 the
    annulus median lands on the UNLIT background, which is the case that
    makes aura.py report a large improvement for an image that lost nothing.
    A 0.5 scatter does not test that -- it moves the median the wrong way
    (measured: +5844 DN against the ring's +3001) and would let a broken
    discriminator pass.

    THE ANNULUS IS BUILT FROM THE SAME distance-from-subject TRANSFORM THE
    MEASUREMENT USES, not from distance-to-centre. Those differ by the disc
    radius, and a plant whose geometry does not match the partition geometry
    is invisible to the statistic: aura.py's commission failed exactly this
    way when a top-hat ring straddled a band boundary and a 3000 DN plant read
    0.0. Deriving both from one transform makes the mismatch impossible.
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    c = np.hypot(yy - n / 2.0, xx - n / 2.0)
    disc = c < 150.0
    y = np.full((n, n), 20000.0)
    y[disc] = 5000.0                           # dark subject
    y += rng.normal(0.0, 60.0, y.shape)        # sensor grain
    d = dist_px(disc, scale=1)
    ann = (d >= r - HALF) & (d <= r + HALF)
    if mode == "ring":
        y[ann] += amp
    elif mode == "scatter":
        pick = rng.random(y.shape) < frac
        y[ann & pick] += amp / frac
    elif mode == "clean":
        pass
    else:
        raise ValueError(mode)
    return np.clip(y, 0, 65535).astype(np.uint16), ann, disc


def commission():
    """REMOVED and SCATTERED, at identical total excess, must read apart."""
    print("=" * 76)
    print("annulus.py commission")
    print("=" * 76)
    fails = []

    n, r = 1200, 200.0
    y_ring, ann, disc = _plant(n, r, mode="ring")
    y_s30, _, _ = _plant(n, r, mode="scatter", frac=0.3)
    y_s50, _, _ = _plant(n, r, mode="scatter", frac=0.5)
    y_clean, _, _ = _plant(n, r, mode="clean")

    # 0. The plants must carry the SAME TOTAL EXCESS, or any difference
    #    between them could just be that one is brighter. Asserted, not
    #    assumed: a plant set that is not matched cannot test what this file
    #    claims to test.
    base = y_clean.astype(np.float64)
    ex = {t: float((im.astype(np.float64) - base)[ann].sum())
          for t, im in (("ring", y_ring), ("s30", y_s30), ("s50", y_s50))}
    rel = max(abs(v - ex["ring"]) / ex["ring"] for v in ex.values())
    ok = rel < 0.03
    fails += [] if ok else ["plants not matched in total excess"]
    print("[%s] 0 plants matched in total excess to %.2f%%: %s"
          % ("PASS" if ok else "FAIL", 100 * rel,
             "  ".join("%s %.4g" % (t, v) for t, v in ex.items())))

    # Measured at FULL resolution (scale=1) so the plant radius and the
    # measured radius are the same number.
    dist = dist_px(disc, scale=1)
    res = {}
    print("     %-8s %10s %10s %10s %7s" % ("plant", "median", "mean", "p90", "conc"))
    for tag, img in (("clean", y_clean), ("ring", y_ring),
                     ("s30", y_s30), ("s50", y_s50)):
        res[tag] = annulus_stats(img, dist, r, far=(300.0, 390.0))
        print("     %-8s %+10.1f %+10.1f %+10.1f %7s"
              % (tag, res[tag]["median_dn"], res[tag]["mean_dn"],
                 res[tag]["p90_dn"], res[tag]["conc"]))

    # 1. THE FAILURE MODE THIS FILE EXISTS FOR. A sparse scatter must drive
    #    the MEDIAN -- the statistic aura.py uses -- most of the way to clean,
    #    while the light is all still there. If it does not, there is no
    #    confound to detect and everything below passes vacuously.
    ok = abs(res["s30"]["median_dn"]) < 0.25 * res["ring"]["median_dn"]
    fails += [] if ok else ["sparse scatter did not fool the median; plant is weak"]
    print("[%s] 1 sparse scatter collapses the median: ring %+.1f -> s30 %+.1f DN"
          % ("PASS" if ok else "FAIL", res["ring"]["median_dn"],
             res["s30"]["median_dn"]))

    # 2. THE LOAD-BEARING ONE. The MEAN must be conserved across ALL THREE
    #    plants, because all three carry the same light. Stated as a spread
    #    across arms rather than a threshold on one, so it cannot be satisfied
    #    by tuning a single number.
    means = [res[t]["mean_dn"] for t in ("ring", "s30", "s50")]
    spread = (max(means) - min(means)) / max(means)
    ok = spread < 0.05
    fails += [] if ok else ["mean not conserved under rearrangement"]
    print("[%s] 2 mean conserved across ring/s30/s50: %s (spread %.1f%%)"
          % ("PASS" if ok else "FAIL",
             " ".join("%+.1f" % m for m in means), 100 * spread))

    # 3. NEGATIVE CONTROL. On clean ground all three statistics must read
    #    zero, or "the mean is high" would mean "this is an annulus" rather
    #    than "there is excess light in it".
    ok = all(abs(res["clean"][k]) < 100.0
             for k in ("median_dn", "mean_dn", "p90_dn"))
    fails += [] if ok else ["clean ground does not read zero"]
    print("[%s] 3 clean ground reads zero on all three (%.1f %.1f %.1f)"
          % ("PASS" if ok else "FAIL", res["clean"]["median_dn"],
             res["clean"]["mean_dn"], res["clean"]["p90_dn"]))

    # 4. THE DISCRIMINATOR ITSELF must be quiet on a coherent ring. If a
    #    genuine uniform halo already reported concentration, "conc rose"
    #    would not mean "it broke up" and the reading inverts.
    ok = abs(res["ring"]["conc"] - 1.0) < 0.1
    fails += [] if ok else ["coherent ring reads as concentrated; conc inverts"]
    print("[%s] 4 coherent ring reads conc %.2f (must be ~1.00)"
          % ("PASS" if ok else "FAIL", res["ring"]["conc"]))

    # 5. SENSITIVITY FLOOR. Report, do not assert: how small a coherent ring
    #    this still reads, so a null result later can be quoted with a bound
    #    rather than as "nothing there".
    print("     coherent-ring sensitivity floor:")
    for amp in (3000.0, 1000.0, 300.0, 100.0, 30.0):
        yy, _a, _d = _plant(n, r, amp=amp, mode="ring")
        s = annulus_stats(yy, dist, r, far=(300.0, 390.0))
        print("       plant %7.1f DN -> median %+8.1f  mean %+8.1f  (%.0f%%)"
              % (amp, s["median_dn"], s["mean_dn"],
                 100.0 * s["median_dn"] / amp))

    print("-" * 76)
    print("%d/%d PASS" % (5 - len(fails), 5))
    for f in fails:
        print("  FAIL: %s" % f)
    return 1 if fails else 0


def profile(files, maskfrom, tag):
    """Full radial profile in BOTH median and mean, for every arm side by side.

    THE REASON THIS EXISTS. The two-radius annulus comparison gave a mixed
    verdict on a real subject -- the median reversal shrank while the mean
    reversal did not -- and a mixed verdict from two sample points is not a
    result, it is a reason to look at the whole curve. An annulus at a fixed
    distance from a THIN, BRANCHING subject (tweezers, leaf veins) is not
    homogeneous the way it is around the commission's disc: it mixes the
    bright open background with the dark gaps between the arms. A mean over
    that mixture is a real number but it is not the same quantity the disc
    commission validated, so the two-point reading has to be checked against
    the shape of the whole profile before it is quoted either way.
    """
    from aura import EDGES

    ym = luma(tifffile.imread(maskfrom))[::SUB, ::SUB]
    dist = dist_px(segment(ym), scale=SUB)
    del ym
    bands = []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        m = (dist >= lo) & (dist < hi)
        if int(m.sum()) >= MIN_N:
            bands.append((0.5 * (lo + hi), m))
    print("radial profile, mask FIXED from %s, %d bands\n"
          % (pathlib.Path(maskfrom).name, len(bands)))

    cols = {}
    for f in files:
        y = luma(tifffile.imread(f))[::SUB, ::SUB]
        med = [float(np.median(y[m])) for _, m in bands]
        mean = [float(y[m].mean()) for _, m in bands]
        del y
        cols[pathlib.Path(f).stem] = (med, mean)

    names = list(cols)
    hdr = "%8s" % "mid px"
    for n in names:
        hdr += " | %10s %10s" % (n[:10] + " med", "mean")
    print(hdr)
    print("-" * len(hdr))
    for i, (mid, _m) in enumerate(bands):
        line = "%8.1f" % mid
        for n in names:
            line += " | %10.1f %10.1f" % (cols[n][0][i], cols[n][1][i])
        print(line)
    print("-" * len(hdr))

    # The quantity actually in dispute: the size of the non-monotone reversal.
    # Reported for BOTH statistics, on the SAME band pair, for every arm.
    print("\nnon-monotone reversal (peak band -> trough band), per arm:")
    print("%-16s %12s %12s %12s" % ("arm", "peak@px", "med reversal", "mean reversal"))
    for n in names:
        med, mean = cols[n]
        pm = prominence(np.array(med))
        fin = np.isfinite(pm)
        if not fin.any():
            continue
        j = int(np.argmax(np.where(fin, pm, -np.inf)))
        # Peak = the highest band strictly inside the trough's outer shoulder.
        k = int(np.argmax(np.array(med)[:j])) if j > 0 else 0
        print("%-16s %12.0f %12.1f %12.1f"
              % (n, bands[k][0], med[k] - med[j], mean[k] - mean[j]))
    print("\nBOTH falling = light removed.  med falling, mean HELD = rearranged.")

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / ("profile-%s.json" % tag)
    p.write_text(json.dumps(
        {"mids": [b[0] for b in bands],
         "arms": {n: {"median": cols[n][0], "mean": cols[n][1]} for n in names}},
        indent=1))
    print("wrote %s" % p)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--radius", type=float, default=None,
                    help="annulus radius in FULL-RESOLUTION px")
    ap.add_argument("--maskfrom", default=None,
                    help="tiff whose subject mask to use for every file; "
                         "defaults to the first file. FIXING THE MASK MATTERS: "
                         "if each arm segmented itself, a softer arm would "
                         "move its own annulus and the comparison would stop "
                         "being about the same pixels.")
    ap.add_argument("--tag", default="annulus")
    ap.add_argument("--profile", action="store_true",
                    help="print the whole radial profile in median AND mean")
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args()

    if a.commission:
        return commission()
    if not a.files:
        print("need files (or --commission)")
        return 2
    if a.profile:
        return profile(a.files, a.maskfrom or a.files[0], a.tag)
    if a.radius is None:
        print("need --radius (or --profile, or --commission)")
        return 2

    mf = a.maskfrom or a.files[0]
    ym = luma(tifffile.imread(mf))[::SUB, ::SUB]
    dist = dist_px(segment(ym), scale=SUB)
    del ym
    print("mask and annulus FIXED from %s, radius %.0f px (+/-%.0f px)\n"
          % (pathlib.Path(mf).name, a.radius, HALF))
    print("%-16s %10s %10s %10s %10s %7s"
          % ("arm", "far", "median", "mean", "p90", "conc"))
    print("-" * 70)
    rows = []
    for f in a.files:
        y = luma(tifffile.imread(f))[::SUB, ::SUB]
        s = annulus_stats(y, dist, a.radius)
        del y
        if s is None:
            print("%-16s  too few pixels in annulus" % pathlib.Path(f).stem)
            continue
        s["arm"] = pathlib.Path(f).stem
        rows.append(s)
        print("%-16s %10.1f %+10.1f %+10.1f %+10.1f %7s"
              % (s["arm"], s["far_dn"], s["median_dn"], s["mean_dn"],
                 s["p90_dn"], s["conc"]))
    print("-" * 70)
    print("median falling AND mean falling  = the ring was REMOVED")
    print("median falling, mean HELD        = the ring was SCATTERED, not fixed")
    print("(conc = mean/median; ~1.0 is a uniform annulus, >1 concentrated)")
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / ("annulus-%s.json" % a.tag)
    p.write_text(json.dumps(rows, indent=1))
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
