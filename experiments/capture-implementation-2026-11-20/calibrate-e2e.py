"""Calibrate step end to end through the desktop's control interface (headless, no window).

  python calibrate-e2e.py <Strehl.exe> <scratch dir> <start> <end> <out.json> [compact-test-run]

Launches the desktop headless with native Capture, marks the bounds through capture commands,
sends `calibrate_step`, and polls the snapshot until the calibration is done or failed.
Records the camera's pixel-shift mode before and after (it must come back), the survey folder
(it must be deleted), and the result. With a run name, also exercises `measure_focus_step`
and the compact estimate on that completed capture (never `apply`). Shuts the session down.
Prints no keys: the capture settings file is passed by path only.
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
exe, scratch = sys.argv[1], pathlib.Path(sys.argv[2])
start, end, out = int(sys.argv[3]), int(sys.argv[4]), pathlib.Path(sys.argv[5])
extra = sys.argv[6] if len(sys.argv) > 6 else None
scratch.mkdir(parents=True, exist_ok=True)
session = scratch / ('ready-%d.json' % int(time.time()))
ctl = [sys.executable, str(ROOT / 'scripts/strehl-control.py'), '--exe', exe, '--session-file', str(session), '--timeout', '60']
settings = pathlib.Path(os.environ['LOCALAPPDATA']) / 'Strehl' / 'capture.json'


def run(args, stdin=None):
    r = subprocess.run(ctl + args, input=stdin, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('control %s failed: %s' % (args[0], (r.stdout + r.stderr)[-600:]))
    return json.loads(r.stdout) if r.stdout.strip() else None


def snap():
    d = run(['snapshot'])['data']
    r = d['result']
    r['revision'] = d['revision']
    return r


def call(command):
    data = snap()
    req = json.dumps({'expected_revision': data['revision'], 'command': command})
    return run(['call', '--request', '-'], stdin=req)


def capture_command(command):
    st = snap()['capture']['state']
    req = {'id': str(uuid.uuid4()), 'camera_revision': st['camera_revision'], 'plan_revision': st['plan_revision'],
           'sequence_id': st['sequence_id'], 'command': command}
    return call({'operation': 'capture_command', 'request': req})


def until(pred, timeout, what):
    end_at = time.time() + timeout
    while time.time() < end_at:
        d = snap()
        if pred(d):
            return d
        time.sleep(1.0)
    raise RuntimeError('timed out waiting for ' + what)


record = {}
run(['launch', '--capture', '--capture-settings', str(settings), '--output-dir', str(scratch / 'results'),
     '--catalog', str(scratch / 'catalog.projects.json')])
try:
    call({'operation': 'open_capture'})
    d = until(lambda d: d['capture'].get('state', {}).get('editable') is True, 120, 'the camera')
    record['shots_before'] = d['capture']['state']['shots_per_plane']
    for target, mark_start in ((start, True), (end, False)):
        capture_command({'op': 'focus', 'target': target})
        until(lambda d: d['capture']['state'].get('position') == target and not d['capture']['state'].get('busy'), 60, 'focus')
        capture_command({'op': 'mark', 'start': mark_start})
        time.sleep(1.5)
    d = until(lambda d: d['capture']['state'].get('start_set') and d['capture']['state'].get('end_set'), 30, 'the bounds')
    before = {p.name for p in pathlib.Path('D:/StrehlCaptures').iterdir()}
    t0 = time.time()
    call({'operation': 'calibrate_step'})
    stages = []
    d = None
    while time.time() - t0 < 900:
        d = snap()
        stage = d['capture']['tools']['calibration']['stage']
        if not stages or stages[-1][1] != stage:
            stages.append((round(time.time() - t0, 1), stage))
            print(stages[-1], flush=True)
        if stage in ('done', 'failed'):
            break
        time.sleep(1.0)
    record['stages'] = stages
    record['result'] = d['capture']['tools']['calibration']['result']
    after = {p.name for p in pathlib.Path('D:/StrehlCaptures').iterdir()}
    record['survey_runs_left'] = sorted(after - before)
    d = until(lambda d: not d['capture']['state'].get('busy'), 60, 'idle')
    record['shots_after'] = d['capture']['state']['shots_per_plane']
    record['plan_after'] = d['capture']['state'].get('plan')
    if extra:
        completed = d['capture'].get('completed') or []
        index = next(i for i, c in enumerate(completed) if pathlib.Path(c['folder']).name == extra)
        call({'operation': 'measure_focus_step', 'index': index})
        d = until(lambda d: not d['capture']['tools']['focus_step']['running'] and d['capture']['tools']['focus_step']['result'], 300, 'focus step')
        record['focus_step'] = d['capture']['tools']['focus_step']['result']
        call({'operation': 'compact_capture', 'index': index, 'apply': False})
        d = until(lambda d: not d['capture']['tools']['compact_estimate']['running'] and d['capture']['tools']['compact_estimate']['result'], 300, 'compact estimate')
        record['compact_estimate'] = {k: d['capture']['tools']['compact_estimate']['result'].get(k) for k in ('before_bytes', 'estimated_after_bytes', 'added_variance', 'applied', 'error')}
finally:
    try:
        run(['shutdown'])
    except Exception as e:  # noqa: BLE001
        record['shutdown_error'] = str(e)
out.write_text(json.dumps(record, indent=1) + '\n')
print(json.dumps(record, indent=1)[:3000])
