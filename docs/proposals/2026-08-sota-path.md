# strehl — the path to a defensible SOTA claim

**Status: PROPOSAL, revision 3 (2026-08-29).** Every claim here is ARGUED unless it
cites a measured report by name. Numbers I derived myself are labelled DERIVED with the
arithmetic shown; numbers transcribed from the corpus carry the report or file that owns
them. Per rule 12, nothing in this document should be believed — it should be falsified,
item by item, in the order §9 proposes. Per fact 1886, every corpus absolute quoted here
is a timestamp, not a constant: re-measure at point of use.

**Revision 3 — what changed and why.** Revision 2 was written earlier today. This
revision is the "sit with the physics" pass the commission asked for: a deeper read of
F (the rig model, in full), M70 §13–§14, M88, M115 in full, G-edof Q5–Q6, and B §6–§8,
looking for channels the first two revisions did not open. It found several, and one of
them was named by the corpus itself and then never picked up:

- **§3.0 (new) — the one model.** The workstreams now hang off a single written-down
  observation model. Every shipped stage and every proposed item is a named
  approximation to one likelihood, which makes the graveyard *derivable* rather than
  merely respected, and gives every future lane a place to say exactly which term it
  estimates.
- **C10 (new) — the phase channel.** M70 measured only *modulus* spectra; its rank-1
  refutation of matched filtering is a modulus result; and its own §14 names complex
  cross-spectra "the single highest-value unmeasured thing M70 touched" — twice, for
  two independent reasons. Nobody ever ran it. Phase carries sub-0.1 px registration,
  the *sign* of defocus, the pupil's aberration state (the measured 2.2× blur budget,
  decomposed), and a contrast-inversion guard. This is the largest genuinely new item
  in this revision.
- **C11 (new) — aperture diversity.** One extra bracket at a second aperture opens a
  channel with real physics on every axis this project fights on: classic two-aperture
  depth, smaller blur discs exactly where veiling lives, a per-frame PSF family
  calibration, and the pupil factor M88 §10 says the corpus cannot currently feed.
  Prior art named up front (Hasinoff & Kutulakos confocal stereo).
- **C12 (new) — the quincunx green pair.** G1 and G2 sample the scene half a quad
  apart. Their disagreement is a per-frame noise probe (B1 already uses it), and —
  unexploited anywhere — a *super-Nyquist alias detector and finest-scale focus cue*
  that needs no demosaic and no second frame.
- **C13 (new) — the vendor's own calibration payload.** Every ARW in the corpus
  carries Sony's 16-knot radial distortion table and 32-knot per-channel CA table for
  this exact lens+TC (F §6.1). The shipped CA model is one scalar per channel and is
  measured *net-beneficial and over-corrected at the same time* (fact 1865) — which is
  what a scalar fit to a radial profile looks like. The payload is a profile, sitting
  in every input file, unread.
- **B6 (new) — variance-stabilised gating**, F §2.3's own unshipped recommendation:
  one admission width that is correct at every signal level.
- **B7 (new) — the re-renderable master and the output noise floor**: sufficient
  statistics persisted so gate/width/exposure become post-fold decisions; float or
  dithered output where deep stacks push σ below the 16-bit LSB (with the arithmetic).
- **B5 (expanded) — the ledger gains the per-frame PSF-quality arm** (vibration/shock
  as *frame-level* state, carefully distinguished from the five-times-refused
  per-pixel outlier rejection), plus capture classifiers F already validated.
- **D8 (new) — split-stack self-calibration**: the M115 §2 split-half instrument and
  FRC, moved from "instrument we use in reports" to "mechanism the product runs per
  stack" — per-stack tuning of the admission width with an objective that cannot be
  fooled by noise amplification, and a per-tile *empirical* certified-resolution map
  beside D2's model-based one.
- **D9 (new) — determinism decoupled from worker count**: the 1.29× worker-cap cost
  and the GPU blockade both dissolve if the reduction lattice is fixed independent of
  workers (CPU) and integerised (GPU). Engineering, not research — and it unblocks D5.
- **D10 (new) — the live capture loop**: the fold is already streaming; pointed at a
  tethered camera it becomes "stop shooting, coverage is certified" *before* the rig
  is torn down. The reshoot advisor, moved to the only moment it can still act.
