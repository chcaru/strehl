# Strehl application artwork

Three focal planes and one resolved point. The mark uses the workspace's Ayu
gold and dark ink, with a transparent outer silhouette. Small Windows frames
have a minimum one-pixel edge. UI navigation uses the related line vocabulary
in `src/workspace-icons.rs`.

The icon sources, generator and generated assets are MIT OR Apache-2.0, like
Strehl. No third-party artwork or icon font is included.

From the source root, reproduce or check the complete asset set with Python
3.9 or later. Only the standard library is used:

```powershell
python crates/strehl-ui/assets/generate-icons.py
python crates/strehl-ui/assets/generate-icons.py --check
```

`generate-icons.py` owns the vector geometry and produces `strehl.svg`, PNGs
at 16, 20, 24, 32, 40, 48, 64, 128 and 256 pixels, the multi-resolution
`strehl.ico`, and a dark/light size preview. Windows icon entries up to 48 px
use 32-bit BGRA DIBs with an AND mask; larger entries contain PNGs.

The runtime viewport loads `strehl-256.png`. The ICO's 256 px entry contains
that exact PNG. Tests check their decoded equality and native-size entries.
The Windows build script compiles the ICO as resource 1 and links it into the
executable. It finds `rc.exe` on PATH or in the Windows SDK; `STREHL_RC` can
name an explicit compiler. A failed Windows resource build is an error,
never a fallback to the generic icon. GNU Windows builds use `windres`;
non-Windows builds need no resource compiler. Python is never used by Cargo.

The same resource includes Windows version information: FileDescription and
ProductName are `Strehl`, OriginalFilename is `Strehl.exe`, the fixed numeric
version is `0.0.0.0`, and the displayed version is Cargo's package version.
No company or copyright claim is invented. The development binary and crate
remain `strehl-ui`; the distributed application is named `Strehl.exe`.

The desktop packager copies the complete `crates` tree, including these files
and `build.rs`, so the packaged source can reproduce the same icon.

After building, verify the PE contains one group-icon resource with all nine
image entries and one VERSIONINFO resource. Read the executable's FileVersionInfo
to check the product name, original filename and version, then inspect Explorer
and the running app's taskbar icon.
`icon-preview.png` is a design witness, not proof of the linked PE resource.
