"""Run one desktop-shaped render arm and record what P2's acceptance needs.

Mirrors the desktop's engine command (`jobs.rs` `render_command` with the
default settings and a retained master) and environment (every inherited
STREHL_* removed; STREHL_UI_PROGRESS, STREHL_GPU_FOLD, STREHL_TEMPORAL_ENERGY
and an isolated STREHL_CACHE_DIR set). Outputs go to a fresh folder outside
the capture, which is only read. Prints one JSON line per arm.

Usage: python -I p2-evidence-run.py ENGINE SOURCE OUT_DIR --progress {0,1,placebo}
       --gpu {auto,on,off} --cache CACHE_DIR [--limit N]
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
    parser.add_argument('--progress', choices=['0', '1', 'placebo'], required=True)
    parser.add_argument('--gpu', choices=['auto', 'on', 'off'], required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--env', action='append', default=[],
                        help='Extra KEY=VALUE for diagnostics (STREHL_FOLD_TRACE, STREHL_GPU_PROFILE)')
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
    env.update(STREHL_UI_PROGRESS=args.progress, STREHL_GPU_FOLD=args.gpu,
               STREHL_TEMPORAL_ENERGY='off', STREHL_CACHE_DIR=str(args.cache.resolve()))
    env.update(item.split('=', 1) for item in args.env)
    log = out / 'render.log'
    psutil.cpu_percent(interval=None)
    load_before = psutil.cpu_percent(interval=1.0)
    started = time.perf_counter()
    samples = []
    with log.open('xb') as stream:
        child = subprocess.Popen(command, env=env, cwd=out, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT)
        own = psutil.Process(child.pid)
        while child.poll() is None:
            try:
                total = psutil.cpu_percent(interval=2.0)
                mine = own.cpu_percent(interval=None) / psutil.cpu_count()
                samples.append((total, mine))
            except psutil.NoSuchProcess:
                break
        child.wait()
    wall = time.perf_counter() - started
    assert child.returncode == 0, f'engine exited {child.returncode}: {log}'
    text = log.read_text(encoding='utf-8', errors='replace')
    folded = re.findall(r'^folded\s*:\s*(\d+) / (\d+) frames in ([0-9.]+) s', text, re.M)
    gpu_line = re.findall(r'^gpu fold\s*:\s*(.*)$', text, re.M)
    kinds = {}
    for match in re.finditer(r'event=diagnostic .*?kind=(\S+) scope=(\S+)', text):
        key = f'{match.group(1)}/{match.group(2)}'
        kinds[key] = kinds.get(key, 0) + 1
    evidence = out / 'evidence.strehl'
    others = [max(0.0, total - mine) for total, mine in samples]
    record = dict(
        engine=str(args.engine), engine_sha256=digest(args.engine), source=str(source),
        extra_env=args.env,
        out=str(out), progress=args.progress, gpu=args.gpu, limit=args.limit,
        command=command, wall_s=round(wall, 1),
        folded=[dict(folded=int(a), frames=int(b), seconds=float(c)) for a, b, c in folded],
        gpu_fold=gpu_line, result_sha256=digest(partial), master_sha256=digest(master),
        result_bytes=partial.stat().st_size, log_bytes=log.stat().st_size,
        diagnostic_lines=kinds,
        evidence_line=re.findall(r'^STREHL_UI_PROGRESS event=evidence-file .*$', text, re.M),
        unplaced_lines=len(re.findall(r'event=frame-unplaced ', text)),
        evidence_bytes=evidence.stat().st_size if evidence.exists() else None,
        evidence_sha256=digest(evidence),
        host_load_before_pct=load_before,
        host_load_other_mean_pct=round(sum(others) / len(others), 1) if others else None,
        host_load_other_max_pct=round(max(others), 1) if others else None,
    )
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
