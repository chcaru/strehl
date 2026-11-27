"""One pipeline over any stack measured by curves.py: where it is truly in focus, what the
product's rule and the proposed rule say, the sharp depth by tile size, and what coarser steps
would keep. Nothing here is fitted to one subject: every threshold is a share of a quantity the
stack itself supplies.

  python general.py <stack scratch folder> <capture folder> [--subject frame|manifest|engine]

Reads curves/, and the subject from the capture's manifest (plan.subject), else from
subject.json (the engine's own `strehl subject`), else the whole frame. Writes general.json and
prints one block.
"""
import json
import pathlib
import sys

import numpy as np
from matplotlib.path import Path as MplPath
from scipy import ndimage

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import noisefit  # noqa: E402

PEAK_OVER_FLOOR = 6.0
SCORE = 20.0
GUARD = 1.5
ENGINE_THRESHOLD = 1.75        # x the noise floor: `strehl subject`'s default evidence threshold


def load(folder):
    c = folder / 'curves'
    focus = np.load(c / 'focus.npy').astype(np.float64)
    order = np.argsort(focus)
    cubes = {n: np.load(c / (n + '.npy'), mmap_mode='r') for n in ('lap2', 'mean', 'bright', 'pin')}
    return focus[order], order, cubes


def tiles(cube, order, t, mean=False):
    p, h, w = cube.shape
    h, w = h // t * t, w // t * t
    out = np.empty((p, h // t, w // t), np.float32)
    for i, src in enumerate(order):
        a = np.asarray(cube[src, :h, :w]).reshape(h // t, t, w // t, t)
        out[i] = a.mean(axis=(1, 3)) if mean else a.sum(axis=(1, 3))
    return out


def subject_mask(folder, run, h, w, choice):
    rings, source = None, 'whole frame'
    if choice != 'frame':
        m = json.loads((run / 'manifest.json').read_text()).get('plan', {}).get('subject')
        if m and m.get('rings') and choice in ('auto', 'manifest'):
            rings, source = m['rings'], 'manifest outline'
        elif (folder / 'subject.json').exists():
            s = json.loads((folder / 'subject.json').read_text())
            s = s.get('subject', s)
            if s.get('rings'):
                rings, source = s['rings'], 'engine outline (13 planes)'
    if rings is None:
        return np.ones((h, w), bool), source
    yy, xx = np.mgrid[0:h, 0:w]
    pts = np.column_stack([(xx.ravel() + 0.5) / w, (yy.ravel() + 0.5) / h])
    inside = np.zeros(h * w, bool)
    for i, ring in enumerate(rings):
        hit = MplPath(np.array(ring)).contains_points(pts)
        inside = inside ^ hit if i else hit            # later rings are holes
    return inside.reshape(h, w), source


def half_widths(cube, pos):
    p = cube.shape[0]
    c = cube.reshape(p, -1)
    floor = np.percentile(c, 10, axis=0)
    k = c.argmax(0)
    peak = c[k, np.arange(c.shape[1])]
    real = (peak >= PEAK_OVER_FLOOR * np.maximum(floor, 1e-9)) & (k > 0) & (k < p - 1)
    half = floor + (peak - floor) / 2
    wid = np.full(c.shape[1], np.nan)
    for i in np.nonzero(real)[0]:
        a = b = k[i]
        while a > 0 and c[a - 1, i] > half[i]:
            a -= 1
        while b < p - 1 and c[b + 1, i] > half[i]:
            b += 1
        if a == 0 or b == p - 1:
            continue
        lo = pos[a - 1] + (pos[a] - pos[a - 1]) * (half[i] - c[a - 1, i]) / (c[a, i] - c[a - 1, i])
        hi = pos[b] + (pos[b + 1] - pos[b]) * (c[b, i] - half[i]) / (c[b, i] - c[b + 1, i])
        wid[i] = hi - lo
    return wid.reshape(cube.shape[1:])


def narrow_peak(cube, pos, width):
    spacing = float(np.median(np.diff(pos)))
    p = cube.shape[0]
    c = cube.reshape(p, -1).astype(np.float64)
    span = max(int(round(3.5 * width / spacing)) | 1, 5)
    r = c - ndimage.median_filter(c, size=(span, 1), mode='nearest')
    m = ndimage.gaussian_filter1d(r, max(width / 2.3548 / spacing, 0.6), axis=0, mode='nearest')
    med = np.median(m, axis=0)
    score = (m - med) / (1.4826 * np.median(np.abs(m - med), axis=0) + 1e-12)
    k = score.argmax(0)
    cols = np.arange(c.shape[1])
    s = score[k, cols]
    k0 = np.clip(k, 1, p - 2)
    a, b, cc = m[k0 - 1, cols], m[k0, cols], m[k0 + 1, cols]
    d = a - 2 * b + cc
    shift = np.where(np.abs(d) > 1e-12, 0.5 * (a - cc) / np.where(np.abs(d) > 1e-12, d, 1), 0.0)
    f = pos[k0] + np.clip(shift, -1, 1) * spacing
    ok = (s >= SCORE) & (f > pos[0] + GUARD * width) & (f < pos[-1] - GUARD * width)
    f = np.where(ok, f, np.nan)
    return f.reshape(cube.shape[1:]), s.reshape(cube.shape[1:])


def block_contrast(cubes, order, table, t=4, reach=3):
    """Per tile and plane: the 75th percentile over the tile's blocks of (fine energy above its
    noise) / (level squared + a dark floor squared), counted only where the energy is at least
    3 x its noise. The level is the brightest block mean within `reach` blocks."""
    lapb, meanb = cubes['lap2'], cubes['mean']
    p, h, w = lapb.shape
    h, w = h // t * t, w // t * t
    out = np.empty((p, h // t, w // t), np.float32)
    floor = noisefit.dark_floor(table)
    for i, src in enumerate(order):
        l = np.asarray(lapb[src, :h, :w]) / 64.0
        m = np.maximum(np.asarray(meanb[src, :h, :w]), 0)
        n = noisefit.apply(table, m)
        level = ndimage.maximum_filter(m, size=2 * reach + 1, mode='nearest') if reach else m
        c = np.where(l >= 3 * n, np.maximum(l - n, 0) / (level ** 2 + floor ** 2), 0)
        out[i] = np.percentile(c.reshape(h // t, t, w // t, t).transpose(0, 2, 1, 3).reshape(h // t, w // t, t * t), 75, axis=2)
    return out


def contrast_range(sub, pos, sel, share=0.2):
    """Planes with tiles in focus, by a threshold that is `share` of the subject's own in-focus contrast."""
    best = sub[sel].max(0)
    ref = float(np.percentile(best, 90))
    counts = (sub[sel] >= share * ref).sum(1)
    live = counts >= max(3, 0.0005 * sub.shape[1])
    if not live.any():
        return None
    return {'first': float(pos[sel][live].min()), 'last': float(pos[sel][live].max()), 'reference': ref,
            'at_first_sampled': int(counts[0]), 'at_last_sampled': int(counts[-1]), 'planes': int(len(sel))}


def main():
    folder, run = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    choice = sys.argv[sys.argv.index('--subject') + 1] if '--subject' in sys.argv else 'auto'
    pos, order, cubes = load(folder)
    step = float(np.median(np.diff(pos)))
    lap = tiles(cubes['lap2'], order, 4)
    mean = tiles(cubes['mean'], order, 4, mean=True)
    px = 32 * 32
    inside, source = subject_mask(folder, run, lap.shape[1], lap.shape[2], choice)
    table = noisefit.fit(lap / px, mean)
    wid = half_widths(lap, pos)
    w64 = wid[inside & np.isfinite(wid)]
    W = float(np.median(w64))
    f, score = narrow_peak(lap, pos, W)
    good = inside & np.isfinite(f)
    neigh = ndimage.generic_filter(np.where(np.isfinite(f), f, np.nan), np.nanmedian, size=5, mode='constant', cval=np.nan)
    coherent = good & (np.abs(f - neigh) <= 2 * W)
    truth_lo, truth_hi = float(f[coherent].min()), float(f[coherent].max())
    truth_count = ((np.abs(pos[:, None, None] - f[None]) <= W / 2) & coherent[None])[:, inside].sum(1)
    energy = (lap / px) / noisefit.apply(table, mean)
    engine_count = (energy >= ENGINE_THRESHOLD)[:, inside].sum(1)
    am = pos[lap.argmax(0)]
    cb = block_contrast(cubes, order, table)
    sub = cb[:, inside]
    P = len(pos)
    every_w = max(int(round(W / step)), 1)
    out = {
        'run': run.name, 'subject': source, 'subject_tiles': int(inside.sum()), 'planes': P, 'step': step,
        'captured': [float(pos[0]), float(pos[-1])], 'noise': [table[0].tolist(), table[1].tolist()],
        'width_64': {'p10': float(np.percentile(w64, 10)), 'p50': W, 'p90': float(np.percentile(w64, 90)), 'tiles': int(w64.size)},
        'narrow': {'tiles': int(good.sum()), 'coherent': int(coherent.sum()), 'share_of_subject': float(good.sum() / inside.sum()),
                   'outside_subject': int((np.isfinite(f) & ~inside).sum()), 'outside_tiles': int((~inside).sum())},
        'truth': [truth_lo, truth_hi],
        'truth_with_margin': [truth_lo - W / 2, truth_hi + W / 2],
        'planes_outside_truth': int(((pos < truth_lo - W / 2) | (pos > truth_hi + W / 2)).sum()),
        'engine_rule': {'tiles_in_focus_first_plane': int(engine_count[0]), 'tiles_in_focus_last_plane': int(engine_count[-1]),
                        'truth_first_plane': int(truth_count[0]), 'truth_last_plane': int(truth_count[-1]),
                        'argmax_range': [float(am[inside].min()), float(am[inside].max())],
                        'argmax_at_end_planes': int(((am == pos[0]) | (am == pos[-1]))[inside].sum())},
        'contrast_rule': {'all_planes': contrast_range(sub, pos, np.arange(P)),
                          'spaced_one_width': contrast_range(sub, pos, np.arange(0, P, every_w)),
                          'spaced_two_widths': contrast_range(sub, pos, np.arange(0, P, 2 * every_w)),
                          'thirteen_planes': contrast_range(sub, pos, np.unique(np.round(np.linspace(0, P - 1, 13)).astype(int)))},
    }
    # the sharp depth against tile size
    for name, t in (('width_32', 2), ('width_16', 1)):
        cube = tiles(cubes['lap2'], order, t)
        ins, _ = subject_mask(folder, run, cube.shape[1], cube.shape[2], choice)
        wd = half_widths(cube, pos)
        v = wd[ins & np.isfinite(wd)]
        out[name] = {'p10': float(np.percentile(v, 10)), 'p50': float(np.median(v)), 'p90': float(np.percentile(v, 90)), 'tiles': int(v.size)}
        del cube
    # what coarser steps would keep: each trusted tile's curve thinned to every k-th plane, every phase
    cols = lap[:, coherent]
    peak = cols.max(0)
    keep = {}
    for k in (2, 3, 4, 6, 8, 12):
        if k * step > 3 * W:
            continue
        amp = np.stack([np.sqrt(cols[ph::k].max(0) / peak) for ph in range(k)])        # amplitude kept, by phase
        keep[str(k)] = {'step': k * step, 'overlap': W / (k * step), 'median_phase_p10_tile': float(np.median(np.percentile(amp, 10, axis=1))),
                        'worst_phase_p10_tile': float(np.percentile(amp, 10, axis=1).min()), 'median_tile_mean_phase': float(np.median(amp.mean(0)))}
    out['thinned'] = keep
    (folder / 'general.json').write_text(json.dumps(out, indent=1))
    np.savez(folder / 'general.npz', pos=pos, order=order, focus=f, coherent=coherent, inside=inside, width=wid,
             contrast=cb.astype(np.float16), truth_count=truth_count, engine_count=engine_count)
    t = out
    print('\n== %s | %s | %d subject tiles | %d planes, step %g, captured %d to %d' % (t['run'], source, t['subject_tiles'], P, step, pos[0], pos[-1]))
    print('   sharp depth (64 px tiles): %.0f (%.0f to %.0f); 32 px: %.0f; 16 px: %.0f' % (W, t['width_64']['p10'], t['width_64']['p90'], t['width_32']['p50'], t['width_16']['p50']))
    print('   tiles with a narrow peak: %.0f %% of the subject; outside it %d of %d' % (100 * t['narrow']['share_of_subject'], t['narrow']['outside_subject'], t['narrow']['outside_tiles']))
    print('   TRUTH in focus from %d to %d; with half a width each side %d to %d; planes captured outside that: %d of %d'
          % (truth_lo, truth_hi, truth_lo - W / 2, truth_hi + W / 2, t['planes_outside_truth'], P))
    e = t['engine_rule']
    print('   product rule (energy over 1.75 x noise): tiles "in focus" at the first plane %d (truth %d), at the last %d (truth %d); argmax range %d to %d'
          % (e['tiles_in_focus_first_plane'], e['truth_first_plane'], e['tiles_in_focus_last_plane'], e['truth_last_plane'], *e['argmax_range']))
    for label, key in (('all planes', 'all_planes'), ('one width apart', 'spaced_one_width'), ('two widths apart', 'spaced_two_widths'), ('13 planes', 'thirteen_planes')):
        c = t['contrast_rule'][key]
        if c:
            print('   contrast rule, %-16s (%3d planes): %d to %d; tiles at the first and last sampled plane: %d, %d' % (label, c['planes'], c['first'], c['last'], c['at_first_sampled'], c['at_last_sampled']))
    print('   thinned (step: amplitude kept at the worst tenth of tiles, median phase / worst phase): ' + '; '.join(
        '%g: %.3f / %.3f' % (v['step'], v['median_phase_p10_tile'], v['worst_phase_p10_tile']) for v in keep.values()))


if __name__ == '__main__':
    main()
