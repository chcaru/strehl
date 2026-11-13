"""Eight real exposures through the unchanged installed app; retain 500 ms default."""
import importlib.util
from pathlib import Path
import hashlib
import json
import time
import rawpy

spec=importlib.util.spec_from_file_location('probe',Path(__file__).with_name('run-probe.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
s=p.state()
assert s['phase']=='ready' and s['editable'] and not s['start_set'] and not s['end_set']
original_plan=s['plan'].copy();position=s['position']
p.command('mark',start=True)
p.command('jog',delta=1);p.wait(lambda s:s['editable'] and s['position']==position+1)
p.command('mark',start=False)
results=[]
try:
    for arm,settle in enumerate([500,100,100,500]):
        p.command('settings',step=1,settle_ms=settle,approach=original_plan['approach'],capture_timeout_s=120)
        assert p.state()['planned']==2
        sequence=p.state()['sequence_id']
        p.command('start')
        done=p.wait(lambda s:s['phase']=='complete' and s['sequence_id']>sequence,seconds=90)
        assert done['completed']==2 and done['saved']==2 and done['storage']['pending_frames']==0
        folder=Path(done['storage']['receipt']['path']).parent
        events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
        captures=[e for e in events if e['event']=='capture_buffered']
        assert len(captures)==2
        receipts=[json.loads(line) for line in (folder/'transfer-receipts.jsonl').read_text().splitlines()]
        files=[]
        for file in sorted(folder.glob('*.ARW')):
            digest=hashlib.sha256(file.read_bytes()).hexdigest()
            ack=next(r for r in receipts if Path(r['path']).name==file.name)
            assert ack['durable'] and ack['sha256']==digest and ack['bytes']==file.stat().st_size
            with rawpy.imread(str(file)) as raw:
                shape=raw.raw_image_visible.copy().shape
                assert shape==(4688,7028)
            files.append({'name':file.name,'bytes':file.stat().st_size,'sha256':digest,'shape':list(shape)})
        assert len(files)==2
        row={'arm':arm,'settle_ms':settle,'stack':str(folder),'state':done,'files':files,
             'interval_seconds':(captures[1]['unix_ms']-captures[0]['unix_ms'])/1000,
             'manifest':json.loads((folder/'manifest.json').read_text()),'events':events}
        results.append(row)
        (p.out/'settle-comparison.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps({'arm':arm,'settle_ms':settle,'interval_seconds':row['interval_seconds'],'raws':len(files)}),flush=True)
finally:
    state=p.state()
    if state['failure']:
        (p.out/'settle-fault.json').write_text(json.dumps(state,indent=2)+'\n')
        assert not state['failure']['exposure_uncertain'], 'Inspect uncertain exposure before recovery'
        p.command('recover',acknowledge_uncertain=False)
        p.wait(lambda s:s['phase']=='ready' and s['preview']['fresh'])
    assert not p.state()['busy'], 'Preserve active camera work'
    p.command('settings',step=original_plan['step'],settle_ms=original_plan['settle_ms'],
              approach=original_plan['approach'],capture_timeout_s=original_plan['capture_timeout_s'])
    p.command('disconnect');p.wait(lambda s:not s['connected'] and not s['busy'])
    p.command('connect');s=p.wait(lambda s:s['phase']=='ready' and s['preview']['fresh'])
    assert not s['start_set'] and not s['end_set'] and s['plan']['settle_ms']==original_plan['settle_ms']
    (p.out/'final-ready.json').write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps({'ready':s['phase'],'settle_restored_ms':s['plan']['settle_ms'],'pending':s['storage']['pending_frames']}))
