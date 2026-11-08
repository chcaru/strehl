#!/usr/bin/env python3
"""Build and package the Rust capture UI from a fresh copied source snapshot.

Private Windows x64 package for the owner's supplied Sony SDK. No camera access.
Cargo dependencies must already be cached for this offline package build; the
included source rebuild route can fetch the exact locked dependencies normally.
"""
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tomllib
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def extract(archive, destination):
    for member in archive.infolist():
        path = PurePosixPath(member.filename.replace('\\', '/'))
        if path.is_absolute() or '..' in path.parts or ':' in str(path):
            raise ValueError('Unsafe ZIP member')
        if not member.is_dir():
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(archive.read(member))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, default=Path.home()/'Downloads/CrSDK_v2.02.00_20260610a_Win64.zip')
    parser.add_argument('--vs', type=Path, default=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools'))
    args = parser.parse_args()
    out = args.out.resolve()
    archive = out.with_suffix('.zip')
    if out.exists() or archive.exists():
        raise ValueError('Choose a fresh package directory; existing packages are never overwritten')
    receipt = json.loads((ROOT/'outputs/sony-control/build-receipt.json').read_text(encoding='utf-8'))
    native = ROOT/'outputs/sony-control/bin/strehl-sony-control.exe'
    if digest(native) != receipt['executableSha256'].lower():
        raise ValueError('Bridge does not match its build receipt')
    for name, expected in receipt['sourceFilesSha256'].items():
        if digest(ROOT/'tools/sony-control'/name) != expected.lower():
            raise ValueError(f'Bridge source changed since build: {name}')
    if digest(args.sdk) != receipt['sdk']['sha256'].lower():
        raise ValueError('SDK archive does not match the bridge build')
    out.mkdir(parents=True)
    source = out/'source'
    source.mkdir()
    inputs = []

    def copy_input(path):
        relative = path.relative_to(ROOT)
        target = source/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        inputs.append({'path': relative.as_posix(), 'sha256': digest(path)})

    for folder in ['crates/strehl-capture', 'third-party/egui-wgpu', 'tools/sony-control',
                   'experiments/sony-capture-ui-2026-11-07', 'experiments/sony-focus-control-2026-11-07',
                   'experiments/sony-focus-control-2026-11-07-capture-review', 'experiments/sony-upgrade-2026-11-07']:
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file() and not any(part in ('target', '__pycache__', '.git') for part in path.parts):
                copy_input(path)
    for name in ['Cargo.lock', 'rust-toolchain.toml', 'LICENSE-MIT', 'LICENSE-APACHE', 'scripts/strehl-capture-control.py']:
        copy_input(ROOT/name)
    # This application deliberately has no dependency on the RAW engine/decoder.
    original = tomllib.loads((ROOT/'Cargo.toml').read_text(encoding='utf-8'))
    workspace = '[workspace]\nresolver = "3"\nmembers = ["crates/strehl-capture"]\n\n[workspace.package]\n'
    for key in ['version', 'edition', 'rust-version', 'license', 'repository']:
        workspace += f'{key} = {json.dumps(original["workspace"]["package"][key])}\n'
    workspace += '\n[workspace.dependencies]\nanyhow = "1.0"\nclap = { version = "4.5", features = ["derive"] }\n'
    workspace += '\n[profile.release]\nopt-level = 3\nlto = "thin"\ncodegen-units = 1\nstrip = "symbols"\n'
    workspace += '\n[patch.crates-io]\negui-wgpu = { path = "third-party/egui-wgpu" }\n'
    (source/'Cargo.toml').write_text(workspace, encoding='utf-8', newline='\n')
    metadata = subprocess.run(['cargo','metadata','--offline','--format-version','1','--filter-platform','x86_64-pc-windows-msvc'],cwd=source,check=True,capture_output=True,text=True)
    meta = json.loads(metadata.stdout)
    if any(p['name'] in ('rawler','strehl-raw','strehl-cli') for p in meta['packages']):
        raise ValueError('Capture-only dependency boundary was violated')
    build_dir = ROOT/'outputs/sony-capture-ui/cargo-package-target'
    command = ['cargo','build','--locked','--offline','--release','-p','strehl-capture','-j','2','--target-dir',str(build_dir)]
    print('Building the shipped executable from the copied source snapshot…', flush=True)
    build = subprocess.run(command,cwd=source,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (ROOT/'outputs/sony-capture-ui'/f'{out.name}-build.log').write_text(build.stdout,encoding='utf-8')
    print(build.stdout,flush=True)
    if build.returncode:
        raise RuntimeError(f'Capture build failed: {build.returncode}')
    shutil.copy2(build_dir/'release/strehl-capture.exe',out/'Strehl-Capture.exe')
    for path in (ROOT/'outputs/sony-control/bin').rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.dll','.exe','.md'):
            target=out/'camera'/path.relative_to(ROOT/'outputs/sony-control/bin')
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    redist=args.vs/'VC/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT'
    for name in ['msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll']:
        for folder in [out,out/'camera']:
            shutil.copy2(redist/name,folder/name)
    notices=out/'third-party';notices.mkdir()
    for name in ['Redist.txt','ThirdPartyNotices.txt']:
        target=notices/'microsoft'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(args.vs/'Licenses/1033'/name,target)
    packages=[]
    for package in meta['packages']:
        if package['source'] is None:
            continue
        packages.append({k:package[k] for k in ['name','version','license','repository']})
        folder=Path(package['manifest_path']).parent
        for path in folder.iterdir():
            if path.is_file() and path.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','AUTHORS')):
                target=notices/'rust'/f'{package["name"]}-{package["version"]}'/path.name
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    (notices/'rust-dependencies.json').write_text(json.dumps(packages,indent=2)+'\n',encoding='utf-8')
    with ZipFile(args.sdk) as sdk:
        with ZipFile(io.BytesIO(sdk.read('Driver.zip'))) as driver:
            extract(driver,out/'drivers/sony-usb')
        for name in ['Camera_Remote_SDK_Readme_v2.02.00.pdf','RemoteSampleApp_IM_v2.02.00.pdf']:
            (out/'drivers'/name).write_bytes(sdk.read(name))
        (notices/'libusb-source.zip').write_bytes(sdk.read('SourceCodeOfOpenSourceSoftware/libusb.zip'))
    for name in ['LICENSE-MIT','LICENSE-APACHE','LICENSE-LGPL-2.1']:
        shutil.copy2(ROOT/name,out/name)
    guide=(ROOT/'crates/strehl-capture/README.md').read_text(encoding='utf-8').replace('../../experiments/','source/experiments/')
    (out/'START-HERE.md').write_text(guide,encoding='utf-8',newline='\n')
    (out/'try-demo.cmd').write_bytes(b'@echo off\r\nstart "" "%~dp0Strehl-Capture.exe" --demo\r\n')
    (source/'REBUILD.md').write_text('''# Rebuild the capture workspace

Install Rust 1.98.0 (MSVC x64), Visual Studio C++ Build Tools and Windows SDK.
From this source directory, run `cargo build --locked --release -p strehl-capture -j 2`.
Cargo downloads exact locked dependencies if needed. This private source kit does
not vendor every Rust dependency and does not promise an offline or byte-identical
rebuild. Copy `target/release/strehl-capture.exe` to `../Strehl-Capture.exe`.

To rebuild the native ABI bridge, supply your original Sony SDK 2.02.00 archive:
`./tools/sony-control/build.ps1 -SdkArchive C:/path/to/CrSDK_v2.02.00_20260610a_Win64.zip`.
Copy its new executable and DLL layout to `../camera`. The SDK's proprietary
headers/runtime retain Sony's terms; they are not Strehl's MIT/Apache source.
The dynamically linked libusb corresponding source is in `../third-party/libusb-source.zip`.
Keep notices and the source kit with the binary. This app does not link the RAW decoder.
''',encoding='utf-8',newline='\n')
    receipt['sdk']['archive']=args.sdk.name
    build_receipt={'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'rustc':subprocess.check_output(['rustc','-Vv'],text=True),'command':command[:-2]+['--target-dir','<external-build-cache>'],'build_working_directory':'source','app_sha256':digest(out/'Strehl-Capture.exe'),'native':receipt,'copied_inputs':inputs,'generated_workspace_sha256':digest(source/'Cargo.toml'),'resolved_lock_sha256':digest(source/'Cargo.lock'),'raw_downloads':False,'preview_storage':'memory-only'}
    (out/'build-receipt.json').write_text(json.dumps(build_receipt,indent=2)+'\n',encoding='utf-8')
    files=[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(out.rglob('*')) if p.is_file()]
    (out/'package-manifest.json').write_text(json.dumps({'files':files,'platform':'windows-x64','private_preview':True},indent=2)+'\n',encoding='utf-8')
    with ZipFile(archive,'x',compression=ZIP_DEFLATED,compresslevel=6,strict_timestamps=False) as z:
        for path in sorted(out.rglob('*')):
            if path.is_file():z.write(path,(Path(out.name)/path.relative_to(out)).as_posix())
    sha=digest(archive)
    archive.with_suffix('.zip.sha256').write_text(f'{sha}  {archive.name}\n',encoding='ascii')
    print(json.dumps({'zip':str(archive),'bytes':archive.stat().st_size,'sha256':sha,'files':len(files)+1},indent=2),flush=True)


if __name__=='__main__':
    main()
