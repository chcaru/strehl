# Central original-CFA ROI: rejected photographic arm

MEASURED / VIEWED, 2026-10-28. Root executed the frozen release04 diagnostic at
sensor rectangle [3420,2548,192,192], existing insect-repeat-7 geometry/native
master, historical original-CFA cache only. Exact command, binary and host load:
outputs/multi-stack/completion/sr-roi-run-03/receipt.json. Binary SHA256
`aa48df582883061179d11c41223b7e3d383dc7c35b4fe9ac0b932271b84c27b5`.
The process exited0 in90.748s; internal workload89.05s; sampled peak private
1,211,146,240bytes. Raw decodes0. Geometry uncertainty0.10sensor was explicitly
assumed, not measured. No production or photographic gain follows from this run.

The initial cache load refusal under current decoder binding is retained in
sr-roi-run-02. The explicit historical reader checks exact checkpoint normalized
raw-source equality and full-lock equivalence after removing only core's added
sha2 dependency, reconstructs the exact old CRLF binding, and verifies original
identity/stamps, complete header/payload digest and envelope. It never relabels
or writes caches. Root reviewed it and three historical controls passed in
sr-historical-controls-01. Production SourceCache still refuses stale binding.

## What the photograph falsified

The fixed ten sources148–152/437–441 reconstructed R2/G748/B3 pixels of36,864.
The displayed candidate has visible magenta/purple pits where mostly green was
replaced while native red/blue remained. This arm is rejected. Its component
support and scalar/parallel bit agreement establish implementation mechanics,
not useful image quality. Noninvertible native pixels and wholly unsupported
pixels retained exact native float bits. Direct native192px comparison and masks:
outputs/multi-stack/completion/sr-roi-03/inspection/.

Inspection command, one worker, exit0:
`python -X faulthandler -I experiments/multi-stack-2026-10-28/completion/sr/roi-inspect.py outputs/multi-stack/completion/sr-roi-03`.
The inspection JSON binds native/candidate/report hashes and identical fixed
DisplayBaseline. Difference RMSE is not an error or quality metric.

Saved full-track focus puts most usable first-pass pixels near ordinals74–77,
and second-pass near66–71, far from the fixed targets. Broad widths could assign
tiny nonzero weights to those far sources; normalizing them erased the common
small scale. Good geometric phase conditioning then masqueraded as usable
reconstruction from defocused data. New actual-kernel control a03 plants exactly
this failure: dense independent phases with tiny common focus weights must
refuse before gathering, while a qualified near-mode case must reconstruct.
The declared policy is one measured log-Gaussian width around a qualified local
mode, with response exp(-0.5*distance^2) and an absolute exp(-1/2) floor. This is
a conservative locality policy, not a calibrated focus probability. Existing
shared full-track support/multimodality/weak/boundary flags remain mandatory.

The display arm now requires all three independently qualified channels before
replacing any native RGB component; all other pixels retain exact native triples.
Per-channel reasons remain diagnostics. An exhaustive eight-mask control covers
this arm. It prevents mixed-source color holes but does not establish matched
R/G/B blur: positive local-constant kernels can have different sample centroids.
A direct local affine estimator with exact signed influence/variance is a possible
causal next arm if the all-color photograph still fails; it is not yet implemented.

## Spatial selection rather than central repetition

The old ROI is near the breathing center (about300sensor radius), where the
proposal predicts a diversity dead zone. Saved-geometry plus measured-focus
census `roi-source-opportunity.py` ran one worker in2.238s, no RAW. Its best
14source set73–79/365–371 passed allRGB actual Gaussian condition<=20 at only
9/2304 sampled points before motion/clipping/local-registration checks. This
is DERIVED opportunity, not a positive photograph. The central ROI is retained
as a negative; no further full-track center sweep is requested.

Three new192sensor regions were chosen from existing complete native photograph
texture and radius, independently of candidate appearance: origins1970,2090;
2350,1330;4620,2600. Exact native crop and annotated orientation witnesses are
in spatial-selection/. Receipt binds the native source SHA and same full canvas.
The new focus-census.rs streams each original once per phase across all three
windows, preserving all mode ordinals/prominence/boundary and every quality flag.
It caps4workers,3windows,384sensor expanded focus domain,1external original handle
and checked total reservation below2GiB. No candidate is reconstructed by this
census. Execution is pending root scheduling.

Current local-registration.rs is an unmeasured prototype with six controls.
It checks same-color original patches, explicit physical-site/crop gauge,
calibrated two-dimensional information, disjoint training/held-out patches,
and saved versus refined pair displacement in anchor sensor units. A successful
training fit does not certify the saved map. Pair consistency does not establish
absolute channel calibration or a per-source statistical uncertainty; graph
cycle/component checks and photographic prediction remain required.
