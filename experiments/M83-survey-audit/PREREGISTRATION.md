# M83 survey audit — preregistration

**Status: FROZEN BEFORE PRIMARY-SOURCE VERIFICATION.**

This document fixes the sample, adjudication rules, denominator, and search
procedure for M83. It was written after reading the six reports, M79,
`SYNTHESIS.md`, `AGENTS.md`, and the downstream code needed to establish
dependencies. No external paper, specification, licence, vendor documentation,
or prior-project source was opened to adjudicate any A–F claim before this
freeze.

Internal later milestones are unavoidably visible in `SYNTHESIS.md`: that file
is the dependency record the brief requires the selection to use. Their
findings may establish that a claim remained load-bearing, was superseded, or
reached code; they do **not** count as M83 verification. M83 will re-read the
underlying primary source and report when a later milestone had already found
the same correction.

## 1. What this sample can and cannot estimate

The eighteen claims below are a purposive, risk-weighted sample: three claims
per report selected because code, a rule, a closed scope decision, or a public
product claim depends on them. They are not a random sample of sentences in the
six reports. Therefore:

- M83 can estimate the **architectural-exposure overstatement rate** among the
  six reports' most load-bearing claims.
- M83 cannot estimate an unbiased corpus-wide base rate for all factual claims,
  all citations, or all prose in the reports.
- Equal allocation of three claims per report weights reports equally, not
  claims, words, citations, or downstream cost.

Question 201's phrase “base rate” is consequently too broad. M83 will retain it
for continuity but will name the measured quantity precisely in the final
report. This is still the decision-relevant quantity: it asks how often the
claims carrying architecture survive primary-source checking.

## 2. Eligibility and selection rule

The unit is one proposition, or one tightly coupled premise-and-decision bundle
when the decision was made from the bundle as a whole. A claim was eligible if
it appears in the current report file, including its amendments. A report's
own explicit retraction was not eligible as the old positive claim; the
replacement claim was eligible. Later independent measurements neither remove
a claim from eligibility nor verify it for M83.

Claims were ranked in this order:

1. an irreversible rule or an implemented type, dependency, or algorithm;
2. a current v1 inclusion/exclusion or an architecture row in `SYNTHESIS.md`;
3. a numbered fact, closed risk, or public novelty/product claim;
4. prominence within the report only as a tiebreaker.

The selection deliberately includes negative and absence claims. Those claims
carried architecture and product differentiation, so excluding them because
they are harder to prove would bias the audit toward easy confirmations.

## 3. Adjudication and arithmetic

M79 correctly separates **what the source says** from **how deeply it was
read**. M83 will preserve those two axes.

### 3.1 Factual verdict

- **VERIFIED** — the primary source supports the claim at the scope and
  strength used downstream.
- **OVERSTATED** — the primary source supports a materially narrower,
  conditional, configuration-specific, or weaker proposition. The report will
  state the strongest supported replacement.
- **REFUTED** — the primary source contradicts the core proposition.
- **UNVERIFIABLE** — no legitimate full primary source or reproducible primary
  record can be reached. An abstract cannot verify body-level details.

### 3.2 Evidence depth

- **VERIFIED-AT-PRIMARY-SOURCE** — M83 read the paper body, specification,
  standard, licence text, API/vendor documentation, or reproducible first-party
  measurement record that carries the proposition.
- **TAKEN-FROM-SECONDARY** — the survey's load-bearing chain stops at a summary,
  abstract, another survey, practitioner report, or unsupported inference.
- **READ-AT-PROJECT-SOURCE** — the proposition is about this project's or the
  prior project's own implementation or measurement and M83 read that source
  record. This is not silently relabelled as literature.

A row may therefore read, for example, `OVERSTATED;
VERIFIED-AT-PRIMARY-SOURCE`, as in M79.

### 3.3 Fractions

For each report and pooled:

```text
adverse overstatement fraction
  = (OVERSTATED + REFUTED) / (VERIFIED + OVERSTATED + REFUTED)
```

`REFUTED` counts in the numerator because it is a stronger form of
overstatement. M83 will also publish the strict `OVERSTATED / adjudicated` and
the raw verdict counts so the convention cannot hide a result.
`UNVERIFIABLE` is excluded from the denominator and shown explicitly.
`TAKEN-FROM-SECONDARY` is evidence depth, not by itself a factual verdict; if
the proposition cannot be adjudicated beyond that chain, its factual verdict
is `UNVERIFIABLE`.

