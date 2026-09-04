# Amendment 1 — distinguish the coverage-mode and coverage-fit banners

The Scale control passed exactly:

`3d46f11413e5cf37bdeb730eb6faf66c266ac52107e1b5af1e032052080d16bc`

The first Crop render, `m1-bright-a12`, also completed and wrote its TIFF and
log. The harness then failed while parsing, because it selected the earlier
`coverage mode : crop -- as asked, --cover` banner instead of the later
`coverage : CROPPED ... (k=...)` fit banner.

This is a post-render parser defect, not a binary, input, solve, cache, output,
threshold, estimator, or gate failure. No result was interpreted.

Before the remaining seven renders:

1. Select only a banner whose label is exactly `coverage`, excluding
   `coverage mode`.
2. Do not overwrite or rerender the completed control or first Crop output.
3. Recover the first Crop record from its exact command line, committed log,
   TIFF, and the private-cache equality before the control and after the failed
   parser. Use the binary's `total` banner as its diagnostic wall value because
   the outer Python timer was lost when post-processing raised.
4. Permit later resumptions to reuse only already-manifested successful
   records; every new output still refuses implicit overwrite.

No scientific decision, command, environment, arm, or acceptance threshold
changes.

