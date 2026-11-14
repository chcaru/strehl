"""Phone controls against an isolated simulator; no production keys or camera."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'outputs/native-capture-controls-2026-11-13/phone-ui'

def main():
    OUT.mkdir(exist_ok=False)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    key='0123456789abcdef'*3
    config=OUT/'headless.json'
    config.write_text(json.dumps({'bind':f'127.0.0.1:{port}','pairing_key':key,'bridge':'',
        'journal_directory':str(OUT/'journal'),'transfer':{'receiver':'http://127.0.0.1:1','key':key,'lan':'10.0.0.0/24','ram_directory':str(OUT/'ram'),'state_directory':str(OUT/'state')}}))
    process=None
    try:
        with (OUT/'headless.log').open('w') as log:
            process=subprocess.Popen([str(ROOT/'target/debug/strehl-capture-headless.exe'),'--config',str(config),'--demo'],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':412,'height':915},device_scale_factor=1)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            for _ in range(30):
                try:page.goto(f'http://127.0.0.1:{port}/#key={key}');break
                except Exception:time.sleep(.2)
            page.wait_for_function('()=>!document.querySelector("#camera-connect").disabled')
            page.locator('#camera-connect').click()
            page.wait_for_function('()=>window.document.querySelector("#focus-slider") && !document.querySelector("#focus-slider").disabled')
            page.wait_for_function('()=>document.querySelector("#preview").naturalWidth>0')
            initial=int(page.locator('#position').inner_text())
            # Keyboard edits exercise the real range input and coalescing code.
            slider=page.locator('#focus-slider');slider.focus()
            for _ in range(5):slider.press('ArrowRight')
            page.wait_for_function('(n)=>Number(document.querySelector("#position").textContent)===n',arg=initial+5)
            page.wait_for_function('()=>!document.querySelector("[data-mark=true]").disabled')
            page.locator('[data-mark=true]').click();page.locator('[data-mark=false]').click()
            page.wait_for_function('()=>!document.querySelector("#start").disabled')
            single=page.locator('#initial-estimate').inner_text()
            page.locator('#pixel-shift').click()
            page.wait_for_function('()=>document.querySelector("#plan-count").textContent.includes("4 RAWs")')
            four=page.locator('#initial-estimate').inner_text();assert single!=four
            assert page.locator('#roi').is_hidden()
            assert page.locator('#peaking-overlay').is_visible()
            # Verify the peaking canvas has nontransparent highlighted detail.
            highlighted=page.locator('#peaking-overlay').evaluate('(c)=>{const p=c.getContext("2d").getImageData(0,0,c.width,c.height).data;let n=0;for(let i=3;i<p.length;i+=4)n+=p[i]>0;return n;}')
            assert highlighted>0
            page.screenshot(path=str(OUT/'phone-controls.png'),full_page=True)
            page.locator('#start').click()
            page.wait_for_function('()=>document.querySelector("#run-message").textContent.toLowerCase().includes("complete")')
            page.wait_for_function('()=>!document.querySelector("#pixel-shift").disabled')
            page.locator('#pixel-shift').click()
            page.wait_for_function('()=>!document.querySelector("#plan-count").textContent.includes("4 RAWs")')
            assert not errors,errors
            report={'focus_slider_readback':initial+5,'single_estimate':single,'four_estimate':four,'peaking_pixels':highlighted,'permanent_roi_hidden':True,'single_four_toggle':True,'page_errors':errors}
            (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
            browser.close()
    finally:
        if process is not None and process.poll() is None:process.terminate();process.wait(timeout=10)

if __name__=='__main__':main()
