"""Statistic F. Cache per-patch, per-frame BAND POWERS once; derive every arm.

Fixes measured to be necessary, each because an earlier build failed:
 * denominator selected by ABSOLUTE noise-corrected detail power, never by a
   ratio. A ratio HI/LO is maximised by defocus (LO collapses, read noise
   stays), and statistic E's envelope duly picked the most defocused frame at
   15.2% of sites -- the largest single share of any frame.
 * a CONTENT-MATCH GATE from physics: defocus is a low-pass and cannot change
   low-frequency content. If master/frame low-band power is outside [0.5, 2.0]
   the pair is not the same content and is NOT A MEASUREMENT.
 * a noise floor MEASURED per render, and sites refused where noise dominates.
"""
import os, sys, glob, argparse
import numpy as np
import tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, register, P, SEARCH

ROOT = r"C:\dev\strehl-out\V-GATHER\sharp"
CACHE = r"C:\dev\strehl-out\V-GATHER\bandcache"
BANDS = [(0.02,0.05),(0.05,0.12),(0.12,0.15),(0.15,0.20),(0.20,0.25),
         (0.25,0.30),(0.30,0.35),(0.35,0.42),(0.42,0.50)]
B_LO, B_HI, B_NZ = 1, [3,4,5], 8      # LO=0.05-0.12, HI=0.15-0.30, NZ=0.42-0.50
STRIDE, MARGIN, CORR_MIN = 320, 384, 0.60
CLIP_MAX, BLACK_MAX, STD_FLOOR = 0.02, 0.02, 250.0
_W = _RF = None


def bandpow(y):
    global _W, _RF
    n = y.shape[0]
    if _W is None or _W.shape[0] != n:
        w = np.hanning(n); _W = np.outer(w, w)
        fy = np.fft.fftfreq(n)[:, None]; fx = np.fft.fftfreq(n)[None, :]
        _RF = np.sqrt(fy*fy + fx*fx)
    pw = np.abs(np.fft.fft2((y - y.mean()) * _W)) ** 2
    return np.array([pw[(_RF >= a) & (_RF < b)].mean() for a, b in BANDS])


def build(subject):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, subject + ".npz")
    if os.path.exists(p):
        return dict(np.load(p, allow_pickle=True))
    d = os.path.join(ROOT, subject)
    mrgb = tifffile.imread(os.path.join(d, "MASTER.tiff"))[..., :3]
    my = luma(mrgb.astype(np.float32))
    h, w = my.shape
    sites = []
    for y in range(MARGIN, h - MARGIN - P, STRIDE):
        for x in range(MARGIN, w - MARGIN - P, STRIDE):
            b = my[y:y+P, x:x+P]
            if float((mrgb[y:y+P, x:x+P] >= 64000).mean()) > CLIP_MAX: continue
            if float((b <= 200).mean()) > BLACK_MAX: continue
            if float(b.std()) < STD_FLOOR: continue
            sites.append((y, x))
    del mrgb
    sites = np.array(sites)
    M = np.array([bandpow(my[y:y+P, x:x+P]) for y, x in sites])
    frames = sorted(glob.glob(os.path.join(d, "f[0-9]*.tiff")))
    nf, ns, nb = len(frames), len(sites), len(BANDS)
    A = np.full((nf, ns, nb), np.nan); C = np.zeros((nf, ns))
    for fi, fp in enumerate(frames):
        fy = luma(tifffile.imread(fp)[..., :3].astype(np.float32))
        for si, (y, x) in enumerate(sites):
            dy, dx, c = register(my[y:y+P, x:x+P],
                                 fy[y-SEARCH:y+P+SEARCH, x-SEARCH:x+P+SEARCH])
            C[fi, si] = c
            if c >= CORR_MIN:
                A[fi, si] = bandpow(fy[y+dy:y+dy+P, x+dx:x+dx+P])
        del fy
        print("   %s %d/%d" % (os.path.basename(fp), fi+1, nf), flush=True)
    np.savez_compressed(p, sites=sites, M=M, A=A, C=C,
                        frames=np.array([os.path.basename(f) for f in frames]))
    return dict(np.load(p, allow_pickle=True))


def noisefloor(Pb):
    """Per-image noise spectrum, MEASURED: the 10th percentile across patches in
    each band. At least a tenth of a real field is featureless at high f."""
    return np.nanpercentile(Pb, 10, axis=0)


def detail_power(Pb, nf_):
    """Noise-corrected detail power. Scale the measured noise spectrum by this
    patch's own 0.42-0.50 band, which carries no optical detail."""
    scale = np.clip(Pb[..., B_NZ] / max(nf_[B_NZ], 1e-30), 0.0, None)[..., None]
    corr = Pb - nf_[None, :] * scale if Pb.ndim == 2 else Pb - nf_ * scale
    return np.clip(corr[..., B_HI].sum(axis=-1), 0.0, None), \
           np.clip(corr[..., B_NZ] * 0 + Pb[..., B_HI].sum(axis=-1), 0.0, None)
