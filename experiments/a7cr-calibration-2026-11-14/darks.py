"""Capture lens-capped dark series on the A7CR through the LAN controller.

Usage: python -X utf8 darks.py --frames 32 [--shots 1] [--iso 100] [--shutter 393226] [--label x]

Each series is one ordinary controller stack with step 1 (focus is irrelevant with
the lens capped). ISO/shutter changes need the controller's `exposure` command.
The owner's focus marks, plan, ROI, pixel-shift mode and exposure are restored.
Refuses to run unless the live preview is dark (lens capped).
"""
import argparse
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/sony-a7cr-2026-11-13'))
import deploy as api  # noqa: E402

OUT = ROOT / 'outputs/a7cr-calibration-2026-11-14'


def settled(timeout=60):
    return api.wait(lambda s: s['editable'] and not s['busy'], timeout=timeout)


def prop(state, name):
    return ((state.get('exposure') or {}).get(name))


def preview_dark():
    r = requests.get(api.URL + '/api/preview', headers=api.AUTH, timeout=8)
    r.raise_for_status()
    im = np.asarray(Image.open(io.BytesIO(r.content)).convert('L'), float)
    return float(im.mean()), float(np.percentile(im, 99.9))


def restore(before):
    for key, start in [('start', True), ('end', False)]:
        if before[key + '_set']:
            api.command('focus', target=before['plan'][key]); settled()
            api.command('mark', start=start); settled()
    p = before['plan']
    api.command('settings', **{k: p[k] for k in ['step', 'settle_ms', 'approach', 'capture_timeout_s']}); settled()
    api.command('roi', roi=before['roi']); settled()
    api.command('focus', target=before['position']); settled()
    if api.state()['shots_per_plane'] != before['shots_per_plane']:
        api.command('pixel_shift', shots=before['shots_per_plane']); settled()
    ex = before.get('exposure')
    if ex and (prop(api.state(), 'iso') != ex['iso'] or prop(api.state(), 'shutter') != ex['shutter']):
        api.command('exposure', iso=ex['iso'], shutter=ex['shutter']); settled()


def series(frames, shots, iso, shutter, label):
    s = settled()
    if iso is not None or shutter is not None:
        ex = s.get('exposure') or {}
        want_iso = iso if iso is not None else ex['iso']
        want_sh = shutter if shutter is not None else ex['shutter']
        if (ex.get('iso'), ex.get('shutter')) != (want_iso, want_sh):
            api.command('exposure', iso=want_iso, shutter=want_sh); s = settled()
            assert prop(s, 'iso') == want_iso and prop(s, 'shutter') == want_sh, s.get('exposure')
    if s['shots_per_plane'] != shots:
        api.command('pixel_shift', shots=shots); s = settled()
        assert s['shots_per_plane'] == shots
    start = s['position']
    end = start + frames - 1 if start + frames + 200 < 65535 else start - frames + 1
    api.command('settings', step=1, settle_ms=100, approach=4, capture_timeout_s=120); settled()
    for target, is_start in [(start, True), (end, False)]:
        api.command('focus', target=target); settled()
        api.command('mark', start=is_start); settled()
    s = settled()
    assert s['planned'] == frames, s['planned']
    assert not s['storage_error'], s['storage_error']
    mean, p999 = preview_dark()
    assert mean < 4 and p999 < 16, f'preview not dark: mean {mean} p99.9 {p999}; is the lens capped?'
    expected = s['sequence_id'] + 1
    began = time.monotonic()
    api.command('start')
    s = api.wait(lambda s: s['sequence_id'] == expected and s['phase'] in ['complete', 'fault', 'stopped']
                 and not s['busy'], timeout=frames * shots * 12 + 240)
    assert s['phase'] == 'complete', s['message']
    assert s['storage']['pending_frames'] == 0
    folder = Path(s['storage']['receipt']['path'].replace('\\\\?\\', ''))
    folder = folder.parent
    raws = sorted(folder.glob('*.ARW.straw'))
    assert len(raws) == frames * shots, (len(raws), folder)
    return {'label': label, 'folder': str(folder), 'frames': frames, 'shots': shots,
            'exposure': s.get('exposure'), 'wall_seconds': time.monotonic() - began,
            'preview_mean': mean, 'preview_p999': p999}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', type=int, default=32)
    ap.add_argument('--shots', type=int, default=1)
    ap.add_argument('--iso', type=int)
    ap.add_argument('--shutter', type=int)
    ap.add_argument('--label', default='dark')
    ap.add_argument('--no-restore', action='store_true')
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    before = settled()
    assert before['storage'].get('pending_frames', 0) == 0
    stamp = str(int(time.time()))
    (OUT / f'before-{stamp}.json').write_text(json.dumps({k: v for k, v in before.items() if k != 'samples'}, indent=2) + '\n')
    try:
        result = series(a.frames, a.shots, a.iso, a.shutter, a.label)
    finally:
        if not a.no_restore and api.state()['editable']:
            restore(before)
    log = OUT / 'series.jsonl'
    with log.open('a') as f:
        f.write(json.dumps(result) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
