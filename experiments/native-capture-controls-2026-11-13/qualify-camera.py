"""Five physical RAWs, and an oversized-plan refusal with no shutter or focus move."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from deploy import api,restore,OUT

def settled(): return api.wait(lambda s:s['editable'] and not s['busy'],timeout=25)
def mark(position,start):
    api.command('focus',target=position);settled();api.command('mark',start=start)

def main():
    before=api.state();assert before['editable'] and not before['busy'] and before['storage'].get('pending_frames',0)==0
    report={'before':before,'runs':[]}
    try:
        api.command('pixel_shift',shots=4);settled()
        start=before['position'];end=start+1800 if start<63000 else start-1800
        mark(start,True);mark(end,False)
        api.command('settings',step=1,settle_ms=500,approach=128,capture_timeout_s=120)
        large=api.state();assert large['storage_error'] and large['storage_required_bytes']>large['storage']['free_bytes']
        sequence=large['sequence_id'];position=large['position']
        api.command('start')
        refused=api.wait(lambda s:not s['busy'] and 'Shorten the stack' in s['message'])
        assert refused['position']==position and refused['sequence_id']==sequence
        assert not refused.get('failure') and refused['storage'].get('pending_frames',0)==0
        report['oversized_refusal']={k:refused[k] for k in ['message','position','sequence_id','storage_required_bytes','storage_error']}
        mark(start,True);mark(start,False)
        for shots in [1,4]:
            api.command('pixel_shift',shots=shots);s=settled()
            assert s['shots_per_plane']==shots and not s['storage_error']
            initial=s['initial_seconds'];expected=s['sequence_id']+1
            began=time.monotonic();api.command('start')
            s=api.wait(lambda s:s['sequence_id']==expected and s['phase'] in ['complete','fault','stopped'] and not s['busy'],timeout=100)
            assert s['phase']=='complete',s['message']
            assert s['storage']['saved_frames']==shots and s['storage']['pending_frames']==0
            receipt=s['storage']['receipt'];folder=Path(receipt['path']).parent
            raws=list(folder.glob('*.ARW.straw'));assert len(raws)==shots and not list(folder.glob('*.ARW'))
            manifest=json.loads((folder/'manifest.json').read_text())
            result=json.loads((folder/'result.json').read_text())
            assert manifest['camera']['pixel_shift_shots']==shots and result['outcome']=='complete'
            report['runs'].append({'shots':shots,'folder':str(folder),'files':[p.name for p in raws],
                'initial_seconds':initial,'wall_seconds':time.monotonic()-began,'timer':s['timer'],'receipt':receipt})
        assert report['runs'][1]['initial_seconds']>report['runs'][0]['initial_seconds']
    finally:
        if api.state()['editable']:restore(before)
        report['after']=api.state()
        (OUT/'camera-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['after']['position']==before['position'] and report['after']['plan']==before['plan']
    print(json.dumps({'oversized_refusal':report['oversized_refusal'],'runs':report['runs'],'focus_and_plan_restored':True},indent=2))

if __name__=='__main__':main()
