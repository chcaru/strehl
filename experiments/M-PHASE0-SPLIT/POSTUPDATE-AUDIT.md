# D8 post-update audit protocol

Written after the orchestrator's 2026-09-02 closure-warning update and before
re-running any historical M115 code.  This is an additive audit of the already
committed SPLIT work; it does not pretend to have preceded that work.

## Question and stop rule

Does the evidence cited by `2026-09-phase0-triage.md` actually establish D8's
claim that an interleaved split is a calibrated, noise-resistant per-stack
SNR/FRC objective suitable for tuning and an empirical null?

The historical source at commit `77c8d5e9` will be loaded byte-for-byte from
Git.  Its only in-memory edit may replace its forbidden
`C:\dev\strehl-out\M115-deconv-headroom\out` destination with
`experiments/M-PHASE0-SPLIT/out/m115-rerun`; the loader must prove exactly one
replacement.  It will re-run M115 `s01_rois.py` and `s03_instrument.py` against
the original read-only `109MSDCF`, `119MSDCF`, and flat-field captures.

The triage pass requires all of the following:

1. M115's published blur-response range, filter-invariance readings, null
   classes, and identity reading reproduce within their published rounding.
2. At least one non-algebraic control is sensitive to each real failure class
   on which D8 relies: common-mode/fixed-pattern content, latent mismatch, and
   a data-dependent tuning change.  A common linear filter and the power
   identity do not count, because they cancel algebraically.
3. The quoted quantity must be FRC/SNR information attributable to scene
   detail, not merely cross-half correlation, broad-band power conservation, or
   a same-model synthetic blur response.
4. Later correction/retraction evidence must not withdraw the claimed numeric
   crossing or demonstrate a false objective optimum.

If any clause fails, the triage's own FALSE branch binds: **no current merge
code changes**.  Because the Rust prototype was committed before this
clarification arrived, failure means removing its CLI/core/merge wiring in a
new path-scoped commit while retaining the offline experiment and audit record.
A useful diagnostic is not silently promoted into closure-grade product
evidence.

## Bias direction

The sunk implementation and the desire to end the no-Rust streak bias toward
keeping the prototype.  The orchestrator's three-for-three audit failure can
bias toward a dramatic removal.  The fixed rule above counters both: numerical
reproduction is necessary but not sufficient; transfer across the named real
failure classes decides.

## Loader commissioning

Before real RAWs are opened, three defects must go RED:

* `H1`: substitute the wrong historical Git blob;
* `H2`: disable the sole output-root replacement;
* `H3`: corrupt extraction of a fixed literal fixture.

Clean self-test must exit 0; every planted invocation must exit 1.  A fresh
output directory and a source-object manifest prevent stale results from
counting as a rerun.
