# M192d independent artifact verification

Written before inspecting completed run records/results. Root's registered seven
invocations are active; this review neither executes their recorded commands nor
replaces them. Reviewer owns this document, independent-verify.py, its JSON result,
and an independent report section. No new native render is planned: actual retained
output files permit independent stimulus and parser choices without another run.

Choice points re-chosen:

- Parse classic uncompressed interleaved RGB16 TIFF directly with Python struct,
  without importing author sampler/harness or tifffile. Hash raster strip payload
  in row order and compare to whole-file hashes and the archived N33 worker8 row.
- Change a Software metadata byte in a read-only patched view: whole-file identity
  must reject while decoded pixel identity remains unchanged. Change a high-byte
  bit in the blue sample at (width-29,height-17): both hashes must reject. Neither
  mutation uses the author's byte offsets. A placebo view with an empty patch
  must reproduce both baseline hashes. Re-read original afterward.
- Recompute host CPU from raw kernel+user-idle fields and product CPU from raw
  Job user+kernel fields, rather than trusting their redundant totals. Identify
  exact observer boundary values as unavailable when only their difference was
  retained; cumulative telemetry is not a replacement for those endpoints.
- Reconstruct memory observation intervals from timestamps, including the initial
  endpoint when retained and final closure, and search incident contexts for
  observations evicted from the bounded ordinary list. Bound what cannot be
  reconstructed rather than fabricate omitted samples. Check every retained phase
  duration independently against endpoints and separately verify count/max/drop
  accounting. Require final-poll/final-accounting/final-memory coverage in enabled
  traces. Sampling pass uses the unchanged complete-interval <=100ms and >=.9
  schedule coverage; no claim that the observer is the cause of any real stall.
- Decode terminal output independently with field/number expressions, validate
  actual argv/environment/input/sidecar/binary binding and full 33-frame folding,
  and check raw archived logs by hash. Require all seven warmup/forward/reverse
  invocations, preserving failed sampling outcomes.
- Prove review code's semantic rejection with counter/report mutations: changed
  CPU raw field, changed phase duration, changed sampling boolean and changed
  dimensions must fail while unchanged receipts pass. A rejector that compares a
  field only to itself is not sufficient.

Review only begins outcome validation after summary.json or aborted.json exists.
Abort is an outcome, not permission to discard an invocation. Use selected-input
hash manifests for read-only integrity checks; no capture files are altered.
Timing uses the declared two opposite-order sweeps and reports descriptive
minima/deltas only. No effective-clock, memory-campaign, M12, or SOTA claim.
