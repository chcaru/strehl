# Three original-frame checks: source loss is not yet established

**VERIFIED — diagnostic observation, no improvement claim.** The alignment
anchor 149 and bracket endpoints 0 and 298 were chosen without ranking image
sharpness. Each was read through RawPy and independently through the retained
`m61-decode-check.exe`. Original hashes and mtimes were unchanged. No additional
original was decoded by this lane.

The persisted `source-{0,149,298}/active-cfa-u16.npy` arrays contain the complete
RawPy visible area, copied inside its open context. Each 7028 × 4688 array agrees
exactly with the corresponding rawler rectangle. This does **not** verify the
extra four columns that rawler exposes: rawler reports 7032 × 4688. RawPy also
reports white 16383; rawler and the actual baseline use 15360. The source-patch
development uses baseline/rawler levels 512/15360. WB is 1637:1024:2774 in all
three originals.

`source-*/native-fixed-display/receipt.json` records each crop's gauge, source
rectangle and display. Both source and baseline linear patches use fixed gain
3.434, the sRGB transfer, and the same ICC. No local fitting or sharpening is
used. Source patches use the repository MHC port, as-shot WB and baseline camera
matrix. They retain native samples: the source crop center is mapped through the
actual saved reference-to-frame similarity and rounded to even coordinates;
scale/rotation is not resampled. The anchor is identity. Endpoint framing differs
slightly as recorded, and source patches lack the baseline CA gather. This is a
structure witness, not byte-identical native pipeline development.

At `upper-leg-hairs`, anchor149 resolves part of the left/central appendage,
while the right side is less focused. The completed stack preserves the main
protruding hairs and resolves more of the right surface. The three scale/line
sites in anchor149 are strongly defocused, showing broad specular disks. Both
endpoints are strongly defocused at the inspected hair, thorax and turquoise
sites. The selected three sources therefore do not establish an erased detail
or a focused-source ceiling. They also do not establish a capture limit: the
remaining 296 frames were not inspected here.

The source149 raw-green planes retain the visible hair shape, but attribution
of its colored edge to CA gathering, repeated MHC, merging or the source optics
is **UNVERIFIED**. Root is preparing an observation through the actual baseline
gather kernel. This lane will not substitute a hand-ported whole pipeline for
that observation.

The frozen original coordinates and baseline-only review remain unchanged.
Their `raw_decodes: 0` field records that earlier phase; the follow-on phase here
read three distinct originals. The original source149 scripts are preserved
inside `source-149/` alongside their hash-bound execution receipts.

Commands executed successfully from the worktree:

```powershell
python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/source-witness.py 149
python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/develop-source.py
python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/source-witness.py 0
python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/develop-source.py 0
python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/source-witness.py 298
python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/develop-source.py 298
```

All six commands exited 0. The latter developer prints the legacy phrase
`identity-anchor`; endpoint receipts correctly record the actual nonidentity
placements and center-mapped native crop rectangles. That printed label is not
evidence of identity.

## Next locator, before any claim

`locate-sources.py` is prepared for the forthcoming complete 299-file native
source-development set. It must receive an explicit ordered TIFF manifest and
declared encoding. It has not been executed against photographs yet.

It will inspect dark-background control statistics first, then measure two
spatial scales in the frozen hair/scale regions, one source TIFF at a time.
The saved runtime map locates source crop centers; no new geometry is fitted.
Smoothing acts only on the resulting scalar score sequence, not on images or
an aligned frame volume. A broad connected interval supplies a contact sheet
and center-plus-neighbor native patches. Scores locate a focus neighborhood;
they never become a merge reference, selected-pixel oracle, value-admission
rule, detail proof or quality score. Multiple scales can disagree, and noise,
halos or glints can raise these scores. Generated noisy-flat and blur controls
make that limitation explicit before photographic statistics are used.

The next photographic decision still requires native inspection of real feature
separation and continuity across the located neighborhood, followed by the actual
gather and complete-stack comparison. A contact-sheet thumbnail is orientation
only. The existing complete output and full-resolution master are linked in
[the baseline review](baseline-review.md).
