"""M39 verification, script 10: CLAIM D -- is fact 24's "argmax raises gradient"
partly the noise fact 19 measured?

Reproduces BOTH selectors on the same frames:
  - unregularised argmax (fact 19's 1.253x / fact 24's operator)
  - 17x17-regularised argmax (fact 23's 1.075x, = this merge at gate 0)
and reports, for each, on a FLAT ROI the measured noise ratio, and on the two
DETAIL ROIs the m2 gradient and the corrected gradient against one frame.

Then decomposes the gradient rise into the part the MEASURED noise inflation
accounts for and the part it does not.

Also measures the corrected metric's own repeatability under a fresh noise draw,
so that "-4.6%" can be read against its own error bar.
"""
import numpy as np, rawpy, glob
FRAMES = sorted(glob.glob(r'D:\personal\macro\109MSDCF\*.ARW'))
BLACK, ISO, GAIN_DIV, RN_E = 512.0, 160.0, 436.8, 4.20
G = ISO / GAIN_DIV; READ_DN = RN_E * G
SIGMA_EPS = 1e-3; WR, RR, MARGIN = 13, 8, 24
MIDDLE = 11
ROIS = {'flat 2272,1344': (2272, 1344, 256, 256),
        'detail A 1630,1044': (1630, 1044, 256, 256),
        'detail B 64,800': (64, 800, 256, 256)}
def sigma_luma(S): return np.sqrt(0.5*(G*np.maximum(S,0.0) + READ_DN*READ_DN))
def box_mean(a, r):
    H, W = a.shape
    c = np.pad(np.cumsum(np.cumsum(a,0),1), ((1,0),(1,0)))
    y0 = np.maximum(np.arange(H)-r,0); y1 = np.minimum(np.arange(H)+r,H-1)
    x0 = np.maximum(np.arange(W)-r,0); x1 = np.minimum(np.arange(W)+r,W-1)
    return (c[np.ix_(y1+1,x1+1)]-c[np.ix_(y0,x1+1)]-c[np.ix_(y1+1,x0)]+c[np.ix_(y0,x0)]) \
           / np.outer(y1-y0+1, x1-x0+1)
def sobel_mag(a):
    p = np.pad(a, 1, mode='edge')
    gx = (p[:-2,2:]+2*p[1:-1,2:]+p[2:,2:]-p[:-2,:-2]-2*p[1:-1,:-2]-p[2:,:-2])*0.125
    gy = (p[2:,:-2]+2*p[2:,1:-1]+p[2:,2:]-p[:-2,:-2]-2*p[:-2,1:-1]-p[:-2,2:])*0.125
    return np.hypot(gx, gy)
def parts(v): return v[:-1,1:]-v[:-1,:-1], v[1:,:-1]-v[:-1,:-1]
def raw_rms(v):
    dx,dy = parts(v); return np.sqrt((dx*dx+dy*dy).mean())
def noise_rms(sig):
    s2 = sig**2; return np.sqrt((2*s2[:-1,:-1]+s2[:-1,1:]+s2[1:,:-1]).mean())
def m2(v):
    dx,dy = parts(v); return (0.5*(np.abs(dx)+np.abs(dy))).mean()
def corr_from(r, n): return np.sqrt(max(0.0, r*r-n*n))

acc = {k: dict(l=[], raw=[], reg=[]) for k in ROIS}
for path in FRAMES:
    rr = rawpy.imread(path); a = rr.raw_image_visible
    for k, (x, y, w, h) in ROIS.items():
        cx, cy, cw, ch = x-MARGIN, y-MARGIN, w+2*MARGIN, h+2*MARGIN
        sub = a[2*cy:2*(cy+ch), 2*cx:2*(cx+cw)].astype(np.float64)
        g1 = sub[0::2,1::2]; g2 = sub[1::2,0::2]
        luma_f = 0.5*(np.maximum(g1-BLACK,0.0)+np.maximum(g2-BLACK,0.0))
        focus = box_mean(sobel_mag(luma_f), WR)/np.maximum(sigma_luma(luma_f), SIGMA_EPS)
        acc[k]['raw'].append(focus.astype(np.float32))
        acc[k]['reg'].append(box_mean(focus, RR).astype(np.float32))
        acc[k]['l'].append(0.5*(g1+g2) - BLACK)
    del rr, a

