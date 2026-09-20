"""Independent generated adequacy/refusal fixtures; no RAW or rendered inputs."""
from pathlib import Path
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import sys

import numpy as np
from scipy.signal import fftconvolve

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('relative_blur_model', HERE / 'model.py')
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)
W = H = 256
PARAMS = (6.0, 2.5, np.pi / 6)
NOISE_DN = 5.0
CLEAN_LIMIT = np.full(4, 1.0)
NOISY_LIMIT = np.full(4, 30.0)
SEEDS = (48271, 99173)


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def serializable(v):
    if dataclasses.is_dataclass(v):
        return serializable(dataclasses.asdict(v))
    if isinstance(v, dict):
        return {str(k): serializable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [serializable(x) for x in v]
    if isinstance(v, np.ndarray):
        return serializable(v.tolist())
    if isinstance(v, np.generic):
        return serializable(v.item())
    if isinstance(v, float) and not np.isfinite(v):
        return str(v)
    return v


def box(x0, y0, x1, y1):
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = True
    return m


def psf(sa, sb, angle):
    # Independent literal rotated-axis construction, not model.kernel.
    yy, xx = np.mgrid[-24:25, -24:25]
    u = xx * np.cos(angle) + yy * np.sin(angle)
    v = -xx * np.sin(angle) + yy * np.cos(angle)
    k = np.exp(-0.5 * ((u / sa) ** 2 + (v / sb) ** 2))
    k[xx * xx + yy * yy > 24 * 24] = 0
    return k / k.sum()


def blur(a, kernel):
    return np.asarray([fftconvolve(p, kernel, mode='same') for p in a], np.float32)


def scene():
    # Native site phases [R,G1,G2,B], in quad-coordinate units.
    channels, ridge = [], []
    for c, (dx, dy) in enumerate(((0, 0), (.5, 0), (0, .5), (.5, .5))):
        y, x = np.mgrid[:H, :W].astype(np.float64)
        x += dx
        y += dy
        spot = np.exp(-((x - 63) ** 2 + (y - 58) ** 2) / (2 * 2.4 ** 2))
        env = np.exp(-.5 * (((x - 62) / 12) ** 2 + ((y - 172) / 12) ** 2))
        edge = env * (.5 + .5 * np.tanh((x - 58 + .6 * (y - 172)) / .8))
        edge *= 1 + .22 * np.cos(.8 * x + .39 * y)
        glint = np.exp(-.5 * (((x - 171) / 1.0) ** 2 + ((y - 121) / 1.4) ** 2))
        channels.append((1700 + 180 * c) * spot + (900 + 80 * c) * edge
                        + (4200, 3200, 3200, 5100)[c] * glint)
        # Real, independently coloured depth-B structure crosses the spread.
        envelope = .25 * (1 + np.tanh((y - 96) / 2)) * (1 - np.tanh((y - 186) / 2))
        line = np.exp(-.5 * ((x - 189) / .75) ** 2) * envelope
        ridge.append((1600, 350, 350, 2200)[c] * line * (1 + .4 * np.cos(.83 * y + .4 * c)))
    return np.asarray(channels, np.float32), np.asarray(ridge, np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir(parents=True)
    receipt = dict(status='RUNNING', actual_consumer_admitted=False,
                   scope='Generated model adequacy only; no ownership, RAW calibration or fusion claim',
                   kernel_params=list(PARAMS), sigma_source_target_dn=NOISE_DN,
                   clean_limit4=CLEAN_LIMIT.tolist(), noisy_limit4=NOISY_LIMIT.tolist(), records=[])

    def save():
        (out / 'screen.json').write_text(json.dumps(serializable(receipt), indent=2) + '\n')

    def check(condition, message):
        if not condition:
            receipt.update(status='REFUSED', first_failure=message)
            save()
            raise AssertionError(message)

    def trial(name, source, target, train, held, *, protected=None, clipped=None, limit=CLEAN_LIMIT):
        before = [digest(source), digest(target), digest(train), digest(held)]
        fit = model.fit(source, target, train, protected_mask=protected, clipped_mask=clipped)
        evaluation = model.evaluate(source, target, fit, held, rmse_limit4=limit,
                                    clipped_mask=clipped)
        record = dict(name=name, fit=serializable(fit), evaluation=serializable(evaluation))
        receipt['records'].append(record)
        check(before == [digest(source), digest(target), digest(train), digest(held)], 'Input mutation: ' + name)
        save()
        return fit, evaluation

    def accepted(result):
        return result['status'] == 'compatible'

    check(model.SUPPORT == 24, 'Frozen support changed')
    a, b = scene()
    kernel = psf(*PARAMS)
    background = np.full((4, H, W), 800, np.float32)
    src, dst = background + a, background + blur(a, kernel)
    train = box(38, 38, 89, 84) | box(38, 147, 89, 199)
    protected = box(130, 78, 224, 218)
    core = box(143, 93, 184, 151)
    ridge = box(186, 109, 193, 151)
    continuation = box(186, 158, 193, 183)
    # Independent stencil exclusion: dilation by the actual full square apron.
    expanded = fftconvolve(train.astype(float), np.ones((49, 49)), mode='same') > .5
    check(not np.any(expanded & protected), 'Training leaks into protected target')
    check(np.all(src > 0) and np.max(src) < 16000, 'Fixture source headroom')
    receipt['inputs'] = dict(source_sha256=digest(src), target_sha256=digest(dst),
                             training_sha256=digest(train), protected_sha256=digest(protected),
                             component_a_sha256=digest(a), component_b_sha256=digest(b))

    # Flat FIRST. Exact identity cannot supply a strict directional decision.
    flat_fit, flat = trial('flat-first', background, background.copy(), train, core, protected=protected)
    check(flat['status'] == 'ambiguous', 'Flat did not explicitly remain ambiguous')
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        nflat0 = np.rint(background + rng.normal(0, NOISE_DN, background.shape)).astype(np.float32)
        nflat1 = np.rint(background + rng.normal(0, NOISE_DN, background.shape)).astype(np.float32)
        _, nflat = trial(f'flat-independent-noise-{seed}', nflat0, nflat1, train, core,
                         protected=protected, limit=NOISY_LIMIT)
        _, nflat_reverse = trial(f'flat-independent-noise-reverse-{seed}', nflat1, nflat0,
                                 train, core, protected=protected, limit=NOISY_LIMIT)
        strict_order = ((accepted(nflat) and nflat_reverse['status'] == 'refused') or
                        (accepted(nflat_reverse) and nflat['status'] == 'refused'))
        check(not strict_order, 'Independent flat noise created an exclusive directional acceptance')
    identity_fit, identity = trial('structured-identity', src, src.copy(), train, core, protected=protected)
    check(identity['status'] == 'ambiguous', 'Identity created a strict source order')

    forward_fit, forward = trial('useful-positive', src, dst, train, core, protected=protected)
    check(accepted(forward), 'In-family held-out positive not model-compatible')
    check(max(forward['rmse4']) <= 1.0, 'Positive exceeds independent1DN held-out bar')
    check(max(forward_fit.params[:2]) < 7.99, 'Positive hit sigma ceiling')
    _, reverse = trial('wrong-direction', dst, src, train, core, protected=protected)
    check(not accepted(reverse), 'Wrong direction falsely accepted')
    check(min(reverse['rmse4']) > 10, 'Wrong-direction stimulus did not exercise discrimination')

    # Training is unchanged; same fitted operator must fail at the other depth.
    mixed_src, mixed_dst = src + blur(b, kernel), dst + b
    mixed_fit, mixed = trial('two-depth-crossing', mixed_src, mixed_dst, train, ridge, protected=protected)
    check(not accepted(mixed), 'Crossing ridge incorrectly accepted as one-depth spread')
    check(max(mixed['rmse4']) > 30, 'Crossing fixture failed to express other-depth residual')
    cont = model.evaluate(mixed_src, mixed_dst, mixed_fit, continuation, rmse_limit4=CLEAN_LIMIT)
    receipt['records'].append(dict(name='ridge-continuation-same-fit', evaluation=serializable(cont)))
    check(not accepted(cont), 'True ridge continuation incorrectly assigned to core depth')
    # Remove the disputed glint, preserving training and the real ridge.
    only_training = a.copy()
    only_training[:, 78:218, 130:224] = 0
    twin_src = background + only_training + blur(b, kernel)
    twin_dst = background + blur(only_training, kernel) + b
    _, twin = trial('no-glint-real-ridge-twin', twin_src, twin_dst, train, ridge, protected=protected)
    check(not accepted(twin), 'Real ridge accepted as glint spread in no-glint twin')

    # Nonnegative centred spectral fan: physically admissible spreading, outside
    # one shared Gaussian. This is a model-family destroyer, not a new fit family.
    yy, xx = np.mgrid[-24:25, -24:25]
    fan_planes = []
    for c, (dx, dy) in enumerate(((17, 0), (12, 7), (12, 7), (0, 17))):
        centre = np.exp(-.5 * (xx * xx + yy * yy) / 1.8 ** 2)
        positive = np.exp(-.5 * ((xx - dx) ** 2 + (yy - dy) ** 2) / 1.8 ** 2)
        negative = np.exp(-.5 * ((xx + dx) ** 2 + (yy + dy) ** 2) / 1.8 ** 2)
        fan_kernel = .4 * centre + .3 * positive + .3 * negative
        fan_kernel[xx * xx + yy * yy > 24 * 24] = 0
        fan_kernel /= fan_kernel.sum()
        fan_planes.append(fftconvolve(a[c], fan_kernel, mode='same'))
    fan_target = background + np.asarray(fan_planes, np.float32)
    _, fan = trial('coloured-fan-family-mismatch', src, fan_target, train,
                   box(144, 94, 201, 152), protected=protected)
    check(not accepted(fan), 'Out-of-family coloured fan accepted as one shared Gaussian')

    # Both inputs carry independent supplied noise; rerun fit and decision.
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        nsrc = np.rint(src + rng.normal(0, NOISE_DN, src.shape)).astype(np.float32)
        ndst = np.rint(dst + rng.normal(0, NOISE_DN, dst.shape)).astype(np.float32)
        _, noisy = trial(f'noisy-positive-{seed}', nsrc, ndst, train, core,
                         protected=protected, limit=NOISY_LIMIT)
        check(accepted(noisy), 'Noisy positive refused')
        _, noisy_reverse = trial(f'noisy-wrong-direction-{seed}', ndst, nsrc, train, core,
                                 protected=protected, limit=NOISY_LIMIT)
        check(not accepted(noisy_reverse), 'Noisy wrong direction accepted')
        # Same noise arrays, independent of frame content; no private estimate.
        msrc = mixed_src + (nsrc - src)
        mdst = mixed_dst + (ndst - dst)
        _, noisy_mixed = trial(f'noisy-crossing-{seed}', msrc, mdst, train, ridge,
                               protected=protected, limit=NOISY_LIMIT)
        check(not accepted(noisy_mixed), 'Noisy crossing assigned to the wrong depth')

    # Exact scaled copies: blur cannot silently acquire a photometric nuisance.
    _, gain = trial('gain-only', src, (1.2 * src).astype(np.float32), train, core, protected=protected)
    check(not accepted(gain), 'Gain-only copy misclassified as shared blur')
    clipped = box(167, 116, 177, 127)
    clipped_source = src.copy()
    clipped_source[:, clipped] = 16383
    _, clipping = trial('clipped-protected-core', clipped_source, dst, train, core,
                         protected=protected, clipped=clipped)
    check(not accepted(clipping), 'Clipped core accepted without an identifiable latent')
    receipt.update(status='PASS_GENERATED_ADEQUACY_ONLY', actual_consumer_admitted=False,
                   next_scope='A separately authorized retained-linear-source diagnostic only')
    save()
    print('RELATIVE_BLUR_INDEPENDENT ' + json.dumps(dict(status=receipt['status'],
          records=len(receipt['records']), actual_consumer_admitted=False)), flush=True)


if __name__ == '__main__':
    main()
