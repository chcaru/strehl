"""Live-view frames of a lab run.

  lv-analyse.py sharp <frames root> <log.jsonl>     settled sharpness per position directory
  lv-analyse.py motion <frames dir> <log.jsonl>     when the image stops changing after a jog

`motion`: every frame is compared with the mean of the last frames (the settled image) and
with the mean of the frames before the jog; the lens is taken to have arrived when the
distance to the settled image falls to its own noise floor (the level among the last
frames). Times are from the jog command; a frame's time is when its transfer began, and the
camera's live-view latency (unknown, tens of ms) delays what it shows, so arrival times are
upper bounds.
"""
import json
import pathlib
import sys

import cv2
import numpy as np


def load(path):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    return img.astype(np.float32)


def logs(path):
    out = []
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if line.startswith('{'):
            out.append(json.loads(line))
    return out


mode, root, log = sys.argv[1], pathlib.Path(sys.argv[2]), logs(sys.argv[3])
views = [v for v in log if v.get('lab') == 'liveview']
if mode == 'sharp':
    for v in views:
        d = root / pathlib.Path(v['dir']).name
        frames = sorted(d.glob('*.jpg'))
        img = load(frames[-1])
        lap = cv2.Laplacian(cv2.GaussianBlur(img, (0, 0), 1.0), cv2.CV_32F)
        gx = cv2.Sobel(img, cv2.CV_32F, 1, 0)
        print('%s focus %6d  frames %3d  fps %.1f  mean %.1f  laplacian var %.2f  gradient p99 %.1f' % (
            d.name, v['focus'], len(frames), len(frames) / max(1e-6, v['frames'][-1][1] - v['frames'][0][0]),
            img.mean(), lap.var(), np.percentile(np.abs(gx), 99)))
else:
    name = root.name
    v = next(x for x in views if pathlib.Path(x['dir']).name == name)
    i = log.index(v)
    jog = next(x for x in reversed(log[:i]) if x.get('lab') == 'jog')
    c218 = [x['t'] for x in log[:i] if x.get('lab') == 'event' and x['code'] == 'c218' and x['t'] > jog['t']]
    frames = sorted(root.glob('*.jpg'))
    times = np.array([f[0] for f in v['frames']]) - jog['t']
    done = np.array([f[1] for f in v['frames']]) - jog['t']
    imgs = [cv2.GaussianBlur(load(f), (0, 0), 2.0) for f in frames]
    settled = np.mean(imgs[-8:], axis=0)
    before = np.mean([im for im, t in zip(imgs, times) if t < 0][-8:], axis=0)
    # Matched filter: how far each frame is along the way from the before-image to the
    # settled image (0 before the move, 1 when the lens has arrived).
    direction = settled - before
    norm = float(np.sum(direction * direction))
    s = np.array([float(np.sum((im - before) * direction)) / norm for im in imgs])
    noise = s[times < 0].std()
    signal = np.sqrt(np.mean(direction ** 2))
    print('%s: jog %+d at t=0 (from %d), focus-result event at %s s, %d frames at %.1f fps' % (
        name, jog['target'] - jog['from'], jog['from'], ', '.join('%.3f' % (t - jog['t']) for t in c218) or 'none',
        len(frames), len(frames) / (done[-1] - times[0])))
    print('   before-to-settled image change %.3f grey levels rms; progress noise %.3f (1 = full move)' % (signal, noise))
    after = times > 0
    start = next((times[k] for k in np.flatnonzero(after) if s[k] > 5 * noise + 0.05), None)
    arrive = next((times[k] for k in np.flatnonzero(after) if np.all(np.abs(s[k:] - 1) < 5 * noise + 0.05)), None)
    peak = float(s[after].max())
    print('   progress first leaves 0 at %s s; stays within noise of 1 from %s s; peak progress %.2f' % (
        'n/a' if start is None else '%.3f' % start, 'n/a' if arrive is None else '%.3f' % arrive, peak))
    print('   t(s): progress   ' + '  '.join('%.2f:%.2f' % (times[k], s[k]) for k in range(len(imgs)) if -0.08 < times[k] < 0.9))