- **D11–D15 (new, added at the owner's follow-up on speed) — the speed program.**
  Speed is the axis strehl already leads, and the corpus's own numbers say the lead
  is nowhere near the floor: the fold is 98.5% of the run (BUILD-SPEED §2), the
  hardware envelope was priced in 2026-08-22's workstream D at **decode-bound,
  roughly 7–20 s for a 299-frame stack on this box against ~102–117 s today** —
  5–10× of measured headroom — and D's own FU1.3 names the one unmeasured number
  that decides the whole ordering (per-core LJPEG throughput: "the highest-value
  measurement in the project", still not taken). D11 owns decode, D12 the fold
  kernels (SIMD + fusion), D13 parallel scaling within the memory budget, D14 the
  GPU decision made the corpus's way, D15 the cold path and the speed scorecard.
- **State corrections against revision 2:** V-ENVSURF has landed — the 46-variable
  env surface is now classified (14 LIVE / 7 LIVE-UNVALIDATED / 23 INERT-SILENT, with
  `NOT-REACHED-BY-DESIGN` **empty**), so §2.2's "treat env claims as inert until
  proven" hardens from caution to measured fact. The corpus already *contains* IBIS-ON
  brackets (F §2.6 measured `ImageStabilization: On` on the May stacks), so C1's
  requested IBIS capture has a free pilot. A licence-discipline hazard inside the
  research corpus itself is flagged in §2.2 (F quotes GPL source verbatim; C13's
  implementer must not read those blocks).
- **Novelty hygiene:** every new C/D item carries named prior art or a `could not
  confirm` with its phase-0 search owed, per the fact-1136 discipline. Citations made
  from memory in this revision are flagged as such and assigned to the item's own
  literature pass.

**Revision 2 — what changed (kept for provenance).** Re-audited against
ARCHITECTURE.md (2026-08-28) and the lanes that landed after it (V-SOFTCHECK /
V-NEVERWORSE facts 1969/1978–1981; V-H2H2 facts 1974–1975; V-RIM facts 1896–1902; the
print gate closing 33/33, facts 1966–1968; the pyramid byte-freeze row, fact 1982).
Named the §2.4 exhibit (the fullres-gather doc/code contradiction). Added A5 (the
depth-field election), B5, C7–C9, the §6.0 information ledger, the D2 CRLB spine, and
four zero-capture phase-0 measurements. Withdrew the optically-black black-tracking
channel before anyone built it (`strehl-raw/src/lib.rs:10–15`: the padding is exact
zeros, not masked sensels).

**What was read before writing (cumulative over three revisions):** `README.md` in
full, `docs/ARCHITECTURE.md` in full, `docs/STATUS.md` in full, `AGENTS.md` (rules,
rig, licence discipline), `SYNTHESIS.md` §6 verbatim plus §7 and targeted facts, the
external-review triage in full, `docs/captures-needed.md` (START-HERE index, §29–§33
at depth), F in full, M115 in full, M70 §0 and §13–§14, M88 §4 and §10, G-edof Q5–Q6,
B §6–§8, BUILD-THESIS and BUILD-SPEED reports, V-ENVSURF verdict, and the following at
verdict depth or in source: M2, M5, M12, M20, M21, M22, M23, M27, M29, M30, M32, M33,
M34, M64, M65, M75, M84b, M90, M103, M110, M118, M120, M123, ORCH-veiling §59.3,
BUILD-PYRNOISE (via README), V-SOFTCHECK-nyquist and V-DCNULL (via STATUS),
`align_cmd.rs:1160–2100`, `merge.rs`, `edgeaware.rs`, `strehl-raw/src/lib.rs`, and the
withheld soft-gate patch's paper trail (facts 1917–1940).

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
1843–1845, 1849) — and the two knobs built to soften that are respectively **measured
as a null at depth** (facts 1974–1975) and **withheld as a patch** (facts 1933–1940),
which says the fix is a calibrated admission rule, not a better constant. Meanwhile the
project's own research has identified, and never developed, the physical channels no
other stacker can reach — sub-pixel diversity from focus breathing, longitudinal CA as
three offset focus sweeps, the two-layer occlusion model, metric depth from breathing,
the depth *field* as the election's latent variable — and this revision adds the
channels the corpus itself flagged and forgot: **the phase of the through-focus field**
(M70's own "single highest-value unmeasured thing", never run), **aperture diversity**,
**the quincunx green pair**, and **the vendor calibration tables already inside every
input file**. Every one of them requires exactly what strehl uniquely has: RAW samples,
a calibrated noise model, and a fixed rig. The path to SOTA is five moves: **(T) write
the model down once** — so every stage, and every grave in the graveyard, is a named
approximation to one likelihood; **(A) make the thesis ship** — one merge, estimation
in the band domain *and in the election*, confidence on the default path; **(B) finish
estimation** — runtime self-calibration, censored samples, variance-stabilised gates,
the sensor-state ledger, the re-renderable master; **(C) exploit the physics** —
sample-level fusion, depth, wavelength, phase, orientation, aperture and illumination;
**(D) build the instrument and close the loop** — the pre-registered scorecard, the
certified-acuity map (model-based *and* empirical), per-stack self-tuning, the capture
planner up to and including a live tethered loop, and the wall clock taken to its
measured physical floor, which the profile says sits **5–10× below the current default
and is decode-bound, not merge-bound** (D11–D15). Sequenced in §9; **ten of the
sixteen items new in this revision can be killed or confirmed from the corpus and this
machine alone, without the owner lifting a camera.** If only two things survive triage: **phase 1**
(the thesis shipping by default) and **phase 0's capture session**, because the latter
is the only item no amount of software can substitute for.

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
commissioned instruments.** An instrument is admitted to the scorecard only after it
has (a) failed on a planted defect of the kind it polices, and (b) passed a null it was
not tuned on — the standard this project already applies internally (rules 9, 11, 13;
the V-RIM acquittal is the template: the statistic that convicted 13 subjects also
convicts Zerene *and a raw unstacked camera frame*, facts 1896–1902, so it was
measuring shoulder roughness, not a stacker). Proposed axes, with today's honest state:

| Axis | Today | What blocks a claim |
| --- | --- | --- |
| Noise, flat/defocused ground | **Ahead, measured.** 4.5× vs the fork (≥2.4× worst-case grade-corrected); 0.746× vs one unstacked frame at gate 4.5; 9.9× flat-field rms on the deepest stack with the compound eye indistinguishable (README) | Nothing — quotable now |
| Highlight retention | **Ahead vs fork (32% clipped vs 4e-6), but the default path cannot see its own clipping** — the clip census does not run there (README) | Wire the census; B2 below |
| Invented structure | **Ahead.** 0.0000% out-of-hull for every convex arm, held as a discipline (M115 §1) | Keep it an axis, so it cannot be quietly traded away; D2 ships it as a certificate |
| Occlusion veil / aura | Directional win, all 17 conditioned readings (fact 1871); halo axis: 11 of 26 demonstrated clean, 4 blind + 7 unmeasurable (fact 1891); ±12 px rim axis **acquitted** (facts 1896–1902); veil mechanism measured, unfixed (ORCH-veiling §59.3); `chia-seeds-cpl` crevice haze is the live specimen (STATUS §4) | ≥400 px clear-background captures; A2/C3 below |
| Fine detail ≥ 0.15 cyc/px | **Split by frequency, one subject, no CI:** the master reads **1.10–1.19× the per-site best-frame ceiling below 0.20 cyc/px** and **0.9426 (≈5.7% short) at 0.20–0.25**, softer above (facts 1969, 1978–1981; V-SOFTCHECK-nyquist). Vs comparators: **undecidable in either direction** (README) | §30/§32/§33 captures; a licensed comparator; the D1 instrument. The below-0.20 win is the first of its kind in the corpus and needs its CI and its exposure audit before anyone quotes it |
| Per-pixel trust | **Absent from the field (VERIFIED, C) and absent from strehl's default path** — the refused-flags list | A4/D2/D8 below. This is the thesis, not a feature |
| Depth output | Absent from the field; unbuilt here (R20/R21 queued) | A5/C5 below |
| Speed / memory | **Ahead, measured.** 22.58× enfuse; 2.4× the fork's best build; 0.20–0.39 s/frame; flat memory (STATUS §1, ARCHITECTURE §9) | Hold the line (D5; D9 buys back the worker-cap tax first), then extend it: the measured hardware floor sits **5–10× below the current wall and is decode-bound** — D11–D15 is the program, and one unmeasured number (per-core LJPEG throughput, D11) decides its ordering |

The scorecard needs three purchases/captures that no algorithm can substitute for: a
Zerene licence (the trial saves zero bytes — README), the slanted-edge chart and its
Lightroom-export half (§30/§32), and one subject with real contrast above 0.25 cyc/px
(§33). These are cheap against the months of instrument-building they unblock, and
**every fine-detail claim in this proposal is contingent on them.**

The end-state sentence the project should be able to print, each clause with its
licensing instrument in parentheses:

> On [subjects], strehl resolves detail at or beyond the best shipping comparator
> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly lower noise
> (existing flat-ROI instrument), with zero invented structure (hull census, stamped
> per file), no occlusion veil above [bar] (halo instrument at full reach), while
> emitting per-pixel certified acuity, n_eff, and depth in physical units that no
> comparator emits at all (D2/D8/A5/C5), in [X] s per frame on CPU (existing harness).

---

## 2. The research corpus: an audit

The owner asked directly whether the research is useful at all. Verdict unchanged from
revision 1 and strengthened twice since: **it is the project's principal asset, and it
is what makes this proposal writable.** Three ways it earns that, five hazards, one
exhibit, and the residue it left unexploited — which this revision found more of.

### 2.1 What it is worth

**(a) The graveyard.** The obvious ideas an outside proposer would reach for first are
already measured dead, with mechanisms: multi-frame Wiener across the focus axis (M20:
wins 15.1% of pixels; M70: the band matrix is rank-1 to 0.9959, so matched filtering
over near-scaled copies *is* weighted averaging; M115: R_SNR 1.0014, CI [0.965, 1.038],
with 29.5–36.4% of deconvolved pixels outside the convex hull of their own sources —
three instruments, one answer); OTF self-calibration from through-focus *curve width*
(M115 §5: over-estimates the defocus scale 1.87–2.15×, fitted s falls with frequency —
the model is qualitatively wrong, not mis-scaled); outlier rejection (**five**
independent refusals — M123 fired on 29.55% of a *stationary* subject, and a second
mechanism was 21.5× more active on the stack that never moved); entropy-scalar
confidence (M32: blind, non-monotone, degenerate); shrinkage calibration for alignment
(M12: transfers 0 of 18, worst case 83.4× worse); metacalibrated edges (M23: the
measured "response" was the probe's own bilinear resampler); the significance exponent
at depth (facts 1974–1975). Without this record, the present proposal would be longer
and mostly wrong. §8 lists what is therefore *not* proposed — and §3.0 now shows most
of those graves falling out of the model plus one measured constant each.

**(b) The measured constants that make the physics exploits designable.** Magnification
m = 2.7198 ± 0.0051 (M84b); bellows factor B ≤ 3.064 at f/11 with a genuine spectral
knee at 0.2762 cyc/px (M5); pupil factor p ∈ [1.31, 1.94] putting the f/5.6 diffraction
cutoff at **106–135 cy/mm, above the 97.66 cy/mm sensor Nyquist** (M88); the rig
measured **~2.2× softer than diffraction alone explains**, two instruments within 4%,
with "mostly optical" bounded above at ≤76.6% on n=1 and a printed target
(captures-needed §29) — which means both that aliasing physically exists to recover and
that a real, optics-shaped blur budget exists that only reconstruction can touch; the
noise model g/read/κ with an independent PTC cross-check (M71, M90) and the full
per-ISO table with the dual-conversion-gain step at ISO 400 (F §2.3);
FOCUS_NOISE_SD and the 10.27× operator span (plugin seam); breathing = −1.012% scale
across 33 frames, linear, scale centre ~400 px off image centre (F §5–§7), up to 299
plane px corner drift at N=299 (ARCHITECTURE §7); adjacent-frame warp 0.07–0.22 green
px (M29); track jitter median second-difference 0.48 px, 13.8% of adjacent pairs ≥1 px
(M110); the sub-frame peak cost distribution (M33: 48.7% of pixels miss peak; median
4.64%, p99 17.34% of response); and the selection premium itself, 24–240× (facts
1843–1845, 1849).

**(c) The instrument discipline.** Pre-registration, planted defects, placebo arms, the
author-never-verifies rule, "a statistic that has only ever been shown to succeed is
not evidence." A SOTA claim is exactly the kind of statement that dies without this,
and the project already knows how to build claims that survive attack — the V-RIM
acquittal and the V-SOFTCHECK sign-immunity argument are the two best recent specimens.
G-edof additionally hands the project the one ground-truth-free sharpness metric that
cannot be fooled upward by noise amplification (FRC — R25(iv)), which D1 adopts as its
spine and D8 now promotes into the product itself.

### 2.2 The hazards

1. **A large share of quality results measure the estimator backend, which no longer
   ships.** The gate table, the n_eff calibration ladder, the veil estimator, the
   edge-aware machinery, photometric — all estimator-path. The pyramid default beats
   the estimator on acuity, microcontrast and aura (README), so the *conclusions*
   mostly transfer in strehl's favour, but the *numbers* do not, and README documents
   two headline retractions caused by exactly this transfer.
2. **Absolutes are timestamps** (fact 1886). Everything quantitative in this proposal
   must be re-derived inside the lane that consumes it, from one pinned build.
3. **Instrument churn ate the project's middle.** Three detail statistics, two rim
   instruments, one timing harness and one deconvolution channel failed their own
   commissioning. The cure is D1: build the instruments *once, first,* against the
   captures that give them something to grip.
4. **Several load-bearing questions are blocked on captures, not analysis** — and have
   been for weeks: §30/§32/§33, the aperture ladder (§29), the TC-off bracket
   (§17/§29), darks at working exposure (§6/§28), the ≥400 px clear-background subject
   (fact 1891). The cheapest schedule acceleration available to the owner is one
   capture session (§9, phase 0).
5. **Summaries lean flattering; the docs age faster than the code.** The 8-of-25 audit
   above, plus §2.4 below. The discipline that follows: this proposal cites files and
   facts, not summaries of summaries, and every number in it is re-measured at point
   of use. The env-channel caution of revision 2 is now a measurement:
   **V-ENVSURF classified all 46 `STREHL_*` variables on the shipping default — 14
   LIVE, 7 LIVE-UNVALIDATED, 1 INERT-VALIDATED, 1 DEBUG-ONLY, 23 INERT-SILENT, and
   `NOT-REACHED-BY-DESIGN` is empty.** Half the env surface is the `STREHL_SOFT_GATE`
   failure class. Any env-gated claim is inert until its liveness control is cited.
6. **NEW — the corpus itself contains licence-discipline breaches, quarantine them.**
   Workstream F (2026-08-22, predating the hardened AGENTS licence table) quotes
   verbatim source from darktable's `exif.cc` (GPL-3.0) in §6.1 and ExifTool's
   `Sony.pm` Perl (GPL) in §3.1/§6.1. Under AGENTS' own rules those blocks must not
   be read by anyone implementing the features they describe. This matters
   practically for **C13**, which touches exactly those tags: its implementer works
   from tag IDs, counts and offsets (uncopyrightable facts, explicitly permitted),
   from hex dumps of the owner's own files, and from fitting semantics against
   strehl's own measured CA/distortion profiles — never from F's quoted blocks. A
   docs task should fence those sections with a warning header. **Workstream D (same
   date) has the same defect in a different direction:** its §1.1 and FU1.3 quote
   `rawler` source (`arw.rs`, `decompressors/mod.rs`) — LGPL-2.1, "link only, do not
   read" in AGENTS' own table. Two of the facts it extracted are load-bearing for
   D11 (ARW frames are 512×512-tiled; rawler already strip-parallelises decode with
   rayon). Both are re-establishable black-box — a thread-scaling decode benchmark
   says the same things legally — and D11 requires exactly that re-establishment
   rather than citing the quoted source, and forbids reading rawler going forward.

### 2.3 The unexploited residue — the corpus's own novelty list

SYNTHESIS §6 records four verified-absent-from-literature bets, and B §6–§7 sketch two
of them at hypothesis level. **None has been developed.** They are workstream C:
super-resolution from focus-breathing sub-pixel diversity (B §6: four arXiv queries,
zero results); per-channel focus stacking exploiting longitudinal CA (B §7.2: no prior
work found; Trouvé 2013 and Chang & Wetzstein verify the physical signal exists);
diffraction+defocus PSF modelling at macro magnification; a monocular depth prior as an
ordinal regulariser (folded into A5 as an opt-in, covenant-safe per risk 3);
depth-from-breathing as a metric ruler (R21, "QUEUED — attractive"); and the two-layer
occlusion model, where the defensible claim is "first *shipping* tool" (Asada 1995
precedent, M19). Two external-review items were parked rather than killed and are
revived here: R18 (active texture — C8) and R16's aperture-paired half.

**And the corpus named one more and then forgot it.** M70 §14, items 3 and 4, in the
author's own words: registration-aligned **complex cross-spectra** would (3) bound the
phase slack in every gain M70 reported, and (4) see the defocus asymmetry the modulus
family is "constitutionally blind" to — "**the single highest-value unmeasured thing
M70 touched**." No milestone ever ran it. Every through-focus statistic in this corpus
— the rank-1 finding, the election, the parabola, the asymmetry addendum — is built on
magnitude alone. C10 is that channel, opened.

**A standing caution on every novelty claim in this file, from the corpus's own audit
of itself:** two prior surveys each missed their nearest prior art (Pertuz 2013;
Schechner 1998 — facts 1112, 1136), so *"verified absent" inherits the search quality
of the report that made it*. Every C-item below therefore carries the `could not
confirm` posture, each one's phase-0 gate includes its own literature pass, and
citations introduced from memory in this revision are marked so they get verified
rather than trusted.

### 2.4 EXHIBIT — the pipeline has two contradictory identities, and the freshest document in the tree picked the wrong one

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
workstream. Note also the two mid-band correlation numbers in the first bullet are the
project's only direct sighting of **contrast inversion** in its own pipeline — C10
gives that observation its physical name and its guard.)

---

## 3. Strategy

### 3.0 The one model — every stage is a named approximation, including the graves

**ARGUED, with every constant it invokes MEASURED elsewhere in the corpus.** The
project's stages, its refutations, and this proposal's new items all live inside one
observation model. Writing it down once is not decoration: it converts "we measured
that idea dead" into "the model plus a measured constant *predicts* that idea dead,"
and it tells every future lane which term it is estimating and which terms it is
holding fixed. Per frame i, at output position x, channel c:

```
y_i(x_s) = C_i · ∫ h( x_s − W_i(u; z(u)) ;  ζ_i − z(u),  r, c,  θ ) · R_c(u) du
           + veil/occlusion mixing at depth steps        [two-layer term]
           + n_i(x_s),      n_i ~ N(0, σ²(S; g, RN, κ)),   censored at S_max
```

where `R_c` is the scene radiance (the thing being estimated), `z(u)` the depth field,
`ζ_i` the frame's focus position, `W_i` the warp (similarity + residuals, possibly
z-dependent), `h` the PSF — parameterised by defocus `ζ_i − z`, field position `r`,
wavelength `c`, and pupil aberration state `θ` — `C_i` the photometric state, `n_i`
the calibrated noise, and `x_s` ranging over the *actual photosites* of frame i's CFA.
The map from here to the tree:

| Term | Who estimates it | Approximation the shipping code makes |
| --- | --- | --- |
| `R_c` at 1× with h ≈ within-DOF indicator | A1 (banded admission), today's pyramid/estimator | selection above the floor instead of admission-averaging |
| `z(u)` | A5 (+ C2, C10, C11 data terms) | per-coefficient argmax, no spatial model |
| `W_i` | alignment + C4 (+C10's phase instrument) | similarity only; z-dependence assumed zero |
| `ζ_i` axis, metric | C5 (breathing ruler) | frame index |
| `h(·; θ, r, c)` | C10 retrieval, C11 sweep, D4's H, §30 chart | never estimated; gather kernel stands in |
| `C_i`, sensor state | B3, B5, B1 | estimator-only or absent |
| censoring | B2 | clipped values ingested as values |
| two-layer term | A2 (pedestal), C3 (full) | base band averages the veil in |
| the sampling operator `x_s` | C1 (sample-level fusion) | per-frame demosaic *or* per-phase band-limit (§2.4 — both wrong) |
| `σ²(·)` | shipped (profile), B1 (in-situ), B6 (stabilised) | profile-only, Gaussian at all levels |

And the graveyard becomes derivable. **Multi-frame Wiener** inverts `h` along ζ; M70
measured the within-window family rank-1 in modulus (0.9959), so the inversion
degenerates to a weighted average whose weights buy 1.0009–1.0107× (M70 §0.3) — the
model says the estimator collapses, and M115 measured the collapse end-to-end (R_SNR
1.0014). **Curve-width OTF self-calibration** estimates a parameter of `h` from a
statistic the operator convolves and the step quantises — G-edof Q5 caveat 3 named the
circularity, M115 §5 measured the 1.87–2.15× bias. **Per-pixel outlier rejection** adds
a per-pixel per-frame latent the data cannot support at n_eff ≈ 3 (M29's floor was
scene texture); the frame-level state B5 estimates instead is O(N) parameters, not
O(N·pixels). Each new item below names its term; anything that names no term is
decoration and should be cut in review.

Two standing constraints the model makes explicit. **Convexity:** every estimator of
`R_c` this project ships is a convex combination of measured samples (the hull
discipline, 0.0000% for every convex arm — M115 §4); inversion of `h` is permitted
only in D4's single-pass, measured-H, noise-budgeted restore, and never feeds back
into election. **Identifiability before machinery:** a term enters the joint estimate
only after a phase-0 census shows the data constrains it (σ_z for A5, phase
conditioning for C1, δ for C2/C7, the DPAR slope for C4c) — that is the pattern every
sequenced item in §9 follows.

Four workstreams execute the model. A and B make the thesis true of the product a user
runs. C is the novel territory — the physics only strehl can reach. D is the
instrument and the product surface that turn all of it into claims and into a tool
someone can trust. Nothing in C is load-bearing for A/B/D; the plan degrades
gracefully if any bet dies, and each item below carries its own kill bar so it can die
cheaply.

A one-line version of each:

- **A — One merge, thesis on both axes.** Estimation moves into the band domain
  (A1–A4) and into the *election itself* (A5): the merge stops crowning winners and
  starts estimating the focus surface. The backend fork retires; confidence ships by
  default.
- **B — Estimation finished.** The noise model measures itself per stack; clipped
  samples become inequalities; photometric gain follows the breathing law; gates run
  in a variance-stabilised domain; the bracket becomes a time series with per-frame
  state; the fold's sufficient statistics outlive the render.
- **C — The physics exploits.** The merge consumes photosites; colour becomes three
  offset focus sweeps; occlusion becomes a two-layer estimate; the warp gains the one
  physical term a similarity cannot carry; depth becomes micrometres; the sensor
  calibrates itself under the sliding scene; focus becomes orientation-resolved; the
  **phase** of the through-focus field is finally read; the capture side gains
  aperture, texture and polarisation diversity — one accessory or one extra bracket
  each.
- **D — The instrument, and the loop closed.** The scorecard; the certified-acuity
  map with a CRLB spine *and* an empirical FRC spine; per-stack self-tuning; the
  capture planner, offline and then live; determinism decoupled from worker count;
  the bounded restore; the performance budget that keeps all of it shippable.

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
piece was never a new kernel; it is a **calibrated admission width**. M70 §0.4 says
the same thing from the physics side: of the mid-band SNR available at ±5 frames,
~30 points come from *admitting more frames* and ~8 from weighting them optimally —
"the cheap change is the big one, and it is a constant, not an architecture."

**The design.** Keep the Laplacian frame — M120 proved the estimator's polygonal
patchwork is a property of the per-pixel winner field, and the pyramid's spatial
coherence is why it won the A/B; do not re-litigate that. Inside each band, replace
soft-power ratio weighting with the estimator's own admission logic, per coefficient:
elect the winner by smoothed band energy exactly as today; **admit every frame whose
smoothed energy lies within k·σ_band of the winner** (σ from the injected model times
the per-frame measured floor that already ships); **average the admitted coefficients
with inverse-variance weights**; below the floor, fall back to the plain mean as today.
Report per-band n_eff as a first-class statistic. Gate arithmetic runs in B6's
variance-stabilised domain, so one k is correct at every signal level; the *estimate*
stays a linear-domain convex average (B6 explains why that split is mandatory).

Binding lessons from the soft-gate lane: **match kernels on effective width (n_eff),
never on the threshold parameter** (facts 1917–1920 — the same T admits n_eff 4.674
hard vs 19.295 Gaussian), and note the Gaussian kernel is not one-pass streamable (a
cross term forced a second decode pass, 56.3 → 124.7 s at N=79). An admission-by-margin
rule needs the winner before weighting, so the unified merge is likely **two-pass over
frames**; the estimator's two-pass structure and its O(1)-per-pixel sufficient
statistics are the template (ARCHITECTURE §5b), and the ~2.2× wall cost is priced in
D5 (and partly bought back by D9). The withheld patch is the starting material. The
admission width k itself stops being a constant the day D8 lands: it becomes a
per-stack calibration against the split-half objective, which is what finally closes
the 2.0-vs-4.5 standoff with a measurement instead of a memo.

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
collapses with it, and the 46-variable env surface — now measured at 23 INERT-SILENT
(V-ENVSURF) — shrinks with the code that read it.

### A4. Confidence on the default path

The README names this the single largest gap between what the project is for and what
it does. M34 fixed the shape: **a vector, never a scalar** — the three channels flag
near-disjoint pixel sets (union 14.278% vs a 15.0% disjoint ceiling) and predicted σ is
*anti*-correlated with the sub-frame deficit in the worst tail. Ship, per pixel, on the
default path: per-band n_eff (A1 makes it exist), admission width, sub-frame peak
deficit via the **log-domain parabola with baseline subtraction** (M33 — the naive
parabola's peak-height estimate is anti-correlated with the truth), hull-clamp
distance, and — once B2 lands — the censored flag. D2 turns this vector into the
certified-acuity product; A5 adds depth and σ_z; D8 adds the empirical (split-half)
channel beside the model-based ones.

### A5. The depth-field election: estimation, not selection, in the election itself

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
The data term is deliberately open at the back: C2 (chromatic peaks), C10 (signed
displacement and phase asymmetry), C11 (two-aperture blur ratio) and C8 (projected
texture) each add an independent per-pixel measurement of the same latent z, with its
own σ — the solve does not change shape when they arrive.

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
to fixed pattern by construction (the M90 method applied in-stack; F §2.3's local
single-frame PTC recovered the modelled g within 2% after the known percentile bias
correction, so the method family is already validated on this body). Cross-check with
the G1−G2 split within single frames (C12 owns that channel's full exploitation; here
it is the σ probe — after calibrating the static G1/G2 imbalance once on the delivered
flats), and against the per-frame measured band floors `gatefloor.rs` already computes.
Output: measured g, read floor, and a κ consistency check against the profile; on an
unknown body this *is* the model — `Provenance::Measured` — which retires the
one-profiled-camera limitation as a portability blocker.

**One channel that does NOT exist, recorded so nobody re-proposes it:** per-frame black
tracking from optically-black photosites. The decoded buffer's padding is **exactly
zero — "not masked sensor pixels and not black level"** (`strehl-raw/src/lib.rs:10–15`;
F §2.2 measured the same through LibRaw). Black-level drift must instead be estimated
as the intercept of the temporal PTC and from the deep-shadow quantiles of low-gradient
tiles (B5).

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
polarisation channel and C11's stopped-down arm both attack the same speculars
upstream.

**Novelty note (ARGUED, `could not confirm`):** burst/HDR pipelines *weight down*
near-clip samples (the Debevec-hat family; citation from memory — the phase-0 pass
verifies); I know of no stacker or burst merge that treats clipped RAW samples as
censored data in a per-pixel MLE. B §3/§8 record nothing of the kind.

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

### B5. The sensor-state ledger — the bracket as a time series, now with a per-frame quality arm

A 299-frame bracket spans minutes; the sensor, the rig and the light are not
stationary across it, and the corpus keeps meeting the consequences one at a time:
flux ramps (M24, 8.2–36.9%), the foam exposure excursion, EXIF that does not predict
level (R9), warm-up drift in dark current the 1/100 s darks cannot speak to (fact
808). Rather than one fix per symptom, estimate a small per-frame state vector —
black-level offset, gain, flux scale, warp residual summary (from C4), and the two new
arms below — as a **joint smooth-in-time fit** across the stack, with the breathing
law (B3) as its deterministic backbone and B1's PTC as its noise scale. This is glue,
not a new estimator: each component is already proposed or shipped; the ledger makes
them share one temporal prior and one report, and it is what makes the banner able to
say "frame 212 is 0.3 stops off-model and was down-weighted" instead of nothing.

**NEW — the per-frame PSF-quality arm, and why it is not the refused outlier
rejection.** A frame can be *globally* degraded — vibration during exposure (shutter
shock, a bumped tripod, a gust), a focus-motor overshoot, a flicker trough — and today
nothing in either backend can notice. Two cheap per-frame observables detect it:
(i) the frame's high-band energy at its *own elected-sharp* regions, referenced to its
neighbours' at theirs (a vibration-blurred frame is soft exactly where it should be
sharpest, and its neighbours cover for it); (ii) C12's within-frame G1−G2 noise
residual, which separates "soft because defocused" from "soft plus wrong noise" —
a smeared frame keeps its noise while losing its signal. The response is a *frame*
state: widen that frame's σ in every gate, demote it in admission, and say so in the
banner — never a per-pixel mask. The graveyard row stands untouched: five refusals
killed *per-pixel scene-motion rejection*, whose latent is O(N·pixels) and whose
measured floor was scene texture (M29); this arm estimates O(N) parameters from
whole-frame statistics and is commissionable on the §12 static repeat burst with a
pre-registered FPR, which is exactly the reopen condition §8's row names.

**NEW — the capture classifiers F already validated, wired in.** `FocusPosition2` as a
*classifier* (focus-driven vs rail-driven — its two-level resolution is sufficient for
that and nothing else, F §3.2/§5.2, and it selects the alignment model rail support
will someday need); `SonyRawFileType == 2` (lossy 11+7 delta) detected and warned
loudly, since its artefacts concentrate at exactly the high-contrast edges a focus
measure reads (F §2.4 — the corpus is type 4, lossless, so today this is a guard, not
a fix); `ImageStabilization: On` flagged on tripod brackets (F §2.6 — note C1 turns
this vice into a virtue deliberately); ISO 320's dual-gain trap (F §2.3: 1.2 stops
worse than ISO 400) reported at decode time, not just in the planner; body temperature
EXIF, where present, logged into the ledger for the dark-current arm. Row-noise/
banding common-mode estimation in deep shadow slots in here if measured to matter
(this body's read floor at second base is 1.24 e⁻, so the prior is that it does not —
measure once, then keep or close).

### B6. NEW — variance-stabilised gates: one width, correct everywhere

**The gap.** Every gate in the tree compares an energy or a response against k·σ(S)
with Gaussian σ from the model. That is right in the mid-tones and progressively wrong
in deep shadow, where the Poisson term skews, and it forces every threshold to be
re-derived per level. F §2.3 already recommended the fix and nothing shipped it: the
**generalised Anscombe transform** `T(S) = (2/a)·√(a·S + (3/8)a² + b)` with the
calibrated (a, b) maps the signal-dependent noise to unit variance, so *one*
dimensionless admission width k is correct at every brightness, every ISO, every
photometric gain (B3's c rescales a and b and T absorbs it).

**The discipline that makes it safe:** the VST is used for **decisions only** — gates,
admission margins, floors, the CRLB bookkeeping in D2 — never for the estimate itself.
The merged value remains a convex combination of *linear* samples (unbiasedness and
the hull certificate both live in linear light; an averaged-then-inverted VST value
would be neither). No inverse transform ever runs, so the Mäkitalo–Foi exact-unbiased
machinery is not needed (citation from memory — flagged for the pass). Scope: A1's
band gates need the band-domain variance propagated through the transform (a one-line
delta-method factor); B2's censored likelihood stays in linear DN where the censoring
boundary is physical. Acceptance: byte-identical output above [level bar] where the
Gaussian approximation was already fine; measured gate false-fire rate in the deepest
shadow decile moves toward its nominal value on the M25 twin; zero change to the hull
census.

### B7. NEW — the re-renderable master, and the output container as a noise floor

Two related products of the same observation: **the fold's sufficient statistics are
worth more than the render.**

**(a) The re-renderable master.** The unified merge's per-pixel, per-band state —
winner energy, floor, Σw, Σw·v, plain-sum, count, and A5's (ẑ, σ_z) — is a few GB as
a sidecar (DERIVED: ~7 bands × ~4 statistics × 4 B ≈ 112 B per quad-plane pixel ≈
3.7 GB at 33 MP; opt-in, compressible, and the estimator path already proved the
pattern by folding a whole `--gate` ladder in one pass two). Persist it, and
admission width, exposure, tone, and even A2's coherence ramp become **post-fold
decisions re-renderable in seconds** — no re-decode, no re-warp. The gate-2.0-vs-4.5
class of dilemma stops being a compiled constant war and becomes a reviewable slider
over frozen statistics; D1's scorecard sweeps admission width for the cost of a
re-collapse; and a support engineer can re-render a user's reported defect at ten
settings from one uploaded sidecar. Prior art posture: this is the deep-image/AOV
pattern from VFX compositing (deep EXR; citation from memory), applied to a stacker's
sufficient statistics — `could not confirm` any stacker shipping it.

**(b) The output container is about to be the noisiest component in the shadows.**
DERIVED, with the profile's own constants: at ISO 100 (g = 0.2285 DN/e⁻, read var
1.165 DN²), a deep-shadow pixel at S = 50 DN has σ = √(0.2285·50 + 1.165) ≈ 3.6 DN;
at n_eff = 50 the merged σ is ≈ 0.51 DN, while a 1-DN output LSB contributes
σ_q = 1/√12 ≈ 0.29 DN — **~25% of the remaining noise variance, rising as admission
widens**. The fix costs almost nothing: measure LSB/σ_cert per render (D2 already
computes σ_cert); where it clears a bar, either emit 32-bit float TIFF (opt-in) or
add sub-LSB triangular dither before the 16-bit quantise (default, deterministic
seed, disclosed in the banner). M115 P18/P19 is the sharp warning here: quantisation
error is *correlated* across frames and split-halves — it books as signal in every
difference-based estimator and hides from the very instruments D8 relies on — so the
output stage must never be allowed to quantise *inputs* to any measurement path.

---

## 6. Workstream C — the physics exploits

### C6.0 The information ledger — why this list has these members

A SOTA proposal that says "novel physics" owes an argument that the list is complete
rather than merely long. The capture is: a static scene, a fixed rig, one aperture,
one exposure, N focus positions, RAW CFA samples. Every independent axis of that data
cube, and what reads it:

| Channel | Physical content | Exploited by |
| --- | --- | --- |
| Focus axis z (modulus) | depth, through-focus response shape | A5, C2, C3, C5 |
| **Focus axis z (phase)** | **signed defocus, sub-pixel registration, pupil aberrations, contrast inversion** | **C10** (new; C4c's instrument) |
| Spatial sampling phase under breathing/jitter | aliased super-Nyquist structure | C1 |
| Wavelength (CFA) | longitudinal CA = 3 offset z-sweeps; per-λ diffraction cutoff | C2, C1's kernel |
| **G1/G2 quincunx offset** | **within-frame noise probe; alias energy between plane and sensor Nyquist** | **C12** (new; feeds B1, B5, C1) |
| Orientation | astigmatism/coma anisotropy of the PSF | C7 |
| Amplitude statistics | photon-transfer self-calibration; censored samples at clip | B1, B2 |
| Fixed pattern vs sliding scene | PRNU/dust/hot in situ (breathing = dither) | C6 |
| Depth-dependent geometry | axial pupil parallax; magnification vs depth | C4c ↔ C10, C5 |
| Time within bracket | sensor/illumination/rig state drift; per-frame PSF quality | B5 |
| **The file itself** | **vendor 16/32-knot distortion+CA tables; compression type; capture flags** | **C13, B5** (new) |
| **Split-stack halves** | **two independent realisations of the same latent — empirical noise/resolution ground truth** | **D8** (new) |
| Illumination (capture-side, controllable) | texture where the scene has none; specular/diffuse split; two-lamp normals | C8, C9, D3 |
| **Aperture (capture-side, one more bracket)** | **blur-ratio depth; small discs at occlusions; PSF family; pupil factor p** | **C11** (new) |

Channels examined and left closed on purpose, each with its measured reason: absolute
phase/coherence (no interferometer; C8's speckle statistics are the accessible
shadow); exposure diversity (M30: allocation neutral at fixed light; the planner owns
the −2 EV highlight arm); polarisation *without* capture change (the CPL is fixed
within a bracket — C9 is the capture change that opens it); **PDAF as data or defect**
(F §2.5: no published pattern for this body, the prior empirical recovery ended RED,
and the disparity baseline collapses at working apertures — closed unless Sony
documents the pattern); **optically-black black tracking** (the padding is exact
zeros — revision 2's withdrawal, F §2.2 concurring). If a reader can name another
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
Green arrives quincunx (2× diagonal density per frame — and C12's disagreement
statistic reports, per tile, whether there is alias energy for the finer lattice to
unfold at all); R/B arrive at quarter density and are completed across frames.
**Per-λ refinement:** the kernel's target bandwidth should follow the channel's
physical cutoff — diffraction scales as 1/λ, so blue carries the finest transmissible
structure and red the coarsest; a per-channel bandwidth cap from the measured optics
is one constant per channel and prevents the kernel from chasing alias energy past
red's physical limit. Where sample count or phase diversity is poor the kernel widens
and the estimator degenerates to exactly today's behaviour — degradation is continuous
and *reportable per pixel* (`phase_coverage` and `sr_contributing_frames` as honest
outputs, per B §6.5).

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
motion it is free dither everywhere), and IBIS wander — and here revision 3 corrects
revision 2's framing: **the corpus already contains IBIS-ON brackets.** F §2.6
measured `ImageStabilization: On` on the May stacks (109MSDCF among them), flagged
then as a capture error; for this item it is a free pilot dataset. The deliberate
IBIS-ON bracket stays requested (to get IBIS diversity *with* current capture
quality), and would still be, to my knowledge (ARGUED, `could not confirm`), the
first deliberate use of a stabiliser as a super-resolution dither source in stacking.

**The registration wall, named.** 2× reconstruction needs *relative* registration of
the contributing samples good to ~0.1–0.15 px. The global similarity's held-out corner
error spans 0.353–11.562 px across stacks — but that is the end-to-end gauge; the merge
consumes per-frame placement (M103), and SR consumes something smaller still:
**relative placement among the 3–6 within-DOF frames**, which are content-matched (the
correlation problem alignment finds hard — cross-focus appearance change — is absent
between them). That is the easiest sub-problem in the whole alignment space, and C4's
local refinement owns it — with C10's phase-correlation channel as its precision
instrument. Where the per-window registration confidence fails its bar, that pixel's
lattice contribution degrades to 1× — refusal per pixel.

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
the measurement says; defringing becomes a lookup instead of an inference; and the
three per-channel peaks are **three interleaved samplings of the same surface at known
z-offsets**, which both triples the effective z-sampling density of A5's data term and
hands C5 a per-pixel LCA measurement (the spread), a capability no stacker has. **If it
does not:** close it as a measured null the way M17 closed the dual-response — the
corpus gains the number either way.

**Frontier note, one sentence for the record (ARGUED, almost certainly sub-resolution
here):** LoCA varies *within* each channel's passband too, so a channel's through-focus
peak position carries a trace of the surface's spectral slope inside that band —
"focus spectroscopy"; on an apo macro behind a TC the within-band spread is plausibly
far below one step, so this is recorded as the ultimate form of the channel, not
proposed.

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
to invert it**, and even that keeps the `could not confirm` label. C10 adds one guard
here: a heavily-defocused occluder contributes mid-band energy with *inverted
contrast* once its blur disc passes the band's first OTF zero (DERIVED: first zero at
≈0.61/R_disc cyc/px, so a 60 px disc inverts everything above ~0.01 cyc/px), and a
phase-coherence check against the winner detects exactly that contamination class —
the veil model's mixing term gains a sign the modulus channel cannot see.

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
adds ~tens of parameters per frame, not per pixel; C13's vendor distortion knots give
it a deterministic radial seed;

**(b)** for C1 only, per-tile relative refinement within the in-DOF window, where
content is matched and precision is at its best — and C10's complex cross-spectrum is
the right instrument for it (a linear phase ramp *is* sub-pixel displacement, read
from hundreds of coefficients at once rather than from one correlation peak);

**(c) the depth-dependent magnification term — the one physical term a similarity
cannot carry, now with its mechanism and its instrument.** A similarity fits one scale
per frame. But magnification is a property of a *plane*: the lens is not image-space
telecentric (F §5.3 — chief rays land at an angle growing with field height, which is
the very mechanism of breathing), so content at depth offset δ from a frame's focused
plane is rendered displaced radially by its *own* defocus, not the frame's. DERIVED,
with the assumption stated: if the depth term carries the same coefficient family as
the breathing term (both are Δz/z_pupil geometry), the corpus's adjacent-step scale of
3.2e-4 predicts **~0.3–0.6 px of radial displacement at r = 1000–2000 px per focus
step of depth offset** — squarely measurable, and cumulatively exactly the kind of
depth-correlated residual that would produce the three unexplained corpus
observations: held-out error spanning **33× across stacks** (deep close-up stacks
worst), shrinkage magnitude "a property of the scene, not of the optics" with no
edge-set predictor (rule 6's own words), and the scale centre sitting ~400 px off the
image centre (F §7). **M-PHASE0-DPAR settles it from existing artifacts, zero
captures:** regress per-tile similarity residuals against the elected depth index per
tile across a deep stack; a nonzero slope is the term. If present, three consequences,
in rising order: one added parameter per frame calibrates it out of the warp; the
merge's gather becomes depth-corrected per pixel once A5's z exists (`W_i(x; z)` —
which C1 consumes natively); and **the sign of the displacement is the sign of the
depth offset** — pupil-baseline parallax as a second, absolute depth ruler for C5 and
a sign channel for A5, independent of the breathing ruler. If absent, the assumption
"similarity suffices" graduates from assumption to measurement.

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
across a 33-frame stack; one LSB ≈ 22× the depth of field; F §5.3's exit-pupil
geometry, `scale ≈ 1 + Δz/z_xp`, is the physical model behind the ruler and yields
z_xp itself as a fitted by-product). A5 supplies z(x,y) ± σ_z in frame-index units;
this item converts the axis. Cross-checks now number four: fact 54's pixel-measured
focus index, C2's chromatic spread, C4c's parallax ruler if M-PHASE0-DPAR finds one,
and C11's blur-ratio depth if the aperture pair is shot.

**NEW — field curvature, separated instead of ignored.** F §6.5 correctly argued that
per-pixel *selection* absorbs field curvature and it should not be modelled for image
output. A5 changes the calculus: the solved z-field is scene depth **plus the lens's
focal-surface bowl**, and the metric products (depth TIFF, normals, reshoot advice in
mm) inherit the bowl unless it is separated. The separation is nearly free and the
ground truth is already in the corpus: the planar subjects (`flat-on-ruler-cpl`,
`dime-flat-narrow-slices-cpl`) are flat to far better than a step, so their solved
z(r, θ) *is* the bowl plus a tilt term — **M-PHASE0-CURV is a corpus-only census**
that fits it once, caches it in the optical profile behind the existing gear guard,
and doubles as C7's astigmatism companion (the bowl is the mean of the sagittal and
tangential surfaces C7 maps separately). No stacker has the concept because no
stacker has a depth product to protect.

