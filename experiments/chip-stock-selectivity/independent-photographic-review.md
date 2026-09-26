# Independent photographic result: reject the fixed flat2 arm

VISUALLY REVIEWED on 2026-09-25: **the fixed ramp1.4-to1.0, exponent2 change does
not provide the required useful chip quality improvement.** Close this arm;
do not transfer it to marigold, sweep its strength or promote it by smoothing
the stipple score. This is not evidence that every possible source/depth model
fails.

I inspected both complete overviews first, then all 25 registered native pairs
(50 files) in their fixed order. The rail was viewed at unresampled 384 pixels;
the six other regions were each fully covered by four unresampled 256 tiles.
Both outputs use the same 6500x4332 geometry, RGB16-to-8 conversion and ICC.
The native-view receipt records every file and coordinate. Complete images
establish overall appearance; they were not used to infer fine-detail fidelity.

| Fixed region | Paired observation |
| --- | --- |
| Rail crossing | Broad yellow/green glow and multiple coloured edges remain. The flat2 arm softens fine mottling and contact marks without restoring a distinctly cleaner rail separation. |
| Upper colour | Small rectangular interiors and fine subdivisions appear softer. Broad horizontal colour spread persists; no compensating boundary improvement is identifiable. |
| Central stipple | Blue/red granular appearance decreases, but the compartment's broad multicolour edges and extensions remain. Quieting the interior is not proof of correct detail or reduced sensor noise. |
| Lower array | Main repeated gaps and cyan cell boundaries remain recognizable, but their finer borders/interiors are smoother. No useful new separation is identified. |
| Lower colour | Broad green/blue boundary transitions remain soft. Shadow contact dots, lines and small surface marks lose prominence; no restored structure offsets this. |
| Surface scratches | Main diagonal scratch trajectories survive. Fine surrounding flecks/texture weaken and the paths become smoother; this does not constitute new resolved detail. |
| Upper-left contact grid | The strong bright plumes and overlapping coloured contact edges remain in all four pairs. Several contact shapes/interiors are softer, while the cleaner separation visible in the earlier HeliconB whole field is not reproduced. |

The complete candidate has a slightly smoother overall appearance but does not
resolve the owner's broad spill/ghosting complaint. I do not claim every small
baseline fleck is true scene texture, or that every disappearing speck is lost
detail. The rejection is based on the missing promised boundary benefit together
with visible softening of protected structures. No scalar sharpness, clipping,
noise or changed-pixel statistic was used to reach it.

Tone is a material limitation. Retained rounded logs give baseline black
0.00432, white0.94644 and candidate black0.00463, white0.86036, with contrast0.55
in both. The actual automatic tone anchors were not pinned across arms. Thus
global/local brightness differences cannot be assigned solely to selection
weights, and stronger brightness is not a restoration claim. The observed
softening and persisting broad plumes nevertheless fail the delivered-image
criterion as registered.

The root-run completion binds all 299 inputs, reference149, common crop
[133,89,3250,2166] and repaired executable. It records exactly two command-value
differences: ramp1.4 becomes1.0 and the output path changes. Originals and held
references are reported unchanged. Candidate TIFF SHA256:
`d5342cef36fc70946ba0f09855880f6eaf3086574c15feec42d5243e6a4b07ee`.
The reviewed complete output is run-1/stack-master.tiff, with full JPEG and
overview beside it. Baseline remains outputs/quality-september25/chip-fixed.

No RAW job, render or parameter change was performed by this reviewer. The
single whole-stack trial has answered its narrow question; additional ramp,
exponent or band tuning is not the next program action.
