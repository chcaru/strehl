r"""INDEPENDENT ALL-IN-FOCUS COMPOSITE -- the innocent mechanism, built by
somebody else's program.

The defence for every ratio above 1 is: "the master is in focus everywhere, so
inside one window it legitimately carries more 50-400 px contrast than ANY single
frame."  That defence is testable.  Take the SAME frames, register them the same
way, and build an all-in-focus composite with twenty lines of numpy that contain
no strehl code, no pyramid, no election, no outlier stage.  Then measure the
gate's statistic on it.

  soft   per-pixel weighted mean, w = local_HF^4  (seam-free, no selection map)
  hard   per-pixel argmax of local_HF            (naive, seam-prone)
  mean   plain average of the frames             (no selection at all)

PREDICTION, declared before the run:
  mean  <  best single frame  <=  soft ~ hard  ~  master
If the independent composite reaches the master's reading, the reading is what
all-in-focus stacking of THESE frames produces and the merge added nothing.

ONE-SIDED.  The composite is built from a SUBSET of the bracket and from windows
that had to be resampled to get here, so it can only UNDER-represent the
mechanism.  Reaching the master proves the mechanism; falling short proves
nothing and is reported as inconclusive, never as a conviction.

  python vr_indep.py SUBJECT k0 k1 step
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
import vr_reg2 as R                                           # noqa: E402
from orch_blotch import boxblur                               # noqa: E402


def sharp(rgb, r=15):
    L = V.lum_of(rgb)
    return boxblur(np.abs(L - boxblur(L, 3)), r)


def compose(stack, rule):
    """stack: list of (win,win,3) float32.  Returns the composite."""
    S = [sharp(a, 15 if rule.endswith("15") else 60).astype(np.float64) for a in stack]
    if rule.startswith("mean"):
        return np.mean(stack, axis=0).astype(np.float32)
    if rule.startswith("hard"):
        idx = np.argmax(np.stack(S), axis=0)
        out = np.zeros_like(stack[0])
        for i, a in enumerate(stack):
            m = idx == i
            out[m] = a[m]
        return out
    p = 8.0 if rule.startswith("soft") else 4.0
    W = [s ** p for s in S]
    den = np.sum(W, axis=0)
    num = np.sum([w[..., None] * a for w, a in zip(W, stack)], axis=0)
    return (num / np.maximum(den, 1e-30)[..., None]).astype(np.float32)


class Acc:
    def __init__(self, win):
        self.num = np.zeros((win, win, 3), np.float64)
        self.den = np.zeros((win, win), np.float64)
        self.best = np.zeros((win, win, 3), np.float32)
        self.bs = np.full((win, win), -1.0, np.float32)
        self.mean = np.zeros((win, win, 3), np.float64)
        self.n = 0

    def add(self, rgb):
        s = sharp(rgb).astype(np.float64)
        w = s ** 4
        self.num += w[..., None] * rgb
        self.den += w
        m = s > self.bs
        self.best[m] = rgb[m]
        self.bs[m] = s[m]
        self.mean += rgb
        self.n += 1

    def out(self):
        soft = (self.num / np.maximum(self.den, 1e-30)[..., None]).astype(np.float32)
        return soft, self.best.copy(), (self.mean / max(self.n, 1)).astype(np.float32)


def main():
    subj = sys.argv[1]
    k0, k1, step = (int(x) for x in sys.argv[2:5])
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    ms = S["master"]
    bw = (ms["blotch"]["y"], ms["blotch"]["x"])
    cw = (ms["chroma"]["y"], ms["chroma"]["x"])
    km = R.master_cover(subj)
    mrgb = V.read_rgb(V.master_path(subj))
    mlum = V.lum_of(mrgb)
    mb = V.blotch_ratio(V.lum_of(mrgb[bw[0]:bw[0] + V.BWIN, bw[1]:bw[1] + V.BWIN]))[0]
    mc = V.gate_chroma(mrgb[cw[0]:cw[0] + V.CWIN, cw[1]:cw[1] + V.CWIN], at=(0, 0))["chroma"]
    del mrgb
    ab, ac = Acc(V.BWIN), Acc(V.CWIN)
    cache = os.path.join(V.OUT, "cache_%s" % subj)
    os.makedirs(cache, exist_ok=True)
    cache = os.path.join(V.OUT, "cache_%s" % subj)
    os.makedirs(cache, exist_ok=True)
    used, singles = [], []
    print("SUBJECT %s   frames %d..%d step %d   master blotch %.5f chroma %.6f"
          % (subj, k0, k1, step, mb, mc))
    for k in range(k0, k1 + 1, step):
        t0 = time.time()
        tif = os.path.join(V.OUT, "%s--ind%04d.tiff" % (subj, k))
        log = V.render_frame(subj, k, tif)
        ks = R.cover_of_log(log) or 1.0
        rgb = V.read_rgb(tif)
        slum = V.lum_of(rgb)
        A, d = R.register_best(mlum, slum, km / ks, bw[0], bw[1], V.BWIN)
        ncc = d.get("ncc_context") if d else None
        wb = V.warp_window(rgb, A, bw[0], bw[1], V.BWIN) if A is not None else None
        wc = V.warp_window(rgb, A, cw[0], cw[1], V.CWIN) if A is not None else None
        del rgb, slum
        os.remove(tif)
        if wb is None or wc is None or ncc is None or ncc < 0.75:
            print("  frame %4d SKIPPED (ncc %s)" % (k, ncc))
            continue
        b1 = V.blotch_ratio(V.lum_of(wb))[0]
        c1 = V.gate_chroma(wc, at=(0, 0))["chroma"]
        singles.append((b1, c1, k))
        ab.add(wb.astype(np.float64))
        ac.add(wc.astype(np.float64))
        np.save(os.path.join(cache, "b%04d.npy" % k), wb.astype(np.float32))
        np.save(os.path.join(cache, "c%04d.npy" % k), wc.astype(np.float32))
        np.save(os.path.join(cache, "b%04d.npy" % k), wb.astype(np.float32))
        np.save(os.path.join(cache, "c%04d.npy" % k), wc.astype(np.float32))
        used.append(k)
        print("  frame %4d ncc %.3f  single-frame blotch %.5f chroma %.6f  (%.0fs)"
              % (k, ncc, b1, c1, time.time() - t0))
        sys.stdout.flush()
    if len(used) < 3:
        print("NOT ENOUGH FRAMES")
        return
    res = {}
    for nm, (sb, hb, mnb), (sc, hc, mnc) in [("", ab.out(), ac.out())]:
        for lab, wbb, wcc in (("soft", sb, sc), ("hard", hb, hc), ("mean", mnb, mnc)):
            b = V.blotch_ratio(V.lum_of(wbb))[0]
            c = V.gate_chroma(wcc.astype(np.float32), at=(0, 0))["chroma"]
            res[lab] = (b, c)
    bs = max(s[0] for s in singles)
    cs = max(s[1] for s in singles)
    print("\n%-26s %10s %10s" % ("ARM", "blotch", "chroma"))
    print("%-26s %10.5f %10.6f" % ("MASTER (strehl merge)", mb, mc))
    for lab in ("soft", "hard", "mean"):
        b, c = res[lab]
        print("%-26s %10.5f %10.6f   master/this  %.3f  %.3f"
              % ("INDEPENDENT %s" % lab, b, c, mb / b, mc / c))
    print("%-26s %10.5f %10.6f   master/this  %.3f  %.3f"
          % ("best single frame", bs, cs, mb / bs, mc / cs))
    print("frames used: %s" % used)
    # extra composite rules from the cache: the r=15 sharpness map is per-pixel
    # noisy, which mixes frames at the PIXEL scale and can drive a composite
    # BELOW its own inputs.  r=60 selects in contiguous regions instead.
    sb = [np.load(os.path.join(cache, "b%04d.npy" % k)) for k in used]
    sc = [np.load(os.path.join(cache, "c%04d.npy" % k)) for k in used]
    for rule in ("hard60", "soft60", "hard15"):
        b = V.blotch_ratio(V.lum_of(compose(sb, rule)))[0]
        c = V.gate_chroma(compose(sc, rule), at=(0, 0))["chroma"]
        res[rule] = (b, c)
        print("%-26s %10.5f %10.6f   master/this  %.3f  %.3f"
              % ("INDEPENDENT %s" % rule, b, c, mb / b, mc / c))
    # extra composite rules from the cache: the r=15 sharpness map is per-pixel
    # noisy, which mixes frames at the PIXEL scale and can drive a composite
    # BELOW its own inputs.  r=60 selects in contiguous regions instead.
    sb = [np.load(os.path.join(cache, "b%04d.npy" % k)) for k in used]
    sc = [np.load(os.path.join(cache, "c%04d.npy" % k)) for k in used]
    for rule in ("hard60", "soft60", "hard15"):
        b = V.blotch_ratio(V.lum_of(compose(sb, rule)))[0]
        c = V.gate_chroma(compose(sc, rule), at=(0, 0))["chroma"]
        res[rule] = (b, c)
        print("%-26s %10.5f %10.6f   master/this  %.3f  %.3f"
              % ("INDEPENDENT %s" % rule, b, c, mb / b, mc / c))
    with open(os.path.join(V.OUT, "indep_%s.json" % subj), "w") as fh:
        json.dump(dict(subject=subj, used=used, master=[mb, mc],
                       soft=res["soft"], hard=res["hard"], mean=res["mean"],
                       best_single=[bs, cs], singles=singles), fh, indent=1)


if __name__ == "__main__":
    main()
