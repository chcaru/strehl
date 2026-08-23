"""M39 verification, script 03: the merge, re-implemented in numpy from merge.rs.

This does NOT call the Rust binary and shares no code with the author's scripts.
Pass one : green luma (black-subtracted, each green clamped at 0 -- plane.rs
           green_luma), 3x3 Sobel/8 magnitude with replicate clamp, 27x27 box
           mean, divide by the calibrated green-luma sigma at that pixel, then a
           17x17 box mean (the regulariser).  argmax across frames, ties to the
           lower index.
Pass two : admit frame k at pixel i iff k is the winner there OR
           best_focus[i] - focus_k[i] <= gate * sqrt(2) * FOCUS_NOISE_SD.
           Average the admitted frames' G1 and G2 in raw DN.

Only a crop around each ROI is processed. The margin is 24 plane px, which is
2 px more than the 1 (Sobel) + 13 (window) + 8 (regulariser) = 22 px reach of
the regularised focus value, so every value used is bit-for-bit what the full
plane would give (all box windows are unclamped inside the crop).
"""
import numpy as np, rawpy, json, glob, os, time

FRAMES = sorted(glob.glob(r'D:\personal\macro\109MSDCF\*.ARW'))
assert len(FRAMES) == 22, len(FRAMES)
BLACK, ISO, GAIN_DIV, RN_E = 512.0, 160.0, 436.8, 4.20
G = ISO / GAIN_DIV
READ_DN = RN_E * G
SIGMA_EPS = 1e-3
WINDOW_RADIUS, REG_RADIUS, MARGIN = 13, 8, 24
FOCUS_NOISE_SD = 0.015214
GATES = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0]
ROIS = {'A 1630,1044': (1630, 1044, 256, 256), 'B 64,800': (64, 800, 256, 256)}
MIDDLE = 11

def sigma_luma(S):
    return np.sqrt(0.5 * (G * np.maximum(S, 0.0) + READ_DN * READ_DN))

