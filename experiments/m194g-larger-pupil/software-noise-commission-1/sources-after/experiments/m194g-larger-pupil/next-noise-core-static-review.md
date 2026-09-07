# Software-noise core: independent static review

**STATIC REVIEW ONLY; no draws or commissioning authority.** Zeno reviewed
`software-noise.py` at SHA-256
`01cf39b1a4d43361b6b51c5c7f2bc6523a4fd743324df0859213c58ab1f25924`
against the committed `next-noise-contract.md` at
`4e92e176d0cfae6dcdc9fedab3ff8f5d40f858c47eb0fcddbd14877d894d29f2`.
The corrected source was subsequently inspected at
`abe9d712cbf9caf07f8dfc276a0e0ab4474366db039fd3b1fc2f25cb7a057292`.
There is no remaining static blocker identified in this core-only review;
the required runtime commission remains unexecuted.
The original contract was Zeno's design, subsequently amended by Curie after
independent review; this pass challenges Curie's implementation. It is not an
independent calibration of the synthetic noise parameters.

## Finding and correction status

**ARGUED from source: expired weak entries can lose a new live allocation.**
`Budget.watch` looks up `id(root)` before removing expired weak references.
If Python reuses a dead ndarray's identity for a newly supplied backing array,
the code adds the new name to the old entry. The following `check()` removes
that expired entry without registering the new live array. This affects direct
`watch` callers, including the input validator and array writer; internal
allocation paths usually prune through their preceding allocation check.

This was sent to Curie and root before execution. Required correction: prune
before lookup, or replace any entry whose weak reference does not resolve to
the actual backing ndarray. A prospective guard control should supply a stale
weak entry for the new root's key, then verify registration and cumulative
limit refusal, with a live alias counted once. Such a control should not rely
on nondeterministic real-world object-id reuse. No reproduction was executed
in this review.

**Correction inspected:** the corrected `watch` prunes expired owners before
key lookup, then replaces a missing entry or an entry whose weak reference is
not the actual root. Only an entry resolving to the same root is treated as
an alias. This closes the identified source-level path. Its prospective
runtime control remains necessary; a static correction is not measured
memory-limit commissioning.

## Contract comparison

No additional mismatch was found in the reviewed core paths:

- `key_bytes`, `validate_key`, and `_new_generator` use the declared ASCII
  tuple, final LF, SHA-256 little-endian words, pool size 4, and separate
  PCG64DXSM generators. `sample_frame` makes one flattened native-order
  Poisson call and one full normal call, retaining actual key, state, call,
  and draw metadata. Repeat/frame key faults alter the consumed stream;
  omitted-component validation precedes generator construction.
- Photosite factors precede the normal Poisson draw. The seven main faults
  affect consumed photo, read, gain, key, or encoder-input values. The
  photo-after-factor and green-clone interventions retain consumed-photo
  overrides; zero-read and correlated-read interventions retain original
  normal draws. The actual electron sum and pre-encoder DN have separate
  hashes. Restored calls execute the nominal path.
- The encoder uses float64 arithmetic, ties-to-even, pre-clipping rail
  counts, then clipping to 0 through 15360 and little-endian u16. The
  black-clamp fault retains pre-fault rail evidence. Tagged swaps move
  actual photosite payloads. Intended persistence refuses any recorded
  pre-clipping rail excursion.
- Noise-off reaches no generator branch and has null streams. Mandatory
  sampling/encoding counters are separate from the optional count/placebo
  hook; the hook contains no random operation. This is source inspection,
  not the required byte-invariance or forbidden-sampler experiment.
- Named internal array allocations and requested variates are checked
  before their respective allocations/draws. The writer checks the byte cap
  before each write, rehashes persisted bytes, retains primary exceptions
  through cleanup errors, and can reconcile the complete directory extent.
  The corrected weak-entry handling addresses the finding above; none of
  these resource guards has been executed by this review.
- The runtime guard pins declared versions, the actual interpreter and
  loaded RNG/core module files, constructor/writer identities, and thread
  settings. Thread settings precede the first NumPy import. Final runtime
  and source rechecks exist. No statement here verifies those checks at
  runtime.

## Remaining consumer obligations

The file explicitly supplies a core, not the complete experiment controller.
Its caller must independently bind the frozen runtime record and input float
authority; enforce the exact 1,186-call private schedule and 90-file intended
matrix; hold only the permitted frames; include snapshots, negative fixtures,
reader work and final metadata within the same stage budgets; and perform the
post-terminal-write check. `RuntimeGuard.finish()` alone cannot account for
work or files a caller subsequently creates outside that shared budget/store.
The independent moment, correlation, quantization, replay, observer and
malformed-input controls remain required before any noise admission.

Read commands used PowerShell `Get-Content` and `rg` on the two project files;
`Get-FileHash ... -Algorithm SHA256` confirmed the three hashes above. No imports,
helper calls, noise draws, model renders, or output quality scores were run.
