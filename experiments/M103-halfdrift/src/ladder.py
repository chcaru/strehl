"""M103 E1 -- decompose the half-drift defect: estimator or solver?

Reads the per-edge CSV written by `probe/` and answers, by arithmetic alone:

  * what each span's edges say the end-to-end log-scale is (the telescoping
    ladder -- AGENTS rule 6's conservation identity, per span);
  * how many edges each span loses, and to which refusal;
  * what the DIRECT long edges say, which is the only measurement in the set
    that carries the end-to-end scale without composing anything.

Truth for `bee-3-cpl` is 0.85714 (M97 signtest RAW arm, and the orchestrator's
independent 0.85715 with no strehl code in it).
"""

import math
import sys
from collections import defaultdict


def load(path):
    edges = {}
    refused = []
    n = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or line.startswith("i,j,"):
                continue
            f = line.rstrip("\n").split(",")
            if len(f) < 4:
                continue
            i, j, span, status = int(f[0]), int(f[1]), int(f[2]), f[3]
            n = max(n, j + 1)
            if status != "OK":
                refused.append((i, j, span, status))
                continue
            a = complex(float(f[4]), float(f[5]))
            b = complex(float(f[6]), float(f[7]))
            edges[(i, j)] = dict(
                a=a, b=b, span=span, used=int(f[8]), total=int(f[9]),
                raw_n=int(f[10]), rms=float(f[11]), lever=float(f[12]),
                peak=float(f[13]), low_contrast=int(f[14]), low_peak=int(f[15]),
                border=int(f[16]), oob=int(f[17]), outlier=int(f[18]),
            )
    return edges, refused, n


def main(path, truth=0.85714):
    edges, refused, n = load(path)
    L_true = math.log(truth)
    print(f"file      : {path}")
    print(f"frames    : {n}")
    print(f"edges OK  : {len(edges)}   refused: {len(refused)}")
    print(f"truth     : scale {truth:.5f}  ln {L_true:+.6f}  over {n - 1} frames")
    print()

    by_span = defaultdict(list)
    for (i, j), e in edges.items():
        by_span[e["span"]].append(e)
    ref_by_span = defaultdict(list)
    for i, j, s, st in refused:
        ref_by_span[s].append(st)

    print("=== per-span census and telescoped end-to-end log-scale ===")
    print(f"{'span':>5} {'ok':>5} {'ref':>5} {'used/tile':>10} {'peak':>7} "
          f"{'border':>7} {'lowpk':>6} {'mean ln|a|':>12} {'x(n-1)/s':>11} "
          f"{'recovery':>9}")
    rows = {}
    for s in sorted(by_span):
        es = by_span[s]
        lna = [math.log(abs(e["a"])) for e in es]
        mean_ln = sum(lna) / len(lna)
        # Telescoping estimate of the end-to-end log-scale: the mean per-edge
        # log-scale scaled by how many span-s hops cover the bracket.
        extrap = mean_ln * (n - 1) / s
        used = sum(e["used"] for e in es) / len(es)
        total = es[0]["total"]
        peak = sum(e["peak"] for e in es) / len(es)
        border = sum(e["border"] for e in es) / len(es)
        lowpk = sum(e["low_peak"] for e in es) / len(es)
        rec = extrap / L_true
        rows[s] = dict(mean_ln=mean_ln, extrap=extrap, rec=rec, nok=len(es),
                       nref=len(ref_by_span.get(s, [])), used=used, peak=peak)
        print(f"{s:>5} {len(es):>5} {len(ref_by_span.get(s, [])):>5} "
              f"{used:>6.1f}/{total:<3} {peak:>7.4f} {border:>7.1f} {lowpk:>6.1f} "
              f"{mean_ln:>+12.6f} {extrap:>+11.6f} {rec:>9.4f}")
    print()

    # An honest chained telescope for each span: actually walk 0 -> n-1 in
    # hops of s, using the edges that exist, so the "mean x count" shortcut
    # above cannot hide a coverage hole.
    print("=== walked chains (0 -> last, hops of span s) ===")
    print(f"{'span':>5} {'hops':>5} {'missing':>8} {'sum ln|a|':>12} {'scale':>9} {'recovery':>9}")
    for s in sorted(by_span):
        tot, hops, missing = 0.0, 0, 0
        k = 0
        while k + s <= n - 1:
            e = edges.get((k, k + s))
            if e is None:
                missing += 1
            else:
                tot += math.log(abs(e["a"]))
                hops += 1
            k += s
        # tail
        if k < n - 1:
            e = edges.get((k, n - 1))
            if e is not None:
                tot += math.log(abs(e["a"]))
                hops += 1
            else:
                missing += 1
        print(f"{s:>5} {hops:>5} {missing:>8} {tot:>+12.6f} {math.exp(tot):>9.5f} "
              f"{tot / L_true:>9.4f}")
    print()

    print("=== direct long edges from frame 0 (no composition at all) ===")
    print(f"{'j':>5} {'ln|a|':>12} {'scale':>9} {'used':>5} {'peak':>7} "
          f"{'per-frame':>11} {'x(n-1)':>10} {'recovery':>9}")
    for (i, j), e in sorted(edges.items()):
        if i != 0 or e["span"] < 32:
            continue
        l = math.log(abs(e["a"]))
        print(f"{j:>5} {l:>+12.6f} {abs(e['a']):>9.5f} {e['used']:>5} "
              f"{e['peak']:>7.4f} {l / e['span']:>+11.7f} "
              f"{l / e['span'] * (n - 1):>+10.6f} {l / e['span'] * (n - 1) / L_true:>9.4f}")
    print()
    if (0, n - 1) in edges:
        e = edges[(0, n - 1)]
        print(f"THE end-to-end edge (0,{n - 1}): |a| = {abs(e['a']):.6f}, "
              f"used {e['used']}/{e['total']}, peak {e['peak']:.4f}, "
              f"recovery {math.log(abs(e['a'])) / L_true:.4f}")
    else:
        r = [x for x in refused if x[0] == 0 and x[1] == n - 1]
        print(f"THE end-to-end edge (0,{n - 1}) was REFUSED: {r}")

    print()
    print("=== refusal reasons ===")
    reasons = defaultdict(int)
    for _, _, s, st in refused:
        reasons[(s, st)] += 1
    for (s, st), c in sorted(reasons.items()):
        print(f"  span {s:>4}  {st:<48} x{c}")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.85714)
