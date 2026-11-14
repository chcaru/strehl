"""Exercise the actual release receiver in isolation; never operate the camera.

Use an existing real A7CR RAW and an archive produced by the shipped pack tool.
Credentials are generated for this loopback-only test and never written out.
All fixtures and restored copies are outside the read-only source capture.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/sony-raw-storage-2026-11-13'
RAW = Path(r'D:\StrehlCaptures\stack-1794612335049-9932\frame-000001.ARW')
ARCHIVE = OUT / 'reference/frame-000001.ARW.straw'
EXE = ROOT / 'target/release/strehl-capture-receiver.exe'
TOOL = ROOT / 'target/release/strehl-raw-archive.exe'


def main():
    fixture = OUT / ('http-' + str(time.time_ns()))
    fixture.mkdir()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    config = fixture / 'receiver.json'
    key = secrets.token_hex(32)
    config.write_text(json.dumps({'bind': f'127.0.0.1:{port}', 'lan': '10.0.0.0/24', 'key': key, 'folder': str(fixture / 'captures')}))
    auth = {'Authorization': 'Bearer ' + key}
    url = f'http://127.0.0.1:{port}'
    log = (fixture / 'server.log').open('w')
    process = subprocess.Popen([str(EXE), '--config', str(config)], stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    records = []
    try:
        for _ in range(100):
            try:
                s = requests.get(url + '/api/status', headers=auth, timeout=1)
                s.raise_for_status()
                break
            except requests.RequestException:
                assert process.poll() is None
                time.sleep(.1)
        assert s.json()['compress_raw'] is True
        raw = RAW.read_bytes()
        archive = ARCHIVE.read_bytes()
        wire = archive[48:]
        checksum = hashlib.sha256(raw).hexdigest()
        headers = {**auth, 'x-strehl-encoding': 'strehl-raw-v1', 'x-strehl-decoded-length': str(len(raw)), 'x-content-sha256': checksum}
        run = 'stack-real-archive'
        response = requests.post(url + '/api/runs/' + run, headers=auth, timeout=10)
        response.raise_for_status()
        folder = Path(response.json()['folder'])
        endpoint = url + '/api/files/' + run + '/frame-000001.ARW'
        def refused(body, extra=None):
            try:
                r = requests.put(endpoint, headers={**headers, **(extra or {})}, data=body, timeout=30)
                assert r.status_code >= 400
                status = r.status_code
            except requests.ConnectionError:
                # An early header/version refusal can close HTTP while the
                # client is still sending a large body. Verify server survival.
                status = 'connection-reset-on-refusal'
            requests.get(url + '/api/status', headers=auth, timeout=3).raise_for_status()
            return status
        for label, body, extra in [('truncated', wire[:-1], {}), ('trailing', wire + b'x', {}), ('wrong-hash', wire, {'x-content-sha256': '0' * 64}), ('oversized', wire[:16], {'x-strehl-decoded-length': str(2**30)}), ('version', b'BADMAGIC' + wire[8:], {})]:
            status = refused(body, extra)
            assert not list(folder.iterdir()), label
            records.append({'control': label, 'status': status, 'no_committed_or_partial_files': True})
        # A real TCP interruption, not just a complete body with bad contents.
        request_header = ('PUT /api/files/' + run + '/frame-000001.ARW HTTP/1.1\r\nHost: 127.0.0.1:' + str(port) + '\r\n' + ''.join(k + ': ' + v + '\r\n' for k, v in headers.items()) + 'Content-Length: ' + str(len(wire)) + '\r\nConnection: close\r\n\r\n').encode()
        with socket.create_connection(('127.0.0.1', port)) as sock:
            sock.sendall(request_header + wire[:32768])
        time.sleep(.4)
        assert not list(folder.iterdir())
        records.append({'control': 'TCP-disconnect', 'no_committed_or_partial_files': True})
        r = requests.put(endpoint, headers=headers, data=wire, timeout=30)
        r.raise_for_status()
        receipt = r.json()
        saved = Path(receipt['path'])
        assert saved.suffix == '.straw' and saved.read_bytes() == archive
        assert receipt['bytes'] == len(raw) and receipt['storage_bytes'] == len(archive)
        assert receipt['sha256'] == checksum and receipt['durable'] is True
        retry = requests.put(endpoint, headers=headers, data=wire, timeout=30)
        retry.raise_for_status()
        assert retry.json()['already_saved'] is True
        refused(wire[:-1])
        corrupt = bytearray(archive); corrupt[16] ^= 1
        saved.write_bytes(corrupt)
        refused(wire)
        assert saved.read_bytes() == corrupt
        saved.write_bytes(archive)
        subprocess.run([str(TOOL), 'restore', str(saved), '--output-dir', str(fixture / 'restored')], check=True, capture_output=True, text=True)
        restored = fixture / 'restored/frame-000001.ARW'
        assert restored.read_bytes() == raw
        # Second restore must refuse an overwrite, leaving the recovered RAW intact.
        refusal = subprocess.run([str(TOOL), 'restore', str(saved), '--output-dir', str(fixture / 'restored')], capture_output=True, text=True)
        assert refusal.returncode == 1 and restored.read_bytes() == raw
        records.append({'control': 'restore-exact-and-no-overwrite', 'refusal_exit': refusal.returncode, 'original_sha256': checksum})
        # Identity bodies are compressed locally under the same pinned policy.
        r = requests.put(endpoint.replace('000001', '000002'), headers={**auth, 'x-content-sha256': checksum}, data=raw, timeout=30)
        r.raise_for_status()
        assert Path(r.json()['path']).read_bytes() == archive
        requests.post(url + '/api/folder', headers=auth, json={'folder': str(fixture / 'captures'), 'compress_raw': False}, timeout=10).raise_for_status()
        r = requests.post(url + '/api/runs/stack-plain-null', headers=auth, timeout=10)
        r.raise_for_status(); assert r.json()['compress_raw'] is False
        r = requests.put(url + '/api/files/stack-plain-null/frame-000001.ARW', headers=headers, data=wire, timeout=30)
        r.raise_for_status(); assert Path(r.json()['path']).read_bytes() == raw
        # Re-registering the first run must not pick up the changed default.
        r = requests.post(url + '/api/runs/' + run, headers=auth, timeout=10)
        assert r.json()['compress_raw'] is True
        output = {'input_sha256': checksum, 'input_bytes': len(raw), 'archive_bytes': len(archive), 'disk_saved_percent': 100 * (1 - len(archive) / len(raw)), 'receiver_sha256': hashlib.sha256(EXE.read_bytes()).hexdigest(), 'controls': records, 'exact_payload_retention': True, 'identity_sender_archived': True, 'compression_off_plain_arw': True, 'corrupt_duplicate_refused': True, 'receipt': receipt, 'fixture': str(fixture)}
        (OUT / 'http-qualification.json').write_text(json.dumps(output, indent=2) + '\n')
        print(json.dumps({k: output[k] for k in ['input_bytes', 'archive_bytes', 'disk_saved_percent', 'exact_payload_retention', 'identity_sender_archived', 'compression_off_plain_arw', 'corrupt_duplicate_refused']}))
    finally:
        # This script terminates only the isolated test process it started.
        process.terminate(); process.wait(timeout=10); log.close()
        # Avoid leaving even this throwaway authentication key in an artifact.
        if config.exists():
            c = json.loads(config.read_text()); c['key'] = 'REDACTED-TEST-KEY'; config.write_text(json.dumps(c, indent=2) + '\n')


if __name__ == '__main__':
    main()