Products, in increasing ambition: depth + uncertainty TIFF (no stacker emits this);
surface normals from its gradient; the reshoot advisor upgraded to physical units
("bracket ended 0.8 mm short of the far edge — 11 more frames at your current step");
and **synthetic aperture re-rendering** — with depth, per-frame admission, and actual
captured defocus in hand, re-render the stack at any focal plane and any simulated
stop between "one frame" and "all-in-focus", by depth-consistent blending of
*captured* frames (selection with physics, no invented values — the hull discipline
extends naturally). A focus stacker whose output is not one image but a refocusable
object is a different product category, and every ingredient is already in the tree.

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
ops decision upstream of this item and should not wait for it.) One more consumer now
depends on this map: D8's split-half instrument reads static pattern as common-mode
signal (M115 P13 bounds it at 0.05–0.073% of scene signal on the flat corpus), and
C6's in-situ κ map is what lets D8 subtract rather than merely bound it.

### C7. Orientation-resolved election: astigmatism is a focus split, and no stacker looks

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
one lane, no captures, and the 2.2× suspect list shortens by one. If C10's retrieval
runs, its Zernike astigmatism term must agree with this measurement — two instruments,
one aberration, the cross-check free.

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

### C8. Active texture: one bracket of projected light, election where the scene has none

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
best-case ones. The same illumination-diversity family holds two cheaper siblings,
recorded here rather than as items: a **two-lamp pair** (one bracket per lamp
position) yields photometric-stereo normals as an independent regulariser for A5's
surface (`could not confirm` for stackers; classic otherwise — citation from memory),
and D3 already owns the −2 EV highlight arm.

