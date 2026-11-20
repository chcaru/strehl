"""Per-run capture cadence from the recorded journals (read-only).

  python capture-cadence.py [D:/StrehlCaptures]

For every run with a capture journal: when it ran, how many groups, the
controller's `capture()` time, the gap between the third and fourth RAW of a
four-shot group, and the plane period. Once the camera has finished exposing,
that gap is one RAW's download from the camera to the Pi, so 125.7 MB divided
by it is the link's rate; while the camera is still exposing it is the
camera's own cadence (shutter + about 0.55 s) and only bounds the rate from
below.
"""
import json
import os
import statistics as st
import sys
import time

root = sys.argv[1] if len(sys.argv) > 1 else 'D:/StrehlCaptures'
for run in sorted(os.listdir(root)):
    path = os.path.join(root, run, 'events.jsonl')
    if not os.path.isfile(path):
        continue
    try:
        events = [json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]
    except ValueError:
        continue
    captures = [e for e in events if e.get('event') == 'capture_buffered']
    if not captures:
        continue
    gaps, totals, singles, size = [], [], [], 0
    for c in captures:
        reply = c['data']['response'].get('camera_reply') or {}
        files = reply.get('files') or []
        if len(files) >= 4:
            gaps.append(files[3]['seconds'] - files[2]['seconds'])
            totals.append(reply.get('seconds'))
            size = files[3]['bytes']
        elif len(files) == 1:
            singles.append((files[0]['seconds'], files[0]['bytes']))
    intents = [e['unix_ms'] for e in events if e.get('event') == 'capture_intent']
    period = st.median([b - a for a, b in zip(intents, intents[1:])]) / 1000 if len(intents) > 2 else float('nan')
    when = time.strftime('%m-%d %H:%M', time.localtime(captures[0]['unix_ms'] / 1000))
    if gaps:
        gap = st.median(gaps)
        print('%s %-28s four-shot groups=%3d  capture()=%5.2f s  RAW 3->4 gap=%.2f s (>= %3.0f MB/s)  plane period=%.1f s'
              % (when, run, len(gaps), st.median(totals), gap, size / 1e6 / gap, period))
    elif singles:
        print('%s %-28s single    shots=%3d  capture()=%5.2f s  period=%.1f s'
              % (when, run, len(singles), st.median([s for s, _ in singles]), period))
