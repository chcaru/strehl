# V-HEADTOHEAD3 — cover-border output-space correction

**Frozen after the first profile failed specificity, before rendering or opening
any camera-linear profile arm.**

## What failed

The preregistered instrument itself commissioned GREEN: 9/9 fixed controls and
4/4 planted mutants.  The real `--srgb` result nevertheless failed its mandatory
specificity predicate:

* Scale, which has no black-fill crop boundary, returned a nominal 768-pixel
  safe inset rather than 8 pixels.
* Crop also returned 768 pixels.
* Therefore neither number is admitted as a black-fill reach, and the 256-pixel
  V-HEADTOHEAD3 ROI gate was not validated.

This is not an estimator defect.  The preregistration selected the wrong output
space.  The pinned binary's own help says its default output is binned,
camera-linear native RGB and is the file intended for measurement; it says of
`--srgb`, verbatim, **"For looking at, NOT for measuring."**  The sRGB render
also expands to full sensor resolution.  The independently commissioned
COVER-default profile whose method this amendment adopted used default linear
outputs, not `--srgb`.

The first result and provenance remain an audit record.  Its disposition is
`WITHDRAWN_OUTPUT_SPACE_SPECIFICITY_FAILURE`; it supplies no safe inset.

## Corrected frozen arm

Render a complete matched four-cell design from the same pinned executable,
same 63-frame `113MSDCF` source, same cached warp map, same default pyramid
merge, and the same cover choices:

```text
strehl.exe stack D:\personal\macro\113MSDCF
  -o <scale-linear-b7> --pyramid-bands 7
strehl.exe stack D:\personal\macro\113MSDCF
  -o <scale-linear-b2> --pyramid-bands 2
strehl.exe stack D:\personal\macro\113MSDCF
  -o <crop-linear-b7> --pyramid-bands 7 --cover crop
strehl.exe stack D:\personal\macro\113MSDCF
  -o <crop-linear-b2> --pyramid-bands 2 --cover crop
```

No `--srgb`, `--auto-exposure`, `--exposure`, or output-scale option is
permitted.  Environment clearing, eight-thread caps, source/executable/map
hashes, 63/0 placement, `k=0.9809`, exact crop rectangle, and unity-scale Crop
requirements remain unchanged.  The two band depths within each cover mode
must have identical dimensions.  The Scale dimensions must be `3516x2344`;
Crop must be `3448x2298`.

The original annuli, deep start, 0.1% threshold, commissioning predicates,
bias, and fail-closed disposition are unchanged.  Scale must return 8 pixels
before any Crop reach is admitted.  If it does not, this lane reports the exact
stack as nonspecific rather than adding a new threshold or subtracting an
unregistered scene trend.

This correction affects only the border instrument.  It does not replace or
recompute the already frozen sRGB ordinal cover comparison, whose statistic is
monotone-point-tone invariant but is not a resolution metric.
