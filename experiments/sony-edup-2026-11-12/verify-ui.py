"""Read-only real browser checks of the deployed camera and receiver interfaces."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from remote import BASE,OUT


def main():
    camera_key=json.loads((BASE/'private/headless.json').read_text())['pairing_key']
    receiver_key=json.loads((Path.home()/'AppData/Local/StrehlCaptureReceiver/receiver.json').read_text())['key']
    errors=[];checks=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
            for label,host,mobile in [('phone-edup','10.0.0.178',True),('desktop-existing-address','10.0.0.187',False)]:
                context=browser.new_context(viewport={'width':390 if mobile else 1280,'height':844 if mobile else 900},is_mobile=mobile,has_touch=mobile)
                page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto('http://'+host+':8787/#key='+camera_key)
                expect(page.locator('#workspace')).to_be_visible(timeout=15000)
                expect(page.locator('#connection-label')).to_contain_text('Camera connected')
                expect(page.locator('#preview')).to_be_visible(timeout=15000)
                page.wait_for_function("document.querySelector('#preview').naturalWidth > 0")
                expect(page.locator('[data-mark="true"]')).to_be_enabled()
                expect(page.locator('[data-mark="false"]')).to_be_enabled()
                expect(page.locator('#start')).to_be_disabled()
                assert page.locator('#pairing').is_hidden()
                image=page.locator('#preview').evaluate('(e)=>[e.naturalWidth,e.naturalHeight]')
                page.screenshot(path=str(OUT/(label+'.png')),full_page=True)
                checks.append({'view':label,'preview_size':image,'focus_marks_enabled':True,'unmarked_start_disabled':True})
                context.close()
            page=browser.new_page(viewport={'width':1280,'height':900})
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto('http://127.0.0.1:8789/#key='+receiver_key)
            expect(page.locator('#settings')).to_be_visible(timeout=15000)
            folder=page.locator('#folder').input_value()
            assert 'StrehlCaptures' in folder
            page.screenshot(path=str(OUT/'receiver-desktop.png'),full_page=True)
            checks.append({'view':'receiver-desktop','configured_destination':folder})
            assert not errors,errors
            browser.close()
    except Exception as e:
        raise RuntimeError(str(e).replace(camera_key,'[redacted]').replace(receiver_key,'[redacted]')) from None
    result={'checks':checks,'browser_errors':errors,'actual_android_device_tested':False,'production_ui':True}
    (OUT/'ui-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
