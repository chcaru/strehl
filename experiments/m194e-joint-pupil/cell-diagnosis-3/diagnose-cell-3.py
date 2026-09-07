"""Frozen full3 refusal decomposition; no tolerance or numerical source changes."""
from pathlib import Path
import json
import math
import shutil
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "float-run-3" / "source"
sys.path.insert(0, str(FROZEN))
from model import primary_scene, primary_frames, sha256, write_json
import render

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
sources = {p: sha256(FROZEN / p) for p in ("model.py", "render.py")}
assert sources['render.py'] == 'a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460'
for p in sources:
    shutil.copyfile(FROZEN / p, out / p)
shutil.copyfile(Path(__file__), out / Path(__file__).name)
scene, frame, xy = primary_scene(), primary_frames()[2], (4, 0)
config = render.integrator_for('cell-refined')
ref_result = HERE / 'independent-reference-1' / 'result.json'
ref = next(r for r in json.loads(ref_result.read_text())['frames'] if r['index']==2 and r['arm']=='refined')
ref_path = ref_result.parent / ref['array']['path']
assert sha256(ref_path) == ref['array']['sha256']
truth = float(np.load(ref_path,allow_pickle=False)[xy[1],xy[0]])
record = dict(schema='m194e-cell3-diagnostic-v1',argv=sys.argv,orig_argv=sys.orig_argv,
              xoptions=sys._xoptions,executable=sys.executable,cwd=str(Path.cwd()),
              sources_before=sources,diagnostic_source=sha256(Path(__file__)),xy=xy,frame=2,
              reference=dict(value_e=truth,array=ref['array'],result_sha256=sha256(ref_result)))


def describe(leaves):
    ordered = sorted(leaves,key=lambda leaf:leaf.path)
    return [dict(path=leaf.path,depth=leaf.depth,triangle=leaf.triangle.tolist(),area=leaf.area,
                 low_e=leaf.low,high_e=leaf.high,delta_e=abs(leaf.high-leaf.low),
                 pupil_low_e=leaf.pupil_low,pupil_high_e=leaf.pupil_high,indicator_e=leaf.indicator)
            for leaf in ordered]


meter = render.Meter(config)
try:
    record['returned'] = render.render_cell(scene,frame,xy,config,meter)
except Exception as exc:
    record['error'] = repr(exc)
    record['traceback'] = traceback.format_exc()
    tb = exc.__traceback__
    while tb:
        scope = tb.tb_frame.f_locals
        if tb.tb_frame.f_code.co_name == 'integrate_frontier':
            record['terminal_sums'] = dict(scope['sums'])
            record['terminal_leaves'] = describe(scope['leaves'])
            record['eligible'] = len(scope['eligible'])
        tb = tb.tb_next
record['work'] = meter.receipt()
roots = render.cell_triangles(scene,frame,xy)
initial_meter = render.Meter(config)
initial = [render.evaluate_cell_leaf(scene,frame,t,(i,),config,initial_meter) for i,t in enumerate(roots)]
record['initial_sums'] = render.aggregate_frontier(initial,[float(render.triangle_area(t)) for t in roots],config)
record['initial_leaves'] = describe(initial)
record['initial_work'] = initial_meter.receipt()
for prefix in ('initial','terminal'):
    sums = record[prefix+'_sums']
    leaves = record[prefix+'_leaves']
    sums['sum_low_pupil_e'] = math.fsum(leaf['pupil_low_e'] for leaf in leaves)
    sums['signed_truth_error_e'] = sums['value']-truth
record['sources_after'] = {p:sha256(FROZEN/p) for p in sources}
assert record['sources_after']==sources
record['status'] = 'DIAGNOSTIC_ONLY_NO_ADMISSION'
write_json(out/'result.json',record)
print(json.dumps({k:v for k,v in record.items() if not k.endswith('_leaves')}))
