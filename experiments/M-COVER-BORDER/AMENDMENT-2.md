# Amendment 2 — preserve the registered 8 px candidate

The first Amendment-1 execution exited before scoring Crop because the
implementation made every annulus, including the first, as wide as the
candidate calibration width. At widths above 8 there was therefore no row
whose lower edge was 8, making the required `safe_inset_px == 8` impossible by
construction.

This is an implementation error, not a failed Scale control. Before another
profile run, freeze the intended edges:

- outer row `[0, 8)`;
- rows starting at 8 with the candidate width;
- one aggregate row for `distance >= 768`.

Thus every candidate width can return the registered 8 px floor. No threshold,
candidate width, image, hash, or pass predicate changes. The failed invocation
produced no v2 profile JSON and no Crop statistic.
