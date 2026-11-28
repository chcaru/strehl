"""Write the small files the plates are drawn from (numbers only) into the experiment's
plates/ folder, from this scratch folder's analysis results."""
import json
import pathlib

import numpy as np

HERE = pathlib.Path('C:/strehl-scratch/calib-page')
OUT = pathlib.Path('C:/dev/blog/death-of-software/projects/strehl/.claude/worktrees/calibration-page-spec/experiments/setup-page-2026-11-27/plates')
OUT.mkdir(parents=True, exist_ok=True)
NAMES = ['R', 'G1', 'G2', 'B']


def write(name, data):
    (OUT / (name + '.json')).write_text(json.dumps(data, separators=(',', ':')) + '\n', encoding='utf-8')
    print(name, (OUT / (name + '.json')).stat().st_size, 'bytes')


# Bright: noise against signal (ISO 100, five bursts pooled in log bins)
d = json.load(open(HERE / 'sensor-iso100.json'))
bins = {}
for ci, c in enumerate(NAMES):
    acc = {}
    for s in d['series']:
        for m, v, n in s['bins'][ci]:
            if m < 15700:                      # the clipped bin is drawn as the wall
                k = round(np.log10(max(m, 1)) * 14)
                a = acc.setdefault(k, [0.0, 0.0, 0.0])
                a[0] += m * n
                a[1] += v * n
                a[2] += n
    bins[c] = [[round(a[0] / a[2], 1), round(a[1] / a[2], 2)] for k, a in sorted(acc.items()) if a[2] >= 2000]
fit = d['fits'][0]['fit']
write('bright-noise', {'iso': 100, 'bins': bins, 'gain': {c: round(fit[c]['gain'], 4) for c in NAMES}, 'fit_to': 4000,
                       'read_dn': 1.305, 'clip_code': 16383, 'clip_above_black': 15871, 'black': 512,
                       'source': 'D:/StrehlCaptures stacks 1795845325970, 1795845346254, 1795845373546, 1795845416183, 1795845474051 (2026-11-27)'})

# Bright: exposure ratio against level
pairs = []
for p in d['pairs']:
    rows = p['ratio'][1]
    mid = sorted(r[1] for r in rows if 1500 <= r[0] <= 6000)
    flat = mid[len(mid) // 2]
    pairs.append({'short_s': p['short'], 'long_s': p['long'],
                  'points': [[round(r[0]), round(100 * (r[1] / flat - 1), 3)] for r in rows[::2] if r[0] < 15800]})
write('bright-levels', {'iso': 100, 'pairs': pairs, 'clip_code': 16383, 'clip_above_black': 15871,
                        'declared_code': 15360, 'declared_above_black': 14848})

# Dark: read noise against ISO
dark = json.load(open(HERE / 'e1b.json'))
rows = [json.loads(l) for l in open(HERE / 'series.jsonl') if 'dark-off' in l]
measured = []
for r, s in zip(rows, dark):
    if r['shutter'] == 65636:
        measured.append({'iso': int(s['iso']), 'read': round(s['active_stats']['G1']['read_noise_pooled_rms'], 3),
                         'black': round(s['active_stats']['G1']['black_mean'], 2)})
capped = [{'iso': i, 'read': v} for i, v in [(100, 1.330), (125, 1.629), (160, 1.984), (200, 2.467), (250, 3.060), (320, 3.836),
                                              (400, 2.224), (500, 2.797), (640, 3.510), (800, 4.406), (1600, 8.642), (3200, 16.808),
                                              (6400, 32.590)]]
gain = 0.4040
model = [[iso, round((3.30 if iso < 400 else 1.386) * gain * iso / 100, 3)] for iso in (100, 125, 160, 200, 250, 320, 399.9, 400, 800, 1600, 3200, 6400)]
write('dark', {'measured': measured, 'capped': capped, 'model': model, 'second_mode_iso': 400,
               'leak': {'unlit': [512.22, 512.41], 'lit': [513.88, 969.78], 'shutters_s': [0.01, 2.5]}})

# Motion: return
a = json.load(open(HERE / 'e4' / 'approach.json'))
order = [('below128', 'from 128 below', True), ('above128', 'from 128 above', False), ('below16', 'from 16 below', False),
         ('above16', 'from 16 above', False), ('below8', 'from 8 below', False), ('above8', 'from 8 above', False),
         ('farabove+128', 'far above, then 128 below', False), ('farbelow+128', 'far below, then 128 below', False),
         ('farabove', 'from 5,000 above', False), ('farbelow', 'from 5,000 below', False)]
write('motion-return', {'P': a['P'], 'instrument': round(a['instrument']['loo_rms'], 1),
                        'rows': [{'label': label, 'reps': [round(v, 2) for v in a['kinds'][k]['reps']], **({'chosen': True} if chosen else {})}
                                 for k, label, chosen in order]})

# Warm-up
runs = []
for name, t0, cold in [('warm2.json', 1795847236.995, True), ('warm1.json', 1795844728.5, False)]:
    w = json.load(open(HERE / name))
    t = np.array([r['unix'] - t0 for r in w['rows']])
    g = np.array([(r['level'][1] + r['level'][2]) / 2 for r in w['rows']])
    ref = g[-12:].mean() if cold else g[:36].mean()
    runs.append({'cold': cold, 'points': [[round(float(a), 1), round(float(100 * (b / ref - 1)), 3)] for a, b in zip(t, g)],
                 'red_over_green': [round(float(r['level'][0] / ((r['level'][1] + r['level'][2]) / 2)), 4) for r in w['rows']][::4],
                 'drift_px': [[round(r['dx'], 3), round(r['dy'], 3)] for r in w['rows']][::4]})
cold = runs[0]['points']
late = np.array([v for t, v in cold if t > 140])
tol = float(2 * late.std())
last_out = max([t for t, v in cold if abs(v) > tol], default=0)
nxt = min([t for t, v in cold if t > last_out], default=last_out)
write('warm-up', {'runs': runs, 'tolerance': round(tol, 2), 'settled_s': round(nxt), 'axis': [-4, 10]})
print('warm-up: late sd %.2f %%, tolerance %.2f %%, last outside at %.0f s, settled from %.0f s' % (late.std(), tol, last_out, nxt))

# Settle
p = HERE / 'settle.json'
if p.exists():
    s = json.load(open(p))
    rows = {}
    for b in s['bursts']:
        rel = np.array(b['rel'])[1:]
        rows.setdefault(b['settle'], []).extend(np.hypot(rel[:, 0], rel[:, 1]).round(3).tolist())
    write('settle', {'rows': [{'ms': ms, 'frames': v, 'median': round(float(np.median(v)), 3)} for ms, v in sorted(rows.items())],
                     'axis': 1.0})
