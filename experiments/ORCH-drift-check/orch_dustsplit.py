"""Does the cross-master median show dust, or does it show that every subject is centred?

orch_dustmed.py commissioned cleanly: planting at common coordinates moved the statistic
1.60, planting at independent coordinates moved it 0.08. That certifies the median rejects
*independent* structure. It does not certify the thing that matters here, because the
confound is not independent -- macro subjects are centred by composition, so "appears in
the middle of every frame" is a property dust and subject texture share, and a randomly
placed plant cannot express it. The commissioning arm I ran was orthogonal to the failure
mode I actually face.

The discriminator that works is reproducibility rather than location. Dust is a fixed
physical pattern: split the corpus into two disjoint halves and the same motes appear in
the same places in both. A statistical consequence of centred composition is not fixed:
the two halves would each show centre-weighted structure, but not the SAME blobs. So:

  * per-pixel correlation of the two half-medians   (fixed pattern -> high)
  * top-N blob position overlap between halves      (fixed pattern -> high)
  * the same two quantities on a SHIFTED control, where one half is rolled by a large
    offset -- this destroys sensor registration while preserving every other statistical
    property of the data, and is the null the correlation must beat.

And it renders the median to PNG, because a dust map looks like dust and no summary
statistic substitutes for reading the artifact.
"""
import pathlib
import sys

import numpy as np

DS = 4


def blobs_of(m, thr, minpx=4):
    hits = m < thr
    ys, xs = np.nonzero(hits)
    hs = set(zip(ys.tolist(), xs.tolist()))
    seen = set()
    out = []
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if (sy, sx) in seen:
            continue
        q = [(sy, sx)]
        seen.add((sy, sx))
        cells = []
        while q:
            cy, cx = q.pop()
            cells.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    n = (cy + dy, cx + dx)
                    if n in hs and n not in seen:
                        seen.add(n)
                        q.append(n)
        if len(cells) >= minpx:
            a = np.array(cells)
            out.append((len(cells), int(a[:, 0].mean()), int(a[:, 1].mean()),
                        float(m[a[:, 0], a[:, 1]].min())))
    out.sort(key=lambda b: b[3])
    return out


def overlap(ba, bb, n=60, tol=6):
    a = [(b[1], b[2]) for b in ba[:n]]
    b = [(b[1], b[2]) for b in bb[:n]]
    hit = 0
    for ay, ax in a:
        if any(abs(ay - by) <= tol and abs(ax - bx) <= tol for by, bx in b):
            hit += 1
    return hit / max(1, len(a))


def png(m, path, lo=-6.0, hi=2.0):
    import zlib
    import struct
    v = np.clip((m - lo) / (hi - lo), 0, 1)
    g = (v * 255).astype(np.uint8)
    h, w = g.shape
    raw = b"".join(b"\x00" + g[i].tobytes() for i in range(h))
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c))
    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6))
            + chunk(b"IEND", b""))
    pathlib.Path(path).write_bytes(data)


def half_medians(stack, roll=0):
    n = stack.shape[0]
    a = stack[0::2]
    b = stack[1::2]
    if roll:
        b = np.roll(b, roll, axis=2)
    return np.median(a, axis=0), np.median(b, axis=0), a.shape[0], b.shape[0]


def report(ma, mb, label):
    fa = ma.ravel()
    fb = mb.ravel()
    r = float(np.corrcoef(fa, fb)[0, 1])
    ta = float(np.median(ma) - 6.0 * 1.4826 * np.median(np.abs(ma - np.median(ma))))
    tb = float(np.median(mb) - 6.0 * 1.4826 * np.median(np.abs(mb - np.median(mb))))
    ba = blobs_of(ma, ta)
    bb = blobs_of(mb, tb)
    ov = overlap(ba, bb)
    print(f"  {label:26s} corr {r:7.4f}   blobs {len(ba):5d}/{len(bb):5d}   "
          f"top60 overlap {100 * ov:5.1f}%")
    return r, ov


def main(argv):
    group = int(argv[0]) if argv else 7032
    import tifffile
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from orch_dustmed import load_residual

    d = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")
    paths = []
    for p in sorted(d.iterdir()):
        if p.suffix.lower() != ".tiff":
            continue
        with tifffile.TiffFile(str(p)) as tf:
            if tf.series[0].shape[1] == group:
                paths.append(p)
    print(f"group width {group}: {len(paths)} masters")
    resids = []
    for p in paths:
        r, _ = load_residual(p)
        resids.append(r)
    stack = np.stack(resids)
    del resids
    print(f"stack {stack.shape}\n")

    print("half-split reproducibility (the discriminator):")
    ma, mb, na, nb = half_medians(stack)
    print(f"  halves: {na} and {nb} masters, disjoint")
    r_true, ov_true = report(ma, mb, "REGISTERED")
    rolls = [137, 311, 613]
    ctrl = []
    for k in rolls:
        mc, md, _, _ = half_medians(stack, roll=k)
        ctrl.append(report(mc, md, f"SHIFTED (roll {k})"))
    r_ctrl = float(np.mean([c[0] for c in ctrl]))
    ov_ctrl = float(np.mean([c[1] for c in ctrl]))

    print()
    print(f"  registered correlation : {r_true:7.4f}")
    print(f"  shifted-control mean   : {r_ctrl:7.4f}")
    print(f"  registered overlap     : {100 * ov_true:5.1f}%")
    print(f"  shifted-control overlap: {100 * ov_ctrl:5.1f}%")
    fixed = (r_true > 0.30 and r_true > 3 * abs(r_ctrl)) and (ov_true > 0.40)
    print()
    if fixed:
        print("  VERDICT: a FIXED sensor-coordinate pattern is present.")
        print("           The blobs reproduce across disjoint halves and collapse when")
        print("           registration is destroyed. Consistent with dust.")
    else:
        print("  VERDICT: NO fixed sensor-coordinate pattern at this sensitivity.")
        print("           The blobs do NOT reproduce across disjoint halves, so the")
        print("           cross-master median is showing composition, not dust.")
        print("           The earlier 1319-blob count certifies nothing about dust.")

    full = np.median(stack, axis=0)
    outdir = pathlib.Path(r"C:\dev\strehl-out\ORCH-DUSTMAP")
    outdir.mkdir(parents=True, exist_ok=True)
    png(full, outdir / f"median_{group}.png")
    png(ma, outdir / f"half_a_{group}.png")
    png(mb, outdir / f"half_b_{group}.png")
    print(f"\n  rendered -> {outdir}")
    return 0 if fixed else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
