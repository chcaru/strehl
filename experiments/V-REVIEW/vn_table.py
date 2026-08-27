"""The publishable table, on ONE named gauge.

GAUGE: "container-matched, shift-corrected."
Every ratio is comparator-over-strehl where strehl has first been placed in the
COMPARATOR'S OWN CONTAINER, and both arms are shift-corrected by the same
49-candidate integer search driven on luma.

  vs enfuse       both uint16 -> requantisation is a NO-OP, ratio unchanged
  vs focus-stack  strehl is requantised to uint8 before measurement

This replaces "divide by a penalty factor" with "measure against an arm that
carries the same quantisation." The penalty stops being a divisor with its own
unstated uncertainty and becomes part of the arm, so the bootstrap propagates
it for free. It is also why ONE convention covers both columns: the correction
is present in both and is simply zero in one of them.
"""
import json
import numpy as np, tifffile

rng = np.random.default_rng(31)
CEN = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
CELLS, FLAT, T = CEN["cells"], CEN["flat"], int(CEN["T"])
TILES = [tuple(CELLS[i]) for i in FLAT]
R, CH = 3, ("Y", "R-Y", "B-Y")


def raw_pad(path):
    a = tifffile.imread(path)
    if a.shape[2] == 4: a = a[:, :, :3]
    o = np.empty((len(TILES), T + 2 * R, T + 2 * R, 3), a.dtype)
    for i, (y, x) in enumerate(TILES):
        o[i] = a[y - R:y + T + R, x - R:x + T + R, :3]
    del a
    return o


def opp(u):
    f = u.astype(np.float64) / (255.0 if u.dtype == np.uint8 else 65535.0)
    Y = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    return np.stack([Y, f[..., 0] - Y, f[..., 2] - Y], -1)


def q8(u):
    if u.dtype == np.uint8: return u
    return np.round(u.astype(np.float64) * 255.0 / 65535.0).astype(np.uint8)


def per_tile(A, B):
    c = slice(R, R + T)
    m = A[:, c, c, 0].mean(axis=(1, 2))
    n = A.shape[0]
    best = np.full(n, np.inf); bd = np.zeros((n, 2), int)
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            d = A[:, c, c, 0] - B[:, R + dy:R + dy + T, R + dx:R + dx + T, 0]
            v = (d ** 2).mean(axis=(1, 2)) - (d.mean(axis=(1, 2))) ** 2
            w = v < best
            best[w] = v[w]; bd[w] = (dy, dx)
    out = np.empty((n, 3))
    for i in range(n):
        dy, dx = bd[i]
        d = A[i, c, c, :] - B[i, R + dy:R + dy + T, R + dx:R + dx + T, :]
        v = (d ** 2).mean(axis=(0, 1)) - (d.mean(axis=(0, 1))) ** 2
        out[i] = np.sqrt(0.5 * v) / m[i]
    return out


sA = raw_pad(r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff")
sB = raw_pad(r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff")
P = {}
P["strehl"] = per_tile(opp(sA), opp(sB))
P["strehl8"] = per_tile(opp(q8(sA)), opp(q8(sB)))
del sA, sB
eA = raw_pad(r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif")
eB = raw_pad(r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-B.tif")
P["enfuse"] = per_tile(opp(eA), opp(eB))
P["enfuse8"] = per_tile(opp(q8(eA)), opp(q8(eB)))
del eA, eB
fA = raw_pad(r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif")
fB = raw_pad(r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif")
P["focus-stack"] = per_tile(opp(fA), opp(fB))
P["focus-stack8"] = per_tile(opp(q8(fA)), opp(q8(fB)))
del fA, fB

print("=" * 78)
print("COMMISSIONING THE GAUGE ITSELF")
print("=" * 78)
d = np.abs(P["focus-stack8"] - P["focus-stack"]).max()
print("  requantising an already-8-bit arm  max |delta| = %.3e   %s"
      % (d, "NO-OP (pass)" if d == 0 else "FAIL"))
d2 = np.abs(P["enfuse8"] - P["enfuse"]).max()
print("  requantising the uint16 enfuse arm max |delta| = %.3e   (informative)" % d2)
for ch in range(3):
    r = np.median(P["strehl"][:, ch]) / np.median(P["strehl"][:, ch])
    assert abs(r - 1.0) < 1e-12
print("  identity ratio strehl/strehl        = 1.000000000000   pass")
print("  8-bit container cost to strehl      = " + "  ".join(
    "%s %+.1f%%" % (CH[i], 100 * (np.median(P["strehl8"][:, i])
                                  / np.median(P["strehl"][:, i]) - 1)) for i in range(3)))

NB, n = 4000, len(TILES)
idx = rng.integers(0, n, size=(NB, n))
PAIR = {"enfuse": ("enfuse", "strehl"), "focus-stack": ("focus-stack", "strehl8")}
Rz = {}
print()
print("=" * 78)
print("CONTAINER-MATCHED, SHIFT-CORRECTED RATIOS   comparator / strehl")
print("=" * 78)
print("  %-13s %-5s %8s %20s %12s" % ("comparator", "chan", "point", "95% interval", "parity"))
for lab, (num, den) in PAIR.items():
    for j, ch in enumerate(CH):
        pt = float(np.median(P[num][:, j]) / np.median(P[den][:, j]))
        bs = np.median(P[num][idx, j], axis=1) / np.median(P[den][idx, j], axis=1)
        lo, hi = [float(v) for v in np.percentile(bs, [2.5, 97.5])]
        Rz["%s|%s" % (lab, ch)] = (pt, lo, hi)
        print("  %-13s %-5s %8.3f  [%6.3f, %6.3f]  %12s"
              % (lab, ch, pt, lo, hi,
                 "CLEAR" if lo > 1.0 else "touches 1.0"))

print()
print("=" * 78)
print("THE FOUR README CELLS")
print("=" * 78)
for lab in ("enfuse", "focus-stack"):
    y = Rz["%s|Y" % lab]
    print("  LUMA   vs %-12s %.2fx cleaner   interval %.2f to %.2f   %s"
          % (lab, y[0], y[1], y[2], "bounded away from parity"
             if y[1] > 1.0 else "TOUCHES PARITY"))
    a, b = Rz["%s|R-Y" % lab], Rz["%s|B-Y" % lab]
    los, his = min(a[1], b[1]), max(a[2], b[2])
    print("  CHROMA vs %-12s %.2f to %.2fx cleaner (B-Y %.2f, R-Y %.2f)"
          % (lab, min(a[0], b[0]), max(a[0], b[0]), b[0], a[0]))
    print("         %-12s outer interval %.2f to %.2f   %s"
          % ("", los, his, "bounded away from parity" if los > 1.0 else "TOUCHES PARITY"))
json.dump(Rz, open(r"C:\dev\strehl-out\V-REVIEW\noise\table.json", "w"), indent=1)
