"""Classify every block's through-focus curve: FLAT / SINGLE-PEAK / MULTI-PEAK.

The detector is `experiments/V-VEILCLAW/curve.py`'s, imported verbatim -- the
same `smooth(v, 7)`, the same floor (10th percentile of the smoothed curve),
the same `min_prom=0.10`, `min_sep=15`.  That is deliberate: the claw result
this whole map is calibrated against was produced by those parameters, and a
screening statistic computed with different ones would not be comparable.

ONE correction is offered alongside it.  `curve.py::peaks` measures prominence
against `v[:i].min()` and `v[i+1:].min()` -- the GLOBAL minimum on each side,
not the highest saddle between this peak and the neighbouring higher one.  For
a curve that descends far away from a peak, that is the wrong number and it is
wrong in the direction that inflates the multi-peak count: a small ripple
riding a broad shoulder gets credited with the whole descent to the far end of
the bracket.  Over a 299-frame stack, where the response falls to the noise
floor at both ends, every local wiggle is scored against that floor.
`peaks_topo` implements the standard topographic definition instead (walk out
to the first higher sample on each side; prominence is measured from the
higher of the two intervening minima).  Both are reported.  The topographic
one is the headline, because it is the one that is right.

Arms and normalisations exist so that each confound can be shown rather than
asserted:
  --arm resp|fixed      drift-tracked blocks vs fixed blocks (the drift null)
  --norm plain|geo|gnorm  plain is V-VEILCLAW exactly; geo removes the
                        1/a^2 tilt that demagnification puts on |Laplacian|;
                        gnorm divides by the frame's own global mean response.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "V-VEILCLAW"))
from curve import peaks, smooth  # noqa: E402  (V-VEILCLAW's, verbatim)

FLAT, SINGLE, MULTI = 0, 1, 2


def peaks_topo(v, floor, min_prom=0.10, min_sep=15):
    """`curve.peaks` with true topographic prominence.

    Same signature, same floor normalisation, same greedy min_sep pruning;
    only the reference level changes, from the global minimum on each side to
    the highest saddle -- i.e. walk out until a sample higher than this peak,
    take the minimum along the way, and use the larger of the two sides.
    """
    n = len(v)
    out = []
    for i in range(1, n - 1):
        if not (v[i] >= v[i - 1] and v[i] > v[i + 1]):
            continue
        j = i - 1
        lo = v[i]
        while j >= 0 and v[j] <= v[i]:
            lo = min(lo, v[j])
            j -= 1
        left = lo
        j = i + 1
        lo = v[i]
        while j < n and v[j] <= v[i]:
            lo = min(lo, v[j])
            j += 1
        right = lo
        out.append((i, v[i], (v[i] - max(left, right)) / max(floor, 1e-9)))
    out.sort(key=lambda t: -t[2])
    kept = []
    for i, val, prom in out:
        if prom < min_prom or any(abs(i - j) < min_sep for j, _, _ in kept):
            continue
        kept.append((i, val, prom))
    return sorted(kept)


def classify(v, detector, min_prom=0.10, min_sep=15, k=7):
    s = smooth(v, k)
    pk = detector(s, float(np.percentile(s, 10)), min_prom, min_sep)
    return pk, (FLAT if not pk else SINGLE if len(pk) == 1 else MULTI)


def normalise(t, a, gmean, mode):
    if mode == "plain":
        return t
    if mode == "geo":                # |Laplacian| ~ 1/a^2 under demagnification
        return t * (a ** 2 / a[0] ** 2)[:, None, None]
    if mode == "gnorm":
        return t / (gmean / gmean[0])[:, None, None]
    raise SystemExit(f"unknown norm {mode}")


def run_grid(t, ok, detector, ks, **kw):
    nf, ny, nx = t.shape
    cls = np.full((ny, nx), -1, np.int8)
    npk = np.zeros((ny, nx), np.int16)
    sep = np.zeros((ny, nx), np.float32)
    for i in range(ny):
        for j in range(nx):
            if not ok[i, j]:
                continue
            pk, c = classify(t[:, i, j], detector, **kw)
            cls[i, j], npk[i, j] = c, len(pk)
            if len(pk) >= 2:
                idx = [ks[p[0]] for p in pk]
                sep[i, j] = max(idx) - min(idx)
    return cls, npk, sep


def frac(cls):
    m = cls >= 0
    n = int(m.sum())
    if not n:
        return dict(n=0, flat=float("nan"), single=float("nan"),
                    multi=float("nan"))
    return dict(n=n, flat=float((cls[m] == FLAT).mean()),
                single=float((cls[m] == SINGLE).mean()),
                multi=float((cls[m] == MULTI).mean()))


def render(cls, sep, path, title, ref_shape, b):
    import cv2
    ny, nx = cls.shape
    img = np.zeros((ny, nx, 3), np.uint8)
    img[cls == FLAT] = (60, 60, 60)
    img[cls == SINGLE] = (150, 110, 40)                     # BGR: steel blue
    m = cls == MULTI
    if m.any():                       # red, brighter the wider the separation
        s = np.clip(sep[m] / max(np.percentile(sep[m], 90), 1.0), 0.25, 1.0)
        img[m] = np.stack([np.full(s.shape, 40.0), 40 + 40 * s,
                           110 + 145 * s], 1).astype(np.uint8)
    img[cls < 0] = (0, 0, 0)
    sc = max(1, int(round(720 / max(ny, 1))))
    big = cv2.resize(img, (nx * sc, ny * sc), interpolation=cv2.INTER_NEAREST)
    bar = np.zeros((26, big.shape[1], 3), np.uint8)
    cv2.putText(bar, title, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (235, 235, 235), 1)
    cv2.imwrite(str(path), np.vstack([bar, big]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--blocks", default="")
    ap.add_argument("--arms", default="resp,fixed")
    ap.add_argument("--norms", default="plain,geo,gnorm")
    ap.add_argument("--min-prom", type=float, default=0.10)
    ap.add_argument("--min-sep", type=int, default=15)
    ap.add_argument("--smooth", type=int, default=7)
    ap.add_argument("--maps", default="resp/plain",
                    help="arm/norm combos to render, comma separated")
    a = ap.parse_args()

    outd = pathlib.Path(a.out)
    z = np.load(outd / "tensors" / f"{a.subject}.npz")
    ks = z["ks"]
    blocks = ([int(v) for v in a.blocks.split(",")] if a.blocks
              else [int(v) for v in z["blocks"]])
    kw = dict(min_prom=a.min_prom, min_sep=a.min_sep, k=a.smooth)
    dets = {"global": peaks, "topo": peaks_topo}
    print(f"{a.subject}: {len(ks)} frames, blocks {blocks}, "
          f"smooth={a.smooth} min_prom={a.min_prom} min_sep={a.min_sep}")

    rec = dict(subject=a.subject, nframes=int(len(ks)),
               params=dict(smooth=a.smooth, min_prom=a.min_prom,
                           min_sep=a.min_sep),
               probes={}, grids=[])

    names = [str(s) for s in z["probe_names"]]
    if names:
        print("\nPROBES (named windows, master coords):")
        for arm, key in (("resp", "probe_resp"), ("fixed", "probe_fixed")):
            for i, nm in enumerate(names):
                v = z[key][:, i].astype(np.float64)
                for dn, det in dets.items():
                    pk, c = classify(v, det, **kw)
                    tag = ["FLAT", "SINGLE-PEAK", "MULTI-PEAK"][c]
                    d = "  ".join(f"f{ks[p[0]]} prom={p[2]:.2f}" for p in pk)
                    print(f"  {arm:<5} {nm:<5} {dn:<6} {tag:<11} "
                          f"floor={np.percentile(smooth(v, a.smooth), 10):7.1f}"
                          f"  {d}")
                    rec["probes"][f"{arm}/{nm}/{dn}"] = dict(
                        cls=tag, peaks=[[int(ks[p[0]]), float(p[1]),
                                         float(p[2])] for p in pk])

    want = set(a.maps.split(",")) if a.maps else set()
    print(f"\n{'block':>6} {'arm':>6} {'norm':>6} {'det':>7} {'blocks':>7}"
          f" {'flat':>7} {'single':>7} {'MULTI':>7}  {'med sep':>7}")
    for B in blocks:
        t0 = z[f"resp_b{B}"], z[f"fixed_b{B}"]
        ok = z[f"ok_b{B}"]
        for arm, t_raw in zip(("resp", "fixed"), t0):
            if arm not in a.arms.split(","):
                continue
            for nm in a.norms.split(","):
                t = normalise(t_raw.astype(np.float64), z["a"], z["gmean"], nm)
                for dn, det in dets.items():
                    cls, npk, sep = run_grid(t, ok, det, ks, **kw)
                    f = frac(cls)
                    ms = float(np.median(sep[cls == MULTI])) if (
                        cls == MULTI).any() else float("nan")
                    print(f"{B:>6} {arm:>6} {nm:>6} {dn:>7} {f['n']:>7}"
                          f" {f['flat']:>7.3f} {f['single']:>7.3f}"
                          f" {f['multi']:>7.3f}  {ms:>7.0f}")
                    rec["grids"].append(dict(block=B, arm=arm, norm=nm,
                                             det=dn, med_sep=ms, **f))
                    if f"{arm}/{nm}" in want and dn == "topo":
                        p = outd / "maps" / f"{a.subject}-b{B}-{arm}-{nm}.png"
                        p.parent.mkdir(parents=True, exist_ok=True)
                        render(cls, sep, p,
                               f"{a.subject}  b={B}px  {arm}/{nm}/topo  "
                               f"multi={f['multi'] * 100:.1f}%  "
                               f"(red=MULTI blue=SINGLE grey=FLAT)",
                               z["ref_shape"], B)
                        rec["grids"][-1]["map"] = str(p)
                sys.stdout.flush()

    p = outd / "classify" / f"{a.subject}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
