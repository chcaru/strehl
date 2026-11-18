"""Capture 1 (plan section 10): photon-transfer bursts of a strongly defocused,
static scene at fixed ISO, swept over shutter times so the scene spans dark to
near-clipping. Focus is moved off the subject by --defocus units for the
bursts; the owner's focus, plan, pixel-shift mode and exposure are restored.

  python -X utf8 ptc-sweep.py --defocus 1500 --iso 100 --series 16:393226 32:1638410
Each --series item is FRAMES:SHUTTER (camera ShutterSpeed property value).
"""
import argparse
import json
import time

import burst
import darks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--defocus', type=int, required=True)
    ap.add_argument('--iso', type=int, default=100)
    ap.add_argument('--series', nargs='+', required=True)
    ap.add_argument('--label', default='ptc')
    a = ap.parse_args()
    darks.OUT.mkdir(parents=True, exist_ok=True)
    before = darks.settled()
    results = []
    try:
        darks.api.command('focus', target=before['position'] + a.defocus)
        darks.settled()
        for item in a.series:
            frames, shutter = map(int, item.split(':'))
            r = burst.burst(frames, 1, a.iso, shutter, f'{a.label}-iso{a.iso}-{shutter}')
            r['defocus'] = a.defocus
            results.append(r)
            with (darks.OUT / 'series.jsonl').open('a') as f:
                f.write(json.dumps(r) + '\n')
            print(r['label'], r['folder'], round(r['wall_seconds'], 1), flush=True)
    finally:
        if darks.api.state()['editable']:
            darks.restore(before)
        s = darks.api.state()
        print('restored', s['position'], s['shots_per_plane'], s['exposure']['iso'], s['exposure']['shutter'],
              s['plan'] == before['plan'], time.strftime('%H:%M:%S'))


if __name__ == '__main__':
    main()
