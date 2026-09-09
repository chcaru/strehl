# Native sensor transfer continuation

2026-09-09. SOURCE PREPARATION. No RAW payload, simulation, numerical control,
test, build or product execution has been released for this task.

Root adopted raw-program-priority-review.md at59202e51df6c09485099618a393ebad0b5468777.
The integer common-TIFF design is retained but deferred; native RAW sensor
information and the owner's existing requests corpus drive the next work.
Completed dimensions report/review aa8390dd stays closed; do not rerun it.

Charter/AGENTS allocation c6a9128e5592815ffccfdfcb3404c8e253a0f80f,
charter9945B5f2e183de6e4e04fe8481304cdad860214eabe23b834b859451d8657ca9e4852.
Mandatory new prior_art query ran once, exit0; exact command and all returned
reports are in the charter. Current native source paths were clean before
dispatch. No live crate edits yet; implementation patch must remain unapplied.

## Fixed source and domain

Exactly27 existing CONTROL RAWs, never protected bee-repeat holdout:
paper DSC00235..00239 and dark DSC00872..00893, under the two named requests
directories in the charter. Root matched the exact M141 segment15/segment1 rows,
then checked file metadata only. All27 are present, encoded926855168B,
paper192868352B/dark733986816B/max38825984B. No content hash, decode or new EXIF.
Different release modes/time/camera state remain explicit; not a matched
physical calibration pair. No new capture is needed.

Root chooses ONE actual128x128 CFA-plane Crop at quad origin(1694,1108),
conditional on independently verified7032x4688 active /3516x2344 quad domain.
No automatic crop-to-pass or full-frame-pyramid/five-window substitution.
Keep all4CFA planes and finite within-plane neighbours in that one window.
The result will be local current-policy opt-in Crop transfer, not sensor-wide
calibration or certification of the full-frame Scale default.

Configured/default bands stays7. Current level_sizes stops below8:
actual128/64/32/16/8 levels, four Laplacians plus base, exponent_at(k,nb4).
Retain requested versus actual depth, complete support/phase/boundary strata,
and actual measured-beta prefix versus white fallback. The16x16 band cannot
satisfy256 trimmed probe samples and current probe code excludes unsupported
coarse levels. Do not invent a measured k3 floor or an interior inference.
No-map white floor and placed-identity measured-probe paths are separate.
Identity probe variation alone is not physical noise-model error.

## Owners and scope

factor_eight_implementation: source/implementation-contract.md and unapplied
native adapter/hook patch. Reuses M194 actual RawPyramidSource/load_frame/
extract_planes/BandWorker::fold/BandMerge and writer. Root scope-amendment-1
authorizes a default-off native-sensor-transfer feature in CLI/core Cargo,
experiment-owned passive core-hook.rs and minimal read-only observation calls
in pyramid.rs at actual gate/plane-consumption operands. Do not touch M194h,
force cache preparation, mutate weights, reorder arithmetic or write a parallel
merge. Observer comparisons require same-feature off/on/placebo and appropriate
feature-off byte preservation. Count full-frame probe synthesis/warp costs as
well as streaming RAW decodes; one Crop avoids27x5work.

coordinate_verification: independent-protocol.md and checker/decode design.
Choose exact temporal contrasts, independent signal witness, nuisance controls,
uncertainty, phase/support and sample roles BEFORE any RAW pixels. Paper
proposed primary two disjoint contrasts with fifth signal witness; all5
variance as sensitivity. Dark11pairs/all22. These choices are still source
preparation, not accepted observed results. Spatial pixel counts are not
independent temporal repeats; no chi-square claim for smoothed energy.
Paper nuisance refusal must not erase independently interpretable dark data.

sampler_result_review: source-choice-review.md; challenges recommendation
choices including crop boundary, short burst, Gaussian/quantized noise,
data-coupled native luma_variance, nearblack clamp and current beta. Priority
authorship disclosed. Actual gate is smooth5(L squared) versus gate*beta*
GaussianReduce(V); temporal noise comparison must remove scene signal and
retain those operators. It is not a raw-Laplacian-only check.

Each lane:64MiB source/report reads,4MiB newly retained source/docs,
60CPU/120active process-wall SOURCE PREPARATION ONLY. Record actual known
costs and failures; no fabricated exact totals. Core scope extension remains
an UNAPPLIED patch. Root alone integrates, commits and releases executions.

## Remaining work

Finish and independently review protocol, observation-source patch, fixed
synthetic falsifiers/observer witnesses and decode/runner/cap design. Register
all exact command/environment/source/input identities and stage resource
bounds before application/build or any scientific read. Reuse existing owned
process tools, not another provenance framework. Independently decode the same
originals, resolving native active/white semantics explicitly, copying rawpy
views while their owner is alive. All source corpora remain read-only.

Stop at the first interpretable finite result. No refit, wider corpus,
registration rescue, profile/default change or SOTA metric follows from it.

## Source-choice review and native processing correction

source-choice-review.md is published15806B,
22043fee103588a2b603e785fd20625608515c55594e3e88778f6989eb57482e.
Root read it and accepts preparation, not execution. It re-chooses the paper
temporal contrast/prediction witness, retains covariance/clamp/quantization
limits, identifies actual smoothed-energy gate operands and derives phase
support. Final protocol and observer patch are still required.

scope-amendment-1.md2606B175697f4d4b5f42b2221d73577fdeeb4e75b6845c6a4aec9294b75fe1fecb0d4
and scope-amendment-2.md3969B5e14f570195b964e47bee6ea6c291c9416d7aa058add64e1a05ef3ad08f9eaeb
bind the expanded passive observer source scope and actual native processing.

Root corrects an earlier user explanation: final output demosaic is NOT the
only interpolation stage. Current default warp_frame_in_place_fullres already
MHC-demosaics temporary full-resolution channels before per-channel gathering
and u16 CFA-site reinsertion. It also applies/removes working white balance and
composes CA from the actual capture identity. Root independently read the
actual source after the reviewer caught the charter's overbroad no-RGB phrase.
Preserve these internals and report their transfer; do not disable them to
force a clean-looking CFA/identity null. The new diagnostic adds no external
RGB input and must not duplicate the merge.

A placed identity geometric Similarity can retain nonidentity R/B CA maps.
Physical-prediction eligibility needs actual transformation provenance and
appropriate green-site equality; a failed premise means not identified, not
a refitted law or a discarded result. No source mutation or RAW read has
occurred. Factor and coordinate are continuing source/protocol preparation;
sampler is available for the cohesive final source review. Root has not
granted build, application, decode, control or image execution.
