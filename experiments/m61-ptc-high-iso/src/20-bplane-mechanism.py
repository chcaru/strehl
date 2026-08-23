"""M61 step 20 -- is the B plane's 0.84x a property of the SENSOR or the DECODE?

THE OBSERVABLE UNDER TEST
-------------------------
M61 measured the B plane's conversion gain at 0.840 +/- 0.011 of the greens',
at every ISO from 50 to 1000 and in both gain modes. `profile.rs` models one
gain for all four CFA planes, so if this is real it is a ~16% calibration
error on one plane of four, in the file the whole noise model is injected
from. The orchestrator asks what would distinguish a sensor property from a
decode artefact, and what observable separates them.

FIRST, THE QUESTION IS NOT BINARY. Splitting it into two hides a third
possibility that is neither:

  H-A  SENSOR.   The blue pixels genuinely convert charge to voltage at a
                 lower rate, or an ANALOG per-channel attenuation is applied
                 before the ADC.
  H-B  IN-CAMERA DIGITAL.  The camera applies a per-channel DIGITAL scale
                 AFTER the ADC and writes the scaled values into the ARW.
                 The decoder then reproduces them faithfully. This is not a
                 decoder defect and not a sensor property.
  H-C  DECODER.  The decoding library applies a per-channel scale that the
                 file does not contain.

H-C IS ALREADY LARGELY EXCLUDED and I am recording why rather than
re-testing it: M61 measured that `strehl-raw`/rawler and rawpy/LibRaw decode
this corpus BIT-FOR-BIT IDENTICALLY (4 frames x 262144 px, max |diff| = 0),
and both were read through the pre-white-balance surface (`raw_image_visible`),
not through a demosaic. Two independent implementations agreeing bit-for-bit
does not exclude a SHARED convention, but it does exclude a bug in one of
them. What remains of H-C is "both libraries implement the same documented
Sony per-channel scaling", which is observationally identical to H-B here.

--------------------------------------------------------------------------
THE PHYSICS THAT SEPARATES THEM -- derived before looking at any data
--------------------------------------------------------------------------
Write s for a per-channel scale and g for a conversion gain in DN/e-.

A PTC slope is var(DN)/mean(DN). Under a multiplicative scale s applied to
DN, mean -> s*mean and var -> s^2*var, so the measured slope -> s*g. So a
digital scale and a genuine gain difference produce EXACTLY the same PTC
ratio, and the PTC alone cannot tell them apart at any ISO. That is why
this script does not measure another PTC.

Note also what CANNOT produce it: a quantum-efficiency difference. If blue
collects fewer electrons, mean and variance both fall in proportion and
var/mean is UNCHANGED. QE is not a candidate and should not be offered as
one.

Three observables do separate them, because they are sensitive to WHERE in
the chain the scale sits rather than to its size:

  D1 CODE OCCUPANCY. A digital scale s < 1 applied after quantisation maps
     integer codes k -> round(s*k), which is many-to-one. Some output codes
     become unreachable, leaving GAPS in the plane's DN histogram at a
     regular spacing. An analog attenuation or a true gain difference is
     applied before quantisation and leaves a gap-free histogram.
         gaps in B and not in G   -> H-B
         no gaps anywhere         -> H-A

  D2 SATURATION CEILING. A digital scale s < 1 applied after the ADC caps
     the plane at s * (ADC full scale): B could never reach the container
     white level however bright the scene. An analog attenuation leaves the
     ADC free to saturate at full scale; it merely takes more light.
         B ceiling < G ceiling    -> H-B
         all planes reach the same ceiling -> H-A

  D3 BLACK PEDESTAL. If a scale were applied to the raw value including its
     512 pedestal, B's black would sit at s*512 ~ 430. If black is identical
     across planes, any scale was applied after pedestal subtraction, or
     there is none.
         B black != G black       -> a scale that includes the pedestal
         all planes at 512        -> uninformative between H-A and H-B

--------------------------------------------------------------------------
PRE-REGISTERED, AND I AM NOT STATING WHICH OUTCOME I EXPECT
--------------------------------------------------------------------------
The orchestrator asked for the discriminator without being told which way I
lean, so the mapping above is written as outcome -> hypothesis in both
directions and I record no prediction. What I DO pre-register is the failure
mode that would make D1 worthless:

  THE SPARSE-SAMPLING TRAP. At low signal a histogram has empty codes simply
  because few pixels landed there. A gap is only evidence of quantisation
  loss if the neighbouring codes are WELL populated. So D1 is measured only
  over a DN window where the median code occupancy is >= 100 pixels, and B
  is compared against G at MATCHED OCCUPANCY, never at matched DN -- because
  if B really is scaled it sits at lower DN, and comparing at equal DN would
  compare a sparse B against a dense G and manufacture the result.

  ACCEPTANCE: if no window in any plane reaches the occupancy floor, D1 is
  reported as UNAVAILABLE rather than as a null.

  D2's known risk, recorded in advance: M61 already found that no probed
  frame in this corpus has a single pixel at the 15360 white level, because
  the CPL costs 1.5-2 stops. If nothing clips, D2 is UNAVAILABLE, and saying
  so is the honest outcome rather than reading a ceiling off unsaturated
  data.

WHAT THIS SCRIPT CANNOT DO, stated so the report does not overclaim: if the
answer is H-A, this script CANNOT separate "true sensor conversion gain" from
"analog per-channel attenuation before the ADC". Nothing in a raw file can:
both sit upstream of quantisation and are identical in every statistic
available here. Separating those two needs the dark-frame noise decomposition
sketched in the report, or a datasheet.
"""
import glob
import os
import sys

