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

---

## AMENDMENT 1 — 2026-08-27, before any arm was scored

This is appended, not merged into the clauses above. A pre-registration that is
edited in place is not a pre-registration, so the original clause (c) stands as
written and this records what changed about it and why.

### Trigger

ORCH withdrew the baseline `17 PASS / 5 FAIL / 4 REFUSED`. `recert.py`
re-measured `orch_printready.py` over 26 subjects / 4,825 frames at
**17 PASS / 0 FAIL / 9 ACQUITTED**, and `recert.py:456` records that the
withdrawn FAILs were `5 ACQUIT->FAIL` transitions mislabelled as `PASS->FAIL`.
Diffing a candidate against the withdrawn split would have manufactured five
FAIL->PASS wins out of nothing.

**No clause above depended on that split.** Clause (c) grades
`printcert4.py` (axes blotch/rim/sharp), which is a different instrument with a
different verdict space from `orch_printready.py` (PASS/FAIL/ACQUITTED). The
only citation of the withdrawn figure anywhere in this lane was a passing remark
in section 20.9, now corrected.

But ORCH's structural warning — that a gate can be *insensitive to success by
construction* — does not depend on which instrument is named, and it had not
been checked against `printcert4`. So it was measured.

### What was measured

`src/75-clause-c-power.py` calls `printcert4`'s own verdict functions over the
26 sealed masters, enumerated from the seal directory and cross-checked against
26 `.ok` seals.

```
blotch   17 PASS,  8 FAIL,  1 SUBJECT                    (sums to 26)
rim      13 FAIL,  9 PASS,  4 REFUSED                    (sums to 26)
sharp    16 REFUSED, 7 NOT EXAMINED, 2 PASS, 1 FAIL      (sums to 26)
dust     26 PASS                                          (sums to 26)
```

Clause (c) says "zero subjects move PASS -> FAIL". Only a subject that is
currently PASS can make that move, so the observable population per axis is:

```
blotch   17 observable,  9 blind  (35% of subjects)
rim       9 observable, 17 blind  (65%)
sharp     2 observable, 24 blind  (92%)

19 subjects PASS at least one gradable axis; 7 PASS none and are invisible to
clause (c) entirely: 112MSDCF, 113MSDCF, couch-fibers-cpl, flat-on-ruler-cpl,
foam, lead-1-cpl, leaf-2-cpl.
```

`sharp.json` carries records for 19 of 26 subjects; the other 7 read
NOT EXAMINED, which this census counts separately from REFUSED and from PASS.

### Why this matters more than the withdrawn number did

The sharpness axis is 92% blind — **two subjects**. That is the axis that exists
because two lanes independently found that on a blotch statistic alone the worst
arm wins. A clause that protects sharpness on two of twenty-six subjects is not
protecting sharpness.

The failure direction is the dangerous one. Clause (c) is a *no-regression*
clause, so blindness makes it **easier to pass**, not harder. "Zero subjects
moved PASS -> FAIL" would have been reported as evidence of safety while 7
subjects could not have registered damage at all.

### Amendments, in force from now

**(c1)** Every "zero regressions" reading is quoted **with its denominator** and
per axis: `0 of 17 observable (blotch)`, `0 of 9 (rim)`, `0 of 2 (sharp)`. A
bare "no regressions" is not an admissible form of this result.

**(c2)** For the 7 subjects that PASS no gradable axis, and for any axis where a
subject is FAIL/REFUSED/NOT EXAMINED, the **continuous statistic** underlying
the verdict is compared OFF vs ON per subject and reported. A verdict is a
threshold; the number behind it still moves. This reads `printcert4`'s own
outputs and does not build a parallel judgement.

**(c3)** `ACQUIT -> EXPIRED` on `orch_printready` is reported **separately** from
`PASS -> FAIL` and is not counted as a regression. Correction changes the render,
and an acquittal expires when the render moves 5%; a fix that expires its own
evidence has not thereby failed.

**(c4)** Every verdict quoted names its instrument. `orch_printready.py` and
`printcert4.py` are not reconciled to each other in either direction.

**Unchanged:** (a), (b), (d), (e), (f), and the ruling that the DUST axis is
reported UNGRADED rather than PASS. That ruling is reinforced here: dust reads
26 PASS, and section 19 measured its detection floor at 500-2000 DN against a
worst real defect of 330.875 DN. A 26/26 PASS from an axis that cannot resolve
the defect is the same failure as a 92%-blind sharpness axis, one step further
along.