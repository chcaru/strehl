"""Root-owned bounded jobs, using the existing process runner."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'cross_scale_jobs', ROOT / 'experiments/learned-band-guide/run.py')
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
c = old.c


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['build', 'export-train', 'export-held', 'texture-train', 'texture-held', 'generic-controls', 'commission', 'check-commission', 'train', 'infer', 'check', 'generic-commission', 'expanded-cost', 'expanded-train', 'expanded-infer', 'develop-qualify', 'transfer-qualify', 'transfer-check', 'training-diagnosis', 'preserve-cost', 'preserve-qualify', 'preserve-train', 'preserve-infer'])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--dataset', type=Path, default=ROOT / 'experiments/learned-band-guide/export-1/output/dataset.json')
    p.add_argument('--commission', type=Path)
    p.add_argument('--qualification', type=Path)
    p.add_argument('--weights', type=Path)
    p.add_argument('--predictions', type=Path)
    p.add_argument('--build', type=Path)
    p.add_argument('--textures', type=Path)
    p.add_argument('--annotations', type=Path)
    p.add_argument('--schedule', choices=['full43'])
    p.add_argument('--require-odd-seven', action='store_true')
    args = p.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    if args.phase == 'training-diagnosis':
        inputs = [c.ref(HERE / name) for name in ('independent-training-diagnosis.py',
            'independent-transfer-check.py', 'independent-develop-check.py', 'run.py')]
        out.mkdir()
        c.save(out / 'inputs.json', inputs)
        command = [sys.executable, '-I', '-B', '-X', 'faulthandler',
            str(HERE / 'independent-training-diagnosis.py'), '--out', str(out / 'output')]
        old.run_job(command, {}, out, 180, 600, 8 << 30)
        assert all(c.ref(Path(row['path'])) == row for row in inputs)
        result = json.loads((out / 'output/diagnosis.json').read_text())
        assert all(c.ref(Path(row['path']))['sha256'] == row['sha256'] for row in result['inputs'])
        c.save(out / 'completion.json', dict(process_completed=True, inputs_unchanged=True,
            scope='Training-only preservation diagnosis; no fit or new quality claim.'))
        return
    if args.phase == 'generic-commission' or args.phase.startswith(('expanded-', 'transfer-', 'develop-', 'preserve-')):
        transfer = args.phase.startswith('transfer-')
        phase = args.phase.split('-', 1)[1] if args.phase.startswith(('expanded-', 'transfer-', 'develop-', 'preserve-')) else args.phase
        script = HERE / ('independent-preserve-check.py' if args.phase == 'preserve-qualify' else 'preserve.py' if args.phase.startswith('preserve-') else 'independent-develop-check.py' if args.phase == 'develop-qualify' else 'independent-transfer-check.py' if transfer else 'develop.py')
        paths = {script, Path(__file__), HERE / 'develop.py', HERE / 'generic-consumer.py', HERE / 'train.py',
            ROOT / 'experiments/learned-band-guide/train.py',
            ROOT / 'experiments/band-weight-oracle/independent-check.py'}
        if transfer:
            paths.add(HERE / 'transfer-plan.md')
        if args.phase.startswith('preserve-'):
            paths.add(HERE / 'preserve.py')
        datasets = [args.dataset.resolve()]
        if args.phase in ('expanded-cost', 'expanded-train', 'develop-qualify', 'preserve-cost', 'preserve-train', 'preserve-qualify'):
            datasets.append(ROOT / 'experiments/learned-band-guide/export-1/output/dataset.json')
        for dataset in datasets:
            paths.add(dataset)
            data = json.loads(dataset.read_text())
            names = data.get('cases', data.get('training', []) + data.get('heldout', []))
            for name in names:
                case = Path(name)
                if not case.is_absolute():
                    case = dataset.parent / case
                paths.add(case.resolve())
                meta = json.loads(case.read_text())
                paths.update((case.parent / row['file']).resolve() for row in meta['arrays'].values())
                if transfer:
                    paths.update(case.parent.glob('independent-*'))
        for key in ('commission', 'qualification', 'weights', 'predictions', 'annotations'):
            path = getattr(args, key)
            if path is not None:
                paths.add(path.resolve())
        inputs = [c.ref(path) for path in sorted(paths)]
        out.mkdir()
        c.save(out / 'inputs.json', inputs)
        command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(script),
            phase, '--dataset', str(args.dataset.resolve()), '--out', str(out / 'output')]
        for key in ('commission', 'qualification', 'weights', 'predictions', 'annotations'):
            path = getattr(args, key)
            if path is not None:
                command += ['--' + key, str(path.resolve())]
        if args.schedule:
            command += ['--schedule', args.schedule]
        if args.require_odd_seven:
            command.append('--require-odd-seven')
        fields = dict(CUDA_VISIBLE_DEVICES='0', PYTHONHASHSEED='137', CUBLAS_WORKSPACE_CONFIG=':4096:8')
        old.run_job(command, fields, out, 660 if phase == 'train' else 300, 1800, 16 << 30)
        assert all(c.ref(Path(row['path'])) == row for row in inputs)
        c.save(out / 'completion.json', dict(process_completed=True, inputs_unchanged=True,
            scope='Generated development/transfer evidence only; no photographic claim.'))
        return
    if args.phase == 'generic-controls':
        paths = [HERE / name for name in ('generic-consumer.py', 'train.py', 'independent-generic-controls.py', 'run.py')]
        paths.append(ROOT / 'experiments/learned-band-guide/train.py')
        inputs = [c.ref(path) for path in paths]
        out.mkdir()
        c.save(out / 'inputs.json', inputs)
        command = [sys.executable, '-I', '-B', '-X', 'faulthandler',
            str(HERE / 'independent-generic-controls.py'), '--out', str(out / 'output')]
        fields = dict(CUDA_VISIBLE_DEVICES='0', PYTHONHASHSEED='137', CUBLAS_WORKSPACE_CONFIG=':4096:8')
        old.run_job(command, fields, out, 180, 600, 8 << 30)
        assert all(c.ref(Path(row['path'])) == row for row in inputs)
        c.save(out / 'completion.json', dict(process_completed=True, inputs_unchanged=True,
            scope='Independent generic consumer controls, no new photographic evidence.'))
        return
    if args.phase == 'build':
        out.mkdir()
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        prior = json.loads((ROOT / 'experiments/learned-band-guide/build-1/sources.json').read_text())
        paths = {Path(row['path']) for row in prior if Path(row['path']).suffix in ('.rs', '.toml', '.lock')}
        paths.update(HERE.glob('*.rs'))
        sources = [c.ref(path) for path in sorted(paths)]
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
    if args.phase.startswith('export-'):
        assert args.build is not None and args.textures is not None
        build, textures = args.build.resolve(), args.textures.resolve()
        sources = json.loads((build / 'sources.json').read_text())
        assert all(c.ref(Path(row['path'])) == row for row in sources)
        exe = build / 'cli-tests.exe'
        assert c.ref(exe) == json.loads((build / 'executable.json').read_text())
        texture_data = json.loads(textures.read_text())
        inputs = [c.ref(textures)] + [c.ref(Path(row['file'])) for row in texture_data['tiles']]
        out.mkdir()
        c.save(out / 'sources.json', sources)
        c.save(out / 'inputs.json', inputs)
        config = dict(split='training' if args.phase == 'export-train' else 'heldout',
            textures=str(textures), out=str(out / 'output'))
        c.save(out / 'config.json', config)
        fields = dict(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2', STREHL_ALIGN='1',
            STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
            STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
            STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
            STREHL_CROSS_SCALE_EXPORT_CONFIG=str(out / 'config.json'))
        command = [str(exe), 'merge_cmd::cross_scale_band_export::independent_fixtures::export_dataset',
            '--exact', '--nocapture', '--test-threads=1']
        old.run_job(command, fields, out, 900, 3600, 10 << 30)
        assert 'test result: ok. 1 passed;' in (out / 'process.log').read_text()
        assert all(c.ref(Path(row['path'])) == row for row in inputs + sources)
        c.save(out / 'completion.json', dict(process_completed=True, inputs_unchanged=True,
            scope='Independent generated export, no learned model or photographic admission.'))
        return
    if args.phase.startswith('texture-'):
        script = HERE / 'texture-stage.py'
        inputs = [c.ref(script), c.ref(Path(__file__))]
        out.mkdir()
        c.save(out / 'inputs.json', inputs)
        split = 'training' if args.phase == 'texture-train' else 'heldout'
        command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(script),
            '--split', split, '--out', str(out / 'output')]
        old.run_job(command, {}, out, 120, 240, 4 << 30)
        assert all(c.ref(Path(row['path'])) == row for row in inputs)
        c.save(out / 'completion.json', dict(process_completed=True, inputs_unchanged=True,
            scope='Retained texture staging only; source hashes are in textures.json.'))
        return
    dataset = args.dataset.resolve()
    data = json.loads(dataset.read_text())
    paths = {dataset, Path(__file__), ROOT / 'experiments/learned-band-guide/train.py',
        ROOT / 'experiments/learned-band-guide/run.py',
        ROOT / 'experiments/full-context-placement/run.py',
        ROOT / 'experiments/m193c-output-grid/bounded-process.py',
        ROOT / 'experiments/m12-scorecard/m12-harness.py'}
    # Bind the executable path, not unrelated fixtures being developed in parallel.
    paths.add(HERE / 'train.py')
    paths.add(HERE / 'plan.md')
    if (HERE / 'architecture.md').is_file():
        paths.add(HERE / 'architecture.md')
    if args.phase.startswith('check'):
        paths.add(HERE / 'independent-check.py')
        paths.add(HERE / 'independent-plan.md')
        paths.add(ROOT / 'experiments/band-weight-oracle/independent-check.py')
    for group in ('training', 'heldout'):
        for name in data[group]:
            case = Path(name)
            if not case.is_absolute():
                case = dataset.parent / case
            paths.add(case.resolve())
            meta = json.loads(case.read_text())
            paths.update((case.parent / row['file']).resolve() for row in meta['arrays'].values())
    for path in (args.commission, args.qualification, args.weights, args.predictions):
        if path is not None:
            path = path.resolve()
            assert path.is_file()
            paths.add(path)
    inputs = [c.ref(p) for p in sorted(paths)]
    out.mkdir()
    c.save(out / 'inputs.json', inputs)
    script = 'independent-check.py' if args.phase.startswith('check') else 'train.py'
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE / script),
        args.phase, '--dataset', str(dataset), '--out', str(out / 'output')]
    for key in ('commission', 'weights', 'predictions'):
        path = getattr(args, key)
        if path is not None:
            command += ['--' + key, str(path.resolve())]
    if args.phase == 'train':
        assert args.commission is not None and args.qualification is not None
        qualification = json.loads(args.qualification.read_text())
        assert qualification['passed'] is True
        assert qualification['source_sha256'] == c.ref(HERE / 'train.py')['sha256']
    fields = dict(CUDA_VISIBLE_DEVICES='0', PYTHONHASHSEED='137', CUBLAS_WORKSPACE_CONFIG=':4096:8')
    old.run_job(command, fields, out, 240 if args.phase == 'train' else 180, 1800, 8 << 30)
    assert all(c.ref(Path(row['path'])) == row for row in inputs)
    c.save(out / 'completion.json', dict(process_completed=True, inputs_unchanged=True,
        scope='Developer-visible cases only; no generalization or photographic qualification.'))


if __name__ == '__main__':
    main()
