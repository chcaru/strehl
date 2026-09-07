"""Exact finite-coefficient support selector; no radiance evaluation."""
from fractions import Fraction
import math
import numbers

import numpy as np


class UnsupportedRational(ArithmeticError):
    pass


class BoundedRationals:
    def __init__(self, bits=4096):
        if type(bits) is not int or not 1 <= bits <= 4096:
            raise ValueError("rational bit limit must be1..4096")
        self.bits = bits

    def integer(self, value):
        if abs(value).bit_length() > self.bits:
            raise UnsupportedRational("rational intermediate bit ceiling")
        return value

    def product(self, a, b):
        if abs(a) == 1:
            return self.integer(b if a > 0 else -b)
        if abs(b) == 1:
            return self.integer(a if b > 0 else -a)
        if a and b and abs(a).bit_length() + abs(b).bit_length() > self.bits:
            raise UnsupportedRational("rational product preallocation ceiling")
        return self.integer(a * b)

    def sum(self, a, b):
        # Opposite signs cannot grow; same-sign addition may gain one bit.
        if a and b and (a > 0) == (b > 0) and max(abs(a).bit_length(), abs(b).bit_length()) + 1 > self.bits:
            raise UnsupportedRational("rational sum preallocation ceiling")
        return self.integer(a + b)

    def value(self, value):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real) or not math.isfinite(value):
            raise ValueError("finite real coefficient required")
        if isinstance(value, numbers.Integral):
            return Fraction(self.integer(int(value)), 1)
        n, d = float(value).as_integer_ratio()
        return Fraction(self.integer(n), self.integer(d))

    def add(self, a, b):
        return Fraction(self.sum(self.product(a.numerator, b.denominator),
                                 self.product(b.numerator, a.denominator)),
                        self.product(a.denominator, b.denominator))

    def mul(self, a, b):
        return Fraction(self.product(a.numerator, b.numerator), self.product(a.denominator, b.denominator))

    def neg(self, a):
        return Fraction(-a.numerator, a.denominator)


class ExactSelector:
    def __init__(self, scene, frame, bit_limit=4096, budget=None):
        self.arithmetic = BoundedRationals(bit_limit)
        self.unsupported_reason = None
        self.mask_state = scene.mask_state
        if self.mask_state not in ("half-plane", "full", "absent"):
            raise ValueError("unknown mask state")
        if budget is not None:
            budget.check()
        matrix = frame.forward_similarity.inverse_matrix()
        if matrix.shape != (2, 2) or not np.isfinite(matrix).all():
            raise ValueError("finite2x2 inverse matrix required")
        if budget is not None:
            budget.watch(matrix)
        raw = [*matrix.flat, *frame.forward_similarity.centre,
               *frame.forward_similarity.translation, *scene.mask_normal,
               scene.mask_offset, frame.defocus(scene)[0]]
        if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, numbers.Real) or not math.isfinite(v) for v in raw):
            raise ValueError("finite model coefficients required")
        if math.hypot(*scene.mask_normal) == 0:
            raise ValueError("nonzero mask normal required")
        self._coefficients = {}
        try:
            r = self.arithmetic
            m00, m01, m10, m11, cx, cy, tx, ty, nx, ny, offset, df = map(r.value, raw)
            a = r.add(r.mul(nx, m00), r.mul(ny, m10))
            b = r.add(r.mul(nx, m01), r.mul(ny, m11))
            c = r.add(r.add(r.mul(nx, cx), r.mul(ny, cy)), r.neg(offset))
            c = r.add(c, r.neg(r.mul(a, r.add(cx, tx))))
            c = r.add(c, r.neg(r.mul(b, r.add(cy, ty))))
            half = r.mul(r.add(abs(a), abs(b)), r.value(.5))
            radius2 = r.mul(r.mul(df, df), r.add(r.mul(a, a), r.mul(b, b)))
            self._coefficients = dict(a=a, b=b, c=c, half=half, radius_squared=radius2)
            scale = max(v.denominator for v in (a, b, c, half))
            if any(scale % v.denominator for v in (a, b, c, half)):
                raise ValueError("expected binary-rational denominators")
            self._scale = r.integer(scale)
            self._ints = tuple(r.product(v.numerator, scale // v.denominator) for v in (a, b, c, half))
            self._rden = radius2.denominator
            self._rhs = r.product(radius2.numerator, r.product(scale, scale))
        except UnsupportedRational as exc:
            self.unsupported_reason = str(exc)
        if budget is not None:
            budget.check()

    def coefficients(self):
        return {k: dict(numerator=str(v.numerator), denominator=str(v.denominator)) for k, v in self._coefficients.items()}

    def exact_height(self, xy):
        if self.unsupported_reason:
            raise UnsupportedRational(self.unsupported_reason)
        r = self.arithmetic
        if len(xy) != 2:
            raise ValueError("coordinate pair required")
        x, y = map(r.value, xy)
        return r.add(r.add(r.mul(self._coefficients["a"], x), r.mul(self._coefficients["b"], y)), self._coefficients["c"])

    def classify(self, xy):
        if len(xy) != 2 or any(isinstance(v, (bool, np.bool_)) or not isinstance(v, numbers.Real) or not math.isfinite(v) for v in xy):
            raise ValueError("finite coordinate pair required")
        if self.mask_state == "full":
            return "foreground"
        if self.mask_state == "absent":
            return "background"
        if self.unsupported_reason:
            return "numerical"
        r = self.arithmetic
        try:
            if all(isinstance(v, numbers.Integral) for v in xy):
                a, b, c, half = self._ints
                h = r.sum(r.sum(r.product(a, int(xy[0])), r.product(b, int(xy[1]))), c)
                clearance = r.sum(abs(h), -half)
                if clearance <= 0:
                    return "numerical"
                square = r.product(r.product(clearance, clearance), self._rden)
                return ("foreground" if h > 0 else "background") if square > self._rhs else "numerical"
            h = self.exact_height(xy)
            clearance = r.add(abs(h), r.neg(self._coefficients["half"]))
            if clearance <= 0:
                return "numerical"
            delta = r.add(r.mul(clearance, clearance), r.neg(self._coefficients["radius_squared"]))
            return ("foreground" if h > 0 else "background") if delta > 0 else "numerical"
        except UnsupportedRational:
            return "numerical"
