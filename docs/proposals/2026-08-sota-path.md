# strehl — the path to a defensible SOTA claim

**Status: PROPOSAL.** Every claim here is ARGUED unless it cites a measured report by
name. Numbers I derived myself are labelled DERIVED with the arithmetic shown; numbers
transcribed from the corpus carry the report that owns them. Per rule 12, nothing in
this document should be believed — it should be falsified, item by item, in the order
§9 proposes. Per fact 1886, every corpus absolute quoted here is a timestamp, not a
constant: re-measure at point of use.

**What was read before writing:** `README.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md`,
`AGENTS.md` (rules, rig, corpus index), `SYNTHESIS.md` (§1, §6, §7), the external-review
triage (`docs/proposals/2026-08-external-review.md`), and the following reports in full
or at verdict depth: M2, M5, M12, M20, M21, M22, M23, M27, M29, M30, M32, M33, M34,
M64, M65, M70, M75, M84b, M88, M90, M103, M110, M115, M118, M123, B §6–§8, F, G-edof
(M19), ORCH-veiling §59.3, captures-needed §29–§33, plus the shipping source for the
full-resolution gather (`align_cmd.rs:1160–2100`), the pyramid and estimator merges
(via ARCHITECTURE §5), and `SELECTION_INFLATION` (`merge.rs:136`).

**The commissioned question:** what to add, change, or do to make strehl a *truly*
SOTA focus stacker — novel territory explicitly allowed.

---

## 0. The one-paragraph answer

strehl already holds the axes it has measured — noise, clipping, invented structure,
speed, memory — and cannot yet *quote* the axis the field is judged on, fine detail,
because the corpus contains no target sharp enough to measure it (M88, captures-needed
§33) and the comparator refuses to save output (README, Zerene licence). The thesis
that wins those axes ships **diluted**: the estimation machinery lives on a backend
that is not the default, and the default still *selects* — measurably, on noise, in
flat regions, at every band (`pyramid.rs:1136–1147`), with a 24–240× selection premium
standing on essentially every mid-frequency coefficient of every subject (facts
1843–1845, 1849). Meanwhile the project's own research has already identified, and
never developed, the physical channels that no other stacker can reach — sub-pixel
diversity from focus breathing, longitudinal CA as three offset focus sweeps, the
two-layer occlusion model, metric depth from breathing (SYNTHESIS §6, B §6–§7, R21) —
because every one of them requires exactly what strehl uniquely has: RAW samples, a
calibrated noise model, and a fixed rig. The path to SOTA is therefore four moves:
**(A) make the thesis ship** — one merge, estimation in the band domain, confidence on
the default path; **(B) finish estimation** — runtime noise self-calibration, censored
(clipped) samples, photometric via the breathing law; **(C) exploit the physics** —
sample-level fusion that retires demosaic and resampling as separate lossy stages and
opens the only un-refuted route past the sharpest captured frame; **(D) build the
instrument that makes any of it quotable** — the pre-registered scorecard, the
certified-acuity map, the capture planner. Sequenced in §9.

---

## 1. What "SOTA" is allowed to mean here

README says, correctly: *"'State of the art' is not a defensible claim for this tool
today, and is not made anywhere in this document."* This proposal's terminal goal is
that that sentence becomes deletable. That requires deciding, in advance, what would
license deleting it — otherwise the claim will be minted by whichever statistic
happens to flatter the build of the day, which is the failure mode this corpus has
caught in itself at least seven times (README §Measured-against-other-stackers).

**SOTA = a pre-registered scorecard, versus named comparators, on axes with
commissioned instruments.** An instrument is admitted to the scorecard only after it
has (a) failed on a planted defect of the kind it polices, and (b) passed a null it
was not tuned on — the standard this project already applies internally (rules 9, 11;
the V-RIM acquittal is the template). Proposed axes, with today's honest state:

| Axis | Today | What blocks a claim |
| --- | --- | --- |
| Noise, flat/defocused ground | **Ahead, measured.** 4.5× vs the fork (≥2.4× worst-case grade-corrected); 0.746× vs one unstacked frame at gate 4.5 (README) | Nothing — quotable now |
| Highlight retention | **Ahead vs fork (32% clipped vs 4e-6), but the default path cannot see its own clipping** — clip census does not run there (README) | Wire the census; B2 below |
| Invented structure | **Ahead.** 0.0000% out-of-hull for every convex arm, held as a discipline (M115 §1) | Keep it an axis, so it cannot be quietly traded away |
| Occlusion halo / veil | Directional win, all 17 conditioned readings (fact 1871); halo demonstrated clean on 11 of 26, **4 blind + 7 unmeasurable**; veil mechanism measured, unfixed (ORCH-veiling §59.3) | ≥400 px clear-background captures (STATUS §4); A2 below |
| Fine detail ≥ 0.15 cyc/px | **UNDECIDABLE in either direction** (README); merge vs best frame: sharper below 0.20 cyc/px, softer above (V-SOFTCHECK-nyquist, one subject, no CI) | §30/§32/§33 captures; a licensed comparator; the D1 instrument |
| Per-pixel trust | **Absent from the field (VERIFIED, C) and absent from strehl's default path** — the refused-flags list | A4 below. This is the thesis, not a feature |
| Depth output | Absent from the field; unbuilt here (R20/R21 queued) | C5 below |
| Speed / memory | **Ahead, measured.** 22.58× enfuse; 2.4× the fork's best build; 0.2–0.39 s/frame; flat memory (STATUS §1) | Hold the line: quality features must fit ~2× current wall (D5) |

The scorecard needs three purchases/captures that no algorithm can substitute for:
a Zerene licence (the trial saves zero bytes — README), the slanted-edge chart and its
Lightroom-export half (§30/§32), and one subject with real contrast above 0.25 cyc/px
(§33). These are cheap against the months of instrument-building they unblock, and
**every fine-detail claim in this proposal is contingent on them.**

The end-state sentence the project should be able to print, each clause with its
licensing instrument in parentheses:

