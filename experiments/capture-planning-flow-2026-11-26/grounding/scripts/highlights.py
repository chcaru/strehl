"""What the highlight groups of a capture hold, read from extract.py's summaries.

Per plane: samples at the pin in the base frame (all, and inside the subject's outline), the
brightest sample of the highlight frame, and the exposure ratio measured between the two frames
on 8 x 8 blocks that are well exposed in the base (their mean between LO and HI of full scale,
their brightest sample under 0.7 of the pin) -- the median of base / highlight block means.

  python highlights.py <planes folder> <capture folder> <out json>
"""
import json
import pathlib
import sys

import numpy as np
from matplotlib.path import Path as MplPath

LO, HI = 0.05, 0.6
src, run, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
manifest = json.loads((run / 'manifest.json').read_text())
rings = manifest['plan'].get('subject', {}).get('rings', [])


def third_stop(seconds):
    """The camera's nominal time as its exact third-stop value."""
    return 2.0 ** (round(3 * np.log2(seconds)) / 3)


def subject_mask(shape):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    pts = np.column_stack([(xx.ravel() + 0.5) / w, (yy.ravel() + 0.5) / h])
    mask = np.zeros(h * w, bool)
    for ring in rings:
        mask |= MplPath(np.array(ring)).contains_points(pts)
    return mask.reshape(h, w)


rows = []
masks = {}
for base_path in sorted(src.glob('base-*.npz')):
    b = np.load(base_path)
    bm = json.loads(str(b['meta']))
    full = bm['white'] - bm['black']
    pin = b['pin64'].astype(np.int64)                      # (3, th, tw), R G B
    if pin.shape[1:] not in masks:
        masks[pin.shape[1:]] = subject_mask(pin.shape[1:])
    inside = masks[pin.shape[1:]]
    row = {'plane': bm['plane'], 'focus': bm['focus'], 'base_seconds': bm['seconds'],
           'pinned': pin.sum(axis=(1, 2)).tolist(), 'pinned_subject': pin[:, inside].sum(axis=1).tolist(),
           'tiles_with_pins_subject': int((pin.sum(0) > 0)[inside].sum()), 'subject_tiles': int(inside.sum())}
    hp = src / ('highlight-%04d.npz' % bm['plane'])
    if hp.exists():
        h = np.load(hp)
        hm = json.loads(str(h['meta']))
        top = (h['max8'].astype(np.float32) - hm['black']) / full
        row['highlight_seconds'] = hm['seconds']
        row['highlight_top'] = top.max(axis=(1, 2)).tolist()          # of full scale, R G B
        row['highlight_pinned'] = h['pin64'].sum(axis=(1, 2)).tolist()
        nominal = third_stop(bm['seconds']) / third_stop(hm['seconds'])
        row['nominal_ratio'] = nominal
        row['glint_over_base_full'] = float(top.max() * nominal)
        ratios = {}
        for i, c in enumerate('RGB'):
            bmean, hmean = b['mean8'][i], h['mean8'][i]
            ok = (bmean > LO * full) & (bmean < HI * full) & (b['max8'][i] < bm['black'] + 0.7 * full) & (hmean > 0)
            if ok.sum() >= 50:
                r = bmean[ok] / hmean[ok]
                med = float(np.median(r))
                ratios[c] = {'blocks': int(ok.sum()), 'median': med,
                             'mad': float(1.4826 * np.median(np.abs(r - med))),
                             'sem': float(1.2533 * 1.4826 * np.median(np.abs(r - med)) / np.sqrt(ok.sum()))}
            else:
                ratios[c] = {'blocks': int(ok.sum())}
        row['ratio'] = ratios
    rows.append(row)
out.write_text(json.dumps(rows, indent=1))

full_sites = {'R': 1, 'G': 2, 'B': 1}
print('planes', len(rows), 'with a highlight frame', sum('highlight_top' in r for r in rows))
pinned = np.array([r['pinned'] for r in rows])
print('base frames, samples at the pin (R, G, B): median', np.median(pinned, 0), 'max', pinned.max(0), 'min', pinned.min(0))
ps = np.array([r['pinned_subject'] for r in rows])
print('inside the outline: median', np.median(ps, 0), '; share of all pins inside it %.3f' % (ps.sum() / max(pinned.sum(), 1)))
tw = np.array([r['tiles_with_pins_subject'] / r['subject_tiles'] for r in rows])
print('64 px tiles of the subject holding a pinned sample: median %.3f, range %.3f to %.3f' % (np.median(tw), tw.min(), tw.max()))
hl = [r for r in rows if 'highlight_top' in r]
top = np.array([r['highlight_top'] for r in hl])
print('highlight frames: brightest sample of full scale (R, G, B): median', np.round(np.median(top, 0), 3), 'max', np.round(top.max(0), 3),
      '; pinned samples in any highlight frame:', int(sum(sum(r['highlight_pinned']) for r in hl)))
g = np.array([r['glint_over_base_full'] for r in hl])
print('glint top over the base full scale: median %.1f, max %.1f (%.1f stops above the base pin); nominal ratio %.2f'
      % (np.median(g), g.max(), np.log2(g.max()), hl[0]['nominal_ratio']))
for c in 'RGB':
    med = np.array([r['ratio'][c].get('median', np.nan) for r in hl])
    n = np.array([r['ratio'][c]['blocks'] for r in hl])
    sem = np.array([r['ratio'][c].get('sem', np.nan) for r in hl])
    ok = np.isfinite(med)
    print('measured ratio %s: planes measurable %d of %d; blocks a plane median %d; ratio median %.2f, plane-to-plane range %.2f to %.2f (%.1f %% spread); typical standard error %.3f'
          % (c, ok.sum(), len(hl), np.median(n), np.nanmedian(med), np.nanmin(med), np.nanmax(med),
             100 * (np.nanmax(med) - np.nanmin(med)) / np.nanmedian(med), np.nanmedian(sem)))
