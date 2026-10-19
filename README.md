# Strehl

Noise-aware RAW focus stacking in Rust, with a desktop workspace and command-line engine.

Strehl aligns a focus bracket, combines detail across its frames, and writes a
16-bit RGB TIFF. The desktop adds source browsing, saved projects and visual
inspection of the processing stages. The normal merge runs on the CPU; the GPU
displays the workspace.

**Status: experimental software.** Windows is the exercised desktop platform.
The current import paths accept Sony `.ARW` files; the decoder's broader format
support does not mean other formats are supported by this application. Image
quality varies with capture, alignment and scene content. Inspect complete
results and native-resolution detail before relying on an output. There is no
claim of universal artifact removal or superiority to other stackers.

## Build and open the desktop

Requirements for the Windows build:

- Rust and Cargo **1.98 or newer**, with the MSVC host toolchain. The checkout's
  `rust-toolchain.toml` selects stable; it does not pin a particular release.
- Microsoft C++ build tools and a Windows SDK for linking.
- PowerShell 7 (`pwsh`) for the packaging and rebuild scripts.
- A graphics driver supported by wgpu, enough free disk space for the build and
  render outputs, and RAM appropriate to the capture size and worker count.
- Network access for the first download of the dependencies in `Cargo.lock`.

From the repository root:

```powershell
./scripts/package-desktop.ps1 -Destination ./outputs/strehl-desktop
./outputs/strehl-desktop/Strehl.exe
```

The package contains **Strehl.exe**, its rebuildable source kit, and a separate
`strehl-cli.exe` for scripts. The desktop includes its engine; a second
executable is not required to stack. For development, `cargo run -p strehl-ui`
opens the same application. In
**Projects**, open a folder containing one focus bracket. Files are ordered by
filename, and subdirectories are not combined. Choose an output destination,
adjust the recipe if needed, and select **Stack**. Source files stay in place;
projects store references to them. Start with a small bracket and reduce the
worker limit if memory is constrained.

[Desktop controls](crates/strehl-ui/README.md) ·
[Build and redistribution guide](docs/desktop-build.md)

Linux and macOS desktop builds are not release-validated here. This repository
does not yet provide a tested installation recipe for those platforms.

## Run the command-line engine

```powershell
cargo build --locked --release -p strehl-cli --bin strehl
./target/release/strehl.exe probe "path/to/capture-folder" --limit 3
./target/release/strehl.exe stack "path/to/capture-folder" --merge pyramid --srgb --out "result.tiff"
./target/release/strehl.exe stack --help
```

`--merge pyramid` is the normal backend. The command above uses its current
compiled defaults; historical research recipes can use different settings.
`--srgb` produces a viewing TIFF with full-resolution demosaicing by default.
Add `--binned` for half the linear dimensions, or `--auto-exposure` for the
engine's automatic viewing exposure. Without `--srgb`, the default is linear,
binned, camera-native RGB, which can look dark in an ordinary image viewer.
Always supply `--out` when you want an image file.

The alternate `--merge estimator` backend and experiment features are research
paths. Their flags and results are not interchangeable with the normal pyramid
workflow. The pinned native/GPU research runner also requires separate build
receipts and is not the desktop's default engine path.

## Inspect the result

On a finished stack, the timeline can compare sources beside the final photo.
Shift selects a capture range; Ctrl adds another. Each range keeps a colored
estimated admission region, with mixed stripes where regions overlap. Holding
Space temporarily hides overlays; Escape clears the selection.

Admission marks show where recorded samples passed a gate. They are not blend
weights, a sharpness score, or exact per-pixel ownership. Region boundaries
estimate the space between sparse observations. Source-photo overlays are
explicitly approximate because camera previews are not registered final images.
The saved TIFF contains the photograph, not these inspection overlays.

## Development and research

The workspace contains `strehl-core`, `strehl-raw`, `strehl-plugin`, `strehl-cli`
and `strehl-ui`. Normal builds need the complete checkout: Cargo also resolves
the optional library at `experiments/native-gpu-gather`, even when its feature
is disabled. Python tools and private photographic corpora are not required to
launch the desktop or run the normal CLI.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change, especially the
project's source-license and measurement rules. The research decision record is
[docs/research/SYNTHESIS.md](docs/research/SYNTHESIS.md). Reports may describe older
builds, unavailable local data, rejected experiments or superseded results.
The [previous research README](docs/archive/readme-research-2026-10-18.md) is
preserved with its corrections and historical claims.

[Security reporting](SECURITY.md) · [Public-release checklist](docs/public-release.md)

## License and binary distribution

Strehl's own code is available under [MIT](LICENSE-MIT) or
[Apache-2.0](LICENSE-APACHE), at your option. The linked RAW decoder, `rawler`,
is LGPL-2.1; see the [decoder notice](docs/raw-decoder-notice.md) and
[license text](LICENSE-LGPL-2.1).

Use the source-inclusive packaging workflow in the build guide when sharing
binaries. Keep the corresponding application sources, lockfile, build recipe
and notices with the executables, and verify that recipients can obtain the
corresponding decoder source and rebuild with a modified decoder. Do not
redistribute a lone statically linked executable.
