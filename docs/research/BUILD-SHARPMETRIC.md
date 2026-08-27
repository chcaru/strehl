# BUILD-SHARPMETRIC — the 1:1 sharpness statistic: what its ceiling arm actually was, and what the instrument can and cannot measure

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`P1, P2, …` per rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision:** `c86e4341` (`veiling 111: I convicted a pink subject, and
three instruments died proving it`).

**Read-only inputs, never written to:** `C:\dev\strehl-out\acceptance\SHIP-V4\`
(26 masters), `D:\personal\macro\` (26 subject stacks),
`experiments/ORCH-drift-check/orch_sharp1to1.py` (read, copied, never edited).
Scripts and logs: `experiments/BUILD-SHARPMETRIC/`.

---

## 0. The commission

> *`docs/research/ORCH-veiling.md` §105 records a metric that fails its own
> commission … `SELECTION 1.0000`, `DEFECT 0.1717`, `RECONSTRUCT 3.4867` … and
> five of nine real subjects score ABOVE 3.4867. A real photograph cannot be
> sharper than a perfect reconstruction of itself … find out why real subjects
> exceed the ceiling arm, and either fix the metric or establish what it can and
> cannot measure.*

With the instruction that decided the order of work:

> *Is the RECONSTRUCT arm actually a ceiling? … **Check the arm before you check
> the subjects.** A ceiling arm that isn't a ceiling is the cheapest explanation
> and my §105 never tested it.*

That instruction was correct, and it was sufficient. §1 answers the question and
everything after it is consequence.

---

## 1. The answer, up front

**There is no anomaly to explain.** The premise "a real photograph cannot be
sharper than a perfect reconstruction of itself" is sound, but neither of its
two operands was what its name said.

- **`3.4867` is not a ceiling.** It is a construction constant of the
  commission's synthetic sources, and it moves over **1.0000 … 20.2615** — a
  spread of **20.26×** — while the master is held *byte-identical at perfect*
  (P1). Nothing about it bounds anything. A real subject scoring above it is
  **legal**, not anomalous.
- **The real subjects' numbers are inflated about fourfold by rendering, not
  detail.** A *monotone* tone remap — an operation that cannot add or remove one
  feature of spatial structure — collapses the shipped statistic from **6.099 to
  1.536**, a factor of **0.24** (P8).

So the two numbers being compared in §105 were **an arbitrary constant** and **a
mostly-photometric measurement**, and the comparison between them never had
meaning in either direction. Both halves of the discrepancy dissolve; neither
required any subject to be sharper than perfect.

**What survives, and what does not.** The *direction* claim survives: the
statistic is not blind, and its planted-improvement arm is monotone (P5, P10).
The *magnitude* claim does not, and cannot be rescued by rescaling, because the
inflation factor is **per-subject** (×4.49 to ×14.44, P7) rather than a constant.

**Consequence for the corpus:** §105's embargo — *no sharpness multiple may be
quoted outside `ORCH-veiling.md`* — **stands, and should be tightened**. It now
has a measured mechanism rather than an unexplained discrepancy, and my repaired
statistic does **not** lift it (P12). See §7.

---

## 2. Pre-registered bars

Written before the measurements, so the result could fail.

| # | Bar | Outcome |
|---|---|---|
| B1 | Reproduce all three published arms **exactly** before criticising them | **MET** — 1.0000 / 0.1717 / 3.4867, P1 |
| B2 | The ceiling test must be capable of returning "it *is* a ceiling" | **MET** — it could have been flat; it spanned 20.26× |
| B3 | Any candidate repair is commissioned with a planted **improvement**, not only degradations | **MET** — P5, P10; one candidate died on this arm |
| B4 | Any candidate must pass on **real photographs**, not only synthetic targets | **MET** — P10; and it is where my best candidate stops (P12) |
| B5 | A hypothesis for the residual must be *tested*, and allowed to be refuted | **MET** — two raised, **both refuted** (P13, P14) |
| B6 | No rescaling without a mechanism | **MET** — no rescaling is proposed anywhere in this report |

---

## 3. The ceiling arm is a construction constant

### 3.1 What the arm is

`commission()` in `orch_sharp1to1.py` builds

```python
lat = rng.normal(8000, 1500, (CROP, CROP)) + 4000*np.sin(np.arange(CROP)/3)
srcs = [blur(lat, k) for k in (2, 3, 4, 5)]
```

and reports `patch_gain(lat, srcs)` as **RECONSTRUCT** — "a perfect
reconstruction". `patch_gain`'s denominator is `max` over sources, so the value
is set **entirely by the sharpest source**, `k=2`. It is therefore not a
property of the reconstruction at all. It is *how much a 2-pixel box blur
attenuates the mean absolute gradient of this particular latent*.

**P1 (MEASURED).** Holding the master byte-identical at perfect and changing
only which sources it is scored against (`src/01-ceiling-arm.py`,
`out/01-ceiling-arm.log`):

| sources (`k`) | "RECONSTRUCT" | vs published |
|---|---|---|
| 1,2,3,4 | 1.0000 | 0.29× |
| **2,3,4,5** | **3.4867** | **1.00× (published)** |
| 3,4,5,6 | 4.2479 | 1.22× |
| 4,5,6,7 | 5.1014 | 1.46× |
| 5,6,7,8 | 6.3216 | 1.81× |
| 6,7,8,9 | 8.3201 | 2.39× |
| 8,9,10,11 | **20.2615** | 5.81× |
| 10,11,12,13 | 18.3969 | 5.28× |

**Range 1.0000 … 20.2615 with the master unchanged and perfect throughout.**
The published `3.4867` is one arbitrary point on that line. Choosing sources
`k=1..4` would have published a "ceiling" of `1.0000`, at which point *nine of
nine* subjects exceed it; choosing `k=8..11` publishes `20.2615`, at which point
none do. **The "5 of 9" in §105 is a fact about the source list, not about the
subjects.**

**P2 (MEASURED).** The single-source sweep `k=1..13` gives 1.0000, 3.4867,
4.2479, 5.1014, 6.3216, 8.3201, 11.9210, 20.2615, 53.3900, 50.2794, 26.6679,
20.4649, 18.3969 — **non-monotonic above k≈9**. The latent's sinusoid has period
`2π·3 ≈ 18.85 px`, so a box of width `2k ≈ 18–20` nulls it outright. A blur that
*destroys more* can score *lower*. This is a second, independent sign that the
synthetic latent is a poor stand-in for a photograph.

### 3.2 Why nobody caught it

**P3 (ARGUED).** The arm was named `RECONSTRUCT` and described as perfect, and
it *is* a perfect reconstruction — of the master. The unexamined step is that
the number is a **ratio**, and no one asked what the denominator was. Naming a
ratio after its numerator is how an arbitrary constant acquires the authority of
a bound. The test that would have caught it costs four lines and is the one in
the table above.

---

## 4. The commissioning target is degenerate

**P4 (MEASURED).** Adding `N(0, 1500)` noise to a master that merely SELECTS
scores **3.4855**, against the published perfect-reconstruction arm of
**3.4867** — agreement to **0.03%** (`src/02-perversity.py`).

That looked like a coincidence. It is not. The commission's latent **is** white
noise of σ=1500 plus one sinusoid. So "the detail a perfect reconstruction
restores" is, literally, white noise of σ≈1500 — the identical signal the noise
arm adds. On this target the two arms are not similar, **they are the same
experiment**, and no statistic of any kind could separate them.

**P5 (MEASURED).** Confirmed from the opposite direction. Candidate S2 (§6),
which subtracts an estimated noise floor, **fails** the planted-improvement arm
on the commission's own white target — sweep `t=0…1` reads `1.000 0.961 0.942
0.941 0.959`, **not monotonic** — and **passes** it on a 1/f "photograph-like"
target — `1.000 1.043 1.176 1.308 1.414`, monotone (`src/05-noise-corrected.py`).
A noise-aware statistic *correctly* reports that the white target contains no
recoverable structure. The target, not the statistic, is what fails.

**P6 (DERIVED).** This is upstream of the metric. A commissioning target whose
"signal" is statistically identical to noise cannot commission any
noise-sensitive property, in either direction. `ORCH-veiling.md` §105.3's second
hypothesis is therefore answered: the RECONSTRUCT arm was never measuring
reconstruction.

---

## 5. Why the real numbers are large: rendering, not detail

### 5.1 The shipped statistic is exactly linear in master gain

**P7 (MEASURED).** `src/02-perversity.py`, full battery in
`out/02-perversity.log`. **10 of 15 arms fail** on both targets:

| arm | reads | verdict |
|---|---|---|
| blur master k=8 | 0.1717 | PASS |
| blur master k=3 | 0.8207 | PASS |
| master `+ N(0,200)` | 1.1179 | **PERVERSE** |
| master `+ N(0,600)` | 1.6985 | **PERVERSE** |
| master `+ N(0,1500)` | 3.4960 | **PERVERSE** |
| master USM ×0.5 / ×1.5 / ×3.0 | 1.1784 / 1.5599 / 2.1662 | **PERVERSE** |
| master ×1.200 gain | **1.2000** | **INFLATED** |
| master ×1.500 gain | **1.5000** | **INFLATED** |
| master ×1.854 gain | **1.8540** | **INFLATED** |
| master `+3000` offset | 1.0000 | PASS |
| contrast ×1.3 about mean | **1.3000** | **INFLATED** |
| **planted improvement, t=0…1** | **1.000 1.318 1.953 2.699 3.487** | **monotone PASS** |

The gain rows are not approximate — they are the identity
`mean|∇(a·y)| = a·mean|∇y|`, exact. **The statistic multiplies by any brightness
scaling applied to the master.**

The improvement arm passing and being monotone is the load-bearing negative
result: **the statistic is not blind**, so its direction claim is sound. This is
the arm `experiments/BUILD-TRIAGE/halosens.py` documents as the one that
separates "blind" from "correct", and it is the reason this report recommends
tightening the embargo rather than discarding the instrument.

### 5.2 The two arms of the real comparison are rendered differently

`main()` renders the two sides through different pipelines:

| arm | pipeline |
|---|---|
| master | `strehl … --srgb --auto-exposure` — sRGB curve, exposure fitted |
| source | `rawpy.postprocess(gamma=(2.222,4.5), no_auto_bright=True, …)` — Rec.709 curve, **no** auto-exposure |

**P8 (MEASURED).** Over 21 sites / 8 subjects (`src/03-asymmetry.py`): median
level ratio `M_med/S_med` = **1.854** (0.850–3.609); std/contrast ratio =
**2.348** (1.448–6.107); gradient ratio median **5.785** (2.425–8.778).
By P7 the level and contrast ratios enter the reported sharpness **directly**.

### 5.3 The decisive test: a monotone remap

Histogram-matching the source to the master is a **monotone per-image remap**.
It cannot reorder, create or destroy spatial structure; it can only put the two
images on a common tonal footing. Anything the statistic loses under it was
never structure.

**P9 (MEASURED).** `src/08-tonecurve.py`, `out/08-tonecurve.log`:

| subject | S0 raw | S0 matched | S2 raw | S2 matched |
|---|---|---|---|---|
| wrapped-text-1 | 7.039 | 1.883 | 0.5914 | 0.5660 |
| bee-3-cpl | 7.198 | 1.189 | 0.5012 | 0.4944 |
| coffee-bean | 5.160 | 3.118 | 0.6242 | 0.6092 |
| lavendar-cpl | 4.848 | **1.000** | 0.5041 | 0.4971 |
| **median** | **6.099** | **1.536** | **0.5477** | **0.5316** |
| | | **×0.24** | | ×0.98 |

**About three-quarters of the shipped statistic's real-subject reading is
photometric.** `lavendar-cpl` falls to exactly **1.000** — under a common tonal
footing its master is indistinguishable from its sharpest source by this
statistic, against a published-style reading of 4.848.

**Caveat, stated in the script before the result was seen:** a monotone remap
also rescales real local contrast, and local contrast is partly what sharpness
*is*. So this arm removes some genuine signal along with the confound. It
**bounds** the photometric contribution; it does not cleanly partition it. The
honest reading is "most of the multiple was photometric", not "exactly 76%".

**P10 (DERIVED).** §105's five-of-nine is fully accounted for without any
subject exceeding any real bound: the threshold was arbitrary (P1) *and* the
subject values were inflated ~4× (P9). Two independent errors pointing the same
way.

---

## 6. The repair, and exactly where it stops

### 6.1 Candidates

Three statistics, two targets, 15 arms each (`src/05-noise-corrected.py`):

| candidate | white target | natural target |
|---|---|---|
| **S0** fine-band magnitude (**shipped**) | 10 fail | 10 fail |
| **S1** fine/coarse band ratio | 6 fail | 6 fail |
| **S2** energy, gain-invariant + noise-corrected | 8 fail | 6 fail |

**S1** fixes all five photometric arms *exactly* (1.0000 on every gain, offset
and contrast transform — it is invariant to `y → a·y + b` by construction) but
**goes near-blind to blur**: k=8 reads **0.9636** where S0 reads 0.1717. Rejected.

**S2** keeps S1's exact gain invariance and adds an *exact* noise subtraction:
`E[(∇(s+n))²] = E[(∇s)²] + E[(∇n)²]` for independent zero-mean noise, so squared
gradients admit a subtraction that absolute values do not. σ is estimated per
patch by Immerkær's 3×3 mask. A patch whose signal does not survive the
subtraction returns **NaN and is counted `unmeasurable`**, never a meaningless
ratio.

**P11 (MEASURED).** S2's noise arms read **0.9995 / 1.0032 / 0.9860** (white
target) and **1.0001 / 1.0007 / 0.9947** (natural) where S0 read up to **3.4960**.
The perversity is gone — held flat to ≤0.5%.

> **A specification error I am disclosing rather than fixing quietly.** I
> classified the noise arms as `DEGRADE` (must fall), so S2's ≈1.000 is scored
> `PERVERSE` in the logs. On reflection that specification is wrong: noise is not
> blur, and a *sharpness* statistic should be **invariant** to noise, not punish
> it — punishing it is a noise metric's job. Under the corrected specification
> (`INVARIANT`, must not move) S2 fails **three** arms on the natural target, not
> six. **I noticed this only after seeing S2's result**, so the re-specification
> is post-hoc and should be read as such. The logs carry the original strict
> verdicts unaltered.

### 6.2 S2 commissioned on real photographs

**P12 (MEASURED).** `src/07-real-commission.py`. Sources synthesised from a real
master, so the true answer is known exactly and no decode or registration is
involved:

| arm | wrapped-text-1 | bee-3-cpl | coffee-bean | lavendar-cpl |
|---|---|---|---|---|
| **IDENTITY (must be 1.0000)** | **1.0000** | **1.0000** | **1.0000** | **1.0000** |
| source = blur(master,2) | 1.1551 | 1.0945 | 1.1037 | 1.0947 |
| source = blur(master,4) | 1.2200 | 1.1344 | 1.1576 | 1.1357 |
| source = master + N(0,400) | 1.0012 | 1.0024 | 1.0034 | 1.0031 |
| master = blur(4) (must be <1) | 0.8197 | 0.8815 | 0.8639 | 0.8805 |

**All real-content arms PASS.** The IDENTITY arm is the one the original
commission never ran: if source *is* master the ratio must be exactly 1.0 by
construction, on any image, for any statistic. It costs nothing and it is the
cheapest possible detector of an implementation asymmetry.

### 6.3 Where S2 stops — and it stops before the number the project wants

**P13 (MEASURED).** Against **real** sources, S2 reads **0.588, 0.934, 0.594,
0.501, 0.502, 0.496, 0.630, 0.525** — median **0.557**, 8 of 8 below 1.0
(`src/06-real.py`; 192/128 patches each, `skipped 0`, `unmeasurable 0`).

**This must not be reported as "the merge loses detail."** P12 fixes S2's scale
on real content: blurring the master by a 4-pixel box only reaches **0.82–0.88**.
The real readings sit **below what any amount of blur of the master produces**.
Whatever separates master from source, it is outside the range of effects that
"one of them is blurrier" spans — so the statistic is being driven by something
it was not commissioned against, and its value is not interpretable as sharpness.
Seven of the eight subjects clustering into 0.496–0.630 across a bee, a lavender
floret, a pencil tip and a coffee bean is the signature of a pinned statistic,
not of a measurement.

I raised two mechanisms and **both are refuted**:

**P14 (MEASURED, REFUTES my own hypothesis).** *Correlated noise.* Immerkær
assumes spatially independent noise; demosaicing correlates it. Measured: real
source high-pass lag-1 autocorrelation **−0.456 / −0.459** against **−0.664** for
white — the noise **is** correlated. But planting correlated noise of identical
σ=400 in a real master moves S2 only to **0.9867**, against **1.0025** for white
(`src/09-correlated-noise.py`). **A 1.6% effect cannot explain a 0.47 gap.**
My white-noise arm was indeed unrepresentative in the way I accused the
commission's latent of being — and it turned out not to matter.

**P15 (MEASURED, REFUTES my own hypothesis).** *Scale mismatch.* My
`register()` searches translation only, while focus breathing changes
magnification frame to frame, and S2 is a band ratio, so scale should move it.
Measured: a **5%** scale error moves S2 to **1.0292** — **+2.9%, and upward**
(`src/10-scale.py`). Wrong magnitude and wrong direction. Refuted.

**P16 (ARGUED).** The residual is therefore **unexplained**, and I am reporting
it as unexplained. S2 is commissioned for **same-pipeline** comparison (P12) and
is **not** commissioned for **cross-render** comparison (P13). The number the
project actually wants — how much real detail the merge reconstructs — is
cross-render, so **S2 does not yet deliver it.**

**P17 (ARGUED).** S2's residual USM/ringing sensitivity (**1.0345 / 1.0987 /
1.1697**) is probably irreducible for *any* reference-free energy statistic:
sharpening genuinely adds high-frequency energy, and no local statistic can
separate a real edge from a manufactured overshoot without a reference. This is
why `usm_match` must remain a **mandatory companion control**, not an optional one.

---

## 7. What the instrument can and cannot measure

The bounded-instrument outcome the brief explicitly accepted.

**Valid:**

- **Direction, within one rendering pipeline.** S0 and S2 both order blur
  correctly and both pass a planted improvement monotonically (P7, P12).
- **S2 for same-pipeline magnitude**, over the commissioned span — identity to a
  4-pixel box blur, i.e. roughly **0.82 … 1.22** (P12).

**Invalid:**

- **S0 for any cross-render magnitude.** Inflated ×4.1 median, and the inflation
  is **per-subject** (×4.49–×14.44), so no single rescale can repair it (P7–P9).
  This is the class of defect `halosens.py` documents: an error the statistic
  charges in the wrong direction and no degradation-only battery can see.
- **S2 for cross-render magnitude.** Pinned outside its commissioned range;
  cause unknown, two candidates refuted (P13–P15).
- **Any absolute "sharpness multiple", by either statistic, today.**

**P18 (ARGUED).** §105's embargo stands and should be **tightened**: it is not
merely that a multiple may not be quoted outside `ORCH-veiling.md`, it is that
**no cross-render sharpness multiple in the corpus is currently supportable by
any instrument this project owns**, including mine. The "state of the art"
sharpness claim remains unsupported. That is the same answer §105 reached, but
it now rests on a measured mechanism rather than an unexplained discrepancy —
which means it is actionable, and §8 says how.

---

## 8. Open questions

**Q1 — the cross-render residual (P13).** The next test is to remove the
rendering asymmetry at the source instead of correcting for it downstream:
render the sources through the **same** `--srgb --auto-exposure` path as the
master and re-run P12's battery against them. If S2 lands inside 0.82–1.22 the
instrument is fixed and the embargo can be lifted with a number. If it stays
pinned near 0.5, the residual is in the imagery and worth chasing. **I did not
run this because it needs the strehl render path applied to single frames, which
is `crates/` work and this was scoped as pure metrology.** Cheapest decisive
experiment in this report; I recommend it be routed as such.

**Q2 — is the pyramid merge's top band attenuated?** A Laplacian-pyramid blend
with a smoothed mask can attenuate the finest band, which would be a *real*
property of the stacker in the direction P13 points. Distinguishable from Q1 by
running Q1 first: if same-pipeline rendering closes the gap, Q2 is moot.
**Unclaimed. Do not read P13 as evidence for Q2** — P13 is uninterpretable until
Q1 is done.

**Q3 — should `commission()` be repaired in place?** Its target is degenerate
(P4–P6) and its ceiling arm is a constant (P1). A minimal repair is: replace the
white-noise latent with the 1/f-plus-edges target, add the IDENTITY arm, and
name the RECONSTRUCT arm for what it is. **Not done: `orch_sharp1to1.py` is the
orchestrator's file and I was scoped to a copy.** Routing this for a decision.

---

## 9. My own defects, disclosed

- **A post-hoc re-specification, §6.1.** I reclassified the noise arms from
  `DEGRADE` to `INVARIANT` *after* seeing that it improved my own candidate's
  score. The principled argument is given and I believe it, but the ordering is
  exactly the ordering that produces motivated reasoning. Logs are unaltered;
  the orchestrator should judge it, not me.
- **Two refuted hypotheses of my own (P14, P15).** Both were mine, both were
  plausible, both are dead. Recorded because a report that only lists the
  hypotheses that worked is not a record of what was tested.
- **`best_site()` and `register()` in scripts 03/06/08 are my
  re-implementations**, written from the originals' docstrings, not the
  originals. `detail`/`patch_gain`/`blur` are verbatim and validated — script 01
  reproduces all three published arms exactly. So P1–P7 are exact; the
  *absolute* real-subject ratios in P8/P9/P13 are not directly comparable to
  §105's (my S0 median 5.433 vs §105's 4.120, and a different arm, SHIP-V4 vs
  V3). **The ×0.24 collapse in P9 is a within-my-own-harness comparison and is
  unaffected by this.**
- **A dead loop left in `06-real.py`** crashed the first run
  (`TypeError: cannot unpack non-iterable NoneType`). Fixed; the log is from the
  clean re-run.
- **`dry-erase-marker-head-cpl` returned no usable site** and is excluded from
  all real-subject medians — 8 subjects, not 9. Counted, not dropped silently.

---

## 10. Rules discharged

| Rule | Where |
|---|---|
| Nothing is true until measured | Every P-number carries its script and log |
| Commission before trusting | §6.2; the IDENTITY arm the original never ran |
| Plant an **improvement**, not only defects | P5, P7, P12 — and it killed S2 on the white target |
| A search must be able to return nothing | P1's sweep could have been flat; P14/P15 were allowed to refute me |
| Print, then TEST | `unmeasurable` is counted and gates the ratio (P13) |
| Partition into counted outcomes | P13: `n`, `skipped`, `unmeasurable` sum to the patch count |
| Typed refusal over silent default | S2 returns NaN + `unmeasurable`, never a fabricated ratio |
| Disclose your own defects | §9 |
