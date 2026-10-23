#!/usr/bin/env python3
"""Package native Strehl releases and the corresponding source/relink kit.

Python 3.11+, standard library only. Dependency sources are copied mechanically;
only Cargo metadata and licence filenames are inspected. No dependency
implementation is read or printed. Run on the native OS after a locked build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/chcaru/strehl"
TARGETS = {
    "x86_64-pc-windows-msvc": "windows",
    "x86_64-unknown-linux-gnu": "linux",
    "x86_64-apple-darwin": "macos",
    "aarch64-apple-darwin": "macos",
}
SOURCE_PATHS = (
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "LICENSE*", ".gitattributes",
    "crates", "third-party", "experiments/native-gpu-gather/Cargo.toml", "experiments/native-gpu-gather/src",
    "scripts/release-package.py", "scripts/release-rebuild.py", "scripts/release-smoke.py",
    "scripts/test-release-package.py", "scripts/verify-hdr-avif.py",
    ".github/workflows/*.yml", "docs/development/release-workflow.md",
    "docs/desktop-build.md", "docs/raw-decoder-notice.md", "docs/public-release.md",
    "docs/development-and-hdr.md", "docs/agent-interface.md",
)
APPIMAGE_TOOL = (
    "https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage",
    "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0",
)
APPIMAGE_RUNTIME = (
    "https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64",
    "2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d",
)
RUNTIME_REVISION = "dd6cebedcbddde9c82f89b011e8e1d40b6e43868"
RUNTIME_SOURCES = [
    ("type2-runtime.tar.gz",
     f"https://codeload.github.com/AppImage/type2-runtime/tar.gz/{RUNTIME_REVISION}",
     "f5fec23be76e50e2445ed2d018bac49b367490fc483c62c4637e99ec705d27ba"),
    ("fuse-3.15.0.tar.xz",
     "https://github.com/libfuse/libfuse/releases/download/fuse-3.15.0/fuse-3.15.0.tar.xz",
     "70589cfd5e1cff7ccd6ac91c86c01be340b227285c5e200baa284e401eea2ca0"),
    ("squashfuse-0.5.2.tar.gz",
     "https://codeload.github.com/vasi/squashfuse/tar.gz/0.5.2",
     "db0238c5981dabbd80ee09ae15387f390091668ca060a7bc38047912491443d3"),
]
# The upstream runtime's licence names musl, zstd and zlib; its pinned build
# recipe also links mimalloc. Preserve these permissive component notices.
# These are licence-document versions, not a claim about undocumented binary
# component versions in the upstream prebuilt runtime.
RUNTIME_LICENSES = [
    ("musl-COPYRIGHT", "https://git.musl-libc.org/cgit/musl/plain/COPYRIGHT?h=v1.2.5",
     "f9bc4423732350eb0b3f7ed7e91d530298476f8fec0c6c427a1c04ade22655af"),
    ("zstd-LICENSE", "https://raw.githubusercontent.com/facebook/zstd/v1.5.6/LICENSE",
     "7055266497633c9025b777c78eb7235af13922117480ed5c674677adc381c9d8"),
    ("zlib-LICENSE.html", "https://zlib.net/zlib_license.html",
     "d16e1e49584a44abccebc8fc9eda5378ce0e08d25d8fb00d99f7e4c40a84e594"),
    ("mimalloc-LICENSE", "https://raw.githubusercontent.com/microsoft/mimalloc/v2.1.7/LICENSE",
     "19c99805e7a44a34b297a75d1edea9985e300066dfc024d5c99d4236d4573b5d"),
]
# Kernel, glibc and the installed graphics driver belong to the supported OS.
# All other ELF dependencies below, including libgcc_s, are copied recursively.
LINUX_SYSTEM = re.compile(
    r"^(?:linux-vdso|ld-linux|lib(?:c|m|dl|pthread|rt|resolv|util|anl)\.so)(?:[.-]|$)"
)
LINUX_DLOPEN = (
    "libX11.so.6", "libX11-xcb.so.1", "libXcursor.so.1", "libXi.so.6",
    "libXrandr.so.2", "libXinerama.so.1", "libXrender.so.1", "libXfixes.so.3",
    "libxcb.so.1", "libxkbcommon.so.0", "libxkbcommon-x11.so.0",
    "libwayland-client.so.0", "libwayland-cursor.so.0", "libwayland-egl.so.1",
    "libdecor-0.so.0", "libvulkan.so.1", "libEGL.so.1", "libGL.so.1",
    "libGLESv2.so.2",
)
WINDOWS_SYSTEM = set("""
advapi32 avrt bcrypt bcryptprimitives cfgmgr32 combase comctl32 comdlg32 crypt32 cryptbase
cryptsp d2d1 d3d11 d3d12 d3dcompiler_47 dbghelp dwmapi dwrite dxcore dxgi dxva2
gdi32 hid imm32 iphlpapi kernel32 kernelbase msimg32 mswsock ncrypt netapi32 ntdll
ole32 oleaut32 opengl32 powrprof profapi propsys psapi rpcrt4 secur32 setupapi
shell32 shcore shlwapi user32 userenv uxtheme version windowscodecs winhttp
winmm winspool ws2_32 wtsapi32
""".split())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(args, *, cwd=ROOT, env=None, timeout=1800):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                            capture_output=True, text=True, timeout=timeout)
    require(result.returncode == 0,
            f"Command failed ({result.returncode}): {args[0]}\n"
            + result.stdout[-6000:] + result.stderr[-6000:])
    return result.stdout


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def artifact(path):
    path = Path(path)
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}


def new_output(output, name):
    path = output / name
    require(not path.exists(), f"Refusing to replace release artifact: {path}")
    return path


def safe_relative(name):
    # ZIP/tar paths always use '/', including on Windows. Backslashes and drive
    # prefixes are refused instead of relying on the host's path interpretation.
    require(not name.startswith("/") and "\\" not in name and ":" not in name,
            f"Unsafe archive path: {name}")
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts,
            f"Unsafe archive path: {name}")
    return path


def unzip(archive, destination):
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            relative = safe_relative(entry.filename)
            require(not stat.S_ISLNK(entry.external_attr >> 16), "Symlink in notices ZIP")
            path = destination / relative
            require(path.resolve().is_relative_to(destination), "Archive escapes destination")
            if entry.is_dir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with source.open(entry) as stream, path.open("wb") as out:
                    shutil.copyfileobj(stream, out)


def zip_tree(root, destination):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                require(not path.is_symlink(), f"Unexpected archive symlink: {path}")
                archive.write(path, path.relative_to(root).as_posix())


def tar_tree(root, destination):
    # Source kits retain source symlinks but do not dereference them.
    with tarfile.open(destination, "w:gz", dereference=False) as archive:
        archive.add(root, arcname=root.name)


def fetch(url, destination, expected=None):
    require(url.startswith("https://"), "Release inputs require HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "Strehl-release"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)
    digest = sha256(destination)
    require(expected is None or digest == expected, f"SHA-256 mismatch: {destination.name}")
    return {"url": url, "sha256": digest, "name": destination.name}


def source_context(version):
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version), "Invalid version")
    manifest = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))
    require(manifest["workspace"]["package"]["version"] == version,
            "Requested version differs from Cargo workspace version")
    commit = run(["git", "rev-parse", "HEAD"]).strip()
    require(re.fullmatch(r"[0-9a-f]{40}", commit), "Cannot identify release source commit")
    dirty = run(["git", "status", "--porcelain", "--untracked-files=normal", "--", *SOURCE_PATHS])
    require(not dirty.strip(), "Release inputs must be committed before packaging")
    return {"schema": 1, "version": version, "source_commit": commit,
            "repository": REPOSITORY,
            "rustc": run(["rustc", "--version", "--verbose"]).strip()}


def copy_application_source(destination):
    paths = run(["git", "ls-files", "-z", "--", *SOURCE_PATHS]).split("\0")
    copied = []
    for relative in sorted(filter(None, paths)):
        source = ROOT / safe_relative(relative)
        require(source.is_file() and not source.is_symlink(),
                f"Source-kit input is missing or linked: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"path": relative, "sha256": sha256(target)})
    require((destination / "experiments/native-gpu-gather/Cargo.toml").is_file(),
            "Optional Cargo path dependency must be present in the source kit")
    manifest = tomllib.loads((destination / "Cargo.toml").read_text(encoding="utf-8"))
    for patches in manifest.get("patch", {}).values():
        for name, patch in patches.items():
            if isinstance(patch, dict) and "path" in patch:
                relative = safe_relative(patch["path"])
                require((destination / relative / "Cargo.toml").is_file(),
                        f"Patched dependency missing from source kit: {name}")
    return copied


def license_name(name):
    return re.match(r"^(?:licen[cs]e|copying|notice|copyright|patents?)(?:$|[._-])", name, re.I) is not None


def collect_notices(metadata, destination, context, application_root=ROOT):
    destination.mkdir(parents=True)
    packages = []
    for package in sorted(metadata["packages"], key=lambda item: (item["name"], item["version"])):
        directory = Path(package["manifest_path"]).parent
        source = package["source"]
        if source is None:
            # Cargo registry patches become local path dependencies. Preserve
            # their upstream notices even though ordinary workspace crates are
            # already covered by Strehl's own top-level licences.
            if not directory.resolve().is_relative_to((application_root / "third-party").resolve()):
                continue
            source = "local-patch:" + directory.relative_to(application_root).as_posix()
        name = f'{package["name"]}-{package["version"]}'
        candidates = {path for path in directory.rglob("*")
                      if path.is_file() and license_name(path.name)}
        if package.get("license_file"):
            candidates.add(directory / package["license_file"])
        require(package.get("license") or candidates, f"No licence metadata for {name}")
        copies = []
        for path in sorted(candidates):
            require(path.resolve().is_relative_to(directory.resolve()),
                    f"Licence file escapes dependency directory: {name}")
            relative = path.relative_to(directory)
            target = destination / "licenses" / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)  # Mechanical copy; never print its contents.
            copies.append(target.relative_to(destination).as_posix())
        packages.append({"name": package["name"], "version": package["version"],
                         "license": package.get("license"), "source": source,
                         "repository": package.get("repository"), "license_files": copies})
    require(any(item["name"] == "rawler" for item in packages), "RAW decoder notice missing")
    for name in ("LICENSE-MIT", "LICENSE-APACHE", "LICENSE-LGPL-2.1"):
        shutil.copyfile(ROOT / name, destination / name)
    release = f'{REPOSITORY}/releases/tag/v{context["version"]}'
    (destination / "NOTICE.md").write_text(
        "# Strehl third-party notices\n\n"
        "Strehl includes the rawler RAW decoder, licensed under GNU LGPL version 2.1. "
        "Its licence is included as LICENSE-LGPL-2.1. The other bundled Rust "
        "dependencies and their licence expressions appear in dependencies.json; "
        "verbatim licence/notice files are in licenses/.\n\n"
        "The matching source/relink kit is distributed beside every binary at:\n"
        f"{release}\n\n"
        "It contains the application source, all locked Cargo dependencies, and "
        "instructions to rebuild with a modified decoder. Modification for your "
        "own use and reverse engineering for debugging such modifications are "
        "permitted. The application's MIT OR Apache-2.0 terms remain unchanged.\n",
        encoding="utf-8")
    write_json(destination / "dependencies.json", {"source_commit": context["source_commit"],
               "version": context["version"], "packages": packages})
    return packages


REBUILD = """# Rebuild and relink Strehl

