"""Three predeclared tilted-chart windows; cache-only original-CFA trials."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import tifffile

p = argparse.ArgumentParser()
p.add_argument('--binary', type=Path, required=True)
p.add_argument('--stage', choices=['measure', 'render'], required=True)
p.add_argument('--tag', required=True)
p.add_argument('--wide-geometry', action='store_true')
a = p.parse_args()
root = Path(__file__).resolve().parents[4]
out = root / 'outputs/multi-stack/completion'
arms = [
    ([2132, 1410], list(range(29, 36)) + list(range(119, 126)), [28, 36, 118, 126]),
    ([1438, 4180], list(range(69, 76)) + list(range(160, 167)), [68, 76, 159, 167]),
    ([3812, 2092], list(range(37, 44)) + list(range(128, 135)), [36, 44, 127, 135]),
]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


records = []
for roi, (origin, targets, guides) in enumerate(arms):
    destination = out / f'sr-tilted-{a.tag}-{a.stage}-roi{roi}'
    receipt = out / f'sr-tilted-run-{a.tag}-{a.stage}-roi{roi}'
    command = [str(a.binary), '--render-dir', 'outputs/multi-stack/completion/interleave-02',
               '--cache', 'outputs/multi-stack/completion/interleave-source-cache', '--out', str(destination),
               '--workers', '4', '--x', str(origin[0]), '--y', str(origin[1]), '--size', '192',
               '--assumed-registration-sigma-sensor', '0.10',
               '--focus-census', 'outputs/multi-stack/completion/sr-tilted-focus-census-01',
               '--focus-seal', 'experiments/multi-stack-2026-10-28/completion/sr/tilted-focus-census-01-seal.json',
               '--focus-roi', str(roi), '--targets', ','.join(map(str, targets)),
               '--guides', ','.join(map(str, guides)), '--measure-registration',
               '--registration-geometry-sigma-quad', '1.2', '--registration-tile-quad', '46',
               '--registration-grid-axis', '5' if a.wide_geometry else '3',
               '--registration-window-quad', '384' if a.wide_geometry else '192', '--refine-registration',
               '--registration-patch-diagnostics', '--coherent-color-motion']
    if a.stage == 'measure':
        command += ['--registration-only', '--original-patch-diagnostics']
    else:
        command += ['--require-registration', '--heldout-prediction', '--matched-comparator']
    subprocess.run([sys.executable, 'experiments/multi-stack-2026-10-28/run-command.py',
                    '--receipt', str(receipt), '--cwd', str(root), '--env', 'RAYON_NUM_THREADS=4',
                    '--', *command], cwd=root, check=True)
    name = 'local-registration-report.json' if a.stage == 'measure' else 'report.json'
    report = json.loads((destination / name).read_text())
    assert report['raw_decodes'] == 0
    record = dict(roi=roi, origin=origin, targets=targets, guides=guides,
                  report=str(destination / name), report_sha256=sha(destination / name),
                  receipt_sha256=sha(receipt / 'receipt.json'), raw_decodes=0)
    if a.stage == 'render':
        assert report['coherent_color_motion']
        mask = np.fromfile(destination / 'coherent-rgb-mask.u8', np.uint8).reshape(192, 192).astype(bool)
        native = tifffile.imread(destination / 'native.tiff')
        for candidate in ['candidate.tiff', 'matched-cfa-mhc.tiff']:
            pixels = tifffile.imread(destination / candidate)
            assert np.isfinite(pixels).all()
            assert pixels[~mask].tobytes() == native[~mask].tobytes()
        record.update(coherent_pixels=int(mask.sum()), finite=True, exact_fallback=True)
    records.append(record)
result = dict(command=sys.argv, script_sha256=sha(Path(__file__)),
              plan_sha256=sha(Path(__file__).with_name('tilted-chart-plan.md')),
              binary_sha256=sha(a.binary), arms=records)
with (out / f'sr-tilted-{a.tag}-{a.stage}-summary.json').open('x') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(json.dumps(result, indent=2))
