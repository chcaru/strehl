# Public-release preparation

This checklist records preparation work. It does not authorize changing
repository visibility, publishing a release, uploading a package or rewriting
history. A private push and a public release are separate actions.

The repository currently includes a substantial research history, compact
result artifacts and archived source packages. Historical reports contain
machine-specific paths, private-corpus references and superseded claims.
The working-tree ignore rules do not remove files already tracked or erase
historical binaries. A source checkout can therefore remain large even after
generated files are excluded from new commits. Preserve this evidence unless
the owner explicitly approves a separate history-cleanup plan.

## Before making the repository public

- Review both the proposed tree and reachable Git history for credentials,
  private data, personal identifiers and material without redistribution rights.
  A filename scan alone is not a secret audit. Rotate any exposed credential;
  removing its latest copy is insufficient.
- Confirm the README commands work from a clean checkout without local build
  bindings, private corpora or environment overrides. Record the exact revision,
  Rust compiler, platform, commands and failures. Check the documentation links.
- Confirm every workspace member, lockfile entry and optional path dependency
  needed by Cargo is present. The normal build currently resolves
  `experiments/native-gpu-gather` even with that feature disabled.
- State which platforms and camera inputs were actually exercised. Windows and
  Sony ARW are the current documented desktop scope; do not infer support from
  the decoder or graphics backend alone.
- Review source ownership, project license texts and dependency notices. Keep
  the project's prohibited-source rules in [AGENTS.md](../AGENTS.md).
- Enable and test a private vulnerability-reporting route, then update
  [SECURITY.md](../SECURITY.md) if a more specific contact is available.
- Review the retained research history's size and local-path disclosures with
  the owner. A public README cleanup is not a certification that every old
  report or historical artifact is suitable for public distribution.

## Before distributing a binary

- Choose a release identifier and supported platform explicitly. Workspace
  package metadata is currently `0.0.0`; a local build/package label does not
  establish a public versioning or support policy.
- Run the relevant automated checks and inspect complete photographic outputs,
  native-resolution regions and the actual GPU interface. Record limitations
  rather than converting old benchmark or quality claims into current ones.
- Build from the exact source snapshot being supplied. Use
  [the desktop packaging workflow](desktop-build.md), which refuses an existing
  destination and records source, compiler and package hashes.
- Include the corresponding application source, lockfile, rebuild recipe,
  project licenses, [decoder notice](raw-decoder-notice.md) and LGPL text.
  Verify that recipients can obtain the exact corresponding decoder source and
  rebuild/relink with a modified decoder. The current kit fetches dependencies
  from Cargo registries; it is not an offline dependency bundle. Do not ship
  only a statically linked executable or assume a successful build alone proves
  redistribution obligations have been met.
- Rebuild the supplied kit on a separate clean environment, verify its receipt
  and test launch, one render, cancellation and saved-result reopening. Exact
  executable bytes across different linker environments are not promised.
- Review package contents for local paths, logs, caches, private images and
  debug artifacts. Keep generated packages under ignored `outputs/`.
- Obtain the owner's explicit public-publication decision before changing
  visibility, creating a public release or uploading its assets.

Mark these items with concrete evidence in the release review; an unchecked
list or an old passing run is not a completed release gate.

## Preparation audit, 2026-10-18

A conventional credential-pattern scan of reachable local history examined
41,275 text blobs (14,695 binary blobs were outside its scope). It found two
occurrences of one Google Maps browser key in the captured public Canva page
`experiments/M132-blocker-d-routes/canva-affinity-free.html`, Git blob
`b7b7c504b656cd619b739997ae2a3f01e1450a97`. The snapshot matches its recorded
public-page URL and manifest hash; its frontend configuration states that the
visitor is logged out. This is a narrow third-party snapshot finding, not a
Strehl account credential. The key was not tested; its restrictions and validity
are unknown. Keep future scans enabled for this pattern and review changed
content independently. This scan does not certify all historical content as
safe or licensed for public distribution.
