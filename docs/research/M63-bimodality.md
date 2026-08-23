# M63 — Occlusion bimodality: the corpus, and the instrument that measured it

**Status: MEASURED. Two findings. The second reopens a question the corpus had
closed.**

Milestone type: measurement. **No Rust was written.** `crates/**`, `SYNTHESIS.md`,
`AGENTS.md`, `OWNER-QUESTIONS.md` and `docs/captures-needed.md` were read-only for
this milestone. Everything M63 produced lives in
`experiments/M60-bimodality/**` and in this file.

> **Renumbered M60 → M63 after the work was complete.** `M60` had been dispatched
> to more than one agent; M54's milestone came first and keeps the number. This
> report was `docs/research/M60-bimodality.md` and any citation to that path means
> this file. **The experiment directory deliberately keeps its `M60-bimodality`
> name** — it is referenced by `SYNTHESIS.md` (facts 831 and 907) and by four other
> agents' reports (M55, M59, M64, and M54's `M60-robustness-mask-at-merge-time.md`),
> and renaming it would break live citations to fix a cosmetic mismatch. Prose in
> this report says M63; paths say M60, and they are the same milestone.
> **The scripts under `src/` also keep their `M60`/`M60b` print labels on
> purpose**: those labels are echoed verbatim into the frozen `data/*.txt` outputs
> that are this milestone's evidence, and `m60lib.py` is imported by thirty of
> them. Rewriting the labels without re-running would desync the scripts from the
> outputs they produced, and re-running to fix a name is exactly the manufactured
> work the owner asked agents not to do.

**This report has two parts, because the commission changed mid-milestone.**
M63 was originally asked whether the through-focus response at occluding edges is
bimodal. That is **Part I** (§1–§16), and it stands. The brief was then corrected:
`M21-occlusion-bimodality-measured.md` had already asked that question, and M25
had built a plant that failed to reproduce it at **0.23x — the wrong sign**
(fact 568). The corrected question is better and harder: **is the wrong sign the
phenomenon, or the instrument?** That is **Part II** (§17–§22), pre-registered
separately in `PREREGISTRATION-B.md` and committed before it was run.

Every claim below is labelled:

* **MEASURED** — a number this milestone computed from data, with the script and
  the output file named.
* **DERIVED** — algebra, or a consequence of a MEASURED number plus stated
  arithmetic. No new data.
* **ARGUED** — reasoning. Not evidence. Flagged so it can be attacked cheaply.

---

## 0. Verdict, first

### 0.1 Part I — the corpus

**The reviewer's load-bearing premise fails, and it fails at a specific step.**

The reviewer's chain is:

> occluding edge → veiled background → two-layer composite → **bimodal
> through-focus curve** → detect the bimodality → recover the background peak.

The bimodality is **there**. It is abundant: 78.3% of band pixels at
hand-labelled occluding edges carry a second through-focus peak that clears a
noise floor calibrated per cell against the project's injected noise model
(**MEASURED**). Occlusion cells beat no-discontinuity control cells with a
perfect rank separation, AUC 1.000 (**MEASURED**).

The premise fails at a specific step. **The inference from the bimodality to a
second depth is what fails**, and five independent measurements say so:

1. The statistic fires **just as hard** at silhouettes standing against a
   featureless white card, where there is no background texture to be veiled and
   a veiled-background peak is physically impossible. 78.9% vs 78.3%,
   AUC 0.600, p = 0.61 (**MEASURED**).
2. The second mode lands within 6 frames of the background's own focus frame
   — measured on an independent, unoccluded pixel set — in **7.2%** of
   occlusion band pixels (chance, from permuted pairing, 1.6%) (**MEASURED**).
3. The flag **does not reproduce** across two independent 299-frame captures of
   the same scene. At matched flag rate Cohen's κ = **+0.109** median, range
   −0.013 to +0.185. Among pixels flagged in both captures, `k2` agrees within
   6 frames only 8.5–16.5% of the time (**MEASURED**).
4. A **single-depth** mechanism reproduces the whole phenomenon. A high-contrast
   edge that defocuses produces a *pair* of secondary through-focus peaks whose
   offset from the primary grows linearly with distance from the edge. The law
   is derived in §9 (**DERIVED**), confirmed by halving the defocus rate and
   watching the offset multiply by 1.873 against a predicted 2.00 (**MEASURED**),
   and in a plant with a *known* second depth it captures the detected `k2`
   54–68% of the time while the true background peak is captured 0.0–1.0%
   (**MEASURED**).
5. That law's signature is visible on the real cells. The prominence of the
   second peak tracks **edge contrast**, not class: Spearman +0.772, p = 6.1e-6
   over 25 cells; normalised by contrast, occlusion cells and blank-card
   silhouettes sit within 16% of each other (**MEASURED**).

Downstream of that, the reviewer's other three unifications:

* **occlusion detection = posterior bimodality** — refuted, per the above.
* **confidence = posterior entropy** — entropy tracks something real but adds
  nothing. AUC 0.63 median for predicting cross-capture focus-frame
  disagreement; the primary peak's *height alone* gets 0.62 (**MEASURED**).
* **"no frame in focus" = mass at the stack boundary** — has no population to
  work on in this corpus. The registered statistic (argmax within 2 frames of
  either stack end) is **0.00% median, 1.09% max** across all 25 cells, and the
  soft version is exactly 0.0000 at the noise temperature in every class
  (**MEASURED**).

**What survives Part I.** Within roughly 8 px of the silhouette, the plant *does*
recover the true background peak 25–44% of the time (**MEASURED**), and on the
occlusion class the separation is comparable in median to the independently
measured depth step (sep/step median 1.15, n = 8) (**MEASURED**). A narrowly
scoped near-edge estimator is not excluded by this milestone. It is a different
and much smaller claim than the one under test.

### 0.2 Part II — the instrument

**Fact 568's headline is falsified. Fact 603's headline is an instrument
artifact. Neither conclusion required a new plant — only a different statistic on
the identical frames.**

Facts 150, 151, 152, 568 and 603 all rest on **one function**, `multipeak`,
defined once in M21 and copied **verbatim** into three M25 scripts (M25's own
comment says so). Its peak test is `> both neighbours + 0.04 × (that pixel's own
through-focus range)`. Four published probes attacked fact 568's wrong sign, and
**every one of them varied the plant. None varied the instrument** (**MEASURED**
from the source; the probe list is facts 568 and 603).

On M25's control plant, re-rendered from M25's own simulator at M25's own config
and then held **byte-fixed** while only the statistic changed:

| statistic | truth-gated veiling enrichment | placebo |
| --- | ---: | ---: |
| **S0** — M21's `multipeak`, verbatim | **0.19×** (reproduces fact 603's control exactly) | 1.05–1.07 ✓ |
| **S1** — same function, noise-thresholded | 0.70× / 0.82× — **disqualified**, placebo 1.25–1.26 | ✗ |
| **S2** — M63's prominence-over-noise | **1.21–1.23×**, the right sign | 1.05–1.07 ✓ |

1. **The mechanism is measured, not argued.** S0's denominator — the pixel's own
   curve range — is **3.94× larger** at truth-gated veiled pixels than at smooth
   ones, so S0 demands a ~4× higher bar exactly where occlusion lives
   (**MEASURED**). The *signal* is the same in both populations: median
   prominence 3.042 DN veiled vs 2.803 DN smooth, measured on the very cube S0
   operates on. Only the bar differs.
2. **Fact 568's claim that "the simulator does not contain the effect it was
   built to test" is FALSIFIED.** On the identical rendered frames a
   noise-calibrated statistic reads 1.21–1.23× — the right sign (**MEASURED**).
3. **Fact 603's "largest single effect ever measured on this statistic, 4.5×" is
   substantially denominator relief.** Multi-scale occluder geometry moves S0
   from 0.19× to **0.86×** — reproduced here exactly — while on the same frames
   S2 moves 1.23× → 1.11×, i.e. **not at all**, and the denominator inflation
   collapses from 3.94× to 1.26× (**MEASURED**). The geometry did not add
   veiling. It lowered the bar.
4. **A second, independent defect compounds the first.** S0 tests the largest
   *single-frame step* into a peak, not the peak's prominence, and the step is
   **9.2× smaller** than the prominence at these peak widths (~5.1 frames of
   rise). Applying S0's own `0.04 × range` bar to the prominence instead of the
   step — changing nothing else — moves 0.19× → **0.71×** (**MEASURED**).
5. **The statistic's sensitivity depends on stack depth.** On M63's 299-frame
   stacks, decimating to 23 frames raises S0's rate **2.8×** (17.2% → 48.5%,
   median over 10 cells) (**MEASURED**). Rates are not comparable across stacks
   of different depth, which is what facts 150–151 compare.

**But Part II does not rescue the reviewer.** The mandatory positive control
(T7) asked where S2's flagged second peak actually lands in a plant whose
background focus index is **known to be 16**. Answer: within ±2 frames of it
**47.8%** of the time, against a 26.3% uniform chance rate (**1.82×**) and 30.0%
in the no-background control population (**1.59×**) — **INDETERMINATE** against
the pre-registered bar of 2× on both. The `k2` histogram peaks not at the
background index but at the **stack boundary** (**MEASURED**). So the plant's
veiling is *partially* visible to a well-normalised detector: it knows which half
of the stack the background is in, and not which frame.

### 0.3 What the two parts say together

The owner's reframing put it as a disjunction — *either the instrument is broken,
or the phenomenon is not there.* **Measured answer: both, and they are not
independent.**

* The instrument **is** broken, in two named and separately measured ways, and
  that is why fact 568 got the wrong sign (§17–§20).
* The phenomenon **is** weak. Even in a plant built to contain veiling, with a
  12 px blur separation and rendered truth, a correctly normalised detector reads
  only 1.11–1.23× and cannot localise the background's focus frame (§21).
* And in the real corpus, Part I shows the bimodality that *is* abundant is
  dominated by a single-depth side-lobe, not by veiling.

**What this does not license.** M63 does **not** show that veiled-background
peaks do not exist. It shows that firing of a prominence-over-noise bimodality
statistic is not evidence of one, on this rig, in this corpus, at these labels;
and that the corpus's negative plant result was measured with an instrument that
cannot see the thing it was pointed at. The strongest limitation is stated in §12
and it is real: only **2 of 9** occlusion cells have a background with genuinely
focusable texture.

**One correction to the corrected brief.** `M6-residual-halo-measured.md` was
named as directly adjacent. It is not: it contains **zero** occurrences of
"occlusion", "veil", "bimodal" or "depth discontinuity" (**MEASURED**, grep). Its
"halo" is the focus-breathing rectangle expansion — a gather-area and
buffer-sizing quantity, per its own §2.2 ("a halo is a rectangle expansion"). The
two uses of the word name different things and M6 has no bearing on this question.

---

# PART I — the corpus


## 1. Why M63 exists when M21 already measured this

> **Read with §17.** Part I was designed from M21's *stated* gaps. Part II, written
> after the brief was corrected and M21 was re-read against its own source, finds
> a deeper reason: the statistic underlying M21's answer **cannot fire at edges**,
> which is measured in §19–§20. Section 1 is preserved as written because it is
> what the Part I design was actually based on.

M21 (`docs/research/M21-occlusion-bimodality-measured.md`, facts 150–152)
measured a version of this question and folded a result. M63 was commissioned
because M21's answer is *enrichment of a shape statistic at depth steps inferred
from the same focus volume*, and its own §8 lists three gaps that decide M63's
design (**ARGUED**, from reading M21):

1. M21 never used the calibrated noise model. Its only control was a
   frame-permutation placebo.
2. M21's "depth steps" were `|∇ argmax|` — derived from the focus volume it was
   testing — not labels. Its §8 lists "no ground truth" first.
3. M21 never measured the **separation in frames**, only the *rate* of
   multi-peakedness.

M63 supplies all three: an injected, externally validated noise model; hand
labels that never touch the focus volume; and separations in frames with their
dependence on `n` and on operator scale.

M13's "occluding-edge cells" were named in the brief as a ready-made hand-labelled
harness. **They are not.** They are a synthetic Porter-Duff plant
(`experiments/m13-window-depth/src/edge.rs`), and M13 §2.5 item 4 says so:
"the plant has no disocclusion; both layers are fully observed everywhere"
(**MEASURED**, by reading the source). M63 therefore re-implemented it in Python
in the role it can actually fill — a positive control — and hand-labelled its own
real cells.

---

## 2. Pre-registration

**Frozen and committed as `experiments/M60-bimodality/PREREGISTRATION.md` at
commit `5dee1f4`, before any occlusion-cell result existed.** The commit graph
carries that ordering. What follows is that document's load-bearing content,
reproduced here so this report can be read on its own; the committed file is
authoritative if they ever differ.

### 2.1 Data, and why these stacks

The corpus is `D:\personal\macro` (15 stacks), read only. `C:\dev\macro\test`
holds only a subset and was not used.

| stack | frames | ISO | shutter | marked | role |
| --- | ---: | ---: | ---: | ---: | --- |
| `bee-3` | 299 | 100 | 0.20 s | f/5.6 | **primary.** Finest focus sampling in the corpus; genuine occluding geometry (legs, antennae, wings standing off a body) |
| `bee-1` | 299 | 100 | 0.50 s | f/5.6 | **replication.** A different pose of the same subject (NCC 0.60 vs `bee-3`) |
| `bee-2` | 299 | 400 | 0.05 s | f/5.6 | **not an independent scene.** NCC **0.9562** vs `bee-3`. Used as an ISO arm and as the repeatability replicate, never counted as a second sample |
| `wrapped-text-1` | 130 | 100 | 0.067 s | f/5.6 | **negative control.** Printed text on a smoothly curved surface: dense broadband texture, continuous depth, no discontinuity anywhere, self-similar at the glyph pitch — simultaneously the no-occlusion control **and** the periodic-structure control |
| `wrapped-text-2` | 120 | 400 | 0.025 s | f/5.6 | negative control, second framing, second ISO |
| `109MSDCF` | 22 | 160 | 1.3 s | f/11 | shallow arm — **substituted, see §3** |

Excluded on purpose: `foam` (scene evolves during capture) and `coffee-bubbles`
(bubble motion). Both are confounds for this measurement, not features.
`112`/`113`/`119`/`coffee-bean` are not deeper than `bee-*`, carry no deliberate
occlusion, and `coffee-bean` is where M21's number already lives.

