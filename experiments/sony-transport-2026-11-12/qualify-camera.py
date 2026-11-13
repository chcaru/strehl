"""Three physical RAW captures through the existing UI API and production receiver."""
import hashlib
import io
import json
from pathlib import Path
import time
import uuid
import numpy as np
import rawpy
import requests
from PIL import Image
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/sony-edup-2026-11-12'))
from remote import BASE, ssh
OUT=Path(__file__).resolve().parents[2]/'outputs/sony-transport-2026-11-12'

CFG=json.loads((BASE/'private/headless.json').read_text())
URL='http://10.0.0.178:8787'
HEADERS={'Authorization':'Bearer '+CFG['pairing_key']}


def state():
    r=requests.get(URL+'/api/state',headers=HEADERS,timeout=8);r.raise_for_status();return r.json()


def command(op,**args):
    s=state()
    r=requests.post(URL+'/api/command',headers=HEADERS,json={'id':str(uuid.uuid4()),
        'camera_revision':s['camera_revision'],'plan_revision':s['plan_revision'],
        'sequence_id':s['sequence_id'],'command':{'op':op,**args}},timeout=8)
    r.raise_for_status()


def wait(test,timeout=35):
    end=time.monotonic()+timeout
    while True:
        s=state()
        if s['failure']:raise RuntimeError(s['failure']['message'])
        if test(s):return s
        if time.monotonic()>end:raise TimeoutError('Camera state wait expired')
        time.sleep(.2)


def network():
    p=ssh("from pathlib import Path;import json,subprocess;print(json.dumps({'tx':{i:int(Path('/sys/class/net/'+i+'/statistics/tx_bytes').read_text()) for i in ['wlan0','wlan1']},'route':subprocess.run(['ip','route','get','10.0.0.109'],capture_output=True,text=True).stdout}))",root=True,host='10.0.0.178')
    assert p.returncode==0,p.stderr
    return json.loads(p.stdout)


def capture():
    initial=wait(lambda s:s['editable'] and s['preview']['fresh'])
    assert not initial['start_set'] and not initial['end_set'], 'Preserve user focus marks'
    assert initial['plan']['step']==1 and initial['plan']['settle_ms']==500
    assert 200<initial['position']<65000
    (OUT/'capture-initial.json').write_text(json.dumps(initial,indent=2)+'\n')
    command('mark',start=True)
    command('jog',delta=1)
    wait(lambda s:s['editable'] and s['position']==initial['position']+1)
    command('jog',delta=1)
    wait(lambda s:s['editable'] and s['position']==initial['position']+2)
    command('mark',start=False)
    plan=state();assert plan['planned']==3
    before=network();assert 'dev wlan1' in before['route']
    command('start')
    completed=wait(lambda s:s['phase']=='complete',timeout=240)
    after=network()
    (OUT/'capture-completed.json').write_text(json.dumps(completed,indent=2)+'\n')
    (OUT/'capture-network.json').write_text(json.dumps({'before':before,'after':after},indent=2)+'\n')
    return initial,completed,{'before':before,'after':after}


def finish(initial,completed,network_pair=None,restored=False):
    assert completed['completed']==3 and completed['storage']['pending_frames']==0
    folder=Path(completed['storage']['receipt']['path']).parent
    receipts=[json.loads(l) for l in (folder/'transfer-receipts.jsonl').read_text().splitlines()]
    raws=sorted(folder.glob('*.ARW'));assert len(raws)==3
    rows=[]
    for path in raws:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        receipt=next(r for r in receipts if Path(r['path']).name==path.name)
        assert receipt['encoding']=='strehl-raw-v1'
        assert receipt['durable'] and receipt['sha256']==digest and receipt['bytes']==path.stat().st_size
        with rawpy.imread(str(path)) as raw:
            plane=raw.raw_image_visible.copy()
        assert plane.shape==(4688,7028) and plane.dtype==np.uint16
        rows.append({'file':str(path),'bytes':path.stat().st_size,'sha256':digest,
                     'visible_shape':list(plane.shape),'dtype':str(plane.dtype),'receipt':receipt})
    deltas=None
    if network_pair:
        before,after=network_pair['before'],network_pair['after']
        deltas={i:after['tx'][i]-before['tx'][i] for i in before['tx']}
        total=sum(r['receipt']['wire_bytes'] for r in rows)
        assert deltas['wlan1']>.9*total and deltas['wlan0']<.1*total
    if not restored:
        command('go',start=True)
        wait(lambda s:s['editable'] and s['position']==initial['position'])
        command('disconnect');wait(lambda s:not s['connected'] and not s['busy'])
        command('connect')
    ready=wait(lambda s:s['editable'] and s['preview']['fresh'])
    assert ready['position']==initial['position'] and not ready['start_set'] and not ready['end_set']
    assert all(ready['plan'][k]==initial['plan'][k] for k in ['step','settle_ms','approach','capture_timeout_s'])
    for attempt in range(20):
        r=requests.get(URL+'/api/preview',headers=HEADERS,timeout=8);r.raise_for_status()
        try:
            image=Image.open(io.BytesIO(r.content));image.load();assert image.width>=640
            break
        except (OSError,AssertionError):
            if attempt==19:raise
            time.sleep(.25)
    image.save(OUT/'final-live-preview.jpg',quality=95)
    result={'physical_captures':3,'folder':str(folder),'exact_receipts_and_decodes':rows,
            'tx_deltas':deltas,'focus_returned_to':ready['position'],'phase':ready['phase'],
            'pending_frames':ready['storage']['pending_frames'],'preview_size':list(image.size),
            'camera_settings_unchanged':True,'compression_enabled_in_production':True}
    (OUT/'camera-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--finish-existing',action='store_true');parser.add_argument('--verify-restored',action='store_true');args=parser.parse_args()
    if args.finish_existing or args.verify_restored:
        initial=json.loads((OUT/'capture-initial.json').read_text())
        completed=json.loads((OUT/'capture-completed.json').read_text())
        current=state()
        if args.verify_restored:
            assert current['phase']=='ready' and current['position']==initial['position'] and not current['busy'] and not current['start_set'] and not current['end_set']
        else:
            assert current['phase']=='complete' and current['plan']==completed['plan'] and current['position']==completed['position'] and not current['busy']
        finish(initial,completed,restored=args.verify_restored)
    else:
        finish(*capture())
