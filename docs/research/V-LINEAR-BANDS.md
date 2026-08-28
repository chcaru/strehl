# V-LINEAR-BANDS — per-subject band qualification across the corpus

*Lane V-LINEAR. Every number below was produced by `experiments/V-LINEAR/bandsweep.py`
and is stored in the `bandsweep*.json` beside it. The decision rule and the band
edges are **imported** from `experiments/V-LINEAR2/bandsignal.py`, which is frozen
and cited by three lanes; this driver has no opinion of its own about what passes.*

---

## 0. The verdict, in one paragraph

**The 0.25 cyc/px signal/noise boundary does not hold corpus-wide. It moves by
subject, from 0.17 to 0.48 cyc/px — a factor of 2.8.** No lane may use a fixed
band. A sharpness claim must state the subject it was measured on and the band
that subject qualifies, and a band qualified on one subject transfers to no
other. Two of the five subjects sampled (`flower-bud-alone-cpl`, `leaf-2-cpl`)
qualify **no band at or above 0.20 cyc/px**, so the 0.20–0.25 band that this
project has quoted repeatedly is noise on them.

The spread is a property of the subjects, not of the instrument: it survives a
three-rung defocus ladder unchanged (§4). What the spread is *caused by* is
**not** stack depth, **not** the defocus parameter, **not** fine-structure
content, and **not** either term of `R` taken separately — five candidates,
all measured and all rejected in §5. The operational consequence is stated in
§5.4: **no subject property measured here predicts where a subject's boundary
will land, so a lane cannot infer a band from a subject and must run the test.**

---

## 1. Why this measurement exists

`bandsignal.py` established a signal/noise boundary at 0.25 cyc/px on **one
subject**, `113MSDCF`, from 29 tiles. Three lanes are now applying that single
result to *their* subjects. That is the unjustified transfer this project has
already been burned by once — fact 52, a scalar fitted on one scene and used on
another. The question here is only whether the transfer is legitimate.

It is not.

---

## 2. Method, stated so it can be re-run in six months

Per subject, over linear-develop TIFFs (`--linear-srgb --demosaic`, no tone
curve, no sharpening):

1. Lay a fixed 5×6 grid of 256 px tiles with a 700 px margin (`T`, `MARGIN`,
   imported from `bandsignal`). 30 tiles per subject.
2. Read frames subsampled by `step = round(N / 80)`, so ~60–100 frames are read
   whatever the stack depth. **Subsampling changes which frames are examined,
   never the frequency axis** — no binning and no resampling, so cyc/px means
   the same thing on every subject.
3. For each tile, find its in-focus frame as the argmax of band power in the
   pre-registered selection band 0.05–0.20 cyc/px.
4. Take the defocused reference as the mean of the frames `far` positions either
   side, where `far` is in **real** frames and converted to sampled units by
   `max(2, round(far / step))`.
5. Discard tiles whose focus maximum is not interior (it would have no reference
   on one side).
6. Restrict to the **CONFIRMED** population — tiles whose selection-band power
   ratio is ≥ 2.0, i.e. tiles where the lens demonstrably moved. Fall back to all
   tiles only if fewer than 4 confirm. All five subjects here are CONFIRMED.
7. Per band, `R` = ratio of sums of in-focus to defocused power, with a
   10,000-resample percentile bootstrap over tiles (`bandsignal.ratio_ci`).

**Decision rule, pre-registered at `experiments/V-LINEAR2/PREREGISTRATION.md:51`
before `bandsignal.py` first ran, and imported here rather than restated:**

| verdict | rule |
| --- | --- |
| `PASS` | `R >= 2.0` **and** bootstrap CI low `>= 1.5` |
| `MARGINAL` | `1.3 <= R < 2.0` |
| `FAIL(noise)` | `R < 1.3` |

**The boundary** is the top edge of the highest-frequency band that PASSes,
read off the `FINE` partition only. §6 explains why "only" is load-bearing.

### 2.1 Which subjects, and why these

Five, and they are the five that **already had linear develops on disk**.
Developing the full 26-subject / 4,825-frame corpus would be roughly 950 GB and
is not affordable; these five cost nothing. They span 33–299 frames and four
subject types.

**None were dropped after being measured.** Every subject that had develops was
swept and every one appears in the table below, including the two that produce
the least convenient answer.

This is the honest weakness of the result: five subjects is a small sample and
they were selected by what happened to be on disk, not at random. The claim
"the boundary moves" needs only one counterexample to the fixed-boundary
assumption and has four; the claim that it moves **specifically** between 0.17
and 0.48 is a floor and a ceiling observed on five subjects, not the corpus range.

