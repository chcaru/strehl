# M50 — Is this sensor's fixed-pattern noise anisotropic?

**Status: MEASURED.** Runs against the owner's 242 delivered dark frames
(`D:\macro-dark-frames`, 11 ISOs × 22 frames, first two dropped as stabilisation
shots). Source: `experiments/m50-fpn-anisotropy/`, committed at `2bbb60b`.

---

## 1. The question, and why it was worth asking

SYNTHESIS question 20 records an unexplained orientation anomaly in M13 and M15:
`horizontal` test cells behave unlike `vertical` and `bar` cells, in a way no
milestone has accounted for. An external review proposed a mechanism:

> M4 measured row/column FPN, and Sobel-x/Sobel-y see row-banding
> asymmetrically — horizontal-band noise is pure vertical gradient. That is a
> concrete, checkable mechanism … and the fix (subtract per-row/per-column means
> per frame before the gradient — nearly free) is testable in an afternoon. If
> confirmed, it removes a directional bias sitting inside *every* window number
> M13 and M15 produced.

The mechanism is plausible and the stake is high — it would contaminate every
window measurement the project has made. But **the premise is not what M4 says.**

M4 §5 measured a *plane-level* asymmetry: G2 and B, the bottom row of the RGGB
quad, carry more FPN than R and G1 at high ISO (ISO 2000: 0.999 and 1.002 against
0.722 and 0.714). M4 then wrote, explicitly:

> **ARGUED:** a row-dependent readout path is the obvious explanation, but this
> experiment cannot distinguish that from a colour-filter-dependent dark current
> and does not try.

M4 never decomposed FPN into row banding versus column banding. So the review's
premise is **untested rather than established**, and its own citation says so.
This milestone tests it.

Darks are the right place: there is no scene content to confound the answer.

---

## 2. Method, and why the obvious method cannot work

The naive statistic — average N frames, take row means, report their spread —
cannot answer this. Averaging N frames leaves `sigma_t/sqrt(N)` of temporal noise
per pixel, and a row mean over W pixels has a spread of `sigma_t/sqrt(N*W)` from
that noise **alone**. A statistic whose null expectation is nonzero will always
find structure, and the structure being looked for here is small.

Every quantity in M50 is instead a **cross-half covariance**. The 20 frames are
split into two disjoint halves, each averaged independently, and the reported
value is the covariance between the two halves' statistics. Temporal noise is
independent between disjoint halves, so it contributes **exactly zero in
expectation**, and the covariance is an unbiased estimator of the fixed-pattern
variance in DN². It is free to return a negative number, and a negative number is
the correct answer for "no fixed pattern here".

That property is the reason for the choice: **the design can say no**, which is
what an experiment expecting a null needs. Reported beside every value is the
spread across 6 independent random half-splits, which is the error bar. A value
below its own spread is not a measurement of anything.

This is M4 §6's split-half discipline applied to a different question and carried
through to the derivative operators the focus measure actually uses.

Per CFA plane — the 2×2 CFA would otherwise dominate any row or column statistic
— the master is decomposed as `M[y,x] = grand + row[y] + col[x] + resid[y,x]`,
and each term's fixed-pattern variance is estimated by cross-half covariance.
Sobel-x and Sobel-y are then applied directly, because the claim under test is
about gradient operators rather than about row means, with energy again taken as
the cross-half product `<Sx_A · Sx_B>`. Convention: Sobel-x differentiates along
x and so sees **column** banding; Sobel-y sees **row** banding. Row banding
predicts `Ey > Ex`.

Anisotropy is reported as the bounded index `A = (Ey − Ex)/(Ey + Ex)` — see §6
for why not the ratio.

---

## 3. The estimator is validated before it is believed

`00-selftest.py` plants known FPN of each kind at 0.30 DN under 1.0 DN of
temporal noise — the plant is invisible in any single frame — and checks
recovery. All 16 checks pass:

| plant | sd_row | sd_col | sd_pix | index A |
| --- | --- | --- | --- | --- |
| row only | **+0.2693** | −0.0033 | −0.0092 | **+1.004** |
| column only | −0.0035 | **+0.2760** | −0.0090 | **−1.000** |
| per-pixel only | +0.0163 | +0.0199 | **+0.2975** | +0.004 |
| **nothing (placebo)** | −0.0036 | −0.0033 | −0.0083 | n/a |

