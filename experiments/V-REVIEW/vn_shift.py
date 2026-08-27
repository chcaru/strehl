"""Correct my own potency prediction, then put every arm on ONE gauge.

MY DEFECT, disclosed: vn_comm.py predicted sqrt(s0^2 + sadd^2). Planting noise
on ONE side of a half-difference contributes only HALF its variance:
    0.5*Var(A+n-B) = s0^2 + 0.5*sadd^2
The 0.5x level passed at 5.01% error against the wrong formula and would have
shipped. Only the 2x level failed. Two levels was pre-registered; this is what
that buys.

THE GAUGE QUESTION. M127's load-bearing table pairs strehl 0.05187, which is
SHIFT-CORRECTED, with enfuse 0.08394 and focus-stack 0.09953, which are RAW.
Its own 4 control table gives the raw strehl figure as 0.07859. So the shift
correction is applied to one arm of a three-arm table. Here every arm gets the
same treatment, and the correction itself gets a selection-bias control that
cannot contain a real shift.
"""
import os, json
import numpy as np, tifffile
from scipy.ndimage import uniform_filter

CEN = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
CELLS, FLAT, T = CEN["cells"], CEN["flat"], int(CEN["T"])
TILES = [tuple(CELLS[i]) for i in FLAT]
R = 3
rng = np.random.default_rng(7)
CH = ("Y", "R-Y", "B-Y")
ARM = {
 "strehl": (r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff",
            r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff"),
 "enfuse": (r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif",
            r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-B.tif"),
 "focus-stack": (r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif",
                 r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif"),
}


def pad_tiles(path):
    a = tifffile.imread(path)
    s = 255.0 if a.dtype == np.uint8 else 65535.0
    if a.shape[2] == 4: a = a[:, :, :3]
    out = np.empty((len(TILES), T + 2 * R, T + 2 * R, 3), np.float64)
    for i, (y, x) in enumerate(TILES):
        out[i] = a[y - R:y + T + R, x - R:x + T + R, :3].astype(np.float64) / s
    del a
    return out


def opp(t):
    Y = 0.2126 * t[..., 0] + 0.7152 * t[..., 1] + 0.0722 * t[..., 2]
    return np.stack([Y, t[..., 0] - Y, t[..., 2] - Y], -1)


def sig(d, m):
    v = (d ** 2).mean(axis=(1, 2)) - (d.mean(axis=(1, 2))) ** 2
    return np.sqrt(0.5 * v) / m[:, None]


def raw_and_shift(A, B, m):
    """RAW = centre against centre. SHIFT = best of 49 integer offsets, chosen
    per tile on LUMA only, then applied to all three channels -- so chroma
    cannot be independently minimised and the search has one degree of freedom
    per tile, not three."""
    c = slice(R, R + T)
    raw = sig(A[:, c, c, :] - B[:, c, c, :], m)
    n = A.shape[0]
    best = np.full(n, np.inf); bdy = np.zeros(n, int); bdx = np.zeros(n, int)
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            sy = slice(R + dy, R + dy + T); sx = slice(R + dx, R + dx + T)
            d = A[:, c, c, 0] - B[:, sy, sx, 0]
            v = (d ** 2).mean(axis=(1, 2)) - (d.mean(axis=(1, 2))) ** 2
            better = v < best
            best[better] = v[better]; bdy[better] = dy; bdx[better] = dx
    out = np.empty((n, 3))
    for i in range(n):
        sy = slice(R + bdy[i], R + bdy[i] + T); sx = slice(R + bdx[i], R + bdx[i] + T)
        out[i] = sig((A[i:i + 1, c, c, :] - B[i:i + 1, sy, sx, :]), m[i:i + 1])[0]
    return raw, out, bdy, bdx


print("=" * 78)
print("POTENCY re-run with the CORRECTED prediction")
print("=" * 78)
A = opp(pad_tiles(ARM["strehl"][0])); B = opp(pad_tiles(ARM["strehl"][1]))
c = slice(R, R + T)
m = A[:, c, c, 0].mean(axis=(1, 2))
b0 = float(np.median(sig(A[:, c, c, :] - B[:, c, c, :], m)[:, 0]))
for k in (0.5, 2.0, 4.0):
    add = k * b0 * float(np.median(m))
    An = A.copy(); An[..., 0] += rng.normal(0, add, A.shape[:3])
    got = float(np.median(sig(An[:, c, c, :] - B[:, c, c, :], m)[:, 0]))
    pred = float(np.sqrt(b0 ** 2 + 0.5 * (add / float(np.median(m))) ** 2))
    e = abs(got - pred) / pred
    print("  planted %.1fx  measured %.5f  predicted %.5f  err %5.2f%%  %s"
          % (k, got, pred, 100 * e, "PASS" if e < 0.10 else "FAIL"))
del An

print()
print("=" * 78)
print("SELECTION-BIAS CONTROL for the shift search")
print("An arm that CANNOT contain a real shift: two independent noise fields.")
print("Any reduction here is the search fitting noise.")
print("=" * 78)
sh = (40, T + 2 * R, T + 2 * R, 3)
N1 = rng.normal(0, 1, sh); N2 = rng.normal(0, 1, sh)
mm = np.ones(40)
r0, r1, _, _ = raw_and_shift(N1, N2, mm)
print("  pure noise pair   raw %.5f -> shifted %.5f   spurious gain %+.2f%%"
      % (np.median(r0[:, 0]), np.median(r1[:, 0]),
         100 * (np.median(r1[:, 0]) / np.median(r0[:, 0]) - 1)))

print()
print("=" * 78)
print("ONE GAUGE  every arm, raw and shift-corrected")
print("=" * 78)
res = {}
for arm, (pa, pb) in ARM.items():
    if arm == "strehl":
        AA, BB = A, B
    else:
        AA, BB = opp(pad_tiles(pa)), opp(pad_tiles(pb))
    mm = AA[:, c, c, 0].mean(axis=(1, 2))
    r, s, dy, dx = raw_and_shift(AA, BB, mm)
    res[arm] = {"raw": r, "shift": s,
                "med_shift": float(np.median(np.hypot(dy, dx)))}
    print("  %-12s median |offset| %.2f px" % (arm, res[arm]["med_shift"]))
    for i, ch in enumerate(CH):
        print("      %-4s raw %.5f -> corrected %.5f  (%+.1f%%)"
              % (ch, np.median(r[:, i]), np.median(s[:, i]),
                 100 * (np.median(s[:, i]) / np.median(r[:, i]) - 1)))
    if arm != "strehl":
        del AA, BB

print()
print("=" * 78)
print("RATIOS on a CONSISTENT gauge, comparator / strehl, >1 = comparator noisier")
print("=" * 78)
print("  %-14s %-5s %14s %14s" % ("comparator", "chan", "both RAW", "both CORRECTED"))
out = {}
for arm in ("enfuse", "focus-stack"):
    for i, ch in enumerate(CH):
        rr = float(np.median(res[arm]["raw"][:, i]) / np.median(res["strehl"]["raw"][:, i]))
        cc = float(np.median(res[arm]["shift"][:, i]) / np.median(res["strehl"]["shift"][:, i]))
        out["%s|%s" % (arm, ch)] = {"raw": rr, "corrected": cc}
        print("  %-14s %-5s %14.3f %14.3f" % (arm, ch, rr, cc))
json.dump({"ratios": out,
           "med": {a: {ch: [float(np.median(res[a]["raw"][:, i])),
                            float(np.median(res[a]["shift"][:, i]))]
                       for i, ch in enumerate(CH)} for a in res}},
          open(r"C:\dev\strehl-out\V-REVIEW\noise\gauge.json", "w"), indent=1)
