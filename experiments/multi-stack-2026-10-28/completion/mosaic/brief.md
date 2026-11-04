# Focus-aware mosaics: completion lane

State: active research and interface design, 2026-10-28. Owner: architecture.
Allocation: the root's multi-stack completion allocation. Product source remains
frozen until root agrees to the interface and grants paths. This is a continuation
of the user request, not a claim that the earlier session implementation fulfilled
stitching. Capture directories stay read-only.

## Question and consumer

Can the supplied peacock ore, marigold and grid views support an extended-field,
multi-perspective focus mosaic, with a measured, visibility-aware backward warp
and bounded original-CFA gathers? The desired output preserves the union of useful
source views. The output is not a metric-depth reconstruction or an orthographic
view. There is no primary pass preference for stitching.

The proposed consumer maps each output CFA site through a spatial pass warp and
the source frame's measured breathing placement, then gathers its original u16
same-color CFA samples into bounded f32 workspaces. One final demosaic remains.
Focus evidence is ordinal and uncertain; it is not physical depth. Source support,
visibility, clipping, focus reliability and disagreement remain separate facts.

## Bounded first measurement, preregistered before running

Use five evenly spaced acquisition positions from each actual pass: marigold
2.1+2.2, 3.1+3.2, off-center .1+.2; both peacock ore directories; all five grid
directories. Extract untouched embedded JPEGs only. No RAW pixel decoding or
full render is authorized in this lane yet. Four CPU threads maximum; OpenCV
worker threads are bounded and feature extraction is sequential. Record JPEG
SHA-256, source path/size/mtime, settings, commands and implementation versions.

Commission the candidate finder first using known translated random texture,
unrelated texture, blank texture and a periodic-grid ambiguity control. The
positive case must recover the planted translation; negatives must not pass the
same candidate bar. A synthetic depth-discontinuous displacement checks that a
single global warp is not mistaken for validated local geometry.

At a 1280-pixel maximum side, use SIFT and reciprocal ratio-0.70 descriptors.
Fit homographies with a 3-pixel RANSAC threshold, but reserve one third of a fixed
6-by-4 spatial grid for evaluation. Candidate support requires >=25 training
inliers, >=10 held-out correspondences, >=4 occupied cells and convex-hull area
>=2% in each view. Held-out p90 <=3 preview pixels is only a coarse global-model
screen. Save failed models and residual distributions too; non-global overlap
can remain useful to a local/depth-aware model. Repeated grid candidates require
additional distinctive nonperiodic evidence and are never certified by periodic
RANSAC consensus alone. These preview bars are not native placement guarantees.

No sharpness or resolution gain will be inferred from gradient energy or JPEGs.
JPEG matching can be fooled by repeated texture, view-dependent specularities,
focus-dependent feature migration and camera sharpening. The later consumer
acceptance requires native source-backed geometry, held-out depth strata,
occlusion controls, full-output comparison and independent review.

## Prior work and changed question

The original Proposal.md proposes focus-index-conditioned parallax correction and
coverage-aware multiscale blending. It supplies optical arithmetic, not measured
registration. The earlier corpus report only inspected sparse JPEG orientation;
it did not test overlap. The earlier architecture/challenge reports explain why
the current global similarity and intersection canvas cannot implement mosaics.
`docs/research/B-algorithms-sota.md` distinguishes depth-dependent parallax from
global breathing; its claimed lack of literature was explicitly unconfirmed.

Repository discovery commands run for this allocation:

```powershell
python scripts/research.py search mosaic parallax focus
python experiments/ORCH-drift-check/prior_art.py mosaic parallax
```

The mechanical search also returns demosaic research because of the shared word
"mosaic". Those are not evidence about extending field of view. Current
engineering invariants and prior rejected reconstruction evidence still apply:
synthetic operator success does not establish photographic quality.

## Acceptance plan

1. Find real shared content, distinct expanded coverage and focus-dependent
   residual behavior, with named positive/negative pairs and complete previews.
2. Agree a core field/canvas/visibility API and CLI ownership before product edits.
3. Commission native CFA spatial gathers, global-phase tile halos, visibility and
   constant/flat/noise controls, plus a planted depth-discontinuous scene with a
   foreground occluder. Compare a global warp and shuffled focus-label placebo.
4. Test real overlap at held-out sites in the consumer's gauge. Emit local refusal
   and selected-view masks rather than ghosted mixtures across disagreement.
5. Render complete useful union canvases under an explicit resource reservation,
   inspect identical-display full outputs and native seam/depth witnesses, then
   obtain independent review. Record conditional failures without declaring the
   whole feature deferred merely because captures are imperfect.
