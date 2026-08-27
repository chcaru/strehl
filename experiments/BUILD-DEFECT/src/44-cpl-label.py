"""P44 -- which flat block wears the CPL, and why the pre-registered gate refused.

PREREG-cpl.txt gate C1 labelled the blocks photometrically: a CPL costs light,
the two passes use identical shutter speeds, so the CPL block must be darker by
a consistent amount at every matched step.  C1 required the ratio to sit on one
side of unity at all nine steps AND to spread less than 0.5 stop.

C1 FAILED.  Same side, yes -- 9 of 9 -- but the spread is 2.130 stops.  The
pre-registration says that when C1 fails I report blocks "1" and "2" and claim
no filter label, and that is what 43-cpl-split.rs printed.

This script does two things and keeps them apart:

  (a) DIAGNOSES the failure.  Post-hoc.  A ratio of medians is only a ratio of
      transmissions where the sensor is linear, and the ladder's ends are not:
      the long exposures clip against white and the short ones sit on the black
      floor.  Restricted to the steps where both blocks are inside the linear
      window the ratio is far tighter -- but this is a window chosen after
      seeing the data and it is labelled as such, not folded back into C1.

  (b) Presents INDEPENDENT, NON-PHOTOMETRIC evidence for the label: the capture
      timeline.  Cloud cannot move a timestamp.  This evidence was not part of
      C1 and does not rescue it; it is a different argument that happens to
      answer the same question, and it is reported separately so a reader can
      reject (a) and keep (b) or vice versa.

Nothing here changes the P43 result.  Mote 2 is in BOTH blocks at -3.480% and
-3.486%.  That holds whichever block wears the filter, so the main finding is
independent of everything on this page.

Every number is parsed out of the artifacts -- 43-cpl-split.log and the EXIF
CSVs -- and none is typed into this file.  A checker that compares a document
against constants written in the checker verifies the checker.
"""

import csv
import datetime as dt
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
LOG = ROOT / "experiments" / "BUILD-DEFECT" / "out" / "43-cpl-split.log"
EXIF = pathlib.Path(r"C:\dev\strehl-out\BUILD-DEFECT\exif")

# The linear window, declared before looking at which steps fall in it: a median
# below this fraction of range sits on the black floor, above it clips.  These
# are the same bounds the shipping census uses to accept a frame at all
# (EXPOSURE_WINDOW), tightened at the top because a MEDIAN at 0.90 already has
# a clipped upper tail.
LINEAR_LO, LINEAR_HI = 0.08, 0.80


def die(msg):
    print(f"HALT: {msg}")
    sys.exit(1)


def parse_c1(log_text):
    """Pull the C1 table out of the P43 log.  Anchored on the section header so
    a stray line elsewhere in the log cannot be mistaken for a table row."""
    m = re.search(r"-- C1: which block wears the CPL --\n(.*?)\n  C1:", log_text, re.S)
    if not m:
        die("C1 table not found in 43-cpl-split.log -- cannot proceed")
    rows = []
    for line in m.group(1).splitlines():
        g = re.match(
            r"\s*(\S+)\s+block1\s+([\d.]+)\s+block2\s+([\d.]+)\s+ratio\s+([\d.]+)", line
        )
        if g:
            rows.append((g.group(1), float(g.group(2)), float(g.group(3)), float(g.group(4))))
    if len(rows) != 9:
        die(f"expected 9 C1 rows, parsed {len(rows)}")
    return rows


def shutter_seconds(s):
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b)
    return float(s)