def box_mean(a, r):
    """Mean over a (2r+1)^2 window, window clamped to the array, divided by the
    clamped count -- boxfilter.rs's border policy."""
    H, W = a.shape
    c = np.cumsum(np.cumsum(a, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    y0 = np.maximum(np.arange(H) - r, 0); y1 = np.minimum(np.arange(H) + r, H - 1)
    x0 = np.maximum(np.arange(W) - r, 0); x1 = np.minimum(np.arange(W) + r, W - 1)
    s = (c[np.ix_(y1 + 1, x1 + 1)] - c[np.ix_(y0, x1 + 1)]
         - c[np.ix_(y1 + 1, x0)] + c[np.ix_(y0, x0)])
    n = np.outer(y1 - y0 + 1, x1 - x0 + 1)
    return s / n

def sobel_mag(a):
    p = np.pad(a, 1, mode='edge')
    gx = (p[:-2, 2:] + 2*p[1:-1, 2:] + p[2:, 2:]
          - p[:-2, :-2] - 2*p[1:-1, :-2] - p[2:, :-2]) * 0.125
    gy = (p[2:, :-2] + 2*p[2:, 1:-1] + p[2:, 2:]
          - p[:-2, :-2] - 2*p[:-2, 1:-1] - p[:-2, 2:]) * 0.125
    return np.hypot(gx, gy)

def metrics(v, sig):
    dx = v[:-1, 1:] - v[:-1, :-1]
    dy = v[1:, :-1] - v[:-1, :-1]
    s2 = sig ** 2
    nsq = 2*s2[:-1, :-1] + s2[:-1, 1:] + s2[1:, :-1]
    raw = np.sqrt((dx*dx + dy*dy).mean()); nrm = np.sqrt(nsq.mean())
    return dict(m2=float((0.5*(np.abs(dx)+np.abs(dy))).mean()),
                iso=float(np.hypot(dx, dy).mean()),
                raw_rms=float(raw), noise_rms=float(nrm),
                corrected=float(np.sqrt(max(0.0, raw*raw - nrm*nrm))))

# crop windows in plane coords
crops = {k: (x - MARGIN, y - MARGIN, w + 2*MARGIN, h + 2*MARGIN)
         for k, (x, y, w, h) in ROIS.items()}

acc = {k: dict(g1=[], g2=[], reg=[]) for k in ROIS}
t0 = time.time()
for fi, path in enumerate(FRAMES):
    r = rawpy.imread(path)
    a = r.raw_image_visible
    for k, (cx, cy, cw, ch) in crops.items():
        sub = a[2*cy:2*(cy+ch), 2*cx:2*(cx+cw)].astype(np.float64)
        g1 = sub[0::2, 1::2]           # RGGB: G1 at (x=1, y=0)
        g2 = sub[1::2, 0::2]           #       G2 at (x=0, y=1)
        luma = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
        focus = box_mean(sobel_mag(luma), WINDOW_RADIUS) / np.maximum(sigma_luma(luma), SIGMA_EPS)
        acc[k]['reg'].append(box_mean(focus, REG_RADIUS).astype(np.float32))
        acc[k]['g1'].append(g1); acc[k]['g2'].append(g2)
    del r, a
    print(f'  frame {fi:2d} {os.path.basename(path)}  {time.time()-t0:6.1f} s', flush=True)

results = {}
for k, (x, y, w, h) in ROIS.items():
    reg = np.stack(acc[k]['reg'])            # (22, ch, cw)
    g1 = np.stack(acc[k]['g1']).astype(np.float64)
    g2 = np.stack(acc[k]['g2']).astype(np.float64)
    sl = (slice(MARGIN, MARGIN + h), slice(MARGIN, MARGIN + w))
    reg_r = reg[:, sl[0], sl[1]]
    g1_r, g2_r = g1[:, sl[0], sl[1]], g2[:, sl[0], sl[1]]

    best = reg_r.max(axis=0)
    win = reg_r.argmax(axis=0)               # numpy argmax: first max wins == ties to lower index
    single = 0.5 * (g1_r[MIDDLE] + g2_r[MIDDLE]) - BLACK
    base = metrics(single, sigma_luma(single))
    results[k] = {'single': base, 'gates': {}, 'mean_signal': float(single.mean())}
    print()
    print(f'=== ROI {k} ===')
    print(f'single frame {MIDDLE}: ' + '  '.join(f'{a}={b:.4f}' for a, b in base.items()))
    print(f'winner index: {len(np.unique(win))} distinct, median {int(np.median(win))}, '
          f'mode {np.bincount(win.ravel()).argmax()}')
    print(f'  gate  corrected  retention    raw_rms   noise_rms         m2        iso   n_eff(roi)')
    for gate in GATES:
        tol = gate * np.sqrt(2.0) * FOCUS_NOISE_SD
        admit = (best[None, :, :] - reg_r <= tol)
        admit[win, np.arange(h)[:, None], np.arange(w)[None, :]] = True
        n = admit.sum(axis=0)
        mg1 = (g1_r * admit).sum(axis=0) / n
        mg2 = (g2_r * admit).sum(axis=0) / n
        merged = 0.5 * (mg1 + mg2) - BLACK
        sig = sigma_luma(merged) / np.sqrt(n)
        m = metrics(merged, sig)
        m['n_eff_roi'] = float(n.mean())
        m['retention'] = m['corrected'] / base['corrected']
        results[k]['gates'][gate] = m
        print(f'  {gate:4.2f}  {m["corrected"]:9.4f}  {m["retention"]:8.3f}x  '
              f'{m["raw_rms"]:9.4f}  {m["noise_rms"]:9.4f}  {m["m2"]:9.4f}  {m["iso"]:9.4f}  '
              f'{m["n_eff_roi"]:9.3f}')
    c0 = results[k]['gates'][0.0]; c8 = results[k]['gates'][8.0]
    print(f'  gate 0 -> gate 8 :  m2 {c0["m2"]:.4f} -> {c8["m2"]:.4f} '
          f'({100*(c8["m2"]/c0["m2"]-1):+.1f}%)   '
          f'corrected {c0["corrected"]:.4f} -> {c8["corrected"]:.4f} '
          f'({100*(c8["corrected"]/c0["corrected"]-1):+.1f}%)')
    c2 = results[k]['gates'][2.0]
    print(f'  gate 0 -> gate 2 :  m2 {100*(c2["m2"]/c0["m2"]-1):+.1f}%   '
          f'corrected {100*(c2["corrected"]/c0["corrected"]-1):+.1f}%')

json.dump(results, open('out/03-merge-numpy.json', 'w'), indent=1)
print()
print('total', f'{time.time()-t0:.1f} s')
