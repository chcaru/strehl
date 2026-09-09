# Native sensor-to-band transfer diagnostic

2026-09-09. Root commission: SOURCE PREPARATION ONLY. Named task identifier
`native-sensor-transfer`; no SYNTHESIS fact block is allocated.

## Decision and existing answers

The user reaffirmed native RAW stacking and the diagnostic captures in
D:/personal/macro/requests as the product objective. Root adopts the independent
priority review at59202e51: defer the integer common-TIFF extension until a
named comparison needs it. Its completed design and all dimensions evidence
remain intact. The native M194 shared consumer already supplies the relevant
RAW/CFA gather, fold and writer; no new RGB interface is required.

Question: on one fixed recorded sensor-control condition, does the frozen
noise model supplied to the production CFA consumer predict independently
measured temporal residuals at its actual green-luma/pyramid gate inputs?
This is a finite sensor/processing diagnostic, not another flat-ROI photographic
noise score, a profile fit, default promotion or SOTA quality measurement.

Root ran the mandatory prior-art query once, exit0, on2026-09-09:
    
    C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe -I -S -B experiments/ORCH-drift-check/prior_art.py "sensor noise" "temporal variance" "pyramid" "green luma"

The query is a source/report search, not a scientific control. Its complete
reported headline set was V-DILUTE.md, M130-crop-early.md, BUILD-PYRNOISE.md,
BUILD-SOFTGATE.md, M194-production-truth.md and V-REVIEW-aura.md; secondary
matches were ORCH-veiling.md, BUILD-HULL.md, BUILD-ELECT.md, BUILD-BLEND.md,
V-hull.md and BUILD-SHARP.md, all under docs/research. The source matches
included the native fold/domain and BandMerge. Root read BUILD-PYRNOISE's
instrument/geometry distinction; its aligned photographic flat-ROI result is
not the same-site fixed-focus prediction now proposed.

Also binding are the priority review's examined M48/M61/M68 calibration
corrections, M71/M90 fixed-pattern and rho_warp amendments, M72's voided
materiality bar and sensor-wide covariance, M92/M92b controls, M135/M189
repeat/detail limitations, M164/M166 reference requirements, M141 inventory,
current scorecard roles, M193c's closed mixed/failed geometry and M194g/h's
closed policy tradeoff. Name an already-answered question and stop if this
proposed question is also already resolved. Do not redo those measurements.
Source search/inspection identified a next question; it has not proved a defect.

## Fixed available source population

Use only these27 proposed control RAW files, all already captured:
    
- D:/personal/macro/requests/10-paper-iso-var/DSC00235.ARW through DSC00239.ARW:
  five files, recorded ISO160,1/8s,f/5.6, M141 segment15.
- D:/personal/macro/requests/6-11-extended-dark-frames/DSC00872.ARW through
  DSC00893.ARW:22 files, recorded ISO160,1/8s,f/5.6, M141 segment1.

Root checked both exact segment rows in the existing capture-segments.csv.
That is inherited metadata, not a new decode. These groups are CONTROL, not
quality holdout. They differ in time/release mode and may differ in temperature
or camera state; do not call them a matched physical calibration pair or
subtract one into the other without an independently justified contract.
Do not touch protected bee repeat pixels, reinterpret burned slide/ruler
material as holdout, widen to a full corpus, or request another capture.

The native source, active geometry, per-frame levels, ISO/profile provenance
and code-value decode must be authenticated against an independent decoder
on the SAME files and active-domain addresses. Previous M193c rawler/rawpy
visible-width and white-level differences are known choices to resolve,
not mismatches to erase by cropping to whatever passes. Never read rawler
or other forbidden dependency source. Corpus files remain read-only.

## Consumer and sampling boundaries

Use the M194 native source/production seam and current BandWorker::fold,
load_frame, extract_planes, luma_variance and BandMerge::add_frame_with_gain.
Store u16 CFA; use f32 arithmetic and at most current-frame preparation.
No new merge, no materialized aligned stack, no RGB conversion before the
measurement. Current production policy/coefficient/profile/defaults stay fixed.

Distinguish sensor codes before black subtraction, consumed clamped CFA
planes, green luma, injected variance, actual beta and band predictions.
All four photosite planes and a finite set of within-plane neighbours must
remain visible. Dark clipping can change noise transfer without implying an
incorrect gain. Spatial SD is not temporal sigma; no paper texture/gradient
score serves as a noise denominator. No sample may be chosen because its
measured residual makes a desired ratio.

