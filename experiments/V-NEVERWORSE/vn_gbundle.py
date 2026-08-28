"""Green-luma-only frame bundles, so a 299-frame stack fits in memory.

`vn_commission.build_bundle` keeps both the 900 px blotch window and the
1200 px chroma window as RGB uint16, which is 13.5 MB per frame -- 4.0 GB at
N=299, on a box with ~16 GB shared across ten lanes. The dilution question is
answered entirely on the SELECTION plane, and `pyramid.rs:1300` says the
selection is made on green luma:

    `luma` is the plane the selection is made on - green luma, so that
    the decision is the same one the shipped election makes.

So this keeps the green plane of the blotch window only: 1.62 MB per frame,
484 MB at N=299. Registration, gauge, windows and admission are unchanged --
this calls the SAME `measure_source_frame` the RGB bundler does and simply
discards two of the three planes and the second window afterwards.

Emphatically NOT a substitute for the RGB bundle: anything that reconstructs
an image (hull violations, sharpness on colour) still needs `vn_commission`.
"""
import io
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vn_lib as L  # noqa: E402
from vn_commission import lum_of  # noqa: E402

GDIR = r"C:\dev\strehl-out\V-NEVERWORSE\gbundle"


def build(subj, force=False, limit=None):
    os.makedirs(GDIR, exist_ok=True)
    npz = os.path.join(GDIR, "%s.npz" % subj)
    js = os.path.join(GDIR, "%s.json" % subj)
    if os.path.exists(npz) and os.path.exists(js) and not force:
        print("  %s already built" % subj)
        return
    L.check_pin()
    mp = L.ensure_linear_master(subj)
    mrgb = L.read_rgb(mp)
    bw, cw = L.choose_windows(mrgb)
    mlum = lum_of(mrgb)
    km = L.master_cover(subj) or 1.0
    n = L.n_frames(subj)
    idx = list(range(n))[:limit] if limit else list(range(n))
    rows, greens, kept = [], [], []
    t0 = time.time()
    for k in idx:
        keep = []
        r = L.measure_source_frame(subj, k, mlum, bw, cw, km, keep=keep)
        rows.append(r)
        if keep:
            _, wb, _wc = keep[0]
            greens.append(np.ascontiguousarray(wb[:, :, 1]).astype(np.uint16))
            kept.append(int(k))
            del wb, _wc
        del keep
        if k % 10 == 0 or k == idx[-1]:
            el = time.time() - t0
            done = len(rows)
            print("  %s f%-4d %-16s kept=%d  %.0fs elapsed, ~%.0f min left"
                  % (subj, k, r["state"], len(kept), el,
                     (el / max(done, 1)) * (len(idx) - done) / 60.0))
            sys.stdout.flush()
    G = np.stack(greens) if greens else np.zeros((0, L.BWIN, L.BWIN), np.uint16)
    mg = np.ascontiguousarray(
        mrgb[bw[0]:bw[0] + L.BWIN, bw[1]:bw[1] + L.BWIN, 1]).astype(np.uint16)
    np.savez_compressed(npz, g=G, kept=np.array(kept, dtype=np.int32), mg=mg)
    json.dump(dict(subject=subj, bw=list(bw), km=km, n_source=n,
                   kept=kept, rows=rows),
              io.open(js, "w", encoding="utf-8"))
    print("  %s DONE: %d/%d frames kept, %.1f min"
          % (subj, len(kept), len(idx), (time.time() - t0) / 60.0))


def _admitted(rows, rule=None):
    """Frames admissible as a selection input, and which rule decided it.

    `ok_b` is the per-statistic admission flag added later; bundles written
    before it carry only `state`. Falling back silently would change the
    admission rule between subjects without saying so, so the rule in force is
    returned and recorded alongside the measurement.

    `rule="registered"` widens admission to every frame that got a warp,
    excluding only UNREGISTERED. This exists because `ok_b` gates on
    `ncc_b >= 0.75`, and on a deep stack that threshold does NOT separate
    frames that failed to register from frames that registered fine and are
    simply far from the master's focus plane. On `bee-2-cpl` the correlation
    decays smoothly and monotonically with depth -- 0.950, 0.943, 0.916,
    0.865, 0.752, 0.628, 0.517, 0.386, 0.265, 0.143 -- which is a defocus
    ramp, not a registration cliff. Excluding those 118 frames would measure a
    172-frame subrange and call it the 299-frame stack. The merge sees them,
    so an arm that answers "what does depth do to the merge" must see them
    too.
    """
    if rule == "registered":
        return ({r["frame"] for r in rows
                 if r.get("state") != "UNREGISTERED"}, "state!=UNREGISTERED")
    if any("ok_b" in r for r in rows):
        return {r["frame"] for r in rows if r.get("ok_b")}, "ok_b"
    return {r["frame"] for r in rows if r.get("state") == "OK"}, "state==OK"


def load(subj, rule=None):
    """Frames as float64 green luma, in the order they were kept.

    Falls back to the RGB bundle written by `vn_commission.build_bundle` when
    no green bundle exists, taking plane 1 of the same 900 px window. The two
    paths are the same pixels -- the RGB bundle is built by the same
    `measure_source_frame` call -- so this is a format fallback, not a
    different gauge. Which path was used is returned, because a silent
    fallback is how two arms end up on different data.
    """
    npz = os.path.join(GDIR, "%s.npz" % subj)
    if os.path.exists(npz):
        z = np.load(npz)
        meta = json.load(io.open(os.path.join(GDIR, "%s.json" % subj),
                                 encoding="utf-8"))
        ok, rule = _admitted(meta["rows"], rule)
        kept = list(z["kept"])
        sel = [i for i, k in enumerate(kept) if k in ok]
        meta["source"], meta["admit_rule"] = "gbundle", rule
        return z["g"][sel].astype(np.float64), [kept[i] for i in sel], meta
    bdir = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"
    bnpz = os.path.join(bdir, "%s.npz" % subj)
    if not os.path.exists(bnpz):
        raise IOError("no green bundle and no RGB bundle for %s" % subj)
    z = np.load(bnpz)
    meta = json.load(io.open(os.path.join(bdir, "%s.json" % subj),
                             encoding="utf-8"))
    ok, rule = _admitted(meta["rows"], rule)
    keys = [k for k in sorted(z.files)
            if k.startswith("b") and k != "bw" and int(k[1:]) in ok]
    if not keys:
        raise IOError("%s: no frames admitted under %s" % (subj, rule))
    meta["source"], meta["admit_rule"] = "rgb-bundle-green-plane", rule
    return (np.stack([z[k][:, :, 1] for k in keys]).astype(np.float64),
            [int(k[1:]) for k in keys], meta)


if __name__ == "__main__":
    for s in sys.argv[1:]:
        build(s)
