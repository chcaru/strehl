# BUILD-DEFECT / Q1 second half -- PRE-REGISTRATION
# Written and committed BEFORE the ON-vs-OFF renders are measured.
# The point of writing it first is that a decision rule invented after seeing
# the numbers is not a rule, it is a description of the numbers.

## The question

Should sensor-defect correction (`STREHL_DEFECT=on`, default arm `dust`) ship
ON by default?

## What is already settled, and is NOT re-litigated here

- Planted-mote fidelity against truth: measured, section 20, six arms all pass.
  That result speaks to whether the corrector does what it claims at a site
  where truth is known. It says nothing about real motes on real stacks.
- The stated reason section 13.1 parked the default OFF -- a disputed correction
  site -- has been retired: both sites are confirmed sensor-borne and an open
  search over 469,792 filter sites found nothing. "The reason for OFF has
  evaporated" is NOT evidence for ON, which is why this document exists.
- The default was ON once already: flipped at 49227061, and eb5145d4 records
  that an exact-equality geometry guard broke 11 of 26 renders while it was on.
  439563ff reverted it to opt-in. Section 20 measured and replaced that guard.
  ON has therefore already failed once, and the burden here is higher, not lower.

## What has been measured about the grading instrument, before using it

The print gate's DUST axis CANNOT grade this feature. Measured in
70-dustaxis-power.py, re-derived by calling the shipping axis's own functions:

- Its detection floor is 500 DN (best subject) to 2000 DN (worst), and on
  flat-on-ruler-cpl no planted rung cleared even at 4000 DN.
- The largest real defect the darks record is 330.875 DN; the median mapped
  site carries 11.219 DN, and the axis's statistic is a MEDIAN over sites.
- Best floor / worst real defect = 1.51x. Worst floor / median real defect = 178x.
- The axis loads defectmap.json (48 dark frames, hot pixels). The flat-field
  dust map, dustmap.json, is read by NOTHING in the gate path. The axis named
  DUST has never tested dust.
- Its own docstring says a subject whose defects sit below the floor "is REFUSED
  rather than passed". No dust.json record carries a power arm (0 of 26) and
  dust_verdict() never accesses one. The rule is disclosed in prose and enforced
  nowhere.

CONSEQUENCE, PRE-REGISTERED: the DUST axis is reported as UNGRADED for every
subject in this experiment. It is not counted as a PASS in either arm and no
claim of "no dust regression" is made from it. Doing otherwise would repeat
tonight's `E*` failure -- grading a feature with a ruler that cannot read at the
scale of the thing it grades.

## Design

Matched pair. ONE binary, built once from the tree state recorded in the
provenance, renders both arms. The pin binary 9b05d0b7 CANNOT be used: defect_map.rs
is absent from that commit, so the SHIP-V4 seals were produced by a binary with
no defect correction at all, and an ON-vs-seal comparison would confound this
feature with every other change since. Only `STREHL_DEFECT` differs between arms.

Every render is sealed at render time with the binary hash and a provenance file.

## Pre-registered decision rule

ON ships only if ALL of the following hold. Any one failing leaves it OFF.

(a) IT FIRES. The ON arm's correction report shows a non-zero corrected-site
    count that partitions (corrected + refused + out-of-range + ... == examined)
    on a majority of subjects. A "corrected: 0" that is really "examined: 0"
    counts as a failure of this clause, not a pass.

(b) THE BYTES MOVE. ON and OFF differ by SHA-256 on the subjects where (a)
    fired. If they are identical, ON is a no-op and there is nothing to ship.

(c) NO REGRESSION ON THE THREE GRADABLE AXES. Zero subjects move PASS -> FAIL on
    blotch, rim or sharp. Reported per subject, never pooled. A subject that was
    REFUSED in the OFF arm and PASS in the ON arm is NOT counted as an
    improvement.

(d) A MEASURED IMPROVEMENT AT THE REAL SITES. Defect-site response falls in the
    ON arm relative to OFF, measured with matched controls drawn by the same
    procedure, at the two confirmed sensor-borne mote sites.

(e) SHARPNESS ON THE SAME PIXELS DOES NOT DEGRADE. Reported for the same windows
    used in (d), with band, subject and frame count named. Pre-registered bound:
    a median sharpness loss worse than 1.0% inside the corrected windows fails
    this clause. This clause exists because two lanes independently found that on
    a blotch statistic alone the worst arm wins -- a plain mean scores best and
    destroys 78% of the sharpness.

(f) NO BYTE-FREEZE MOVEMENT ATTRIBUTABLE TO A DEFAULT FLIP. The freeze registry
    is owned by the orchestrator. If flipping the default moves either frozen
    render, the flip is reported and NOT self-baselined.

## Pre-registered threats to this experiment

1. The tree is shared and other lanes are mid-build. The binary may contain
    another lane's uncommitted work. This does not break the matched pair -- both
    arms use the same binary -- but the absolute numbers are not comparable to
    the SHIP-V4 corpus, and every table must say so.
2. The default arm is `dust`, which names two motes. Two motes over a 3516x2344
    quad plane is roughly 0.1% of the field. An improvement that is real may
    still be too small to move a whole-image statistic, and a whole-image
    statistic that does not move is NOT evidence the correction did nothing.
    Clause (d) is therefore measured at the sites, not over the image.
3. A corrector that repaints everywhere would look excellent at planted sites
    and destroy the image. Clause (e) and the ON-vs-OFF byte diff outside the
    mote neighbourhoods are the controls for that.
