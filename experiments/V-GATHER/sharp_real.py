"""Measure a numerator against a per-patch max over the SAME-PIPELINE frame set.

Numerator and denominator are both renders from the same pinned binary with the
same flags, same pinned exposure and STREHL_COVER=0, so there is no tone,
exposure, demosaic or magnification difference between them.

Sites are a FULL-FIELD GRID WITH ABSOLUTE FLOORS. There is no top-N picker: a
search that cannot fail returns its least-bad candidate and calls it a find.
"""
import os, sys, glob, json, argparse
import numpy as np
import tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, acutance, orig_detail, register, blur, usm, P, SEARCH

ROOT = r"C:\dev\strehl-out\V-GATHER\sharp"
STRIDE = 256
MARGIN = 384          # COVER=0 leaves uncovered edges; stay well inside
CORR_MIN = 0.60
CLIP_MAX = 0.02       # saturated data has no gradient
BLACK_MAX = 0.02      # uncovered/black pixels are not a measurement
STD_FLOOR = 250.0     # ABSOLUTE structural floor, DN. Not a share of the best
                      # site -- a relative floor just measures how textured the
                      # subject is and always returns something.


def load_y(p):
    return luma(tifffile.imread(p)[..., :3].astype(np.float32))


def grid(my, mrgb):
    h, w = my.shape
    out = []
    for y in range(MARGIN, h - MARGIN - P, STRIDE):
        for x in range(MARGIN, w - MARGIN - P, STRIDE):
            b = my[y:y + P, x:x + P]
            clip = float((mrgb[y:y + P, x:x + P] >= 64000).mean())
            blk = float((b <= 200).mean())
            if clip > CLIP_MAX or blk > BLACK_MAX or float(b.std()) < STD_FLOOR:
                continue
            out.append((y, x))
    return out


def run(subject, numer="MASTER.tiff", plant=None, refblur=0.0, refkeep=1, quiet=False):
    d = os.path.join(ROOT, subject)
    npath = os.path.join(d, numer)
    mrgb = tifffile.imread(npath)[..., :3]
    my = luma(mrgb.astype(np.float32))
    sites = grid(my, mrgb)
    del mrgb
    frames = sorted(glob.glob(os.path.join(d, "f[0-9]*.tiff")))[::refkeep]
    if plant == "blur":
        my = blur(my, 0.8)
    elif plant == "usm":
        my = usm(my, 0.8, 1.0)
    M = np.array([acutance(my[y:y + P, x:x + P]) for y, x in sites])
    Mo = np.array([orig_detail(my[y:y + P, x:x + P]) for y, x in sites])
    A = np.full((len(frames), len(sites)), np.nan)
    Ao = np.full((len(frames), len(sites)), np.nan)
    C = np.zeros((len(frames), len(sites)))
    SH = np.zeros((len(frames), len(sites), 2), dtype=int)
    for fi, fp in enumerate(frames):
        fy = load_y(fp)
        if refblur > 0:
            fy = blur(fy, refblur)
        for si, (y, x) in enumerate(sites):
            ref = my[y:y + P, x:x + P]
            win = fy[y - SEARCH:y + P + SEARCH, x - SEARCH:x + P + SEARCH]
            dy, dx, c = register(ref, win)
            C[fi, si] = c
            SH[fi, si] = (dy, dx)
            if c < CORR_MIN:
                continue
            crop = fy[y + dy:y + dy + P, x + dx:x + dx + P]
            A[fi, si] = acutance(crop)
            Ao[fi, si] = orig_detail(crop)
        del fy
        if not quiet:
            print("   %-14s corr med %.3f  registered %d/%d"
                  % (os.path.basename(fp), float(np.median(C[fi])),
                     int((C[fi] >= CORR_MIN).sum()), len(sites)), flush=True)
    return dict(sites=sites, M=M, Mo=Mo, A=A, Ao=Ao, C=C, SH=SH,
                frames=[os.path.basename(f) for f in frames])


def ratios(r):
    ok = np.isfinite(r["A"]).sum(axis=0) >= 3
    den = np.nanmax(r["A"], axis=0)
    deno = np.nanmax(r["Ao"], axis=0)
    e = r["M"][ok] / den[ok]
    o = r["Mo"][ok] / deno[ok]
    return e, o, int(ok.sum()), len(r["sites"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--numer", default="MASTER.tiff")
    ap.add_argument("--plant", default=None)
    ap.add_argument("--refblur", type=float, default=0.0)
    ap.add_argument("--refkeep", type=int, default=1)
    a = ap.parse_args()
    r = run(a.subject, a.numer, a.plant, a.refblur, a.refkeep)
    e, o, n, tot = ratios(r)
    print("\n%s  numer=%s plant=%s refblur=%.2f refkeep=%d"
          % (a.subject, a.numer, a.plant, a.refblur, a.refkeep))
    print("  patches %d measured of %d gridded" % (n, tot))
    print("  E    median %.4f   p10 %.4f   p90 %.4f" % (np.median(e), np.percentile(e,10), np.percentile(e,90)))
    print("  orig median %.4f   p10 %.4f   p90 %.4f" % (np.median(o), np.percentile(o,10), np.percentile(o,90)))
