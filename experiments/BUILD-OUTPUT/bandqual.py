"""Qualify this lane's six subjects at THIS lane's bands, before quoting them.

ORCH's standing rule: no sharpness, softening or acuity claim is quotable
without naming the band AND the subject's qualification at that band. He has now
named `112MSDCF` and `coffee-bubbles` as subjects on which sharpness must not be
scored, because V-LINEAR measured them at 0.30-0.35 cyc/px as R = 1.079
FAIL(noise) and R = 1.542 MARGINAL.

Two of my six mottle subjects are on that list, and one hour ago I quoted
"-34.27% of struct-band structure on 112MSDCF". So the figure needs a
disposition, and there are two ways to reach one:

  * ARGUE that my band (0.077-0.20 cyc/px) is coarser than the slice V-LINEAR
    disqualified (0.30-0.35), that the noise floor falls steeply with coarseness
    while signal does not, and that a subject failing above therefore passes
    below. This is probably true and it is NOT ADMISSIBLE. It is an argument
    about where a boundary should be, offered in place of measuring it, which is
    the exact error the rule exists to stop. A qualification is a measurement or
    it is nothing.

  * MEASURE the qualification at my band, per subject, on the pixels the verdict
    was formed on. That is what this script does.

WHAT THE RATIO IS, AND WHY IT IS ALREADY IN THE HARNESS
`recertlib._structure` computes `expected = NOISE_PEAK[band] * floor` -- the
p99.5 that a band residual of PURE NOISE at this subject's own floor would
produce anyway -- and calls the band undetectable unless `peak` exceeds it by
5%. So the harness already carries a per-subject, per-band signal-versus-noise
gate, and

    R = peak / (NOISE_PEAK[band] * floor)

is that gate expressed as a ratio, directly analogous in shape to V-LINEAR's R.
The threshold is 1.05 and it is not a new number: it is the constant already
compiled into `_structure`, which `classify` already enforces by returning
`refused = True` and withholding `d_peak` entirely. This script does not invent
an instrument. It reports the reading of one that already ran before every
verdict I have quoted.

WHY IT IS COMMISSIONED WITH TWO ARMS AND NOT ONE
ORCH, tonight: "Commissioning sensitivity is not commissioning specificity.
Planting a signal and confirming detection says nothing about whether noise is
rejected. Plant noise too." So:

  SENSITIVITY  SPARSE structure inside each band's own passband must QUALIFY.
               A gate that cannot see real structure would disqualify every
               subject and I would withdraw findings that were sound.
  SPECIFICITY  a field of pure noise must FAIL, and must read R near 1.0. A gate
               that passes noise would qualify every subject and the rule would
               be decorative -- which is the failure mode ORCH is warning about,
               since a decorative gate and a sound one both print "PASS".
  BLIND SPOT   DENSE in-band texture must FAIL, and this is asserted rather than
               discovered, for the reason below.

WHAT COMMISSIONING CAUGHT, AND WHY THE THIRD ARM EXISTS
The sensitivity arm was first written as a full-field sinusoid at the band
centre. It read R = 0.356 at `struct` -- BELOW the 0.997 that pure noise reads.
A strong, perfectly in-band signal scored as less detectable than noise.

That is not a bug in `_structure`; it is a property of it that I did not know.
`floor` is a MAD-derived robust scale and `peak` is p99.5, so the ratio between
them is a measure of how HEAVY-TAILED the band residual is, not how much energy
it holds. Structure that fills the field raises the robust scale and the
percentile together and the ratio collapses; a sine wave is the worst case,
since its MAD is 1.048x its amplitude while its p99.5 is 1.000x. The gate sees
structure only where structure is SPARSE against a quieter background -- which
is what a real band residual looks like, edges and detail occupying a minority
of pixels, and is why the instrument works on photographs at all.

So the arm was wrong and the instrument was right. But the limitation is real
and a reader is entitled to it: a subject whose band is a DENSE periodic texture
(weave, foam cell walls, a regular grid) can read as unqualified while carrying
plenty of real detail. The blind-spot arm asserts the limitation and requires
the measurement to confirm it, so that it is a measured property of this
instrument rather than a caveat I merely believe.

I guessed in an earlier draft of this comment that `foam` would be the subject
exposed to that blind spot. IT IS NOT: measured, `foam` reads R = 5.523 at
`struct` and 2.967 at `mottle`, on 100% of crops -- among the strongest
qualifications in the table. The cell walls are apparently sparse enough at
these scales to leave the robust scale noise-dominated. The guess is recorded
rather than deleted because it was wrong in the direction that would have had me
discount a sound subject, and because "which real subjects the blind spot
actually bites" remains unmeasured -- none of these six is an instance of it.

All arms must land or the per-subject table below is not evidence.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "BUILD-RECERT"))
sys.path.insert(0, str(HERE))
from recertlib import BANDS, NOISE_PEAK, band_stats, display_crop  # noqa: E402
from scalescore import BASE_ARM, CROPS, SUBJECTS, find  # noqa: E402

# The threshold is `_structure`'s own, not a new one chosen here.
QUAL_MIN = 1.05

# Subjects ORCH has forbidden sharpness scoring on at 0.30-0.35 cyc/px, with the
# ratio he quoted. Listed so the table can state, per subject, whether this
# lane's own measurement agrees or disagrees at ITS band -- and so a reader can
# see that the two numbers are measurements of different bands, not a dispute.
ORCH_030_035 = {"112MSDCF": (1.079, "FAIL(noise)"),
                "coffee-bubbles": (1.542, "MARGINAL")}

# Claims this lane has quoted, and the band each was taken in. Every entry is
# CONDITIONED on below: if its band does not qualify on its subject, this script
# exits non-zero. A qualification table that were merely printed would be the
# defect AGENTS.md names -- a value printed but never conditioned on.
QUOTED_CLAIMS = [("lead-1-cpl", "struct", "--pyramid-gate 64 costs 42.20% of struct"),
                 ("112MSDCF", "struct", "--pyramid-gate 64 costs 34.27% of struct"),
                 ("lead-1-cpl", "mottle", "per-band 4096x wins mottle +0.1691"),
                 ("112MSDCF", "mottle", "per-band 4096x wins mottle +0.0659")]


def ratio(st):
    """R for one band_stats reading. None when the floor is degenerate."""
    denom = st["noise_peak_ratio"] * st["floor"]
    return (st["peak"] / denom) if denom > 1e-12 else None


# (arm, must_qualify, what it establishes)
COMMISSION_ARMS = [
    ("sparse", True, "sensitivity: sparse in-band ridges must be seen"),
    ("noise", False, "specificity: pure noise must be rejected"),
    ("dense", False, "blind spot: dense in-band texture is NOT seen"),
]


def synth(band, kind, seed=11, n=400):
    """A 400x400x3 display-space field, in-band sparse, in-band dense, or noise.

    The band's own passband sets the feature scale in every arm, so each band is
    commissioned at the frequency it actually passes rather than at one
    convenient frequency shared by all three.
    """
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 3.0, size=(n, n, 3))
    if kind == "noise":
        return 128.0 + noise

    lo, hi = BANDS[band][2]
    period = 1.0 / float(np.sqrt(lo * hi))
    y = np.arange(n, dtype=np.float64)

    if kind == "dense":
        # Fills the field: the case the instrument cannot see.
        prof = 30.0 * np.sin(2.0 * np.pi * y / period)
    else:
        # Sparse ridges at the band scale, spaced 8 periods apart, so they
        # occupy roughly an eighth of the field and the robust scale stays
        # noise-dominated. This is what structure looks like in a photograph.
        sigma = period / 4.0
        spacing = max(period * 8.0, 4.0)
        prof = np.zeros(n)
        c = spacing / 2.0
        while c < n:
            prof += 30.0 * np.exp(-0.5 * ((y - c) / sigma) ** 2)
            c += spacing
    return 128.0 + prof[:, None, None] + noise


def commission():
    print("COMMISSIONING the qualification gate (threshold R >= "
          f"{QUAL_MIN}, from _structure)\n")
    ok = True
    print(f"  {'band':<8}{'arm':<8}{'R':>10}  {'qualifies':>10}  {'required':>10}   result")
    for band in BANDS:
        for kind, want, _why in COMMISSION_ARMS:
            st = band_stats(synth(band, kind), band)
            r = ratio(st)
            got = (r is not None and r >= QUAL_MIN)
            good = (got == want)
            ok &= good
            rs = "None" if r is None else f"{r:.3f}"
            print(f"  {band:<8}{kind:<8}{rs:>10}  {str(got):>10}  {str(want):>10}"
                  f"   {'ok' if good else 'ARM FAILED'}")
    for _k, _w, why in COMMISSION_ARMS:
        print(f"    - {why}")
    print()
    return ok


def main():
    if not commission():
        print("COMMISSIONING FAILED -- the table below is not evidence.")
        return 3

    data = {}
    print("PER-SUBJECT QUALIFICATION at this lane's bands, on the SC-BASE master")
    print("(median R over the same 10 crops every verdict was formed on)\n")
    hdr = f"  {'subject':<20}"
    for b in ("mottle", "struct", "grain"):
        hdr += f"{b:>22}"
    print(hdr)
    sub2 = f"  {'':<20}" + "".join(
        f"{f'{BANDS[b][2][0]}-{BANDS[b][2][1]} c/px':>22}" for b in ("mottle", "struct", "grain"))
    print(sub2)
    for subj in SUBJECTS:
        p = find(BASE_ARM, subj)
        if p is None:
            print(f"  {subj:<20}  MISSING master")
            return 4
        arr = tifffile.imread(str(p))
        ident = ((0, 0), (1.0, 1.0, 1.0), (0.0, 0.0, 0.0))
        per = {b: [] for b in BANDS}
        for (y, x) in CROPS:
            try:
                d = display_crop(arr, y, x, *ident, 1.0, already_srgb=True)
            except ValueError:
                continue
            for b in BANDS:
                r = ratio(band_stats(d, b))
                if r is not None:
                    per[b].append(r)
        row = f"  {subj:<20}"
        data[subj] = {}
        for b in ("mottle", "struct", "grain"):
            med = float(np.median(per[b])) if per[b] else None
            frac = (sum(1 for v in per[b] if v >= QUAL_MIN) / len(per[b])) if per[b] else 0.0
            data[subj][b] = {"median_R": med, "frac_crops_qualifying": frac,
                             "n_crops": len(per[b]),
                             "qualifies": bool(med is not None and med >= QUAL_MIN)}
            cell = "--" if med is None else f"{med:8.3f} {frac * 100:3.0f}% crops"
            row += f"{cell:>22}"
        print(row)

    print("\n  (grain is reported here for completeness only; BANDS marks it")
    print("   sharpness_admissible = False and no claim may be formed from it")
    print("   regardless of what R reads.)\n")

    print("CROSS-CHECK against ORCH's 0.30-0.35 cyc/px measurements\n")
    for subj, (orch_r, orch_v) in ORCH_030_035.items():
        mine = data[subj]["struct"]["median_R"]
        print(f"  {subj:<18} ORCH 0.30-0.35: R={orch_r:.3f} {orch_v}"
              f"   |  this lane 0.077-0.20: R={mine:.3f} "
              f"{'QUALIFIES' if data[subj]['struct']['qualifies'] else 'FAILS'}")
    print("\n  These are measurements of DIFFERENT BANDS on the same subject and")
    print("  they do not contradict each other. A subject may carry no signal")
    print("  above the noise at 0.30-0.35 and carry plenty at 0.077-0.20; that is")
    print("  what a signal/noise boundary between the two means.")
    print("\n  THE TWO R COLUMNS ARE DIFFERENT STATISTICS AND THEIR THRESHOLDS DO")
    print("  NOT TRANSFER. Mine is p99.5 over (NOISE_PEAK x MAD-scale) with a 1.05")
    print("  threshold compiled into _structure; V-LINEAR's is its own and carries")
    print("  its own FAIL/MARGINAL/PASS landmarks. Reading 1.694 against V-LINEAR's")
    print("  MARGINAL-at-1.542 would be borrowing a landmark from an instrument")
    print("  that did not produce the number. ORCH: name the instrument, and do")
    print("  not reconcile two instruments by adjusting either.\n")

    print("DISPOSITION OF EVERY SHARPNESS CLAIM THIS LANE HAS QUOTED\n")
    bad = 0
    for subj, band, claim in QUOTED_CLAIMS:
        q = data[subj][band]
        adm = BANDS[band][3]
        verdict = "QUOTABLE" if (q["qualifies"] and adm) else "WITHDRAWN"
        if verdict == "WITHDRAWN":
            bad += 1
        print(f"  [{verdict:9}] {claim}")
        print(f"              {subj} at {band} {BANDS[band][2][0]}-{BANDS[band][2][1]} c/px:"
              f" R={q['median_R']:.3f} (need {QUAL_MIN}),"
              f" admissible={adm}, {q['frac_crops_qualifying'] * 100:.0f}% of crops")

    out = HERE / "bandqual.json"
    out.write_text(json.dumps({"threshold": QUAL_MIN, "per_subject": data},
                              indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    if bad:
        print(f"\n{bad} quoted claim(s) fail qualification at their own band -- WITHDRAW them.")
        return 1
    print("\nAll quoted claims qualify at the band they were taken in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
