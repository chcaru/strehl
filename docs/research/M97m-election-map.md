# M97m — the election map, exported

**Status: SHIPPED.** An optional debug export of the merge's per-pixel elected
frame index, requested by the orchestrator as an instrument for the "waxy
blobs" complaint. Six pre-registered bars, all passing, both nulls planted.

Owner: M97. Files touched: `crates/strehl-cli/src/merge_cmd.rs`,
`crates/strehl-cli/src/main.rs`. **No change to `merge.rs`, and none to any
merge arithmetic.**

---

## 1. What it is

`strehl stack --index-map <PATH>` — or `STREHL_DUMP_ELECTION=<PATH>` for a
harness that cannot edit the command line — writes the pass-one winner field as
a single-channel 16-bit TIFF.

- **Grid: the PLANE grid, half sensor resolution.** One election per 2x2 CFA
  quad, because that is where the focus field the election is computed on
  lives. Measured at **3516 x 2344** on an A7C II bracket. Same size as a binned
  render, half a `--srgb`/`--demosaic` one: scale by two to overlay the latter.
- **Values: the literal 0-based frame index in input order.** `raw_paths` sorts
  by filename, so that is capture order, and `--limit N` keeps `0..N-1`.
  Measured `0..11` at `--limit 12` and `0..12` at `--limit 13`.
- `u16::MAX` is the never-decided sentinel. It is **refused rather than
  written**, because a map containing it would be silently misread as a frame
  index near 65535.

Nothing was computed for this. `FocusStats::best_index()` already existed and is
already consumed by `halo::Plan::build` and by the `speckle_fraction` companion;
this is a read of it, taken after pass one's completeness assertion and before
pass two starts.

### 1.1 Why a flag *and* a variable

The orchestrator asked for an environment variable. I shipped both, with the
flag winning, and the resolved path is **printed either way**.

`argmax-baseline --index-map` already does exactly this for the naive argmax
merge. Those two subcommands exist to be compared against each other, and this
repository has twice had to repair an asymmetry between them — M104c on
resolution, M109 on exposure — each time because the asymmetry was a thumb on
the scale. Shipping the same capability under a different name on the two
halves of a designed comparison would have been a third.

The printing is not decoration. Rule 47 binds environment variables into a hash
record precisely because they are invisible in the invocation; an unannounced
one is the input that makes a frozen hash unreproducible later.

---

## 2. Bars (MEASURED)

`experiments/M97-warped-merge/src/election.ps1`, one run, all arms
`STREHL_ALIGN=0` so that the shared sidecar cache is not a confound.

| bar | claim | result |
|---|---|---|
| B1 | `--index-map` writes a map | PASS |
| B2 | `--index-map` does not move the merged image | PASS, `F240C193…` both arms |
| B3 | `STREHL_DUMP_ELECTION` does not move it either | PASS, same hash |
| B3b | the variable's map is identical to the flag's | PASS, `EC225A4C…` both |
| B4 | **PLANT** — 13 frames instead of 12 moves the merged image | PASS, `DBD8CC3E…` |
| B4b | **PLANT** — 13 frames moves the election map | PASS, `73120F22…` |

B2 and B3 are nulls, and a null that is not planted is indistinguishable from a
disconnected probe (discipline 598). B4/B4b are that plant: the *same* hash
comparison that reports "unchanged" for the flag reports "changed" for one extra
frame, so it is live in both directions.

### 2.1 Rule 47 invocation record

```
strehl stack D:\personal\macro\109MSDCF --limit 12 --gate 4.0 --out A.tiff
  STREHL_ALIGN=0   STREHL_WARPMAP unset   STREHL_FIX_HALO unset
  STREHL_DUMP_ELECTION unset   STREHL_CACHE_DIR unset   STREHL_CAPTURES unset
  32 logical processors (default worker count)
  merged: 49 449 626 B, SHA-256/16 F240C1933CF08A4C
  commit cb61774 + this working-tree change
```

`--gate 4.0` is written out although it is the default, per the habit M106's
attribution asked for: three milestones froze three invocations, none recorded
the gate, and splicing them produced a fourth nobody had frozen.

---

## 3. The map is real content, not a valid file full of nothing

`experiments/M97-warped-merge/src/readmap.py` on the 12-frame map:

- **12 distinct indices**, range `0..11` — every frame wins somewhere.
- **0 pixels** at the sentinel.
- Modal index 28.4% (`9`), then 26.9% (`10`), 22.5% (`7`). Not a dead map.
- **Boundary density 3.33% horizontal, 3.34% vertical.** Isotropic to within
  0.01 points, which is what a depth map should be and a scanline artefact
  would not be.
- **Median jump across a boundary: 1 frame. 71.4% of boundaries are
  single-frame steps.** Piecewise-smooth depth, not speckle.
- **SHUFFLE CONTROL:** permuting the same pixel values gives **77.41%**
  horizontal boundaries against the map's 3.33% — a **23.2x structure factor**.
  A map that was spatial noise would score 1.0x.

The shuffle control is the plant for the boundary statistic itself: it shows the
statistic *can* report a structureless map, so 3.33% is a measurement of the
merge and not of the arithmetic.

---

## 4. What this does and does not license

**It is an instrument, not a finding.** It says nothing yet about whether
election boundaries coincide with the blobs. What it does establish is that the
statistic the hypothesis needs is well-defined and well-behaved on real data:
elections are spatially structured at 23.2x, boundaries are sparse at 3.3%, and
they are overwhelmingly single-frame steps.

**Why a single-frame control cannot refute this the way it refuted the
8-check audit (fact 1438).** Election-boundary correlation is a *joint*
statistic between the output and the merge's internal state. An unstacked
LibRaw frame scores nothing on it, because it has no election map — not a low
score, no score. That is a structural property, not a lucky one, and it is the
reason this instrument is worth having where a generic image statistic was not.

**Caveat on the boundary/blob link, ARGUED not measured.** The prediction is
that adjacent pixels electing frames `j` and `j+1` inherit placements differing
by the alignment track's jitter (fact 1435: median 0.4829 px second difference,
13.8% of adjacent pairs disagreeing by >= 1 px), so boundaries are where
geometric incoherence should appear. **This run had `STREHL_ALIGN=0`**, so its
3.33% is the boundary density *without* any warp applied. Whoever tests the
correlation must re-measure with alignment on, against a pinned sidecar via
`STREHL_WARPMAP`, or the two halves of the comparison come from different
registrations.

---

## 5. Facts

- **R1 (MEASURED).** The shipped merge's election map exports at the plane grid,
  3516 x 2344 on an A7C II bracket, values `0..N-1` in filename order, 0
  sentinels. `--index-map` and `STREHL_DUMP_ELECTION` produce byte-identical
  maps.
- **R2 (MEASURED).** Neither mechanism moves the merged image by a byte:
  `F240C1933CF08A4C` with the flag, without it, and via the variable. Planted
  against a 13-frame arm that does move it (`DBD8CC3E7CCAED38`).
- **R3 (MEASURED).** On 12 frames of `109MSDCF` with alignment off, 3.33% of
  horizontal and 3.34% of vertical adjacent pixel pairs elect different frames;
  71.4% of those boundaries are single-frame steps, median jump 1 frame.
- **R4 (MEASURED).** The election map is spatially structured at **23.2x** a
  value-preserving shuffle of itself (3.33% against 77.41% boundary density), so
  R3 measures the merge rather than the statistic.
- **R5 (DERIVED, from R2).** The export is safe to leave in the shipped binary:
  unset costs one `env::var` miss per run and touches no pixel.
