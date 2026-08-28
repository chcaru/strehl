r"""Settle the residual at exponent 1 by measuring the ceiling EXHAUSTIVELY.

WHAT IS UNRESOLVED. Seven of nine subjects show no ceiling excess at exponent 1,
which is what the selection-law mechanism predicts. Two do: flower-inner-edge-cpl
keeps +28.8% and pencil-steep-angle-cpl keeps +43.6%. lad_depth.py found that
residual tracks stack depth at Spearman +0.9333 and ceiling coverage at -0.8167
across all nine subjects -- the signature of an UNDER-SAMPLED CEILING in my own
instrument rather than of anything the merge does. sharpaxis.py caps its ceiling
search at 56 renders, so a 299-frame stack is searched at 18.7% coverage while a
19-frame stack is searched at 78.9%.

A CORRELATION IS NOT A DEMONSTRATION. Nine points and a rank correlation are
suggestive; depth is also confounded with subject, with focus travel, and with
how much of the frame is ever in focus. The direct measurement is available and
is simply expensive: render EVERY frame and take the true max. That is done here.

WHAT EACH OUTCOME MEANS, STATED BEFORE THE RUN. If the exhaustive ceiling
absorbs the residual -- excess at exponent 1 falling to about zero -- the
residual was my instrument and the selection law accounts for the whole effect.
If the residual survives against a ceiling that has seen every frame, it is real
and the selection law is not the only source. Both are publishable; only one is
currently believed.

THE MASTER IS NOT RE-RENDERED. Per-site band values for every arm are already in
ladder-sites.json, so this changes only the DENOMINATOR. Registration and window
placement are sharpaxis.py's own, unchanged, so the exhaustive ceiling is
comparable to the sampled one it replaces.
"""
import io
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402
import lad_measure as lm                                           # noqa: E402
import sharpaxis as sa                                             # noqa: E402

OUT = os.path.join(HERE, "ladder-ceiling.json")


def exhaustive(sub, sites, every=1):
    d = os.path.join(cm.WORK, sub)
    os.makedirs(d, exist_ok=True)
    mp = os.path.join(d, "lad-master.tiff")
    got, err, _ = cm.render(sub, mp)
    if not got:
        raise SystemExit("master render failed: %s" % err)
    mrgb, lat = cm.read_rgb(mp)
    ml = sa.lum(mrgb)
    del mrgb
    os.remove(mp)
    n_raw = len([f for f in os.listdir(os.path.join(cm.RAW, sub))
                 if f.lower().endswith(".arw")])
    coords = [(s["y"], s["x"]) for s in sites]
    store = [dict() for _ in coords]
    ks = list(range(0, n_raw, every))
    t0 = time.time()
    ok = 0
    for i, k in enumerate(ks):
        if sa._render_and_measure(sub, d, k, ml, lat, coords, store):
            ok += 1
        if (i + 1) % 25 == 0:
            el = time.time() - t0
            print("      %3d/%3d frames  %.0fs elapsed  %.0fs left"
                  % (i + 1, len(ks), el, el / (i + 1) * (len(ks) - i - 1)))
    return store, n_raw, ok, len(ks)


def main():
    cm.check_binary()
    sites_doc = json.load(io.open(os.path.join(HERE, "ladder-sites.json"),
                                  encoding="utf-8"))
    doc = {}
    if os.path.exists(OUT):
        doc = json.load(io.open(OUT, encoding="utf-8"))
    subs = sys.argv[1:]
    if not subs:
        raise SystemExit("name subjects explicitly; this renders every frame")
    for sub in subs:
        if sub in doc:
            print("  %-26s already done" % sub)
            continue
        sites, _ = lm.frozen_sites(sub)
        if not sites:
            print("  %-26s no frozen sites" % sub)
            continue
        print("\n== %s  (%d sites, exhaustive ceiling)" % (sub, len(sites)))
        store, n_raw, ok, tried = exhaustive(sub, sites)
        rec = {"n_raw": n_raw, "n_rendered_ok": ok, "n_attempted": tried,
               "sites": []}
        arms = sites_doc.get(sub, {}).get("arms", {})
        for i, s in enumerate(sites):
            st = store[i]
            e = {"y": s["y"], "x": s["x"], "ceiling_sampled": s["ceiling"],
                 "n_frames_seen": len(st)}
            if st:
                e["ceiling_exhaustive"] = float(max(st.values()))
                e["peak_frame"] = int(max(st, key=lambda k: st[k]))
                e["ceiling_rise"] = e["ceiling_exhaustive"] / s["ceiling"] - 1.0
            rec["sites"].append(e)
        for tag in ("e1", "e2", "e4", "e8", "default"):
            mb = arms.get(tag, {}).get("master_band")
            if not mb:
                continue
            old, new = [], []
            for i, s in enumerate(sites):
                v = mb[i] if i < len(mb) else None
                ce = rec["sites"][i].get("ceiling_exhaustive")
                if not lm.finite(v) or not lm.finite(ce) or ce <= 0:
                    continue
                old.append(v / s["ceiling"] - 1.0)
                new.append(v / ce - 1.0)
            if old:
                rec.setdefault("excess", {})[tag] = {
                    "n": len(old),
                    "sampled_ceiling_median": float(np.median(old)),
                    "exhaustive_ceiling_median": float(np.median(new))}
        doc[sub] = rec
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        rises = [s["ceiling_rise"] for s in rec["sites"] if "ceiling_rise" in s]
        print("    frames rendered %d/%d   ceiling rose: median %+.2f%%  max %+.2f%%"
              % (ok, n_raw, 100 * float(np.median(rises)), 100 * max(rises)))
        for tag, v in rec.get("excess", {}).items():
            print("    %-8s excess  sampled ceiling %+8.3f%%  ->  exhaustive %+8.3f%%"
                  % (tag, 100 * v["sampled_ceiling_median"],
                     100 * v["exhaustive_ceiling_median"]))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
