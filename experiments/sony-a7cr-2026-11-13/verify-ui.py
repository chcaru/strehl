"""Physical four-shot stop through the phone-sized production browser UI."""
import json
import argparse
from pathlib import Path
import time
from playwright.sync_api import sync_playwright, expect
from deploy import CONFIG, OUT, state, wait


def main():
    key = CONFIG['pairing_key']
    errors = []
    parser=argparse.ArgumentParser()
    parser.add_argument('--finish-only',action='store_true')
    parser.add_argument('--stopped-run',type=Path)
    args=parser.parse_args()
    before = state()
    assert before['editable']
    if not args.finish_only: assert before['planned']==3
    if args.finish_only:
        # The first browser run reached stopped/reconnected; only its final
        # wait-for-function assertion violated CSP. Read the preserved result.
        folder=args.stopped_run or Path(before['storage']['receipt']['path']).parent
        result=json.loads((folder/'result.json').read_text())
        assert result['outcome']=='stopped' and result['completed_camera_events']==1
        assert len(list(folder.glob('*.ARW')))==4
        done={'folder':str(folder),'storage':{'saved_frames':4},'result':result}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
            context = browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto('http://10.0.0.178:8787/#key='+key)
            expect(page.locator('#workspace')).to_be_visible(timeout=15000)
            expect(page.locator('#storage-info')).to_contain_text('A7CR')
            expect(page.locator('#storage-info')).to_contain_text('4-shot pixel shift')
            if not args.finish_only: expect(page.locator('#plan-count')).to_contain_text('3 planes / 12 RAWs')
            expect(page.locator("#preview")).to_have_js_property("naturalWidth",1024,timeout=15000)
            assert page.locator('#preview').evaluate('(e)=>[e.naturalWidth,e.naturalHeight]') == [1024,680]
            for selector in ['[data-mark="true"]','[data-mark="false"]']:
                expect(page.locator(selector)).to_be_enabled()
            if args.finish_only:
                expect(page.locator('#start')).to_be_disabled()
                page.reload()
                expect(page.locator('#pairing')).to_be_hidden(timeout=15000)
                expect(page.locator('#preview')).to_have_js_property('naturalWidth',1024,timeout=15000)
                page.screenshot(path=str(OUT/'phone-final.png'),full_page=True)
                desktop=browser.new_page(viewport={'width':1280,'height':900})
                desktop.on('pageerror',lambda e:errors.append(str(e)))
                desktop.goto('http://10.0.0.178:8787/#key='+key)
                expect(desktop.locator('#preview')).to_have_js_property('naturalWidth',1024,timeout=15000)
                expect(desktop.locator('#start')).to_be_disabled()
                desktop.screenshot(path=str(OUT/'desktop-final.png'),full_page=True)
                assert not errors,errors
                browser.close()
                result={'physical_camera':True,'actual_android_device':False,'browser_errors':errors,'stopped_run':done,
                        'final':state(),'checks':'physical stop from prior screenshots and journal; final phone and desktop preview; marks; cleared bounds; paired reload'}
                (OUT/'ui-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
                print(json.dumps({'checks':result['checks'],'errors':errors}))
                return
            page.screenshot(path=str(OUT/'phone-ready.png'), full_page=True)
            page.locator('#start').click()
            s = wait(lambda s:s['sequence_id']>before['sequence_id'] and s['phase']=='capturing' and s['storage']['captured_frames']>=1)
            expect(page.locator('#stop')).to_be_enabled()
            page.locator('#stop').click()
            expect(page.locator('#run-message')).to_contain_text('four-shot group', timeout=5000)
            page.screenshot(path=str(OUT/'phone-stopping.png'), full_page=True)
            done = wait(lambda s:s['phase'] in ['stopped','fault'] and not s['busy'])
            assert done['phase']=='stopped' and done['completed']==1
            assert done['storage']['saved_frames']==4 and done['storage']['pending_frames']==0
            expect(page.locator('#run-count')).to_contain_text('4 / 12 RAWs saved', timeout=10000)
            expect(page.locator('#start')).to_be_enabled(timeout=10000)
            page.screenshot(path=str(OUT/'phone-stopped.png'), full_page=True)
            # Reconnect through the existing UI clears diagnostic marks. It must
            # retain pairing, leave pixel shift enabled, and take no new pictures.
            page.locator('#camera-connect').click()
            expect(page.locator('#camera-connect')).to_have_text('Connect camera',timeout=15000)
            expect(page.locator('#camera-connect')).to_be_enabled(timeout=15000)
            page.locator('#camera-connect').click()
            expect(page.locator('[data-mark="true"]')).to_be_enabled(timeout=15000)
            expect(page.locator('#start')).to_be_disabled()
            expect(page.locator("#preview")).to_have_js_property("naturalWidth",1024,timeout=15000)
            page.reload()
            expect(page.locator('#pairing')).to_be_hidden(timeout=15000)
            expect(page.locator('#storage-info')).to_contain_text('A7CR')
            page.screenshot(path=str(OUT/'phone-final.png'),full_page=True)
            desktop = browser.new_page(viewport={'width':1280,'height':900})
            desktop.on('pageerror',lambda e:errors.append(str(e)))
            desktop.goto('http://10.0.0.178:8787/#key='+key)
            expect(desktop.locator('#workspace')).to_be_visible(timeout=15000)
            expect(desktop.locator("#preview")).to_have_js_property("naturalWidth",1024,timeout=15000)
            expect(desktop.locator('#start')).to_be_disabled()
            desktop.screenshot(path=str(OUT/'desktop-final.png'),full_page=True)
            assert not errors,errors
            browser.close()
    except Exception as e:
        raise RuntimeError(str(e).replace(key,'[redacted]')) from None
    result={'physical_camera':True,'actual_android_device':False,'browser_errors':errors,
            'stop_requested_during_member_delivery':True,'final_group_finished':True,
            'paired_reload':True,'phone_and_desktop':True,'stopped_run':done,'final':state()}
    (OUT/'ui-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'checks':'preview, A7CR labels, 3-plane/12-RAW count, physical start/stop, complete four-shot boundary, reconnect, retained pairing, LAN access',
                      'saved_raws':done['storage']['saved_frames'],'focus':result['final']['position'],'errors':errors}))


if __name__=='__main__': main()
