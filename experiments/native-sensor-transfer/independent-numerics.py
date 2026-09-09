"""Independent finite arithmetic for native-sensor-transfer. Source-only until release.
No producer imports. NumPy is supplied by the source-authenticated entry point;
importing this file does not allocate arrays, execute a control, or open data.
"""
import math
import struct

NP = None
SIDES = (128, 64, 32, 16, 8)
KERNEL = (1 / 16, 4 / 16, 6 / 16, 4 / 16, 1 / 16)
SAFE = ((5, 121), (7, 57), (7, 25), (7, 9))
SAFE_COUNTS = (13689, 2601, 361, 9)
NIST = {4: (0.484, 11.143), 11: (3.816, 21.920), 21: (10.283, 35.479)}


def need(test, reason):
    if not test:
        raise ValueError(reason)


def configure(numpy_module):
    global NP
    need(NP is None, 'numerical module already configured')
    NP = numpy_module


def f32(value):
    try:
        return struct.unpack('<f', struct.pack('<f', float(value)))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def bits(value):
    return struct.unpack('<I', struct.pack('<f', float(value)))[0]


def from_bits(value):
    need(type(value) is int and 0 <= value < 2**32, 'f32 bits integer')
    return struct.unpack('<f', struct.pack('<I', value))[0]


def array(value, shape=None, dtype=None):
    need(NP is not None, 'numerical module not configured')
    a = NP.asarray(value, dtype=dtype)
    need(shape is None or a.shape == tuple(shape), 'array shape')
    need(bool(NP.isfinite(a).all()), 'nonfinite array')
    return a


def bit_equal(actual, expected, reason='binary32 arithmetic disagreement'):
    a = array(actual, dtype=NP.float32)
    b = array(expected, a.shape, NP.float32)
    need(a.astype('<f4', copy=False).tobytes(order='C') ==
         b.astype('<f4', copy=False).tobytes(order='C'), reason)
    return True


def same_real(a, b, reason='binary64 prediction disagreement'):
    aa, bb = NP.asarray(a, dtype=NP.float64), NP.asarray(b, dtype=NP.float64)
    need(aa.shape == bb.shape and bool(NP.isfinite(aa).all()) and
         bool(NP.isfinite(bb).all()), reason)
    bound = 2.0**-38 * NP.maximum(1.0, NP.maximum(NP.abs(aa), NP.abs(bb)))
    need(bool((NP.abs(aa-bb) <= bound).all()), reason)
    return True


def extract(raw, black):
    a = array(raw, (256, 256))
    need(a.dtype == NP.dtype('uint16'), 'sensor u16 dtype')
    out = []
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        signed = NP.subtract(a[dy::2, dx::2].astype(NP.float32), NP.float32(black),
                             dtype=NP.float32)
        out.append(NP.maximum(signed, NP.float32(0)))
    planes = NP.stack(out)
    luma = NP.multiply(NP.add(planes[1], planes[2], dtype=NP.float32),
                       NP.float32(0.5), dtype=NP.float32)
    return planes, luma


def signed_planes(raw, black):
    a = array(raw, (256, 256))
    need(a.dtype == NP.dtype('uint16'), 'sensor u16 dtype')
    return NP.stack([a[dy::2, dx::2].astype(NP.float64)-float(black)
                     for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))])


def native_variance(luma, gains, read_e):
    """Independent spelling of actual green_luma_sigma -> square, each f32 step."""
    y = array(luma, (128, 128), NP.float32)
    components = []
    for p in (1, 2):
        g, r = NP.float32(gains[p]), NP.float32(read_e[p])
        read_dn = NP.multiply(r, g, dtype=NP.float32)
        shot = NP.multiply(g, NP.maximum(y, NP.float32(0)), dtype=NP.float32)
        components.append(NP.add(shot, NP.multiply(read_dn, read_dn, dtype=NP.float32),
                                 dtype=NP.float32))
    total = NP.multiply(NP.add(*components, dtype=NP.float32), NP.float32(0.25), dtype=NP.float32)
    sigma = NP.sqrt(total, dtype=NP.float32)
    return NP.multiply(sigma, sigma, dtype=NP.float32)


