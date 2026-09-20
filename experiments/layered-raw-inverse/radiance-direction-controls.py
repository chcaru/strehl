"""Export fixed truth directions and score saved directional images; never fit."""
from pathlib import Path
import argparse
import importlib.util
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('direction_helpers', HERE / 'visibility-oracle-controls.py')
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)
sha, read, inventory = helpers.sha, helpers.read, helpers.inventory
LABELS = ['glint', 'shifted-glint']


def directions(control):
    latent = control.scene('layered')
    assert np.all(latent['alpha'] <= np.float32(.95))
    glint = (latent['glint_template'] / (np.float32(1) - latent['alpha'][..., None])).astype(np.float32)
    shifted = np.zeros_like(glint)
    shifted[:, 20:] = glint[:, :-20]
    assert np.count_nonzero(glint) > 0 and np.all(shifted[:, :20] == 0)
    return latent, {'glint': glint, 'shifted-glint': shifted}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'score'])
    parser.add_argument('--source', type=Path, default=HERE / 'screen-1' / 'output')
    parser.add_argument('--checkpoint', type=Path, default=HERE / 'visibility-1' / 'output' / 'layered' / 'fixed-alpha')
    parser.add_argument('--directions', type=Path)
    parser.add_argument('--diagnostic', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    assert not out.exists()
    control = helpers.frozen(source)
    latent, fields = directions(control)
    original = inventory(source)
    assert np.array_equal(latent['truth'], np.load(source / 'layered' / 'truth-rgb-f32.npy', allow_pickle=False))
    for field in fields.values():
        assert field.dtype == np.float32 and field.shape == (96, 96, 3) and np.isfinite(field).all() and (field >= 0).all()
    if args.mode == 'prepare':
        out.mkdir(parents=True)
        rows = []
        for label, field in fields.items():
            path = out / f'{label}-dn.npy'
            np.save(path, field, allow_pickle=False)
            rows.append(dict(label=label, path=str(path), sha256=sha(path), array_sha256=control.digest(field)))
        result = dict(status='PHYSICAL_FAR_DIRECTIONS_PREPARED', directions=rows, shift_native_xy=[20, 0], zero_fill=True,
                      controls_sha256=helpers.CONTROL_HASH, model_sha256=helpers.MODEL_HASH, exporter_sha256=sha(__file__),
                      source_root=str(source), units='black-subtracted far-sheet camera RGB DN; no observed inputs exported')
        assert inventory(source) == original
        control.save(out / 'manifest.json', result)
    else:
        assert args.directions is not None and args.diagnostic is not None
        checkpoint, supplied, diagnostic = args.checkpoint.resolve(), args.directions.resolve(), args.diagnostic.resolve()
        roots = [checkpoint, supplied, diagnostic]
        before = [inventory(p) for p in roots]
        manifest = read(supplied / 'manifest.json')
        assert manifest['controls_sha256'] == helpers.CONTROL_HASH and manifest['model_sha256'] == helpers.MODEL_HASH
        assert manifest['exporter_sha256'] == sha(__file__)
        assert [r['label'] for r in manifest['directions']] == LABELS
        for row in manifest['directions']:
            path = supplied / f"{row['label']}-dn.npy"
            assert sha(path) == row['sha256'] and np.array_equal(np.load(path, allow_pickle=False), fields[row['label']])
        with np.load(checkpoint / 'reconstruction.npz', allow_pickle=False) as saved:
            fixed_base = saved['pinhole_rgb'].copy()
            assert np.array_equal(saved['alpha'], latent['alpha'])
            positive_scale = latent['alpha'][..., None] * np.abs(saved['near_rgb']) + (1 - latent['alpha'][..., None]) * np.abs(saved['far_rgb'])
        base = np.load(diagnostic / 'base-pinhole-rgb-f32.npy', allow_pickle=False)
        assert np.array_equal(base, fixed_base)
        references = [np.load(source / 'layered' / f'{label}-rgb-f32.npy', allow_pickle=False)
                      for label in ['far-only', 'mean', 'oracle-bound']]
        def measure(image):
            assert image.dtype == np.float32 and image.shape == (96, 96, 3) and np.isfinite(image).all()
            return dict(quality=control.quality('layered', latent, image, *references), rgb_sha256=control.digest(image),
                        core=control.score(image, latent['truth'], 'core'),
                        glint=control.component(image, latent, 'glint', 'core'),
                        filament=control.component(image, latent, 'ridge', 'ridge-detail'))
        baseline, rows = measure(base), []
        unit = np.finfo(np.float32).eps / 2
        gamma16 = np.float32(16 * unit / (1 - 16 * unit))
        for label in LABELS:
            variants = {}
            for name, sign in [('minus', -1), ('plus', 1)]:
                image = np.load(diagnostic / label / f'{name}-pinhole-rgb-f32.npy', allow_pickle=False)
                delta = np.float32(sign * .001) * (np.float32(1) - latent['alpha'][..., None]) * fields[label]
                error = np.abs(image - (base + delta))
                bound = gamma16 * (positive_scale + np.abs(delta) + np.float32(1))
                assert np.all(error <= bound), 'saved output is not the prescribed physical far-sheet perturbation'
                variants[name] = dict(**measure(image), literal_perturbation_max_bound_fraction=float(np.max(error / bound)))
            recovery, previous = np.array(variants['plus']['glint']['recovery']), np.array(baseline['glint']['recovery'])
            rows.append(dict(label=label, **variants,
                plus_core_rgb_improves=variants['plus']['core']['rgb_rmse'] < baseline['core']['rgb_rmse'],
                plus_core_chroma_improves=variants['plus']['core']['chroma_rmse'] < baseline['core']['chroma_rmse'],
                plus_glint_component_toward_truth=bool(np.all(np.abs(recovery - 1) < np.abs(previous - 1)))))
        assert inventory(source) == original and [inventory(p) for p in roots] == before
        result = dict(status='DIRECTIONAL_IMAGES_SCORED', base=baseline, directions=rows,
            derivative_diagnostic=read(diagnostic / 'result.json'), source_immutable=True, diagnostic_immutable=True,
            source_files=original, checkpoint_files=before[0], direction_files=before[1], diagnostic_files=before[2],
            scorer_sha256=sha(__file__), real_photo_admission=False,
            interpretation='Truth improvement and objective derivatives are separate. Shift is a specificity placebo, not a required negative outcome; no optimizer or model-family verdict.')
        out.mkdir(parents=True)
        control.save(out / 'result.json', result)
    print('RADIANCE_DIRECTION_' + args.mode.upper(), result['status'], flush=True)


if __name__ == '__main__':
    main()
