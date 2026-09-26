# Independent photographic review of the final band guide

2026-09-26. **ARGUED decision: reject this frozen recipe for adoption.** The
complete 70-source vitamin-C observation fails its photographic preservation
condition. Background smoothness improves visibly, but the dark boundary beside
a strong glint is replaced by a broad pale magenta-white patch, and another
glint gains colored spread. Keep the complete outputs as a failed diagnostic;
do not promote the model, change a threshold, substitute a checkpoint, or run a
fourth fit in this development program.

**VERIFIED by native visual inspection:** I inspected all 24 individual PNGs
in `views-1`, baseline/candidate/retained Helicon B at each of the eight frozen
sites, using `view_image` without enlargement or resampling. I began with
`pale-background`; the other images were 384, 160 or 120 pixels square. Both
whole-image JPEGs were viewed for orientation only. No JPEG metric, sharpness
score, new crop selection, RAW decode or merge was performed for this review.

| Frozen native output region, xywh | Observation |
| --- | --- |
| Pale background, 400,1150,384,384 | Candidate substantially reduces visible fine grain and makes the broad dark lobe smoother. Some faint specks also weaken. This is a visible aesthetic benefit, not a calibrated noise reduction claim: this region contains defocused structure and has no flat truth. |
| Bright facet, 1150,3850,384,384 | Candidate similarly smooths the surrounding field. The main dark facet and obvious small inclusions remain visible. This supports smoothness, not newly recovered detail. |
| Fine crystals, 4200,1700,384,384 | Main fine edges and glints remain recognizable; the candidate is subtly smoother. I cannot identify a convincing new detail recovery or quantify fine-detail preservation from these photographs. No wholesale collapse is visible here. |
| Competing structure, 3180,2010,120,120 | Candidate retains the main intersecting shapes but looks softer. This small view provides no clear occlusion repair win. |
| Dark inclusion, 3050,1850,384,384; dark core boundary, 3011,2097,160,160 | Decisive failure: the black strip near the upper-left of the 160-pixel boundary view, approximately local x=30..80/y=25..50, is largely replaced by luminous pink-white spread. It remains dark in both baseline and the retained Helicon rendering. The larger inclusion view shows the same change; these are overlapping views of one failure, not two independent examples. |
| Facet edges, 2500,2700,384,384; facet core boundary, 2533,2846,160,160 | Candidate broadens the smooth colored flare toward the left background around the bright core. Several radiating streaks persist. Helicon has a more confined bright group here. The small boundary view and its larger parent again show one site. No persuasive glare cleanup is visible. |

The dark-boundary change is too large to explain by the retained Helicon crop's
small scale/position mismatch, and it occurs between baseline and candidate in
the exact same coordinate gauge. Helicon is corroborating context, not truth.
No source-frame inspection here proves the physical identity of the black strip;
the direct conclusion is that the candidate replaces an independently retained
boundary and enlarges colored spread. Smoothing can erase faint real structure
as easily as grain; shorter or smoother rays alone cannot establish quality.

The comparison uses the complete 6920x4612 masters and the same pinned baseline
development for the candidate. **MEASURED by root:** the bound full command in
`full-1/invocation.json` was `build-4/cli-tests.exe
merge_cmd::cross_scale_band_full::complete_pair --exact --ignored --nocapture
--test-threads=1`, with the recorded environment/config; all 70 sources were
scored and the complete run took 157.75 s. The exact model is
`02f5d9fbfa16efa18207b82884a83f232cd8ab2355995dba04c11a91dd1fa02a`.
Mechanical canonical replay and mean/hull identity remain valid; they do not
establish photographic improvement.

Provenance: `views-1/coordinate-receipt.json` binds the frozen regions, matched
tone, native images and retained Helicon registration. Baseline TIFF SHA256 is
`50da15bf7d86839ac04f642623bdd5e9033a9342026767dfdd0f04dd27d05434`;
candidate is
`331eb89a86e8bcf77c0f81f64cbacec07e2ef7871ae15365541292bfbc7aa879`;
full merge receipt is
`9a6fb091fdf55310d6b4ec5ac0b3a8b5222ef1d2c3b731f0175bd1312cc47a0d`.
The explicitly reviewed four-sample historical baseline transition remains in
`baseline-reference-review.md`; no historical RGB16 identity is claimed.

The old scientific failures remain unchanged, including curved chroma, glint
adjacency and the finest carrier. The ten generated challenge cases are now
reused regression cases, not fresh independent validation. This photograph
reinforces the rejection of this particular trained recipe; it proves neither
a ceiling for learned band weights nor anything about 488-source marigold or
mineral-wide quality. The bounded photographic question has been answered;
stop this lane under its declared three-fit contract.