> On [subjects], strehl resolves detail at or beyond the best shipping comparator
> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly lower noise
> (existing flat-ROI instrument), with zero invented structure (hull census), no
> occlusion halo above [bar] (halo instrument at full reach), while emitting per-pixel
> certified acuity, n_eff, and depth in physical units that no comparator emits at all
> (D2/C5), in [X] s per frame on CPU (existing harness).

---

## 2. The research corpus: an audit

The owner asked directly whether the research is useful at all. Verdict: **it is the
project's principal asset, and it is what makes this proposal writable.** Three ways,
then four hazards, then the residue it left unexploited.

### 2.1 What it is worth

**(a) The graveyard.** The obvious ideas an outside proposer would reach for first are
already measured dead, with mechanisms: multi-frame Wiener across the focus axis
(M20: wins 15.1% of pixels; M70: the band matrix is rank-1 to 0.9959, so matched
filtering over near-scaled copies *is* weighted averaging; M115: R_SNR 1.0014,
CI [0.965, 1.038], with 29.5–36.4% of deconvolved pixels outside the convex hull of
their own sources — three instruments, one answer); OTF self-calibration from the
through-focus curve (M115, separately); outlier rejection (four independent refusals;
M123 fired on 29.55% of a *stationary* subject); entropy-scalar confidence (M32:
blind, non-monotone, degenerate — the posterior is a delta at 142–991σ); shrinkage
calibration for alignment (M12: transfers 0 of 18, worst case 83.4× worse);
metacalibrated edges (M23: the measured "response" was the probe's own bilinear
resampler). Without this record, the present proposal would be longer and mostly
wrong. §8 lists what is therefore *not* proposed.

**(b) The measured constants that make the physics exploits designable.** Magnification
m = 2.7198 ± 0.0051 (M84b); bellows factor B ≤ 3.064 at f/11 with a genuine spectral
knee at 0.2762 cyc/px (M5); pupil factor p ∈ [1.31, 1.94] putting the f/5.6
diffraction cutoff at **106–135 cy/mm, above the 97.66 cy/mm sensor Nyquist** (M88);
the rig measured **~2.2× softer than diffraction alone explains**, two instruments
within 4% (captures-needed §29) — which means both that aliasing physically exists to
recover and that a real, optics-shaped blur budget exists that only reconstruction can
touch; the noise model g/read/κ with an independent PTC cross-check (M71, M90);
FOCUS_NOISE_SD and the 10.27× operator span (plugin seam); breathing = −1.012% scale
across 33 frames, linear, scale centre ~400 px off image centre (F §6–§7), up to
299 plane px corner drift at N=299 (ARCHITECTURE §7); the sub-frame peak cost
distribution (M33: 48.7% of pixels miss peak; median 4.64%, p99 17.34% of response);
and the selection premium itself, 24–240× (facts 1843–1845, 1849).

**(c) The instrument discipline.** Pre-registration, planted defects, placebo arms,
the author-never-verifies rule, "a statistic that has only ever been shown to succeed
is not evidence." A SOTA claim is exactly the kind of statement that dies without
this, and the project already knows how to build claims that survive attack. G-edof
additionally hands the project the one ground-truth-free sharpness metric that cannot
be fooled upward by noise amplification (FRC — R25(iv)), which D1 should adopt as its
spine.

### 2.2 The hazards

1. **A large share of quality results measure the estimator backend, which no longer
   ships.** The gate table, the n_eff calibration ladder, the veil estimator, the
   edge-aware machinery, photometric — all estimator-path. The pyramid default beats
   the estimator on acuity, microcontrast and aura (README), so the *conclusions*
   mostly transfer in strehl's favour, but the *numbers* do not, and README documents
   two headline retractions caused by exactly this transfer.
2. **Absolutes are timestamps** (fact 1886: a coefficient-independent arm re-rendered
   across builds differed on 33M px). Everything quantitative in this proposal must be
   re-derived inside the lane that consumes it, from one pinned build.
3. **Instrument churn ate the project's middle.** Three detail statistics, two rim
   instruments, one timing harness and one deconvolution channel failed their own
   commissioning. The cure is D1: build the instruments *once, first,* against the
   captures that give them something to grip.
4. **Several load-bearing questions are blocked on captures, not analysis** — and have
   been for weeks: §30/§32/§33, the aperture ladder (§29), the TC-off bracket (§17),
   darks at working exposure (§6). The cheapest schedule acceleration available to
   the owner is one capture session (§9, phase 0).

### 2.3 The unexploited residue — the corpus's own novelty list

SYNTHESIS §6 records four verified-absent-from-literature bets, and B §6–§7 sketch two
of them at hypothesis level. **None has been developed.** They are this proposal's
workstream C: super-resolution from focus-breathing sub-pixel diversity (B §6: four
arXiv queries, zero results; "could not confirm any published work"); per-channel
focus stacking exploiting longitudinal CA (B §7.2: no prior work found; Trouvé 2013
and Chang & Wetzstein verify the physical signal exists); diffraction+defocus PSF
modelling at macro magnification; depth-from-breathing as a metric ruler (R21,
"QUEUED — attractive"); and the two-layer occlusion model, where the defensible claim
is "first *shipping* tool" (Asada 1995 precedent, M19).

---

## 3. Strategy

Four workstreams. A and B make the thesis true of the product a user runs. C is the
novel territory — the physics only strehl can reach. D is the instrument and the
product surface that turn all of it into claims and into an instrument someone can
hold. Nothing in C is load-bearing for A/B/D; the plan degrades gracefully if any bet
dies, and each item below carries its own kill bar so it can die cheaply.

A one-line version of each:

- **A — One merge.** Estimation moves into the band domain; the backend fork retires;
  confidence ships by default.
- **B — Estimation finished.** The noise model measures itself per stack; clipped
  samples become inequalities instead of lies; photometric gain follows the breathing
  law it measurably obeys.
- **C — The physics exploits.** The merge consumes photosites, not resampled planes —
  which unifies demosaic, warp, merge and super-resolution into one estimator; colour
  becomes three offset focus sweeps; occlusion becomes a two-layer estimate; depth
  becomes an output in micrometres.
- **D — The instrument.** The scorecard, the certified-acuity map, the capture
  planner, the performance budget that keeps all of the above shippable.

---

