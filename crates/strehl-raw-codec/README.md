# Exact RAW transport and storage

MIT OR Apache-2.0. This crate does not link or decode through `rawler`. It retains
all original file bytes, including metadata, padding and inactive sensor pixels.
The capture sender and receiver share the wire codec; Strehl's RAW wrapper uses
the same archive reader before handing original bytes to its existing decoder.

`STRHRAW1` wire framing is documented in `src/lib.rs`. A `.ARW.straw` archive is
48 bytes followed by that unchanged stream:

| Offset | Bytes | Meaning |
| --- | ---: | --- |
| 0 | 8 | ASCII `STRHARC1` |
| 8 | 8 | Original file length, unsigned little-endian |
| 16 | 32 | SHA-256 of the entire original ARW, binary |
| 48 | remaining | `STRHRAW1` stream |

Limits: 256 MiB original file, 4 MiB decoded chunks, at most 1024 chunks.
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
run on old captures. The restore utility is independent of the receiver process.
