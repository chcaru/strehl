"""Bounded exact-consumer export; no model result or photographic admission."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('relative_witness_job', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'export'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir()
    if args.phase == 'build':
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        old = json.loads((ROOT / 'experiments/parallel-cfa-wavelet/build-1/sources.json').read_text())
        paths = {Path(row['path']) for row in old}
        paths.update(HERE / name for name in ('source-witness.rs', 'witness-run.py'))
        sources = [c.ref(p) for p in sorted(paths)]
        c.save(out / 'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--no-run', '--release',
            '--features', 'native-pyramid-profile,native-gpu-gather,native-direct-planes,native-correction-variance',
            '--jobs', '2', '--target-dir', str(ROOT / 'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics', '--locked', '--offline']
        c.job(command, {'RAYON_NUM_THREADS': '8', 'CARGO_INCREMENTAL': '0'}, out, wall=600)
        log = (out / 'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log
        executables = []
        for line in log.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if (row.get('reason') == 'compiler-artifact' and row.get('executable')
                    and row.get('target', {}).get('name') == 'strehl' and row['profile']['test']):
                executables.append(row['executable'])
        assert len(executables) == 1
        exe = out / 'cli-tests.exe'
        shutil.copyfile(executables[0], exe)
        assert all(c.ref(Path(row['path'])) == row for row in sources)
        c.save(out / 'executable.json', c.ref(exe))
        return
    assert args.build is not None
    build = args.build.resolve()
    sources = json.loads((build / 'sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    exe = build / 'cli-tests.exe'
    assert c.ref(exe) == json.loads((build / 'executable.json').read_text())
    old = ROOT / 'experiments/donor-consistency/spatial-on-2'
    config = json.loads((old / 'config.json').read_text())
    originals = sorted(Path(config['source_dir']).glob('*.ARW'))
    assert len(originals) == 70
    inputs = [dict(path=str(p), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns) for p in originals]
    refs = [c.ref(old / name) for name in ('config.json', 'output/receipt.json', 'witness/receipt.json')]
    refs.append(c.ref(Path(config['warp_map'])))
    c.save(out / 'bindings.json', dict(sources=sources, executable=c.ref(exe), references=refs, inputs=inputs))
    fields = dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
        STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
        STREHL_WARPMAP=config['warp_map'], STREHL_RELATIVE_BLUR_SOURCE_OUT=str(out / 'output'))
    command = [str(exe), 'merge_cmd::relative_blur_source_witness::vitamin_c_wide_source_witness',
               '--exact', '--ignored', '--nocapture', '--test-threads=1']
    c.job(command, fields, out, wall=120)
    log = (out / 'process.log').read_text()
    assert 'test result: ok. 1 passed;' in log
    assert all(c.ref(Path(row['path'])) == row for row in sources + refs)
    for row in inputs:
        stat = Path(row['path']).stat()
        assert (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    receipt = out / 'output/receipt.json'
    record = json.loads(receipt.read_text())
    assert record['source_indices'] == [25, 28, 33, 69] and len(record['groups']) == 4
    for group in record['groups']:
        for artifact in group['artifacts']:
            assert artifact['old_overlap_bit_exact']
            for key in ('known4', 'guide', 'variance'):
                assert c.ref(out / 'output' / artifact[key]['path'])['sha256'] == artifact[key]['sha256']
    c.save(out / 'completion.json', dict(receipt=c.ref(receipt), sources_unchanged=True,
        original_metadata_unchanged=True, retained_consumer_exact=True,
        scope='Four original-source measurement export only; no complete stack, model or image-quality result.'))


if __name__ == '__main__':
    main()