The three 299-frame stacks had never been touched by any milestone. They were
named `134MSDCF`/`135MSDCF`/`136MSDCF` and `131MSDCF`/`133MSDCF` when M63 started
and were **renamed by the owner while a probe was running**. The mapping is fixed
by exact fingerprint — frame count, ISO, shutter, EXIF timestamps — recorded in
`data/02-corpus-rename.txt`. Nothing under `D:\` was written.

**Rename confirmed independently after the milestone closed** (**MEASURED**). The
owner supplied an EXIF read of the five renamed directories taken from his own
copy. It agrees with `data/01-survey.csv` — which M63 wrote *before* the rename,
under the old names — on **all five stacks, on both ISO and shutter**:

| new name | old name | n | ISO | M63's shutter | owner's shutter |
| --- | --- | ---: | ---: | ---: | --- |
| `bee-1` | `134MSDCF` | 299 | 100 | 0.5000 s | 1/2 s ✓ |
| `bee-2` | `135MSDCF` | 299 | 400 | 0.0500 s | 1/20 s ✓ |
| `bee-3` | `136MSDCF` | 299 | 100 | 0.2000 s | 1/5 s ✓ |
| `wrapped-text-1` | `131MSDCF` | 130 | 100 | 0.0667 s | 1/15 s ✓ |
| `wrapped-text-2` | `133MSDCF` | 120 | 400 | 0.0250 s | 1/40 s ✓ |

**Reader's warning.** `data/01-survey.txt`, `data/01-survey.csv` and the
`fig/01-*` filenames are frozen artefacts written before the rename and therefore
carry the **old** names. Every script in `src/` and every number in this report
uses the new ones. The two naming schemes in this experiment directory are the
same bytes, not two different corpora.

### 2.6b A matched-scene pair, measured — and one that is not

`data/03-previews.txt` holds a normalised cross-correlation of the 8×-binned
first frame of all five stacks, computed for M63's own scene-identity check. It
bears on a question the owner has flagged as open — whether the ISO-100/ISO-400
captures are of a held scene — so it is surfaced here (**MEASURED**):

| pair | ISO | NCC |
| --- | --- | ---: |
| **`bee-2` vs `bee-3`** | 400 / 100 | **0.9562** |
| `bee-1` vs `bee-3` | 100 / 100 | 0.6036 |
| **`wrapped-text-1` vs `wrapped-text-2`** | 100 / 400 | **0.3834** |

**The two candidate matched-scene pairs are not equivalent.** `bee-2`/`bee-3` is
a genuine re-capture of one scene and M63 used it as such (§8.9). The
`wrapped-text` pair is **not** — 0.3834 is a different framing, which is also
what direct viewing showed when the cells were labelled (`src/cells.py` records
`wrapped-text-2` as "second framing, second ISO").

Two caveats, stated because this number will be reused: NCC is computed on frame
0 only, so it measures scene similarity at the *start* of each stack rather than
stability through it; and frame 0 of two stacks sits at different focus
positions, so some of any shortfall is focus, not motion. The 0.9562 / 0.3834 gap
is far larger than that effect could explain, but a milestone that needs
through-stack stability should measure it directly rather than inherit this.

### 2.2 Instrument

**Focus measure.** `f_k(x)` = box mean of Sobel gradient magnitude at radius `R`
on the G1 green sublattice, black level 512 subtracted. `R = 2` is the
**primary**, pre-registered from fact 152 (bimodality is depleted 0.36× at the
shipped `R = 13`, because a 27×27 CFA box is 54 sensor px and averages both
layers together). `R ∈ {1, 2, 4, 8}` swept.

**Noise.** `σ²(S) = g·S + (RN_e·g)²` with `g = max(ISO,100)/436.8` DN/e⁻,
`RN_e = 4.20` below ISO 400 and `1.2392` at or above; black 512, white 15360.
Transcribed from `crates/strehl-core` and asserted against that source in gate 0
(AGENTS rule 3 — injected, never re-derived).

`σ_f(k, x)`, the sampling sd of the focus response, is obtained by Monte Carlo:
draw independent noise at the observed signal level, recompute `f`, take the sd
over reps.

**Two-peak decomposition.** Per pixel: `k1 = argmax_k f_k`; `k2` = the interior
local maximum other than `k1` with the greatest prominence over the running
minimum between it and `k1`; `kd` = the argmin on `[k1, k2]`.

```
prom = f(k2) − f(kd)                        DN
z    = prom / sqrt( σ_f(k2)² + σ_f(kd)² )   dimensionless
```

Frames are independent captures, so the two variances add. **No smoothing along
the frame axis** (AGENTS rule 23) — a frame-axis smoother correlates neighbouring
samples and would make that addition wrong.

`prom` and the denominator are reported **separately** as well as the ratio
(AGENTS rule 39, discipline 338).

### 2.3 Registered threshold policy

`z*` is **not** fixed a priori and no σ-count is asserted. `k2` is a maximum over
O(n/2) candidate frames, so its null distribution is a multiplicity tail, not a
Gaussian tail; quoting "3σ" would be arithmetic and not evidence (AGENTS rule
20). `z*` is calibrated **per cell** on that cell's own noise-only null to a **1%
per-pixel false-positive rate at the same `n` and the same population size**.
Every hit rate is quoted against that `z*`, so all classes are compared at
matched FPR by construction.

### 2.4 Labels, and why they are drawn by eye

Bins and binned quantity must not share a driving mechanism (AGENTS rule 17,
discipline 358). M21's first number was 29.47× and collapsed to 4.38× once the
depth-step map moved to an independent scale, because a bimodal pixel
*manufactures* the `|∇ argmax|` step it is credited with landing on. The clean
fix is a label that never touches the focus volume:

* **Occlusion cells** — rectangles drawn by hand on rendered frames, each
  straddling a visible silhouette where a nearer element crosses in front of a
  farther one.
* Each cell carries two hand-drawn **reference patches**, `FG` and `BG`, on
  unambiguous unoccluded ground on each side, well away from the boundary.
* **Control cells** — rectangles on continuous surfaces, matched on texture and
  signal.

### 2.5 Hypotheses, with the falsifying observation stated in advance

| id | claim | predicted direction | falsified if |
| --- | --- | --- | --- |
| **H1** | real occluding edges show a second peak clearing the calibrated noise floor | hit rate at occlusion cells **>** matched controls | rates within the controls' own between-cell sd, or occlusion **<** control |
| **H2** | the separation is usable | \|k2 − k1\| well above the through-focus FWHM, and tracking the depth step measured from the *unoccluded* reference patches | \|k2 − k1\| piles up at ≤ FWHM, or is uncorrelated with the reference step |
| **H3** | bimodality is *occlusion*, not texture or periodicity | \|k2 − k_BG,ref\| at occlusion cells **<** the same under permuted cell↔reference pairing; and control-cell hit rate at the calibrated `z*` ≈ 1% | control cells fire at occlusion-like rates, or `k2` is unrelated to the background's own focus frame |
| **H4** | posterior entropy is a real confidence output | entropy separates occlusion from control with AUC > 0.55 | AUC ≤ 0.55, or entropy is degenerate/saturated, replicating M32 |

### 2.6 Controls, each with what it cannot separate

| id | control | what it cannot separate |
| --- | --- | --- |
| **N1** | **noise-only plant** — one real frame repeated `n` times with independent calibrated noise. True curve flat; every peak is noise. Sets `z*` | Blind to the calibration itself: draws noise from `g` and normalises by `g` (AGENTS rule 34, fact 599). Validates the *operator*, never the gain |
| **N2** | **frame permutation** (M21's placebo). Preserves the observed marginal exactly | The marginal contains one very tall in-focus value, so a permuted curve is not a noise curve. Bounds order-dependence, not amplitude |
| **N3** | **real no-discontinuity cells** — `wrapped-text-*` and single-surface bee patches | Cannot separate "no occlusion here" from "an occlusion this operator cannot see" |
| **N4** | **periodic structure** — printed glyphs repeat at a fixed pitch | Cannot rule out periodicity at a pitch this text does not contain |
| **N5** | **boundary mass** — fraction with `k1` within 2 frames of either end | Nothing. It is a definition, reported as a separate diagnosis, not as evidence for or against H1 |
| **the two-layer plant** (`P1` in the frozen file) | two layers at known separation, real textures, calibrated noise | fact 738 / discipline 358: the plant's blur ladder is mine, so it is read out as *recovered vs planted separation* and never against the constant that generated it |
| **B1** | **fact-73 blindness check** — box-mean \|∇\| on a monotone step at four blurs | If the operator is blind at the cells, nothing about curve *shape* there is admissible |

> Naming note: AGENTS rule 28 requires proposed facts to be numbered `P1, P2, …`.
> The pre-registration independently named its plant control `P1`. In this report
> `P1…P14` are **proposed facts** (§13) and the plant is always called "the
> two-layer plant".

### 2.7 Power, asserted before any result is read

Fact 779: a control on 22–107 px had no power and only its own count assertion
revealed it. So, before any hit rate is printed, the run asserts the pixel
population of every cell class, the number of independent cells per class, and
prints the minimum detectable difference at the realised `n`, using **between-cell**
spread rather than the binomial sd, because pixels within a cell are not
independent.

### 2.8 What this milestone will not do

No unmixing, no reconstruction, no merge change, no Rust. No claim about whether
a two-component fit *recovers* usable background — that is out of scope even if
H1 survives. No alignment model: drift is measured and reported as a bound, and
if it exceeds 1 green px on any stack used, the affected result is labelled
UNVERIFIED rather than corrected.

### 2.9 The outcome that would end this line of work

> If H1 fails — if the second peak is absent, or present at an amplitude
> indistinguishable from the calibrated noise floor, or present but equally
> common on a surface with no depth discontinuity — then the reviewer's cascade
> does not have a foundation on this rig, and that is the result. **It is not to
> be rescued by re-tuning `R`, the prominence rule or `z*`.** Any such retune is
> reported as a post-hoc arm, labelled so, and does not replace the registered
> one.

That clause is the one that decided this milestone. See §11.

---

## 3. Deviations from the pre-registration, declared

Three, all declared here rather than folded silently.

**D-1 — the shallow arm was substituted.** §2.1 registered `109MSDCF` (22 frames)
as the shallow arm. It was replaced by a **frame-density sweep on the same
cells**: the 299-frame curves thinned by stride 1/2/4/8/13 to n = 299/150/75/38/23.
This is a strictly better design for the registered question ("can a shallow
stack resolve two peaks at all?") because it varies `n` while holding the scene,
the geometry, the texture, the ISO and the labels fixed; the `109MSDCF` arm would
have confounded `n` with an entirely different subject at a different aperture.
Reported in §7.2. **This is a substitution, not a silent swap.**

**D-2 — the analysed pixel population is a subsample.** §2.7 asserts ≥ 20 000
band pixels per cell. The **labelled** band population satisfies that in every
cell (min 20 000 at `occ1-claw-card`, max 60 000, `data/06-cells.csv`). The
**analysed** population is a seeded 12 000-pixel subsample per cell
(`NPIX = 12000` in `src/09-curves.py`), taken for tractability at 299 frames ×
25 cells × 12 Monte-Carlo noise reps. 12 000 pixels resolve a per-cell hit rate
to ±0.89% binomially, which is far finer than any difference this report turns
on. The between-cell spread, not the within-cell binomial, is what limits every
class comparison.

**D-3 — `occ_flat` is a post-hoc sub-split of the occlusion class, and it is
under-powered on its own.** The pre-registration names two label classes,
occlusion and control. While drawing labels it became clear that some silhouettes
stand against the plain white card the bee is shot on and others against genuine
scene texture; those are physically different situations, so the occlusion class
was split into `occ` (n = 9) and `occ_flat` (n = 5). The registered classes still
pass their assertions: occlusion 14 cells ≥ 6, control 11 cells ≥ 6.
**`occ_flat` at 5 cells is below the registered ≥ 6 and is reported as
under-powered on its own**; it is used as a *direction* argument (it fires as
hard as `occ`), not as a precise effect size.

The split was frozen before any curve was extracted. The commit graph proves the
ordering only for the pre-registration itself; for the class split the evidence is
file mtimes — `src/cells.py` last written 14:39:38, first curve written 14:42:03
(**MEASURED**, filesystem). That is weaker evidence than a commit and is labelled
as such.

**One cell was dropped, with its reason recorded.** `occ1-leg-body-3` was
labelled, then dropped after its 4-frame contact sheet showed the rectangle
contains blank card and no silhouette (sd 104.82 DN against 782–1124 DN for the
other three `bee-1` occlusion cells, `data/06-cells.csv`). Final set: 9 `occ`,
5 `occ_flat`, 11 `ctl`.

---

## 4. Instrument gates — run before the hypothesis, all passed

### 4.1 Gate 0 — the library does what it says

`src/00-selftest.py` → `data/gate0.txt`. **GATE 0 PASSED** (**MEASURED**).

* G0.1 noise constants match `crates/strehl-core/src/profile.rs` exactly:
  `gain_divisor 436.8`, `base_iso 100`, `read_noise_e_low 4.2`,
  `read_noise_e_high 1.2392`, `second_base_iso 400`.
* G0.4 a hand-computed bimodal curve returns the hand value: prominence 5.000.
* G0.5 a *shoulder* returns prominence 1.000 — small, not zero. **The noise gate
  must do the rejecting**; the peak-finder deliberately does not.
* G0.7 a monotone-to-the-end curve puts `k1` at the boundary and reports no
  second peak.
* G0.8 **power**: a pure-noise cube, n = 60, 4096 px, gives max `z` = 4.87 and
  `frac(z > 6) = 0.0000`.
* G0.9 **power**: the same cube with two planted +8σ bumps gives `frac(z > 6)` =
  **0.8530**, median `z` = 6.70. The detector misses ~15% of a genuine 8σ bump.
  Recorded, not tuned away.
* G0.10 AGENTS rule 23: `sobel_mag` refuses a `(frames, y, x)` cube.

### 4.2 B1 — fact 73, and whether the operator can see the thing being measured

Fact 73 says the box mean of gradient magnitude is blind on monotone edges,
because blur conserves total variation. **An occluding edge is an edge**, so if
that blindness held at M63's operator scale, nothing about curve shape at these
cells would be admissible.

`src/13-plant.py` → `data/13-plant.txt` (**MEASURED**):

| σ | Σ\|∇\| across the edge | box R=60 | **box R=2 at the edge** | box R=2, 12 px off |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 1000.000000 | 8.264463 | **200.0000** | 0.0000 |
| 1 | 1000.000000 | 8.264463 | 193.2178 | −0.0000 |
| 2 | 1000.000000 | 8.264463 | 153.0815 | 0.0000 |
| 3 | 1000.000000 | 8.264463 | 116.9277 | 0.0924 |
| 6 | 1000.000000 | 8.264463 | 64.2671 | 8.3730 |
| 12 | 1000.000000 | 8.264463 | **32.9610** | 19.3375 |

Total variation across the edge varies by **6.8 × 10⁻¹³** over σ = 0…12 — fact 73
reproduced exactly, to machine precision. **But the R = 2 box at the edge falls
200.0 → 32.96, a ratio of 0.165.** The operator is *not* blind at R = 2; fact
73's blindness is a large-box property, and the shipped R = 13 sits on the wrong
side of it. **Gate passes: curve shape at these cells is admissible.** This also
explains fact 152's 0.36× depletion at R = 13 mechanically.

Note the last column: the response 12 px off the edge goes 0 → 19.34 as blur
grows. That column is the entire finding of §9, visible here before anyone went
looking for it.

### 4.3 The denominator is externally validated, not a null residual

Discipline 338: a separation score whose denominator is a null residual behaves
like a random number. Facts 695–706 refuted a metric of exactly that shape after
three milestones. M63's denominator is a *predicted* sd from an injected model,
which is the right shape — but that is worth nothing unless the model actually
predicts the observed scatter, and the check must not run against the constant
that generated the prediction (fact 738).

`src/22-sigmacheck.py` → `data/22-sigmacheck.txt`. On real frames, the robust
second difference `D_k = f_{k−1} − 2f_k + f_{k+1}` annihilates any locally linear
trend, so `σ_emp = MAD(D)·1.4826/√6` is an **upper bound** on the sampling sd
(real curvature inflates it; nothing deflates it). It shares no arithmetic with
the Monte-Carlo prediction (**MEASURED**):

| class | n | σ_emp/σ_pred on real frames | on flat null cubes |
| --- | ---: | ---: | ---: |
| `occ` | 9 | 0.96 (0.93–0.98) | 0.99 |
| `occ_flat` | 5 | 0.95 (0.89–0.97) | 1.00 |
| `ctl` | 11 | 0.99 (0.87–1.01) | 0.98 |
| **ALL** | **25** | **0.96 (0.87–1.01)** | **0.99 (0.96–1.02)** |

The injected model predicts the observed frame-to-frame scatter of the focus
response to within **4%** in median, over ISO 100 and 400 and over a 4.6× range of
absolute σ_f (1.00 → 4.58 DN). **DERIVED:** the ratio sits slightly *below* 1, so
the model very slightly over-predicts σ, which means every hit rate in this report
is if anything a slight *under*-estimate. That does not rescue anything, because
`occ`, `occ_flat` and `ctl` all share the same denominator.

**What this cannot separate** (AGENTS rule 34, fact 599): a wrong gain would move
σ_pred and appear here only as a constant ratio offset — which is exactly the
quantity measured. A 4% offset is equally consistent with a 4% gain error.

### 4.4 Monte-Carlo rep count

`src/21-sweeps.py` → `data/21-sweeps.txt`. Median σ_f at 6/12/24/96 reps:
2.10811 / 2.18596 / 2.20482 / 2.18154 DN. **12 reps, used throughout, is within
+0.20% of 96 reps** (**MEASURED**). The pre-registration promised this check
"before use"; it was in fact run after, and is labelled so.

### 4.5 Drift

`src/02-drift-and-cache.py` → `data/02-drift.txt` (**MEASURED**). Direct
frame-0-to-frame-k integer-pixel displacement is **0.00 px** at every span probed
(k = n/8, n/4, n/2, n−1) on all five stacks used. The span-1 ladder — a lower
bound per fact 51 — has max |d| ≤ 1.00 px per step everywhere. The pre-registered
1-green-px threshold is met; no result is labelled UNVERIFIED for drift.

---

## 5. Cells, and power asserted before any result

25 cells, hand-drawn on rendered frames, each visually confirmed on a 4-frame
contact sheet at fixed frame indices (`fig/08-sheet-*.png`). Nothing in the
labelling touches the focus volume.

Band, foreground and background are separated **by intensity only**, identically
in all three classes: `Ī = mean_k I_k`; band = top 20% of `|∇Ī|` (5-px smoothed);
interior = bottom 40%, split dark/pale at the cell median.

`src/18-classes.py` prints this **before** the first hit rate (**MEASURED**):

```
  class ctl        cells=11   band pixels per cell: min 12000  median 12000  total 132000
  class occ        cells= 9   band pixels per cell: min 12000  median 12000  total 108000
  class occ_flat   cells= 5   band pixels per cell: min 12000  median 12000  total  60000
