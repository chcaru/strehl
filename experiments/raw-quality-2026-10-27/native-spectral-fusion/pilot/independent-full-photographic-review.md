# Independent complete native spectral photograph review

2026-10-27. **VERIFIED visual review / REJECTED as a photographic improvement.**
The complete299 candidate is much clearer than its uniform-average control,
but it is visibly less faithful and less usable than the previous native CA-off
output. Hair/scale separation weakens, colored haze broadens depth boundaries,
and fine regular raster-like texture appears in several subject regions.
The quieter empty background does not compensate for those losses. No product
promotion, transfer release or SOTA claim follows. The broader goal is unfinished.

I reviewed candidate, uniform, prior native, HeliconB4 and HeliconB8 complete
photographs first, then every one of the ten fixed384px witnesses in all five
arms: fifty existing native PNGs. No root appearance verdict was supplied or read.
No new crop, retone, numerical score, reconstruction or source decode was made.
The full JPEG viewer reduced images to about1920px across for whole-composition
inspection; the fifty384px PNGs were opened at original size for detail judgment.
I authored the final writer/view helper, not the fusion operator; this is an
independent photographic judgment, not an independent certification of my own
writer. Its separate source/null/receipt reviews remain the mechanical authority.

## Complete evidence and display

| Arm | Complete photograph | Full RGB16 master | Full float master |
| --- | --- | --- | --- |
| candidate | [complete JPEG](../../../../outputs/raw-quality-2026-10-27/native-spectral-full-views-1/output/candidate/complete-stack.jpg) | [RGB16](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/output/candidate/native/rgb16-master.tiff) | [RGB32](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/output/candidate/native/linear-master.tiff) |
| uniform | [complete JPEG](../../../../outputs/raw-quality-2026-10-27/native-spectral-full-views-1/output/uniform/complete-stack.jpg) | [RGB16](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/output/uniform/native/rgb16-master.tiff) | [RGB32](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/output/uniform/native/linear-master.tiff) |

[All full-resolution camera/CFA masters and fifty witness links](../../../../outputs/raw-quality-2026-10-27/native-spectral-full-views-1/output/index.md); [display bindings](../../../../outputs/raw-quality-2026-10-27/native-spectral-full-views-1/output/views.json).

Both new outputs are6896x4596, active-native origin68,46 in the held reference149
gauge. The same held WB, levels, matrix, tone and ICC were used. The display
conversion is `(RGB16+128)//257`; witness pixels are unresampled and ICC/readback
checks are recorded. Prior native has the same crop. HeliconB4/B8 use their own
7020x4676 alignment/scale and pre-fusion RGB development; their mapped crops are
full-workflow comparisons, not placement truth or a controlled operator ablation.
Their similar visible limitations do not make the new candidate acceptable.

The new candidate's RGB16 SHA is
`4429231573f1a2fcb09b9a7b1c3b12567433c28c6e6923c2653413d127ef8a2c`;
float SHA `bf39ddc7261dceab40c50d1308cbd141c77a6619ed6a637af06d8090d70db0d5`.
The uniform RGB16 SHA is
`506a7d7caecf641a37cb820ca6b9590376f591937497ec32c97d68852d8fffb7`.
The display receipt SHA read for this review is
`dfbf12a668e0410ec9e87dfd1215280a02964e3594c9b33c944f5d5faff9f118`.

## Whole-photograph finding

The candidate retains the recognizable insect, blue joints, turquoise scale
pattern, legs, antennae and the crossing filament at multiple depths. It is not
a failed blank render. Nevertheless, compared with prior native, the body and
legs look veiled: dark grooves are lifted toward blue/green, contours leak into
the black surround, and delicate hairs have less distinct tips and shoulders.
HeliconB4/B8 also retain more distinct scale gaps and hair edges than this
candidate, despite their own unresolved glints and occlusion fringes.

