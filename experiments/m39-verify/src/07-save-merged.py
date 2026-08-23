"""M39 verification, script 07: same merge as script 03, but SAVES the arrays so the
breaking tests in script 08 can work on the real merged output.
"""
import numpy as np, rawpy, glob
FRAMES = sorted(glob.glob(r'D:\personal\macro\109MSDCF\*.ARW'))
BLACK, ISO, GAIN_DIV, RN_E = 512.0, 160.0, 436.8, 4.20
G = ISO / GAIN_DIV; READ_DN = RN_E * G
SIGMA_EPS = 1e-3; WINDOW_RADIUS, REG_RADIUS, MARGIN = 13, 8, 24
FOCUS_NOISE_SD = 0.015214
GATES = [0.0, 2.0, 8.0]
ROIS = {'A': (1630, 1044, 256, 256), 'B': (64, 800, 256, 256)}
MIDDLE = 11

def sigma_luma(S): return np.sqrt(0.5 * (G * np.maximum(S, 0.0) + READ_DN * READ_DN))
def box_mean(a, r):
    H, W = a.shape
    c = np.pad(np.cumsum(np.cumsum(a, 0), 1), ((1,0),(1,0)))
    y0 = np.maximum(np.arange(H)-r, 0); y1 = np.minimum(np.arange(H)+r, H-1)
    x0 = np.maximum(np.arange(W)-r, 0); x1 = np.minimum(np.arange(W)+r, W-1)
    s = (c[np.ix_(y1+1, x1+1)] - c[np.ix_(y0, x1+1)] - c[np.ix_(y1+1, x0)] + c[np.ix_(y0, x0)])
    return s / np.outer(y1-y0+1, x1-x0+1)
def sobel_mag(a):
    p = np.pad(a, 1, mode='edge')
    gx = (p[:-2,2:] + 2*p[1:-1,2:] + p[2:,2:] - p[:-2,:-2] - 2*p[1:-1,:-2] - p[2:,:-2]) * 0.125
    gy = (p[2:,:-2] + 2*p[2:,1:-1] + p[2:,2:] - p[:-2,:-2] - 2*p[:-2,1:-1] - p[:-2,2:]) * 0.125
    return np.hypot(gx, gy)

crops = {k: (x-MARGIN, y-MARGIN, w+2*MARGIN, h+2*MARGIN) for k, (x,y,w,h) in ROIS.items()}
acc = {k: dict(g1=[], g2=[], reg=[]) for k in ROIS}
for path in FRAMES:
    r = rawpy.imread(path); a = r.raw_image_visible
    for k, (cx, cy, cw, ch) in crops.items():
        sub = a[2*cy:2*(cy+ch), 2*cx:2*(cx+cw)].astype(np.float64)
        g1 = sub[0::2,1::2]; g2 = sub[1::2,0::2]
        luma = 0.5*(np.maximum(g1-BLACK,0.0) + np.maximum(g2-BLACK,0.0))
        focus = box_mean(sobel_mag(luma), WINDOW_RADIUS) / np.maximum(sigma_luma(luma), SIGMA_EPS)
        acc[k]['reg'].append(box_mean(focus, REG_RADIUS).astype(np.float32))
        acc[k]['g1'].append(g1); acc[k]['g2'].append(g2)
    del r, a

save = {}
for k, (x, y, w, h) in ROIS.items():
    sl = (slice(MARGIN, MARGIN+h), slice(MARGIN, MARGIN+w))
    reg = np.stack(acc[k]['reg'])[:, sl[0], sl[1]]
    g1 = np.stack(acc[k]['g1']).astype(np.float64)[:, sl[0], sl[1]]
    g2 = np.stack(acc[k]['g2']).astype(np.float64)[:, sl[0], sl[1]]
    best = reg.max(axis=0); win = reg.argmax(axis=0)
    save[f'{k}_single'] = 0.5*(g1[MIDDLE]+g2[MIDDLE]) - BLACK
    save[f'{k}_win'] = win
    for gate in GATES:
        tol = gate*np.sqrt(2.0)*FOCUS_NOISE_SD
        admit = (best[None] - reg <= tol)
        admit[win, np.arange(h)[:,None], np.arange(w)[None,:]] = True
        n = admit.sum(axis=0)
        save[f'{k}_merged_{gate}'] = 0.5*((g1*admit).sum(0)/n + (g2*admit).sum(0)/n) - BLACK
        save[f'{k}_n_{gate}'] = n
    print(k, 'done', {g: float(save[f'{k}_n_{g}'].mean()) for g in GATES})
np.savez_compressed('out/07-merged-rois.npz', **save)
print('saved out/07-merged-rois.npz')
