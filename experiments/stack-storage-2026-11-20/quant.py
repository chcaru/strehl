"""The calibrated quantiser of S6/S7: a per-sample table from the product's noise model.

Raw values are grouped into consecutive bins; a bin's code is its index and its
reconstruction is its MIDDLE member. Every bin has an ODD number of integer members, the
largest odd width w with (w^2 - 1) / 12 <= (k sigma)^2 / 12, sigma being the model's noise
(variance a (v - B) + r^2 DN^2) at the bin's middle. So:

- the error of a sample is an integer in [-(w - 1) / 2, +(w - 1) / 2], at most k sigma / 2;
- the reconstruction is the centroid of its bin, so a locally flat density has zero mean
  error (a first version reconstructed at the centre in the variance-stabilised domain and
  rounded: bins of even width then carried up to half a DN of bias each, which showed as a
  level-dependent bias of a mean of repeats; MEASURED, kept in s6-stats-v1.txt);
- the added variance is (w^2 - 1) / 12 <= (k sigma)^2 / 12 at every level;
- where k sigma < 3 DN (near black) the width is 1: those values are stored exactly;
- 16383 (clipped) has a code of its own and is restored exactly.

Each sample is quantised on its own value alone: no prediction and no neighbours, so an
error cannot spread or follow an edge.
"""
import numpy as np

BLACK, GAIN, READ = 512.0, 0.4040, 1.334
WHITE = 16383


def sigma(v):
    return np.sqrt(GAIN * np.maximum(np.asarray(v, dtype=np.float64) - BLACK, 0.0) + READ * READ)


def tables(k):
    """(code of every raw value 0..16383 as uint16, raw value of every code as uint16, bin width of every code)."""
    code = np.zeros(WHITE + 1, dtype=np.uint16)
    rec = []
    width = []
    v = 0
    while v < WHITE:
        w = 1
        while True:
            w2 = w + 2
            mid = v + (w2 - 1) // 2
            if v + w2 <= WHITE and (w2 * w2 - 1) <= (k * float(sigma(mid))) ** 2:
                w = w2
            else:
                break
        code[v:v + w] = len(rec)
        rec.append(v + (w - 1) // 2)
        width.append(w)
        v += w
    code[WHITE] = len(rec)
    rec.append(WHITE)
    width.append(1)
    return code, np.array(rec, dtype=np.uint16), np.array(width, dtype=np.int64)
