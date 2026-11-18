"""Per-thread means of chosen timers, and a rate timeline of the fold.

  python tp-threads.py <file.tp.csv> T0 T1 name [name ...]

For each thread: count and mean ms of each named timer between offsets T0 and
T1 (seconds from the first event). Then planes folded per second in 2 s bins
(from fold.add_staged events).
"""
import collections
import sys


def main():
    path, lo, hi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    names = sys.argv[4:]
    ev = []
    for line in open(path, encoding='utf-8'):
        p = line.rstrip('\n').split(',', 5)
        if len(p) == 6:
            ev.append((float(p[1]), float(p[2]), p[3], p[5]))
    t0 = min(e[0] for e in ev)
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    for start, dur, name, th in ev:
        if name in names and lo <= start - t0 <= hi:
            per[th][name].append(dur)
    print('%-14s' % 'thread' + ''.join('  %22s' % n for n in names))

    def key(t):
        digits = ''.join(c for c in t if c.isdigit())
        return (t.rstrip('0123456789'), int(digits) if digits else 0)

    for th in sorted(per, key=key):
        print('%-14s' % (th or '(unnamed)') + ''.join(
            '  %6d x %10.1f ms' % (len(per[th][n]), 1e3 * sum(per[th][n]) / max(1, len(per[th][n]))) for n in names))
    adds = sorted(start - t0 for start, dur, name, th in ev if name == 'fold.add_staged')
    if adds:
        print('\nplanes folded per second, 2 s bins:')
        b = collections.Counter(int(a // 2) for a in adds)
        print(' '.join('%d-%ds:%.1f' % (2 * k, 2 * k + 2, b[k] / 2.0) for k in sorted(b)))


if __name__ == '__main__':
    main()
