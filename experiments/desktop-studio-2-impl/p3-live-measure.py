"""UI frame times while a live render streams evidence (P3, item 4).

A native window (`--agent`, never driven by Computer Use) on an isolated catalog,
output folder, capture settings (absent: the Pi is unreachable) and
LOCALAPPDATA / STREHL_CACHE_DIR inside OUT, so caches, warp maps, history and
the source-preview folder are scratch. The capture folder is only read.

Frame times are the desktop's own `frame_performance` samples (CPU time of
`App::update` per egui frame; not GPU time). Snapshots every POLL seconds are
merged by frame number; their own UI work is included. Derived from
`p2-desktop-measure.py` (render action), with the route selectable.

Usage:
  python -I p3-live-measure.py EXE OUT_DIR SOURCE [--route stack|engine] [--label NAME]
Prints one JSON object.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

CONTROL = Path(__file__).resolve().parents[2] / 'scripts' / 'strehl-control.py'
POLL = 0.25


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exe', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('--route', choices=['stack', 'engine'], default=None)
    parser.add_argument('--label', default='')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for name in ('appdata', 'cache', 'results'):
        (out / name).mkdir()
    env = dict(os.environ, LOCALAPPDATA=str(out / 'appdata'), STREHL_CACHE_DIR=str(out / 'cache'))
    pointer = out / 'ready.json'
    command = [str(args.exe.resolve()), '--agent', '--agent-session-out', str(pointer),
               '--source', str(args.source), '--output-dir', str(out / 'results'),
               '--catalog', str(out / 'catalog.projects.json'),
               '--capture-settings', str(out / 'capture-none.json')]
    if args.route:
        command += ['--route', args.route]
    with (out / 'desktop.log').open('ab') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, env=env)
    base = [sys.executable, '-I', str(CONTROL), '--exe', str(args.exe.resolve()),
            '--session-file', str(pointer), '--timeout', '120']
    frames, clock = {}, []

    def snapshot():
        reply = subprocess.run(base + ['snapshot'], capture_output=True, text=True)
        if reply.returncode != 0:
            raise RuntimeError(reply.stdout + reply.stderr)
        data = json.loads(reply.stdout)['data']
        result = data['result']
        for frame, update, framework in result['frame_performance']['samples']:
            frames[int(frame)] = max(update, frames.get(int(frame), (0, 0))[0]), framework
        clock.append((time.perf_counter(), max(frames, default=-1), result['stage']))
        return data['revision'], result

    def stage_of(frame):
        return next((stage for _, newest, stage in clock if newest >= frame), None)

    try:
        deadline = time.monotonic() + 120
        while not pointer.exists():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('the desktop did not publish its session')
            time.sleep(0.1)
        time.sleep(5.0)
        revision, state = snapshot()
        time.sleep(1.0)
        revision, state = snapshot()
        first = max(frames, default=-1)
        request = out / 'request.json'
        request.write_text(json.dumps({'expected_revision': revision,
                                       'command': {'operation': 'start_stack'}}), encoding='utf-8')
        start = time.perf_counter()
        reply = subprocess.run(base + ['call', '--request', str(request)], capture_output=True, text=True)
        if reply.returncode != 0:
            raise RuntimeError(reply.stdout + reply.stderr)
        busy_seen, loads, trace = False, [], []
        psutil.cpu_percent(interval=None)
        while time.perf_counter() - start < 1800:
            _, state = snapshot()
            loads.append(psutil.cpu_percent(interval=None))
            busy = state['busy']['stack']
            busy_seen |= busy
            trace.append((round(time.perf_counter() - start, 1), state['stage'],
                          state['diagnostics']['admission_packets']))
            if busy_seen and not busy:
                break
            time.sleep(POLL)
        # A few seconds of the finished view as well.
        settle = time.perf_counter()
        while time.perf_counter() - settle < 4.0:
            snapshot()
            time.sleep(POLL)
        by_stage = {}
        for frame, (update, _) in frames.items():
            if frame > first:
                by_stage.setdefault(stage_of(frame), []).append((frame, update))
        pick = lambda values, q: values[min(len(values) - 1, int(q * (len(values) - 1) + 0.5))]
        stages = {}
        for stage, rows in by_stage.items():
            values = sorted(update for _, update in rows)
            worst = sorted(rows, key=lambda row: -row[1])[:6]
            stages[str(stage)] = dict(frames=len(values), p50_ms=round(pick(values, 0.5), 3),
                                      p95_ms=round(pick(values, 0.95), 3), max_ms=round(values[-1], 3),
                                      over_16ms=sum(v > 16.0 for v in values),
                                      worst=[(frame, round(update, 2)) for frame, update in worst])
        print(json.dumps(dict(label=args.label, route=args.route or 'default',
                              seconds=round(time.perf_counter() - start, 1), stage=state['stage'],
                              stages=stages, maps=state['diagnostics']['admission_packets'],
                              host_cpu_mean_pct=round(sum(loads) / max(1, len(loads)), 1),
                              trace=trace[::max(1, len(trace) // 12)] + trace[-1:])), flush=True)
    finally:
        subprocess.run(base + ['shutdown'], capture_output=True, text=True)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            # This script started the process, so it ends it.
            process.terminate()
            process.wait(timeout=30)


if __name__ == '__main__':
    main()