Uniform averaging is severely defocused over the whole animal. The candidate
recovers much of that lost focus, demonstrating a useful difference from that
control, **not an improvement over prior native**. No new topology is required
for acceptance: cleaner existing edges, more faithful tones or quieter color
without detail loss could be substantial. Here the conspicuous tonal/edge changes
go in the wrong direction and are accompanied by detail attenuation.

## All ten frozen witnesses

Coordinates below are `[x,y,384,384]` in the new/prior-native delivered image.
The linked comparison index retains distinct vendor origins without resampling.

| Witness and origin | Candidate versus prior native, with B4/B8 context |
| --- | --- |
| background-black3800,500 | Candidate and uniform are visually quieter than prior native's faint speckle, with no conspicuous new contour here. This isolated flat benefit cannot validate subject detail or final noise statistics. |
| dark-elytron2750,2120 | Dark ridges lose the prior native/vendor granular separation. Blue haze fills the groove; fine regular checker-like and short rectilinear traces are visible around the dark/bright transition. |
| turquoise-scales2120,1340 | Round scale groups remain, but intervening dark gaps and boundary texture soften. The colored area looks washed together; prior native/B4/B8 retain more separation. No faithful detail gain is visible. |
| elytron-seam2950,1960 | The crossing filament remains at its different depth, but is broader/less distinct against the body. Regular dotted horizontal/vertical traces appear among glints and in the dark groove; prior references lack these conspicuous traces. |
| bright-wing-rim4050,1810 | The long pale rim persists. The dark region below carries broader cyan haze, and surface structure is softened. White glints remain; making some less crisp does not resolve glare or the occlusion contour. |
| thorax-texture4520,2560 | Colored beads remain but become less separated, with fine regular raster texture across bead/gap regions. Prior native/vendor gaps are cleaner and individual bright/color centers remain more distinct. |
| upper-leg-hairs1820,640 | The clearest regression: broader green haze above/below the leg, weaker lower hair tips and shaft separation, and a less definite upper contour. Prior native/B4/B8 are visibly preferable; uniform loses most hairs. |
| blue-joint2680,850 | Blue/green gross color separation remains, but blue surface relief and the layered junction soften. The dark band and nearby hairs are less definite. No independent-color fidelity gain is established. |
| upper-occlusion3850,1300 | The blue edge and green junction glow remain and spread into neighboring dark regions. Adjacent dark texture is weakened. The existing bright green glint is still present; the overlap is not repaired. |
| eye-and-antenna5350,2920 | Major boundaries remain but acquire broad colored veiling; edge scales/hairs soften and sparse dark-region flecks are suppressed. Those flecks are not all established noise, so their removal is not credited as fidelity. |

In every subject witness the uniform control is still substantially softer.
Candidate color remains broadly cyan/green/blue, but local warm/cool variation
is less distinct under the veil. No calibrated color truth is available here;
this report does not claim absolute hue accuracy for any arm. Regular traces
are visible observations, not a diagnosis of their origin in interpolation,
windowing, weighting or final MHC. Likewise, the photos do not establish a lens
PSF, a geometry error, an optical ceiling or recoverability of unseen structure.

## Completion and stopping point

The [actual invocation](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/invocation.json) and [terminal process record](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/process.json) bind the root-run full299 command. The latter records
clean exit0, wall7627.829s, observed direct exit/EOF and no cleanup errors.
The [completion receipt](../../../../outputs/raw-quality-2026-10-27/native-spectral-full299-1/completion.json) records unchanged sources; the saved presentation reports
complete images, exact PNG/ICC checks and held-CFA replay parity. These are
execution/mechanical facts, not photographic success or an exclusive full-workflow
speed benchmark. Source preparation/export and preceding control/build costs
are outside this elapsed figure.

The useful stopping point is this complete, inspectable negative photograph:
retain the current native baseline, all candidate/uniform masters and every
reported regression. The final-color follow-up remains source preparation,
unbuilt and unrun in this review; it has no photographic result. No additional
algorithm, build, reconstruction, tuning or transfer was dispatched. Review is
finished and work pauses at the user's request, without marking the quality goal
complete.
