# V-HEADTOHEAD3 cover-mode preregistration

Frozen 2026-09-03 before creating or opening a `--cover crop` render of
`113MSDCF`.  This is a second, separate arm.  It does not alter or rehabilitate
the sharpening follow-up, whose registered causal verdict remains
`INDETERMINATE`.

## Question, prior evidence, and bias

Does the shipping default `--cover scale` measurably suppress rendered ordinal
structure at 0.10--0.20 cyc/px relative to the same pinned stack rendered with
`--cover crop`, enough to explain the previously observed strehl/PMax trail?

My investigator-favoured direction is **crop improves 0.10--0.20**.  That
would identify a recoverable product loss and an already implemented remedy.
The prior corpus points the other way and is recorded before measurement:
`docs/research/BUILD-CROP.md` says the older cover hypothesis was 270x too
small and reports removing the enlargement at `-0.0030 dex`, the wrong sign,
on 8/9 other stacks.  Those runs did not include this 113 competitive pairing
or this capped ordinal statistic.  The new outcome must therefore be judged
against the bars below, not either narrative.

The direct answer about the old scale factor is frozen now: `s` was
**measured from the image pixels**, not inferred from nominal dimensions.
`ordinal.fit_geometry` replaces sampled green planes by global mid-ranks,
sweeps comparator scale to an interior correlation maximum, and refines it.
The previous author estimates were 1.002 for PMax0 and 1.003 for PMax40.
This arm remeasures every scale from the new images and never substitutes
dimension ratios or the renderer's printed `k`.

## Frozen inputs and only intervention

| role | path | SHA-256 |
| --- | --- | --- |
| pinned executable | `C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe` | `2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7` |
| shipping scale master | `C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff` | `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F` |
| primary unchanged comparator | `D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif` | `B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0` |
| confounded secondary comparator | `D:\edited\macro\test\2026-05-07-21.31.06 ZS PMax.tif` | `4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E` |

The source is the 63 ARWs in `D:\personal\macro\113MSDCF`, read only.  The
historical command is:

```text
strehl.exe stack D:\personal\macro\113MSDCF -o <output> --srgb
```

All inherited `STREHL_*` variables are removed; only a private
`STREHL_CACHE_DIR` below this experiment's `out` directory is set.
`RAYON_NUM_THREADS=8` and numerical-library thread caps of 8 are disclosed
operational constraints.  Before the treatment, the historical command with
no `--cover` flag must reproduce the frozen scale master byte-for-byte.  If it
does not, stop without rendering crop.

The treatment command differs by exactly `--cover crop`.  Both commands use
the same executable, source bytes, private cache, environment, backend,
colour path, and output encoding.  Both PMax files remain untouched.

## Input-fixed physical sites

Sites are frozen before the crop render, separately for PMax0 and PMax40:

1. Fit scale-master-to-PMax geometry from sampled green mid-ranks.
2. Use a 512-pixel PMax-native grid at least 512 px from each PMax edge.
3. At each PMax centre, map the corresponding scale-master centre with the
   fitted image scale and translation, then refine translation by rank phase
   correlation.  The PMax crop centre remains fixed; the strehl centre moves.
4. Reject bounds, more than 1% rail samples, non-interior geometry, local
   correlation at or below its fixed toroidal-shift null, or a registration
   improvement below 0.02.
5. Texture uses only PMax `Q` energy from 0.02--0.20.  Within every spatial
   quadrant, freeze the bottom quartile as flat and top half as detail.

The frozen record contains PMax-native centres and labels.  Crop pixels may
not select, replace, or relabel a site.  Sites lost to the smaller crop or a
256-pixel crop-border clearance are coverage losses, not invitations to
backfill.  Each pairing needs at least 12 detail and 6 flat sites after these
losses.

For each frozen PMax centre, crop and scale are mapped independently by their
own image-measured geometry and local correction.  The exact same native PMax
crop is the denominator in both arms.  Measurement pixels are never
resampled; interpolation is permitted only for geometry and registration
diagnostics.

## Strictly capped ordinal statistic

The four PMax-native physical bands are:

```text
[0.02,0.05), [0.05,0.10), [0.10,0.20), [0.20,0.25)
```

For each native crop, replace samples by centred average ranks `q`, apply a
separable Hann window `w`, and define independently for band `b`:

