"""Matte-subject capture for the A7CR full-potential prototype
(docs/captures-needed.md, 2026-11-15 request 1): a white scarab's scaled back,
same rig as the coin (capture 3), paired single-shot and four-shot stacks with
the same bounds and step through the controller's ordinary plan/Start path.
`strehl follow` checks each plane of the four-shot run live.

Preparation (2026-11-15, recorded in outputs/scarab-capture/prep.json):
- bounds from two live-preview focus sweeps (focus-sweep.py, 8x6 tiles): the
  back's tiles peak between 50460 and 51660; nothing is sharp past 51900; the
  frame's top edge and corners fall away to about 48800 and are left out;
- exposure from two single-shot test RAWs at focus 51563: 1/10 s put green's
  brightest photosite at 1572 of 14848 DN of headroom; 0.6 s measured 9661
  (6.1x), nothing near white. ISO 100, f/5.6 (wide open with the 2x TC).

  python -X utf8 capture-scarab.py --start 50300 --end 51860 --step 8 --shutter 393226

Checks the plan and exposure the controller reports before each run, and
refuses rather than silently capturing something else. Leaves the marks and
plan in place; restores the pixel-shift mode and the parked focus.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/a7cr-calibration-2026-11-14'))
import darks  # noqa: E402

api = darks.api
OUT = ROOT / 'outputs/scarab-capture'
STREHL = ROOT / 'target-ui/release/strehl.exe'


def log(*a):
    line = time.strftime('%H:%M:%S') + ' ' + ' '.join(str(x) for x in a)
    print(line, flush=True)
    with (OUT / 'capture.log').open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def run(shots, label, want, follow=False):
    s = darks.settled()
    if s['shots_per_plane'] != shots:
        api.command('pixel_shift', shots=shots)
        s = darks.settled()
    p = s['plan']
    got = (p['start'], p['end'], p['step'], s['exposure']['iso'], s['exposure']['shutter'], s['shots_per_plane'])
    assert got == want + (shots,), f'controller state {got} is not the prepared {want + (shots,)}'
    assert not s['storage_error'] and not s['plan_error'], (s['storage_error'], s['plan_error'])
    previous = (s['storage'].get('receipt') or {}).get('path')
    expected = s['sequence_id'] + 1
    began = time.monotonic()
    log(label, 'start; planned', s['planned'], 'estimate', round(s['initial_seconds']), 's')
    api.command('start')
    follower = None
    if follow:
        st = api.wait(lambda st: (st['storage'].get('receipt') or {}).get('path') not in (None, previous)
                      or st['phase'] in ['fault', 'stopped'], timeout=300)
        folder = Path(st['storage']['receipt']['path'].replace('\\\\?\\', '')).parent
        follower = subprocess.Popen([str(STREHL), 'follow', str(folder), '--interval-ms', '2000'],
                                    stdout=open(OUT / f'{label}-follow.log', 'w'), stderr=subprocess.STDOUT)
        log(label, 'follow on', folder)
    s = api.wait(lambda st: st['sequence_id'] == expected and st['phase'] in ['complete', 'fault', 'stopped']
                 and not st['busy'], timeout=s['planned'] * shots * 12 + 1800)
    folder = str(Path(s['storage']['receipt']['path'].replace('\\\\?\\', '')).parent)
    r = {'label': label, 'phase': s['phase'], 'message': s['message'], 'folder': folder, 'shots': shots,
         'plan': s['plan'], 'exposure': {k: s['exposure'][k] for k in ['iso', 'shutter', 'f_number']},
         'pending_frames': s['storage'].get('pending_frames'), 'wall_seconds': round(time.monotonic() - began, 1)}
    log(json.dumps(r))
    if follower:
        try:
            follower.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            log(label, 'follow still running after 30 min; left running')
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', type=int, required=True)
    ap.add_argument('--end', type=int, required=True)
    ap.add_argument('--step', type=int, required=True)
    ap.add_argument('--shutter', type=int, required=True)
    ap.add_argument('--iso', type=int, default=100)
    ap.add_argument('--delay', type=int, default=0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    before = darks.settled()
    want = (a.start, a.end, a.step, a.iso, a.shutter)
    time.sleep(a.delay)
    results = []
    try:
        results.append(run(1, 'single', want))
        if results[-1]['phase'] == 'complete':
            results.append(run(4, 'fourshot', want, follow=True))
    finally:
        if api.state()['editable']:
            if api.state()['shots_per_plane'] != before['shots_per_plane']:
                api.command('pixel_shift', shots=before['shots_per_plane'])
                darks.settled()
            api.command('focus', target=before['position'])
            darks.settled()
        with (OUT / 'series.jsonl').open('a') as f:
            for r in results:
                f.write(json.dumps(r) + '\n')
        log('done')


if __name__ == '__main__':
    main()
