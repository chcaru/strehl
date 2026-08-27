r"""Measure every master and a sample of its source frames on ONE sound gauge.

WHAT IS DIFFERENT FROM THE GATE THIS REPLACES, and it is exactly two things:

  THE GAUGE. Every published master/source ratio in this project was taken on
  --srgb. Verified at the source (image_out.rs:165-172) and by experiment
  (gaugecheck.py): --srgb fits its black and white points from EACH IMAGE'S OWN
  luminance percentiles. A 299-frame master and a single source frame therefore
  sit on two different content-derived nonlinear curves, and neither blotch
  (band/mean) nor chroma ((R-Y)/Y) survives that -- both are invariant to a
  LINEAR gain, and a fitted tone curve is not one. The documented defence was to
  pin --exposure; measured, a commanded 64x moves 0 of 98,898,048 samples and
  delivers a gain of 1.0000000, so the defence reaches no pixel. This renders
  both sides on --linear-srgb, which carries no tone stage at all.

  THE BASELINE. The frozen rule is "max over registered source frames", and for
  blotch and chroma LOW IS GOOD, so the max is the WORST frame. Nine subjects
  were acquitted for being no worse than the worst frame available. Both are
  computed here and BOTH LABELS ARE DERIVED FROM THE RULE, never typed.

--linear-srgb DOES NOT IMPLY --demosaic while --srgb does, so a linear render
taken without it is half-resolution and every spatial statistic changes meaning.
--demosaic is passed explicitly AND THE LATTICE IS READ BACK FROM THE FILE.

THE WINDOW IS PINNED ON THE MASTER AND REUSED. flattest() chooses where to
measure from the image it is given; letting a source frame choose its own window
compares two different pieces of the subject and calls the difference a merge
defect.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np
import tifffile

ORCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ORCH-drift-check")
sys.path.insert(0, os.path.abspath(ORCH))
from orch_blotch import blotch_ratio, flattest, lum_of        # noqa: E402
from orch_chroma import banding, chroma_blotch, pick_window   # noqa: E402

EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
SEAL_DIR = r"C:\dev\strehl-out\acceptance\SHIP-V4"
RAW = r"D:\personal\macro"
WORK = r"C:\dev\strehl-out\V-GATHER\cert"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cert.json")
K_SAMPLE = 12


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def check_binary():
    """Identify the build by hash against the corpus seal. Four builds share its size."""
    got = sha256(EXE)
    seals = {open(os.path.join(SEAL_DIR, f), encoding="utf-8").read().strip().upper()
             for f in os.listdir(SEAL_DIR) if f.endswith(".tiff.ok")}
    if len(seals) != 1:
        raise SystemExit("SHIP-V4 seals disagree (%d distinct) -- refusing" % len(seals))
    want = seals.pop()
    if got != want:
        raise SystemExit("BINARY REFUSED\n  have %s\n  seal %s" % (got, want))
    print("binary %s..  matches all %d SHIP-V4 seals" % (got[:16], 26))
    return got


def render(subject, out_path, only_frame=None):
    env = dict(os.environ)
    env["STREHL_CACHE_DIR"] = os.path.join(WORK, subject, "cache")
    os.makedirs(env["STREHL_CACHE_DIR"], exist_ok=True)
    for v in ("STREHL_FIX_CA", "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU",
              "STREHL_EDGE_CONF", "STREHL_ONLY_FRAME"):
        env.pop(v, None)
    if only_frame is not None:
        env["STREHL_ONLY_FRAME"] = str(only_frame)
    cmd = [EXE, "stack", os.path.join(RAW, subject), "--out", out_path,
           "--linear-srgb", "--demosaic"]
    t = time.time()
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if p.returncode != 0 or not os.path.exists(out_path):
        return None, p.stderr[-400:], time.time() - t
    return out_path, "", time.time() - t


def read_rgb(path, expect=None):
    """Read, and VERIFY THE LATTICE FROM THE FILE rather than trusting the flags."""
    with tifffile.TiffFile(path) as t:
        pg = t.pages[0]
        w, h = pg.tags["ImageWidth"].value, pg.tags["ImageLength"].value
        desc = str(pg.tags["ImageDescription"].value) if "ImageDescription" in pg.tags else ""
    if "Tone rendering" in desc:
        raise SystemExit("REFUSED: %s carries a fitted tone stage; not a linear gauge" % path)
    if expect is not None and (w, h) != expect:
        raise SystemExit("REFUSED: lattice %dx%d != master %dx%d" % (w, h, expect[0], expect[1]))
    a = tifffile.imread(path)
    return a[:, :, :3].astype(np.float32), (w, h)


def est_shift(a, b):
    """Integer-only shift by FFT cross-correlation. Sign is COMMISSIONED, not derived.

    Sub-pixel resampling is deliberately not used: it would add blur to the very
    band energy being measured. Returns (dy, dx, confidence), where confidence is
    the peak height in units of the correlation surface's own standard deviation
    -- a flat window has no localisable peak and must be refused rather than
    silently assigned (0, 0).
    """
    a = a - a.mean()
    b = b - b.mean()
    c = np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(b)), s=a.shape)
    pk = np.unravel_index(int(np.argmax(c)), c.shape)
    h, w = a.shape
    dy = pk[0] if pk[0] <= h // 2 else pk[0] - h
    dx = pk[1] if pk[1] <= w // 2 else pk[1] - w
    conf = float((c.max() - c.mean()) / (c.std() + 1e-12))
    return int(dy), int(dx), conf


def window_shift(m_lum, s_lum, at, half=768, win=900):
    """Where has the master's window moved to in this source frame?

    MEASURED, BECAUSE IT IS NOT ZERO. STREHL_ONLY_FRAME emits a frame in its own
    geometry, not warped into the reference grid: regcheck.py measures a drift of
    about 0.9px per frame, so on a 299-frame bracket the last frame's content has
    walked ~270px across a 900px window. Comparing the same COORDINATES in master
    and source therefore compares different scene content, and the contamination
    grows with stack depth -- which is exactly the artifact that made the ratio
    correlate with frame count at rho = 0.764 before this was applied.

    The estimate is LOCAL to the window because the per-frame transform is a
    similarity: focus breathing changes magnification, so the displacement is
    position-dependent and a single global translation would be wrong away from
    wherever it was measured.

    SIGN IS NEGATED HERE, AND IT WAS WRONG UNTIL signcheck.py MEASURED IT.
    est_shift's own control (below, "SHIFT ESTIMATOR FAILED CONTROL") fixes its
    convention as est_shift(a, roll(a, k)) == -k, i.e. it returns the negative of
    the displacement. Every call site consumes the result as `y + dy` to locate
    the master's window inside the source, so the raw return value moved the
    window AWAY from the matching content by twice the drift.

    A convention is not a usage, and the sign could not be settled by reading it.
    signcheck.py plants a displacement of (23, -17) and asks which candidate
    window actually matches: `y - dy` won on 8 of 8 sites, with a residual of
    exactly 0.0 DN at the two sites where the estimate was exact, against 339 and
    1648 DN for `y + dy`. The negation is applied here, once, so that the
    docstring above -- "where has the master's window moved to" -- is true of the
    returned value and every call site is correct as written.

    THIS INVALIDATES THE REGISTERED ARM OF THE PREVIOUS RUN, preserved beside
    this file as cert-wrongsign.json. It also supplies the missing explanation
    for a result reported earlier: adding registration made the ratio-vs-depth
    correlation RISE from rho +0.764 to +0.867, which was attributed to
    depth-dependent refusals. A registration applied backwards doubles the
    misregistration it was introduced to remove, and drift grows with stack
    depth, so it would produce exactly that.
    """
    y, x = at
    cy, cx = y + win // 2, x + win // 2
    h, wd = m_lum.shape
    y0, x0 = max(0, cy - half), max(0, cx - half)
    y1, x1 = min(h, cy + half), min(wd, cx + half)
    dy, dx, conf = est_shift(m_lum[y0:y1, x0:x1], s_lum[y0:y1, x0:x1])
    return -dy, -dx, conf


def sharpness(lum):
    """Mean |gradient|. A defocus proxy, decimated for speed."""
    d = lum[::4, ::4]
    return float(np.abs(np.diff(d, axis=0)[:, :-1]).mean()
                 + np.abs(np.diff(d, axis=1)[:-1, :]).mean())


def measure(rgb, at_blotch=None, at_chroma=None):
    """Statistics, plus TWO focus proxies that exist to commission the denominator.

    `best source frame` is an ARGMIN over frames of a low-is-good statistic, and
    this project has already caught a ratio used as an argmax over a focus stack
    SELECTING DEFOCUS. Blur lowers mid-scale band energy, so the frame with the
    least blotch may simply be the frame that is least in focus here -- in which
    case the denominator is defocus and the ratio means nothing.

    focus_win is the one that matters: the window is chosen as the FLATTEST
    region of the master, and if a source frame is defocused THERE it will read
    artificially clean and win the argmin for the wrong reason.
    """
    lum = lum_of(rgb)
    y, x = at_blotch if at_blotch else flattest(lum)
    win = lum[y:y + 900, x:x + 900]
    br = blotch_ratio(win)
    at_c = at_chroma if at_chroma else pick_window(rgb, "chroma")
    ch = chroma_blotch(rgb, at=at_c) if at_c else None
    return {"blotch": float(br[0]), "band_dn": float(br[1]),
            "noise_dn": float(br[2]), "mean_dn": float(br[3]),
            "chroma": float(ch[0]) if ch else None,
            "focus_global": sharpness(lum), "focus_win": sharpness(win),
            "at_blotch": [int(y), int(x)],
            "at_chroma": [int(at_c[0]), int(at_c[1])] if at_c else None}


# Ordered by what can still CHANGE A VERDICT. The 17 subjects not listed read
# 0.00036-0.01090 blotch and 0.00010-0.00992 chroma on the delivered file -- one
# to two orders below any visibility threshold -- so no source-frame ratio can
# move them off clean, and spending the deepest stacks on them buys nothing.
# 109MSDCF is here as a PASS CONTROL: a subject that reads clean absolutely must
# also read clean in ratio, or the ratio is manufacturing defects.
PRIORITY = ["109MSDCF", "coffee-bubbles", "flat-on-ruler-cpl", "112MSDCF",
            "lead-1-cpl", "113MSDCF", "leaf-2-cpl", "foam",
            "couch-fibers-cpl", "flower-inner-edge-cpl"]


def subjects():
    out = []
    for f in sorted(os.listdir(SEAL_DIR)):
        if f.endswith("--SHIP-V4.tiff"):
            out.append(f[:-len("--SHIP-V4.tiff")])
    rank = {s: i for i, s in enumerate(PRIORITY)}
    return sorted(out, key=lambda s: (rank.get(s, 10 ** 6), s))


def main():
    check_binary()
    os.makedirs(WORK, exist_ok=True)
    doc = {}
    if os.path.exists(OUT):
        doc = json.load(open(OUT, encoding="utf-8"))
    subs = subjects()
    print("%d subjects\n" % len(subs))
    for si, s in enumerate(subs, 1):
        if s in doc and doc[s].get("done"):
            print("[%2d/%d] %-38s cached" % (si, len(subs), s))
            continue
        d = os.path.join(WORK, s)
        os.makedirs(d, exist_ok=True)
        rec = {"subject": s}
        mp = os.path.join(d, "master.tiff")
        got, err, dt = render(s, mp)
        if not got:
            rec["refused"] = "master render failed: %s" % err.strip()[:200]
            doc[s] = rec
            json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1)
            print("[%2d/%d] %-38s REFUSED %s" % (si, len(subs), s, rec["refused"][:60]))
            continue
        rgb, lat = read_rgb(mp)
        rec["lattice"] = list(lat)
        m = measure(rgb)
        rec["master"] = m
        m_lum = lum_of(rgb)
        del rgb
        os.remove(mp)

        # PER-RUN POSITIVE CONTROL on the shift estimator. A registration that
        # cannot recover a shift it was just given would return (0,0) for every
        # frame and present as "already registered" -- the failure mode this
        # whole correction exists to remove. Refuse the subject rather than
        # measure it with an instrument that has not answered.
        yb, xb = m["at_blotch"]
        ctl = m_lum[max(0, yb - 300):yb + 1200, max(0, xb - 300):xb + 1200]
        for wnt in ((9, -13), (-6, 4)):
            gy, gx, gc = est_shift(ctl, np.roll(np.roll(ctl, wnt[0], 0), wnt[1], 1))
            if (gy, gx) != (-wnt[0], -wnt[1]):
                raise SystemExit("SHIFT ESTIMATOR FAILED CONTROL on %s: planted %s got %s"
                                 % (s, wnt, (gy, gx)))
        rec["shift_control"] = "recovered (9,-13) and (-6,4)"

        # COUNT FRAMES, NOT FILES. The first version counted directory entries.
        # Three subjects carry an .xmp sidecar per raw, so the count came out at
        # EXACTLY 2x the bracket: 113MSDCF read 126 for 63 real frames. Sampling
        # linspace(0, 125, 12) would have had six of twelve indices refused as
        # out of range and drawn every survivor from the first half of the stack
        # -- a halved, one-sided sample presenting as a full one.
        #
        # It surfaced only because an out-of-range STREHL_ONLY_FRAME panics
        # rather than clamping. A silent clamp would have mapped all six onto
        # the last frame and the run would have looked complete.
        n = len([f for f in os.listdir(os.path.join(RAW, s))
                 if f.lower().endswith(".arw")])
        if n == 0:
            rec["refused"] = "no .arw frames in source directory"
            doc[s] = rec
            json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1)
            print("[%2d/%d] %-38s REFUSED no frames" % (si, len(subs), s))
            continue
        idx = list(range(n)) if n <= 24 else \
            sorted(set(np.linspace(0, n - 1, K_SAMPLE).astype(int).tolist()))
        rec["n_frames"] = n
        rec["sampled"] = idx
        rec["exhaustive"] = n <= 24
        srcs = []
        for k in idx:
            sp = os.path.join(d, "src.tiff")
            g, e, _ = render(s, sp, only_frame=k)
            if not g:
                srcs.append({"k": k, "refused": e.strip()[:120]})
                continue
            try:
                srgb, slat = read_rgb(sp, expect=lat)
            except SystemExit as ex:
                srcs.append({"k": k, "refused": str(ex)[:160]})
                os.remove(sp)
                continue
            s_lum = lum_of(srgb)
            dyb, dxb, cb = window_shift(m_lum, s_lum, m["at_blotch"])
            ab = (m["at_blotch"][0] + dyb, m["at_blotch"][1] + dxb)
            ac = m["at_chroma"]
            dyc = dxc = 0
            cc = float("nan")
            if ac:
                dyc, dxc, cc = window_shift(m_lum, s_lum, ac)
                ac = (ac[0] + dyc, ac[1] + dxc)
            del s_lum
            hgt, wid = m_lum.shape
            if not (0 <= ab[0] <= hgt - 900 and 0 <= ab[1] <= wid - 900):
                srcs.append({"k": k, "refused": "registered window falls outside the frame"})
                del srgb
                os.remove(sp)
                continue
            # The chroma window needs the SAME bounds check the blotch window
            # gets four lines up. Without it an off-frame window slices to an
            # empty array and chroma returns NaN -- and NaN is False against
            # every `>` comparison, so a MISSING measurement reads as a CLEAN
            # one. One such value reached cert.json (bee-2-cpl frame 11).
            #
            # Passing at_chroma=None is NOT the repair: measure() falls back to
            # pick_window() and would silently measure a DIFFERENT region of the
            # source than the master window it is compared against. So the
            # window is nulled AFTER measurement, and the frame carries an
            # explicit refusal rather than a number nobody can trace.
            chroma_bad = None
            if ac is not None and not (0 <= ac[0] <= hgt - 900
                                       and 0 <= ac[1] <= wid - 900):
                chroma_bad = "registered chroma window falls outside the frame"
                ac = None
            sm = measure(srgb, at_blotch=ab, at_chroma=ac)
            if chroma_bad:
                sm["chroma"] = None
                sm["at_chroma"] = None
                sm["chroma_refused"] = chroma_bad
            for _k, _v in sm.items():
                if isinstance(_v, float) and _v != _v:
                    raise SystemExit(
                        "NON-FINITE MEASUREMENT %s on %s frame %d -- refusing to "
                        "write a value that would compare False against every "
                        "threshold" % (_k, s, k))
            sm["k"] = k
            sm["shift_blotch"] = [dyb, dxb, round(cb, 2)]
            sm["shift_chroma"] = [dyc, dxc, None if cc != cc else round(cc, 2)]
            srcs.append(sm)
            del srgb
            os.remove(sp)
        rec["sources"] = srcs
        rec["done"] = True
        doc[s] = rec
        json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1)
        ok = [x for x in srcs if "blotch" in x]
        print("[%2d/%d] %-38s %5d frames, %2d sampled, %2d measured  master blotch %.5f  %.0fs"
              % (si, len(subs), s, n, len(idx), len(ok), m["blotch"], dt))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
