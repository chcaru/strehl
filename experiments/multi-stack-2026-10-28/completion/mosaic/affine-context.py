"""Orientation-only overview of saved guide coordinates; no RAW or quality score."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '4'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('run', type=Path)
parser.add_argument('guides', type=Path)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(exist_ok=False, parents=True)
native_path = args.run / 'mosaic-native-measurements.json'
native = json.loads(native_path.read_text())
accepted = [r for r in native if r['accepted']]
images = []
headers = []
dtype = np.dtype({'names': ['intensity', 'covered'], 'formats': ['<f4', 'u1'],
                 'offsets': [0, 4], 'itemsize': 46})
for pass_id in range(2):
    with (args.guides / f'guide-{pass_id}.bin').open('rb') as stream:
        prefix = stream.read(12)
        assert prefix[:8] == b'STRHGUI1'
        header = json.loads(stream.read(struct.unpack('<I', prefix[8:])[0]))
        data = np.frombuffer(stream.read(), dtype=dtype)
    w, h = header['receipt']['guide_geometry']
    assert len(data) == w * h
    images.append(data['intensity'].reshape(h, w))
    headers.append(header)
lo, hi = np.percentile(np.concatenate([a.ravel() for a in images]), [1, 99.5])
fig, axes = plt.subplots(1, 2, figsize=(17.58, 6.6), dpi=100)
rows = []
for pass_id, (axis, values) in enumerate(zip(axes, images)):
    axis.imshow(np.clip((values-lo)/(hi-lo), 0, 1)**0.5, cmap='gray', vmin=0, vmax=1)
    axis.set_title(f'Pass {pass_id}: diagnostic focus guide, orientation only')
    step = headers[pass_id]['receipt']['step_quad_pixels']
    offset = (step-1)*0.5
    for index, row in enumerate(accepted):
        c = row['candidate']
        q = c['point_a_quad'] if pass_id == 0 else row['refined_b_quad']
        p = (np.array(q)-offset)/step
        color = '#40e7ff' if c['role'] == 'heldout' else '#ffbd38'
        axis.plot(*p, marker='o', markersize=6, fillstyle='none', color=color)
        axis.annotate(str(index), p, xytext=(5, 4), textcoords='offset points', color=color, fontsize=10)
        if pass_id == 0:
            rows.append({'number': index, 'id': c['id'], 'role': c['role'],
                         'sources': [c['source_a'], c['source_b']],
                         'pass_anchor_quad': [c['point_a_quad'], row['refined_b_quad']]})
    axis.set_xlim(0, values.shape[1]-1)
    axis.set_ylim(values.shape[0]-1, 0)
    axis.set_axis_off()
fig.suptitle('Native accepted correspondences: gold FIT, cyan heldout. Numbers identify pairs; this overview is not a photograph or a geometry certificate.')
fig.tight_layout()
fig.savefig(args.out / 'accepted-context.png')
record = {'schema': 'strehl.mosaic-correspondence-context.v1', 'rows': rows,
          'native_sha256': hashlib.sha256(native_path.read_bytes()).hexdigest(),
          'display': {'shared_dn_limits': [lo, hi], 'gamma': 0.5, 'scope': 'resized orientation only'},
          'guide_receipts': headers}
(args.out / 'receipt.json').write_text(json.dumps(record, indent=2)+'\n')
