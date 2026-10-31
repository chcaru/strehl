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
Both failures are retained. Desktop/edit formatting now passes. Initial broad
tests passed the edit suites, but found the one density regression described
above; the repaired full-suite run is in progress at this source checkpoint.

The refreshed strict lint, final full desktop/edit tests, source-inclusive build,
packaged worker/UI smoke and output checks will be recorded here before delivery.
Local full command/resource receipts are under
`outputs/multi-stack/integration-2026-10-31/`. Prior photographic evidence and
remaining repeat/HDR/SR/mosaic outcomes remain as recorded in the handoff.
