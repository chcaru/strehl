"""Warp sidecar parsing and the corner-error geometry, re-implemented.

The point of re-implementing rather than calling into strehl is that this lane
is testing a hypothesis about strehl's alignment. An instrument that shares
code with its subject cannot find a fault in that shared code, and a number
that agrees with the product because it *is* the product has not been checked.

The geometry is taken from `align.rs` at pin `9b05d0b7`:

    corner_err(p, q)  = max over plane-centred corners c of |(p.a - q.a) c + (p.b - q.b)|
    corner_err_parts  = (rho |da|, |db|)      rho = |(W/2, H/2)|

A similarity is the complex map z -> a z + b with z measured from the plane
centre, so the reference frame has a = 1, b = 0.

`selfcheck()` is the commissioning: strehl prints its own
"total corner drift frame 0 -> N-1" when it solves, and this module must
reproduce that number from the sidecar alone. If it does not, nothing else in
this lane can be trusted.
"""

import cmath
import re
import struct


def _f64(word):
    """Sidecar stores f64 as a big-endian hex bit pattern."""
    return struct.unpack(">d", bytes.fromhex(word))[0]


class WarpMap:
    def __init__(self, path):
        self.path = path
        self.name = None
        self.frames = None
        self.width = None
        self.height = None
        self.reference = None
        self.heldout_px = None
        self.cycle_floor_px = None
        self.spans = None
        self.a = {}
        self.b = {}
        self.state = {}
        self._parse(path)

    def _parse(self, path):
        for line in open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.startswith("#") or not line.strip():
                continue
            tok = line.split()
            head = tok[0]
            if head == "stack-name":
                self.name = tok[1]
            elif head == "frames":
                self.frames = int(tok[1])
            elif head == "plane":
                w, h = tok[1].split("x")
                self.width, self.height = int(w), int(h)
            elif head == "reference":
                self.reference = int(tok[1])
            elif head == "heldout-px":
                self.heldout_px = None if tok[1] == "none" else _f64(tok[1])
            elif head == "cycle-floor-px":
                self.cycle_floor_px = None if tok[1] == "none" else _f64(tok[1])
            elif head == "note":
                m = re.search(r"spans \[([0-9, ]+)\]", line)
                if m:
                    self.spans = [int(x) for x in m.group(1).split(",")]
            elif head.isdigit():
                idx = int(head)
                self.state[idx] = tok[1]
                if tok[1] == "placed":
                    self.a[idx] = complex(_f64(tok[2]), _f64(tok[3]))
                    self.b[idx] = complex(_f64(tok[4]), _f64(tok[5]))

    # -- geometry -------------------------------------------------------

    def corners(self):
        w, h = self.width / 2.0, self.height / 2.0
        return [complex(-w, -h), complex(w, -h), complex(-w, h), complex(w, h)]

    def rho(self):
        return abs(complex(self.width / 2.0, self.height / 2.0))

    def corner_err(self, i, j):
        """Worst-corner disagreement between two frames' placements, plane px."""
        da = self.a[i] - self.a[j]
        db = self.b[i] - self.b[j]
        return max(abs(da * c + db) for c in self.corners())

    def corner_err_parts(self, i, j):
        da = self.a[i] - self.a[j]
        db = self.b[i] - self.b[j]
        return self.rho() * abs(da), abs(db)

    def params(self, i):
        """(scale-1, rotation rad, dx, dy) -- the human-readable decomposition."""
        a, b = self.a[i], self.b[i]
        return abs(a) - 1.0, cmath.phase(a), b.real, b.imag

    def placed(self):
        return sorted(self.a)

    def rel(self, i, j):
        """Relative map i -> j, as (a, b), with the solve's reference removed."""
        r = self.a[j] / self.a[i]
        s = self.b[j] - r * self.b[i]
        return r, s

    def rel_err(self, base, j):
        """Corner error of the relative map base -> j against identity."""
        r, s = self.rel(base, j)
        return max(abs((r - 1.0) * c + s) for c in self.corners())

    def total_drift(self, base=0):
        """strehl's `total_drift`: max over placed frames of corner error vs identity.

        Reproducing it needs one fact that is not in the sidecar: the array
        `total_drift` sees is referenced to **frame 0**, and the placements are
        re-referenced to the middle frame only when the sidecar is written. So
        the printed number is the worst drift measured from frame 0, not from
        the sidecar's own reference. On bee-3-cpl: 185.266 px from frame 0
        (matches the product exactly) against 132.508 px from the middle.

        That gap is not noise -- it is the measured value of the middle
        reference, 1.40x less worst-case drift for free.
        """
        return max(self.rel_err(base, i) for i in self.placed())


def cross_err(wm1, wm2, i, j):
    """Disagreement between two *solves* about the relative geometry of i and j.

    Each solve has its own reference, so absolute placements are not
    comparable; the relative map i->j is. Composing q_j . q_i^-1 removes the
    reference and leaves a quantity two independent solves must agree on.
    """
    r1 = wm1.a[j] / wm1.a[i]
    s1 = wm1.b[j] - r1 * wm1.b[i]
    r2 = wm2.a[j] / wm2.a[i]
    s2 = wm2.b[j] - r2 * wm2.b[i]
    da, db = r1 - r2, s1 - s2
    w, h = wm1.width / 2.0, wm1.height / 2.0
    cs = [complex(-w, -h), complex(w, -h), complex(-w, h), complex(w, h)]
    return max(abs(da * c + db) for c in cs)


def selfcheck(path, expect_drift, tol=0.01):
    """Reproduce strehl's own printed drift from the sidecar alone."""
    wm = WarpMap(path)
    got = wm.total_drift()
    ok = abs(got - expect_drift) <= tol
    print(f"selfcheck {wm.name}: total corner drift {got:.3f} px, "
          f"strehl printed {expect_drift:.3f} px, "
          f"delta {got - expect_drift:+.4f}  {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if selfcheck(sys.argv[1], float(sys.argv[2])) else 1)
