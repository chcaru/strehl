# Build the Strehl desktop

The release checkout pins Rust **1.98.0**. Install that toolchain through rustup.
The desktop uses the native linker, operating-system graphics libraries, and a
working graphics driver.

| Platform | Build prerequisites |
| --- | --- |
| Windows x64 | MSVC Rust host, Microsoft C++ Build Tools, and Windows SDK |
| Linux x64 | GCC/build-essential, pkg-config, libssl-dev, libx11-dev, libxi-dev, libxcursor-dev, libxrandr-dev, libxkbcommon-dev, libxkbcommon-x11-dev, libwayland-dev |
| macOS | Xcode command line tools; native Apple silicon or Intel Rust host |

On Ubuntu 22.04:

```sh
sudo apt-get install build-essential pkg-config libssl-dev libx11-dev libxi-dev \
  libxcursor-dev libxrandr-dev libxkbcommon-dev libxkbcommon-x11-dev libwayland-dev
```

From the repository root:

```sh
cargo build --locked --release -p strehl-ui --bin strehl-ui
cargo run --locked --release -p strehl-ui
```

Keep the complete checkout, including `experiments/native-gpu-gather`, which
Cargo resolves as an optional path dependency even when its feature is disabled.
The first checkout build needs network access for locked Cargo dependencies.
Python is not required to run the application.

The internal Cargo targets are `strehl-ui` (desktop) and `strehl` (CLI).
Distributed applications are named **Strehl**. The desktop includes the CLI
engine and launches an owned copy of itself with `--engine-worker`. This
preserves cancellation and process memory isolation without a second executable
or engine picker. The desktop compiles the experimental `temporal-energy` engine
feature so its **Temporal detail smoothing** toggle can control each render.
The toggle defaults to Off, including for older saved recipes. Enabling it can
remove faint detail that appears in only one capture; compare against Off.
See the [experimental mode guide](temporal-energy.md).

## Native metadata and command control

The desktop's **Camera metadata** panel reads a bracket once and presents its AF
grid, raw focus progression and optical sample curves inside Strehl. It follows
capture selection on the timeline; chart clicks select the corresponding capture.
The separate CLI's HTML export remains optional.

For scripted application control, the executable supports `--control` and a
headless workspace. The supplied `scripts/strehl-control.py` helper adds launch,
session discovery and orderly shutdown. The `--offscreen-screenshot` path can
also render the real native workspace to PNG without an operating-system window;
combine it with `--metadata` to inspect the metadata panel. Offscreen rendering
requires a working graphics backend, while ordinary headless command control
does not. See the [desktop control guide](desktop-control.md) for invocation,
source grants, separate state/output folders and the readiness limits.

## Render destination

New desktop sessions default to the user's **Pictures/Strehl** directory, using
the Windows known Pictures folder when available. The launcher's working
directory does not determine where photographs are saved. An explicit choice
under **Adjust > Destination** remains the destination for that session. If no
absolute user directory is available, choose a destination before stacking.
A failed write reports the attempted folder and how to change it; it does not
silently redirect the output.

## Official release packages

The [release workflow](development/release-workflow.md) creates Windows portable
ZIPs, Linux AppImages, and macOS application bundles. Windows uses the static MSVC
C runtime; macOS bundles are audited for non-system dependencies. Linux packages
include the selected user-space libraries, with corresponding native source
archives. Core operating-system libraries and GPU drivers remain prerequisites.

Every release includes a source/relink kit containing Strehl's application
sources, lockfile, all locked Cargo dependency sources, notices, and rebuild
instructions. All four release jobs build the shipped executable from that
delivered kit with Cargo offline. The kit records the exact source revision and
compiler identity. It does not promise byte-identical builds across different
SDKs, linkers, or hosted-runner images.

Extract the kit and choose the command for your native platform:

```sh
python scripts/release-rebuild.py --target x86_64-pc-windows-msvc
python scripts/release-rebuild.py --target x86_64-unknown-linux-gnu
python scripts/release-rebuild.py --target aarch64-apple-darwin
python scripts/release-rebuild.py --target x86_64-apple-darwin
```

To replace the LGPL RAW decoder, copy its vendored directory to a separate
editable directory and follow `REBUILD.md` in the kit. The rebuild script accepts
`--patch rawler=modified/rawler`, uses the replacement's source, and allows the
required lockfile change while keeping Cargo offline. Do not modify the original
checksum-protected vendor directory. See the [decoder notice](raw-decoder-notice.md).

Preserve the corresponding source/relink kit and license notices when
redistributing binaries. A lone statically linked executable is not a complete
redistribution package.

## Local Windows development packages

The older local helper remains available:

```powershell
./scripts/package-desktop.ps1 -Destination ./outputs/strehl-desktop
./outputs/strehl-desktop/Strehl.exe
```

It requires PowerShell 7 (`pwsh`), refuses an existing destination, and creates
a copied application source snapshot, a desktop executable, and a separate CLI.
Both binaries are built from that copied snapshot. The source manifest records
`temporal-energy` as compiled and its runtime default as Off; the snapshot also
includes the small Rust sources referenced outside `crates/` by the current
example targets and research controls. Generated research data and captures are not
included. Its local source kit fetches locked Cargo dependencies on rebuild;
unlike the official release kit, it does not vendor them. Use the official
workflow for published binaries.
