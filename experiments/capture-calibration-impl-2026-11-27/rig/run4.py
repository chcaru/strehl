"""Run 4: stop mid-survey, run the rest, the proof, a core sample from the kept survey."""
import json
import sys
import time

sys.path.insert(0, 'C:/strehl-scratch/rig-1')
import drive  # noqa: E402


def cal():
    return drive.tools(drive.snapshot()).get('calibration') or {}


def wait(pred, timeout, label):
    t0 = time.time()
    while time.time() - t0 < timeout:
        c = cal()
        if pred(c):
            print('%-28s %5.0f s' % (label, time.time() - t0), flush=True)
            return c
        time.sleep(4)
    raise SystemExit('timed out: ' + label + ' ' + json.dumps(cal().get('pass'))[:400])


subprocess_setup = drive.main
sys.argv = ['drive.py', 'setup']
drive.main()
print(drive.call({'operation': 'open_capture'}))
time.sleep(4)
print(drive.call({'operation': 'calibrate'}))
wait(lambda c: (c.get('pass') or {}).get('stage') == 'survey' and c.get('stage') == 'capturing', 600, 'survey capturing')
time.sleep(30)
print(drive.call({'operation': 'stop_calibration'}))
c = wait(lambda c: (c.get('pass') or {}).get('stage') == 'failed' and c.get('stage') in ('done', 'failed', 'idle'), 600, 'stopped')
print('stopped_in', c['pass'].get('stopped_in'), 'error', c['pass'].get('error'))
print(drive.call({'operation': 'resume_calibration'}))
c = wait(lambda c: (c.get('pass') or {}).get('stage') in ('done', 'failed'), 1200, 'rest finished')
p = c['pass']
d = p.get('survey_depth') or {}
print('stage', p.get('stage'), 'error', p.get('error'), 'in focus', d.get('in_focus_first'), d.get('in_focus_last'),
      'seeded', p.get('seeded'), 'offset_measured', p.get('offset_measured'), 'light_on', c.get('light_on_seconds'))
c = wait(lambda c: (c.get('proof') or {}).get('results') or ((c.get('proof') or {}).get('error') and not c['proof'].get('running')), 300, 'proof')
print('proof', c['proof'].get('line'), c['proof'].get('error'), 'survey kept', c.get('survey_kept'))
for col, row in [(74, 49), (70, 49), (78, 49), (74, 45), (74, 53), (66, 49), (82, 49)]:
    print(drive.call({'operation': 'pin_core_sample', 'column': col, 'row': row}))
    c = wait(lambda c: not (c.get('core_sample') or {}).get('reading'), 120, 'core sample %d,%d' % (col, row))
    cs = c.get('core_sample') or {}
    print(json.dumps(cs)[:700])
    if cs.get('sample'):
        break
