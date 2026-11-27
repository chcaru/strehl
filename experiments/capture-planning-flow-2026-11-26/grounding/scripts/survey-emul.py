"""The calibration's RAW survey on independent frames: rig-series-2.py's single RAWs (one test run
a position) read by the contrast rule, against the range the full stack of the day before gives.

  python survey-emul.py <series folder> <dragonfly scratch folder (general.npz of the stack)>
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import curves  # noqa: E402
import extract  # noqa: E402
import general  # noqa: E402
import noisefit  # noqa: E402

series, stack = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
rec = json.loads((series / 'record.json').read_text())
work = series / 'survey'
(work / 'planes').mkdir(parents=True, exist_ok=True)
runs = rec['survey']
for i, r in enumerate(runs):
    dst = work / 'planes' / ('base-%04d.npz' % i)
    if dst.exists():
        continue
    run = pathlib.Path(r['folder'])
    recd = {'plane': i, 'tier': 'base', 'focus': r['position'], 'iso': 100, 'shutter': 851978, 'seconds': 1.3,
            'file': 'frame-000001.ARW', 'files': ['frame-000001.ARW'], 'group': run.name, 'unix_ms': int(r['started_unix'] * 1000)}
    # extract.one writes '<tier>-<plane>.npz' into its out folder
    extract.one((run, work / 'planes', recd))
if not (work / 'curves' / 'focus.npy').exists():
    sys.argv = ['curves.py', str(work / 'planes'), str(work / 'curves'), '8']
    curves.main()
pos, order, cubes = general.load(work)
lap = general.tiles(cubes['lap2'], order, 4)
mean = general.tiles(cubes['mean'], order, 4, mean=True)
inside, source = general.subject_mask(work, pathlib.Path(runs[0]['folder']), lap.shape[1], lap.shape[2], 'auto')
table = noisefit.fit(lap / 1024.0, mean)
cb = general.block_contrast(cubes, order, table)
sub = cb[:, inside]
out = {'positions': pos.tolist(), 'subject': source}
print('survey of %d single RAWs, %d to %d, %g apart; subject: %s (%d tiles); median wall %.1f s a RAW, %.0f s in all'
      % (len(pos), pos[0], pos[-1], np.median(np.diff(pos)), source, inside.sum(),
         np.median([r['wall_s'] for r in runs]), sum(r['wall_s'] for r in runs)))
for label, sel in (('all %d' % len(pos), np.arange(len(pos))), ('every second (%d)' % len(pos[::2]), np.arange(0, len(pos), 2))):
    r = general.contrast_range(sub, pos, sel)
    print('   contrast rule, %-18s: in focus from %d to %d; tiles at the first and last frame %d, %d; reference %.3f'
          % (label, r['first'], r['last'], r['at_first_sampled'], r['at_last_sampled'], r['reference']))
    out[label] = r
ref = float(np.percentile(sub.max(0), 90))
counts = (sub >= 0.2 * ref).sum(1)
print('   tiles in focus by position:', ' '.join('%d:%d' % (p, c) for p, c in zip(pos, counts)))
# the same positions in the stack of the day before
g = np.load(stack / 'general.npz')
spos, scb, sins = g['pos'], g['contrast'].astype(np.float32), g['inside']
idx = [int(np.argmin(np.abs(spos - p))) for p in pos]
ssub = scb[idx][:, sins]
sref = float(np.percentile(ssub.max(0), 90))
scounts = (ssub >= 0.2 * sref).sum(1)
print('   the same positions in the stack:', ' '.join('%d:%d' % (p, c) for p, c in zip(pos, scounts)))
print('   stack truth (every plane, narrow peaks): %d to %d' % (g['focus'][g['coherent']].min(), g['focus'][g['coherent']].max()))
out['counts'] = counts.tolist(); out['stack_counts'] = scounts.tolist()
# the light: mean level of each survey frame inside the subject against the stack's frame at that position
lv = mean[:, inside].mean(1)
smean = general.tiles(np.load(stack / 'curves' / 'mean.npy', mmap_mode='r'), g['order'], 4, mean=True)[idx][:, sins].mean(1)
print('   subject mean level, survey / stack of the day before: median %.3f (range %.3f to %.3f)' % (np.median(lv / smean), (lv / smean).min(), (lv / smean).max()))
out['level_ratio'] = (lv / smean).tolist()
(series / 'survey-emul.json').write_text(json.dumps(out, indent=1))
