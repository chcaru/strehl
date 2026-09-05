# M172: D9 closure assessment for M12-S

**Status:** NEGATIVE CONTROL FIRES. D9'S CONSTRUCTION IS MATRIX-WIDE.
THE REGISTERED N33/N105/N299 EMPIRICAL CERTIFICATE IS NOT YET COMPLETE.

This report supersedes and removes M172's earlier scoreability memo. The
registered M139 result stands: M12 is measured and fails on the code that M139
measured. This report does not promote a post-repair memory diagnostic, assess
the memory repair, or change any M12 component other than D9's M12-S target.

## 1. Secured evidence

The initially at-risk throughput files were committed first:

`09b4dccff4c60ef5414d8150d53a21e08ffa16d9`

That commit contains:

- `experiments/M172-worker-memory/campaign.py`
- `experiments/M172-worker-memory/verify.py`
- `experiments/M172-worker-memory/results/campaign.json`

The expanded output control, f32 observer, independent verifier, five planted
RED controls, and research record are committed at:

`97e5ad9cd5fdb0f47cdffc7a1c7a9418d6df89a8`

The D9 production change itself is:

`fc2abb499126a56302de7f21f527de5613be34e7`

## 2. The original gate was structurally inert

The first gate used pre-D9 N=16, alignment off, and only W1 versus W16. It
produced one pixel hash where two were expected. That did not show that the
defect was absent or quantized away.

Pre-D9 partitioned frames with
`per_chunk = ceil(frame_count / execution_workers)`. At N=16/W16 every chunk
held one frame. Absorbing those one-frame partials left-to-right reconstructed
W1's exact addition tree. The equality was therefore predicted by the broken
implementation.

The f32 observer confirmed this before demosaic and uint16 encoding:

- N16/W1: `2D57F3FA0432B536138CCFA850D8BE90`
- N16/W16: `2D57F3FA0432B536138CCFA850D8BE90`

The gate compared an equivalent pair. It was not blinded by final
quantization.

## 3. The negative control fires

Keeping N=16, alignment off, ordinary `catmull-rom`, the same input, binary,
flags, output format, and cache policy, changing only W1 to W2 produces:

| Arm | Pixel SHA-256 | f32 fingerprint |
|:--|:--|:--|
| pre-D9 W1 | `A197B0704EE39983D67264C2823CF50695E9DE1C44B834D32257612FC2004185` | `2D57F3FA0432B536138CCFA850D8BE90` |
| pre-D9 W2 | `3A31F9D0DC45429849F88540FE6AFCD6DF5765FB428C6161D2795C8851914541` | `70283E61417CDB2F506275B8F5D87ECB` |

This is the smallest tested change that fires the pre-D9 control.

The independent axes agree:

- all five N16 workers produce four pre-D9 output and f32 classes;
- raising only N from 16 to 17 makes pre-D9 W1 and W16 differ;
- N33 W1 and W16 differ with alignment off, so alignment is unnecessary;
- registered N33 alignment produces five distinct pre-D9 worker hashes.

On registered N33 alignment, the post-D9 product produces one pixel hash across
W1/W2/W4/W8/W16:

`6EFC261E892DCDB5D492AD3FD79BDC7E5A208D93D0227A41B258FB3B900F9B89`

and one TIFF hash:

`9CCF896743B08E68AB08E4437EC4E3EAF2AAD8D37884170E95067577C80286B5`.

Its post-merge f32 fingerprints also match:

- post-D9 N33/W1: `A38952442C2F4FF206A49DBE75808717`
- post-D9 N33/W16: `A38952442C2F4FF206A49DBE75808717`

The observer was output-inert, and every diagnostic output reproduced the
unmodified production binary. The verifier rejected an inert pre arm, divergent
post pixels, divergent post f32 values, observer perturbation, and record
corruption.

## 4. D9's implementation scope

The current Pyramid fold separates arithmetic topology from execution
topology:

1. `canonical_band_chunks(planning_bytes, paths.len())` depends on the build's
   memory plan and N, not the requested worker count
   (`crates/strehl-cli/src/merge_cmd.rs:5466-5469`, `:5796`).
2. `per_chunk = ceil(N / canonical_chunks)` therefore has one value for every
   worker count at a fixed N (`:5798`).
3. `STREHL_PYRAMID_WORKERS` enters only `band_workers` and
   `ThreadPoolBuilder::num_threads` (`:5473-5484`, `:5797`, `:5809-5811`).
4. Canonical chunks are folded in frame order and absorbed left-to-right
   (`:5815-5857`). `BandMerge::absorb` explicitly requires canonical chunk
   boundaries and order for byte identity
   (`crates/strehl-core/src/pyramid.rs:1998-2008`).
5. The memory repair reuses one scratch accumulator without changing that
   topology. Its production test compares every finished f32 bit against the
   retained-partial implementation
   (`crates/strehl-core/src/pyramid.rs:3696-3768`).

N can change the canonical lattice, which is allowed: M12-S compares workers
at the same N. Worker count cannot change that lattice. The Rayon work inside
each chunk writes disjoint rows or planes; no remaining use of
`STREHL_PYRAMID_WORKERS` was found outside the execution-pool resolver and its
tests.

**Construction assessment:** D9 applies to N33, N105, and N299, not only N33.
There is no N-specific branch in the repair and no registered worker value
that changes arithmetic grouping.

## 5. Evidence scope and M12-S disposition

The M172 post-D9 product evidence covers the full W1/W2/W4/W8/W16 ladder at
N33, one run per worker, plus a W1/W16 pre-quantization witness. It does not
contain six post-warm-up repetitions for N105 or N299.

Therefore:

- **Does D9's design close all registered M12-S cells? Yes, by construction.**
- **Has M172 empirically certified all registered cells? No.** M172 certifies
  N33 and the causal mechanism.
- **May M12-S be promoted to PASS now? No.** The registered certificate still
  requires six repetitions at every worker for N33, N105, and N299 from one
  hash-bound repaired binary. M179's complete matrix must decide that claim.

If N105 or N299 diverges, that is evidence of another worker-sensitive path;
it must not be averaged away or excused as a failure of the D9 control.

## 6. Registered-result correction boundary

This report accepts the registered M139 hard results relevant to D9:

- M12-S **FAIL**: five TIFF and five pixel hashes across workers at each N;
- M12-D **PASS**: one hash within every fixed-worker six-run cell;
- overall M12 **FAIL**, independently established by the registered memory and
  M12-S failures.

One arithmetic correction remains necessary in the superseding dispatch:
`0.07618677189815302` is the raw `(max-min)/min` fraction, not a percent.
It equals `7.618677189815302%`, which numerically misses the `0.02` (`2%`)
bar. M139 separately records the timing value as host-quarantined. This does
not alter the registered overall FAIL or D9's M12-S scope.
