# Independent corrected-address photographic review

September 19. **VERIFIED visually: positive local headroom, with incomplete
cleanup.** Moving only the dark capsule endpoint onto the actual long tail
substantially removes that tail while retaining the compact bright contact and
black inclusion. The remaining right-hand branch is conspicuous, and Helicon B
is still more compact overall. This is a useful manual-oracle result, not a
complete two-branch correction, automatic acceptance, or SOTA claim. The earlier
recipes' failed joint judgments remain unchanged.

I inspected all three complete overviews, all five native six-arm boards, all
three centred 3x-nearest boards, and their separate old/new mask outlines in
`corrected-full-1/photo-comparison-1` and `corrected-review-1`. I additionally
viewed the old and corrected dark crops individually. The dark/facet judgments
were formed before reading the root's matching visual verdict. No donor,
support, threshold, image-development setting, or viewing window was changed
for this review.

| Frozen witness | Photographic finding |
| --- | --- |
| Dark long left/downward column, including (3080,2212) | The old spatial candidate retains a long cyan column ending in magenta. The corrected candidate replaces most of that column with the surrounding blue-grey background and a short bright contact. This is a substantial visible improvement, not just removal of the core. |
| Dark compact core and separate right branch | The upper black inclusion and small bright contacts remain resolved. The right branch, including the previously favoured (3102,2203) neighbourhood, remains bright and extended. Its thin lower fringe appears slightly more present than in the old candidate; reduced old coverage must not be described as improving both branches. There is no gross new bloom comparable to the late control. |
| Facet core/fan | Unchanged from the spatial candidate: prominent left/down rays are shorter than baseline while the upper core and lower bright contact survive. Diffuse cyan/grey residue remains; Helicon B is cleaner around this feature. |
| Nearby source-25 structure | The ridge/junction remains intact. The endpoint correction leaves this intervention exactly unchanged. Late69 softens the structure, demonstrating that donor identity matters. |
| Transitions and background | No obvious hard capsule edge or pasted rectangular boundary appears at the inspected 3x scale. The small dark-region background left after tail removal is visually plausible; that is not a noise measurement. The three remote control windows remain unchanged. |
| Late69 control | Both spatial late arms visibly enlarge/blur the glint. Corrected support does not by itself guarantee suppression: the late source still produces a strong broad cyan/white plume. |

**MEASURED support, not quality:** the frozen helper was executed as
`python experiments/donor-consistency/corrected-photo-review.py` by the root.
Its `corrected-review-1/change-extent.json` records 4,271 changed RGB16 pixels
versus the original spatial candidate, inclusive bounds
[3054,2141,3127,2235], all inside the predeclared [3052,2122,80,120] rectangle.
Every pixel outside that rectangle is exact, including the other two donor
interventions and the other four canonical windows. The baseline is pixel
exact. The late arm changes 4,283 pixels, also wholly inside the rectangle.
The counts establish a small intervention, not an all-image gain. Only 4,258
of the candidate changes lie inside the canonical dark window; the centred
view and full-image extent check also cover the remainder.

The view helper is bound by SHA256
`80830a3167a70afeaa710a348673ee70628d82daf2ab234058217b9cb5a2268f`;
the corrected candidate TIFF is
`a41c456285253b1031e14fdd6b5313a89d85062d8ff8cfebcfa07613ada25b32`.
The receipt preserves all input/output hashes. Helicon uses the held independent
registration, native unresampled samples and the same embedded sRGB profile;
its approximately 1.0107 scale and residual registration error remain, so the
boards support qualitative morphology comparison, not pixelwise truth.

The result establishes that source33 plus this reconstruction has useful
headroom when its support actually covers the visible defect. It does not
establish automatic ownership, correct support discovery, or unchanged noise
inside the donor region. Single-source texture/noise is a possible cost;
unchanged remote flat windows cannot measure it. No gradient score or calibrated
noise claim is used. The corrected endpoint was selected after failure, and
the failed automatic locator remains failed. Keep this exact result as a
bounded positive photographic witness; do not turn it into another support
sweep or advertise the residual right branch as solved.
