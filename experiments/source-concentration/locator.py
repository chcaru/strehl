"""Fixed display-space concentration discriminator; no RAW or repair consumer.

Rule: experiments/donor-consistency/automatic-design.md, One rule to try.
Coordinates denote original pixel centres. Reference cells are globally anchored
half-open [2i,2i+2), represented by their centres. No image is resampled.
"""
import struct
import numpy as np
from scipy import ndimage as ndi

SIGMA = 32.0
FILTER_RADIUS = 64
CELL = 2
SEED_GRID = 32
SEED_SEPARATION = 32.0
SEARCH_RADIUS = 8.0
MEASURE_RADIUS = 64.0
COMPONENT_FRACTION = 0.1
AMBIGUITY_FRACTION = 0.8
CENTROID_LIMIT = 4.0
MASS_FRACTION = 0.25
PEAK_FRACTION = 0.5
TRACK_MARGIN = 5
CONTRACTION_RATIO = 1.25
CONNECTIVITY = np.ones((3, 3), dtype=np.uint8)


def local_contrast(rgb):
    """Return q and display-ceiling flag after discarding the64-pixel margin.

    Gaussian never touches a nonspatial axis. Its padded numerical boundary is
    discarded; every returned sample uses genuine caller-supplied context.
    """
    rgb = np.asarray(rgb, dtype=np.float64)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) <= 2 * FILTER_RADIUS:
        raise ValueError('RGB context must exceed128pixels on both axes')
    if not np.all(np.isfinite(rgb)) or np.any(rgb < 0) or np.any(rgb > 1):
        raise ValueError('finite normalized developed RGB required')
    q = np.zeros(rgb.shape[:2], dtype=np.float64)
    for c in range(3):
        background = ndi.gaussian_filter(rgb[:, :, c], SIGMA, truncate=2.0, mode='constant', cval=0.0)
        np.maximum(q, rgb[:, :, c] - background, out=q)
    r = FILTER_RADIUS
    return q[r:-r, r:-r].copy(), np.any(rgb[r:-r, r:-r] >= 1.0, axis=2)


def pull_parameters(pull_bits):
    values = np.asarray([struct.unpack('>d', bytes.fromhex(v))[0] for v in pull_bits], dtype=np.float64)
    if values.shape != (4,) or not np.all(np.isfinite(values)) or np.dot(values[:2], values[:2]) <= 0:
        raise ValueError('finite invertible similarity required')
    return values


def source_coordinates(x, y, pull_bits, sensor_center, output_offset):
    ar, ai, br, bi = pull_parameters(pull_bits)
    cx, cy = sensor_center
    u, v = np.asarray(x) + output_offset[0] - cx, np.asarray(y) + output_offset[1] - cy
    return cx + ar * u - ai * v + 2 * br, cy + ai * u + ar * v + 2 * bi


def reference_coordinates(shape, source_origin, pull_bits, sensor_center, output_offset):
    ar, ai, br, bi = pull_parameters(pull_bits)
    y, x = np.indices(shape, dtype=np.float64)
    cx, cy = sensor_center
    u, v = x + source_origin[0] - cx - 2 * br, y + source_origin[1] - cy - 2 * bi
    norm = ar * ar + ai * ai
    return (cx + (ar * u + ai * v) / norm - output_offset[0],
            cy + (-ai * u + ar * v) / norm - output_offset[1])


def grid_shape(field_xywh):
    x, y, w, h = field_xywh
    if w <= 0 or h <= 0:
        raise ValueError('positive field required')
    x0, y0 = int(np.floor(x / CELL)), int(np.floor(y / CELL))
    x1, y1 = int(np.ceil((x + w) / CELL)), int(np.ceil((y + h) / CELL))
    return y1 - y0, x1 - x0


