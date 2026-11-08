#!/usr/bin/env python3
"""Package the small personal-PC relay helper; vendor binary downloads directly."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('away_relay', Path(__file__).with_name('away-relay.py'))
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--camera-url', required=True)
    args = parser.parse_args()
    target = relay.validate_camera_url(args.camera_url)
    out = args.out.resolve()
    archive = out.with_suffix('.zip')
    assert not out.exists() and not archive.exists(), 'Choose a fresh package path'
    out.mkdir(parents=True)
    shutil.copy2(Path(__file__).with_name('away-relay.py'), out / 'away-relay.py')
    for name in ('LICENSE-MIT', 'LICENSE-APACHE'):
        shutil.copy2(ROOT / name, out / name)
    for action in ('start', 'stop', 'status'):
        lines = ['@echo off', 'cd /d "%~dp0"']
        if action == 'start':
            lines += ['echo Starting the camera website relay on this personal PC.',
                      f'python "%~dp0away-relay.py" start --connector "%~dp0cloudflared.exe" --download-connector --state-dir "%~dp0state" --camera-url "{target}"',
                      'if errorlevel 1 goto done', r'start "" "%~dp0state\open-away-link.url"',
                      'echo Keep this PC and the camera laptop awake. You may close this window.',
                      'echo Use stop-away-access.cmd to stop only this relay.']
        else:
            lines += [f'python "%~dp0away-relay.py" {action} --state-dir "%~dp0state"']
        lines += [':done', 'pause']
        (out / f'{action}-away-access.cmd').write_bytes(('\r\n'.join(lines) + '\r\n').encode('ascii'))
    (out / 'START-HERE.md').write_text(f'''# Strehl away access through a personal PC

This helper relays only the Strehl Capture website at `{target}` over HTTPS.
It is the fallback for a camera laptop that cannot install Tailscale. Run it on
the personal wired PC, where Python 3.12 is already available. The camera laptop
keeps running the existing Strehl Capture r5 app and needs no replacement build.

1. Leave Web remote enabled on the camera laptop.
2. Double-click **start-away-access.cmd** here. On first use, it downloads
   Cloudflare's official portable connector (about 55 MB), checks its pinned
   SHA-256, then starts it in the background. No service or driver is installed.
3. The browser opens the HTTPS link. On the phone, open the same link and paste
   the camera laptop's full **Copy pairing link** into **Pairing link or key**.
   This extracts the original key; the browser continues using the HTTPS route.
   Keep the pairing link private. The helper never reads or stores that key.
4. Keep **both PCs awake**, with the camera attached and Strehl open. The phone
   can use cellular or another Wi-Fi network. Try cellular before leaving.
5. **stop-away-access.cmd** stops only the owned relay. Capture on the laptop
   continues. **status-away-access.cmd** shows whether the relay is running.
   Starting again while it is running reuses it; starting after stopping creates
   a new link. Stop before moving this helper's folder.

If the camera laptop's address changes, edit the `--camera-url` argument in the
start script to its new plain HTTP address. Never put `#key=...` in that argument.
Python must be available as `python` on this personal PC's PATH. This helper is
not intended to work around managed software restrictions on a corporate PC.

RAWs remain on the camera SD card. Transient preview and camera-control traffic
pass through Cloudflare; the hop from this personal PC to the camera laptop uses
the existing LAN HTTP connection. Strehl's random pairing key protects every API
request. The generic pairing page can be opened without a key. No folder, shell,
RAW-transfer or other-PC access is added. Default info-level logging does not log
request headers; do not enable debug logging with pairing credentials in use.

This uses a [Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/):
a temporary development relay with no uptime guarantee, not a permanent hosted
service. Its URL changes on restart. A lost relay/browser connection does not
interrupt a stack already running on the laptop.

For local Android access, allow **Settings → Apps → Chrome → Permissions →
Nearby devices**. The owner confirmed this resolved ERR_TOO_MANY_RETRIES on
`http://10.0.0.7:8787/`.

Connector: {relay.CONNECTOR_VERSION}; official download:
{relay.CONNECTOR_URL}

Pinned SHA-256: `{relay.CONNECTOR_SHA256}`.
The connector downloads directly from Cloudflare's release; it is not bundled
in this ZIP. Its upstream license and source are available in that repository.
The helper source is included here under Strehl's MIT OR Apache-2.0 licenses.
''', encoding='utf-8', newline='\n')
    files = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(out.iterdir()) if p.is_file()]
    (out / 'manifest.json').write_text(json.dumps({'files': files, 'camera_url': target}, indent=2) + '\n', encoding='utf-8')
    with ZipFile(archive, 'x', ZIP_DEFLATED) as z:
        for p in sorted(out.iterdir()):
            z.write(p, f'{out.name}/{p.name}')
    print(json.dumps({'zip': str(archive), 'bytes': archive.stat().st_size,
                      'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
