#!/usr/bin/env python3
"""Exercise focus and shutter fault recovery through the actual browser UI."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from playwright.sync_api import sync_playwright, expect

spec = importlib.util.spec_from_file_location('sessions', Path(__file__).with_name('verify-web-session.py'))
sessions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, errors = [], []
    with sync_playwright() as pw:
        for kind in ['focus', 'capture']:
            with sessions.demo(args.exe, out / kind, kind) as session:
                browser = pw.chromium.launch(executable_path=sessions.EDGE, headless=True)
                try:
                    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
                    page = ctx.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    base = f'http://127.0.0.1:{session["port"]}'
                    headers = {'Authorization': 'Bearer ' + session['key']}

                    def state():
                        response = ctx.request.get(base + '/api/state', headers=headers)
                        assert response.status == 200
                        return response.json()

                    def wait(predicate):
                        end = time.monotonic() + 20
                        while True:
                            value = state()
                            if predicate(value):
                                return value
                            assert time.monotonic() < end, value['message']
                            page.wait_for_timeout(50)

                    page.goto(session['url'])
                    expect(page.locator('#camera-connect')).to_be_enabled()
                    page.locator('#camera-connect').click()
                    wait(lambda s: s['editable'])
                    page.locator('[data-mark="true"]').click()
                    first = wait(lambda s: s['start_set'])['position']
                    page.locator('[data-jog="1"]').click()
                    wait(lambda s: s['editable'] and s['position'] == first + 1)
                    page.locator('[data-mark="false"]').click()
                    plan = wait(lambda s: s['planned'] == 2)['plan']
                    page.locator('#start').click()
                    fault = wait(lambda s: s['phase'] == 'fault' and not s['busy'])
                    expect(page.locator('#camera-recovery')).to_be_visible()
                    expect(page.locator('#start')).to_be_disabled()
                    page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
                    expect(page.locator('#review-failure')).to_be_visible()
                    page.locator('#review-failure').click()
                    expect(page.locator('#recover-camera')).to_be_in_viewport()
                    assert fault['failure']['exposure_uncertain'] == (kind == 'capture')
                    assert fault['completed'] == (1 if kind == 'focus' else 0)
                    previous = list((out / kind / 'journals').glob('*/events.jsonl'))
                    assert len(previous) == 1
                    old_bytes = previous[0].read_bytes()
                    if kind == 'capture':
                        expect(page.locator('#recover-camera')).to_be_disabled()
                        refusal = ctx.request.post(base + '/api/command', headers=headers, data={
                            'id': 'refuse-unsafe-recovery', 'camera_revision': fault['camera_revision'],
                            'plan_revision': fault['plan_revision'], 'sequence_id': fault['sequence_id'],
                            'command': {'op': 'recover', 'acknowledge_uncertain': False}})
                        assert refusal.status == 409
                        assert state()['phase'] == 'fault'
                        page.locator('#recovery-ack').check()
                    expect(page.locator('#recover-camera')).to_be_enabled()
                    page.screenshot(path=str(out / f'{kind}-fault.png'), full_page=True)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    page.locator('#recover-camera').click()
                    recovered = wait(lambda s: s['editable'] and s['failure'] is None)
                    assert recovered['plan'] == plan and recovered['start_set'] and recovered['end_set']
                    assert recovered['sequence_id'] == fault['sequence_id']
                    assert recovered['completed'] == fault['completed']
                    assert previous[0].read_bytes() == old_bytes
                    assert len(list((out / kind / 'journals').glob('*/events.jsonl'))) == 1
                    page.locator('#start').click()
                    complete = wait(lambda s: s['phase'] == 'complete' and not s['busy'])
                    assert complete['completed'] == 2 and complete['sequence_id'] > fault['sequence_id']
                    assert len(list((out / kind / 'journals').glob('*/events.jsonl'))) == 2
                    assert previous[0].read_bytes() == old_bytes
                    expect(page.locator('#run-message')).to_contain_text('Complete')
                    expect(page.locator('#start')).to_be_enabled()
                    expect(page.locator('#camera-recovery')).to_be_hidden()
                    page.locator('#start').hover()
                    page.screenshot(path=str(out / f'{kind}-restarted.png'), full_page=True)
                    page.locator('#camera-connect').click()
                    wait(lambda s: s['phase'] == 'disconnected' and not s['busy'])
                    checks.append(f'{kind}: clear recovery guidance, retained marks/count/journal, no automatic exposure, new two-plane stack completes without app restart')
                finally:
                    browser.close()
    assert not errors, errors
    report = {'schema': 'strehl-web-fault-verification-v1', 'camera': 'simulator only',
              'app_sha256': hashlib.sha256(args.exe.read_bytes()).hexdigest(), 'checks': checks,
              'unacknowledged_uncertain_recovery_refused': True, 'browser_errors': errors}
    (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
