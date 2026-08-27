"""Re-derive the four cells on the SHIP-V4 pin and apply the pre-registered rule."""
import hashlib, json
import numpy as np, tifffile

CEN = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
CELLS, FLAT, T = CEN["cells"], CEN["flat"], int(CEN["T"])
TILES = [tuple(CELLS[i]) for i in FLAT]
R, CH = 3, ("Y", "R-Y", "B-Y")
rng = np.random.default_rng(31)

V3 = (r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff",
      r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff")
V4 = (r"C:\dev\strehl-out\V-REVIEW\shipv4\113-A-g1-v4.tiff",
      r"C:\dev\strehl-out\V-REVIEW\shipv4\113-B-g1-v4.tiff")
CMP = {"enfuse": (r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif",
                  r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-B.tif"),
       "focus-stack": (r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif",
                       r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif")}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest().upper()


print("=" * 78)
print("INPUT IDENTITY  which bytes each arm actually reads")
print("=" * 78)
for a, b in zip(V3, V4):
    ha, hb = sha(a), sha(b)
    print("  %-22s V3 %s" % (a.split("\\")[-1], ha[:32]))
    print("  %-22s V4 %s   identical=%s" % (b.split("\\")[-1], hb[:32], ha == hb))


def pad(p):
    a = tifffile.imread(p)
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
    return u if u.dtype == np.uint8 else np.round(
        u.astype(np.float64) * 255.0 / 65535.0).astype(np.uint8)


def per_tile(A, B):
    c = slice(R, R + T)
    m = A[:, c, c, 0].mean(axis=(1, 2)); n = A.shape[0]
    best = np.full(n, np.inf); bd = np.zeros((n, 2), int)
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            d = A[:, c, c, 0] - B[:, R + dy:R + dy + T, R + dx:R + dx + T, 0]
            v = (d ** 2).mean(axis=(1, 2)) - (d.mean(axis=(1, 2))) ** 2
            w = v < best; best[w] = v[w]; bd[w] = (dy, dx)
    out = np.empty((n, 3))
    for i in range(n):
        dy, dx = bd[i]
        d = A[i, c, c, :] - B[i, R + dy:R + dy + T, R + dx:R + dx + T, :]
        v = (d ** 2).mean(axis=(0, 1)) - (d.mean(axis=(0, 1))) ** 2
        out[i] = np.sqrt(0.5 * v) / m[i]
    return out


uA, uB = pad(V4[0]), pad(V4[1])
P = {"strehl": per_tile(opp(uA), opp(uB)), "strehl8": per_tile(opp(q8(uA)), opp(q8(uB)))}
del uA, uB
for k, (pa, pb) in CMP.items():
    a, b = pad(pa), pad(pb)
    P[k] = per_tile(opp(a), opp(b)); del a, b

PUB = {"enfuse|Y": (1.618, 1.511, 1.709), "enfuse|B-Y": (1.606, 1.525, 1.702),
       "enfuse|R-Y": (1.813, 1.717, 1.966), "focus-stack|Y": (1.475, 1.400, 1.514),
       "focus-stack|B-Y": (1.640, 1.550, 1.710), "focus-stack|R-Y": (1.661, 1.592, 1.755)}
PAIR = {"enfuse": ("enfuse", "strehl"), "focus-stack": ("focus-stack", "strehl8")}
idx = rng.integers(0, len(TILES), size=(4000, len(TILES)))

print()
print("=" * 78)
print("SHIP-V3 (published) vs SHIP-V4 (this run), same gauge, same code")
print("=" * 78)
print("  %-13s %-4s %8s %8s %9s %20s %8s"
      % ("comparator", "ch", "V3 pub", "V4", "delta", "V4 95% interval", "parity"))
verdicts = []
for lab, (num, den) in PAIR.items():
    for j, ch in enumerate(CH):
        key = "%s|%s" % (lab, ch)
        pt = float(np.median(P[num][:, j]) / np.median(P[den][:, j]))
        bs = np.median(P[num][idx, j], axis=1) / np.median(P[den][idx, j], axis=1)
        lo, hi = [float(v) for v in np.percentile(bs, [2.5, 97.5])]
        p3, l3, h3 = PUB[key]
        inside = l3 <= pt <= h3
        clear = lo > 1.0
        verdicts.append((key, inside, clear, round(p3, 2) == round(pt, 2)))
        print("  %-13s %-4s %8.3f %8.3f %+9.5f  [%6.3f, %6.3f] %8s"
              % (lab, ch, p3, pt, pt - p3, lo, hi, "CLEAR" if clear else "AT 1.0"))

print()
print("=" * 78)
print("PRE-REGISTERED DECISION RULE  (committed e358bd3c, before any render)")
print("=" * 78)
n_in = sum(1 for v in verdicts if v[1]); n_cl = sum(1 for v in verdicts if v[2])
n_rd = sum(1 for v in verdicts if v[3])
print("  points inside the published interval : %d of 6" % n_in)
print("  intervals clear of parity            : %d of 6" % n_cl)
print("  README cells unchanged at 2 decimals : %d of 6" % n_rd)
print()
if n_in == 6 and n_cl == 6 and n_rd == 6:
    print("  VERDICT: HOLD.  Strike the scope line, publish nothing new.")
elif n_in == 6 and n_cl == 6:
    print("  VERDICT: RESTATE DIGITS.")
else:
    print("  VERDICT: RESTATE THE CLAIM.")
