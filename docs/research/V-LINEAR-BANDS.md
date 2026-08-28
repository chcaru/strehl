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
other. Across the **eleven** subjects now measured (five in §3, six in §9) the
boundary takes **five distinct values** — 0.17, 0.20, 0.25, 0.30 and 0.48 — and
three subjects qualify **no band at or above 0.20 cyc/px**, so the 0.20–0.25
band that this project has quoted repeatedly is noise on them.

**The finest pyramid band is unqualified on the majority.** Band 0 of the merge
pyramid — the top octave, ≈0.25–0.50 cyc/px — carries signal on only **5 of 11**
subjects; on the other six it is noise or mixed (§10). Any acuity, sharpness or
gate result scored in band 0 alone is unlicensed until that subject is
qualified. §11 works one such result through end to end.

The spread is a property of the subjects, not of the instrument: it survives a
three-rung defocus ladder unchanged (§4), and every round-2 subject repeats its
boundary at both `far` rungs (§9.4). What the spread is *caused by* is
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

1. **Eleven subjects, chosen by what was on disk and by what depended on them.**
   Not a random sample of the corpus and not a claim about the remaining ~16
   subjects. It is sufficient to refute "0.25 holds corpus-wide", which needs one
   counterexample and now has **nine** (every subject except `113MSDCF` and
   `119MSDCF`); it is **not** sufficient to state the corpus range, and the
   round-2 six were selected precisely because decisions rested on them, which
   is the opposite of random.
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
5. **Verdicts near the CI bar inherit §6.1's jitter.** In §3 none was close: the
   tightest margin was 59.8× its own jitter. **Round 2 changed that** —
   `lavendar-cpl` sits at 1.490 and 1.501 against a 1.3/2.0 rule and
   `paper-sweep` PASSes 0.30–0.40 at 2.0015, 0.1% over the bar. Those three
   cells are flagged in §9.2 and **no lane should build on them**; the jitter
   study was run on `leaf-2-cpl` only and has not been repeated per subject.
6. **The develops for round 2 were not independently re-derived.** They come
   from the same decoder as round 1 by design (§9.6), which makes demosaic and
   white balance identical across subjects but means a decoder-level bias would
   be invisible to every row of every table here.

---

## 8. Consequences for other lanes

- **A band must be qualified on the subject it is measured on.** `bandsignal.py`'s
  0.25 boundary is `113MSDCF`'s boundary. It is also `119MSDCF`'s. It is not
  `leaf-2-cpl`'s (0.20), not `flower-bud-alone-cpl`'s (0.17), not `112MSDCF`'s
  (0.20), not `lavendar-cpl`'s (0.30), and not the 0.48 of the five subjects
  that qualify to Nyquist.
- **No lane may use a fixed band across subjects.** This is the headline.
- **Band 0 (0.25–0.50 cyc/px) is unqualified on 6 of 11 subjects** (§10). Any
  acuity, micro-contrast or gate result scored in band 0 alone is unlicensed
  until its subject is qualified. §11 works one such result through end to end.
- **Sharpness claims on `leaf-2-cpl`, `flower-bud-alone-cpl` and `112MSDCF` are
  limited to below 0.20 cyc/px.** Anything quoted at 0.20–0.25 or above on those
  subjects is measuring noise.
- **The four halo subjects are qualified, and three of them generously.**
  `flat-on-ruler-cpl`, `tweezers-cpl` and `dry-erase-marker-head-cpl` qualify to
  **0.48**, so V-SPEED may score its halo fix at any band up to Nyquist on them.
  `lavendar-cpl` qualifies only to **0.30** and its 0.30–0.48 cells are on the
  line (§9.2) — score that subject at or below 0.30.
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

---

## 9. Round 2 — six more subjects (MEASURED)

