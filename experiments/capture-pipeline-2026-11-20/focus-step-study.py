"""How many planes is a point of the subject sharp in? (Is the focus step finer than needed?)

  python -X faulthandler focus-step-study.py <capture folder> <first plane> <last plane> <scratch>

Read-only over the capture: the first exposure of each four-shot plane in the range is
restored to <scratch> one at a time with strehl-raw-archive, read, and deleted. Two measures
of detail are taken per tile and plane:
  mid   gradient energy of the mean of the two greens after a 1.6 px (sensor) blur;
  fine  energy of the 4-neighbour Laplacian of ONE green site plane, unblurred: its samples
        are 2 sensor px apart, so it responds to the finest detail the lens delivers
        (including what aliases), which is what pixel shift is bought for.
For tiles whose measure peaks inside the range and well above their out-of-focus level, the
script reports the width of the peak in planes and what the neighbouring planes still hold.
These measures only compare a tile with itself across planes; they do not judge image quality.

Controls: (1) a tile's level far from its peak (noise and blur floor) is subtracted;
(2) widths are reported for small tiles (64 sensor px) and large ones (256 px): a large tile
holds detail at several depths, which widens its peak, so the small-tile figure is the one
nearer the optics; (3) strongest- and weakest-detail thirds separately: a width set by noise
rather than optics would differ between them.
"""
import pathlib
import subprocess
import sys

import cv2
import numpy as np
import rawpy

run, first, last, scratch = pathlib.Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), pathlib.Path(sys.argv[4])
ROOT = pathlib.Path(__file__).resolve().parents[2]
tool = ROOT / 'target/release/strehl-raw-archive.exe'
scratch.mkdir(parents=True, exist_ok=True)
TILE = 32  # half-resolution pixels (64 sensor pixels)
mid, fine = [], []
lap = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32)
for plane in range(first, last + 1):
    name = 'frame-%06d.ARW' % (4 * plane + 1)
    out = scratch / name
    if out.exists():
        out.unlink()
    subprocess.run([str(tool), 'restore', str(run / (name + '.straw')), '--output-dir', str(scratch)], check=True, capture_output=True)
    with rawpy.imread(str(out)) as raw:
        img = raw.raw_image_visible.copy()  # copy inside the context
        black = float(np.mean(raw.black_level_per_channel))
        pattern = raw.raw_pattern.copy()
        colours = raw.color_desc.decode()
    out.unlink()
    sites = [(y, x) for y in (0, 1) for x in (0, 1) if colours[pattern[y, x]] == 'G']
    greens = [img[y::2, x::2].astype(np.float32) - black for y, x in sites]
    g = sum(greens) / len(greens)
    s = cv2.GaussianBlur(g, (0, 0), 0.8)
    gx = cv2.Sobel(s, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(s, cv2.CV_32F, 0, 1)
    e_mid = gx * gx + gy * gy
    l = cv2.filter2D(greens[0], cv2.CV_32F, lap)
    e_fine = l * l
    h, w = e_mid.shape
    th, tw = h // TILE, w // TILE
    mid.append(e_mid[:th * TILE, :tw * TILE].reshape(th, TILE, tw, TILE).mean(axis=(1, 3)))
    fine.append(e_fine[:th * TILE, :tw * TILE].reshape(th, TILE, tw, TILE).mean(axis=(1, 3)))
    print('plane %d read' % plane, flush=True)


def pool(E, k):
    n, th, tw = E.shape
    return E[:, :th // k * k, :tw // k * k].reshape(n, th // k, k, tw // k, k).mean(axis=(2, 4))


def report(label, E):
    n = E.shape[0]
    flat = E.reshape(n, -1)
    floor = np.percentile(flat, 10, axis=0)
    peak = flat.max(axis=0)
    at = flat.argmax(axis=0)
    margin = 12
    good = (at >= margin) & (at < n - margin) & (peak > 6 * floor)
    widths, strength = [], []
    rel = {1: [], 2: [], 3: [], 4: [], 6: [], 8: []}
    for t in np.flatnonzero(good):
        c = flat[:, t] - floor[t]
        p = at[t]
        half = c[p] / 2
        lo = p
        while lo > 0 and c[lo] > half:
            lo -= 1
        hi = p
        while hi < n - 1 and c[hi] > half:
            hi += 1
        left = lo + (half - c[lo]) / max(c[lo + 1] - c[lo], 1e-9)
        right = hi - (half - c[hi]) / max(c[hi - 1] - c[hi], 1e-9)
        widths.append(right - left)
        strength.append(c[p])
        for d in rel:
            rel[d].append((c[p - d] + c[p + d]) / (2 * c[p]))
    widths, strength = np.array(widths), np.array(strength)
    print('\n%s: %d of %d tiles peak inside the range (by %d planes) at more than 6x their floor' % (label, len(widths), flat.shape[1], margin))
    if len(widths) < 9:
        return
    order = np.argsort(strength)
    third = len(order) // 3
    for name, idx in (('all', order), ('strongest-detail third', order[-third:]), ('weakest-detail third', order[:third])):
        v = widths[idx]
        print('   peak width at half height, %-23s median %.1f planes (10th-90th percentile %.1f-%.1f), n=%d' % (
            name + ':', np.median(v), np.percentile(v, 10), np.percentile(v, 90), len(v)))
    print('   left of the peak value at a distance of d planes (median tile, mean of both sides; 10th percentile tile in brackets):')
    print('   ' + '  '.join('d=%d: %.3f (%.3f)' % (d, np.median(rel[d]), np.percentile(rel[d], 10)) for d in rel))


M, F = np.stack(mid), np.stack(fine)
print('\n%d planes (%d-%d) of %s' % (M.shape[0], first, last, run.name))
report('mid detail, 64 px tiles', M)
report('mid detail, 256 px tiles', pool(M, 4))
report('fine detail, 64 px tiles', F)
report('fine detail, 256 px tiles', pool(F, 4))
print('\nA focus step k times coarser puts the worst-placed point k/2 planes from its best plane: read d = k/2 above.')
