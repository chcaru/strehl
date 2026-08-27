r"""V-NEVERWORSE / DAMAGE ASSESSMENT -- how much of the published ratio was gauge?

`vn_gauge.py` shows the two arms of every existing master/source ratio sit on
two different per-image tone curves. That is an argument. This is the
measurement: the SAME subject, the SAME source frames, the SAME window
coordinates, the ratio computed twice -- once the way V-REVIEW computed it
(shipped `--srgb` master against source frames rendered `--srgb
--exposure=<the master's own stops>`, its documented common-mode defence) and
once on the measurement gauge.

Any difference between the two columns is gauge, not merge. Nothing else moved.

Window coordinates are taken from the LINEAR master and applied unchanged to
the shipped master; the run asserts the two masters were cropped to the same
cover first, since they are the same merge and differ only in develop.

  python vn_damage.py [subject ...]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402
import vn_run as RUN                                          # noqa: E402
from orch_blotch import lum_of                                # noqa: E402

# The three subjects whose published ratios drove the print gate's adjudication:
# lead-1-cpl is the 1.258x that created this lane, leaf-2-cpl the 1.138x, and
# foam the 0.885x/0.527x that the gate reads as the merge halving the defect.
SUBJ = ["lead-1-cpl", "leaf-2-cpl", "foam"]
N = 21          # the same N the main run used, so the linear arm is reused
                # from `ratio/<subj>.json` and only the sRGB arm is rendered:
                # identical frames on both sides, which is what makes the
                # difference between the columns attributable to gauge alone


def ship_cover(subj):
    with open(L.ship_master_path(subj)[:-5] + ".log",
              encoding="utf-8", errors="replace") as fh:
        return L.cover_of_log(fh.read())


def srgb_arm(subj, frames, bw, cw):
    """V-REVIEW's protocol, reproduced exactly, at fixed window coordinates."""
    ks = ship_cover(subj)
    km = L.master_cover(subj) or 1.0
    if ks is None or abs(ks - km) > 1e-6:
        raise RuntimeError("%s: shipped cover %s != linear cover %s -- the two "
                           "masters are not the same geometry, so a fixed "
                           "window cannot be shared" % (subj, ks, km))
    mrgb = L.read_rgb(L.ship_master_path(subj))
    mstat = L.stats_at(mrgb, bw, cw)
    mlum = lum_of(mrgb)
    del mrgb
    flags = L.SHIP_FLAGS[:1] + ["--exposure=" + L.master_exposure(subj)]
    rows = []
    for k in frames:
        r = L.measure_source_frame(subj, k, mlum, bw, cw, ks, flags=flags)
        rows.append(r)
        print("   srgb %-22s f%-4d %-16s %.1fs" % (subj, k, r["state"], r["secs"]))
        sys.stdout.flush()
    del mlum
    return mstat, rows


def main(argv):
    subs = argv or SUBJ
    out = {}
    for s in subs:
        lin = RUN.measure(s, N)
        bw, cw = tuple(lin["bw"]), tuple(lin["cw"])
        ms, rows = srgb_arm(s, lin["frames"], bw, cw)
        # Same frames on both arms, admitted or refused by the SAME decision,
        # so the only thing that differs between the columns is the gauge. The
        # linear arm makes the call; the sRGB arm inherits it. (The clipping
        # test is calibrated on linear DN and would drop a different set on a
        # tone-curved render, which would silently change the comparison from
        # "gauge" to "gauge plus a different frame set".)
        adm = {r["frame"]: (r.get("ok_b"), r.get("ok_c")) for r in lin["rows"]}
        for r in rows:
            ob, oc = adm.get(r["frame"], (False, False))
            r["ok_b"], r["ok_c"] = bool(ob) and r.get("blotch") is not None, \
                bool(oc) and r.get("chroma") is not None
        rec = dict(subject=s, frames=lin["frames"], bw=list(bw), cw=list(cw),
                   srgb_master=ms, srgb_rows=rows, lin_master=lin["master"])
        for key in ("blotch", "band", "chroma"):
            ol = L.order_stats(lin["rows"], key)
            os_ = L.order_stats(rows, key)
            if ol is None or os_ is None:
                continue
            rec[key] = dict(
                lin=dict(vs_min=lin["master"][key] / ol["min"],
                         vs_med=lin["master"][key] / ol["med"],
                         vs_max=lin["master"][key] / ol["max"], n=ol["n"]),
                srgb=dict(vs_min=ms[key] / os_["min"], vs_med=ms[key] / os_["med"],
                          vs_max=ms[key] / os_["max"], n=os_["n"]))
        out[s] = rec
        print("\n%s  (window %s / %s, %d frames)" % (s, bw, cw, len(lin["frames"])))
        print("  %-7s %-28s %-28s %s" % ("stat", "sRGB gauge (as published)",
                                         "linear gauge (measurable)", "gauge effect"))
        for key in ("blotch", "band", "chroma"):
            if key not in rec:
                continue
            a, b = rec[key]["srgb"], rec[key]["lin"]
            print("  %-7s min %.4f med %.4f max %.4f   min %.4f med %.4f max %.4f"
                  "   vs_max x%.3f  vs_min x%.3f"
                  % (key, a["vs_min"], a["vs_med"], a["vs_max"],
                     b["vs_min"], b["vs_med"], b["vs_max"],
                     b["vs_max"] / a["vs_max"], b["vs_min"] / a["vs_min"]))
        sys.stdout.flush()
    L.jdump(out, os.path.join(L.OUT, "damage", "damage.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
