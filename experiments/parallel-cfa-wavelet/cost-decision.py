"""Apply the prior root resource rule; no photographic or speed-quality claim."""
from pathlib import Path
import argparse
import hashlib
import json

HERE = Path(__file__).resolve().parent


def binding(path):
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cost', type=Path, required=True)
    args = parser.parse_args()
    cost_dir = args.cost.resolve()
    assert cost_dir.is_relative_to(HERE)
    completion = json.loads((cost_dir / 'completion.json').read_text())
    path = cost_dir / 'output/cost.json'
    assert binding(path) == completion['cost']
    measured = json.loads(path.read_text())
    process = json.loads((cost_dir / 'process.json').read_text())
    assert measured['frames'] == 1 and measured['source_indices'] == [35]
    assert measured['generated_quality_admitted'] is False
    assert measured['candidate_extent'] == [4096, 4096] and measured['candidate_levels'] == 12
    assert process['exit_code'] == 0 and process['error'] is None
    source = measured['source_phase_seconds']
    finish = measured['finish_seconds']
    peak = process['job_memory']['peak_job_memory_used_bytes']
    assert source > 0 and finish > 0 and peak > 0
    estimate = 70 * source + finish + 120
    result = dict(observational_full_feasible=peak < 12 * (1 << 30) and estimate <= 1500,
        measured_cost=binding(path), process=binding(cost_dir / 'process.json'),
        prior_plan=binding(HERE / 'charter.md'), helper=binding(Path(__file__)),
        source_phase_seconds=source, finish_seconds=finish, cost_peak_job_bytes=peak,
        estimated_full_wall_seconds=estimate, maximum_estimate_seconds=1500,
        maximum_cost_peak_bytes=12 * (1 << 30), full_wall_cap_seconds=1800,
        full_cpu_cap_seconds=3600, full_committed_cap_bytes=16 * (1 << 30),
        generated_quality_admission=False, photographic_promotion=False,
        scope='One measured source and a prior feasibility extrapolation; not a speed benchmark.')
    with (cost_dir / 'root-cost-decision.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