M79's comparison remains exactly **2/3 adverse**: M79's claims 1 and 3 were
OVERSTATED and M79's claim 2 was narrowly confirmed.

## 4. Frozen claims

### A — `A-prior-corpus.md`

#### A1 — selector-style merging intrinsically amplifies noise

- **Exact report claim:** “`max|c|` selection plus winner-copy colour means
  flat regions receive one random frame's noise, measured at **1.82× worse than
  a single source frame** in highlights” and therefore “**Make the merge an
  estimator, not a selector**” (`A-prior-corpus.md:506`; mechanism and
  2.3–4.6× range at line 309).
- **Downstream dependency:** `SYNTHESIS.md` §§1.1–1.2; `AGENTS.md` rule 4; the
  estimator and `n_eff` contract in `crates/strehl-core/src/merge.rs`; the raw
  argmax command is retained only as a named negative control.
- **OVERSTATED if:** the 1.82× comparison does not compare the claimed same
  ROI/domain/baseline; winner-copy rather than coefficient selection carries
  the effect; the mechanism requires the prior pipeline's particular
  normalisation or post-processing; or primary order-statistic analysis does
  not support the general “intrinsic to selector-style merging” conclusion.

#### A2 — the reported 1.10× correlated-noise result was a metric error

- **Exact report claim:** “**The 1.10× is a measurement of scene structure, not
  of noise correlation**” because the script compared spatial variance after
  downsampling and quantisation instead of temporal per-pixel sigma
  (`A-prior-corpus.md:545`).
- **Downstream dependency:** `SYNTHESIS.md` §4.1 retracts the correlated-noise
  claim; `AGENTS.md` rule 10 forbids comparing spatial sd with temporal sigma;
  current flat-noise instrumentation high-passes spatial structure before
  making a noise claim.
- **OVERSTATED if:** the primary script actually computes a temporal estimator,
  the preprocessing/domain account is wrong, or the available data establish
  cross-frame covariance despite the stated metric defect.

#### A3 — accretion caused the 81→456 s and 6→23 GB regression

- **Exact report claim:** “the fork went **81 s → 456 s** and **6 GB → 23 GB**
  by accretion, with no gate” (`A-prior-corpus.md:510`; component timings at
  lines 279–291).
- **Downstream dependency:** `AGENTS.md` rule 2; `SYNTHESIS.md` §§3.2, 5, and 9;
  O(workers) streaming and the memory budget in
  `crates/strehl-cli/src/stack.rs`.
- **OVERSTATED if:** the endpoints are not the same workload, hardware,
  thread-count, flags, cache state, and memory statistic; 23 GB is an
  extrapolation rather than an observed peak for the named 33-frame workload;
  or the evidence cannot attribute the change to feature accretion rather than
  a changed baseline.

### B — `B-algorithms-sota.md`

#### B1 — the Laplacian family inverts under real RAW noise

- **Exact report claim:** “**The Laplacian's winner margin and curvature both
  go negative at σ ≥ 0.01**” and therefore “Any pipeline whose focus measure is
  variance-of-Laplacian or SML on real RAW is, in noisy regions, actively
  anti-correlated with focus” (`B-algorithms-sota.md:208`).
- **Downstream dependency:** `SYNTHESIS.md` fact 6 and risk 2; the original veto
  on Laplacian-family focus operators. Later M11/M13 measurements selected the
  shipped Tenengrad operator independently, but they did not erase the
  literature claim that closed the first choice.
- **OVERSTATED if:** Surh Table 1 uses a narrower operator, normalization,
  synthetic scene/noise model, or metric than “the Laplacian family on real
  RAW”; negative WM/CUR does not mean anti-correlation with focus accuracy; or
  RDF's advantage is configuration-specific.

#### B2 — changing HDR+'s reference turns its merge into a focus stacker

- **Exact report claim:** HDR+'s merge “**already does the right thing on
  defocus mismatch**” and “replace the fixed reference `T₀` with a per-band,
  per-tile reference chosen by the §2 focus measure, and HDR+'s merge becomes a
  focus-stacking merge that also denoises” (`B-algorithms-sota.md:629`).
- **Downstream dependency:** the estimator thesis in `SYNTHESIS.md` §§1.1 and
  3.3; the noise-gated accumulation shape and diagnostics in
  `crates/strehl-core/src/merge.rs`.
