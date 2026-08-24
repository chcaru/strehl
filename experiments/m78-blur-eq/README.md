# M78 — blur-equalised and phase-shifted short alignment edges

**Status:** pre-registered; measurement not yet run.

This directory forks `experiments/m23-metacal/` to test two separately attributable repairs:

- **Arm A:** R5 cross-blur equalisation using fixed per-tile focus labels.
- **Arm B:** a known integer-plus-half-pixel moving-frame shift, removed analytically.

The binding contract is `PREREGISTRATION.md`. The real capture trees are read-only. No M78 code or
result belongs under `crates/`, `SYNTHESIS.md`, or `AGENTS.md`.

The inherited Rust estimator files were byte-identical to M23 when copied. The crate rename and
this documentation are the only pre-registration-stage changes.
