"""Root-owned bounded build and exact-consumer source-trace measurement."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('through_focus_events_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'controls', 'export'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir()
    if args.phase == 'build':
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        prior = json.loads((ROOT / 'experiments/rb-residual-full/build-1/sources.json').read_text())
        paths = {Path(row['path']) for row in prior}
        paths.update(p for p in HERE.iterdir() if p.suffix in ('.rs', '.py', '.md'))
        paths.add(ROOT / 'experiments/relative-blur-evidence/witness-1/output/receipt.json')
        sources = [c.ref(p) for p in sorted(paths)]
        c.save(out / 'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--no-run', '--release',
            '--features', 'native-pyramid-profile,native-gpu-gather,native-direct-planes,native-correction-variance',
            '--jobs', '2', '--target-dir', str(ROOT / 'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics', '--locked', '--offline']
        c.job(command, {'RAYON_NUM_THREADS':'8', 'CARGO_INCREMENTAL':'0'}, out, wall=600)
        log = (out / 'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log
        exes = []
        for line in log.splitlines():
            try: row = json.loads(line)
            except ValueError: continue
            if (row.get('reason') == 'compiler-artifact' and row.get('executable')
                and row.get('target', {}).get('name') == 'strehl' and row['profile']['test']):
                exes.append(row['executable'])
        assert len(exes) == 1
        exe = out / 'cli-tests.exe'
        shutil.copyfile(exes[0], exe)
        assert all(c.ref(Path(row['path'])) == row for row in sources)
        c.save(out / 'executable.json', c.ref(exe))
        return
    assert args.build is not None
    build = args.build.resolve()
    sources = json.loads((build / 'sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    exe = build / 'cli-tests.exe'
    assert c.ref(exe) == json.loads((build / 'executable.json').read_text())
    c.save(out / 'bindings.json', dict(sources=sources, executable=c.ref(exe), runner=c.ref(Path(__file__))))
    fields = dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
        STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
        STREHL_THROUGH_FOCUS_EVENTS_OUT=str(out / 'output'))
    if args.phase == 'controls':
        command = [str(exe), 'merge_cmd::through_focus_events::independent_controls::',
                   '--nocapture', '--test-threads=1']
        c.job(command, fields, out, wall=120)
        log = (out / 'process.log').read_text()
        assert 'test result: ok.' in log and '0 passed;' not in log
        assert all(c.ref(Path(row['path'])) == row for row in sources)
        c.save(out / 'completion.json', dict(passed=True, executable=c.ref(exe),
            sources_unchanged=True, process=c.ref(out / 'process.json')))
        return
    controls = build.parent / 'controls-1/completion.json'
    assert json.loads(controls.read_text())['executable'] == c.ref(exe)
    assert json.loads(controls.read_text())['passed']
    old = ROOT / 'experiments/donor-consistency/spatial-on-2'
    cfg = json.loads((old / 'config.json').read_text())
    inputs = [dict(path=str(p), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns)
              for p in sorted(Path(cfg['source_dir']).glob('*.ARW'))]
    assert len(inputs) == 70
    refs = [c.ref(old / name) for name in ('config.json', 'output/receipt.json', 'witness/receipt.json')]
    refs.append(c.ref(Path(cfg['warp_map'])))
    c.save(out / 'input-bindings.json', dict(references=refs, inputs=inputs, controls=c.ref(controls)))
    fields['STREHL_WARPMAP'] = cfg['warp_map']
    command = [str(exe), 'merge_cmd::through_focus_events::vitamin_c_complete_source_traces',
               '--exact', '--ignored', '--nocapture', '--test-threads=1']
    c.job(command, fields, out, wall=300)
    assert 'test result: ok. 1 passed;' in (out / 'process.log').read_text()
    assert all(c.ref(Path(row['path'])) == row for row in sources + refs)
    for row in inputs:
        stat = Path(row['path']).stat()
        assert (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    receipt = out / 'output/receipt.json'
    record = json.loads(receipt.read_text())
    assert record['source_indices'] == list(range(70))
    c.save(out / 'completion.json', dict(receipt=c.ref(receipt), sources_unchanged=True,
        original_metadata_unchanged=True, references_unchanged=True,
        scope='Complete-sequence scalar source measurements; no rendered image or quality admission.'))

if __name__ == '__main__': main()
