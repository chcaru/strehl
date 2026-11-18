"""Coherent through-focus transfer, measured (what a neighbouring plane's
band coefficient actually contributes to the in-focus one).

  python -X utf8 coherence.py WORK_DIR TAG X0 Y0 [SIZE]

Two planes j apart do not hold scaled copies of the same band image when
highlights walk sideways with defocus (specular surfaces fill only part of the
aperture). What a linear fusion can use is the coherent part:

  t_b(j) = < Y_k Y_(k+j) > / < Y_k Y_k >_signal,   k the plane nearest focus,

per band b, averaged over an in-focus crop. Different planes carry
independent noise, so the numerator is unbiased for every j != 0; the j = 0
signal power cannot be measured that way (same noise in both factors) and is
extrapolated from j = +-1, +-2 with an even quadratic in log t. For
comparison the incoherent amplitude curve a_b(j) = sqrt(power_(k+j) /
power_k) (noise power subtracted) is printed: t / a is what the walk costs.

The crop [X0, Y0, SIZE] (default 2048) of every assembled plane is warped to
the reference geometry and band-split exactly as in fuse.py (split_fine),
per channel against the channel's own depth map. Sites near a
clipped sample and sites whose depth cell is not strongly in focus are left
out. Writes WORK_DIR/coherence-TAG.json and keeps green's band stack in
WORK_DIR/cohstack-TAG.npy ([planes, bands, SIZE, SIZE] float16) for the
trajectory experiments.
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp
import fuse

work, tag = Path(sys.argv[1]), sys.argv[2]
x0, y0 = int(sys.argv[3]), int(sys.argv[4])
size = int(sys.argv[5]) if len(sys.argv) > 5 else 2048
J = 14
H, W = fuse.H, fuse.W
with torch.no_grad():
    geo = fuse.Geometry(work, use_ca=False)
    dj = json.loads((work / f'depth-{tag}.json').read_text())
    planes = dj['planes']
    n = len(planes)
    NB = fuse.NBF
    raw = np.load(work / f'depth-{tag}-raw.npy')
    strong8 = torch.from_numpy(((raw[3] > 0) & (raw[4] > 25.0)).astype(np.float32)).to(fp.DEV)
    sl = (slice(y0, y0 + size), slice(x0, x0 + size))
    strong = F.interpolate(strong8[None, None], size=(H, W), mode='nearest')[0, 0][sl] > 0
    kappa = fuse.fine_noise_gain()
    out = {'crop': [x0, y0, size], 'offsets': list(range(-J, J + 1)), 'channels': []}
    for c, dname in ((0, f'depth-{tag}-own-red.npy'), (1, f'depth-{tag}.npy'), (2, f'depth-{tag}-own-blue.npy')):
        D8 = torch.from_numpy(np.load(work / dname)).to(fp.DEV)
        D = F.interpolate(D8[None, None], size=(H, W), mode='bilinear', align_corners=False)[0, 0][sl].clone()
        stack = torch.zeros(n, NB, size, size, device=fp.DEV, dtype=torch.float16)
        peak = torch.zeros(size, size, device=fp.DEV)
        level = torch.zeros(size, size, device=fp.DEV)
        for i, p in enumerate(planes):
            w = geo.warp(fuse.load_asm(work, p)[c], p, c)
            bands, q, dq = fuse.split_fine(w)
            for b in range(NB):
                stack[i, b] = bands[b][sl].half()
            peak = torch.maximum(peak, w[sl])
            if i == n // 2:
                level = fuse.up4(dq)[sl].clone()
            del w, bands, q, dq
        if c == 1:
            np.save(work / f'cohstack-{tag}.npy', stack.cpu().numpy())
            np.save(work / f'cohstack-{tag}-depth.npy', D.cpu().numpy())
        clip = (F.max_pool2d((peak > 0.8 * (15360.0 - 512.0)).float()[None, None], 25, 1, 12)[0, 0] > 0)
        kn = D.round().long().clamp(J, n - 1 - J)
        mask = (strong & ~clip & ((D - kn).abs() <= 0.5)).float()
        var = (fp.GAIN_DN_PER_E * level.clamp(min=0) + fp.READ_NOISE_DN ** 2) * (0.5 if c == 1 else 1.0)
        ch = {'sites_fraction': float(mask.mean()), 'bands': []}
        print(f'channel {"RGB"[c]}: sites used {100 * float(mask.mean()):.1f}% of the crop', flush=True)
        for b in range(NB):
            ref = torch.gather(stack[:, b].float(), 0, kn[None])[0]
            prod, power = [], []
            for j in range(-J, J + 1):
                other = torch.gather(stack[:, b].float(), 0, (kn + j)[None])[0]
                prod.append(float((ref * other * mask).double().sum()))
                power.append(float(((other * other - kappa[b] * var) * mask).double().sum()))
            prod, power = np.array(prod), np.array(power)
            ctr = J
            p1, p2 = 0.5 * (prod[ctr - 1] + prod[ctr + 1]), 0.5 * (prod[ctr - 2] + prod[ctr + 2])
            p0 = p1 * (p1 / p2) ** (1 / 3)
            t = prod / p0
            t[ctr] = 1.0
            a = np.sqrt(np.maximum(power, 0) / max(power[ctr], 1e-9))
            ch['bands'].append({'coherent': t.tolist(), 'incoherent_amplitude': a.tolist(),
                                'signal_power_extrapolated_over_measured': float(p0 / power[ctr])})
            print(f' band {b}: extrapolated signal power / (measured power - noise model) = {p0 / power[ctr]:.3f}')
            print('   offset     ' + ' '.join(f'{j:+5d}' for j in range(-J, J + 1, 2)))
            print('   coherent   ' + ' '.join(f'{v:5.2f}' for v in t[::2]))
            print('   amplitude  ' + ' '.join(f'{v:5.2f}' for v in a[::2]), flush=True)
        out['channels'].append(ch)
        del stack
        torch.cuda.empty_cache()
    (work / f'coherence-{tag}.json').write_text(json.dumps(out, indent=1) + '\n')
