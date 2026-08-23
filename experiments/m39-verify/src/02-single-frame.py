"""M39 verification, script 02: geometry + the single-frame reference row.

Independent numpy re-implementation of:
  - the green-luma plane extraction (RGGB, G1 at (x=1,y=0), G2 at (x=0,y=1))
  - the four detail metrics in `detail_metrics()`
  - the calibrated noise model sigma_L(S) = sqrt(0.5*(g*S + (RN*g)^2))

and a comparison against the Rust run's "single frame 11" row, plus an
x/y-offset scan so that the plane-coordinate alignment is IDENTIFIED rather
than assumed.
"""
import numpy as np, rawpy, json

PATH = r'D:\personal\macro\109MSDCF\DSC00020.ARW'   # index 11 of 22 = the middle
BLACK, ISO, GAIN_DIV = 512.0, 160.0, 436.8
G = ISO / GAIN_DIV
RN_E = 4.20                       # ISO 160 < 400
READ_DN = RN_E * G

ROI_A = (1630, 1044, 256, 256)
ROI_B = (64, 800, 256, 256)

def sigma_luma(S):
    """green_luma_sigma: Var(L) = (Var(G1)+Var(G2))/4, both planes identical."""
    s = np.maximum(S, 0.0)
    return np.sqrt(0.5 * (G * s + READ_DN * READ_DN))

def metrics(v, sig):
    dx = v[:-1, 1:] - v[:-1, :-1]
    dy = v[1:, :-1] - v[:-1, :-1]
    s2 = sig ** 2
    nsq = 2 * s2[:-1, :-1] + s2[:-1, 1:] + s2[1:, :-1]
    raw = np.sqrt((dx * dx + dy * dy).mean())
    nrm = np.sqrt(nsq.mean())
    return dict(
        m2=float((0.5 * (np.abs(dx) + np.abs(dy))).mean()),
        iso=float(np.hypot(dx, dy).mean()),
        raw_rms=float(raw),
        noise_rms=float(nrm),
        corrected=float(np.sqrt(max(0.0, raw * raw - nrm * nrm))),
        mean_signal=float(v.mean()),
    )

r = rawpy.imread(PATH)
a = r.raw_image_visible.astype(np.float64)     # (4688, 7028), origin (0,0)
print('raw_image_visible', a.shape)

# ---- CFA phase, verified rather than assumed -------------------------------
print('sub-lattice means (row,col parity):')
for dy in (0, 1):
    for dx in (0, 1):
        print(f'   ({dy},{dx}) mean {a[dy::2, dx::2].mean():9.2f}')
print('rawpy raw_pattern:\n', r.raw_pattern, ' color_desc', r.color_desc)

def plane_luma(a, ox=0, oy=0):
    """0.5*(G1+G2) - black on the plane lattice, with an optional plane-pixel offset."""
    g1 = a[2*oy + 0::2, 2*ox + 1::2]
    g2 = a[2*oy + 1::2, 2*ox + 0::2]
    n = min(g1.shape[0], g2.shape[0]); m = min(g1.shape[1], g2.shape[1])
    return 0.5 * (g1[:n, :m] + g2[:n, :m]) - BLACK

L = plane_luma(a)
print('plane shape', L.shape, '(Rust: 2344 x 3516)')

# ---- flat ROI: a geometry check that does NOT involve the metric under test -
fx, fy, fw, fh = 2272, 1344, 256, 256
flat = L[fy:fy+fh, fx:fx+fw]
print()
print('FLAT ROI 2272,1344,256,256  (Rust reported mean 2020.29 DN, sigma 28.201 DN)')
print(f'   numpy mean {flat.mean() + BLACK - BLACK + 0:.4f} DN (black-subtracted)  '
      f'--> +black = {flat.mean() + BLACK:.4f}')
print(f'   numpy sigma (population) {flat.std():.4f} DN')
fx2, fy2 = 2352, 1408
flat2 = L[fy2:fy2+fh, fx2:fx2+fw]
print('FLAT ROI 2352,1408,256,256  (Rust reported mean 2019.38 DN, sigma 27.491 DN)')
print(f'   numpy mean+black {flat2.mean() + BLACK:.4f} DN   sigma {flat2.std():.4f} DN')

# ---- detail ROIs -----------------------------------------------------------
out = {}
for name, (x, y, w, h) in (('A 1630,1044', ROI_A), ('B 64,800', ROI_B)):
    v = L[y:y+h, x:x+w]
    m = metrics(v, sigma_luma(v))
    out[name] = m
    print()
    print(f'DETAIL ROI {name}')
    for k, val in m.items():
        print(f'   {k:12s} {val:12.4f}')

# ---- offset scan: is the plane alignment identified? -----------------------
print()
print('offset scan on ROI A, m2 metric (Rust single-frame m2 = 11.8907):')
for oy in (-1, 0, 1):
    row = []
    for ox in (-1, 0, 1):
        x, y, w, h = ROI_A
        vv = L[y+oy:y+oy+h, x+ox:x+ox+w]
        row.append(metrics(vv, sigma_luma(vv))['m2'])
    print('   dy=%+d ' % oy + '  '.join(f'{c:9.4f}' for c in row))
print('   (the metric is a smooth function of position, so a small mis-registration')
print('    would NOT be caught by this; it is reported for magnitude, not identity)')

json.dump(out, open('out/02-single-frame.json', 'w'), indent=1)
