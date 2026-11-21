"""Desktop measurements on long stacks through the control interface: reopen
time, UI-thread frame times while a reopen or a live render streams evidence,
and resident memory. A native window (`--gui`) on an isolated catalog copy and
output folder; capture folders are only read.

Frame times are the desktop's own `frame_performance` observations (CPU time
of `App::update` per egui frame, summed over repeated layout passes; not GPU
time or input-to-photon latency). Snapshots are taken through one-shot
`--control` clients every POLL seconds, so the window of 256 frames is merged
by frame number; the snapshots' own UI work is included in what they measure.

Usage:
  python -I p2-desktop-measure.py EXE OUT_DIR --catalog CATALOG reopen STACK_ID RUN_INDEX EXPECTED_MAPS [...]
  python -I p2-desktop-measure.py EXE OUT_DIR --catalog CATALOG render SOURCE
Prints one JSON object per measured action.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

CONTROL = Path(__file__).resolve().parents[2] / 'scripts' / 'strehl-control.py'
POLL = 0.25


class Desktop:
    def __init__(self, exe, out, catalog, source=None):
        self.exe, self.out = Path(exe), Path(out)
        self.out.mkdir(parents=True, exist_ok=False)
        self.session = self.out / 'ready.json'
        self.base = [sys.executable, '-I', str(CONTROL), '--exe', str(self.exe),
                     '--session-file', str(self.session), '--timeout', '120']
        command = self.base + ['launch', '--gui', '--catalog', str(catalog),
                               '--output-dir', str(self.out / 'results')]
        if source:
            command += ['--source', str(source)]
        (self.out / 'results').mkdir()
        launched = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
        self.pid = launched['data']['pid']
        self.process = psutil.Process(self.pid)
        self.frames = {}
        self.clock = []

    def snapshot(self):
        reply = subprocess.run(self.base + ['snapshot'], capture_output=True, text=True)
        if reply.returncode != 0:
            raise RuntimeError(reply.stdout + reply.stderr)
        data = json.loads(reply.stdout)['data']
        result = data['result']
        for frame, update, framework in result['frame_performance']['samples']:
            self.frames[int(frame)] = max(update, self.frames.get(int(frame), (0, 0))[0]), framework
        # When each frame happened, to the poll: the newest frame per snapshot.
        self.clock.append((time.perf_counter(), max(self.frames, default=-1), result['stage']))
        return data['revision'], result

    def call(self, command, revision):
        request = self.out / 'request.json'
        request.write_text(json.dumps({'expected_revision': revision, 'command': command}), encoding='utf-8')
        reply = subprocess.run(self.base + ['call', '--request', str(request)], capture_output=True, text=True)
        if reply.returncode != 0:
            raise RuntimeError(reply.stdout + reply.stderr)
        return json.loads(reply.stdout)

    def rss(self):
        return self.process.memory_info().rss

    def stage_of(self, frame):
        """The stage reported by the first snapshot that had seen `frame`."""
        return next((stage for _, newest, stage in self.clock if newest >= frame), None)

    def frames_after(self, first, last=None):
        rows = sorted((frame, value) for frame, value in self.frames.items()
                      if frame > first and (last is None or frame <= last))
        updates = sorted(value[0] for _, value in rows)
        if not updates:
            return dict(frames=0)
        pick = lambda q: updates[min(len(updates) - 1, int(q * (len(updates) - 1) + 0.5))]
        over = [(frame, round(value[0], 2), self.stage_of(frame)) for frame, value in rows if value[0] > 16.0]
        return dict(frames=len(updates), update_p50_ms=round(pick(0.5), 3),
                    update_p95_ms=round(pick(0.95), 3), update_max_ms=round(updates[-1], 3),
                    frames_over_16ms=len(over), worst=sorted(over, key=lambda r: -r[1])[:5])

    def shutdown(self):
        subprocess.run(self.base + ['shutdown'], capture_output=True, text=True)
        try:
            self.process.wait(timeout=30)
        except psutil.TimeoutExpired:
            # A native window may refuse an idle shutdown request: this
            # script started the process, so it ends it.
            self.process.terminate()
            self.process.wait(timeout=30)


def reopen(desktop, stack_id, run_index, expected):
    revision, state = desktop.snapshot()
    time.sleep(1.0)
    revision, state = desktop.snapshot()
    first = max(desktop.frames, default=-1)
    rss_before = desktop.rss()
    load = psutil.cpu_percent(interval=None)
    start = time.perf_counter()
    desktop.call({'operation': 'select_run', 'stack_id': stack_id, 'run_index': run_index}, revision)
    accepted = time.perf_counter() - start
    observed = photo = None
    trace = []
    while time.perf_counter() - start < 180:
        _, state = desktop.snapshot()
        now = time.perf_counter() - start
        maps = state['diagnostics']['admission_packets']
        opening = state['busy']['opening']
        trace.append((round(now, 3), opening, state['stage'], maps, state['photo_ready']))
        if observed is None and not opening and maps >= expected:
            observed = now
        if photo is None and state['photo_ready']:
            photo = now
        if observed is not None and photo is not None and now > max(observed, photo) + 2.0:
            break
        time.sleep(POLL)
    return dict(action='reopen', stack_id=stack_id, run_index=run_index, expected_maps=expected,
                maps=trace[-1][3], stage=trace[-1][2], accepted_s=round(accepted, 3),
                fully_observed_s=observed and round(observed, 3), photo_shown_s=photo and round(photo, 3),
                poll_s=POLL, rss_before_mib=round(rss_before / 2**20, 1), rss_after_mib=round(desktop.rss() / 2**20, 1),
                host_cpu_pct=load, ui=desktop.frames_after(first), trace=trace[:6] + trace[-2:])


def render(desktop):
    revision, state = desktop.snapshot()
    time.sleep(1.0)
    revision, state = desktop.snapshot()
    first = max(desktop.frames, default=-1)
    start = time.perf_counter()
    desktop.call({'operation': 'start_stack'}, revision)
    busy_seen, loads, trace = False, [], []
    while time.perf_counter() - start < 1800:
        _, state = desktop.snapshot()
        loads.append(psutil.cpu_percent(interval=None))
        busy = state['busy']['stack']
        busy_seen |= busy
        trace.append((round(time.perf_counter() - start, 1), state['stage'],
                      state['diagnostics']['admission_packets'], state['diagnostics'].get('evidence_maps')))
        if busy_seen and not busy:
            break
        time.sleep(POLL)
    # The frames while evidence streams: from the first snapshot in Merge.
    merge_first = next((newest for _, newest, stage in desktop.clock if stage == 'Merge'), None)
    by_stage = {}
    for frame, (update, _) in desktop.frames.items():
        if frame > first:
            stage = desktop.stage_of(frame)
            by_stage.setdefault(stage, []).append(update)
    stages = {stage: dict(frames=len(values), p95_ms=round(sorted(values)[int(0.95 * (len(values) - 1))], 3),
                          max_ms=round(max(values), 3), over_16ms=sum(v > 16.0 for v in values))
              for stage, values in by_stage.items()}
    return dict(action='render', seconds=round(time.perf_counter() - start, 1), stage=state['stage'],
                stages=stages, merge_first_frame=merge_first,
                maps=state['diagnostics']['admission_packets'], evidence_maps=state['diagnostics'].get('evidence_maps'),
                rss_after_mib=round(desktop.rss() / 2**20, 1), host_cpu_mean_pct=round(sum(loads) / len(loads), 1),
                ui=desktop.frames_after(first), trace=trace[::max(1, len(trace) // 12)] + trace[-1:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exe')
    parser.add_argument('out', type=Path)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('action', choices=['reopen', 'render'])
    parser.add_argument('args', nargs='*')
    args = parser.parse_args()
    source = args.args[0] if args.action == 'render' else None
    desktop = Desktop(args.exe, args.out, args.catalog, source)
    try:
        if args.action == 'reopen':
            values = [int(v) for v in args.args]
            for at in range(0, len(values), 3):
                print(json.dumps(reopen(desktop, *values[at:at + 3])), flush=True)
        else:
            time.sleep(5.0)
            print(json.dumps(render(desktop)), flush=True)
    finally:
        desktop.shutdown()


if __name__ == '__main__':
    main()
