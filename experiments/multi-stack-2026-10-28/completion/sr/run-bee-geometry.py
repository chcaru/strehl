"""Frozen Q/V-only bee geometry, with no sweep/plateau qualification or output."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--binary', type=Path, required=True)
p.add_argument('--tag', required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[4]
out = root/'outputs/multi-stack/completion'
phase_path = out/'sr-bee-phase-opportunity-01.json'
phase = json.loads(phase_path.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = out/'noise-bee-repeat-01'
assert sha(base/'alignment.json') == phase['inputs']['alignment']
assert sha(base/'equal/source-identities.json') == phase['inputs']['identities']
ids = json.loads((base/'equal/source-identities.json').read_text())
assert [ids[i] for i in phase['targets']] == phase['target_identities']
assert len(phase['rois']) == 9 and len(phase['targets']) == 14 and len(phase['guides']) == 2
records = []
for index, roi in enumerate(phase['rois']):
    destination = out/f'sr-bee-{a.tag}-geometry-roi{index}'
    receipt = out/f'sr-bee-run-{a.tag}-geometry-roi{index}'
    x, y = roi['origin_sensor']
    command = [str(a.binary), '--render-dir', str(base/'equal'),
        '--cache', str(base/'source-cache'), '--out', str(destination),
        '--workers', '4', '--size', '192', '--x', str(x), '--y', str(y),
        '--assumed-registration-sigma-sensor', '0.10',
        '--targets', ','.join(map(str,phase['targets'])),
        '--guides', ','.join(map(str,phase['guides'])),
        '--measure-registration', '--registration-only', '--geometry-without-focus',
        '--registration-geometry-sigma-quad', '1.2', '--registration-tile-quad', '46',
        '--registration-grid-axis', '3', '--registration-window-quad', '192',
        '--refine-registration', '--registration-patch-diagnostics', '--coherent-color-motion']
    subprocess.run([sys.executable, 'experiments/multi-stack-2026-10-28/run-command.py',
        '--receipt', str(receipt), '--cwd', str(root), '--env', 'RAYON_NUM_THREADS=4',
        '--', *command], cwd=root, check=True)
    report_path = destination/'local-registration-report.json'
    report = json.loads(report_path.read_text())
    assert report['raw_decodes']==0 and report['cache_disk_hits']==16
    assert report['focus_not_evaluated_geometry_only']
    assert all(s['focus_usable_pixels']==0 and s['focus_weight_sum']==0
               for s in report['source_identities'])
    assert {s['global_index'] for s in report['source_identities']} == set(phase['targets'])
    assert not (destination/'candidate.tiff').exists()
    assert not list(destination.glob('focus-pass-*'))
    m = report['measurement']
    records.append(dict(index=index,id=roi['id'],origin=roi['origin_sensor'],
        report_sha256=sha(report_path),receipt_sha256=sha(receipt/'receipt.json'),
        edges_rgb=m['passed_edges_rgb'],cycles_rgb=m['cycle_rank_rgb'],
        admitted_geometry_sources=sum(s['admitted_all_rgb'] for s in m['sources']),
        focus_admitted_sources=0,raw_decodes=0,cache_disk_hits=report['cache_disk_hits']))
result = dict(command=sys.argv,script_sha256=sha(Path(__file__)),binary_sha256=sha(a.binary),
              plan_sha256=sha(Path(__file__).with_name('bee-repeat-plan.md')),
              phase_opportunity_sha256=sha(phase_path),rois=records,
              scope='Geometry-only Q/V originals, fixed sweep focus admission false; no repeat-compatible eligibility or candidate output. Global map and native domain conditional on all32 sources.')
with (out/f'sr-bee-{a.tag}-geometry-summary.json').open('x') as f:
    json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
