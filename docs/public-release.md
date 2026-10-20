# Public release review

This checklist records the first public preview, `v0.1.0-alpha.2`. It is an
experimental release; native build checks do not establish photographic quality
or compatibility with every desktop, GPU, or camera.

## Public history preparation

The owner authorized publication and a narrowly scoped history cleanup on
2026-10-19. The original remote history was preserved in a verified local Git
bundle before filtering. The backup stays private and is not a release asset.

The filter removed an accidentally committed build directory, seven generated
executables, and full copies of 33 third-party web pages and four manuals.
Research reports, source code, result tables, source archives, and existing
source URL/hash citation records were preserved.

Verification compared all 3,593 original commits. Each of the 3,592 retained
commit trees differs only by the approved deletions. The single pruned commit
only removed the already-filtered build directory. All 1,164 targeted historical
paths and their 1,033 object IDs are absent from every retained ref.

Commit IDs changed. Historical reports can still contain original IDs; the
[commit map](public-history-commit-map.txt) maps them to the public history.
A zero replacement identifies the one pruned cleanup commit.

An earlier conventional credential-pattern scan examined 41,275 text blobs.
The additional archive review examined all 2,925 members of 16 reachable ZIP
archives and found no matching private-key, token, API-key, or credential
assignment patterns. The captured public vendor-page browser key identified in
the earlier review was removed with that full snapshot. These bounded checks
are evidence of the work performed, not a guarantee that arbitrary historical
data contains no sensitive information.

Historical reports retain machine paths, references to private photographic
corpora, and superseded research claims. Those datasets are not included.

## Release gates

- Build from committed sources with a pinned Rust toolchain.
- Supply the matching application and dependency sources, notices, and a
  working offline rebuild/relink recipe.
- Build and test the delivered kit on Windows x64, Linux x64, macOS Apple
  silicon, and macOS Intel.
- Audit native dependencies and run the packaged embedded engine.
- Check Windows executable resources, macOS bundle metadata/signature, and
  Linux runtime/native-library source coverage.
- Reject missing, extra, empty, or incorrectly identified release assets.
- Sign checksums and verify the exact workflow/tag identity and build provenance.
- Review genuine application recordings and document diagnostic limitations.
- Enable a private vulnerability-reporting route.
- Publish the draft only after reviewing its assets and verification results.

The [release workflow guide](development/release-workflow.md) records the
commands, platform assumptions, signing scope, and maintenance procedure.
Windows Authenticode and Apple Developer ID/notarization are not enabled for
this preview; the owner selected signed checksums and build provenance.

Future publication changes should repeat the relevant checks. Do not treat an
old passing result as evidence for a modified binary, source kit, or workflow.
