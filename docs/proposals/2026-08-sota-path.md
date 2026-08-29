# strehl — the path to a defensible SOTA claim

**Status: PROPOSAL, revision 2 (2026-08-29).** Every claim here is ARGUED unless it
cites a measured report by name. Numbers I derived myself are labelled DERIVED with the
arithmetic shown; numbers transcribed from the corpus carry the report or file that owns
them. Per rule 12, nothing in this document should be believed — it should be falsified,
item by item, in the order §9 proposes. Per fact 1886, every corpus absolute quoted here
is a timestamp, not a constant: re-measure at point of use.

**Revision 2 — what changed and why.** Revision 1 was written 2026-08-28. Between then
and now the state moved and the audit deepened:

- **The state audit was re-run against `ARCHITECTURE.md` (2026-08-28) and the lanes that
  landed after it** — V-SOFTCHECK/V-NEVERWORSE (the frequency-resolved merge-vs-best-frame
  answer, facts 1969/1978–1981), V-H2H2 (the significance exponent measured at depth: a
  null that should not ship, facts 1974–1975), V-RIM (the ±12 px rim axis acquitted,
  facts 1896–1902), the print gate closing 33/33 (facts 1966–1968), and the pyramid
  byte-freeze row (fact 1982).
- **A structural contradiction between the architecture document and the shipping code
  was found and is now a named exhibit** (§2.4): the fold's most consequential recent
  change — a full per-frame demosaic inside the warp — is invisible in the architecture
  document written two days after it shipped, and it inverts three of the document's own
  headline invariants. This materially strengthens workstream C1 and is cited there.
- **New items:** A5 (the depth-field election — election itself becomes estimation),
  B5 (the per-stack sensor-state ledger), C7 (orientation-resolved election /
  astigmatism), C8 (active-texture capture), C9 (polarisation diversity from the CPL the
  owner already uses), the §6.0 information-channel ledger that argues the C list is
  *complete* rather than merely long, a CRLB formalisation for D2, a bootstrap-MTF
  instrument for D1/D4, and four new zero-capture phase-0 measurements.
- **Corrections to revision 1:** the memory-planner understatement is now correctly
  attributed (`align_cmd.rs:1794–1804`, the fullres-gather transient — it is a property
  of the *new* default, not of the planner in general); the fine-detail axis row now
  carries V-SOFTCHECK's split verdict instead of "undecidable" alone; the halo/rim rows
  are updated to the acquittal; and one proposed data channel (per-frame black tracking
  from optically-black photosites) is **withdrawn before anyone builds it** — the decoded
  buffer's padding is exactly zero, not masked sensels (`strehl-raw/src/lib.rs:10–15`),
  so the channel does not exist in this decode. Its purpose survives inside B1/B5 by
  other means.

**What was read before writing (cumulative over both revisions):** `README.md` in full,
`docs/ARCHITECTURE.md` (2026-08-28 revision) in full, `docs/STATUS.md` (2026-08-27
wind-down) in full, `AGENTS.md` (rules 1–48, rig, licence discipline),
`SYNTHESIS.md` §6 verbatim plus §7 and targeted facts, the external-review triage
(`2026-08-external-review.md`) in full, `docs/captures-needed.md` (START-HERE index,
§29–§33 at depth), and the following at verdict depth or in source: M2, M5, M12, M20,
M21, M22, M23, M27, M29, M30, M32, M33, M34, M64, M65, M70, M75, M84b, M88, M90, M103,
M110, M115, M118, M120, M123, B §6–§8, F, G-edof (M19), ORCH-veiling §59.3,
BUILD-PYRNOISE (via README), V-SOFTCHECK-nyquist and V-DCNULL (via STATUS),
`align_cmd.rs:1160–2100` (the fullres gather, in source), `merge.rs` (FocusStats,
sufficient statistics, the gate), `edgeaware.rs` (the domain-transform filter,
depth-layer support), `strehl-raw/src/lib.rs`, and the withheld soft-gate patch's
paper trail (facts 1917–1940).

**The commissioned question:** what to add, change, or do to make strehl a *truly*
SOTA focus stacker — novel territory explicitly allowed.

---

## 0. The one-paragraph answer

strehl already holds the axes it has measured — noise, clipping, invented structure,
speed, memory — and cannot yet *quote* the axis the field is judged on, fine detail,
because the corpus contains no target sharp enough to measure it (M88, captures-needed
§30/§33) and the comparator refuses to save output (README, Zerene licence). The thesis
that wins those axes ships **diluted**: the estimation machinery lives on a backend that
is not the default, and the default still *selects* — measurably, on noise, in flat
regions, at every band (`pyramid.rs:1136–1147`), with a 24–240× selection premium
standing on essentially every mid-frequency coefficient of every subject (facts
1843–1845, 1849) — and the two knobs built to soften that (the significance exponent,
the soft gate) are now respectively **measured as a null at depth** (facts 1974–1975)
and **withheld as a patch** (facts 1933–1940), which says the fix is a calibrated
admission rule, not a better constant. Meanwhile the project's own research has already
identified, and never developed, the physical channels no other stacker can reach —
sub-pixel diversity from focus breathing, longitudinal CA as three offset focus sweeps,
the two-layer occlusion model, metric depth from breathing, and (new in this revision)
the depth *field* as the election's latent variable, orientation-resolved focus, and
two capture-side channels the owner can open with hardware already on the desk. Every
one of them requires exactly what strehl uniquely has: RAW samples, a calibrated noise
model, and a fixed rig. The path to SOTA is four moves: **(A) make the thesis ship** —
one merge, estimation in the band domain *and in the election*, confidence on the
default path; **(B) finish estimation** — runtime noise self-calibration, censored
(clipped) samples, photometric via the breathing law, the sensor-state ledger; **(C)
exploit the physics** — sample-level fusion that retires demosaic and resampling as
separate lossy stages (and resolves the §2.4 contradiction), plus the depth, wavelength,
orientation and illumination channels; **(D) build the instrument that makes any of it
quotable** — the pre-registered scorecard, the certified-acuity map, the capture
planner. Sequenced in §9. If only two things survive triage: **phase 1** (the thesis
shipping by default) and **phase 0's capture session**, because the latter is the only
item no amount of software can substitute for.

---

## 1. What "SOTA" is allowed to mean here

README says, correctly: *"'State of the art' is not a defensible claim for this tool
today, and is not made anywhere in this document."* This proposal's terminal goal is
that that sentence becomes deletable. That requires deciding, in advance, what would
license deleting it — otherwise the claim will be minted by whichever statistic happens
to flatter the build of the day, which is the failure mode this corpus has caught in
itself at least seven times (README §Measured-against-other-stackers) and which the
captures-needed self-audit quantified: of 25 owner-facing summaries re-derived from
their underlying data, **8 were wrong in some detail and all 8 leaned flattering**
(p = 0.0039 under a coin-flip null). Directions hold; magnitudes discount.

**SOTA = a pre-registered scorecard, versus named comparators, on axes with
commissioned instruments.** An instrument is admitted to the scorecard only after it has
(a) failed on a planted defect of the kind it polices, and (b) passed a null it was not
tuned on — the standard this project already applies internally (rules 9, 11, 13; the
V-RIM acquittal is the template: the statistic that convicted 13 subjects also convicts
Zerene *and a raw unstacked camera frame*, facts 1896–1902, so it was measuring shoulder
roughness, not a stacker). Proposed axes, with today's honest state:

| Axis | Today | What blocks a claim |
| --- | --- | --- |
| Noise, flat/defocused ground | **Ahead, measured.** 4.5× vs the fork (≥2.4× worst-case grade-corrected); 0.746× vs one unstacked frame at gate 4.5; 9.9× flat-field rms on the deepest stack with the compound eye indistinguishable (README) | Nothing — quotable now |
| Highlight retention | **Ahead vs fork (32% clipped vs 4e-6), but the default path cannot see its own clipping** — the clip census does not run there (README) | Wire the census; B2 below |
| Invented structure | **Ahead.** 0.0000% out-of-hull for every convex arm, held as a discipline (M115 §1) | Keep it an axis, so it cannot be quietly traded away |
| Occlusion veil / aura | Directional win, all 17 conditioned readings (fact 1871); halo axis: 11 of 26 demonstrated clean, 4 blind + 7 unmeasurable (fact 1891); ±12 px rim axis **acquitted** (facts 1896–1902); veil mechanism measured, unfixed (ORCH-veiling §59.3); `chia-seeds-cpl` crevice haze is the live specimen (STATUS §4) | ≥400 px clear-background captures; A2/C3 below |
| Fine detail ≥ 0.15 cyc/px | **Split by frequency, one subject, no CI:** the master reads **1.10–1.19× the per-site best-frame ceiling below 0.20 cyc/px** and **0.9426 (≈5.7% short) at 0.20–0.25**, softer above (facts 1969, 1978–1981; V-SOFTCHECK-nyquist). Vs comparators: **undecidable in either direction** (README) | §30/§32/§33 captures; a licensed comparator; the D1 instrument. The below-0.20 win is the first of its kind in the corpus and needs its CI and its exposure audit before anyone quotes it |
| Per-pixel trust | **Absent from the field (VERIFIED, C) and absent from strehl's default path** — the refused-flags list | A4/D2 below. This is the thesis, not a feature |
| Depth output | Absent from the field; unbuilt here (R20/R21 queued) | A5/C5 below |
| Speed / memory | **Ahead, measured.** 22.58× enfuse; 2.4× the fork's best build; 0.20–0.39 s/frame; flat memory (STATUS §1, ARCHITECTURE §9) | Hold the line: quality features must fit ~2× current wall (D5) |

The scorecard needs three purchases/captures that no algorithm can substitute for: a
Zerene licence (the trial saves zero bytes — README), the slanted-edge chart and its
Lightroom-export half (§30/§32), and one subject with real contrast above 0.25 cyc/px
(§33). These are cheap against the months of instrument-building they unblock, and
**every fine-detail claim in this proposal is contingent on them.**

The end-state sentence the project should be able to print, each clause with its
licensing instrument in parentheses:

> On [subjects], strehl resolves detail at or beyond the best shipping comparator
> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly lower noise
> (existing flat-ROI instrument), with zero invented structure (hull census), no
> occlusion veil above [bar] (halo instrument at full reach), while emitting per-pixel
> certified acuity, n_eff, and depth in physical units that no comparator emits at all
> (D2/A5/C5), in [X] s per frame on CPU (existing harness).

---

## 2. The research corpus: an audit

The owner asked directly whether the research is useful at all. Verdict unchanged from
revision 1 and strengthened by what landed since: **it is the project's principal
asset, and it is what makes this proposal writable.** Three ways it earns that, four
hazards, one new exhibit, and the residue it left unexploited.

### 2.1 What it is worth

**(a) The graveyard.** The obvious ideas an outside proposer would reach for first are
already measured dead, with mechanisms: multi-frame Wiener across the focus axis (M20:
wins 15.1% of pixels; M70: the band matrix is rank-1 to 0.9959, so matched filtering
over near-scaled copies *is* weighted averaging; M115: R_SNR 1.0014, CI [0.965, 1.038],
with 29.5–36.4% of deconvolved pixels outside the convex hull of their own sources —
three instruments, one answer); OTF self-calibration from the through-focus curve
(M115, separately); outlier rejection (**five** independent refusals now — M123 fired on
29.55% of a *stationary* subject, and a second mechanism was 21.5× more active on the
stack that never moved); entropy-scalar confidence (M32: blind, non-monotone,
degenerate — the posterior is a delta at 142–991σ); shrinkage calibration for alignment
(M12: transfers 0 of 18, worst case 83.4× worse); metacalibrated edges (M23: the
measured "response" was the probe's own bilinear resampler); and now the significance
exponent at depth (facts 1974–1975: benefit saturates by z=100, cost does not, the
lane falsified its own pre-registered prediction). Without this record, the present
proposal would be longer and mostly wrong. §8 lists what is therefore *not* proposed.

**(b) The measured constants that make the physics exploits designable.** Magnification
m = 2.7198 ± 0.0051 (M84b); bellows factor B ≤ 3.064 at f/11 with a genuine spectral
knee at 0.2762 cyc/px (M5); pupil factor p ∈ [1.31, 1.94] putting the f/5.6 diffraction
cutoff at **106–135 cy/mm, above the 97.66 cy/mm sensor Nyquist** (M88); the rig
measured **~2.2× softer than diffraction alone explains**, two instruments within 4%,
with "mostly optical" bounded above at ≤76.6% on n=1 and a printed target
(captures-needed §29) — which means both that aliasing physically exists to recover and
that a real, optics-shaped blur budget exists that only reconstruction can touch; the
noise model g/read/κ with an independent PTC cross-check (M71, M90); FOCUS_NOISE_SD and
the 10.27× operator span (plugin seam); breathing = −1.012% scale across 33 frames,
linear, scale centre ~400 px off image centre (F §6–§7), up to 299 plane px corner
drift at N=299 (ARCHITECTURE §7); adjacent-frame warp 0.07–0.22 green px (M29); track
jitter median second-difference 0.48 px, 13.8% of adjacent pairs ≥1 px (M110); the
sub-frame peak cost distribution (M33: 48.7% of pixels miss peak; median 4.64%, p99
17.34% of response); and the selection premium itself, 24–240× (facts 1843–1845, 1849).

**(c) The instrument discipline.** Pre-registration, planted defects, placebo arms, the
author-never-verifies rule, "a statistic that has only ever been shown to succeed is not
evidence." A SOTA claim is exactly the kind of statement that dies without this, and the
project already knows how to build claims that survive attack — the V-RIM acquittal
(the instrument convicts a raw camera frame, therefore it convicts nothing) and the
V-SOFTCHECK sign-immunity argument (one gain scalar cannot take seven values of opposite
sign) are the two best recent specimens. G-edof additionally hands the project the one
ground-truth-free sharpness metric that cannot be fooled upward by noise amplification
(FRC — R25(iv)), which D1 adopts as its spine.

### 2.2 The hazards

1. **A large share of quality results measure the estimator backend, which no longer
   ships.** The gate table, the n_eff calibration ladder, the veil estimator, the
   edge-aware machinery, photometric — all estimator-path. The pyramid default beats the
   estimator on acuity, microcontrast and aura (README), so the *conclusions* mostly
   transfer in strehl's favour, but the *numbers* do not, and README documents two
   headline retractions caused by exactly this transfer.
2. **Absolutes are timestamps** (fact 1886: a coefficient-independent arm re-rendered
   across builds differed on 33M px). Everything quantitative in this proposal must be
   re-derived inside the lane that consumes it, from one pinned build.
3. **Instrument churn ate the project's middle.** Three detail statistics, two rim
   instruments, one timing harness and one deconvolution channel failed their own
   commissioning. The cure is D1: build the instruments *once, first,* against the
   captures that give them something to grip.
4. **Several load-bearing questions are blocked on captures, not analysis** — and have
   been for weeks: §30/§32/§33, the aperture ladder (§29), the TC-off bracket
   (§17/§29), darks at working exposure (§6/§28), the ≥400 px clear-background subject
   (fact 1891). The cheapest schedule acceleration available to the owner is one capture
   session (§9, phase 0).
5. **Summaries lean flattering; the docs age faster than the code.** The 8-of-25 audit
   above, plus §2.4 below, plus the stale rim-FAIL line still standing in
   ARCHITECTURE §11 after V-RIM acquitted it. The discipline that follows: this
   proposal cites files and facts, not summaries of summaries, and every number in it
   is re-measured at point of use. And 46 `STREHL_*` environment variables are
   currently unproven on the default backend (fact 1882, V-ENVSURF in flight) — treat
   any env-gated claim as inert until a liveness control proves otherwise.

### 2.3 The unexploited residue — the corpus's own novelty list

SYNTHESIS §6 records four verified-absent-from-literature bets, and B §6–§7 sketch two
of them at hypothesis level. **None has been developed.** They are this proposal's
workstream C: super-resolution from focus-breathing sub-pixel diversity (B §6: four
arXiv queries, zero results); per-channel focus stacking exploiting longitudinal CA
(B §7.2: no prior work found; Trouvé 2013 and Chang & Wetzstein verify the physical
signal exists); diffraction+defocus PSF modelling at macro magnification; a monocular
depth prior as an ordinal regulariser (folded into A5 as an opt-in, covenant-safe per
risk 3); depth-from-breathing as a metric ruler (R21, "QUEUED — attractive"); and the
two-layer occlusion model, where the defensible claim is "first *shipping* tool"
(Asada 1995 precedent, M19). Two external-review items were parked rather than killed
and are revived here: R18 (active texture — C8) and R16's aperture-paired half.

**A standing caution on every novelty claim in this file, from the corpus's own audit
of itself:** two prior surveys each missed their nearest prior art (Pertuz 2013;
Schechner 1998 — facts 1112, 1136), so *"verified absent" inherits the search quality
of the report that made it*. Every C-item below therefore carries the `could not
confirm` posture, and each one's phase-0 gate includes its own literature pass.

### 2.4 NEW EXHIBIT — the pipeline has two contradictory identities, and the freshest document in the tree picked the wrong one

Dated from git, verifiable in ten minutes:

- **2026-08-26**, commit `740e7056`: `STREHL_FULLRES_GATHER` defaults **on**. The
  shipping warp now runs a **full Malvar demosaic of every frame inside the warp**
  (`warp_frame_in_place_fullres`, `align_cmd.rs:1839–1862`), because the per-phase-plane
  gather band-limits every phase to 0.25 cyc/output px *before* election, "so no later
  stage can recover it" (`align_cmd.rs:1164–1174`). Measured for the flip: band
  correlation at 0.25 cyc/output px rises 0.1514 → 0.9329, at 0.35 from **−0.4965
  (inverted structure) to +0.4478**, and it is 40–97 ms/frame *faster* — with one
  overshoot statistic dissenting and recorded open (`align_cmd.rs:1177–1208`). Cost:
  a 503 MiB transient per warp, and a measured fold peak of **12.5–13.4 GiB against a
  printed 5.2 GB plan** on the deepest stack (`align_cmd.rs:1794–1804`).
- **2026-08-28**, commit `550fded6`: `ARCHITECTURE.md` lands — and describes the
  *other* pipeline. "Never materialise aligned frames … demosaics 60 times instead of
  once" (§3, rule 2); "Demosaic runs exactly once, at the end, on the merged planes"
  (§4); "One resampling pass, ever" (§7). The string `fullres` appears **zero times**
  in the document. The default path it documents is the one you get with
  `STREHL_FULLRES_GATHER=0`.

Both identities are honest about their own trade — the plane gather never invents a
value but destroys super-Nyquist phase content before the election; the fullres gather
preserves it but feeds **interpolated values into the election and the merge**, 299
demosaics per stack. The project's freshest architectural document asserting the first
identity while the code ships the second is not a documentation bug to file and forget;
it is the clearest statement available that **the current pipeline's reconstruction
story is unstable because both options are wrong**. Reconstruction quality is being
decided per-frame, blind, before the estimator sees anything — each arm merely picks a
different casualty. That is the specific incoherence C1 exists to dissolve: one
reconstruction, at the end, from real samples, under the noise model. (Separately:
ARCHITECTURE §11 still lists "13 subjects FAIL on a rim axis at ±12 px" — acquitted by
facts 1896–1902 — so the document needs a correction pass; that is a docs task, not a
workstream.)

---

## 3. Strategy

Four workstreams. A and B make the thesis true of the product a user runs. C is the
novel territory — the physics only strehl can reach. D is the instrument and the
product surface that turn all of it into claims and into a tool someone can trust.
Nothing in C is load-bearing for A/B/D; the plan degrades gracefully if any bet dies,
and each item below carries its own kill bar so it can die cheaply.

A one-line version of each:

- **A — One merge, thesis on both axes.** Estimation moves into the band domain
  (A1–A4), and — new — into the *election itself* (A5): the merge stops crowning
  winners and starts estimating the focus surface. The backend fork retires;
  confidence ships by default.
- **B — Estimation finished.** The noise model measures itself per stack; clipped
  samples become inequalities instead of lies; photometric gain follows the breathing
  law it measurably obeys; the sensor's slow drift across a bracket becomes state, not
  noise.
- **C — The physics exploits.** The merge consumes photosites, not resampled
  estimates; colour becomes three offset focus sweeps; occlusion becomes a two-layer
  estimate; the warp gains the one physical term a similarity cannot carry; depth
  becomes an output in micrometres; the sensor calibrates itself under the sliding
  scene; focus becomes orientation-resolved; and the capture side gains two channels
  (projected texture, rotated polariser) that cost the owner one accessory each.
- **D — The instrument.** The scorecard, the certified-acuity map with a CRLB spine,
  the capture planner, the bounded restore, the performance budget that keeps all of
  the above shippable.

---

## 4. Workstream A — one merge: the thesis ships

### A1. The banded admission merge

**The defect, measured.** The default pyramid is a per-coefficient *selector* above its
noise floor: the exponent ladder runs 7.68/8.0/8.0 in the three finest bands ("a frame
with twice another's band energy gets 256 times the weight", `pyramid.rs:1241`), bands
1–6 average essentially nothing (0.29/0.08/0.06/0.03/0.00/0.00% — STATUS §2), the
24–240× selection premium stands on those coefficients, and selection concentration is
measured *higher in flat regions than in detail regions at every band* — "a merge
selecting on noise" in the module's own words (`pyramid.rs:1136–1147`; 1.0000 vs 0.8214
at band 0 where a plain mean reads 0.0526).

**The knob family is now exhausted, which is the new evidence for the rule change.**
Three attempts to fix this inside the existing weight form have each terminated:
the built significance fix ships off because at derived strength it does not collapse
the inversion (ARCHITECTURE §1), and measured at depth it is a null that "should not
ship on this evidence" — benefit saturated by z=100, cost growing, the lane's own
pre-registered prediction falsified (facts 1974–1975); the soft-gate wiring landed as
validation-without-application (`enable_soft`: zero call sites) and the 242-line hunk
is deliberately withheld at `experiments/BUILD-SOFTGATE/pyramid-softgate.patch`
(facts 1933–1940); and the gate-2.0-vs-4.5 question remains a two-constant standoff in
which the shipped default is the measured worst operating point on the curve (README
FoM table: **1.06 at 0.40–0.50 cyc/px — discarding detail and noise in equal
proportion, which is what an indiscriminate blur does** — against 2.87–4.77 at 4.5).
Meanwhile the corpus proved the shipped soft-power weight *is already* an exponential
soft kernel over log-SNR deficit at temperature 1/p (facts 1933–1940) — so the missing
piece was never a new kernel; it is a **calibrated admission width**.

**The design.** Keep the Laplacian frame — M120 proved the estimator's polygonal
patchwork is a property of the per-pixel winner field, and the pyramid's spatial
coherence is why it won the A/B; do not re-litigate that. Inside each band, replace
soft-power ratio weighting with the estimator's own admission logic, per coefficient:
elect the winner by smoothed band energy exactly as today; **admit every frame whose
smoothed energy lies within k·σ_band of the winner** (σ from the injected model times
the per-frame measured floor that already ships); **average the admitted coefficients
with inverse-variance weights**; below the floor, fall back to the plain mean as today.
Report per-band n_eff as a first-class statistic.

Binding lessons from the soft-gate lane: **match kernels on effective width (n_eff),
never on the threshold parameter** (facts 1917–1920 — the same T admits n_eff 4.674
hard vs 19.295 Gaussian), and note the Gaussian kernel is not one-pass streamable (a
cross term forced a second decode pass, 56.3 → 124.7 s at N=79). An admission-by-margin
rule needs the winner before weighting, so the unified merge is likely **two-pass over
frames**; the estimator's two-pass structure and its O(1)-per-pixel sufficient
statistics are the template (ARCHITECTURE §5b), and the ~2.2× wall cost is priced in
D5. The withheld patch is the starting material.

**Why this is the highest-value quality item in the tree.** It attacks, with one
mechanism, the flat-region noise election (the largest measured divergence between what
ships and what the thesis promises), the gate-default dilemma (a calibrated width
replaces both magic numbers), and fact 341 (B4 below).

**Acceptance / kill bars.** Pre-registered before build: (i) the flat-vs-detail
concentration inversion collapses at every band on `coffee-bubbles`; (ii) detail-kept
at 0.10–0.30 cyc/px on the §33 subject within [bar]% of the gate-4.5 arm while
noise-kept improves; (iii) no regression on the four conditioned aura subjects and the
`coffee-bean` hull-clamp test; (iv) per-band n_eff maps show ≥[bar]× the averaged
fraction in bands 1–3 on flat ground with detail regions unmoved; (v) a flat-ground
plateau census (M120's ceiling statistic) shows no band-domain patchwork. Kill: if
(ii) fails after width calibration, the admission form is wrong for band statistics and
the result publishes as a negative with the sweep attached.

### A2. The depth-aware base band — the veil fix

**The defect, measured, with its mechanism confirmed in source.** The base band is a
plain unweighted mean across all frames (`BaseBand::Mean`, ARCHITECTURE §5a); at an
occluded pixel ~290 of 299 frames show the defocused bright foreground, so the correct
detail is added to the wrong pedestal — claw base 0.581, foreground 0.892, master
0.802, with detail correlation 0.852 to the right frame (ORCH-veiling §59.3). The
alternative arm (`WeightedFromCoarsest`) was measured and correctly rejected for
flat-field wander. The live specimens are `chia-seeds-cpl`'s crevice milkiness and the
0.708% rms far-field mottling (STATUS §4, README).

**The design resolves that dilemma with the gate instead of a global choice:** base
coefficients use the admitted-set mean (A1's admission at the coarsest band) *ramped by
election coherence* — coherent regions (a real object; `election_coherence.rs` exists,
estimator-only today) take the admitted base; incoherent flat ground keeps the plain
mean that is optimal there. Quantile-anchored thresholds, ramped not switched, per the
edgeaware lessons. Under A5 this generalises for free: the base-band admitted set is
"frames within DOF of the depth field", which is the same rule everywhere.

**Acceptance:** the §59.3 probe re-run — master base moves from 0.802 toward 0.581 with
the null window unmoved; `chia-seeds-cpl` crevice haze re-scored; flat-field wander
bounded at the level that killed `WeightedFromCoarsest`.

### A3. Edge-aware support and the estimator's other organs, ported or retired

`edgeaware.rs` (including the superseded depth-layer masked-support arm,
`merge_cmd.rs:1838`), the veil estimator, election coherence and through-focus
statistics are ESTIMATOR-ONLY today (ARCHITECTURE §10). After A1/A2/A5, measure which
still earn a place: the pyramid's seven bands already answer the occlusion halo
differently, and the halo is gone on this path (README) — so the null hypothesis is
that most of edgeaware is not needed in the band domain, and A5 subsumes the rest
(SelectionScale's "shrink support near depth steps" is what a solved depth field with
discontinuities does natively). Whatever survives, the fork retires: one merge, the
argmax baseline kept as the negative control, the estimator kept as a reference arm the
way `stack.rs` is today. The ten-vs-seven refused-flags split (ARCHITECTURE §5)
collapses with it, and the 46-variable env surface (fact 1882) shrinks with the code
that read it.

### A4. Confidence on the default path

The README names this the single largest gap between what the project is for and what
it does. M34 fixed the shape: **a vector, never a scalar** — the three channels flag
near-disjoint pixel sets (union 14.278% vs a 15.0% disjoint ceiling) and predicted σ is
*anti*-correlated with the sub-frame deficit in the worst tail. Ship, per pixel, on the
default path: per-band n_eff (A1 makes it exist), admission width, sub-frame peak
deficit via the **log-domain parabola with baseline subtraction** (M33 — the naive
parabola's peak-height estimate is anti-correlated with the truth), hull-clamp
distance, and — once B2 lands — the censored flag. D2 turns this vector into the
certified-acuity product; A5 adds depth and σ_z to it.

### A5. NEW — the depth-field election: estimation, not selection, in the election itself

**The observation.** The thesis fixed the *value* side of the merge — average the
admitted set instead of copying the winner — but the *election* side is still an
argmax: per coefficient (pyramid) or per pixel (estimator), independently, with
smoothing as the only spatial glue. The corpus has measured what that costs from four
directions: winner identity is fragile where it does not matter (M65: electing on the
raw field changes **56.70% of winners while the acceptance set moves 0.44%**), winner
fields shatter where no correct answer exists (M120: flat ground breaks into
piecewise-constant plateaus — "a detail statistic scores those manufactured edges as
detail"), flat regions elect on noise at every band (facts 1843–1849), and the
project's own diagnostic prose has said for a year that *"real depth is piecewise
smooth, so coherent bands are genuine focus structure and salt-and-pepper speckle is
the argmax defect made visible"* (README, `--index-map`) — an observation used
everywhere as a diagnostic and nowhere as a constraint.

**The design (ARGUED).** Make the latent variable explicit. Per pixel, pass one already
holds the through-focus sufficient statistics (FocusStats today keeps `best_focus` +
`best_index` at O(1)/px, `merge.rs:867–889`; the `--stats` arm adds the log-parabola at
a 5 px window). Extend pass one to keep three parabola coefficients per pixel; from
them, ẑ (sub-frame peak position, M33's estimator) and a **data confidence** — DERIVED:
for a parabola peak under response noise σ_r, σ_z ∝ σ_r / (curvature × step²), so
confidence is curvature over noise, and it goes to zero exactly where the ground is
flat and election currently chases noise. Then solve one global problem per stack:

```
z(x,y) = argmin  Σ_p  w_p · ρ( z(p) − ẑ(p) )  +  λ · Σ_edges  ψ( ∇z )
```

with `w_p` the curvature/σ confidence, ρ Huber, and ψ an edge-aware penalty that
*permits* discontinuities where election coherence and M21 bimodality say a depth step
is real, and enforces smoothness elsewhere. **The v0 solver is already in the tree:**
the domain-transform recursive filter (`edgeaware.rs` — one-tap IIR, cost independent
of radius) applied to the ẑ field with confidence pre-weighting is a one-sprint
prototype; a Huber multigrid solve is the v1. Admission in pass two becomes the union
of two rules: A1's energy margin, **or |z_i − z(x,y)| ≤ DOF/2 in frame-index units**
(DOF from the measured optics: ≈1.3–1.5 frames at the recommended step, 3–6 at corpus
density — M27, SYNTHESIS §1). The union can only widen admission, so it degenerates
safely: where the surface is confident it admits the physically-sharp set even if band
energies are noisy (flat mid-ground: admission driven by *interpolated depth*, so the
whole selection premium vanishes there); where the surface is uncertain (σ_z large) the
depth term admits everything and A1's rule alone governs — which is today's behaviour.

**Why this is not "smooth the index map".** A post-hoc smoothing of the winner field
inherits the winner field's haloed, shattered geometry (the edgeaware module already
learned this: the guide could not be the winner field, ARCHITECTURE §8). This is a
joint estimate with per-pixel uncertainty from the calibrated noise model, and its
failure modes are declared: thin structures (a hair crossing defocused ground) violate
smoothness — the bimodality/coherence guards route those pixels to C3's two-layer model
instead of forcing one z; textureless ground gets its z from the prior — and a wrong z
there is harmless by construction, because every frame is equally defocused there and
the value estimate degenerates to the mean regardless.

**Prior art, named before anyone claims novelty (fact 1136 discipline):** depth-map
stacking *exists* — Zerene DMap and Helicon Method B build a depth map, smooth it
ad hoc, and select from it; the shape-from-focus literature (Pertuz 2013 survey) fits
focus surfaces; microscopy EDOF has smooth-manifold extraction. What I could not
confirm existing anywhere (`could not confirm`, phase-0 literature pass required): the
**noise-calibrated joint form** — per-pixel σ_z from a measured sensor model, admission
by DOF around a solved surface with refusal semantics, occlusion routed to an explicit
two-layer model, and the surface exported in metric units (C5) with its uncertainty.
DMap has never even rendered here (licence), which D1 must fix — it is this item's true
comparator, not PMax.

**What it buys.** (i) The flat-region selection premium attacked at its root rather
than at the weight (the premium exists because election is per-pixel; a surface has no
per-pixel freedom to sell); (ii) the patchwork class closed structurally (plateaus
cannot form when z is continuous); (iii) the veil/base-band fix unified (A2 becomes
"admit by depth" at the coarsest band); (iv) **the depth map itself as a product** —
A5's z(x,y) ± σ_z *is* C5's deliverable once the breathing ruler converts index to
micrometres; (v) the reshoot advisor's coverage verdicts localise in depth, not just in
the frame. The monocular-depth ordinal prior (SYNTHESIS §6 bet) slots in as an
opt-in, twin-trained regulariser per R24's covenant — never on the default path.

**Acceptance / kill bars (pre-registered):** on the M25 twin (whose gates already
include a two-layer scene), recovered z within [bar] of truth where confidence clears
[bar], and **no regression through the planted-defect suite**; on real stacks, the
flat-ground plateau census and the selection-concentration inversion both collapse at
least as far as A1 alone; the 36-site merge-vs-best-frame tie (README) must not move
toward "softer"; `flower-bud-with-background-fern-cpl` (the many-layer tangle) renders
without new boundary defects. Kill: if the twin shows the surface prior dragging z
across real discontinuities faster than the guards catch it — measured as edge
displacement of depth steps beyond [bar] px — the item dies and A1 stands alone.
Cheap phase-0 gate first: **M-PHASE0-ZFIELD**, a corpus-only census of ẑ curvature,
σ_z, and coherence from existing estimator statistics — if σ_z is so large at corpus
step sizes that the surface never beats the per-pixel estimate outside already-easy
regions, kill it for one sprint's cost.

---

## 5. Workstream B — estimation finished

### B1. Runtime noise self-calibration — rule 3's unimplemented half

**The gap, in the project's own words:** "there is no runtime noise estimator, so
nothing cross-checks a profiled body against what its own frames actually show"
(ARCHITECTURE §3). Exactly one body is profiled; every other camera degrades to
`Provenance::Fallback`. And the shipped model is knowingly over-confident above
S = 504 DN (PRNU measured, off — −12.8% at S = 8000, ARCHITECTURE §6).

**The design.** The stack itself is a photon-transfer instrument. Adjacent frames in a
bracket differ by a sub-pixel warp (0.07–0.22 green px — M29), a fitted photometric
gain, and noise. Per stack: take adjacent-frame pairs, remove the fitted gain ratio,
high-pass, and in low-gradient tiles regress the robust variance of the difference
against mean signal — a temporal PTC at the working exposure, ISO and aperture, blind
to fixed pattern by construction (the M90 method applied in-stack). Cross-check with
the G1−G2 split within single frames (the two green phases sample the scene a half-quad
apart; their high-passed difference in smooth regions is an independent σ probe — after
calibrating the static G1/G2 imbalance once on the delivered flats), and against the
per-frame measured band floors `gatefloor.rs` already computes. Output: measured g,
read floor, and a κ consistency check against the profile; on an unknown body this *is*
the model — `Provenance::Measured` — which retires the one-profiled-camera limitation
as a portability blocker.

**One channel that does NOT exist, recorded so nobody re-proposes it:** per-frame black
tracking from optically-black photosites. The decoded buffer's 136 columns / 432 rows
of padding are **exactly zero — "not masked sensor pixels and not black level"**
(`strehl-raw/src/lib.rs:10–15`). Black-level drift must instead be estimated as the
intercept of the temporal PTC and from the deep-shadow quantiles of low-gradient tiles
(B5).

Ship with M90's two-piece rule: the κ term into `predicted_sigma` is free (zero
selection decisions moved); any gain correction touches n_eff (0.38–14.72%) and lands
behind its own freeze. Warp residual is the confound to commission against: the planted
control is a pair of synthetically re-gained, re-warped copies of one frame, which must
return the model σ within [bar]%.

**Acceptance:** recovers M90's independent g within its CI on the reference body,
per-stack, from subject frames alone; disagreement with the profile beyond [bar] prints
in the banner and widens the gates — never silently.

### B2. The censored-sample merge — clipped values are inequalities

**The physics.** Defocus conserves flux (measured — the photometric work leans on it),
so a specular highlight that pins the sensor in its in-focus frames is spread below
clip in defocused frames. The census machinery already sees this: only **21.02% of
ever-pinned sensels are pinned in every frame** (ARCHITECTURE §6) — for the other 79%,
the stack itself contains unclipped measurements of the same scene point. Today those
pixels' merges either ingest the pinned lie or roll it off cosmetically, and the
measured consequence is the foam defect class: green pins first (ceiling 38921 vs blue
52239 in the rendered master), B/G climbs monotonically across all nine level deciles,
and every blown specular on any subject inherits a one-sided colour rim (README).

**The design.** In the admission merge, a sample at the container maximum enters the
per-pixel estimate as a **censored observation** — a lower-bound likelihood term, not a
value. The per-pixel MLE under Gaussian noise with censoring is a few Newton steps over
a handful of samples, run only on the ever-pinned set (a few percent of pixels; zero
cost and **byte-identical output elsewhere, asserted by hash** in the A-series freeze
style). Where all admitted samples are censored, fall back to today's roll-off and say
so in the confidence vector ("censored" is a fourth channel). This uses defocused
frames *legally* — no deconvolution, no invented values above measured flux — and it is
the estimator thesis extended to the one sample class the thesis currently ignores. It
composes with, not against, M30's finding that highlight rescue by exposure needs
−2 EV: that is the capture-side complement, and the planner (D3) owns it. C9's
polarisation channel, if the owner opens it, attacks the same speculars upstream.

**Novelty note (ARGUED, `could not confirm`):** I know of no stacker or burst-merge
pipeline that treats clipped RAW samples as censored data in a per-pixel estimator;
B §3/§8 record nothing of the kind. Phase-0 literature pass owed, per §2.3's caution.

**Acceptance:** on `foam`, the B/G-vs-level monotone climb flattens toward the optical
expectation with the flat-region placebo unmoved; the §25 deliberately-clipped capture
gives the controlled version. Kill: any change off the ever-pinned set, or any
reconstructed value exceeding the flux bound of its own defocused evidence.

### B3. Photometric normalisation via the law it measurably obeys

The flux ramp is mostly not drift — it is magnification: `ln flux = −2 ln scale`, no
free parameter, RMS down up to 5.06×, permutation p = 0.0025 (README). So the default
correction on the unified merge is **deterministic**, from the alignment scale the
merge already holds, with a *fitted* residual gain only where it clears a bar —
`foam`'s genuine 0.32 stops / 8 frames is the one corpus subject that needs it. The
estimator's measured rule carries over: the gain drags the noise model with it (σ
scales by c, not √c). This removes the "NOT YET IMPLEMENTED on this backend" refusal
without importing the estimator's two-pass photometric machinery wholesale.

### B4. `SELECTION_INFLATION` dissolved structurally

Fact 341 is open because the penalty term for degenerating to selection was refuted at
1.074×. The admission merge makes the question nearly moot before it answers it: under
a soft/admission kernel the n_eff ≤ 1 population collapses 3.936% → 0.023% (facts
1917–1920), and under A5 the population that *elects* at all shrinks further. Land A1,
then measure the residual term on the pixels that remain selectors; if it is
second-order there, close 341 by measurement rather than by constant.

### B5. NEW — the sensor-state ledger: the bracket as a time series

A 299-frame bracket spans minutes; the sensor and the light are not stationary across
it, and the corpus keeps meeting the consequences one at a time: flux ramps (M24,
8.2–36.9%), the foam exposure excursion, EXIF that does not predict level (R9), warm-up
drift in dark current the 1/100 s darks cannot speak to (fact 808). Rather than one fix
per symptom, estimate a small per-frame state vector — black-level offset, gain, flux
scale, and (from C4) warp residual summary — as a **joint smooth-in-time fit** across
the stack, with the breathing law (B3) as its deterministic backbone and B1's PTC as
its noise scale. Row-noise/banding common-mode estimation in deep shadow slots in here
if measured to matter (this body's read floor at second base is 1.24 e⁻, so the prior
is that it does not — measure once, then keep or close). This is glue, not a new
estimator: each component above is already proposed or shipped; the ledger makes them
share one temporal prior and one report, and it is what makes the banner able to say
"frame 212 is 0.3 stops off-model and was down-weighted" instead of nothing.

---

## 6. Workstream C — the physics exploits

### C6.0 The information ledger — why this list has these members

A SOTA proposal that says "novel physics" owes an argument that the list is complete
rather than merely long. The capture is: a static scene, a fixed rig, one aperture, one
exposure, N focus positions, RAW CFA samples. Every independent axis of that data cube,
and what reads it:

| Channel | Physical content | Exploited by |
| --- | --- | --- |
| Focus axis z | depth, through-focus response shape | A5, C2, C3, C5 |
| Spatial sampling phase under breathing/jitter | aliased super-Nyquist structure | C1 |
| Wavelength (CFA) | longitudinal CA = 3 offset z-sweeps; per-λ diffraction cutoff | C2, C1's kernel |
| Orientation | astigmatism/coma anisotropy of the PSF | C7 |
| Amplitude statistics | photon-transfer self-calibration; censored samples at clip | B1, B2 |
| Fixed pattern vs sliding scene | PRNU/dust/hot in situ (breathing = dither) | C6 |
| Depth-dependent geometry | axial pupil parallax; magnification vs depth | C4b, C5 |
| Time within bracket | sensor/illumination state drift | B5 |
| Illumination (capture-side, controllable) | texture where the scene has none; specular/diffuse split | C8, C9, D3 |

Channels examined and left unexploited on purpose: absolute phase/coherence (no
interferometer; speckle statistics under C8 are the accessible shadow of it), exposure
diversity (M30: allocation is neutral at fixed light; the planner owns the −2 EV
highlight arm), and polarisation *without* capture change (the CPL is fixed within a
bracket — C9 is the capture change that opens it). If a reader can name a tenth
channel, it belongs in this table with an owner or a reason.

### C1. Sample-level fusion — the merge consumes photosites

**The claim (ARGUED):** the single largest un-refuted quality lever in this project is
to stop feeding the merge *resampled estimates* and start feeding it *the sensor's
actual samples*, each carrying its exact warped position, channel and σ — one estimator
that subsumes demosaic, warp resampling, merge, and (at a finer output lattice)
super-resolution. This is the logical completion of the project's two oldest
commitments — estimation-not-selection, and gather-at-consumption — and §2.4 is now the
sharpest argument for it: **the tree currently ships one of two wrong reconstructions
and documents the other**, because reconstruction is being decided per-frame, blind,
before the estimator sees anything.

**Why the current path leaves information on the table, from the tree's own
measurements:**

- The shipping fold runs a **full Malvar demosaic of every frame inside the warp**
  (§2.4): 299 demosaics per stack, 503 MiB transient per warp, measured fold peak
  12.5–13.4 GiB against a 5.2 GB printed plan — and, the material part,
  **interpolated values enter the election and the merge**. The alternative arm
  band-limits every phase to 0.25 cyc/output px before election and reads inverted
  structure (−0.4965 correlation) at 0.35 (`align_cmd.rs:1160–1215`).
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
  The corpus wrote the specification and then shipped the opposite for expediency —
  twice, §2.4 shows, in opposite directions.

**The design.** Per output pixel on an arbitrary lattice (1× default, 2× SR mode):
gather every source photosite of the wanted channel within a small radius of its
inverse-warped position — real `u16` samples, black-subtracted, WB-gained, never
interpolated — and estimate:

```
value(p, c) = Σ_i  a_i · K(Δx_i; Σ_local) · v_i / σ_i²   /   Σ_i  a_i · K · 1/σ_i²
```

where `a_i` is the admission weight from the focus gate (A1/A5's machinery, evaluated
at the band scale of the lattice), `K` an anisotropic kernel steered by the local
structure tensor (the Wronski construction — VERIFIED in B §8 to beat SOTA demosaicers
by >3 dB *and* beat merge-then-demosaic), and `σ_i` the injected model per sample.
Green arrives quincunx (2× diagonal density per frame); R/B arrive at quarter density
and are completed across frames. **Per-λ refinement (new):** the kernel's target
bandwidth should follow the channel's physical cutoff — diffraction scales as 1/λ, so
blue carries the finest transmissible structure and red the coarsest; a per-channel
bandwidth cap from the measured optics is one constant per channel and prevents the
kernel from chasing alias energy past red's physical limit. Where sample count or
phase diversity is poor the kernel widens and the estimator degenerates to exactly
today's behaviour — degradation is continuous and *reportable per pixel*
(`phase_coverage` and `sr_contributing_frames` as honest outputs, per B §6.5).

**The identifiability condition, stated so the census can gate it (DERIVED).** Alias
unfolding is a small linear system per frequency neighbourhood: replicas at f ± k·f_s
enter frame i with phase e^{j2π k f_s φ_i}, so recovery needs the matrix of those
phases across contributing frames to be well-conditioned — which is precisely a
statement about the *spread of sub-pixel phases φ_i* among within-DOF frames.
M-PHASE0-PHASE therefore reports not just coverage but the condition-number
distribution by field radius; SR mode refuses per pixel where it is poor, in the house
style.

**Feasibility, DERIVED from corpus numbers.** Adjacent-frame breathing step ≈ 1.012% /
32 ≈ 0.032% (F §6, one stack; deep stacks larger). Per-adjacent-frame shift at radius
r is r·3.2e-4: ≈1.35 px at the corner, 0.32 px at r = 1000, 0.10 px at r = 300. Frames
within DOF at the recommended step: k ≈ 1.3–1.5, but the corpus shoots 2–4× denser
(M27) and the seven new stacks at step 1/5/7 denser still — call it 3–6 sharp frames
per site. So the within-DOF phase sweep is ≈1.6 px at r = 1000 with five sharp frames
(good diversity), ≈0.5 px at r = 300 (marginal), and a **central dead zone** below
r ≈ 150–300 px where breathing alone contributes nothing — B §6.3 predicted exactly
this. Two additional diversity sources close it: the measured track jitter (median
second-difference 0.48 px, 13.8% of adjacent pairs ≥ 1 px — M110; if it is real rig
motion it is free dither everywhere, and note this is the resolution of the fact-#9
"jitter too small" apparent contradiction — random jitter is small, breathing offsets
are deterministic and grow with radius), and — a deliberately requested capture — **one
bracket with IBIS left ON on the tripod**, which turns the stabiliser's slow wander
into designed sub-pixel dither. That request costs the owner one bracket and would be,
to my knowledge (ARGUED, `could not confirm`), the first deliberate use of a
stabiliser as a super-resolution dither source in stacking.

**The registration wall, named.** 2× reconstruction needs *relative* registration of
the contributing samples good to ~0.1–0.15 px. The global similarity's held-out corner
error spans 0.353–11.562 px across stacks — but that is the end-to-end gauge; the merge
consumes per-frame placement (M103), and SR consumes something smaller still:
**relative placement among the 3–6 within-DOF frames**, which are content-matched (the
correlation problem alignment finds hard — cross-focus appearance change — is absent
between them). That is the easiest sub-problem in the whole alignment space, and C4's
local refinement owns it. Where the per-window registration confidence fails its bar,
that pixel's lattice contribution degrades to 1× — refusal per pixel.

**What it buys at 1× before any SR claim:** no invented values in the election or the
merge, one reconstruction instead of 299, the 503 MiB/warp transient and its
2 GiB-at-four-workers gone (memory goes *down*), no second resampling loss, §2.4's
contradiction dissolved rather than adjudicated, and the interpolation-kernel dispute
(M118/M113/ORCH-kernel-decision) retired — there is no resampling kernel, only a
reconstruction kernel whose bandwidth the estimator chooses locally.

**What it buys at 2×:** alias-unfolded R/B at full resolution (the honest,
physics-backed form of "beyond the demosaic"), and genuine super-Nyquist recovery in
the mid-to-outer field at f/5.6 where M88 says the optics deliver it. This is the only
route to "resolve beyond the sharpest captured frame *as rendered*" that no corpus
refutation touches: M115 killed reweighting *within* a band across focus; sample fusion
recovers *sampling* diversity within the sharp set, which is orthogonal. State the
boundary honestly: it cannot exceed the optical cutoff, and at f/11 (knee 0.2762
cyc/px, M5) the 2× lattice buys only alias margin, not new signal.

**Acceptance / kill bars (pre-registered against D1's instruments):** FRC gain over the
current default on the §33 subject and the §30 chart; demosaic-artifact disappearance
on a zone-plate/fine-check target (false-colour moiré must *decrease* — a signature
interpolation cannot fake); the M115 split-half SNR instrument re-run on the
sample-fusion arm (R_SNR must exceed 1 where phase coverage is reported high, and must
not fall below 1 anywhere); hull discipline per contributing sample set; noise at
matched band ≤ current default; the fullres-gather ringing statistic that dissented
(`align_cmd.rs:1197–1205`) re-run and required not to worsen. Kill: if within-DOF
relative registration cannot reach [bar] px on real stacks (measured first, cheaply,
from existing warpmaps + one local refinement prototype — the phase/conditioning census
is a corpus-only computation requiring zero new captures).

### C2. Chromatic z-diversity — the bracket is three focus sweeps

Longitudinal CA offsets the R/G/B focus planes, so one bracket carries three z-offset
sweeps of the scene (B §7.4; physical signal VERIFIED via Trouvé 2013, Chang &
Wetzstein; no per-channel focus-stack prior work found, §7.2 — subject to the fact-1136
search-quality caveat). The default merge shares green's election across all four
planes (ARCHITECTURE §5a) — so today, R and B are gathered from frames green chose,
and any longitudinal CA renders R/B *systematically slightly defocused* plus fringed at
defocused edges.

**Step 1 is a corpus-only measurement, and it is decisive either way:** per-channel
through-focus peak offsets δ_R, δ_B in frame-index units, at several field radii, on
two or three subjects, using M33's log-domain parabola (which resolves sub-step
offsets). The lens is a modern apo-corrected macro behind a 2× TC — B §7.4's own caveat
says the offset may be sub-step, and the TC may equally magnify it.

**If δ clears the bar:** per-channel election offset (elect on green exactly as today;
gather R/B at index + δ(field)) — a one-line change in gather indexing worth whatever
the measurement says; defringing becomes a lookup instead of an inference; and — new in
this revision — the three per-channel peaks are **three interleaved samplings of the
same surface at known z-offsets**, which both triples the effective z-sampling density
of A5's data term and hands C5 a per-pixel LCA measurement (the spread), a capability
no stacker has. **If it does not:** close it as a measured null the way M17 closed the
dual-response — the corpus gains the number either way.

### C3. Two-layer occlusion estimation — the veil's principled completion

A2 fixes the *pedestal*; the boundary itself still mixes two surfaces. The corpus has
every ingredient for the real model: bimodality enrichment 4.38× at r = 2, gated on the
calibrated noise floor (M21); the veil's convex-combination direction and the pmax
bound (ARCHITECTURE §5b — the shipped veil estimator is the degenerate one-sided case
of a two-layer fit); election coherence for eligibility; the M25 twin for ground truth
(its pre-registered gates already include a physically-veiled two-layer scene); and now
the first clean occlusion subjects — `duck-tape-side-layers-cpl` (thin dark fibres over
textured ground, STATUS §4) and `chia-seeds-cpl`'s crevice haze. Under A5 the routing
is natural: pixels the surface solve flags as bimodal/incoherent are exactly the
two-layer candidates.

**Design:** at pixels flagged bimodal *and* boundary-coherent, fit
`v_i = α·F(z_i) + (1−α)·B` across the through-focus curve — F constrained by the near
layer's admitted frames, B by the far layer's, α by the transition shape. Everything
ramps, nothing vetoes (the edgeaware lesson). Fact 412's cheap remedy (split the patch
by local edge orientation, Wang et al. 2015) must be tried first as the confound
control, per R25's disposition. Outputs: the corrected backdrop *and the α matte as a
product artifact* — subject cut-outs from physics, not segmentation. Prior-art posture
per M19: Asada et al. 1995 formulated the model; the claim is **first shipping stacker
to invert it**, and even that keeps the `could not confirm` label.

**Acceptance:** twin two-layer gate; chia-seeds crevices; wing/eye blotch guard (the
failure that motivated the veil floor must stay green); no motion on the 17 conditioned
aura readings' direction.

### C4. Local warp refinement — a residual layer, not a new model

Two consumers need better *local, relative* placement: C1's within-DOF sample fusion,
and the ordinary merge, whose real input is per-frame placement (M103: end-to-end and
per-frame error are nearly independent; the 50× headline improvement bought nothing
where it counts). The global similarity stays — never chained, exactly as rule 6
demands. Added:

**(a)** a smooth low-order residual field per frame, splined from the solver's own tile
displacements (which the solve currently collapses to four parameters and discards),
bounded in amplitude, refused where tiles are blind — this is *not* optical flow and
adds ~tens of parameters per frame, not per pixel;

**(b)** for C1 only, per-tile relative refinement within the in-DOF window, where
content is matched and ZNCC parabola precision is at its best;

**(c) NEW — the depth-dependent magnification term, and it is the one physical term a
similarity cannot carry.** A similarity fits one scale per frame. But magnification is
a property of a *plane*: if the entrance pupil translates axially as the lens focuses
(common in internal-focus designs, plausibly amplified by the TC), every object scales
by its own depth — radial parallax proportional to (1/z_obj − 1/z_focus). The rig
treats in-camera bracketing as parallax-free by assumption ("occlusion never changes",
ARCHITECTURE §7); physically it is only *approximately* free, and three unexplained
corpus observations are exactly what a depth-scale term would produce: the held-out
error spanning **33× across stacks** (0.353–11.562 px — deep close-up stacks worst),
shrinkage magnitude being "a property of the scene, not of the optics" with no
edge-set predictor (rule 6's own words), and the scale centre sitting ~400 px off the
image centre (F §7). **M-PHASE0-DPAR settles it from existing artifacts, zero
captures:** regress per-tile similarity residuals against the elected depth index per
tile across a deep stack; a nonzero slope is the term, and its sign and size calibrate
one added parameter per frame (scale linear in z). If present it also *is* an absolute
depth cue — pupil-baseline parallax, a second ruler for C5, independent of the
breathing ruler. If absent, the assumption "similarity suffices" graduates from
assumption to measurement.

Blur-equalisation (R5) remains the queued upgrade for cross-focus edges, and any
experiment on it must run M23's zero-defocus self-pair control first. Track jitter gets
re-examined here too: M110's 0.48 px is either signal (real rig motion — free dither
for C1) or noise (solve error — the enemy); the refinement decides which, per stack.
Risk 4 (sub-pixel misalignment reads as a focus difference downstream) makes this
workstream a quality item even if C1 never lands.

**Acceptance:** held-out per-frame gauge (M103's) improves on the deep stacks;
planted-similarity nulls return identity; the 33× held-out spread narrows or its cause
gets named (possibly by (c) alone).

### C5. Metric depth, and the products that fall out of it

R21 sits queued: the fitted per-frame `log a` ladder plus measured m (M84b) and B (M5)
is a **metric ruler** — frame index → focus distance in micrometres — needing no lens
database, on a rig where the EXIF focus axis is useless (F §5: two distinct values
across a 33-frame stack; one LSB ≈ 22× the depth of field). A5 supplies z(x,y) ± σ_z
in frame-index units; this item converts the axis. Cross-checks now number three:
fact 54's pixel-measured focus index, C2's chromatic spread, and C4c's parallax ruler
if M-PHASE0-DPAR finds one. Products, in increasing ambition: depth + uncertainty TIFF
(no stacker emits this); surface normals from its gradient; the reshoot advisor
upgraded to physical units ("bracket ended 0.8 mm short of the far edge — 11 more
frames at your current step"); and **synthetic aperture re-rendering** — with depth,
per-frame admission, and actual captured defocus in hand, re-render the stack at any
focal plane and any simulated stop between "one frame" and "all-in-focus", by
depth-consistent blending of *captured* frames (selection with physics, no invented
values — the hull discipline extends naturally). A focus stacker whose output is not
one image but a refocusable object is a different product category, and every
ingredient is already in the tree.

### C6. In-situ sensor self-calibration — breathing as the dither

**The observation (ARGUED):** breathing slides the scene under the fixed pattern by up
to hundreds of plane px while the pattern stays put — the geometry astronomers create
deliberately by dithering. Per photosite, regressing its residual against the warped
consensus across N frames estimates its gain (PRNU, dust) and offset (DSNU, hot) *at
the working exposure, ISO and aperture* — the exact regime where the delivered darks
are wrong (fact 808: 1/100 s darks vs 1/8–5/2 s working exposures) and where dust depth
is aperture-dependent (V-MOTE: −2.94% on flats vs −3.4 to −5.7% on masters).

**Respecting M29, which killed the naive version:** M29 refuted *shadow detection at
merge time* — the floor was scene texture at n_eff ≈ 3, because the merge averages
adjacent frames that agree. This estimator is different in kind: longitudinal, per
photosite, across the *whole* stack, with the scene term supplied by the consensus
rather than assumed smooth. It may still die on the same sword — scene texture leaking
through warp error — so the kill bar is set before the build: it must recover both
known real motes (−3.63%, −8.24%) and the flat-derived dust field on subjects with
≥[bar] px of drift, at FPR < [bar] on the M25 twin with zero planted defects. Flats
remain the gold standard; this is the zero-capture fallback, the working-exposure hot
map M22 could not deliver, and a drift tracker for a map that ages. (Meanwhile the
*shipped* dust arm is built, tested, and OFF with two real motes in every delivered
master — STATUS §1 recommends defaulting it ON after the cache-key question; that is an
ops decision upstream of this item and should not wait for it.)

### C7. NEW — orientation-resolved election: astigmatism is a focus split, and no stacker looks

**The physics.** Off-axis aberrations — astigmatism above all — put the sagittal and
tangential foci at *different depths*: horizontal and vertical detail at the same field
point peak at different frame indices. The corpus's own §29 correction names
astigmatism among the candidates for the measured **2.2× non-diffraction blur**, and
the rig's TC is the leading suspect for aberration amplification. Every stacker,
strehl included, elects with an orientation-blind scalar (Tenengrad sums Gx² + Gy²), so
on an astigmatic field the elected frame is the compromise focus — *neither* axis at
its best — and the loss is invisible to any orientation-blind sharpness metric
afterwards. The corpus already owns the machinery to see it: the Sobel response is
computed from Gx and Gy separately before summing, and fact 412's
edge-orientation-split is sitting in the disposition table waiting for a second
consumer.

**Step 1 is a corpus-only measurement (M-PHASE0-ASTIG), decisive either way:** split
the through-focus response into Gx² and Gy² arms, fit each with M33's log-parabola, and
map δ_astig(r, θ) = ẑ_tangential − ẑ_sagittal across field annuli on two or three
subjects (the §30 chart, when it lands, gives the clean version; natural edges binned
by orientation give the first pass). If δ is sub-step everywhere, close it as a null —
one lane, no captures, and the 2.2× suspect list shortens by one.

**If it clears the bar:** three escalating exploits, each independently shippable —
(i) *report it*: the certified-acuity map (D2) becomes orientation-aware, which is
honest output no tool has; (ii) *admit through it*: widen A1/A5's admission along the z
interval spanned by the two axes, so the average includes each axis's best frames
(cheap, convex, hull-safe); (iii) *elect through it*: split the two finest pyramid
bands by orientation (steerable pair or plain Gx/Gy energies) and elect per
orientation, recombining per band — the anisotropic completion of the exponent ladder.
Kill bars: (iii) must show FRC gain on oriented structure (the §30 chart's two edge
orientations are the built-in test) with the flat-ROI control unmoved, else stop at
(ii). Novelty posture: focus-measure anisotropy is studied in shape-from-focus
literature; *election exploiting astigmatic focus split in a shipping stacker* gets the
`could not confirm` label pending the item's own search.

### C8. NEW — active texture: one bracket of projected light, election where the scene has none

The external review proposed structured illumination (R18) and the triage parked it —
"genuinely novel; out of scope for v1; needs hardware." Three things have changed since:
the corpus now contains a subject class that *fails by texture* (`medication-pill-cpl` —
"individual powder grains on a near-white low-contrast tablet, which is the focus
measure's hardest case", STATUS §4; band qualification fails on most subjects for want
of contrast, STATUS §3.2.9), the election machinery is about to be rebuilt anyway
(A1/A5), and the hardware costs less than the Zerene licence this proposal already
asks for.

**Protocol (ARGUED):** shoot each subject twice on the fixed rig — the normal bracket,
then an identical bracket with a cheap projected texture (laser-speckle emitter or
pico-projector gobo; nothing calibrated). **Elect and solve depth on the textured
bracket; render values only from the clean bracket.** The two brackets share the rig
and the subject, so cross-bracket registration is the easy kind (same scene, one of
the two arms saturated with texture — ZNCC's best case). Projected speckle gives the
focus measure contrast *everywhere*, including optically-flat ground where election
currently chases noise; defocus of the *projection* adds a second, independent depth
cue (projected-texture contrast falls with defocus twice — illumination and imaging —
which sharpens the through-focus peak). This turns A5's worst-case subjects into its
best-case ones.

**Kill bars:** on a textured subject shot both ways, speckle-elected z must agree with
self-elected z within σ_z (else the projection is moving the answer, not informing
it); cross-bracket registration must clear the same bar as intra-bracket; any
rendered-value contribution from the textured bracket is a defect by construction
(hash-assert the render reads clean frames only). Prior art: active illumination for
depth is classic (structured light, speckle DfD); *a consumer stacker with a
texture-pass capture mode* gets `could not confirm` pending search. Deliberately
opt-in, capture-side, and last in the C queue — but it is the only item in this file
that helps the subjects the focus measure is *physically blind* on, and no software
item can.

### C9. NEW — polarisation diversity: the filter is already on the lens

Every `-cpl` subject was shot through a circular polariser at a fixed rotation. One
extra bracket at ~90° rotation makes speculars separable (Wolff/Nayar-classic physics:
the diffuse component is polarisation-stable, the specular component is not), which
attacks B2's censored-pixel class *upstream* — a specular that clips at one CPL angle
is often unclipped at the other — and yields a gloss map as a product artifact.
Everything B2 says about legality applies: per-pixel min/blend across the two brackets
is convex in measured values, no inversion, hull-safe. Kill bars mirror C8's
(cross-bracket registration; byte-identical output where the two brackets agree).
Cost to the owner: one rotation of a filter already owned, per subject that needs it.
`could not confirm` any stacker doing this; it is one search plus one capture away
from being either a null or a first.

---

## 7. Workstream D — the instrument and the product

### D1. The scorecard, built once, first

Everything §1 defined, plus the build-order discipline: **instruments before
features.** The FRC spine (R25(iv): cannot be fooled upward by noise amplification);
the split-half SNR channel (M115's §2 design, the best-commissioned instrument in the
corpus — reuse it verbatim); the slanted-edge SFR estimator that already exists
validated to 114.6 cy/mm (M88 §2) pointed, at last, at something sharp (§30 chart);
planted-defect commissioning for every axis (the blur-plant detector already proved
potent at 0.3–0.4 px — README); the V-RIM specificity lesson baked in as a rule (an
instrument that convicts a raw camera frame convicts nothing); SSIMULACRA2/butteraugli
for the perceptual axis (never dssim — licence). Comparators pinned and priced:
licensed Zerene (PMax *and* DMap — DMap has never rendered here and is A5's true
comparator), the fork rebuilt at its best-known build (2.4× is the honest speed quote
against it), Helicon if obtainable. Every scorecard run archives hashes and sidecars
under the banked-purge discipline so no result ever becomes unreproducible the way
V-RIM's 5-of-14 did.

**New sub-instrument — the bootstrap MTF from the corpus's own edges.** M88's verdict
was "nothing sharp enough to point at"; the §30 chart fixes that properly. But the
stack itself contains a partial substitute available *now*: every strong edge's
through-focus sequence of edge-spread functions is an empirical defocus family, and
its envelope at best focus is the system ESF at that field point — width-limited (the
corpus's edges are 13–18 px against the instrument's 5.13 px validity bound), so it
cannot answer the comparator question, but it *can* map relative MTF across the field,
feed C7's orientation split, and give D4 a provisional H. Commission it against the
§30 chart the day the chart lands; if they disagree beyond [bar], the bootstrap dies
and the chart stands alone.

### D2. The certified-acuity map — "which file am I holding"

README names the gap: the tool hands over a print-worthy file or a soft one and does
not say which. The unified merge knows, per pixel and per band, whether the admitted
set cleared the calibrated floor. **Formal spine (DERIVED, to be commissioned like any
instrument):** per pixel and band, the admitted set's Fisher information is
I = Σ 1/σ_i² (inverse-variance weights make this exact under the model), so the merge
carries a per-band CRLB σ_cert = 1/√I; the **certified acuity** is the highest band
whose reconstructed signal clears [bar]·σ_cert. Collapse to: per pixel, an acuity in
cyc/px (orientation-resolved if C7 lands); per image, the field-coverage summary
README says is the honest form of the quality claim (fraction of field certified at
≥ band k). This is the instrument-grade output that separates "retouch this" from
"reshoot this" from "print this", it costs no new measurement machinery beyond A1/A4,
and no shipping stacker has anything like it. It becomes the print gate's input,
replacing the broken clip/crush statistics called out in STATUS §3.2.14, and ships in
the file: the render's manifest (already carrying build id, ICC, develop statement —
ARCHITECTURE §9) gains the acuity summary and the per-axis scorecard verdicts, so the
claim travels with the artifact.

### D3. The capture planner — the other half of the instrument

The corpus keeps proving capture dominates software: f/11 → f/5.6 was 13.5× on
matched-filter SNR (M20 §4.4, R15) — though §29's correction stands: "open up" as
standing advice is withdrawn until the aperture ladder exists, because a large
aberration term argues the *other* way; the 2× TC is the leading suspect for the
entire 2.2× non-diffraction blur (§29 — if the TC-off capture confirms it, "remove
the TC, crop less" may outweigh every algorithm in this file); step density decides
the estimation premium (M27; the step-1/5/7 stacks are the ladder, rendered and
uninstrumented — STATUS §4). `strehl plan` folds the measured optics (m, B, cutoff),
the noise model, and M27's coverage criterion into: given magnification, aperture and
subject depth → step, N, predicted coverage, noise, and certified-acuity forecast;
afterwards the reshoot advisor closes the loop in millimetres (C5).

**New planner content, each one measured or derivable from the profile today:**
- **Second-base-ISO advice.** The body's read noise falls 4.20 e⁻ → 1.2392 e⁻ at the
  second base (profile, ARCHITECTURE §6; F §9) — for the dim long-exposure macro this
  corpus actually shoots, base-ISO choice is worth more than most algorithms, and the
  planner should print it.
- **Repeat-bracket and burst-per-step modes.** Photon count is the only free noise
  lever left once ETTR (§22) is taken; two identical brackets cost linear time and the
  merge already folds them (admission by z does not care which bracket a frame came
  from once A5 lands). The planner prices "2× bracket" against "wider gate" honestly.
- **Interleaved half-step passes** (R16's surviving half): a repair for a diagnosed
  coverage gap, never a default — M27's criterion is the diagnostic, and M30's fact 240
  (photon budget indifferent to the split) is why it is free.
- **The −2 EV highlight arm** (M30) triggered per stack from
  clipping-at-gathered-frames, which is the census B2 wires in.
- The standing capture asks it should nag for, by owner cost: grey card in frame
  (§20), ETTR (§22), static repeat burst (§12), aperture ladder + TC-off (§29), the
  §30/§32/§33 instrument set, ≥400 px clear-background subject (fact 1891), IBIS-ON
  bracket (C1), CPL-rotation pair (C9), darks at working exposure (§28).

### D4. Measured-PSF restoration — conditional, last, honestly bounded

M115 killed multi-frame deconvolution and the self-calibrated OTF; it did not kill
single-pass restoration under a *measured* system MTF — it never had one to test (M88).
And §29 sharpened the stakes in both directions: the system is ~2.2× softer than
diffraction (two instruments, 4%), so a real, optics-shaped blur budget exists that
only restoration can spend — and ≤76.6% of it being optical is an upper bound from one
printed target, so the budget's true size is unknown until the chart and the razor-
blade edge land. The existing `restore.rs` is the template of the honest shape: exact
H, noise-budgeted gain, no ringing because the calibrated noise stops it first. After
§30 (or provisionally after D1's bootstrap MTF): measure the composite MTF (optics ×
gather × merge — noting C1 at 1× deletes the gather term), extend H accordingly, keep
the same noise budget, gate on FRC and the split-half instrument, flag any pixel the
restore moves beyond its sample hull. Expectation management is part of the design:
the *information* is fixed; this stage trades the noise budget B1 certifies for
contrast, no more. If FRC shows no gain, it ships as the measured negative beside M115.

### D5. The performance budget

Quality features above must fit inside roughly 2× the current wall clock or they will
not ship as defaults. Known prices and offsets: the two-pass unified merge measured
~2.2× once (56.3 → 124.7 s at N=79, fact 1939 — one kernel, one N; re-price in lane);
A5's v0 solver is two DT-filter passes over one plane (cost ~one extra band, trivial);
C1 at 1× *removes* 299 Malvar demosaics and a 503 MiB/warp transient
(`align_cmd.rs:1794–1804` — sign: faster and smaller, to be measured; note the flip
itself measured *faster* against a +549 ms/frame prediction, so priced predictions on
this fold have been wrong before in both directions); SIMD is untouched headroom on a
fold that is 98.5% of the run (zero `std::simd`/intrinsics in 93 kLOC — ARCHITECTURE
§11); GPU stays optional and non-contending (M7: 173× on a stage worth 0.40–0.57% of
wall; a separate crate per STATUS §3.3.11); the memory planner must start pricing the
fullres transient it currently understates (12.5–13.4 GiB measured against a 5.2 GB
printed plan — same file) for as long as that path ships. Determinism rules stand:
worker counts stay memory-derived on the default path; every reduction-order change is
a freeze event; the byte-freeze registry now has a pyramid row (fact 1982) and needs
its **aligned** pyramid sibling before phase 1 touches the warp path.

### D6. The plugin surface, resolved by A1/A5 rather than by more traits

Today the only real seam (focus measures) is refused on the default backend — "the
plugin surface and the shipping path do not intersect" (ARCHITECTURE §8). The unified
merge decides this properly: pass one (election/depth) consumes a focus field again, so
the calibrated `FocusMeasure` seam becomes live on the default path for free — and A5
gives plugins a sharper contract (respond + curvature ⇒ ẑ, σ_z) that the registry's
existing calibration machinery already knows how to certify. Alignment models, optical
profiles and output stages stay data-plus-enum until a second consumer exists —
SYNTHESIS §9's rule against pre-building seams has been right every time it was tested.

### D7. Colour and print polish

Landed and cheap to keep: ICC + 300 DPI in the deliverable (fact 1916); the print gate
now closes 33/33 with 0 FAIL and 0 unresolved (facts 1966–1968), so this workstream is
maintenance plus two decisions: the owner's paper profile (§31 — outranks any code
change for print) with a soft-proof gamut census against it, and the
per-channel-vs-per-luminance tone decision STATUS §3.2.14 says nobody has authorised —
take it to a decision memo with the print gate's numbers attached. The dust-ON default
(STATUS §1's recommendation, pending the cache-key resolution) belongs in the same
decision memo: every delivered master currently carries both motes.

---

## 8. What this proposal deliberately does not contain

Respecting the graveyard is half of what the corpus is for. Each row names the one
condition that would reopen it; absent that condition, re-proposing these is noise.

| Killed idea | Killed by | Reopens only if |
| --- | --- | --- |
| Multi-frame Wiener / matched filter across focus as the merge | M20, M70, M115 — three instruments, one answer (R_SNR 1.0014 [0.965, 1.038]) | A future merge stops harvesting off-peak frames (it will not — A1/A5 harvest more) |
| OTF self-calibration from through-focus curves | M115 (separately refuted) | Never for deconvolution; D4 uses a *measured* PSF instead |
| **Sub-step "peak completion" — extrapolating the through-focus curve to its unsampled maximum** (new row; considered and declined in this revision) | M70's rank-1 structure (0.9959) says the z-axis carries almost no independent band information to extrapolate with; M33 prices the loss (median 4.64% of response); M115's hull census shows what extrapolation does | A measured, field-dependent defocus family from the §30 chart changes the rank-1 premise — re-derive before proposing |
| Outlier / robustness rejection at merge time | Refused **five** times; M123 fired on 29.55% of a stationary subject; a second mechanism 21.5× more active on the unmoving stack | A detector with pre-registered FPR commissioned on the §12 static repeat burst — and only behind the reshoot verdict |
| Confidence as a scalar (entropy or otherwise) | M32, M34 — no monotone scalar is faithful | Nothing. Ship the vector |
| The significance exponent as the flat-region fix | Facts 1974–1975 — benefit saturates by z=100, cost does not; own prediction falsified | Nothing. A1 supersedes the question |
| Alignment shrinkage correction | M12 — 0/18 transfer, worst case 83.4× worse | Nothing |
| Metacalibrated edges | M23 — the "response" was the probe's own resampler | Nothing; R5 blur-equalisation is the surviving heir, behind its self-pair control |
| Adaptive `--target-n-eff` rule | M64 (refuted on M52's own numbers) | A1's calibrated admission width supersedes the question |
| Chained alignment, in any disguise | Rule 6, M10, M103 | Nothing. C4 adds residual layers to the *global* solve |
| Post-hoc smoothing of the winner/index field as a cosmetic filter | M120's lesson (winner fields shatter where no answer exists); the edgeaware guide finding (a haloed field cannot guide itself) | Nothing — A5 is the joint-estimation form and is the only depth-smoothing this file proposes |
| Per-frame demosaic quality as a battleground | M104b, M118, ORCH-kernel-decision — kernel datasheets, not photograph facts; §2.4 shows the ground itself is unstable | C1 dissolves the question rather than answering it |
| Deep MFIF / learned fusion on the default path | Risk 3 (domain: 2-image, low-res, synthetic) | Only ever twin-trained (R24's covenant), only ever opt-in — the A5 ordinal prior included |

---

## 9. Sequencing

Ordered so that every expensive build is preceded by a cheap measurement that can kill
it, and every claim-bearing phase lands after its instrument. Lane names follow house
convention. Zero-capture phase-0 measurements are deliberately front-loaded: **six of
the eight new items in this revision can be killed or confirmed without the owner
lifting a camera.**

**Phase 0 — measurements and purchases (corpus-only + one capture session).**

*Owner (one session covers all of it; captures-needed "START HERE" already orders
most):* the §30 chart + §32 export; §33 sharp subject; §29 aperture ladder (f/5.6, f/8,
f/11) and TC-off bracket; §12 static repeat burst; §26 bright-on-dark subject and the
≥400 px clear-background subject (fact 1891); darks at working exposure (§28); one
IBIS-ON bracket (C1); one CPL-rotation pair on a specular subject (C9); §24 spectral
flats if the session has room. *Owner (purchase):* the Zerene licence — D1 is blocked
on it and A5's true comparator (DMap) has never rendered here.

*Corpus-only lanes, no captures:*
- **M-PHASE0-ZFIELD** — ẑ curvature / σ_z / coherence census from existing estimator
  statistics (A5's go/no-go).
- **M-PHASE0-LCA** — per-channel through-focus peak offsets on 2–3 stacks (C2's
  go/no-go).
- **M-PHASE0-PHASE** — sub-pixel phase coverage *and conditioning* census from existing
  warpmaps, by field radius (C1's go/no-go).
- **M-PHASE0-ASTIG** — orientation-split through-focus peak offsets by field annulus
  (C7's go/no-go).
- **M-PHASE0-DPAR** — tile-residual-vs-elected-depth regression on the deep stacks
  (C4c's go/no-go; doubles as an alignment-systematics audit).
- **M-PHASE0-PTC** — B1 prototype on two stacks, scored against M90's independent g.
- **V-VEIL2** — re-run the §59.3 probe harness so A2 has its acceptance instrument
  before its build.
- **Literature passes** for every `could not confirm` in this file, at the depth
  fact 1136 demands (a survey that misses Pertuz/Schechner-grade prior art certifies
  nothing).

**Phase 1 — one merge (A1, A2, A4, B3, B4), behind the freeze.**
Entry: phase 0's veil instrument; the soft-gate patch as starting material;
width-matched calibration per facts 1917–1920; the aligned-pyramid byte-freeze row
(D5). Exit: the §1 scorecard v0 run end-to-end on the corpus — noise, hull,
halo-where-measurable, speed — plus per-band n_eff maps as shipped artifacts. The
gate-default question (2.0 vs 4.5) closes here as a calibration, not a constant. The
dust-ON and paper-profile decision memos (D7) land alongside, being independent of the
merge.

**Phase 2 — the election becomes estimation (A5 v0 behind the twin), estimation
finished (B1, B2, B5), D2 acuity map, D3 planner v1.**
Exit: A5 passes or dies on the twin's pre-registered gates; `Provenance::Measured` on
an unknown body's stack; foam's B/G climb flattened; the certified-acuity map shipping
by default; the planner speaking millimetres once C5's ruler lands (else frame
indices).

**Phase 3 — the fusion bet (C4 then C1), C2/C7 if phase 0 cleared them.**
C1 lands in two rungs: **1× lattice first** (demosaic-free merge — strictly a
correctness/efficiency win that also closes §2.4, no SR claim), then **2×** behind the
D1 instruments. Exit: FRC-scored, moiré-scored, split-half-scored verdicts on §30/§33;
either the first defensible resolution claim in the project's history, or a measured
negative with the phase/conditioning census explaining exactly why.

**Phase 4 — the frontier (C3, C5, C6, C8, C9, D4), and the product surface (D6, D7
residue).** Each independently killable; none load-bearing for the phases before it.

**Standing constraints across all phases:** D5's 2× wall-clock budget; byte-freeze
rows per backend maintained; author-never-verifies on every claim-bearing number;
every instrument commissioned for specificity as well as sensitivity (the V-RIM rule);
and the scorecard — not this document — is where "SOTA" gets decided.

---

## 10. Self-audit — where this proposal is most likely wrong

1. **The two-pass cost may bite harder than priced.** The 2.2× figure is one
   measurement at N=79 on a different kernel. If SIMD cannot buy it back, A1 needs a
   one-pass approximation (provisional winner + correction) and that approximation
   needs its own commissioning. This is the likeliest engineering wall in phase 1.
2. **A5 may be a solution in search of a regime.** If M-PHASE0-ZFIELD finds σ_z large
   at corpus step sizes outside regions A1 already handles, the surface solve adds
   machinery without moving pixels — which is why the census runs before any solver is
   written, and why A5's failure leaves A1 whole. The converse risk is subtler: a
   surface prior that *works* will look better on every smoothness-loving statistic
   even where it is wrong, so its acceptance leans on the twin and on planted
   discontinuities, not on corpus prettiness.
3. **C1's registration wall may be real.** The within-DOF-frames-are-easy argument is
   ARGUED, not measured; M110's 0.48 px jitter might be solve noise that local
   refinement inherits rather than fixes. That is exactly what M-PHASE0-PHASE and C4's
   planted nulls exist to find out before the big build.
4. **Per-coefficient admission could resurrect the patchwork in the band domain.** The
   pyramid's smoothed energies and the winner's spatial coherence argue not, but
   M120's lesson is that winner fields shatter where no correct answer exists —
   phase 1's acceptance includes a flat-ground plateau census for this reason.
5. **B2 touches the most dangerous pixels in the image.** Censored estimation on
   speculars must be byte-identical off the clip set and flux-bounded on it, or it
   becomes the invented-values defect wearing a likelihood. The hull axis on the
   scorecard is the tripwire.
6. **The novelty claims inherit their searches** (facts 1112/1136). Every `could not
   confirm` in this file is one adequate literature pass away from becoming "known
   since 1998", and the phase-0 passes exist to take that hit before a build does, not
   after.
7. **Scope.** This document proposes more than a team ships in a season — more in
   revision 2 than in revision 1. The phase gates are the control: each phase ends at
   a scorecard run, and any phase's negative result is a publishable stopping point,
   not a sunk cost. If only one thing survives triage, it should be **phase 1** — the
   thesis shipping by default is worth more than any single novel technique in this
   file — with **phase 0's capture session** alongside, because it is the only item
   here that no amount of software can substitute for.
