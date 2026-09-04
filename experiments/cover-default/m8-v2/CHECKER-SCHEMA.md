# M8 v2 independent checker contract

`checker_v2.py` is an adjudicator, not a trace producer. It imports NumPy and
tifffile but no Strehl, historical checker, producer, or runner module.

## Commands

All commands cap Cargo, Rayon, OMP, OpenBLAS, MKL, NumExpr, BLIS, and VecLib at
eight threads before NumPy is imported.

```text
python -B checker_v2.py commission

python -B checker_v2.py adjudicate \
  --capture CAPTURE \
  --trace-dir TRACE_DIR \
  --tiff CAMERA_LINEAR_RGB16.tiff \
  --source-inventory ORDERED_SOURCES.json \
  --sidecar-sha256 64_HEX_DIGITS \
  --mode scale|crop \
  [--crop x,y,w,h] \
  --output-dir NEW_DIRECTORY

python -B checker_v2.py verify --result NEW_DIRECTORY/result.json
```

`--crop` is mandatory in Crop mode and forbidden in Scale mode. Its coordinates
are an explicit rectangle in the full plane grid; the checker never infers an
origin. The TIFF must be exactly `h x w x 3` for Crop or the full trace
dimensions for Scale, one-page RGB `uint16`.

The source inventory is an array, or an object whose `entries` or `sources` is
an array. Every entry must contain:

```json
{
  "path": "absolute/or/inventory-directory-relative/path.ARW",
  "name": "path.ARW",
  "size": 123,
  "sha256": "..."
}
```

`path` may be replaced by `name` when the object has a `directory`. Entries
must already be in exact lexical frame-name order. Every source file, size, and
SHA-256 is checked before any result staging directory is created. This order
defines frame indices and exact-tie precedence.

Every emitted block frame path must be absolute and resolve to the matching
inventory entry's full path. A matching basename in another directory is a
hard refusal; trace evidence is never relabelled with an inventory hash by
basename alone.

## Trace input

The historical `M8SITE01` block-v1 byte layout is:

```text
<8s9I6d2fI
magic, embedded_protocol, kernel,
source_width, source_height, destination_width, destination_height,
site_x, site_y, channel,
a_re, a_im, b_re, b_im, cx, cy,
white_minus_black, frame_site_gain, frame_path_byte_count
UTF-8 frame path
source_width*source_height little-endian f32 source values
destination_width*destination_height little-endian f32 gathered values
```

Embedded protocols 1 and 2 share this fixed layout. Full-resolution source
dimensions must be exactly twice the destination dimensions. The four admitted
RGGB records are `R=(0,0,0)`, `G1=(1,0,1)`, `G2=(0,1,1)`, and `B=(1,1,2)`.
Adjudication requires exactly one Catmull-Rom block for every ordered
frame/site pair.

A trace directory may instead contain exactly one explicitly versioned wrapper
named `trace-index.json`, `trace-metadata.json`, `metadata.json`, or
`*.m8meta.json`:

```json
{
  "schema": "strehl-m8-trace-metadata",
  "version": 1,
  "payload_layout": "block-v1",
  "blocks": [
    {"path": "frame-00000-R.m8site", "sha256": "..."}
  ]
}
```

`m8-trace-metadata` and `strehl-m8-trace` are equivalent schema spellings.
The wrapper must list every `.m8site` under the trace directory exactly once.
Payload hashes are checked when supplied. Any wrapper support indices,
validity, hull, tolerance, contributor, or pass fields are deliberately
ignored.

The checker derives output gains from frame index zero's R, G, and B site
gains, matching the production output's first sorted frame contract. Every
frame's G1 and G2 gains must be bit-identical and all sensor ranges must be
bit-identical.

## Independent computation

For every block and full destination coordinate, the checker applies the
effective f64 similarity at the CFA half-plane offset, multiplies both source
coordinates by two, reconstructs Catmull validity, clamps before floor, and
reads offsets `[-1,0,1,2]^2`. Source intervals and
`8*ULP_f32(max(1,abs(lo),abs(hi)))` use binary32 operations. The finite gathered
pattern must exactly equal independent validity.

M8-R's primary denominator is every independent valid full-grid sample.
Crop's delivered subset is selected only with the supplied rectangle; an M8-R
row outside it has local coordinates `(-1,-1)`. Scale's full and delivered
counts must coincide.

Per-site output intervals and tolerances are transformed in binary32 by
`output_gain/frame_site_gain/(white-black)`. R and B use global endpoint and
maximum-tolerance witnesses. Green uses independent G1 and G2 endpoint
witnesses:

```text
lo = .5*(min G1 lower + min G2 lower)
hi = .5*(max G1 upper + max G2 upper)
tau = max(max G1 tau, max G2 tau)
```

Exact ties retain the lowest ordered frame index; a same-frame green-tau tie
retains G1. TIFF comparison is in float64 after exact `encoded/65535` and adds
exactly `0.5/65535`.

## Atomic output and evidence

The final output directory must not exist. Work is written below a sibling
`.staging-PID` directory, removed on refusal, and renamed to the requested
directory only after all blocks, finite patterns, TIFF samples, intervals,
witnesses, rows, and hashes validate.

`result.json` references a content-addressed
`evidence-index-SHA256.json`. The index contains:

* one structured M8-R violation `.npy` for every frame/site, including zero-row
  files;
* one complete structured M8-O violation `.npy`;
* full-grid `endpoint-values.npy`, shaped `(4,H,W,3)` with axes
  `(R|G1|G2|B, y, x, lo|hi|tau)`;
* matching `endpoint-witness-frames.npy`; the site axis itself identifies each
  witness site;
* capture, mode, sidecar, ordered source, trace-payload, frame/site/channel,
  full/delivered census, row count, byte count, and SHA-256 metadata.

M8-R rows hold full coordinate, Crop-local coordinate or `(-1,-1)`, gathered
value, bounds, tau, direction, signed excursion, and positive excess beyond
tolerance. M8-O rows hold local/full coordinates, channel, encoded/normalized
value, bounds, total tolerance, direction, excursions, both green endpoint
witnesses (or one R/B witness), and the tau witness.

`verify` checks the result-to-index hash, content-addressed filename, every
artifact's bytes/SHA-256/shape/dtype/row count, completeness of the frame/site
index against the separately retained source inventory, and the retained TIFF
and source-inventory hashes. It refuses modified coordinates, arrays, index
content, omitted whole frames, or external identities.

## Runner-owned strict controls

A value-only payload cannot prove how many writers raced before the retained
files existed or prove output transparency between separate binaries.
`refuse_unsafe_producer_state(...)` is the strict helper for the runner's
commissioning plants. It requires:

* observed block count exactly equals `4 * ordered_frame_count`;
* zero duplicates;
* exactly one trace-state writer;
* byte-identical uninstrumented, instrumented-tracing-off, and
  instrumented-tracing-on TIFF SHA-256 values.

The checker independently catches missing/duplicate retained blocks. The
runner must measure concurrent-state and three-way output transparency; a
producer assertion cannot substitute for those observations.
