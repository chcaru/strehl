#!/usr/bin/env python3
"""Exercise the embedded web remote in Edge with an explicit simulated camera."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    exe = args.exe.resolve()
    publication = out / 'test-session.json'
    command = [str(exe), '--demo', '--web-test-session', str(publication),
               '--journal-dir', str(out / 'journals'), '--web-test-seconds', '240']
    log = (out / 'server.log').open('w', encoding='utf-8')
    process = subprocess.Popen(command, cwd=exe.parent, stdout=log, stderr=log,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    checks, errors, expected_conflicts = [], [], []
    try:
        deadline = time.monotonic() + 20
        while not publication.is_file():
            assert process.poll() is None, 'Demo server exited'
            assert time.monotonic() < deadline, 'Demo server did not start'
            time.sleep(.1)
        session = json.loads(publication.read_text(encoding='utf-8'))
        assert session['demo'] and session['pid'] == process.pid
        base = f'http://127.0.0.1:{session["port"]}'

        def http(path, data=None, auth=True, origin=None):
            headers = {'Authorization': f'Bearer {session["key"]}'} if auth else {}
            if origin:
                headers['Origin'] = origin
            if data is not None:
                headers['Content-Type'] = 'application/json'
            req = Request(base + path, headers=headers,
                          data=json.dumps(data).encode() if data is not None else None)
            try:
                with urlopen(req, timeout=8) as response:
                    return response.status, response.read()
            except HTTPError as error:
                return error.code, error.read()

        def state():
            code, body = http('/api/state')
            assert code == 200
            return json.loads(body)

        def wait(predicate, seconds=20):
            end = time.monotonic() + seconds
            while True:
                current = state()
                if predicate(current):
                    return current
                assert time.monotonic() < end, f'Timeout: {current["phase"]} {current["message"]}'
                time.sleep(.1)

        def ready():
            return wait(lambda s: s['editable'])

        assert http('/api/state', auth=False)[0] == 401
        assert http('/api/state', origin='https://foreign.invalid')[0] == 403
        assert http('/../../Cargo.toml')[0] == 404
        assert http('/api/preview')[0] == 204
        checks.append('Unauthenticated, cross-origin and file-path requests are rejected; no phantom preview')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                headless=True, args=['--disable-background-networking'])
            desktop = browser.new_context(viewport={'width': 1366, 'height': 1000})
            phone = browser.new_context(viewport={'width': 390, 'height': 844},
                                        is_mobile=True, has_touch=True, device_scale_factor=2)

            def page(context):
                tab = context.new_page()
                tab.on('pageerror', lambda error: errors.append(str(error)))
                def console(message):
                    if message.type != 'error' or '404' in message.text:
                        return
                    if '409 (Conflict)' in message.text and message.location.get('url', '').endswith('/api/command'):
                        expected_conflicts.append(message.text)
                    else:
                        errors.append(message.text)
                tab.on('console', console)
                tab.goto(session['url'])
                expect(tab.locator('#workspace')).to_be_visible()
                expect(tab.locator('#connection-label')).not_to_have_text('Web remote')
                assert '#key=' not in tab.url, 'Pairing key was not removed from history'
                return tab

            pc = page(desktop)
            pc.locator('#camera-connect').click()
            ready()
            expect(pc.locator('#preview')).to_be_visible(timeout=10000)
            expect(pc.locator('#preview')).to_have_js_property('naturalWidth', 960, timeout=10000)
            pc.locator('[data-mark="true"]').click()
            start = wait(lambda s: s['start_set'])['plan']['start']
            pc.locator('[data-jog="128"]').click()
            wait(lambda s: s['editable'] and s['position'] == start + 128)
            pc.locator('[data-mark="false"]').click()
            wait(lambda s: s['end_set'])
            mobile = page(phone)
            expect(mobile.locator('#start-position')).to_have_text(str(start))
            expect(mobile.locator('#end-position')).to_have_text(str(start + 128))
            checks.append('Real browser decodes live JPEG; desktop marks and focus moves appear on a phone client')

            mobile.locator('#step').fill('2')
            pc.locator('#step').fill('4')
            pc.get_by_role('button', name='Apply settings', exact=True).click()
            wait(lambda s: s['plan']['step'] == 4)
            mobile.get_by_role('button', name='Apply settings', exact=True).click()
            expect(mobile.locator('#notice')).to_contain_text('State changed')
            assert state()['plan']['step'] == 4
            mobile.locator('#reset-settings').click()
            pc.locator('#step').fill('1')
            pc.locator('#settle-ms').fill('100')
            pc.get_by_role('button', name='Apply settings', exact=True).click()
            wait(lambda s: s['plan']['step'] == 1 and s['plan']['settle_ms'] == 100)
            checks.append('Conflicting edits from two controllers are refused without overwriting the current plan')

            pc.locator('#select-roi').click()
            box = pc.locator('#preview').bounding_box()
            pc.mouse.move(box['x'] + box['width'] * .2, box['y'] + box['height'] * .2)
            pc.mouse.down()
            pc.mouse.move(box['x'] + box['width'] * .75, box['y'] + box['height'] * .75, steps=10)
            pc.mouse.up()
            wait(lambda s: .18 < s['roi']['x'] < .22 and .5 < s['roi']['width'] < .6)
            checks.append('Pointer selection sets the subject ROI in shared preview coordinates')
            pc.screenshot(path=str(out / 'desktop-bounds.png'), full_page=True)
            mobile.evaluate('window.scrollTo(0,0)')
            mobile.screenshot(path=str(out / 'phone-bounds.png'), full_page=True)
            assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Phone page overflows horizontally'
            assert pc.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Desktop page overflows horizontally'

            pc.locator('#start').click()
            running = wait(lambda s: s['phase'] == 'capturing' and s['completed'] >= 1)
            stale = {k: running[k] for k in ('camera_revision', 'plan_revision', 'sequence_id')}
            stale.update(id='second-start-0001', command={'op': 'start'})
            assert http('/api/command', stale)[0] == 409
            mobile.close()
            later = wait(lambda s: s['completed'] > running['completed'])
            mobile = page(phone)
            expect(mobile.locator('#pause')).to_be_enabled()
            mobile.locator('#pause').click()
            paused = wait(lambda s: s['phase'] == 'paused')
            time.sleep(.7)
            assert state()['completed'] == paused['completed']
            assert state()['timer']['elapsed'] == paused['timer']['elapsed']
            expect(pc.locator('#pause')).to_have_text('Resume')
            pc.screenshot(path=str(out / 'desktop-paused.png'), full_page=True)
            mobile.evaluate('window.scrollTo(0,0)')
            mobile.screenshot(path=str(out / 'phone-paused.png'))
            pc.locator('#pause').click()
            wait(lambda s: s['completed'] > paused['completed'])
            mobile.locator('#stop').click()
            stopped = wait(lambda s: s['phase'] == 'stopped' and not s['busy'])
            assert stopped['completed'] < stopped['total']
            checks.append('Browser closure leaves capture running; reconnect, pause, frozen countdown, resume and stop work across clients')

            pc.locator('[data-go="true"]').click()
            wait(lambda s: s['editable'] and s['position'] == start)
            for delta in (1, 2):
                pc.locator('[data-jog="1"]').click()
                wait(lambda s: s['editable'] and s['position'] == start + delta)
            pc.locator('[data-mark="false"]').click()
            wait(lambda s: s['planned'] == 3)
            pc.locator('#start').click()
            complete = wait(lambda s: s['phase'] == 'complete' and not s['busy'])
            assert complete['completed'] == 3 and complete['timer']['remaining'] == 0
            checks.append('A second three-plane stack completes with both endpoints and a finished timer')

            pc.locator('#camera-connect').click()
            wait(lambda s: s['phase'] == 'disconnected' and not s['busy'])
            expect(mobile.locator('#start-position')).to_have_text('Not marked')
            expect(pc.locator('#preview')).to_be_hidden()
            checks.append('Disconnect clears shared focus marks and the browser preview')
            browser.close()

        assert not errors, f'Browser errors: {errors}'
        assert len(expected_conflicts) == 1, 'Expected exactly the intentionally stale settings request'
        files = list((out / 'journals').rglob('*'))
        assert not any(p.suffix.lower() in ('.arw', '.jpg', '.jpeg', '.png', '.arq') for p in files)
        results = [json.loads(p.read_text(encoding='utf-8')) for p in (out / 'journals').rglob('result.json')]
        assert len(results) == 2
        report = {'schema': 'strehl-web-remote-verification-v1', 'camera': 'explicit simulator; no physical camera access',
                  'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
                  'browser': 'Microsoft Edge / Playwright, headless', 'sizes': [[1366, 1000], [390, 844]],
                  'checks': checks, 'browser_errors': errors, 'expected_conflicts': len(expected_conflicts), 'journal_runs': len(results),
                  'away_vpn': 'Not exercised; Tailscale must be installed and connected on owner devices',
                  'screenshots': [p.name for p in out.glob('*.png')]}
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        log.close()
        publication.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