def accumulate_maximum(maximum, seen, q, rx, ry, field_xywh):
    """Mutate only one scalar max field and its coverage flags, never RGB."""
    x, y, w, h = field_xywh
    if maximum.shape != grid_shape(field_xywh) or seen.shape != maximum.shape:
        raise ValueError('seed field shape differs')
    if q.shape != rx.shape or q.shape != ry.shape or not np.all(np.isfinite(q)) or np.any(q < 0):
        raise ValueError('finite nonnegative q and equal coordinate arrays required')
    inside = (rx >= x) & (rx < x + w) & (ry >= y) & (ry < y + h)
    ix = np.floor(rx[inside] / CELL).astype(np.int64) - int(np.floor(x / CELL))
    iy = np.floor(ry[inside] / CELL).astype(np.int64) - int(np.floor(y / CELL))
    np.maximum.at(maximum, (iy, ix), q[inside])
    seen[iy, ix] = True


def nominate_seeds(maximum, seen, field_xywh):
    x0, y0 = np.floor(np.asarray(field_xywh[:2]) / CELL).astype(int)
    best = {}
    for iy, ix in np.argwhere(seen & (maximum > 0)):
        x, y = CELL * (x0 + int(ix)) + CELL / 2, CELL * (y0 + int(iy)) + CELL / 2
        seed = {'x': float(x), 'y': float(y), 'q': float(maximum[iy, ix]), 'cell': [int(ix), int(iy)]}
        key = (int(np.floor(y / SEED_GRID)), int(np.floor(x / SEED_GRID)))
        previous = best.get(key)
        if previous is None or (-seed['q'], seed['y'], seed['x']) < (-previous['q'], previous['y'], previous['x']):
            best[key] = seed
    kept = []
    for seed in sorted(best.values(), key=lambda s: (-s['q'], s['y'], s['x'])):
        if all((seed['x'] - p['x']) ** 2 + (seed['y'] - p['y']) ** 2 > SEED_SEPARATION ** 2 for p in kept):
            kept.append(seed)
    return sorted(kept, key=lambda s: (s['y'], s['x']))


def _empty(reason):
    return {'status': 'unknown', 'reasons': [reason], 'mass': None, 'peak': None,
            'centroid': None, 'covariance': None, 'eigenvalues': None, 'r': None,
            'display_ceiling_contact': False, 'raw_clipping': 'unknown',
            'footprint_bounds': None, 'component_pixels': 0}


def measure_seed(q, ceiling, rx, ry, seed):
    """One source-lattice connected footprint in continuous reference geometry."""
    q, ceiling, rx, ry = np.asarray(q), np.asarray(ceiling), np.asarray(rx), np.asarray(ry)
    if q.ndim != 2 or min(q.shape) < 2 or not (q.shape == ceiling.shape == rx.shape == ry.shape):
        raise ValueError('equal2D source arrays required')
    if not all(np.all(np.isfinite(a)) for a in (q, rx, ry)) or np.any(q < 0):
        raise ValueError('finite nonnegative q and coordinates required')
    jac = np.array([[rx[0, 1] - rx[0, 0], rx[1, 0] - rx[0, 0]],
                    [ry[0, 1] - ry[0, 0], ry[1, 0] - ry[0, 0]]])
    inv = np.linalg.inv(jac)
    centre = inv @ np.array([seed['x'] - rx[0, 0], seed['y'] - ry[0, 0]])
    extents = MEASURE_RADIUS * np.linalg.norm(inv, axis=1)
    lo = np.floor(centre - extents).astype(int) - 1
    hi = np.ceil(centre + extents).astype(int) + 2
    if lo[0] < 0 or lo[1] < 0 or hi[0] > q.shape[1] or hi[1] > q.shape[0]:
        return _empty('missing-support')
    sl = np.s_[lo[1]:hi[1], lo[0]:hi[0]]
    p, clip, x, y = q[sl], ceiling[sl], rx[sl], ry[sl]
    distance2 = (x - seed['x']) ** 2 + (y - seed['y']) ** 2
    search, disk = distance2 <= SEARCH_RADIUS ** 2, distance2 <= MEASURE_RADIUS ** 2
    if not np.any(search):
        return _empty('missing-search-samples')
    peak_location = np.unravel_index(np.argmax(np.where(search, p, -np.inf)), p.shape)
    peak = float(p[peak_location])
    if peak <= 0:
        return _empty('no-positive-peak')
    reasons = []
    _, competing = ndi.label(search & (p >= AMBIGUITY_FRACTION * peak), CONNECTIVITY)
    if competing > 1:
        reasons.append('ambiguous-identity')
    labels, _ = ndi.label(disk & (p > COMPONENT_FRACTION * peak), CONNECTIVITY)
    component = labels == labels[peak_location]
    if np.any(component & ndi.binary_dilation(~disk, structure=CONNECTIVITY)):
        reasons.append('disk-boundary-contact')
    weights = p[component]
    mass = float(np.sum(weights))
    cx, cy = float(np.sum(weights * x[component]) / mass), float(np.sum(weights * y[component]) / mass)
    dx, dy = x[component] - cx, y[component] - cy
    cov = np.array([[np.sum(weights * dx * dx), np.sum(weights * dx * dy)],
                    [np.sum(weights * dx * dy), np.sum(weights * dy * dy)]]) / mass
    eigenvalues = np.linalg.eigvalsh(cov)
    radius = None
    if eigenvalues[0] <= 0 or not np.all(np.isfinite(eigenvalues)):
        reasons.append('singular-covariance')
    else:
        radius = float(np.prod(eigenvalues) ** 0.25)
    if np.hypot(cx - seed['x'], cy - seed['y']) > CENTROID_LIMIT:
        reasons.append('centroid-displacement')
    clipped = bool(np.any(clip[component]))
    if clipped:
        reasons.append('display-ceiling-contact')
    return {'status': 'unknown' if reasons else 'measured', 'reasons': reasons,
            'mass': mass, 'peak': peak, 'centroid': [cx, cy], 'covariance': cov.tolist(),
            'eigenvalues': eigenvalues.tolist(), 'r': radius, 'display_ceiling_contact': clipped,
            'raw_clipping': 'unknown', 'component_pixels': int(np.count_nonzero(component)),
            'footprint_bounds': [float(x[component].min()), float(y[component].min()),
                                 float(x[component].max()), float(y[component].max())]}


