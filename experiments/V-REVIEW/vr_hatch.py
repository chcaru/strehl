r"""The ~35 px cross-hatch: is it in the MASTER only, or in every strehl render?

vr_pitch.py found the master's band field carries a directional comb at
pitch_x 33-37 px with |v| small (near-vertical stripes), and proved it is NOT a
float32 artefact of the gate's own boxblur (float32 minus float64 is 0.034% of
the band and is white).  So it is in the data.  This asks WHOSE data.

STATISTIC (on the raw window, where the hatch is 4.6x stronger than after the
gate's band-pass): f = win - boxblur(win, 200), Hann, |rfft2|^2.
  cluster  = bins within 6 of an axis with pitch in [22,50] px  (stripes)
  ring     = bins at the same radii but more than 20 deg off both axes
  HATCH    = mean(cluster) / mean(ring).   1.0 = no directional excess.
A subject with texture at that scale raises BOTH and cancels; only an
axis-aligned periodic structure raises the ratio.

POSITIVE CONTROL: --plant AMP,PITCH adds a square-wave grid of AMP*mean at that
pitch to the window; HATCH must rise with AMP.  Detection floor is printed.

ARMS: MASTER | SINGLE-FRAME strehl render (same pyramid, no election, no
outlier stage) in its OWN pixel grid | RAWPY linear (no strehl code at all).

  python vr_hatch.py SUBJECT [--frame=K] [--plant=0.002,35]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from orch_blotch import boxblur                               # noqa: E402

PLO, PHI = 22.0, 50.0


def hatch(win, tag, quiet=False):
    W = min(win.shape)
    f = win[:W, :W].astype(np.float32)
    f = f - boxblur(f, 200)
    h = np.hanning(W)[:, None] * np.hanning(W)[None, :]
    P = np.abs(np.fft.rfft2(f.astype(np.float64) * h)) ** 2
    v = np.fft.fftfreq(W) * W
    vv, uu = np.meshgrid(v, np.arange(P.shape[1]), indexing="ij")
    rad = np.hypot(vv, uu)
    lo, hi = W / PHI, W / PLO
    inr = (rad >= lo) & (rad <= hi)
    near = ((np.abs(vv) <= 6) | (np.abs(uu) <= 6)) & inr
    ang = np.degrees(np.arctan2(np.abs(vv), np.abs(uu)))
    ring = inr & (ang > 20) & (ang < 70)
    c, r = float(P[near].mean()), float(P[ring].mean())
    Pm = np.where(near, P, 0)
    i = int(np.argmax(Pm))
    iv, iu = np.unravel_index(i, P.shape)
    vs = iv if iv <= W // 2 else iv - W
    pk = W / max(abs(vs), abs(iu), 1e-9)
    if not quiet:
        print("  %-34s HATCH %6.3f   peak bin u=%d v=%d -> pitch %.2f px  "
              "(peak/ring %.1f)" % (tag, c / max(r, 1e-30), iu, vs, pk,
                                    float(P[iv, iu]) / max(r, 1e-30)))
    return c / max(r, 1e-30), pk


def plant(win, amp, pitch):
    m = float(np.mean(win))
    W = win.shape[0]
    x = np.arange(W)
    s = (np.sign(np.sin(2 * np.pi * x / pitch)) * (amp * m)).astype(np.float32)
    return win.astype(np.float32) + s[None, :] + s[:, None]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    subj = args[0]
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    wy, wx = S["master"]["blotch"]["y"], S["master"]["blotch"]["x"]
    W = V.BWIN
    mfull = V.lum_of(V.read_rgb(V.master_path(subj)))
    win = mfull[wy:wy + W, wx:wx + W]
    import vr_reg2 as R2
    km = R2.master_cover(subj)
    print("SUBJECT %s  window (%d,%d)  mean %.1f  master cover k=%.4f"
          % (subj, wy, wx, win.mean(), km))
    hatch(win, "MASTER")
    if "plant" in opts:
        a, p = opts["plant"].split(",")
        for aa in [float(x) for x in a.split("+")]:
            hatch(plant(win, aa, float(p)), "  MASTER + %.4f*mean (%.0f DN) grid p=%s"
                  % (aa, aa * win.mean(), p))
        return

    ok = [r for r in S["rows"] if r["state"] == "OK"]
    k = int(opts["frame"]) if "frame" in opts else sorted(ok, key=lambda r: -r["blotch"])[0]["frame"]
    tif = os.path.join(V.OUT, "%s--hatch-f%04d.tiff" % (subj, k))
    if not os.path.exists(tif):
        V.render_frame(subj, k, tif)
    src = V.lum_of(V.read_rgb(tif))
    A, d = R2.register_best(mfull, src, km / 1.0, wy, wx, W)
    pt = A @ np.array([wx + W / 2.0, wy + W / 2.0, 1.0])
    sx = max(0, min(src.shape[1] - W, int(round(pt[0] - W / 2))))
    sy = max(0, min(src.shape[0] - W, int(round(pt[1] - W / 2))))
    sc = float(np.hypot(A[0, 0], A[0, 1]))
    print("  frame %d: master->source scale %.4f, window at (%d,%d) in the source's"
          " own grid, ncc %.3f" % (k, sc, sy, sx, d["ncc_context"]))
    hp, pk_s = hatch(src[sy:sy + W, sx:sx + W], "SINGLE-FRAME f%d (own grid)" % k)
    print("      -> a hatch at %.2f px in the source grid maps to %.2f px in the master"
          % (pk_s, pk_s * sc))
    os.remove(tif)
    try:
        import rawpy
        with rawpy.imread(V.frames_of(subj)[k]) as rp:
            rgb = rp.postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16,
                                 use_camera_wb=True)
        rl = V.lum_of(rgb.astype(np.float32))
        fy = max(0, min(rl.shape[0] - W, int(sy * rl.shape[0] / src.shape[0])))
        fx = max(0, min(rl.shape[1] - W, int(sx * rl.shape[1] / src.shape[1])))
        hatch(rl[fy:fy + W, fx:fx + W], "RAWPY LINEAR f%d (no strehl)" % k)
    except Exception as e:
        print("  rawpy arm unavailable: %r" % (e,))


if __name__ == "__main__":
    main()