---

## 3. The table (MEASURED)

Matched defocus, `far = 20` real frames on every subject. `N` = frames, `st` =
subsample step, `kept` = tiles surviving the interior-maximum test, all
CONFIRMED population.

| subject | N | st | kept | 0.17–0.20 | 0.20–0.25 | 0.25–0.30 | 0.30–0.40 | 0.40–0.48 | **boundary** |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: |
| `113MSDCF` | 63 | 1 | 29 | **4.874** PASS | **2.419** PASS | 1.387 MARG | 1.149 FAIL | 1.105 FAIL | **0.25** |
| `119MSDCF` | 33 | 1 | 30 | **5.898** PASS | **2.790** PASS | 1.624 MARG | 1.273 FAIL | 1.242 FAIL | **0.25** |
| `bee-1-cpl` | 299 | 4 | 27 | **58.740** PASS | **27.993** PASS | **10.728** PASS | **4.732** PASS | **3.629** PASS | **0.48** |
| `flower-bud-alone-cpl` | 205 | 3 | 27 | 2.015 MARG | 1.342 MARG | 1.108 FAIL | 1.035 FAIL | 1.066 FAIL | **0.17** |
| `leaf-2-cpl` | 182 | 2 | 30 | **2.218** PASS | 1.512 MARG | 1.171 FAIL | 1.068 FAIL | 1.040 FAIL | **0.20** |

With confidence intervals, on the two bands that decide most verdicts:

| subject | 0.17–0.20 `R` [CI] | 0.20–0.25 `R` [CI] |
| --- | --- | --- |
| `113MSDCF` | 4.874 [3.648, 6.631] | 2.419 [1.970, 3.058] |
| `119MSDCF` | 5.898 [3.889, 7.651] | 2.790 [2.114, 3.414] |
| `bee-1-cpl` | 58.740 [25.680, 102.702] | 27.993 [14.287, 43.521] |
| `flower-bud-alone-cpl` | 2.015 [1.413, 2.775] | 1.342 [1.146, 1.598] |
| `leaf-2-cpl` | 2.218 [1.900, 2.567] | 1.512 [1.361, 1.684] |

`flower-bud-alone-cpl` at 0.17–0.20 is the one verdict decided by the CI rather
than by `R`: `R = 2.015` clears the 2.0 bar, but the CI low of 1.413 does not
clear 1.5, so it is MARGINAL and not PASS. That is the pre-registered rule doing
exactly what it was written to do.

### 3.1 Subjects on which no sharpness claim may be made above 0.20 cyc/px

**`flower-bud-alone-cpl`** — boundary 0.17. **`leaf-2-cpl`** — boundary 0.20.

Neither qualifies the 0.20–0.25 band. Both are MARGINAL there, and every band
above is FAIL(noise). `leaf-2-cpl` is the subject the item-2 gate-floor
comparison is being run on, so that comparison may not be scored above
0.20 cyc/px either.

No subject in this sample is dead outright — all five qualify *something* above
0.10 cyc/px — so the "no sharpness claim of any kind" flag fires for none of
them. The weaker flag above is the one that fires.

---

## 4. The control that decides whether §3 is real (MEASURED)

`far` is a free parameter of my instrument. If `far` had been chosen per subject
and the boundary moved with it, the entire §3 spread would be my own parameter
and not the corpus. The original sweep did scale it, `far = max(20, round(N/6))`,
giving bee 50 and `113MSDCF` 20 — so this had to be tested, not assumed.

Three rungs were run: `far` = 8, 20, and the scaled value (20–50).

| subject | far=8 | far=20 | far=auto | `R` span | **boundary at 8 / 20 / auto** |
| --- | ---: | ---: | ---: | ---: | --- |
| `113MSDCF` | 4.299 | 4.874 | 4.874 (20) | 1.13× | 0.25 / 0.25 / 0.25 |
| `119MSDCF` | 5.585 | 5.898 | 5.898 (20) | 1.06× | 0.25 / 0.25 / 0.25 |
| `bee-1-cpl` | 17.977 | 58.740 | 78.318 (50) | **4.36×** | 0.48 / 0.48 / 0.48 |
| `flower-bud-alone-cpl` | 2.021 | 2.015 | 2.073 (34) | 1.03× | 0.17 / 0.17 / 0.17 |
| `leaf-2-cpl` | 2.170 | 2.218 | 2.179 (30) | 1.02× | 0.20 / 0.20 / 0.20 |

*(`R` shown for 0.17–0.20; span is max/min across the three rungs.)*

