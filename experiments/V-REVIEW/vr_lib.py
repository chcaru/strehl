r"""V-REVIEW adjudication library.

READ-ONLY on the repo. Writes only under experiments\V-REVIEW (scripts) and
C:\dev\strehl-out\V-REVIEW (scratch renders).

The statistics are IMPORTED from the gate's own modules, not re-typed:
orch_blotch.blotch_ratio/flattest/lum_of and orch_chroma.chroma_blotch/
pick_window. A re-typed definition measures a different thing.

THE SOURCE ARM USED HERE IS NOT A rawpy DECODE.
`orch_blotch.py`'s source arm decodes the ARW with rawpy gamma=(1,1),
no_auto_bright -- LINEAR light -- and compares it against a master that has the
sRGB transfer curve applied (provenance: "colour space: sRGB, TONE CURVE
APPLIED -- DO NOT MEASURE NUMERICALLY").  band/mean contrast is invariant to a
LINEAR gain, which is what section 99 corrected for; it is NOT invariant to a
transfer curve. So the source arm here renders each source frame THROUGH THE
SAME PINNED BINARY, with the same flags and the SAME exposure stops as the
master, using STREHL_ONLY_FRAME=k (merge_cmd.rs:1734: restricts the bracket to
one frame, no election). Demosaic, CA, alignment resample, colour matrix,
exposure gain and the sRGB curve are then COMMON MODE, and the only difference
between the arms is the merge itself.

Geometry is measured, not assumed: the master is rendered with a fit-to-cover
crop (0.84-0.99 depending on subject) about the bracket's reference frame,
while a one-frame render is cropped about itself, so the two do not share pixel
coordinates. Every source window is located by registering the render to the
master and warping the master's own window out of it.
"""
import glob
import hashlib
import os
import subprocess
import sys

import cv2
import numpy as np
import tifffile

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)

from orch_blotch import blotch_ratio, flattest, lum_of   # noqa: E402
from orch_blotch import WIN as BWIN                      # noqa: E402
from orch_chroma import chroma_blotch, pick_window       # noqa: E402
from orch_chroma import WIN as CWIN                      # noqa: E402

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V3"
ARM = "SHIP-V3"
OUT = r"C:\dev\strehl-out\V-REVIEW"
SRC = r"D:\personal\macro"
PINS = r"C:\dev\strehl-out\acceptance-pins"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def corpus_seal(ship=None, arm=None):
    """The SHA256 every master in this corpus records as its renderer.

    Hard-fails if the corpus is unsealed or the seals disagree. Never
    returns a value that has not been read off the masters themselves.
    """
    ship = SHIP if ship is None else ship
    arm = ARM if arm is None else arm
    oks = sorted(glob.glob(os.path.join(ship, "*--%s.tiff.ok" % arm)))
    if not oks:
        raise RuntimeError("PIN GUARD: no .ok seals in %s" % ship)
    seals = set()
    for q in oks:
        with open(q) as f:
            seals.add(f.read().strip().upper())
    if len(seals) != 1:
        raise RuntimeError(
            "PIN GUARD: corpus %s is not internally sealed; %d distinct "
            "renderer hashes across %d masters: %s"
            % (ship, len(seals), len(oks), sorted(seals)))
    return seals.pop(), len(oks)


def pin_for(seal):
    """Select the pin whose binary hashes to the corpus seal.

    Derivation, not declaration: re-pointing SHIP/ARM at another corpus
    automatically selects that corpus's renderer. A cross-gauge render is
    therefore not merely discouraged, it is unreachable.
    """
    found = {}
    for name in sorted(os.listdir(PINS)):
        cand = os.path.join(PINS, name, "target", "release", "strehl.exe")
        if os.path.isfile(cand):
            found[name] = _sha256(cand)
    for name, h in found.items():
        if h == seal:
            return os.path.join(PINS, name, "target", "release",
                                "strehl.exe"), name
    raise RuntimeError(
        "PIN GUARD: no pin matches the corpus seal.\n"
        "  corpus seal : %s\n"
        "  pins present: %s"
        % (seal, ", ".join("%s=%s" % kv for kv in sorted(found.items()))))


CORPUS_SEAL, N_SEALED = corpus_seal()
EXE, EXE_PIN = pin_for(CORPUS_SEAL)