Requested by ORCH after §3 landed, on the grounds that the subjects §3 did *not*
cover were the ones about to change the product. Same instrument, same frozen
`bandsignal.py`, same pre-registered rule. The reading rules were fixed in
`experiments/V-LINEAR/PREREG-R2.md`, committed at `d6e4ab47` **before any
round-2 subject was swept**.

### 9.1 Which subjects, and why

| subject | why it is here |
| --- | --- |
| `112MSDCF` | carries ORCH's band-0 gate-floor arm (32.1% -> 80.9% averaged duty cycle) and was absent from §3, so a candidate default rested on an unqualified band |
| `flat-on-ruler-cpl` | fails the halo measurement (fact 1841, overshoot **+4481.8 DN**) |
| `tweezers-cpl` | fails the halo measurement (bump **1542.3**) |
| `lavendar-cpl` | marginal on the halo measurement |
| `dry-erase-marker-head-cpl` | marginal on the halo measurement |
| `paper-sweep` | **not on ORCH's list.** `flat-fields\subject-focus-sweep-with-cpl`, 62 frames. It is the *structure* side of fact 1826's self-targeting claim and the only subject on that side, and it had never been band-qualified — the claim rested on a duty cycle and a visual crop. See §11. |

The four halo subjects are the ones V-SPEED must score its halo fix on, and it
needs a qualified band to do that.

**Nothing was dropped.** All six sampled subjects appear below, including
`lavendar-cpl`, whose two top bands land 0.010 and 0.001 either side of the
MARGINAL floor and are the least comfortable cells in this document.

### 9.2 The table (MEASURED, `far` = 20)

Rule: **PASS** = `R >= 2.0` and CI low `>= 1.5`; **MARG** = `1.3 <= R < 2.0`;
**FAIL** = `R < 1.3`. `R` is in-focus over defocused band power, CONFIRMED
population.

| subject | N | st | kept | 0.17–0.20 | 0.20–0.25 | 0.25–0.30 | 0.30–0.40 | 0.40–0.48 | boundary |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: |
| `112MSDCF` | 79 | 1 | 30 | **3.012** PASS | **1.724** MARG | **1.202** FAIL | **1.089** FAIL | **1.049** FAIL | **0.20** |
| `flat-on-ruler-cpl` | 79 | 1 | 30 | **104.037** PASS | **36.314** PASS | **11.415** PASS | **4.154** PASS | **2.774** PASS | **0.48** |
| `tweezers-cpl` | 100 | 1 | 27 | **196.995** PASS | **81.304** PASS | **24.548** PASS | **8.360** PASS | **5.409** PASS | **0.48** |
| `lavendar-cpl` | 300 | 4 | 25 | **15.535** PASS | **6.202** PASS | **2.435** PASS | **1.490** MARG | **1.501** MARG | **0.30** |
| `dry-erase-marker-head-cpl` | 300 | 4 | 24 | **117.666** PASS | **35.900** PASS | **9.665** PASS | **4.877** PASS | **6.647** PASS | **0.48** |
| `paper-sweep` | 62 | 1 | 30 | **22.551** PASS | **8.699** PASS | **3.203** PASS | **2.002** PASS | **2.066** PASS | **0.48** |

Confidence intervals on the two bands most often quoted:

| subject | 0.17–0.20 R [CI] | 0.20–0.25 R [CI] |
| --- | --- | --- |
| `112MSDCF` | 3.012 [2.363, 3.890] | 1.724 [1.476, 2.043] |
| `flat-on-ruler-cpl` | 104.037 [77.615, 134.825] | 36.314 [28.585, 44.837] |
| `tweezers-cpl` | 196.995 [157.975, 243.732] | 81.304 [61.367, 106.052] |
| `lavendar-cpl` | 15.535 [8.985, 22.485] | 6.202 [3.705, 8.866] |
| `dry-erase-marker-head-cpl` | 117.666 [64.739, 192.078] | 35.900 [19.714, 56.562] |
| `paper-sweep` | 22.551 [19.583, 25.738] | 8.699 [7.451, 10.016] |

