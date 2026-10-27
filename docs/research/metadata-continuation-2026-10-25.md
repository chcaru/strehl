# Metadata and core research status, 2026-10-25

This compact publication summary records the outcomes behind the metadata
inspector and experimental temporal-energy mode. It retains negative results
without distributing private captures, firmware images, identifying metadata,
local paths or generated campaign artifacts. The detailed immutable study
records remain separate; this page is not a replacement reproducibility bundle.

**VERIFIED / DERIVED:** no metadata-driven improvement to Strehl's core stacked
photograph has been demonstrated by these continuations. Reader conformance,
useful inspection, generated coordinate correctness and a better photograph
are separate claims. None of these results promotes a new quality default.

## Metadata reader

REA-a7c2-2026-10-24, -b and subsequent native-reader work established the observed
focus-field layout and an inspector that preserves unknown values. The optical
reader's independent conformance audit checked all 19,734 typed fields in its
fixed 598-file population without a mismatch. This verifies representation on
that population, not optical calibration or quality improvement.

The sparse AF field carries conditional focus information. Its signed display
interpretation does not establish metric depth, exposure-time freshness, complete
status semantics or image registration. Firmware can reuse older AF and lens
buffers; matching sequence fields do not prove that those buffers are fresh.
The inspected status semantics are tied to firmware 2.01, while the retained RAW
witnesses use 2.00. That transfer remains unverified.

Conditional grid and scattered-cell tests retained sparse usable support and
failed to improve on both direct image-response references. They do not justify
automatic focus-window selection or replacing the existing image-only fit.
See the [inspector guide](../sony-focus-metadata.md) for supported formats and API.

## AF support screen

**MEASURED / DERIVED, REA-a7c2-2026-10-25-a:** the fixed local AF screen passed
55 of 56 generated checks. Its sparse-positive check failed, so the control run
remains failed. A separately reviewed necessary-support calculation, using only
status masks and geometry, admitted at most 1 of 17 and 7 of 17 held sites in
the two populations. Both are below the frozen minimum of 8.

This upper bound deliberately ignores AF values and several other admission
conditions, so actual qualification can only be narrower. The fixed candidate
was rejected before a real-value fit, alignment-patch implementation or photo
campaign. The failure does not show that all AF information or other consumers
are useless. No gate, radius, split or witness was changed to rescue the result.

## Optical tables and ordinary coordinate correction

**MEASURED, REA-a7c2-2026-10-24-l:** the conditional per-frame optical-table
consumer did not achieve its required photographic improvement against the
forced-zero and fixed-profile controls. The required positive gate failed.
Exact metadata representation does not establish a calibrated correction law.

**MEASURED / DERIVED, REA-a7c2-2026-10-24-t:** the separately completed ordinary
guide-to-native coordinate trial produced zero qualifying On improvements on
either scene. Both reviewers tied all 40 fixed native crop pairs after complete
output inspection. No confirmed new differential defect was found. The unchanged
gate required two spatially separated informative improvements per scene.

That is a completed negative for photographic benefit on the tested recipe,
not mathematical identity or a general safety proof. The independent reviewer
recognized a public image hash from earlier Off inventory, so blinding was
incomplete; the limitation was disclosed before rating. Both rating records
were frozen before the key was opened. This ordinary coordinate trial does not
establish Sony metadata value or justify default promotion.

## Temporal energy

**MEASURED, REA-a7c2-2026-10-24-d:** filtering adjacent-frame energy and the full
noise floor can erase a weak feature present sharply in only one frame.
Generated broad-focus and noise cases do not negate that failure. The mode
therefore remains experimental and Off by default.

**VERIFIED visual observations:** some inspected fields appeared smoother, with
no clear new protected-detail loss in the retained native witnesses. This
establishes neither general sharpness improvement nor correction of existing
broad colored rims. Spatial smoothness alone is not temporal-noise evidence.

**MEASURED, independently reviewed:** the retained dark-repeat comparison found
lower aggregate temporal variance in its fixed groups and regions. Most of the
effect also occurred with spatially shifted neighbor guidance. Its scope does
not establish general radiometric calibration or detail preservation. The
[mode guide](../temporal-energy.md) retains the numerical range, controls and
usage limits. The method does not consume camera AF or depth metadata.

## Retained command and record identities

These are historical command records, not commands to execute automatically.
The full research bundles, input identities and outputs are not included in a
public desktop source kit. Public source retains only the Rust examples/test
includes required by Cargo and the compact summaries needed by product guides.

- Reader audit: `python -X faulthandler experiments/rea-a7c2-2026-10-24-l/review/setting-width-native-audit.py`; exit 0.
- AF controls: `python -X faulthandler experiments/rea-a7c2-2026-10-25-a/candidate/local-screen.py controls --out outputs/rea-a7c2-a/controls-1`; exit 1, retained failure.
- AF support: `python -X faulthandler experiments/rea-a7c2-2026-10-25-a/candidate/mask-support.py`; exit 0, necessary-bound calculation only.
- Ordinary phase continuation: `python -X utf8 -X faulthandler experiments/rea-a7c2-2026-10-24-t/resume-2026-10-25/photo-continue-v2.py <step-id>`, with each population's `off-confirmation`, `on-map`, `on-render`, `on-validate`, `on-matched-display` and `on-export` IDs. Both native On renders exited 0; downstream saved-output gates passed. Native renders used four workers each and the same frozen map, Crop, CA, pyramid recipe and display baseline.
- Temporal generated core checks: `cargo test --locked --offline --release -p strehl-core --features temporal-energy temporal_energy -- --nocapture`; exit 0.
- Temporal finish falsifier: `cargo test --locked --offline --release -p strehl-cli --features temporal-energy,spatial-noise-floor --lib merge_cmd::noise_floor_gather::reconstruction::temporal_d::temporal_finish_falsifier -- --ignored --exact --nocapture --test-threads=1`; execution completed, including the retained weak-feature failure. Spatial-floor mode was explicitly Off; the stage used 16 repeats and one Rayon worker.

| Retained record | SHA-256 |
| --- | --- |
| Native optical conformance review | `171e2a733ee17ecd68dde4c264e1e4cdbf7eeadf3b3aba805dfd10072c51c31f` |
| Optical-table completion record | `d0e260a71fccfa2cd7bc2ca81bc75dedebb7c1c6e806ab5c8f07e56968494796` |
| Independent AF result review | `dc64defa34d41f931fadf402864a77b2a32d5cac66c03a9e46f88c5eda41b6d7` |
| Ordinary phase photo decision | `abe84920a37cf49b604e9d9695044ba72549ba7da7282d2c41f3fbcf727a4373` |
| Temporal generated-results report | `a1c3e332b72818dd3886e2812c1fe88a7d13260ad93a68fe379eab1cf8fc45ea` |
| Independent dark-repeat review | `8009de44a7bc7bf3388f7473aa4be875392a338f5adf23a9a182be2f3ba9b370` |

These hashes identify retained records; they do not make the omitted private
data public or establish independent reproduction from this source package.
