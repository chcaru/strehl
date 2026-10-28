"""Root-only bounded presentation of a completed full299 GPU observation."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
HELPER = ROOT / 'experiments/raw-quality-2026-10-27/native-restoration/run.py'
spec = importlib.util.spec_from_file_location('dual_tree_gpu_view_helper', HELPER)
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    source, output = args.input.resolve(), args.out.resolve()
    assert source.is_relative_to(ROOT / 'outputs') and source.name == 'output'
    assert output.is_relative_to(ROOT / 'outputs') and not output.exists() and not output.is_relative_to(source)
    completion = source.parent / 'completion.json'
    assert json.loads(completion.read_text())['mode'] == 'full', 'successful complete full299 sibling receipt required'
    job = output.with_name(output.name+'-job')
    assert not job.exists()
    job.mkdir()
    script = AREA / 'prepare-views.py'
    bindings = [r.ref(p) for p in (script, Path(__file__), HELPER, completion, source / 'receipt.json')]
    command = [sys.executable, '-B', '-X', 'faulthandler', str(script), '--input', str(source), '--out', str(output)]
    fields = dict(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    env, removed = r.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=180, cpu_seconds=180, log_bytes=16 << 20, committed_bytes=4 << 30)
    r.save(job / 'invocation.json', dict(command=command, bindings=bindings, environment=fields,
           removed_environment=removed, bounds=bounds, RAW_reads=0, fitting=False, prospective_quality_claim=False))
    api = r.b.load_job_api(r.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
    result = r.b.run(command, env, ROOT, job / 'process.log', api=api, **bounds)
    r.save(job / 'process.json', result)
    print(json.dumps({key: result[key] for key in ('exit_code', 'error', 'wall_seconds', 'job_memory')}))
    print((job / 'process.log').read_text(encoding='utf-8', errors='replace')[-4000:])
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    assert all(r.ref(row['path']) == row for row in bindings)
    receipt = output / 'display-receipt.json'
    display = json.loads(receipt.read_text())
    assert display['status'] == 'THREE_COMPLETE_DUAL_TREE_GPU_DISPLAYS_READY_NO_VERDICT'
    assert display['inputs_unchanged'] and display['admission'] is False and display['photographic_improvement_claimed'] is False
    assert [row['arm'] for row in display['arms']] == ['baseline', 'candidate', 'uniform']
    assert all(len(row['crops']) == 10 for row in display['arms'])
    r.save(job / 'completion.json', dict(bindings=bindings, reports=[r.ref(receipt), r.ref(output/'index.md')],
           photographic_improvement_claimed=False, source_full_completion=r.ref(completion)))


if __name__ == '__main__':
    main()
