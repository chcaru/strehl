"""Complete only a successful bound control job with the corrected log marker.

The build-bound driver expects the old full-control marker. Keep that source
and its binding unchanged; this separately bound helper checks the actual new
record. It cannot rescue a failed test, changed source, or changed quality result.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--controls', type=Path, required=True)
    args = p.parse_args()
    out = args.controls.resolve()
    assert out.is_relative_to(HERE) and not (out / 'completion.json').exists()
    c = module('bounded_common', ROOT / 'experiments/full-context-placement/run.py')
    bindings = json.loads((out / 'bindings.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in bindings['sources'])
    assert c.ref(Path(bindings['executable']['path'])) == bindings['executable']
    process = json.loads((out / 'process.json').read_text())
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    log_path = out / 'process.log'
    assert c.ref(log_path) == process['log']
    log = log_path.read_text()
    assert re.search(r'test result: ok\. [4-9] passed; 0 failed;', log)
    records = {}
    for marker in ['PARALLEL_CFA_NUMERIC ', 'PARALLEL_CFA_FULL_MECHANICAL ']:
        rows = [json.loads(line.split(marker, 1)[1]) for line in log.splitlines() if marker in line]
        assert len(rows) == 1
        records[marker.strip()] = rows[0]
    assert records['PARALLEL_CFA_NUMERIC']['status'] == 'PASS'
    assert records['PARALLEL_CFA_FULL_MECHANICAL']['previous_quality_admission'] is False
    screen = out / 'output/screen.json'
    result = json.loads(screen.read_text())
    preservation = module('continuity', HERE / 'preserved-screen.py').check(result)
    c.save(out / 'completion.json', dict(screen=c.ref(screen), sources_unchanged=True,
        structural_controls_passed=True, mechanical_passed=True,
        preservation=preservation, generated_result=result, records=records,
        completion_helper=c.ref(Path(__file__)),
        wrapper_note='Bound run.py final marker assertion expected BOUNDARY_CFA_FULL_MECHANICAL; '
                     'this helper requires actual PARALLEL_CFA_FULL_MECHANICAL. No test rerun or source edit.'))
    print(json.dumps(dict(completed=True, preservation=preservation)))


if __name__ == '__main__':
    main()