**Every subject's boundary is identical at all three rungs.** The 0.17–0.48
spread is a property of the subjects. This is the pre-registered reading: it was
fixed in advance that if bee stayed far above the others at matched `far` the
headline stands, and if it collapsed the table was an artifact. It did not
collapse.

**But `R`'s magnitude is not comparable across subjects, and that is a
limitation of this instrument.** Four of five subjects move ≤ 1.13× across the
ladder; bee moves **4.36×** and is still climbing at the top rung, meaning its
defocus is not saturated even at ±50 frames. So bee's *verdict* is robust and
bee's *number* is not. **Do not quote 58.740, or any cross-subject ratio of
`R`.** The verdicts and the boundaries are what this document licenses.

One direction is worth stating because it is the conservative one: bee still
PASSes 0.40–0.48 at the **smallest** `far` tested (`R = 3.164` at far=8), which
is the least-defocused and therefore least favourable rung. The finding survives
at the conservative end of its own ladder.

---

## 5. What the boundary moves with (three candidates measured and rejected)

### 5.1 Stack depth — REJECTED (MEASURED)

Non-monotone, and not close:

| N | 33 | 63 | 182 | 205 | 299 |
| --- | ---: | ---: | ---: | ---: | ---: |
| boundary | 0.25 | 0.25 | 0.20 | 0.17 | **0.48** |

The two shallowest stacks share a boundary with each other and beat two of the
three deepest; the deepest stack has the highest boundary of all. No ordering.

### 5.2 The defocus parameter — REJECTED (MEASURED)

§4. Boundary invariant on 5/5 subjects across a 2.5–6× range of `far`.

### 5.3 Fine-structure content — REJECTED, and it was my own hypothesis (MEASURED)

The obvious candidate was that hairy, high-micro-contrast subjects qualify
higher bands than smooth ones. Tested with a scale-free, exposure-free subject
statistic computed from **in-focus power only**, with no defocus term in it:

    f2c = median in-focus power 0.30-0.40  /  median in-focus power 0.05-0.08

| subject | boundary | `f2c` | rank by `f2c` |
| --- | ---: | ---: | ---: |
| `119MSDCF` | 0.25 | 1.005 | 1 |
| `leaf-2-cpl` | 0.20 | 0.212 | 2 |
| `113MSDCF` | 0.25 | 0.0841 | 3 |
| `flower-bud-alone-cpl` | 0.17 | 0.0631 | 4 |
| `bee-1-cpl` | **0.48** | **0.0249** | **5** |

**4 of 10 subject pairs are concordant** (one pair is tied on boundary and
cannot be). That is chance. Worse for the hypothesis, it is *anti*-correlated at
the extreme: `bee-1-cpl` has the **highest boundary and the lowest fine-structure
content of all five**. The subject that qualifies the finest bands is the one
with the least fine detail in its in-focus frames.

This is my own candidate explanation refuted by my own measurement, and it is
recorded rather than dropped because the refutation is what points at §5.4.

### 5.4 R's denominator explains the outlier, and nothing explains the ordering (MEASURED)

`R` is a ratio. It rises when the in-focus numerator is large **or** when the
defocused denominator collapses. Both terms are now recorded per band, each
normalised by the **same** per-subject coarse in-focus power `pf(0.05–0.08)` so
exposure and scene brightness divide out. At 0.30–0.40 cyc/px:

| subject | boundary | numerator `pf/pfc` | denominator `pd/pfc` | `R` |
| --- | ---: | ---: | ---: | ---: |
| `119MSDCF` | 0.25 | 1.0054 | 0.85257 | 1.273 |
| `leaf-2-cpl` | 0.20 | 0.21200 | 0.19358 | 1.068 |
| `113MSDCF` | 0.25 | 0.08412 | 0.06923 | 1.149 |
| `flower-bud-alone-cpl` | 0.17 | 0.06306 | 0.06118 | 1.035 |
| `bee-1-cpl` | **0.48** | **0.02491** | **0.01104** | **4.732** |

**For bee, the outlier, the denominator account is confirmed.** Bee has the
lowest value of *both* terms, but not by the same margin: its **numerator is
2.53× below the next-lowest subject while its denominator is 5.54× below the
next-lowest.** The denominator is anomalous by more than twice the factor the
numerator is. Bee's `R = 4.732` at a band where every other subject sits at
1.03–1.27 is therefore driven by a defocused reference that has emptied out, not
by an in-focus frame that is unusually rich — bee's in-focus fine power is in
fact the *smallest* in the sample (§5.3).

