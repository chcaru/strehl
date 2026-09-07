# Independent complete-array reader controls

2026-09-07. Prospective implementation choices following the accepted full-array
reader design and authority schema. No helper/control/full-array run accompanies
this document. Existing optical populations and numerical bars are unchanged.

The private comparison fixture is11 columns by7 rows, separately chosen from
the producer's observer geometry. Use float64 zero reference values so exact
boundary comparisons are not contaminated by subtracting a large radiance.
The private band is `abs(x-0.15*y-4)<=1`; both it and its complement must occur.
The actual320×240 admission uses only the registered scene band, not this mask.

Required valid/refused companions include zero residual, every residual exactly
.004 with maximum-only admission, nextafter(.004,+inf), every residual exactly
.0008 with RMS admission, every residual.0009 (below maximum but above RMS),
one.0041 residual at(y5,x9) outside the private band, one at(y3,x4) inside it,
and distinct negative/positive extrema with repeated absolute maxima. A failure
in one of five frames or one author arm cannot be averaged with other frames.
Report signed extrema and the first row-major maximum coordinate consistently.
NaN/Inf, malformed masks, empty masks, mismatched arrays and finite subtraction
overflow refuse; restored companions pass. Statistics retain an empty
descriptive branch subset as empty without turning it into an acceptance mask.

The actual bounded NPY path receives the same11×7 scalar and branch arrays,
sorted numerical indices and four diagnostic columns, written in a clearly
private directory. Reopen/hash the actual files. Test stale and coherently
rehashed payload changes, enormous header with tiny payload before allocation,
wrong shape/dtype/order, trailing bytes, bad branch, missing/duplicated numerical
index and a changed diagnostic with the scalar unchanged. Valid/restored bytes
are reopened. The private package is not an optical result or float authority.

Full-arm metadata controls exercise the actual scope validator with inclusive
16M-point/2.4B-node per-frame limits,1800CPU/3600wall per-arm limits and32MiB
storage. Point counters reset only at a frame boundary while cumulative
counters persist. Test equality and one-over, false scope, bool/float aliases,
changed limits, frame count and cumulative-versus-frame inconsistency. The
independent reference budget remains cumulative30M/600CPU/1200wall across5;
the full reader must not silently borrow component author limits.

The reader's own clocks and unique backing-array ledger use injected small
budgets for exact equality/one-over, an alias and a distinct owner, released
owners and final-persistence overrun. No actual large allocation or wait is
needed to power those limits. One clock pair spans entry through publication.
The ledger is named ndarray backing storage, not process RSS.

The actual top-level reader entry must be called with the genuine independently
admitted component record when it becomes available. A clearly named private
boundary can stop before unavailable full-render inputs; it cannot return a
fabricated full success. Check Markdown dependencies as bytes, exact component
wrapper/child success, wrong external pins, and required release/source entries.
The final full command later reads all25 actual arrays and all five complete
results. A scoped entry sentinel cannot supply that admission.

Authority/child controls use explicit private records and unchanged actual
bounded array files. Challenge unknown schema/keys, bool identities, wrong arm,
missing/duplicate original index, changed focus/gauge, an escaping or aliased
path, substituted scalar/receipt pairing, incomplete child status, and changed
whole admitted-input projection. Rehashed private copies remain fixture-only.
The acyclic writer must revoke successful publication on an injected final
budget/source failure while retaining the original error; a restored finite
writer companion remains valid. Root freezes exact source hashes and commands
before any of these tests execute. No stochastic draw or optical integration
belongs to the reader or controls.
