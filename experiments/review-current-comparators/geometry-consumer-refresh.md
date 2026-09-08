# Geometry consumer check on external methods

2026-09-08, root. VERIFIED primary-paper content; ARGUED scheduling decisions. This is a bounded desk review, not an external method run, comprehensive SOTA survey, new comparator admission or physical-truth measurement. No external repository source, model, dataset or capture was downloaded or opened.

## The 2026 result does not remove alignment as an input

FOSSA, Zero-Shot Depth from Defocus, was submitted in March2026 and revised in June2026. Its task definition requires pixel-aligned RGB frames and focus distances in meters, and predicts a metric depth map. ZEDD's appendix reports unstable direct alignment of large-aperture images. Its acquisition pipeline instead estimates transformations on F/16 captures and transfers them to wider-aperture captures at matching focus settings. The paper also identifies motion/alignment robustness as future work. These are the authors' method and limitations, not measurements on strehl.
[Primary paper, sections3.1, A1.4 and A6](https://arxiv.org/html/2603.26658v2).

ARGUED: retain FOSSA/ZEDD as a later depth-development reference. Do not intake another learned model to solve M193c's missing geometry: the paper assumes that input and obtains it with additional captures. The stopped-down capture route could motivate a future independently validated physical-reference design, but is not available evidence for the present stacks. Neither a metric-depth claim nor its reported depth benchmark validates macro placement or merged RAW quality. No extra photograph is requested by this memo.

## Visually good warps can answer a different question

Video Depth-From-Defocus uses coarse-to-fine refocusing and patch correspondence. Section4.1 explicitly permits geometrically wrong matches to visually similar regions because they help its defocus-preserving warping objective. Its matching costs therefore cannot be treated as a physical-placement oracle for the common denominator consumed by strehl.
[Primary paper, section4.1](https://arxiv.org/html/1610.03782v1#S4.SS1).

Depth from Focus with Your Mobile Phone combines adjacent affine initialization with concatenated optical flows. That is a concrete prior design, not permission to chain this project's deep stack.
[Author-hosted primary paper, section4](https://www.supasorn.com/Suwajanakorn_Depth_From_Focus_2015_CVPR_paper.pdf).

ARGUED: do not use attractive alignment examples or photometric similarity as the acceptance bar. A repeated pattern can improve appearance while moving material to the wrong site. The consumer remains per-frame gathered placement in a named gauge, with curved-track truth and occlusion/support limits.

## Existing negative evidence takes precedence over rediscovery

The local read found the already measured blur-equalisation experiment, not an untested opportunity. M78's cross-blur and sampling-phase arms did not pass their registered held-out criterion. M103 explicitly records those prior failures and also explains why their chosen pairwise criterion did not settle global gain. Neither observation licenses repeating the old arm unchanged or pretending the old criterion established per-frame accuracy.
[M78](../../docs/research/M78-blur-equalised-edges.md),
[M103 section3](../../docs/research/M103-halfdrift.md).

The saved local-image probe still awaits numerical verification after two checker startup-authority refusals. Those operational failures provide no evidence for or against correlation, blur compensation, a physical displacement model or the stacker's image quality. The already verified empty feature-match graph remains the current real registration outcome.

## Decision

First recover the existing saved-data checks in a deterministic, declared checker environment, retaining the refused original subject and all costs. Do not rerun image extraction or tune the fixed patch population to repair audit metadata. Then choose the next geometric experiment from the verified local outcomes. Any returned local translation remains a diagnostic until a separately tested direct-edge/per-frame consumer validates it. Keep source-only systems integration moving independently.

This review changes the research queue only by ruling out an unsupported shortcut: neither a depth model requiring aligned inputs nor an appearance-preserving warp supplies the missing physical registration. It does not select a new production alignment implementation.

## Read record

Web search queries actually run included 'focus stack image registration different defocus blur invariant image alignment paper scale magnification', 'defocus blur invariant image registration cross blur equalization focus stacking paper', and targeted title searches. Primary arXiv HTML was read for1610.03782v1 and2603.26658v2. Author-hosted/cvf search text supplied the2015 section4 description. Two initial PDFs failed to fetch and supplied no new full-text evidence.

Local text search actually run: rg -n -i 'VideoDfD|Suwajanakorn|Myles|Desch.nes|blur.equal|cross.blur|Grossmann|finite aperture stereo|defocus.preserving' docs/research experiments/ORCH-drift-check --glob '*.md'. It found M78, M103 and the synthesis record. Targeted PowerShell reads covered M103's commission corrections and M78's first175 lines. No forbidden GPL/LGPL implementation source was opened.
