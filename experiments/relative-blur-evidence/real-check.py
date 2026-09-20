"""Six frozen descriptive fits of immutable actual consumer witnesses."""
from pathlib import Path
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('relative_actual_model', HERE / 'model.py')
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)

PAIRS = (
    ('facet', 'facet-edges', 28, 69, [248, 252, 16, 10],
     [('extension', [240, 272, 12, 12]), ('adjacent', [268, 272, 20, 20])]),
    ('dark', 'dark-inclusion', 33, 69, [248, 252, 16, 10],
     [('column', [250, 283, 12, 12]), ('fan', [261, 278, 12, 12]), ('structure', [328, 210, 16, 16])]),
    ('nearby', 'dark-inclusion', 25, 33, [328, 212, 16, 10],
     [('continuation', [328, 224, 16, 16]), ('column', [250, 283, 12, 12])]),
)


def ref(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def box(rect):
    x, y, w, h = rect
    mask = np.zeros((512, 512), bool)
    mask[y:y+h, x:x+w] = True
    assert mask.sum() == w*h and np.all(model.valid_mask(mask.shape)[mask])
    return mask


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--witness', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out, witness = args.out.resolve(), args.witness.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    completion_path = witness / 'completion.json'
    completion = json.loads(completion_path.read_text())
    assert completion['retained_consumer_exact']
    receipt_path = witness / 'output/receipt.json'
    assert ref(receipt_path) == completion['receipt']
    receipt = json.loads(receipt_path.read_text())
    bindings = [ref(completion_path), ref(receipt_path), ref(HERE / 'model.py'),
                ref(HERE / 'real-plan.md'), ref(Path(__file__))]
    fields = {}
    for group in receipt['groups']:
        for artifact in group['artifacts']:
            field = artifact['known4']
            path = witness / 'output' / field['path']
            binding = ref(path)
            assert binding['sha256'] == field['sha256'] and field['shape'] == [4, 512, 512]
            array = np.fromfile(path, dtype='<f4').reshape(4, 512, 512)
            assert np.isfinite(array).all()
            fields[group['source_index0'], artifact['region']] = array
            bindings.append(binding)
    for _, _, _, _, train_rect, targets in PAIRS:
        train = box(train_rect)
        assert all(not np.any(train & box(rect)) for _, rect in targets)
    out.mkdir()
    result = dict(schema=1, status='RUNNING', image_quality_claim=False,
                  ownership_claim=False, native_noise_calibration=False,
                  split='disjoint target values; observed source stencils may overlap',
                  bindings=bindings, cases=[])

    def save():
        (out / 'result.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    save()
    for name, region, first, second, train_rect, targets in PAIRS:
        for source_id, target_id in ((first, second), (second, first)):
            start = time.monotonic()
            source, target = fields[source_id, region], fields[target_id, region]
            train = box(train_rect)
            fitted = model.fit(source, target, train)
            prediction = model.predict(source, fitted.params)
            case = dict(name=name, source_id=source_id, target_id=target_id,
                        train_quad_xywh=train_rect, fit=dataclasses.asdict(fitted), held=[])
            for label, rect in targets:
                mask = box(rect)
                error = model.error(source, target, fitted.params, mask)
                identity = model.error(source, target, (0., 0., 0.), mask)
                x, y, w, h = rect
                stem = f'{name}-{source_id:02}-{target_id:02}-{label}'
                prediction_path = out / (stem + '-prediction.f32')
                residual_path = out / (stem + '-residual.f32')
                predicted = prediction[:, y:y+h, x:x+w].copy()
                residual = predicted - target[:, y:y+h, x:x+w]
                assert np.isfinite(predicted).all() and np.isfinite(residual).all()
                predicted.tofile(prediction_path)
                residual.tofile(residual_path)
                case['held'].append(dict(label=label, quad_xywh=rect, shape=[4, h, w],
                    rmse4_dn=error, identity_rmse4_dn=identity,
                    prediction=ref(prediction_path), signed_residual=ref(residual_path)))
            case['seconds'] = time.monotonic()-start
            result['cases'].append(case)
            save()
            print(json.dumps(dict(name=name, source=source_id, target=target_id,
                                  status=fitted.status, seconds=case['seconds'])), flush=True)
    assert all(ref(Path(row['path'])) == row for row in bindings)
    result.update(status='COMPLETE_DESCRIPTIVE_ONLY', bindings_unchanged=True)
    save()


if __name__ == '__main__':
    main()
