# Exact session accumulation optimization

Root transferred ownership of crates/strehl-core/src/session-fusion.rs from the
fusion author to the sampler author for this bounded optimization. Numerical
recipe, masks, thresholds, grouping, source order and group order are fixed.
The fusion author independently reviews the change afterward. No Cargo or RAW
job is scheduled by this implementation lane.

## Measured baseline and opportunity

MEASURED by root, verified by reading the retained receipts:

- Candidate 1 executable SHA256:
  c71cf9be854727090ee620269e6ab7fccd9e67387ef6e8766c688c2378a35dea.
  Elapsed 92.60536670684814 s; sampled peak private 3919335424 bytes.
- Candidate 2 executable SHA256:
  69c2c374f571bfcb28d9b9a462a221547a54ebf1e5d7e3d80b70c4ed486597b0.
  Elapsed 33.459447383880615 s; sampled peak private 3915931648 bytes.

The actual commands in outputs/multi-stack/pilot-{1,2}-run/receipt.json are:

    outputs/multi-stack/candidate-1/strehl.exe session stack outputs/multi-stack/manifests/insect-middle-five.json --out-dir outputs/multi-stack/pilot-1 --cache outputs/multi-stack/source-cache --threads 16 --memory-limit-gib 16
    outputs/multi-stack/candidate-2/strehl.exe session stack outputs/multi-stack/manifests/insect-middle-five.json --out-dir outputs/multi-stack/pilot-2 --cache outputs/multi-stack/source-cache --threads 16 --memory-limit-gib 16

Both ran from C:/Users/chris/.codex/worktrees/multi-stack/strehl with
RAYON_NUM_THREADS=16, Windows 11, 16 physical/32 logical CPUs and 66094223360
bytes physical RAM. Receipts record available memory before/after and sampled
owned-process CPU. These are end-to-end runs, not isolated sampler timings;
identical initial cache warmth is not established by the command alone.

Root measured candidate-2 stages over ten sources: probe 10.05 s, gather 1.22 s,
prepare 3.34 s, accumulate 11.14 s. DERIVED: accumulation is about one third of
33.46 s, so even eliminating its entire measured cost would leave about 22.32 s.
No parallel speedup is assumed; memory bandwidth and remaining serial work limit
what the next run can establish.

## Changes

- Safe disjoint 4096-coefficient chunks update ordinary/primary contributions,
  source counts, Welford means/M2 and variance sums within each source.
- Coverage fallback sums/counts and primary preference update independent chunks.
- The preferential uncensored hull updates independent chunks while preserving
  which source first resets a coverage-only bound.
- A one-source Repeat group skips repeat-only residual/energy smoothing. It
  cannot satisfy count>=2; unchanged final decisions use ordinary contributions.

All operations for one pixel retain their previous arithmetic and source order.
The next source starts only after parallel work joins. There is no floating
parallel reduction, source reordering, unsafe aliasing, new pixel buffer, change
to the memory estimate, or environment mutation. Coarse/final diagnostics remain
serial and retain their previous semantics.

## Prepared control and status

The new independent_pixels_are_bit_identical_with_one_and_sixteen_workers test
covers both group modes and both primary policies, paired and singleton groups
with reused buffers, a wholly censored singleton, a shared censored patch,
missing coverage with NaN poison, and odd sizes spanning full/partial chunks.
It compares every output float bit, final validity mask, per-fold diagnostics,
final diagnostics and independent-count histograms between one and sixteen
workers. It also requires exercised averaging, primary fallback, saturation
fallback, valid output and genuinely missing output.

Source-only formatting completed:

    rustfmt --edition 2024 crates/strehl-core/src/session-fusion.rs

Root subsequently reported all 17 fusion tests passing in
outputs/multi-stack/checks/fusion-suite-5.log, including the new worker-count
bitwise output/diagnostic control. Four unnecessary mut bindings were removed
afterward; that cleanup changes no algorithm. Source was immediately refrozen
for root clippy/build and independent review. Frozen candidate comparison and
updated performance measurement remain pending.