**This is not a claim that bee resolves finer.** It is a claim that bee's
defocused frames are emptier, which is what an isolated subject against a far
background produces. `R` cannot distinguish the two, and that is a limitation of
the qualification test itself rather than of this corpus.

**What it does not explain is the ordering.** Neither term alone orders the
boundary across the five subjects: **4 of 10 pairs concordant for the numerator,
4 of 10 for the denominator** — chance in both cases, the same as §5.3's texture
statistic. So after four candidates, the honest position is that the boundary is
firmly established to move (§4), the outlier's mechanism is identified, and **no
measured subject property predicts where a given subject's boundary will land.**

That is itself the operational answer to "with what": nothing available in
advance. A lane cannot look at a subject and infer its band. It has to run the
test.

---

## 6. An instrument defect found and fixed before publication

`boundary()` originally scanned every band in the record. The record carries
both `bandsignal.BANDS` and `bandsignal.FINE`, and `BANDS` contains the **wide**
band 0.10–0.20 alongside `FINE`'s 0.14–0.17 and 0.17–0.20.

On `flower-bud-alone-cpl` the wide band 0.10–0.20 PASSes at `R = 4.731`, while
its own top slice 0.17–0.20 is only MARGINAL at 2.015. The wide band passes on
content an octave below its own top edge, and the unrestricted scan therefore
reported a **0.20 boundary that subject does not have**.

This is the same error class as a wide-band acuity gate certifying a frequency
its own low end is carrying. `boundary()` now reads the `FINE` partition only,
and `_fine_partition()` hard-errors if `FINE` ever stops being contiguous, so the
definition cannot outlive its assumption.

**Effect of the fix:** `flower-bud-alone-cpl` 0.20 → **0.17**; the reported range
widened from 0.20–0.48 to **0.17–0.48**. Four subjects unchanged. The headline
verdict is unchanged and slightly strengthened.

**Commissioned** — `experiments/V-LINEAR/commission_boundary.py`, 5 arms, exit 0.
Arm 1 reproduces `flower-bud-alone-cpl`'s actual numbers and requires 0.17, so
the fix is shown to catch the real defect rather than an invented one. Arm 2
requires `leaf-2-cpl`'s shape to still return 0.20, so the fix cannot pass by
clamping everything down. Arm 5 mutates `FINE` into a non-partition and requires
the guard to raise.

One arm was **corrected after its first run, and the correction was to the arm**:
I expected a band 0.08–0.11 straddling the 0.10 gate to certify the sliver above
0.10, and it does not. The code is right — a straddling band cannot certify part
of itself any more than 0.10–0.20 could certify 0.17–0.20 — and my expectation
was mis-derived from the principle I had already written into the function. It is
logged in the file, because an expectation edited after seeing the output is
otherwise indistinguishable from moving the target.

### 6.1 Two reproduction hazards in the shared instrument

**Bootstrap CIs are call-order dependent.** `bandsignal.RNG` is module-level,
stateful and seeded once (`default_rng(20260827)`). `R` is therefore exactly
reproducible — measured `0.000e+00` absolute difference over **12/12** bands on
an independent re-run — but a CI depends on how many subjects were swept before
it. `leaf-2-cpl` swept **alone** versus swept **as one of five** moved the CI low
on **12/12** bands, with verdicts identical on all 12.

Whether that threatens a verdict has to be asked **per band against that band's
own jitter**, and getting this wrong produced a false alarm here worth recording.
Taking the worst CI movement across all 12 bands gives 0.1486, which is larger
than `leaf-2-cpl`'s 0.1387 margin to the 1.5 bar at 0.20–0.25 — apparently a
verdict at risk. It is not. That 0.1486 belongs to a coarse band whose CI low is
of order 80, where it is a relative movement of ~0.2%; comparing it to a fine
band's margin is not like-for-like. Per band:

| band | CI low | margin to 1.5 | own jitter | margin / own jitter |
| --- | ---: | ---: | ---: | ---: |
| 0.17–0.20 | 1.8998 | 0.3998 | 0.006686 | **59.8×** |
| 0.20–0.25 | 1.3613 | 0.1387 | 0.000731 | 189.8× |
| 0.25–0.30 | 1.1138 | 0.3862 | 0.000341 | 1133.6× |
| 0.30–0.40 | 1.0430 | 0.4570 | 0.000008 | 58451.8× |
| 0.40–0.48 | 1.0248 | 0.4752 | 0.000110 | 4311.6× |