- **OVERSTATED if:** Monod/HDR+ only guarantees preservation of a fixed sharp
  reference; replacing that reference changes the estimator, consistency, or
  non-amplification argument; the gate cannot distinguish defocus from
  misregistration/occlusion; or no primary source evaluates the proposed
  per-band reference substitution.

#### B3 — direct Bayer-to-RGB merging earns a >3 dB advantage and removes demosaic

- **Exact report claim:** Wronski et al. “merge Bayer raw images directly onto
  a full RGB frame, bypassing single-frame demosaicing” and report “**over 3 dB
  better than the next best one, DeepJoint, on both datasets**”
  (`B-algorithms-sota.md:911,923`).
- **Downstream dependency:** `SYNTHESIS.md` §1.2 and architecture rows for CFA
  processing/demosaic; `AGENTS.md` rule 1; `strehl-raw::Frame` stores mosaiced
  `u16`; the current stack path has no conventional full-frame demosaic stage.
- **OVERSTATED if:** the >3 dB result is primarily multi-frame-versus-single-
  frame rather than direct-merge-versus-merge-then-demosaic; the latter
  comparison is qualitative or differently configured; or the paper's burst
  assumptions do not support eliminating demosaic as a general focus-stack
  architecture decision.

### C — `C-landscape.md`

#### C1 — no shipping stacker is Bayer-domain

- **Exact report claim:** “Is any tool RAW-native / Bayer-domain? **No. Not
  one.**” and “**No shipping tool has tried it**”
  (`C-landscape.md:14,395`).
- **Downstream dependency:** the CFA-native differentiation claim in
  `SYNTHESIS.md` §§1.2 and 6; the public rationale for a CFA-native path.
- **OVERSTATED if:** any shipping or publicly released stacker performs focus
  estimation or fusion on CFA samples without first developing full RGB; the
  report conflates RAW ingest/output with the processing domain; or its search
  can only support “none among the named tools as of the search date.”

#### C2 — no competing tool emits confidence or uncertainty

- **Exact report claim:** “**The central finding: no tool emits a confidence
  map. Nothing even close**” (`C-landscape.md:748`; the product-gap statement
  first appears at line 483).
- **Downstream dependency:** confidence map in the v1 scope
  (`SYNTHESIS.md` §9); `n_eff`, predicted sigma, and through-focus confidence
  channels in `strehl-core`; the product claim that the output is novel.
- **OVERSTATED if:** a shipping stacker exposes uncertainty, reliability,
  focus-quality, source-coverage, or an actionable suspect-region map; a depth
  map or threshold preview is functionally close enough that “nothing even
  close” is false; or only an enumerated-tool claim is supportable.

#### C3 — LGPL-2.1 is close to free here, so use `rawler`

- **Exact report claim:** “**LGPL-2.1 is not fatal, and for a project like ours
  it is close to free**” and “**Verdict: use `rawler`**”
  (`C-landscape.md:582,641`).
- **Downstream dependency:** the `rawler` dependency in `strehl-raw`;
  `SYNTHESIS.md`'s RAW-decode architecture row and risk 6; the distribution
  obligations in `AGENTS.md`.
- **OVERSTATED if:** LGPL-2.1 §6 requires relinkable application materials not
  satisfied by merely publishing ordinary source; static Rust linking imposes
  material object/reproducibility, notice, offer, reverse-engineering, or
  downstream-distribution duties omitted by “close to free”; or `rawler`'s
  actual licence/dependency terms differ from the report.

### D — `D-rust-and-hardware.md`

#### D1 — `f16` cannot store 14-bit linear CFA without losing sensor codes

- **Exact report claim:** `f16` has “a quantisation step of roughly **8 LSB**”
  at full-scale 14-bit linear data; “**Keep CFA/linear-scene-referred data in
  u16 (storage) and f32 (arithmetic)**”
  (`D-rust-and-hardware.md:618`).
- **Downstream dependency:** `AGENTS.md` rule 1;
  `crates/strehl-core/src/lib.rs`; `strehl-raw::Frame`; core buffers and
  arithmetic types.
- **OVERSTATED if:** IEEE binary16 spacing over the actual normalized storage
  range preserves all 14-bit codes or materially fewer than eight codes are
  lost near white; the pipeline can scale/offset without losing the claimed
  precision; or `f32` arithmetic is not required to preserve the relevant
  operations.

#### D2 — gather-at-consumption is time-neutral and saves 4 GB

