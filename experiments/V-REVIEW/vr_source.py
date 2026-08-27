r"""ARM SOURCE -- the gate's two statistics on the frames the master was built
from, rendered through the SAME pinned binary, the SAME flags and the SAME
exposure stops, one frame at a time (STREHL_ONLY_FRAME=k, merge_cmd.rs:1734),
and measured at the MASTER'S OWN window after the geometry between the two
renders has been measured rather than assumed.

Why not rawpy: the master has the sRGB transfer curve applied (its own
provenance says so). band/mean contrast is invariant to a linear gain, which is
what section 99 corrected; it is NOT invariant to a transfer curve. Rendering
the source frame through the same pipeline makes demosaic, CA, alignment
resample, colour matrix, exposure gain and the curve COMMON MODE, so the only
difference left between the arms is the merge.

Two floors, both absolute, both declared before the run:
  REGISTRATION  a frame whose context NCC against the master is below NCC_MIN is
                not looking at the same piece of subject and is EXCLUDED from
                the source maximum (it is still printed).
  FOCUS         the winning source frame's relative high-frequency content at
                the window is printed against the master's. If no frame in the
                bracket resolves the window at all, the control cannot speak and
                the subject is UNVERIFIABLE rather than convicted -- a merge
                cannot be convicted of manufacturing structure by a comparison
                against frames that were never in focus there.

  python vr_source.py SUBJECT [coarse] [refine]
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
import vr_reg2 as R                                           # noqa: E402

BWIN, CWIN = V.BWIN, V.CWIN
NCC_MIN = 0.75


def f(v, spec="%9.5f"):
    try:
        return spec % v
    except (TypeError, ValueError):
        return "%*s" % (int(spec[1:spec.index(".")]), "-")


def measure_frame(subj, k, mlum, bw, cw, km, keep=False):
    t0 = time.time()
    tif = os.path.join(V.OUT, "%s--f%04d.tiff" % (subj, k))
    log = V.render_frame(subj, k, tif)
    ks = R.cover_of_log(log) or 1.0
    srgb = V.read_rgb(tif)
    slum = V.lum_of(srgb)
    A, d = R.register_best(mlum, slum, km / ks, bw[0], bw[1], BWIN)
    row = dict(frame=k, how=d.get("how"), ecc=d.get("ecc"), scale=d.get("scale"),
               ncc_b=d.get("ncc_context"), cover_src=ks, secs=None)
    if A is None:
        row["state"] = "UNREGISTERED"
    else:
        row["ncc_c"] = R.context_ncc(mlum, slum, A, cw[0], cw[1], CWIN)
        wb = V.warp_window(srgb, A, bw[0], bw[1], BWIN)
        wc = V.warp_window(srgb, A, cw[0], cw[1], CWIN)
        if wb is None or wc is None:
            row["state"] = "WINDOW-OUTSIDE-SOURCE"
        else:
            r, bd, nd, md = V.blotch_ratio(V.lum_of(wb))
            ch = V.gate_chroma(wc, at=(0, 0))
            row.update(state="OK", blotch=r, band=bd, noise=nd, mean=md,
                       relhf=nd / max(md, 1e-9), chroma=ch["chroma"],
                       chr_std=ch["chr_std"])
            if row["ncc_b"] is None or row["ncc_b"] < NCC_MIN:
                row["state"] = "POOR-REG"
    del srgb, slum
    if not keep:
        try:
            os.remove(tif)
        except OSError:
            pass
    row["secs"] = round(time.time() - t0, 1)
    return row


def main():
    subj = sys.argv[1]
    ncoarse = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    nrefine = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    with open(os.path.join(V.OUT, "master_stats.json")) as fh:
        ms = json.load(fh)[subj]
    bw = (ms["blotch"]["y"], ms["blotch"]["x"])
    cw = (ms["chroma"]["y"], ms["chroma"]["x"])
    km = R.master_cover(subj)
    n = len(V.frames_of(subj))
    mrelhf = ms["blotch"]["noise"] / ms["blotch"]["mean"]
    print("SUBJECT %s  %d frames  master cover %.4f  blotch %.5f chroma %.6f  relHF %.5f"
          % (subj, n, km, ms["blotch"]["contrast"], ms["chroma"]["chroma"], mrelhf))
    print("windows: blotch %r  chroma %r   (master mean %.1f DN band %.1f noise %.1f)"
          % (bw, cw, ms["blotch"]["mean"], ms["blotch"]["band"], ms["blotch"]["noise"]))
    print("%6s %9s %9s %9s %8s %7s %7s %7s %9s %5s %s"
          % ("frame", "blotch", "chroma", "meanDN", "relHF", "ncc_b", "ncc_c", "scale",
             "how", "secs", "state"))
    rows, done = [], set()
    mlum = V.lum_of(V.read_rgb(V.master_path(subj)))

    def run(idx):
        for k in idx:
            k = int(k)
            if k in done or k < 0 or k >= n:
                continue
            done.add(k)
            r = measure_frame(subj, k, mlum, bw, cw, km)
            rows.append(r)
            print("%6d %s %s %s %s %s %s %s %9s %5.0f %s"
                  % (k, f(r.get("blotch")), f(r.get("chroma"), "%9.6f"),
                     f(r.get("mean"), "%9.1f"), f(r.get("relhf"), "%8.5f"),
                     f(r.get("ncc_b"), "%7.3f"), f(r.get("ncc_c"), "%7.3f"),
                     f(r.get("scale"), "%7.4f"), r.get("how"), r["secs"], r["state"]))
            sys.stdout.flush()

    coarse = sorted(set(np.linspace(0, n - 1, ncoarse).astype(int).tolist()))
    run(coarse)
    step = max(1, (n - 1) // max(ncoarse - 1, 1))
    for _ in range(2):
        ok = [r for r in rows if r["state"] == "OK"]
        if not ok or not nrefine:
            break
        extra = []
        for key in ("blotch", "chroma"):
            best = max(ok, key=lambda r: r[key])["frame"]
            extra += [best - step // 2, best + step // 2, best - step // 4,
                      best + step // 4, best - 1, best + 1]
        run(sorted(set(int(e) for e in extra))[:2 * nrefine])
        step = max(1, step // 2)

    ok = [r for r in rows if r["state"] == "OK"]
    out = dict(subject=subj, n_frames=n, master=ms, master_relhf=mrelhf,
               rows=rows, sampled=sorted(done), ncc_min=NCC_MIN)
    if ok:
        for key in ("blotch", "chroma"):
            v = [r[key] for r in ok]
            best = max(ok, key=lambda r: r[key])
            out["src_%s_max" % key] = max(v)
            out["src_%s_min" % key] = min(v)
            out["src_%s_med" % key] = float(np.median(v))
            out["src_%s_argmax" % key] = best["frame"]
            out["src_%s_relhf" % key] = best.get("relhf")
        mb, mc = ms["blotch"]["contrast"], ms["chroma"]["chroma"]
        print("\nBLOTCH  master %9.5f  source max %9.5f (frame %d, relHF %.5f vs master "
              "%.5f)  med %9.5f  RATIO %.3f"
              % (mb, out["src_blotch_max"], out["src_blotch_argmax"],
                 out["src_blotch_relhf"], mrelhf, out["src_blotch_med"],
                 mb / out["src_blotch_max"]))
        print("CHROMA  master %9.6f  source max %9.6f (frame %d)  med %9.6f  RATIO %.3f"
              % (mc, out["src_chroma_max"], out["src_chroma_argmax"],
                 out["src_chroma_med"], mc / out["src_chroma_max"]))
        add = mc ** 2 - out["src_chroma_max"] ** 2
        print("CHROMA  component the merge could have added: %s"
              % (("<= %.6f" % np.sqrt(add)) if add > 0 else "NONE (master <= source max)"))
        print("registered OK %d of %d rendered (floor ncc %.2f)" % (len(ok), len(rows), NCC_MIN))
    with open(os.path.join(V.OUT, "source_%s.json" % subj), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
