"""Error correction end to end on the rig, without the desktop window: a capture with error
correction on, `strehl follow` checking it as it arrives, and a relay posting each group's
verdict to this PC's receiver as the desktop does. Planes listed in `forced` fail their first
check (STREHL_FOLLOW_RETAKE_PLANES), so the controller must go back and retake them.

  python ec-e2e.py <start> <planes> <step> <forced planes, e.g. 3,7> <out.json>

Prints the run, its plane period, the retakes recorded and the engine's group check.
The receiver key is read from its settings and never printed.
"""
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import cmd, state, wait  # noqa: E402

start, planes, step, forced, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
exe = ROOT / 'target/release/strehl.exe'
settings = json.loads(pathlib.Path(os.environ['LOCALAPPDATA'], 'StrehlCaptureReceiver', 'receiver.json').read_text(encoding='utf-8-sig'))
port = int(str(settings['bind']).rsplit(':', 1)[1])
key = settings['key']
captures = pathlib.Path(settings['folder'])
cache = pathlib.Path('C:/strehl-scratch/ec-cache')
cache.mkdir(parents=True, exist_ok=True)


def post(run, verdicts):
    body = json.dumps({'verdicts': verdicts}).encode()
    req = urllib.request.Request('http://127.0.0.1:%d/api/runs/%s/verdicts' % (port, run), data=body, method='POST',
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


s = wait(lambda a: not a['busy'], timeout=60)
if not s['error_correction']:
    cmd('error_correction', enabled=True)
    wait(lambda a: not a['busy'] and a['error_correction'] is True)
s = state()
before = {p.name for p in captures.iterdir()}
seq = s['sequence_id'] + 1
t0 = time.time()
cmd('capture_positions', positions=[start + step * i for i in range(planes)])
run = None
while run is None:
    new = [p for p in captures.iterdir() if p.name not in before and p.is_dir()]
    if new:
        run = new[0]
    time.sleep(0.2)
env = dict(os.environ, STREHL_CACHE_DIR=str(cache), STREHL_FOLLOW_RETAKE_PLANES=forced)
follow = subprocess.Popen([str(exe), 'follow', '--interval-ms', '500', str(run)], env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          creationflags=0x0000_4000)
posted = set()
stop = threading.Event()


def relay():
    while not stop.is_set():
        for journal in (cache / 'follow').glob(run.name + '-*.jsonl'):
            fresh = []
            for line in journal.read_text(errors='replace').splitlines():
                try:
                    v = json.loads(line)
                except ValueError:
                    continue
                if isinstance(v.get('group_id'), str) and isinstance(v.get('verdict'), str) and v['group_id'] not in posted:
                    fresh.append({'group_id': v['group_id'], 'plane': v.get('plane'), 'verdict': v['verdict'],
                                  'retake': v.get('retake') is True, 'reason': v.get('reason')})
            if fresh:
                post(run.name, fresh)
                posted.update(f['group_id'] for f in fresh)
        time.sleep(0.2)


threading.Thread(target=relay, daemon=True).start()
s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected') and not a['busy'], timeout=3600)
wall = time.time() - t0
time.sleep(3)
stop.set()
follow.terminate()
events = [json.loads(l) for l in open(run / 'events.jsonl', encoding='utf-8')]
kinds = {}
for e in events:
    kinds[e['event']] = kinds.get(e['event'], 0) + 1
retakes = [(e['data']['ordinal'] + 1, e['data']['retake'], e['data']['reason']) for e in events if e['event'] == 'retake_intent']
caps = [e['unix_ms'] for e in events if e['event'] == 'capture_intent']
check = subprocess.run([str(exe), 'pixel-shift', str(run)], capture_output=True, text=True).stdout
summary = {'run': run.name, 'phase': s['phase'], 'message': s['message'], 'wall_s': wall,
           'mean_capture_interval_s': (caps[-1] - caps[0]) / 1000 / (len(caps) - 1), 'events': kinds,
           'retakes': retakes, 'verdicts_posted': len(posted),
           'engine_check': [l for l in check.splitlines() if l.startswith(('groups', 'plane'))]}
pathlib.Path(out).write_text(json.dumps(summary, indent=1) + '\n')
print(json.dumps({k: summary[k] for k in ('run', 'phase', 'wall_s', 'mean_capture_interval_s', 'events', 'retakes', 'verdicts_posted')}, indent=1))
print('\n'.join(summary['engine_check'][:16]))
