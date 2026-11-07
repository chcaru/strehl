"""Geometry-only phase opportunity on frozen bee witnesses and Q/V identities.

No original samples, focus admission, local geometry certificate or R/M assay
are read. The existing global map used all32 sources and is not score-blind.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import numpy as np


def conditions(points, pulls, color, full):
    center = complex(*full) + .5+.5j
    gram = np.zeros((len(points), 4, 4), complex)
    total = np.zeros(len(points))
    frequencies = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    for a, b in pulls:
        source = a*(points-center) + 2*b + center
        fx, fy = np.floor(source.real).astype(int), np.floor(source.imag).astype(int)
        radius = int(np.ceil(2*abs(a))) + 1
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                x, y = fx+dx, fy+dy
                kind = np.where((x%2==0)&(y%2==0), 0,
                                np.where((x%2==1)&(y%2==1), 2, 1))
                d = (x+1j*y-center-2*b)/a + center - points
                squared = d.real*d.real + d.imag*d.imag
                valid = (kind==color)&(squared<=4)&(x>=0)&(y>=0)&(x<2*full[0])&(y<2*full[1])
                if not valid.any():
                    continue
                w = np.exp(-.5*squared[valid]/(.35**2))
                ds = np.column_stack([d.real[valid], d.imag[valid]])
                v = np.exp(1j*np.pi*(ds@frequencies.T))
                gram[valid] += np.einsum('n,ni,nj->nij', w, v.conj(), v)
                total[valid] += w
    eigenvalues = np.linalg.eigvalsh(gram/np.maximum(total[:,None,None], 1e-300))
    result = np.full(len(points), np.inf)
    good = eigenvalues[:,0] > 1e-6
    result[good] = np.sqrt(eigenvalues[good,-1]/eigenvalues[good,0])
    return result


def controls():
    points = np.array([100+100j, 101+100j, 100+101j, 101+101j])
    duplicate = [(1+0j, 0j)]*16
    phases = [(1+0j, (x+1j*y)/4) for y in range(4) for x in range(4)]
    rows = []
    for color in [0, 1, 2]:
        same = conditions(points, duplicate, color, [256,256])
        rich = conditions(points, phases, color, [256,256])
        assert np.all(same>20)
        assert np.all(rich<=20), rich
        rows.append(dict(color=color, phased_condition=rich.tolist(), duplicate_refused=True))
    return rows


p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, required=True)
p.add_argument('--registered-prefix', type=Path, help='Read all nine fixed geometry-only reports; no image or admission is created')
a = p.parse_args()
checks = controls()  # Before real saved-map inspection.
root = Path(__file__).resolve().parents[4]
base = root/'outputs/multi-stack/completion/noise-bee-repeat-01'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inputs = dict(alignment=base/'alignment.json', identities=base/'equal/source-identities.json',
              calibration=base/'equal/calibration.json', witnesses=base/'inspection/equal/receipt.json')
alignment = json.loads(inputs['alignment'].read_text())
ids = json.loads(inputs['identities'].read_text())
cal = json.loads(inputs['calibration'].read_text())
witnesses = json.loads(inputs['witnesses'].read_text())['witnesses']
ordinals = [int(re.search(r'DSC(\d+)\.ARW$', s['path']).group(1))-328 for s in ids]
assert sorted(ordinals)==list(range(32))
qv = [i for i,k in enumerate(ordinals) if k%8 in {0,1,6,7}]
assert qv==[0,3,4,7,8,11,12,15,16,19,20,23,24,27,28,31]
# Frozen by chronology: first/last Q/V are guides, all remaining14 are targets.
guides = [ordinals.index(0), ordinals.index(31)]
targets = sorted(set(qv)-set(guides), key=ordinals.__getitem__)
assert len(targets)==14 and all(ordinals[i]%8 in {0,1,6,7} for i in targets+guides)
maps = {}
for line in alignment['warpmap'].splitlines():
    parts = line.split()
    if parts[0]=='plane':
        full = [int(v) for v in parts[1].split('x')]
    if len(parts)>=6 and parts[0].isdigit() and parts[1]=='placed':
        v = [struct.unpack('>d',bytes.fromhex(x))[0] for x in parts[2:6]]
        maps[int(parts[0])] = (complex(*v[:2]),complex(*v[2:]))
assert len(maps)==32
assert cal[0]['optical_profile']==cal[1]['optical_profile']
profile = cal[0]['optical_profile']
results = []
for roi, witness in enumerate(witnesses):
    ox, oy = np.array(witness['origin_full_sensor']) + 96
    # Fixed5x5 locations, each with all four integer output parities.
    points = np.array([ox+x+px+1j*(oy+y+py) for y in [16,48,80,112,144]
                       for x in [16,48,80,112,144] for py in [0,1] for px in [0,1]])
    rows = []
    for color, eps in enumerate([profile['eps_r'],0.,profile['eps_b']]):
        pulls = [(maps[i][0]*(1+eps),maps[i][1]*(1+eps)) for i in targets]
        rows.append(conditions(points,pulls,color,full))
    values = np.column_stack(rows)
    row = dict(id=witness['id'], origin_sensor=[int(ox),int(oy)],
                        tested_points=len(points), phase_pass_rgb=np.sum(values<=20,axis=0).tolist(),
                        phase_pass_all_rgb=int(np.all(values<=20,axis=1).sum()),
                        finite_condition_percentiles_rgb=[np.percentile(v[np.isfinite(v)],[0,50,100]).tolist()
                            if np.isfinite(v).any() else [] for v in rows])
    if a.registered_prefix:
        path = Path(str(a.registered_prefix)+str(roi))/'local-registration-report.json'
        envelope = json.loads(path.read_text())
        m = envelope['measurement']
        assert envelope['focus_not_evaluated_geometry_only'] is True and envelope['raw_decodes']==0
        assert envelope['alignment_sha256']==sha(inputs['alignment'])
        assert m['full_geometry_quad']==full and m['roi_sensor_origin']==[int(ox),int(oy)]
        assert m['roi_output_dimensions']==[192,192]
        assert {s['acquisition'] for s in m['sources']}==set(targets)
        assert {s['global_index'] for s in envelope['source_identities']}==set(targets)
        assert all(s['source']['sha256']==ids[s['global_index']]['sha256']
                   and s['focus_usable_pixels']==0 and s['focus_weight_sum']==0
                   for s in envelope['source_identities'])
        selected = [s for s in m['sources'] if s['admitted_all_rgb']]
        assert all(all(s['admitted_rgb']) for s in selected)
        registered_rows=[]
        for color in range(3):
            pulls=[(complex(*s['consuming_color_pulls'][color]['a']),
                    complex(*s['consuming_color_pulls'][color]['b'])) for s in selected]
            registered_rows.append(conditions(points,pulls,color,full))
        registered_values=np.column_stack(registered_rows)
        row['registered']=dict(report_sha256=sha(path),measurement_sha256=m['measurement_sha256'],
            graph_sha256=m['graph_sha256'],coherent_geometry_sources=[s['acquisition'] for s in selected],
            phase_pass_rgb=np.sum(registered_values<=20,axis=0).tolist(),
            phase_pass_all_rgb=int(np.all(registered_values<=20,axis=1).sum()),
            finite_condition_percentiles_rgb=[np.percentile(v[np.isfinite(v)],[0,50,100]).tolist()
                if np.isfinite(v).any() else [] for v in registered_rows],
            scope='Only original-held/loop-qualified corrected geometry. No repeat eligibility, original clipping, actual precision, optical bandwidth or candidate image.')
    results.append(row)
result = dict(schema='strehl.bee-phase-opportunity.v1', command=sys.argv,
              script_sha256=sha(Path(__file__)), controls=checks,
              inputs={k:sha(v) for k,v in inputs.items()}, targets=targets, guides=guides,
              target_identities=[ids[i] for i in targets], target_chronological_ordinals=[ordinals[i] for i in targets],
              full_geometry_quad=full, rois=results,
              scope='DERIVED geometry-only positiveGaussian.35sensor phase opportunity. Uniform relative precision; samecamera/exposure. No actual guide, clipping, motion, PSF/focus or measured local placement admission. Jointmap conditioned on all32 originals. Q/V-only selected identities; R/M assay photons not read. Neither photographic gain nor plateau eligibility follows.')
with a.out.open('x') as f:
    json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({'controls':checks,'rois':results},indent=2))
