#!/usr/bin/env python3
"""Real browser and HTTP checks; uses simulated focus and explicit transfer fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import socket
import subprocess
import time
import requests
from playwright.sync_api import sync_playwright,expect

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--bin',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);binary=a.bin.resolve()
    rp,hp=port(),port();key=secrets.token_hex(24);camera_key=secrets.token_hex(24)
    rc=dict(bind=f'127.0.0.1:{rp}',lan='10.0.0.0/24',key=key,folder=str(out/'raw-fixtures'))
    hc=dict(bind=f'127.0.0.1:{hp}',pairing_key=camera_key,bridge='',journal_directory=str(out/'journals'),transfer=dict(receiver=f'http://127.0.0.1:{rp}',key=key,lan='10.0.0.0/24',ram_directory=str(out/'ram'),state_directory=str(out/'state')))
    for name,value in [('receiver',rc),('headless',hc)]:(out/f'{name}.json').write_text(json.dumps(value))
    processes=[];logs=[];checks=[]
    def launch(name,args):
        log=(out/f'{name}-{len(processes)}.log').open('wb');logs.append(log)
        process=subprocess.Popen([str(binary/f'strehl-capture-{name}.exe')]+args,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);processes.append(process);return process
    def await_http(url):
        end=time.monotonic()+20
        while time.monotonic()<end:
            try:
                if requests.get(url,timeout=1).status_code==200:return
            except requests.RequestException:pass
            time.sleep(.1)
        raise RuntimeError('Server did not start')
    try:
        launch('receiver',['--config',str(out/'receiver.json')]);headless=launch('headless',['--config',str(out/'headless.json'),'--demo'])
        receiver=f'http://127.0.0.1:{rp}';camera=f'http://127.0.0.1:{hp}'
        await_http(receiver);await_http(camera)
        assert requests.get(receiver+'/api/status').status_code==401
        assert requests.get(receiver+'/api/status',headers={'Authorization':'Bearer '+key,'Origin':'https://unrelated.example'}).status_code==403
        auth={'Authorization':'Bearer '+key}
        assert requests.post(receiver+'/api/runs/stack-ui-fixture',headers=auth).status_code==200
        data=bytes(range(256))*262144;digest=hashlib.sha256(data).hexdigest()
        url=receiver+'/api/files/stack-ui-fixture/frame-000001.ARW'
        bad=requests.put(url,headers=auth|{'x-content-sha256':'0'*64},data=data,timeout=30)
        assert bad.status_code!=200 and not (out/'raw-fixtures/stack-ui-fixture/frame-000001.ARW').exists()
        good=requests.put(url,headers=auth|{'x-content-sha256':digest},data=data,timeout=30)
        assert good.status_code==200 and good.json()['durable'] and good.json()['sha256']==digest
        again=requests.put(url,headers=auth|{'x-content-sha256':digest},data=data,timeout=30)
        assert again.status_code==200 and again.json()['already_saved']
        assert hashlib.sha256((out/'raw-fixtures/stack-ui-fixture/frame-000001.ARW').read_bytes()).hexdigest()==digest
        checks+=['API authentication and cross-origin rejection','64 MiB fixture SHA-256 and on-disk readback','bad checksum rejected without committed file','duplicate upload idempotent']
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
            context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(camera+'/#key='+camera_key);page.get_by_role('button',name='Connect camera',exact=True).click()
            expect(page.locator('#position')).not_to_have_text('—',timeout=20000)
            expect(page.locator('#preview')).to_be_visible(timeout=15000)
            assert page.locator('#preview').evaluate('(e)=>e.naturalWidth')>0
            page.locator('[data-mark="true"]').click();page.locator('[data-jog="16"]').click()
            expect(page.locator('[data-mark="false"]')).to_be_enabled(timeout=10000);page.locator('[data-mark="false"]').click()
            expect(page.locator('#start')).to_be_enabled();page.screenshot(path=str(out/'phone-focus.png'),full_page=True)
            page.locator('#start').click();expect(page.locator('#pause')).to_be_enabled(timeout=10000);page.locator('#pause').click()
            expect(page.locator('#pause')).to_have_text('Resume',timeout=20000);page.locator('#pause').click()
            expect(page.locator('#pause')).to_have_text('Pause',timeout=10000);page.locator('#stop').click()
            expect(page.locator('#start')).to_be_visible(timeout=20000)
            expect(page.locator('#run-message')).to_contain_text('Stopped',timeout=20000)
            checks+=['phone live JPEG and mark A/B','headless start/pause/resume/stop']
            headless.terminate();headless.wait(timeout=10)
            launch('headless',['--config',str(out/'headless.json'),'--demo']);await_http(camera)
            page.reload();expect(page.locator('#camera-connect')).to_be_enabled(timeout=20000);expect(page.locator('#pairing')).to_be_hidden()
            checks+=['persistent pairing survives controller restart']
            desktop=browser.new_page(viewport={'width':1300,'height':900});desktop.on('pageerror',lambda e:errors.append(str(e)))
            desktop.goto(receiver+'/#key='+key);expect(desktop.locator('#settings')).to_be_visible(timeout=15000)
            desktop.locator('#folder').fill(str(out/'next-stack-folder'));desktop.get_by_role('button',name='Save folder').click()
            expect(desktop.locator('#notice')).to_contain_text('Folder updated');desktop.screenshot(path=str(out/'receiver.png'),full_page=True)
            assert requests.post(receiver+'/api/runs/stack-second-fixture',headers=auth).json()['folder']==str(out/'next-stack-folder/stack-second-fixture') or (out/'next-stack-folder/stack-second-fixture').is_dir()
            assert (out/'raw-fixtures/stack-ui-fixture/frame-000001.ARW').exists()
            checks+=['receiver folder changes apply only to future stacks','receiver desktop UI']
            assert not errors,errors
            browser.close()
        (out/'verification.json').write_text(json.dumps(dict(status='passed',checks=checks,fixture_bytes=len(data),fixture_sha256=digest,physical_camera_tested=False),indent=2)+'\n')
        print(json.dumps(dict(status='passed',checks=checks)))
    finally:
        for process in processes:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
        for log in logs:log.close()

if __name__=='__main__':main()
