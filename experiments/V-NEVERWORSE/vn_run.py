r"""V-NEVERWORSE / THE MEASUREMENT -- merge-attributable ratio on all 26 subjects.

For each subject: render the SHIP-V4 merge into the measurement space
(`--linear-srgb --demosaic`, see `vn_gauge.py` for why the shipped `--srgb`
render may not be measured), choose the flattest blotch window and the chroma
window on THAT master, then render a uniform sample of its own source frames
into the SAME space, register each to the master and measure the same two
statistics through the same two windows.

WHAT THE DENOMINATOR IS, SAID OUT LOUD
    For both statistics LOW is good, so over the source frames
        min    = the BEST single frame   -> the invariant as literally stated
        median = the typical frame
        max    = the WORST single frame  -> what `vr_baseline.json` actually
                 used, and what `orch_printready.py:223` mislabels
                 "master/best-source"
    All three are reported. `min` and `max` are extrema and therefore biased in
    N; the median is not. `vn_sens.py` measures that bias instead of assuming
    it away.

WHY A SAMPLE, AND WHAT IT BOUNDS
    A full source arm is 4825 frames at ~5 s each. This lane samples N=21 per
    subject on a linspace that always includes both ends of the focus sweep.
    Subsampling can only RAISE the estimated min, so
        ratio_vs_min(sample) <= ratio_vs_min(full)
    which means a VIOLATION found on the sample is real, while a PASS on the
    sample is only a pass at the sampled reference. That asymmetry is stated
    with the result rather than buried.

  python vn_run.py [--n 21] [--shard i/k] [subject ...]
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402
from orch_blotch import lum_of                                # noqa: E402

RDIR = os.path.join(L.OUT, "ratio")
DEFAULT_N = 21


def sample(n_total, n_want):
    """Uniform over the focus sweep, both ends always included."""
    if n_want >= n_total:
        return list(range(n_total))
    return sorted(set(np.linspace(0, n_total - 1, n_want).round().astype(int).tolist()))


def measure(subj, n_want=DEFAULT_N, tag=None, force=False):
    out = os.path.join(RDIR, "%s%s.json" % (subj, tag or ""))
    if os.path.exists(out) and not force:
        return L.jload(out)
    t0 = time.time()
    L.check_pin()
    mp = L.ensure_linear_master(subj)
    mrgb = L.read_rgb(mp)
    bw, cw = L.choose_windows(mrgb)
    mstat = L.stats_at(mrgb, bw, cw)
    mlum = lum_of(mrgb)
    del mrgb
    km = L.master_cover(subj) or 1.0
    nt = L.n_frames(subj)
    ks = sample(nt, n_want)
    rows = []
    for k in ks:
        r = L.measure_source_frame(subj, k, mlum, bw, cw, km)
        rows.append(r)
        print("   %-30s f%-4d %-18s ncc %-6s blotch %-9s %.1fs"
              % (subj, k, r["state"], ("%.3f" % r["ncc_b"]) if r.get("ncc_b") else "-",
                 ("%.5f" % r["blotch"]) if r.get("blotch") else "-", r["secs"]))
        sys.stdout.flush()
    del mlum
    rec = dict(subject=subj, arm=L.ARM, gauge=" ".join(L.MEASURE_FLAGS),
               n_total=nt, n_asked=len(ks), frames=ks, bw=list(bw), cw=list(cw),
               cover_master=km, master=mstat, rows=rows,
               secs=round(time.time() - t0, 1))
    for key in ("blotch", "band", "chroma"):
        o = L.order_stats(rows, key)
        rec["src_" + key] = o
        rec["ratio_" + key] = None if o is None else dict(
            vs_min=mstat[key] / o["min"], vs_med=mstat[key] / o["med"],
            vs_max=mstat[key] / o["max"])
    # Admission bookkeeping, per statistic, so a dropped frame is a counted
    # frame and never a silently absent one.
    rec["admit"] = dict(
        blotch=dict(ok=sum(1 for r in rows if r.get("ok_b")),
                    drop=sorted(set(r.get("why_b") or r["state"]
                                    for r in rows if not r.get("ok_b")))),
        chroma=dict(ok=sum(1 for r in rows if r.get("ok_c")),
                    drop=sorted(set(r.get("why_c") or r["state"]
                                    for r in rows if not r.get("ok_c")))))
    rec["master_sat"] = dict(b=mstat["sat_b"], c=mstat["sat_c"])
    L.jdump(rec, out)
    return rec


def main(argv):
    n, shard, want = DEFAULT_N, None, []
    i = 0
    while i < len(argv):
        if argv[i] == "--n":
            n = int(argv[i + 1]); i += 2
        elif argv[i] == "--shard":
            a, b = argv[i + 1].split("/"); shard = (int(a), int(b)); i += 2
        else:
            want.append(argv[i]); i += 1
    subs = want or L.subjects()
    if shard:
        subs = [s for j, s in enumerate(subs) if j % shard[1] == shard[0]]
    print("V-NEVERWORSE ratio: %d subjects, N=%d frames each, gauge %s"
          % (len(subs), n, " ".join(L.MEASURE_FLAGS)))
    for s in subs:
        r = measure(s, n)
        rb, rc = r.get("ratio_blotch"), r.get("ratio_chroma")
        print("%-38s blotch vs min/med/max %s | chroma %s | admit b %d c %d of "
              "%d | %.0fs"
              % (s,
                 "-" if not rb else "%.4f/%.4f/%.4f"
                 % (rb["vs_min"], rb["vs_med"], rb["vs_max"]),
                 "-" if not rc else "%.4f/%.4f/%.4f"
                 % (rc["vs_min"], rc["vs_med"], rc["vs_max"]),
                 r["admit"]["blotch"]["ok"], r["admit"]["chroma"]["ok"],
                 r["n_asked"], r["secs"]))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
