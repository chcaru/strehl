"""Measure the real per-aperture spectral SNR, because the bias correction rides on it.

WHY THIS EXISTS. Amendment 1 argued that the crossing estimator's 5-23% low bias is
"multiplicative and common across apertures, because it is a property of where the
roll-off disappears into the floor, not of N". The first half of that sentence is
true and the second half is false, and xspec.py's commissioning measured it to be
false: on a diffraction roll-off the bias runs -4.5% at spectral SNR 15 and -36.6% at
SNR 1. It is a property of where the roll-off disappears into the floor, and the
floor is exactly what changes with aperture when exposure is held constant.

So the bias depends on N through the SNR, and Amendment 5 registered the fix. What
neither amendment has is the NUMBER: how much does the spectral SNR actually vary
across the apertures this ladder measures? That decides three things.

  1. How large the differential bias is, and therefore whether A3's constancy test
     of f_c(N)*N is contaminated.
  2. How large the ABSOLUTE bias is at each aperture. This is the one that matters
     most and it is easy to miss: H2 and H3 both predict f_c proportional to 1/N, so
     constancy does not discriminate between them. The discriminating quantity is the
     VALUE of f_c*N. A bias of 5-36% sits directly on top of a 28.07% separation, so
     the correction does nearly all of the discriminating work.
  3. What the equalisation of Amendment 5 costs. Equalising means degrading every
     aperture to the worst one, so the worst one's SNR sets the precision of the
     whole ladder.

WHAT IS MEASURED. For each selected ROI and each aperture, at that ROI's own
best-focus frame, the radially averaged power spectrum on the GQ lattice. From it:

  floor      median power over the top fifth of the band, in the same normalisation
             m5_lib uses, where white noise of variance s^2 gives a flat s^2.
  scene(b)   mean power in band b, minus the floor. Excess over noise.
  snr(b)     scene(b) / floor. The dimensionless quantity xspec.py's bias surface is
             indexed by.

Four bands are reported rather than one, because the crossing does not happen in an
average of the spectrum, it happens where the roll-off meets the floor. "knee" is the
band containing the candidate cutoffs at the two apertures that are the measurement.

NO CUTOFF IS ESTIMATED HERE and none is quoted. This script measures the CONDITIONS
under which a cutoff will later be estimated. Keeping the two apart is deliberate:
running the estimator now, before its bias is commissioned, would put a number in the
record that A1' has not yet licensed.

Read-only with respect to D:\\personal\\macro.
"""

import argparse
import glob
import json
import os
import sys

import numpy as np

M5 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "m5-diffraction")
sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
ROOT = r"D:\personal\macro\requests\7-aperture-pairs"

EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}

# Bands in sensor cyc/px. Multiply by 1000/PITCH_UM = 195.31 for cy/mm.
#   low    below every candidate cutoff at every aperture; pure texture contrast.
#   mid    between f/18's H2 cutoff and the low band.
#   knee   contains H2 and H3 at f/18 (0.168, 0.215) and H2 at f/14 (0.216).
#          This is where the crossing actually lands, so this is the SNR that
#          governs the bias.
#   high   above every candidate cutoff at f/14 and f/18; should be close to floor.
BANDS = {
    "low": (0.040, 0.090),
    "mid": (0.100, 0.150),
    "knee": (0.150, 0.230),
    "high": (0.260, 0.330),
}

# The apertures section 2.3 declares able to discriminate. f/11 is a supporting
# point; f/14 and f/18 are the measurement. Equalisation is computed over these.
PRIMARY = ["f11", "f14", "f18"]


def cy_mm(f):
    return f * 1000.0 / L.PITCH_UM


