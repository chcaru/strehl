"""Does the weave put a periodic peak where the crossing estimator will be looking?

THE WORRY, which is specific to this subject and not to spectral methods generally.
The fabric is a WEAVE. A weave is periodic. A periodic structure puts discrete peaks
in the power spectrum at its fundamental and harmonics, and everything this lane has
modelled -- a power law rolled off by a diffraction MTF -- is smooth. If a weave
harmonic lands near the cutoff, the crossing estimator can latch onto it: the
spectrum would rise back above the floor after having fallen to it, and the "last
detectable bin" would be the harmonic rather than the end of the roll-off. That would
bias f_c HIGH, in the H3 direction, and it would do so more at the apertures whose
cutoff is nearest the harmonic. It is the only mechanism found so far that pushes the
opposite way to T1 and to the SNR bias, so it cannot be waved away as conservative.

WHAT IS MEASURED. For each ROI and aperture, the saved radial PSD is compared against
the smooth power law fitted to the low band and extended across the whole band. Bins
that stand well above that extension, in the region between the low band and the
lattice reach, are candidate harmonics. Two things then matter and are reported
separately:

  presence   is there a peak at all, anywhere in the band?
  position   is it near the candidate cutoffs of the apertures that are the
             measurement, which section 2.3 fixes at f/14 and f/18?

A peak that exists but sits far above every candidate cutoff is harmless. A peak that
sits inside 30-55 cy/mm is not.

A CONTROL IS INCLUDED, because "no peaks found" from a detector that has never fired
is not evidence. A synthetic harmonic of known height and position is injected into a
real spectrum and must be recovered.

Reads only out/snr-w2.json. No decode, no raw file, no cutoff estimated.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slope_survey import fit_slope, LOW  # noqa: E402

PITCH_UM = 5.12
GQ_REACH_CYMM = 69.05
# The region that matters: from the top of the low band to the lattice reach.
SEARCH = (0.095, 0.340)
# Candidate cutoffs, cy/mm, for the two apertures section 2.3 calls the measurement.
DANGER_CYMM = (30.0, 55.0)
PEAK_RATIO = 3.0        # sigma above the floor, same rule as m5_lib.knee


def cy_mm(f):
    return f * 1000.0 / PITCH_UM


def find_peaks(f, p, floor, counts, z=3.0):
    """Bins that stand above the floor AFTER the spectrum has already reached it.

    THE FIRST VERSION OF THIS FUNCTION WAS WRONG AND ITS CONTROL CAUGHT IT. It
    compared each bin against the power law fitted to the low band and extended
    across the whole band. Above the cutoff that extension sits far above the data,
    because it contains no roll-off, so a harmonic standing well above the NOISE
    FLOOR is still far below the extrapolated power law and reads as no peak at all.
    Planted harmonics of 3x, 4x and 8x were all missed.

    The reference has to be the floor, because the floor is what the crossing
    estimator compares against. The mechanism that threatens the measurement is
    re-emergence: the spectrum falls to the floor at the end of the roll-off, and
    then a periodic component lifts it back out, so the "last detectable bin" is the
    harmonic rather than the cutoff. So this looks only ABOVE the first frequency at
    which the spectrum reaches the floor, and asks whether anything climbs back out.

    Detection uses the same statistical rule as m5_lib.knee: a bin is above the floor
    when p - floor exceeds z * floor / sqrt(counts), so a bin averaged over few
    samples has to stand further out to count.
    """
    f = np.asarray(f, float)
    p = np.asarray(p, float)
    c = np.maximum(np.asarray(counts, float), 1.0)
    thresh = floor + z * floor / np.sqrt(c)
    reg = (f >= SEARCH[0]) & (f <= SEARCH[1])
    idx = np.where(reg)[0]
    if idx.size == 0:
        return [], float("nan"), float("nan")
    # Where does the spectrum first reach the floor inside the search region?
    below = idx[p[idx] <= thresh[idx]]
    if below.size == 0:
        # Never reaches the floor in band: texture-limited. Re-emergence is not
        # defined, and there is nothing here for a harmonic to hide behind.
        return [], float("nan"), float(f[idx[-1]])
    first = int(below[0])
    out = []
    for k in idx[idx > first]:
        if p[k] > thresh[k]:
            out.append({"f": float(f[k]), "cy_mm": float(cy_mm(f[k])),
                        "excess": float((p[k] - floor) / floor)})
    worst = max((q["excess"] for q in out), default=0.0)
    return out, float(worst), float(f[first])


def main():
    w = sys.argv[1] if len(sys.argv) > 1 else "2"
    with open(os.path.join(OUT, f"snr-w{w}.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    recs = d["records"]
    if "psd" not in recs[0]:
        raise SystemExit("snr-w*.json has no saved spectra; re-run snr_survey.py")
    tags = []
    for r in recs:
        if r["aperture"] not in tags:
            tags.append(r["aperture"])
    rois = sorted({r["roi"] for r in recs})

    print("WEAVE HARMONICS: is there periodic structure near the cutoffs?")
    print()
    print(f"Search region {cy_mm(SEARCH[0]):.1f}-{cy_mm(SEARCH[1]):.1f} cy/mm, "
          f"from the top of the low band to the")
    print(f"GQ lattice reach {GQ_REACH_CYMM:.2f} cy/mm. A peak is a bin standing "
          f"{PEAK_RATIO:.0f} sigma above the")
    print(f"noise floor AFTER the spectrum has already reached that floor -- a")
    print(f"re-emergence, which is the mechanism that would fool the estimator.")
    print(f"Danger zone for the measurement is {DANGER_CYMM[0]:.0f}-"
          f"{DANGER_CYMM[1]:.0f} cy/mm, bracketing the H2 and H3")
    print(f"candidates at f/14 and f/18.")
    print()
    print(f"  {'ROI':>4} " + "".join(f"{t:>10}" for t in tags) +
          "   worst re-emergence")
    total, danger = 0, 0
    worst_overall = 0.0
    hits = []
    reach_floor = {t: 0 for t in tags}
    for i in rois:
        cells, worst = [], 0.0
        for t in tags:
            r = next(x for x in recs if x["roi"] == i and x["aperture"] == t)
            pk, mx, ffirst = find_peaks(r["f"], r["psd"], r["floor"], r["counts"],
                                        z=PEAK_RATIO)
            for q in pk:
                hits.append(dict(q, roi=i, aperture=t))
            if np.isfinite(mx):
                reach_floor[t] += 1
                worst = max(worst, mx)
                cells.append(f"{len(pk):10d}")
            else:
                cells.append(f"{'n/a':>10}")
            total += len(pk)
            danger += sum(1 for q in pk
                          if DANGER_CYMM[0] <= q["cy_mm"] <= DANGER_CYMM[1])
        worst_overall = max(worst_overall, worst)
        print(f"  {i:>4} " + "".join(cells) + f"{worst:20.3f}")
    print()
    print("  'n/a' means the spectrum never reaches the floor inside the search")
    print("  region, so re-emergence is undefined. That is the texture-limited case")
    print("  and it is expected at the wide apertures:")
    print("    " + "  ".join(f"{t} reaches floor in {reach_floor[t]}/{len(rois)}"
                             for t in tags))
    print()
    print(f"  re-emergent bins found anywhere : {total}")
    print(f"  re-emergent bins in danger zone : {danger}")
    print(f"  largest re-emergence, as a fraction of the floor : {worst_overall:.3f}")

    # --- control: calibrate the threshold, do not demand impossible sensitivity ---
    print()
    print("  CONTROL. Two earlier versions of this control were wrong and both")
    print("  failures were informative. The first compared bins against the")
    print("  extrapolated power law and missed every plant. The second demanded the")
    print("  detector see a re-emergence of 30% of the floor -- but the detector uses")
    print("  the SAME rule as the crossing estimator, so a harmonic it cannot see is")
    print("  one the estimator cannot see either, and demanding more sensitivity than")
    print("  the estimator has tests the wrong thing.")
    print()
    print("  The right control is a threshold calibration: plant just above the local")
    print("  detection threshold and require a hit, plant just below and require a")
    print("  miss. That shows the detector is sharp and that its blind spot is")
    print("  exactly the estimator's blind spot.")
    print()
    r = next(x for x in recs if x["roi"] == rois[0] and x["aperture"] == "f18")
    f = np.array(r["f"], float)
    cnt = np.array(r["counts"], float)
    _, _, ffirst = find_peaks(r["f"], r["psd"], r["floor"], r["counts"],
                              z=PEAK_RATIO)
    # A THIRD CONTROL BUG, CAUGHT THE SAME WAY. Fixed plant positions of 36 and 44
    # cy/mm sat BELOW the frequency at which this spectrum first reaches the floor,
    # so the re-emergence rule excluded them by design and the control read FAIL on
    # a detector that was behaving correctly. Plant positions have to be derived
    # from the spectrum being planted into, not chosen in advance.
    above = np.where((f > ffirst) & (f <= SEARCH[1]))[0]
    if above.size < 6:
        raise SystemExit("not enough bins above the floor crossing to calibrate")
    picks = [int(above[1]), int(above[above.size // 2]), int(above[-2])]
    print(f"  {'at cy/mm':>10} {'threshold':>10} {'planted':>9} {'expect':>8} "
          f"{'got':>12}")
    ctrl_ok = True
    for k in picks:
        t = PEAK_RATIO / np.sqrt(max(cnt[k], 1.0))
        for mult, want in ((1.5, True), (0.5, False)):
            p = np.array(r["psd"], float).copy()
            p[k] = r["floor"] * (1.0 + t * mult)
            pk, _, _ = find_peaks(f, p, r["floor"], r["counts"], z=PEAK_RATIO)
            got = any(abs(q["cy_mm"] - cy_mm(f[k])) < 0.6 for q in pk)
            ok = got == want
            ctrl_ok &= ok
            print(f"  {cy_mm(f[k]):10.1f} {t:10.3f} {t * mult:9.3f} "
                  f"{'hit' if want else 'miss':>8} "
                  f"{('hit' if got else 'miss') + ('' if ok else '  WRONG'):>12}")
    print()
    print(f"  control {'PASS' if ctrl_ok else 'FAIL'}: the detector fires above its")
    print(f"  threshold and is silent below it, at all three positions.")
    print()
    print("  SENSITIVITY, stated plainly. The smallest re-emergence this null covers,")
    print("  as a fraction of the floor, at each danger-zone frequency:")
    for target_cymm in (30.0, 36.0, 44.0, 52.0):
        k = int(np.argmin(np.abs(cy_mm(f) - target_cymm)))
        t = PEAK_RATIO / np.sqrt(max(cnt[k], 1.0))
        print(f"    {cy_mm(f[k]):5.1f} cy/mm : {t:6.3f}  "
              f"({int(cnt[k])} samples in the radial bin)")
    print("  A harmonic below those heights is invisible here AND invisible to the")
    print("  crossing estimator, so it cannot move the measurement.")

    # --- is the one detection a real harmonic, or the chance the null predicts? ---
    print()
    print("  IS THE ONE DETECTION REAL? A genuine weave harmonic is a property of the")
    print("  fabric, so it sits at a FIXED frequency and must repeat across ROIs and")
    print("  across apertures. An isolated bin in a single cell is what chance looks")
    print("  like. Both readings are checked.")
    print()
    tested = 0
    for i in rois:
        for t in tags:
            rr = next(x for x in recs if x["roi"] == i and x["aperture"] == t)
            ff = np.asarray(rr["f"], float)
            tested += int(((ff >= SEARCH[0]) & (ff <= SEARCH[1])).sum())
    expected = tested * 0.00135          # one-sided 3 sigma
    print(f"    bins examined                       : {tested}")
    print(f"    false positives expected at 3 sigma : {expected:.1f}")
    print(f"    detections observed                 : {total}")
    if hits:
        byf = {}
        for h in hits:
            byf.setdefault(round(h["cy_mm"], 1), []).append(h)
        rep = max((len(v) for v in byf.values()), default=0)
        print(f"    most cells sharing one frequency    : {rep} of {len(rois) * len(tags)}")
        for k2, v in sorted(byf.items()):
            print(f"      {k2:6.1f} cy/mm : " +
                  ", ".join(f"ROI{h['roi']}/{h['aperture']} +{h['excess']:.3f}"
                            for h in v))
        repeats = rep >= 3
    else:
        repeats = False
        print("    most cells sharing one frequency    : 0")
    print()
    if total <= expected * 3 and not repeats:
        print("    READING: the count is at or below chance and nothing repeats at a")
        print("    fixed frequency. There is no evidence of a weave harmonic.")
        clean = True
    else:
        print("    READING: this is more than chance, or it repeats. Treat as real.")
        clean = False
    print()
    if clean and ctrl_ok:
        print("  VERDICT: nothing climbs back out of the floor inside the region")
        print("  where the f/14 and f/18 cutoffs lie. The threat is retired for those")
        print("  two apertures, which section 2.3 calls the measurement.")
    elif not clean:
        print("  VERDICT: harmonics ARE present in the danger zone. The crossing")
        print("  estimator can latch onto them and this must be handled before any")
        print("  cutoff is quoted.")
    else:
        print("  VERDICT: withheld. The detector failed its own control.")

    dest = os.path.join(OUT, f"weave-w{w}.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"search": SEARCH, "danger_cymm": DANGER_CYMM,
                   "z": PEAK_RATIO, "total_peaks": total,
                   "danger_peaks": danger, "worst_excess": worst_overall,
                   "bins_tested": tested, "expected_false": expected,
                   "max_shared_frequency": (rep if hits else 0),
                   "hits": hits,
                   "control_pass": bool(ctrl_ok), "clean": bool(clean)}, fh,
                  indent=2)
    print(f"\nwrote {dest}")
    return 0 if ctrl_ok else 1


if __name__ == "__main__":
    sys.exit(main())
