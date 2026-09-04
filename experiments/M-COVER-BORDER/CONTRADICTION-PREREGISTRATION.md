# M-COVER-BORDER contradiction — preregistration

Frozen: 2026-09-03, before new Scale renders, new 113 renders, or scoring the
matched rerenders.

## Prior knowledge and correction

This is not blinded. I have read:

- `docs/research/cover-default.md`, including its linear-plane 109 result
  Scale 8 px / Crop 256 px and its nonspecific ruler result;
- the deleted V-HEADTOHEAD3 sRGB, corrected-linear and sensitivity records from
  `d1ad7458^`;
- the previously generated M-COVER-BORDER outputs.

During preparation I found a material error in `M-COVER-BORDER.md`: the fresh
two-worker Crop b2/b7 rerenders do **not** equal the old cover-default files.

```text
fresh b2: 10F7DEAF5A82CA2A311C76A323AE5627207520E7DA3BB71D237BB861CC7CC977
old b2:   02C1470ED0750248EFB5D321F05205CF1F1BD502931D2E50C0B65C46FFC2EC34
fresh b7: 0465D253F14431CE76BA1DD68E54C1BD2CBAE56DA17F079D5DD572852FCAD304
old b7:   B2489C692AA924AEF230B21388407B902845219851C54FCA892E2DB362A0A83D
```

The old `profile-final.json` combined the fresh two-worker b4 with the old
b2/b7 files. Its b2/b4/b7 causal ladder is withdrawn until a matched-worker
rerun. Its source audit, exact coverage audit, synthetic commission, and
original matched b7/b2 Scale-versus-Crop mass comparison are not changed by
that discovery.

## Questions

1. What does each disputed number measure after explicit unit conversion?
2. Under one camera-linear definition, what nominal safe inset does each mode
   return on matched renders?
3. Is a non-8 Scale value conserved Crop error smeared below threshold, a
   genuine Scale boundary field, or a nonspecific scene statistic?
4. Does the historical 8/256 result survive as a 109-specific measurement, and
   does its direction survive a second already-burned source?

## Frozen executable, sources and render arms

One executable will produce every newly scored file:

```text
D:\strehl-out\cover-default\target\release\strehl.exe
sha256 1AC423529D5AAD88B7141801E47DCD612FCA8061558578A88592DB715CE81A0F
```

Sources:

- `D:\personal\macro\109MSDCF` — already burned by cover-default.
- `D:\personal\macro\113MSDCF` — already burned by V-HEADTOHEAD3.

`D:\personal\macro` remains strictly read-only.

For each source, render camera-linear binned RGB16:

```text
Scale b2, Scale b7, Crop b2, Crop b7
```

The existing fresh 109 Crop b2/b7 files may be used because their commands and
two-worker logs are already frozen. Fresh 109 Scale b2/b7 and all four 113
arms will use the identical environment below. The 109 Crop b4 will be scored
only as a repair of the withdrawn causal ladder.

All inherited `STREHL_*` variables are removed, then:

```text
STREHL_FULLRES_GATHER=1
STREHL_DEFECT=off
STREHL_FIX_CA=off
STREHL_PYRAMID_WORKERS=2
RAYON_NUM_THREADS=6
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
```

109 uses the existing explicit sidecar
`experiments\M-PHASE0-SPLIT\out\real-109\109-warpmap.txt`, SHA-256
`C29CAB9C6F944F4D03C4402998E54AAD4D4221CC450AC4BEF42A453DE848434D`.
113 uses a new private cache under
`D:\strehl-out\M-COVER-BORDER\common-113-cache`; its generated map and source
manifest will be hashed. The cache must be unchanged between its four arms.

Command shape:

```text
strehl.exe stack <source>
  --merge pyramid --pyramid-bands <2|7>
  --resampler catmull-rom --cover <scale|crop> --out <scratch TIFF>
```

No `--srgb`, auto exposure, exposure, or output-scale option is permitted.
All outputs and caches are outside the capture tree.

## Common primary quantity

The primary unit is one default-linear **plane pixel**. These outputs are
binned from one 2x2 sensor quad, so:

```text
1 plane pixel = 2 full-resolution sRGB-output pixels per axis
              = 2 sensor photosites per axis
```

For green and mode `m`, compare b7 with b2 on the identical emitted grid.
For annulus `[lo, hi)` measured from the emitted image boundary:

```text
E_m(lo,hi) =
  (mean G_m,b7(lo,hi) / mean G_m,b2(lo,hi)) / R_m,deep - 1

R_m,deep =
  mean G_m,b7(distance >= 768) / mean G_m,b2(distance >= 768)
```