This kit contains the application sources, Cargo.lock, and mechanically vendored
sources of every locked external Cargo package. Dependency source/notice files
are unmodified. The source_commit and compiler identity are in release-source.json.

Install the exact Rust toolchain in rust-toolchain.toml, Python 3.11 or newer,
and the native platform SDK/compiler. These normal system tools are not bundled.
On Windows use the MSVC Build Tools and Windows SDK in a developer shell. On
macOS install Xcode command line tools. On Ubuntu 22.04 or newer install
build-essential, pkg-config, libx11-dev, libxi-dev, libxcursor-dev, libxrandr-dev,
libxkbcommon-dev, libxkbcommon-x11-dev and libwayland-dev.

From this directory, build entirely from the vendored crates:

    python scripts/release-rebuild.py --target x86_64-pc-windows-msvc
    python scripts/release-rebuild.py --target x86_64-unknown-linux-gnu
    python scripts/release-rebuild.py --target aarch64-apple-darwin
    python scripts/release-rebuild.py --target x86_64-apple-darwin

Choose the target for your native host; this is not a cross-compilation setup.
The result is target/<target>/release/strehl-ui[.exe]. It contains the processing
worker. No separately installed engine or Python is needed to run the result.
Windows uses a static MSVC C runtime. macOS deployment target is 11.0.

