r"""Is the master's mid-scale structure the SUBJECT's, or did the merge make it?

A ratio slightly above 1 has two mechanisms and the ratio cannot separate them:

  INNOCENT  the master is all-in-focus. Inside one 900x900 window different
            parts are in focus in different frames, so the composite legitimately
            carries more 50-400 px contrast than ANY single frame does.
  GUILTY    the merge stitched a patchwork whose seams are mid-scale mottling.

They look completely different, and this measures the difference three ways:

  1. CORRELATION of the master's band field with the best-focused source frame's.
     Subject structure correlates; manufactured mottling does not.
  2. WHERE THE RESIDUAL LIVES. Under the innocent mechanism the master-minus-
     source residual must sit where that frame is DEFOCUSED (that is the only
     place the composite can differ). Under blotching it sits in the smoothest
     places, uncorrelated with the frame's local sharpness. Reported as the
     correlation between |residual| and local defocus.
  3. THE PICTURE, at one stated gain, because five instruments in this project
     were wrong and every one was caught by looking.

POSITIVE CONTROL: --plant SIGMA plants a blotch field into the master before
measuring. An instrument that reads the same on a planted master as on a clean
one cannot convict, and its acquittals are worthless.

  python vr_novel.py SUBJECT [nframes] [--plant=2.0] [--chroma]
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
import vr_reg2 as R                                           # noqa: E402
from orch_blotch import boxblur, LO_R, HI_R, NOISE_R          # noqa: E402
from orch_chroma import boxblur as cboxblur                   # noqa: E402
from orch_chroma import relative_chroma, LO_R as C_LO, HI_R as C_HI  # noqa: E402


def band_rel(blk):
    """The gate's own band-pass, divided by the window mean -- the same
    tone-invariant quantity blotch_ratio reports the sd of."""
    b = boxblur(blk, LO_R // 2) - boxblur(blk, HI_R // 2)
    return b / max(float(np.mean(blk)), 1e-9)


def local_sharp(blk, r=NOISE_R, smooth=60):
    hf = blk - boxblur(blk, r)
    return boxblur(np.abs(hf), smooth) / max(float(np.mean(blk)), 1e-9)


def chroma_bands(rgb):
    a, b, _ = relative_chroma(rgb)
    return (cboxblur(a, C_LO) - cboxblur(a, C_HI),
            cboxblur(b, C_LO) - cboxblur(b, C_HI))


def corr(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else float("nan")


def blot_field(shape, rng, cell=64):
    h, w = shape
    c = rng.normal(0, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
    f = cv2.resize(c, (w, h), interpolation=cv2.INTER_LINEAR)
    return (f - f.mean()) / max(float(np.std(f)), 1e-6)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    subj = args[0]
    nk = int(args[1]) if len(args) > 1 else 3
    plant = float(opts.get("plant", 0.0))
    do_chroma = "chroma" in opts
    key = "chroma" if do_chroma else "blotch"
    WIN = V.CWIN if do_chroma else V.BWIN

    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    ms = S["master"]
    wy, wx = (ms["chroma"]["y"], ms["chroma"]["x"]) if do_chroma else \
             (ms["blotch"]["y"], ms["blotch"]["x"])
    ok = [r for r in S["rows"] if r["state"] == "OK"]
    top = sorted(ok, key=lambda r: -r[key])[:nk]
    print("SUBJECT %s   statistic %s   window (%d,%d)   frames %s"
          % (subj, key, wy, wx, [r["frame"] for r in top]))

    mrgb = V.read_rgb(V.master_path(subj))
    mlum = V.lum_of(mrgb)
    mw = mrgb[wy:wy + WIN, wx:wx + WIN].astype(np.float32).copy()
    if "asmaster" in opts:
        # CONTROL: put a SOURCE frame in the master's chair.  Every number below
        # is then frame-vs-frame.  If a source frame is as "novel" against its
        # neighbours as the master is, the master's novelty convicts nobody.
        ka = int(opts["asmaster"])
        top = [r for r in top if r["frame"] != ka]
        ta = os.path.join(V.OUT, "%s--am%04d.tiff" % (subj, ka))
        if not os.path.exists(ta):
            V.render_frame(subj, ka, ta)
        argb = V.read_rgb(ta)
        Aa, da = R.register_best(mlum, V.lum_of(argb), R.master_cover(subj) / 1.0,
                                 wy, wx, WIN)
        mw = V.warp_window(argb, Aa, wy, wx, WIN).astype(np.float32)
        del argb
        os.remove(ta)
        print("CONTROL: frame %d warped into the master's window (ncc %.3f) is the "
              "reference" % (ka, da["ncc_context"]))
    if "asmaster" in opts:
        # CONTROL: put a SOURCE frame in the master's chair.  Every number below
        # is then frame-vs-frame.  If a source frame is as "novel" against its
        # neighbours as the master is, the master's novelty convicts nobody.
        ka = int(opts["asmaster"])
        top = [r for r in top if r["frame"] != ka]
        ta = os.path.join(V.OUT, "%s--am%04d.tiff" % (subj, ka))
        if not os.path.exists(ta):
            V.render_frame(subj, ka, ta)
        argb = V.read_rgb(ta)
        Aa, da = R.register_best(mlum, V.lum_of(argb), R.master_cover(subj) / 1.0,
                                 wy, wx, WIN)
        mw = V.warp_window(argb, Aa, wy, wx, WIN).astype(np.float32)
        del argb
        os.remove(ta)
        print("CONTROL: frame %d warped into the master's window (ncc %.3f) is the "
              "reference" % (ka, da["ncc_context"]))
    if plant:
        rng = np.random.default_rng(3)
        blk = V.lum_of(mw)
        sig = float(np.std(blk - boxblur(blk, NOISE_R)))
        f = blot_field(blk.shape, rng) * plant * sig
        if do_chroma:
            # a CHROMA plant: equal and opposite in R and B leaves luminance almost
            # untouched and moves a/Y, b/Y -- the thing chroma_blotch measures.
            mw[..., 0] += f
            mw[..., 2] -= f
            print("POSITIVE CONTROL: planted %.1f sigma (+-%.1f DN R/B) CHROMA mottle"
                  % (plant, plant * sig))
        else:
            mw += f[..., None]
            print("POSITIVE CONTROL: planted %.1f sigma (%.1f DN) blotch into the master"
                  % (plant, plant * sig))
    if do_chroma:
        ma, mb = chroma_bands(mw)
        # SIGNED fields, both channels, trimmed exactly as chroma_blotch trims.
        # hypot() would be non-negative and two non-negative fields correlate
        # through their common level alone -- that would flatter the acquittal.
        Bm = np.stack([ma[C_HI:-C_HI, C_HI:-C_HI], mb[C_HI:-C_HI, C_HI:-C_HI]])
        stat_m = float(np.hypot(np.sqrt(np.mean(Bm[0] ** 2)), np.sqrt(np.mean(Bm[1] ** 2))))
    else:
        Bm = band_rel(V.lum_of(mw))[None]
        stat_m = float(np.std(Bm)) if (plant or "asmaster" in opts) else ms["blotch"]["contrast"]
    Sm = local_sharp(V.lum_of(mw))
    if do_chroma:
        Sm = Sm[C_HI:-C_HI, C_HI:-C_HI]
    print("master statistic %.6f   band-field rms %.6f" % (stat_m, float(np.sqrt(np.mean(Bm ** 2)))))

    km = R.master_cover(subj)
    tiles = [(mw, "MASTER %s %.5f" % (key, stat_m))]
    rows = []
    for r in top:
        k = r["frame"]
        tif = os.path.join(V.OUT, "%s--f%04d.tiff" % (subj, k))
        if not os.path.exists(tif):
            log = V.render_frame(subj, k, tif)
            ks = R.cover_of_log(log) or 1.0
        else:
            ks = r.get("cover_src", 1.0)
        srgb = V.read_rgb(tif)
        slum = V.lum_of(srgb)
        A, d = R.register_best(mlum, slum, km / ks, wy, wx, WIN)
        w = V.warp_window(srgb, A, wy, wx, WIN)
        del srgb, slum
        os.remove(tif)
        if do_chroma:
            sa, sb = chroma_bands(w)
            Bs = np.stack([sa[C_HI:-C_HI, C_HI:-C_HI], sb[C_HI:-C_HI, C_HI:-C_HI]])
        else:
            Bs = band_rel(V.lum_of(w))[None]
        Ss = local_sharp(V.lum_of(w))
        if do_chroma:
            Ss = Ss[C_HI:-C_HI, C_HI:-C_HI]
        res = Bm - Bs
        c_bb = corr(Bm, Bs)
        # IS THE RESIDUAL JUST THE SAME STRUCTURE, SHARPER?  An all-in-focus
        # composite differs from one frame by an unsharp-mask term on the SAME
        # field: U = Bs - blur(Bs).  Fit resid = alpha*U by least squares and
        # report the fraction of residual variance it explains.  A planted
        # mottle is not the frame's own structure and must score near zero.
        U = np.stack([b - cv2.GaussianBlur(b, (0, 0), 40) for b in Bs])
        a_hat = float((res * U).sum() / max(float((U * U).sum()), 1e-30))
        r2 = 1.0 - float(np.var(res - a_hat * U)) / max(float(np.var(res)), 1e-30)
        # IS THE RESIDUAL JUST THE SAME STRUCTURE, SHARPER?  An all-in-focus
        # composite differs from one frame by an unsharp-mask term on the SAME
        # field: U = Bs - blur(Bs).  Fit resid = alpha*U by least squares and
        # report the fraction of residual variance it explains.  A planted
        # mottle is not the frame's own structure and must score near zero.
        U = np.stack([b - cv2.GaussianBlur(b, (0, 0), 40) for b in Bs])
        a_hat = float((res * U).sum() / max(float((U * U).sum()), 1e-30))
        r2 = 1.0 - float(np.var(res - a_hat * U)) / max(float(np.var(res)), 1e-30)
        # where does the residual live? against the SOURCE's local sharpness.
        c_rd = corr(np.abs(res).mean(axis=0), -Ss)
        print("  frame %4d ncc %.3f   corr(Bm,Bs) %+.4f   rms Bs %.6f  rms resid %.6f "
              "(%.1f%% of master)   corr(|resid|,defocus) %+.4f   sharpen-model "
              "alpha %+.3f R2 %.3f"
              % (k, d["ncc_context"], c_bb, float(np.sqrt(np.mean(Bs ** 2))),
                 float(np.sqrt(np.mean(res ** 2))),
                 100 * np.sqrt(np.mean(res ** 2)) / max(np.sqrt(np.mean(Bm ** 2)), 1e-12),
                 c_rd, a_hat, r2))
        rows.append(dict(frame=k, corr=c_bb, corr_resid_defocus=c_rd, alpha=a_hat, r2=r2,
                         rms_bs=float(np.sqrt(np.mean(Bs ** 2))),
                         rms_res=float(np.sqrt(np.mean(res ** 2)))))
        tiles.append((w, "f%d source" % k))
        if len(tiles) == 2:
            keep = (Bs, res, Ss, k)
    # picture: as seen | master band | source band | residual
    Bs, res, Ss, k = keep
    Bm, Bs, res = Bm[0], Bs[0], res[0]     # channel 0 for the picture
    g = 2.5 / max(float(np.percentile(np.abs(Bm), 99)), 1e-9)
    def band_png(f):
        return np.clip(0.5 + g * f, 0, 1)
    mw = mw[C_HI:-C_HI, C_HI:-C_HI] if do_chroma else mw
    lo, hi = np.percentile(V.lum_of(mw), [1, 99])
    panels = [(np.clip((mw - lo) / max(hi - lo, 1e-9), 0, 1), "MASTER as seen"),
              (np.dstack([band_png(Bm)] * 3), "MASTER band-pass x%.0f" % g),
              (np.dstack([band_png(Bs)] * 3), "f%d band-pass x%.0f" % (k, g)),
              (np.dstack([band_png(res)] * 3), "residual master-f%d x%.0f" % (k, g))]
    S_ = 460
    canvas = np.zeros((S_ + 18, len(panels) * S_, 3), np.uint8)
    for i, (img, lab) in enumerate(panels):
        t = cv2.resize(np.asarray(img, np.float32), (S_, S_), interpolation=cv2.INTER_AREA)
        canvas[:S_, i * S_:(i + 1) * S_] = (np.clip(t, 0, 1) * 255).astype(np.uint8)
        cv2.putText(canvas, lab[:44], (i * S_ + 3, S_ + 13), cv2.FONT_HERSHEY_PLAIN,
                    0.9, (255, 255, 255), 1)
    tag = "%s-%s%s" % (subj, key, "-PLANT%.0f" % plant if plant else ("-AM%s" % opts["asmaster"] if "asmaster" in opts else ""))
    out = os.path.join(V.OUT, "novel-%s.png" % tag)
    cv2.imwrite(out, canvas[:, :, ::-1])
    print("wrote %s" % out)
    with open(os.path.join(V.OUT, "novel_%s.json" % tag), "w") as fh:
        json.dump(dict(subject=subj, key=key, plant=plant, rows=rows), fh, indent=1)


if __name__ == "__main__":
    main()