# Stops read verbatim from each master's own render log ("reproduce this exact
# file with --exposure=..."). Forcing them is what keeps the transfer curve
# common-mode; --auto-exposure would pick a different gain per frame.
EXPOSURE = {
    # PASS-subject control (gate: blotch 0.00169, chroma 0.0005). Exposure read
    # verbatim from its own master log, same as every other row.
    '109MSDCF': '+2.60',
    "112MSDCF": "+3.33",
    "113MSDCF": "+2.33",
    "coffee-bubbles": "-0.26",
    "couch-fibers-cpl": "+1.82",
    "flat-on-ruler-cpl": "+1.95",
    "flower-inner-edge-cpl": "+0.50",
    "foam": "-0.34",
    "lead-1-cpl": "+3.76",
    "leaf-2-cpl": "+3.19",
}
SUBJECTS = list(EXPOSURE)


def master_path(subj):
    return os.path.join(SHIP, "%s--%s.tiff" % (subj, ARM))


def read_rgb(path):
    """As the gate reads it: tifffile (never PIL), 3 channels, float32."""
    a = tifffile.imread(path)
    return a[:, :, :3].astype(np.float32)


def gate_blotch(rgb):
    """Exactly orch_printready.verdict's blotch term."""
    lum = lum_of(rgb)
    y, x = flattest(lum)
    r, bd, nd, md = blotch_ratio(lum[y:y + BWIN, x:x + BWIN])
    return dict(contrast=r, band=bd, noise=nd, mean=md, y=y, x=x)


def gate_chroma(rgb, at=None):
    """Exactly orch_printready.verdict's chroma term (at=None picks the window)."""
    cb = chroma_blotch(rgb, at)
    if cb is None:
        return None
    return dict(chroma=cb[0], a_rms=cb[1], b_rms=cb[2], chr_std=cb[3],
                y=cb[4][0], x=cb[4][1])


def frames_of(subj):
    d = os.path.join(SRC, subj)
    return sorted(os.path.join(d, f) for f in os.listdir(d)
                  if f.lower().endswith(".arw"))


def seal_render(out_tiff, cmd=None, env=None):
    """Write the same seal the acceptance harness writes on a master.

    A render without a seal cannot be audited the way a shipped master
    can. The seal is the whole reason a cross-gauge comparison is
    detectable after the fact rather than merely suspected.
    """
    h = _sha256(EXE)
    with open(out_tiff + ".ok", "w") as f:
        f.write(h)
    with open(out_tiff + ".provenance.txt", "w") as f:
        f.write("binary   %s\n" % EXE)
        f.write("pin      %s\n" % EXE_PIN)
        f.write("sha256   %s\n" % h)
        f.write("corpus   %s (seal %s)\n" % (ARM, CORPUS_SEAL))
        if cmd is not None:
            f.write("command  %s\n" % " ".join(cmd))
        for k in ("STREHL_FIX_CA", "STREHL_EDGE_AWARE",
                  "STREHL_EDGE_TAU", "STREHL_EDGE_CONF",
                  "STREHL_ONLY_FRAME"):
            v = "<cleared>" if env is None else env.get(k, "<cleared>")
            f.write("%-18s %s\n" % (k, v))
    return out_tiff + ".ok"


def render_frame(subj, k, out_tiff, timeout=900):
    """One frame of the bracket through the pinned binary, master's exposure."""
    env = {kk: v for kk, v in os.environ.items() if not kk.startswith("STREHL_")}
    env["STREHL_ONLY_FRAME"] = str(k)
    cmd = [EXE, "stack", os.path.join(SRC, subj), "--out", out_tiff, "--srgb",
           "--exposure=%s" % EXPOSURE[subj]]
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout)
    log = p.stderr.decode("utf-8", "replace")
    if p.returncode != 0:
        raise RuntimeError("render failed rc=%d\n%s" % (p.returncode, log[-2000:]))
    seal_render(out_tiff, cmd, env)
    return log


def _n8(a):
    lo, hi = np.percentile(a, [1.0, 99.0])
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1).__mul__(255).astype(np.uint8)