def nominate_track(frame_records):
    """Fixed through-focus gate. Fail the best radius; never search a runner-up."""
    frames = [dict(record) for record in frame_records]
    if not frames or [r.get('index0', i) for i, r in enumerate(frames)] != list(range(len(frames))):
        raise ValueError('contiguous complete source order required')
    mass_max = max((r['mass'] for r in frames if r['mass'] is not None), default=0.0)
    peak_max = max((r['peak'] for r in frames if r['peak'] is not None), default=0.0)
    for i, record in enumerate(frames):
        record['index0'] = i
        reasons = list(record['reasons'])
        if record['mass'] is None or record['mass'] < MASS_FRACTION * mass_max:
            reasons.append('insufficient-relative-mass')
        if record['peak'] is None or record['peak'] < PEAK_FRACTION * peak_max:
            reasons.append('insufficient-relative-peak')
        if record['r'] is None or not np.isfinite(record['r']) or record['r'] <= 0:
            reasons.append('unknown-radius')
        record['eligibility_reasons'] = reasons
        record['eligible'] = record['status'] == 'measured' and not reasons
    answer = {'status': 'refused', 'reason': 'no-eligible-frame', 'index0': None,
              'mass_max': mass_max, 'peak_max': peak_max, 'frames': frames}
    eligible = [i for i, r in enumerate(frames) if r['eligible']]
    if not eligible:
        return answer
    minimum = min(frames[i]['r'] for i in eligible)
    tied = [i for i in eligible if frames[i]['r'] == minimum]
    if tied != list(range(tied[0], tied[-1] + 1)):
        answer['reason'] = 'separated-tied-intervals'
        return answer
    index = tied[(len(tied) - 1) // 2]
    if index < TRACK_MARGIN or index >= len(frames) - TRACK_MARGIN:
        answer['reason'] = 'endpoint-minimum'
    elif not all(frames[i]['eligible'] and frames[i]['r'] <= CONTRACTION_RATIO * minimum for i in (index - 1, index + 1)):
        answer['reason'] = 'unstable-immediate-neighbours'
    elif not all(frames[i]['eligible'] and frames[i]['r'] >= CONTRACTION_RATIO * minimum for i in (index - TRACK_MARGIN, index + TRACK_MARGIN)):
        answer['reason'] = 'no-stable-contraction'
    else:
        answer.update(status='nominated', reason='stable-contraction', index0=index)
    return answer
