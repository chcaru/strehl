"""No shutter: test the documented 1/4 selector on an idle camera and restore it."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/sony-a7cr-2026-11-13'))
import deploy

OUT = ROOT / 'outputs/native-capture-controls-2026-11-13'


def main():
    before = deploy.state()
    assert before['editable'] and not before['busy']
    assert before['storage'].get('pending_frames', 0) == 0
    (OUT / 'before-camera.json').write_text(json.dumps(before, indent=2)+'\n')
    dest = '/home/strehl/strehl-ptp-controls-candidate'
    result = subprocess.run(['scp', *deploy.OPTIONS, '-o', 'HostKeyAlias=10.0.0.187',
        str(OUT/'arm64/strehl-sony-ptp'), 'strehl@10.0.0.178:'+dest], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    deploy.command('disconnect')
    deploy.wait(lambda s: not s['connected'] and not s['busy'])
    script = r'''
import json,subprocess,os
from pathlib import Path
path='/home/strehl/strehl-ptp-controls-candidate'
os.chmod(path,0o755)
assert not list(Path('/run/strehl-raw').glob('*.ARW'))
p=subprocess.Popen([path,'serve-host','/run/strehl-raw'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
def call(command):
 p.stdin.write(command+'\n');p.stdin.flush();return json.loads(p.stdout.readline())
results={'hello':json.loads(p.stdout.readline())}
try:
 results['configure']=call('configure')
 for key,cmd in [('before','status'),('single','pixel-shift\t1'),('after_single','status'),('four','pixel-shift\t4'),('after_four','status')]:
  r=call(cmd);results[key]=r if not r.get('properties') else {k:r.get(k) for k in ['ok','error','pixel_shift_shots','pixel_shift_options','raw_max_bytes'] }|{'properties':{k:v for k,v in r['properties'].items() if k in ['PixelShiftMode','PixelShiftShots','RAW_FileCompressionType','PredictedMaximumFileSize']}}
finally:
 results['close']=call('quit');p.wait(timeout=20)
print(json.dumps(results))
'''
    try:
        result = deploy.ssh(script, host='10.0.0.178', timeout=70)
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        (OUT/'mode-probe.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        deploy.command('connect')
        deploy.wait(lambda s:s['editable'] and not s['failure'])
        restore(before)


def restore(before):
    for key, start in [('start',True),('end',False)]:
        if before[key+'_set']:
            target=before['plan'][key]
            # Existing controller supports jog only: use its original direction-inspection
            # is impossible before marking. Keep the restored marks for the new Focus API.
            current=deploy.state()['position']
            while current!=target:
                distance=target-current
                delta=next(d for d in [128,16,1] if d<=abs(distance))*(1 if distance>0 else -1)
                deploy.command('jog',delta=delta)
                current=deploy.wait(lambda s:s['editable'])['position']
            deploy.command('mark',start=start)
    target=before['position'];current=deploy.state()['position']
    while current!=target:
        distance=target-current
        delta=next(d for d in [128,16,1] if d<=abs(distance))*(1 if distance>0 else -1)
        deploy.command('jog',delta=delta)
        current=deploy.wait(lambda s:s['editable'])['position']


if __name__=='__main__': main()
