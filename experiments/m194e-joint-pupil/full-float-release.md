# M194e complete float-run release

2026-09-07, root. The numerical amendment committed at
`d77bc3feccefb3a02d8d2c8e3911d681ead4f8f1` is now implemented and independently
checked on the registered analytic and textured point/cell controls. Release
all five fixed frames in all three accuracy arms through `commission.py` with
`author-controls-6/result.json`. All original dimensions, scenes, accuracy,
depth and work ceilings remain unchanged. The complete bundle is still
uncommissioned until the independent full-array comparison passes.

The final author control result is
`b7725860b8b7b21a812e97f01eba81d9aaf7bf0da3709edfe3c857b1f4807daf`
(135 checks). Independent numerical API3 is
`4c7d513a986b952e1f99f77ef283b3a62a44b548985e22e4a06f4410d39a48bb`
(31 analytic and 336 textured cases). Independent emitter API3 is
`d37270e2a3f1b990a69607e122b2c95beaa33238c0a1a6b77c721406e46e53f2`
(109 controls). The independent 19x11 observer/traversal result is
`b399094afc2956ab2f2d38aa4c8470ce62eb1cbd54c4ecc3e25648dfc18b4385`
(25 controls with distinct actual traversal orders).

The original angular-depth failure, initial author test failures and accepted
receipt-dtype mutant remain retained. The final schema binds the child scalar's
dtype/shape/length/hash as well as its resolved path to the parent scalar. Root
also mistyped that schema digest as 65 characters in a coordination message;
independent emitter API2 refused at startup before controls. Its log is retained.
The correct on-disk schema digest is
`0bcc546634a748ee31fbd5095b6aae3a1eab18899a557dbed8aeeb8af102a82c`.

Use a fresh per-attempt bytecode prefix and preserve the original interpreter
invocation, output, all source/design snapshots and actual terminal result.
Numerical refusal is a result, not authority to omit frames or loosen a bar.
Final CFA emission remains dependent on the genuine independent float gate;
private API fixture gates have no scientific authority.
