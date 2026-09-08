# Independent read of the actual camera-white native release

Root independently reviewed Socrates's final metadata preparer and its actual
output. The exact preparer ran once with held source/review hashes and exited0,
`PREPARED_METADATA_ONLY`. No subject or image payload ran in preparation.

Release `native-sensor-white-derivative-release-1.json`:60531 bytes,
SHA256 `70d44a9c43d9d8c194824b214b1287358a4f254e01ce6e1efc955d1f85af6611`.
Preparation `work/native-sensor-white-release-1-preparation.json`:22474 bytes,
SHA256 `681974d69d377fc77733f28f5c5028e03880d93c021793a33d09dcecad394d47`.

Actual independent metadata-read command from the repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/m193c-output-grid/work/read-native-sensor-white-release-1.py
```

It exited0 with `PASS_METADATA_RELEASE_READ_ONLY`:253 distinct actual files,
150 source bindings,118 inputs, exact parent/nine-reader argv and17 planned
new children. All previous146-source/93-input bindings remain intact. Three
administrative documents were checked at preparation time but are absent from
scientific inputs. The previous sensor attempt remains a bound REFUSED result;
the sole reused primary is still from original native1, not the failed reader.

New carry is43.46875 CPU seconds,37.9876842 wall seconds,242700386 file bytes
and5871335 metadata bytes, including the additional one-MiB reservation.
The actual inventory is647066 bytes. Inventory plus actual22474-byte preparation,
128-KiB release allowance and192-KiB future root allowance totals997220 bytes,
within1048576. The actual60531-byte release fits its allowance. These are
prospective reservations, not measured future output or a resource refund.

Original0's snapshot/TIFF references were not opened by this read. Actual fresh
original/plan/image identity, ten white controls, eight sensor controls and all
eleven native checks must still pass in the new reader. There is no substituted
metadata, assumed first-frame success, control execution or nine-frame admission
in the preparer's result. Existing scientific resource caps remain unchanged.

VERIFIED by independent source and actual metadata inspection: no release
blocker remains. Root may commit the exact files and invoke the sole released
parent with the actual release SHA. Subsequent coverage remains conditional on
all nine independently admitted derivatives. No physical calibration, product
default, real-detail or SOTA conclusion follows from this metadata release.