**Zero cells sit within 10× of flipping.** The tightest is 59.8×.
`flower-bud-alone-cpl`'s 0.17–0.20 is the closest call in the whole table at CI
low 1.413, margin 0.087; measured against `leaf-2-cpl`'s 0.17–0.20 jitter as the
best available estimate — **a cross-subject transfer, and labelled as one, since
the single-subject control was only run on `leaf-2-cpl`** — that is 13×.

Still, **quote the subject list alongside any CI from this tool**, because the
guarantee is conditional on reproducing the same sweep.

### 6.2 The verifier for this document failed its own negative control

`verify_bands_doc.py` re-reads every number in §3 from the JSON. Its first
version tested whether each value appeared *anywhere in the document*. It read
**40 claims verified, 0 missing, exit 0** — and it still read exactly that after
the §3 cell `**4.874** PASS` was corrupted to `**4.875**`, because each `R` is
quoted in up to three tables and any surviving copy satisfied the check. Its
docstring claimed it anchored on the subject row; the code computed that anchor
into a variable and never used it.

Rewritten to bind every check to **one table row**, located by its leading
`` | `subject` | `` cell. Re-commissioned against four planted defects — the
sabotage that defeated v1, a CI upper bound, a kept-tile count, and a deleted
row — **4/4 caught, exit 1 each, exit 0 restored.** The document was backed up
to `%TEMP%` and restored from that copy, not from git.

*The generalisable point, and it is the same one as §6: a value quoted in three
places has no single site that can be falsified. Give each measured number one
canonical site, and pin each check to its own anchor.*

**A partial run could overwrite a full one.** A single-subject sweep wrote to the
same `bandsweep-far20.json` as the five-subject sweep and replaced it with one
row, with nothing in the file to show it was partial. Output filenames now encode
the subject subset. This was caught by running the control above, not by review.

---

## 7. What this does not establish

1. **Five subjects, chosen by what was on disk.** Not a random sample of the
   corpus and not a claim about the other 21 subjects. It is sufficient to refute
   "0.25 holds corpus-wide", which needs one counterexample and has four; it is
   not sufficient to state the corpus range.
2. **`R`'s magnitude is not cross-subject comparable** (§4). Only verdicts and
   boundaries are licensed by this document.
3. **No measured subject property predicts a subject's boundary.** Four
   candidates were tested and all four rejected (§5): stack depth, the defocus
   parameter, fine-structure content, and each term of `R` separately. The
   denominator account explains the *outlier* (§5.4) but not the ordering. A
   fifth candidate not tested here is optical magnification, which was not
   recoverable from the develops on disk.
4. **Nothing here measures strehl.** These are properties of the *source frames*.
   The document says which bands carry signal for a given subject; it says
   nothing about what any stacker does with them.
5. **Verdicts near the CI bar inherit §6.1's jitter**, but none is close: the
   tightest measured margin is 59.8× its own jitter, and the closest call in the
   table (`flower-bud-alone-cpl` at 0.17–0.20) clears by ~13× on a transferred
   jitter estimate. The single-subject reproduction control was run on
   `leaf-2-cpl` only.

---

## 8. Consequences for other lanes

- **A band must be qualified on the subject it is measured on.** `bandsignal.py`'s
  0.25 boundary is `113MSDCF`'s boundary. It is also `119MSDCF`'s. It is not
  `leaf-2-cpl`'s (0.20) and not `flower-bud-alone-cpl`'s (0.17).
- **No lane may use a fixed band across subjects.** This is the headline.
- **Sharpness claims on `leaf-2-cpl` and `flower-bud-alone-cpl` are limited to
  below 0.20 cyc/px.** Anything quoted at 0.20–0.25 or above on those two
  subjects is measuring noise.
- **A cross-subject ratio of `R` is not a thing this instrument supports** (§4).

---

*Instruments: `experiments/V-LINEAR/bandsweep.py` (measurement, this lane),
`experiments/V-LINEAR/bandanalysis.py` (every derived table in §4, §5 and §6.1;
reads only the saved JSON, so it cannot disagree with the measurement),
`experiments/V-LINEAR/commission_boundary.py` (5 arms, exit 0),
`experiments/V-LINEAR/verify_bands_doc.py` (re-reads §3 from the JSON; 4/4
planted defects caught),
`experiments/V-LINEAR2/bandsignal.py` (frozen, imported not reimplemented),
`experiments/V-LINEAR2/PREREGISTRATION.md:51` (decision rule).
Data: `experiments/V-LINEAR/bandsweep.json` (scaled `far`),
`bandsweep-far8.json`, `bandsweep-far20.json` (matched, the §3 table),
`bandsweep-far20-leaf-2-cpl.json` (the §6.1 reproduction control).*