## 4. Workstream A — one merge: the thesis ships

### A1. The banded admission merge

**The defect, measured.** The default pyramid is a per-coefficient *selector* above
its noise floor: the exponent ladder runs 7.68/8.0/8.0 in the three finest bands
("a frame with twice another's band energy gets 256 times the weight",
`pyramid.rs:1241`), bands 1–6 average essentially nothing (0.29/0.08/0.06/0.03/0.00/
0.00% — STATUS §2), the 24–240× selection premium stands on those coefficients, and
selection concentration is measured *higher in flat regions than in detail regions at
every band* — "a merge selecting on noise" in the module's own words
(`pyramid.rs:1136–1147`). The built significance fix ships off because at derived
strength it does not collapse the inversion (ARCHITECTURE §1).

**The design.** Keep the Laplacian frame — M120 proved the estimator's polygonal
patchwork is a property of the per-pixel winner field, and the pyramid's spatial
coherence is why it won the A/B; do not re-litigate that. Inside each band, replace
soft-power ratio weighting with the estimator's own admission logic, per coefficient:
elect the winner by smoothed band energy exactly as today; **admit every frame whose
smoothed energy lies within k·σ_band of the winner** (σ from the injected model times
the per-frame measured floor that already ships); **average the admitted coefficients
with inverse-variance weights**; below the floor, fall back to the plain mean as
today. Report per-band n_eff as a first-class statistic.

Two corpus facts make this a re-calibration rather than a rewrite. The shipped
soft-power weight *is already* an exponential soft kernel over log-SNR deficit at
temperature 1/p (facts 1933–1940) — so the change is from an uncalibrated temperature
schedule to a calibrated admission width. And a 242-line starting patch exists,
withheld deliberately: `experiments/BUILD-SOFTGATE/pyramid-softgate.patch` (applies to
`ec96973d`). The soft-gate lane's own findings are binding here: **match kernels on
effective width (n_eff), never on the threshold parameter** (facts 1917–1920 — the
same T admits n_eff 4.674 hard vs 19.295 Gaussian), and note the Gaussian kernel is
not one-pass streamable (a cross term forced a second decode pass, 56.3 → 124.7 s at
N=79). An admission-by-margin rule needs the winner before weighting, so the unified
merge is likely **two-pass over frames**; the estimator's two-pass structure and its
O(1)-per-pixel sufficient statistics are the template (ARCHITECTURE §5b), and the
~2.2× wall cost is priced in D5.

**Why this is the highest-value quality item in the tree.** It attacks, with one
mechanism, the flat-region noise election (the largest measured divergence between
what ships and what the thesis promises), the gate-2.0-vs-4.5 dilemma (the FoM table
in README shows the shipped default discarding detail and noise in equal proportion —
1.06 at 0.40–0.50 cyc/px — which is what an indiscriminate blur does; a calibrated
admission width replaces both magic numbers), and fact 341 (B4 below).

**Acceptance / kill bars.** Pre-registered before build: (i) the flat-vs-detail
concentration inversion collapses at every band on `coffee-bubbles`; (ii) detail-kept
at 0.10–0.30 cyc/px on the §33 subject within [bar]% of the gate-4.5 arm while
noise-kept improves; (iii) no regression on the four conditioned aura subjects and the
`coffee-bean` hull-clamp test; (iv) per-band n_eff maps show ≥[bar]× the averaged
fraction in bands 1–3 on flat ground with detail regions unmoved. Kill: if (ii) fails
after width calibration, the admission form is wrong for band statistics and the
result publishes as a negative with the sweep attached.

### A2. The depth-aware base band — the veil fix

**The defect, measured, with its mechanism confirmed in source.** The base band is a
plain unweighted mean across all frames (`pyramid.rs:895`, `608–612`); at an occluded
pixel ~290 of 299 frames show the defocused bright foreground, so the correct detail
is added to the wrong pedestal — claw base 0.581, foreground 0.892, master 0.802, with
detail correlation 0.852 to the right frame (ORCH-veiling §59.3). The alternative arm
(`WeightedFromCoarsest`) was measured and correctly rejected for flat-field wander.

