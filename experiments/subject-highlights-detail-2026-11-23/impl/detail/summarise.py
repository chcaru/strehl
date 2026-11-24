"""The gate's log lines and byte checks, per capture and arm (shd-d-detail).

  python summarise.py <out root> <capture name> [...]

Per arm: the build (run.json's engine SHA-256), the restoration's Detail line and per-channel
noise cost and amplitude gain, the highlight guard's share, whether the alignment and group
measurements came from the cache, and the tone lines. Then the byte checks: each arm pair named
in PAIRS compared by the SHA-256 of photograph and master; and for `subj` against `safe`, the
master's pixels (the description differs: it records the tone).
"""
import json
import pathlib
import re
import sys

import numpy as np
import tifffile

root, names = pathlib.Path(sys.argv[1]), sys.argv[2:]
ARMS = ['base', 'off', 'newoff', 'natural', 'safe', 'safe2', 'crisp', 'subj', 'subjoff']
PAIRS = [('off', 'newoff', 'unrestored: base binary vs this one'),
         ('safe', 'safe2', 'default vs STREHL_DETAIL=safe (a re-render)'),
         ('safe', 'subjoff', 'default vs --subject off')]
for name in names:
    print('=' * 100)
    print(name)
    runs = {}
    for arm in ARMS:
        d = root / arm / name
        if not (d / 'run.json').exists():
            continue
        run = json.loads((d / 'run.json').read_text())
        runs[arm] = run
        log = (d / 'render.log').read_text(encoding='utf-8', errors='replace')
        # run.json 'args' is the command after `strehl stack`: the capture and the desktop's
        # seven fixed arguments, then the arm's own flags.
        flags = ' '.join(run.get('args', [])[8:]) or '-'
        print('-- %s: exit %d, engine %s, flags %s, env %s' % (
            arm, run['exit'], run['exe_sha256'][:12], flags, run.get('extra_env', {})))
        for pat in (r'^detail\s+: .*', r'^\s+[RGB]: noise power in .*', r'highlight guard covers [^;]*',
                    r'^STREHL_UI_PROGRESS event=align-result .*', r'^group journal .*', r'^tone subject .*',
                    r'^tone\s+: .*'):
            seen = set()
            for m in re.finditer(pat, log, re.M):
                s = m.group(0).strip()
                if s not in seen:
                    seen.add(s)
                    print('   ' + s)
        g = re.search(r'target Gaussian sigma ([0-9.]+) px', log)
        if g:
            print('   target sigma %s px' % g.group(1))
    for a, b, what in PAIRS:
        if a in runs and b in runs:
            same = all(runs[a].get(f) == runs[b].get(f) for f in ('result.tiff', 'master.tiff'))
            print('BYTES %-8s vs %-8s (%s): photograph and master %s' % (a, b, what, 'IDENTICAL' if same else 'DIFFER'))
    if 'safe' in runs and 'subj' in runs:
        x = tifffile.imread(root / 'safe' / name / 'master.tiff')
        y = tifffile.imread(root / 'subj' / name / 'master.tiff')
        print('PIXELS safe vs subj master: %s (the description records the tone)' % (
            'IDENTICAL' if np.array_equal(x.view(np.uint32), y.view(np.uint32)) else 'DIFFER'))