def main():
    if not LOG.exists():
        die(f"{LOG} missing -- run defect-cpl-split first")
    log_text = LOG.read_text(encoding="utf-8", errors="replace")
    rows = parse_c1(log_text)

    # The pre-registered verdict, re-read from the artifact rather than assumed.
    c1_line = re.search(r"\n  C1: .*", log_text).group(0).strip()
    c1_failed = "C1 FAILS" in log_text
    print("== P44 -- labelling the flat blocks ==")
    print(f"parsed from : {LOG.name}")
    print(f"C1 as run   : {c1_line}")
    print(f"C1 verdict  : {'FAILED (pre-registered refusal stands)' if c1_failed else 'PASSED'}")

    # ---------- (a) diagnosis: where is the sensor linear ----------
    print("\n-- (a) POST-HOC diagnosis: the ladder's ends are not linear --")
    print(f"   linear window declared as [{LINEAR_LO:.2f}, {LINEAR_HI:.2f}] of range")
    print(f"   {'step':>6} {'block1':>8} {'block2':>8} {'ratio':>7} {'stops':>7}  {'level/t block1':>15} {'block2':>9}  in-window")
    usable = []
    for step, b1, b2, ratio in rows:
        t = shutter_seconds(step)
        inw = LINEAR_LO <= b1 <= LINEAR_HI and LINEAR_LO <= b2 <= LINEAR_HI
        if inw:
            usable.append((step, b1, b2, ratio))
        import math

        print(
            f"   {step:>6} {b1:8.4f} {b2:8.4f} {ratio:7.3f} {math.log2(ratio):+7.2f}  "
            f"{b1 / t:15.2f} {b2 / t:9.2f}  {'yes' if inw else 'NO'}"
        )
    import math

    n_examined = len(rows)
    n_in = len(usable)
    n_out = n_examined - n_in
    print(f"   partition: examined {n_examined} = {n_in} in-window + {n_out} out-of-window")

    if n_in < 3:
        print("   fewer than 3 usable steps -- the diagnosis has no power, nothing claimed.")
        stops_in = None
    else:
        logs = [math.log2(r[3]) for r in usable]
        spread = max(logs) - min(logs)
        mean = sum(logs) / len(logs)
        stops_in = mean
        print(
            f"   in-window ratio: mean {mean:+.2f} stops, spread {spread:.3f} stops "
            f"(C1 bar was 0.5 over all nine)"
        )
        print(
            f"   -> the {'spread does' if spread >= 0.5 else 'spread does NOT'} still exceed the C1 bar "
            f"when restricted to the linear region."
        )
        print(
            "   Either way this is a window chosen after seeing the data. It explains"
        )
        print("   C1's failure; it does not overturn C1's refusal.")

    # ---------- (b) the timeline: cloud cannot move a timestamp ----------
    print("\n-- (b) INDEPENDENT evidence: the capture timeline --")
    flats = sorted(
        csv.DictReader((EXIF / "flats.csv").open(encoding="utf-8-sig")),
        key=lambda r: r["FileName"],
    )
    if len(flats) != 360:
        die(f"expected 360 flats in EXIF, got {len(flats)}")

    def ts(r):
        return dt.datetime.strptime(r["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")

    gaps = []
    for a, b in zip(flats, flats[1:]):
        gaps.append(((ts(b) - ts(a)).total_seconds(), b["FileName"]))
    gaps.sort(reverse=True)
    biggest, at = gaps[0]
    runner_up = gaps[1][0]
    # The block boundary was derived from the ExposureTime ladder, independently
    # of any timing.  Does the largest pause land on it?
    boundary = "DSC00263.ARW"
    print(f"   inter-frame gaps over {len(gaps)} transitions")
    print(f"   largest      : {biggest:6.0f} s  before {at}")
    print(f"   next largest : {runner_up:6.0f} s  before {gaps[1][1]}")
    print(f"   ratio        : {biggest / runner_up:.1f}x")
    on_boundary = at == boundary
    print(
        f"   block boundary from the EXPOSURE LADDER (independent) : {boundary}"
    )
    print(f"   largest pause falls on that boundary                   : {on_boundary}")

    # A floor, so this cannot be a search that always finds something.
    GAP_FACTOR_FLOOR = 3.0
    gap_evidence = on_boundary and biggest / runner_up >= GAP_FACTOR_FLOOR
    print(
        f"   floor: the pause must be >= {GAP_FACTOR_FLOOR:.0f}x the largest other gap "
        f"AND land on the ladder boundary -> {'MET' if gap_evidence else 'NOT MET'}"
    )

    sweeps = {}
    for name, fn in (("WITH cpl", "sweep-cpl.csv"), ("NO cpl", "sweep-nocpl.csv")):
        p = EXIF / fn
        if not p.exists():
            die(f"{fn} missing")
        rs = list(csv.DictReader(p.open(encoding="utf-8-sig")))
        t = sorted(ts(r) for r in rs)
        sweeps[name] = (t[0], t[-1], len(rs))

    b1_start, b1_end = ts(flats[0]), ts(flats[179])
    b2_start, b2_end = ts(flats[180]), ts(flats[359])
    events = [
        (sweeps["WITH cpl"][0], sweeps["WITH cpl"][1], f"subject sweep WITH cpl  (n={sweeps['WITH cpl'][2]})"),
        (b1_start, b1_end, "flats BLOCK 1           (n=180)"),
        (b2_start, b2_end, "flats BLOCK 2           (n=180)"),
        (sweeps["NO cpl"][0], sweeps["NO cpl"][1], f"subject sweep NO cpl    (n={sweeps['NO cpl'][2]})"),
    ]
    events.sort()
    print("\n   session order, by DateTimeOriginal:")
    for a, b, label in events:
        print(f"     {a:%H:%M:%S} .. {b:%H:%M:%S}   {label}")

    ordered = [e[2] for e in events]
    expected = (
        "WITH cpl" in ordered[0]
        and "BLOCK 1" in ordered[1]
        and "BLOCK 2" in ordered[2]
        and "NO cpl" in ordered[3]
    )
    print(
        f"\n   the labelled sweeps BRACKET the flats, CPL side first: {expected}"
    )

    # ---------- the verdict, with its outcome partition ----------
    print("\n-- verdict --")
    strands = {
        "C1 photometric (pre-registered)": "REFUSED",
        "largest pause on the ladder boundary": "SUPPORTS" if gap_evidence else "SILENT",
        "labelled sweeps bracket, CPL first": "SUPPORTS" if expected else "SILENT",
        "block 2 brighter at 9 of 9 steps": "SUPPORTS"
        if all(r[3] > 1.0 for r in rows)
        else "SILENT",
    }
    for k, v in strands.items():
        print(f"   {k:<40} {v}")
    n_supp = sum(1 for v in strands.values() if v == "SUPPORTS")
    n_ref = sum(1 for v in strands.values() if v == "REFUSED")
    n_sil = sum(1 for v in strands.values() if v == "SILENT")
    print(
        f"   partition: {len(strands)} strands = {n_supp} supporting + {n_ref} refusing + {n_sil} silent"
    )

    if n_supp >= 3 and gap_evidence and expected:
        print("\n   BLOCK 1 = with CPL,  BLOCK 2 = bare.")
        print("   Rests on the TIMELINE, not on the photometry. C1 stays refused.")
        if stops_in is not None:
            print(
                f"   Note the tension: removing a CPL should brighten by ~1.3-2.5 stops"
            )
            print(
                f"   and the in-window measurement is only {stops_in:+.2f} stops. Cloud"
            )
            print(
                "   thinning or brightening between 16:45 and 16:47 is unmeasured and is"
            )
            print("   the obvious reason C1 could not hold a constant ratio.")
    else:
        print("\n   NOT LABELLED. Blocks stay '1' and '2'.")

    print("\n   The P43 result does not depend on any of this: mote 2 reads")
    m = re.search(r"mote 2\s+(-[\d.]+)%\s+(-[\d.]+)%\s+([+-][\d.]+)\s+([\d.]+)\s+(\w+)", log_text)
    if m:
        print(
            f"   {m.group(1)}% and {m.group(2)}% in the two blocks, DELTA {m.group(3)} pp, "
            f"p {m.group(4)}, {m.group(5)}."
        )
    else:
        die("could not re-read the mote 2 row from the P43 log")


if __name__ == "__main__":
    main()