The independent protocol must choose a SMALL finite spatial sample before any
RAW pixel read. A proposed ceiling is five128x128 CFA-plane windows, each with
predeclared support/interior/boundary roles. The final plan may use fewer or
smaller windows and must state native active origins and output-grid gauge.
Use production Crop-before-pyramid semantics where relevant; do not silently
treat crop-boundary coefficients as an interior white-noise population.

Separate unwarped/no-map white-floor execution from an explicitly placed
identity map, which reaches the measured-floor probe. Neither is evidence
that real paper stayed stationary. A fixed input-only illumination/motion
screen must have a positive planted nuisance and a null and must be independent
of residual-based site selection. Refusal stops the affected inference; no
registration, illumination fit or profile refit may rescue it post hoc.

## Independent protocol and finite controls

Before executable work, the independent author must freeze:
    
- exact sites/regions and native coordinate conventions;
- temporal estimators, degrees of freedom, block dependence and uncertainty;
- independent signal/prediction terms and the noise-model failure directions;
- input-only nuisance/refusal rules and examples that can fail each;
- the finite current-policy arms and required actual observation points;
- exact simulation witnesses, decode/address and variance-scaling destroyers,
  restored controls and minimum exercise counts;
- output byte identity for observer off/on/placebo on the SAME native route;
- what agreement, disagreement and premise refusal each permit us to conclude.

A synthetic witness validates software power, not physical sensor calibration.
A model-generated noise plant cannot independently validate its own constant.
A low-noise result is not a photographic improvement; smoothing and clamp can
reduce variance. Report direction/scale along with the separate null. Five
paper repeats do not identify a full photon-transfer curve.

Read actual consumer arrays/operands where the API permits. If an observation
requires a new narrow accessor, propose it explicitly; do not substitute a
parallel implementation and call it the consumed value. Source telemetry and
independently saved arrays have different evidentiary scope. Any observer
added to the merge must be hash-tested against off and placebo.

## Ownership, source grants and release

Root owns this charter, source integration, scheduling, source/evidence commits
and all later execution grants. AGENTS names the allocation before dispatch.

factor_eight_implementation owns source/implementation-contract.md and an
UNAPPLIED source patch under this experiment, plus the proposed native adapter.
First settle observation points and existing reusable observer capabilities.
Propose minimal changes to merge_cmd.rs and one test-only native-sensor-transfer
child. Any core observation accessor or broader source edit needs a root
scope decision before application. Do not alter live crate files yet.

coordinate_verification owns independent-protocol.md and independent checker/
decode design here, choosing nuisance/ROI/prediction terms independently of the
producer's candidate outputs. No candidate output exists yet. Use primary
decoder APIs without reading forbidden library source; any rawpy view must be
copied inside its owning context. Plan independent same-file code comparisons.

sampler_result_review owns source-choice-review.md and the later independent
result interpretation; it must challenge the choices it made in the priority
recommendation, including ISO160, dark clamp, the short paper burst and crop
boundary gains. Its priority authorship is disclosed, not called independence
from that choice.

Each source-preparation lane has64MiB repository-source/report reads,
4MiB newly retained source/docs,60CPU/120active-process-wall allowance.
These are finite preparation grants, not measured resource claims. No RAW
payload, fixture generation, simulation, numerical control, Cargo build/test,
product invocation or candidate execution is released. Source parsing/sizing
and ordinary publication are allowed; record failures and unknown actual
totals honestly. Root later adopts independently reviewed build/commission/
decode/observer/analysis caps and exact source/command/environment identities.
Reuse existing owned-process capture tools; avoid another bespoke provenance
framework or repeated successful source/control campaigns.

All27 original identities, bounded decode lifetime and independent-decoder
plan must be held before execution. Preserve complete stdout/stderr/exit and
failure prefixes. No automatic retries or larger population after failure.
The source preparation itself may show the proposed inference is untenable;
that is useful progress and does not require a data run.

Stop after the first interpretable fixed outcome. Agreement closes this
limited transfer diagnostic; disagreement identifies a stage to challenge;
a premise refusal remains a refusal. Each requires a separately reasoned next
task. No policy/noise-profile update, M1/M2 resurrection or SOTA admission
follows automatically.