def register(mlum, slum, ds=8):
    """Similarity master->source, ORB+RANSAC then ECC refine. Measured, not assumed.

    Returns (A 2x3 mapping FULL-RES master (x,y) -> source (x,y), diag dict).
    """
    m = cv2.resize(mlum, None, fx=1.0 / ds, fy=1.0 / ds, interpolation=cv2.INTER_AREA)
    s = cv2.resize(slum, None, fx=1.0 / ds, fy=1.0 / ds, interpolation=cv2.INTER_AREA)
    m8, s8 = _n8(m), _n8(s)
    orb = cv2.ORB_create(nfeatures=8000)
    k1, d1 = orb.detectAndCompute(m8, None)
    k2, d2 = orb.detectAndCompute(s8, None)
    diag = dict(kp_master=len(k1), kp_source=len(k2), inliers=0, ecc=float("nan"))
    if d1 is None or d2 is None or len(k1) < 20 or len(k2) < 20:
        return None, diag
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    good = []
    for pair in bf.knnMatch(d1, d2, k=2):
        if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance:
            good.append(pair[0])
    diag["matches"] = len(good)
    if len(good) < 20:
        return None, diag
    p1 = np.float32([k1[g.queryIdx].pt for g in good])
    p2 = np.float32([k2[g.trainIdx].pt for g in good])
    M, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC,
                                         ransacReprojThreshold=2.0,
                                         maxIters=5000, confidence=0.999)
    if M is None:
        return None, diag
    diag["inliers"] = int(inl.sum())
    res = p2 - (p1 @ M[:, :2].T + M[:, 2])
    sel = inl.ravel().astype(bool)
    diag["rms_px_ds"] = float(np.sqrt(np.mean(np.sum(res[sel] ** 2, axis=1))))
    W = M.astype(np.float32)
    try:
        cc, W = cv2.findTransformECC(
            cv2.GaussianBlur(m8, (0, 0), 1.5), cv2.GaussianBlur(s8, (0, 0), 1.5),
            W, cv2.MOTION_AFFINE,
            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-7), None, 5)
        diag["ecc"] = float(cc)
    except cv2.error as exc:                                   # noqa: BLE001
        diag["ecc_error"] = str(exc)[:120]
        W = M.astype(np.float32)
    A = np.array(W, dtype=np.float64)
    A[:, 2] *= ds                       # downsampled translation -> full res
    diag["scale"] = float(np.sqrt(abs(A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0])))
    return A, diag


def warp_window(src_rgb, A, y, x, win):
    """Pull the master's (y,x,win) window OUT of the source render, in the
    master's geometry. Returns None if the window falls outside the source."""
    T = np.array([[1.0, 0.0, x], [0.0, 1.0, y], [0.0, 0.0, 1.0]])
    A3 = np.vstack([A, [0.0, 0.0, 1.0]])
    M = (A3 @ T)[:2, :]
    h, w = src_rgb.shape[:2]
    cor = np.array([[0, 0, 1], [win - 1, 0, 1], [0, win - 1, 1], [win - 1, win - 1, 1]],
                   dtype=np.float64)
    p = cor @ M.T
    if p[:, 0].min() < 1 or p[:, 1].min() < 1 or p[:, 0].max() > w - 2 or p[:, 1].max() > h - 2:
        return None
    return cv2.warpAffine(src_rgb, M.astype(np.float32), (win, win),
                          flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)


def context_ncc(mlum, slum, A, y, x, win, pad=800, blur=6.0):
    """Did the two windows land on the same scene? Correlate a padded box.

    The window itself is chosen for FLATNESS, so it may carry no signal to
    correlate; the surrounding box does. Both sides are blurred so that the
    master being sharper than a defocused frame cannot by itself lower it.
    """
    y0, x0 = y - pad, x - pad
    n = win + 2 * pad
    if y0 < 0 or x0 < 0 or y0 + n > mlum.shape[0] or x0 + n > mlum.shape[1]:
        pad = min(pad, y, x, mlum.shape[0] - y - win, mlum.shape[1] - x - win)
        y0, x0, n = y - pad, x - pad, win + 2 * pad
    a = mlum[y0:y0 + n, x0:x0 + n]
    b = warp_window(slum[..., None], A, y0, x0, n)
    if b is None:
        return float("nan")
    b = b if b.ndim == 2 else b[..., 0]   # cv2 DROPS a singleton channel
    a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), blur)
    b = cv2.GaussianBlur(b.astype(np.float32), (0, 0), blur)
    a = a - a.mean()
    b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else float("nan")