**The design resolves that dilemma with the gate instead of a global choice:** base
coefficients use the admitted-set mean (A1's admission at the coarsest band) *ramped
by election coherence* — coherent regions (a real object; `election_coherence.rs`
exists, estimator-only today) take the admitted base; incoherent flat ground keeps the
plain mean that is optimal there. Quantile-anchored thresholds, ramped not switched,
per the edgeaware lessons.

**Acceptance:** the §59.3 probe re-run — master base moves from 0.802 toward 0.581
with the null window unmoved; `chia-seeds-cpl` crevice milkiness (STATUS §4) and the
0.708% rms far-field mottling (README) re-scored; flat-field wander bounded at the
level that killed `WeightedFromCoarsest`.

### A3. Edge-aware support and the estimator's other organs, ported or retired

`edgeaware.rs`, the veil estimator, election coherence and through-focus statistics
are ESTIMATOR-ONLY today (ARCHITECTURE §10). After A1/A2, measure which still earn a
place: the pyramid's seven bands already answer the occlusion halo differently, and
the halo is gone on this path (README) — so the null hypothesis is that most of
edgeaware is not needed in the band domain. Whatever survives, the fork retires: one
merge, the argmax baseline kept as the negative control, the estimator kept as a
reference arm the way `stack.rs` is today. The ten-vs-seven refused-flags split
(ARCHITECTURE §5) collapses with it.

### A4. Confidence on the default path

The README names this the single largest gap between what the project is for and what
it does. M34 fixed the shape: **a vector, never a scalar** — the three channels flag
near-disjoint pixel sets (union 14.278% vs a 15.0% disjoint ceiling) and predicted σ
is *anti*-correlated with the sub-frame deficit in the worst tail. Ship, per pixel, on
the default path: per-band n_eff (A1 makes it exist), admission width, sub-frame peak
deficit via the **log-domain parabola with baseline subtraction** (M33 — the naive
parabola's peak-height estimate is anti-correlated with the truth), and hull-clamp
distance. D2 turns this vector into the certified-acuity product.

---

## 5. Workstream B — estimation finished

### B1. Runtime noise self-calibration — rule 3's unimplemented half

**The gap, in the project's own words:** "there is no runtime noise estimator, so
nothing cross-checks a profiled body against what its own frames actually show"
(ARCHITECTURE §3). And exactly one body is profiled; every other camera degrades to
`Provenance::Fallback`.

**The design.** The stack itself is a photon-transfer instrument. Adjacent frames in
a bracket differ by a sub-pixel warp (0.07–0.22 green px adjacent — M29), a fitted
photometric gain, and noise. Per stack: take adjacent-frame pairs, remove the fitted
gain ratio, high-pass, and in low-gradient tiles regress the robust variance of the
difference against mean signal — a temporal PTC at the working exposure, ISO and
aperture, by construction blind to fixed pattern (the M90 method, §2.1, applied
in-stack). Cross-check with the G1−G2 split within single frames (the two green
phases sample the scene a half-quad apart; their high-passed difference in smooth
regions is an independent σ probe), and against the per-frame measured band floors
`gatefloor.rs` already computes. Output: measured g, read floor, and a κ
consistency check against the profile; on an unknown body this *is* the model —
`Provenance::Measured` — which retires the one-profiled-camera limitation as a
portability blocker.

Ship with M90's two-piece rule: the κ term into `predicted_sigma` is free (zero
selection decisions moved); any gain correction touches n_eff (0.38–14.72%) and lands
behind its own freeze. Warp residual is the confound to commission against: the
planted control is a pair of synthetically re-gained, re-warped copies of one frame,
which must return the model σ within [bar]%.

**Acceptance:** recovers M90's independent g within its CI on the reference body,
per-stack, from subject frames alone; disagreement with the profile beyond [bar]
prints in the banner and widens the gates — never silently.

### B2. The censored-sample merge — clipped values are inequalities

**The physics.** Defocus conserves flux (measured — the photometric work leans on it),
so a specular highlight that pins the sensor in its in-focus frames is spread below
clip in defocused frames. The census machinery already sees this: only **21.02% of
ever-pinned sensels are pinned in every frame** (ARCHITECTURE §6) — for the other
79%, the stack itself contains unclipped measurements of the same scene point. Today
those pixels' merges either ingest the pinned lie or roll it off cosmetically, and the
measured consequence is the foam defect class: green pins first (ceiling 38921 vs
blue 52239 in the rendered master), B/G climbs monotonically across all nine level
deciles, and every blown specular on any subject inherits a one-sided colour rim
(README).

**The design.** In the admission merge, a sample at the container maximum enters the
per-pixel estimate as a **censored observation** — a lower-bound likelihood term, not
a value. The per-pixel MLE under Gaussian noise with censoring is a few Newton steps
over a handful of samples, run only on the ever-pinned set (a few percent of pixels;
zero cost and **byte-identical output elsewhere, asserted by hash** in the A-series
freeze style). Where all admitted samples are censored, fall back to today's roll-off
and say so in the confidence vector ("censored" is a fourth channel). This uses
defocused frames *legally* — no deconvolution, no invented values above measured
flux — and it is the estimator thesis extended to the one sample class the thesis
currently ignores. It also composes with, not against, M30's finding that highlight
rescue by exposure needs −2 EV: that is the capture-side complement, and the planner
(D3) owns it.

**Novelty note (ARGUED):** I know of no stacker or burst-merge pipeline that treats
clipped RAW samples as censored data in a per-pixel estimator; B §3/§8 record nothing
of the kind. Worth the same arXiv-negative-search treatment SYNTHESIS §6 items got.

**Acceptance:** on `foam`, the B/G-vs-level monotone climb flattens toward the
optical expectation with the flat-region placebo unmoved; the §25 deliberately-clipped
capture gives the controlled version. Kill: any change off the ever-pinned set, or any
reconstructed value exceeding the flux bound of its own defocused evidence.

### B3. Photometric normalisation via the law it measurably obeys

The flux ramp is mostly not drift — it is magnification: `ln flux = −2 ln scale`,
no free parameter, RMS down up to 5.06×, permutation p = 0.0025 (README). So the
default correction on the unified merge is **deterministic**, from the alignment
scale the merge already holds, with a *fitted* residual gain only where it clears a
bar — `foam`'s genuine 0.32 stops / 8 frames is the one corpus subject that needs it.
The estimator's measured rule carries over: the gain drags the noise model with it
(σ scales by c, not √c). This removes the "NOT YET IMPLEMENTED on this backend"
refusal without importing the estimator's two-pass photometric machinery wholesale.

### B4. `SELECTION_INFLATION` dissolved structurally

Fact 341 is open because the penalty term for degenerating to selection was refuted
at 1.074×. The admission merge makes the question nearly moot before it answers it:
under a soft/admission kernel the n_eff ≤ 1 population collapses 3.936% → 0.023%
(facts 1917–1920). Land A1, then measure the residual term on the pixels that remain
selectors; if it is second-order there, close 341 by measurement rather than by
constant.

---

## 6. Workstream C — the physics exploits

These are the SOTA-differentiating bets. Each begins with a corpus-only or
single-capture measurement that can kill it cheaply. C1 is the flagship.

### C1. Sample-level fusion — the merge consumes photosites

**The claim (ARGUED):** the single largest un-refuted quality lever in this project is
to stop feeding the merge *resampled estimates* and start feeding it *the sensor's
actual samples*, each carrying its exact warped position, channel and σ — one
estimator that subsumes demosaic, warp resampling, merge, and (at a finer output
lattice) super-resolution. This is the logical completion of the project's two oldest
commitments: estimation-not-selection, and gather-at-consumption.

**Why the current path leaves information on the table, from the tree's own
measurements:**

- The shipping fold now runs a **full Malvar demosaic of every frame inside the warp**
  (`warp_frame_in_place_fullres`, on by default): 299 demosaics per stack, 503 MiB of
  transient per warp, and — the material part — **interpolated values enter the
  election and the merge**. It ships because the alternative was worse: the per-plane
  gather band-limits every phase to 0.25 cyc/output px *before* election, "so no later
  stage can recover it" (`align_cmd.rs:1160–1215`), and flipping it moved band
  correlation at 0.25 cyc/px from 0.1514 to 0.9329. Both arms concede the same
  premise: reconstruction quality is being decided per-frame, blind, before the
  estimator sees anything.
- The gather kernel destroys most sub-pixel displacement — planted motion reads gain
  0.29 against 0.98 interpolator-free (ARCHITECTURE §7) — and its MTF costs 18.6% of
  the merge's blur variance (restore.rs rationale). A kernel-regression merge has no
  second resampling to lose it in.
- The optics out-transmit the sampling. At f/5.6 the diffraction cutoff is 106–135
  cy/mm against 97.66 sensor Nyquist (M88), and each CFA phase plane samples at a
  quarter of that reach. R and B at quarter density are the measured fringing victims.
  Aliasing is physically present; only sample diversity can unfold it.
- B §6.5 already mandated the interface: *"`Merger` must accept an arbitrary output
  lattice and must sample source frames through the `WarpField` rather than from
  pre-warped buffers. Any plugin that bakes warps is permanently excluded from SR."*
  The corpus wrote the specification and then shipped the opposite for expediency.

**The design.** Per output pixel on an arbitrary lattice (1× default, 2× SR mode):
gather every source photosite of the wanted channel within a small radius of its
inverse-warped position — real `u16` samples, black-subtracted, WB-gained, never
interpolated — and estimate:

```
value(p, c) = Σ_i  a_i · K(Δx_i; Σ_local) · v_i / σ_i²   /   Σ_i  a_i · K · 1/σ_i²
```

where `a_i` is the admission weight from the focus gate (A1's machinery, evaluated at
the band scale of the lattice), `K` an anisotropic kernel steered by the local
structure tensor (the Wronski construction — VERIFIED in B §8 to beat SOTA demosaicers
by >3 dB *and* beat merge-then-demosaic), and `σ_i` the injected model per sample.
Green arrives quincunx (2× diagonal density per frame); R/B arrive at quarter density
and are completed across frames. Where sample count or phase diversity is poor the
kernel widens and the estimator degenerates to exactly today's behaviour — degradation
is continuous and *reportable per pixel* (`phase_coverage` and
`sr_contributing_frames` as honest outputs, per B §6.5).

**Feasibility, DERIVED from corpus numbers.** Adjacent-frame breathing step ≈ 1.012% /
32 ≈ 0.032% (F §6, one stack; deep stacks larger). Sensor-grid corner radius ≈
√(3516² + 2344²)·2 ≈ 4226 px, scale centre ~400 px off-centre (F §7). Per-adjacent-
frame shift at radius r is r·3.2e-4: ≈1.35 px at the corner, 0.32 px at r = 1000,
0.10 px at r = 300. Frames within depth of field at the recommended step: k ≈ 1.3–1.5
(SYNTHESIS §1.1b), but the corpus shoots 2–4× denser (M27) and the seven new stacks
at step 1/5/7 denser still — call it 3–6 sharp frames per site. So the within-DOF
phase sweep is ≈1.6 px at r = 1000 with five sharp frames (good diversity), ≈0.5 px
at r = 300 (marginal), and a **central dead zone** below r ≈ 150–300 px where
breathing alone contributes nothing — B §6.3 predicted exactly this. Two additional
diversity sources close it: the measured track jitter (median second-difference
0.48 px, 13.8% of adjacent pairs ≥ 1 px — M110; if it is real rig motion it is free
dither everywhere), and — a deliberately requested capture — **one bracket with IBIS
left ON on the tripod**, which turns the stabiliser's slow wander into designed
sub-pixel dither. That request costs the owner one bracket and would be, to my
knowledge (ARGUED), the first deliberate use of a stabiliser as a super-resolution
dither source in stacking.

**The registration wall, named.** 2× reconstruction needs *relative* registration of
the contributing samples good to ~0.1–0.15 px. The global similarity's held-out corner
error spans 0.353–11.562 px across stacks — but that is the end-to-end gauge; the
merge consumes per-frame placement (M103), and SR consumes something smaller still:
**relative placement among the 3–6 within-DOF frames**, which are content-matched
(the correlation problem alignment finds hard — cross-focus appearance change — is
absent between them). That is the easiest sub-problem in the whole alignment space,
and C4's local refinement owns it. Where the per-window registration confidence fails
its bar, that pixel's lattice contribution degrades to 1× — refusal per pixel, in the
house style.

**What it buys at 1× before any SR claim:** no invented values in the election or the
merge (the Malvar-inside-the-warp transient and its 503 MiB go away — memory goes
*down*), one reconstruction instead of 299, no second resampling loss, and the
interpolation kernel dispute (M118/M113/ORCH-kernel-decision) dissolves — there is no
resampling kernel, only a reconstruction kernel whose bandwidth the estimator chooses
locally.

**What it buys at 2×:** alias-unfolded R/B at full resolution (the honest,
physics-backed form of "beyond the demosaic"), and genuine super-Nyquist recovery in
the mid-to-outer field at f/5.6 where M88 says the optics deliver it. This is the
only route to "resolve beyond the sharpest captured frame *as rendered*" that no
corpus refutation touches: M115 killed reweighting *within* a band across focus;
sample fusion recovers *sampling* diversity within the sharp set, which is orthogonal.
State the boundary honestly: it cannot exceed the optical cutoff, and at f/11 (cutoff
0.2762 cyc/px, M5) the 2× lattice buys only alias margin, not new signal.

**Acceptance / kill bars (pre-registered against D1's instruments):** FRC gain over
the current default on the §33 subject and the §30 chart; demosaic-artifact
disappearance on a zone-plate/fine-check target (false-colour moiré must *decrease* —
a signature interpolation cannot fake); the M115 split-half SNR instrument re-run on
the sample-fusion arm (R_SNR must exceed 1 where phase coverage is reported high, and
must not fall below 1 anywhere); hull discipline per contributing sample set; noise at
matched band ≤ current default. Kill: if within-DOF relative registration cannot reach
[bar] px on real stacks (measured first, cheaply, from existing warpmaps + one local
refinement prototype — phase-coverage census is a corpus-only computation requiring
zero new captures).

### C2. Chromatic z-diversity — the bracket is three focus sweeps

Longitudinal CA offsets the R/G/B focus planes, so one bracket carries three
z-offset sweeps of the scene (B §7.4; physical signal VERIFIED via Trouvé 2013,
Chang & Wetzstein; no per-channel focus-stack prior work found, §7.2). The default
merge shares green's election across all four planes (ARCHITECTURE §5a) — so today,
R and B are gathered from frames green chose, and any longitudinal CA renders R/B
*systematically slightly defocused* plus fringed at defocused edges.

**Step 1 is a corpus-only measurement, and it is decisive either way:** per-channel
through-focus peak offsets δ_R, δ_B in frame-index units, at several field radii, on
two or three subjects, using M33's log-domain parabola (which resolves sub-step
offsets). The lens is a modern apo-corrected macro behind a 2× TC — B §7.4's own
caveat says the offset may be sub-step, and the TC may equally magnify it.

**If δ clears the bar:** per-channel election offset (elect on green exactly as
today; gather R/B at index + δ(field)) — a one-line change in gather indexing worth
whatever the measurement says; defringing becomes a lookup instead of an inference;
and the three per-channel peaks are three quasi-independent depth estimates feeding
C5 (spread = per-pixel LCA measurement, a capability no stacker has). **If it does
not:** close it as a measured null the way M17 closed the dual-response — the corpus
gains the number either way.

### C3. Two-layer occlusion estimation — the veil's principled completion

A2 fixes the *pedestal*; the boundary itself still mixes two surfaces. The corpus has
every ingredient for the real model: bimodality enrichment 4.38× at r = 2, gated on
the calibrated noise floor (M21); the veil's convex-combination direction and the
pmax bound (ARCHITECTURE §5b — the shipped veil estimator is the degenerate one-sided
case of a two-layer fit); election coherence for eligibility; the M25 twin for ground
truth (its pre-registered gates already include a physically-veiled two-layer scene);
and now the first clean occlusion subjects — `duck-tape-side-layers-cpl` (thin dark
fibres over textured ground, STATUS §4) and `chia-seeds-cpl`'s crevice haze.

**Design:** at pixels flagged bimodal *and* boundary-coherent, fit
`v_i = α·F(z_i) + (1−α)·B` across the through-focus curve — F constrained by the
near layer's admitted frames, B by the far layer's, α by the transition shape.
Everything ramps, nothing vetoes (the edgeaware lesson). Outputs: the corrected
backdrop *and the α matte as a product artifact* — subject cut-outs from physics, not
segmentation. Prior-art posture per M19: Asada et al. 1995 formulated the model;
the claim is **first shipping stacker to invert it**, and even that needs the
`could not confirm` label until checked.

**Acceptance:** twin two-layer gate; chia-seeds crevices; wing/eye blotch guard
(the failure that motivated the veil floor must stay green); no motion on the 17
conditioned aura readings' direction.

### C4. Local warp refinement — a residual layer, not a new model

Two consumers need better *local, relative* placement: C1's within-DOF sample fusion,
and the ordinary merge, whose real input is per-frame placement (M103: end-to-end and
per-frame error are nearly independent; the 50× headline improvement bought nothing
where it counts). The global similarity stays — never chained, exactly as rule 6
demands. Added: (a) a smooth low-order residual field per frame, splined from the
solver's own tile displacements (which the solve currently collapses to four
parameters and discards), bounded in amplitude, refused where tiles are blind — this
is *not* optical flow and adds ~tens of parameters per frame, not per pixel; and
(b) for C1 only, per-tile relative refinement within the in-DOF window, where content
is matched and ZNCC parabola precision is at its best. Blur-equalisation (R5) remains
the queued upgrade for cross-focus edges, and any experiment on it must run M23's
zero-defocus self-pair control first — that is already written into the R5
disposition. Track jitter gets re-examined here too: M110's smoothing prior is
invisible at the *image* level, but C1's consumer is sub-pixel phase, where 0.48 px
of jitter is either signal (real motion, free diversity) or noise (solve error, the
enemy) — the refinement decides which, per stack.

