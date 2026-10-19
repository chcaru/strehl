# Desktop engine and rebuild kit

The supported packaging workflow is Windows with Rust/Cargo 1.98 or newer,
the MSVC host toolchain, Microsoft C++ build tools, a Windows SDK, and
PowerShell 7 (`pwsh`). The checkout selects the stable Rust channel; a generated
source kit records the exact compiler used for that package. Linux and macOS
desktop builds have not received the same release validation.

For a normal checkout build, run from the repository root:

```powershell
cargo build --locked --release -p strehl-ui
./target/release/strehl-ui.exe
```

Keep the complete checkout, including `experiments/native-gpu-gather`: Cargo
resolves that optional path dependency even when its feature is disabled.
Python is not required for the normal desktop build. The first build needs
network access to fetch the locked Cargo dependencies.

The packaged **Strehl.exe** carries the same command-line engine as the separate
**strehl-cli.exe**. Cargo's development targets retain the internal names
`strehl-ui` and `strehl`; the package gives the desktop its product name. Stack jobs
launch an isolated copy of the desktop executable with `--engine-worker`. The
child enters the CLI before starting any window or GUI worker. This keeps render
cancellation, log capture and process memory isolation. No engine picker or
second executable is required to use the desktop. The standalone CLI remains
available for scripts.

The package includes the exact owned source snapshot, its `Cargo.lock`, a
per-file SHA-256 manifest, the compiler identity, both project licences, and a
rebuild script. It also includes `RAW-DECODER-NOTICE.md` and the decoder's LGPL
license text. Keep `source/` or `strehl-source.zip` and these notices with
distributed binaries.
The RAW decoder is the locked `rawler` crate (LGPL-2.1); Cargo obtains its
published crate normally. Its source is not incorporated into Strehl's own
source tree. This source kit lets recipients rebuild and relink the desktop and
CLI, including with a modified decoder. The project does not permit shipping
only a statically linked binary.
The kit is not an offline dependency bundle. Before redistribution, verify
availability of the corresponding decoder source and the complete relinking
materials; see [the release checklist](public-release.md).

On Windows, install the Rust version and host listed in
`source/desktop-source.json`, plus the Microsoft C++ build tools. From the
package directory, select that installed version and run:

```powershell
$manifest = Get-Content ./source/desktop-source.json -Raw | ConvertFrom-Json
$env:RUSTUP_TOOLCHAIN = $manifest.toolchain
& ./source/scripts/rebuild-desktop.ps1
```

The script first checks that the compiler and owned sources match the recorded
snapshot, then uses the lockfile and recorded build stamp. Cargo may download
the dependencies pinned in `Cargo.lock`. Output is in
`source/target-desktop/release/`. The default build enables no experimental
engine features. This kit covers that desktop build; the repository's separate
research experiments and their external data are not part of it.
The script temporarily clears caller-supplied Rust flags and release-profile
environment overrides so they cannot silently change this recipe.

To rebuild modified sources or replace a dependency, make your changes and run
`cargo build --release -p strehl-cli --bin strehl -p strehl-ui --bin strehl-ui`
directly from `source/`, allowing Cargo to update the lockfile if you changed a
dependency. The script's initial hash check deliberately detects modifications.
Choose a new `STREHL_BUILD_ID`
for that build so its TIFF provenance distinguishes it from the supplied kit.

For example, to use a separately obtained, modified `rawler` checkout with a
compatible package version, add this to the source kit's root `Cargo.toml`:

```toml
[patch.crates-io]
rawler = { path = "../rawler-modified" }
```

Then run the direct build command above from `source/` and retain its updated
lockfile. This is a modified build, so the original source-manifest verification
script is expected to reject it. Changing the decoder does not require modifying
or reverse-engineering a supplied executable.

To create a new release package from a checkout:

```powershell
& ./scripts/package-desktop.ps1 -Destination ./outputs/strehl-desktop-release
```

The packager refuses an existing destination. It builds from the copied source
snapshot and records hashes of the resulting UI, standalone CLI and source ZIP.
Compiler/linker metadata can affect executable bytes across machines; the
manifest is a source and build recipe, not a promise of identical PE hashes on
different Windows toolchains.
