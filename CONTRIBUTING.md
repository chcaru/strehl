# Contributing to Strehl

Strehl is an experimental focus stacker. Small, reproducible fixes to the normal
CLI and desktop paths are welcome. Keep research experiments separate from
changes intended for normal use.

Before working on the code, read [AGENTS.md](AGENTS.md). Read the
[research decision record](docs/research/SYNTHESIS.md) before changing the
architecture. These documents include source-license restrictions: do not copy
or consult the prohibited GPL implementations or the `rawler`/`dnglab` source
when implementing Strehl. The linked decoder is a dependency, not a source for
Strehl's implementation.

## Build and check a change

Use the prerequisites and build commands in [README.md](README.md). Keep
`Cargo.lock` in version control. Normal desktop builds do not enable experimental
engine features.

Run checks appropriate to the files you change. For desktop work, useful checks
include:

```powershell
cargo test --locked -p strehl-ui
cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-ui -- --check
```

Engine changes also need focused tests in the affected crates. Record the exact
commands, toolchain and outcomes in the pull request; do not describe an
unrun command as passing. After edits or restored files, confirm the output
shows the affected crate being rebuilt. Ignored corpus tests and benchmarks
need their documented external inputs and are not covered by an ordinary
successful test run.

Some older experimental CLI tests also require private manifests or explicit
output-directory environment variables without being marked ignored. A blanket
workspace test run can fail on these in a clean checkout. Report those failures
separately; do not substitute them for focused tests of the changed normal path
or silently skip them in a claim that the whole workspace passed.

For a visual change, exercise the actual desktop with a representative stack
and inspect the affected window sizes and interactions. Unit tests of UI state
do not establish GPU rendering quality or responsiveness.

## Describe the evidence

A useful bug report or pull request includes the build identity, operating
system, reproduction steps, expected behavior and actual result. Include a
small fixture you have permission to share when possible. Remove personal paths,
camera serials, location metadata and other private information from attachments.
Do not upload someone else's RAW files or a private corpus.

Quality and performance claims need a command that was run. Distinguish
measured, verified, derived, argued and unverified conclusions. A sharpness
comparison needs a flat-region noise control, and independent review should
reconsider the chosen inputs and controls rather than only repeat arithmetic.
View complete outputs before choosing native-resolution inspection regions.
Keep failed experiments and retractions visible in the research record.

Commit source, tests, documentation and intentional compact result receipts.
Keep executables, RAW inputs, caches, local settings and generated release
packages out of Git. Put reusable reproduction scripts in `scripts/` or
`experiments/`, not the ignored `outputs/` directory. Do not rewrite unrelated
research records or reformat the whole repository for a local fix.

See [SECURITY.md](SECURITY.md) for security-sensitive reports and
[the release checklist](docs/public-release.md) before distributing a build.