```

**Effect size detectable.** The unit of analysis is the **cell**, not the pixel —
pixels within a cell are spatially correlated and are not independent samples.
With 9 `occ` against 11 `ctl` cells, a two-sided Mann-Whitney reaches p < 0.05
only when the two distributions barely overlap, so the smallest detectable effect
is roughly **a full separation of the per-class medians**. Within a cell, 12 000
band pixels resolve a hit rate to ±0.89% binomially, which is a lower bound on the
true interval. `occ_flat` at 5 cells is below the registered minimum (§3, D-3).

**This design cannot detect a subtle shift.** It can detect the difference the
reviewer's premise predicts — occlusion cells firing and non-discontinuity cells
not — and that is what it was built for.

---

## 6. H1 — does a second peak clear the calibrated noise floor?

`src/18-classes.py` → `data/18-classes.txt`. `z*` per cell at 1% FPR on that
cell's own noise-only null, so the null hit rate is 1.0% by construction in every
row (**MEASURED**):

| class | cells | median band hit rate | range |
| --- | ---: | ---: | --- |
| `occ` | 9 | **78.3%** | 69.8 – 90.6% |
| `occ_flat` | 5 | **78.9%** | 7.5 – 82.5% |
| `ctl` | 11 | **47.0%** | 4.9 – 59.4% |

| comparison | AUC | p |
| --- | ---: | ---: |
| `occ` vs `ctl` | **1.000** | 0.000197 |
| `occ` vs `occ_flat` | **0.600** | 0.61 |
| `occ_flat` vs `ctl` | 0.818 | 0.052 |

**H1 as registered: not falsified.** Every one of the 9 occlusion cells
(min 69.8%) exceeds every one of the 11 control cells (max 59.4%). The rank
separation is perfect.

**Deliverable item 1, plainly.** The fraction of labelled occlusion cells showing
a second through-focus peak that clears the calibrated noise floor is **9/9**;
within those cells the median fraction of *band pixels* that do is **78.3%**.
Matched on frame count (n = 299 only), `occ` 78.3%, `occ_flat` 78.9%, `ctl` 56.9%
(1 cell).

Three things immediately qualify it.

**6.1 The control fires too.** `ctl` cells sit at 47% median, not at the 1% their
own nulls were calibrated to. The `wrapped-text-*` cells are printed glyphs on a
smoothly curved surface with **no depth discontinuity anywhere** and a reference
depth step of 0–3 frames (§7.1). Roughly half their band pixels carry a second
peak that clears the calibrated noise floor. Whatever the statistic is measuring,
it is not exclusively occlusion.

**6.2 `occ_flat` is the control that matters, and it fires identically.** These
are silhouettes — a bee's leg, a claw — against the **featureless white card the
subject is shot on**. There is no background texture to be veiled, so a
veiled-background focus peak is physically impossible there. AUC against `occ` is
**0.600, p = 0.61**: indistinguishable.

**6.3 The permutation placebo saturates.** `src/21-sweeps.py` (**MEASURED**),
M21's control run on M63's cells at M63's calibrated `z*`: permuting the frame
order per pixel destroys all through-focus structure while preserving the
marginal exactly, and gives a hit rate of **100.0%** in every class (median), with
median separation 94–102 frames on the 299-frame stacks.

A hit rate of 78% therefore cannot be read as "78% of pixels have two depths".
A curve with *no depth structure at all* scores higher. The placebo bounds
order-dependence and nothing else — the permuted marginal still contains one very
tall in-focus value — but it disposes of any reading of the raw rate as a
population fraction.

---

## 7. H2 — the separation in frames, and the focus-step geometry

### 7.1 Separation vs the through-focus width and vs the labelled depth step

`src/20-audit.py` → `data/20-audit.txt`, `src/23-boundary.py` →
`data/23-boundary.txt` (**MEASURED**).

The physical focus step per frame is **not recorded** in EXIF for a rail or
focus-bracket capture, so all separations are quoted in frames and normalised two
ways: by the **measured primary-peak FWHM** (the operational through-focus
resolution of this operator on this rig, which is where facts 12 and 28 land in
practice — at these magnifications marked f/5.6 is optically far slower and the
MTF at Nyquist is at or near zero, so the peak cannot be arbitrarily sharp), and
by the **reference depth step** `|k_fg − k_bg|` measured on the two hand-drawn
unoccluded patches.

| class | primary-peak FWHM | median \|k2 − k1\| | ratio | reference step \|k_fg − k_bg\| | sep/step |
| --- | ---: | ---: | ---: | ---: | ---: |
| `occ` | 10 fr | **32 fr** | **3.6×** | 19 fr | **1.15** (n = 8) |
| `occ_flat` | 9 fr | 17 fr | 1.8× | 49 fr | 0.39 |
| `ctl` | 13 fr | 19 fr | 1.5× | **1 fr** | 18.00 |

**Deliverable item 2, plainly.** At occlusion cells the measured separation is
**32 frames, 3.6× the 10-frame primary-peak FWHM**. It is comfortably resolvable
— H2's first clause is not falsified.

**The labels validate themselves.** Control cells have `k_fg ≈ k_bg` — median
**1 frame** apart, i.e. glyph and paper at one depth, exactly as a
no-discontinuity label should. Occlusion cells have a real step, median 19 frames.
This is an independent check on the hand labels that never touches the band
pixels the hypothesis is tested on.

**But H2's second clause fails.** The separation does not track the step:

| class | n | Spearman(\|k2−k1\|, \|k_fg−k_bg\|) | p |
| --- | ---: | ---: | ---: |
| `occ` | 9 | +0.579 | 0.103 |
| `occ_flat` | 5 | −0.359 | 0.553 |
| `ctl` | 11 | −0.575 | 0.064 |
| **ALL** | **25** | **+0.066** | **0.755** |

Per-cell sep/step on the occlusion class ranges 0.61 to 2.11 — within a factor of
two of the step, but scattered, and not significantly correlated at n = 9. Across
all 25 cells the correlation is **+0.066**.

One cell settles the tone. **`occ3-antenna-eye` has a reference depth step of
exactly 0 frames** — both its unoccluded patches focus at frame 101 — and it has
the **highest hit rate in the corpus, 85.3%**, with a separation of 35 frames.
A hand-labelled silhouette whose two sides are at the same depth fires hardest.

### 7.2 The separation is not a property of the scene (D-1's substituted arm)

`src/18-classes.py`, frame-density sweep: the same cells, the same pixels, thinned
along the focus axis (**MEASURED**).

| cell | n=299 | n=150 | n=75 | n=38 | n=23 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `occ3-wing-thorax` hit / sep | 69.8% / 27 | 66.9% / 15 | 61.0% / 9 | 48.7% / 7 | 35.0% / 6 |
| `occ3-leg-hair-1` | 76.6% / 16 | 74.0% / 9 | 62.6% / 6 | 39.8% / 6 | 25.1% / 6 |
| `occ3-limb-abdomen` | 78.1% / 53 | 78.1% / 27 | 76.9% / 15 | 72.7% / 8 | 65.2% / 6 |
| `occ1-leg-body-1` | 90.6% / 27 | 88.7% / 15 | 84.5% / 8 | 71.4% / 6 | 59.5% / 4 |

**The separation scales as `n`.** 53 → 27 → 15 → 8 → 6; 27 → 15 → 9 → 7 → 6. A
separation that is a fixed depth difference in the scene would occupy a *fixed
fraction* of the stack and would therefore scale as `n` too — so this alone is
not decisive. What *is* decisive is the **floor at 4–6 frames**: below n ≈ 38 the
separation collapses to a small integer number of frames regardless of cell, which
is the peak-finder's own resolution, not the scene's.

**And the hit rate falls with `n`**: 78% → 35% for `occ3-wing-thorax`, 76.6% →
25.1% for `occ3-leg-hair-1`. **DERIVED:** a real second mode at a real second
depth does not become *less* detectable when the same focus range is sampled more
coarsely — its amplitude is unchanged and its prominence is unchanged; only the
number of noise samples competing for the maximum falls, which if anything should
*reduce* false positives and raise the true rate. The observed direction is what a
statistic dominated by curve wiggle does. **The registered shallow-stack question
is answered: a 23-frame stack resolves almost nothing here** — separations pile up
at 4–6 frames, at or below the primary-peak FWHM, which is exactly H2's stated
falsification condition.

### 7.3 The separation is not a property of the scene, second demonstration

`src/21-sweeps.py`, R sweep on 5 cells (**MEASURED**):

| cell | R=1 | R=2 | R=4 | R=8 |
| --- | ---: | ---: | ---: | ---: |
| `occ3-wing-thorax` hit / sep | 18.8% / 21 | 33.6% / 27 | 39.1% / 46 | 34.9% / 68 |
| `occ3-limb-abdomen` | 22.0% / 46 | 35.8% / 53 | 48.5% / 63 | 56.0% / 67 |
| `occ3-antenna-head` | 16.7% / 47 | 26.6% / 49 | 38.7% / 54 | 51.6% / 63 |
| `occ3-leg-card-2` (`occ_flat`) | 20.4% / 22 | 32.3% / 24 | 43.7% / 30 | 44.5% / 37 |
| `ctl3-eye` (`ctl`) | 9.0% / 26 | 18.0% / 32 | 27.9% / 48 | 37.8% / 79 |

**The measured separation grows monotonically with the operator's box radius** —
21 → 68 frames on `occ3-wing-thorax`, 26 → **79** on a *control* cell with a
1-frame depth step. A separation that measures a depth difference in the scene
must be invariant to the size of the box used to measure it. This one is not.

(The R-sweep's absolute hit rates are lower than §6's because it uses a
single-draw σ estimator rather than the 12-rep Monte Carlo, which inflates the
denominator. It is internally consistent across R, so the *trend* is valid; the
absolute rates are not comparable to §6 and are not quoted as such.)

---

## 8. H3 and the discriminators — measured, not asserted

The brief required each discriminator to be stated with what it cannot separate,
and then *measured*. Here is each one with its result.

### 8.1 Noise — the control that matters most

**Instrument:** per-cell `z*` calibrated on a matched noise-only null (N1), 1% FPR
by construction; denominator externally validated to 4% (§4.3).
**Result:** it does its job, and the numerator — not the denominator — is what
separates the classes (`src/24-numden.py` → `data/24-numden.txt`, **MEASURED**):

| class | `prom` = f(k2)−f(kd), median | `denom`, median | median `z` | `z*` range | null `prom` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `occ` | **37.79 DN** (25.16–67.91) | 3.012 DN | **14.52** (9.49–23.08) | 5.48–5.92 | 8.0–14.1 DN |
| `occ_flat` | 28.54 DN (13.98–31.02) | 2.881 DN | 10.93 (3.22–11.39) | 5.55–5.85 | 9.4–15.0 DN |
| `ctl` | 11.04 DN (8.13–18.59) | 2.268 DN | 4.66 (2.81–6.49) | 4.86–5.38 | 5.0–21.3 DN |

Median `z` at occlusion cells is **14.52 against a threshold of 5.5–5.9**. The
apparent second peak is not one noise sigma; it is a ~38 DN prominence against a
~3 DN predicted sd, on cells whose own noise-only nulls produce a median
prominence of only 8–14 DN. Per AGENTS rule 39 and discipline 338, the two parts
are published separately precisely so this can be checked: the denominators are
nearly equal across classes (2.27–3.01 DN) while the numerators differ by 3.4×.
**The denominator is not doing the work.**
**What it cannot separate:** it draws noise from `g` and normalises by `g` (AGENTS
rule 34, fact 599), so it validates the operator, never the gain. §4.3 bounds that
at 4% but cannot rule it out.
**Verdict:** noise is **excluded** as the explanation. The bimodality is real
signal structure.

### 8.2 Bimodal texture at one depth

**Instrument:** `occ_flat` (silhouette against a featureless card — two spatial
frequencies, one depth, by construction) and `ctl3-eye` (a single continuous
surface with strong texture).
**Result:** `occ_flat` fires at **78.9%**, indistinguishable from `occ` at 78.3%
(AUC 0.600, p = 0.61). `ctl3-eye` fires at 56.9%.
**What it cannot separate:** `occ_flat` cannot separate "no background to veil"
from "a background this operator cannot see" — but §4.2 shows the operator is not
blind at R = 2, and §8.6's texture audit shows the `occ_flat` backgrounds have a
peak-to-floor focus ratio of 1.55–1.81, i.e. no focusable texture at all.
**Verdict:** **not excluded.** The statistic does not distinguish one-depth
structure from two-depth structure.

### 8.3 Periodic and self-similar structure

**Instrument:** `wrapped-text-1` and `wrapped-text-2` — printed glyphs at a fixed
pitch on a smoothly curved surface, no discontinuity anywhere.
**Result:** 47.0% median hit rate (range 4.9–59.4%), and a `k2`-lands-near-`k_bg`
rate of **20.1%** — *higher* than the occlusion class's 7.2%, because with
`k_fg ≈ k_bg` any second peak near the primary counts. Separation 17–36 frames,
1.2–7.2× FWHM.
**What it cannot separate:** cannot rule out periodicity at a pitch this text does
not contain (N4's stated blind spot). The macro corpus is coffee, foam and
bubbles; glyph pitch is not bubble pitch.
**Verdict:** **not excluded as a contributor.** Periodic structure produces
abundant second peaks that clear the calibrated noise floor. It is separable from
occlusion only in that occlusion cells score higher (AUC 1.000) — but so does
`occ_flat`, which has no depth discontinuity either, so the AUC is not evidence
that the difference is *depth*.

### 8.4 The stack running out of frames

**Instrument (registered form, no free parameter):** fraction of band pixels whose
`k1` is within 2 frames of either stack end. `src/23-boundary.py` (**MEASURED**).

| class | k1 at boundary, median | max | k2 at boundary, median |
| --- | ---: | ---: | ---: |
| `occ` | **0.00%** | 0.04% | 0.12% |
| `occ_flat` | **0.00%** | 1.09% | 0.37% |
| `ctl` | **0.00%** | 0.08% | 2.38% |

**Soft form** (posterior mass in the outer 5% of frames, at the calibrated noise
temperature): **0.0000** median and **0.0000** at p90, in every class
(`data/18-classes.txt`).

**Verdict:** this diagnosis has **no population** in this corpus. Every cell in
every stack has its focus peak comfortably interior. The reviewer's fourth
unification is not wrong — it is untestable here, and §10 shows the soft form is
not even expressible at the noise temperature.

### 8.5 The one the pre-registration did not list: a single defocusing edge

See §9. It is the discriminator that decided the milestone, and M63 did not know
it existed when the pre-registration was frozen. It is therefore **post-hoc and
labelled so** — but it is *derived analytically* and confirmed against a plant
whose ground truth is known, which is a different epistemic status from a
post-hoc threshold retune.

### 8.6 Is the second mode at the background's focus frame? (H3 proper)

`k_bg` = median argmax over the cell's **pale interior** pixels — a different
pixel set from the band, so this is not circular (**MEASURED**,
`data/18-classes.txt`):

| class | \|k_fg − k_bg\| median | `k2` within 6 fr of `k_bg` | same, permuted pairing |
| --- | ---: | ---: | ---: |
| `occ` | 19 fr | **7.2%** | 1.6% |
| `occ_flat` | 49 fr | 2.9% | 0.5% |
| `ctl` | 1 fr | 20.1% | 10.8% |

**H3 splits.** Its first clause — occlusion `k2` closer to `k_bg` than under
permuted cell↔reference pairing — is **not falsified**: 7.2% vs 1.6% is a genuine
4.5× enrichment above chance. Its second clause — control cells firing at ≈1% —
is **flatly falsified**: they fire at 47%.

And 7.2% is not a detector. **DERIVED:** if the veiled-background peak were the
thing the statistic finds, this number would be a large fraction, not single
digits. 92.8% of the time the second mode is somewhere else.

### 8.7 Texture audit — can these backgrounds be veiled at all?

`src/20-audit.py`, per pixel: `median_p(max_k f) / median_p(median_k f)`. A pixel
with no focusable texture has a ratio near 1 (**MEASURED**):

| class | background peak/floor, median | range |
| --- | ---: | --- |
| `occ` | **1.58** | 1.54 – **13.85** |
| `occ_flat` | 1.58 | 1.55 – 1.81 |
| `ctl` | 3.60 | 2.24 – 6.37 |

**This is the milestone's most uncomfortable number and it is stated plainly.**
The bee is shot on a white card, so most `occ` cells' "backgrounds" are that card.
Only **`occ3-wing-thorax` (13.85)** and **`occ3-antenna-eye` (6.15)** have
genuinely textured backgrounds. **n = 2.** See §12.

### 8.8 The distance discriminator — and the one point that favours the reviewer

`src/16-distance.py`, `src/20-audit.py`. Theil-Sen slope of `|k2 − k1|` against
distance to the silhouette (**MEASURED**):

| class | slope, median | range | spread of sep across distance bins |
| --- | ---: | --- | ---: |
| `occ` | **+0.053** fr/px | −0.462 to +0.692 | 19 fr |
| `occ_flat` | −0.387 fr/px | −0.561 to +0.000 | 18.5 fr |
| `ctl` | **+0.632** fr/px | −0.258 to +0.947 | 44 fr |

**This is reported because it cuts against the rest of the report.** Under the
side-lobe law (§9) the separation must *grow* with distance from the edge; under a
fixed second depth it must be flat. The occlusion class has a slope of
**+0.053 fr/px — flat**, which is what the reviewer predicts. The **control**
class has +0.632 fr/px, which is the side-lobe law, clearly.

Two readings, and M63 cannot choose between them with the data it has
(**ARGUED**): either occlusion cells genuinely carry a fixed second depth that the
side-lobe hides in aggregate, or the occlusion cells' silhouettes are so convoluted
(hairs, antennae, legs at all angles) that "distance to the nearest silhouette" is
a much noisier regressor there than on a text page, flattening the slope. The
per-cell range on `occ`, −0.462 to +0.692, spans both signs and is consistent with
the second reading. **This is the strongest surviving point in the reviewer's
favour and it deserves a dedicated measurement, not this one.**

### 8.9 The replicate test — the decisive result

`src/17-repeat.py`, `src/20-audit.py`. `bee-2` and `bee-3` are the **same scene**,
independently captured, 299 frames each, NCC 0.9562 — measured, not assumed. The
comparison uses `bee-3`'s frozen pixel selection and a measured global frame
offset of **−2.0 frames**. Flag rates are **matched** between captures rather than
thresholded independently, so the agreement statistic is not inflated by a rate
mismatch (**MEASURED**):

| cell | class | flag rate (both) | agree | chance | **κ** | `k2` within 6 fr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `occ3-wing-thorax` | occ | 69.8% | 57.3% | 57.8% | **−0.013** | 12.3% |
| `occ3-leg-hair-1` | occ | 76.6% | 68.1% | 64.2% | +0.110 | 16.5% |
| `occ3-leg-hair-2` | occ | 78.3% | 69.6% | 66.0% | +0.107 | 13.4% |
| `occ3-limb-abdomen` | occ | 78.1% | 66.0% | 65.8% | **+0.006** | 9.8% |
| `occ3-antenna-head` | occ | 73.7% | 66.7% | 61.2% | +0.142 | 9.9% |
| `occ3-antenna-eye` | occ | 85.3% | 76.5% | 74.9% | +0.064 | 11.9% |
| `occ3-leg-card-1` | occ_flat | 82.5% | 74.2% | 71.1% | +0.108 | 10.7% |
| `occ3-claw-card` | occ_flat | 78.9% | 70.9% | 66.7% | +0.124 | 8.5% |
| `occ3-leg-card-2` | occ_flat | 79.0% | 71.3% | 66.8% | +0.135 | 15.2% |
| `ctl3-eye` | ctl | 56.9% | 60.0% | 50.9% | +0.185 | 10.0% |

**Cohen's κ median +0.109, range −0.013 to +0.185.**

Point-estimate repeatability, same pairs: `|Δk1|` median 5–24 frames, p90 32–86
frames (`data/19-entropy.txt`).

**DERIVED:** if the bimodality flag were a property of the scene — of where the
legs are relative to the body — it would reproduce when the scene is photographed
again. κ ≈ 0.11 is agreement barely above chance. Among the pixels flagged in
*both* captures, the two captures locate the second peak within 6 frames of each
other **8.5–16.5%** of the time. The flag is dominated by something that changes
between two captures of the same static subject.

Note the `ctl3-eye` row: the **control** cell has the *highest* κ of the ten. That
is not a defect in the test, it is a further problem for the hypothesis.

---

## 9. The mechanism nobody listed: the defocus side-lobe

This is the milestone's main positive contribution, and it was not in the
pre-registration. It emerged when the **two-layer plant's own D = 0 null** — two
layers at the *same* depth, where by construction there is nothing to detect —
fired at `z ≈ 17`, far above the noise floor.

### 9.1 The law (DERIVED)

Take a step edge of height `ΔI` at position 0, blurred by a Gaussian of width σ.
The image is `ΔI·Φ_σ(x)` plus a constant, so its gradient magnitude at offset `x`
from the edge is exactly

```
|∇I|(x) = ΔI · G_σ(x) = ΔI · exp(−x²/2σ²) / (σ√(2π))
```

Differentiate with respect to σ at fixed `x`: this is **zero at σ = 0**, rises to
a **maximum at σ = |x|**, and decays as `1/σ` thereafter.

Now put it on the focus axis. Defocus grows roughly linearly with distance from
the focused frame, `σ_k ≈ rate · |k − k_focus|`. Substituting:

**a pixel at fixed offset `x` from a high-contrast edge has a local maximum of its
through-focus gradient response at `|k − k_focus| = |x| / rate`.**

Since `x` can be either side, this is a **symmetric pair** of secondary peaks
straddling the primary. **There is one depth in this derivation.** No occlusion,
no veil, no second layer. And the offset **grows linearly with distance from the
edge** — which is the signature that separates it from a fixed second depth.

§4.2's last column is this law showing up before anyone looked for it: the R = 2
box 12 px off the edge goes 0.0000 → 19.3375 as σ goes 0 → 12, peaking near σ = 12.

### 9.2 Confirmation on a physically correct single-depth plant (MEASURED)

`src/15-sidelobe.py` → `data/15-sidelobe.txt`, `fig/15-sidelobe.png`. Composite
first, then blur — the physically correct order, so this is not an artefact of a
layered matte.

| x (px) | lobe offset, right | left | predicted x/rate | lobe/focus height |
| ---: | ---: | ---: | ---: | ---: |
| 2 | 1 | 1 | 4.0 | 0.98 |
| 4 | 9 | 8 | 8.0 | 6.17 |
| 6 | 14 | 12 | 12.0 | 4.28 |
| 8 | 17 | 20 | 16.0 | 3.32 |
| 12 | 26 | 26 | 24.0 | 2.28 |
| 16 | 32 | 34 | 32.0 | 1.75 |
| 24 | 47 | 40 | 48.0 | 1.60 |
| 32 | 53 | 39 | 64.0 | 1.30 |

Three local maxima at a single depth: the focus spike and a symmetric side-lobe
pair. **The lobes are up to 6× taller than the in-focus response at the same
pixel** — this is not a subtle wiggle.

**The rate test.** Halving the defocus rate must double the offset if the law is
`σ = x`. Measured ratio of offsets (rate 0.25 / rate 0.50) = **1.873** against a
predicted **2.00** (**MEASURED**). The shortfall is at large `x`, where the
predicted offset (96–128 frames) exceeds what a 120-frame stack can hold and the
lobe is truncated by the stack boundary — visible in the table as the measured
offsets saturating near 76–77 while the prediction runs to 128.

Per fact 738 and discipline 358, the readout is **recovered offset vs predicted
offset**, and the rate is varied so the law is tested against a *change* it
predicts, not against the constant that generated the plant.

### 9.3 With a real second depth planted, which peak does the detector find?

`src/15-sidelobe.py`, n = 120, foreground focused at frame 40, background planted
at `D` frames beyond it, rate 0.50 (**MEASURED**):

| D | x ≈ 4.5 px | x ≈ 12 px | x ≈ 20 px | x ≈ 32 px |
| ---: | --- | --- | --- | --- |
| 20 | true bg **25.1%** / lobe 54.3% | 0.5% / **68.1%** | 0.0% / 53.8% | 0.0% / 17.1% |
| 40 | true bg **42.9%** / lobe 55.8% | 0.4% / **68.4%** | 0.0% / 56.9% | 0.1% / 2.9% |
| 60 | true bg **43.5%** / lobe 56.1% | 1.0% / **68.0%** | 0.0% / 58.7% | 0.1% / 0.1% |

Beyond about 8 px from the edge, the detected `k2` lands on the **side-lobe
54–68%** of the time and within 6 frames of the **true background peak 0.0–1.0%**
of the time — with a genuine second depth present and fully observable.

**Within ~4.5 px of the edge it does find the true background peak 25–44% of the
time.** That is the positive residue, and it is the only part of the reviewer's
reconstruction proposal this milestone leaves standing.

### 9.4 The law's prediction, checked on the real cells

P5 says the lobe height is proportional to the step height `ΔI`. So on real data
the *numerator* of `z` should track edge contrast and should not care about the
class label. `src/24-numden.py` → `data/24-numden.txt` (**MEASURED**):

* **Spearman(`prom`, band peak focus response) over all 25 cells = +0.772,
  p = 6.1e-6.**
* `prom` normalised by band peak response: `occ` **0.2145**, `occ_flat`
  **0.1849**, `ctl` 0.1333.

`occ` cells do carry a larger raw prominence than `occ_flat` — 37.79 vs 28.54 DN
(§8.1) — but they also have more edge contrast (band peak focus response 188.44
vs 151.08, `data/20-audit.txt`). **Once normalised by contrast the two classes
are within 16% of each other**, while the no-discontinuity class sits 30–40%
lower. **DERIVED:** the extra prominence at occlusion cells is their extra edge
contrast, which is what §9.1 predicts and what a second depth does not.

### 9.5 The detector works, and its ceiling is low
The two-layer plant (`src/13-plant.py` → `data/13-plant.txt`), textured
background, veil zone = the 24 px of background nearest the silhouette
(**MEASURED**):

| rate | D=0 | D=5 | D=10 | D=20 | D=40 | D=60 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.25 | 1.9% | 9.2% | 13.7% | 14.5% | 15.1% | 16.2% |
| 0.50 | 0.9% | 14.1% | 14.7% | 16.9% | 17.4% | 18.2% |

The detector **does** respond to a planted second depth — 0.9–1.9% at D = 0 rising
to 16–18% at D = 60 — so it is not broken. But its ceiling is ~18%, and far-background
pixels (beyond the veil zone) hit **0.0%** at every D, correctly.

**And the threshold does not transfer.** The `P1b` arm repeats the plant with an
**untextured** background — fact 73's case — and applies the textured cell's `z*`:
**16.8% at D = 0**, i.e. indistinguishable from the 16.2% it gives at D = 60
(**MEASURED**). A `z*` calibrated on textured data is meaningless on untextured
data. M63's per-cell matched-null design already handles this; it is recorded
because any future detector that calibrates a single global threshold will walk
straight into it.

---

## 10. H4 — posterior entropy, the reviewer's proposed confidence output

`src/19-entropy.py` → `data/19-entropy.txt`. Posterior over frame-of-best-focus
formed as `softmax(f_k / T)`, normalised entropy in [0, 1].

**At the calibrated noise temperature the posterior is a near-delta** (**MEASURED**):

| class | T=0.5 | T=1.0 | T=2.0 | T=5.0 | T=20 | T=100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `occ` | 0.0056 | 0.0495 | 0.1147 | 0.2196 | 0.7911 | 0.9973 |
| `occ_flat` | 0.0100 | 0.0643 | 0.1244 | 0.2557 | 0.8968 | 0.9983 |
| `ctl` | 0.0336 | 0.1196 | 0.2226 | 0.4022 | 0.9306 | 0.9981 |

Median H at T = median σ_f is **0.0056 / 0.0100 / 0.0336**. This is the M32
degeneracy: the posterior carries essentially no spread until the temperature is
raised well past the noise scale, and by T = 100 it is saturated at 1.0.

**Boundary mass is not expressible.** At the noise temperature, posterior mass in
the outer 5% of frames is **exactly 0.0000** in every class at median and at p90.
It only becomes non-zero (0.014–0.100) at T ≈ 20σ — an **uncalibrated free
parameter**, chosen to make the output non-trivial. **DERIVED:** an output that
exists only at a temperature chosen to make it exist is not a measurement.

### 10.1 Does entropy track anything real?

The right target is not class label — it is *error*. Using the `bee-2`/`bee-3`
replicate, ask entropy to predict which pixels' focus-frame estimate disagrees by
more than 10 frames between two captures of the same scene (**MEASURED**):

| cell | class | frac \|Δk1\| > 10 fr | **AUC entropy** (T=σ) | AUC entropy (T=20σ) | **AUC peak height alone** |
| --- | --- | ---: | ---: | ---: | ---: |
| `occ3-wing-thorax` | occ | 35.2% | 0.669 | 0.659 | 0.649 |
| `occ3-leg-hair-1` | occ | 31.4% | 0.665 | 0.658 | 0.652 |
| `occ3-leg-hair-2` | occ | 53.9% | 0.658 | 0.603 | 0.584 |
| `occ3-limb-abdomen` | occ | 75.6% | 0.593 | 0.566 | 0.596 |
| `occ3-antenna-head` | occ | 89.5% | 0.595 | 0.561 | 0.544 |
| `occ3-antenna-eye` | occ | 63.4% | 0.564 | 0.538 | 0.508 |
| `occ3-leg-card-1` | occ_flat | 40.8% | 0.692 | 0.672 | 0.647 |
| `occ3-claw-card` | occ_flat | 43.8% | **0.792** | 0.762 | 0.753 |
| `occ3-leg-card-2` | occ_flat | 52.5% | 0.600 | 0.623 | **0.627** |
| `ctl3-eye` | ctl | 38.1% | 0.594 | 0.741 | 0.727 |

**Deliverable item 5, plainly.** Entropy tracks something real: AUC 0.564–0.792,
median ≈ **0.63**, above chance in all ten cells. H4's registered threshold
(AUC > 0.55) is met.

**And it adds nothing.** The primary peak's **height alone** — one number,
already computed, requiring no posterior at all — gets 0.508–0.753, median
≈ **0.62**. The gap is 0.01 AUC. On `occ3-limb-abdomen` and `occ3-leg-card-2` the
peak height *beats* entropy.

Entropy does do one thing correctly: `occ1-claw-card`, the cell with no focusable
texture anywhere (peak/floor 1.62, hit rate 7.5%), has entropy **0.902 at T = 1**
against 0.026–0.097 for every other cell. **Entropy correctly flags "there is no
information in this pixel."** That is a real and useful property. It is also a
property that a signal-level check would deliver more cheaply.

**Verdict on the reviewer's confidence claim:** the direction is right, the
magnitude is not worth the machinery. A posterior is not needed to learn that a
tall sharp peak is more trustworthy than a low flat one.

---

## 11. Does the reviewer's premise survive?

**Deliverable item 4, explicitly. No.** Here is exactly which part failed.

| step in the argument | status | evidence |
| --- | --- | --- |
| a background pixel near an occluding boundary is veiled by defocused foreground | **not tested** — physically uncontroversial, and M63 measured no unmixing | — |
| the observation is a two-layer composite | **not tested** | — |
| its through-focus curve is bimodal | **MEASURED, TRUE, and much more common than claimed** | 78.3% of occlusion band pixels clear a calibrated noise floor; 9/9 cells; AUC 1.000 vs control (§6) |
| **the bimodality identifies occlusion** | **MEASURED, FALSE** | fires at 78.9% where no background exists to veil (§6.2); control cells at 47% (§6.1); permutation placebo at 100% (§6.3) |
| **the second mode is the background's focus frame** | **MEASURED, FALSE** | 7.2% of pixels, vs 1.6% chance (§8.6); in a plant with a known second depth, 0.0–1.0% beyond 8 px while the single-depth side-lobe takes 54–68% (§9.3) |
| **the separation is a property of the scene** | **MEASURED, FALSE** | grows monotonically with the operator box radius, 21→68 frames (§7.3); floors at 4–6 frames as `n` falls (§7.2); κ ≈ 0.11 across two captures of the same scene (§8.9) |
| no selector can be right at an occluding edge | **not tested, and untouched by this result** | M63 measured detectability, not selector error |
| a reconstruction could fit the two-component model in bimodal cells | **premise removed** — "bimodal cells" is not a usable population selector | §6.2, §8.6, §8.9 |
| posterior entropy is confidence | **MEASURED, TRUE BUT REDUNDANT** | AUC 0.63 vs 0.62 for peak height alone (§10.1) |
| bimodality is occlusion detection | **MEASURED, FALSE** | as above |
| boundary mass is "no frame in focus" | **MEASURED, NO POPULATION** | 0.00% median, 1.09% max on the registered statistic; 0.0000 on the soft one (§8.4) |

**The failing step is the inference, not the observation.** "Bimodal ⇒ two depths
⇒ the second mode is the background's focus" is false on this rig, at this
operator scale, on this corpus. Bimodality at edges is dominated by a
**single-depth** mechanism: a high-contrast edge that goes out of focus produces a
symmetric pair of gradient-response maxima whose offset from the primary grows
linearly with distance from the edge (§9). This mechanism was not on the brief's
list of three confounds. It is now the fourth, and on this evidence it is the
largest.

**The cascade the reviewer builds on the premise does not have a foundation
here.** Merge weights as a posterior-weighted matched filter is not addressed
either way by this milestone. Confidence-as-entropy is real but redundant.
Occlusion-detection-as-bimodality is refuted. Boundary-mass-as-"no frame in focus"
has no population.

**Per §2.9, this is not rescued by retuning.** The R sweep and the frame-density
sweep were run because they were registered, and both made the picture *worse*,
not better. No threshold, prominence rule or radius was changed to improve any
number in this report.

### 11.1 What a future milestone could still do

**ARGUED**, offered so the negative result is actionable:

1. **Subtract the lobe before looking for a mode.** The law `ΔI · G_σ(x)` is
   analytic and its parameters (`ΔI`, `rate`, `x`) are estimable from the same
   volume. A statistic that fits and removes the side-lobe pair, *then* asks
   whether a residual second mode survives, is a genuinely different instrument
   from the one M63 refuted. M63 did not build it.
2. **Restrict to the near-edge band.** The plant recovers the true background peak
   25–44% of the time within ~4.5 px, and 0.0–1.0% beyond 8 px (§9.3). A
   deliberately narrow near-edge estimator is not excluded.
3. **Test the flat distance slope.** §8.8 is the one measurement that favours the
   reviewer and M63 cannot resolve it. It needs cells with clean, straight,
   well-separated silhouettes so that distance-to-edge is a clean regressor.
4. **Capture the missing data.** See §15 item 4 — this corpus does not contain the
   case the hypothesis is actually about.
5. **Read §17–§24 first.** Part II measures that the corpus's *prior* answer to
   this question was produced by an instrument that cannot fire at edges. That
   does not change §11's verdict — Part II's own plant reads 1.11–1.23× with a
   working statistic, and 0.87× on M63's real occlusion cells (§23.1) — but it
   changes which existing facts a future milestone should trust as its starting
   point.

---

## 12. Limitations, blunt

1. **Only 2 of 9 occlusion cells have a genuinely textured background.** The bee
   is photographed on a white card. The background peak/floor focus ratio is 1.58
   median across `occ` (§8.7); only `occ3-wing-thorax` (13.85) and
   `occ3-antenna-eye` (6.15) have backgrounds with real focusable structure.
   **M63 therefore cannot claim to have refuted "veiled background peaks exist in
   textured-background occlusion."** It claims something narrower and still
   decisive: *firing of this statistic is not evidence that one is present.*
   Note that `occ3-antenna-eye` — one of the two — has a measured depth step of
   **zero frames** (§7.1), which leaves n = 1 fully clean case.
2. **`bee-1`, `bee-2` and `bee-3` are one subject, one session, one card.** The
   replicate test compares two captures of the same scene, not two scenes. A κ of
   0.11 is a strong result *for that comparison* and says nothing about
   generalisation across subjects.
3. **No ground-truth depth.** The reference depth step is `|k_fg − k_bg|` from
   hand-drawn unoccluded patches, which is a focus-derived quantity on an
   *independent pixel set* — better than M21's `|∇ argmax|`, but not metrology.
   Nothing in this corpus has a measured depth map.
4. **`occ_flat` has 5 cells, below the registered 6** (§3, D-3). It is used
   directionally.
5. **The side-lobe law was derived after the pre-registration was frozen.** Its
   confirmations (the rate test, the depth-planted arm) are proper tests of a
   prediction the law makes, but the arm as a whole is post-hoc and is labelled so
   throughout.
6. **`z*` is calibrated per cell**, so hit rates are comparable across classes at
   matched FPR but are **not** absolute probabilities of anything.
7. **The MC convergence check was run after use, not before**, contrary to §2.2's
   wording. It passed (+0.20% at 12 reps vs 96), but the ordering was not as
   promised.
8. **No milestone-level replication.** Everything here is one agent, one pass.
   The scripts are deterministic given their seeds and every number in this report
   names the file it came from.
9. **A circular polarizer is in the optical path for every frame M63 measured —
   but not for every frame in the corpus, and the difference matters.** Reported
   by the owner after this milestone closed: a Breakthrough Photography X4 CPL
   67 mm (Schott B270, MRC16), in front of the 100 mm GM. An earlier broadcast
   stated it was in the path corpus-wide; **that universal quantifier was
   retracted** and resolved by EXIF capture date into `CPL ON` from 25 May
   (`bee-1`, `bee-2`, `bee-3`, `wrapped-text-1`, `wrapped-text-2`,
   `coffee-bubbles`, `foam`) and `CPL OFF` up to 17 May (`109MSDCF`, `112MSDCF`,
   `113MSDCF`, `119MSDCF`), with `coffee-bean` **UNKNOWN**.

   **M63's exposure to this is bounded and was checked, not assumed**
   (**MEASURED**, by enumerating `src/cells.py`): the measured cell set is
   `bee-1`, `bee-3`, `wrapped-text-1`, `wrapped-text-2`, and the replicate arm
   adds `bee-2`. **All five are on the ON side**, so the caveat applies uniformly
   to M63's real-data numbers rather than unevenly across them — which is a
   cleaner position than the corpus-wide claim would have given. `109MSDCF` is
   the only OFF-side stack this milestone ever registered and it was
   **substituted before any measurement** for unrelated reasons (§3, D-1), so no
   number here is hedged against a bare-lens stack and **there is no hedge to
   remove**. `coffee-bean`, `112MSDCF`, `113MSDCF`, `119MSDCF`, `foam` and
   `coffee-bubbles` appear in this report **only as stack-selection rationale**
   (§2.1) and carry no measurement, so **no headline of M63's inherits
   `coffee-bean`'s unknown filter state**.

   **Part II's headline is immune by construction.** P17–P21 — the instrument
   defect, which is this milestone's main result — are measured entirely on M25's
   rendered plant. There is no lens, no filter and no photon in that arm.

   What remains genuinely polarizer-conditioned is the real-data arm. A polarizer
   suppresses specular highlights, and speculars are among the highest-contrast
   features a scene offers, so they are exactly what drives the through-focus
   *range* that P17's denominator is built from. The direction is stateable and
   the magnitude is not (**ARGUED**): with speculars suppressed, the denominator
   inflation measured in §23.1 (`occ` 85.2 DN vs `ctl` 41.2 DN, **2.07×**) is
   more likely an **under**-estimate of what a bare lens would give than an
   over-estimate. That makes P17's defect worse on unpolarized data, not better,
   so no conclusion in this report is at risk — but the 2.07× should be quoted as
   *measured on CPL-ON stacks*, not as a corpus constant. Part I's contrast
   statistics (§8.7, §24) carry the same scoping.

   The noise-model denominator is **not** affected: it was validated empirically
   against observed scatter on these same frames (P10, 0.96 median ratio), so any
   light loss is already inside the measurement.

---

## 13. Proposed facts

Numbered `P1…P16` per AGENTS rule 28. **Absolute `§4` numbers belong to the
orchestrator at fold time.** Before folding, match the first ~70 characters of
each against the whole of `§4` and require zero matches (rule 28, rule 25);
several of these are close to M21's facts 150–152 in subject and must be checked
for content collision, not number collision.

**Part II's proposed facts continue this sequence as `P17…P24` in §25, and
several of them *contradict* facts 150–152, 568 and 603 rather than extending
them.** Fold the two tables together.

| # | Proposed fact | Label | Source |
| --- | --- | --- | --- |
| **P1** | At hand-labelled occluding edges in `bee-1`/`bee-3` (299 frames, ISO 100, marked f/5.6), 78.3% of band pixels (median of 9 cells, range 69.8–90.6%) carry a second through-focus peak clearing a per-cell noise floor calibrated to 1% FPR on a matched noise-only null. 9/9 occlusion cells exceed every no-discontinuity control cell; AUC 1.000, p = 2.0e-4 | MEASURED | `data/18-classes.txt` |
| **P2** | The same statistic fires at 78.9% (median, 5 cells) at silhouettes standing against a featureless white card, where no background texture exists to be veiled. AUC(occ vs occ_flat) = 0.600, p = 0.61. **Firing is not evidence of a veiled background** | MEASURED | `data/18-classes.txt` |
| **P3** | The second mode lands within 6 frames of the background's own focus frame — measured on an independent unoccluded pixel set — in 7.2% of occlusion band pixels; permuted cell↔reference pairing gives 1.6%. Above chance, and single-digit | MEASURED | `data/18-classes.txt` |
| **P4** | The bimodality flag does not reproduce across two independent 299-frame captures of the same scene (`bee-2` vs `bee-3`, NCC 0.9562). At matched flag rate Cohen's κ = +0.109 median, range −0.013 to +0.185 over 10 cells; among pixels flagged in both, `k2` agrees within 6 frames 8.5–16.5% of the time | MEASURED | `data/20-audit.txt` |
| **P5** | A single high-contrast edge at **one** depth generates a symmetric pair of secondary through-focus peaks. For a step of height ΔI blurred by σ_k, the gradient at fixed offset x is ΔI·G_{σ_k}(x), maximal at σ_k = x; with σ_k = rate·\|k − k_focus\| the lobe sits at \|k − k_focus\| = x/rate, so **its offset grows linearly with distance from the edge**. Halving the defocus rate multiplies the measured offset by 1.873 against a predicted 2.00 | DERIVED + MEASURED | §9.1, `data/15-sidelobe.txt` |
| **P6** | In a two-layer plant with a **known** second depth, the detected `k2` lands on the single-depth side-lobe 54–68% of the time and within 6 frames of the true background peak 0.0–1.0% of the time beyond ~8 px from the edge. Within ~4.5 px the true background peak is recovered 25.1–43.5% | MEASURED | `data/15-sidelobe.txt` |
| **P7** | Measured second-peak separation \|k2 − k1\| is not a property of the scene: it grows monotonically with the focus-operator box radius (21 → 68 frames as R goes 1 → 8 on one cell; 26 → 79 on a control cell whose depth step is 1 frame), and it floors at 4–6 frames as the stack is thinned to n ≤ 38 | MEASURED | `data/21-sweeps.txt`, `data/18-classes.txt` |
| **P8** | The "no frame in focus" diagnosis has no population in this corpus: the fraction of band pixels whose argmax is within 2 frames of either stack end is 0.00% median (max 1.09%) across all 25 cells, and posterior mass in the outer 5% of frames is exactly 0.0000 at median and p90 in every class at the calibrated noise temperature | MEASURED | `data/23-boundary.txt`, `data/18-classes.txt` |
| **P9** | Posterior entropy at the calibrated noise temperature predicts cross-capture focus-frame disagreement (\|Δk1\| > 10 frames) with AUC 0.564–0.792 (median ≈ 0.63), while the primary peak's **height alone** achieves 0.508–0.753 (median ≈ 0.62). Entropy adds ≈ 0.01 AUC over a number already computed | MEASURED | `data/19-entropy.txt` |
| **P10** | The injected `strehl-core` noise model predicts the observed frame-to-frame scatter of the box-Sobel focus response on **real** frames to within 4%: robust second-difference upper bound / MC-predicted σ_f = 0.96 median (range 0.87–1.01) over 25 cells spanning ISO 100–400 and σ_f 1.00–4.58 DN; 0.99 on flat null cubes | MEASURED | `data/22-sigmacheck.txt` |
| **P11** | The box mean of Sobel magnitude is **not** blind at R = 2. Across a monotone step blurred σ = 0→12, total variation is conserved to 6.8e-13 (fact 73 reproduced exactly) while the R = 2 box response at the edge falls 200.0 → 32.96 (ratio 0.165). Fact 73's blindness is a large-box property, which also explains fact 152's 0.36× depletion at the shipped R = 13 | MEASURED | `data/13-plant.txt` |
| **P12** | A bimodality threshold calibrated on a textured-background null is invalid on untextured background: applying a textured cell's `z*` to an untextured two-layer plant gives 16.8% "hits" at **zero** planted depth separation, against 16.2% at D = 60 | MEASURED | `data/13-plant.txt` |
| **P13** | On the occlusion class the measured separation is comparable in median to the independently measured depth step (sep/step 1.15, n = 8, range 0.61–2.11) but the two are not significantly correlated across cells: Spearman +0.579, p = 0.103 (n = 9); across all 25 cells +0.066, p = 0.755. One labelled occlusion cell with a **zero-frame** reference depth step has the corpus's highest hit rate, 85.3% | MEASURED | `data/21-sweeps.txt`, `data/23-boundary.txt` |
| **P14** | M21's frame-permutation placebo, run on M63's cells at M63's calibrated `z*`, fires at 100.0% (median, every class) against 78.3% on real occlusion data. A bimodality hit rate is therefore not interpretable as the fraction of pixels containing two depths | MEASURED | `data/21-sweeps.txt` |
| **P15** | The prominence of the second through-focus peak tracks **edge contrast**, not depth: Spearman(prom, band peak focus response) = +0.772, p = 6.1e-6 over 25 cells; prominence normalised by band contrast is 0.2145 at occlusion cells and 0.1849 at blank-card silhouettes — within 16% — against 0.1333 at no-discontinuity cells. Confirms P5's ΔI-proportionality on real data | MEASURED | `data/24-numden.txt` |
| **P16** | In M63's `z`, the numerator does the work and the denominator does not: median prominence is 37.79 / 28.54 / 11.04 DN across `occ` / `occ_flat` / `ctl` — a 3.4× spread — while the median predicted denominator is 3.012 / 2.881 / 2.268 DN. Median `z` at occlusion cells is 14.52 against a per-cell threshold of 5.48–5.92 | MEASURED | `data/24-numden.txt` |

---

## 14. Proposed disciplines

**D-a.** *When a statistic is proposed as a detector for a physical cause, build
the control in which the cause is physically impossible and everything else
matches.* `occ_flat` — a silhouette against a blank card — is a real occluding
edge with no background to veil. It cost one extra label class and it decided the
milestone. The cheapest possible refutation of "X detects Y" is a case with X's
geometry and none of Y.

**D-b.** *A defocusing high-contrast edge generates single-depth secondary
through-focus peaks whose offset grows linearly with distance from the edge.* Any
through-focus multi-peak statistic must be tested against this before its second
peak is attributed to a second depth. The law is `ΔI · G_σ(x)`, the offset is
`x/rate`, and on this rig the lobes reach 6× the in-focus response.

**D-c.** *Two independent captures of the same scene are the cheapest test of
whether a per-pixel statistic is a scene property.* Repeatability first, meaning
second. A statistic with κ ≈ 0.1 across two captures of a static subject cannot
be measuring the subject, and no amount of class-separation AUC repairs that.
This test cost one extra stack that was already in the corpus.

**D-d.** *Calibrate a detection threshold per cell on a matched null.* A threshold
calibrated on textured data is not valid on untextured data — measured at 16.8%
false hits (P12). Global thresholds across heterogeneous texture are a hidden free
parameter.

**D-e.** *Report a two-peak separation together with its dependence on `n` and on
the operator scale.* If it moves with either, it is not a scene measurement. Both
sweeps are cheap and both were decisive here.

**D-f.** *An externally validated denominator is not the same as an externally
sourced one.* Discipline 338 warns against a null-residual denominator. M63's
denominator came from the injected model, which is the right shape — but it was
worth quoting only after §4.3 showed it predicts the observed scatter on real
frames to 4%, using an estimator that shares no arithmetic with it. The
validation is a separate measurement and should be run whenever a model-predicted
σ is used as a denominator.

---

## 15. Open questions

1. **Does the near-edge regime survive on real textured-background occlusion?**
   The plant recovers the true background peak 25–44% within ~4.5 px (P6). M63 has
   n = 2 real cells with focusable background texture and one of them has a
   zero-frame depth step. **This is the single measurement that would most change
   the verdict.**
2. **Does a side-lobe-subtracted statistic find a residual second mode?** Fit
   `ΔI·G_σ(x)` from the same volume, remove the lobe pair, then re-run the
   prominence test. Not measured; it is a different instrument, not a retune.
3. **Is the flat `occ` distance slope (+0.053 fr/px, §8.8) a fixed second depth or
   a noisy regressor?** It is the strongest surviving point for the reviewer and
   M63 cannot resolve it. It needs cells with clean straight silhouettes.
4. **Capture request (for `docs/captures-needed.md`, which M63 may not write).**
   The corpus contains **no stack with a deliberate occluding edge in front of a
   textured background at a known depth separation.** Every occlusion in
   `bee-1`/`bee-3` is a limb against a white card. The measurement this question
   actually needs is: a foreground object with fine detail, a background with
   dense broadband texture, a measured rail step, and 200+ frames. Without it,
   *any* answer to the reviewer's question — mine or a future one's — is bounded by
   §12 item 1.

---

## 16. Reproduction

```powershell
$env:PYTHONIOENCODING = 'utf-8'
cd C:\dev\blog\death-of-software\projects\strehl\experiments\M60-bimodality
python src\00-selftest.py      # gate 0 — must print GATE 0 PASSED
python src\01-survey.py        # corpus survey (reads D:\personal\macro, read-only)
python src\02-drift-and-cache.py
python src\06-cell-overlays.py # labels -> fig/06-cell-*.png, data/06-cells.csv
python src\08-sheets.py        # 4-frame contact sheets at fixed indices
python src\09-curves.py        # ~310 s per 10 cells x 299 frames
python src\11-null.py          # per-cell noise-only nulls, ~165 s per bee stack
python src\12-analyse.py
python src\13-plant.py         # B1 blindness + two-layer plant
python src\15-sidelobe.py      # the side-lobe law
python src\16-distance.py
python src\17-repeat.py        # bee-2 replicate at bee-3's frozen pixels
python src\18-classes.py       # power first, then H1 / H3 / N5 / frame density
python src\19-entropy.py       # H4
python src\20-audit.py         # texture audit, replicate kappa, geometry
python src\21-sweeps.py        # MC convergence, N2, H2 Spearman, R sweep
python src\22-sigmacheck.py    # denominator validation
python src\23-boundary.py      # N5 as registered
python src\24-numden.py        # numerator vs denominator, contrast scaling
```

Every script carries an `if __name__ == "__main__":` guard. `M63_REPS` sets the
Monte-Carlo rep count (default 12; §4.4). All corpus reads are read-only; nothing
under `D:\personal\macro` was written. `cargo` is not required — no Rust was
built or changed.

**Artefacts.** `data/*.txt` are the verbatim console outputs quoted above;
`data/*.json` are the machine-readable forms. `data/curves/*.npz` and
`data/null/*.npz` are the extracted through-focus volumes (3.4 GB) and
`fig/*.png` are the figures — both are `.gitignore`d per the repository's rule
that generated heavy binaries never enter Git, and both are regenerated by the
scripts above. `fig/15-sidelobe.png` and `fig/14-plant-curves.png` show the
side-lobe directly and are worth regenerating before reading §9.

**Commit provenance.** The pre-registration (§2) was committed at `5dee1f4`
**before any hypothesis result** — that ordering is the point of this milestone
and it is checkable in the log. The remaining 47 files, including this report,
landed in commit `701dc11` rather than in one of M63's own: a concurrently
running agent ran a non-path-scoped commit in the window between M63 staging its
paths and committing them, and swept M63's files in alongside four M55 files.
Nothing was lost or altered — `src/25-verify-commit.py` reads the committed blob
back out of `701dc11` and asserts it is byte-identical to the final working-tree
report (71 294 characters, exit 0), per discipline 351. History was deliberately
**not** rewritten to unmix it, because another agent's work is in the same
commit.

**Sweep audit, run against this milestone's own commits (rule 42).** The
mechanism behind `701dc11` was later generalised: `git add -- <paths>` scopes
only the *staging*, so a subsequent bare `git commit` writes the whole shared
index and silently absorbs whatever a concurrent agent staged in the interim. A
`git diff --cached` audit does not protect against it, because nothing holds the
index still between the audit and the commit.

M63 was on the receiving end of that in `701dc11`, and was asked to check
whether it had ever been on the causing end. **It has not** (**MEASURED**). All
ten of this milestone's commits were audited with `git show --name-only`, which
reads what actually landed rather than what was staged:

| commit | files | foreign |
| --- | ---: | ---: |
| `5dee1f4` pre-registration | 14 | **0** |
| `789d214` Part I report | 2 | **0** |
| `b28b2e3` / `a2d8756` / `20f7e23` Part II registrations | 1 each | **0** |
| `d544bfa` Part II | 20 | **0** |
| `476421d` corpus rename | 3 | **0** |
| `d18fbd9` polarizer scoping | 2 | **0** |
| `9cb31f7` renumber to M63 | 3 | **0** |
| `9e022f5` S3 lint fix | 1 | **0** |

Every one used `git commit -F <msg> -- <explicit pathspec>`, which is the form
rule 42 now requires, so the index was never the thing being committed. One
commit, `9e022f5`, does touch a file this milestone does not own —
`docs/research/M60-prior-art-and-the-rival-explanations.md`, a whitespace-only
S3 repair on another agent's report. **That was requested and is disclosed in its
own commit message**, and it is deliberately a separate commit so its owner can
revert it without disturbing the renumber. It is not a sweep.

---

# PART II — the instrument

## 17. Why there is a Part II, and what reading the three named reports found

The brief was corrected mid-milestone. Three reports that the original commission
had not named were named: `M21-occlusion-bimodality-measured.md`,
`M32-posterior-confidence-measured.md`, and `M6-residual-halo-measured.md`. The
question was reframed from *measure the bimodality* to:

> **Is the occlusion halo in this corpus actually the two-layer veiling
> phenomenon the reviewer describes, or is it something else that has been called
> veiling?** M21's instrument returned the wrong sign. Either the instrument is
> broken, or the phenomenon is not there, and the corpus has eliminated the
> obvious explanation for the first without establishing the second.

Reading the three, in full, before designing anything, produced four findings
that changed the design. All four are **MEASURED** by reading committed sources,
not argued.

### 17.1 M21 used no plants at all

M21's §1 says "Three real stacks, no plants." **The plant in fact 568 is M25's,
not M21's** — `experiments/m25-simulator`. The corrected brief's instruction "do
not reuse M21's plant" therefore had no referent, and the instruction that
mattered instead was: *do not reuse the statistic*, because that **is** shared.

### 17.2 One function carries facts 150, 151, 152, 568 and 603

`multipeak()` is defined once, in
`experiments/m21-occlusion-bimodality/src/03-permutation-placebo.py`, and copied
**verbatim** into three M25 scripts — M25's own comment in
`src/17-multiscale-occluder.py` says "copied verbatim from its committed script."
Reproduced here exactly as it ships:

```python
def multipeak(V, thr=0.04):
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    mx = Vs.max(0); mn = Vs.min(0)
    rng = np.maximum(mx - mn, 1e-6)
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = ((Vs[1:-1] > Vs[:-2] + thr * rng) &
                  (Vs[1:-1] > Vs[2:]  + thr * rng))
    return ispk.sum(0) >= 2, (mx - mn) / np.maximum(mx, 1e-6), np.argmax(Vs, 0)
```

Three properties of it were never varied by any of the five facts that rest on
it, and each became a Part II hypothesis:

* **H-A.** The peak bar is `0.04 × (that pixel's own through-focus range)`. At an
  occluding boundary the range is set by the *foreground edge coming into focus*,
  which is the largest swing in the scene. **The bar is raised precisely where
  occlusion lives.** This is the shape discipline 338 warns about — a separation
  score whose denominator is itself driven by the condition under test.
* **H-B.** The test compares **immediate frame neighbours only**. Sensitivity
  therefore depends on focus step and frame density, so rates are not comparable
  across stacks of different depth.
* **H-C.** The population gate `c13 = (max − min)/max > 0.10` is also relative,
  so it selects on the same contrast H-A penalises.

### 17.3 M21 measured H-A's consequence and read it as reassurance

M21's §5 reports its statistic at **0.00×** when binned on intensity gradient
alone — "0.0% at the top decile of intensity gradient vs 9.2% in flat regions" —
and concludes "the effect cannot be an intensity-edge artifact in disguise."

An occluding edge **is** an intensity edge; that is fact 73's whole point, and it
is the premise of Part I. A statistic reading **exactly 0.0%** in the top decile
of intensity gradient is not thereby proven free of edge artifacts. It is
demonstrated **blind at edges** (**ARGUED**, from M21 §5; the underlying
blindness is **MEASURED** in §19–§20 below).

### 17.4 M25's oracle fixed the label, not the measurement

M25 did the right thing about *ground truth*: it gated populations on rendered
truth (`alpha_front`, `visible_focus`) instead of on inferred depth steps. That
satisfies discipline 358 on the quantity that **labels** the test. But the
quantity **under** test is still `multipeak`. So fact 568's conclusion —
"a perfect detector scores near zero here" — holds only if `multipeak` faithfully
reports bimodality, and that had never been checked.

Four published probes then attacked fact 568's wrong sign: defocus rate, luminance
step, gain, and multi-scale occluder geometry (facts 568, 603). **Every one of
them varied the plant. None varied the instrument.** That gap is Part II's entire
opportunity.

### 17.5 M6 is a name collision

`M6-residual-halo-measured.md` contains **zero** occurrences of "occlusion",
"veil", "bimodal" or "depth discontinuity" (**MEASURED**, `Select-String` over
the file). Its "halo" is the focus-breathing rectangle expansion — its §2.2 reads
"a halo is a rectangle expansion" — a gather-area and buffer-sizing quantity for
the warp stage. The word is shared; the phenomenon is not. **M6 has no bearing on
this question**, and this is recorded because the corrected brief named it as
directly adjacent and a future reader would otherwise chase it.

### 17.6 Why a second pass was warranted rather than a stop

The corrected brief offered an explicit stopping rule: if the question is settled,
say so and stop. It is not settled, and §17.2–§17.4 say why in one line: **the
corpus has tested the plant four times and the instrument zero times.** Open
question 138 asks for "a plant that passes fact 568's bar **or a different,
truth-bearing route entirely**." Swapping the statistic on frames that are held
byte-fixed is exactly that second route, and it is cheap.

---

## 18. Pre-registration B

**Frozen as `experiments/M60-bimodality/PREREGISTRATION-B.md` at commit
`b28b2e3`, before any Part II result existed.** Two addenda were registered later
and each was committed **before its own run**: §7b (T6) at `a2d8756`, §7c (T7) at
`20f7e23`. The ordering is checkable in the log and is the point.

### 18.1 Hypotheses

* **H-A** — the contrast-dependent bar suppresses detection where the curve range
  is large, i.e. at occluding boundaries.
* **H-B** — the neighbour-only test suppresses detection of peaks broader than
  one frame.
* **H-C** — the relative population gate co-selects with H-A.

### 18.2 The three statistics, all run on identical frames

| | definition | what it changes vs S0 |
| --- | --- | --- |
| **S0** | M21's `multipeak`, copied verbatim | — (the control) |
| **S1** | same function, bar replaced by `3σ` from the injected noise model | H-A only |
| **S2** | M63's Part I statistic: peak prominence over the interior dip, thresholded against the model-predicted σ of the focus response | H-A and H-B |

S1 is the minimal edit — one line — so that any difference between S0 and S1 is
attributable to the bar alone.

### 18.3 Registered decision rules

| outcome | rule |
| --- | --- |
| **INSTRUMENT** | S0 < 1.0 and max(S1, S2) ≥ 1.5, placebo in band |
| **PARTIAL** | S0 < 1.0 and 1.0 ≤ max(S1, S2) < 1.5 |
| **PHENOMENON** | all three < 1.0 |
| **H-A supported** | T2 denominator ratio ≥ 1.5 |
| any statistic **disqualified** | its permutation placebo outside 0.9–1.15 |

### 18.4 Power, asserted before reading any result

Registered floors: ≥ 500 px per class on M25 plants, ≥ 5 000 px on M63 cells. The
frozen plant delivers **veiled 10 133 px** and **smooth 994 940 px**
(**MEASURED**, `data/31-swap.txt`), so at a 10% base rate the standard error on
the veiled rate is 0.30 pp and a 1.5× enrichment is **≈ 12 sd**. Both floors
cleared by ≥ 20×. This is fact 779's discipline applied first, not last.

### 18.5 What Part II's discriminators cannot separate

* A statistic swap on **one** plant cannot separate "the instrument is blind" from
  "the instrument is blind *on plants of this construction*." T6 partly addresses
  this by re-running on a second geometry.
* The plant's veiling is rendered by M25's own compositor. **If that compositor's
  two-layer model is itself wrong, every Part II number inherits the error.** No
  measurement here can detect that; it would need real data with known depths,
  which §15 item 4 requests and the corpus does not contain.
* Enrichment ratios say nothing about *usable* detection. 1.23× is the right sign
  and a useless detector; §21 is where that matters.

---

## 19. T1, T2, T3 — swapping the statistic on frames held byte-fixed

**Method.** `src/30-render-m25-plant.py` re-renders M25's `discs` control from
M25's own simulator at M25's own configuration and **freezes the result** to
`data/30-m25-plant.npz` (41.6 MB) together with the rendered truth arrays. Every
statistic below reads those identical arrays. The reproduction is faithful: the
rendered feature size is **218.0 latent px**, and fact 603 records M25's control
as "218 latent-px discs" (**MEASURED**, `data/30-render.txt`).

### 19.1 T1 — the swap (`data/31-swap.txt`)

| statistic | veiled % | smooth % | **enrichment** | placebo | base rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| **S0** M21 verbatim | 1.97 | 10.61 | **0.19×** | 1.05 ✓ | 10.3% |
| **S1** noise-thresholded | 4.92 | 7.06 | 0.70× | **1.25 ✗** | 7.0% |
| **S2** prominence-over-noise | 43.10 | 35.66 | **1.21×** | 1.05 ✓ | 35.9% |

**S0 = 0.19× reproduces fact 603's single-scale control value exactly**, which is
the check that the reproduction is of M25's measurement and not of something
adjacent to it (**MEASURED**).

Per rule 39, S2's numerator and denominator separately: prominence **7.600 DN**
veiled vs **6.594 DN** smooth; denominator **2.477** vs **2.357 DN**. The
enrichment is carried by the numerator, and the denominator is nearly flat across
the two populations — which is precisely what S0's is not.

Registered verdict: **PARTIAL** (S0 < 1.0, and 1.0 ≤ max(S1, S2) < 1.5).

### 19.2 T2 — the mechanism, measured directly (`data/31-swap.txt`)

| | median curve range `rng` | S0's implied bar |
| --- | ---: | ---: |
| truth-gated **veiled** pixels | **108.412 DN** | 4.336 DN |
| **smooth** pixels | **27.503 DN** | 1.100 DN |
| ratio | **3.942×** | 3.942× |

For scale, S1's absolute noise-derived bar is **1.067 DN** — i.e. S0 demands
**4.06× more** than the noise floor justifies at veiled pixels, and almost exactly
the noise floor at smooth ones. The registered rule was "≥ 1.5 ⇒ H-A supported."
**H-A is supported at 3.94×** (**MEASURED**).

### 19.3 T3 — lowering the bar uniformly does not fix it (`data/31-swap.txt`)

| `thr` | veiled % | smooth % | enrichment |
| ---: | ---: | ---: | ---: |
| 0.040 (as shipped) | 1.97 | 10.61 | 0.19 |
| 0.020 | 6.91 | 27.16 | 0.25 |
| 0.010 | 13.79 | 43.52 | 0.32 |
| 0.005 | 22.05 | 55.29 | 0.40 |
| 0.002 | 31.30 | 64.28 | 0.49 |
| 0.000 | 43.53 | 71.39 | 0.61 |

The registered saturation guard (base rate > 90%) never fired; the highest base
rate reached is 70.4%. Enrichment climbs monotonically and **never crosses 1.0**.

**This is the sharpest single statement of the defect** (**MEASURED**): it is not
the *level* of S0's threshold that inverts the sign, it is the threshold's
**contrast-dependence**. Turning the bar down uniformly cannot repair a bar that
scales with the signal.

### 19.4 S1's disqualification is structural, and it matters (`data/32-swap2.txt`)

S1 failed its placebo at 1.25. `src/32-swap2.py` repaired the two candidate
implementation causes — per-frame σ, and a threshold that permutes together with
its frames — and the placebo still reads **1.26** at enrichment 0.82×.

The cause is structural (**DERIVED**, confirmed by the repair failing): frame
permutation preserves a curve's *range* but destroys its smoothness, manufacturing
large frame-to-frame jumps at exactly the high-swing pixels. A statistic with an
**absolute** bar counts those jumps; a statistic whose bar scales with range does
not. So M25's frame-permutation placebo — the corpus's validation gate for this
family — **structurally rejects the noise-calibrated fix that M21's own §7
prescribes.** S2 passes it (1.05–1.07) because prominence-over-dip is
permutation-robust in a way a neighbour-step test is not.

That is worth recording on its own: **a validation gate that only a
contrast-relative statistic can pass will keep selecting contrast-relative
statistics**, which is how a defect survives five facts and four probes.

---

## 20. The mechanism, decomposed (`data/35-mechanism.txt`)

T2 leaves an apparent contradiction. S0's bar at veiled pixels is 4.336 DN, and
S2 measures 7.600 DN of prominence there — *above* the bar. So why does S0 flag
only 1.97%?

`src/35-mechanism.py` measures both quantities on the same pixels, on the
`[1,2,1]`-smoothed cube that S0 itself operates on:

| population | prominence | S0's step | S0's bar | step/bar | prom/bar |
| --- | ---: | ---: | ---: | ---: | ---: |
| **veiled** | 3.042 DN | 0.331 DN | 4.336 DN | **0.076** | 0.702 |
| **smooth** | 2.803 DN | 0.355 DN | 1.100 DN | **0.323** | 2.548 |

Three things are measured here, and together they are the whole defect:

1. **The signal is the same in both populations.** 3.042 vs 2.803 DN of
   prominence. Whatever separates the two rates, it is not the amount of
   structure in the curve.
2. **The bar is 3.94× higher at veiled pixels**, which alone costs a factor of
   **3.63** in `prom/bar` — H-A.
3. **S0 does not test the prominence.** It tests the largest single-frame step
   into the peak, and at these peak widths (**5.08 frames of rise** at veiled,
   5.24 at smooth) the step is **9.2× smaller** than the prominence — H-B.

H-A and H-B **compound**: `step/bar` is 0.076 at veiled pixels, i.e. the test is
failed by more than 13× over.

### 20.1 The counterfactual that isolates H-B

Applying **S0's own `0.04 × range` bar** to the prominence instead of to the
single-frame step — changing nothing else, keeping the contrast-dependent
denominator intact:

**0.19× → 0.71×** (veiled 46.18%, smooth 64.89%) (**MEASURED**).

So the full decomposition of fact 568's wrong sign, all on identical frames:

| version | what is fixed | enrichment |
| --- | --- | ---: |
| S0 as shipped | nothing | **0.19×** |
| S0's bar on prominence | H-B only | **0.71×** |
| S2 prominence over noise | H-A + H-B | **1.23×** |
| fact 603's multi-scale geometry | **the plant**, not the instrument | 0.86× |

**DERIVED from the four rows:** repairing the instrument alone moves the
statistic across the sign boundary (0.19 → 1.23) without touching the plant,
while the corpus's largest-ever published improvement to this statistic — which
did touch the plant, four times — never crosses it.

---

## 21. T6 — fact 603 re-examined (`data/33-t6.txt`)

Fact 603 records that multi-scale occluder geometry moved the statistic from
0.19× to 0.86×, "the largest single effect ever measured on this statistic,
4.5×", and that this **eliminated** the leading explanation for fact 568's wrong
sign. T6 was registered (§7b, commit `a2d8756`) **before** the run and asks one
question: did the geometry add veiling, or did it lower the bar?

The test is to render both variants and score **S0, S2 and the T2 denominator
ratio on the identical frames**.

| variant | mean feature | **S0** (veiled/smooth) | **S2** (veiled/smooth) | T2 denom ratio | placebo S0/S2 |
| --- | ---: | ---: | ---: | ---: | --- |
| `discs` (M25 control) | 218.0 latent px | **0.19×** (1.97 / 10.61%) | 1.23× (40.73 / 33.07%) | **3.942×** | 1.07 / 1.07 ✓ |
| `discs-powerlaw` r⁻³, 2–160 px | 17.4 latent px | **0.86×** (5.99 / 6.98%) | 1.11× (46.85 / 42.17%) | **1.258×** | 0.99 / 1.01 ✓ |

Power on both: veiled 10 133 / 128 406 px, smooth 994 940 / 625 289 px.

* **S0 improves 4.62×** — 0.19 → 0.86 reproduces fact 603 **exactly**.
* **S2 improves 0.90×** — the veiling signal, measured with a statistic that can
  see it, did **not** rise. It fell slightly.
* **The denominator inflation collapses to 0.32× of its control value**, 3.942 →
  1.258.

Registered verdict: **DENOMINATOR RELIEF.** Smaller occluders make the
foreground's in-focus swing smaller at any given veiled pixel, which lowers
`0.04 × rng`, which lets S0 fire. **Fact 603's 4.5× is substantially an
instrument effect, not added veiling** (**MEASURED**).

This is the fact-738 trap avoided by construction: the quantity that improved
(S0) and the quantity that did not (S2) were computed on the **same frames**, so
the comparison cannot be explained by anything about the plant.

---

## 22. T7 — the mandatory positive control (`data/34-t7.txt`)

The corrected brief made the positive control mandatory and named the strongest
available outcome: *if the detector finds a synthetic two-layer composite while
real occluding edges show nothing, the phenomenon is absent from the corpus rather
than invisible to the tooling* — the distinction fact 568 could not make.

Sign enrichment is not enough for that. A statistic can be enriched at veiled
pixels for reasons unrelated to the background's focus frame — Part I §9's
side-lobe does exactly that. So T7 was registered (§7c, `20f7e23`) before its run
and asks **where the flagged second peak lands**, against the plant's *rendered*
truth: background focus index **16**, foreground **4**, 21 frames, window ±2.
Uniform chance is 5 of 19 interior indices = **26.3%**.

| statistic / population | n flagged | k2 within ±2 of bg | k1 within ±2 of fg |
| --- | ---: | ---: | ---: |
| **S2 veiled** (truth: has background) | 4 095 | **47.8%** | 11.1% |
| S2 smooth (truth: no background) | 329 157 | 30.0% | 20.6% |
| S2 veiled, frames permuted (null) | 10 041 | 29.4% | — |
| **S0 veiled** | **200** | too few to interpret | — |
| S0 smooth | 105 565 | 28.5% | 23.8% |

Registered bar: ≥ 2× chance **and** ≥ 2× the flagged-smooth rate. Measured
**1.82×** and **1.59×** → **INDETERMINATE**. It is not the side-lobe verdict
either, which required ≤ 34.2% or ≤ 1.15× smooth.

**The `k2` histogram is the more informative result** (**MEASURED**). Percentages
of flagged S2-veiled pixels by frame index, near the background index:

| index | 14 | 15 | **16 (bg)** | 17 | 18 | **19** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S2 veiled | 8.3 | 9.2 | **8.6** | 10.5 | 11.3 | **11.8** |

The mass rises monotonically toward the high indices and **peaks at the stack
boundary, not at the background index**. The detector knows which *half* of the
stack the background is in; it does not know which frame.

Two readings are consistent with this and Part II cannot separate them
(**stated, not resolved**): the plant's background is only 3 px defocused by
frame 19 at 1 px/frame, so a broad true peak and a truncated stack look alike
here. Distinguishing them needs a plant with the background placed mid-stack, and
that is registered as an open question rather than quietly resolved.

Two secondary facts from the same run:

* **S0 flags 200 of 10 133 veiled pixels.** That is the same 2% as T1, and it is
  why fact 568 could not have located this: **a 200-pixel population cannot
  support a localisation test.** M21/M25's instrument does not merely get the sign
  wrong, it destroys the sample.
* The `k1 in fg±2` column for the permuted null reads 67.4%. That is an artifact
  of a single shared permutation making `k1` near-deterministic and **is not
  interpretable**; only the 29.4% ≈ chance figure from that row is a meaningful
  null. Recorded because it is in the output file and would otherwise be misread.

---

## 23. T4 and T5 — real data, and the frame-density confound

### 23.1 T4 — the same three statistics on M63's real cells (`data/32-swap2.txt`)

| class | cells | S0 % | S1 % | S2 % | median `rng` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `occ` | 15 | 17.4 | 21.3 | 80.4 | 85.2 DN |
| `occ_flat` | 8 | **41.1** | 14.7 | 64.4 | 55.3 DN |
| `ctl` | 12 | 14.0 | 12.5 | 92.6 | 41.2 DN |

occ : ctl ratios — S0 **1.24×**, S1 **1.70×**, S2 **0.87×**.

The registered sign-inversion signature (S0 < 1.0 while S1 > 1.0) **does not
reproduce on real data**. Recorded as a negative result. The *denominator*
inflation does reproduce: median `rng` is 85.2 DN at `occ` vs 41.2 DN at `ctl` =
**2.07×** (**MEASURED**), about half the plant's 3.94× and in the same direction.

Two things follow. First, the real corpus is not a clean replication of the
plant's geometry, which is §18.5's stated limit. Second — and this is a Part I
result reinforced with **M21's own statistic** — `occ_flat`, silhouettes on a
blank card with **no background at all**, has the corpus's **highest S0 rate**.
Whatever S0 is enriched by on real data, it is not the presence of a background
to veil.

### 23.2 T5 — H-B confirmed on real stacks (`data/32-swap2.txt`)

S0's rate as the same `bee-3` cells are decimated, median over 10 cells:

| frames `n` | 299 | 150 | 75 | 38 | 23 |
| --- | ---: | ---: | ---: | ---: | ---: |
| S0 rate | 17.2% | 31.6% | 39.4% | 45.9% | **48.5%** |

**2.8× from thinning the stack alone** (**MEASURED**), monotone throughout, on
identical scene content. H-B confirmed.

This has a direct consequence for the existing record (**ARGUED**, from the
measurement): facts 150–151 compare `multipeak` rates across stacks, and those
stacks do not have equal frame counts or equal focus steps. Rates from this
statistic are **not comparable across stacks of different depth** without
normalising for `n`, and none of the published comparisons did.

---

## 24. What Part II changes in the record

Stated as directly as the evidence allows, with the corpus rows named. **M63 may
not write `SYNTHESIS.md`; these are proposals for the fold, not edits.**

| corpus row | what it says | what Part II measures |
| --- | --- | --- |
| **fact 568** | "The simulator does not contain the effect it was built to test" — enrichment 0.23×, wrong sign | **Falsified as stated.** On identical frames S2 reads 1.21–1.23×, the right sign. The plant contains the effect; the statistic could not see it |
| **fact 603** | multi-scale geometry 0.19 → 0.86, "largest single effect ever measured on this statistic, 4.5×"; eliminated the leading explanation | **Substantially denominator relief.** Same frames: S2 moves 1.23 → 1.11 (0.90×) while the denominator inflation falls 3.942 → 1.258. The geometry lowered the bar |
| **fact 152** | 0.36× depletion of the statistic at high intensity gradient, on real data | Same artifact, on real data: T4 measures the denominator 2.07× inflated at `occ`. Part I §8 additionally shows the shipped R = 13 box is the *other* half of it |
| **facts 150, 151** | `multipeak` rates compared across stacks | **Confounded by frame count.** T5 measures 2.8× from decimation alone on identical content |
| **question 137** | suspects the phenomenon may have been mis-identified | **Partially answered.** The instrument is defective in two measured ways; the phenomenon is also weak (1.11–1.23× in a plant built to contain it) and does not localise the background (T7) |
| **question 138** | needs "a plant that passes fact 568's bar **or a different, truth-bearing route entirely**" | **The second route is taken and it works.** Hold the frames byte-fixed and vary the statistic. No new plant was needed to falsify fact 568's headline |
| **discipline 338** | a separation score whose denominator is a null residual behaves like a random number | **A second instance found in production.** `0.04 × range` is a denominator driven by the condition under test. The generalisation in D-g below is the proposal |

**What Part II does *not* change.** Part I's corpus refutation stands, and Part II
strengthens rather than weakens it: a statistic that *can* see the plant's veiling
(S2) reads **0.87×** at real occlusion cells versus controls (§23.1) and 1.11–1.23×
on a plant built to contain veiling. The reviewer's premise does not survive
either pass.

---

## 25. Proposed facts — Part II

Numbered `P17…P26`, continuing Part I's sequence per AGENTS rule 28. These
**contradict** existing rows rather than extending them, so the fold must diff
them against facts 150, 151, 152, 568 and 603 by content and decide supersession
explicitly.

| # | Proposed fact | Label | Source |
| --- | --- | --- | --- |
| **P17** | M21's `multipeak`, the single function underlying facts 150–152, 568 and 603, thresholds peaks at `0.04 × the pixel's own through-focus range`. On M25's frozen `discs` control that denominator is **3.942×** larger at truth-gated veiled pixels (108.412 DN) than at smooth ones (27.503 DN), so the bar is 4.336 DN where occlusion lives against 1.100 DN elsewhere, versus a noise-justified 1.067 DN | MEASURED | `data/31-swap.txt` |
| **P18** | On frames held byte-fixed, swapping only the statistic moves the truth-gated veiling enrichment from **0.19×** (M21 verbatim) to **1.21–1.23×** (prominence over model-predicted noise), placebos 1.05–1.07 in both cases. **Fact 568's "the simulator does not contain the effect it was built to test" is falsified**: the plant contains it and the instrument could not see it | MEASURED | `data/31-swap.txt`, `data/33-t6.txt` |
| **P19** | Fact 603's 4.5× improvement is substantially denominator relief. Rendering both variants and scoring on identical frames: S0 0.19 → 0.86 (4.62×) while S2 1.23 → 1.11 (0.90×) and the veiled/smooth range ratio falls 3.942 → 1.258 (0.32×). Multi-scale geometry lowered the bar; it did not add veiling | MEASURED | `data/33-t6.txt` |
| **P20** | Lowering `multipeak`'s threshold uniformly cannot repair it: 0.040 → 0.000 raises enrichment monotonically 0.19 → 0.61 and never crosses 1.0 (base rate ≤ 70.4%, saturation guard never fired). It is the threshold's contrast-dependence, not its level, that inverts the sign | MEASURED | `data/31-swap.txt` |
| **P21** | `multipeak` tests the largest single-frame step into a peak, not the peak's prominence; at these peak widths (5.08 frames of rise) the step is **9.2×** smaller. Applying `multipeak`'s own `0.04 × range` bar to the prominence instead, changing nothing else, moves enrichment 0.19 → **0.71×**. The two defects compound: `step/bar` is 0.076 at veiled pixels vs 0.323 at smooth | MEASURED | `data/35-mechanism.txt` |
| **P22** | `multipeak`'s rate depends strongly on frame count. Decimating identical `bee-3` cells 299 → 23 frames raises the median rate **2.8×** (17.2% → 48.5%), monotone throughout. Rates from this statistic are not comparable across stacks of different depth without normalising for `n` | MEASURED | `data/32-swap2.txt` |
| **P23** | M25's frame-permutation placebo structurally rejects noise-calibrated peak tests: permutation preserves a curve's range while manufacturing large frame-to-frame jumps at high-swing pixels, so an absolute-bar statistic reads placebo 1.25–1.26 (repairing per-frame σ and permuting the threshold with its frames does not help), while prominence-over-dip reads 1.05–1.07. The corpus's validation gate for this family cannot admit the fix M21 §7 itself prescribes | MEASURED | `data/31-swap.txt`, `data/32-swap2.txt` |
| **P24** | In a plant whose background focus index is rendered-known at 16 of 21 frames, the flagged second peak lands within ±2 of it 47.8% of the time against 26.3% chance (1.82×) and 30.0% in the no-background population (1.59×) — below the pre-registered 2× bar on both. The `k2` histogram peaks at the **stack boundary** (11.8% at index 19) rather than at the background index (8.6% at 16). M21's statistic flags 200 of 10 133 veiled pixels here, too few to localise at all | MEASURED | `data/34-t7.txt` |
| **P25** | Of the two ISO-100/ISO-400 stack pairs in the corpus, only one is a matched scene. Normalised cross-correlation of the 8×-binned first frame gives `bee-2`↔`bee-3` **0.9562** but `wrapped-text-1`↔`wrapped-text-2` **0.3834**; `bee-1`↔`bee-3` is 0.6036 (same subject, different pose). The `wrapped-text` pair is a re-framing, not a re-capture, and is not usable as a matched-scene control | MEASURED | `data/03-previews.txt` |
| **P26** | M63's pre-rename corpus survey, written before the owner renamed five directories, agrees with the owner's independent post-rename EXIF read on all five stacks for both ISO and shutter (`bee-1` 299/100/0.5 s, `bee-2` 299/400/0.05 s, `bee-3` 299/100/0.2 s, `wrapped-text-1` 130/100/0.0667 s, `wrapped-text-2` 120/400/0.025 s). The rename mapping is confirmed by two independent reads | MEASURED | `data/01-survey.csv`, owner report 2026-08-23 |

---

## 26. Proposed disciplines — Part II

**D-g.** *A detection threshold that scales with a quantity the condition under
test also drives is a denominator defect, and it inverts signs rather than merely
adding noise.* Discipline 338 states this for a null-residual denominator; P17–P21
are a second, independent instance in production code, where the driven quantity
is the pixel's own dynamic range and the condition is an occluding edge. The test
is one line: hold the data fixed, replace the relative bar with an absolute one
sourced from the noise model, and compare. **Check any threshold of the form
`c × (max − min)` this way before trusting a null result from it.**

**D-h.** *When a plant fails to show an effect, vary the instrument before varying
the plant again.* Fact 568's wrong sign drew four published probes and all four
changed the plant. The instrument swap that falsified the headline took one
render and one function. **A negative result from a plant is a joint statement
about the plant and the measurement, and the measurement is usually the cheaper
half to test** — freeze the frames and swap the statistic, and any difference is
attributable to the instrument by construction.

**D-i.** *An oracle over the population is not an oracle over the measurement.*
M25 correctly gated its populations on rendered truth — satisfying discipline 358
for the quantity that **labels** the test — while the quantity **under** test
remained unvalidated. Both halves need a truth source. The cheap check is to ask
what the rendered truth would predict the measured quantity to be, and compare;
here it would have shown 200 flagged pixels where truth says 10 133.

**D-j.** *A statistic reading exactly zero on a confounder is a blindness result
until proven otherwise.* M21 §5 read 0.00× at the top decile of intensity
gradient as proof the effect "cannot be an intensity-edge artifact in disguise."
Exact zero on a large population is the signature of a statistic that **cannot
fire** in that regime, and the disambiguating measurement — does the statistic
detect a **planted** signal in the same regime? — is cheap and decisive.

**D-k.** *A permutation placebo is a property of the statistic's construction, not
a neutral gate.* Frame permutation preserves range and destroys smoothness, so it
is systematically harder for absolute-bar statistics than for relative-bar ones
(P23). A validation gate that only one family can pass will keep selecting that
family. **State what a placebo preserves and what it destroys, and check that the
candidate fix is admissible under it before adopting it as the gate.**

---

## 27. Open questions — Part II

5. **Does the plant's background peak actually sit where its truth says?** T7's
   `k2` mass peaks at the stack boundary, and at 1 px/frame the background is only
   3 px defocused at frame 19 — so a broad true peak and a truncated stack are not
   separable in this render. **Re-render with the background focus index near
   mid-stack and the stack extended past it.** This is one config change and it
   would turn T7's INDETERMINATE into a verdict.
6. **Do facts 150 and 151 survive frame-count normalisation?** P22 measures 2.8×
   from decimation alone. Re-running those comparisons at matched `n`, or with the
   statistic replaced by S2, is a small job with a large blast radius on the
   record.
7. **What does M32's posterior-over-depth read on these same frozen frames?**
   M63 read M32 for the entropy question (Part I §10 answers it independently and
   agrees the gain is ≈ 0.01 AUC), but did not run M32's object on the plant. If
   the posterior's bimodality is computed with prominence rather than a relative
   step, it may already be free of P17's defect — and that is worth knowing before
   anyone rebuilds it.
8. **Is there a third defect?** S2 reads only 1.11–1.23× on a plant *built* to
   contain veiling with a 12 px blur separation. That is the right sign and a
   useless detector. Whether the remaining gap is the plant's compositor, the
   focus operator, or genuine physics is **not** measured here and is the question
   that decides whether occlusion-aware merging is worth building at all.

---

## 28. Reproduction — Part II

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\dev\blog\death-of-software\projects\strehl\experiments\m25-simulator\src'
cd C:\dev\blog\death-of-software\projects\strehl\experiments\M60-bimodality
python src\30-render-m25-plant.py   # ~145 s; freezes M25's control to data/30-m25-plant.npz
python src\31-swap.py               # T1, T2, T3      -> data/31-swap.txt
python src\32-swap2.py              # S1 repair, T4, T5 -> data/32-swap2.txt
python src\33-t6-powerlaw.py        # T6, ~300 s      -> data/33-t6.txt
python src\34-t7-where.py           # T7              -> data/34-t7.txt
python src\35-mechanism.py          # the decomposition -> data/35-mechanism.txt
python src\36-verify-numbers.py     # read-back gate   -> data/36-verify.txt
```

`36-verify-numbers.py` is the discipline-351 gate for this report: it takes the
98 headline numbers quoted in Part II and asserts each one is present **both** in
the `data/*.txt` file cited for it **and** in this document. It currently reports
`ALL TOKENS PRESENT IN BOTH THE DATA FILE AND THE REPORT` (`data/36-verify.txt`).
Re-run it after any edit to Part II.

`31-swap.py` contains M21's `ff` and `multipeak` **copied verbatim**, so the S0
column is M21's function and not a re-implementation of it; `multipeak_abs` next
to it differs by one line. Nothing under `D:\personal\macro` was written, no Rust
was built or changed, and `experiments/m21-occlusion-bimodality` and
`experiments/m25-simulator` were read-only throughout.

`data/30-m25-plant.npz` (41.6 MB) is `.gitignore`d as generated heavy binary and
is regenerated by the first line above. Its faithfulness check is in
`data/30-render.txt`: mean feature **218.0 latent px** against fact 603's
"218 latent-px discs".

**Commit provenance, Part II.** `PREREGISTRATION-B.md` was committed at `b28b2e3`
before any Part II result; the T6 addendum (§7b) at `a2d8756` and the T7 addendum
(§7c) at `20f7e23`, each **before its own script was run**. Per discipline 351 no
exit code is quoted anywhere above as evidence — every number in Part II is read
back out of the named `data/*.txt` file.
