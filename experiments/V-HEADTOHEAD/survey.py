"""Survey candidate ROIs in PRIOR coordinates: detail energy, flatness, clipping.
Used to pick (a) detail ROIs on the subject, (b) a genuinely FLAT ROI for the
rule-9 control, (c) occluding-edge locations."""
import numpy as np, tifffile, h2h
from scipy import ndimage

P, S = h2h.open_arms()
pg = np.ascontiguousarray(P[:, :, 1]).astype(np.float32)
clip = (np.asarray(P[:, :, 0]) >= 1.0) | (np.asarray(P[:, :, 1]) >= 1.0) | (np.asarray(P[:, :, 2]) >= 1.0)
T = 384
rows = []
for y in range(200, pg.shape[0] - T - 200, 192):
    for x in range(200, pg.shape[1] - T - 200, 192):
        sx, sy = h2h.prior_to_strehl(x + T/2, y + T/2)
        Ts = T * h2h.SCALE
        if sx - Ts/2 < 8 or sy - Ts/2 < 8 or sx + Ts/2 > S.shape[1]-8 or sy + Ts/2 > S.shape[0]-8:
            continue
        t = pg[y:y+T, x:x+T]
        c = clip[y:y+T, x:x+T].mean()
        hp = t - ndimage.uniform_filter(t, 9)
        rows.append((y, x, float(t.mean()), float(hp.std()), float(c), float(t.std())))
r = np.array(rows)
np.save("roi_survey.npy", r)
print("cells:", len(r))
unclipped = r[r[:, 4] == 0.0]
print("unclipped cells:", len(unclipped))
print("\nTOP DETAIL (high-pass sd), unclipped:")
for q in unclipped[np.argsort(-unclipped[:, 3])][:12]:
    print(f"  y={q[0]:5.0f} x={q[1]:5.0f} mean {q[2]:.3f} hp_sd {q[3]:.4f} sd {q[5]:.4f}")
print("\nFLATTEST unclipped cells with mean in [0.05,0.85] (rule-9 control candidates):")
m = unclipped[(unclipped[:, 2] > 0.05) & (unclipped[:, 2] < 0.85)]
for q in m[np.argsort(m[:, 3])][:12]:
    print(f"  y={q[0]:5.0f} x={q[1]:5.0f} mean {q[2]:.3f} hp_sd {q[3]:.5f} sd {q[5]:.5f}")
