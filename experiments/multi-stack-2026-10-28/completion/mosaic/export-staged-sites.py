"""Export the actual Rust-selected sites from a staged geometry receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('run', type=Path)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
stage = args.run / 'stage-2'
paths = dict(native=stage/'mosaic-native-measurements.json',
             selection=stage/'independent-native-sites.json',
             binding=stage/'binding.json',
             sources=args.run/'source-identities.json',
             plan=args.run/'frozen-role-plan.json')
assert all(path.stat().st_size < 128 << 20 for path in paths.values())
data = {key: json.loads(path.read_text()) for key, path in paths.items()}
assert data['binding']['sources'] == data['sources']
assert data['binding']['config']['role_plan'] == data['plan']
indices = data['selection']['receipt_indices']
assert len(indices) == len(set(indices))
assert all(0 <= i < len(data['native']) for i in indices)
records = [dict(receipt_index=i, receipt=data['native'][i]) for i in indices]
assert all(row['receipt']['accepted'] for row in records)
fit = sum(row['receipt']['candidate']['role'] == 'fit' for row in records)
held = sum(row['receipt']['candidate']['role'] == 'heldout' for row in records)
assert fit == data['selection']['fit'] and held == data['selection']['held']
assert fit + held == len(records)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = dict(schema='strehl.mosaic-independent-sites.v1', command=sys.argv,
              script_sha256=sha(Path(__file__)),
              source_bindings={key: sha(path) for key, path in paths.items()},
              passes=2, sources=len(data['sources']), fit_sites=fit,
              heldout_sites=held, measured_loops=len(records), records=records,
              claim='Export of actual Rust physical-support-selected sites; no new selection, image measurement, fitting or photographic claim.')
with args.out.open('x') as out:
    json.dump(result, out, indent=2)
    out.write('\n')
print(json.dumps(dict(fit=fit, held=held, output=str(args.out)), indent=2))