Threshold: `abs(E) <= 0.001` (0.1%).

Fixed plane-pixel edges, exactly matching cover-default and the deleted
corrected-linear instrument:

```text
0, 2, 4, 8, 16, 32, 64, 96, 128, 160, 192,
256, 320, 384, 448, 512, 640, 768, maximum
```

The **nominal safe inset** is the smallest registered `lo >= 8` for which that
annulus and every deeper annulus through the deep region pass 0.1%. It is a
tail statistic, not automatically a causal boundary reach.

The original protocol's **specificity condition** is reported separately:
Scale nominal safe inset equals 8 px. A source that fails it still receives
both nominal numbers, but neither is relabelled as a black-fill requirement.
This records rather than assumes the original reasoning.

## Explicit conversions of the disputed historical values

These conversions are fixed before scoring:

| Record | Native statistic unit | Native values | Linear plane equivalent |
| --- | --- | --- | --- |
| cover-default 109 | linear plane px | Scale 8, Crop 256 | 8, 256 |
| deleted sRGB result | full-resolution sRGB output px | Scale 768, Crop 768 | 384, 384 |
| deleted corrected linear result | linear plane px | Scale 640, Crop 320 | 640, 320 |
| sensitivity required clearance | full-resolution site/output px | Scale 1280, Crop 640 | 640, 320 |

The sensitivity file's `minimum_retained_clearance_px` values are measured
locations of surviving paired patches after those gates. They are not required
safe insets and will not be compared as such.

## Preregistered discriminators

### P1 — exact historical-definition rerun

Report both nominal values on 109 and 113 without changing edges, deep start,
threshold, or units.

- The historical 109 result is reproduced exactly if Scale=8 and Crop=256.
- A one-bin difference caused by serialization/order is reported as such, not
  silently rounded to the old value.
- If Scale is not 8, the original instrument is nonspecific on that source.

### P2 — matched-worker repair of the causal ladder

On matched two-worker 109 Crop b2/b4/b7, use the same fixed-edge statistic.
The dyadic mechanism predicate passes only if:

- reaches are monotone with band count;
- log2(reach) versus band count has slope in `[0.75, 1.25]`;
- `R² >= 0.90`;
- b7/b2 endpoint reach ratio is at least 16.

Failure withdraws the real causal ladder from the mechanism report. It does not
alter the source-ordering audit.

### P3 — conserved-error Scale test

Using one-pixel distance rings before annular aggregation, deep-normalize each
mode and integrate positive residual level:

```text
sum(max(mean_b7(d)/Rdeep - mean_b2(d), 0) * samples(d))
---------------------------------------------------------
sum(mean_b2(d) * samples(d))
```

Compute it through 256 plane px and over the full plane.

- Scale/Crop `< 0.20` in both scopes rejects “Scale merely smears the same
  positive contamination.”
- ratio `>= 0.50` in either scope, together with a lower Scale peak, supports
  conserved-error concealment.
- intermediate or discordant ratios are unresolved.

### P4 — boundary-shape descriptor

For each fixed annulus, report sign and effect. Count sign changes outside the
outer 8 px and report the fraction of positive residual mass lying within 256
px. These are descriptors, not pass/fail gates. A long nominal safe inset with
alternating signs and little boundary-concentrated mass is not by itself proof
of a physical boundary field.

### P5 — interpretation across sources

- If 109 reproduces 8/256 but 113 fails Scale specificity, 8/256 survives only
  as a 109-specific statistic; the apparent directional contradiction is a
  source/specificity interaction, not evidence that Crop generally needs half
  Scale's inset.
- If both sources are specific and Crop exceeds Scale, the direction survives.
- If both are specific and direction reverses, the shipping default's border
  premise is refuted.
- If 109 itself does not reproduce, the cover-default blocker is refuted on
  its own source and binary.

## Commissioning

Before real scoring, the instrument must:

1. return safe=8 and zero mass on an untouched null;
2. recover a `+2%` outer 64 px defect and safe=64;
3. reduce a `+0.05%` improvement to safe=8 and at most 5% of defect mass;
4. restore the original defect result exactly;
5. go RED for swapped b7/b2, an altered 0.1% threshold, an altered edge, and
   omitted deep normalization;
6. verify `768/2=384`, `1280/2=640`, and `640/2=320`;
7. fail on shape, dtype, binary hash, sidecar/cache change, or nonzero render
   exit.

The commission result is written before the real profile result.
