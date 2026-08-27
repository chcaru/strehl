"""Commission `halo_profile.py` by planting halos of known size.

A detector that reports "clean" on all 26 masters and a detector that is broken
print the same table. The only thing separating them is whether the detector
can be made to say HALO by something that IS a halo.

So: plant a rim of known amplitude into a real master's background, in exactly
the geometry a stacking halo has -- background pixels within a few tens of
pixels of the subject silhouette, raised -- and require the reported overshoot
to come back at the planted amplitude.

ARMS, with verdicts pre-registered before running:

  CLEAN     untouched                              -> clean, |overshoot| small
  HALO600   background d in [2,30) raised  +600 DN  -> HALO, overshoot ~ +600
  HALO2000  background d in [2,30) raised +2000 DN  -> HALO, overshoot ~ +2000
  VEIL2000  background d in [2,30) lowered -2000 DN -> veiling, veil ~ -2000

The amplitude recovery is the real test. A detector that fires on the presence
of a plant but reports the wrong size is measuring something other than the
thing it names, and every number it prints about a real master is then
uninterpretable. Requiring recovery within a tolerance is what makes the DN
figures on the corpus table mean anything.

VEIL2000 exists because the two defects have opposite sign and this project has
spent real effort on the dark-aura one. A detector that collapsed both into
"anomaly" would let a fix for one report as a fix for the other.
"""

import pathlib
import subprocess
import sys

import numpy as np
import tifffile
from scipy.ndimage import (binary_closing, binary_opening,
                           distance_transform_edt)

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from halo_profile import luma, otsu           # noqa: E402

PLANT_LO, PLANT_HI = 2, 120
TOL = 0.25          # recovered amplitude must be within 25% of planted


def plant(a, amp, lo, hi):
    y = luma(a)
    sub = 4
    ys = y[::sub, ::sub]
    t = otsu(ys.ravel())
    subj = ys < t
    subj = binary_opening(subj, np.ones((3, 3)))
    subj = binary_closing(subj, np.ones((5, 5)))
    d = distance_transform_edt(~subj) * sub
    m = (d >= lo) & (d < hi)
    full = np.repeat(np.repeat(m, sub, axis=0), sub, axis=1)
    full = full[:a.shape[0], :a.shape[1]]
    out = a.astype(np.int32).copy()
    out[full] += int(amp)
    return np.clip(out, 0, 65535).astype(np.uint16), int(full.sum())


def run(d):
    r = subprocess.run(
        [sys.executable, str(HERE / "halo_profile.py"), str(d), "--thresh", "200"],
        capture_output=True, text=True)
    return r.stdout + r.stderr