**Three cells that must not be leaned on**, stated here rather than left for a
reader to find:

- `paper-sweep` 0.30–0.40 PASSes at **R = 2.0015**, 0.1% above the 2.0 bar.
- `lavendar-cpl` 0.30–0.40 is MARG at **1.490** and 0.40–0.48 at **1.501** —
  the second sits 0.001 above the 1.5 CI-low bar's numeric neighbourhood and is
  MARGINAL only because `R < 2.0`. Both are effectively on the line.
- `dry-erase-marker-head-cpl` 0.40–0.48 (**6.647**) is *higher* than 0.30–0.40
  (**4.877**). A band ratio rising toward Nyquist is not physical for a
  detail signal and most likely reflects aliasing of the marker's printed edge.
  The subject's boundary does not depend on it (0.25–0.30 already PASSes at
  9.665), but the cell itself should not be quoted as a detail measurement.

### 9.3 N is overstated by one on the two decimated subjects (KNOWN, cosmetic)

`lavendar-cpl` and `dry-erase-marker-head-cpl` both have **299** source frames.
The table reports **300**, because `n_real` is computed as `n_dev * decim` =
`75 * 4` and 299 is not a multiple of 4. The measurement reads the 75 develops
that exist and is unaffected; only the printed N is wrong, by one frame out of
299. It is recorded rather than silently corrected because a number in a
published table that is wrong by one is still wrong, and a reader comparing this
against `D:\personal\macro` will find the discrepancy.

### 9.4 The `far` ladder control (MEASURED)

Every round-2 subject swept at `far` = 20 and `far` = 8. If a boundary moved
with the defocus offset it would be a property of the ladder rather than of the
subject and would have to be reported as indeterminate.

| subject | boundary @ far=20 | boundary @ far=8 | verdict |
| --- | ---: | ---: | --- |
| `112MSDCF` | 0.20 | 0.20 | same |
| `flat-on-ruler-cpl` | 0.48 | 0.48 | same |
| `tweezers-cpl` | 0.48 | 0.48 | same |
| `lavendar-cpl` | 0.30 | 0.30 | same |
| `dry-erase-marker-head-cpl` | 0.48 | 0.48 | same |
| `paper-sweep` | 0.48 | 0.48 | same |

**6/6 unchanged**, matching the 5/5 of §4. Eleven subjects have now held their
boundary across at least two defocus offsets.

### 9.5 Decimation, commissioned before use (MEASURED)

The two 299-frame subjects were developed at stride 4 (75 develops each) because
developing all five subjects in full would have needed ~163 GB against ~107 GB
free. `bandsweep.py --decim k` is then told the on-disk set is every k-th frame
of a k-times longer stack, so `far` stays in **real** frame units.

The protocol was commissioned against the expensive one it replaces, with the
expectation fixed in advance: `--simdecim 2` on `leaf-2-cpl` reads the *same 91
frames* as the full 182-develop run, so `R` and CI must match to every printed
digit.

```
n_real   full=182  decim=182   ok        kept  full=30  decim=30  ok
step     full=2    decim=2     ok        bands differing: 0/12
```

**Digit-exact on 12/12 bands.** Run `python bandsweep.py --far 20 --simdecim 2
leaf-2-cpl` and compare against `bandsweep-far20-leaf-2-cpl.json` to reproduce.

### 9.6 The develops are comparable to round 1's, and that was measured (MEASURED)

