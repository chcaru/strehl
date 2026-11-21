"""Run one desktop-shaped render arm with focus evidence off, on or placebo,
and record what P8's E5 measurement needs: output hashes, wall and stage
times, peak memory over the whole run and during the focus pass, the
evidence file, and host load.

Mirrors `p2-evidence-run.py` (the desktop's `stack SRC --merge pyramid --srgb
--out DIR/result.partial.tiff --linear-master DIR/master.partial.tiff`, every
inherited STREHL_* removed, STREHL_UI_PROGRESS=1, STREHL_TEMPORAL_ENERGY=off,
an isolated STREHL_CACHE_DIR) and adds STREHL_FOCUS_EVIDENCE. The engine runs
at below-normal priority. The capture folder is only read; outputs go to a
fresh folder outside it, and the TIFFs are deleted after hashing unless
--keep.

Usage: python -I p8-focus-evidence-run.py ENGINE SOURCE OUT_DIR
       --focus {off,on,placebo} --gpu {auto,on,off} --cache CACHE_DIR [--keep]
Prints one JSON line.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import psutil

FOCUS_LINE = b'focus evidence  :'


def digest(path):
    if not path.exists():
        return None
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('engine', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--focus', choices=['off', 'on', 'placebo'], required=True)
    parser.add_argument('--gpu', choices=['auto', 'on', 'off'], required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--keep', action='store_true')
    parser.add_argument('--env', action='append', default=[])
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    assert source.is_dir() and not out.is_relative_to(source)
    out.mkdir(parents=True, exist_ok=False)
    partial = out / 'result.partial.tiff'
    master = out / 'master.partial.tiff'
    command = [str(args.engine), 'stack', str(source), '--merge', 'pyramid', '--srgb',
               '--out', str(partial), '--linear-master', str(master)]
    if args.limit:
        command.append(f'--limit={args.limit}')
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith('STREHL_') and k.upper() != 'RAYON_NUM_THREADS'}
    env.update(STREHL_UI_PROGRESS='1', STREHL_GPU_FOLD=args.gpu, STREHL_TEMPORAL_ENERGY='off',
               STREHL_CACHE_DIR=str(args.cache.resolve()), STREHL_FOCUS_EVIDENCE=args.focus)
    env.update(item.split('=', 1) for item in args.env)
    log = out / 'render.log'
    psutil.cpu_percent(interval=None)
    load_before = psutil.cpu_percent(interval=1.0)
    available_before = psutil.virtual_memory().available
    started = time.perf_counter()
    samples = []
    focus_started = None
    peak = dict(wset=0, private=0)
    peak_before_focus = dict(wset=0, private=0)
    peak_focus = dict(wset=0, private=0)
    with log.open('xb') as stream:
        child = subprocess.Popen(command, env=env, cwd=out, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT,
                                 creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        own = psutil.Process(child.pid)
        read_at = 0
        while child.poll() is None:
            try:
                info = own.memory_info()
                total = psutil.cpu_percent(interval=None)
                mine = own.cpu_percent(interval=None) / psutil.cpu_count()
            except psutil.NoSuchProcess:
                break
            now = time.perf_counter() - started
            if focus_started is None:
                with log.open('rb') as reader:
                    reader.seek(read_at)
                    chunk = reader.read()
                if FOCUS_LINE in chunk:
                    focus_started = now
                read_at += max(0, len(chunk) - len(FOCUS_LINE))
            target = peak_focus if focus_started is not None else peak_before_focus
            target['wset'] = max(target['wset'], info.wset)
            target['private'] = max(target['private'], info.private)
            peak['wset'] = max(peak['wset'], info.peak_wset)
            peak['private'] = max(peak['private'], info.peak_pagefile)
            samples.append((now, total, mine, info.wset))
            time.sleep(0.5)
        child.wait()
    wall = time.perf_counter() - started
    assert child.returncode == 0, f'engine exited {child.returncode}: {log}'
    text = log.read_text(encoding='utf-8', errors='replace')
    evidence = out / 'evidence.strehl'
    others = [max(0.0, total - mine) for _, total, mine, _ in samples]
    gib = lambda n: round(n / 2**30, 3)
    record = dict(
        engine=str(args.engine), engine_sha256=digest(args.engine), source=str(source),
        focus=args.focus, gpu=args.gpu, limit=args.limit, extra_env=args.env, command=command,
        wall_s=round(wall, 1),
        total_line=re.findall(r'^total\s*:\s*([0-9.]+) s', text, re.M),
        folded=re.findall(r'^folded\s*:\s*(.*)$', text, re.M),
        gpu_fold=re.findall(r'^gpu fold\s*:\s*(.*)$', text, re.M),
        focus_lines=re.findall(r'^focus evidence  :\s*(.*)$', text, re.M),
        focus_started_s=round(focus_started, 1) if focus_started is not None else None,
        result_sha256=digest(partial), master_sha256=digest(master),
        evidence_bytes=evidence.stat().st_size if evidence.exists() else None,
        evidence_sha256=digest(evidence),
        peak_wset_gib=gib(peak['wset']), peak_private_gib=gib(peak['private']),
        peak_wset_before_focus_gib=gib(peak_before_focus['wset']),
        peak_wset_focus_gib=gib(peak_focus['wset']),
        peak_private_focus_gib=gib(peak_focus['private']),
        memory_sampling='psutil every ~0.5 s; peak_* from the OS counters (peak_wset, peak_pagefile)',
        host_available_before_gib=gib(available_before),
        host_load_before_pct=load_before,
        host_load_other_mean_pct=round(sum(others) / len(others), 1) if others else None,
        host_load_other_max_pct=round(max(others), 1) if others else None,
    )
    if not args.keep:
        for path in (partial, master):
            if path.exists():
                path.unlink()
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