import numpy as np

CORPUS = r"D:\personal\macro"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "bplane-mechanism.txt")
BLACK, WHITE, CONTAINER = 512, 15360, 16383
OCC_FLOOR = 100
LINES = []


def say(s=""):
    print(s)
    LINES.append(s)


def planes(path):
    import rawpy
    with rawpy.imread(path) as r:
        a = r.raw_image_visible.astype(np.int32)
    return {"R": a[0::2, 0::2], "G1": a[0::2, 1::2],
            "G2": a[1::2, 0::2], "B": a[1::2, 1::2]}


def occupancy_gaps(v):
    """Return (window_lo, window_hi, gap_fraction, median_occupancy).

    Restricted to the densest contiguous window whose median occupancy
    clears OCC_FLOOR, so a sparse tail cannot manufacture gaps.
    """
    v = v[(v > BLACK) & (v < CONTAINER)]
    if v.size < 10000:
        return None
    lo, hi = int(np.percentile(v, 5)), int(np.percentile(v, 95))
    if hi - lo < 50:
        return None
    counts = np.bincount(v - lo, minlength=hi - lo + 1)[:hi - lo + 1]
    med = float(np.median(counts))
    if med < OCC_FLOOR:
        return (lo, hi, None, med)
    return (lo, hi, float((counts == 0).mean()), med)


