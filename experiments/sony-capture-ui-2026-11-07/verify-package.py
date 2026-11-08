#!/usr/bin/env python3
"""Audit and exercise a relocated capture ZIP. Never focus or expose a camera."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from zipfile import ZipFile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, cwd, timeout=120):
    # Hide development SDK/toolchain paths from the packaged runtime.
    environment={**os.environ,'PATH':str(Path(os.environ['SystemRoot'])/'System32')}
    result=subprocess.run(command,cwd=cwd,env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    if result.returncode!=0:
        raise RuntimeError(f'{Path(command[0]).name} exited {result.returncode}: {result.stdout}\n{result.stderr}')
    return result.stdout.strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--preview-fix',action='store_true',help='Require offset-JPEG, countdown and failed-preview UI regressions')
    parser.add_argument('--web-remote',action='store_true',help='Require embedded browser assets, firewall helper and native pairing controls')
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    with ZipFile(args.zip) as z:
        names=z.namelist()
        for name in names:
            path=PurePosixPath(name.replace('\\','/'))
            if path.is_absolute() or '..' in path.parts or ':' in str(path):raise ValueError('Unsafe archive path')
        roots={PurePosixPath(n).parts[0] for n in names}
        assert len(roots)==1
        z.extractall(out)
    package=out/roots.pop()
    manifest=json.loads((package/'package-manifest.json').read_text(encoding='utf-8'))
    listed=set()
    for entry in manifest['files']:
        path=package/entry['path'];assert path.stat().st_size==entry['bytes'],entry['path'];assert digest(path)==entry['sha256'],entry['path'];listed.add(entry['path'])
    actual={p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    assert actual==listed|{'package-manifest.json'}
    if args.web_remote:
        assert {'allow-web-remote.ps1','source/crates/strehl-capture/web/index.html','source/crates/strehl-capture/web/app.js','source/crates/strehl-capture/web/style.css'} <= listed
    assert not any(Path(name).suffix.lower() in ('.arw','.arq','.dng','.jpg','.jpeg','.png','.tif','.tiff') for name in listed)
    build=json.loads((package/'build-receipt.json').read_text(encoding='utf-8'))
    assert digest(package/'Strehl-Capture.exe')==build['app_sha256']
    assert digest(package/'camera/strehl-sony-control.exe')==build['native']['executableSha256'].lower()
    for entry in build['copied_inputs']:
        if entry['path']!='Cargo.lock':assert digest(package/'source'/entry['path'])==entry['sha256'],entry['path']
    assert digest(package/'source/Cargo.lock')==build['resolved_lock_sha256']
    assert digest(package/'source/Cargo.toml')==build['generated_workspace_sha256']
    gate=json.loads(run([str(package/'camera/strehl-sony-control.exe'),'self-test'],package/'camera'))
    assert gate['assertions']==19
    if args.preview_fix:assert gate['preview_assertions']==9
    cameras=json.loads(run([str(package/'camera/strehl-sony-control.exe'),'list'],package/'camera',30))
    assert cameras['ok'] is True and cameras['sdk_version']==0x02020000
    exercise=out/'rendered ui and journals'
    report=json.loads(run([str(package/'Strehl-Capture.exe'),'--demo','--exercise',str(exercise)],package))
    assert report['last_phase']=='Disconnected' and len(report['checks'])>=(8 if args.preview_fix else 6)
    if args.web_remote:assert len(report['checks'])>=9 and any('Web remote' in check for check in report['checks'])
    # Exercise smaller layout with an active preview, not just a disconnected page.
    preview=out/'laptop live preview.png'
    run([str(package/'Strehl-Capture.exe'),'--demo','--offscreen-screenshot',str(preview),'--size','1280x720'],package,30)
    summary={'schema':'strehl-capture-package-verification-v2','zip_name':args.zip.name,'zip_sha256':digest(args.zip),'zip_bytes':args.zip.stat().st_size,'manifest_files_verified':len(listed),'source_snapshot_verified':True,'relocated_path_contains_spaces':' ' in str(out),'native_gate_assertions':gate['assertions'],'native_preview_assertions':gate.get('preview_assertions'),'sdk_image_pointer_offset_without_camera':gate.get('sdk_image_pointer_offset'),'sdk_version':cameras['sdk_version'],'enumerated_camera_count':len(cameras['cameras']),'camera_activity':'enumeration only; no camera connection, focus or exposure','app_sha256':build['app_sha256'],'bridge_sha256':build['native']['executableSha256'].lower(),'ui':report,'laptop_live_preview_sha256':digest(preview)}
    (out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
