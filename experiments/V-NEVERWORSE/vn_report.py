r"""V-NEVERWORSE / THE TABLE -- 26 rows, a partition that sums, and a verdict.

Absolute blotch and absolute chroma are the GATE's numbers: `orch_blotch` and
`orch_chroma` run unmodified on the shipped SHIP-V4 master, so the first two
columns are directly comparable with `orch_printready.py`.

The ratio columns are this lane's: the same two statistics on the same merge
developed into `--linear-srgb --demosaic`, against that subject's OWN source
frames developed the same way and registered into the master's own windows.

The partition is explicit. A subject that could not be measured appears in its
own counted category with a reason. measured + refused + failed = 26, checked
arithmetically before anything is printed, because a count that does not move
is the same glyph whether nothing was wrong or nothing was examined.

  python vn_report.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402

RDIR = os.path.join(L.OUT, "ratio")
MIN_OK = 7          # fewer registered frames than this and the order statistic
                    # is not an order statistic; the subject is REFUSED


def absolute(subj):
    """The gate's own absolute statistics, on the shipped master."""
    rgb = L.read_rgb(L.ship_master_path(subj))
    bw, cw = L.choose_windows(rgb)
    s = L.stats_at(rgb, bw, cw)
    del rgb
    return s


def load(subj):
    p = os.path.join(RDIR, "%s.json" % subj)
    return L.jload(p) if os.path.exists(p) else None


def sharp_half(ok):
    """The source frames that are actually resolving detail at this window.

    A blotch statistic rewards smoothness, and a defocused frame is smooth, so
    the plain min over frames can be won by a frame that resolved nothing. This
    is rule 4's argmax defect wearing the other sign. `relhf` (3 px energy over
    mean) is the available focus proxy: every source window is resampled
    identically, so relhf is comparable ACROSS frames even though W1 shows
    resampling suppresses it by ~20-30% relative to the unwarped master.
    """
    if not ok:
        return []
    med = float(np.median([r["relhf"] for r in ok]))
    return [r for r in ok if r["relhf"] >= med]


def extra_denoms(rec, key):
    ok = [r for r in rec["rows"] if L.admits(r, key) and r.get(key) is not None]
    if not ok:
        return None
    m = rec["master"][key]
    sh = sharp_half(ok)
    v = sorted(r[key] for r in ok)
    return dict(
        vs_min_sharp=m / min(r[key] for r in sh) if sh else None,
        n_sharp=len(sh),
        beaten=sum(1 for x in v if x < m),      # frames STRICTLY better than the master
        n=len(v))


def classify(rec, key="blotch"):
    """Per-STATISTIC partition. A subject can be measurable on blotch and
    refused on chroma; collapsing the two would hide a refusal inside a pass."""
    if rec is None:
        return "failed", "no measurement record written"
    rows = rec["rows"]
    if not rows:
        return "failed", "no source frames attempted"
    ok = [r for r in rows if L.admits(r, key)]
    bad = {}
    for r in rows:
        if not L.admits(r, key):
            w = r.get("why_c" if key == "chroma" else "why_b") or r["state"]
            bad[w] = bad.get(w, 0) + 1
    msat = rec.get("master_sat", {}).get("c" if key == "chroma" else "b", 0.0)
    if msat > L.SAT_MAX:
        return "refused", ("the MASTER's own %s window is %.1f%% clipped -- the "
                           "statistic has no headroom on either arm"
                           % (key, 100 * msat))
    if len(ok) < MIN_OK:
        return "refused", ("only %d/%d source frames admissible (%s)"
                           % (len(ok), len(rows),
                              ", ".join("%s x%d" % (k, v)
                                        for k, v in sorted(bad.items()))
                              or "no reason recorded"))
    return "measured", ("%d/%d frames" % (len(ok), len(rows))
                        + ("; dropped " + ", ".join("%s x%d" % (k, v)
                                                    for k, v in sorted(bad.items()))
                           if bad else ""))


