#!/usr/bin/env python3
"""Exercise relay refusal/ownership gates without exposing or controlling a camera."""
import argparse
import ast
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import patch
from urllib.error import URLError
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('away_relay', ROOT / 'tools/sony-control/away-relay.py')
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connector', type=Path, required=True)
    parser.add_argument('--zip', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    checks = []
    invalid = ['https://10.0.0.7:8787', 'http://10.0.0.7:8787/#key=secret',
               'http://user:password@10.0.0.7:8787', 'http://10.0.0.7:8787/api/state',
               'http://8.8.8.8:8787', 'http://0.0.0.0:8787', 'http://camera:8787',
               'http://10.0.0.7']
    for target in invalid:
        try:
            relay.validate_camera_url(target)
        except ValueError:
            continue
        raise AssertionError(f'Unsafe target was accepted: {target}')
    assert relay.validate_camera_url('http://10.0.0.7:8787/') == 'http://10.0.0.7:8787'
    checks.append('eight invalid target forms rejected; plain LAN target accepted')

    class Fixture(BaseHTTPRequestHandler):
        valid_title = True
        api_code = 200

        def do_GET(self):
            self.send_response(self.api_code if self.path == '/api/state' else 200)
            self.end_headers()
            self.wfile.write(b'<title>Strehl Capture</title>' if self.valid_title else b'Other application')

        def log_message(self, *_args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        target = f'http://127.0.0.1:{server.server_port}'
        bad_connector = args.out / 'wrong-connector.exe'
        bad_connector.write_bytes(b'not the official connector')
        # Any spawn would violate these guards. The fixture never contains a key
        # or camera state, and the actual connector is never launched here.
        with patch.object(relay.subprocess, 'Popen', side_effect=AssertionError('Spawned before gate passed')) as spawn:
            cases = [('digest', bad_connector, True, 'verified official release'),
                     ('pairing', args.connector, True, 'must require pairing'),
                     ('wrong-page', args.connector, False, 'does not serve')]
            for name, connector, valid_title, expected in cases:
                Fixture.valid_title = valid_title
                try:
                    relay.start(connector, args.out / name, target)
                except (ValueError, RuntimeError) as error:
                    assert expected in str(error), str(error)
                else:
                    raise AssertionError(f'{name} gate did not reject')
            spawn.assert_not_called()
        checks.append('wrong connector, unpaired API and wrong page refused before connector spawn')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    # Reproduce the observed startup failure: the page resolves, then the next
    # request has a transient DNS error. Use an owned inert child, not a tunnel.
    real_popen = subprocess.Popen
    child = None
    def inert_connector(*_args, **kwargs):
        nonlocal child
        kwargs['stdout'].write(b'https://regression-fixture.trycloudflare.com\n')
        kwargs['stdout'].flush()
        child = real_popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                          creationflags=subprocess.CREATE_NO_WINDOW)
        return child

    replies = [(200, b'<title>Strehl Capture</title>'), (401, b''),
               (200, b'<title>Strehl Capture</title>'), URLError('planted DNS failure'),
               (200, b'<title>Strehl Capture</title>'), (401, b''), (401, b''), (403, b'')]
    try:
        with patch.object(relay.subprocess, 'Popen', side_effect=inert_connector), \
             patch.object(relay, 'fetch', side_effect=replies) as fetch:
            result = relay.start(args.connector, args.out / 'dns-retry', 'http://127.0.0.1:8787')
            assert fetch.call_count == len(replies)
            assert len(result['read_only_checks']) == 4
        assert relay.stop_owned(result)
        child.wait(timeout=5)
        checks.append('transient DNS error after page load retried; every authentication gate still checked')
        base = [(200, b'<title>Strehl Capture</title>'), (401, b''),
                (200, b'<title>Strehl Capture</title>')]
        for name, responses, message in [
            ('public-api', [(200, b'')], 'did not enforce pairing'),
            ('same-origin', [(401, b''), (403, b'')], 'Same-origin'),
            ('foreign-origin', [(401, b''), (401, b''), (200, b'')], 'Foreign-origin'),
        ]:
            with patch.object(relay.subprocess, 'Popen', side_effect=inert_connector), \
                 patch.object(relay, 'fetch', side_effect=base + responses):
                try:
                    relay.start(args.connector, args.out / name, 'http://127.0.0.1:8787')
                except RuntimeError as error:
                    assert message in str(error)
                else:
                    raise AssertionError(f'{name} failed response was retried or accepted')
            assert child.poll() is not None
        checks.append('failed remote pairing and origin gates terminate the owned test process')
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=5)

    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        identity = relay.process_identity(process.pid)
        assert identity
        state = {'pid': process.pid, 'process_identity': identity}
        wrong = {**state, 'process_identity': {**identity, 'created_filetime': identity['created_filetime'] + 1}}
        try:
            relay.stop_owned(wrong)
        except RuntimeError as error:
            assert 'identity' in str(error)
        else:
            raise AssertionError('Mismatched process identity was accepted')
        assert process.poll() is None
        assert relay.stop_owned(state)
        process.wait(timeout=5)
        assert relay.process_identity(process.pid) is None
        checks.append('mismatched process identity refused; exact owned process stopped')
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)

    scripts = [ROOT / 'tools/sony-control/away-relay.py',
               ROOT / 'tools/sony-control/package-away-relay.py',
               Path(__file__).with_name('verify-away-relay.py'), Path(__file__)]
    for script in scripts:
        ast.parse(script.read_text(encoding='utf-8'), filename=str(script))
    with ZipFile(args.zip) as archive:
        manifests = [name for name in archive.namelist() if name.endswith('/manifest.json')]
        assert len(manifests) == 1
        prefix = manifests[0].removesuffix('manifest.json')
        manifest = json.loads(archive.read(manifests[0]))
        assert len(archive.namelist()) == len(manifest['files']) + 1
        for item in manifest['files']:
            data = archive.read(prefix + item['path'])
            assert len(data) == item['bytes']
            assert hashlib.sha256(data).hexdigest() == item['sha256']
        assert archive.read(prefix + 'away-relay.py') == scripts[0].read_bytes()
        assert not any(name.endswith('.exe') for name in archive.namelist())
    checks.append('all package hashes match; helper source matches; vendor executable is not bundled')
    report = {'schema': 'strehl-away-relay-helper-verification-v1', 'checks': checks,
              'python': sys.version, 'package_files': len(manifest['files']) + 1,
              'zip_sha256': hashlib.sha256(args.zip.read_bytes()).hexdigest()}
    (args.out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
