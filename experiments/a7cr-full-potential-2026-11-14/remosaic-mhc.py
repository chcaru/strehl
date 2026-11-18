"""Control: what the shipped pipeline's CFA round trip does to a full-RGB image.

  python -X utf8 remosaic-mhc.py IN.npy OUT.npy [--keep-green]

IN: [3, H, W] float32 in the prototype's units (black-subtracted DN per
channel, not white-balanced). Each channel is white-balanced (gain = green
mean / channel mean over the image, as the product balances the mosaic
before demosaicing), sampled at its RGGB sites (red at even x and even y),
and the mosaic is demosaiced with Malvar-He-Cutler (the published 5x5
filters), then the balance is divided out. This is the shipped gather's
"sample each site's own colour back into CFA storage" followed by the final
demosaic, without its resampling. --keep-green keeps the input's green at
every site (only red and blue go through the round trip), to separate the
channels' shares of any loss.
"""
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp

src, dst = sys.argv[1], sys.argv[2]
keep_green = '--keep-green' in sys.argv
x = torch.from_numpy(np.load(src)).to(fp.DEV)
_, H, W = x.shape
m = x.mean((1, 2))
wb = (m[1] / m).view(3, 1, 1)
x = x * wb
yy, xx = torch.meshgrid(torch.arange(H, device=fp.DEV), torch.arange(W, device=fp.DEV), indexing='ij')
r_site = (yy % 2 == 0) & (xx % 2 == 0)
b_site = (yy % 2 == 1) & (xx % 2 == 1)
g_site = ~(r_site | b_site)
mos = torch.where(r_site, x[0], torch.where(b_site, x[2], x[1]))

k = {
    'g_at_rb': [[0, 0, -1, 0, 0], [0, 0, 2, 0, 0], [-1, 2, 4, 2, -1], [0, 0, 2, 0, 0], [0, 0, -1, 0, 0]],
    # colour at a green site whose ROW holds that colour
    'c_at_g_row': [[0, 0, .5, 0, 0], [0, -1, 0, -1, 0], [-1, 4, 5, 4, -1], [0, -1, 0, -1, 0], [0, 0, .5, 0, 0]],
    # colour at a green site whose COLUMN holds that colour
    'c_at_g_col': [[0, 0, -1, 0, 0], [0, -1, 4, -1, 0], [.5, 0, 5, 0, .5], [0, -1, 4, -1, 0], [0, 0, -1, 0, 0]],
    'r_at_b': [[0, 0, -1.5, 0, 0], [0, 2, 0, 2, 0], [-1.5, 0, 6, 0, -1.5], [0, 2, 0, 2, 0], [0, 0, -1.5, 0, 0]],
}
pad = F.pad(mos[None, None], (2, 2, 2, 2), mode='reflect')
f = {n: F.conv2d(pad, torch.tensor(v, device=fp.DEV, dtype=torch.float32)[None, None] / 8)[0, 0] for n, v in k.items()}
g_row_r = g_site & (yy % 2 == 0)   # green in a red row (red left and right)
g_row_b = g_site & (yy % 2 == 1)   # green in a blue row
G = torch.where(g_site, mos, f['g_at_rb'])
R = torch.where(r_site, mos, torch.where(g_row_r, f['c_at_g_row'], torch.where(g_row_b, f['c_at_g_col'], f['r_at_b'])))
B = torch.where(b_site, mos, torch.where(g_row_b, f['c_at_g_row'], torch.where(g_row_r, f['c_at_g_col'], f['r_at_b'])))
out = torch.stack([R, G, B]) / wb
if keep_green:
    out[1] = x[1] / wb[1]
np.save(dst, out.cpu().numpy().astype(np.float32))
print('wrote', dst, 'wb', wb.flatten().tolist())
