# Full R/B residual adapter handoff

Source implementation only. The adapter author has not built, tested, decoded
RAW, or judged images. Root owns execution and resource limits; an independent
reviewer owns verification. This is a bounded photographic observation, not
generated-screen admission or a production-default change.

The ignored entry is
`merge_cmd::rb_residual_full::full_stack::vitamin_c_observational_pair`.
`STREHL_RB_RESIDUAL_PHASE` is exactly `cost` or `full`;
`STREHL_RB_RESIDUAL_FULL_CONFIG` supplies the retained strict schema-1 config.
Cost consumes source index 35. Full consumes the complete 70-frame vitamin-C
sequence in order. Both use the fixed significance multiplicity N=70; cost does
not obtain a lower threshold from its single consumed source.

The adapter mechanically retains the earlier parallel-CFA full adapter's held
map, source metadata, crop [28,19,3460,2306], original full-domain rounded GPU
MHC/Catmull/CA gather, injected noise model, WB, matrix, tone, source-file guards,
and canonical 18,18,18,16 baseline absorption. One operator worker uses the fixed
eight-thread pool. Original storage remains u16. No source-image volume is stored.

The numerical author owns the full-scoped Accumulator and row writer. The
adapter calls close_chunk immediately after each canonical absorb, so both
one-plane R/B accumulators retain that same grouping. It keeps canonical total
alive through the guarded finish, and retains baseline planes for the writer.
The operator uses the actual baseline pyramid domain and reached bands: no
complex transform, padding, alternate boundary rule, or old wavelet type remains.
All sixteen original-source probe draws are retained. The fixed residual rule
and conditional F-law caveats belong to the numerical design; the multiplicity
is not an empirically calibrated camera or full-image false-alarm guarantee.

Full execution must reproduce the held baseline RGB16 hash before candidate
finish/write. Candidate G1/G2 hashes must equal canonical. The numerical row
writer combines guarded camera R/B with canonical camera G, then uses the same
developer; this does not promise unchanged final sRGB G after the colour matrix.
Cost additionally requires exact four-plane equality with the actual gathered
source and exact baseline/candidate TIFF pixel equality. Output file hashes and
all four plane hashes are recorded without requiring build-dependent TIFF
Software metadata to match an older executable.

Progress lines and receipts retain decode, baseline fold, per-source numerical
phase, reconstruction, write, and total times. Root's external runner applies
the resource gate before any 70-source run. These are operational receipts,
not a speed benchmark or an image-quality claim. No original read, test, or
candidate execution was performed while authoring this adapter.