**Acceptance:** held-out per-frame gauge (M103's) improves on the deep stacks;
planted-similarity nulls return identity; the 33× held-out spread across stacks
narrows or its cause gets named.

### C5. Metric depth, and the products that fall out of it

R21 sits queued: the fitted per-frame `log a` ladder plus measured m (M84b) and B
(M5) is a **metric ruler** — frame index → focus distance in micrometres — needing no
lens database, on a rig where the EXIF focus axis is useless (F §5: two distinct
values across a 33-frame stack; one LSB ≈ 22× the depth of field). Per pixel, M33's
log-parabola gives sub-step peak position; together: **a depth map in physical units
with per-pixel σ**, plus surface normals from its gradient. Products, in increasing
ambition: depth + uncertainty TIFF (no stacker emits this); the reshoot advisor
upgraded to physical units ("bracket ended 0.8 mm short of the far edge — 11 more
frames at your current step"); and **synthetic aperture re-rendering** — with depth,
per-frame admission, and actual captured defocus in hand, re-render the stack at any
focal plane and any simulated stop between "one frame" and "all-in-focus", by
depth-consistent blending of *captured* frames (selection with physics, no invented
values — the hull discipline extends naturally). A focus stacker whose output is not
one image but a refocusable object is a different product category, and every
ingredient is already in the tree.

### C6. In-situ sensor self-calibration — breathing as the dither

**The observation (ARGUED):** breathing slides the scene under the fixed pattern by
up to hundreds of plane px while the pattern stays put — the geometry astronomers
create deliberately by dithering. Per photosite, regressing its residual against the
warped consensus across N frames estimates its gain (PRNU, dust) and offset (DSNU,
hot) *at the working exposure, ISO and aperture* — the exact regime where the
delivered darks are wrong (fact 808: 1/100 s darks vs 1/8–5/2 s working exposures)
and where dust depth is aperture-dependent (V-MOTE: −2.94% on flats vs −3.4 to −5.7%
on masters).

**Respecting M29, which killed the naive version:** M29 refuted *shadow detection at
merge time* — the floor was scene texture at n_eff ≈ 3, because the merge averages
adjacent frames that agree. This estimator is different in kind: longitudinal, per
photosite, across the *whole* stack, with the scene term supplied by the consensus
rather than assumed smooth. It may still die on the same sword — scene texture
leaking through warp error — so the kill bar is set before the build: it must recover
both known real motes (−3.63%, −8.24%) and the flat-derived dust field on subjects
with ≥[bar] px of drift, at FPR < [bar] on the M25 twin with zero planted defects.
Flats remain the gold standard; this is the zero-capture fallback, the working-
exposure hot map M22 could not deliver, and a drift tracker for a map that ages.

---

## 7. Workstream D — the instrument and the product

### D1. The scorecard, built once, first

Everything §1 defined, plus the build order discipline: **instruments before
features.** The FRC spine (R25(iv): cannot be fooled upward by noise amplification);
the split-half SNR channel (M115's §2 design, the best-commissioned instrument in the
corpus — reuse it verbatim); the slanted-edge SFR estimator that already exists
validated to 114.6 cy/mm (M88 §2) pointed, at last, at something sharp (§30 chart);
planted-defect commissioning for every axis (the blur-plant detector already proved
potent at 0.3–0.4 px — README); SSIMULACRA2/butteraugli for the perceptual axis
(never dssim — licence). Comparators pinned and priced: licensed Zerene (PMax *and*
DMap — DMap has never rendered here), the fork rebuilt at its best-known build
(2.4× is the honest speed quote against it), Helicon if obtainable. Every scorecard
run archives hashes and sidecars under the banked-purge discipline so no result ever
becomes unreproducible the way V-RIM's did.

### D2. The certified-acuity map — "which file am I holding"

README names the gap: the tool hands over a print-worthy file or a soft one and does
not say which. The unified merge knows, per pixel and per band, whether the admitted
set cleared the calibrated floor. Collapse that into: per pixel, **the highest band
certified above noise** — an acuity map in cyc/px — plus the field-coverage summary
README says is the honest form of the quality claim (fraction of field certified at
≥ band k). This is the instrument-grade output that separates "retouch this" from
"reshoot this" from "print this", it costs no new measurement machinery beyond A1/A4,
and no shipping stacker has anything like it. It also becomes the print gate's input,
replacing the broken clip/crush statistics called out in STATUS §3.2.14.

### D3. The capture planner — the other half of the instrument

The corpus keeps proving capture dominates software: f/11 → f/5.6 was 13.5× on
matched-filter SNR (M20 §4.4, R15); the 2× TC is the leading suspect for the entire
2.2× non-diffraction blur (§29 — if the TC-off capture confirms it, "remove the TC,
crop less" may outweigh every algorithm in this file); ISO 400 is a second base with
more DR than ISO 320 (F §9); ETTR is free (§22); step density decides the estimation
premium (M27; the new step-1/5/7 stacks are the ladder). `strehl plan` folds the
measured optics (m, B, cutoff), the noise model, and M27's coverage criterion into:
given magnification, aperture and subject depth → step, N, predicted coverage, noise,
and certified-acuity forecast; afterwards the reshoot advisor closes the loop in
millimetres (C5). The §29 aperture ladder and TC-off brackets are the two captures
that turn the planner's aperture advice from ARGUED to MEASURED — they gate it.

### D4. Measured-PSF restoration — conditional, last, honestly bounded

M115 killed multi-frame deconvolution and the self-calibrated OTF; it did not kill
single-pass restoration under a *measured* system MTF — it never had one to test
(M88: "it has nothing sharp enough to point at"). The existing `restore.rs` is the
template of the honest shape: exact H, noise-budgeted gain, no ringing because the
calibrated noise stops it first. After §30 exists: measure the composite MTF (optics
× gather × merge), extend H accordingly, keep the same noise budget, gate on FRC and
the split-half instrument, flag any pixel the restore moves beyond its sample hull.
Expectation management is part of the design: M115's gate already reaches
R_SNR ≈ 1.36 by averaging, and the *information* is fixed — this stage can only trade
the noise budget for contrast honestly, which is worth shipping exactly insofar as
the budget B1 certifies is real. If FRC shows no gain, it ships as the measured
negative beside M115.

### D5. The performance budget

Quality features above must fit inside roughly 2× the current wall clock or they will
not ship as defaults. Known prices and offsets: the two-pass unified merge measured
~2.2× once (56.3 → 124.7 s at N=79, fact 1939); C1 at 1× *removes* 299 Malvar
demosaics and a 503 MiB/warp transient (sign: faster, smaller — to be measured);
SIMD is untouched headroom on a fold that is 98.5% of the run (zero `std::simd`/
intrinsics in 93 kLOC — ARCHITECTURE §11); GPU stays optional and non-contending
(M7: 173× on a stage worth 0.4–0.57% of wall; a separate crate per STATUS §3.3.11);
the memory planner must start pricing what it currently understates (measured
12.5–13.4 GiB against a printed 5.2 GB plan). Determinism rules stand: worker counts
stay memory-derived on the default path; every reduction order change is a freeze
event.

### D6. The plugin surface, resolved by A1 rather than by more traits

Today the only real seam (focus measures) is refused on the default backend —
"the plugin surface and the shipping path do not intersect" (ARCHITECTURE §8). The
unified merge decides this properly: pass one (election/depth) consumes a focus
field again, so the calibrated `FocusMeasure` seam becomes live on the default path
for free. Alignment models, optical profiles and output stages stay data-plus-enum
until a second consumer exists — SYNTHESIS §9's rule against pre-building seams has
been right every time it was tested.

### D7. Colour and print polish

Landed and cheap to keep: ICC + 300 DPI in the deliverable (fact 1916). Remaining:
the owner's paper profile (§31 — outranks any code change for print), soft-proof
gamut census against that profile, and the per-channel-vs-per-luminance tone decision
STATUS §3.2.14 says nobody has authorised — take it to a decision memo with the print
gate's numbers attached.

---

## 8. What this proposal deliberately does not contain

Respecting the graveyard is half of what the corpus is for. Each row names the one
condition that would reopen it; absent that condition, re-proposing these is noise.

| Killed idea | Killed by | Reopens only if |
| --- | --- | --- |
| Multi-frame Wiener / matched filter across focus as the merge | M20, M70, M115 — three instruments, one answer (R_SNR 1.0014 [0.965, 1.038]) | A future merge stops harvesting off-peak frames (it will not — A1 harvests more) |
| OTF self-calibration from through-focus curves | M115 (separately refuted) | Never for deconvolution; D4 uses a *measured* PSF instead |
| Outlier / robustness rejection at merge time | Refused 4×; M123 fired on 29.55% of a stationary subject | A detector with pre-registered FPR commissioned on the §12 static repeat burst — and only behind the reshoot verdict |
| Confidence as a scalar (entropy or otherwise) | M32, M34 — no monotone scalar is faithful | Nothing. Ship the vector |
| Alignment shrinkage correction | M12 — 0/18 transfer, worst case 83.4× worse | Nothing |
| Metacalibrated edges | M23 — the "response" was the probe's own resampler | Nothing; R5 blur-equalisation is the surviving heir, behind its self-pair control |
| Adaptive `--target-n-eff` rule | M64 (refuted on M52's own numbers) | A1's calibrated admission width supersedes the question |
| Chained alignment, in any disguise | Rule 6, M10, M103 | Nothing. C4 adds residual layers to the *global* solve |
| Per-frame demosaic quality as a battleground | M104b, M118, ORCH-kernel-decision — kernel datasheets, not photograph facts | C1 dissolves the question rather than answering it |
| Deep MFIF / learned fusion on the default path | Risk 3 (domain: 2-image, low-res, synthetic) | Only ever twin-trained (R24's covenant), only ever opt-in |

---

## 9. Sequencing

Ordered so that every expensive build is preceded by a cheap measurement that can
kill it, and every claim-bearing phase lands after its instrument. Lane names follow
house convention.

**Phase 0 — measurements and purchases (corpus-only + one capture session).**
- OWNER: the capture session — §30 chart + §32 export, §33 sharp subject, §29
  aperture ladder (f/5.6, f/8, f/11), §17/§29 TC-off bracket, §12 static repeat
  burst, one IBIS-ON bracket (C1), §6 darks at working exposure. One session covers
  all of it; captures-needed "START HERE" already orders most of this.
- OWNER: Zerene licence (D1 is blocked on it; the trial writes zero bytes).
- M-PHASE0-LCA: per-channel through-focus peak offsets on 2–3 corpus stacks (C2's
  go/no-go; zero captures needed).
- M-PHASE0-PHASE: phase-coverage census from existing warpmaps — the distribution of
  within-DOF sub-pixel phases by field radius, per stack (C1's go/no-go; zero
  captures needed).
- M-PHASE0-PTC: B1 prototype on two stacks, scored against M90's independent g.
- V-VEIL2: re-run the §59.3 probe harness so A2 has its acceptance instrument before
  its build.

**Phase 1 — one merge (A1, A2, A4, B3, B4), behind the freeze.**
Entry: phase 0's veil instrument; the soft-gate patch as starting material; width-
matched calibration per facts 1917–1920. Exit: the §1 scorecard v0 run end-to-end on
the corpus — noise, hull, halo-where-measurable, speed — plus per-band n_eff maps as
shipped artifacts. The gate-default question (2.0 vs 4.5) closes here as a
calibration, not a constant.

**Phase 2 — estimation finished (B1, B2), D2 acuity map, D3 planner v1.**
Exit: `Provenance::Measured` on an unknown body's stack; foam's B/G climb flattened;
the certified-acuity map shipping by default; the planner speaking millimetres once
C5's ruler lands (else frame indices).

**Phase 3 — the fusion bet (C4 then C1), C2 if phase 0 cleared it.**
C1 lands in two rungs: **1× lattice first** (demosaic-free merge — strictly a
correctness/efficiency win, no SR claim), then **2×** behind the D1 instruments.
Exit: FRC-scored, moiré-scored, split-half-scored verdicts on §30/§33; either the
first defensible resolution claim in the project's history, or a measured negative
with the phase-coverage census explaining exactly why.

**Phase 4 — the frontier (C3, C5, C6, D4), and the product surface (D6, D7).**
Each independently killable; none load-bearing for the phases before it.

**Standing constraints across all phases:** D5's 2× wall-clock budget; byte-freeze
rows per backend maintained (the pyramid row's `env_align=0` gap gets its aligned
sibling in phase 1); author-never-verifies on every claim-bearing number; and the
scorecard — not this document — is where "SOTA" gets decided.

---

## 10. Self-audit — where this proposal is most likely wrong

1. **The two-pass cost may bite harder than priced.** The 2.2× figure is one
   measurement at N=79 on a different kernel. If SIMD cannot buy it back, A1 needs a
   one-pass approximation (provisional winner + correction) and that approximation
   needs its own commissioning. This is the likeliest engineering wall in phase 1.
2. **C1's registration wall may be real.** The within-DOF-frames-are-easy argument is
   ARGUED, not measured; M110's 0.48 px jitter might be solve noise that local
   refinement inherits rather than fixes. That is exactly what M-PHASE0-PHASE and
   C4's planted nulls exist to find out before the big build.
3. **Per-coefficient admission could resurrect the patchwork in the band domain.**
   The pyramid's smoothed energies and the winner's spatial coherence argue not, but
   M120's lesson is that winner fields shatter where no correct answer exists —
   phase 1's acceptance includes a flat-ground plateau census for this reason.
4. **B2 touches the most dangerous pixels in the image.** Censored estimation on
   speculars must be byte-identical off the clip set and flux-bounded on it, or it
   becomes the invented-values defect wearing a likelihood. The hull axis on the
   scorecard is the tripwire.
5. **Scope.** This document proposes more than a team ships in a season. The phase
   gates are the control: each phase ends at a scorecard run, and any phase's
   negative result is a publishable stopping point, not a sunk cost. If only one
   thing survives triage, it should be **phase 1** — the thesis shipping by default
   is worth more than any single novel technique in this file — with **phase 0's
   capture session** alongside, because it is the only item here that no amount of
   software can substitute for.
