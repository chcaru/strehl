"""Pass 0: assemble every four-shot group with member motion compensated.

  python -X utf8 pass0.py CACHE_DIR WORK_DIR

Per plane: nominal assembly (fp.assemble), joint member fit (fp.member_motion),
compensation (fp.compensate). Writes WORK_DIR/asm/pNNN.u16 ([3, H, W] u16 =
round(4 * (value + 64)), value black-subtracted raw DN, green the mean of its
two samples), WORK_DIR/q4/pNNN.npy (green box-averaged 4x4, float16, for
alignment) and one line per plane in WORK_DIR/pass0.jsonl with the fit and the
2-photosite-period pattern amplitudes before and after (over tiles with strong
smoothed green gradient, and over the rest).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp

run = fp.Run(sys.argv[1])
work = Path(sys.argv[2])
(work / 'asm').mkdir(parents=True, exist_ok=True)
(work / 'q4').mkdir(parents=True, exist_ok=True)
done = set()
log = work / 'pass0.jsonl'
if log.exists():
    done = {json.loads(l)['plane'] for l in log.read_text().splitlines()}
clip = [0.9 * (run.white - run.black)] * 3
for p in run.planes:
    if p in done:
        continue
    t0 = time.time()
    m = run.meta[p]
    mem = run.members(p)
    rgb, src, gd = fp.assemble(mem, m['offsets'], m['gains'], run.P)
    del mem
    mot = fp.member_motion(rgb, src, gd, clip=clip)
    fixed = fp.compensate(rgb, src, mot)
    sx, sy = fp.grad(fp.gauss(rgb[1], 1.5))
    act = fp.gauss(sx * sx + sy * sy, 12.0)[::16, ::16] > 100.0 ** 2

    def ne(x):
        e = fp.nyquist_energy(x)
        return ([float(e[i][act].pow(2).mean().sqrt()) for i in range(3)],
                [float(e[i][~act].pow(2).mean().sqrt()) for i in range(3)])

    rec = {'plane': p, 'target': m['target'], 'motion': mot.tolist(), 'active_tiles': int(act.sum()),
           'pattern_before': [ne(rgb[c]) for c in range(3)], 'pattern_after': [ne(fixed[c]) for c in range(3)],
           'mean_level': [float(fixed[c].mean()) for c in range(3)]}
    out = ((fixed + 64.0) * 4.0).round().clamp(0, 65535).to(torch.int32).cpu().numpy().astype('<u2')
    out.tofile(work / 'asm' / f'p{p:03d}.u16')
    q = F.avg_pool2d(fixed[1][None, None], 4)[0, 0].half().cpu().numpy()
    np.save(work / 'q4' / f'p{p:03d}.npy', q)
    rec['seconds'] = time.time() - t0
    with log.open('a') as f:
        f.write(json.dumps(rec) + '\n')
    print(p, round(rec['seconds'], 1), [round(v, 3) for v in mot[:, 1].tolist()], flush=True)
    del rgb, fixed, gd
