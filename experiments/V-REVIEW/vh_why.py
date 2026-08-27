"""Which declared floor is rejecting every site?  Count the reasons."""
import sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_lib as H
import vh_measure as M

subject = sys.argv[1]
RR = float(sys.argv[2]) if len(sys.argv) > 2 else M.R_FULL
TT = float(sys.argv[3]) if len(sys.argv) > 3 else M.TAN_FULL
rgb = H.read_master(subject)
lm = H.lum(rgb).astype(np.float32)
g = cv2.GaussianBlur(lm, (0, 0), 2.0)
gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=5)
gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=5)
mag = cv2.magnitude(gx, gy)
h, w = lm.shape
cells = (28, 42)
ch, cw = h // cells[0], w // cells[1]
cand = []
for iy in range(cells[0]):
    for ix in range(cells[1]):
        y0, x0 = iy * ch, ix * cw
        blk = mag[y0:y0 + ch, x0:x0 + cw]
        j = int(np.argmax(blk)); yy, xx = divmod(j, blk.shape[1])
        cand.append((float(blk[yy, xx]), y0 + yy, x0 + xx))
cand.sort(reverse=True)

reason = dict(border=0, straight=0, step=0, flat=0, cross=0, fit=0, ok=0)
steps, ws, sdfr = [], [], []
for _, y, x in cand:
    if y < 150 or x < 150 or y > h - 150 or x > w - 150:
        reason["border"] += 1; continue
    nx, ny = float(gx[y, x]), float(gy[y, x]); n = np.hypot(nx, ny)
    if n < 1e-6: continue
    nx, ny = nx / n, ny / n
    tx, ty = -ny, nx
    ss = np.arange(-25, 26, 5.0)
    ang = np.arctan2(H.bilinear(gy, y + ss * ty, x + ss * tx),
                     H.bilinear(gx, y + ss * ty, x + ss * tx))
    cs, sn = np.cos(ang).mean(), np.sin(ang).mean()
    if np.sqrt(-2.0 * np.log(max(np.hypot(cs, sn), 1e-9))) > H.ORIENT_TOL:
        reason["straight"] += 1; continue
    us, p = H.profile_at(lm, y, x, nx, ny, RR, TT)
    if p[-1] < p[0]:
        nx, ny = -nx, -ny
        us, p = H.profile_at(lm, y, x, nx, ny, RR, TT)
    k = max(3, len(p) // 8)
    A = float(np.median(p[:k])); B = float(np.median(p[-k:])); step = B - A
    steps.append(step)
    if step < H.STEP_MIN:
        reason["step"] += 1; continue
    sdA = float(np.std(p[:k])); sdB = float(np.std(p[-k:]))
    sdfr.append(max(sdA, sdB) / step)
    if sdA > H.FLAT_MAX * step or sdB > H.FLAT_MAX * step:
        reason["flat"] += 1; continue
    q = (p - A) / step
    i10 = np.argmax(q >= 0.10); i90 = np.argmax(q >= 0.90)
    if i90 <= i10:
        reason["cross"] += 1; continue
    wid = float(us[i90]) - float(us[i10]); ws.append(wid)
    if float(us[i90]) + (H.SHOULDER + H.REFSPAN) * wid > us[-1] or \
       float(us[i10]) - (H.SHOULDER + H.REFSPAN) * wid < us[0]:
        reason["fit"] += 1; continue
    reason["ok"] += 1

print("SUBJECT", subject, " candidates", len(cand), " R=%.0f TAN=%.0f" % (RR, TT))
for k2, v in reason.items():
    print("  %-9s %5d" % (k2, v))
if steps:
    print("  step height DN   p50 %.0f  p90 %.0f  max %.0f (floor %.0f)"
          % (np.percentile(steps, 50), np.percentile(steps, 90), max(steps), H.STEP_MIN))
if sdfr:
    print("  plateau sd/step  p10 %.3f  p50 %.3f (floor %.3f)"
          % (np.percentile(sdfr, 10), np.percentile(sdfr, 50), H.FLAT_MAX))
if ws:
    print("  edge width px    p10 %.2f  p50 %.2f  p90 %.2f" % tuple(np.percentile(ws, [10, 50, 90])))