To replace a packaged application with your rebuild, rename the Windows result
to Strehl.exe. On macOS replace Strehl.app/Contents/MacOS/Strehl, then apply a
new local ad-hoc signature: `codesign --force --sign - --timestamp=none Strehl.app`.
On Linux run the original AppImage with `--appimage-extract`, replace
squashfs-root/usr/bin/Strehl, and invoke appimagetool with that AppDir and the
runtime you rebuilt or the release's pinned upstream runtime. The packaging
script records exact upstream runtime/tool versions and hashes.

To modify and relink rawler, copy vendor/rawler-<version> to modified/rawler,
make your changes in that copy, and run:

    python scripts/release-rebuild.py --target <your-target> --patch rawler=modified/rawler

Do not edit the checksum-protected vendor directory directly. The patch command
uses a local Cargo path override, permits the necessary Cargo.lock update, and
keeps network access disabled. The same mechanism works for another vendored
crate. Keep the originals if you want to compare or restore them. Any changes
you make are your rebuild, not the publisher's signed binary.

For the Linux AppImage's bundled shared libraries and runtime, download the
matching *-native-sources.tar.gz from the same release. It contains exact distro
source packages, the pinned AppImage runtime and libfuse source archives, licence
notices, and a native dependency manifest. See REBUILD-NATIVE.md inside it.
The installed OS, glibc, graphics driver, SDKs and compiler are system prerequisites.
"""


def package_source(args, stage, context):
    source = stage / "Strehl-source"
    source.mkdir()
    copied = copy_application_source(source)
    # cargo vendor only downloads/copies dependency archives; no source is
    # inspected or executed here. All platforms and optional locked crates are
    # included, not merely the build host's active dependency subset.
    configuration = run(["cargo", "vendor", "--locked", "--versioned-dirs", "vendor"],
                        cwd=source, timeout=3600)
    (source / ".cargo").mkdir()
    (source / ".cargo/config.toml").write_text(configuration, encoding="utf-8")
    metadata = json.loads(run(["cargo", "metadata", "--locked", "--offline", "--all-features",
                              "--format-version", "1"], cwd=source, timeout=3600))
    locked = tomllib.loads((source / "Cargo.lock").read_text(encoding="utf-8"))
    expected = {(p["name"], p["version"]) for p in locked["package"] if p.get("source")}
    actual = {(p["name"], p["version"]) for p in metadata["packages"] if p.get("source")}
    require(expected <= actual, "Metadata/vendor set omits a locked dependency")
    notices = stage / "notices"
    packages = collect_notices(metadata, notices, context, source)
    # Keep generated notices distinct from the checked-in third-party sources
    # on case-insensitive filesystems as well as when extracting the archive.
    shutil.copytree(notices, source / "THIRD-PARTY-NOTICES")
    (source / "REBUILD.md").write_text(REBUILD, encoding="utf-8")
    write_json(source / "release-source.json", {**context, "files": copied,
               "dependency_count": len(packages), "rebuild": "scripts/release-rebuild.py"})
    prefix = f"Strehl-{args.version}"
    kit = new_output(args.output, prefix + "-source-relink-kit.tar.gz")
    legal = new_output(args.output, prefix + "-third-party-notices.zip")
    tar_tree(source, kit)
    zip_tree(notices, legal)
    return [kit, legal], {"dependency_count": len(packages), "application_files": len(copied)}


def pe_imports(data):
    """Read normal and delay-load PE DLL names without loading the executable."""
    require(data[:2] == b"MZ", "Not a PE executable")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    require(data[pe:pe + 4] == b"PE\0\0", "Invalid PE signature")
    machine, sections = struct.unpack_from("<HH", data, pe + 4)
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    require(magic in (0x10B, 0x20B), "Unsupported PE optional header")
    directories = optional + (112 if magic == 0x20B else 96)
    image_base = struct.unpack_from("<Q" if magic == 0x20B else "<I", data,
                                   optional + (24 if magic == 0x20B else 28))[0]
    directory_count = struct.unpack_from("<I", data, directories - 4)[0]
    table = optional + optional_size
    headers_size = struct.unpack_from("<I", data, optional + 60)[0]

    def offset(rva):
        if 0 <= rva < headers_size:
            return rva
        for index in range(sections):
            at = table + 40 * index
            _, address, size, raw = struct.unpack_from("<IIII", data, at + 8)
            if address <= rva < address + size:
                return raw + rva - address
        raise RuntimeError("PE import RVA does not map to file data")

    def string(rva):
        at = offset(rva)
        end = data.find(b"\0", at, at + 512)
        require(end != -1, "Invalid PE DLL name")
        return data[at:end].decode("ascii").lower()

    names = set()
    for slot, stride, name_offset in ((1, 20, 12), (13, 32, 4)):
        if directory_count <= slot:
            continue
        rva, size = struct.unpack_from("<II", data, directories + slot * 8)
        if not rva:
            continue
        at = offset(rva)
        require(size >= stride, "Truncated PE import directory")
        for index in range(size // stride):
            row = at + index * stride
            require(row + stride <= len(data), "Truncated PE import descriptor")
            if not any(data[row:row + stride]):
                break
            name_rva = struct.unpack_from("<I", data, row + name_offset)[0]
            if slot == 13 and not (struct.unpack_from("<I", data, row)[0] & 1):
                name_rva -= image_base
            names.add(string(name_rva))
    return machine, sorted(names)


def audit_windows(binary):
    machine, imports = pe_imports(binary.read_bytes())
    require(machine == 0x8664, "Windows package must contain an x86_64 executable")
    require(imports, "PE audit did not identify any imported system libraries")
    rejected = [name for name in imports if not (
        name.removesuffix(".dll") in WINDOWS_SYSTEM
        or (name.startswith(("api-ms-win-", "ext-ms-win-")) and "crt-" not in name))]
    require(not rejected, "Non-system Windows DLL imports: " + ", ".join(rejected)
            + ". Build with -C target-feature=+crt-static; do not drop required DLLs.")
    return {"format": "PE", "machine": "x86_64", "imports": imports,
            "policy": "Windows 10+ system DLLs only; no external MSVC runtime"}


def smoke(command, context, *, env=None):
    help_text = run([*command, "--engine-worker", "--help"], env=env, timeout=60)
    require("stack" in help_text.lower() and "usage" in help_text.lower(),
            "Packaged application did not expose its bundled processing worker")
    version = run([*command, "--engine-worker", "--version"], env=env, timeout=60).strip()
    require(context["version"] in version, "Packaged worker reports the wrong version")
    require(context["source_commit"][:12] in version,
            "Packaged worker does not identify this source commit")
    return {"help": "passed", "version": version}


def make_icns(destination):
    # Reuse checked-in, reproducible PNGs; no new bitmap artist/tool dependency.
    # PNG-based ICNS entries are native macOS icon formats.
    elements = []
    for kind, size in ((b"icp4", 16), (b"icp5", 32), (b"icp6", 64),
                       (b"ic07", 128), (b"ic08", 256)):
        data = (ROOT / f"crates/strehl-ui/assets/strehl-{size}.png").read_bytes()
        elements.append(kind + struct.pack(">I", len(data) + 8) + data)
    content = b"".join(elements)
    destination.write_bytes(b"icns" + struct.pack(">I", len(content) + 8) + content)


def package_windows(args, stage, context, notices):
    executable = stage / "Strehl.exe"
    shutil.copy2(args.binary, executable)
    shutil.copytree(notices, stage / "THIRD-PARTY")
    checks = {"dependency_audit": audit_windows(executable),
              "worker_smoke": smoke([executable], context)}
    path = new_output(args.output, f"Strehl-{args.version}-{args.target}.zip")
    zip_tree(stage, path)
    return [path], checks


def package_macos(args, stage, context, notices):
    app = stage / "Strehl.app"
    contents = app / "Contents"
    executable = contents / "MacOS/Strehl"
    resources = contents / "Resources"
    executable.parent.mkdir(parents=True)
    resources.mkdir()
    shutil.copy2(args.binary, executable)
    executable.chmod(0o755)
    shutil.copytree(notices, resources / "THIRD-PARTY")
    make_icns(resources / "Strehl.icns")
    info = {"CFBundleName": "Strehl", "CFBundleDisplayName": "Strehl",
            "CFBundleIdentifier": "io.github.chcaru.strehl", "CFBundleExecutable": "Strehl",
            "CFBundlePackageType": "APPL", "CFBundleIconFile": "Strehl.icns",
            "CFBundleShortVersionString": args.version.split("-")[0],
            "CFBundleVersion": args.version.split("-")[0], "StrehlReleaseVersion": args.version,
            "LSMinimumSystemVersion": "11.0", "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.photography",
            "NSPrincipalClass": "NSApplication",
            "NSHumanReadableCopyright": "Copyright Strehl contributors. MIT OR Apache-2.0."}
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    libraries = []
    for line in run(["otool", "-L", executable]).splitlines()[1:]:
        library = line.strip().split(" (", 1)[0]
        require(library.startswith(("/System/Library/", "/usr/lib/")),
                f"Unbundled macOS dependency: {library}")
        libraries.append(library)
    require(libraries, "Mach-O audit did not identify any system libraries")
    expected = "arm64" if args.target.startswith("aarch64") else "x86_64"
    require(run(["lipo", "-archs", executable]).strip() == expected, "Mach-O architecture mismatch")
    run(["plutil", "-lint", contents / "Info.plist"])
    run(["codesign", "--force", "--sign", "-", "--timestamp=none", app])
    run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", app])
    checks = {"dependency_audit": {"format": "Mach-O", "architecture": expected,
                                  "libraries": libraries, "policy": "system frameworks only"},
              "signature": "ad-hoc; no Developer ID or Apple notarization",
              "worker_smoke": smoke([executable], context)}
    path = new_output(args.output, f"Strehl-{args.version}-{args.target}.zip")
    run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app, path])
    return [path], checks


def parse_ldd(output):
    require("not found" not in output, "Missing Linux dependency:\n" + output)
    result = {}
    for line in output.splitlines():
        found = re.match(r"\s*(\S+)\s+=>\s+(/\S+)\s+\(", line)
        if found:
            result[found[1]] = Path(found[2])
        elif re.match(r"\s*/", line):
            path = Path(line.strip().split()[0])
            result[path.name] = path
    return result


def audit_linux_resolution(executable, library_dir):
    environment = {**os.environ, "LD_LIBRARY_PATH": str(library_dir)}
    root = library_dir.resolve()
    # Check dlopen roots as well as the executable: their dependencies need not
    # appear in `ldd Strehl`, and a host library must not hide a missing bundle.
    for path in [executable, *sorted(library_dir.iterdir())]:
        resolved = parse_ldd(run(["ldd", path], env=environment))
        require(all(LINUX_SYSTEM.match(name) or library.resolve().is_relative_to(root)
                    for name, library in resolved.items()),
                f"Packaged ELF still resolves external app libraries: {path.name}")


def native_package(path):
    candidates = [path]
    if str(path).startswith("/usr/lib/"):
        candidates.append(Path(str(path).removeprefix("/usr")))
    elif str(path).startswith("/lib/"):
        candidates.append(Path("/usr" + str(path)))
    for candidate in candidates:
        result = subprocess.run(["dpkg-query", "-S", str(candidate)], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                owner, separator, _ = line.rpartition(": ")
                if separator and not owner.startswith(("diversion ", "local diversion")):
                    return owner.split(", ")[0]
    raise RuntimeError(f"Cannot identify owning distro package: {path}")


def bundle_linux_libraries(binary, appdir, native, notices):
    library_dir = appdir / "usr/lib"
    library_dir.mkdir(parents=True)
    cache = run(["ldconfig", "-p"])
    pending = [binary]
    for soname in LINUX_DLOPEN:
        found = re.search(r"^\s*" + re.escape(soname) + r"\s+\([^)]*x86-64[^)]*\)\s+=>\s+(\S+)",
                          cache, re.M)
        require(found is not None, f"Install the Linux runtime dependency {soname} before packaging")
        pending.append(Path(found[1]))
    bundled, system, owners, visited = {}, set(), set(), set()
    while pending:
        source = pending.pop()
        resolved = source.resolve()
        if resolved in visited:
            continue
        visited.add(resolved)
        deps = parse_ldd(run(["ldd", source]))
        for soname, path in deps.items():
            if LINUX_SYSTEM.match(soname):
                system.add(soname)
                continue
            destination = library_dir / soname
            if destination.exists():
                require(sha256(destination) == sha256(path), f"Conflicting ELF SONAME: {soname}")
            else:
                shutil.copyfile(path, destination)
                destination.chmod(0o755)
                bundled[soname] = {"sha256": sha256(destination), "package": native_package(path)}
                owners.add(bundled[soname]["package"])
                pending.append(path)
        if source != binary and source.name not in bundled:
            destination = library_dir / source.name
            shutil.copyfile(source, destination)
            destination.chmod(0o755)
            bundled[source.name] = {"sha256": sha256(destination), "package": native_package(source)}
            owners.add(bundled[source.name]["package"])
    # xkbcommon needs the keyboard rules/data as well as its shared library.
    xkb = Path("/usr/share/X11/xkb")
    require(xkb.is_dir(), "Install xkb-data before packaging")
    shutil.copytree(xkb, appdir / "usr/share/X11/xkb", symlinks=False)
    owners.add(native_package(xkb / "rules/evdev"))
    packages = []
    native.mkdir()
    for owner in sorted(owners):
        fields = run(["dpkg-query", "-W", "-f=${source:Package}\t${source:Version}", owner]).split("\t")
        require(len(fields) == 2 and all(fields), f"Missing distro source identity: {owner}")
        source_name, version = fields
        copyright_file = Path("/usr/share/doc") / owner.split(":")[0] / "copyright"
        require(copyright_file.is_file(), f"Missing native copyright notice: {owner}")
        target = notices / "linux" / owner.replace(":", "-")
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(copyright_file, target / "copyright")
        packages.append({"binary_package": owner, "source_package": source_name,
                         "source_version": version})
    for source_name, version in sorted({(p["source_package"], p["source_version"]) for p in packages}):
        run(["apt-get", "source", "--download-only", f"{source_name}={version}"],
            cwd=native, timeout=1800)
    shutil.copytree("/usr/share/common-licenses", notices / "linux/common-licenses")
    require(list(native.glob("*.dsc")), "No corresponding native source packages downloaded")
    return {"bundled": bundled, "system_libraries": sorted(system), "source_packages": packages}


def runtime_sources(destination, notices):
    receipt = []
    for name, url, expected in RUNTIME_SOURCES:
        archive = destination / name
        receipt.append(fetch(url, archive, expected))
        # Copy licence/notice files by archive member name, without opening any
        # implementation source. Archives themselves are preserved verbatim.
        with tarfile.open(archive) as source:
            for member in source.getmembers():
                if member.isfile() and license_name(Path(member.name).name):
                    relative = safe_relative(member.name)
                    target = notices / "appimage-runtime" / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.extractfile(member) as stream, target.open("wb") as out:
                        shutil.copyfileobj(stream, out)
    license_dir = notices / "appimage-runtime/permissive-components"
    license_dir.mkdir(parents=True, exist_ok=True)
    for name, url, expected in RUNTIME_LICENSES:
        receipt.append({**fetch(url, license_dir / name, expected), "kind": "licence document"})
    return receipt


APP_RUN = """#!/bin/sh
set -eu
APPDIR="${APPDIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
export LD_LIBRARY_PATH="$APPDIR/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export XKB_CONFIG_ROOT="$APPDIR/usr/share/X11/xkb"
exec "$APPDIR/usr/bin/Strehl" "$@"
"""


def package_linux(args, stage, context, notices):
    appdir = stage / "Strehl.AppDir"
    executable = appdir / "usr/bin/Strehl"
    executable.parent.mkdir(parents=True)
    shutil.copy2(args.binary, executable)
    executable.chmod(0o755)
    legal = appdir / "usr/share/doc/strehl/THIRD-PARTY"
    shutil.copytree(notices, legal)
    native = stage / "Strehl-native-sources"
    dependencies = bundle_linux_libraries(executable, appdir, native, legal)
    runtime_receipts = runtime_sources(native, legal)
    shutil.copytree(legal, native / "THIRD-PARTY")
    write_json(native / "native-dependencies.json", {**context, **dependencies,
               "appimage_runtime": {"revision": RUNTIME_REVISION, "sources": runtime_receipts}})
    (native / "REBUILD-NATIVE.md").write_text(
        "# Native components\n\nThe .dsc and accompanying original/debian archives "
        "are the exact source versions reported by dpkg for every bundled distro "
        "library. Extract each with `dpkg-source -x <name>.dsc`, install its build "
        "dependencies, and use its Debian build recipe (`dpkg-buildpackage`). "
        "Replace the matching .so files in the extracted AppDir's usr/lib/ before "
        "repacking; the application loads these from that directory.\n\n"
        f"The AppImage runtime is AppImage/type2-runtime at {RUNTIME_REVISION}. "
        "Its complete upstream archive, build scripts and libfuse patch accompany "
        "the unmodified libfuse 3.15.0 and squashfuse 0.5.2 source archives. "
        "Extract the runtime archive and follow its README and "
        "scripts/docker/build-with-docker.sh instructions. "
        "Its scripts/common/install-dependencies.sh names the included libfuse and "
        "squashfuse archive versions and applies the included libfuse patch. "
        "When rebuilding with local modifications, point that script's download "
        "steps at your modified source trees/archives and update its checksum "
        "checks accordingly, then use its Docker build entry point. Pass the "
        "replacement runtime using appimagetool --runtime-file. "
        "Normal compiler/OS prerequisites and upstream permissive runtime dependencies "
        "(musl, zlib, zstd, mimalloc) are described by that build recipe. "
        "The archive hashes and provenance are in native-dependencies.json.\n",
        encoding="utf-8")
    (appdir / "AppRun").write_text(APP_RUN, encoding="utf-8", newline="\n")
    (appdir / "AppRun").chmod(0o755)
    shutil.copyfile(ROOT / "crates/strehl-ui/assets/strehl-256.png", appdir / "strehl.png")
    (appdir / "strehl.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Strehl\n"
        "Comment=RAW focus stacking\nExec=Strehl\nIcon=strehl\n"
        "Terminal=false\nCategories=Graphics;Photography;\n", encoding="utf-8")
    run(["desktop-file-validate", appdir / "strehl.desktop"])
    audit_linux_resolution(executable, appdir / "usr/lib")
    tool = stage / "appimagetool.AppImage"
    runtime = stage / "runtime-x86_64"
    tool_receipt = fetch(APPIMAGE_TOOL[0], tool, APPIMAGE_TOOL[1])
    runtime_receipt = fetch(APPIMAGE_RUNTIME[0], runtime, APPIMAGE_RUNTIME[1])
    tool.chmod(0o755)
    prefix = f"Strehl-{args.version}-{args.target}"
    path = new_output(args.output, prefix + ".AppImage")
    run([tool, "--runtime-file", runtime, "--no-appstream", appdir, path],
        env={**os.environ, "APPIMAGE_EXTRACT_AND_RUN": "1", "ARCH": "x86_64",
             "VERSION": args.version}, timeout=600)
    path.chmod(0o755)
    checks = {"dependency_audit": dependencies, "appimage_tool": tool_receipt,
              "appimage_runtime": runtime_receipt,
              "worker_smoke": smoke([path, "--appimage-extract-and-run"], context)}
    sources = new_output(args.output, prefix + "-native-sources.tar.gz")
    tar_tree(native, sources)
    return [path, sources], checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("source", "windows", "macos", "linux"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--target", choices=tuple(TARGETS))
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--notices", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    context = source_context(args.version)
    if args.platform != "source":
        require(args.target and TARGETS[args.target] == args.platform, "Platform/target mismatch")
        require(args.binary and args.binary.is_file(), "Built native --binary is required")
        require(args.notices and args.notices.is_file(), "Matching source-job --notices ZIP is required")
        args.binary = args.binary.resolve()
        native = {"win32": "windows", "darwin": "macos", "linux": "linux"}.get(sys.platform)
        require(native == args.platform, "Run packaging on its native operating system")
    with tempfile.TemporaryDirectory(prefix=".strehl-release-", dir=args.output) as temp:
        stage = Path(temp)
        require(stage.resolve().is_relative_to(args.output), "Unsafe release staging directory")
        if args.platform == "source":
            paths, checks = package_source(args, stage, context)
            manifest_name = f"Strehl-{args.version}-source-manifest.json"
        else:
            notices = stage / "notice-input"
            unzip(args.notices, notices)
            source = json.loads((notices / "dependencies.json").read_text(encoding="utf-8"))
            require(source["source_commit"] == context["source_commit"]
                    and source["version"] == args.version, "Notices come from a different release source")
            payload = stage / "payload"
            payload.mkdir()
            package = {"windows": package_windows, "macos": package_macos, "linux": package_linux}[args.platform]
            paths, checks = package(args, payload, context, notices)
            manifest_name = f"Strehl-{args.version}-{args.target}-manifest.json"
        manifest = new_output(args.output, manifest_name)
        write_json(manifest, {**context, "platform": args.platform, "target": args.target,
                   "artifacts": [artifact(path) for path in paths], "checks": checks})
        print(json.dumps({"manifest": str(manifest), "artifacts": [path.name for path in paths]}))


if __name__ == "__main__":
    main()
