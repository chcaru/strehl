# RAW detail and mineral-glare survey

2026-10-26. Allocation raw-quality-2026-10-26-detail. Read-only survey of main4813e46b, original private reports and selected images, followed by the separately allocated CFA sampler source preparation. No RAW decode, build, test or render executed by this lane. Recommendations ARGUED; no new quality gain.

## Recommended bounded direction

Direct quincunx-CFA gathering merits a small actual-consumer falsifier, followed by a COMPLETE real bracket only if neutral and independent-color detail survive. This question differs from old half-plane interpolation, original-green guidance, all-CFA wavelets and direct float writeback. It is not yet superior and is not a broad glare cure.

Current align_cmd::warp_frame_fullres_coordinates_impl reconstructs full R/G/B per source, samples channels at output CFA sites, invokes a remosaic sink, then the complete merge is demosaiced again. RAW storage is retained but source sampling is not strictly original-CFA-only. This alone does not prove a cause of softness: V-GATHER rejects blaming its chroma excess on double demosaic, while BUILD-DEMOSAIC shows that correlated-noise statistics can hide actual demosaic error.

The new sampler uses measured same-color source sensels with both greens on one quincunx lattice, preserving actual pulls, focus algorithm, injected model, band weights and final development. Root's allocated cfa-brief.md and cfa-design.md contain consumer and acceptance details. Current code seam is align_cmd.rs near2624, with source reconstruction near2660-2715 and pull sampling near2750-2830. The synthetic GREEN_ONLY noise probe must follow the identical sampler. Source u16 must stay immutable across phase writes.

Green coordinates: u=(x+y-1)/2,v=(x-y-1)/2; inverse x=u+v+1,y=u-v. Unshifted half-sum/half-difference coordinates place greens at half integers. Test oblique neutral high frequency, pure/independent R/B features, a weak single-frame witness and unequal green phases, alongside flat noise and phase/coordinate destroyers. Same-color R/B interpolation can lose high neutral detail borrowed from green by current MHC. A high-band score alone is insufficient.

## Prior outcomes that constrain this direction

| Prior | Consequence |
| --- | --- |
| native-direct-planes/results.md | Same fullres MHC gather with direct plane sink; rounded exact, float not promoted. Not the original-CFA sampler. |
| all-cfa-wavelet/results.md | Transform/guide screen failed coarse-neutral; not isolated source sampling. |
| native-green-cue/results.md | Better high-component response coexisted with worse total noisy error in all48 individual cases; keep focus guide unchanged initially. |
| M-PHASE0-QUINCUNX; M-PHASE0-RHO | Green lattice has measured energy beyond individual phase Nyquist. Not a new-image quality result; retain alias ambiguity and anisotropic support. |
| native-cfa-kernel/results.md | COMPLETE299-source chip isotropic/anisotropic kernels were already rejected for softer rails/crossbars/scratches. Earlier patch positives do not supersede this. |
| chip-local-affine-kernel/results.md | Affine kernel already rejected, with persistent stipple and signed-weight amplification; not a new recommendation. |
| chip-vectorial-raw; chip-inverse-photographic-probe | Fixed Lanczos/Huber and capture-anchored inverses did not produce photographic gains; do not infer family impossibility. |
| chip-kernel-placement-ablation | Missing saved local shifts materially blur divisions with frame count fixed; a sampler does not repair wrong geometry. |

The current demosaic unit test explicitly retracts a diffraction-imposed empty high band for this rig; do not reinstate that as a real-photo artifact detector.

## Glitter-weevil identity

VERIFIED directory enumeration: D:/personal/macro/insects/bug-3 has seven subdirectories:100MSDCF299ARW,102MSDCF247ARW,103MSDCF22ARW,104MSDCF299ARW,105MSDCF185ARW,106MSDCF299ARW,107MSDCF299ARW. No other file type appeared in that enumeration. Counts do not establish bracket boundaries, capture regime or full-depth coverage. Do not concatenate blindly or choose22 merely because it is cheap. Root subsequently selected the complete299-source107 group for the first baseline.

Scoped retained Markdown/JSON search found no literal bug-3/glitter/weevil matches; this is not an absence proof because older outputs may have different labels. Old bee-3-cpl is not automatically the requested weevil.

## Mineral priorities and existing masters

Ore source witnesses have sparse original threshold exceedance but extensive developed output ceilings. This does not identify a recoverable missing structure. Existing highlight shoulder/rolloff, shared-neutral-contrast, coherent-source and spectral extrapolation recipes failed. Repeating tone darkening, clipped-source rejection or the same tiny inclusion sequence has low expected value.

Viewed this turn: complete ore composition outputs/quality-september25/ore-100/overview.jpg, then native384 current-white-grain.png and current-blue-facet.png from experiments/ore-native-coherent/views-1. These are context views, not a new comparative or exhaustive full-resolution judgment. The initial guessed current-overview.jpg was absent; the experiment's actual overview format is PNG.

Complete master under original workspace: outputs/quality-september25/ore-100/stack-master.tiff,6702x4468. Leading complete competitor retained: experiments/ore-commercial-comparison/run-1/helicon-b-host/whole-stack.tiff. Prior independent review finds more distinct small grain interiors with stronger red/cyan rims; broad white matrix persists. Geometry, tone and CA differ, preventing merge-only attribution. Retain white-grain[1208,748,384,384], blue-facet[2908,2768,384,384], white-ridge[2200,600,384,384], thin-facet[5940,460,384,384], lower-texture[1500,3300,384,384].

Opal and rutile source witnesses did not establish specific merge-erased structures at their fixed sites. That is no capture ceiling. Target clearer real grain boundaries/color while keeping broad bright source material separate from invented spill. Another complete mineral with a stronger defect is preferable to prolonged diagnosis of the same ore inclusion.

## Primary literature and limits

[Wronski et al.](https://arxiv.org/abs/1905.03277) and the [author project](https://sites.google.com/view/handheld-super-res/) support original-CFA multi-frame reconstruction as a credible architecture. Their burst sampling assumptions do not validate focus-changing optics or this tripod corpus. No external implementation source was opened.

Old A-prior-corpus F5 used limited translation jitter to reject burst super-resolution. That is not a complete per-pixel rank proof: breathing can change local phase, but diversity must be measured among compatible in-focus observations. All-frame phase spread or global translation sigma alone cannot certify it.

## Commands and scope

Executed unified searches: glare; resampling inverse; specular; sampling reconstruction; super-resolution; polyphase; local linear kernel; demosaic once; quincunx. Mechanical searches: glare softness resampling; specular defocus radiance; quincunx green lattice. Source inspected with rg/bounded PowerShell reads, including actual result reports and adjacent reviews. Initial guessed report filenames/PowerShell glob forms produced read failures; directory discovery resolved the relevant reports. No corpus contents hashed, no RAW decoded, no new metric measured. Source writing subsequently produced cfa-lattice.rs and cfa-design.md under the separate allocation; root owns execution and independent reviewer owns photographic/control decisions.
