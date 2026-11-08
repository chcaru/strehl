#!/usr/bin/env python3
"""Commission and verify pairing recovery against actual embedded demo servers."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright, expect

EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'


@contextmanager
def demo(exe, folder, failure=None):
    folder.mkdir(parents=True, exist_ok=False)
    publication = folder / 'private-session.json'
    with (folder / 'server.log').open('wb') as log:
        command = [str(exe.resolve()), '--demo', '--web-test-session', str(publication),
                   '--journal-dir', str(folder / 'journals'), '--web-test-seconds', '360']
        if failure:
            command += ['--web-test-failure', failure]
        process = subprocess.Popen(command,
                                   stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            end = time.monotonic() + 20
            while not publication.exists():
                assert process.poll() is None and time.monotonic() < end
                time.sleep(.05)
            value = json.loads(publication.read_text())
            assert value['demo'] and value['pid'] == process.pid
            yield value
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            publication.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, errors = [], []
    with sync_playwright() as pw:
        # Red control: old embedded client signs out on exactly one 401, even
        # while the same key remains valid on its server.
        with demo(args.baseline, out / 'baseline') as old:
            browser = pw.chromium.launch(executable_path=EDGE, headless=True)
            page = browser.new_page()
            page.goto(old['url'])
            expect(page.locator('#camera-connect')).to_be_enabled()
            page.route('**/api/state', lambda route: route.fulfill(status=401, json={'error': 'planted rejection'}), times=1)
            expect(page.locator('#notice')).to_contain_text('Pairing expired')
            assert page.evaluate("sessionStorage.getItem('strehl-pairing')") is None
            req = Request(f'http://127.0.0.1:{old["port"]}/api/state', headers={'Authorization': 'Bearer ' + old['key']})
            with urlopen(req, timeout=5) as response:
                assert response.status == 200
            browser.close()
            checks.append('Old client reproduced: one planted 401 deletes a still-valid key and reports expiration')

        with demo(args.exe, out / 'updated') as session:
            base = f'http://127.0.0.1:{session["port"]}'

            def http(path, payload=None, key=None):
                headers = {'Authorization': 'Bearer ' + (key or session['key'])}
                if payload is not None:
                    headers['Content-Type'] = 'application/json'
                req = Request(base + path, headers=headers, data=None if payload is None else json.dumps(payload).encode())
                try:
                    with urlopen(req, timeout=8) as reply:
                        return reply.status, json.loads(reply.read())
                except HTTPError as error:
                    return error.code, json.loads(error.read())

            def state():
                code, value = http('/api/state')
                assert code == 200
                return value

            def wait(predicate, seconds=20):
                end = time.monotonic() + seconds
                while True:
                    value = state()
                    if predicate(value):
                        return value
                    assert time.monotonic() < end, value['message']
                    time.sleep(.05)

            def command(op, key=None):
                value = state()
                return http('/api/command', {'id': uuid.uuid4().hex, 'camera_revision': value['camera_revision'],
                                            'plan_revision': value['plan_revision'], 'sequence_id': value['sequence_id'],
                                            'command': op}, key)

            def context():
                return pw.chromium.launch_persistent_context(str(out / 'private-browser-profile'),
                    executable_path=EDGE, headless=True, viewport={'width': 390, 'height': 844},
                    is_mobile=True, has_touch=True)

            ctx = context()
            try:
                page = ctx.new_page()
                page.clock.install()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(session['url'])
                expect(page.locator('#camera-connect')).to_be_enabled()
                assert '#key=' not in page.url
                page.locator('#camera-connect').click()
                wait(lambda s: s['editable'])
                page.locator('[data-mark="true"]').click()
                first = wait(lambda s: s['start_set'])['position']
                for step in range(3):
                    page.locator('[data-jog="128"]').click()
                    wait(lambda s: s['editable'] and s['position'] == first + (step + 1) * 128)
                page.locator('[data-mark="false"]').click()
                wait(lambda s: s['planned'] == 385)
                starts = []

                def lose_start_reply(route):
                    if route.request.post_data_json['command']['op'] == 'start':
                        starts.append(True)
                        response = route.fetch()
                        assert response.status == 200
                        route.abort()
                    else:
                        route.continue_()

                page.route('**/api/command', lose_start_reply)
                page.locator('#start').click()
                running = wait(lambda s: s['phase'] == 'capturing')
                sequence = running['sequence_id']
                page.route('**/api/state', lambda route: route.fulfill(status=401, json={'error': 'planted rejection'}), times=1)
                expect(page.locator('#notice')).to_contain_text('Retrying saved pairing')
                expect(page.locator('#workspace')).to_be_visible()
                expect(page.locator('#stop')).to_be_disabled()
                assert page.evaluate("JSON.parse(localStorage.getItem('strehl-pairing-v2')).key") == session['key']
                expect(page.locator('#stop')).to_be_enabled(timeout=15000)
                checks.append('One 401 mid-capture retains pairing and last progress, disables commands, then reconnects')

                def offline(route):
                    route.abort()

                page.route('**/api/state', offline)
                expect(page.locator('#run-message')).to_contain_text('last confirmed')
                expect(page.locator('#stop')).to_be_disabled()
                page.screenshot(path=str(out / 'mobile-offline.png'), full_page=True)
                page.unroute('**/api/state', offline)
                page.evaluate("() => window.dispatchEvent(new Event('online'))")
                expect(page.locator('#stop')).to_be_enabled(timeout=15000)
                page.clock.fast_forward('24:00:00')
                page.evaluate("() => window.dispatchEvent(new Event('pageshow'))")
                expect(page.locator('#stop')).to_be_enabled(timeout=15000)
                assert state()['sequence_id'] == sequence and starts == [True]
                checks.append('Network loss and a 24-hour browser-clock jump recover without replaying the lost Start reply')

                # A browser process restart, with only its profile retained.
                ctx.close()
                ctx = context()
                page = ctx.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base)
                expect(page.locator('#stop')).to_be_enabled(timeout=15000)
                expect(page.locator('#preview')).to_have_js_property('naturalWidth', 960, timeout=15000)
                checks.append('Full browser process restart reconnects from stored pairing without a URL fragment')

                held = []
                page.route('**/api/state', lambda route: held.append(route), times=1)
                end = time.monotonic() + 10
                while not held:
                    assert time.monotonic() < end
                    page.wait_for_timeout(50)
                page.locator('#unpair').click()
                page.locator('#pair-key').fill(session['url'])
                page.locator('#pair-form button').click()
                held[0].fulfill(status=401, json={'error': 'old request'})
                expect(page.locator('#stop')).to_be_enabled(timeout=15000)
                assert page.evaluate("JSON.parse(localStorage.getItem('strehl-pairing-v2')).key") == session['key']
                checks.append('A delayed 401 from a forgotten pairing cannot erase a newer pairing attempt')

                def replaced(route):
                    route.fulfill(status=401, headers={'x-strehl-remote-session': 'f' * 32}, json={'error': 'planted revocation'})

                page.route('**/api/state', replaced)
                expect(page.locator('#notice')).to_contain_text('restarted or its links were revoked')
                expect(page.locator('#workspace')).to_be_visible()
                expect(page.locator('#stop')).to_be_disabled()
                page.screenshot(path=str(out / 'mobile-repair.png'), full_page=True)
                page.unroute('**/api/state', replaced)
                page.locator('#retry-pairing').click()
                expect(page.locator('#stop')).to_be_enabled(timeout=15000)
                checks.append('Changed server identity produces actionable re-pair UI with last progress retained')

                wrong = '0' * 48
                page.goto(base + '/#key=' + wrong)
                expect(page.locator('#pairing')).to_be_visible(timeout=15000)
                assert page.evaluate("JSON.parse(localStorage.getItem('strehl-pairing-v2')).key") == wrong
                assert '#key=' not in page.url
                expect(page.locator('#camera-connect')).to_be_disabled()
                assert command({'op': 'stop'}, key=wrong)[0] == 401
                assert state()['phase'] == 'capturing'
                page.locator('#pair-key').fill(session['url'])
                page.locator('#pair-form button').click()
                expect(page.locator('#stop')).to_be_enabled(timeout=15000)
                checks.append('Opening a replacement link in the current tab applies its key; wrong keys remain refused and correct re-pair restores control')

                other = ctx.new_page()
                other.goto(base)
                expect(other.locator('#stop')).to_be_enabled(timeout=15000)
                page.locator('#unpair').click()
                expect(other.locator('#pairing')).to_be_visible()
                expect(other.locator('#workspace')).to_be_hidden()
                assert other.evaluate("localStorage.getItem('strehl-pairing-v2')") is None
                checks.append('Explicit Forget removes persistent pairing and signs out other open tabs without stopping capture')

                isolated = pw.chromium.launch(executable_path=EDGE, headless=True)
                try:
                    memory = isolated.new_page(viewport={'width': 1366, 'height': 1000})
                    memory.on('pageerror', lambda error: errors.append(str(error)))
                    memory.add_init_script("for (const name of ['localStorage','sessionStorage']) Object.defineProperty(window,name,{get(){throw new DOMException('blocked','SecurityError')}})")
                    memory.goto(session['url'])
                    expect(memory.locator('#stop')).to_be_enabled(timeout=15000)
                    memory.route('**/api/state', lambda route: route.fulfill(status=401, json={'error': 'planted rejection'}), times=1)
                    expect(memory.locator('#notice')).to_contain_text('Retrying saved pairing')
                    expect(memory.locator('#stop')).to_be_enabled(timeout=15000)
                    memory.screenshot(path=str(out / 'desktop-recovered.png'), full_page=True)
                    assert memory.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    checks.append('Blocked browser storage falls back to memory and still reconnects after a rejected request')
                finally:
                    isolated.close()
                final = state()
                assert final['sequence_id'] == sequence and final['completed'] > running['completed']
                assert starts == [True] and not errors, errors
                assert command({'op': 'stop'})[0] == 200
                wait(lambda s: s['phase'] == 'stopped')
                checks.append('Same simulated sequence advanced throughout recovery; exactly one Start was issued')
            finally:
                ctx.close()

    report = {'schema': 'strehl-web-session-verification-v1', 'camera': 'explicit simulator only',
              'app_sha256': hashlib.sha256(args.exe.read_bytes()).hexdigest(),
              'baseline_sha256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
              'checks': checks, 'browser_errors': errors, 'clock_jump_hours': 24,
              'real_hours_long_soak': False, 'start_requests': len(starts),
              'simulated_captures_completed': final['completed']}
    (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