**MEASURED:** plants recovered to within 10.2%; no component leaks into another;
and the placebo — pure temporal noise, no pattern at all — returns 1.2%, 1.1% and
2.8% of the plant amplitude. **That placebo row is what licenses believing a null
result below.** Without it, "there is no row banding" and "this estimator cannot
see row banding" are the same output.

**MEASURED:** the proposed fix destroys 99.96% of planted row-banding Sobel-y
energy and 99.83% of planted column-banding Sobel-x energy, while preserving
99.2% of ordinary per-pixel structure. So the fix works as intended on data where
there is something for it to do. Remember that when reading §5.

**MEASURED:** the isotropic per-pixel plant returns A = +0.004. This is the
control that matters most for §5's positive finding: it says the Sobel-x/Sobel-y
pair, as implemented here, carries **no intrinsic directional bias of its own**.

---

## 4. The loader is proven, not assumed

M50's decode reproduces M4 §8.1's dark-sigma table — through a third independent
route — at a mean ratio of **0.99993**, spread **0.00007**, across all eleven
ISOs (worst 0.99988). This is not decoration: it is what proves the pixel data is
correct after the use-after-free described in §6, whose failure mode is silent
corruption rather than a reliable crash. Corrupted pixels could not reproduce an
independently measured table to one part in fourteen thousand.

