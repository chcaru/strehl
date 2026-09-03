# M-PHASE0-SPLIT — the cited result reproduces, but does not license a build

**Verdict: KILL — STOP/REMOVE RUST; retain the split instrument offline.**
The orchestrator's closure warning arrived after the flagged prototype had
already been committed.  Re-audit against the triage's own binding FALSE branch
changes the action: the exact historical M115 numbers reproduce, but their
controls do not transfer to the common-mode and data-dependent-tuning failures
on which D8 depends.  The prototype's Rust CLI/core/merge wiring is therefore
removed in the corrective commit; its code, measurements, and failure are
retained in history and in this experiment.

The prototype measured a 1/7 FRC crossing of **0.400367
cycles/quad-pixel** on `109MSDCF`, with a 1,000-resample spatial-tile bootstrap
median **0.399986** and 95% percentile interval **[0.381916, 0.408871]**.
That remains a deterministically reproduced cross-half correlation crossing,
not optical resolution: common sensor structure is indistinguishable from scene
signal, and the number does not justify keeping a product path.

Preregistered before implementation in
`experiments/M-PHASE0-SPLIT/PREREGISTRATION.md`.  Feature commit measured:
`1cd3019c77b8f4a2c45cd1d541cc85305296e390`.

## 1. What the corpus actually established

The authoritative D8 text in `docs/proposals/2026-08-sota-path.md` §D8 asks for
two interleaved, disjoint half-stacks, each re-deriving its own data-dependent
weights.  It proposes three products: per-stack tuning, per-tile FRC acuity, and
a half-difference null.

The phase-0 triage called this “already answered,” but its own header says that
assessment is not self-certifying and instructs the lane to stop if audit
breaks the premise.  Audit broke the broad premise:

* M115 did commission important pieces: planted blur recovery was
  **0.9938–0.9974**, common filtering moved its band SNR ratio by at most
  **0.54%**, and its separately written report checker re-derived 17/17 claims
  and caught 6/6 plants.  It was not independently re-choice-verified
  (`M115-deconv-headroom.md` §§2, 13).
* Two celebrated checks are not independent evidence.  A common linear
  transfer function cancels algebraically from ideal FRC, and
  `(P(A)+P(B))/2 = P_sig + P_noise` is an identity.  They cannot catch a wrong
  generator and checker that share an error.
* M115's replacement flat null itself failed the registered 0.25 bar:
  `MEAN=0.2984`, `WIENER_UNG=0.4034` (`M115-deconv-headroom.md` §2.5).
* `M41-r3-kill-measured.md` facts 475–478 are an explicit later correction.  The published
  **0.4961** crossing was the final ring returned on no crossing; 9/12 values
  were that fallback.  A 4×4×2 sweep repaired **0/32** settings, so the crossing
  was withdrawn.  A flat ROI reached the same endpoint.
* Common-mode content is structural, not a small-sample problem.  Fact 478
  measures blur sensitivity falling approximately as `1-rho`; the repair is a
  second independent capture, not another FRC threshold.
* `V-SOFTCHECK-coherence.md` shows the adversarial output `(A+B)/2` scoring
  perfect coherence and zero half-difference while losing **29.6%** of delivered
  band power.
* Separately rendered halves also confound selection with registration.
  `V-SOFTCHECK-selection-vs-alignment.md` measured **8.885 px** median half-field
  shift and **1.354 px** local residual on `bee-1-cpl`; the planted residual was
  sufficient for **87.3%** of observed incoherence.

M115 has no retraction banner at its top, but the later M41 fact rows
do withdraw the FRC-crossing use.  The lane initially treated that as permission
for a diagnostic-only substrate.  The orchestrator's later clarification makes
the triage's FALSE branch binding instead, so that interpretation is withdrawn.

The mandatory mechanical prior-art search was commissioned first and passed all
two positive and one negative self-tests.  Its split/FRC search surfaced M92,
M97, M103, M127, V-THESIS, V-DCNULL, and both V-SOFTCHECK reports.

### Post-update reproduction and transfer audit

