# M194h checker Windows reader source correction

SOURCE ONLY; no checker/control/import/image/build execution. Original source68,539B/045fb2a20126440446e9128c05b7eb1d5d4a1ed8c4b2f3276b5dc95130936579 and its original reviews remain preserved by commit b2475a48f4fb73000b9748142c3e2cbc121850ab.

Root's first metadata preparation refused before build because Windows path stat and handle fstat reported different ctime conventions. Their dev/ino/size/mtime/nlink agreed; each API's ctime was stable independently. This note does not invent a successful new execution or generalize that observation to every Windows filesystem.

The correction is limited to Files.read, Files.actual and the ordinary imported-NumPy initializer observation. Full object_identity remains unchanged, including ctime and attributes. A new shared_identity contains dev/ino/size/mtime/attributes/nlink. Path-before and handle-open compare that common identity. Handle-close compares its complete tuple, including ctime, with handle-open. Path-after compares its complete tuple with path-before. The normal reader's seen table retains both full path and full handle tuples and requires both on repeated reads. No ctime field is dropped from within-API stability checks; existing positive/empty role, extent/hash, reparse, ownership and file-link predicates remain.

A six-replacement reverse-text proof restores the exact old bytes. AST comparison confirms only those three existing functions changed and shared_identity was added; all other function bodies are identical. No source population, command, grant, arithmetic, float bound, metric, decoder, case order, resource cap or output population changed. Original design/ledger/review files are unchanged; this addendum documents the new reader semantics before independent review.

Root will exercise the correction in the separately bounded metadata preparation: allow stable differing cross-API ctime; reject path-only ctime drift, handle-only ctime drift and shared-identity mismatches through the corresponding actual seam. Those are future control outcomes, not claims of this source-only proof.

Current checker: 69266 bytes; SHA256 800afb0cc1dbfd6528c163fd53fcc67eb325ab7c53943babd40689f0830bdd65.

Unchanged existing function/method bodies: 62. Changed: Files.actual, Files.read, numpy_source_observation. Added: shared_identity. Syntax parsed only.
