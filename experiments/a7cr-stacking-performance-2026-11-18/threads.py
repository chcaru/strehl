"""CPU seconds per thread role and stage, from trace.py --threads.

  python threads.py <tag> [t_split ...]

Threads are grouped by name with digits removed; unnamed threads are grouped
by how much CPU they used (so a pool of similar workers shows as one row).
The optional split times cut the run into intervals.
"""
import collections
import csv
import os
import re
import sys

# Outputs go to an ignored folder, never beside these tracked scripts.
HERE = os.environ.get('STREHL_PERF_OUT') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'outputs', 'a7cr-perf-2')
os.makedirs(HERE, exist_ok=True)


def main():
    tag = sys.argv[1]
    splits = [float(x) for x in sys.argv[2:]]
    rows = list(csv.DictReader(open(os.path.join(HERE, tag + '.threads.csv'), encoding='utf-8')))
    per = collections.defaultdict(list)
    for r in rows:
        per[int(r['tid'])].append((float(r['t']), r['name'], float(r['user_s']), float(r['kernel_s'])))
    end = max(float(r['t']) for r in rows)
    cuts = [0.0] + splits + [end + 1.0]
    names = {}
    for tid, s in per.items():
        name = next((x[1] for x in reversed(s) if x[1]), '')
        names[tid] = re.sub(r'\d+', '#', name) if name else '(unnamed)'
    table = collections.defaultdict(lambda: [[0.0, 0.0] for _ in cuts[1:]])
    count = collections.Counter()
    for tid, s in per.items():
        count[names[tid]] += 1
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            inside = [x for x in s if a <= x[0] < b]
            if not inside:
                continue
            before = [x for x in s if x[0] < a]
            u0, k0 = (before[-1][2], before[-1][3]) if before else (0.0, 0.0)
            table[names[tid]][i][0] += inside[-1][2] - u0
            table[names[tid]][i][1] += inside[-1][3] - k0
    head = '%-34s %4s' % ('thread role', 'n') + ''.join('  %14s' % ('%.0f-%.0f s u/k' % (a, min(b, end))) for a, b in zip(cuts, cuts[1:]))
    print(head)
    order = sorted(table, key=lambda n: -sum(x[0] + x[1] for x in table[n]))
    for n in order:
        if sum(x[0] + x[1] for x in table[n]) < 0.3:
            continue
        print('%-34s %4d' % (n[:34], count[n]) + ''.join('  %6.1f /%6.1f' % (x[0], x[1]) for x in table[n]))
    tot = [[sum(table[n][i][0] for n in table), sum(table[n][i][1] for n in table)] for i in range(len(cuts) - 1)]
    print('%-34s %4d' % ('TOTAL', sum(count.values())) + ''.join('  %6.1f /%6.1f' % (x[0], x[1]) for x in tot))


if __name__ == '__main__':
    main()