def load_rois(w):
    path = os.path.join(OUT, f"rois-w{w}.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_maps():
    maps = {}
    for path in sorted(glob.glob(os.path.join(OUT, "focusmap-f*.json"))):
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        maps[d["aperture"]] = d
    if not maps:
        raise SystemExit("no focusmap-*.json; run focus_map.py first")
    return maps


def band_stats(f, p, floor):
    """Excess power and SNR per band. Floor is passed in so every band shares one."""
    out = {}
    for name, (lo, hi) in BANDS.items():
        sel = (f >= lo) & (f <= hi)
        if not sel.any():
            out[name] = {"scene": float("nan"), "snr": float("nan"), "nbin": 0}
            continue
        mean = float(np.mean(p[sel]))
        scene = mean - floor
        out[name] = {"mean": mean, "scene": scene,
                     "snr": scene / floor if floor > 0 else float("nan"),
                     "nbin": int(sel.sum())}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=2)
    ap.add_argument("--tile", type=int, default=128)
    ap.add_argument("--rois", type=int, default=0,
                    help="how many ROIs to survey; 0 means all")
    ap.add_argument("--eq-band", default="low", choices=list(BANDS),
                    help="band on which Amendment 5's equalisation is computed")
    args = ap.parse_args()

    doc = load_rois(args.w)
    rois = doc["rois"]
    if args.rois:
        rois = rois[:args.rois]
    maps = load_maps()
    tags = [t for t in EXACT_N if t in maps]
    ref = next(iter(maps.values()))
    rcs, ccs = np.array(ref["rcs"]), np.array(ref["ccs"])

    print(f"spectral SNR survey: {len(rois)} ROIs x {len(tags)} apertures, "
          f"GQ {doc['gq_size']}, Welch tile {args.tile}")
    print(f"GQ reach {cy_mm(0.5 / L.LATTICE_PITCH_PX['GQ']):.2f} cy/mm")
    print("bands, sensor cyc/px -> cy/mm:")
    for n, (lo, hi) in BANDS.items():
        print(f"  {n:5s} {lo:.3f}-{hi:.3f}  ->  {cy_mm(lo):6.1f}-{cy_mm(hi):6.1f} cy/mm")
    print()

    recs = []
    for i, roi in enumerate(rois):
        ir = int(np.argmin(np.abs(rcs - roi["rc"])))
        ic = int(np.argmin(np.abs(ccs - roi["cc"])))
        print(f"ROI {i} at ({roi['rc']},{roi['cc']})")
        print(f"  {'ap':>6} {'frame':>6} {'meanDN':>8} {'floor':>10} " +
              "".join(f"{'snr ' + b:>10}" for b in BANDS))
        for t in tags:
            files = sorted(glob.glob(os.path.join(
                ROOT, f"fabric-weave-{t}-sw5-cpl", "*.ARW")))
            j = int(np.array(maps[t]["best"], float)[ir, ic])
            j = min(j, len(files) - 1)
            a = L.load_active(files[j])
            patch = L.crop_lattice(a, "GQ", roi["rc"], roi["cc"], roi["gq_size"])
            f, p, c = L.spectrum(patch, "GQ", tile=args.tile, window="hann")
            top = f >= 0.8 * f[-1]
            floor = float(np.median(p[top]))
            bs = band_stats(f, p, floor)
            mean_dn = float(patch.mean())
            recs.append({"roi": i, "rc": roi["rc"], "cc": roi["cc"],
                         "aperture": t, "N": EXACT_N[t], "frame": j,
                         "file": os.path.basename(files[j]),
                         "mean_dn": mean_dn, "floor": floor, "bands": bs})
            print(f"  {t:>6} {j:6d} {mean_dn:8.1f} {floor:10.1f} " +
                  "".join(f"{bs[b]['snr']:10.2f}" for b in BANDS))
        print()

    # ---- the numbers Amendment 5 needs -----------------------------------
    print("=" * 74)
    print("SPECTRAL SNR IN THE KNEE BAND, the quantity the bias is indexed by")
    print()
    print(f"  {'ROI':>4} " + "".join(f"{t:>9}" for t in tags) +
          f"{'max/min':>10}{'primary':>10}")
    ratios, prim_ratios = [], []
    for i in range(len(rois)):
        row = {r["aperture"]: r["bands"]["knee"]["snr"]
               for r in recs if r["roi"] == i}
        vals = [row[t] for t in tags if t in row and np.isfinite(row[t])]
        pv = [row[t] for t in PRIMARY if t in row and np.isfinite(row[t])]
        rat = max(vals) / min(vals) if len(vals) > 1 and min(vals) > 0 else float("nan")
        prat = max(pv) / min(pv) if len(pv) > 1 and min(pv) > 0 else float("nan")
        ratios.append(rat)
        prim_ratios.append(prat)
        print(f"  {i:>4} " + "".join(f"{row.get(t, float('nan')):9.2f}" for t in tags) +
              f"{rat:10.2f}{prat:10.2f}")
    print()
    print(f"  across all apertures : median ratio {np.nanmedian(ratios):.2f}x")
    print(f"  across {'+'.join(PRIMARY)} : median ratio "
          f"{np.nanmedian(prim_ratios):.2f}x")
    print()
    print("  BUT THE KNEE BAND IS THE WRONG PLACE TO READ THE NUISANCE FROM. Its")
    print("  SNR is non-monotone in aperture because it mixes two effects: the")
    print("  noise floor, which is a constant-exposure artefact, and the roll-off")
    print("  moving into the band, which is the measurement. The 'low' band lies")
    print("  below every candidate cutoff and so isolates the artefact.")
    print()
    print(f"  {'ROI':>4} " + "".join(f"{t:>9}" for t in tags) + f"{'primary':>10}")
    low_prim = []
    for i in range(len(rois)):
        row = {r["aperture"]: r["bands"]["low"]["snr"]
               for r in recs if r["roi"] == i}
        pv = [row[t] for t in PRIMARY if t in row and np.isfinite(row[t])]
        prat = max(pv) / min(pv) if len(pv) > 1 and min(pv) > 0 else float("nan")
        low_prim.append(prat)
        print(f"  {i:>4} " + "".join(f"{row.get(t, float('nan')):9.0f}" for t in tags) +
              f"{prat:10.2f}")
    lr = float(np.nanmedian(low_prim))
    kr = float(np.nanmedian(prim_ratios))
    print()
    print("  READ THIS AS FOLLOWS, AND MIND THE UNITS, WHICH DIFFER BETWEEN THE TWO")
    print("  MEASUREMENTS AND ARE EASY TO CONFLATE.")
    print("    xspec.py indexed its bias surface by AMPLITUDE snr, sigma_signal over")
    print("    sigma_noise, and measured about 11.4 points of bias per e-fold of it.")
    print("    Every ratio printed above is a POWER ratio, scene power over floor")
    print("    power. Amplitude = sqrt(power), so the same slope is 5.7 points per")
    print("    e-fold of power ratio.")
    print()
    print(f"    low-band power ratio across the primary arm  {lr:6.2f}x"
          f"  -> {5.7 * np.log(lr):5.1f} points differential")
    print(f"    knee-band power ratio, contaminated, for contrast {kr:5.2f}x"
          f"  -> {5.7 * np.log(kr):5.1f} points")
    print("    The H2-H3 separation is 28.07 points.")
    print()
    print("  AND THIS IS AN EXTRAPOLATION, NOT A MEASUREMENT. xspec.py's surface")
    print("  spans amplitude SNR 1 to 15; the low band here sits at amplitude 31 to")
    print("  74, far above it, on a texture whose spectral slope was not the one")
    print("  planted. The slope is quoted to size the problem, not to correct it.")
    print("  The commissioning battery measures the bias where the ladder actually")
    print("  sits, and its numbers supersede these.")

    # ---- equalisation prescription ---------------------------------------
    print()
    print("=" * 74)
    print(f"AMENDMENT 5 EQUALISATION, computed on the '{args.eq_band}' band")
    print()
    print("  Adding white noise of variance v raises the floor by v in this")
    print("  normalisation and leaves the scene untouched, so the ratio can be")
    print("  driven down to any target below the current one, never up.")
    print()
    print("  THE BAND MATTERS AND THE OBVIOUS CHOICE IS WRONG. Equalising on the")
    print("  knee band equalises away the effect under test: f/18's knee-band SNR")
    print("  is low partly because its cutoff lies INSIDE that band, which is the")
    print("  signal, not a nuisance. Degrading f/11 and f/14 until they match it")
    print("  would be matching them to f/18's optics rather than to its noise.")
    print("  The 'low' band lies below every candidate cutoff at every aperture, so")
    print("  its SNR is texture contrast over noise floor with the roll-off")
    print("  excluded by construction -- the part of the SNR that is an artefact of")
    print("  constant exposure rather than a consequence of the optics.")
    print()
    eq = {}
    for i in range(len(rois)):
        sub = {r["aperture"]: r for r in recs if r["roi"] == i}
        pv = {t: sub[t]["bands"][args.eq_band]["snr"] for t in PRIMARY if t in sub}
        if not pv:
            continue
        target = min(pv.values())
        worst = min(pv, key=pv.get)
        print(f"  ROI {i}: target {args.eq_band}-band SNR {target:.1f}, set by {worst}")
        print(f"     {'ap':>5} {'floor':>9} {'add var':>9} {'new floor':>10} "
              f"{'x':>6} {'knee snr before':>16} {'after':>8}")
        for t in PRIMARY:
            if t not in sub:
                continue
            scene = sub[t]["bands"][args.eq_band]["scene"]
            floor = sub[t]["floor"]
            v = max(scene / target - floor, 0.0) if target > 0 else 0.0
            knee_before = sub[t]["bands"]["knee"]["snr"]
            knee_after = sub[t]["bands"]["knee"]["scene"] / (floor + v)
            eq.setdefault(str(i), {})[t] = {
                "add_var": v, "floor": floor, "scene": scene, "target": target,
                "band": args.eq_band, "knee_before": knee_before,
                "knee_after": knee_after}
            print(f"     {t:>5} {floor:9.1f} {v:9.1f} {floor + v:10.1f} "
                  f"{(floor + v) / floor:6.2f} {knee_before:16.2f} "
                  f"{knee_after:8.2f}")
        ka = [eq[str(i)][t]["knee_after"] for t in PRIMARY if t in eq.get(str(i), {})]
        if len(ka) > 1:
            print(f"     knee-band SNR ratio after equalising: "
                  f"{max(ka) / min(ka):.2f}x  (this is the RESIDUAL, and it is the")
            print(f"     roll-off difference the ladder exists to measure)")
        print()

    dest = os.path.join(OUT, f"snr-w{args.w}.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"w": args.w, "tile": args.tile, "bands": BANDS,
                   "primary": PRIMARY, "records": recs, "equalise": eq}, fh,
                  indent=2)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
