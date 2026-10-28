"""Bounded full flat60 development and fixed Helicon B/C workflow arms."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import time
import numpy as np
import psutil
import tifffile
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/raw-quality-2026-10-26/flat-1s-comparator'
HELPER = ROOT / 'experiments/m193c-output-grid/bounded-process.py'
spec = importlib.util.spec_from_file_location('flat_comparator_bounded', HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')

def ref(path):
    return dict(path=str(path), **b.binding(path))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('b', 'c'))
    p.add_argument('--config', type=Path, default=HERE / 'flat-export-config.json')
    p.add_argument('--exe', type=Path)
    p.add_argument('--sha256')
    p.add_argument('--build-log', type=Path)
    args = p.parse_args()
    config = args.config.resolve()
    cfg = read(config)
    export = Path(cfg['out'])
    assert export.is_relative_to(ROOT / 'outputs/raw-quality-2026-10-26')
    OUT.mkdir(exist_ok=True)
    stage = OUT / (args.stage + '-desktop')
    stage.mkdir()
    receipt = None
    started = time.monotonic()
    free = shutil.disk_usage(OUT).free
    available = psutil.virtual_memory().available
    save(stage / 'resources.json', dict(free_disk_bytes=free, available_physical_bytes=available,
        cpu_percent=psutil.cpu_percent(interval=1), physical_cores=psutil.cpu_count(logical=False),
        logical_cores=psutil.cpu_count(), purpose='Operational resource receipt; no isolated speed claim'))
    if args.stage == 'develop':
        assert args.exe and args.sha256 and args.build_log
        assert not export.exists()
        assert free > (40 << 30)
        assert available > 10 << 30
        exe = args.exe.resolve()
        assert b.binding(exe)['sha256'] == args.sha256.lower()
        log = args.build_log.read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log and 'Finished' in log
        command = [str(exe), str(config)]
        fields = dict(RAYON_NUM_THREADS='4')
        limits = dict(wall_seconds=900, cpu_seconds=3600, committed_bytes=6 << 30)
        extra = dict(config=ref(config), build_log=ref(args.build_log))
    else:
        receipt = read(export / 'receipt.json')
        assert receipt['status'] == '60_UNALIGNED_NATIVE_RGB16_DEVELOPED'
        assert receipt['input_content_and_metadata_unchanged'] and len(receipt['frames']) == 60
        assert receipt['worker_count'] == 4 and receipt['golden']['status'] == 'EXACT'
        inputs = [Path(row['output']) for row in receipt['frames']]
        before = [ref(path) for path in inputs]
        for row, expected in zip(before, receipt['frames']):
            assert row['sha256'] == expected['output_sha256'] and row['bytes'] == expected['output_bytes']
        save(stage / 'inputs-before.json', before)
        manifest = stage / 'inputs.txt'
        manifest.write_text('\n'.join(str(path) for path in inputs) + '\n', encoding='utf-8')
        exe = Path('C:/dev/blog/death-of-software/projects/strehl/experiments/helicon-current/program/HeliconFocus.exe')
        output = stage / 'stack-master.tiff'
        command = [str(exe), '-silent', '-noprogress', '-i', str(manifest),
            '-mp:' + {'b': '1', 'c': '2'}[args.stage],
            *(['-rp:8'] if args.stage == 'b' else []), '-sp:4', '-sort:asc', '-tif:u',
            '-save:' + str(output), '-o', str(stage / 'saved-outputs.txt')]
        fields = {}
        assert available > (44 << 30), 'Need previously exercised 40GiB vendor job plus host reserve; native weevil run has completed'
        limits = dict(wall_seconds=1200, cpu_seconds=24000, committed_bytes=40 << 30)
        extra = dict(development_receipt=ref(export / 'receipt.json'), method=args.stage,
            radius=8 if args.stage == 'b' else 'inactive', smoothing=4,
            remaining_settings='installed application defaults recorded in application log',
            scope='Full source development plus external alignment and merging; premerge tone, no Strehl CA warp; not a pure merge comparison')
    env, removed = b.clean_environment(fields.items())
    harness = ROOT / 'experiments/m12-scorecard/m12-harness.py'
    save(stage / 'invocation.json', dict(command=command, executable=ref(exe), runner=ref(Path(__file__)),
        helper=ref(HELPER), harness=ref(harness), fields=fields, removed_environment=removed, **extra))
    result = b.run(command, env, ROOT, stage / 'process.log',
        api=b.load_job_api(b.binding(harness)), log_bytes=32 << 20, **limits)
    save(stage / 'process.json', result)
    if args.stage != 'develop':
        app_log = Path('C:/Users/chris/AppData/Local/HeliconFocus/HeliconFocus.log')
        if app_log.exists():
            shutil.copyfile(app_log, stage / 'application.log')
    assert result['exit_code'] == 0 and result['error'] is None and result['terminal_job_accounting'] and not result['cleanup_errors'], result
    if args.stage == 'develop':
        receipt = read(export / 'receipt.json')
        assert receipt['status'] == '60_UNALIGNED_NATIVE_RGB16_DEVELOPED'
        assert len(receipt['frames']) == 60 and receipt['input_content_and_metadata_unchanged']
        summary = dict(export=ref(export / 'receipt.json'), frames=60)
    else:
        assert output.is_file()
        with tifffile.TiffFile(output) as tf:
            assert len(tf.pages) == 1
            page = tf.pages[0]
            rgb = page.asarray()
            icc = bytes(page.tags[34675].value)
        assert rgb.dtype == np.uint16 and rgb.ndim == 3 and rgb.shape[2] == 3 and icc
        assert rgb.shape[1] >= 0.9 * receipt['active_wh'][0] and rgb.shape[0] >= 0.9 * receipt['active_wh'][1], 'unexpectedly small vendor output; no complete-image admission'
        image = Image.fromarray(((rgb.astype(np.uint32) + 128) // 257).astype(np.uint8))
        image.save(stage / 'stack-full.jpg', quality=98, subsampling=0, icc_profile=icc)
        image.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
        image.save(stage / 'overview.jpg', quality=98, icc_profile=icc)
        after = [ref(path) for path in inputs]
        assert before == after
        save(stage / 'inputs-after.json', after)
        summary = dict(master=ref(output), shape=list(rgb.shape), dtype='uint16',
            icc_sha256=hashlib.sha256(icc).hexdigest(), inputs_unchanged=True,
            visual_review='pending; dimensions alone do not establish artifact-free output')
    summary['whole_stage_seconds_including_preparation_and_verification'] = time.monotonic() - started
    save(stage / 'completion.json', summary)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
