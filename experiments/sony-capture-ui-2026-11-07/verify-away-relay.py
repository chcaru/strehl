#!/usr/bin/env python3
"""Verify the real HTTPS tunnel with a simulated capture app, then retire both."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('away_relay', ROOT / 'tools/sony-control/away-relay.py')
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--connector', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    publication = out / 'demo-session.json'
    log = (out / 'demo.log').open('wb')
    app = subprocess.Popen([str(args.exe.resolve()), '--demo', '--web-test-session', str(publication),
                            '--journal-dir', str(out / 'journals'), '--web-test-seconds', '180'],
                           stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    tunnel = None
    try:
        end = time.monotonic() + 15
        while not publication.exists():
            assert app.poll() is None and time.monotonic() < end
            time.sleep(.1)
        local = json.loads(publication.read_text(encoding='utf-8'))
        tunnel = relay.start(args.connector, out / 'relay', f'http://127.0.0.1:{local["port"]}')
        auth = f'Bearer {local["key"]}'

        def state():
            status, body = relay.fetch(tunnel['url'] + '/api/state', authorization=auth)
            assert status == 200
            return json.loads(body)

        def wait(predicate):
            end = time.monotonic() + 25
            while True:
                try:
                    value = state()
                except OSError:
                    if time.monotonic() >= end:
                        raise
                    time.sleep(.2)
                    continue
                if predicate(value):
                    return value
                assert time.monotonic() < end, value['message']
                time.sleep(.2)

        errors = []
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
            page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(tunnel['url'] + '/#key=' + local['key'])
            expect(page.locator('#camera-connect')).to_be_enabled(timeout=15000)
            page.locator('#camera-connect').click()
            wait(lambda s: s['editable'])
            expect(page.locator('#preview')).to_have_js_property('naturalWidth', 960, timeout=15000)
            page.locator('[data-mark="true"]').click()
            marked = wait(lambda s: s['start_set'])
            page.locator('[data-jog="1"]').click()
            wait(lambda s: s['editable'] and s['position'] == marked['position'] + 1)
            page.locator('[data-mark="false"]').click()
            wait(lambda s: s['planned'] == 2)
            page.locator('#start').click()
            result = wait(lambda s: s['phase'] == 'complete' and not s['busy'])
            assert result['completed'] == 2
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(out / 'https-phone.png'))
            page.locator('#camera-connect').click()
            wait(lambda s: not s['connected'] and not s['busy'])
            browser.close()
        assert not errors, errors
        report = {'schema': 'strehl-away-relay-verification-v1', 'camera': 'explicit simulator; no physical camera commands',
                  'app_sha256': hashlib.sha256(args.exe.read_bytes()).hexdigest(), 'connector_version': relay.CONNECTOR_VERSION,
                  'connector_sha256': relay.CONNECTOR_SHA256, 'transport': 'real Cloudflare HTTPS Quick Tunnel',
                  'checks': tunnel['read_only_checks'] + ['browser authenticated over HTTPS', 'live JPEG decoded over HTTPS',
                                                        'marked both focus bounds and jogged focus', 'two-plane demo capture completed over HTTPS'],
                  'browser_errors': errors, 'screenshot': 'https-phone.png'}
    finally:
        if tunnel:
            relay.stop_owned(tunnel)
        if app.poll() is None:
            app.terminate()
            app.wait(timeout=10)
        log.close()
        publication.unlink(missing_ok=True)
    # Publish completion only after cleanup itself has succeeded.
    end = time.monotonic() + 5
    while relay.process_identity(tunnel['pid']) is not None:
        assert time.monotonic() < end, 'Test connector did not stop'
        time.sleep(.05)
    report['test_tunnel_stopped'] = True
    (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