def filter_axis(a, axis, centres, dtype):
    """Replicated five taps, serial multiply then add. Never touches time axis."""
    a = array(a, dtype=dtype)
    need(a.ndim == 2 and axis in (0, 1), 'spatial filter only')
    n = a.shape[axis]
    shape = list(a.shape); shape[axis] = len(centres)
    result = NP.zeros(shape, dtype=dtype)
    for tap, coefficient in enumerate(KERNEL):
        take = NP.clip(centres + tap - 2, 0, n - 1)
        part = NP.multiply(NP.take(a, take, axis=axis), dtype(coefficient), dtype=dtype)
        result = NP.add(result, part, dtype=dtype)
    return result


def reduce_plane(a, dtype=None):
    dtype = NP.float32 if dtype is None else dtype
    a = array(a, dtype=dtype)
    need(a.ndim == 2 and min(a.shape) >= 2, 'reduce shape')
    horizontal = filter_axis(a, 1, NP.arange((a.shape[1]+1)//2)*2, dtype)
    return filter_axis(horizontal, 0, NP.arange((a.shape[0]+1)//2)*2, dtype)


def smooth(a, dtype=None):
    dtype = NP.float32 if dtype is None else dtype
    a = array(a, dtype=dtype)
    horizontal = filter_axis(a, 1, NP.arange(a.shape[1]), dtype)
    return filter_axis(horizontal, 0, NP.arange(a.shape[0]), dtype)


def expand_axis(a, axis, size, dtype):
    a = array(a, dtype=dtype)
    n = a.shape[axis]
    need(size in (2*n, 2*n-1), 'expand destination')
    c = NP.arange(size)//2
    prev = NP.take(a, NP.maximum(c-1, 0), axis=axis)
    here = NP.take(a, c, axis=axis)
    following = NP.take(a, NP.minimum(c+1, n-1), axis=axis)
    even = NP.add(NP.multiply(dtype(0.125), prev, dtype=dtype),
                  NP.multiply(dtype(0.75), here, dtype=dtype), dtype=dtype)
    even = NP.add(even, NP.multiply(dtype(0.125), following, dtype=dtype), dtype=dtype)
    odd = NP.multiply(dtype(0.5), NP.add(here, following, dtype=dtype), dtype=dtype)
    mask_shape = [1, 1]; mask_shape[axis] = size
    return NP.where((NP.arange(size)%2 == 0).reshape(mask_shape), even, odd)


def expand_plane(a, shape, dtype=None):
    dtype = NP.float32 if dtype is None else dtype
    horizontal = expand_axis(a, 1, shape[1], dtype)
    return expand_axis(horizontal, 0, shape[0], dtype)


def pyramid(a, dtype=None):
    dtype = NP.float32 if dtype is None else dtype
    gaussian = [array(a, (128, 128), dtype)]
    for size in SIDES[1:]:
        b = reduce_plane(gaussian[-1], dtype)
        need(b.shape == (size, size), 'pyramid exact level sizes')
        gaussian.append(b)
    laplacian = []
    for k in range(4):
        laplacian.append(NP.subtract(gaussian[k], expand_plane(gaussian[k+1],
                                     gaussian[k].shape, dtype), dtype=dtype))
    return gaussian, [*laplacian, gaussian[4]]


def energy(laplacian):
    a = array(laplacian, dtype=NP.float32)
    return smooth(NP.multiply(a, a, dtype=NP.float32))


def support(k):
    need(type(k) is int and 0 <= k < 4, 'support band')
    side = SIDES[k]; lo, hi = SAFE[k]
    y, x = NP.indices((side, side))
    inside = (x >= lo) & (x <= hi) & (y >= lo) & (y <= hi)
    need(int(inside.sum()) == SAFE_COUNTS[k], 'support count')
    rows = []
    for full, word in ((True, 'full-support'), (False, 'boundary-dependent')):
        for px, py in ((0, 0), (1, 0), (0, 1), (1, 1)):
            mask = (inside if full else ~inside) & (x%2 == px) & (y%2 == py)
            rows.append((f'{word}-x{px}-y{py}', mask))
    need(sum(int(m.sum()) for _, m in rows) == side*side, 'support partition')
    return rows


def independent_operators():
    """One-dimensional original-site maps; binary dyadics, no subject functions."""
    g = [NP.eye(128, dtype=NP.float64)]
    for side in SIDES[1:]:
        old = g[-1]; new = NP.zeros((side, 128), dtype=NP.float64)
        for q in range(side):
            for t, c in enumerate(KERNEL):
                new[q] += c * old[min(max(2*q+t-2, 0), len(old)-1)]
        g.append(new)
    e = []
    for k in range(4):
        old = g[k+1]; new = NP.zeros((SIDES[k], 128), dtype=NP.float64)
        for q in range(SIDES[k]):
            centre = q//2
            taps = ((centre-1, 1/8), (centre, 6/8), (centre+1, 1/8)) if q%2 == 0 else (
                   (centre, 1/2), (centre+1, 1/2))
            for i, c in taps:
                new[q] += c * old[min(max(i, 0), len(old)-1)]
        e.append(new)
    return g, e


def diagonal_prediction(q, operators=None):
    q = array(q, (128, 128), NP.float64)
    need(bool((q >= 0).all()), 'negative diagonal input variance')
    g, e = independent_operators() if operators is None else operators
    bands = []
    for a, b in zip(g[:4], e):
        aa, bb, ab = a*a, b*b, a*b
        # H_ij = a_i outer a_j - b_i outer b_j; duplicate addresses already coalesced.
        v = (aa @ q @ aa.T) + (bb @ q @ bb.T) - 2*(ab @ q @ ab.T)
        need(bool(NP.isfinite(v).all()) and bool((v >= 0).all()), 'negative diagonal prediction')
        bands.append(v)
    return bands, [smooth(v, NP.float64) for v in bands]


def direct_diagonal(q, k, x, y, operators=None, duplicate_fault=False):
    q = array(q, (128, 128), NP.float64)
    g, e = independent_operators() if operators is None else operators
    h = NP.outer(g[k][y], g[k][x]) - NP.outer(e[k][y], e[k][x])
    if duplicate_fault:
        # Deliberately splitting one real coefficient into two independent draws is wrong.
        h = h.copy(); flat = h.reshape(-1); i = int(NP.argmax(NP.abs(flat)))
        value = float(flat[i]); flat[i] = 0
        return float(NP.sum(h*h*q)) + 2*(value/2)**2*float(q.reshape(-1)[i])
    return float(NP.sum(h*h*q, dtype=NP.float64))


def temporal(values):
    a = array(values, dtype=NP.float64)
    need(a.ndim >= 2 and len(a) in (5, 22), 'fixed temporal population')
    mean = NP.mean(a, axis=0, dtype=NP.float64)
    s2 = NP.sum((a-mean)**2, axis=0, dtype=NP.float64)/(len(a)-1)
    if len(a) == 5:
        diffs = NP.stack((a[0]-a[1], a[2]-a[3]))
    else:
        diffs = a[0::2]-a[1::2]
    components = diffs*diffs/2
    q = NP.mean(components, axis=0, dtype=NP.float64)
    return {'mean': mean, 'all_variance': s2, 'pair_variance': q,
            'pair_components': components, 'contrasts': diffs,
            'all_df': len(a)-1, 'pair_df': len(diffs)}


def covariance(a, b):
    a, b = array(a, dtype=NP.float64), array(b, dtype=NP.float64)
    aa, bb = temporal(a), temporal(b)
    need(aa['contrasts'].shape == bb['contrasts'].shape, 'covariance matched sites')
    pair = NP.mean(aa['contrasts']*bb['contrasts'], axis=0)/2
    va, vb = aa['pair_variance'], bb['pair_variance']
    rho = NP.full(pair.shape, NP.nan, dtype=NP.float64)
    ok = (va > 0) & (vb > 0)
    rho[ok] = pair[ok]/NP.sqrt(va[ok]*vb[ok])
    centered = NP.sum((a-aa['mean'])*(b-bb['mean']), axis=0)/(len(a)-1)
    return pair, centered, rho, ok


def overlap(a, b, dx, dy):
    need(a.shape == b.shape and a.shape[-2:] == (128, 128), 'neighbour shapes')
    y0, y1 = max(0, -dy), min(128, 128-dy)
    x0, x1 = max(0, -dx), min(128, 128-dx)
    return a[..., y0:y1, x0:x1], b[..., y0+dy:y1+dy, x0+dx:x1+dx]


def summarize(a, mask=None):
    a = array(a, dtype=NP.float64)
    values = a.reshape(-1) if mask is None else a[mask]
    if not len(values):
        return {'count': 0, 'mean': None, 'min': None, 'max': None}
    return {'count': int(len(values)), 'mean': float(NP.mean(values)),
            'min': float(NP.min(values)), 'max': float(NP.max(values))}


def blocks(a):
    a = array(a, (128, 128), NP.float64)
    return [dict(x=x, y=y, **summarize(a[y:y+32, x:x+32]))
            for y in range(0, 128, 32) for x in range(0, 128, 32)]


def ratio(numerator, denominator):
    n, d = float(numerator), float(denominator)
    need(math.isfinite(n) and math.isfinite(d), 'ratio finite operands')
    return {'numerator': n, 'denominator': d, 'ratio': n/d if d > 0 else None,
            'available': d > 0}


def prediction(reference_raw, black, gains, read_e, reference_role):
    reference_admit(reference_role)
    signed = signed_planes(reference_raw, black)
    need(bool((signed >= 64).all()), 'reference near-black prediction not admitted')
    photosites = NP.stack([float(gains[p])*signed[p] + (float(gains[p])*float(read_e[p]))**2
                          for p in range(4)])
    green = (photosites[1]+photosites[2])/4
    # The prediction witness is noisy; these are conditional plug-in terms.
    uncertainty = ((float(gains[1])**2*photosites[1]) +
                   (float(gains[2])**2*photosites[2]))/16
    correlated = ((float(gains[1])*NP.sqrt(photosites[1]) +
                   float(gains[2])*NP.sqrt(photosites[2]))/4)**2
    return photosites, green, uncertainty, correlated


def reference_uncertainty(q_photosites, gains, k, x, y, operators=None, energy_scale=False):
    """Propagate noisy independent frame4 q; diagonal and fully correlated bounds."""
    q = array(q_photosites, (4, 128, 128), NP.float64)
    g, e = independent_operators() if operators is None else operators
    coefficients = NP.zeros((128, 128), dtype=NP.float64)
    side = SIDES[k]
    if energy_scale:
        for ty, ky in enumerate(KERNEL):
            yy = min(max(y+ty-2, 0), side-1)
            for tx, kx in enumerate(KERNEL):
                xx = min(max(x+tx-2, 0), side-1)
                h = NP.outer(g[k][yy], g[k][xx]) - NP.outer(e[k][yy], e[k][xx])
                coefficients += ky*kx*h*h
    else:
        h = NP.outer(g[k][y], g[k][x]) - NP.outer(e[k][y], e[k][x])
        coefficients = h*h
    variances, standard_deviations = [], []
    for p in (1, 2):
        a = coefficients*float(gains[p])/4
        variances.append(float(NP.sum(a*a*q[p], dtype=NP.float64)))
        standard_deviations.append(float(NP.sum(NP.abs(a)*NP.sqrt(q[p]), dtype=NP.float64)))
    return {'diagonal_reference_variance': sum(variances),
            'fully_correlated_reference_variance_bound': sum(standard_deviations)**2,
            'parameter_uncertainty': 'unavailable; not included',
            'scope': 'conditional on frozen plug-in sensor prediction; not coverage'}


def exponent(k):
    need(type(k) is int and 0 <= k < 4, 'actual exponent band')
    s = f32(1.4)
    factors = (1.0, s, f32(s*s), f32(f32(s*s)*s))
    return min(f32(f32(2)*factors[3-k]), 8.0)


def weight_reference(energy_value, variance, beta, gate, p):
    e, v, beta, gate, p = map(f32, (energy_value, variance, beta, gate, p))
    need(all(math.isfinite(z) for z in (e, v, beta, gate, p)) and e >= 0 and
         v >= 0 and beta >= 0 and gate >= 0 and p > 0, 'weight finite operands')
    floor = f32(f32(gate*beta)*max(v, 0.0))
    need(math.isfinite(floor), 'nonfinite derived floor')
    excess = max(f32(e-floor), 0.0)
    if excess <= 0:
        return {'weight': 0.0, 'floor': floor, 'excess': excess,
                'branch': 'threshold-zero', 'above': False, 'exact': True}
    r = f32(f32(excess/max(floor, 1.0))/64.0)
    if p == 1.0:
        w, branch, exact = r, 'p1-direct', True
    elif p == 2.0:
        w, branch, exact = f32(r*r), 'p2-square', True
    else:
        log = -math.inf if r == 0 else f32(math.log(r))
        product = f32(p*log)
        clipped = min(max(product, -80.0), 80.0)
        w, branch, exact = math.exp(clipped), 'log-exp', False
    return {'weight': w, 'floor': floor, 'excess': excess, 'branch': branch,
            'above': True, 'rounded_r': r, 'exact': exact,
            'zero_underflow': w == 0.0,
            'exponent_clamp': ('lower' if product<=-80 else 'upper' if product>=80 else 'none') if branch=='log-exp' else 'not-applicable',
            'scope': 'floor/excess/branch DERIVED; weight compared to actual'}


def weight_admit(actual, expected, reason='weight arithmetic disagreement'):
    a, b = float(actual), expected['weight']
    need(math.isfinite(a) and a >= 0 and math.isfinite(b) and b >= 0, reason)
    if expected['exact']:
        need(bits(a) == bits(b), reason)
    else:
        need(abs(a-b) <= 2.0**-14*abs(b) + 8*2.0**-149, reason)
    return True


def weights_check(energies, variances, weights, beta, gate, p):
    e = array(energies, dtype=NP.float32)
    v, w = array(variances, e.shape, NP.float32), array(weights, e.shape, NP.float32)
    need(bool((e >= 0).all()) and bool((v >= 0).all()) and bool((w >= 0).all()), 'negative weight operand')
    floors = NP.multiply(NP.float32(f32(gate*beta)), NP.maximum(v, NP.float32(0)), dtype=NP.float32)
    excess = NP.maximum(NP.subtract(e, floors, dtype=NP.float32), NP.float32(0))
    above = excess > 0
    threshold = ~above
    need(bool((w[threshold].view(NP.uint32) == 0).all()), 'threshold zero weight disagreement')
    r = NP.divide(NP.divide(excess, NP.maximum(floors, NP.float32(1)), dtype=NP.float32),
                  NP.float32(64), dtype=NP.float32)
    if p == 2.0:
        expected = NP.multiply(r, r, dtype=NP.float32)
        bit_equal(w, expected, 'p2 exact weight disagreement')
    elif p == 1.0:
        bit_equal(w, r, 'p1 exact weight disagreement')
    else:
        # Scalar libm gives a deliberately independent implementation of the nonlinear path.
        for j in NP.flatnonzero(above.reshape(-1)):
            expected = weight_reference(float(e.flat[j]), float(v.flat[j]), beta, gate, p)
            weight_admit(float(w.flat[j]), expected)
    return {'above_floor': int(above.sum()), 'threshold_zero': int(threshold.sum()),
            'positive_weights': int((w > 0).sum()),
            'positive_excess_zero_underflow': int((above & (w == 0)).sum()),
            'zero_positive_both_exercised': bool((w == 0).any() and (w > 0).any()),
            'floor': floors, 'above': above,
            'floor_scope': 'DERIVED from actual recorded operands; not directly logged'}


def chi_cdf(df, x, fault=None):
    need(type(df) is int and df in (2, 4, 11, 21), 'unsupported temporal degrees of freedom')
    need(type(x) in (int, float) and math.isfinite(x) and x >= 0, 'chi-square argument')
    if x == 0:
        return 0.0
    z = x/2.0
    odd = df%2 != 0 or fault == 'df4-half-start'
    a = 0.5 if odd else 1.0
    value = math.erf(math.sqrt(z)) if odd else -math.expm1(-z)
    target = df/2.0
    while a < target:
        omit = fault == 'omit-last-half-term' and df%2 and a+1 == target
        if not omit:
            value -= math.exp(a*math.log(z)-z-math.lgamma(a+1))
        a += 1
    return value


def chi_quantile(df, probability, fault=None):
    need(probability in (0.025, 0.975), 'fixed quantile probability')
    lo, hi = 0.0, 128.0
    need(chi_cdf(df, lo, fault) <= probability <= chi_cdf(df, hi, fault), 'quantile bracket')
    for _ in range(64):
        mid = (lo+hi)/2
        if chi_cdf(df, mid, fault) < probability:
            lo = mid
        else:
            hi = mid
    result = (lo+hi)/2
    need(abs(chi_cdf(df, result, fault)-probability) <= 1e-10, 'quantile inverse consistency')
    return result


def quantile_reference(df, values):
    need(df in NIST and len(values) == 2, 'NIST quantile population')
    for a, expected in zip(values, NIST[df]):
        need(math.isfinite(a) and abs(a-expected) <= 0.0005001, 'NIST quantile reference disagreement')
    return True


def variance_interval(value, df, domain='signed-scalar'):
    need(domain in ('signed-scalar', 'linear-band'), 'unlicensed interval domain')
    need(type(df) is int and df in (2, 4, 11, 21), 'unsupported temporal degrees of freedom')
    need(math.isfinite(value) and value >= 0, 'interval variance')
    lower_q, upper_q = chi_quantile(df, .025), chi_quantile(df, .975)
    return {'variance': value, 'df': df, 'lower': df*value/upper_q,
            'upper': df*value/lower_q, 'pointwise_level': .95,
            'scope': 'conditional independent Gaussian scalar; no quantization/drift/calibration coverage claim'}


def literal_texture(x, y):
    return 1000+20*x+30*y+200*((x//8+3*(y//8))%2)


def literal_texture_array(dx=0, dy=0):
    y, x = NP.indices((128, 128))
    return literal_texture(x+dx, y+dy).astype(NP.float64)


def box4(a):
    a = array(a, (96, 96), NP.float64)
    return a.reshape(24, 4, 24, 4).mean(axis=(1, 3), dtype=NP.float64)


def paper_nuisance(raw_frames, black, white):
    need(len(raw_frames) == 5, 'paper nuisance five inputs')
    signed = NP.stack([signed_planes(r, black) for r in raw_frames])
    headroom = ((signed >= 64) & (signed <= white-black-64))
    green = (signed[:, 1]+signed[:, 2])/2
    illumination, motion = input_screens(green)
    return {'headroom_ok': bool(headroom.all()), 'headroom_low_count': int((signed < 64).sum()),
            'headroom_high_count': int((signed > white-black-64).sum()),
            'illumination': illumination, 'motion': motion,
            'physical_paper_eligible': bool(headroom.all()) and not illumination['triggered'] and
                not motion['triggered'] and not motion['low_texture'],
            'scope': 'input-only effect-size screen; no stationarity truth or model agreement gate'}


def input_screens(green):
    a = array(green, (5, 128, 128), NP.float64)
    rectangles = ((16, 16, 96, 96), (16, 16, 48, 48), (64, 16, 48, 48),
                  (16, 64, 48, 48), (64, 64, 48, 48))
    means = []
    for frame in range(4):
        for x, y, w, h in rectangles:
            ref = float(a[4, y:y+h, x:x+w].mean())
            value = float(a[frame, y:y+h, x:x+w].mean())
            delta = value-ref
            means.append({'frame': frame, 'rectangle': [x, y, w, h], 'reference_mean': ref,
                          'actual_mean': value, 'delta_dn': delta,
                          'absolute_trigger': abs(delta) > 8,
                          'relative_trigger': abs(delta) > 0.005*abs(ref)})
    illumination = {'rows': means, 'triggered': any(r['absolute_trigger'] or r['relative_trigger'] for r in means)}
    reference = a[4, 16:112, 16:112]
    ref_boxes = box4(reference-reference.mean())
    texture = float(NP.sqrt(NP.mean(ref_boxes*ref_boxes)))
    comparisons, triggered = [], False
    for frame in range(4):
        scores = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                patch = a[frame, 16+dy:112+dy, 16+dx:112+dx]
                actual = box4(patch-patch.mean())
                score = float(NP.mean((actual-ref_boxes)**2))
                scores.append({'dx': dx, 'dy': dy, 'mse_box_means': score})
        zero = next(r['mse_box_means'] for r in scores if (r['dx'], r['dy']) == (0, 0))
        for r in scores:
            r['absolute_improvement'] = zero-r['mse_box_means']
            r['relative_improvement'] = (zero-r['mse_box_means'])/zero if zero > 0 else 0.0
            r['trigger'] = (r['dx'], r['dy']) != (0, 0) and r['absolute_improvement'] > 4 and r['relative_improvement'] > .25
        hit = any(r['trigger'] for r in scores); triggered |= hit
        comparisons.append({'frame': frame, 'zero_score': zero, 'scores': scores, 'triggered': hit})
    motion = {'reference_box_rms_dn': texture, 'low_texture': texture < 8,
              'triggered': triggered, 'comparisons': comparisons,
              'scope': 'fixed gross-motion alternative scores; no transform applied; subpixel motion unresolved'}
    return illumination, motion


def model_admit(gains, read_e):
    need(len(gains)==len(read_e)==4 and
         [bits(v) for v in gains]==[bits(f32(f32(160)/f32(436.8)))]*4 and
         [bits(v) for v in read_e]==[bits(f32(4.2))]*4, 'immutable profile operands')
    return True


def beta_admit(route, prefix, k, measured, selected, white):
    need(type(route) is int and route in (0,1) and type(k) is int and 0<=k<4 and
         type(measured) is bool, 'beta route types')
    need(type(prefix) in (list,tuple) and len(prefix)==route*3 and
         all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in prefix), 'beta supplied prefix')
    need(math.isfinite(selected) and selected>=0 and math.isfinite(white) and white>=0, 'finite beta selection')
    expected_measured=route==1 and k<3
    need(measured is expected_measured, 'beta measured-source association')
    expected=prefix[k] if expected_measured else white
    need(bits(selected)==bits(expected), 'selected beta disagreement')
    return True


def observer_equal(left, right):
    need(type(left) is dict and type(right) is dict and set(left)==set(right)=={'collapsed','tiff'},
         'observer evidence roles')
    need(all(type(v) is bytes and len(v)>0 for v in [*left.values(),*right.values()]), 'observer evidence buffers')
    need(left['collapsed']==right['collapsed'], 'observer collapsed byte disagreement')
    need(left['tiff']==right['tiff'], 'observer whole TIFF byte disagreement')
    return True


def threshold_side_admit(side, energy_value, variance, beta, gate):
    need(type(side) is bool,'derived threshold-side type')
    floor=f32(f32(f32(gate)*f32(beta))*max(f32(variance),0.))
    expected=max(f32(f32(energy_value)-floor),0.)>0
    need(side is expected,'derived threshold-side association')
    return True


def reference_admit(role):
    need(type(role) is dict and set(role)=={'original_ordinals','estimator'} and
         role['original_ordinals']==[4] and all(type(v) is int for v in role['original_ordinals']) and
         role['estimator']=='single-held-frame4','fixed disjoint signal reference')
    return True
