# Quality continuation: no implementation candidate justified by this review

2026-09-09. Independent source/report triage only. No implementation, build, RAW decode, image read, experiment or new quality score was performed. This memo does not prevent other evidence-supported development; it says that the specific candidates examined here do not yet justify another implementation cycle.

**Decision: do not dispatch the initially suggested CDIFF replay.** The first source skim identified a small output-only seam, but reading the complete prior verdict removed the justification. Ease of implementation is not new evidence of a useful photographic improvement.

## Why the tempting small change does not earn a rerun

M95-cdiff already evaluated linear colour-difference reconstruction against Malvar green. It improved its band-limited R/B signal quantities while leaving green unchanged, but luma gain was 0.0124 dex against its registered 0.03 bar. The fixed truth-selected 1:1 crop was visually indistinguishable, and direct pixel MAE was almost unchanged. Its CDIFF2 refinement raised artifact share and worsened pixel error in every channel. Those failures remain; native integration alone would not reverse their scientific meaning.

The exact current consumer would be `crates/strehl-cli/src/image_out.rs::write_demosaiced`, which calls `demosaic_row` before `develop_pixel`, reached from `merge_cmd.rs::write_merged`. Changing only that call could preserve the merged CFA, alignment gather, probe and noise decisions. Changing the global demosaic selector would also alter the per-frame full-resolution gather and synthetic probe, defeating that isolation. This is an identified implementation seam, **not a recommendation to implement it**.

The main falsifier would be genuine colour-only structure: reducing R-G/B-G error on an achromatic subject can simply erase real chroma. The existing saved analytic-colour fixture can express this property. In canonical `experiments/m194b-known-scene/produce.py::analytic_color_rgb`, output is `(light + redblue, light + green, light - redblue)` with independently declared chromatic waves. The red-blue difference therefore contains known signal independently of the common light term. Its `chroma=False` partner removes those waves. However, `color_electrons` changes only geometry between its frames; it adds **no focus-dependent chromatic PSF or axial CA**. These arrays can reject chroma erasure or mapping errors, but cannot establish that a chromatic focus-offset correction recovers detail. The noisy scalar plane and flat fixtures add noise/detail controls, while the existing larger shared-pupil boundary supplies an occlusion-artifact case. Reusing them would avoid rebuilding apparatus, but the available fixtures do not by themselves supply a new CDIFF mechanism or decision.

## Other reviewed leads and their binding limits

| Lead | Existing evidence | Decision here |
|---|---|---|
| Per-channel focus-index offset for axial CA | M107 and BUILD-CHROMA establish axial focus separation. M-PHASE0-LCA files NOT ROBUST for the requested field-valid offset. | Do not turn existence into a fixed offset. The saved analytic-colour fixture cannot test chromatic defocus, and a new offset/model campaign is outside this bounded continuation. |
| Blur-equalized or metacalibrated short-edge alignment | M78's blur equalization improves conservation but worsens the paired held-out result. M103 shows spectacular endpoint improvement without per-frame improvement in the merge's gauge. | No reused endpoint bar, global gain or Gaussian cross-blur retry. A new alignment algorithm needs an independently specified per-frame failure that the current saved consumer can express. This review found no new source defect establishing one. |
| Phase-based defocus-invariant alignment | Potentially distinct algorithmically, but symmetric defocus is not globally positive in Fourier space; optical zeros, sign reversal, aliasing and poor common focus undermine the simple phase-invariance premise. | ARGUED research lead only. No current commissioned comparison or isolated implementation justification was found in this bounded review. Do not sell it as a ready fix. |
| More pedestal/cutoff, signed black, global beta or gain adjustment | M194h's cutoff fixes one selected error while worsening the broader comparison. Both recent signed-black variants lose texture; native sensor-transfer identifies no global correction. | Remain closed. No additional knob sweep. |
| Broad photometric or ghost-rejection port | BUILD-GHOST found no delivered ghosting in its inspected cases and nominated foam as the specific exposure exception, not the whole corpus. | A generic port is not supported. A foam-specific intervention would need its own fixed native consumer and exposure premise; neither is supplied by this review. |

## What would change this decision

A next quality brief should start with one concrete, currently measured wrong delivered value or lost known structure and identify the operator that can change it. It must state a different causal intervention from the rejected arms above. The saved production-truth input/output seam is ready for that test; it does not require another renderer, TIFF parser, provenance framework or capture request. For a candidate supplied by another lane, run the smallest existing flat, oriented-detail, genuine-colour and boundary controls through the actual consumer, preserving the prior failures and evaluating local error as well as pooled noise. No new quality gain is claimed here.

The initially suggested CDIFF candidate was withdrawn before any code or numerical run. This avoids spending the next cycle re-proving an already below-bar result.

## Search and reading record

Mandatory `Python312 -I -S -B experiments/ORCH-drift-check/prior_art.py` searches executed successfully for: production truth / optical blur / alignment quality / pyramid; chroma focus / colour-only / shared weights / green luma; cross band / sign consistency / occlusion support / band coherence; pyramid photometric / exposure drift / brightness normalization; longitudinal chromatic / per-channel focus / axial CA; Malvar green / colour differences / chroma interpolation; phase congruency / phase correlation / defocus invariant / alignment.

Read the latest program checkpoint, scorecard restrictions and SYNTHESIS architecture/risks, then the relevant passages of M194/b/d/f/g/h, native-signed-black, BUILD-SOFTGATE, V-DILUTE, BUILD-BLEND/HULL/CHROMA/GHOST/SHARP, M95-cdiff, M107, M-PHASE0-LCA, M78, M103, V-DRIFT, M182-kernel-trade and M91. Numerical statements above are prior report results, not measurements by this reviewer. The record includes one recursive source-name search that also returned duplicate snippets beneath M194b's saved source tree; no archived implementation was opened or used as the design authority. Subsequent source reads targeted canonical files only.