- **Exact report claim:** “**option (c) is a wash on time and saves 4 GB**”
  (`D-rust-and-hardware.md:694`; recommendation table at line 728).
- **Downstream dependency:** `AGENTS.md` rule 2; the irreversible
  never-materialise decision in `SYNTHESIS.md` §9; streaming folds in
  `crates/strehl-cli/src/stack.rs`.
- **OVERSTATED if:** the roofline counts omit cache misses, interpolation,
  halos, repeated consumers, synchronization, or CPU execution; the claimed
  96 MiB L2 residency does not hold across 60 frames; the compared alternatives
  do not produce equivalent pixels; or no measured implementation establishes
  approximate time neutrality.

#### D3 — CUDA is only about 1.1× and should be cut from v1

- **Exact report claim:** “**Estimated end-to-end speedup of a CUDA fast path
  over a well-written wgpu implementation: ~1.1x**” and “**cut CUDA from v1
  entirely**” (`D-rust-and-hardware.md:633,637`).
- **Downstream dependency:** `SYNTHESIS.md` compute-backend row and §9; CUDA is
  explicitly outside v1 while a backend seam is retained.
- **OVERSTATED if:** the estimate lacks an equivalent wgpu/CUDA benchmark; any
  material feature/limit premise is assumed rather than read at the API or
  adapter; the 1.1× combines incomparable ideal and measured quantities; or the
  primary sources support only capability, not end-to-end speed.

### E — `E-plugin-architecture.md`

#### E1 — Wasm is the wrong pixel-stage boundary in 2026

- **Exact report claim:** the Component Model lost because “the Canonical ABI
  is a **copy** boundary,” `shared-everything-threads` and `memory-control` are
  unimplemented, and `wasi-webgpu` is only Phase 2; therefore “Wasm is the
  right answer for a *control-plane* extension and the wrong answer for a pixel
  stage — in 2026” (`E-plugin-architecture.md:247–259,459`).
- **Downstream dependency:** `SYNTHESIS.md` plugin-mechanism row and §9;
  statically linked native `FocusMeasure` trait objects in `strehl-plugin`;
  dynamic/Wasm plugins excluded from v1.
- **OVERSTATED if:** the Canonical ABI permits same-memory borrowed buffers or
  zero-copy resources for this boundary; Wasmtime already implements the
  required memory/thread proposal; a stable host-managed GPU/resource handle
  avoids wasi-webgpu; or the cited proposal status does not imply that a
  host-call pixel plugin is impractical.

#### E2 — Cordis confluence requires commutative registries and explicit pipeline order

- **Exact report claim:** Cordis Thm 73 says “the quiescent state is a function
  of the final configuration alone,” and the paper's key distinction means
  registries commute while “**pipeline order must be explicit data, never an
  emergent consequence of load order**”
  (`E-plugin-architecture.md:126,166`).
- **Downstream dependency:** sorted/order-independent lookup and permutation
  tests in `crates/strehl-plugin/src/registry.rs`; the separation between an
  order-insensitive contribution registry and an ordered pixel pipeline.
- **OVERSTATED if:** Thm 73 is conditional on assumptions the report omits;
  confluence concerns loader transitions rather than semantic permutation of
  registry entries; the table/chain quote is descriptive rather than a
  prescription; or the theorem does not license the project's property test.

#### E3 — host-measured focus calibration makes a wrong constant unrepresentable

- **Exact report claim:** host measurement makes `tol = t·√2·calibrate(op,cfg)`
  “**correct by construction for any operator at any window with any
  regulariser**,” and “Fault 5 becomes unrepresentable”
  (`E-plugin-architecture.md:1584–1599`).
- **Downstream dependency:** `FocusMeasure` deliberately has no `noise_sd`;
  `Calibration` has no public constructor; `calibrate`, `Registry`, and their
  tests in `strehl-plugin` implement this exact choice.
- **OVERSTATED if:** finite synthetic Gaussian calibration can itself be
  biased, seed/tail/configuration dependent, or unlike sensor noise; response
  sd is insufficient to make the gate dimensionless across nonlinear
  operators; “any operator” excludes meaningful classes; or the design only
  prevents declaration/inheritance of one scalar rather than miscalibration.

### F — `F-camera-lens-optics.md`

#### F1 — the A7C II photon-transfer model is validated and should ship

