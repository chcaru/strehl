"""Root-owned, source-bound build and independent-control execution."""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ca_order_bounds', ROOT/'experiments/full-context-placement/run.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)


def bindings():
    paths = set(common.source_paths())
    for root in (ROOT/'crates', ROOT/'experiments/native-gpu-gather/src', HERE):
        paths.update(p for p in root.rglob('*') if p.is_file()
                     and p.suffix in ('.rs', '.wgsl', '.toml', '.py', '.md')
                     and not any(part.startswith(('build-', 'controls-', 'full-')) for part in p.relative_to(root).parts[:-1]))
    paths.add(ROOT/'experiments/native-gpu-gather/integration.rs')
    paths.add(ROOT/'experiments/native-gpu-gather/Cargo.toml')
    return [common.ref(p.resolve()) for p in sorted(paths)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('build', 'controls'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--filter')
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE
    out.mkdir(exist_ok=False)
    if args.phase == 'build':
        (ROOT/'crates/strehl-cli/src/align_cmd.rs').touch()
        (ROOT/'experiments/native-gpu-gather/src/lib.rs').touch()
        sources = bindings()
        common.save(out/'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--test', 'byte-freeze',
                   '--no-run', '--release', '--features',
                   'native-pyramid-profile,native-gpu-gather,native-direct-planes', '--jobs', '2',
                   '--target-dir', str(ROOT/'target/native-pyramid-profile'),
                   '--message-format=json-render-diagnostics', '--locked', '--offline']
        common.job(command, {'RAYON_NUM_THREADS': '8', 'CARGO_INCREMENTAL': '0'}, out)
        log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log and 'Compiling strehl-native-gpu-gather' in log
        artifacts = {}
        for line in log.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if (row.get('reason') == 'compiler-artifact' and row.get('executable')
                    and row.get('target', {}).get('name') == 'strehl'):
                name = 'cli-tests' if row['profile']['test'] else 'strehl'
                assert name not in artifacts
                destination = out/(name+'.exe')
                shutil.copyfile(row['executable'], destination)
                artifacts[name] = common.ref(destination)
        assert set(artifacts) == {'cli-tests', 'strehl'}
        assert all(common.ref(Path(row['path'])) == row for row in sources)
        common.save(out/'executables.json', artifacts)
    else:
        assert args.build and args.filter
        build = args.build.resolve()
        sources = json.loads((build/'sources.json').read_text())
        assert all(common.ref(Path(row['path'])) == row for row in sources)
        exe = build/'cli-tests.exe'
        assert common.ref(exe) == json.loads((build/'executables.json').read_text())['cli-tests']
        command = [str(exe), args.filter, '--nocapture', '--test-threads=1']
        fields = {'RAYON_NUM_THREADS': '2', 'STREHL_CA_BEFORE_MHC_OUT': str(out/'output'),
                  'STREHL_GPU_GATHER': 'on', 'STREHL_GPU_SCHEDULE': 'device',
                  'STREHL_GPU_GATHER_LOG': 'off', 'STREHL_FULLRES_GATHER': '1',
                  'STREHL_DIRECT_PLANES': 'rounded', 'STREHL_PROBE_GATHER': 'green',
                  'STREHL_WARP_WRITEBACK': 'parallel', 'STREHL_DEFECT': 'off'}
        common.job(command, fields, out, 180)
        log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
        counts = re.findall(r'test result: ok\. (\d+) passed;', log)
        assert counts and all(int(count) > 0 for count in counts)
        assert all(common.ref(Path(row['path'])) == row for row in sources)
        common.save(out/'completion.json', {'sources_unchanged': True, 'controls_executed': True})


if __name__ == '__main__':
    main()
