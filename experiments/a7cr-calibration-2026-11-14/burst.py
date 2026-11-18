"""Fixed-focus bursts through the LAN controller (plan section 10, captures 1 and 2).

Uses the controller's `capture_positions` command: the current focus position
repeated N times, approached once from the plan's direction. Exposure (ISO and
shutter) may be set for the burst and is restored afterwards with the
pixel-shift mode, focus, marks and plan.

  # Capture 1, noise calibration: a static, strongly defocused scene spanning
  # dark to near-clipping, 32 single-shot frames per ISO used.
  python -X utf8 burst.py --frames 32 --shots 1 --iso 100 --label ptc-iso100
  # Capture 2, static pixel-shift burst: 8 four-shot groups at fixed focus.
  python -X utf8 burst.py --frames 8 --shots 4 --label static-ps
Then: strehl pixel-shift <run folder> --json report.json
"""
import argparse
import json
import time

import darks


def burst(frames, shots, iso, shutter, label):
    s = darks.settled()
    if iso is not None or shutter is not None:
        ex = s['exposure']
        want = (iso if iso is not None else ex['iso'], shutter if shutter is not None else ex['shutter'])
        if (ex['iso'], ex['shutter']) != want:
            darks.api.command('exposure', iso=want[0], shutter=want[1]); s = darks.settled()
    if s['shots_per_plane'] != shots:
        darks.api.command('pixel_shift', shots=shots); s = darks.settled()
    position = s['position']
    expected = s['sequence_id'] + 1
    began = time.monotonic()
    darks.api.command('capture_positions', positions=[position] * frames)
    s = darks.api.wait(lambda s: s['sequence_id'] == expected and s['phase'] in ['complete', 'fault', 'stopped']
                       and not s['busy'], timeout=frames * shots * 15 + 240)
    assert s['phase'] == 'complete', s['message']
    folder = s['storage']['receipt']['path'].replace('\\\\?\\', '').rsplit('\\', 1)[0]
    return {'label': label, 'folder': folder, 'frames': frames, 'shots': shots, 'position': position,
            'exposure': s.get('exposure'), 'wall_seconds': time.monotonic() - began}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', type=int, required=True)
    ap.add_argument('--shots', type=int, choices=[1, 4], default=1)
    ap.add_argument('--iso', type=int)
    ap.add_argument('--shutter', type=int, help='camera ShutterSpeed property value, e.g. 393226 = 0.6 s')
    ap.add_argument('--label', default='burst')
    a = ap.parse_args()
    darks.OUT.mkdir(parents=True, exist_ok=True)
    before = darks.settled()
    try:
        r = burst(a.frames, a.shots, a.iso, a.shutter, a.label)
    finally:
        if darks.api.state()['editable']:
            darks.restore(before)
    with (darks.OUT / 'series.jsonl').open('a') as f:
        f.write(json.dumps(r) + '\n')
    print(json.dumps(r, indent=2))


if __name__ == '__main__':
    main()
