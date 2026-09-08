# Independent read of the actual sensor native release

Root independently reviewed Socrates's final preparer and then its actual
metadata output. The preparer ran once with the three held source pins, both
independent source reviews and root's preparer review as explicit arguments.
It exited 0 with `PREPARED_METADATA_ONLY`; no image payload or subject ran.

The actual release is `native-sensor-derivative-release-1.json`, 54343 bytes,
SHA-256 `fb651f3b4aa5eeb891d6cef77e8719e13bb556ba086bd2dbd2add742d93505b8`.
The actual preparation record is `work/native-sensor-release-1-preparation.json`,
18876 bytes, SHA-256
`2ddb0d480a991a40cf00bf60a4cd2cedb7ba309a2f03e9a8d5f59e288d87ee65`.

Root's separate metadata read ran from the repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/m193c-output-grid/work/read-native-sensor-release-1.py
```

Actual exit 0, `PASS_METADATA_RELEASE_READ_ONLY`: 225 distinct actual files
rehash, 146 source bindings and 93 inputs. It checked exact source/metadata
bytes, retention of every old native source/input, new closed schema, unchanged
compiled producer, carried work, exact parent/nine-reader vectors, one historical
primary and eight newly scheduled primaries. The preparation record lists 17
new child invocations. No RAW/TIFF payload was opened for this review.

The byte carry is 240957039 total file bytes and 4127988 metadata bytes after
the additional one-MiB reservation. CPU remains 37.71875 seconds and conservative
wall 32.1440803 seconds from the actual diagnostic records. The named observed
metadata inventory is 196774 bytes. Inventory plus actual preparation extent,
128-KiB release allowance and 256-KiB future root-metadata allowance totals
608866 bytes, below the reserved 1048576. The actual release fits its allowance.
This is conservative prospective reservation, not actual future I/O or runtime.

The old result remains REFUSED. Original0's saved primary, plan, TIFF and RAW
snapshot are only reuse candidates until the new parent checks actual bytes,
full-nine original identity and complete plan equality, and a fresh independent
reader succeeds. Other eight inputs require fresh primary/reader pairs. The
future coverage variant cannot run on this preparation alone.

VERIFIED by independent source/actual metadata inspection: no remaining release
blocker found. Root may commit these exact bytes and invoke the sole released
parent with the actual release hash. Controls, original0 reuse, real derivative
admission, registration, native output quality and SOTA remain unmeasured by this
preparation. The independent reader source review and root's independent parent
and preparer source reviews retain their separate scopes.