Round-1 develops were written by an older binary and the working tree was dirty
(`d35f905533e2-dirty`, another lane's uncommitted changes) when round 2 ran. If
the develop path had moved, round-2 numbers would not be comparable to §3's.

`leaf-2-cpl/DSC00001.ARW` was developed by the pin `740e7056`
(`15EA73461905EA2D`) and by dirty HEAD (`F1D66AD7220DCC6C`) and both compared
against the round-1 develop already on disk. All three decode **bit-identical**:
0 differing pixels of 99,010,560, maxabs 0, all three means 2104.1348.

**The trap that measurement stepped over:** the three files have three
*different* byte lengths — 198023952, 198023947, 198023958. A file-hash
comparison would have reported three different develops and the wrong conclusion
that the binary matters. The difference is TIFF metadata. This is why the
standing rule is to compare decoded arrays and never file hashes.

The pin is used for the round-2 develops anyway, because it **cannot move**;
dirty HEAD is equivalent today but belongs to another lane that may rebuild it
mid-run.

### 9.7 Clipping control (MEASURED)

A band ratio measures relationships between neighbouring pixels, and a saturated
region has none — so a blown develop reads as "no signal in any band", which is
exactly the verdict returned for `112MSDCF` at 0.25–0.50. Under ORCH's exposure
regression that would have been an artifact of the render rather than a property
of the subject, so it was measured before being believed:

```
DSC00001.tif  median=611  mean= 834.4  max= 8438  clipped_hi=0.000%
DSC00040.tif  median=567  mean= 856.5  max=34153  clipped_hi=0.000%
DSC00079.tif  median=598  mean= 838.9  max= 8306  clipped_hi=0.000%
```

**0.000% clipped**, max 8438 of 65535. The develops carry `--linear-srgb` with
no `--srgb`, no `--exposure` and no `--auto-exposure`, so the dark medians are
expected and are not clipping. This lane is **case 3** of ORCH's exposure
broadcast: rendered at a pinned binary, without `--auto-exposure`.

---

## 10. Band 0 is unqualified on the majority (MEASURED)

The merge pyramid's finest band — band 0, the top octave, ≈**0.25–0.50 cyc/px** —
is where every "acuity" and "micro-contrast" number in this project's recent
work has been scored. Across all eleven subjects:

| subject | 0.25–0.30 | 0.30–0.40 | 0.40–0.48 | band 0 |
| --- | ---: | ---: | ---: | --- |
| `112MSDCF` | 1.202 | 1.089 | 1.049 | **NOISE** |
| `flower-bud-alone-cpl` | 1.108 | 1.035 | 1.066 | **NOISE** |
| `leaf-2-cpl` | 1.171 | 1.068 | 1.040 | **NOISE** |
| `113MSDCF` | 1.387 | 1.149 | 1.105 | mixed |
| `119MSDCF` | 1.624 | 1.273 | 1.242 | mixed |
| `lavendar-cpl` | 2.435 | 1.490 | 1.501 | mixed |
| `paper-sweep` | 3.203 | 2.002 | 2.066 | SIGNAL |
| `bee-1-cpl` | 10.728 | 4.732 | 3.629 | SIGNAL |
| `dry-erase-marker-head-cpl` | 9.665 | 4.877 | 6.647 | SIGNAL |
| `flat-on-ruler-cpl` | 11.415 | 4.154 | 2.774 | SIGNAL |
| `tweezers-cpl` | 24.548 | 8.360 | 5.409 | SIGNAL |

**Signal on 5 of 11; noise or mixed on 6.** `NOISE` means every FINE slice of
band 0 FAILs; `mixed` means at least one slice fails and none of the failing
ones reach PASS.

**Consequence.** A result scored in band 0 alone is unlicensed until its subject
appears in the SIGNAL group. This is retroactive and it does not spare this
lane: the three NOISE subjects include `leaf-2-cpl`, which this lane's own
item-2 gate-floor comparison uses, and that comparison is therefore restricted
to below 0.20 cyc/px.

---

## 11. The gate-floor adjudication — a worked example of the above (MEASURED + ARGUED)

This section exists because the band-0 result immediately threatened a live
tuning decision, and the reasoning is more transferable than the verdict.

### 11.1 What was asked

ORCH's candidate knob `STREHL_GATE_FLOOR_SCALE=4,1,1,1,1,1,1` raises the
band-0 noise-gate floor 4x. Fact 1824 measured on `112MSDCF`: band-0 averaged
duty cycle **32.1% -> 80.9%**, **FLAT high-pass std x0.2717** (73% less grain),
**EDGE high-pass std x0.9108** (9% cost), flat sites **-206.7 DN**. Fact 1826
added a second subject, the backlit-paper sweep, where the same setting moves
the duty cycle only **0.0% -> 1.1%**, and called the knob *self-targeting*.

ORCH set a kill criterion: *"if the benefit is present exactly where the band is
noise, the knob is fitting grain and I will revert the default."*

### 11.2 What was measured

`112MSDCF` band 0 is **NOISE** — 1.202 / 1.089 / 1.049, and all three CIs lie
entirely below the 1.3 MARGINAL floor. The knob's whole measured benefit is
therefore in a band carrying no signal on that subject. The criterion is
**literally satisfied.**

The other side had never been measured, so this lane developed and swept it:
`paper-sweep` band 0 is **SIGNAL** — 3.203 / 2.002 / 2.066, all PASS
(§9.2). Fact 1826's contrast is real, and now rests on band qualification on
both sides rather than a duty cycle and a visual crop on one.

### 11.3 The criterion was refused, and ORCH withdrew it

**The inference does not follow from the criterion.** "Fitting grain" means
manufacturing or preserving detail derived from noise. What is measured is the
*removal* of content from a band that carries no signal, together with
near-zero action on a band that does. That is a correctly targeted denoiser, not
a grain-fitter. The discriminating question is **not** where the benefit
appears, it is **whether qualified bands are damaged.**

ORCH withdrew the criterion and adopted the replacement. Recorded here because
the reasoning should survive both of us:

> **Superseded:** "benefit present where the band is noise" => fitting grain.
> **In force:** does the knob damage bands that qualify as signal?

### 11.4 On the replacement criterion there is a real answer, and it disqualifies the aggressive setting

At **64x**, fact 1826 measured the paper sweep losing **25% of its band-1
structural energy** (EDGE ratio 0.7505) with fibres visibly smeared. Band 1 on
that subject is now qualified: 0.17–0.20 **R = 22.551**, 0.20–0.25 **R = 8.699**,
both PASS. So the 25% is **structural damage in a qualified band on a real
subject** — a print-quality defect, not a tuning cost.

**ADOPTION VERDICT (ORCH, on this evidence): not adopted at any aggressive
scale; 64x disqualified outright; the inert default stands.**

### 11.5 Two corrections this produced, both against the lane that asked

- **The 9% edge cost at 4x is not a licensed structural cost.** It is measured
  in band 0, which on `112MSDCF` is noise. On that subject *both* the 73%
  benefit and the 9% cost are measurements of noise. This cuts in the knob's
  favour on cost and against it on benefit: the 73% is grain removal, not a
  detail gain.
- **The knob was never a shipping default.** `gatefloor.rs` documents
  `STREHL_GATE_FLOOR_SCALE` unset as "no scaling and is a byte-exact no-op", and
  no ship recipe under `experiments/`, `scripts/` or `docs/` sets it. There was
  nothing to revert — only a decision not to adopt. `STREHL_GATE_FLOOR`
  (measured floor vs `white`) is a *different* knob, is defaulted on, and is
  separately motivated by BUILD-GATE's 0.3432–0.9981 measurement.

### 11.6 What this adjudication does NOT establish

**n = 2.** One subject on each side. The three strongest band-0 qualifiers —
`tweezers-cpl` (24.548), `flat-on-ruler-cpl` (11.415), `bee-1-cpl` (10.728) —
have `R` **3–8x above** `paper-sweep`'s 3.203 and **the knob has never been run
on any of them**. Inertness on the weakest qualifier suggests inertness on
stronger ones, but that is inference, not measurement, and it is the direction
that flatters the knob. The self-targeting claim should not be strengthened
beyond two subjects without running them.

---

## 12. How to re-run this, and what checks it passes

### 12.1 Re-running a subject

```
# 1. develop linear per-frame TIFFs with the PINNED decoder
powershell -ExecutionPolicy Bypass -File experiments/V-LINEAR/r2_develop.ps1 `
    -Key <subject> [-Stride <n>]

# 2. sweep it (ONE subject per invocation -- see the RNG note below)
python experiments/V-LINEAR/bandsweep.py --only <subject> --far 20
python experiments/V-LINEAR/bandsweep.py --only <subject> --far 8    # ladder control
```

The develop binary is pinned to `740e7056`, sha256 `15EA73461905EA2D`, and every
round-2 develop was produced by it. §9.6 measures that this pin, the dirty
working tree and the round-1 develops agree **bit-exactly** on decoded pixels
(0 differing of 99,010,560, maxabs 0) while producing **three different file
lengths** — so compare decoded arrays, never file hashes.

**One subject per invocation is not a style preference.** `bandsignal.py:69`
seeds `np.random.default_rng(20260827)` at module level, so the bootstrap CIs
depend on call order. §6.1 measures the size of that: `leaf-2-cpl` swept alone
versus swept as one of five moves the CI low by 0.007. The point estimates do
not move. This is why `bandsweep-far20-leaf-2-cpl.json` disagrees with
`bandsweep-far20.json` and is declared a control rather than a record.

### 12.2 The rule, unchanged since round 1

Frozen at `experiments/V-LINEAR2/PREREGISTRATION.md:51-52`:
**PASS** = `R >= 2.0` **and** CI low `>= 1.5`; **MARGINAL** = `1.3 <= R < 2.0`;
**FAIL** = `R < 1.3`. The boundary is the top edge of the highest contiguous
run of non-FAIL FINE bands. It was not adjusted after seeing any round-2 number,
and round 2 was pre-registered in `experiments/V-LINEAR/PREREG-R2.md`, committed
`d6e4ab47` **before the first subject was swept**.

### 12.3 Checks this document passes

| check | command | result |
| --- | --- | --- |
| every number in §3/§9 tables traces to a saved JSON | `python experiments/V-LINEAR/verify_bands_doc.py` | **88/88** located-and-correct, 0 wrong, 0 unresolved |
| that verifier actually catches corruption | `python experiments/V-LINEAR/commission_verify_doc.py` | **7/7 caught**, 0 missed, document restored byte-identical |
| `boundary()` is not trivially satisfiable | `python experiments/V-LINEAR/commission_boundary.py` | **5/5** arms as expected |
| corpus discipline | `python scripts/corpus_lint.py --root .` | OK, no violations |

**The verifier has now failed twice and both failures were found by running it.**
Version 1 read **40/40 GREEN on a document it had corrupted**, because each `R`
is quoted in three tables and the check tested presence anywhere in the file.
Version 2, rewritten row-anchored, then broke the moment §9.1 and §10 added two
more subject-keyed tables: its row selection was **positional** (`rows[0]`,
`rows[1]`), so `rows[0]` silently became a prose row and all 50 round-2 checks
read WRONG against a row that never carried numbers. Version 3 anchors on row
**shape** and requires exactly one match, reporting ambiguity as unresolved
rather than resolving it to whichever came first.

A third defect appeared in the loader in the same hour: globbing
`bandsweep-far20*.json` pulled in the §6.1 reproduction control and shadowed the
canonical `leaf-2-cpl` record, so the verifier reported the document wrong when
the document was right. The fix is not a list of excluded filenames but a rule —
**agreement is not ambiguity, disagreement is.** A key present in two files whose
values match is accepted silently (`bandsweep-far20-noPF.json` repeats all five
round-1 subjects and was measured to agree to 1e-9 on all 60 of its `R` values);
a key whose values differ is a hard error.

All three are the same failure: **a check satisfied by the wrong instance of the
right-looking thing.** That is the third distinct sighting of this class in this
lane alone, alongside `boundary()`'s original defect and `contrast_ms.py`'s
Gaussian cut-off error.