```text
Q_b = sum(|FFT(w*q)|^2 in b)
      / (N * sum(w^2) * mean(q^2)).
```

No other observed band enters the denominator.  PMax uses the edges above.
If one PMax pixel spans `s` pixels in a strehl arm, that arm uses edges
divided by `s`, so all arms describe the same physical scene frequencies.
Any arm whose mapped upper edge exceeds 0.25 native cyc/px has its final band
replaced by `UNLICENSED_GT_0.25`; it is never truncated silently.

Per frozen site and band:

```text
d_scale = log(Q_scale / Q_PMax)
d_crop  = log(Q_crop  / Q_PMax)
g       = d_crop - d_scale = log(Q_crop / Q_scale).
```

Report geometric means and 95% paired site-bootstrap intervals from 10,000
PCG64 draws, author seed `20260903`.  Detail and flat strata are separate.
The primary quantity is detail `G=exp(mean(g))` at 0.10--0.20 against PMax0.
PMax40 is secondary because its inputs differ in eleven development fields.

## Frozen interpretation

The existing 5% competitive classes remain:

* `TRAILS` if a ratio's UCB95 is below `1/1.05`;
* `LEADS` if its LCB95 is above `1.05`;
* otherwise `UNRESOLVED`.

At primary 0.10--0.20:

* `RECOVERED_BY_CROP` requires scale/PMax0 `TRAILS`,
  crop/PMax0 not `TRAILS`, cover-effect `G` LCB95 above 1.02, every
  spatial-quadrant point effect above 1, and no leave-one-site reversal.
* `PARTIAL_RECOVERY` requires scale/PMax0 `TRAILS`, crop/PMax0 still
  `TRAILS`, and `G` LCB95 above 1.02 with the same spatial guards.
* `COVER_NOT_CAUSE` requires the complete `G` interval inside
  `[0.98,1.02]`.  It eliminates this cover-mode mechanism; it does not turn
  the confounded PMax comparison into physical merge truth.
* `CROP_DEGRADES` requires `G` UCB95 below 0.98.
* every other result is `UNRESOLVED`.

A flat effect is reported, not subtracted.  If it matches the detail effect,
the result is a general spatial-transfer change and may not be called
scene-detail truth.  No ordinal result is MTF, physical resolution, M1, M4,
or M8.

## Geometry, provenance, and coverage gates

Every scale fit must have an interior maximum.  Author and independent
checker scales must agree within 0.5%; the primary result is `NOT ROBUST` on
failure.  Dimension ratios and the renderer's `k` are corroborative only.
The scale-control TIFF must match the frozen master hash exactly.  Pre/post
source manifests and comparator hashes must match.  The crop log must report
63 placed, 0 refused and a crop-at-unity-scale banner.

Report scale/crop dimensions, crop origin and `k`, retained width, height and
pixel fractions, 300-dpi print dimensions, frozen-site losses, and minimum
scored-site border clearance.  No spectral inference is made within 256 crop
pixels of the emitted boundary because prior BUILD-CROP work found
black-fill/pyramid ringing extending inward by roughly 128 px.

## Commissioning before treatment

Before rendering crop, the author and an independent implementation must:

1. admit fixed bins in all four bands and reject 0.28125;
2. show exact affine, gamma-3 and logistic invariance;
3. show identity parity, a blur degradation, and an independent USM
   improvement in 0.10--0.20;
4. recover known scale and translation with the correction sign, while
   dimension-assumed scale, wrong sign and no-op mutants go RED;
5. recover an exact centred crop mapping, while all four one-pixel origin
   mutants go RED;
6. reject a changed executable/comparator hash, extra render flag, inherited
   `STREHL_*`, post-treatment site reselection, omitted border clearance, and
   numeric above-cap output;
7. reach every frozen verdict branch with literal fixtures.

Every plant must go RED and every null GREEN.  The independent checker may
read the preregistration and frozen sites, but may import neither author
outcome code nor author results.

## Stop conditions

Stop competitive inference, without changing a threshold, if the historical
scale render is not byte-identical, source/comparator bytes change, crop does
not place all 63 frames, either geometry lacks an interior optimum, fewer
than 12 detail or 6 flat sites survive, author/checker geometry differs by
more than 0.5%, or an instrument fails commissioning.  Report the failure
instead of selecting new sites or another kernel.