**Kill bars:** on a textured subject shot both ways, speckle-elected z must agree with
self-elected z within σ_z (else the projection is moving the answer, not informing
it); cross-bracket registration must clear the same bar as intra-bracket; any
rendered-value contribution from the textured bracket is a defect by construction
(hash-assert the render reads clean frames only). Prior art: active illumination for
depth is classic (structured light, speckle DfD); *a consumer stacker with a
texture-pass capture mode* gets `could not confirm` pending search. Deliberately
opt-in, capture-side — but it is the only item in this file that helps the subjects
the focus measure is *physically blind* on, and no software item can.

### C9. Polarisation diversity: the filter is already on the lens

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

### C10. NEW — the phase channel: reading the half of the through-focus field nobody measured

**The mandate is the corpus's own.** Every through-focus statistic in this project —
the election, the parabola, M70's rank-1 decomposition, the asymmetry addendum — is
computed on **modulus**. M70 §14 names what that leaves on the table, in its author's
words: registration-aligned complex cross-spectra would bound the phase slack in every
reported gain (item 3), and would see the defocus asymmetry the modulus family is
"constitutionally blind" to — "**the single highest-value unmeasured thing M70
touched**" (item 4). It was never run. §16.6's unresolved ISO-correlated asymmetry
(five-for-five sign alignment, `corr = +0.755` on the powered stacks, formed and
half-rejected as an instrument defect) is exactly the kind of question the phase
channel answers cleanly, and §14 item 5's ISO-only bracket is its designed control.

**One instrument, four independent reads (ARGUED, physics DERIVED):**

1. **Sub-pixel registration at precision the spatial domain cannot reach.** A rigid
   sub-pixel displacement between two tiles is a *linear phase ramp* across the
   cross-spectrum — estimated from hundreds of coefficients jointly, weighted by the
   calibrated per-band SNR, rather than from one correlation peak's curvature. This is
   C4b's instrument for the within-DOF relative registration C1 needs (~0.1 px bar),
   and it is cheap: FFTs of tiles the solver already extracts.
