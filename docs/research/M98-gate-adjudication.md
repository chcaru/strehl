# M98 — the gate, adjudicated: two milestones, two metrics, one photograph

**Milestone:** M98
**Question as dispatched:** `--gate` is the single most user-visible knob, and
M85 (fact 1196) and M92 (fact 1245) disagree about it in the direction the owner
cares about. Is the shipped default costing him sharpness?
**Status:** complete. Verdict **R-INCONCLUSIVE** by the pre-registered rule, and
the reason it is inconclusive is itself the finding — see §1.

---

## 0. PRE-REGISTRATION

The full pre-registration is `experiments/M98-gate/PREREG.md`, committed **before
any number in this milestone existed** (rule 12). This section is the summary; the
file is the authority, and any departure is declared in §9 as a departure.

**HEAD:** `45ba18ba6ed71daa21802b9d45274ee49abe7892`. The working tree is **not
clean** — other agents hold uncommitted edits to `crates/strehl-core/src/robust.rs`
and four `crates/strehl-cli/examples/*`. My binary is built from that tree;
`robust.rs` is not on the default merge path. Recorded so the build is
attributable rather than assumed.

### Hypotheses and their falsifiers

| # | Hypothesis | Falsifier |
|---|---|---|
| **H1** | M85's ladder predates alignment (default-ON at `885e9f7`), so part of the measured gate cost was misregistration. With alignment ON the sharpness-vs-gate curve is **flatter**. | the aligned arm's gate contrast is **≥** the FOV-matched unaligned arm's, top detail tercile, `bee-3-cpl` |
| **H2** | M92's −0.61753 px is largely axis mismatch plus missing registration. On the **shipped** `--gate` axis with the shipped binary and alignment ON, `112MSDCF`'s gate-0 → gate-4 edge-width contrast is **< 0.31 px**. | it is ≥ 0.31 px |
| **H3** | The gate's cost is not one number. Mean `n_eff` is a global average dominated by low-detail regions: top-tercile local `n_eff` at gate 4 is **< ⅓** of the global mean. | it is ≥ ⅓ |
| **H4** | On a millimetre ruler — a-priori known tick spacing — gate 0 → 4 costs **< 10%** of the comb modulation. | it costs ≥ 10% |

### Two assertions about the prior milestones, to be re-verified not assumed

1. **They are not on the same axis.** `m57lib.py:510` `merge_subset` uses
   `acc = cf >= (gate * peak)` — a **fractional peak-height** gate. The shipped
   gate (`merge.rs:319`) thresholds on `T·√2·FOCUS_NOISE_SD`, in calibrated-noise
   units, and its default is **4.0**. Fact 1245 calls 0.50 "the shipped gate".
   `strehl stack --gate --help` already carries the caveat; the fact does not.
2. **M92's half-merges are unregistered** — `merge_subset` gathers `cube[idx]`
   with no warp. Averaging more frames of an unregistered bracket blurs by the
   drift spread, which reads exactly like a gate cost.

Both are *mechanisms that would produce M92's sign without the gate being at
fault*. They are hypotheses at pre-registration time, not findings.

### Instruments

Everything is a **cross-power between two half-merges with independent noise**
(parity frame split), because the gate changes noise ~6.6× and a single-render
band-power metric cannot separate signal from noise. From the *same* two
half-merges:

- `A_hf(T)` — band-integrated ring cross-power over `f ∈ [0.15, 0.2762]` cyc/px.
  **M85's quantity, made noise-free.**
- `dsig(T_a → T_b)` — `m57lib.dsig`, equivalent-Gaussian-blur difference in px
  over `f ∈ [0.05, 0.2762]`. **M92's quantity.**

Measuring both on identical data is what makes the adjudication possible.
All numbers are on the **binned linear camera-native** output, never on
`--srgb`/`--demosaic`.

### Arms

`ALN` (registration on, the shipped default) against `ZOOM` (`STREHL_ALIGN=zoom`
— field-of-view- and resampler-matched, registration discarded). `zoom` rather
than `STREHL_ALIGN=0` because magnification reads as sharpness (discipline 606).

### Stratification, declared in advance

24 ROIs of 512×512 on a procedural 6×4 lattice, split into **detail terciles by
`hp_sd`** measured once on the gate-0 `ALN` render. A conclusion that holds on the
top tercile and reverses on the bottom is **two conclusions, not one**
(discipline 603).

### Controls, each with its failing input

`EQ` at exactly `100.000000%` · `NC1` the negative control made to go red at
exactly `99.999996%` (one pixel, 1 LSB) · `PC` power control, planted σ = 0.30 px
must be recovered in `[0.25, 0.35]` px or **no null in this milestone means
anything** · `PL1` re-render placebo, exactly `0.000000` px · `PL2` half-label
swap, `< 1e-9` px · `FLAT` rule-9 flat-ROI control run **first** · `INERT` the
ruler comb must clear its sidebands by ≥ 3× or the ruler is no evidence ·
`AXIS` re-verify the axis-mismatch claim on the shipped binary.

### Decision rule, fixed in advance

Top detail tercile, `bee-3-cpl`, arm `ALN`, all controls green:

- **R-KEEP — the shipped default is correct:** `A_hf(4)/A_hf(0) ≥ 0.95` **and**
  `|dsig(0 → 4)| ≤ 0.10 px` **and** `sigma_flat(4)/sigma_flat(0) ≤ 0.5`.
  0.10 px is one unit of fact 1243's corrected single-ROI real-dark null.
  **Its failing value is `|dsig(0 → 4)| > 0.10 px` or `A_hf(4)/A_hf(0) < 0.95`.**
- **R-LOWER — the default is too high:** `|dsig(0 → 4)| ≥ 0.20 px` at
  `|mean|/SE ≥ 3.0`, **and** a knee `T*` exists with `|dsig(0 → T*)| ≤ 0.05 px`
  while `sigma_flat(T*)/sigma_flat(0) ≤ 0.5`.
