"""Root-executed, independent known-optics utility screen. No real RAW input.

The generator does not call the model forward. Image arrays are float32 and
original observations uint16. Only scalar score reductions use float64.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import sys

import numpy as np
from scipy import ndimage
import torch

HERE = Path(__file__).resolve().parent
WIDTH = HEIGHT = 96
FOCI = tuple(i / 8 for i in range(9))
TRAIN = (0, 1, 3, 4, 5, 7, 8)
HELD = (2, 6)
DEPTHS = (1.0, 0.0)
SCALE = np.float32(12)
SIGMA = np.float32(.7)
BLACK = 512
CEILING = 16383
METADATA_WHITE = 15360
GAIN = np.float32(100 / 436.8)
READ_VARIANCE = np.float32((np.float32(4.2) * GAIN) ** 2)
MARGIN = 16
Y, X = np.mgrid[:HEIGHT, :WIDTH].astype(np.float32)
REGIONS = {
    'whole': (16, 16, 80, 80), 'core': (39, 42, 52, 55),
    'ridge': (39, 31, 63, 70), 'crossing': (40, 42, 57, 58),
    'fan': (28, 33, 66, 65),
}
RIDGE_DETAIL = (39, 31, 63, 41)  # Predata glint-free segment; RGB regions stay unchanged.


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    return value


def pupil_pairs(count=64):
    assert count > 0 and count % 2 == 0
    j = np.arange(count // 2, dtype=np.float32)
    radius = np.sqrt((j + np.float32(.5)) / np.float32(count // 2))
    theta = j * np.float32(math.pi * (3 - math.sqrt(5))) + np.float32(.37)
    points = np.stack((radius * np.cos(theta), radius * np.sin(theta)), axis=1)
    return np.concatenate((points, -points), axis=0).astype(np.float32)


class TrainingOnly:
    """Refuse heldout reads during the actual fit, including initialization."""
    def __init__(self, source):
        self.source = source
        self.dtype, self.shape = source.dtype, source.shape
        self.reads = []

    def __len__(self):
        return len(self.source)

    def __getitem__(self, index):
        if not isinstance(index, (int, np.integer)) or int(index) not in TRAIN:
            raise AssertionError('fit tried to read nontraining observation: ' + str(index))
        self.reads.append(int(index))
        view = self.source[int(index)].view()
        view.flags.writeable = False
        return view

    def __array__(self, *args, **kwargs):
        raise AssertionError('fit tried to materialize all observations')


def sample(image, dx, dy):
    coords = np.stack((Y + np.float32(dy), X + np.float32(dx)))
    if image.ndim == 2:
        return ndimage.map_coordinates(image, coords, order=1, mode='nearest', prefilter=False)
    return np.stack([ndimage.map_coordinates(image[..., c], coords, order=1,
                     mode='nearest', prefilter=False) for c in range(3)], axis=-1)


def psf(image):
    # Explicit normalized discrete support, implemented independently of torch.
    radius = math.ceil(4 * float(SIGMA))
    sites = np.arange(-radius, radius + 1, dtype=np.float32)
    kernel = np.exp(-np.float32(.5) * (sites / SIGMA) ** 2).astype(np.float32)
    kernel /= np.sum(kernel, dtype=np.float32)
    return ndimage.convolve1d(ndimage.convolve1d(image, kernel, axis=0,
             mode='nearest'), kernel, axis=1, mode='nearest').astype(np.float32)


def independent_forward(near, far, alpha, focus, *, pupil=None, angular=False,
                        wrong_separate_visibility=False):
    """Finite-pixel premultiplied near layer; same pupil ray for both depths."""
    points = pupil_pairs() if pupil is None else np.asarray(pupil, dtype=np.float32)
    assert near.shape == far.shape == (HEIGHT, WIDTH, 3)
    assert alpha.shape == (HEIGHT, WIDTH)
    premult = alpha[..., None] * near
    out = np.zeros_like(near, dtype=np.float32)
    avg_near = np.zeros_like(near, dtype=np.float32)
    avg_alpha = np.zeros_like(alpha, dtype=np.float32)
    avg_far = np.zeros_like(far, dtype=np.float32)
    for ux, uy in points:
        near_shift = SCALE * np.float32(focus - DEPTHS[0])
        far_shift = SCALE * np.float32(focus - DEPTHS[1])
        a = sample(alpha, near_shift * ux, near_shift * uy)
        n = sample(premult, near_shift * ux, near_shift * uy)
        b = sample(far, far_shift * ux, far_shift * uy)
        if angular:
            b = b * (np.float32(1) + np.float32(.55) * ux)
        if wrong_separate_visibility:
            avg_near += n
            avg_alpha += a
            avg_far += b
        else:
            out += n + (np.float32(1) - a[..., None]) * b
    inv = np.float32(1 / len(points))
    if wrong_separate_visibility:
        out = avg_near * inv + (np.float32(1) - avg_alpha[..., None] * inv) * (avg_far * inv)
    else:
        out *= inv
    assert out.dtype == np.float32 and np.isfinite(out).all()
    return psf(out)


def cfa_numpy(rgb):
    out = np.empty((HEIGHT, WIDTH), np.float32)
    out[0::2, 0::2] = rgb[0::2, 0::2, 0]
    out[0::2, 1::2] = rgb[0::2, 1::2, 1]
    out[1::2, 0::2] = rgb[1::2, 0::2, 1]
    out[1::2, 1::2] = rgb[1::2, 1::2, 2]
    return out


def develop_bilinear(raw):
    """Independent simple CFA development, shared by mean and donor bound."""
    signal = raw.astype(np.float32) - np.float32(BLACK)
    mask = np.zeros((HEIGHT, WIDTH, 3), np.float32)
    mask[0::2, 0::2, 0] = 1
    mask[0::2, 1::2, 1] = mask[1::2, 0::2, 1] = 1
    mask[1::2, 1::2, 2] = 1
    kernel = np.array([1, 2, 1], np.float32)
    filt = lambda a: ndimage.convolve1d(ndimage.convolve1d(a, kernel, axis=0,
                   mode='nearest'), kernel, axis=1, mode='nearest')
    return (filt(signal[..., None] * mask) / filt(mask)).astype(np.float32)


def scene(name):
    base = np.broadcast_to(np.array([2200, 2600, 1800], np.float32),
                           (HEIGHT, WIDTH, 3)).copy()
    ripple = np.float32(130) * np.cos(np.float32(2 * math.pi / 27) *
               (np.float32(.8) * X + np.float32(.6) * Y))
    far_bg = base + ripple[..., None]
    spot = np.exp(-np.float32(.5) * (((X - 45) / np.float32(1.45)) ** 2 +
                                   ((Y - 48) / np.float32(1.45)) ** 2))
    glint = spot[..., None] * np.array([28000, 27000, 24000], np.float32)
    far = far_bg + glint
    dx, dy = X - 49, Y - 49
    extent = np.exp(-np.float32(.5) * (dx * dx + dy * dy) / np.float32(23 ** 2))
    lines = np.stack([
        np.exp(-np.float32(.5) * (dx / np.float32(.95)) ** 2),
        np.exp(-np.float32(.5) * ((np.float32(.65) * dx + np.float32(.76) * dy) / np.float32(1.05)) ** 2),
        np.float32(.7) * np.exp(-np.float32(.5) * ((np.float32(-.8) * dx + np.float32(.6) * dy) / np.float32(1.1)) ** 2),
    ], axis=-1) * extent[..., None]
    total = np.sum(lines, axis=-1, dtype=np.float32)
    alpha = np.minimum(np.float32(.95), np.float32(.92) * total)
    colours = np.array([[850, 6200, 1900], [4700, 1200, 5600], [1500, 2700, 6800]], np.float32)
    near = np.einsum('hwk,kc->hwc', lines, colours, dtype=np.float32) / np.maximum(total[..., None], np.float32(1e-8))
    if name == 'flat':
        far = np.broadcast_to(np.array([2500, 3200, 2000], np.float32), far.shape).copy()
        near = far.copy()
        alpha.fill(np.float32(.35))
        glint.fill(0)
        far_bg = far.copy()
    elif name == 'far-only':
        alpha.fill(0)
    elif name not in ('layered', 'angular-mismatch'):
        raise ValueError(name)
    truth = alpha[..., None] * near + (np.float32(1) - alpha[..., None]) * far
    no_glint = alpha[..., None] * near + (np.float32(1) - alpha[..., None]) * far_bg
    no_ridge = far.copy()
    return dict(near=near.astype(np.float32), far=far.astype(np.float32),
                alpha=alpha.astype(np.float32), truth=truth.astype(np.float32),
                glint_template=(truth - no_glint).astype(np.float32),
                ridge_template=(truth - no_ridge).astype(np.float32))


def observation(signal, seed):
    assert signal.dtype == np.float32 and np.all(signal >= 0) and np.isfinite(signal).all()
    rng = np.random.default_rng(seed)
    electrons = rng.poisson(signal / GAIN)
    measured = (electrons.astype(np.float32) * GAIN +
                rng.normal(0, math.sqrt(float(READ_VARIANCE)), signal.shape).astype(np.float32) + np.float32(BLACK))
    return np.clip(np.rint(measured), 0, CEILING).astype(np.uint16)


def dataset(name, number):
    latent = scene(name)
    raw = np.empty((9, HEIGHT, WIDTH), np.uint16)
    expected = np.empty((9, HEIGHT, WIDTH), np.float32)
    oracle = np.zeros_like(latent['truth'])
    oracle_indices = np.full((HEIGHT, WIDTH), -1, np.int16)
    best = np.full((HEIGHT, WIDTH), np.inf, np.float32)
    for k, focus in enumerate(FOCI):
        rgb = independent_forward(latent['near'], latent['far'], latent['alpha'], focus,
                                  angular=name == 'angular-mismatch')
        expected[k] = cfa_numpy(rgb) + np.float32(BLACK)
        raw[k] = observation(expected[k] - np.float32(BLACK), 20260919 + number * 1000 + k)
        if k in TRAIN:
            # The oracle may use truth, but neither noisy nor noiseless heldout input.
            error = np.mean((rgb - latent['truth']) ** 2, axis=-1, dtype=np.float32)
            use = error < best
            developed = develop_bilinear(raw[k])
            oracle[use] = developed[use]
            oracle_indices[use] = k
            best[use] = error[use]
    assert np.isin(oracle_indices, TRAIN).all()
    mean_raw = np.mean(raw[list(TRAIN)].astype(np.float32), axis=0, dtype=np.float32)
    return latent, raw, expected, develop_bilinear(mean_raw), oracle, oracle_indices


def region_slice(name):
    x0, y0, x1, y1 = RIDGE_DETAIL if name == 'ridge-detail' else REGIONS[name]
    return np.s_[y0:y1, x0:x1]


def score(image, truth, region='whole'):
    delta = image[region_slice(region)].astype(np.float64) - truth[region_slice(region)].astype(np.float64)
    return dict(rgb_rmse=float(np.sqrt(np.mean(delta ** 2))),
                chroma_rmse=float(np.sqrt(np.mean(np.stack((delta[..., 0] - delta[..., 1],
                                      delta[..., 2] - delta[..., 1]), -1) ** 2))))


def component(image, latent, name, region):
    template = latent[name + '_template'][region_slice(region)].astype(np.float64)
    absent = (latent['truth'] - latent[name + '_template'])[region_slice(region)].astype(np.float64)
    value = image[region_slice(region)].astype(np.float64) - absent
    denominator = np.sum(template ** 2, axis=(0, 1))
    live = denominator > 100
    recovery = np.divide(np.sum(value * template, axis=(0, 1)), denominator,
                         out=np.zeros(3), where=live)
    return dict(recovery=recovery.tolist(), template_energy=denominator.tolist(), live=bool(live.all()))


def metric_commission():
    latent = scene('layered')
    truth = latent['truth']
    records = {}
    for name, region in [('glint', 'core'), ('ridge', 'ridge-detail')]:
        half = truth - np.float32(.5) * latent[name + '_template']
        correct = component(truth, latent, name, region)
        wrong = component(half, latent, name, region)
        assert correct['live'] and np.max(np.abs(np.array(correct['recovery']) - 1)) < 1e-6
        assert np.max(np.abs(np.array(wrong['recovery']) - .5)) < 1e-5
        assert score(half, truth, region)['rgb_rmse'] > 100
        records[name] = dict(exact=correct, half_destroyer=wrong,
                             bounds=list(RIDGE_DETAIL if region == 'ridge-detail' else REGIONS[region]))
    wrong_colour = truth[..., [2, 1, 0]].copy()
    assert score(wrong_colour, truth, 'ridge')['chroma_rmse'] > 100
    records['wrong_colour'] = score(wrong_colour, truth, 'ridge')
    return records


def tensor(a, device):
    return torch.as_tensor(a, dtype=torch.float32, device=device)


def mechanical(model, config):
    device = config.device
    latent = scene('layered')
    pupil = pupil_pairs(8)
    errors = {}
    interior = region_slice('whole')
    for name, a in [('alpha0', np.zeros((HEIGHT, WIDTH), np.float32)),
                    ('alpha1', np.ones((HEIGHT, WIDTH), np.float32)),
                    ('layered', latent['alpha'])]:
        independent = independent_forward(latent['near'], latent['far'], a, FOCI[4], pupil=pupil)
        with torch.no_grad():
            actual = model.forward(tensor(latent['near'], device), tensor(latent['far'], device),
                      tensor(a, device), config, 4, pupil=tensor(pupil, device)).cpu().numpy()
        err = float(np.max(np.abs(actual[interior] - independent[interior])))
        assert err <= .1, (name, err)
        errors[name] = err
    constant = np.broadcast_to(np.array([2500, 3200, 2000], np.float32), (HEIGHT, WIDTH, 3)).copy()
    with torch.no_grad():
        actual = model.forward(tensor(constant, device), tensor(constant, device),
                 tensor(latent['alpha'], device), config, 4, pupil=tensor(pupil, device)).cpu().numpy()
    assert np.max(np.abs(actual[interior] - constant[interior])) < .1
    right = independent_forward(latent['near'], latent['far'], latent['alpha'], FOCI[4])
    wrong = independent_forward(latent['near'], latent['far'], latent['alpha'], FOCI[4], wrong_separate_visibility=True)
    noncommutation = score(wrong, right, 'crossing')['rgb_rmse']
    assert noncommutation > 10, 'visibility-after-average destroyer inactive'
    # Values above metadata white remain exact-valued observations, not censored.
    mu = tensor(np.array([15500, 15500], np.float32), device)
    y = tensor(np.array([15500, 15600], np.float32), device)
    loss = model.observation_nll(mu, y, gain=float(GAIN), read_variance=float(READ_VARIANCE),
                                  black=BLACK, saturation=CEILING).detach().cpu().numpy()
    expected_difference = 10000 / (2 * (float(GAIN) * (15500 - BLACK) + float(READ_VARIANCE) + 1 / 12))
    assert abs(float(loss[1] - loss[0]) - expected_difference) < 2e-5
    censored = model.observation_nll(tensor(np.array([14000, 18000], np.float32), device),
                   tensor(np.array([CEILING, CEILING], np.float32), device), gain=float(GAIN),
                   read_variance=float(READ_VARIANCE), black=BLACK, saturation=CEILING).detach().cpu().numpy()
    assert np.isfinite(censored).all() and censored[0] > censored[1] + 10
    wrong_ceiling = model.observation_nll(mu, y, gain=float(GAIN), read_variance=float(READ_VARIANCE),
                        black=BLACK, saturation=METADATA_WHITE).detach().cpu().numpy()
    assert np.max(np.abs(wrong_ceiling - loss)) > 1
    for invalid in [float('nan'), float('inf'), -1.0]:
        broken = latent['near'].copy()
        broken[48, 48, 0] = invalid
        refused = False
        try:
            model.forward(tensor(broken, device), tensor(latent['far'], device),
                          tensor(latent['alpha'], device), config, 4)
        except ValueError:
            refused = True
        assert refused, 'invalid radiance was accepted'
    return dict(same_pupil_forward_max_dn=errors, constant_exact_within_dn=.1,
                visibility_noncommutation_crossing_rms=noncommutation,
                uncensored_above_white_loss_difference=float(loss[1] - loss[0]),
                digital_censor_losses=censored.tolist(), wrong_metadata_ceiling_detected=True)


def prediction_score(predicted, observed, expected):
    valid = np.zeros((HEIGHT, WIDTH), bool)
    valid[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
    variance = GAIN * np.maximum(expected - np.float32(BLACK), np.float32(0)) + READ_VARIANCE + np.float32(1 / 12)
    sigma = np.sqrt(variance)
    uncensored = observed < CEILING
    z = (predicted - observed.astype(np.float32)) / sigma
    masks = dict(all=valid)
    for name, (dy, dx) in dict(R=(0, 0), G1=(0, 1), G2=(1, 0), B=(1, 1)).items():
        parity = np.zeros_like(valid)
        parity[dy::2, dx::2] = True
        masks[name] = valid & parity
    masks['bright'] = valid & (expected - BLACK >= 5000)
    masks['dim'] = valid & (expected - BLACK < 5000)
    records = {}
    passed = True
    for name, mask in masks.items():
        mask = mask & uncensored
        count = int(mask.sum())
        rms = float(np.sqrt(np.mean(z[mask].astype(np.float64) ** 2))) if count else None
        bar = 1.5 if name == 'all' else 1.75
        good = rms is None or rms <= bar
        passed &= good
        records[name] = dict(count=count, normalized_rms=rms, bar=bar, passed=good, present=count > 0)
    censored = valid & ~uncensored
    shortfall = np.maximum(np.float32(0), np.float32(CEILING - .5) - predicted) / sigma
    censor_rms = float(np.sqrt(np.mean(shortfall[censored].astype(np.float64) ** 2))) if censored.any() else None
    passed &= censor_rms is None or censor_rms <= 2
    return dict(uncensored=records, censor_count=int(censored.sum()),
                censor_one_sided_rms=censor_rms, passed=bool(passed))


def truth_forward_adequacy(model, config, latent, expected):
    device = config.device
    records = []
    for k in range(9):
        with torch.no_grad():
            rgb = model.forward(tensor(latent['near'], device), tensor(latent['far'], device),
                   tensor(latent['alpha'], device), config, k).cpu().numpy()
        predicted = cfa_numpy(rgb) + np.float32(BLACK)
        values = {}
        for region in ['whole', 'crossing']:
            values[region] = float(np.max(np.abs((predicted - expected[k])[region_slice(region)])))
        records.append(dict(index=k, maximum_difference_dn=values))
    return dict(records=records, passed=all(max(v['maximum_difference_dn'].values()) <= .1 for v in records),
                scope='Same supplied64 discrete pupil; independent interpolation/compositing implementation')


def physical_adequacy(latent, expected):
    records = []
    for k in [0, 2, 4, 6, 8]:
        rgb = independent_forward(latent['near'], latent['far'], latent['alpha'], FOCI[k], pupil=pupil_pairs(1024))
        resolved = cfa_numpy(rgb) + np.float32(BLACK)
        sigma = np.sqrt(GAIN * np.maximum(resolved - BLACK, 0) + READ_VARIANCE + np.float32(1 / 12))
        z = (expected[k] - resolved) / sigma
        values = {region: float(np.sqrt(np.mean(z[region_slice(region)].astype(np.float64) ** 2)))
                  for region in ['whole', 'crossing']}
        records.append(dict(index=k, normalized_rms=values))
    return dict(records=records, passed=all(max(v['normalized_rms'].values()) <= .75 for v in records),
                scope='Independent1024-ray resolution check; does not block discrete utility execution, does block real-RAW license')


def fit_fingerprint(result):
    return dict(pinhole=digest(result.pinhole_rgb), near=digest(result.near_rgb),
                far=digest(result.far_rgb), alpha=digest(result.alpha),
                history=hashlib.sha256(json.dumps(jsonable([{k:v for k,v in row.items() if k != 'elapsed_seconds'}
                              for row in result.history]), sort_keys=True,
                              allow_nan=False).encode()).hexdigest())


def quality(name, latent, candidate, single, mean, oracle):
    regions = ['whole'] if name == 'flat' else list(REGIONS)
    values = {region: {arm: score(image, latent['truth'], region) for arm, image in
              [('candidate', candidate), ('far_only', single), ('mean', mean), ('oracle_bound', oracle)]} for region in regions}
    bars = {}
    if name == 'flat':
        v = values['whole']
        bars = {metric: v['candidate'][metric] <= 1.05 * v['mean'][metric] for metric in ['rgb_rmse', 'chroma_rmse']}
    elif name == 'far-only':
        v = values['whole']
        bars = {metric: v['candidate'][metric] <= 1.05 * v['far_only'][metric] for metric in ['rgb_rmse', 'chroma_rmse']}
    elif name == 'layered':
        for region in ['whole', 'core', 'ridge']:
            v = values[region]
            bars[region + '_mean_gain'] = v['mean']['rgb_rmse'] > 1 and v['candidate']['rgb_rmse'] <= .90 * v['mean']['rgb_rmse']
        for region in ['whole', 'crossing', 'core', 'ridge']:
            v = values[region]
            factor = .95 if region in ['whole', 'crossing'] else 1.05
            bars[region + '_far_only_comparison'] = v['candidate']['rgb_rmse'] <= factor * v['far_only']['rgb_rmse']
    components = {}
    if name in ['layered', 'angular-mismatch']:
        for component_name, region in [('glint', 'core'), ('ridge', 'ridge-detail')]:
            a = component(candidate, latent, component_name, region)
            o = component(oracle, latent, component_name, region)
            rec = np.clip(np.array(a['recovery']), 0, 1)
            ref = np.clip(np.array(o['recovery']), 0, 1)
            good = a['live'] and o['live'] and bool(np.all(rec >= .8) and np.all(rec >= .98 * ref))
            components[component_name] = dict(candidate=a, oracle_bound=o, passed=good,
                bounds=list(RIDGE_DETAIL if region == 'ridge-detail' else REGIONS[region]))
            if name == 'layered':
                bars[component_name + '_component'] = good
    return dict(regions=values, components=components, bars=bars,
                passed=bool(all(bars.values())) if bars else None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args()
    out = args.out.resolve()
    assert not out.exists()
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('layered_raw_model', HERE / 'model.py')
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)
    config = model.Config(width=WIDTH, height=HEIGHT, focus_coordinates=FOCI,
             inverse_depths=DEPTHS, defocus_scale=float(SCALE), psf_sigma=float(SIGMA),
             gain=float(GAIN), read_variance=float(READ_VARIANCE), black=BLACK,
             saturation=CEILING, steps=160, device=args.device,
             pupil_points=tuple(tuple(float(v) for v in p) for p in pupil_pairs(64)))
    assert config.valid_margin <= MARGIN
    save(out / 'bindings.json', dict(model_sha256=digest(np.frombuffer((HERE / 'model.py').read_bytes(), np.uint8)),
        controls_sha256=digest(np.frombuffer(Path(__file__).read_bytes(), np.uint8)),
        train=list(TRAIN), heldout=list(HELD), focus_coordinates=FOCI, known_depths=DEPTHS,
        noise=dict(gain=float(GAIN), read_variance=float(READ_VARIANCE), black=BLACK, saturation=CEILING),
        model_rays=64, utility_generator_rays=64, physical_adequacy_rays=1024,
        pupil_sha256=digest(pupil_pairs(64)), valid_margin=MARGIN))
    metric = metric_commission()
    mechanical_result = mechanical(model, config)
    save(out / 'mechanical.json', dict(metric_commission=metric, model_controls=mechanical_result))
    cases = []
    for number, name in enumerate(['flat', 'layered', 'far-only', 'angular-mismatch']):
        print('LAYERED_CASE_START', name, flush=True)
        latent, raw, expected, mean, oracle, oracle_indices = dataset(name, number)
        original = digest(raw)
        clipped_training_valid = int(np.count_nonzero(raw[list(TRAIN), MARGIN:-MARGIN, MARGIN:-MARGIN] == CEILING))
        core_yx = region_slice('core')
        unclipped_glint_views = [k for k in TRAIN if bool(np.all(raw[k][core_yx] < CEILING))]
        if name == 'layered':
            assert clipped_training_valid > 0, 'digital censoring absent from the actual training likelihood support'
            assert unclipped_glint_views, 'protected glint has no wholly uncensored training view'
        adequate = truth_forward_adequacy(model, config, latent, expected) if name != 'angular-mismatch' else None
        case_dir = out / name
        case_dir.mkdir()
        # Export source u16 and scalar evidence; no truth arrays passed to fit.
        np.save(case_dir / 'observations-u16.npy', raw, allow_pickle=False)
        save(case_dir / 'prefit-adequacy.json', dict(operator=adequate))
        if adequate is not None and not adequate['passed']:
            row = dict(name=name, qualified=False, optimization_run=False,
                       source_sha256=original, operator_adequacy=adequate,
                       reason='Same discrete forward operator failed; no optimization or later case executed')
            save(case_dir / 'result.json', row)
            cases.append(row)
            print('LAYERED_OPERATOR_REFUSED', json.dumps(row), flush=True)
            break
        physical = physical_adequacy(latent, expected) if name == 'layered' else None
        if physical is not None:
            save(case_dir / 'physical-adequacy.json', physical)
        guarded = TrainingOnly(raw)
        result = model.fit(guarded, config, TRAIN, output_dir=case_dir / 'two-layer', mode='two-layer')
        assert set(guarded.reads) == set(TRAIN)
        assert digest(raw) == original
        guarded_single = TrainingOnly(raw)
        single = model.fit(guarded_single, config, TRAIN, output_dir=case_dir / 'far-only', mode='one-layer')
        assert set(guarded_single.reads) == set(TRAIN)
        assert digest(raw) == original
        for field in [result.pinhole_rgb, result.near_rgb, result.far_rgb, result.alpha, single.pinhole_rgb]:
            assert field.dtype == np.float32 and np.isfinite(field).all()
        assert result.pinhole_rgb.shape == single.pinhole_rgb.shape == (HEIGHT, WIDTH, 3)
        neutrality = None
        if name == 'flat':
            replaced = raw.copy()
            replaced[list(HELD)] = np.uint16(12345)
            initialized = model.fit(TrainingOnly(raw), config, TRAIN, mode='two-layer', optimize=False)
            clone = model.fit(TrainingOnly(replaced), config, TRAIN, mode='two-layer', optimize=False)
            neutrality = fit_fingerprint(initialized) == fit_fingerprint(clone)
            assert neutrality, 'withheld original values affected initialization'
            refused = False
            try:
                guarded[HELD[0]]
            except AssertionError:
                refused = True
            assert refused, 'input-read guard did not reject deliberate heldout access'
            assert digest(raw) == original
        predictions = []
        for k in HELD:
            predicted = result.predict(k)
            assert predicted.dtype == np.float32 and predicted.shape == (HEIGHT, WIDTH) and np.isfinite(predicted).all()
            predictions.append(dict(index=k, candidate=prediction_score(predicted, raw[k], expected[k]),
                far_only=prediction_score(single.predict(k), raw[k], expected[k])))
        q = quality(name, latent, result.pinhole_rgb, single.pinhole_rgb, mean, oracle)
        prediction_pass = all(p['candidate']['passed'] for p in predictions)
        clipped = int(np.count_nonzero(raw == CEILING))
        if name == 'angular-mismatch':
            qualified = None
            interpretation = 'Descriptive mismatch. Heldout failure => screen refusal; no automatic model gate exists.'
        else:
            qualified = bool(adequate['passed'] and prediction_pass and q['passed'])
            interpretation = 'Known-optics utility only; neither calibration nor canonical-merge comparison.'
        row = dict(name=name, source_sha256=original, source_unchanged=digest(raw) == original,
            observation_shape=list(raw.shape), saturated_codes=clipped,
            clipped_training_valid=clipped_training_valid,
            protected_glint_core_bounds=list(REGIONS['core']),
            wholly_unclipped_training_glint_views=unclipped_glint_views,
            above_metadata_white_not_censored=int(np.count_nonzero((raw > METADATA_WHITE) & (raw < CEILING))),
            oracle_training_indices=sorted(int(v) for v in np.unique(oracle_indices)),
            operator_adequacy=adequate, physical_adequacy=physical,
            heldout_prediction=predictions, heldout_pass=prediction_pass,
            quality=q, qualified=qualified, heldout_poison_initialization_exact=neutrality,
            actual_fit_read_indices=sorted(set(guarded.reads)), actual_fit_read_count=len(guarded.reads),
            one_layer_read_indices=sorted(set(guarded_single.reads)),
            output_fingerprints=fit_fingerprint(result), interpretation=interpretation)
        save(case_dir / 'result.json', row)
        for label, image in [('truth', latent['truth']), ('candidate', result.pinhole_rgb),
                             ('far-only', single.pinhole_rgb), ('mean', mean), ('oracle-bound', oracle)]:
            np.save(case_dir / (label + '-rgb-f32.npy'), image, allow_pickle=False)
        cases.append(row)
        print('LAYERED_CASE_COMPLETE', json.dumps(dict(name=name, qualified=qualified,
              heldout_pass=prediction_pass, quality_bars=q['bars'])), flush=True)
    admitted = len(cases) == 4 and all(c['qualified'] for c in cases if c['name'] != 'angular-mismatch')
    save(out / 'screen.json', dict(status='SCREEN_COMPLETE', known_optics_utility_pass=admitted,
        real_photo_admission=False, cases=cases, limitations=[
            'Known discrete64-ray optics and depths; shared injected calibration is not independently validated.',
            'Far-only comparator is restricted, not the best possible one-layer method.',
            'Truth-informed donor is a bound and never sees withheld input.',
            'No canonical full-consumer comparison; no SOTA or photographic claim.',
            'Heldout prediction can fit incorrect latent layers; truth/component bars remain binding.']))
    print('LAYERED_SCREEN', json.dumps(dict(known_optics_utility_pass=admitted,
                                          real_photo_admission=False)), flush=True)


if __name__ == '__main__':
    main()
