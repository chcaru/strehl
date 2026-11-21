"""Two charts for the owner: noise against plane time (exposure), detail against the focus
step (its noise measure is confounded on these subjects: see step-curve-*.txt). Reads the evidence JSON written by exposure-analyse.py and
step-curve-analyse.py; plane periods from the paired runs' capture events.
  python make-charts.py <evidence dir> <runs.json> <out dir>"""
import json
import pathlib
import statistics as st
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

ev, runs_json, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
S1, S2 = '#2a78d6', '#eb6834'
plt.rcParams.update({'font.size': 11, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2,
                     'ytick.color': INK2, 'text.color': INK, 'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE})


def style(ax):
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)


def short(t):
    return '%.1f s' % t if t >= 0.3 else '1/%d s' % round(1 / t)


# 1. exposure
data = json.loads((ev / 'exposure-quality.json').read_text())
rows = [r for r in json.loads(runs_json.read_text()) if r['shots'] == 4]


def period(folder):
    t = [json.loads(l)['unix_ms'] for l in open(pathlib.Path(folder) / 'events.jsonl', encoding='utf-8') if '"capture_intent"' in l]
    return st.median([(b - a) / 1000 for a, b in zip(t, t[1:])])


pts = []
for r in rows:
    name = short(r['seconds']) + ' ISO %d' % r['iso']
    p = st.median([period(f) for f in r['runs']])
    pts.append((name, r['seconds'], p, data['final'][name][1], data['raw'][name][4]))
f0, r0 = pts[0][3], pts[0][4]
fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
style(ax)
x = [p[2] for p in pts]
ax.plot(x, [p[3] / f0 for p in pts], '-o', color=S1, lw=2, ms=8, mec=SURFACE, mew=2, label='final stacked image')
ax.plot(x, [p[4] / r0 for p in pts], '--o', color=S2, lw=2, ms=8, mec=SURFACE, mew=2, label='one RAW')
for name, t, p, f, r in pts:
    if t >= 0.3:
        ax.annotate(name, (p, f / f0), textcoords='offset points', xytext=(-10, 8), ha='right', fontsize=9, color=INK2)
    else:
        ax.annotate(name, (p, f / f0), textcoords='offset points', xytext=(12, -4), ha='left', va='center', fontsize=9, color=INK2)
ax.set_xlabel('time per four-shot plane (s)')
ax.set_ylabel('signal-to-noise, relative to 0.6 s ISO 100')
ax.set_ylim(0, 1.1)
ax.set_title('Shorter exposure: noise rises, the plane barely gets faster', loc='left', fontsize=12)
ax.legend(frameon=False, loc='lower right')
fig.text(0.01, 0.01, 'Rig, pencil + printed part, f/5.6, ISO raised to keep brightness; mid-tones; MEASURED 2026-11-20', fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(out / 'exposure-noise-vs-time.png')

# 2. focus step
stacks = [('scarab, four-shot', 'step-curve-scarab4.json', S1), ('dark background, four-shot', 'step-curve-dark4.json', S2)]
fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
style(ax)
for label, fn, colour in stacks:
    d = json.loads((ev / fn).read_text())
    xs = [r['step'] / d['width'] for r in d['rows']]
    ys = [r['scales']['1.5']['p10'] for r in d['rows']]
    ax.plot(xs, ys, '-o', color=colour, lw=2, ms=8, mec=SURFACE, mew=2, label='%s (sharp width %d)' % (label, d['width']))
    for r, xv, yv in zip(d['rows'], xs, ys):
        ax.annotate(str(r['step']), (xv, yv), textcoords='offset points', xytext=(5, -14), fontsize=8, color=INK2)
ax.axvline(1 / 7, color=INK2, lw=1, ls=':')
ax.annotate('suggested now\n(width / 7)', (1 / 7, 0.80), textcoords='offset points', xytext=(4, 0), fontsize=8, color=INK2)
ax.set_ylim(0.78, 1.01)
ax.set_title('Coarser focus steps: no loss until about a fifth of the sharp width', loc='left', fontsize=12)
ax.set_ylabel('fine detail at the worst 10 % of points\n(relative to using every plane)')
ax.set_xlabel('focus step / sharp width   (stack time is proportional to 1 / step)')
ax.legend(frameon=False, loc='upper right')
fig.text(0.01, 0.01, 'Renders from every k-th plane of stacks captured at step 8; point labels: step in focus units; MEASURED 2026-11-20', fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(out / 'focus-step-detail.png')
print('written', out)