**MEASURED, and a second verification in its own right:** M50's *total* fixed
pattern also reproduces M4 **§5**, which is a different table produced by a
different estimator (bias-corrected asymptote of a sd-versus-N curve, against
M50's cross-half covariance):

| ISO | M50 total (DN) | M4 §5 sigma_FPN (DN) | ratio |
| --- | --- | --- | --- |
| 50 | 0.3735 | 0.3730 | 1.0013 |
| 100 | 0.3770 | 0.3768 | 1.0005 |
| 200 | 0.3427 | 0.3420 | 1.0021 |
| 400 | 0.3756 | 0.3756 | 1.0001 |
| 800 | 0.4643 | 0.4633 | 1.0023 |
| 1600 | 0.7104 | 0.6996 | 1.0155 |
| 2000 | 0.8712 | 0.8592 | 1.0139 |

Mean ratio 1.0043, worst deviation 1.55%. Two of M4's tables are now
independently confirmed by two different estimators. M4's arithmetic continues to
be right; last night's finding was that its *labelling* was incomplete, and
nothing here disturbs that split verdict.

The small positive bias at ISO 1600–2000 (+1.4 to +1.6%) is real but unexplained
and not chased here — see question 3.

---

## 5. The result

**MEASURED.** Per CFA plane, cross-half covariance, 6 random half-splits, ±
values are the split spread:

| ISO | sd_pix (DN) | sd_row (DN) | sd_col (DN) | row/pix | index A | Ey/Ex | A after fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | 0.3718 | +0.0301 ± 0.0118 | +0.0190 ± 0.0007 | 0.081 | +0.027 | 1.056 | +0.017 |
| 100 | 0.3754 | +0.0285 ± 0.0146 | +0.0191 ± 0.0008 | 0.076 | +0.026 | 1.053 | +0.017 |
| 200 | 0.3408 | +0.0165 ± 0.0194 | +0.0318 ± 0.0012 | 0.048 | +0.005 | 1.010 | +0.008 |
| 250 | 0.4042 | +0.0072 ± 0.0194 | +0.0389 ± 0.0015 | 0.018 | +0.012 | 1.025 | +0.017 |
| 400 | 0.3734 | +0.0347 ± 0.0107 | +0.0221 ± 0.0009 | 0.093 | +0.026 | 1.053 | +0.014 |
| 500 | 0.3943 | +0.0365 ± 0.0130 | +0.0258 ± 0.0011 | 0.093 | +0.027 | 1.055 | +0.018 |
| 640 | 0.3922 | +0.0300 ± 0.0187 | +0.0345 ± 0.0013 | 0.076 | +0.017 | 1.034 | +0.017 |
| 800 | 0.4611 | +0.0406 ± 0.0219 | +0.0374 ± 0.0017 | 0.088 | +0.030 | 1.061 | +0.025 |
| 1000 | 0.5001 | +0.0638 ± 0.0181 | +0.0516 ± 0.0017 | 0.128 | +0.061 | 1.130 | +0.042 |
| 1600 | 0.7037 | +0.0675 ± 0.0366 | +0.0702 ± 0.0032 | 0.096 | +0.032 | 1.067 | +0.033 |
| 2000 | 0.8643 | +0.0905 ± 0.0443 | +0.0609 ± 0.0039 | 0.105 | +0.041 | 1.086 | +0.038 |

### 5.1 The review's mechanism is refuted, on four independent grounds

1. **There is no row-specific structure.** `sd_row` and `sd_col` are the same
   size. At ISO 200, 250, 640 and 1600 the **column** term is the *larger* of the
   two. Row banding would show `sd_row >> sd_col`; it does not, at any ISO.
2. **Both are dwarfed by ordinary per-pixel FPN.** `sd_row` is 1.8%–12.8% of
   `sd_pix`. The fixed pattern on this sensor is per-pixel, not banded.
3. **The row term is barely a detection at all.** It exceeds twice its own
   split-to-split spread at only **5 of 11** ISOs, and at ISO 250 it is smaller
   than its own spread.
4. **The measured anisotropy is nowhere near the size the mechanism needs.** The
   index runs +0.005 to +0.061. The same estimator returns **+1.004** on planted
   pure row banding. The measured effect is at most **6% of one**.

**And the proposed fix is a no-op.** Subtracting per-row and per-column means
moves the index from +0.026 to +0.017 typical — it removes about a third of an
effect that is already ~3% of what the mechanism requires. §3 showed this same
fix destroying 99.96% of planted banding energy, so the fix is not broken; there
is simply almost nothing here for it to remove.

**Verdict: the mechanism proposed for question 20 does not exist on this sensor.
Question 20 remains open, and the row/column-mean subtraction should not be
built.** The prescription is cheap, which is exactly why it would have been built
without checking; it would have cost a per-frame pass over every plane, forever,
to remove 0.009 of an index that runs to ±1.

### 5.2 But a small real anisotropy does exist, and it is not banding

**MEASURED:** the index is positive at **11 of 11 ISOs**. Under a null of random
sign that is p ≈ 0.001 two-sided. Typical `Ey/Ex ≈ 1.05`: Sobel-y sees about 5%
more fixed-pattern energy than Sobel-x.

**MEASURED:** roughly two-thirds of it **survives** row and column mean removal
(+0.026 → +0.017). Whatever it is, it is not banding — it lives in the per-pixel
residual, meaning neighbouring pixels along x are slightly more correlated than
neighbouring pixels along y *within a single CFA plane*.

The alternative explanation — that my own operator pair is directionally biased —
is excluded by §3's isotropic plant, which returns +0.004 through the identical
code path.

**ARGUED, not measured:** a column-parallel readout with shared per-column ADCs
would impose more correlation along a row than down a column, which is the right
sign. M4's unresolved G2/B excess may be the same effect seen a different way.
Neither is established here.

**This does not resurrect the review's claim.** The direction it guessed is
right; the mechanism, the magnitude and the fix are all wrong. And whether a 5%
imbalance in *fixed-pattern* gradient energy matters at all against *scene*
gradient energy on textured content is a question this experiment does not
answer — see question 1. It is not licensed to explain question 20 and is not
offered as such.

### 5.3 One alternative explanation eliminated for M48

M48 is testing a hypothesised additive DN-domain noise floor near 0.49 DN. The
per-pixel FPN measured here is 0.37–0.40 DN at low ISO — suspiciously close.
**They are not the same thing and one cannot be leaking into the other:**
per-pixel *temporal* variance across frames is immune to a static spatial pattern
by construction. Per rule 10 the two were checked for confusion rather than
assumed distinct. This removes one candidate explanation for M48's floor and
mildly strengthens it; it does not confirm it.

---

## 6. My own errors and near-misses

**1. The summary statistic was wrong, and the self-test caught it before any real
data was touched.** Anisotropy was first written as the ratio `Ey/Ex`. A row-only
pattern has no variation along x at all, so `Ex` is legitimately ~0 and its sign
is noise. On planted row banding the ratio returned **−494.885** — a large
*negative* number for the most strongly *positive* case that exists. Had the
self-test not run first, that number would have appeared in a table about this
sensor and been interpreted. Replaced by the bounded index, which returns +1.004
on the same data. The criteria that replaced the failed ones are **stricter**
(A > 0.90 rather than ratio > 1.5), and the fix assertion is now an absolute
energy collapse, because after the fix *both* energies vanish and the index is
0/0. The ratio is still printed in the self-test output as a standing reminder.

**2. A use-after-free that declined to crash for four minutes.** `rawpy`'s
`raw_image_visible` is a **view** into LibRaw's internal buffer, not a copy. The
first version copied it into the frame stack *outside* the `with` block. It read
freed memory for four minutes and eleven ISOs' worth of work before Windows
raised an access violation — with no Python traceback at all. `python -X
faulthandler` produced the line number in one run. **The crash was the lucky
outcome; the unlucky one is silently corrupted pixels in a measurement nobody
re-checks.** This is now AGENTS rule 32, along with the requirement that any
RAW-decoding script carry a cross-check against an independent decode — which is
why §4 exists and why the result of §5 can be believed.

`01-dark-sigma.py` is **not** affected: it calls `.astype()` inside the `with`,
copying while the buffer is valid. Last night's M4 §8.1 verification stands, and
§4 re-confirms it a third time.

**3. I nearly did not run this at all,** on the grounds that the review's premise
was misattributed to M4 and could be dismissed on a reading. That would have been
wrong twice over: the premise turns out to be refutable by measurement rather
than merely unsupported, and the measurement found a real (if small and
differently-shaped) effect that a reading would have missed entirely.

---

## 7. Facts, disciplines, questions

Numbered **locally from 1**; the orchestrator renumbers on fold.

### Facts

1. **MEASURED.** This sensor's fixed pattern is per-pixel, not banded. Row and
   column terms are 1.8%–12.8% of the per-pixel term at every ISO, and the column
   term is the larger of the two at 4 of 11 ISOs.
2. **MEASURED.** The row term exceeds twice its own split spread at only 5 of 11
   ISOs, and at ISO 250 it is smaller than its own spread.
3. **MEASURED.** The Sobel anisotropy index is +0.005 to +0.061 on real darks
   against +1.004 on planted pure row banding — at most 6% of the mechanism the
   external review proposed. **The proposed row/column-mean subtraction is a
   no-op and must not be built**; it moves the index by 0.009 on a ±1 scale,
   while the same operation destroys 99.96% of *planted* banding energy.
4. **MEASURED.** A small anisotropy is nonetheless real: positive at 11 of 11
   ISOs (p ≈ 0.001), `Ey/Ex ≈ 1.05`, and roughly two-thirds of it survives row
   and column mean removal — so it is not banding. **ARGUED:** column-parallel
   shared-ADC readout has the right sign. Unexplained.
5. **MEASURED.** M4 §5's sigma_FPN table is independently confirmed by a
   different estimator on a different decoder: mean ratio 1.0043, worst deviation
   1.55%, with a real but unexplained +1.4–1.6% excess at ISO 1600–2000.
6. **MEASURED.** M4 §8.1's dark-sigma table is confirmed a third time at 0.99993
   mean ratio, spread 0.00007 — here as a *loader* check, which is what proves
   M50's own pixel data after the §6 use-after-free.
7. **MEASURED.** `rawpy`'s `raw_image_visible` is a view into LibRaw's buffer;
   using it after the `RawPy` context manager exits is a use-after-free that
   Windows reports as 0xC0000005 with no Python traceback, and that ran for four
   minutes before failing. Now AGENTS rule 32.

### Disciplines

1. **An experiment whose expected answer is "no" needs an estimator that can
   return zero, and a placebo that proves it does.** Cross-half covariance has
   exactly this property — temporal noise contributes zero in expectation and the
   estimate may go negative — which is why a null result from it is worth
   something. A statistic with a positive null expectation always finds
   structure. This generalises rule 11's placebo requirement from defects to
   nulls.
2. **A ratio is not an anisotropy measure when either term can legitimately be
   zero.** Use a bounded contrast index. Sign errors from a denominator crossing
   zero are not visible in the output — −494.885 looks like a measurement.
3. **Check what a citation actually says before building on it.** The mechanism
   here was attributed to M4; M4 explicitly declined to make the claim, and said
   so in the same paragraph the number came from.

### Questions

1. **Does the residual 5% gradient anisotropy matter on scene content at all?**
   M50 measures fixed pattern on darks. The relevant downstream comparison is
   against *scene* gradient energy in a focus window, which this does not
   measure. Cheap to settle on M13's existing cells.
2. **What causes the residual anisotropy, and is it the same effect as M4's
   unresolved G2/B excess?** Both are consistent with a row-parallel readout
   path; neither is established.
3. **Why is M50's total FPN 1.4–1.6% above M4 §5 at ISO 1600–2000 only?**
   Candidates: M4's bias correction over-subtracting where sigma_temporal is
   large, or a weak temporal correlation between frames that cross-half
   covariance retains and M4's estimator removes. The second would matter
   elsewhere.
4. **Question 20 is still open.** Its most concrete proposed mechanism is now
   dead, and no replacement is offered here.