sl = (slice(MARGIN, MARGIN+256), slice(MARGIN, MARGIN+256))
print('=' * 84)
print('CLAIM D -- the argmax baseline, both selectors, same frames')
print('=' * 84)
for k in ROIS:
    L = np.stack(acc[k]['l'])[:, sl[0], sl[1]]
    single = L[MIDDLE]
    out = {}
    for lbl, key in (('unregularised argmax', 'raw'), ('17x17-regularised argmax', 'reg')):
        F = np.stack(acc[k][key])[:, sl[0], sl[1]]
        win = F.argmax(axis=0)
        sel = np.take_along_axis(L, win[None], axis=0)[0]
        out[lbl] = (sel, win)
    print(f'\n--- ROI {k} ---')
    print(f'  single frame {MIDDLE}: sigma {single.std(ddof=0):8.4f} DN   mean {single.mean():9.2f} DN'
          f'   m2 {m2(single):8.4f}   raw_rms {raw_rms(single):8.4f}')
    ns = noise_rms(sigma_luma(single))
    print(f'                     model noise_rms {ns:8.4f}   corrected {corr_from(raw_rms(single), ns):8.4f}')
    for lbl, (sel, win) in out.items():
        ratio = sel.std(ddof=0)/single.std(ddof=0)
        nsel = noise_rms(sigma_luma(sel))
        print(f'  {lbl:26s} flat-sigma ratio {ratio:6.4f}x   '
              f'm2 {m2(sel):8.4f} ({100*(m2(sel)/m2(single)-1):+6.2f}%)   '
              f'raw_rms {raw_rms(sel):8.4f} ({100*(raw_rms(sel)/raw_rms(single)-1):+6.2f}%)')
        print(f'  {"":26s} corrected with MODEL noise (n=1)      '
              f'{corr_from(raw_rms(sel), nsel):8.4f} '
              f'({100*(corr_from(raw_rms(sel),nsel)/corr_from(raw_rms(single),ns)-1):+6.2f}%)')
        for infl, src in ((1.253, 'fact 19 unregularised'), (1.075, 'fact 23 regularised')):
            c = corr_from(raw_rms(sel), nsel*infl)
            print(f'  {"":26s} corrected if noise is really {infl:5.3f}x  {c:8.4f} '
                  f'({100*(c/corr_from(raw_rms(single),ns)-1):+6.2f}%)  [{src}]')
        print(f'  {"":26s} winner-index speckle (4-neighbour disagreement): '
              f'{100*np.mean([np.mean(win[:,1:]!=win[:,:-1]), np.mean(win[1:]!=win[:-1])]):5.2f}%')

# ------------- repeatability of the corrected metric ------------------------
print()
print('=' * 84)
print('the corrected metric against its own error bar')
print('=' * 84)
rng = np.random.default_rng(1039)
d = np.load('out/07-merged-rois.npz')
for k in ('A', 'B'):
    s = d[f'{k}_merged_8.0']; n0 = d[f'{k}_n_0.0']
    sig = sigma_luma(s)/np.sqrt(n0)
    vals = []
    for _ in range(40):
        v = s + sig*rng.standard_normal(s.shape)
        vals.append(corr_from(raw_rms(v), noise_rms(sig)))
    vals = np.array(vals)
    print(f'  ROI {k}: 40 fresh noise draws at the gate-0 noise level on a fixed signal:'
          f' corrected mean {vals.mean():.4f}, sd {vals.std(ddof=1):.4f} '
          f'({100*vals.std(ddof=1)/vals.mean():.3f}%)')
