"""Fixture specs for strehl survey from the rig index and tonight's ladder.

  python make-specs.py <rig-index.json> <ladder.json> <out folder>
"""
import json
import pathlib
import sys

idx = json.loads(pathlib.Path(sys.argv[1]).read_text())
ladder = json.loads(pathlib.Path(sys.argv[2]).read_text())
out = pathlib.Path(sys.argv[3])
fx = pathlib.Path('C:/w/shd-census-out/fixtures')


def rung(series, position, shutter, note=None):
    rs = [r for r in idx if r.get('series') == series and r.get('position') == position
          and r.get('shutter') == shutter and (note is None or r.get('note') == note)]
    assert len(rs) == 1, (series, position, shutter, note, len(rs))
    return rs[0]


positions = [24972, 25182, 25462]
LONG, SHORT = 65540, 65596   # 1/4 s, 1/60 s


def weevil(note_long):
    shots = []
    for p in positions:
        shots.append({'run': rung('ladder', p, LONG, note_long)['folder'], 'shutter': LONG, 'position': p})
        shots.append({'run': rung('ladder', p, SHORT)['folder'], 'shutter': SHORT, 'position': p})
    for r in idx:
        # The sweep's 25182 would replace the pair's long frame (a later shot at the same
        # focus and shutter wins, as a retake does).
        if r.get('series') == 'sweep' and r['position'] not in positions:
            shots.append({'run': r['folder'], 'shutter': r['shutter'], 'position': r['position']})
    return shots


src = rung('ladder', 24972, LONG, 'owner shutter, first')['folder']
specs = {
    # Weevil, 1/4 s long (first owner rung) and 1/60 s short at three positions; the
    # 25-position sweep (2 units apart) as the dense cluster.
    'weevil-a': {'source_manifest': src, 'shots': weevil('owner shutter, first'), 'shuffle': None},
    'weevil-a-shuffled': {'source_manifest': src, 'shots': weevil('owner shutter, first'), 'shuffle': 7,
                          'link_from': str(fx / 'weevil-a')},
    # The same with the last owner rung (taken after the short ones: the light drifts).
    'weevil-last': {'source_manifest': src, 'shots': weevil('owner shutter, last'), 'shuffle': None},
}
# Closer to the real Calibrate: the same three pairs, long-only positions spread over the
# owner's weevil stack (199 planes, step 7, 1/4 s, the same session and framing), and a dense
# cluster of 25 consecutive stack planes (7 units apart) around the middle.
STACK = 'D:\\StrehlCaptures\\stack-1795460665629-8651'
stack_pos = lambda plane: 24482 + 7 * (plane - 1) if plane < 199 else 25866
dense = list(range(88, 113))
spread = [p for p in list(range(1, 199, 16)) + [199] if not (dense[0] - 3 <= p <= dense[-1] + 3)]
shots_b = []
for p in positions:
    shots_b.append({'run': rung('ladder', p, LONG, 'owner shutter, first')['folder'], 'shutter': LONG, 'position': p})
    shots_b.append({'run': rung('ladder', p, SHORT)['folder'], 'shutter': SHORT, 'position': p})
for plane in sorted(spread + dense):
    if stack_pos(plane) in positions:
        continue   # the pair's own long frame stands for this position
    shots_b.append({'run': STACK, 'shutter': LONG, 'position': stack_pos(plane), 'plane': plane})
specs['weevil-b'] = {'source_manifest': src, 'shots': shots_b, 'shuffle': None}
# A check of the census's pinned prediction at the exposure "accept" chooses: 1.3 s long,
# 1/4 s (first owner rung) as the short one, at the same three positions.
specs['weevil-13'] = {'source_manifest': src, 'shuffle': None, 'shots': [
    s for p in positions for s in (
        {'run': rung('ladder', p, 851978)['folder'], 'shutter': 851978, 'position': p},
        {'run': rung('ladder', p, LONG, 'owner shutter, first')['folder'], 'shutter': LONG, 'position': p})]}
# Tonight's pronotum ladder at focus 62000: one position, 1 s / 1/15 s and 1/4 s / 1/60 s.
by = {r['shutter']: r for r in ladder}
for name, (lo, sh) in {'pronotum-1s': (655370, 65551), 'pronotum-quarter': (65540, 65596)}.items():
    specs[name] = {'source_manifest': by[lo]['folder'], 'shuffle': None, 'shots': [
        {'run': by[lo]['folder'], 'shutter': lo, 'position': by[lo]['position']},
        {'run': by[sh]['folder'], 'shutter': sh, 'position': by[sh]['position']},
    ]}
out.mkdir(parents=True, exist_ok=True)
for name, s in specs.items():
    (out / (name + '.json')).write_text(json.dumps(s, indent=1))
    print(name, len(s['shots']))