2. **The sign of defocus.** The modulus of a defocused OTF is even in defocus for an
   aberration-free pupil; the corpus measured the family symmetric to ±0.077 (M70
   §16). But the rig is measurably not aberration-free (the 2.2× budget, §29), and
   the lens is measurably not telecentric (F §5.3) — and non-telecentricity converts
   defocus sign into *radial displacement* sign (C4c's term), while odd pupil
   aberrations (coma) put an odd-in-defocus component directly into the OTF phase.
   Either way the phase channel reads a **signed** per-frame defocus where every
   modulus statistic reads |z − ẑ|: the sparse-bracket sign ambiguity in A5's data
   term, resolved from data the fold already touches.
3. **The pupil itself — the 2.2× budget, decomposed.** The through-focus complex
   field of strong-texture tiles at *known* relative defocus steps (known because the
   breathing ruler C5 dates every frame in micrometres) is a **phase-diversity
   dataset** in the Gonsalves/Paxman sense: jointly estimate the unknown scene tile
   and a low-order Zernike pupil per field annulus. Prior art is mature and must be
   named — Gonsalves 1982; Paxman, Schulz & Fienup 1992; phase retrieval from
   through-focus stacks in microscopy (Hanser et al.); "Learning Lens Blur Fields"
   (arXiv 2310.11535) as the consumer-lens analogue; all citations from memory except
   the last (G-edof cites it), owed to this item's literature pass. What I could not
   confirm anywhere: *a shipping stacker that retrieves its own lens's field-resolved
   aberration state from every ordinary bracket and uses it downstream.* Downstream is
   concrete: D4 finally gets its **measured H** without waiting only on charts (M115
   killed OTF-from-curve-width; a curve width is one scalar per z — this estimator
   consumes the full 2D complex field at every z, with the defocus axis externally
   calibrated, which is precisely the difference between the killed idea and a
   measurement); C7 gets its astigmatism map as a cross-check; the §29 attribution
   question ("how much of the 2.2× is the TC?") gets an answer per annulus; and the
   product gets the map the project is named after — **a per-field Strehl ratio**.
4. **The contrast-inversion guard.** Past the first zero of a defocused OTF, structure
   returns with **inverted contrast** (spurious resolution). The corpus has already
   seen inversion once without naming it — the plane-gather arm's −0.4965 band
   correlation at 0.35 cyc/px (§2.4) — and C3 predicts it in the veil band at
   occlusions (a 60 px blur disc inverts everything above ~0.01 cyc/px — DERIVED,
   first zero ≈ 0.61/R). A per-band *phase-coherence-with-winner* term costs one sign
   bit per admitted coefficient and turns a class of silent destructive averaging into
   a refusal. Admission today is magnitude-only; this is the first physically
   principled reason to make it complex.

**Guards, stated with the design (the blind-deconvolution literature is a minefield
and the corpus already mapped part of it):** the joint scene+pupil estimate must
exclude the zero-blur hypothesis from its search space (Levin 2009's delta-kernel
trap — G-edof Q5 already folded this as a design rule); normalise per-slice to kill
the scale degeneracy (Köhler-style, G-edof Q5 caveat 1); and per rule 18, an
over-wide PSF estimate is the metric-friendly failure direction — the retrieval is
scored against the §30 chart the day the chart lands, and D4's use of its H stays
noise-budgeted and FRC-gated regardless. The retrieval runs as an offline per-stack
lane (minutes, not render-path), cached per rig behind the gear guard.

**Phase-0 gate (M-PHASE0-XSPEC, corpus-only, zero captures):** on two stacks, compute
registration-aligned complex cross-spectra of ~200 strong-texture tiles against their
elected-peak frame across ±5 steps. Report: (a) the phase noise floor vs the
calibrated SNR prediction (M70 §14 item 3's bound); (b) the odd-in-z phase component
and its field dependence (items 2/3's existence test — if it is below the floor
everywhere, the sign and pupil reads die together and the item collapses to reads 1
and 4); (c) the measured inversion census at occlusion tiles (read 4's evidence); (d)
the linear-ramp registration precision achieved vs the spatial-domain solver on the
same tiles (read 1's go/no-go, which is also C1's registration-wall answer). One lane,
no captures, and it prices the whole channel before anything is built on it.

### C11. NEW — aperture diversity: the second bracket that changes the physics

**The channel.** Everything in this file so far accepts the capture's one fixed
aperture. One additional bracket of the same subject at a second aperture (in-camera
bracketing handles it; cost ≈ minutes) opens four measured-physics reads at once:

1. **Blur-ratio depth (classic DfD).** Two apertures at matched focus give per-pixel
   relative blur whose ratio is a depth estimate with completely different systematics
   from the through-focus peak — prior art is foundational and named (Pentland 1987;
   Watanabe & Nayar 1998; citations from memory, owed to the pass). For A5 this is an
   independent data term that works *between* focus steps and on slopes where the
   peak is broad.
2. **Small discs exactly where veiling lives.** The veil and the crevice haze are
   made of defocused-foreground blur discs spilling across boundaries (ORCH-veiling
   §59.3); disc diameter scales with aperture. An f/11 arm's discs are ~2× smaller
   than the f/5.6 arm's, so near depth discontinuities the stopped-down bracket is
   systematically the cleaner evidence — while in the open field the f/5.6 arm
   carries the resolution (M88: its cutoff clears sensor Nyquist; f/11's does not).
   **Admission by depth (A5) does not care which bracket a frame came from**; with
   per-frame N_eff in the noise and MTF bookkeeping (the model already carries it),
   cross-aperture fusion is just more frames — selection *with physics deciding
   where each aperture is trustworthy*, convex, hull-safe.
3. **The PSF family, calibrated by sweep.** An aperture ladder at *fixed focus*
   (§29's existing ask, extended by one rung) measures the defocus family h(·; N_eff)
   directly against the same scene — the empirical anchor C10's retrieval and D4's H
   are validated against, and the direct measurement of the pupil factor p that M88
   §10 says the corpus cannot currently feed (p ∈ [1.31, 1.94] is the open interval
   gating every diffraction number).
4. **Fewer censored samples.** Stopping down un-pins speculars; the f/11 arm feeds
   B2 unclipped measurements of the same highlights (and C9's CPL rotation attacks
   the same pixels by a third mechanism — the planner can choose per subject).

**Prior art, named up front (fact-1136 discipline):** Hasinoff & Kutulakos'
**confocal stereo** (the aperture×focus image, AFI) is exactly this data cube, built
for depth via confocal constancy (citation from memory — verify in the pass);
aperture bracketing for exposure is folklore. What I could not confirm: *a stacker
that fuses two apertures for output quality* — resolution from the wide arm, boundary
cleanliness and highlight legality from the narrow arm — under a calibrated noise/MTF
model. The `could not confirm` label applies to that composite only.

**The cheap sibling — the deep-DOF guide frame.** One single f/22 frame per subject
(diffraction-soft but *everywhere-focused*, N_eff ≈ 66 at this magnification so soft
indeed — F §4.2) is: an occlusion-topology guide with no depth ambiguity, a
registration anchor spanning the whole bracket's focus travel (the cross-focus
correlation problem vanishes against it), and a photometric reference. The
flash/no-flash literature is the protocol's family (Petschnigg et al. 2004; citation
from memory); values never come from the guide (hash-asserted, as C8). Costs the
owner ten seconds per subject.

**Kill bars:** cross-bracket registration to the intra-bracket bar (same rig, static
subject — the easy case, but measured not assumed); the fused arm must beat the
better single-aperture arm on the veil instrument *and* not lose to the f/5.6 arm on
FRC in the open field; blur-ratio depth must agree with the through-focus ẑ within
joint σ on the twin. Phase-0: **one capture pair** (this is the one new item that
cannot be corpus-only), then a fusion prototype behind D1's instruments.

### C12. NEW — the quincunx green pair: two samplings, one shutter

**The geometry.** Every RGGB quad carries two greens sampling the scene offset by
(1, 1) sensor px — two interleaved lattices whose union supports spatial frequencies
up to the full sensor Nyquist along the axes, where either plane alone folds
everything past the *plane* Nyquist (0.25 cyc/sensor-px) — DERIVED, standard quincunx
sampling. Consequence: after removing the static G1/G2 imbalance (one calibration on
the delivered flats) and the local low-band content (shared), the **residual G1−G2
disagreement in a tile is the energy the scene carries between plane Nyquist and
sensor Nyquist** plus noise the model prices exactly.

**Three consumers, all cheap (the planes already exist in the fold):**

1. **A super-Nyquist focus cue.** The disagreement statistic responds *only* to the
   finest transmissible structure — precisely the band where Tenengrad's response is
   weakest relative to its noise, and the band that decides "critically sharp" from
   "nearly sharp". As a plugin operator through the existing registry (which
   calibrates its FOCUS_NOISE_SD automatically), it sharpens election exactly at the
   top of the ladder, and its through-focus peak is intrinsically narrower than any
   windowed gradient's. `could not confirm` any use of G1−G2 disagreement as a focus
   measure; the demosaic literature uses the pair for edge orientation (family named,
   owed to the pass).
2. **The SR go/no-go, per tile.** C1's 2× mode should only engage where alias energy
   exists to unfold; this statistic *is* that census, per frame, per tile, measured
   rather than assumed (feeding `phase_coverage`'s honest sibling,
   `alias_energy_present`).
3. **The per-frame noise/quality probe.** B1 uses the pair's difference as a σ
   cross-check; B5's PSF-quality arm uses the *ratio* of disagreement energy to
   gradient energy to separate "defocused" from "smeared" frames (a motion-blurred
   frame loses both coherently; a defocused frame loses signal but keeps its noise
   floor; the pair reads it within one frame, no neighbours needed).

**Phase-0 (M-PHASE0-QUINCUNX, corpus-only):** on two stacks, the disagreement
statistic's through-focus behaviour at elected-sharp tiles (does it peak, and more
sharply than Tenengrad?), its flat-ROI null against the calibrated prediction (rule
9), and its imbalance calibration residual on the flats. Kill: if the optics at
corpus apertures never put measurable energy past plane Nyquist (M88 says f/5.6
should; f/11 should not — the census answers per aperture), consumers 1–2 die and
consumer 3 stands alone under B1/B5.

### C13. NEW — the vendor's calibration payload: the profile that ships inside every frame

**The find (F §4, MEASURED-LOCALLY there):** every ARW in the corpus carries Sony's
own correction tables for this exact lens+TC — `DistortionCorrParams` (16 radial
knots), `ChromaticAberrationCorrParams` (**32 knots: two 16-knot per-channel radial
splines for R and B**), `VignettingCorrParams` (all zeros for this lens — a measured
no-op, do not build on it). LensFun does not cover this lens; Adobe LCP is absent and
licence-encumbered; this payload is "the only per-lens profile source that actually
covers this lens" — and strehl reads none of it.

**Why it matters now, not eventually:** the shipped lateral-CA model is *one scalar
per channel* (`eps_r`, `eps_b`) composed into the similarity — and it is measured
**net-beneficial and over-corrected at the same time** (fact 1865: hue-neutral edge
score 0.160 corrected vs 0.208 off, yet the correction drags red past zero to the
wrong side), with the re-fit landing outside the range of the six measurements quoted
beside it (STATUS §3.1.1). That is the signature of a scalar fit to a quantity that
is actually a radial *profile*. A 16-knot spline can be right at every radius where
one number cannot. The same payload's distortion knots (peak ≈ −1.5%, ≈ 50 px at the
edge — F §6.1) seed C4a's residual field deterministically, and distortion is the
term that does not commute with the scale the warp already applies (F §5.3).

**The licence fence, explicit (see §2.2 hazard 6):** F's own §6.1 quotes GPL source;
the implementer of this item must not read those blocks. The clean route is entirely
sufficient: tag IDs, element counts and offsets are uncopyrightable facts (AGENTS'
ExifTool rule); the arrays are read by a small independent TIFF/maker-note walker in
`strehl-raw` (rawler is linked-not-read and does not expose them); and the *semantics*
— knot spacing along the diagonal, the /10.24-percent scaling — are recovered
clean-room by **fitting the decoded knots against strehl's own measured CA profile**
(the corpus owns leave-one-out-validated eps measurements at 0.071 px corner residual
to fit against), which is both the licence-safe derivation and the item's own
validation. Where interpretation cannot be pinned by measurement, the channel is
refused, in the house style.

**Acceptance:** on `highly-angled-ruler-mm-cpl` (the subject still showing the lens's
natural opposite-sign pattern — the control the scalar model fails), the spline
correction beats the shipped scalar on the hue-neutral instrument with the flat
placebo unmoved; the TC-off capture (§29) separates base-lens from TC terms the day
it lands; composition stays single-interpolation (the whole reason CA correction is
free today). Kill: if the payload's knots, decoded and fitted, disagree with the
measured profile beyond [bar] at every plausible semantic, the payload is untrusted
for this body and the item closes as a documented null.

---

## 7. Workstream D — the instrument and the product

### D1. The scorecard, built once, first

Everything §1 defined, plus the build-order discipline: **instruments before
features.** The FRC spine (R25(iv): cannot be fooled upward by noise amplification);
the split-half SNR channel (M115's §2 design, the best-commissioned instrument in the
corpus — reuse it verbatim, and D8 productises it); the slanted-edge SFR estimator
that already exists validated to 114.6 cy/mm (M88 §2) pointed, at last, at something
sharp (§30 chart); planted-defect commissioning for every axis (the blur-plant
detector already proved potent at 0.3–0.4 px — README); the V-RIM specificity lesson
baked in as a rule (an instrument that convicts a raw camera frame convicts nothing);
SSIMULACRA2/butteraugli for the perceptual axis (never dssim — licence). Comparators
pinned and priced: licensed Zerene (PMax *and* DMap — DMap has never rendered here and
is A5's true comparator), the fork rebuilt at its best-known build (2.4× is the honest
speed quote against it), Helicon if obtainable. Every scorecard run archives hashes
and sidecars under the banked-purge discipline so no result ever becomes
unreproducible the way V-RIM's 5-of-14 did.

**The bootstrap MTF from the corpus's own edges.** M88's verdict was "nothing sharp
enough to point at"; the §30 chart fixes that properly. But the stack itself contains
a partial substitute available *now*: every strong edge's through-focus sequence of
edge-spread functions is an empirical defocus family, and its envelope at best focus
is the system ESF at that field point — width-limited (the corpus's edges are 13–18 px
against the instrument's 5.13 px validity bound), so it cannot answer the comparator
question, but it *can* map relative MTF across the field, feed C7's orientation split,
and give D4 a provisional H (C10's retrieval, if it survives phase 0, supersedes this
bootstrap with a physically-parameterised version of the same information).
Commission it against the §30 chart the day the chart lands; if they disagree beyond
[bar], the bootstrap dies and the chart stands alone.

### D2. The certified-acuity map — "which file am I holding"

README names the gap: the tool hands over a print-worthy file or a soft one and does
not say which. The unified merge knows, per pixel and per band, whether the admitted
set cleared the calibrated floor. **Formal spine (DERIVED, to be commissioned like any
instrument):** per pixel and band, the admitted set's Fisher information is
I = Σ 1/σ_i² (inverse-variance weights make this exact under the model; B6's
stabilised domain makes the bookkeeping level-independent), so the merge carries a
per-band CRLB σ_cert = 1/√I; the **certified acuity** is the highest band whose
reconstructed signal clears [bar]·σ_cert. Collapse to: per pixel, an acuity in
cyc/px (orientation-resolved if C7 lands); per image, the field-coverage summary
README says is the honest form of the quality claim (fraction of field certified at
≥ band k).

Two channels now stand beside the model-based one, so the map cannot be a
self-fulfilling model artefact: **D8's empirical per-tile FRC** between half-stack
renders (agreement between two independent realisations, blind to the model), and a
single-image decorrelation estimate where halves are unavailable (Descloux 2019 — the
corpus already cites it via G-edof). Where model and empirical channels disagree
beyond their joint bars, the map *says so* — disagreement is a defect flag, not an
averaging opportunity.

This is the instrument-grade output that separates "retouch this" from "reshoot this"
from "print this", it costs no new measurement machinery beyond A1/A4/D8, and no
shipping stacker has anything like it. It becomes the print gate's input, replacing
the broken clip/crush statistics called out in STATUS §3.2.14, and ships in the file:
the render's manifest (already carrying build id, ICC, develop statement —
ARCHITECTURE §9) gains the acuity summary, the per-axis scorecard verdicts, **and the
hull certificate** — the out-of-hull census result (0.0000% or the exceptions, with
coordinates) stamped per render, which in the current era is a differentiator worth
stating plainly: *this file provably contains no invented values*.

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

**Planner content, each row measured or derivable from the profile today:**
- **Second-base-ISO advice.** The body's read noise falls 4.20 e⁻ → 1.24 e⁻ at ISO
  400 (profile; F §2.3's full table, including the measured fact that **ISO 320 is
  the single worst setting on the camera**, 1.2 stops of DR behind ISO 400) — for the
  dim long-exposure macro this corpus actually shoots, base-ISO choice is worth more
  than most algorithms, and the planner should print it. B5 warns at decode time as
  the backstop.
- **Repeat-bracket and burst-per-step modes.** Photon count is the only free noise
  lever left once ETTR (§22) is taken; two identical brackets cost linear time and the
  merge already folds them (admission by z does not care which bracket a frame came
  from once A5 lands). The planner prices "2× bracket" against "wider gate" honestly —
  and a repeated bracket is also D8's gold-standard FRC pair (two fully independent
  realisations, where the split-half shares fixed pattern).
- **Aperture-pair mode (C11)** priced per subject: blur-ratio depth and occlusion
  cleanliness against the extra minutes; the f/22 guide frame suggested by default.
