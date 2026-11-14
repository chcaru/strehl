"""Isolated simulator and native receiver lifecycle; only owns test processes."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'scripts/strehl-control.py'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.exe = args.exe.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    ports = []
    for _ in range(2):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            ports.append(sock.getsockname()[1])
    key = '0123456789abcdef' * 3
    receiver = out / 'receiver.json'
    destination = out / 'captures'
    destination.mkdir()
    receiver.write_text(json.dumps({'bind': f'127.0.0.1:{ports[1]}', 'lan': '10.0.0.0/24', 'key': key, 'folder': str(destination), 'compress_raw': True}))
    demo = out / 'headless.json'
    demo.write_text(json.dumps({'bind': f'127.0.0.1:{ports[0]}', 'pairing_key': key, 'bridge': '', 'journal_directory': str(out / 'journal'), 'transfer': {'receiver': f'http://127.0.0.1:{ports[1]}', 'key': key, 'lan': '10.0.0.0/24', 'ram_directory': str(out / 'ram'), 'state_directory': str(out / 'state')}}))
    native = out / 'native.json'
    native.write_text(json.dumps({'controller': f'http://127.0.0.1:{ports[0]}', 'pairing_key': key, 'lan': '10.0.0.0/24', 'receiver_config': str(receiver)}))
    pointer = out / 'ready.json'
    base = [sys.executable, str(HELPER), '--exe', str(args.exe), '--session-file', str(pointer)]
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    demo_process = None
    app = None
    report = {}

    def control(*command):
        result = subprocess.run([*base, *command], capture_output=True, text=True, timeout=30, creationflags=flags)
        data = json.loads(result.stdout)
        if result.returncode or data.get('error'):
            raise RuntimeError(data.get('error') or result.stderr)
        return data['data']['result']

    def wait(predicate, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = control('snapshot')
            if predicate(value):
                return value
            time.sleep(.2)
        raise RuntimeError('Lifecycle state wait timed out')

    def command(value):
        state = control('snapshot')
        request = out / 'command.json'
        request.write_text(json.dumps({'expected_revision': state['revision'], 'command': value}))
        return control('call', '--request', str(request))

    def receiver_status():
        req = urllib.request.Request(f'http://127.0.0.1:{ports[1]}/api/status', headers={'Authorization': 'Bearer ' + key})
        return json.loads(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=3).read())

    try:
        with (out / 'demo.log').open('w') as log:
            demo_process = subprocess.Popen([str(ROOT / 'target/release/strehl-capture-headless.exe'), '--config', str(demo), '--demo'], stdout=log, stderr=log, creationflags=flags)
        with (out / 'app.log').open('w') as log:
            app = subprocess.Popen([*base, 'launch', '--capture', '--capture-settings', str(native), '--output-dir', str(out / 'processed'), '--wait'], stdout=log, stderr=log, creationflags=flags)
        deadline = time.monotonic() + 20
        while not pointer.exists():
            assert time.monotonic() < deadline and app.poll() is None, 'Native workspace failed to launch'
            time.sleep(.1)
        wait(lambda s: s['capture']['online'])
        command({'operation': 'start_capture_receiver'})
        wait(lambda s: (s['capture']['receiver'] or {}).get('ok') is True)
        assert receiver_status()['compress_raw'] is True
        command({'operation': 'set_capture_compression', 'compressed': False})
        wait(lambda s: (s['capture']['receiver'] or {}).get('compress_raw') is False)
        command({'operation': 'set_capture_compression', 'compressed': True})
        wait(lambda s: (s['capture']['receiver'] or {}).get('compress_raw') is True)
        report['native_receiver_start_and_settings'] = 'passed'
        subprocess.run([sys.executable, str(Path(__file__).with_name('qualify-native.py')), '--exe', str(args.exe), '--session-file', str(pointer), '--out', str(out / 'sequence'), '--action', 'simulator'], check=True, creationflags=flags)
        report['native_pause_resume_stop_restart'] = 'passed'
        for size in ['1440x940', '1100x760']:
            subprocess.run([sys.executable, str(HELPER), '--exe', str(args.exe), 'screenshot', '--capture', '--capture-settings', str(native), '--png', str(out / f'native-{size}.png'), '--size', size, '--output-dir', str(out / 'processed')], check=True, creationflags=flags)
        control('shutdown')
        app.wait(timeout=15)
        assert app.returncode == 0
        assert receiver_status()['ok'] is True
        report['receiver_survives_workspace_close'] = 'passed'
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
    finally:
        if app is not None and app.poll() is None:
            try:
                control('shutdown')
                app.wait(timeout=15)
            except Exception:
                # Leave unexpected work alive for inspection; never kill a shared camera session.
                print('Owned native test workspace still needs inspection', file=sys.stderr)
        if demo_process is not None and demo_process.poll() is None:
            demo_process.terminate()
            demo_process.wait(timeout=10)
        # The only receiver that can match this fresh, absolute test config was
        # launched above. Do not select by executable name alone.
        escaped = str(receiver).replace("'", "''")
        exe = str(args.exe).replace("'", "''")
        script = f"Get-CimInstance Win32_Process | Where-Object {{ $_.ExecutablePath -eq '{exe}' -and $_.CommandLine.Contains('{escaped}') -and $_.CommandLine.Contains('--capture-receiver') }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId }}"
        subprocess.run(['powershell.exe', '-NoProfile', '-Command', script], check=True, creationflags=flags)


if __name__ == '__main__':
    main()
