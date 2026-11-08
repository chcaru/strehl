#!/usr/bin/env python3
"""Manage an owned, camera-website-only Cloudflare relay on a personal Windows PC.

Uses the existing Strehl pairing key; never reads keys or issues camera commands.
This does not install a service, driver, VPN, or change firewall/router settings.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener

CONNECTOR_SHA256 = '2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343'
CONNECTOR_VERSION = '2026.10.7'
CONNECTOR_URL = f'https://github.com/cloudflare/cloudflared/releases/download/{CONNECTOR_VERSION}/cloudflared-windows-amd64.exe'
URL_PATTERN = re.compile(r'https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com\b')


def download_connector(path):
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.download')
    with temporary.open('xb') as output:
        request = Request(CONNECTOR_URL, headers={'User-Agent': 'Strehl-remote-setup'})
        with build_opener().open(request, timeout=30) as response:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != CONNECTOR_SHA256:
        raise ValueError('Downloaded connector failed its pinned SHA-256 check; it was not executed')
    # On Windows rename refuses an existing destination, preserving another run.
    temporary.rename(path)


def process_identity(pid):
    # Use Windows process creation time to reject PID reuse. No unrelated process
    # is terminated merely because it has the same executable name.
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        created, exited, system, user = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(system), ctypes.byref(user)):
            raise ctypes.WinError(ctypes.get_last_error())
        if exited.dwHighDateTime or exited.dwLowDateTime:
            return None
        capacity = wintypes.DWORD(32768)
        path = ctypes.create_unicode_buffer(capacity.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(capacity)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'path': str(Path(path.value).resolve()), 'created_filetime': (created.dwHighDateTime << 32) | created.dwLowDateTime}
    finally:
        kernel.CloseHandle(handle)


def stop_owned(state):
    import ctypes
    from ctypes import wintypes
    identity = process_identity(state['pid'])
    if identity is None:
        return False
    if identity != state['process_identity']:
        raise RuntimeError('Refusing to stop a process whose identity no longer matches this relay')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    handle = kernel.OpenProcess(0x1000 | 1, False, state['pid'])
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        # Recheck after opening the termination handle; it refers to this process.
        if process_identity(state['pid']) != identity:
            raise RuntimeError('Process identity changed while stopping the relay')
        if not kernel.TerminateProcess(handle, 0):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)
    return True


def fetch(url, *, authorization=None, origin=None):
    headers = {}
    if authorization:
        headers['Authorization'] = authorization
    if origin:
        headers['Origin'] = origin
    parsed = urlparse(url)
    opener = build_opener(ProxyHandler({})) if parsed.scheme == 'http' else build_opener()
    try:
        with opener.open(Request(url, headers=headers), timeout=5) as response:
            return response.status, response.read(100000)
    except HTTPError as error:
        return error.code, error.read(100000)


def validate_camera_url(url):
    import ipaddress
    value = urlparse(url)
    if value.scheme != 'http' or value.username or value.password or value.query or value.fragment or value.path not in ('', '/'):
        raise ValueError('Use the plain local HTTP address, without a pairing key, path or credentials')
    address = ipaddress.ip_address(value.hostname or '')
    if address.version != 4 or not (address.is_private or address.is_loopback) or address.is_unspecified:
        raise ValueError('The target must be the camera server on a local IPv4 address')
    if not value.port:
        raise ValueError('Include the camera server port, normally 8787')
    return f'http://{address}:{value.port}'


def start(connector, state_dir, target):
    target = validate_camera_url(target)
    connector = connector.resolve(strict=True)
    if hashlib.sha256(connector.read_bytes()).hexdigest() != CONNECTOR_SHA256:
        raise ValueError('Connector differs from the verified official release')
    state_path = state_dir / 'state.json'
    if state_path.exists():
        saved = json.loads(state_path.read_text(encoding='utf-8'))
        if saved.get('schema') != 'strehl-away-relay-v1':
            raise ValueError('Choose a fresh state directory; existing files were not created by this helper')
        identity = process_identity(saved['pid'])
        if identity == saved['process_identity']:
            if saved['target'] != target or identity['path'] != str(connector):
                raise RuntimeError('Stop the existing relay before changing its target or connector')
            if not saved.get('url') or not saved.get('read_only_checks'):
                raise RuntimeError('The existing relay has not finished starting; inspect its status')
            return saved
    elif state_dir.exists() and any(state_dir.iterdir()):
        raise ValueError('Choose an empty directory for relay state')
    state_dir.mkdir(parents=True, exist_ok=True)
    status, page = fetch(target + '/')
    if status != 200 or b'<title>Strehl Capture</title>' not in page:
        raise RuntimeError('The target does not serve the Strehl Capture page')
    if fetch(target + '/api/state')[0] != 401:
        raise RuntimeError('The camera API must require pairing before it is relayed')
    log_path = state_dir / 'connector.log'
    args = [str(connector), 'tunnel', '--no-autoupdate', '--loglevel', 'info', '--protocol', 'http2', '--url', target]
    with log_path.open('wb') as log:
        process = subprocess.Popen(args, cwd=connector.parent, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    state = {'schema': 'strehl-away-relay-v1', 'pid': process.pid, 'process_identity': process_identity(process.pid), 'target': target,
             'connector_version': CONNECTOR_VERSION, 'connector_sha256': CONNECTOR_SHA256,
             'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'url': None}
    if not state['process_identity']:
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError('Could not identify the owned relay process')
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    try:
        end = time.monotonic() + 50
        readiness = 'waiting for the connector URL'
        while time.monotonic() < end:
            if process.poll() is not None:
                raise RuntimeError(f'Connector exited with code {process.returncode}; inspect its local log')
            match = URL_PATTERN.search(log_path.read_text(encoding='utf-8', errors='replace'))
            if match:
                state['url'] = match.group(0)
                try:
                    code, body = fetch(state['url'] + '/')
                    readiness = f'page returned HTTP {code}'
                    if code == 200 and b'<title>Strehl Capture</title>' in body:
                        # DNS can still be settling after the page first loads.
                        # Retry transport errors across all readiness requests;
                        # a response that fails an authentication gate is fatal.
                        if fetch(state['url'] + '/api/state')[0] != 401:
                            raise RuntimeError('Remote API did not enforce pairing')
                        if fetch(state['url'] + '/api/state', authorization='Bearer invalid', origin=state['url'])[0] != 401:
                            raise RuntimeError('Same-origin forwarding changed')
                        if fetch(state['url'] + '/api/state', authorization='Bearer invalid', origin='https://foreign.invalid')[0] != 403:
                            raise RuntimeError('Foreign-origin request was not refused')
                        break
                except OSError as error:
                    readiness = str(error)
            time.sleep(.5)
        else:
            raise RuntimeError(f'Relay URL did not become ready within 50 seconds: {readiness}')
        state['read_only_checks'] = ['page served over HTTPS', 'pairing required', 'same-origin reaches pairing gate', 'foreign origin refused']
        state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
        (state_dir / 'open-away-link.url').write_text('[InternetShortcut]\nURL=' + state['url'] + '/\n', encoding='utf-8')
        return state
    except BaseException:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'status', 'stop'])
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--connector', type=Path)
    parser.add_argument('--camera-url')
    parser.add_argument('--download-connector', action='store_true', help='Download the pinned official connector if absent')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This ownership helper is for Windows')
    if args.action == 'start':
        if not args.connector or not args.camera_url:
            parser.error('start requires --connector and --camera-url')
        validate_camera_url(args.camera_url)
        if args.download_connector:
            download_connector(args.connector)
        result = start(args.connector, args.state_dir.resolve(), args.camera_url)
    else:
        state = json.loads((args.state_dir / 'state.json').read_text(encoding='utf-8'))
        if args.action == 'stop':
            result = {'stopped_owned_process': stop_owned(state), 'url': state['url']}
        else:
            result = {**state, 'running': process_identity(state['pid']) == state['process_identity']}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