- **Interleaved half-step passes** (R16's surviving half): a repair for a diagnosed
  coverage gap, never a default — M27's criterion is the diagnostic, and M30's fact
  240 (photon budget indifferent to the split) is why it is free.
- **The −2 EV highlight arm** (M30) triggered per stack from
  clipping-at-gathered-frames, which is the census B2 wires in; C9/C11 offered as the
  specular alternatives.
- **Capture-defect classifiers** (B5) surfaced at plan time: lossy-RAW, IBIS state
  (with the C1 exception noted), OSS-on, ISO 320, EFCS at speed.
- The standing capture asks it should nag for, by owner cost: grey card in frame
  (§20), ETTR (§22), static repeat burst (§12), aperture ladder + TC-off (§29), the
  §30/§32/§33 instrument set, ≥400 px clear-background subject (fact 1891), IBIS-ON
  bracket (C1), CPL-rotation pair (C9), aperture pair + f/22 guide (C11), ISO-only
  bracket (M70 §14 item 5 / C10), darks at working exposure (§28).

### D4. Measured-PSF restoration — conditional, last, honestly bounded

M115 killed multi-frame deconvolution and the curve-width OTF; it did not kill
single-pass restoration under a *measured* system MTF — it never had one to test
(M88). And §29 sharpened the stakes in both directions: the system is ~2.2× softer
than diffraction (two instruments, 4%), so a real, optics-shaped blur budget exists
that only restoration can spend — and ≤76.6% of it being optical is an upper bound
from one printed target, so the budget's true size is unknown until the chart and the
razor-blade edge land. The existing `restore.rs` is the template of the honest shape:
exact H, noise-budgeted gain, no ringing because the calibrated noise stops it first.
After §30 (or provisionally after D1's bootstrap MTF, or C10's retrieval if it
survives): measure the composite MTF (optics × gather × merge — noting C1 at 1×
deletes the gather term), extend H accordingly, keep the same noise budget, gate on
FRC and the split-half instrument, flag any pixel the restore moves beyond its sample
hull (the D2 certificate then reports restoration separately — the base render's hull
claim is never diluted). Expectation management is part of the design: the
*information* is fixed; this stage trades the noise budget B1 certifies for contrast,
no more. If FRC shows no gain, it ships as the measured negative beside M115.

### D5. The performance budget

Quality features above must fit inside roughly 2× the current wall clock or they will
not ship as defaults. Known prices and offsets: the two-pass unified merge measured
~2.2× once (56.3 → 124.7 s at N=79, fact 1939 — one kernel, one N; re-price in lane);
A5's v0 solver is two DT-filter passes over one plane (cost ~one extra band, trivial);
C1 at 1× *removes* 299 Malvar demosaics and a 503 MiB/warp transient
(`align_cmd.rs:1794–1804` — sign: faster and smaller, to be measured); D8 doubles
accumulator memory when engaged (priced against the planner's budget, and it engages
on demand); SIMD is untouched headroom on a fold that is 98.5% of the run (zero
`std::simd`/intrinsics in 93 kLOC — ARCHITECTURE §11); GPU stays optional and
non-contending (M7: 173× on a stage worth 0.40–0.57% of wall; a separate crate per
STATUS §3.3.11) — but see D9, which removes the determinism obstacle that has kept
both parallelism levers locked; the memory planner must start pricing the fullres
transient it currently understates (12.5–13.4 GiB measured against a 5.2 GB printed
plan — same file) for as long as that path ships. Determinism rules stand: every
reduction-order change is a freeze event; the byte-freeze registry now has a pyramid
row (fact 1982) and needs its **aligned** pyramid sibling before phase 1 touches the
warp path. D5 is the *defensive* speed item — the budget that keeps quality features
shippable. The *offensive* program — taking the wall to the hardware floor rather
than merely holding it — is D11–D15 below, and D9 is the hinge between them.

### D6. The plugin surface, resolved by A1/A5 rather than by more traits

Today the only real seam (focus measures) is refused on the default backend — "the
plugin surface and the shipping path do not intersect" (ARCHITECTURE §8). The unified
merge decides this properly: pass one (election/depth) consumes a focus field again,
so the calibrated `FocusMeasure` seam becomes live on the default path for free — and
A5 gives plugins a sharper contract (respond + curvature ⇒ ẑ, σ_z) that the registry's
existing calibration machinery already knows how to certify (C12's quincunx operator
is the first new client). Alignment models, optical profiles and output stages stay
data-plus-enum until a second consumer exists — SYNTHESIS §9's rule against
pre-building seams has been right every time it was tested.

### D7. Colour and print polish

Landed and cheap to keep: ICC + 300 DPI in the deliverable (fact 1916); the print gate
now closes 33/33 with 0 FAIL and 0 unresolved (facts 1966–1968), so this workstream is
maintenance plus two decisions: the owner's paper profile (§31 — outranks any code
change for print) with a soft-proof gamut census against it, and the
per-channel-vs-per-luminance tone decision STATUS §3.2.14 says nobody has authorised —
take it to a decision memo with the print gate's numbers attached. The dust-ON default
(STATUS §1's recommendation, pending the cache-key resolution) belongs in the same
decision memo: every delivered master currently carries both motes. B7's dither/float
decision joins this memo the day its LSB/σ measurement exists.

### D8. NEW — split-stack self-calibration: the stack contains its own ground truth

**The observation.** The best-commissioned instrument in the corpus is M115 §2's
split-half channel: fold two interleaved disjoint half-stacks through the entire
pipeline, each re-deriving every data-dependent weight inside its own half; the
cross-spectrum of the two outputs is signal (independent noise cancels in
expectation), the half-difference is noise, and the construction was validated with
planted blur recovered at 0.9938–0.9974, gain-invariance to 0.54% under filters that
moved naive metrics 8.25×, and an exact `(P(A)+P(B))/2 = P_sig + P_noise` identity.
FRC is its resolution-domain twin (G-edof §6.2: "a sharpness metric that cannot be
fooled upward by noise amplification"). Both live today in Python, in reports. **Move
them into the product**, as a per-stack mechanism with three faces:

1. **Per-stack tuning with an ungameable objective.** A1's admission width k (and the
   handful of constants like it) stops being a compiled number *or* a per-corpus memo:
   per stack, sweep k over the re-renderable statistics (B7 makes the sweep nearly
   free — two extra accumulator sets folded in the same pass, then cheap re-collapses)
   and pick the k that maximises split-half band SNR at matched contrast — the exact
   statistic M115 built, which post-sharpening cannot inflate and which noise
   amplification cannot fool. The Noise2Noise principle (two noisy realisations of
   one latent suffice for supervision; Lehtinen et al. 2018, citation from memory)
   applied not to train a network but to *calibrate five constants per stack*, which
   is the culture-compatible form. The 2.0-vs-4.5 war ends with each stack carrying
   its own measured optimum and the banner printing it.
2. **The empirical acuity channel.** Per-tile FRC between the two half-renders is a
   spatially-resolved, model-free certified-resolution map — D2's second channel. A
   tile where the halves agree to 0.35 cyc/px *measured* that resolution; no model
   assumption can inflate it.
3. **The shipped null.** `strehl null <dir>` renders the half-difference image — the
   merge's own noise, as a picture, per stack. Every argument this project has had
   about "is that grain or structure" gets a per-stack empirical answer a user can
   open.

**The priced confounds, from the corpus's own record:** fixed-pattern structure is
common-mode to any split of one capture (M115 P13: 0.05–0.073% of scene signal on the
flat corpus — bounded, and C6's in-situ map upgrades the bound to a subtraction);
quantisation error is correlated between halves (P18/P19: a difference-based
estimator under-reports it 16× — so B7's rule that no measurement path ever sees
quantised intermediates is load-bearing here); and a *repeated bracket* (D3) is the
gold form with fully independent realisations, which the planner recommends whenever
the user's tolerance allows. Odd/even interleave splits the z-axis at double step —
fine at corpus densities (2–4× oversampled, M27), and the planner knows when it is
not. **Prior art posture:** FRC and split-half validation are standard instruments
(named above); `could not confirm` any shipping stacker that self-tunes per stack
against a split-half objective or emits an FRC-certified resolution map.

**Acceptance:** the per-stack k optimum reproduces the corpus-measured FoM ordering on
`109MSDCF` (README's table) without being shown it; planted-defect commissioning
inherited from M115 §2 re-run in the Rust port; tuning must move zero bytes when
disengaged (hash), and its objective must be blind to the D2 model channel (no shared
inputs beyond the render). Kill: if the port cannot reproduce M115's identity checks
to [bar], the product form dies and the instrument stays offline in D1.

### D9. NEW — determinism decoupled from workers: the tax refund, then the GPU door

**The problem, priced by the corpus:** float addition is non-associative, so the
worker count sets the reduction order and would make output host-dependent; the
pyramid path therefore derives workers from memory alone and **pays 1.29× against 8
workers on a 16-core part** (ARCHITECTURE §9), and GPU work has been structurally
excluded from the merge (atomics reorder sums). Both are one design decision, not two.

**(a) CPU: fix the reduction lattice, not the worker count.** Partition frames into a
**fixed number of chunks independent of the worker count** (say 32), each chunk an
accumulator, workers stealing chunks; absorb chunk partials in fixed chunk order.
Bytes are then invariant to worker count *by construction* — the freeze rows stop
depending on the memory planner — and `available_parallelism()` becomes usable on the
default path. DERIVED cost: 32 accumulator sets instead of 4 is the only price, and
the existing per-worker cost model already knows how to cap that (chunk count can be
memory-derived once, globally, and *recorded in the banner* — it, not workers, is now
the determinism parameter). This is a freeze event once, with the aligned-pyramid row
in place first (D5), and it refunds the 1.29× immediately.

**(b) GPU: integer accumulation makes the sum associative.** Samples are u16; weights
quantised to fixed point (e.g. 16 fractional bits); per-pixel Σw·v and Σw accumulate
in i64 — associative, commutative, so *any* schedule, including GPU atomics, produces
identical bytes. DERIVED headroom: 16-bit sample × 16-bit weight = 32 bits per term;
×299 frames adds ~9 bits; ~41 bits total against 63 — comfortable. Weight
quantisation truncates only weights below 2⁻¹⁶ of the winner's, which the admission
rule has already effectively zeroed. This does not commit the project to GPU; it
removes the *principled* obstacle, so M7's "wrong stage" verdict can be re-asked about
the fold itself (98.5% of the run) with determinism off the table as an objection —
in a separate crate, non-contending, per STATUS §3.3.11.

### D10. NEW — the live capture loop: the reshoot advisor, before the rig moves

**The observation.** The fold is already streaming — decode, fold, drop, O(workers)
memory (ARCHITECTURE §9) — which is exactly the shape of a *live* consumer. Tethered
over USB (Sony's camera-remote SDK lists recent bodies; support for this body is
UNVERIFIED and is the item's first check), frames fold as they land, and by the time
the bracket ends the tool already knows: coverage against the planned depth span
(M27's criterion, live), the certified-acuity forecast per region (D2's summary at
preview resolution), per-frame ledger anomalies (B5 — "frame 212 is soft, likely
vibration; reshoot from 205"), and the one thing no post-hoc advisor can deliver:
**"extend the bracket 11 more frames — the far edge is 0.8 mm short"** *while the
subject is still on the rail and the light is still on.* The reshoot advisor's whole
category exists because this feedback currently arrives hours late; the corpus's
capture-limited verdicts (10 of 14 defective subjects — README) are the measured cost
of that latency.

**Scope honesty:** Helicon Remote already drives cameras and computes DOF-based step
plans (named prior art; citation from memory) — tethered *bracketing* is not the
claim. The claim is the closed loop: live fold, live certified coverage, live
per-frame quality, against a calibrated model of this rig. `could not confirm` that
composite in any shipping tool. Sequenced last in D because it is product surface
over B5/D2/D3 machinery that must exist first; phase-0 is a one-day SDK feasibility
check (body supported? RAW streaming latency? tether stability under a 299-frame
bracket?) that can kill it for free.

### D11–D15. NEW — the speed program: from measured-fast to the hardware floor

**Where speed actually stands, from the corpus's own instruments.** The default path
folds 299 × 33 MP in **116.88 s at 63% machine-busy (best observed), ~102 s anchored
idle**, with the fold at **98.5% of the run** — decode, registration lookup, collapse
and the 198 MB write together cost 1.8 s (BUILD-SPEED §2). Scaling is
`wall = 1.11 s + 0.768 s × N` (R² 0.9976), really a staircase of `ceil(N/4)` rounds —
N=33 is the measured worst case at 1.00 s/frame against 0.78 (§4). The child burns
**510 CPU-seconds best** = 1.70 core-s/frame on a 16C/32T part. Meanwhile workstream D
priced this machine's envelope in advance and its FU1.3 budget is blunt: on this
hardware the pipeline should be **decode-bound**, with all GPU-suited work for 60
frames costing 0.5–0.8 s at the measured 1500 GB/s VRAM and 56.9 GB/s pinned-PCIe
rates, and CPU LJPEG decode dominating "by a factor of 2–8× over all GPU work
combined."

**The floor, DERIVED from D's measured rates (assumption flagged):** 299 frames
decode to 299 × 66 MB = 19.7 GB of u16 CFA; at D's assumed 60–200 MB/s of output per
core × 16 cores that is **6–21 s of decode**; the fold's GPU-suited work scales to
**~2.5–4 s**; 11.3 GB of NVMe read ≈ 2.3 s overlapped; write 1–2 s. End-to-end floor
≈ **7–25 s against today's 102–117 s: 5–10× of headroom**, all of it gated on one
number nobody has measured — per-core LJPEG throughput — which D's FU1.3 already
called "the single number worth measuring first… the highest-value measurement in the
project." It still has not been taken. The program below is ordered so that number is
taken first and everything else is priced against it.

**The claim this program buys, in product form:** in-camera bracketing shoots at
roughly 0.2–0.5 s/frame; a fold that sustains ≤0.15 s/frame *keeps pace with the
shutter*, and combined with D10 the deliverable becomes **"the certified master is
ready seconds after the last exposure"** — a speed claim stated in the user's units,
which no comparator is within an order of magnitude of (the fork: 13.93 s/frame;
Zerene's own log: 0.82 s/frame excluding load, save and the human — README).

#### D11. Decode first — measure it, overlap it, then own it

1. **M-PHASE0-DECODE (the gating measurement, one evening).** A `divan` benchmark
   over real A7C II ARWs: single-thread and full-machine decode throughput, and the
   thread-scaling curve of the shipped decoder treated as a black box. This
   re-establishes legally what workstream D read out of rawler's source (§2.2
   hazard 6): whether intra-frame parallelism exists and saturates. Everything in
   D12–D14 is re-priced against its result; if decode measures ≥1 GB/s aggregate,
   the floor argument above is conservative and the program accelerates.
2. **The overlap seam.** Today each worker runs decode → warp → fold serially, so
   entropy decode and band arithmetic alternate instead of overlapping. Split them:
   a decode pool feeding fold workers through a bounded channel (bound = the
   existing memory plan, so peak stays O(workers)). If decode and fold are within
   2× of each other — which the CPU-second arithmetic above suggests — overlap is
   worth up to ~1.7× on its own, and it is precisely the seam D's consequence #2
   said to build so the consumer loop can change later without a rewrite. It also
   halves the pain of A1's two-pass structure, whose second decode of every frame
   is the priced 2.2× worst case (fact 1939).
3. **The long play, strictly behind the benchmark: an owned tile decoder.** Sony
   lossless-v2 ARW is tiled LJPEG (SOF3) in a plain TIFF container — public specs
   (ITU T.81, TIFF/DNG), clean-room implementable without reading any LGPL source.
   Per-tile parallelism plus AVX-512 multi-symbol Huffman tables is credibly 2–4×
   per core over a generic decoder (ARGUED — this is the standard result for
   vectorised entropy decode, to be proven by the benchmark not asserted).
   Side-effect worth naming: it removes the LGPL relink constraint from the core
   binary's hot path (rawler remains linked for probe/other formats). Kill bar:
   build only if M-PHASE0-DECODE shows the shipped decoder both ≪200 MB/s/core
   *and* dominant after D12 — otherwise the seam plus the shipped decoder is the
   whole answer.
4. **The decoded-plane cache, small and optional.** B7's re-renderable master
   already removes re-decodes from re-renders. For iterate-heavy workflows (D8
   sweeps, C-item lanes), an LZ4-compressed u16 plane cache keyed like the warp
   sidecar (~10 GB per 299-frame stack) turns every second run decode-free. Off by
   default; banked-purge rules apply.

#### D12. The fold kernels — SIMD and fusion, behind the freeze

The fold's arithmetic per frame is a dozen-plus full-plane passes: defect apply,
warp gather (today a full per-frame Malvar — C1 at 1× deletes it), CFA deinterleave,
luma, a 7-level Laplacian plus a Gaussian noise pyramid, per-band `smooth5`, weight
and accumulate on four planes. DERIVED, order-of-magnitude: ~30 plane passes ×
132 MB ≈ 4 GB of traffic per frame, ≈ 60–70 ms at achievable DDR5 rates — against a
measured 385 ms/frame. The gap between those two numbers is the SIMD-and-fusion
budget, and it is consistent with a tree that contains **zero SIMD in 93 kLOC**
(ARCHITECTURE §11).

- **Vectorise with the stack workstream D already vetted:** stable `core::arch`
  AVX-512 intrinsics (stable since Rust 1.89) wrapped in `pulp`, dispatched by
  `multiversion` — explicitly **not** `std::simd`, which is nightly-only and
  carries an open Windows-MSVC heap-corruption bug at 512-bit widths
  (rust-lang/rust #154152; D §1.6). First targets, by suspected share: the
  soft-power/admission weight's per-coefficient `exp(p·ln r)` (DERIVED: ~15M
  transcendental pairs per frame on the luma bands — a fixed-polynomial vector
  exp/log is ~10× on exactly that; *fixed* polynomial, because the approximation
  is a byte-freeze event once, not a per-build roulette); the separable binomial
  and `smooth5` passes; deinterleave+black-subtract; the Catmull-Rom gather;
  FMA accumulation. Discipline: each kernel lands bit-exact against its scalar
  twin where achievable, else as one declared freeze event with the old/new hashes
  recorded — never silently.
- **Fuse the passes into a strip pipeline.** A line-buffered multirate pyramid
  (classic streaming decomposition) lets a decoded strip flow through
  gather → deinterleave → bands → gate → accumulate while resident in cache;
  DERIVED, the line-buffer state for all seven levels is a few MB — trivially
  resident even in the 32 MB CCD, never mind the 96 MB V-Cache CCD the 9950X3D
  carries (D §2.2). Expected 1.5–3× from traffic alone; `tracy` timelines (D
  §1.10) decide, per kernel, before and after.
- **CCD-aware scheduling, measured not assumed:** decode is branchy with a tiny
  working set (frequency CCD); strip kernels are bandwidth-hungry (V-Cache CCD).
  D §1.7's own caution stands — rayon's stealing self-balances, so pinning ships
  only if a pinned-vs-unpinned A/B clears a bar.
- **Free single-digits:** PGO + fat LTO + `codegen-units=1` (byte-safe in Rust —
  the compiler does not reassociate float arithmetic — and verified against the
  freeze rows anyway), typically 5–15%.

#### D13. Scaling — all sixteen cores inside the same six gigabytes

The worker sweep measured 1→2→4 workers scaling at 2.00×/1.71× and 4→8 at 1.29×
even on a loaded box; 8→16 was never measured, and the 4-worker cap exists only
because workers each carry ~1.3 GB of accumulators against the 6 GiB budget
(BUILD-SPEED §7). Three decompositions, in rising order of surgery, each byte-safe
once D9(a)'s fixed reduction lattice is in:

1. **Budget honesty:** scale `MEMORY_BUDGET_BYTES` with installed RAM (64 GB box,
   6 GiB budget) — BUILD-SPEED's own ARGUED ~1.3× — with the printed plan telling
   the user what was chosen and why, and the chunk lattice keeping bytes invariant.
2. **Chunk-parallel with shared-nothing partials sized to chunks, not workers**
   (D9(a) as shipped): more workers stop costing more accumulator sets than the
   fixed chunk count.
3. **Spatial cooperation within a frame:** workers own disjoint output strips of
   *one shared* accumulator (disjoint rows — no races, fixed assignment — no
   reduction-order change), which kills the `ceil(N/4)` staircase outright (the
   measured N=33 worst case), scales to thread count on any N, and drops
   per-worker memory to line buffers. The engineering risk is the pyramid's
   cross-strip halos; the line-buffered wavefront in D12 is the natural carrier.
   **M-PHASE0-IDLE prices all of this for free:** re-run the worker sweep on an
   idle box, 1→32 workers plus a fine-N ladder to resolve the staircase directly —
   one evening, no code.

#### D14. The GPU, decided the corpus's way — wgpu-only, whole-fold, after decode

Workstream D already made the expensive decision correctly and it should be kept:
**cut CUDA** (FU1.1: every advantage summed is ≤1.2× on GPU stages ≈ 1–3%
end-to-end; tensor cores confirmed irrelevant at <0.5–20 FLOP/byte), ship one
excellent portable `wgpu` backend behind a per-kernel `ComputeBackend` seam —
subgroups, f16 for bounded fields, i16 storage are all present and sufficient
(D §3), and **u16 stays the storage type for linear sensor data** (f16's 10-bit
mantissa is *worse* than u16 there — D's own caveat, and rule 1's origin). M7's
lesson binds: 173× on a stage worth 0.5% of wall is worth nothing — the offload
unit is the **whole fold** (gather → bands → gate → accumulate), with collapse and
write staying on CPU. Upload is a non-issue (66 MB/frame ≈ 1.2 ms pinned,
measured). Determinism is D9(b): i64 fixed-point accumulation plus
lattice-quantised weights makes the sum associative — the ambition is
**cross-vendor byte-identity**; the fallback is per-adapter freeze rows and `--gpu`
staying opt-in with CPU as the reference implementation. Sequencing is the honest
part: the GPU is **not the bottleneck** (D FU1.3) and folding on GPU before C1
settles the reconstruction would mean writing the kernels twice — so D14 waits for
D11's number (can decode feed ≥30–60 frames/s?) and phase 3's 1×-lattice merge,
then lands as: decode on CPU, everything after the channel on GPU, end state
decode-bound by construction. Expected end-to-end at that point, DERIVED from the
floor arithmetic above: **~7–25 s warm for 299 × 33 MP; ~0.02–0.08 s/frame** —
with the CPU-only path targeted at ≤0.15 s/frame via D11–D13 alone (provisional
until M-PHASE0-DECODE, and stated as such).

#### D15. The cold path, the write path, and the speed scorecard

- **Cold ingest:** cold-minus-warm is the 73.4 s registration solve plus uncached
  reads (327 s observed at 99% busy). Readahead via IOCP (`compio` — D §1.8;
  DirectStorage examined and rejected there) hides the 2.3 s of NVMe behind
  decode; **M-PHASE0-NVME** replaces D's assumed 5 GB/s with a measured number.
  The solve program: the ZNCC tile measure is embarrassingly parallel and
  unvectorised — parallelise and SIMD it, prune the span ladder against the
  per-frame gauge that actually feeds the merge (M103's lesson: score what the
  consumer reads), budget its measured 9.3–10.5 GB peak into the printed plan, and
  make it incremental for D10's live mode. Target: cold ≤ warm + 20 s, stated as a
  bar not a promise.
- **The write path:** today's 1.2 s collapse+write is fine; B7's float/tiled
  output requires the owned tiled-BigTIFF writer anyway (`image-tiff` cannot write
  tiles — D §1.4, ~500 lines), built with per-tile parallel compression from day
  one.
- **The speed scorecard, pre-registered like every other instrument:** the
  BUILD-SPEED harness discipline becomes permanent — busy-fraction beside every
  wall clock, rule-16 alternating sweeps, idle-box arms, per-stage banner timings,
  cold and warm as separate axes, comparators re-timed under the identical
  protocol at matched output. Targets registered before the work: **hold** ≥2×
  the best comparator build at matched output (today's honest 2.4× must not decay
  under phases 1–2, per D5); **extend** to ≤0.15 s/frame CPU-only and
  ≤0.06 s/frame hybrid at 33 MP (both provisional on M-PHASE0-DECODE, revised
  once with its number and frozen after); memory ≤6 GiB warm; bytes invariant to
  worker count (D9a); the staircase gone (per-frame cost flat in N mod 4). And
  the product-form target that ties to D10: **master delivered ≤10 s after the
  last shutter of a 100-frame bracket.** Every number that meets a bar is quoted
  with its busy fraction; every number that misses publishes as itself, in the
  house style.

---

## 8. What this proposal deliberately does not contain

Respecting the graveyard is half of what the corpus is for. Each row names the one
condition that would reopen it; absent that condition, re-proposing these is noise.

| Killed idea | Killed by | Reopens only if |
| --- | --- | --- |
| Multi-frame Wiener / matched filter across focus as the merge | M20, M70, M115 — three instruments, one answer (R_SNR 1.0014 [0.965, 1.038]); §3.0 derives the collapse from rank-1 | A future merge stops harvesting off-peak frames (it will not — A1/A5 harvest more) |
| OTF self-calibration from through-focus **curve width** | M115 §5 (1.87–2.15× bias, wrong shape) | Never for deconvolution. C10's phase-diversity retrieval is a *different estimator on different data* (full complex fields at externally-calibrated defocus, not a scalar width) and must beat the §30 chart to be believed — it does not reopen this row, it routes around it, and it dies its own death in phase 0 if the odd-phase signal is not there |
| Sub-step "peak completion" — extrapolating the through-focus curve to its unsampled maximum | M70's rank-1 structure (0.9959); M33 prices the loss (median 4.64% of response); M115's hull census shows what extrapolation does | A measured, field-dependent defocus family from the §30 chart changes the rank-1 premise — re-derive before proposing |
| **Per-pixel** outlier / robustness rejection at merge time | Refused **five** times; M123 fired on 29.55% of a stationary subject; a second mechanism 21.5× more active on the unmoving stack | A detector with pre-registered FPR commissioned on the §12 static repeat burst — and only behind the reshoot verdict. **B5's per-frame quality arm is not this row**: O(N) whole-frame state, not O(N·px) masks, and it carries that same commissioning requirement anyway |
| Confidence as a scalar (entropy or otherwise) | M32, M34 — no monotone scalar is faithful | Nothing. Ship the vector |
| The significance exponent as the flat-region fix | Facts 1974–1975 — benefit saturates by z=100, cost does not; own prediction falsified | Nothing. A1 supersedes the question |
| Alignment shrinkage correction | M12 — 0/18 transfer, worst case 83.4× worse | Nothing |
| Metacalibrated edges | M23 — the "response" was the probe's own resampler | Nothing; R5 blur-equalisation is the surviving heir, behind its self-pair control |
| Adaptive `--target-n-eff` rule | M64 (refuted on M52's own numbers) | A1's calibrated admission width supersedes; D8 gives the calibration its objective |
| Chained alignment, in any disguise | Rule 6, M10, M103 | Nothing. C4 adds residual layers to the *global* solve |
| Post-hoc smoothing of the winner/index field as a cosmetic filter | M120's lesson; the edgeaware guide finding (a haloed field cannot guide itself) | Nothing — A5 is the joint-estimation form and is the only depth-smoothing this file proposes |
| Per-frame demosaic quality as a battleground | M104b, M118, ORCH-kernel-decision — kernel datasheets, not photograph facts; §2.4 shows the ground itself is unstable | C1 dissolves the question rather than answering it |
| PDAF, as mask or as depth | F §2.5 — no published pattern, prior recovery RED, baseline gone at working apertures | Sony documents the pattern for this body |
| Black tracking from optically-black photosites | `strehl-raw/src/lib.rs:10–15`, F §2.2 — the padding is exact zeros | A decode path that exposes real masked sensels |
| Field curvature as an *image-quality* model | F §6.5 — per-pixel election absorbs it exactly | Nothing for the image. C5 measures it **for the depth product only**, which F's argument does not cover |
| Deep MFIF / learned fusion on the default path | Risk 3 (domain: 2-image, low-res, synthetic) | Only ever twin-trained (R24's covenant), only ever opt-in — the A5 ordinal prior included |

---

## 9. Sequencing

Ordered so that every expensive build is preceded by a cheap measurement that can kill
it, and every claim-bearing phase lands after its instrument. Lane names follow house
convention. Zero-capture phase-0 measurements are deliberately front-loaded: **six of
the eight items new in revision 2, and ten of the sixteen new in revision 3, can be
killed or confirmed without the owner lifting a camera** (three of those ten are
machine measurements rather than corpus computations — D11's decode benchmark, D13's
idle-box sweep, D15's disk-rate check — and cost an idle evening, not a session).

**Phase 0 — measurements and purchases (corpus-only + one capture session).**

*Owner (one session covers all of it; captures-needed "START HERE" already orders
most):* the §30 chart + §32 export; §33 sharp subject; §29 aperture ladder (f/5.6,
f/8, f/11) and TC-off bracket; §12 static repeat burst; §26 bright-on-dark subject and
the ≥400 px clear-background subject (fact 1891); darks at working exposure (§28); one
IBIS-ON bracket (C1); one CPL-rotation pair on a specular subject (C9); **one
aperture-pair bracket of one subject plus its f/22 guide frame (C11)**; **one ISO-only
bracket of one static subject (M70 §14 item 5 — settles C10's instrument confound and
every through-focus statistic's ISO question at once)**; §24 spectral flats if the
session has room. *Owner (purchase):* the Zerene licence — D1 is blocked on it and
A5's true comparator (DMap) has never rendered here.

*Corpus-only lanes, no captures:*
- **M-PHASE0-ZFIELD** — ẑ curvature / σ_z / coherence census from existing estimator
  statistics (A5's go/no-go).
- **M-PHASE0-XSPEC** — the complex cross-spectrum pilot (C10's go/no-go, four reads
  priced in one lane; discharges M70 §14 items 3–4; doubles as C1's
  registration-wall answer and C4b's instrument trial).
- **M-PHASE0-LCA** — per-channel through-focus peak offsets on 2–3 stacks (C2's
  go/no-go).
- **M-PHASE0-PHASE** — sub-pixel phase coverage *and conditioning* census from
  existing warpmaps, by field radius, including the May IBIS-ON stacks as the free
  dither pilot (C1's go/no-go).
- **M-PHASE0-QUINCUNX** — G1−G2 disagreement census: through-focus behaviour,
  flat-ROI null, imbalance calibration (C12's go/no-go; feeds B1/B5 regardless).
- **M-PHASE0-ASTIG** — orientation-split through-focus peak offsets by field annulus
  (C7's go/no-go).
- **M-PHASE0-DPAR** — tile-residual-vs-elected-depth regression on the deep stacks
  (C4c's go/no-go; doubles as an alignment-systematics audit; C10 read 2 is its
  precision sibling).
- **M-PHASE0-CURV** — the planar-subject field-curvature fit from existing estimator
  statistics (C5's depth-product prerequisite; C7's companion).
- **M-PHASE0-MAKERNOTE** — hex-dump and decode the Tag9405b arrays from the corpus's
  own ARWs; fit knot semantics against the measured CA profile (C13's go/no-go;
  licence-fenced per §2.2 hazard 6).
- **M-PHASE0-PTC** — B1 prototype on two stacks, scored against M90's independent g.
- **M-PHASE0-SPLIT** — the split-half fold run through the *shipping binary* on two
  subjects (staged file lists), reproducing M115's identity checks end-to-end in
  product conditions (D8's go/no-go).
- **M-PHASE0-TETHER** — the one-day SDK feasibility check (D10's go/no-go).
- **V-VEIL2** — re-run the §59.3 probe harness so A2 has its acceptance instrument
  before its build.
- **Literature passes** for every `could not confirm` in this file, at the depth
  fact 1136 demands, including verification of every citation this revision flagged
  as from-memory (a survey that misses Pertuz/Schechner-grade prior art certifies
  nothing).

**Phase 1 — one merge (A1, A2, A4, B3, B4, B6), behind the freeze.**
Entry: phase 0's veil instrument; the soft-gate patch as starting material;
width-matched calibration per facts 1917–1920; the aligned-pyramid byte-freeze row
(D5); **D9(a)'s fixed reduction lattice lands first**, so the freeze that phase 1
re-baselines is already worker-count-invariant and the 1.29× refund arrives with it.
Exit: the §1 scorecard v0 run end-to-end on the corpus — noise, hull,
halo-where-measurable, speed — plus per-band n_eff maps as shipped artifacts. The
gate-default question (2.0 vs 4.5) closes here as a calibration — provisionally
per-corpus, then per-stack when D8 lands in phase 2. The dust-ON and paper-profile
decision memos (D7) land alongside, being independent of the merge.

**Phase 2 — the election becomes estimation (A5 v0 behind the twin), estimation
finished (B1, B2, B5, B7), D8 self-tuning, D2 acuity map, D3 planner v1.**
Exit: A5 passes or dies on the twin's pre-registered gates; `Provenance::Measured` on
an unknown body's stack; foam's B/G climb flattened; the certified-acuity map (both
channels) shipping by default with the hull certificate in the manifest; per-stack k
tuning live behind its hash-neutrality guard; the planner speaking millimetres once
C5's ruler lands (else frame indices).

**Phase 3 — the fusion bet (C4 then C1), and the cleared physics channels (C2, C7,
C10 exploits, C12, C13) in whatever order phase 0 ranked them.**
C1 lands in two rungs: **1× lattice first** (demosaic-free merge — strictly a
correctness/efficiency win that also closes §2.4, no SR claim), then **2×** behind the
D1 instruments with C12's alias census gating engagement per tile. C10's shipped
exploits land smallest-first: the coherence guard (read 4), then signed admission
(read 2), with the pupil retrieval (read 3) feeding D4 only after the §30 chart can
score it. Exit: FRC-scored, moiré-scored, split-half-scored verdicts on §30/§33;
either the first defensible resolution claim in the project's history, or a measured
negative with the phase/conditioning census explaining exactly why.

**Phase 4 — the frontier (C3, C5, C6, C8, C9, C11 fusion, D4, D9(b), D10), and the
product surface (D6, D7 residue).** Each independently killable; none load-bearing
for the phases before it.

**Standing constraints across all phases:** D5's 2× wall-clock budget; byte-freeze
rows per backend maintained (now worker-invariant per D9a); author-never-verifies on
every claim-bearing number; every instrument commissioned for specificity as well as
sensitivity (the V-RIM rule); the licence fence of §2.2 hazard 6 on anything touching
maker notes or comparator internals; and the scorecard — not this document — is where
"SOTA" gets decided.

---

## 10. Self-audit — where this proposal is most likely wrong

1. **The two-pass cost may bite harder than priced.** The 2.2× figure is one
   measurement at N=79 on a different kernel. D9(a) and SIMD are the buy-backs; if
   they cannot cover it, A1 needs a one-pass approximation (provisional winner +
   correction) and that approximation needs its own commissioning. This is the
   likeliest engineering wall in phase 1.
2. **A5 may be a solution in search of a regime.** If M-PHASE0-ZFIELD finds σ_z large
   at corpus step sizes outside regions A1 already handles, the surface solve adds
   machinery without moving pixels — which is why the census runs before any solver is
   written, and why A5's failure leaves A1 whole. The converse risk is subtler: a
   surface prior that *works* will look better on every smoothness-loving statistic
   even where it is wrong, so its acceptance leans on the twin and on planted
   discontinuities, not on corpus prettiness.
3. **C10's odd-phase signal may not clear the floor.** The modulus family is measured
   symmetric to ±0.077 (M70 §16); if the phase asymmetry and the depth-displacement
   slope are similarly small at corpus SNR, reads 2 and 3 die and the channel shrinks
   to registration (read 1) and the inversion guard (read 4) — still worth the lane,
   but not the headline. That is exactly what M-PHASE0-XSPEC prices before anything
   is built. The retrieval also inherits blind-deconvolution's failure modes; its
   guards (no zero-blur hypothesis, per-slice normalisation, chart validation) are
   named in the item, and rule 18's over-wide drift is the direction to police.
4. **C1's registration wall may be real.** The within-DOF-frames-are-easy argument is
   ARGUED, not measured; M110's 0.48 px jitter might be solve noise that local
   refinement inherits rather than fixes. M-PHASE0-PHASE, M-PHASE0-XSPEC read 1, and
   C4's planted nulls exist to find out before the big build.
5. **Per-coefficient admission could resurrect the patchwork in the band domain.** The
   pyramid's smoothed energies and the winner's spatial coherence argue not, but
   M120's lesson is that winner fields shatter where no correct answer exists —
   phase 1's acceptance includes a flat-ground plateau census for this reason.
6. **B2 touches the most dangerous pixels in the image.** Censored estimation on
   speculars must be byte-identical off the clip set and flux-bounded on it, or it
   becomes the invented-values defect wearing a likelihood. The hull axis on the
   scorecard is the tripwire.
7. **D8's objective could be gamed by the thing it tunes.** The split-half statistic
   is gain-invariant and noise-honest (M115 §2), but the tuner and the instrument now
   share a pipeline; the fixed-pattern common mode (P13) and quantisation correlation
   (P18) are the known leaks, both priced, and the repeated-bracket gold form is the
   escape. The guard is structural: the tuned constants are also scored on the D1
   scorecard, whose instruments the tuner never sees.
8. **The novelty claims inherit their searches** (facts 1112/1136), and this revision
   deliberately introduced citations from memory — flagged, but flags are not
   verification. Every `could not confirm` and every from-memory citation is one
   adequate literature pass away from correction, and the phase-0 passes exist to
   take that hit before a build does, not after.
9. **Scope.** This document now proposes far more than a team ships in a season —
   more in each revision than the one before, which is itself a warning sign the
   phase gates must hold against. The gates are the control: each phase ends at a
   scorecard run, and any phase's negative result is a publishable stopping point,
   not a sunk cost. If only one thing survives triage, it should be **phase 1** — the
   thesis shipping by default is worth more than any single novel technique in this
   file — with **phase 0's capture session** alongside, because it is the only item
   here that no amount of software can substitute for.

---

## 11. Amendment 1 — D1's two named instruments are dead (orchestrator, 2026-09-03)

*Appended by the execution orchestrator. No text above this line has been
altered. This section records where execution has diverged from the plan, in
the spirit of section 10. Evidence for every claim here is in
`docs/STATUS.md` sections 3.1 and 2.9.16--2.9.19.*

**The headline clause at lines 192--197 currently has no licensing instrument
for its first and most important claim.** That sentence licenses *"resolves
detail at or beyond the best shipping comparator"* with `(D1: FRC +
slant-edge)`. Both are now dead:

- **FRC.** Line 251 calls it *"the one ground-truth-free sharpness metric that
  cannot be fooled upward by noise amplification"* and makes it D1's **spine**.
  It cannot be fooled upward by a common linear filter because it is *exactly
  invariant* to one -- `M-FRC-VIABILITY.md:11-12` records common post-noise
  filtering as an **"ideal null."** Blur is also a common linear filter.
  The invariance and the blindness are one property, not two.
- **Slant-edge.** Three builds, all refused. `M-PHASE0-SLANTEDGE.md:271-274`
  records variants whose optical arms *reverse*: blur scores sharper
  (`1.268326`) and genuine improvement scores worse (`.923468`).

Six candidate families across eight implementations have now failed the same
way. The structural cause is that **no single-image high-frequency statistic
separates resolved detail from sharpening, because sharpening adds exactly what
such a statistic measures.** Every candidate has bought one invariance by
forfeiting the other: `Q25` is tone-proof and sharpening-fooled (`5.560744x`);
candidate 2 is sharpening-proof to fifteen decimals and tone-destroyed.

**Section 3's diagnosis was right, and it applied to itself.** Lines 264--267
name instrument churn as what *"ate the project's middle"* and prescribe D1 as
the cure -- *"build the instruments once, first."* D1's own instruments then
churned. The prescription was correct; the specific instruments named in it
were not available to fill it.

**Consequence, stated plainly: strehl can currently prove harm and cannot prove
benefit.** The noise clause, the veil clause and the invented-structure clause
of lines 192--197 retain live instruments. The detail clause does not.

**What survives, and what has changed role.** Line 194's *"zero invented
structure (hull census, stamped per file)"* is alive and has been **promoted
from a per-file self-check to a comparative axis**, which is a change of role
rather than a new instrument. Its licensed claim is narrower than first hoped
and is stated here in the only form the evidence supports: **it can establish
invention; it cannot name the inventor.** Exceeding a resampler's exact
phase-dependent bound rejects that resampler as the sole explanation but does
not distinguish sharpening from local contrast, deconvolution, non-convex
merging or an omitted transform. A `~6%` Catmull-Rom ceiling proposed during
execution was **wrong** -- the exact separable two-dimensional bound is
`0.28125`, not `0.0625`, the latter being one plant at one phase.

**Three routes to a detail claim were identified; two remain open.**

1. **A truth reference.** Blocked on capture geometry: the main sweeps are at
   maximum 2.8x, so a 2.8x reference yields a sampling ratio of `1.0x` against
   a `1.25x` automatic no-go. Under assessment is an inversion -- score a 1.4x
   TC-off stack and use 2.8x bursts as its truth, giving exactly `2.0x`.
2. **Independent repeats.** Closed; this was FRC's route.
3. **A physical constraint sharpening must violate.** The hull census, above.

**A dependency in section 3 may now be discharged.** Lines 268--270 list
questions *"blocked on captures, not analysis -- and have been for weeks,"*
including the sharp chart that D1 needs at lines 1542--1552 (M88's verdict was
*"nothing sharp enough to point at"*). The owner's 2026-09-02
`high-res-calibration-slide-cpl` session, 657 frames, is plausibly that chart.
It also contains something the plan never asked for and the program badly
needed: a **genuine optical improvement pair** -- `tilted-sw4` (182 frames)
against `tilted-sw10` (92 frames) over an identical focus-encoder range -- plus
a real photon-SNR ladder and a flat null. Every candidate above was retired
without such an arm ever being run.

**What this amendment does not change.** Workstreams A, B and C stand. The
phase gates, the comparator pinning, the banked-purge discipline and the rule
that a negative result is a publishable stopping point all stand and have been
load-bearing. Section 10 item 9's instruction -- that if only one thing
survives triage it should be phase 1, with phase 0's capture session alongside
-- is unaffected and, if anything, reinforced.
