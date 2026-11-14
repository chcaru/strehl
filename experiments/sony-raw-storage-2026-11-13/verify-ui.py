"""Installed receiver settings and capture preview, with no exposure commands."""
import json
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/sony-raw-storage-2026-11-13'


def main():
    cfg = json.loads((Path.home() / 'AppData/Local/StrehlCaptureReceiver/receiver.json').read_text())
    camera = json.loads((ROOT / 'outputs/pi-capture-2026-11-11/private/headless.json').read_text())
    headers = {'Authorization': 'Bearer ' + cfg['key']}
    def status():
        r = requests.get('http://127.0.0.1:8789/api/status', headers=headers, timeout=5)
        r.raise_for_status(); return r.json()
    errors = []; checks = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        context.add_init_script('localStorage.setItem("strehl-receiver-pairing",' + json.dumps(cfg['key']) + ');')
        page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto('http://127.0.0.1:8789/')
        expect(page.locator('#settings')).to_be_visible()
        expect(page.locator('#compress-raw')).to_be_checked()
        for setting in [False, True]:
            page.locator('#compress-raw').set_checked(setting)
            with page.expect_response(lambda r: r.url.endswith('/api/folder') and r.request.method == 'POST') as saved:
                page.get_by_role('button', name='Save settings').click()
            assert saved.value.ok
            assert status()['compress_raw'] is setting
        page.reload()
        expect(page.locator('#compress-raw')).to_be_checked()
        expect(page.locator('#latest')).to_contain_text('.ARW.straw')
        expect(page.locator('#latest')).to_contain_text('disk space saved')
        page.screenshot(path=str(OUT / 'receiver-desktop.png'), full_page=True)
        checks.append({'view': 'receiver-local-desktop', 'toggle_saved_both_ways': True, 'default_left_on': True, 'reload_persisted': True, 'compressed_receipt_visible': True})
        context.close()
        context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        context.add_init_script('localStorage.setItem("strehl-receiver-pairing",' + json.dumps(cfg['key']) + ');')
        page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto('http://10.0.0.109:8789/')
        expect(page.locator('#settings')).to_be_visible()
        expect(page.locator('#compress-raw')).to_be_checked()
        expect(page.locator('#compress-raw')).to_be_disabled()
        assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth')
        page.screenshot(path=str(OUT / 'receiver-phone.png'), full_page=True)
        checks.append({'view': 'receiver-LAN-phone-size', 'settings_read_only_away_from_PC': True, 'no_horizontal_overflow': True})
        context.close()
        context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))
        try:
            page.goto('http://10.0.0.178:8787/#key=' + camera['pairing_key'])
            expect(page.locator('#workspace')).to_be_visible(timeout=15000)
            expect(page.locator('#preview')).to_have_js_property('naturalWidth', 1024, timeout=15000)
            expect(page.locator('[data-mark="true"]')).to_be_enabled()
            expect(page.locator('[data-mark="false"]')).to_be_enabled()
            expect(page.locator('#start')).to_be_disabled()
            page.screenshot(path=str(OUT / 'capture-phone.png'), full_page=True)
            checks.append({'view': 'camera-phone-size', 'preview_1024px': True, 'bounds_enabled': True, 'unset_start_disabled': True})
        except Exception as e:
            raise RuntimeError(str(e).replace(camera['pairing_key'], '[redacted]')) from None
        context.close(); browser.close()
    assert not errors, errors
    (OUT / 'ui-verification.json').write_text(json.dumps({'checks': checks, 'browser_errors': errors}, indent=2) + '\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
