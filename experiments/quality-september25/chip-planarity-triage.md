# Chip planarity triage

**READ / VISUALLY REVIEWED / ARGUED, September 25 — insufficient evidence for
a new planar-source treatment.** A same-development whole-size source already
exists. A physically constrained focus-manifold merge is not an executed chip
comparison in the inspected records, but its necessary source support is also
absent. Do not turn that absence into another source-subset sweep or an asserted
planarity fix. No RAW, fit, build or render was run for this review.

**What already exists.** `cross-scale-source-prior/chip-cost-1/output/baseline.tiff`
is a complete 6468x4300, single-source149 actual native-consumer image: held map,
CA, WB, matrix and fixed historical chip tone. Its receipt explicitly has
`source_count=1` and frame149, with exact baseline/candidate planes and RGB16.
`probe_source_count=299` does not mean 299 images were merged. This was a
cost/identity control, not a registered whole-chip photographic improvement
test. Its crop[141,97,3234,2150] also differs from today's chip-fixed crop.
There is no reason to render it again merely to obtain a whole-frame comparator.

All299 full-resolution same-developer source TIFFs also survive in
`chip-competitor/run-1/developed/`. `frame-149.json` binds DSC00150.tiff to the
original and its 7032x4688 active image. `development-complete.json` records
the actual product decoder/MHC/WB/matrix/fixed tone and checked ICC. Those TIFFs
omit CA and alignment, whereas native Current includes CA. Their existence is
not a finding that one source is globally sharp or a controlled merge-only test.

**The source evidence is local.** The independent
[chip-source verdict](../quality-september14/chip-source-verdict.md) finds
reference149 focused at the pale rails, but strongly defocused at fine-grid
and colour-edge. I re-opened the retained matched `raw-native.png` and
`merged-native.png`: the source has tighter rail contours and less broad spill,
but already has dotted coloured edges. The matched developer removes the earlier
LibRaw/product tone discrepancy; source versus merged still differs in gather/CA.
This is neither a clean whole-image replacement nor proof of fusion-only colour.
The same saved145–153 neighbourhood already supported the local geometry
correction, followed by a modest complete299-source benefit; that intervention
and its unsuccessful star-sand transfer are not a new planar route.

**What remains unestablished.** No inspected chip receipt provides independently
held-out best-focus support across its distant contact, rail, grid and coloured
regions for one surface, or for a narrow source interval at each position.
Physical flatness does not make the sensor focal surface coincide with the chip.
The existing source149 counterexample prevents assuming a globally focused frame;
it does not rule out every other frame. No search for such a frame was performed.
M-PHASE0-CURV studies a separate tilted ruler and explicitly does not test global
sharpness. M145's affine focus surface is restricted to a planar, equally stepped
rail capture; it does not license a plane in frame index for this camera bracket.
A proposed manifold without that evidence would impose another source prior.

**Prior closures remain.** V-DILUTE rejects density dilution, not merely one
implementation. ORCH-veiling demonstrates a single-frame advantage on another
scene but cannot establish this chip's source support. M70 retains useful
off-peak signal and rejects treating its informative-frame count as a universal
admission target. Current chip flat2, same-band agreement and finest-derived
shared-field trials already failed; the latter creates colour islands. The
coarse prior's limited broad-boundary benefit retains its depth/glint harms.
Helicon B supplies a whole-field quality gap, not planar-depth evidence or an
accepted matched-native detail benchmark. None justifies discarding sources here.

Mechanical command run: `python -I -B experiments/ORCH-drift-check/prior_art.py
planar stack globally focused source subset`. It returned C-landscape, V-SPEED,
B-algorithms-sota, M86, E-plugin-architecture, BUILD-SHARP, M10, A-prior-corpus,
V-DILUTE and M60b; targeted follow-up read ORCH-veiling, M70, M-PHASE0-CURV,
M145 and the current chip source/consumer/comparator closures. This is a bounded
negative triage, not a claim that every possible planar method has been tested.

## Addendum: a testable spatial focus front, not a global source

**ARGUED — a bounded fit is justified; absent validation is not a rejection.**
M67/M73 show that shape invariance can test focus behaviour while a smooth field
can be many frames wrong. M73 changed no merge, lacked its circumferential reference,
and left shipped admission inconclusive. Neither it, M70 nor prior chip rules test this front.
Missing: a shared spatial coordinate with a nonuniform frame-to-focus schedule,
not an affine plane in frame index; absolute depth remains unidentified.

Minimal proposal: hold geometry fixed; fit complete through-focus curves on a
fixed sparse training grid to one planar coordinate `a*x+b*y+c`, monotone frame
positions `t[k]`, and one fixed Gaussian response family per spatial band
(training-only amplitude/width nuisances). Joint curve fitting uses no local
argmax labels. Fix the schedule's arbitrary offset/scale and freeze the model.
Gaussian is a rejectable response approximation, not a calibrated PSF; M70's
multimodality and useful off-peak signal remain live limits.

Reuse the saved299 developed TIFFs and held chip map for a cheap proxy screen;
M70's `src/s04_through_focus.py` fixed-grid/band layout and `m70lib.py` spectral
helpers are reusable, but its RAW-noise subtraction cannot be applied to toned
TIFFs. No full-chip native focus curves were found retained. Predict withheld
spatial blocks without refitting; separately check predicted source support in
a withheld frequency band, not residuals against the fitted plane itself.
Freeze errors/bars before fitting. Require a nonuniform-step planar positive,
flat null, curved/occluding adversaries and a shifted-front destroyer; smooth wrong predictions must fail.
Only after prediction passes, reuse `band-source-agreement/full-adapter.rs` and
its actual per-band weight replay for one complete native comparison: intersect
existing AC admission with predicted focus intervals, retain canonical fallback,
base/noise/geometry/pinned tone, and refuse unsupported regions. Assess held-out rail/grid/contact
detail and the full image; lower fit error or fewer contributors cannot admit it. Proposal only.
