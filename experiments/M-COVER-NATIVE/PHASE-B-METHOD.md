# M-COVER-NATIVE Phase B — Q3/Q4 method and falsifier

## Scope

Phase B answers Q3 and Q4 from the eight existing Phase A Crop TIFFs and the
committed `out/RENDER-MANIFEST.json`. It does not rerender, re-estimate
alignment, or revisit the disqualified non-translation residual reader.

The actual TIFF dimensions were already observed and reported in Phase A.
Therefore Q3 is a deterministic header census and manifest cross-check, not a
blinded discovery measurement. Percentages are arithmetic derived from fixed
integer dimensions; they are not new experimental evidence.

## Fixed dimensions and predicates

- Native output: width `7032`, height `4688`.
- Synthetic scale-model native dimensions: width `12`, height `8`.
- Matching synthetic null: width `12`, height `8`.
- Known-smaller synthetic failure input: width `10`, height `6`.
- Width pixels lost: `7032 - observed_width`.
- Height pixels lost: `4688 - observed_height`.
- Native-size GREEN: both integer losses are zero.
- Native-size RED: either integer loss is positive.
- Invalid geometry: either observed dimension exceeds its native dimension.
- Retained area: `observed_width * observed_height`.
- Area loss: `7032 * 4688 - retained_area`.
- Common-overlap geometric retention: intersection area between the verified
  full-resolution Crop rectangle and frozen
  `(y=40, x=58, h=4608, w=6912)`, divided by the frozen common area.

The production census must also require every TIFF header dimension and SHA-256
to equal its committed render-manifest record, and every TIFF dimension to equal
twice the banner Crop rectangle in each axis. Exactly the eight frozen arm names
are admitted, including worst arm `m2-second-first16`.

## Commission before actual census

`geometry_census.py --commission` creates two tiny synthetic TIFF arrays under
ignored `work/geometry-census-commission/`, reads their TIFF headers through the
same parser used for the real files, and applies the same full-size-relative
integer predicates with the fixed synthetic native dimensions `12 x 8`. It
requires:

1. the matching `12 x 8` header to stay GREEN with zero lost pixels;
2. the planted `10 x 6` header to go RED with losses of exactly two pixels
   on each axis.

Temporary commissioning files are removed before the command returns; if an
interrupted process leaves them behind, they remain only under ignored `work/`.

Only after both controls pass may the script read the eight actual TIFF
headers and write `out/GEOMETRY-CENSUS.json`.

## Q4 evidence boundary

Q4 reads the current `CoverMode` documentation in
`crates/strehl-cli/src/align_cmd.rs` and the current `sample_lanczos3`
documentation in `crates/strehl-core/src/align.rs` without editing Rust.
`BUILD-CROP.md`, `cover-default.md`, `M112-real-pixels.md`, and
`M104-resample-verify.md` are prior evidence only. Live `M-COVER-BORDER` owns
the border mechanism and remains untouched.
