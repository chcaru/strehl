"""M39 verification, script 12: the FPN bound AT THE GATE THE PROJECT INTENDS.

M38 says the -4.6%/-3.6% figures are "best cases at gate 8" and that "the design
conclusion rests on gate 2.0, where n_eff is 2.9 and the correction is small".
This checks that at gate 2.0 rather than gate 8.
"""
import numpy as np, json
res = json.load(open('out/03-merge-numpy.json'))
for k in res:
    g = res[k]['gates']
    r0, n0, ne0 = g['0.0']['raw_rms'], g['0.0']['noise_rms'], g['0.0']['n_eff_roi']
    r2, n2, ne2 = g['2.0']['raw_rms'], g['2.0']['noise_rms'], g['2.0']['n_eff_roi']
    print(f'ROI {k}: gate 0 n_eff {ne0:.3f}, gate 2.0 n_eff {ne2:.3f}')
    print('     f DN   P1 retention(0->2)   P2 retention(0->2)')
    for f in (0.0, 0.377, 1.0, 2.0, 5.0):
        c0a = np.sqrt(max(0, r0**2 - n0**2 - 4*f*f))
        c2a = np.sqrt(max(0, r2**2 - n2**2 - 4*f*f))
        c0b = np.sqrt(max(0, r0**2 - n0**2 - 4*f*f*(1-1/ne0)))
        c2b = np.sqrt(max(0, r2**2 - n2**2 - 4*f*f*(1-1/ne2)))
        print(f'  {f:8.3f}          {100*(c2a/c0a-1):+7.2f}%            {100*(c2b/c0b-1):+7.2f}%')
    print('     k        retention(0->2)')
    for kk in (0.96, 0.98, 1.00, 1.02, 1.05):
        c0 = np.sqrt(max(0, r0**2 - (kk*n0)**2)); c2 = np.sqrt(max(0, r2**2 - (kk*n2)**2))
        print(f'  {kk:8.2f}          {100*(c2/c0-1):+7.2f}%')
