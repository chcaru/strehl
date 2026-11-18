"""Plan capture 3: paired single-shot and four-shot stacks of one static subject
with the same bounds and step, through the controller's ordinary plan/Start
path. During the four-shot run, `strehl follow` checks each plane live (plan
S1 on real hardware). Leaves the new marks and plan in place; restores the
pixel-shift mode.

  python -X utf8 capture3.py --start 61050 --end 61898 --step 8 --delay 60
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import darks

api = darks.api
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/a7cr-calibration-2026-11-14/capture3'
STREHL = ROOT / 'target-ui/release/strehl.exe'


def run(shots, label, follow=False):
    s = darks.settled()
    if s['shots_per_plane'] != shots:
        api.command('pixel_shift', shots=shots)
        s = darks.settled()
    previous = (s['storage'].get('receipt') or {}).get('path')
    expected = s['sequence_id'] + 1
    began = time.monotonic()
    print(label, 'start', time.strftime('%H:%M:%S'), 'planned', s['planned'], flush=True)
    api.command('start')
    follower = None
    if follow:
        # The run folder is known once the first RAW has a receipt.
        st = api.wait(lambda st: (st['storage'].get('receipt') or {}).get('path') not in (None, previous)
                      or st['phase'] in ['fault', 'stopped'], timeout=300)
        folder = Path(st['storage']['receipt']['path'].replace('\\\\?\\', '')).parent
        log = open(OUT / f'{label}-follow.log', 'w')
        follower = subprocess.Popen([str(STREHL), 'follow', str(folder), '--interval-ms', '2000'],
                                    stdout=log, stderr=subprocess.STDOUT)
        print(label, 'follow on', folder, flush=True)
    s = api.wait(lambda st: st['sequence_id'] == expected and st['phase'] in ['complete', 'fault', 'stopped']
                 and not st['busy'], timeout=s['planned'] * shots * 12 + 900)
    folder = str(Path(s['storage']['receipt']['path'].replace('\\\\?\\', '')).parent)
    r = {'label': label, 'phase': s['phase'], 'message': s['message'], 'folder': folder, 'shots': shots,
         'plan': s['plan'], 'exposure': {k: s['exposure'][k] for k in ['iso', 'shutter', 'f_number']},
         'wall_seconds': time.monotonic() - began}
    print(json.dumps(r), flush=True)
    if follower:
        follower.wait(timeout=600)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', type=int, required=True)
    ap.add_argument('--end', type=int, required=True)
    ap.add_argument('--step', type=int, required=True)
    ap.add_argument('--delay', type=int, default=0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    before = darks.settled()
    p = before['plan']
    api.command('settings', step=a.step, settle_ms=p['settle_ms'], approach=p['approach'],
                capture_timeout_s=p['capture_timeout_s'])
    darks.settled()
    for target, is_start in [(a.start, True), (a.end, False)]:
        api.command('focus', target=target)
        darks.settled()
        api.command('mark', start=is_start)
        darks.settled()
    s = darks.settled()
    print('plan', s['plan'], 'planned', s['planned'], 'storage_error', s['storage_error'], flush=True)
    assert not s['storage_error']
    time.sleep(a.delay)
    results = []
    try:
        results.append(run(1, 'single'))
        results.append(run(4, 'fourshot', follow=True))
    finally:
        if api.state()['editable'] and api.state()['shots_per_plane'] != before['shots_per_plane']:
            api.command('pixel_shift', shots=before['shots_per_plane'])
            darks.settled()
        with (darks.OUT / 'series.jsonl').open('a') as f:
            for r in results:
                f.write(json.dumps({**r, 'kind': 'capture3'}) + '\n')
        print('done', time.strftime('%H:%M:%S'), flush=True)


if __name__ == '__main__':
    main()
