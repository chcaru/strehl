"""Emit the section 14 tables as markdown, from the data.

Every number in section 14 is printed by this script and pasted, never typed.
Transcription is the one error class a verifier cannot catch, because the
verifier re-derives from the same source the typo was made against.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_score as S                                              # noqa: E402
import matched_grain as M                                         # noqa: E402
from floor_predict import read, invert, KS as PKS                 # noqa: E402
from floor_cost import timing                                     # noqa: E402


def main():
    order = ["coffee-bubbles", "109MSDCF", "119MSDCF",
             "flower-bud-alone-cpl", "bee-1-cpl"]
    data = {}
    for s in order:
        r = S.score(s)
        if r and len(r) == len(S.ARMS):
            data[s] = r
    if not data:
        print("no complete subject yet")
        return 1

    print("#### 14.2 The sweep\n")
    for s in order:
        if s not in data:
            continue
        rows = data[s]
        w = rows["WHITE200"]
        print("`%s`, N=%d, measured floor at band 0 = %.4f x white:\n"
              % (s, S.bl.NFRAMES[s], rows["G200"][4]))
        print("| arm | `k` | floor | blotch | grain | sharp/tex | "
              "averaged @ L0 |")
        print("|---|---:|---|---:|---:|---:|---:|")
        for a in S.ARMS:
            r = rows[a]
            tag = {"WHITE200": " (pre-fix ship)", "G200": " (**ships today**)"}
            print("| `%s`%s | %s | %s | %+.2f%% | %+.2f%% | %+.2f%% | %.1f%% |"
                  % (a, tag.get(a, ""), S.KS[a].replace("w", ""),
                     "white" if a == "WHITE200" else "measured",
                     100 * (r[0] / w[0] - 1), 100 * (r[1] / w[1] - 1),
                     100 * (r[2] / w[2] - 1), r[3]))
        av = [rows[a] for a in S.ARMS]
        g = np.array([x[1] for x in av])
        t = np.array([x[2] for x in av])
        m = np.array([x[0] for x in av])
        print("\n`r(sharp/tex, grain)` = **%+.4f**, `r(blotch, grain)` = "
              "%+.4f.\n" % (np.corrcoef(g, t)[0, 1], np.corrcoef(g, m)[0, 1]))

    print("\n#### 14.3 Matched grain\n")
    print("| subject | N | sharp/tex at `k`=2.0, raw | `r`(sharp,grain) | "
          "lower root | upper root |")
    print("|---|---:|---:|---:|---|---|")
    for s in order:
        if s not in data:
            continue
        rows = data[s]
        w = rows["WHITE200"]
        ks = np.array([M.KV[a] for a in M.MEAS])
        gg = np.array([rows[a][1] / w[1] for a in M.MEAS])
        tt = np.array([rows[a][2] / w[2] for a in M.MEAS])
        rr = M.roots(ks, gg, tt, 1.0)
        pk = float(ks[int(np.argmax(gg))])
        lo = [x for x in rr if x[0] < pk]
        hi = [x for x in rr if x[0] >= pk]
        raw = rows["G200"][2] / w[2]
        av = [rows[a] for a in S.ARMS]
        rsg = np.corrcoef(np.array([x[1] for x in av]),
                          np.array([x[2] for x in av]))[0, 1]

        def cell(x):
            return ("`k`=%.3f, **%+.1f%%**" % (x[0], 100 * (x[1] - 1))) \
                if x else "none"
        print("| `%s` | %d | %+.1f%% | %+.3f | %s | %s |"
              % (s, S.bl.NFRAMES[s], 100 * (raw - 1), rsg,
                 cell(lo[0] if lo else None), cell(hi[0] if hi else None)))

    print("\n#### 14.4 The compensation formula\n")
    print("| subject | measured floor b0 (x white) | `k_pred` = 2.0/xw | "
          "`k_obs` | error | band-1 decoy error |")
    print("|---|---:|---:|---:|---:|---:|")
    for s in order:
        if s not in data:
            continue
        wavg, _ = read("WHITE200", s)
        ks, avgs, xw = [], [], None
        for arm, k in PKS:
            a, x = read(arm, s)
            if a is None:
                continue
            ks.append(k)
            avgs.append(a)
            xw = x if x is not None else xw
        ko = invert(ks, avgs, wavg)
        kp = 2.0 / xw
        b1 = data[s]["G200"]
        import re as _re
        t = open(os.path.join(S.AB, "G200", s + ".log"),
                 encoding="utf-8", errors="replace").read()
        xb1 = float(_re.search(r"x white\s*:\s*[\d.]+\s+([\d.]+)",
                               t).group(1))
        kd = 2.0 / xb1
        print("| `%s` | %.4f | %.3f | %.3f | %+.1f%% | %+.1f%% |"
              % (s, xw, kp, ko, 100 * (ko - kp) / kp, 100 * (ko - kd) / kd))
        _ = b1

    print("\n#### 14.5 The weight law\n")
    print("| subject | blotch | grain | sharp/tex | worst level, both arms | "
          "hard gate off everywhere? |")
    print("|---|---:|---:|---:|---:|---|")
    for s in order:
        if s not in data:
            continue
        r = M.softlaw(data[s], s)
        print("| `%s` | %+.2f%% | %+.2f%% | %+.2f%% | %.2f%% | %s |"
              % (s, 100 * r[0], 100 * r[1], 100 * r[2], max(r[3], r[4]),
                 "**yes**" if r[5] else "no, excluded"))

    print("\n#### 14.6 Runtime\n")
    print("| subject | N | white floor | measured floor | ratio |")
    print("|---|---:|---:|---:|---:|")
    rs = []
    for s in order:
        if s not in data:
            continue
        w, m = timing("WHITE200", s), timing("G200", s)
        rs.append(m[0] / w[0])
        print("| `%s` | %d | %.1f s | %.1f s | %.2fx |"
              % (s, S.bl.NFRAMES[s], w[0], m[0], rs[-1]))
    print("\nMedian **%.2fx**, range %.2f-%.2fx."
          % (float(np.median(rs)), min(rs), max(rs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
