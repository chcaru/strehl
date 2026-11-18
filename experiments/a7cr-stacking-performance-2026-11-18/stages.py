"""Summarise a trace.py timeline between marker lines of the stamped log.

  python stages.py <tag> [marker substring ...]

Without markers it uses the stage lines the render prints. For each interval
it prints wall seconds, average busy cores (user + kernel), kernel share,
bytes read by the process, bytes read from the drive, the device's mean and
peak utilisation and the private bytes at the end of the interval.
"""
import csv
import datetime
import os
import sys

# Outputs go to an ignored folder, never beside these tracked scripts.
HERE = os.environ.get('STREHL_PERF_OUT') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'outputs', 'a7cr-perf-2')
os.makedirs(HERE, exist_ok=True)
DEFAULT = ['folded          :', 'collapse+write  :', 'CA refinement   : measured', 'gpu fold        :', 'depth map       :',
           'reference tiles :', 'half-stacks     :', 'optical restore : ON (default for pixel-shift stacks) -- target',
           'wrote           :', 'total           :', 'alignment       :', 'decode ahead    :', 'frames          :']


def main():
    tag = sys.argv[1]
    markers = sys.argv[2:] or DEFAULT
    base = os.path.join(HERE, tag)
    rows = list(csv.DictReader(open(base + '.csv')))
    for r in rows:
        for k in r:
            if k != 'per_cpu':
                r[k] = float(r[k])
    gpu = []
    t_first = None
    for line in open(base + '.gpu.csv'):
        parts = [x.strip() for x in line.split(',')]
        if len(parts) < 5:
            continue
        try:
            ts = datetime.datetime.strptime(parts[0], '%Y/%m/%d %H:%M:%S.%f')
            gpu.append((ts, float(parts[1]), float(parts[3]), float(parts[4])))
        except ValueError:
            continue
    marks = [(0.0, 'start')]
    for line in open(base + '.log', encoding='utf-8'):
        t, _, text = line.partition('|')
        text = text.strip()
        if any(m in text for m in markers):
            marks.append((float(t), text[:70]))
    marks.append((rows[-1]['t'], 'exit'))
    # nvidia-smi started 0.3 s before the process; align its first sample at -0.3 s.
    g0 = gpu[0][0] if gpu else None

    def at(t):
        best = rows[0]
        for r in rows:
            if r['t'] <= t:
                best = r
            else:
                break
        return best

    print('%8s %7s %6s %5s %8s %8s %6s %6s %7s %7s  %s' % (
        't_end', 'wall', 'cores', 'kern%', 'readGB', 'diskGB', 'gpu%', 'gpuPk', 'privGB', 'devMiB', 'until'))
    for (ta, _), (tb, label) in zip(marks, marks[1:]):
        if tb - ta < 0.05:
            continue
        a, b = at(ta), at(tb)
        cpu = (b['user_s'] + b['kernel_s']) - (a['user_s'] + a['kernel_s'])
        kern = b['kernel_s'] - a['kernel_s']
        g = [x for x in gpu if ta - 0.3 <= (x[0] - g0).total_seconds() - 0.3 <= tb] if g0 else []
        print('%8.2f %7.2f %6.1f %5.0f %8.2f %8.2f %6.0f %6.0f %7.1f %7.0f  %s' % (
            tb, tb - ta, cpu / (tb - ta), 100.0 * kern / cpu if cpu > 0 else 0.0,
            (b['read_bytes'] - a['read_bytes']) / 2**30, (b['disk_read'] - a['disk_read']) / 2**30,
            sum(x[1] for x in g) / len(g) if g else -1, max((x[1] for x in g), default=-1),
            b['private'] / 2**30, max((x[2] for x in g), default=-1), label))


if __name__ == '__main__':
    main()