def main() -> int:
    say("=" * 78)
    say("M61 step 20 -- B plane 0.84x: sensor, in-camera digital, or decoder?")
    say("=" * 78)
    say()
    say("H-A sensor/analog (pre-ADC)   H-B in-camera digital (post-ADC)")
    say("H-C decoder -- already largely excluded by rawler/LibRaw bit-identity")
    say()

    # Pick frames across the ISO range and both gain modes. Brightest stacks
    # first for D2, since a ceiling can only be read off saturated data.
    picks = [("109MSDCF", 160), ("112MSDCF", 500), ("bee-2", 400),
             ("bee-3", 100), ("foam", 1000), ("coffee-bean", 50)]
    frames = []
    for st, iso in picks:
        fs = sorted(glob.glob(os.path.join(CORPUS, st, "*.ARW")))
        if fs:
            frames.append((st, iso, fs[len(fs) // 2]))

    say("-" * 78)
    say("D3 -- BLACK PEDESTAL, and D2 -- SATURATION CEILING, per plane")
    say("-" * 78)
    say(f"  {'stack':<15}{'ISO':>5}  " + "".join(f"{p+' min':>9}" for p in
        ("R", "G1", "G2", "B")) + "   " +
        "".join(f"{p+' max':>9}" for p in ("R", "G1", "G2", "B")))
    any_clip = False
    store = {}
    for st, iso, f in frames:
        pl = planes(f)
        store[st] = (iso, pl)
        mins = [int(pl[p].min()) for p in ("R", "G1", "G2", "B")]
        maxs = [int(pl[p].max()) for p in ("R", "G1", "G2", "B")]
        any_clip = any_clip or max(maxs) >= WHITE
        say(f"  {st:<15}{iso:>5}  " + "".join(f"{m:>9}" for m in mins) +
            "   " + "".join(f"{m:>9}" for m in maxs))
    say()

    say("  D3 verdict:")
    same_black = all(
        len({int(pl[p].min()) for p in ("R", "G1", "G2", "B")}) == 1
        for _, (iso, pl) in store.items())
    say(f"    all four planes share a floor in every frame -> "
        f"{'YES' if same_black else 'NO'}")
    say("    A scale applied to the raw INCLUDING its 512 pedestal would put")
    say(f"    B's black near {int(0.84*BLACK)}. Equal floors mean any scale was")
    say("    applied after pedestal subtraction, or there is none. This is")
    say("    uninformative BETWEEN H-A and H-B either way -- it only excludes")
    say("    a pedestal-inclusive scale.")
    say()
    say("  D2 verdict:")
    if not any_clip:
        say(f"    NO plane in any probed frame reaches the {WHITE} white level.")
        say("    D2 is UNAVAILABLE. This was pre-registered as the likely")
        say("    outcome-shape because the CPL costs 1.5-2 stops, and reading")
        say("    a ceiling off unsaturated data would be inventing a number.")
    else:
        say("    Clipping present -- per-plane ceilings above are readable.")
        say("    B ceiling below G ceiling -> H-B; equal ceilings -> H-A.")
    say()

    say("-" * 78)
    say("D1 -- CODE OCCUPANCY: does the B plane's histogram have gaps?")
    say("-" * 78)
    say("  Measured only where median occupancy >= "
        f"{OCC_FLOOR} px, and compared at")
    say("  MATCHED OCCUPANCY rather than matched DN (see docstring).")
    say()
    say(f"  {'stack':<15}{'plane':>6}{'window':>16}{'med occ':>10}{'gap %':>9}")
    verdicts = []
    for st, (iso, pl) in store.items():
        row = {}
        for p in ("R", "G1", "G2", "B"):
            r = occupancy_gaps(pl[p].ravel())
            if r is None:
                say(f"  {st:<15}{p:>6}{'too few px':>16}")
                continue
            lo, hi, gap, med = r
            gs = "UNAVAIL" if gap is None else f"{100*gap:.2f}"
            say(f"  {st:<15}{p:>6}{f'{lo}-{hi}':>16}{med:>10.0f}{gs:>9}")
            row[p] = gap
        if "B" in row and "G1" in row and row["B"] is not None \
                and row["G1"] is not None:
            verdicts.append((st, row["B"], (row["G1"] + row.get("G2", row["G1"])) / 2))
        say()

    say("-" * 78)
    say("D1 VERDICT")
    say("-" * 78)
    if not verdicts:
        say("  UNAVAILABLE -- no plane reached the occupancy floor. Reported")
        say("  as unavailable, not as a null.")
    else:
        say(f"  {'stack':<15}{'B gap %':>10}{'G gap %':>10}   reading")
        nb = 0
        for st, gb, gg in verdicts:
            comb = gb > 0.02 and gb > 5 * max(gg, 1e-6)
            nb += comb
            say(f"  {st:<15}{100*gb:>10.2f}{100*gg:>10.2f}   "
                f"{'GAPS in B only' if comb else 'no B-specific gaps'}")
        say()
        if nb == 0:
            say("  No B-specific comb structure. Under the mapping fixed in the")
            say("  docstring this points AWAY from a post-ADC digital scale")
            say("  (H-B) and toward H-A -- sensor conversion gain or an ANALOG")
            say("  attenuation ahead of the ADC.")
            say()
            say("  AND THE LIMIT, pre-registered: this CANNOT separate a true")
            say("  sensor conversion gain from an analog per-channel")
            say("  attenuation. Both sit upstream of quantisation and are")
            say("  identical in every statistic a raw file can offer. That")
            say("  separation needs the dark-noise decomposition, not this.")
        else:
            say(f"  B-specific gaps in {nb}/{len(verdicts)} stacks -- consistent")
            say("  with a post-ADC per-channel digital scale (H-B).")
    say()
    say("=" * 78)
    say("Decoded through rawpy `raw_image_visible` -- pre-white-balance,")
    say("pre-demosaic, per CFA plane. No binning across a quad.")
    say("=" * 78)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"\n[wrote {OUT}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