The later orchestrator warning required execution, not quotation.  The loader in
`rerun_m115.py` was commissioned before opening RAWs: clean exit 0; plants `H1`
(wrong Git blob), `H2` (failed output reroot), and `H3` (wrong extraction) all
exited 1.  It then loaded the four exact source blobs at historical commit
`77c8d5e9ac6ed342cdc841e541c98f87e5c743f8` directly from Git, changing only
M115's output root to this lane, and reran `s01_rois.py` plus
`s03_instrument.py` on the original 22-frame, 33-frame, and 360-frame inputs.

**The cited numbers reproduce.**  Eight blur recoveries span
**0.9938215871–0.9973982082** and are monotone.  Common-filter SNR ratios are
**1.0000000, 0.9986025, 0.9980240, 0.9946221**; the maximum movement is
**0.537785%**.  The power identity spans
**0.999999999987–1.000000000000**.  This rules out a transcription or stale-run
explanation.

**The meaning does not survive.**  The same exact rerun returns the historical
split null **FAIL**: `MEAN` maximum mid-band SNR **0.438734** and `WIENER_UNG`
**3.331288** against 0.25.  The 1.0000 identity follows algebraically from the
three definitions in `split_stats`; it is bookkeeping, not an independent
control.  The common-filter check likewise applies the same linear transfer to
both halves and cannot exercise a data-dependent tuner.  C2 proves response to
a same-model Gaussian blur, but does not plant fixed-pattern/common-mode
content, unequal half latents, or a tuning change.

The new prototype's own common-mode adversary supplies the missing transfer
test and fails decisively: independent noise plus the same fixed pattern reads
low-band FRC **0.972099**.  M41 facts 475–478 independently withdraw the numeric
FRC crossing: 9/12 were endpoint fallbacks, 0/32 repair settings worked, a flat
ROI reproduced the detail reading, and blur sensitivity fell as `1-rho` under
shared content.  `audit_postupdate.py` therefore returns
`STOP_REMOVE_RUST`; its separately written checker re-derived five claims and
caught 4/4 planted report defects.

The first audit aggregation run itself failed safely but flatteringly: it
reported that the historical numbers did not reproduce because its Markdown
literal for the published blur range was wrong.  Reading the individual
booleans exposed the mismatch.  After correcting that literal, numerical
reproduction is GREEN and the STOP verdict remains for the five independent
transfer/meaning failures above.  The favourable-to-STOP error is not counted
as evidence.

## 2. Rolled-back Rust prototype

The now-removed, off-by-default surface was:

```text
strehl stack <DIR> --split-out <PRODUCT_DIR>
```

It was accepted only by the pyramid backend; pairing it with
`--merge estimator` exited 1 with a named refusal.

The prototype in `crates/strehl-cli/src/merge_cmd.rs` kept the existing four-plane full
`BandMerge` and, only when requested, added separate one-plane even and odd
green-luma `BandMerge` plus workspaces inside each existing worker.  Global
filename index parity was fixed before any alignment refusal.  Each half folded
only its own frames and re-derived every band weight.  It used the same decoded
and registered luma and the same warp map as the full result, eliminating the
separate-invocation solve measured by V-SOFTCHECK.

The ordinary accumulator was updated first, and its worker count, chunk
boundaries, and absorb order were unchanged.  On all 22 real frames, the main
TIFF with split off and on is byte-identical:

`629DA64F…A7236A9` both ways, **49,450,019 bytes**.

The diagnostic cost **+1006 MB per worker** at this geometry; the one-worker
run held an estimated 2.3 GB.  The banner reported this explicitly.  Worker count
was deliberately not reduced, because doing so changes the full render's
floating reduction order.  This makes the flag unsuitable on a memory-limited
host unless `STREHL_PYRAMID_WORKERS` is lowered; it is another reason the
prototype was not suitable for retention.

The historical `crates/strehl-core/src/split.rs` supplied the dependency-free radix-2 FFT,
ring sufficient statistics, and a crossing type with explicit
`MEASURED`, `CENSORED_ABOVE`, `CENSORED_BELOW`, and `INSUFFICIENT` outcomes.
No endpoint fallback existed on the prototype path.  A confirmed crossing
requires three physically adjacent usable rings after the bracketing ring; a
gapped or incomplete terminal drop is `INSUFFICIENT`.

Products were computed from the two `f32` collapses **before** quantisation:

* `half-even.tiff`, `half-odd.tiff` — above-black linear green DN;
* `null-signed.tiff` — even minus odd, zero at code 32768;
* `frc.csv`, `frc-tiles.csv` — cross and both auto powers, sufficient to
  re-form FRC, `P_sig`, and `P_noise`;
* `acuity.csv`, `acuity.tiff`, `acuity-class.tiff` — per-tile value/bound and
  censor class;
* `README.txt` — units, conventions, and the common-mode warning.

`main.rs` owned the flag/help/refusal and `lib.rs` exported the spectral module.
No change was needed in `pyramid.rs`: `BandMerge` was already plane-count
generic and `finish(&self)` already supported all three accumulators.  No auto-tuner was added.  All of this wiring has now been removed from HEAD;
the offline Python measurement and committed run products remain.

## 3. Commissioning

The frozen estimator uses centred, non-overlapping 256² tiles, per-tile mean
removal, separable Hann windowing, integer-radius rings, and a 1/7 crossing only
after three consecutive below-threshold rings.  Units are cycles per native
green quad pixel.

Machine-readable record:
`experiments/M-PHASE0-SPLIT/out/commission.json`.

| control | clean reading | bar/result |
|---|---:|---|
| independent white-noise null | mean `|FRC|` **0.047182**; three band means **−0.027520, −0.013547, −0.014068**; max per-ring `|t|` **3.167384** | `<0.05`, every band `<0.08`, every ring `|t|<4`: PASS |
| common-mode adversary | low-band FRC **0.972099** | required null violation: PASS; exposes specificity limit |
| shared multiscale signal + independent noise | low **0.989378**, high **0.013942** | low `>=0.90`, high `<=0.60`, fall `>=0.25`: PASS |
| fully present shared signal | maximum powered-ring error from 1 = **0.000e0** | `1.0000 +/- 1e-4`: PASS |
| identical 3×3 unsharp, amount 1.5 | crossing **0.222192 → 0.220543** (`−0.001650`); naive acuity **1.838176×** | FRC did not improve and moved <1 ring; naive metric moved >25%: PASS |
| fully correlated broadband pair | `CENSORED_ABOVE 0.5` | no numeric final-bin crossing: PASS |
| fixed gapped and two-ring-tail curves | `gapped=Insufficient`, `short_tail=Insufficient` | no compressed “consecutive” rings and no false terminal lower bound: PASS |
| fixed external DFT | Rust versus independent Python direct DFT max relative error **2.13e−15** | `<1e−9`: PASS |

The first sharpening specification incorrectly required every finite-window
ring to move by less than `5e-4`; it failed at 0.010859 even though the actual
crossing got slightly worse.  The additive preregistration amendment records
why finite Hann tiling and spatial filtering do not commute and replaces that
algebraic demand with the user-facing crossing gate.  Nothing was silently
rewritten.

**7 control families, 6 named Rust plants, every clean family GREEN and every
plant RED with exact cargo exit 101.**  The seven are fixed DFT, independent
noise, common-mode limitation, positive/full-effect, identical sharpening,
endpoint censoring, and gapped/incomplete transition refusal.  The six plants
were:

* `N1`, reuse one noise half: null became **1.000000**.
* `P1`, wrong conjugate sign: positive low band became **−0.066251**.
* `S1`, substitute naive acuity for resolution: reported movement became
  **+0.838176**.
* `C1`, restore last-bin fallback: reported `MEASURED(0.5)`.
* `C2`, compress an unusable physical ring away: a gapped curve falsely
  reported `MEASURED(0.185714)`.
* `C3`, treat a two-ring terminal drop as a lower bound: falsely reported
  `CENSORED_ABOVE 0.4`.

The Python crossing/bootstrap checker has its own literal crossing, censor,
ring-adjacency, and short-tail predicates.  Clean exits 0; its last-bin,
compressed-gap, and false-tail plants all exit 1.  The post-real audit also
tightened the null from broad bands to a per-ring Student screen; the
pre-declared `|t|<4` bar passed at 3.167384, so the real result was retained.

Independent verification found the gap-compression and short-tail defects after
the initial report.  The additive preregistration correction records this
timing rather than laundering `C2`/`C3` into preregistered evidence.  Rust and
the CSV checker were both repaired and planted.  The real aggregate was
unaffected: rings 102–105 are all usable and physically contiguous, and
reclassification reproduced the exact value below.

