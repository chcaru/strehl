# Bounded transfer-probe prefetch

Allocation: multi-stack-2026-10-28-transfer-prefetch. Only the NEW
crates/strehl-cli/src/session-transfer-prefetch.rs is implemented in this lane.
Root wires it as a child of session_consumer beside transfer_cache. Existing
sampler, transfer-cache, core source and cache-key inputs remain unchanged.

## API

- TransferJob: global frame index, Similarity placement, optional static optical
  profile.
- TransferReceipt: owned WarpBandTransfer, actual cache_hit returned by measure,
  and elapsed seconds for that job.
- TransferBatch: receipts in by_index (BTreeMap), planned lanes, per_probe_bytes,
  retained_result_bytes, reserved_bytes and total elapsed_seconds.
- compute(cache_root, domain, resampler, config, jobs, available_phase_bytes,
  workers) returns the complete batch or an error.

The caller supplies the already verified source-cache directory outside inputs,
runs compute inside its configured Rayon pool, and calls it BEFORE allocating
fusion workspaces. available_phase_bytes excludes source-cache reservation and
at least 512 MiB of allocator/cache-I/O/thread overhead. The module neither opens
RAW inputs nor changes global thread settings.

## Bounds and exactness

ProbeMemoryEstimate supplies the full per-probe numeric/mask-buffer peak. The
reservation adds six beta vectors and sample counts for every retained report,
plus 4096 bytes per job for headers, tree nodes and small pending/validation data.
All arithmetic is checked. Lanes are at most four, requested workers, job count,
and the number of complete probes that fit after retained reports. Inability to
fit one full probe is an error before cache access. Empty jobs, zero workers,
overflow, invalid configuration, duplicate global indices and nonfinite or
singular composed placements are refused before any job executes.

Only one batch of at most lanes jobs is submitted to Rayon at a time. The next
batch is not visible to work stealing until the current batch joins. Therefore
nested existing sampler/pyramid work cannot activate an unbounded number of
outer probes. Four-or-fewer active probes retain only their own original-u16
synthetic input and existing scratch; completed jobs retain small reports.

Each job calls the unchanged transfer_cache::measure exactly once and keeps its
returned hit flag. A later populated cache cannot retrospectively relabel a cold
probe as a hit. Fusion order remains the caller's source order, independent of
probe completion order. No floating reduction or probe arithmetic changes.

Jobs with equal placement bits are deliberately separated into different
batches, even if their profiles differ. Identical cache keys necessarily have
equal placement bits, so this conservative scheduling prevents concurrent
corrupt-entry removal in the unchanged cache helper. Healthy publication remains
atomic via the existing helper. Independent external processes are outside this
in-process scheduling guarantee.

On failure, all jobs in the active batch join before compute returns. Valid
completed derived cache entries remain reusable; no partial result batch is
returned. The consumer must not start fusion after that error.

## Prepared checks

Four tests are UNVERIFIED until root schedules Cargo:

1. One versus four lanes on seven distinct placements/profiles, using separate
   cold caches: exact CFA/luma/max-color bits, counts, seeds and realizations;
   then mixed cached/new jobs retain their original per-job hit flags.
2. Exact single-probe boundary, worker/job/four-lane caps, under-budget refusal,
   empty/zero-worker rejection and integer/address-space overflow refusal.
3. Duplicate indices and singular placements fail before writing cache files.
4. Repeated identical operators serialize, including corrupt-cache repair; the
   first job reports a miss and subsequent actual cache reads report hits.

Source formatting completed, without Cargo or numerical execution:

    rustfmt --edition 2024 crates/strehl-cli/src/session-transfer-prefetch.rs

Root will test/build, run isolated cold-cache A/B pilots and verify complete
cached grouped-image equality. Speedup and resource utilization remain
UNVERIFIED. The planned lane count is a cap, not proof that every batch used all
lanes; equal-placement serialization or a short final batch can use fewer.

## Consumer integration review

Source inspection of root's integration confirms:

- Prefetch completes before NativeSampler, PreparedSource, GroupWorkspace and
  SessionMerge allocations. Cache reservation plus 512 MiB overhead is subtracted
  from the phase limit, and the reported overall reservation takes the maximum
  of prefetch and fusion phases.
- The original grouping plan and nested fusion source loops are unchanged.
  Receipts are removed by global index in that original order; a missing receipt
  is an explicit error. Actual per-job cache hit/miss and seconds are retained.
- Prefetch errors occur before fusion starts. Successfully completed derived
  cache files can remain reusable without publishing an incomplete photograph.
- Existing fusion reservation still includes one old single-probe allowance;
  this is conservative because that probe no longer coexists with fusion.
- Retained-result bytes are added to the final fusion reservation after prefetch.
  An extremely near-limit request can therefore do useful cache work and then
  refuse before fusion allocation. At 598 jobs the retained allowance is only
  a few MiB. Root accepts this nonblocking resource-UX limitation for this pass.

Root will move the existing structured merge-progress stage before prefetch
once the current frozen build completes, so a cold cache does not leave the UI
showing the preceding stage for the entire probe phase. That integration edit
belongs to root; no existing operator/cache-key source was edited here.

The source remains frozen. Focused tests, isolated cold-cache speed/memory
comparison, and complete cached grouped-image equality remain pending with root.
No performance improvement is claimed for this new prefetch module yet.
