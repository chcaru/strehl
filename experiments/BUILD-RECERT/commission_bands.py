"""BUILD-RECERT: commission the band pairing before any verdict is taken from it.

A gate only ever tested with defects passes trivially. This project has already
been burned by a statistic bounded below by zero that could never charge for the
artifact it was built to catch, so the planted-IMPROVEMENT arms below are as
required as the planted-defect ones.

ARMS
  A  NULL           identical pixels        -> every band reads HELD. Without
                    this, "nothing moved" is not evidence: a frozen probe reads
                    exactly like a clean result.
  B  DEGRADATION    narrow blur (<=6px)     -> caught in the bands it ACTS in
                    (grain, struct) and never scored CLEANER in the band it
                    cannot reach (mottle). A 3 px blur cannot move a 21-61 px
                    band, so requiring it to would test my assertion, not the
                    metric.
  B2 DEGRADATION    wide blur (~17-33px)    -> caught in `mottle` too. Without
                    this the band all six convicted subjects were convicted in
                    would never have been shown to respond to a defect at all.
  C  IMPROVEMENT    denoise, planted IN     -> reads CLEANER. Structure is
                    THE BAND UNDER TEST        bit-identical between the arms by
                    construction; only band-confined noise differs. A metric that
                    cannot score this as an improvement is not measuring
                    cleanliness, and one that scores it as a BLUR_TRADE is
                    actively perverse.
  D  MONOTONICITY   blur ladder             -> structure falls monotonically. A
                    metric that saturates, or scores heavier blur BETTER, is the
                    perverse mode; one degradation point cannot detect it.
  E  NON-REWARD     heavier vs lighter blur -> never ranked CLEANER. The explicit
                    guard against "wins the noise table by being blurred".
  F  INVARIANCE     blur vs denoise across  -> the two `paid` populations must be
                    24 crops on 6 subjects     DISJOINT with PAID_MAX between
                    them. PAID_MAX is this harness's ONE absolute threshold and
                    arm F is what it owes: here a statistic earns an absolute
                    threshold only by being commissioned subject-invariant.
  G  REFUSAL        degenerate crops        -> REFUSED, never HELD.

TWO THINGS THAT KEEP THE REFUSALS HONEST
  * Every (site, band) cell is PASS, FAIL or REFUSED and the three sum to the
    cells examined. A refused cell is not a passed cell.
  * Each arm must clear MIN_TESTED genuinely-tested cells. Refusal is the right
    answer on a crop with no measurable noise floor or no structure above it,
    but an arm that refused EVERYTHING would report no failures and mean
    nothing -- a gate nothing can reach certifies everything.

Run: python commission_bands.py     Exit 0 only if every arm passes.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recertlib import (BANDS, NOISE_PEAK, PAID_MAX, boxblur, classify,  # noqa: E402
                       display_crop, measure_crop)

ARMS = Path(r"C:\dev\strehl-out\V-NOISE2\119\arms")
MANIFEST = Path(r"C:\dev\strehl-out\DELIVER-V5\vs-the-field\manifest-119MSDCF.json")
SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
# Subjects for arm F, chosen to span the corpus rather than to agree: a crushed
# backdrop, two clean flat fields, the banding-prone one, and a chroma subject.
F_SUBJECTS = ["119MSDCF", "coffee-bean", "bee-1-cpl", "tweezers-cpl",
              "dry-erase-marker-head-cpl", "lead-1-cpl"]
F_CROPS = [(1200, 1200), (2400, 3600), (3600, 2000), (1600, 4800)]
MIN_TESTED = 3
RNG = np.random.default_rng(20260827)

TALLY = defaultdict(lambda: {"PASS": 0, "FAIL": 0, "REFUSED": 0})


def record(arm, outcome):
    TALLY[arm][outcome] += 1


def blur_rgb(d, radius, passes):
    o = d.astype(np.float64).copy()
    for ch in range(o.shape[2]):
        p = o[..., ch]
        for _ in range(passes):
            p = boxblur(p, radius)
        o[..., ch] = p
    return o


def plant_band_noise(disp, band, factor=3.0):
    """Return (noisy, clean, landed). Adds noise CONFINED TO `band`.

    WHY BAND-CONFINED, AND WHY THIS WAS A COMMISSIONING BUG THE FIRST TIME.
    The first version planted white Gaussian noise and required every band to
    score its removal as an improvement. Three cells failed, and the metric was
    right and the plant was wrong: white noise inside a 21-61 px band is averaged
    away almost completely, so removing it moved the mottle floor by 0.01%. It is
    the same error as demanding a 3 px blur be caught in a 21-61 px band. AN
    IMPROVEMENT PLANT MUST LIVE IN THE BAND IT IS TESTING, or it tests nothing
    there.

    `landed` is not decoration. A plant that did not raise the floor leaves the
    cell UNTESTED, and an untested cell that reads green is the failure this
    whole file exists to prevent.
    """
    fn = BANDS[band][0]
    base_floor = measure_crop(disp)[band]["floor"]
    w = RNG.normal(0.0, 1.0, size=disp.shape).astype(np.float64)
    r = np.stack([fn(w[..., c]) for c in range(w.shape[2])], axis=-1)
    unit = 1.4826 * float(np.median(np.abs(r - np.median(r))))
    if unit <= 1e-12 or base_floor <= 1e-12:
        return disp, disp, False
    noisy = disp + (r * (base_floor * (factor - 1.0) / unit)).astype(np.float32)
    return noisy, disp, bool(measure_crop(noisy)[band]["floor"] >= 1.5 * base_floor)


def show(arm, band, c, outcome, why):
    d = lambda v, f: (f % v) if v is not None else "     -"  # noqa: E731
    print(f"  {arm:9s}{band:7s} d_floor {d(c['d_floor'], '%+.5f')} "
          f"d_struct {d(c['d_peak'], '%+.5f')} paid {d(c['paid'], '%.3f')}"
          f"  {outcome:7s} {c['verdict']}  [{why}]")


def main():
    for p in (MANIFEST, SHIP, ARMS):
        if not p.exists():
            print(f"REFUSE: missing {p}")
            return 2
    fails = []
    print("band noise-peak ratios (p99.5 of a PURE-NOISE band residual, in units of its own")
    print("floor -- the part of `peak` that is noise and must not be counted as structure):")
    for b, v in NOISE_PEAK.items():
        print(f"    {b:7s} {v:.4f}")
    man = json.loads(MANIFEST.read_text())
    arr = tifffile.imread(str(ARMS / "strehl-A.tiff")).astype(np.float32)
    print(f"\narms A-E on {ARMS / 'strehl-A.tiff'} (LINEAR arm; sRGB curve applied as display)\n")

    for site in man["sites"]:
        f = site["fits"]["strehl"]
        disp = display_crop(arr, site["y"], site["x"], f["shift"], f["gain"],
                            f["offset"], site["exposure"], already_srgb=False)
        base = measure_crop(disp)
        print(f"--- site {site['label']}  y={site['y']} x={site['x']} ---")
        for b, s in base.items():
            note = ""
            if s["degenerate"]:
                note = "  DEGENERATE FLOOR (%.1f%% constant)" % (s["const_frac"] * 100)
            elif not s["structure_detectable"]:
                note = "  NO STRUCTURE ABOVE FLOOR"
            print(f"    {b:7s} {s['px']:>8s} {s['cyc_px'][0]:.3f}-{s['cyc_px'][1]:.3f}cyc/px"
                  f"  floor {s['floor']:8.4f}  peak {s['peak']:8.4f}"
                  f"  structure {s['structure']:8.4f}"
                  f"{'' if s['sharpness_admissible'] else '  [noise-only]'}{note}")

        narrow = measure_crop(blur_rgb(disp, 1, 2))
        wide = measure_crop(blur_rgb(disp, 8, 2))

        for b in BANDS:
            adm = BANDS[b][3]
            if base[b]["degenerate"]:
                c = classify(base[b], narrow[b])
                ok = c["refused"]
                record("G refusal", "PASS" if ok else "FAIL")
                if not ok:
                    fails.append(f"G/refusal/{site['label']}/{b}: degenerate floor classified "
                                 f"'{c['verdict']}' instead of REFUSED")
                print(f"  G refusal{b:7s} {'PASS' if ok else 'FAIL':7s} refused, not passed "
                      f"(floor {base[b]['floor']:.2e}, {base[b]['const_frac'] * 100:.1f}% constant)")
                continue

            c = classify(base[b], measure_crop(disp.copy())[b])
            out = "REFUSED" if c["refused"] else ("PASS" if c["verdict"].startswith("HELD") else "FAIL")
            record("A null", out)
            if out == "FAIL":
                fails.append(f"A/null/{site['label']}/{b}: {c['verdict']}")
            show("A null", b, c, out, "identical pixels must read HELD")

            c = classify(base[b], narrow[b])
            acts = b in ("grain", "struct")
            if c["refused"]:
                out, why = "REFUSED", "refused before a verdict could form"
            elif acts:
                out = "PASS" if (c["d_peak"] < -0.02 and not c["verdict"].startswith("CLEANER")) else "FAIL"
                why = "acts here: structure must fall and must not be scored CLEANER"
            else:
                out = "PASS" if not c["verdict"].startswith("CLEANER") else "FAIL"
                why = "cannot reach this band: must merely never be scored CLEANER"
            record("B blur-n", out)
            if out == "FAIL":
                fails.append(f"B/narrowblur/{site['label']}/{b}: {c['verdict']}")
            show("B blur-n", b, c, out, why)

            c = classify(base[b], wide[b])
            if c["refused"]:
                out, why = "REFUSED", "refused before a verdict could form"
            else:
                out = "PASS" if (c["d_peak"] < -0.02 and not c["verdict"].startswith("CLEANER")) else "FAIL"
                why = "wide blur must be caught in every band it reaches"
            record("B2 blur-w", out)
            if out == "FAIL":
                fails.append(f"B2/wideblur/{site['label']}/{b}: {c['verdict']}")
            show("B2 blur-w", b, c, out, why)

            noisy, clean, landed = plant_band_noise(disp, b)
            c = classify(measure_crop(noisy)[b], measure_crop(clean)[b])
            want = "CLEANER" if adm else "QUIETER"
            if not landed:
                out, why = "REFUSED", "plant did not land: UNTESTED, not passed"
            elif c["refused"]:
                out, why = "REFUSED", "refused before a verdict could form"
            else:
                out = "PASS" if c["verdict"].startswith(want) else "FAIL"
                why = f"must read {want}"
            record("C denoise", out)
            if out == "FAIL":
                fails.append(f"C/denoise/{site['label']}/{b}: {c['verdict']}")
            show("C denoise", b, c, out, why)

        if not base["struct"]["degenerate"] and base["struct"]["structure_detectable"]:
            amps = [base["struct"]["structure"]] + [
                measure_crop(blur_rgb(disp, 1, n))["struct"]["structure"] for n in (1, 2, 3, 4)]
            mono = all(amps[i + 1] < amps[i] for i in range(len(amps) - 1))
            record("D ladder", "PASS" if mono else "FAIL")
            if not mono:
                fails.append(f"D/ladder/{site['label']}: {['%.3f' % p for p in amps]}")
            print(f"  D ladder struct  structure {' -> '.join('%.3f' % p for p in amps)}"
                  f"  {'PASS' if mono else 'FAIL'}  [must fall monotonically with blur]")
            c = classify(measure_crop(blur_rgb(disp, 1, 1))["struct"],
                         measure_crop(blur_rgb(disp, 1, 3))["struct"])
            out = "REFUSED" if c["refused"] else (
                "PASS" if not c["verdict"].startswith("CLEANER") else "FAIL")
            record("E non-reward", out)
            if out == "FAIL":
                fails.append(f"E/nonreward/{site['label']}: heavier blur scored {c['verdict']}")
            show("E nonrew", "struct", c, out, "heavier blur must never be ranked CLEANER")
        print()

    del arr
    print("--- F: is PAID_MAX subject-invariant? blur vs denoise, 6 subjects x 4 crops ---")
    blur_paid, den_paid, n_unlanded, n_ref_f = [], [], 0, 0
    for subj in F_SUBJECTS:
        tif = SHIP / f"{subj}--SHIP-V4.tiff"
        if not tif.exists():
            fails.append(f"F/missing master {tif.name}")
            continue
        a = tifffile.imread(str(tif))
        for (y, x) in F_CROPS:
            # Masters are --srgb: the curve is already baked in, so do not re-encode.
            d = display_crop(a, y, x, (0, 0), (1, 1, 1), (0, 0, 0), 1.0, already_srgb=True)
            bs = measure_crop(d)["struct"]
            cb_ = classify(bs, measure_crop(blur_rgb(d, 1, 2))["struct"])
            noisy, clean, landed = plant_band_noise(d, "struct")
            if not landed:
                n_unlanded += 1
                record("F invariance", "REFUSED")
                continue
            cd_ = classify(measure_crop(noisy)["struct"], measure_crop(clean)["struct"])
            if cb_["refused"] or cd_["refused"]:
                n_ref_f += 1
                record("F invariance", "REFUSED")
                continue
            record("F invariance", "PASS")
            if cb_["paid"] is not None:
                blur_paid.append(cb_["paid"])
            if cd_["paid"] is not None:
                den_paid.append(cd_["paid"])
        del a
    print(f"  excluded: {n_unlanded} plant-did-not-land, {n_ref_f} refused "
          f"(no structure above floor / degenerate) -- UNTESTED, not passed")
    if blur_paid and den_paid:
        lo_b, hi_d = min(blur_paid), max(den_paid)
        disjoint = hi_d < PAID_MAX < lo_b
        print(f"  planted BLUR    paid: n={len(blur_paid)} min {lo_b:.3f} max {max(blur_paid):.3f}")
        print(f"  planted DENOISE paid: n={len(den_paid)} min {min(den_paid):.3f} max {hi_d:.3f}")
        print(f"  PAID_MAX = {PAID_MAX}  ->  {'PASS' if disjoint else 'FAIL'}"
              f"  [need denoise max {hi_d:.3f} < {PAID_MAX} < blur min {lo_b:.3f}]")
        if not disjoint:
            fails.append(f"F/invariance: populations not disjoint about PAID_MAX={PAID_MAX}: "
                         f"denoise max {hi_d:.3f}, blur min {lo_b:.3f}")
    else:
        fails.append("F/invariance: no usable crops -- the arm is untested, not passed")

    print("\n" + "=" * 92)
    print(f"{'arm':14s}{'PASS':>7s}{'FAIL':>7s}{'REFUSED':>9s}{'total':>8s}   >= {MIN_TESTED} tested?")
    tot = {"PASS": 0, "FAIL": 0, "REFUSED": 0}
    for arm in sorted(TALLY):
        t = TALLY[arm]
        n = t["PASS"] + t["FAIL"] + t["REFUSED"]
        tested = t["PASS"] + t["FAIL"]
        enough = tested >= MIN_TESTED
        if not enough:
            fails.append(f"{arm}: only {tested} genuinely tested cell(s); an arm that refuses "
                         f"everything reports no failures and certifies nothing")
        for k in tot:
            tot[k] += t[k]
        print(f"{arm:14s}{t['PASS']:7d}{t['FAIL']:7d}{t['REFUSED']:9d}{n:8d}   "
              f"{'yes' if enough else 'NO -- ARM IS VACUOUS'} ({tested})")
    n_all = tot["PASS"] + tot["FAIL"] + tot["REFUSED"]
    print(f"{'TOTAL':14s}{tot['PASS']:7d}{tot['FAIL']:7d}{tot['REFUSED']:9d}{n_all:8d}")
    print(f"partition: {tot['PASS']} + {tot['FAIL']} + {tot['REFUSED']} = {n_all} cells examined"
          f"  {'(sums)' if tot['PASS'] + tot['FAIL'] + tot['REFUSED'] == n_all else '(DOES NOT SUM)'}")
    if fails:
        print(f"\nCOMMISSIONING FAILED -- {len(fails)} finding(s):")
        for f_ in fails:
            print("  " + f_)
        return 1
    print("\nCOMMISSIONING PASSED -- null held; narrow and wide blur both caught and both refused a")
    print("win; band-confined denoise scored as an improvement; ladder monotone; heavier blur never")
    print("ranked above lighter; degenerate and structureless crops refused rather than passed;")
    print(f"PAID_MAX={PAID_MAX} separates the planted populations on every subject tested.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
