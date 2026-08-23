"""M39 verification, script 11: closing numbers.

(a) the "~90% of the apparent loss was noise" figure, recomputed WITHIN one
    statistic instead of across two.
(b) the FPN bound under BOTH plausible parameterisations of where the fixed
    pattern sits relative to the calibrated single-frame sigma.
(c) the retention band implied by the measured uncertainty on the sigma scale.
"""
import numpy as np, json
res = json.load(open('out/03-merge-numpy.json'))

print('(a) "about 90% of the apparent detail loss was noise" -- in which statistic?')
for k in res:
    g = res[k]['gates']
    m2_0, m2_8 = g['0.0']['m2'], g['8.0']['m2']
    rr0, rr8 = g['0.0']['raw_rms'], g['8.0']['raw_rms']
    c0, c8 = g['0.0']['corrected'], g['8.0']['corrected']
    dm2 = 100*(m2_8/m2_0-1); drr = 100*(rr8/rr0-1); dc = 100*(c8/c0-1)
    print(f'  ROI {k}:')
    print(f'    apparent loss in m2 (mean|grad|, fact 24 convention): {dm2:+6.2f}%')
    print(f'    apparent loss in raw RMS (the corrected metric\'s OWN statistic, uncorrected): {drr:+6.2f}%')
    print(f'    corrected loss: {dc:+6.2f}%')
    print(f'    -> "explained" fraction across conventions (m2 vs corrected): '
          f'{100*(1-dc/dm2):5.1f}%   <-- the published ~90%')
    print(f'    -> "explained" fraction WITHIN one statistic (raw RMS vs corrected): '
          f'{100*(1-dc/drr):5.1f}%')

print()
print('(b) fixed-pattern floor f, under both parameterisations')
print('    P1: model = sigma_t^2/n, truth = sigma_t^2/n + f^2   (FPN outside the profile)')
print('    P2: model = (sigma_t^2+f^2)/n, truth = sigma_t^2/n + f^2  (FPN inside the profile)')
for k in res:
    g = res[k]['gates']
    r0, n0 = g['0.0']['raw_rms'], g['0.0']['noise_rms']
    r8, n8 = g['8.0']['raw_rms'], g['8.0']['noise_rms']
    ne0, ne8 = g['0.0']['n_eff_roi'], g['8.0']['n_eff_roi']
    print(f'  ROI {k}   (n_eff {ne0:.2f} at gate 0, {ne8:.2f} at gate 8)')
    print(f'      f DN     P1 retention   P2 retention')
    for f in (0.0, 0.377, 1.0, 2.0, 5.0, 10.0):
        # spatially white FPN -> coefficients sum to 4
        c0p1 = np.sqrt(max(0.0, r0**2 - (n0**2 + 4*f*f)))
        c8p1 = np.sqrt(max(0.0, r8**2 - (n8**2 + 4*f*f)))
        c0p2 = np.sqrt(max(0.0, r0**2 - (n0**2 + 4*f*f*(1-1/ne0))))
        c8p2 = np.sqrt(max(0.0, r8**2 - (n8**2 + 4*f*f*(1-1/ne8))))
        a = 100*(c8p1/c0p1-1) if c0p1 > 0 else float('nan')
        b = 100*(c8p2/c0p2-1) if c0p2 > 0 else float('nan')
        print(f'   {f:8.3f}      {a:+8.2f}%      {b:+8.2f}%')

print()
print('(c) retention band from the MEASURED uncertainty on the sigma scale k')
print('    (script 06: G1-G2 ratio p2..p10 reads 0.980-0.987 at 350-450 DN and')
print('     1.032-1.050 at 1300-2200 DN; temporal pairs read 0.980-0.992 at 2020 DN.')
print('     Taking k in [0.96, 1.05] as the measured envelope.)')
for k in res:
    g = res[k]['gates']
    r0, n0 = g['0.0']['raw_rms'], g['0.0']['noise_rms']
    r8, n8 = g['8.0']['raw_rms'], g['8.0']['noise_rms']
    lo, hi = None, None
    for kk in (0.96, 0.98, 1.00, 1.02, 1.05):
        c0 = np.sqrt(max(0.0, r0**2 - (kk*n0)**2)); c8 = np.sqrt(max(0.0, r8**2 - (kk*n8)**2))
        v = 100*(c8/c0-1)
        print(f'  ROI {k}  k={kk:4.2f}  retention {v:+7.2f}%')
