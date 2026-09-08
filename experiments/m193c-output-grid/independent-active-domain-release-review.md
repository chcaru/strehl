# Independent preparation and actual release comparison

Root reviewed Socrates's complete metadata preparer and actual resulting
manifest. This is separate from Curie's independent review of root's probe.
No image payload, numerical module or probe was opened/executed in this release
comparison. Native1 remains refused.

The first preparer used exact binary-float addition for two serialized decimal
wall samples. Root's pre-execution arithmetic check found their sum rounds to
29.334930500000002, so equality to the literal29.3349305 would reject the valid
record. The author replaced only that comparison with exact Decimal sums of
the serialized values. No timing bar, carried value or tolerance changed.
Final preparer is10,174 bytes, SHA256
`3ec571cf56a279114cff6fd9f3411963c6efea406b3a4d5823d93515aac14124`.
Its explicit source/spec/review pins matched the held independent source review.

Root then actually ran the proposed preparation command with the three held
pins. It exited0 as `PREPARED_METADATA_ONLY`. The resulting release is40,553
bytes, SHA256 `b540b3dd8d88587a87a98e5347c579221bc46dd40f014ddd7e0e70de17452538`.
Root independently rehashed all142 current source bindings and73 metadata
input FileRefs, rejecting image-payload extensions in that metadata pass.
The two literal command arrays were read completely: pinned Python, -B,
faulthandler, distinct fresh cache paths, this probe and exact release/hash;
only the child has --worker. Only ACTUAL_RELEASE_SHA256 is substituted.

The primary receipt is the actual350,873-byte first native result, SHAe02482a3
as recorded in the source review. The retained snapshot FileRef is copied from
the failed native evidence: original0 DSC00016.ARW,39,030,784 bytes,
SHA256 `35ccc60a2cadbcdc999fb6765a326f5baaa298776fb951d12287e05c5892ed36`.
Its bytes will be read and verified by the released probe; preparation did not
read or restat the snapshot. Runtime413975cb and adjacent-DLL supplementc93af42e
are unchanged. No later original or TIFF is a probe payload.

The exact prior work is34.984375CPU,29.3349305wall,239,552,727file bytes and
2,723,676metadata bytes: native1's terminal values plus the declared one-MiB
metadata/file reservation, without refund. The fixed preparation inventory is
103,527 bytes; its2,252-byte record plus reserved64KiB release extent fits that
one-MiB charge. Actual release40,553 bytes also fits the reserved release bound.
This is operational accounting, not measured write I/O or a speed claim.

No remaining manifest/constructor blocker was found. Archive the source,
metadata and reviews before the single released diagnostic. Actual parent exit,
worker receipt, whole/row agreement flags and mismatch list still decide what
the run establishes. Completion alone will not prove matching decoded pixels.
