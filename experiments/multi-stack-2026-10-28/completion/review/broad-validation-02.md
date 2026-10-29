# Broad validation checkpoint02

MEASURED root-scheduled validation of the continuing implementation, with exact commands, process resources, complete logs and immediate exit codes retained under outputs/multi-stack/completion. This checkpoint supersedes the earlier failing core-positive control; it does not erase any failed execution.

The full core command `cargo test --locked -p strehl-core -- --test-threads=4` freshly compiled strehl-core and passed864 tests with0 failures and4 ignored corpus tests. This includes718 main-library tests, the sampler integration test, all registered control examples and doc-test discovery. Receipt core-full-validation-02 records94.743s and a1.298GB sampled private peak under concurrent research/render work. The four ignored corpus tests were not executed.

Product15 CLI session controls passed129/129. Desktop session controls passed60/60, saved-state controls34/34, pipeline controls37/37 and process-space controls29/29. These counts overlap by test name and must not be summed as unique coverage. Source rebuilds are present where code changed; later filters intentionally reuse that just-built test binary. Initial sandbox UI session execution passed56 and failed4 due denied native publication/control permissions; the elevated rerun passed all60. Product16's added initial-zoom and reverse view/source mapping controls passed62/62 before the subsequent lint-only cleanup; that cleanup needs its own final rerun.

The fresh strict core clippy check still fails43 diagnostics whose primary source spans match remote main exactly. The prior13 new core diagnostics are no longer reported. Fresh strict CLI clippy02 has30 unchanged remote-main spans, one unchanged prior multi-stack enclosing enum-size span (the largest ordinary Stack variant is inherited, as documented in checkpoint01), six new source diagnostics and three environment messages about incremental-cache hard links. The six new source diagnostics were assigned scoped iterator/type cleanup; their follow-up check is separate. `validation-lint-audit-02.json` binds every compiler diagnostic and current source/base diff mapping. Strict checks are not reported as passing.

Desktop strict clippy02 fails five new source lint sites, one inherited unused photo-viewport helper, and an incremental-cache hard-link environment warning. The scoped cleanup changes tuple argument organization, equivalent let guards/range containment and moves declarations before a test module; no numerical algorithm is changed. `ui-validation-lint-audit-02.json` preserves the full diagnostics. Its first test rebuild exposed an omitted tuple call-site in a test, so no post-cleanup desktop pass is claimed until repaired and rerun.

The broad CLI16 session rerun in the sandbox passed116 and failed13 tests that exercise native atomic cache/TIFF publication or hard-link identity controls; each failed with native AccessDenied. The elevated rerun cli16-session-controls-02 passed129/129. This is a platform permission distinction, not a change to the test expectations or a product workaround. Future native integration checks in this task should use the same authorized native filesystem execution context directly.

Exact required strict commands were:

```powershell
cargo clippy --locked -p strehl-core --all-targets --no-deps --message-format=json -- -D warnings
cargo clippy --locked -p strehl-cli --all-targets --no-deps --message-format=json -- -D warnings
cargo clippy --locked -p strehl-ui --all-targets --no-deps --message-format=json -- -D warnings
```

All builds/tests used CARGO_BUILD_JOBS=4 and GIT_WORK_TREE pointing to this isolated multi-stack checkout. Checks that require native publication were repeated with the required execution permission; failed receipts remain preserved. Full ordinary299-source output regression and the final GPU16 checks are still separate acceptance work.

## Follow-up03 before product16

CLI session controls passed129/129 after all scoped numerical-loop/type cleanup (cli16-session-controls-02). Desktop session controls passed62/62 after repairing the omitted tuple caller (ui16-session-controls-03). Fresh CLI strict clippy03 reports only30 remote-main source spans, the inherited enclosing enum-size span and three environment hard-link messages. Fresh UI strict clippy03 reports only the inherited unused viewport helper and two environment hard-link messages. No new source lint diagnostic remains in these actual invocations. The strict commands still exit101; `cli-validation-lint-audit-03.json` and `ui-validation-lint-audit-03.json` retain every message and baseline mapping. Do not convert a clean changed-source audit into a strict check pass.

## Complete ordinary regression and actual GPU16

MEASURED/VERIFIED product16 stacked the complete299 originals in bug-3/106MSDCF
with the baseline's isolated saved warp and ordinary pyramid recipe. All pixels
in the7032x4688 photograph, float linear master and float sensor master are
bit-identical to baseline. The two float TIFF files are wholly byte-identical;
the photograph container differs while every pixel agrees. All pixels are
finite. The actual command, CLI SHA and16worker settings are in
ordinary-regression-run-16/receipt.json; comparison evidence is
ordinary-regression-readback-16.json. Elapsed148.368s and sampled3,002,474,496
private bytes were measured alongside other owned work, not an isolated speed
comparison.

The independent [actual GPU16 review](ui16-actual-gpu-review.md) verifies the
initial8x zoom fix in both independently reopened views, the Layers control,
strict completed SR15 import and its exact support/fallback values. The owned
UI process exited0. Imported result bundles do not contain original previews;
reverse parent/local source identity is covered by actual handler controls,
not an invented live-source GPU observation.

A fresh `git fetch origin main` after these checks still resolves remote main
to c149e52834fc1c86c2af0fe022713c39fa25f33c, the task's existing base.

## Post16 diagnostics and spatial independence checks

VERIFIED fresh `cargo test --locked -p strehl-core` compiled the changed core
and passed870 tests, zero failures, with four ignored tests. The actual command,
environment and native exit are in `core-full-validation-03/receipt.json`:
58.639seconds, sampled peak private1,302,540,288bytes, concurrent work. This
includes the additive registration diagnostic nonperturbation controls.

Fresh authorized native `cargo test --locked -p strehl-cli --lib session_ --
--test-threads=4` passed132/132 after the mosaic descriptor/source-role isolation
fixes, before the subsequent validation-island integration. Receipt
`cli17-session-controls-01` records45.518seconds and3,172,569,088private bytes.
Neither result validates later uncompiled edits.

Fresh strict core clippy03 still exited101 with43 diagnostics, all at source
spans unchanged from remote main. `core-validation-lint-audit-03.json` binds the
actual diagnostic messages and baseline mappings; there are no new-source
diagnostics in that invocation. Whole-crate fmt17 also fails existing formatting
differences; scoped formatting of the new registration diagnostics passed.
Do not report these strict commands as passing or erase inherited failures.

The subsequent frozen mosaic-island producer checkpoint passed fresh native
CLI session integration140/140 in `cli17-island-session-controls-01`, with an
actual Compiling rebuild, native exit0,59.674seconds and sampled peak private
3,236,868,096bytes. This predates the next additive native support wrapper and
the opt-in wider SR context controls. Release16 libraries remain unchanged.
