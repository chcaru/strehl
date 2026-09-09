# Native observation scope amendment 1

2026-09-09. Root authorizes source patch preparation only, under the existing
per-lane source budgets. No live patch application or numerical release.

The producer's source audit identified the actual gate operands as private
buffers in BandMerge::add_frame_with_gain. Root read the consuming code:
selection Laplacian luma, Gaussian-reduced variance, smooth5 squared energy,
the effective beta, mean-coarse bypass, weights and base handling. A parallel
pyramid or a raw-Laplacian-only test would not observe all of that input.

The producer may prepare a minimal feature-gated passive observation patch to:
    
- crates/strehl-core/Cargo.toml and crates/strehl-cli/Cargo.toml, adding the
  separately named native-sensor-transfer feature, default off;
- crates/strehl-core/src/pyramid.rs, including experiment-owned core-hook.rs
  and read-only hook calls at actual post-smooth/post-weight pre-accumulation
  operands, and at already performed per-plane coefficient consumption;
- the already chartered native CLI seam and one test-only adapter.

No mutable operands are exposed to the observer. It must not force PlaneCache
preparation, change policy/coefficients, insert an alternate merge or reorder
the production arithmetic. Existing M194h hooks/feature/evidence stay untouched.

Native gate energy includes scene signal. The diagnostic compares a
predeclared temporal-noise statistic with the actual prediction, preserving
the smoothing/reduction/boundary operators and effective beta. It must not
compare uncentered scene energy to noise variance. The independent author
chooses the estimator and source of its signal prediction.

Require same-feature observer off/on/placebo byte identity on the actual
native route, and feature-off baseline preservation where the insertion
changes the compiled path. These are future fixed controls, not executed
results. Source preparation must size their finite invocation and decode
population before root releases them.

Root separately checked only file metadata for the charter's exact27 RAWs:
all are present, total encoded926855168 bytes; paper192868352 bytes,
dark733986816 bytes; largest38825984 bytes. No payload hash/decode occurred.
These sizes aid the later bound; they are not source-content identities.
Prefer one streaming native decode per original serving all fixed observations,
with current-frame copies if needed, over redecoding by ROI. Explain the
lifetime and origin/active-domain consequences rather than trading evidence
for an unverified cache. Independent same-file decode remains separate.
