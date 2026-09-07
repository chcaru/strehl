"""Scoped unit-interval quadrature adapter; no numerical dependency imports.

The caller supplies its original quadrature. Frozen Cartesian callbacks charge
their own shared resource budget; these counters are mandatory accounting only.
"""
from contextlib import contextmanager
import math

ADAPTER = 'cartesian-unit-interval-v1'
MAPPING = 'nearest-endpoint-affine-binary64-v1'
_installed_modules = set()


class IntervalRefusal(RuntimeError):
    pass


def finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise IntervalRefusal('nonfinite/non-numeric '+label)
    return float(value)


def coordinate(a, b, width, u):
    u = finite_number(u, 'unit coordinate')
    if not 0. <= u <= 1.:
        raise IntervalRefusal('unit coordinate outside interval')
    if u == 0.:
        t = a
    elif u == 1.:
        t = b
    elif u <= .5:
        t = a + width*u
    else:
        t = b - width*(1.-u)
    if not math.isfinite(t) or not a <= t <= b:
        raise IntervalRefusal('mapped coordinate outside original interval')
    return t


def weighted_sample(value, width):
    value = finite_number(value, 'integrand value')
    weighted = width*value
    if not math.isfinite(weighted):
        raise IntervalRefusal('nonfinite weighted integrand')
    return weighted


def absolute_request(epsabs, width):
    # Width belongs inside the callback, not in the requested absolute error.
    return epsabs


def returned_integral(pair, width):
    # Both values already have the original integral's units.
    return pair


class Normalizer:
    def __init__(self, target_e, observer=None):
        self.target_e = finite_number(target_e, 'target')
        if self.target_e <= 0:
            raise IntervalRefusal('nonpositive target')
        self.observer = observer
        self.intervals = 0
        self.integrand_calls = 0

    def receipt(self, *, intervals=None, integrand_calls=None, target_e=None):
        return dict(adapter=ADAPTER, mapping=MAPPING, jacobian='inside-weighted-callback',
                    request='unchanged-epsabs', target_e=self.target_e if target_e is None else target_e,
                    intervals=self.intervals if intervals is None else intervals,
                    integrand_calls=self.integrand_calls if integrand_calls is None else integrand_calls)

    def quad(self, original, function, a, b, **kwargs):
        a, b = finite_number(a, 'left bound'), finite_number(b, 'right bound')
        if not -1. <= a < b <= 1.:
            raise IntervalRefusal('original interval outside pupil domain')
        width = b-a
        if not math.isfinite(width) or width <= 0:
            raise IntervalRefusal('nonfinite/nonpositive interval width')
        if set(kwargs) != {'epsabs', 'epsrel', 'limit'}:
            raise IntervalRefusal('changed quadrature arguments')
        epsabs = finite_number(kwargs['epsabs'], 'absolute request')
        epsrel = finite_number(kwargs['epsrel'], 'relative request')
        if epsabs <= 0 or epsrel != 0. or type(kwargs['limit']) is not int or kwargs['limit'] != 128:
            raise IntervalRefusal('unsupported quadrature request')
        self.intervals += 1

        def callback(u):
            t = coordinate(a, b, width, u)
            self.integrand_calls += 1
            value = function(t)
            weighted = weighted_sample(value, width)
            if self.observer is not None:
                self.observer(u, t, value, weighted)
            return weighted

        # No warning interception: the frozen caller retains its warning guard.
        pair = original(callback, 0., 1., epsabs=absolute_request(epsabs, width),
                        epsrel=kwargs['epsrel'], limit=kwargs['limit'])
        return returned_integral(pair, width)

    @contextmanager
    def installed(self, module):
        identity = id(module)
        if identity in _installed_modules:
            raise IntervalRefusal('nested interval adapter installation')
        original = module.quad
        _installed_modules.add(identity)
        try:
            def adapted(function, a, b, **kwargs):
                return self.quad(original, function, a, b, **kwargs)
            module.quad = adapted
            yield self
        finally:
            module.quad = original
            _installed_modules.remove(identity)
