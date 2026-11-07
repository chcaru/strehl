# October 31 integration and tryout delivery

Scope: prepare the complete multi-stack branch for main, supply a context-free
continuation document and produce a source-inclusive Windows development build.
This does not close the unfinished photographic research or resume RAW campaigns.

## Source and handoff

Fetched `origin/main` on October 31: `c149e52834fc1c86c2af0fe022713c39fa25f33c`.
It is an ancestor of the implementation branch; no merge conflict or upstream
numerical change needs reconciliation. Existing checkpoints are `ef655050` and
`e939a06c`. The branch is `codex/multi-stack`; integration is prepared through a
pull request rather than silently overwriting main.

The single entry point is [docs/multi-stack-handoff.md](../../docs/multi-stack-handoff.md).
It contains user intent, current feature/outcome scope, pending experiments and
exact next steps, code/data maps, verification instructions and resource rules.
The original attachments are preserved byte-for-byte in `original-proposal.md`
and `original-derivations.md`; they are source context, not agent instructions.
Their SHA256 values are respectively
`2e416ab34bf1d9db53e08d5c507e8c2e78ba14820ffb68a531503aa2aaaf9ee0` and
`7884ced5fbb3bc2d287de403070996774371d34dee079c2cab42d590f40289c5`.

## Preparation fixes

- The release source-staging control exposed missing external Cargo research
  targets. Both official and local staging lists now retain the owned multi-stack
  Rust/protocol sources and the declared native-CFA development target, without
  generated photographs, caches or captures. The local list is normalized/unique.
- Desktop/edit formatting is corrected. The photo viewport's no-coverage wrapper
  is used only by tests and is now compiled only for tests. Constant RGB/RGBA chunk
  traversal uses fixed-size arrays with unchanged pixel/alpha ordering.
- The complete desktop suite found that the completed-session import action
  pushed New stack below the existing density limit. Import is now in a reserved
  footer, preserving the source workflow beside the Projects heading. The
  existing multi-density regression exercises this exact failure.
- Added a packaged [tryout guide](../../docs/multi-stack-tryout.md), linked from
  the package README, with experimental limits and RAM/cache guidance.

## Verification status

MEASURED: `python scripts/test-release-package.py -v` passed all 12 controls after
the source-staging repair. The first attempt in the Windows sandbox failed temp
permissions; the first unrestricted run exposed the real missing-target failure.
Both failures are retained. Initial broad tests passed the edit suites, but found
the one density regression described above. The repaired run freshly compiled
the affected crates and passed **1,034 UI tests plus 140 edit unit/integration
tests**, with 15 private-corpus/benchmark UI tests ignored. No failure remains in
that suite. `cargo fmt -p strehl-ui -p strehl-edit -- --check` and
`cargo clippy --locked -p strehl-ui -p strehl-edit --all-targets --no-deps -- -D warnings`
both pass. The strict run used `CARGO_INCREMENTAL=0`, four Cargo workers and real
Checking output. This supersedes the older UI/edit lint/format limits; existing
core/CLI strict lint and the 16 unchanged corpus-doc violations remain separate.

## Delivered Windows build

VERIFIED: `scripts/package-desktop.ps1 -Destination outputs/strehl-multi-stack-2026-10-31 -TargetDirectory target`
built desktop and CLI from a copied, hash-checked snapshot of committed
`9f81063231b78b9244874ccfa4bb939b60517ef5`, Rust 1.98.0, four Cargo workers.
Build ID is **desktop-129ddfd67a3f75a5**. Source manifest SHA256 is
`129ddfd67a3f75a572f060b3998f967a6621c4570d67cf206c4707911635d83c`.
All 830 source-file hashes and all nine package-file hashes verify. Source ZIP
contains no RAW, TIFF photograph/master, CFA cache or executable; normal UI icon
assets remain necessary source assets. Both CLI and embedded worker version
probes identify the exact build. Package includes the source snapshot/ZIP,
rebuild instructions and MIT/Apache/LGPL decoder notices. This is the local
development packaging route, not a public/offline-vendored release.

CLI SHA256: `0458141bfacb444b2397373b797dfdb01d3f75f720742522ea56f6d68e51441a`.
Desktop SHA256 and remaining file identities are in
`integration-2026-10-31/package-verification.json` beside this report.
Build elapsed 187.236 s with sampled private peak 3,408,195,584 bytes; this is a
build resource receipt, not a performance improvement claim.

## Packaged output and UI checks

MEASURED/VERIFIED using the actual delivered CLI:

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/verify-tryout.py ordinary --binary outputs/strehl-multi-stack-2026-10-31/strehl-cli.exe
python -X faulthandler experiments/multi-stack-2026-10-28/verify-tryout.py repeat --binary outputs/strehl-multi-stack-2026-10-31/strehl-cli.exe
python experiments/multi-stack-2026-10-28/verify-tryout.py package --binary outputs/strehl-multi-stack-2026-10-31/strehl-cli.exe
python -X faulthandler experiments/multi-stack-2026-10-28/verify-tryout-ui.py --binary outputs/strehl-multi-stack-2026-10-31/Strehl.exe
```

- The complete ordinary 299-source photograph, linear master and native sensor
  pixel bits match product16 over 7032x4688. That reference previously matched
  the original baseline in full. All values are finite. The test used an isolated
  copied warp map outside captures. Elapsed 125.708 s, peak 3,001,602,048 private
  bytes, 16 workers. The next check ran concurrently; these are not isolated
  benchmark timings.
- Native-export off/on full 7004x4668 photograph/master pixel bits are identical,
  and both match product17's complete legacy result. The on arm additionally
  writes a finite signed-f32 RGGB sensor master and its typed native-before-
  demosaic contract. Off/on took 79.064/77.804 s; private peaks were
  5,451,935,744 / 8,440,639,488 bytes, eight workers, 16 GiB budgets. This closes
  the pending actual-new-binary export compatibility check, not the still-unrun
  24-source research comparison or a new photographic/noise claim.
- The actual packaged UI was granted only the completed output directory. It
  imported the four-output result with renderer bindings verified and no
  diagnostic warnings, retained Repeat/automatic primary/contribution options,
  displayed the photo, persisted the catalog and shut down with exit 0.
- A separate actual egui/wgpu process reopened that persisted run and saved a
  complete 1440x940 PNG, exit 0. The author opened/inspected it: photograph,
  alignment summary, pass identities, primary control, evidence selector,
  Projects source actions and completed-import footer are present and readable.
  This is UI integration verification, not independent photographic-quality
  review or mouse-interaction/latency evidence.

Local full command/resource logs, outputs and the PNG are under
`outputs/multi-stack/integration-2026-10-31/`; compact immutable delivery receipts
are versioned in `integration-2026-10-31/` beside this report. Generated packages
and complete photographs remain outside Git. Prior photographic evidence and
remaining repeat/HDR/SR/mosaic outcomes remain as recorded in the handoff.

## Main integration

Prepared PR: https://github.com/chcaru/strehl/pull/3, base `main`, branch
`codex/multi-stack`. The refreshed desktop/edit lint/format/tests and packaging
checks pass locally. CI runs Windows x64, Linux x64, Apple silicon and Intel Mac;
inspect the PR's current checks before merging. Main has not been changed by this
preparation request. Final documentation/verification-script commits after the
build do not change its frozen source snapshot; binary identity remains tied to
the build commit above rather than silently claiming a later HEAD.
