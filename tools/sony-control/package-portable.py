#!/usr/bin/env python3
"""Package the existing Sony helper for a Windows x64 laptop; no camera commands."""
# SPDX-License-Identifier: MIT OR Apache-2.0
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
PYTHON_URL = "https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip"
PYTHON_SHA = "9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(archive, destination):
    for info in archive.infolist():
        name = PurePosixPath(info.filename.replace("\\", "/"))
        if name.is_absolute() or ".." in name.parts or ":" in str(name):
            raise ValueError("Unsafe archive member")
        if not info.is_dir():
            path = destination.joinpath(*name.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(archive.read(info))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New staging directory; sibling ZIP is also created")
    parser.add_argument("--sdk", type=Path, default=Path.home() / "Downloads/CrSDK_v2.02.00_20260610a_Win64.zip")
    parser.add_argument("--python-zip", type=Path, default=ROOT / "outputs/sony-control/package-cache/python-3.13.17-embed-amd64.zip")
    parser.add_argument("--vs", type=Path, default=Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"))
    args = parser.parse_args()
    out = args.out.resolve()
    archive_path = out.with_suffix(".zip")
    if out.exists() or archive_path.exists():
        raise ValueError("Choose a fresh staging/package path; existing packages are not overwritten")
    if digest(args.python_zip) != PYTHON_SHA:
        raise ValueError("Embedded Python does not match the official release SHA-256")
    receipt = json.loads((ROOT / "outputs/sony-control/build-receipt.json").read_text(encoding="utf-8"))
    native = ROOT / "outputs/sony-control/bin/strehl-sony-control.exe"
    if digest(native) != receipt["executableSha256"].lower():
        raise ValueError("Native executable does not match build receipt")
    if digest(ROOT / "tools/sony-control/strehl-sony-control.cpp") != receipt["sourceSha256"].lower():
        raise ValueError("Native source changed after the recorded build; rebuild before packaging")
    for name in ("strehl-sony-control.cpp", "card-capture.h", "CMakeLists.txt"):
        if digest(ROOT / "tools/sony-control" / name) != receipt.get("sourceFilesSha256", {}).get(name, "").lower():
            raise ValueError(f"Native build input changed or is unrecorded: {name}; rebuild before packaging")
    if digest(args.sdk) != receipt["sdk"]["sha256"]:
        raise ValueError("Sony SDK archive differs from the one used for the build")
    out.mkdir(parents=True)

    def copy(source, relative):
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for name in ("sony-control.py", "strehl-sony-control.cpp", "card-capture.h", "test-sony-control.py",
                 "portable-launch.py", "package-portable.py", "prepare-sdk.py",
                 "CMakeLists.txt", "build.ps1", "README.md"):
        copy(ROOT / "tools/sony-control" / name, Path("tools/sony-control") / name)
    for path in (ROOT / "outputs/sony-control/bin").rglob("*"):
        if path.is_file() and path.suffix.lower() in (".dll", ".exe", ".md"):
            copy(path, Path("outputs/sony-control/bin") / path.relative_to(ROOT / "outputs/sony-control/bin"))
    # Application-local VC runtime: no machine-wide installer is run.
    redist = args.vs / "VC/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT"
    for name in ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
        copy(redist / name, Path("outputs/sony-control/bin") / name)
    for name in ("Redist.txt", "ThirdPartyNotices.txt"):
        copy(args.vs / "Licenses/1033" / name, Path("third-party/microsoft") / name)
    with ZipFile(args.python_zip) as archive:
        extract(archive, out / "runtime/python")
    with ZipFile(args.sdk) as sdk:
        with ZipFile(io.BytesIO(sdk.read("Driver.zip"))) as driver:
            extract(driver, out / "drivers/sony-usb")
        (out / "drivers/sony-sdk-readme.pdf").write_bytes(sdk.read("Camera_Remote_SDK_Readme_v2.02.00.pdf"))
        (out / "drivers/sony-remote-sample-app-manual.pdf").write_bytes(sdk.read("RemoteSampleApp_IM_v2.02.00.pdf"))
        sources = out / "third-party/sources"
        sources.mkdir(parents=True, exist_ok=True)
        (sources / "libusb.zip").write_bytes(sdk.read("SourceCodeOfOpenSourceSoftware/libusb.zip"))
    for name in ("LICENSE-MIT", "LICENSE-APACHE", "LICENSE-LGPL-2.1"):
        copy(ROOT / name, name)
    for name in ("brief.md", "results.md", "sdk-audit.md"):
        copy(ROOT / "experiments/sony-focus-control-2026-11-07" / name,
             Path("experiments/sony-focus-control-2026-11-07") / name)
    receipt["sdk"]["archive"] = args.sdk.name
    (out / "outputs/sony-control/build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    guide = (ROOT / "tools/sony-control/README.md").read_text(encoding="utf-8")
    guide = guide.replace("Set-Location 'C:\\dev\\blog\\death-of-software\\projects\\strehl'", "# Open PowerShell in this extracted folder.")
    guide = guide.replace("python tools/sony-control/sony-control.py", ".\\sony-control.cmd")
    guide = guide.replace("../../experiments/", "experiments/")
    (out / "focus-test-guide.md").write_text(guide, encoding="utf-8")
    launchers = {"01-check-camera.cmd": ("check", True), "02-run-focus-test.cmd": ("test", True),
                 "03-offline-check.cmd": ("offline", True), "sony-control.cmd": ("cli", False)}
    for filename, (mode, pause) in launchers.items():
        text = ('@echo off\nsetlocal\n'
                '"%~dp0runtime\\python\\python.exe" -I -X utf8 -u "%~dp0tools\\sony-control\\portable-launch.py" '
                + mode + ' %*\nset "STREHL_EXIT=%ERRORLEVEL%"\necho.\n')
        if pause:
            text += 'if not defined STREHL_NO_PAUSE pause\n'
        text += 'exit /b %STREHL_EXIT%\n'
        (out / filename).write_bytes(text.replace("\n", "\r\n").encode("ascii"))
    (out / "start-here.txt").write_text("""STREHL SONY A7C II FOCUS TEST - SD CARD ONLY - WINDOWS x64 PORTABLE

PHOTOS STAY ON THE SD CARD. The laptop writes command/settings logs only.
Use this package instead of the earlier PC+card package. There is no host-save
option, automatic photo download, preview download or review-image copy.

1. Right-click the ZIP and choose Extract All. Use a writable folder on your
   laptop (for example Documents). Run from the extracted folder, not inside ZIP.
2. Connect the a7C II by USB data cable. Choose Remote Shoot (PC Remote) on the
   camera. Close Imaging Edge Remote and disconnect phone remote control.
3. Windows USB setup: in Device Manager, the camera must appear under
   libusbK Usb Devices as Sony Remote Control Camera. If it appears under Portable
   Devices, open drivers/sony-usb, right-click srcameradriver.inf and choose Install.
   Complete Sony's installation prompts (administrator access required), reconnect
   the camera, and check Device Manager again. Sony's illustrated instructions are
   in drivers/sony-remote-sample-app-manual.pdf, pages 9-11. Installation is manual.
4. Double-click 01-check-camera.cmd. It checks the connection without shooting.
5. Prepare the inclined textured target described in focus-test-guide.md. Use MF,
   manual exposure, fixed ISO and your normal macro rig. Leave room for at least
   73 RAWs on the SD card. Note the first/last image filename or create a new
   camera folder for this test. Do not take unrelated pictures during the run.
6. When ready, double-click 02-run-focus-test.cmd. THIS MOVES FOCUS AND TAKES
   73 RAW PHOTOGRAPHS TO THE SD CARD. Ctrl+C once stops future shots after the
   active operation. The camera keeps its normal image naming/folder behavior.

Logs are in the logs folder beside these launchers. Each run gets a new dated
folder with manifest.json, events.jsonl and diagnostics. Check restoration in
manifest.json. SD-card-only saving is retained when the program exits.

Completion uses camera capture events and card-writing/bracket status. The helper
does not open or checksum the SD files. After the run, verify that the camera
saved 73 RAWs. If it times out, inspect the camera/card before retrying; it will
not resend an uncertain shutter command. Logs retain the unfinished capture.

For later image analysis, manually copy the test RAWs when you choose, preserving
filenames and camera folder structure. Keep the matching log folder with them.
The manifest maps each test phase to its expected image order (1 through 73).

Python, the Sony SDK runtime and the needed VC runtime DLLs are included.
No Python installation, compiler, Git checkout, administrator access or internet
is needed after USB driver setup. Driver installation requires administrator
access and is not performed automatically. File Explorer visibility alone does
not mean that the SDK USB driver is installed; follow step 3 above.

03-offline-check.cmd runs software tests without connecting to a camera.
For command-line options, open PowerShell here and run:
  .\\sony-control.cmd --help
  .\\sony-control.cmd plan

To adjust the default test, run from PowerShell:
  .\\02-run-focus-test.cmd --settle-ms 2000 --timeout 300

This is a Windows 10/11 Intel/AMD x64 prototype, not a macOS or ARM-native build.
The camera and optical behavior still need the physical test. It uses USB;
Wi-Fi and a7CR pixel-shift capture are not implemented in this version.

Keep all package folders together. Source and notices are included. Sony runtime
terms are separate from the MIT OR Apache-2.0 client source. This package is for
the owner's use with the supplied Sony SDK; it is not a public Strehl release.
""", encoding="utf-8")
    (out / "third-party/runtime-sources.txt").write_text(
        f"Python 3.13.17 embeddable x64: {PYTHON_URL}\n"
        f"Official SHA-256: {PYTHON_SHA}\n"
        "Release: https://www.python.org/downloads/release/python-31317/\n"
        "Python license: runtime/python/LICENSE.txt\n"
        "Sony SDK third-party notices: outputs/sony-control/bin/sony-sdk-notices.md\n"
        "libusb corresponding source supplied with Sony SDK: third-party/sources/libusb.zip\n"
        "MSVC 14.44.35112 app-local runtime: Microsoft Visual Studio 2022 Build Tools redist directory\n",
        encoding="utf-8")
    files = [{"path": p.relative_to(out).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)}
             for p in sorted(out.rglob("*")) if p.is_file()]
    manifest = {"package": out.name, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "capture_destination": "memory-card", "host_image_downloads": False,
                "platform": "windows-x64", "python_archive_sha256": PYTHON_SHA, "files": files}
    (out / "package-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with ZipFile(archive_path, "x", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                archive.write(path, (Path(out.name) / path.relative_to(out)).as_posix())
    checksum = digest(archive_path)
    archive_path.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive_path.name}\n", encoding="ascii")
    print(json.dumps({"zip": str(archive_path), "bytes": archive_path.stat().st_size,
                      "sha256": checksum, "files": len(files) + 1}, indent=2))


if __name__ == "__main__":
    main()
