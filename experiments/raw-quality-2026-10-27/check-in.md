# October RAW research check-in

2026-10-28. The user requested publication of the October26/27 research and
experiments to remote main. This archives source, reports, compact receipts,
experimental CLI/core support and the corrected architecture description.
The photographic research remains paused. Rejected recipes remain rejected;
the final-CFA color pilot remains unexecuted. This check-in makes no quality
or SOTA claim and does not promote an experimental merge path to the default.

RAW inputs, decoded sensor binaries, generated images, caches, executables and
process logs remain local. Reports retain their original private-corpus/output
references; those artifacts are not bundled in the repository. Scoped ignore
rules prevent the three decoded sensor binaries from entering this commit.
Source snapshots and patch evidence retain their executed formatting, including
patch context spaces and one historical extra EOF newline reported by Git's
whitespace check, rather than silently changing their recorded byte identities.

Validation on the working tree based on main4813e46:

- `cargo test --locked -p strehl-core`:591 unit tests and one sampler integration
  test passed; four research tests ignored. STREHL_TEST_TMP pointed inside local
  outputs. The affected core crate freshly compiled.
- `cargo check --locked -p strehl-cli --all-targets --features direct-cfa-gather`:
  passed, with warnings. CLI/core compilation/checking was observed.
- `python scripts/research.py catalog`: regenerated the two navigation indexes;
  subsequent `catalog --check` passed.
- `cargo fmt -p strehl-core -- --check`: failed, including formatting differences
  in unchanged core files/examples. No broad formatting rewrite was applied.
- `cargo clippy --locked -p strehl-core --all-targets --no-deps -- -D warnings`:
  failed with43 diagnostics in the test target, including untouched existing
  modules. This is not a clean lint certification.

No private-corpus photographic campaign was rerun for this publication. The
complete299 spectral regression and independent reviews remain recorded under
native-spectral-fusion/pilot/full-results.md. The earlier experiment receipts
and explicit negative findings are retained for reproducibility and review.