def main():
    subs = L.subjects()
    rows = []
    part = dict(blotch=dict(measured=[], refused=[], failed=[]),
                chroma=dict(measured=[], refused=[], failed=[]))
    for s in subs:
        rec = load(s)
        cat = {}
        for key in ("blotch", "chroma"):
            c, why = classify(rec, key)
            cat[key] = (c, why)
            part[key][c].append((s, why))
        a = absolute(s)
        r = dict(subject=s, abs_blotch=a["blotch"], abs_chroma=a["chroma"],
                 cat_blotch=cat["blotch"][0], why_blotch=cat["blotch"][1],
                 cat_chroma=cat["chroma"][0], why_chroma=cat["chroma"][1])
        r["cat"] = ("measured"
                    if "measured" in (cat["blotch"][0], cat["chroma"][0])
                    else cat["blotch"][0])
        r["why"] = cat["blotch"][1]
        if rec is not None:
            ok = [q for q in rec["rows"] if q.get("state") == "OK"]
            r["n"] = len(ok)
            r["n_total"] = rec["n_total"]
            for key in ("blotch", "band", "chroma"):
                o, rt = rec.get("src_" + key), rec.get("ratio_" + key)
                if o and rt:
                    r[key] = dict(rt, **{k: o[k] for k in
                                         ("min", "med", "max", "argmin", "argmax")})
                    ex = extra_denoms(rec, key)
                    if ex:
                        r[key].update(ex)
            if ok:
                r["relhf_med"] = float(np.median([q["relhf"] for q in ok]))
                bo = rec.get("src_blotch") or {}
                r["relhf_argmin"] = bo.get("relhf_at_min")
        rows.append(r)

    for key in ("blotch", "chroma"):
        tot = sum(len(v) for v in part[key].values())
        if tot != len(subs):
            raise RuntimeError("%s partition does not sum: %d != %d"
                               % (key, tot, len(subs)))

    print("V-NEVERWORSE -- merge-attributable ratio, all %d subjects" % len(subs))
    print("gauge %s | masters %s pin %s..%s | denominator = the subject's own "
          "source frames" % (" ".join(L.MEASURE_FLAGS), L.ARM,
                             L.PIN_SHA[:8], L.PIN_SHA[-4:]))
    print("\n%-36s %8s %8s | %7s %7s %7s %7s | %7s | %7s %7s %7s | %5s %4s %4s | %s"
          % ("subject", "absBlot", "absChrm", "b/min", "b/mnSh", "b/med", "b/max",
             "band/mn", "c/min", "c/med", "c/max", "beat", "n", "N", "verdict"))
    viol_b, viol_c = [], []
    for r in rows:
        b, bd, c = r.get("blotch"), r.get("band"), r.get("chroma")
        mb = r["cat_blotch"] == "measured"
        mc = r["cat_chroma"] == "measured"
        if not mb and not mc:
            print("%-36s %8.5f %8.5f | %s"
                  % (r["subject"], r["abs_blotch"], r["abs_chroma"],
                     r["cat_blotch"].upper() + ": " + r["why_blotch"]))
            continue
        vb = mb and b["vs_min"] > 1.0
        vc = mc and c["vs_min"] > 1.0
        if vb:
            viol_b.append((r["subject"], b["vs_min"]))
        if vc:
            viol_c.append((r["subject"], c["vs_min"]))

        def f(d, k, w=7):
            if d is None or d.get(k) is None:
                return "%*s" % (w, "-")
            return "%*.4f" % (w, d[k])

        print("%-36s %8.5f %8.5f | %s %s %s %s | %s | %s %s %s | %2s/%2s %4d %4d | %s"
              % (r["subject"], r["abs_blotch"], r["abs_chroma"],
                 f(b if mb else None, "vs_min"), f(b if mb else None, "vs_min_sharp"),
                 f(b if mb else None, "vs_med"), f(b if mb else None, "vs_max"),
                 f(bd if mb else None, "vs_min"),
                 f(c if mc else None, "vs_min"), f(c if mc else None, "vs_med"),
                 f(c if mc else None, "vs_max"),
                 (b or {}).get("beaten", "-") if mb else "-",
                 (b or {}).get("n", "-") if mb else "-",
                 r.get("n", 0), r.get("n_total", 0),
                 ("BLOTCH>1 " if vb else "") + ("CHROMA>1 " if vc else "")
                 + ("b:" + r["cat_blotch"].upper() + " " if not mb else "")
                 + ("c:" + r["cat_chroma"].upper() if not mc else "")
                 or "holds"))

    for key in ("blotch", "chroma"):
        p = part[key]
        print("\nPARTITION %-6s measured %d + refused %d + failed %d = %d of %d"
              % (key, len(p["measured"]), len(p["refused"]), len(p["failed"]),
                 sum(len(v) for v in p.values()), len(subs)))
        for cat in ("refused", "failed"):
            for s, why in p[cat]:
                print("  %-8s %-34s %s" % (cat.upper(), s, why))

    print("\nIS THE ARGMIN FRAME A DEFOCUSED ONE?  (relhf = 3 px energy / mean; a "
          "defocused frame is smooth and wins a smoothness contest for free)")
    print("  %-36s %10s %10s %8s" % ("subject", "relhf@min", "relhf med", "ratio"))
    for r in rows:
        if r["cat_blotch"] != "measured" or not r.get("relhf_argmin"):
            continue
        print("  %-36s %10.5f %10.5f %8.3f"
              % (r["subject"], r["relhf_argmin"], r["relhf_med"],
                 r["relhf_argmin"] / max(r["relhf_med"], 1e-9)))

    print("\nINVARIANT: 'the merge is never worse than the BEST single frame it "
          "was built from'")
    for key, viol in (("blotch", viol_b), ("chroma", viol_c)):
        n = len(part[key]["measured"])
        print("  %-7s HOLDS on %d/%d measured, VIOLATED on %d  (+%d refused, "
              "%d failed)"
              % (key, n - len(viol), n, len(viol),
                 len(part[key]["refused"]), len(part[key]["failed"])))
        for s, v in sorted(viol, key=lambda t: -t[1]):
            print("      %-34s %.4fx" % (s, v))
    L.jdump(dict(rows=rows, partition=part,
                 violations=dict(blotch=viol_b, chroma=viol_c)),
            os.path.join(L.OUT, "report", "table.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