- **Exact report claim:** the white-level cross-check makes
  `g(ISO)=ISO/436.8` “trustworthy”; the local ISO-160 fit agrees within 2%;
  “**the photon-transfer model is validated. Ship it**”
  (`F-camera-lens-optics.md:128,177–184`).
- **Downstream dependency:** A7C II constants and the variance equation in
  `crates/strehl-core/src/profile.rs`; injected-noise architecture in
  `SYNTHESIS.md`; `AGENTS.md` rule 3.
- **OVERSTATED if:** the white-level calculation is not an independent gain
  measurement; the percentile-bias correction is invalid; extended ISO or the
  dual-gain mode violates one divisor; read-noise values are chart
  approximations rather than measured constants; or one green-frame fit cannot
  validate all planes and ISOs.

#### F2 — macro effective aperture is `N(1+m/p)` and requires pupil magnification

- **Exact report claim:** “**Effective aperture:
  `N_eff = N·(1+m/p)`**” (`F-camera-lens-optics.md:342`) and pupil
  magnification “genuinely needs `p`,” with `p=1` merely assumed
  (`F-camera-lens-optics.md:485`).
- **Downstream dependency:** `SYNTHESIS.md` facts 12, 27, and 28; capture-advisor
  arithmetic; the decision that a future lens profile stores `p` while
  magnification remains per shot.
- **OVERSTATED if:** the formula uses the wrong pupil-ratio convention or
  magnification definition; the teleconverter/marked-aperture treatment
  double-counts a factor; the approximation fails materially in this macro
  regime; or the cited primary optics source supports a narrower thin-lens
  case only.

#### F3 — focus bracketing is globally similar, rail capture is not, and mode is reliably detectable

- **Exact report claim:** with focus-driven capture “a global similarity
  transform is not an approximation, it is exact (modulo distortion and pupil
  shift),” while no global 2-D warp can represent rail capture; mode detection
  from `FocusPosition2` variation plus scale drift is “**free and reliable**”
  (`F-camera-lens-optics.md:461,469–475`).
- **Downstream dependency:** `CaptureMode::{FocusBracket,Rail}` in
  `crates/strehl-core/src/lib.rs`; v1 focus-bracket-only scope and deferred rail
  support in `SYNTHESIS.md` §9 and `AGENTS.md`.
- **OVERSTATED if:** internal focusing changes viewpoint, distortion, pupil
  position, or depth-dependent magnification enough to violate global
  similarity; axial rail motion can be globally represented in relevant
  single-depth cases; `FocusPosition2` may be constant/quantized during focus
  bracketing or vary for other reasons; or EXIF plus residuals cannot classify
  mode reliably without capture metadata/user knowledge.

## 5. Verification protocol

For each frozen claim M83 will:

1. Follow every load-bearing citation to the full primary paper,
   specification, standard, licence, API documentation, vendor documentation,
   or first-party measurement record.
2. Quote the exact passage/table/equation that carries the verdict and name
   its configuration, benchmark, date/version, and exclusions.
3. Separate a source's observation from M83's derivation and architectural
   argument using **MEASURED / DERIVED / ARGUED** labels.
4. Treat abstracts, search snippets, repository READMEs describing somebody
   else's result, practitioner posts, and survey prose as secondary.
5. Mark inaccessible full papers **UNVERIFIABLE** rather than infer their body
   from an abstract.
6. Read no GPL-derived implementation and copy no GPL-derived code. Licence
   text, papers, specifications, public API/vendor docs, and uncopyrightable
   factual tag values are in bounds.

### Nearest-prior-art search

For every report, M83 will search beyond its bibliography:

- inspect backward references in each obtained primary source;
- inspect forward citations or bibliographic records where available;
- run at least three mechanism-specific queries, not just title/author queries;
- search the adjacent vocabulary that could hide the same idea under a
  different field name;
- stop after two successive query/ref-list passes yield no closer source, and
  record the queries and boundary.

A missed work counts as “nearest prior art” only if it predates or is
independent of the report and addresses substantially the same mechanism or
decision, not merely the broad topic.

## 6. Fixed exclusions

- No captures, GPU work, Rust build, or benchmark will be run.
- No six-report text, `SYNTHESIS.md`, `AGENTS.md`, `crates/`, or M82-owned file
  will be edited.
- M83 will write only this experiment directory and
  `docs/research/M83-survey-audit.md`.
- Findings cannot change the claim sample or the per-claim overstatement
  conditions above.
