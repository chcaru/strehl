# Amendment 1 — specificity-calibrated annulus width

The first real-profile run made the preregistered 8 px tail statistic
**inadmissible**. Its Scale control returned no safe inset even though:

- Scale's peak through 256 px was only `0.0007224`;
- the failures were narrow alternating-sign scene bins, including
  `+0.001343/-0.001506` at 752/760 px and
  `-0.003515/+0.004171` at 1144/1152 px;
- the latter bins approach the rectangle's maximum border distance and have
  rapidly collapsing sample support.

This is the same kind of specificity failure that disqualified the ruler
profile in COVER. The v1 Crop reaches (`None`) are not interpreted.

Before rerunning, the following repair is frozen:

1. Aggregate the normalization region `distance >= 768` into one deep row,
   rather than subdividing the very region whose joint mean defines the
   normalization.
2. On the **Scale b7/b2 specificity control only**, test dyadic annulus widths
   in the fixed order `8, 16, 32, 64, 128` px.
3. Select the first width for which every Scale annulus, including the outer
   one, is within `|effect| <= 0.001` and the safe inset is the 8 px floor.
4. Lock that width and apply it unchanged to Crop b2/b4/b7.
5. If no width clears Scale, the real reach statistic remains unscorable.

The H2 slope, R², monotonicity, endpoint-ratio, threshold, deep start, files,
and hashes do not change.

This amendment is necessarily after a failed v1 run and the files have already
been opened. The repaired result is therefore an audited replication, not a
blind discovery. The v1 JSON is retained as `profile-v1-invalid.json`.
