"""Diagnostic only: inspect all depth-six nodes of the frozen failed cell.

Falsifiers fixed before execution: a whole-cell indicator above the existing
budgets after the original local traversal, or a retained estimate outside the
frozen .004e truth budget, would refute a purely local-allocation explanation.
The global queue is an analysis of the same precomputed nodes, not an admitted
renderer: largest indicator first, lexical tree path tie, no depth/order change.
No scene array, successful bundle or commission can be emitted here.
"""
from pathlib import Path
import json
import shutil
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "float-run-2" / "source"
sys.path.insert(0, str(FROZEN))
from model import primary_scene, primary_frames, sha256, write_json
import render

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
sources = {p: sha256(FROZEN / p) for p in ("model.py", "render.py")}
assert sources["render.py"] == "a59e9686823d6f4ab2749dd8ca0f1a0bbf6cd847ee32ed04eef44dc78a87aba5"
for p in sources:
    shutil.copyfile(FROZEN / p, out / p)
shutil.copyfile(Path(__file__), out / Path(__file__).name)
config = render.Integrator()
meter = render.Meter(config)
scene, frame, xy = primary_scene(), primary_frames()[3], (31, 7)
nodes = {}
reference_result = HERE / "independent-reference-1" / "result.json"
reference_record = next(r for r in json.loads(reference_result.read_text())['frames']
                        if r['index'] == 3 and r['arm'] == 'refined')
reference_path = reference_result.parent / reference_record['array']['path']
assert sha256(reference_path) == reference_record['array']['sha256']
reference = float(np.load(reference_path, allow_pickle=False)[xy[1], xy[0]])
record = dict(schema="m194e-cell-allocation-diagnostic-v1", status="running",
              argv=sys.argv, orig_argv=sys.orig_argv, xoptions=sys._xoptions,
              executable=sys.executable, cwd=str(Path.cwd()), sources_before=sources,
              diagnostic_source=sha256(Path(__file__)), xy=xy, frame=3,
              reference=dict(value_e=reference, array=reference_record['array'],
                             result_sha256=sha256(reference_result)), nodes=nodes)


def evaluate(t, name, depth):
    area = float(render.triangle_area(t))
    indices = render.tangent_indices(t, scene, frame)
    low_xy, low_w = render.triangle_rule(t, config.cell_low, indices)
    high_xy, high_w = render.triangle_rule(t, config.cell_high, indices)
    low_v, low_e = render.render_points(scene, frame, low_xy, config, meter)
    high_v, high_e = render.render_points(scene, frame, high_xy, config, meter)
    low, high = float(low_w @ low_v), float(high_w @ high_v)
    pl, ph = float(low_w @ low_e), float(high_w @ high_e)
    delta = abs(high - low)
    indicator = delta + pl + ph
    meter.watch(t, low_xy, low_w, high_xy, high_w, low_v, low_e, high_v, high_e)
    node = dict(depth=depth, triangle=t.tolist(), selected_indices=list(indices), area=area,
                low_e=low, high_e=high, low_pupil_e=pl, high_pupil_e=ph,
                cell_delta_e=delta, indicator_e=indicator,
                original_local_budget_e=config.cell_tolerance * area,
                original_local_pass=bool(indicator <= config.cell_tolerance * area),
                children=[])
    nodes[name] = node
    if depth < config.cell_depth:
        lengths = [np.sum((t[(j + 1) % 3] - t[j]) ** 2) for j in range(3)]
        j = int(np.argmax(lengths))
        a, b, c = t[j], t[(j + 1) % 3], t[(j + 2) % 3]
        midpoint = (a + b) / 2
        node['children'] = [name + '/0', name + '/1']
        evaluate(np.array((a, midpoint, c)), node['children'][0], depth + 1)
        evaluate(np.array((midpoint, b, c)), node['children'][1], depth + 1)


def aggregate(names):
    selected = [nodes[n] for n in names]
    high = sum(n['high_e'] for n in selected)
    error = sum(n['indicator_e'] for n in selected)
    pupil = sum(n['high_pupil_e'] for n in selected)
    return dict(leaves=len(names), area=sum(n['area'] for n in selected),
                high_e=high, low_e=sum(n['low_e'] for n in selected),
                cell_indicator_e=error, high_pupil_indicator_e=pupil,
                final_reported_indicator_e=error + pupil,
                within_existing_global_budgets=error <= config.cell_tolerance and pupil <= config.pupil_tolerance,
                signed_truth_error_e=high - reference, abs_truth_error_e=abs(high - reference),
                local_failure_paths=[name for name in names if not nodes[name]['original_local_pass']])


def local_leaves(name):
    n = nodes[name]
    if n['original_local_pass'] or not n['children']:
        return [name]
    return [v for child in n['children'] for v in local_leaves(child)]


try:
    roots = []
    for i, t in enumerate(render.cell_triangles(scene, frame, xy)):
        name = f"root-{i}"
        roots.append(name)
        evaluate(t, name, 0)
    record['initial'] = aggregate(roots)
    local = [n for root in roots for n in local_leaves(root)]
    record['original_local_terminal'] = dict(paths=local, **aggregate(local))
    uniform = sorted(n for n in nodes if nodes[n]['depth'] == config.cell_depth)
    record['uniform_depth6'] = dict(paths=uniform, **aggregate(uniform))
    leaves = list(roots)
    steps = []
    while True:
        state = aggregate(leaves)
        steps.append(dict(step=len(steps), paths=list(leaves), **state))
        if state['within_existing_global_budgets']:
            break
        eligible = [n for n in leaves if nodes[n]['children']]
        if not eligible:
            break
        chosen = min(eligible, key=lambda name: (-nodes[name]['indicator_e'], name))
        slot = leaves.index(chosen)
        leaves[slot:slot + 1] = nodes[chosen]['children']
    record['diagnostic_global_sequence'] = steps
    record['status'] = "DIAGNOSTIC_COMPLETE_NOT_ADMITTED"
except Exception as exc:
    record['status'] = "DIAGNOSTIC_REFUSED"
    record['error'] = repr(exc)
    record['traceback'] = traceback.format_exc()
record['work'] = meter.receipt()
record['sources_after'] = {p: sha256(FROZEN / p) for p in sources}
assert record['sources_before'] == record['sources_after']
write_json(out / 'result.json', record)
print(json.dumps({k: v for k, v in record.items() if k != 'nodes'}))