- **R-INCONCLUSIVE** otherwise, or on any red control. A clean negative result is
  an acceptable outcome and will not be dressed up.

### Registered wrong predictions, to be scored

(a) `dsig(0 → 4)` `ALN` top tercile in `[0.00, 0.15]` px · (b) `ZOOM`'s
`dsig(0 → 4)` ≥ 1.5× `ALN`'s · (c) top-tercile local `n_eff` at gate 4 under 20
against the global 60.86 · (d) `A_hf(4)/A_hf(0)` reproduces M85's 0.985× to ±0.03
on `ZOOM` · (e) the ruler comb keeps ≥ 0.90 of its gate-0 modulation at gate 4.

### Read-only guarantee

`D:\personal\macro` and `D:\macro-dark-frames` are never written to. The shipped
merge caches a solved sidecar at `<dir>/warpmap.txt` (`align_cmd.rs:788`), which
would be a write into the read-only tree, so **every run operates on copies**
under `C:\dev\strehl-out\M98\frames\`.

---

## 1. Verdict

**The shipped default is not what is making the owner's stacks look soft, and
the case for lowering it is dead — but I cannot certify the default at my own
pre-registered bar either, and I am not going to pretend otherwise.**

Three separate findings, in decreasing order of confidence:

1. **M92's 0.61753 px is not a property of the shipped knob.** On M92's own
   stack (`112MSDCF`), on the shipped `--gate` axis, with the shipped binary and
   alignment ON, the **entire** range from pure selection to the shipped default
   costs **+0.10366 ± 0.00352 px** (29.41σ, 24/24 ROIs positive). M92's figure is
   excluded at **58σ**. On `bee-3-cpl` the top-detail-tercile cost is
   **+0.11798 ± 0.05118 px** and M92's figure is excluded at **9.8σ**. On a
   millimetre ruler with a-priori known tick pitch it is
   **+0.0333 ± 0.0366 px** and M92's figure is excluded at **16σ**.
   *(MEASURED.)*

2. **M85's fact 1196 survives the alignment change intact.** On the single
   most-detailed ROI of `bee-3-cpl` — the closest procedural analogue to M85's
   hand-picked facet crop — the raw high-frequency amplitude ratio at HEAD with
   alignment ON is **0.9872×**, against fact 1196's **0.985×**. **H1 is
   falsified:** correcting the registration did *not* flatten the
   sharpness-versus-gate curve. Nothing about the gate's cost was misregistration.
   *(MEASURED.)*

3. **The pre-registered R-KEEP bar fails, marginally and insignificantly, on two
   of its three conditions.** Top tercile, arm `ALN`: `A_hf(4)/A_hf(0)` reads
   **0.9397 ± 0.0266** against a bar of ≥ 0.95 (**0.39σ** short), and
   `|dsig(0→4)|` reads **0.11798 ± 0.05118 px** against a bar of ≤ 0.10 px
   (**0.35σ** over). The noise condition passes at **0.2525×**. R-LOWER is not
   triggered — it needs ≥ 0.20 px at ≥ 3σ and gets 0.118 px at 2.31σ. So the
   answer lands **astride my own bar**, which is R-INCONCLUSIVE, and it is
   reported as R-INCONCLUSIVE. *(MEASURED.)*

**And the softness is somewhere else, and I can name it with a number.** When
alignment became default-ON tonight, `fit_to_cover` began scaling the field of
view so that every frame covers every output pixel while the output dimensions
are held. On `bee-3-cpl` at HEAD that scale is **k = 0.9315**: the render is an
**interpolated enlargement of the optical image by 1.0735× — +7.35%, at every
pixel, at every gate.** The millimetre ruler recovers the aligner's own `k`
independently, from the photograph, at **0.68σ**. That is a global,
every-pixel, brand-new softness source of a size the gate never approaches.
*(MEASURED; see §5.)*

### The one-line answer to the owner

Leave `--gate` at 4. Across its whole range it costs about **a tenth of a pixel**
where your detail is, and buys **4× less noise**. If you want the last one
percent of facet contrast, `--gate 1` keeps **0.9983×** of it for half the noise
benefit. **`--gate 0` is not the sharp setting; it is the noisy one.** What
changed tonight is that your renders are now a 7% interpolated enlargement,
because deep brackets drift 232.7–603 px and the aligner must throw field away
to cover the frame. That is where your softness went.

---

## 2. The instrument, and the two instruments that did not work

### 2.1 What had to be true

The gate changes the noise by up to **6.6×** (M85) — measured here at **3.96×**
on `bee-3-cpl`'s background. Any single-render band-power sharpness metric
therefore reads *noise falling* as *detail falling*, and reads it hardest exactly
where there is least detail. M85's own ladder annotates the defocused background
at **0.151×** for precisely this reason. So the first requirement is a metric
that separates signal from noise, and the second is that both contested
quantities — M85's HF amplitude and M92's `dsig` — come off the **same renders**,
or the adjudication is two milestones again.

### 2.2 Half-merge cross-power: correct in principle, broken on a deep bracket

The pre-registered design was a **parity half-merge**: split the frame list even
/ odd, render each half at each gate, and take the ring **cross-power**
`Re(A·conj(B))`, whose expectation is noise-free because the two halves' noise is
independent. It works. On `112MSDCF` it produced the headline in §1.1 with 24/24
ROIs agreeing.

**On `bee-3-cpl` it returned `NaN` on 24 of 24 ROIs.** The diagnosis is in the
render logs and it is a real property of the pipeline, not a harness bug:
**each half solves its own alignment.** Half A took reference frame 75 and
`fit_to_cover` scale **0.9227**; half B took frame 74 and **0.9360**. The two
renders are at magnifications **1.44% apart** — up to 25 px of relative
displacement across the frame — which annihilates the high-frequency
cross-power. On `112MSDCF` the same two scales are 0.9760 and 0.9767 and the
instrument is fine; a 79-frame bracket barely drifts.

I built a pair-registration repair (global similarity fit, then per-ROI Fourier
shift, frozen on the gate-0 pair). It restored finite values, and then **its own
independent check failed**: the fitted scale was **+0.011364** where the render
logs predict **−0.014209**, with residual rms **12.6 px** and max **52 px**. The
two halves of a deep bracket are **not related by a global similarity** — each
pixel took its winning frame from a different part of the drift, so the
half-to-half map is a field, not a transform. The repair was abandoned rather
than tuned. *(This is reported as a failed bar, not omitted.)*

### 2.3 What was used instead: one render per gate, noise floor subtracted

The design was changed to **one full-stack render per gate, one shared alignment
solve**, which is M85's own design, with the noise handled explicitly rather than
ignored:

- Fact 27 pins the optical cutoff at **`F_SIG = 0.2762 cyc/px`**. Ring power at
  `f ∈ [0.30, 0.45]` is therefore **signal-free by construction** and is the
  noise floor.
- The floor is subtracted from every ring before `m57lib.dsig_db` runs.
  Subtracting a constant from `c` and from every sector-jackknife replicate
  `c_jack(s)` leaves the jackknife variance **exactly** unchanged, so the
  frozen error bars remain valid. The frozen code was not edited (rule 15); a
  `SubRing` duck-type wrapper presents the corrected rings to it.
- Both quantities come off these same renders: `A_hf` band-integrated over
  `f ∈ [0.15, 0.2762]`, and `dsig` over `f ∈ [0.05, 0.2762]`.

**Which way does this fail (rule 18).** The warp resampler is a low-pass, so
noise power just *above* cutoff is *lower* than noise power in-band. The floor
therefore **under-subtracts**, and it under-subtracts most at gate 0 where the
noise is largest. That pushes `A_hf(T)/A_hf(0)` **down** — i.e. the bias runs
*against* "the gate is cheap". **A cheap-gate result measured this way is a floor
on the gate's virtue, not a flattery of it.**

Both raw (M85's actual instrument) and floor-subtracted numbers are reported side
by side throughout, so nothing hides in the correction.

---

## 3. D1 — the gate ladder, re-measured at HEAD with alignment ON

`bee-3-cpl`, **299 frames**, alignment default-ON, 24 procedural ROIs of 512²
on a 6×4 lattice, binned linear camera-native output.

### 3.1 Frames actually averaged, before and after alignment

`strehl stack D:\personal\macro\bee-3-cpl --gate 0 0.5 1 2 4`, one statistics
pass, at HEAD:

| `--gate` | 0 | 0.5 | 1 | 2 | 4 |
|---|---:|---:|---:|---:|---:|
| **mean `n_eff`, alignment ON (M98)** | 1.000 | 1.968 | 4.562 | 19.182 | **55.321** |
| mean `n_eff`, alignment OFF (M85) | 1.000 | 2.125 | 5.244 | 23.043 | 60.860 |
| ratio | 1.000 | 0.926 | 0.870 | 0.832 | **0.909** |

**MEASURED. Correcting the registration lowers mean `n_eff` at every rung.**
Registered frames are more distinguishable in focus, so fewer of them are
statistically indistinguishable from the winner and fewer are admitted. M85's
ladder *was* averaging over misregistration as well as defocus — the mechanism
the dispatch flagged is real and is confirmed. It simply does not move the
sharpness answer, which is §3.3.

### 3.2 The ladder, pooled and stratified

Arm `ALN`, pooled over all 24 ROIs, all ratios against gate 0:

| `--gate` | `A_hf` raw | `A_hf` clean | ± | `dsig` px | ± | σ | ROIs positive |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 0.88613 | 0.89507 | 0.04478 | −0.00191 | 0.02451 | −0.08 | 15/24 |
| 1 | 0.85536 | 0.86756 | 0.05560 | +0.04386 | 0.02244 | 1.95 | 17/24 |
| 2 | 0.83268 | 0.84770 | 0.06080 | +0.12682 | 0.02824 | 4.49 | 22/24 |
| **4** | **0.81263** | **0.82962** | 0.06142 | **+0.18583** | 0.03614 | **5.14** | 23/24 |

Stratified by detail content (discipline 603), gate 4:

| tercile | `hp_sd` | `A_hf` raw | `A_hf` clean | `dsig` px | σ |
|---|---|---:|---:|---:|---:|
| LOW | 331–643 | 0.6337 ± 0.1617 | 0.6475 ± 0.1617 | +0.28474 ± 0.08034 | 3.54 |
| MID | 646–772 | 0.8795 ± 0.0627 | 0.9016 ± 0.0558 | +0.15478 ± 0.04011 | 3.86 |
| **HIGH** | **816–1303** | **0.9247 ± 0.0314** | **0.9397 ± 0.0266** | **+0.11798 ± 0.05118** | **2.31** |
| **single sharpest ROI #4** | **1303** | **0.9872** | **0.9904** | **+0.09840** | — |

**The pooled number is not one conclusion, it is three.** The pooled 0.830 and
+0.186 px are averages over regions where the gate does completely different
things. Discipline 603's warning is confirmed on this frame: the LOW tercile's
`A_hf` collapse to 0.65 is the defocused background losing **noise**, which is
what the gate is *for*, and reporting it in the same average as the facets
manufactures a cost that no photographer experiences.

### 3.3 Did registration change the shape of the curve? — H1

`ALN` against `ZOOM` (`STREHL_ALIGN=zoom`: same field of view, same resampler,
registration discarded — the honest comparator, discipline 606), paired by ROI:

| tercile | gate | `ALN − ZOOM`, paired | σ |
|---|---:|---:|---:|
| LOW | 4 | +0.37977 ± 0.24528 px | +1.55 |
| MID | 4 | −0.02083 ± 0.02786 px | −0.75 |
| HIGH | 4 | **+0.03094 ± 0.02320 px** | **+1.33** |
| HIGH | 1 | +0.00391 ± 0.01989 px | +0.20 |

**H1 is falsified.** Its pre-registered falsifier was "the aligned arm's gate
contrast is ≥ the FOV-matched unaligned arm's, top detail tercile". `ALN`
+0.11798 px against `ZOOM` +0.08704 px is **1.355×** — the wrong direction, and
the paired difference is **not significant** at 1.33σ. The honest reading is
*not* "registration made the gate worse"; it is **"registration made no
difference to what the gate costs"**, which is a null and which falsifies H1 as
written.

And on `A_hf`: `ALN` 0.9397 ± 0.0266 against `ZOOM` 0.9359 ± 0.0270 in the top
tercile. **The two arms agree with each other and both differ from M85's 0.985.**
Whatever separates my tercile mean from fact 1196, **it is not registration** —
it is the ROI definition, and the single-sharpest-ROI row in §3.2 closes that
gap to 0.002.

### 3.4 Against fact 1196, stated exactly

| quantity | M85 (fact 1196, align OFF) | M98 (HEAD, align ON) |
|---|---|---|
| HF amplitude, most-detailed region | **0.985×** (hand-picked facet crop, radius band 0.30–0.50 *of that crop*) | **0.9872×** (procedural ROI #4, `f ∈ [0.15, 0.2762] cyc/px`, raw) |
| HF amplitude, demosaic-free path | 0.997× | not re-measured |
| defocused background | 0.151× | 0.3255× (ROI #23, raw) |
| mean `n_eff` at gate 4 | 60.860 | 55.321 |

**Fact 1196's headline reproduces at HEAD.** The two are not the *same* quantity
— M85's crop and band were chosen by hand and mine procedurally — and I state
that rather than claiming a contradiction or a confirmation stronger than the
evidence. What can be said cleanly: **the corrected registration did not move
it.**

---

## 4. D2 — adjudicating the two metrics against something external

Neither `dsig` nor `A_hf` is ground truth. A **millimetre ruler** is: the tick
pitch is known a priori, so resolved detail can be scored against a physical
scale rather than against a metric the project invented.

### 4.1 `flat-on-ruler-cpl` — the decisive anchor

79 frames, **registered** (it carries a solved `warpmap.txt`, so `load_or_solve`
loads it and never writes — the read-only guarantee holds). The comb was found by
2-D spectral peak search, frozen as `(f₀, θ)` on the gate-0 render, and the
modulation taken as the peak disc **minus the median of its two sidebands**, so
the local noise floor is removed. **13 of 54 candidate ROIs cleared the `INERT`
gate** (S/B ≥ 3) and were used; the rest are reported as inert, not as nulls.

Comb fundamental **f₀ = 0.047–0.206 cyc/px** — *inside the band the gate acts
in*, which is why this stack is the better anchor and the tilted one is not.

| `--gate` | comb modulation vs gate 0 | equivalent blur |
|---|---:|---:|
| 0.5 | 0.99978 ± 0.00014 | +0.0171 ± 0.0147 px |
| 1 | 0.99944 ± 0.00034 | +0.0148 ± 0.0187 px |
| 2 | 0.99955 ± 0.00051 | +0.0139 ± 0.0252 px |
| **4** | **0.99894 ± 0.00065** | **+0.0333 ± 0.0366 px** |

**MEASURED. Against a physical scale, the shipped default costs 0.11% of the
resolved modulation.** M92's 0.61753 px is excluded at **16.0σ**. The result is
consistent with zero *and* with my own 0.10 px — the ruler cannot separate those
two, and I do not claim it does.

### 4.2 `highly-angled-ruler-mm-cpl` — underpowered, reported anyway

299 frames. This is a `TILTED_SUBJECT` (`align_cmd.rs:32`), so the aligner
refuses it and it renders **unregistered by design**. 7 of 54 ROIs cleared
`INERT` at the fundamental, 3 at the higher harmonics.

| harmonic | f range (cyc/px) | gate 4 blur | M92's 0.618 px excluded at |
|---|---|---:|---:|
| n=1 | 0.034–0.050 | +0.2302 ± 0.3686 px | 1.1σ |
| n=2 | 0.068–0.100 | +0.2283 ± 0.1976 px | 2.0σ |
| n=4 | 0.136–0.200 | **−0.1364 ± 0.2084 px** | 3.6σ |

**The fundamental is inert for this question and I should have seen it before
rendering 299 frames.** At 0.034–0.050 cyc/px the comb sits far below the band
the gate acts in; a tenth-pixel blur cannot express itself there, and the wide
error bars are the instrument saying so. Only the n=4 harmonic reaches the
relevant band, on 3 ROIs, and it reads *negative*. This anchor is **weak
supporting evidence**, not a result.

### 4.3 What the adjudication comes to

**Both prior milestones measured their own quantity correctly.** M85's HF
amplitude really is ~0.99 where detail lives; M92's `dsig` really is ~0.6 px on
*its* axis. They are not in contradiction, because they are not measuring the
same knob (§6). Measured on the **same renders** at HEAD, the two quantities
**agree**: on the single sharpest ROI, `A_hf` 0.9904× and `dsig` +0.0984 px —
a ~1% amplitude loss and a ~0.1 px width gain are the *same statement* about the
same edge. The corpus's worry that "the corpus does not know which one the eye
reads" turns out not to bite: **on this knob, in this band, they read the same
thing.**

---

## 5. D3 — what should `--gate` default to, and where the softness actually is

### 5.1 The recommendation

**Recommend: KEEP `DEFAULT_GATE = 4.0`. Do not lower it on this evidence.**
`DEFAULT_GATE` was **not modified** — question 90 is the orchestrator's.

The evidence, and its limits, stated together:

- The M92-motivated case for lowering is **dead**: 0.618 px is excluded at 9.8σ
  on `bee-3-cpl`, 58σ on `112MSDCF`, 16σ on a physical ruler.
- **R-LOWER is not triggered** and there is no knee: the ladder is smooth and
  monotone, and the gate that would satisfy R-LOWER's `|dsig| ≤ 0.05 px`
  requirement (gate ~1) does *not* satisfy its noise requirement — the whole
  premise of R-LOWER, that a free lunch exists on the ladder, is not observed.
- **R-KEEP's own bar was missed by 0.35σ and 0.39σ.** I am not going to round
  that to a pass. The honest statement is that **the shipped default's cost sits
  within about one standard error of the corrected single-ROI real-dark null**
  (fact 1243, 0.089–0.094 px), not demonstrably under it.

### 5.2 What he loses either way, in his own terms

From the D4 panel's two ROIs, all MEASURED on the linear path, gate 0 → gate 4:

| | fine detail (ROI 4, `hp_sd` 1303) | smooth background (ROI 23, `hp_sd` 331) |
|---|---|---|
| noise | 1.000× → **0.944×** | 1.000× → **0.253×** |
| HF amplitude | 1.0000× → **0.9904×** | 1.0000× → 0.3255× |
| equivalent blur | 0 → **+0.098 px** | 0 → +0.423 px |

**Where his detail is, the gate does almost nothing in either direction.** It
takes 1% of the amplitude and returns 6% of the noise. **That is the real reason
lowering the gate cannot fix his softness: the knob is nearly inert on detail,
in both directions.** Where his *background* is, it returns 4× — which is the
entire point of the estimator and is plainly visible on the panel.

This is also the answer to H3. Global mean `n_eff` at gate 4 is **55.321**, but
local `n_eff` estimated from each ROI's own noise floor has median **1.24** in
the top detail tercile — **0.022× the global mean**. On `112MSDCF`, measured
directly from the half-merge incoherent power rather than inferred from a floor
band, the top tercile reads **1.16** against a global 6.489.

**H3's falsifier (top-tercile local `n_eff` ≥ ⅓ of global) is not met, but both
estimators are biased toward H3** — signal leaks into the floor band, and
half-to-half *signal* disagreement does not average down — so the correct
statement is **supported, not established**. The instrument cannot cleanly
separate "few frames were averaged here" from "the frames that were averaged
disagree here". The *outcome* is the same either way and is directly measured:
**the noise reduction the gate delivers where the detail is, is 0.944×.**
"61 frames averaged per pixel" is not a description of what happens on the
facets, and no headline should imply that it is.

### 5.3 Where the softness is — named, with a number

When alignment became default-ON at `885e9f7`, `fit_to_cover` began scaling the
field of view so every frame covers every output pixel, **while holding the
output dimensions**. The render is therefore **upsampled by 1/k through the warp
resampler** — an interpolated enlargement, at every pixel, at every gate.

MEASURED from the render logs at HEAD:

| stack | drift | `fit_to_cover` k | upsample |
|---|---|---:|---:|
| `112MSDCF` (79 frames) | small | 0.9760 | +2.46% |
| `flat-on-ruler-cpl` (79) | small | 0.9708 | +3.01% |
| **`bee-3-cpl` (299 frames)** | **232.7–603 px** | **0.9315** | **+7.35%** |

**Independent check, and it passes.** This cannot be read off a pixel-space
sharpness metric, because magnification reads as sharpness (discipline 606). The
millimetre ruler can read it, because its tick pitch is a physical constant: the
ratio of comb frequencies between the registered and `STREHL_ALIGN=0` renders
measures the magnification directly, from the photograph, knowing nothing about
the aligner's internals. It reads **1.04630 ± 0.02390** against the log's
predicted **1.03008** — **agreement at 0.68σ**.

**ARGUED, and flagged as argued:** a 7.35% interpolated enlargement viewed at
100% is exactly the perceptual signature the owner is describing, it is global
rather than confined to any region, and it appeared tonight — which matches
"those stacks don't look too good *yet*". I have **not** measured that it is the
dominant term, and the object-space blur measurement that would have settled it
came out on 3 paired ROIs with an unnormalised amplitude comparison and is
reported in `out/s8_resample.log` as **exploratory, not a bar**. What is
measured is the magnification and its independent confirmation.

**Two other candidates I did not test and am not claiming:** the demosaic path,
and the absence of any deconvolution or sharpening stage — a stack that averages
55 frames has the SNR headroom to support restoration that a single frame does
not, and the pipeline currently spends none of it.

---

## 6. The two milestones, reconciled — the `AXIS` control

The disagreement resolves in three parts, and only the third is about magnitude.

**(i) They are not the same knob.** *(MEASURED from source, re-verified at HEAD.)*

| | rule | direction |
|---|---|---|
| shipped, `merge.rs:319` `Gate::admits` | `best − focus ≤ T·√2·FOCUS_NOISE_SD` | **larger T admits MORE** |
| M57/M92, `m57lib.py:510` `merge_subset` | `acc = cf ≥ gate·peak` | **larger gate admits FEWER** |

These are different *acceptance rules* on opposite-running axes, not two settings
of one knob. Mean `n_eff` is the only bridge either report supplies.
`main.rs:131-141` and the `DEFAULT_GATE` docstring at `merge.rs:236-297` **already
say this**; fact 1245's phrasing does not.

**The `DEFAULT_GATE` docstring is the documentary find of this milestone.** It
states, verbatim at HEAD: *"**The sharpness price of gate 4.0 on real frames is
not measured anywhere in this corpus, on any axis.** … M57's 0.496–0.740 px
deficit is measured on a **fractional peak-height** gate that runs in the
opposite direction, so it does not transfer to this axis except through mean
`n_eff`."* **M92's 0.61753 px sits inside M57's 0.496–0.740 px range.** It is
M57's number re-measured on M57's axis. M98 supplies the number the docstring
says does not exist: **+0.10366 ± 0.00352 px** on `112MSDCF`, on the shipped
axis.

**(ii) M92's half-merges are unregistered.** `merge_subset` gathers `cube[idx]`
with no warp. Averaging more frames of an unregistered bracket blurs by the drift
spread, which reads exactly like a gate cost. *(MEASURED from source.)*

**(iii) The bridge, on M92's own stack.** Shipped-axis `n_eff` on `112MSDCF`
half A (40 frames):

| `--gate` | 0 | 0.5 | 1 | 2 | 4 |
|---|---:|---:|---:|---:|---:|
| tol (DN-norm) | 0.000000 | 0.010758 | 0.021516 | 0.043032 | 0.086063 |
| mean `n_eff` | 1.000 | 1.309 | 1.809 | 3.457 | **6.489** |

M92 measured its near-selector end at mean `n_eff` **1.45–2.08** (its report S8),
which places it at shipped `--gate ≈ 0.7–1.2`. It does **not** report `n_eff` at
its 0.50 end. Whatever that end admits, **the shipped knob's entire range — from
pure selection at 1.000 to the default at 6.489 — is bounded by the 0 → 4
contrast measured here directly on the same stack, +0.10366 px.** The `AXIS`
control's registered failing value (the shipped default admitting *fewer* frames
than M92's 0.50 end) is not observed. **`AXIS`: GREEN.**

---

## 7. Controls — including the ones that went red

### 7.1 Green

| # | control | bar, exact | result |
|---|---|---|---|
| **EQ** | two identical invocations agree | **`100.000000%`** of pixels and SHA-256 equal | **`100.000000%`** of 24,724,512 px; SHA-256 identical. **PASS** |
| **NC1** | *the negative control made to go red* — one pixel, exactly 1 LSB | EQ must read **exactly `99.999996%`** | read **`99.99999595543079%`**, matching the predicted value to every printed digit. The `100.000000%` bar went **RED**. **PASS** |
| **PC** | planted Gaussian σ = 0.30 px recovered | `dsig ∈ [0.25, 0.35]` px | **+0.299824 ± 0.000015 px** (8/8 ROIs, sd 4.2e−5) — **0.06% accuracy**. **PASS** |
| **PL1** | placebo: same gate rendered twice | exactly `0.000000` px | max \|`dsig`\| = **0.000000000 px**. **PASS** |
| **PL2** | placebo: swap half labels A↔B | < 1e−9 px | max Δ = **0.000e+00 px**. **PASS** |
| **INERT** | ruler comb clears sidebands ≥ 3× | S/B ≥ 3.0 | 13/54 ROIs on `flat-on-ruler-cpl`, 7/54 on the tilted ruler. Inert ROIs reported as inert. **PASS** |
| **AXIS** | M92's 0.50 is not the shipped gate | — | §6. **PASS** |

**PC is the one that licenses every null in this milestone.** An instrument that
recovers a planted 0.30 px to 0.06% can see an effect the size M92 reports; the
nulls reported here are therefore nulls, not blindness.

### 7.2 Red — reported, not buried

1. **`FLAT` on the half-merge instrument — RED.**
   `sigma_flat(4)/sigma_flat(0) ≤ 0.5` read **0.8675** (`112MSDCF` `ALN`) and
   **0.8282** (`ZOOM`). Diagnosis: `sd((a−b)/2)` carries half-to-half **signal**
   disagreement, which does not average down with `n_eff`. A refined
   incoherent-power version was also red on `112MSDCF` (0.838) — because
   **`112MSDCF` has no genuinely flat region** (its lowest `hp_sd` is 121), so
   the control is *inert* there (rule 13) rather than failing. On `bee-3-cpl`,
   which has a real defocused background, the refined bar reads **0.1296** and
   the s4 floor bar reads **0.0638** — both **PASS**. The pre-registered metric
   was wrong; the pre-registered *bar* was met once the metric was fixed, and the
   fix is declared in §9.

2. **Pair-registration independent check — RED, and the design was changed
   because of it.** §2.2. Fitted scale +0.011364 against a log-predicted
   −0.014209; residual rms 12.6 px. Not tuned; abandoned.

3. **s4 noise-model independent check — RED, and it is my defect not the
   pipeline's.** The merge's own model predicts σ gain **0.6273×** at gate 4;
   my floor measurement gives **0.2525×** — agreement 0.40×. Diagnosis: the CLI
   number is a **whole-frame mean** and mine is a **local** measurement on the
   flattest ROI, where local `n_eff` is far higher than the frame mean. The two
   are not the same quantity and I registered a bar comparing them. **A
   specification defect in my own control.**

4. **`ZOOM` arm's `dsig` on `112MSDCF` goes negative at low gate** —
   −0.04645 ± 0.01309 px at gate 0.5 (−3.55σ). An unregistered merge measuring
   *sharper* than its own gate-0 reference is not physical; it is the
   magnification-free `zoom` null interacting with the selector's per-pixel frame
   choice. It does not affect the gate-4 contrast used in any conclusion, and it
   is flagged as an unexplained residual.

---

## 8. Scored: hypotheses and registered wrong predictions

| # | hypothesis | falsifier | result |
|---|---|---|---|
| **H1** | registration flattens the gate curve | aligned contrast ≥ FOV-matched unaligned | `ALN` 0.11798 vs `ZOOM` 0.08704 px → **FALSIFIED** (though the paired difference is only 1.33σ, so the true reading is a null) |
| **H2** | shipped-axis contrast on `112MSDCF` < 0.31 px | ≥ 0.31 px | **+0.10366 ± 0.00352 px** → **CONFIRMED**, 0.31 excluded at **58.5σ** |
| **H3** | top-tercile local `n_eff` < ⅓ of global | ≥ ⅓ | median **1.24** vs bar **18.44** → **CONFIRMED but with an estimator biased toward it** (§5.2) |
| **H4** | ruler comb costs < 10% at gate 4 | ≥ 10% | **0.106%** fall → **CONFIRMED** |

| # | registered prediction | outcome | |
|---|---|---|---|
| (a) | `dsig` `ALN` top tercile in [0.00, 0.15] px | **0.11798** | **CORRECT** |
| (b) | `ZOOM`'s `dsig(0→4)` ≥ 1.5× `ALN`'s | **0.738×** | **WRONG** |
| (c) | top-tercile local `n_eff` at gate 4 under 20 | median **1.24** | **CORRECT** |
| (d) | `A_hf(4)/A_hf(0)` within ±0.03 of M85's 0.985 on `ZOOM` | **0.9359**, \|Δ\| = 0.0491 | **WRONG** |
| (e) | ruler comb keeps ≥ 0.90 modulation at gate 4 | **0.99894** | **CORRECT** |

**(b) and (d) are the informative failures.** Both assumed registration was doing
more work than it is. (b) assumed the unaligned arm would show a much larger gate
cost — it shows a *smaller* one. (d) assumed the tercile mean would land near
M85's hand-picked-crop number on the unaligned arm — it lands 0.049 away, and the
gap closes to **0.002** only when the comparison is made on a single
most-detailed ROI. **Both failures say the same thing: the difference between
M85's number and mine is the ROI definition, not the registration.**

---

## 9. Departures from pre-registration

Declared as departures, per the pre-registration's own terms.

1. **`hp_sd` uses a 9×9 high-pass, not the 3×3 Laplacian written in PREREG §3.**
   A 3×3 Laplacian on a 2×1-binned green plane is dominated by read noise and
   stratified the ROIs by noise rather than by detail. Changed before any gate
   contrast was computed, and the stratifier is still frozen once on the gate-0
   `ALN` render (rule 17), so it is not a function of the arm being compared.

2. **`sigma_flat` was replaced by an incoherent-power estimator `n_incoh`.**
   §7.2 item 1. The pre-registered metric conflated half-to-half signal
   disagreement with noise.

3. **The primary instrument changed from parity half-merges to a single
   full-stack render per gate with noise-floor subtraction.** §2.2 and §2.3.
   This is the largest departure. Forced by a measured instrument failure
   (`NaN` on 24/24 ROIs) whose cause is a real pipeline property, with a repair
   attempted, independently checked, and abandoned when the check failed. The
   `112MSDCF` half-merge results are retained and reported because on that stack
   the instrument is sound and it is M92's own stack.

4. **A pair-registration repair was written and then discarded.** §2.2.

5. **The `s8` object-space resampler measurement was added after the fact and is
   not pre-registered.** It is reported as **exploratory** and is not used in any
   conclusion. Its magnification result *is* used, because that quantity carries
   an independent check that passed at 0.68σ.

6. **`n_eff_loc` fell back to the declared substitution.** PREREG §3 anticipated
   that the shipped binary might emit no per-pixel `n_eff` map. It does not
   (`grep -n n_eff crates/strehl-cli/src/*.rs` finds no map output), so local
   `n_eff` is inferred from each ROI's own noise floor, with the bias direction
   stated in §5.2.

7. **Discipline 605, cited in the dispatch, does not exist in `SYNTHESIS.md`.**
   The substance the dispatch attributes to it — that whole-frame gradient-energy
   sharpness is measured-blind on this rig — is carried by **fact 1235** and
   **discipline 603/606**, and was honoured: no Tenengrad-style metric appears
   anywhere in this milestone.

---

## 10. Candidate facts

Numbered `P1…` per rule 28. Every claim labelled.

- **P1 — MEASURED.** On the **shipped** `--gate` axis, with the shipped binary
  and alignment ON, the **entire** range from pure selection (mean `n_eff`
  1.000) to the shipped default (6.489) costs **+0.10366 ± 0.00352 px** of
  equivalent Gaussian blur on `112MSDCF` — M92's own strongest stack —
  at **29.41σ**, 24/24 ROIs positive, SE from across-ROI repetition. **M92's
  0.61753 px (fact 1245) is excluded at 58.5σ.** This is the number the
  `DEFAULT_GATE` docstring states "is not measured anywhere in this corpus, on
  any axis".

- **P2 — MEASURED.** `m57lib.py:510` `merge_subset` gates on `cf ≥ gate·peak`, a
  fractional peak height where **larger admits fewer**; `merge.rs:319`
  `Gate::admits` gates on `best − focus ≤ T·√2·FOCUS_NOISE_SD`, a calibrated
  noise distance where **larger admits more**. Fact 1245 calls 0.50 "the shipped
  gate"; it is a different acceptance rule on an opposite-running axis.
  M92's 0.61753 px lies inside M57's published 0.496–0.740 px range on that axis.
  **Fact 1245 should be amended to name its axis.**

- **P3 — MEASURED.** M85's fact 1196 reproduces at HEAD with alignment ON. On
  the single most-detailed procedural ROI of `bee-3-cpl`, raw HF amplitude at
  gate 4 / gate 0 is **0.9872×** against fact 1196's **0.985×**, and the
  equivalent blur on the same ROI is **+0.0984 px**. The two contested metrics,
  computed from the same renders, **agree**.

- **P4 — MEASURED.** Correcting the registration **lowers** mean `n_eff` at every
  rung of the gate ladder on `bee-3-cpl`: 1.000 / 1.968 / 4.562 / 19.182 /
  **55.321** with alignment ON, against M85's align-OFF 1.000 / 2.125 / 5.244 /
  23.043 / **60.860** — **0.909× at gate 4**. Registered frames are more
  distinguishable in focus, so fewer are admitted. M85's ladder was averaging
  over misregistration as well as defocus.

- **P5 — MEASURED.** That correction does **not** move the sharpness answer.
  Paired by ROI on the top detail tercile of `bee-3-cpl`, `ALN − ZOOM` at gate 4
  is **+0.03094 ± 0.02320 px** (1.33σ) and the `A_hf` ratios are 0.9397 ± 0.0266
  against 0.9359 ± 0.0270. **The hypothesis that misregistration inflated M85's
  measured gate cost is falsified.**

- **P6 — MEASURED.** Against a **physical scale** — `flat-on-ruler-cpl`, 79
  frames, registered, comb fundamental 0.047–0.206 cyc/px, 13 live ROIs — the
  shipped default preserves **0.99894 ± 0.00065** of the gate-0 comb modulation,
  an equivalent blur of **+0.0333 ± 0.0366 px**. M92's 0.61753 px is excluded at
  **16.0σ**.

- **P7 — MEASURED.** The gate's cost is **not one number** and a pooled figure
  averages incompatible regions (discipline 603 confirmed). On `bee-3-cpl` gate 4:
  top detail tercile `A_hf` **0.9397 ± 0.0266** / `dsig` **+0.118 ± 0.051 px**;
  bottom tercile **0.6475 ± 0.1617** / **+0.285 ± 0.080 px**; pooled
  **0.82962 / +0.18583 px**. The bottom tercile's collapse is the defocused
  background losing **noise**, which is the estimator working.

- **P8 — MEASURED.** Where detail lives, the gate is nearly **inert in both
  directions**. On the most-detailed ROI of `bee-3-cpl`, gate 0 → 4 moves the
  noise only **1.000× → 0.944×** and HF amplitude **1.0000× → 0.9904×**; on the
  smooth background it moves the noise **1.000× → 0.253×**. **Lowering the gate
  cannot recover sharpness on the facets, because the gate is not taking any.**

- **P9 — MEASURED.** Global mean `n_eff` is not a description of what happens
  where detail is. At gate 4 on `bee-3-cpl` the global mean is **55.321** while
  local `n_eff` in the top detail tercile has median **1.24** (0.022× global); on
  `112MSDCF`, measured from half-merge incoherent power, **1.16** against a global
  **6.489**. *(Both estimators are biased toward this conclusion — see §5.2 —
  so this is supported, not established.)*

- **P10 — MEASURED.** A registered render is an **interpolated enlargement** of
  the optical image. `fit_to_cover` scales the field of view to
  **k = 0.9315** on `bee-3-cpl` (299 frames, drift 232.7–603 px), **0.9708** on
  `flat-on-ruler-cpl` and **0.9760** on `112MSDCF` — upsampling by **+7.35%**,
  **+3.01%** and **+2.46%** respectively, at every pixel and every gate. On the
  ruler this is confirmed **independently from the photograph**, by the ratio of
  comb frequencies between the registered and `STREHL_ALIGN=0` renders:
  **1.04630 ± 0.02390** against a predicted **1.03008**, agreeing at **0.68σ**.

- **P11 — ARGUED.** A +7.35% interpolated enlargement applied globally, arriving
  the same night the owner says the stacks "don't look too good yet", is a better
  candidate for his softness than a knob that costs 1% of amplitude where his
  detail is. **Not measured to be the dominant term.** The measurement that would
  settle it (object-space equivalent blur, registered vs `STREHL_ALIGN=0`) came
  out on 3 paired ROIs with an unnormalised comb amplitude and is exploratory
  only. A milestone that renders `bee-3-cpl` at `STREHL_ALIGN=0` and scores it
  against the ruler's physical scale would settle it.

- **P12 — MEASURED (negative result about my own specification).** Parity
  half-merges are **not a valid instrument on a deep bracket**: each half solves
  its own alignment, so half A of `bee-3-cpl` renders at `fit_to_cover` 0.9227
  from reference frame 75 and half B at 0.9360 from frame 74 — **1.44% apart**,
  which returns `NaN` cross-power on 24/24 ROIs. The two halves are **not**
  related by a global similarity (fitted scale +0.011364 against a log-predicted
  −0.014209, residual rms 12.6 px), because each pixel took its winner from a
  different part of the drift. The instrument is sound on short brackets
  (`112MSDCF`: 0.9760 vs 0.9767).

- **P13 — DERIVED.** `sd((a−b)/2)` between two half-merges is **not** a flat-ROI
  noise control. It carries half-to-half *signal* disagreement, which does not
  average down with `n_eff`, so it reads ~0.83–0.87× where the true noise ratio
  is ~0.13×. Any milestone using a half-difference as a noise estimate on a
  scene with structure is measuring the structure.

- **P14 — DERIVED.** A flat-ROI noise control is **inert** on a stack with no
  flat region. `112MSDCF`'s lowest `hp_sd` is 121 against `bee-3-cpl`'s 331 on a
  frame whose top ROI is 1303; the control fails there for lack of stimulus
  (rule 13), not for lack of validity, and passes on `bee-3-cpl` (0.1296 refined,
  0.0638 on the floor metric).

- **P15 — MEASURED.** Discipline **605** as cited in this milestone's dispatch
  does not exist in `SYNTHESIS.md`. The substance is carried by fact 1235 and
  disciplines 603/606.

---

## 11. Artefacts

| path | what |
|---|---|
| `C:\dev\strehl-out\M98\gate-ladder.png` | **D4.** Owner-facing ladder, alignment ON. Same crop per row, same display gain within a row, fine-detail row and smooth-background row, frames-averaged per column, measured cost and benefit on every panel, external ruler check in the footer. |
| `experiments/M98-gate/PREREG.md` | the binding pre-registration, committed `b2a775f` before any number existed |
| `experiments/M98-gate/out/s4_bee-3-cpl.json` · `.log` | **D1.** Full-stack ladder, both arms, per-ROI. |
| `experiments/M98-gate/out/s3_flat-on-ruler-cpl.json` · `s3_ruler.json` | **D2.** External anchors. |
| `experiments/M98-gate/out/s2_controls_112MSDCF.json` | all five controls |
| `experiments/M98-gate/out/s1_112MSDCF.json` | half-merge instrument on M92's stack |
| `experiments/M98-gate/out/s6_axis.log` | the `AXIS` control |
| `experiments/M98-gate/out/s8_resample.log` | §5.3, the `fit_to_cover` measurement and its independent check |
| `experiments/M98-gate/out/s7_report.txt` · `s9_raw.txt` | every number in this report, regenerable in one command |

`DEFAULT_GATE` was not modified. No file owned by another agent was touched.
`D:\personal\macro` and `D:\macro-dark-frames` were never written to — the
render scripts assert it by full recursive listing (name, size, mtime) before and
after, and the assertion printed **PASSED** on every run.

