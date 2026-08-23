"""M39 verification, script 04: how much does the -4.6% depend on things not measured?

(a) Does the "17.1412 vs 2*sigma = 17.14" hand calculation actually discriminate the
    (2,1,1) coefficient structure, or only the SUM of the coefficients?
(b) How does the corrected retention move if the calibrated sigma is scaled by k?
    (The run's own banner says the gain is "DERIVED from white-level consistency,
     not a photon-transfer measurement".)
(c) How does it move under a fixed-pattern-noise floor f that does not average down?
(d) How does it move if the gate-0 output is really 1.074x noisier than one frame
    (fact 320/321) while predicted_sigma says 1.000x?
"""
import numpy as np, rawpy, json

BLACK, ISO, GAIN_DIV, RN_E = 512.0, 160.0, 436.8, 4.20
G = ISO / GAIN_DIV; READ_DN = RN_E * G
ROI_A = (1630, 1044, 256, 256); ROI_B = (64, 800, 256, 256)

def sigma_luma(S, k=1.0):
    return k * np.sqrt(0.5 * (G * np.maximum(S, 0.0) + READ_DN * READ_DN))

# ---------------------------------------------------------------- (a)
r = rawpy.imread(r'D:\personal\macro\109MSDCF\DSC00020.ARW')
a = r.raw_image_visible.astype(np.float64)
L = 0.5 * (a[0::2, 1::2] + a[1::2, 0::2]) - BLACK
print('(a) can the hand calculation see the coefficient STRUCTURE?')
for name, (x, y, w, h) in (('A', ROI_A), ('B', ROI_B)):
    v = L[y:y+h, x:x+w]; s2 = sigma_luma(v) ** 2
    sets = {'(2,1,1) as shipped': (2, 1, 1), '(1,1,2)': (1, 1, 2), '(4,0,0)': (4, 0, 0),
            '(0,2,2)': (0, 2, 2), '(1.34,1.33,1.33)': (4/3, 4/3, 4/3)}
    ref = None
    print(f'  ROI {name}: mean signal {v.mean():.4f} DN   '
          f'2*sigma_L(mean) = {2*sigma_luma(v.mean()):.4f} DN')
    for lbl, (c0, c1, cw) in sets.items():
        nsq = c0*s2[:-1, :-1] + c1*s2[:-1, 1:] + cw*s2[1:, :-1]
        val = np.sqrt(nsq.mean())
        if ref is None: ref = val
        print(f'     {lbl:20s} noise_rms = {val:9.5f}   '
              f'({100*(val/ref-1):+7.4f}% vs shipped)')

# ---------------------------------------------------------------- (b)(c)(d)
res = json.load(open('out/03-merge-numpy.json'))
print()
print('(b) retention gate0 -> gate8 if the calibrated sigma is scaled by k')
print('    (the model term enters both ends, so this does NOT cancel)')
hdr = '     k    ' + '  '.join(f'ROI {n[0]}' for n in res)
print('       k    ROI A corrected0 corrected8  retention      ROI B corrected0 corrected8  retention')
for k in (0.6, 0.7, 0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2, 1.3, 1.5):
    row = f'   {k:5.2f}  '
    for name in res:
        g = res[name]['gates']
        c = []
        for gt in ('0.0', '8.0'):
            raw = g[gt]['raw_rms']; nrm = g[gt]['noise_rms'] * k
            c.append(np.sqrt(max(0.0, raw*raw - nrm*nrm)))
        ret = c[1]/c[0] if c[0] > 0 else float('nan')
        row += f'  {c[0]:10.4f} {c[1]:10.4f}  {100*(ret-1):+8.2f}%'
    print(row)

print()
print('(c) retention if a fixed-pattern floor f DN (identical at every gate, does NOT')
print('    average down) is present and unsubtracted by the model')
print('       f DN   ROI A retention   ROI B retention')
for f in (0.0, 0.377, 1.0, 2.0, 5.0, 10.0, 15.0):
    row = f'   {f:6.3f}  '
    for name in res:
        g = res[name]['gates']
        c = []
        for gt in ('0.0', '8.0'):
            raw = g[gt]['raw_rms']; nrm2 = g[gt]['noise_rms']**2 + 4*f*f
            c.append(np.sqrt(max(0.0, raw*raw - nrm2)))
        ret = c[1]/c[0] if c[0] > 0 else float('nan')
        row += f'      {100*(ret-1):+8.2f}%   '
    print(row)
print('    (4*f^2 because the coefficients 2+1+1 sum to 4 for a spatially white FPN)')

print()
print('(d) if gate 0 is really 1.074x noisier than one frame (facts 320/321) but the')
print('    model says 1.000x, and the model is right at gate 8:')
for name in res:
    g = res[name]['gates']
    raw0 = g['0.0']['raw_rms']; n0 = g['0.0']['noise_rms']
    raw8 = g['8.0']['raw_rms']; n8 = g['8.0']['noise_rms']
    c0 = np.sqrt(max(0.0, raw0**2 - (1.074*n0)**2)); c8 = np.sqrt(max(0.0, raw8**2 - n8**2))
    print(f'   ROI {name}: corrected0 {c0:.4f} (was {g["0.0"]["corrected"]:.4f}), '
          f'retention {100*(c8/c0-1):+.2f}% (was {100*(g["8.0"]["corrected"]/g["0.0"]["corrected"]-1):+.2f}%)')
