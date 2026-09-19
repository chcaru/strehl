"""Observe existing per-band weights; require an identical full product image."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('weight_bounds', ROOT/'experiments/m193c-output-grid/bounded-process.py')
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)

def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def ref(path):
    return dict(path=str(path.resolve()), **b.binding(path))

def main():
    baseline = HERE/'vitamin-c-baseline-1'
    prior = json.loads((baseline/'invocation.json').read_text())
    completion = json.loads((baseline/'completion.json').read_text())
    exe = Path(prior['executable']['path'])
    assert ref(exe) == prior['executable']
    warp = Path(completion['map']['path'])
    assert ref(warp) == completion['map']
    original = Path(completion['image']['path'])
    assert ref(original) == completion['image']
    out = HERE/'vitamin-c-weight-trace-1'
    out.mkdir()
    command = next(argv.copy() for label, argv in prior['commands'] if label == 'render')
    command[command.index('--out')+1] = str(out/'output.tiff')
    fields = prior['environment'].copy()
    fields['STREHL_PYRAMID_WEIGHT_DUMP'] = str(out/'weights')
    env, removed = b.clean_environment(fields.items())
    inputs = prior['inputs']
    def check_inputs():
        for row in inputs:
            stat = Path(row['path']).stat()
            assert (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    check_inputs()
    save(out/'invocation.json', dict(command=command, environment=fields, removed_environment=removed,
        executable=ref(exe), map=ref(warp), baseline_image=ref(original), inputs=inputs,
        runner=ref(Path(__file__)), scope='Existing read-only per-band observer; exact full-image hash required'))
    api = b.load_job_api(b.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    result = b.run(command, env, ROOT, out/'process.log', api=api,
        wall_seconds=180, cpu_seconds=1200, log_bytes=4<<20, committed_bytes=16<<30)
    save(out/'process.json', result)
    print(json.dumps({k:result[k] for k in ('exit_code','error','wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    check_inputs()
    assert ref(warp) == completion['map'] and ref(exe) == prior['executable']
    image = ref(out/'output.tiff')
    assert image['sha256'] == completion['image']['sha256'], 'observer perturbed product output'
    weights = sorted(out.glob('weights-*'))
    assert len(weights) == 25, f'Expected 8 x 3 arrays and dimensions, found {len(weights)}'
    save(out/'completion.json', dict(image=image, observer_output_bit_exact=True,
        original_metadata_unchanged=True, weights=[ref(p) for p in weights]))

if __name__ == '__main__':
    main()