## 4. Real stack

Run record: `experiments/M-PHASE0-SPLIT/out/real-109/run.json`; raw log:
`run.log`; derived values: `measurement.json`.

* Capture: read-only `D:\personal\macro\109MSDCF`, all **22** frames.
* Isolated sidecar: reference 11, **22 placed / 0 refused**, Catmull-Rom,
  39.011 plane-px corner drift and 0.385 plane-px cycle floor.  Held-out error
  was unavailable because the solve had too few edges.
* Build: exact `1cd3019c…e390`; pyramid bands/gate/exponent/ramp
  `7/2/2/1.4`, soft selection, mean base, scale coverage, CA explicitly off;
  one deterministic worker.
* Aggregate FRC: **0.999354** at 0.02–0.10,
  **0.973469** at 0.10–0.25, **0.124165** at 0.35–0.48.
* 1/7 crossing: **0.4003665568 cycles/quad-pixel**.  The curve crosses cleanly
  between rings 102 and 103 (FRC 0.148669 → 0.136900).
* Tile bootstrap: 1000/1000 measured; median **0.3999859920**, 95% interval
  **[0.3819157379, 0.4088708365]**.
* Spatial heterogeneity is much wider: 116/117 tiles measured and one was
  censored above; measured tile range **0.271149–0.489310**, median
  **0.354286**.
* Quantised signed-null product: mean **−0.251 DN**, RMS **14.421 DN**,
  median absolute **6 DN**, p95 absolute **32 DN**, zero saturated pixels.

The bootstrap resamples scene tiles.  It quantifies sensitivity to field
composition; it does not include common-mode sensor bias, which the split
cannot estimate.  Thus the numeric interval is not permission to relabel the
map “certified resolution.”

## 5. Decision and source consequence

**Remove the Rust changes.**  The triage states its FALSE consequence
unambiguously: “No current merge code changes. Keep the split instrument offline
in Python.”  HEAD therefore no longer contains `--split-out`, the dual
accumulators, `strehl_core::split`, or the Rust probe.  `main.rs`,
`merge_cmd.rs`, and `lib.rs` are restored byte-for-byte to their state
immediately before feature commit `1cd3019c`; the two feature-only Rust files are
deleted.

The useful result is retained offline: commissioned synthetic controls, the
real half products and sufficient spectra, the independent CSV classifier, and
the exact historical M115 rerun.  They can support a future experiment, but not
a shipping path.  Re-opening requires a genuinely independent repeated bracket
or independently commissioned sensor-pattern subtraction, a non-degenerate
balanced partition, and a plant that changes the actual data-dependent tuning
choice while a tuner-blind metric grades it.

**Do not change merge constants from the 0.400367 crossing.  Do not add automatic
tuning.  Do not call `acuity.csv` a certificate.**  The corpus and the new
common-mode arm prove that a flat/shared pattern can look resolved, while the
coherence-only average can earn a perfect score after losing 29.6% of delivered
band power.

The preregistered “shift parity by one” sensitivity was itself a no-op: it only
swaps the names even and odd, leaving symmetric FRC unchanged.  It cannot
certify robustness and is disclosed rather than counted.  Acuity shipping now
requires a genuinely independent repeated bracket or an independently
commissioned sensor-pattern subtraction, plus a non-degenerate alternate
partition and more than this one subject.  None was available here.

## 6. Not verified

* No second, independently captured repetition of the same bracket exists, so
  the 0.400367 crossing could not be separated from fixed-pattern/common-mode
  sensor structure.  It is not optical ground truth.
* Only one real subject was measured.  No aperture, stack-density, camera, or
  subject ladder was run.
* The alignment solve had no held-out error estimate.  Same-invocation halves
  remove separate solves but cannot remove a residual shared by both.
* The registered shift-one parity ladder has no power, as explained above; no
  genuinely different balanced partition was measured.
* The opt-in path's multi-worker peak memory was estimated, not measured on a
  constrained host.  The 22-frame evidence used one worker.
* Automatic tuning and the proposal's certified-resolution claim were
  deliberately not implemented, because the audited evidence does not license
  them.
