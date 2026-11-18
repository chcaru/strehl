"""Summarise the timers written by an instrumented scratch build (STREHL_TP_OUT).

  python tp.py <file.tp.csv> [--from T0 --to T1] [--by-thread NAME_SUBSTRING]

Per timer: count, total seconds, mean / median / p90 / max in ms. Times are
wall-clock seconds; --from/--to are offsets from the first event.
"""
import collections
import statistics
import sys


def load(path):
    ev = []
    for line in open(path, encoding='utf-8'):
        p = line.rstrip('\n').split(',', 5)
        if len(p) < 6:
            continue
        ev.append((p[0], float(p[1]), float(p[2]), p[3], int(p[4]), p[5]))
    return ev


def main():
    args = sys.argv[1:]
    path = args[0]
    lo, hi, thread = None, None, None
    if '--from' in args:
        lo = float(args[args.index('--from') + 1])
    if '--to' in args:
        hi = float(args[args.index('--to') + 1])
    if '--by-thread' in args:
        thread = args[args.index('--by-thread') + 1]
    ev = load(path)
    t0 = min(e[1] for e in ev)
    rows = collections.defaultdict(list)
    for crate, start, dur, name, arg, th in ev:
        t = start - t0
        if lo is not None and t < lo:
            continue
        if hi is not None and t > hi:
            continue
        if thread is not None and thread not in th:
            continue
        rows[name].append(dur)
    print('%-28s %6s %9s %8s %8s %8s %8s' % ('timer', 'n', 'total s', 'mean ms', 'p50 ms', 'p90 ms', 'max ms'))
    for name in sorted(rows, key=lambda n: -sum(rows[n])):
        d = sorted(rows[name])
        n = len(d)
        print('%-28s %6d %9.2f %8.2f %8.2f %8.2f %8.2f' % (
            name, n, sum(d), 1e3 * sum(d) / n, 1e3 * statistics.median(d), 1e3 * d[min(n - 1, int(0.9 * n))], 1e3 * d[-1]))


if __name__ == '__main__':
    main()
