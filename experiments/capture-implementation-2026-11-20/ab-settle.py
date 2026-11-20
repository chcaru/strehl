"""A/B: settle after the focus result, interleaved runs of the same planes.
  ab-settle.py <start> <planes> <settle,settle,...>   (prints folders and the engine's verdicts)"""
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import cmd, state, wait  # noqa: E402

start, planes, settles = int(sys.argv[1]), int(sys.argv[2]), [int(x) for x in sys.argv[3].split(',')]
results = []
for settle in settles:
    s = wait(lambda a: not a['busy'], timeout=60)
    p = s['plan']
    cmd('settings', step=p['step'], settle_ms=settle, approach=p['approach'], capture_timeout_s=p['capture_timeout_s'])
    wait(lambda a: not a['busy'] and a['plan']['settle_ms'] == settle)
    s = state()
    seq = s['sequence_id'] + 1
    t0 = time.time()
    cmd('capture_positions', positions=[start + 8 * i for i in range(planes)])
    wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=60)
    s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected') and not a['busy'], timeout=600)
    folder = pathlib.Path(s['storage']['receipt']['path']).parent
    wall = time.time() - t0
    out = subprocess.run([str(ROOT / 'target/release/strehl.exe'), 'pixel-shift', str(folder)], capture_output=True, text=True).stdout
    rows = re.findall(r'plane\s+(\d+)\s+: .*witness shift max ([\d.]+) px .*z2 mean ([\d.]+) .*p99 ([\d.]+) \| (\w+)', out)
    events = [json.loads(l) for l in open(folder / 'events.jsonl', encoding='utf-8')]
    caps = [e['unix_ms'] for e in events if e['event'] == 'capture_intent']
    period = (caps[-1] - caps[0]) / 1000 / (len(caps) - 1)
    passed = sum(1 for r in rows if r[4] == 'pass')
    print('settle %4d ms: %s  wall %.1f s, plane period %.2f s, %d/%d pass, witness shift max per plane %s' % (
        settle, folder.name, wall, period, passed, len(rows), ' '.join(r[1] for r in rows)), flush=True)
    results.append(dict(settle=settle, folder=str(folder), period=period, rows=rows))
(pathlib.Path(__file__).parent / ('ab-settle-%d.json' % int(time.time()))).write_text(json.dumps(results, indent=1))
