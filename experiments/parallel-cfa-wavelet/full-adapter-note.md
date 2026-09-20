# Parallel CFA full adapter handoff

Status: source implementation only; the adapter author has not compiled, tested,
decoded RAW, or judged output. The root owns execution and the independent reviewer
owns verification. This is a distinct observational implementation, retaining the
earlier boundary operator's generated quality rejection and full-run failure.

`full-stack.rs` mechanically retains the existing boundary full adapter. The
numerical API changes only by giving `fold_coefficients` one extra zero-initialized
f32 field, `scales`, with one element per padded coefficient. The numerical author
maintains weighted sums and denominator in that common running-maximum scale;
the adapter still divides sums by denominator and uses the original plain mean
where the denominator is zero. All four CFA channels share each coefficient's
weight. Source order, terminal mean, input hull, and final MHC/developer remain
unchanged. Parallel transform internals and the scaled accumulation are owned by
the numerical author, not implemented a second time here.

The ignored entry is
`merge_cmd::parallel_cfa_wavelet::full_stack::vitamin_c_observational_pair`.
`STREHL_PARALLEL_CFA_PHASE` is exactly `cost` or `full`, and
`STREHL_PARALLEL_CFA_FULL_CONFIG` supplies the unchanged strict schema-1 config.
Cost processes original source index 35. Full processes all 70 originals in their
canonical order, preserving the baseline's 18,18,18,16 chunk absorption and one
operator worker inside the fixed eight-thread execution pool.

The full domain remains 3460 by 2306 quads at crop origin (28,19), reflected into
4096 by 4096 with left/top padding (318,895), twelve levels and a 1 by 1 terminal.
Original 7032 by 4688 active source CFA, map, Catmull/rounded GPU gather, optical CA
profile, ISO100 injected noise, black/white levels, WB, matrix, tone, and all
sixteen original-source probe draws are retained. No source image volume, probe
reduction, donor coordinates, or quality parameter is introduced. The extra scale
field is 67,108,864 bytes at this fixed extent; it is independent of source count.

Cost must complete the same reconstruction and TIFF writes as full, with exact
one-source equality to the actual gathered four planes and baseline RGB16 output.
In full, the baseline RGB16 hash must equal the held baseline before candidate
reconstruction. Actual original active-CFA hashes, gathered-plane hashes, probe
seeds/variance hashes, source-file metadata, and map hash retain their original
guards. The adapter records source-phase, reconstruction, write, and total times;
progress is emitted after each source and at the finish/write boundaries. These
are operational receipts, not a speed or image-quality claim.

The root runner, not this adapter, enforces the independent preflight gate:
measured peak commit below 12 GiB and
`70 * source_phase_seconds + finish_seconds + 120 <= 1500` seconds. Only a passing
source-35 cost run may authorize the one complete 70-source observation, itself
bounded at 1800 wall seconds and 16 GiB. No quality admission is inferred from a
cost pass. A fresh build, independent controls, source review, and eventual
photographic review remain required.
