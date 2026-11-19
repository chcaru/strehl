# Exact RAW transport and storage

MIT OR Apache-2.0. This crate does not link or decode through `rawler`. It retains
all original file bytes, including metadata, padding and inactive sensor pixels.
The capture sender and receiver share the wire codec; Strehl's RAW wrapper uses
the same archive reader before handing original bytes to its existing decoder.

`STRHRAW1` wire framing is documented in `src/lib.rs`. A `.ARW.straw` archive
starts with a 48-byte envelope in either format:

| Offset | Bytes | Meaning |
| --- | ---: | --- |
| 0 | 8 | ASCII `STRHARC1` (format 1) or `STRHARC2` (format 2) |
| 8 | 8 | Original file length, unsigned little-endian |
| 16 | 32 | SHA-256 of the entire original ARW, binary |
| 48 | remaining | Format 1: the unchanged `STRHRAW1` stream. Format 2: an index, then chunks |

**Format 2** (`src/v2.rs`, documented there in full) is what the receiver writes
for RAWs that are a single plain CFA strip (Sony uncompressed RAW). It uses the
same predictor as format 1 but codes the residuals with per-block shifts and a
small canonical code per shift, in eight interleaved bit streams. Every chunk
carries a CRC-32 that is checked before every decode, including renders that
skip the whole-file SHA-256 for a file the receiver already verified, and an
index locates each chunk. MEASURED on the 784-RAW A7CR scarab capture: 51.21 GB
in format 1, 49.00 GB in format 2 (4.3 % smaller) and identical renders. A
one-thread decode is about 8 % slower (95.6 ms a file against 88.0), which
renders do not feel: they are bound elsewhere (20.1 s against 20.4 s cached,
42.0 s against 42.1 s from an empty cache).
About 3 MB of each A7CR file is embedded preview JPEGs, which neither format
compresses.

RAWs that are not a plain strip (Sony's lossless-compressed ARW, any other
file) are stored in format 1. Every reader accepts both formats; format 1 stays
readable for good. `STREHL_ARCHIVE_FORMAT=1` makes the receiver and `pack`
write format 1 (a diagnostic switch). Existing captures are not rewritten.

Limits: 256 MiB original file, 4 MiB decoded chunks, at most 1024 chunks
(format 1) or 4096 (format 2).
Unknown versions/methods, expansion beyond bounds, truncated/trailing data, and
original checksum mismatches fail. Archives are independent; no neighboring
frame, camera SDK, database, or sidecar is required for recovery. This is not
standard Zstd framing and must not be renamed `.zst` or `.ARW`.

```powershell
cargo run --locked --release -p strehl-raw-codec --bin strehl-raw-archive -- verify D:\Captures\stack-example
cargo run --locked --release -p strehl-raw-codec --bin strehl-raw-archive -- restore D:\Captures\stack-example --output-dir D:\RestoredRaw\stack-example
```

Restoration uses private partials, full checksum verification, flush and
non-overwriting commit. Sources are never deleted. Import one representation of
each exposure: Strehl refuses an ARW beside its matching archive. `pack INPUT
OUTPUT` archives an existing RAW without deleting it; it is not automatically
run on old captures. Every archive written (by `pack` or the receiver) is
decoded again and checked against the original's SHA-256 before it is kept.
The restore utility is independent of the receiver process.

`examples/v2-bench.rs` compares the formats' sizes and one-thread decode times
on a capture; `examples/v2-copy.rs` writes a format-2 copy of a capture folder
to a new folder (for testing readers; it never writes the source).
