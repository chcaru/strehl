"""Verify the standalone CLI and bundled desktop worker on the same RAW bracket.

Rejecting inputs: a worker which opens a window instead of parsing its arguments;
a routing mode that loses actual alignment/frame events; any differing TIFF byte
between executables or between disabled, enabled and placebo observation. The
existing observer verifier commissions its own dropped-event controls first.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time


def source_inventory(root, digest):
    """Include hidden files and bytes, not just directory totals or mtimes."""
    return {str(path.relative_to(root)): dict(bytes=path.stat().st_size,
                                            sha256=digest(path))
            for path in sorted(root.rglob('*')) if path.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--ui', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--binned', action='store_true')
    args = parser.parse_args()
    if not 3 <= args.limit <= 256 or not 1 <= args.workers <= 1024:
        parser.error('Use 3–256 inputs and 1–1024 workers')
    cli, ui, source, out = (path.resolve() for path in
                            [args.cli, args.ui, args.source, args.out])
    assert cli.is_file() and ui.is_file() and source.is_dir()
    assert not out.is_relative_to(source), 'Write only outside the RAW source'
    out.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location(
        'progress_proof', Path(__file__).with_name('verify-ui-progress.py'))
    proof = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(proof)
    original_inputs = source_inventory(source, proof.digest)
    assert original_inputs, 'The RAW source is empty'
    result = dict(schema=1, source=str(source), limit=args.limit, workers=args.workers,
                  binned=args.binned, cli=str(cli), ui=str(ui),
                  cli_sha256=proof.digest(cli), ui_sha256=proof.digest(ui),
                  controls=dict(alignment=proof.commission_alignment_verifier(),
                                merge=proof.commission_merge_verifier()),
                  source_inventory=original_inputs, runs=[])
    environment = {k: v for k, v in os.environ.items()
                   if not k.upper().startswith('STREHL_') and k.upper() != 'RAYON_NUM_THREADS'}
    environment.update(RAYON_NUM_THREADS=str(args.workers),
                       STREHL_PYRAMID_WORKERS=str(args.workers))
    for name, prefix in [('cli', [str(cli)]), ('bundled', [str(ui), '--engine-worker'])]:
        version = subprocess.run(prefix + ['--version'], env=environment,
                                 capture_output=True, text=True, timeout=20)
        assert version.returncode == 0 and version.stdout.startswith('strehl ')
        result[name + '_version'] = version.stdout.strip()
        invalid = subprocess.run(prefix + ['--not-a-strehl-option'], env=environment,
                                 capture_output=True, text=True, timeout=20)
        assert invalid.returncode == 2 and 'unexpected argument' in invalid.stderr
        result[name + '_invalid_argument_rejected'] = True
        for observer, enabled in [('off', '0'), ('on', '1'), ('placebo', 'placebo')]:
            arm = name + '-' + observer
            image, log = out / (arm + '.tiff'), out / (arm + '.log')
            command = prefix + ['stack', str(source), '--limit', str(args.limit),
                                '--merge', 'pyramid', '--srgb', '--pyramid-gate', '2',
                                '--pyramid-bands', '7', '--pyramid-exponent', '2',
                                '--pyramid-sharpen', '1.4', '--resampler', 'catmull-rom',
                                '--out', str(image)]
            if args.binned:
                command.append('--binned')
            arm_env = dict(environment, STREHL_UI_PROGRESS=enabled,
                           STREHL_CACHE_DIR=str(out / ('cache-' + arm)))
            assert not Path(arm_env['STREHL_CACHE_DIR']).exists(), 'Cache must start cold'
            started = time.monotonic()
            with log.open('xb') as stream:
                completed = subprocess.run(command, env=arm_env, stdin=subprocess.DEVNULL,
                                           stdout=stream, stderr=subprocess.STDOUT,
                                           timeout=900, check=False)
            assert completed.returncode == 0, f'{arm} failed: {log}'
            text = log.read_text(encoding='utf-8', errors='replace')
            events = [line for line in text.splitlines() if line.startswith('STREHL_UI_PROGRESS ')]
            alignment = merge = None
            if observer == 'on':
                alignment = proof.alignment_events(events, args.limit)
                plan = re.search(r'memory plan\s*:\s*(\d+) canonical chunks', text)
                assert plan, 'Missing canonical work partition'
                chunks = int(plan.group(1))
                merge = proof.merge_events(events, args.limit,
                                           chunk_frames=(args.limit + chunks - 1) // chunks)
            else:
                assert not events, f'{arm} emitted observer events'
            entry = dict(name=arm, command=command, bytes=image.stat().st_size,
                         sha256=proof.digest(image), events=len(events),
                         elapsed_seconds=time.monotonic() - started,
                         alignment=alignment, merge=merge,
                         environment={k: v for k, v in arm_env.items()
                                      if k.startswith('STREHL_') or k == 'RAYON_NUM_THREADS'})
            result['runs'].append(entry)
            print(arm, entry['sha256'], flush=True)
    result['same_version'] = result['cli_version'] == result['bundled_version']
    result['byte_identical'] = len({run['sha256'] for run in result['runs']}) == 1
    result['inputs_unchanged'] = original_inputs == source_inventory(source, proof.digest)
    (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    assert result['same_version'], 'Frontend engine provenance differs'
    assert result['byte_identical'], 'Executable or observer changed the completed TIFF'
    assert result['inputs_unchanged'], 'The source bracket changed during verification'
    print('VERIFIED: all six standalone/bundled × off/on/placebo TIFFs are byte-identical', flush=True)


if __name__ == '__main__':
    main()