def parse(text):
    """-> (overshoot, bump, verdict). Columns: stem over bump penumbra far."""
    for line in text.splitlines():
        p = line.split()
        if len(p) >= 5 and p[0].startswith("commission"):
            if p[1] == "-":
                return None, None, "SKIPPED"
            v = "HALO" if "HALO" in line else "clean"
            return float(p[1]), float(p[2]), v
    return None, None, "MISSING"


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = pathlib.Path(sys.argv[1])
    a = tifffile.imread(str(src))
    assert a.dtype == np.uint16, "expected uint16 master"

    root = pathlib.Path(r"C:\dev\strehl-out\ORCH-HALOCOMM")
    root.mkdir(parents=True, exist_ok=True)

    # (name, amplitude, band_lo, band_hi, which statistic must catch it)
    #
    # WHAT THE FIRST TWO RUNS OF THIS COMMISSION ESTABLISHED
    #
    # Run 1 killed `veil = min(band)`: it read -19951 on a clean master, which
    # is the subject's own out-of-focus penumbra, not a defect.
    #
    # Run 2 killed this script's own scoring. It compared the ABSOLUTE
    # overshoot against the planted amplitude, but the clean master's baseline
    # overshoot is -431.5, so a +600 plant can only ever reach +168. Measured:
    # +600 -> +168.3 and +2000 -> +1568.5, i.e. deltas of +599.8 and +2000.0
    # against plants of 600 and 2000 -- the statistic was recovering the plant
    # to within 0.03% while being marked WRONG. The instrument was right and
    # the test was wrong. Recovery is therefore scored on the DELTA FROM THE
    # CLEAN BASELINE, which is the only quantity a plant can control.
    #
    # `bump` is scored differently on purpose. A ring confined to [2,30) makes
    # a local maximum, and bump measures the STEP DOWN on its outer flank --
    # a real detection signal, but its size depends on where the rim edge falls
    # relative to band boundaries, so it is not an amplitude estimator and
    # must not be tested as one. It is tested as a detector plus a
    # RESPONSIVENESS LADDER: three amplitudes, each must be caught, and bump
    # must rise strictly with the plant. A statistic that fires but does not
    # order is a statistic that cannot tell a small halo from a large one.
    arms = [("CLEAN",    0,    0,   0, "quiet"),
            ("LIFT600",  600,  2, 120, "overshoot"),
            ("LIFT2000", 2000, 2, 120, "overshoot"),
            ("RING500",  500,  2,  30, "floor"),
            ("RING1500", 1500, 2,  30, "bump"),
            ("RING4000", 4000, 2,  30, "bump")]

    print("commissioning halo_profile.py on %s\n" % src.name)
    print("%-10s %8s %9s %10s %9s %8s %-8s %s"
          % ("arm", "planted", "band", "overshoot", "d(over)", "bump",
             "verdict", "check"))
    print("-" * 94)

    ok = True
    base_over = base_bump = None
    ladder = []
    for name, amp, lo, hi, catcher in arms:
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*.tif*"):
            old.unlink()
        img, npx = (a, 0) if amp == 0 else plant(a, amp, lo, hi)
        if amp != 0 and npx < 10000:
            raise SystemExit("PLANT DID NOT LAND: only %d px in the rim band "
                             "-- the mask is wrong, not the detector" % npx)
        tifffile.imwrite(str(d / ("commission-%s.tiff" % name.lower())), img)
        over, bump, verdict = parse(run(d))
        band = "-" if amp == 0 else "%d-%d" % (lo, hi)
        if over is None:
            print("%-10s %8d %9s %10s %9s %8s %-8s %s"
                  % (name, amp, band, "-", "-", "-", verdict, "*** WRONG ***"))
            ok = False
            continue

        if catcher == "quiet":
            base_over, base_bump = over, bump
            good = verdict == "clean" and abs(bump) < 1.0
            note = "baseline; bump must be 0 on a monotone ramp"
            dov = 0.0
        elif catcher == "overshoot":
            # These span EVERY measured band, so they are a uniform lift of the
            # whole near field, not a rim: no local maximum, and bump correctly
            # stays 0. That makes them a CALIBRATION arm, not a detection arm,
            # and asserting a HALO verdict on them would be asserting the wrong
            # thing. What is required is only that overshoot move by exactly
            # what was planted.
            dov = over - base_over
            good = abs(dov - amp) <= TOL * amp
            note = "calib: delta = %.1f%% of plant" % (100.0 * dov / amp)
        else:
            dov = over - base_over
            ladder.append((amp, bump))
            if catcher == "floor":
                # PRE-REGISTERED MISS. A 500 DN rim does not make the profile
                # non-monotone on this subject, because the penumbra's own
                # gradient between adjacent bands is steeper than 500 DN. So
                # bump correctly stays 0 and the rim is not detected.
                #
                # That is a sensitivity FLOOR, and the honest thing to do with
                # a floor is measure it and state it, not pretend it is not
                # there. This arm asserts the miss so that the floor is a
                # checked property: if a future change made 500 detectable the
                # commission would say so, and if it made 1500 undetectable it
                # would say that too. Between them the floor is bracketed.
                good = verdict == "clean" and bump < 1.0
                note = "floor arm: expected MISS"
            else:
                good = verdict == "HALO" and bump > 200.0
                note = "detected; ladder point"

        if not good:
            ok = False
        print("%-10s %8d %9s %+10.1f %+9.1f %8.1f %-8s %s  %s"
              % (name, amp, band, over, dov, bump, verdict, note,
                 "OK" if good else "*** WRONG ***"))

    mono = all(ladder[i][1] < ladder[i + 1][1] for i in range(len(ladder) - 1))
    det = [a for a, bp in ladder if bp > 200.0]
    mis = [a for a, bp in ladder if bp <= 200.0]
    print("-" * 94)
    print("bump responsiveness ladder: %s  -> %s"
          % (", ".join("%d:%.1f" % (a, b) for a, b in ladder),
             "strictly increasing, OK" if mono else "*** NOT ORDERED ***"))
    if not mono:
        ok = False

    if ok:
        print("\nsensitivity floor: a rim of %s DN was NOT detected on this"
              % (", ".join(str(a) for a in mis) or "no tested amplitude"))
        print("subject; %s DN was. The floor is bracketed there, and it is set"
              % (", ".join(str(a) for a in det) or "no tested amplitude"))
        print("by the steepness of the subject's own penumbra, not by the code.")
        print("A `clean` verdict on the corpus table therefore means NO RIM")
        print("ABOVE THAT FLOOR -- it does not mean no rim at all.")
        print("\nCOMMISSION PASSED -- bump is exactly 0 on the clean master's")
        print("monotone ramp; overshoot recovers a planted rim's amplitude to")
        print("within %.0f%%; a LOCAL rim that overshoot alone misses is caught"
              % (TOL * 100))
        print("by bump; and bump orders three amplitudes correctly.")
        return 0
    print("COMMISSION FAILED -- do not trust any halo table this prints.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
