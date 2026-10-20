# Desktop CI and releases

[Desktop CI](../../.github/workflows/ci.yml) tests the desktop crate on pull requests,
branch pushes and manual runs. It checks the generated icons and packaging controls,
runs the self-contained UI tests, builds the native executable, and starts its
embedded engine in help mode without opening a window. Linux also checks desktop
formatting and Clippy. Private RAW benchmarks stay ignored; this workflow does not
claim to run the full photographic corpus or test GPU presentation.
UI tests run with two test threads so concurrent fixtures do not oversubscribe
their decoder pools; the app's production worker count is unchanged.

[Draft desktop release](../../.github/workflows/release.yml) runs on a pushed `v*`
tag, or a manual run explicitly targeting that tag. It requires a public repository,
a tag matching the Cargo workspace version, and an exact Rust version in
`rust-toolchain.toml`. A branch dispatch fails before packaging.

## Native builds

| Package | GitHub runner | Rust target |
| --- | --- | --- |
| Windows x64 ZIP | `windows-2025` | `x86_64-pc-windows-msvc` |
| Linux x64 AppImage | `ubuntu-22.04` | `x86_64-unknown-linux-gnu` |
| macOS Apple silicon ZIP | `macos-15` | `aarch64-apple-darwin` |
| macOS Intel ZIP | `macos-15-intel` | `x86_64-apple-darwin` |

Windows builds use the static C runtime. Both macOS builds set the deployment
target to 11.0. The Linux package bundles its selected userspace dependencies and
includes their matching source archives; it still depends on a compatible Linux
system and graphics driver. A runner build and headless engine check do not prove
compatibility with every supported desktop or GPU.

The package script first creates one source/relink kit containing the locked Cargo
dependencies, licenses and rebuild instructions. It also creates the dependency
notices used by the four native package jobs. Each native job verifies and extracts
that delivered kit, runs its UI tests with Cargo offline, and builds the shipped
executable using the kit's rebuild script and vendored dependencies. It then checks
the packaged engine and dynamic dependencies. The original checkout supplies the
packaging script and Git identity; the executable comes from the extracted kit.
The Linux job enables matching Ubuntu source repositories so unavailable native
library sources stop the release.

Each packaged app must also open a native window, display a generated image and
save its own rendered screenshot before its release artifact is uploaded. The
check decodes that screenshot and requires all four image colors in their expected
quadrants. Linux uses Xvfb and Mesa's software Vulkan renderer for this check;
macOS and Windows use their runner's native graphics backend. This exercises
window creation and preview rendering, not RAW stacking or every graphics driver.
Screenshots, logs and a receipt are saved as separate `smoke-*` Actions artifacts
even when the check fails; they are excluded from the release payloads.

The final job requires all four native jobs and the source job to succeed. It
rejects missing, extra, duplicate or empty assets, checks each manifest against
the tag's source commit, and verifies every package size and SHA-256 digest. The
expected twelve payloads are four app packages, five build manifests, the Cargo
source/relink kit, dependency notices and Linux native-library sources.

## Signatures and verification

The final job generates `SHA256SUMS`, signs it with keyless
[Sigstore Cosign](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/), and
attests the twelve payloads plus the checksum manifest using
[GitHub artifact attestations](https://github.com/actions/attest). Signing uses the
short-lived GitHub Actions identity; no long-lived signing secret is configured.
The workflow verifies the signatures, exact workflow/tag identity, source commit
and all checksums before creating a **draft prerelease**.

The release additionally contains `SHA256SUMS.sigstore.json` and
`release-provenance.sigstore.json`. These authenticate the release workflow and
artifact bytes. They are not a Windows Authenticode signature, an Apple Developer
ID signature or Apple notarization. Operating-system publisher checks can still
appear. Signature verification does not establish photographic quality or prove
that the source is free of defects.

Download the app package, `SHA256SUMS`, and both `.sigstore.json` files from the same
release. With Cosign 3.1.3 or newer and a current GitHub CLI, replace the tag and package below
with the release you downloaded:

```sh
tag=v0.1.0-alpha.4
package=Strehl-0.1.0-alpha.4-x86_64-unknown-linux-gnu.AppImage
identity="https://github.com/chcaru/strehl/.github/workflows/release.yml@refs/tags/$tag"
cosign verify-blob --bundle SHA256SUMS.sigstore.json \
  --certificate-identity "$identity" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com SHA256SUMS
gh attestation verify "$package" --repo chcaru/strehl \
  --bundle release-provenance.sigstore.json --cert-identity "$identity" \
  --source-ref "refs/tags/$tag" --deny-self-hosted-runners
```

Then compare the package's SHA-256 with its line in the authenticated checksum
file: use `sha256sum "$package"` on Linux, `shasum -a 256 "$package"` on macOS,
or `Get-FileHash -Algorithm SHA256 <package>` in PowerShell. When all twelve
payloads are downloaded, `sha256sum --check SHA256SUMS` verifies the complete set.
For a separately reviewed source commit, also pass `--source-digest <full-sha>`
to `gh attestation verify`. The [GitHub CLI reference](https://cli.github.com/manual/gh_attestation_verify)
describes these policy checks.
The Cosign minimum includes the fix for a
[legacy-bundle identity verification bypass](https://github.com/sigstore/cosign/security/advisories/GHSA-fx35-mq7g-6g98).

## Maintainer release procedure

1. Review CI, update the Cargo workspace version and lockfile, and commit the
   intended release sources. Keep the toolchain pinned to an exact release.
2. Push a matching tag, for example `v0.1.0-alpha.4`. Repository visibility must
   already be public so attestations use the public Sigstore service.
3. Wait for every release job to pass. Download all fifteen assets from the draft:
   twelve payloads, checksums and two signature/provenance bundles.
4. Verify signatures, checksums, source identities and package contents. Test the
   actual app on each platform, including opening a stack and running the embedded
   engine. Build logs alone do not establish those interactions.
5. Publish the reviewed draft manually. The workflow never publishes it and never
   overwrites an existing release. A failed upload may leave an incomplete draft;
   inspect it before deleting that draft and rerunning the release job.

Action artifacts are retained for fourteen days; the release assets are the
long-term distribution. Release runs for the same ref are serialized and are not
cancelled automatically. Pull-request jobs have read-only repository permission
and cannot sign or create releases. Checkout does not persist credentials.

## Updating workflow dependencies

All actions are pinned to full commit SHAs. The initial pins were resolved from
the official repositories' release tags using `gh api repos/OWNER/REPO/commits/TAG`:
checkout 7.0.1, setup-python 7.0.0, upload-artifact 7.0.2, download-artifact 8.0.2,
attest 4.2.2 and cosign-installer 4.1.2. Cosign itself is pinned to 3.1.3; its
installer verifies the downloaded binary. Update both the SHA and version comment
when reviewing an action upgrade, and check its inputs and runner requirements.

Runner labels follow the [official hosted-runner inventory](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Pinned action code and Rust versions do not pin the complete hosted runner image,
Ubuntu package repository, Python patch release or system SDK. The rebuild kit
supports source inspection and relinking; bit-for-bit reproducibility across
machines is not claimed.
