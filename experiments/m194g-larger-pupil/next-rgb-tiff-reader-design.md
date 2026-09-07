# Larger independent RGB16 TIFF reader

Root,2026-09-07. Source preparation only; no imports, TIFF decodes or output
measurements. The frozen M194f reader remains unchanged. Its generic classic
TIFF parsing is reused in `independent-rgb-tiff.py`, with a separate RGB-only
entrypoint and native bounds matching the new320 by240 input fixture.

The actual consumer supplies the externally pinned TIFF hash, exact expected
height/width/three-channel shape from the independently checked production
plan, and its already-running stage Budget. Expected shape fields must be
integers (not bool), within height240/width320. Each file is bounded to1MiB
with a limit-plus-one read. Actual IFD dimensions must match that shape.
An image containing a coherent wrong shape, same-size altered sample, wrong
endian interpretation or wrong metadata can therefore fail this consumer;
this parser is a byte/interpretation gate, not a visual-quality metric.

Retain strict classic-TIFF single-IFD, unsigned16-bit RGB, no compression,
identity orientation, chunky layout, no predictor, required exact
CameraLinear description/software, bounded tags and strips, disjoint
referenced regions and no trailing bytes. Both legal endian encodings are
accepted, then normalized to a contiguous little-endian u16 RGB array.
File SHA and canonical little-endian pixel SHA are separate observations.
Strip offsets, counts, shape and payload extent are checked before arrays
are allocated. All actual ndarray backings count through the supplied
`check_allocation(shape,dtype)`/`watch(array,label)` methods; elapsed checks
cover entry and return. The1MiB Python byte limit is separate from named-array
accounting and is not a process-memory claim. The caller bounds/rechecks the
whole decode population and persistence, rather than resetting a budget here.

Independent private tests will use a re-chosen11 by7 RGB fixture, both
endian encodings and multiple strips, with known nonconstant tagged pixels.
Required live failures include wrong hash, changed actual sample under its
new valid file hash (pixel oracle), wrong shape/types, huge dimensions,
truncated/appended bytes, duplicate/unknown tags, overlapping payloads,
wrong sample type/metadata and illegal strip counts/extents. Original valid
companions remain mandatory. An old128-pixel predicate must reject a legal
larger private image that this new reader accepts, before production images
are admitted. A forged successful receipt is never a decoder test.

Curie's independent quality-instrument commission owns these tests and source
review. Final source and exact commands must be frozen before execution. This
new reader does not supply authority for the producer, model or quality score;
those consumers must bind the complete input/plan/receipt/terminal-log chain.
