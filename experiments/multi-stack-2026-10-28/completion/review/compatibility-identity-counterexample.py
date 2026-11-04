"""Independent arithmetic counterexample; no RAW, engine, or image files.
Run: python experiments/multi-stack-2026-10-28/completion/review/compatibility-identity-counterexample.py
This reproduces the old statistic, not a Rust producer execution.
"""
import hashlib
import itertools
import json
import math
import random
from pathlib import Path

coordinates = list(itertools.product(range(-2, 3), repeat=2))
low1 = {p: ((1, 2, 1)[p[0]+1]*(1, 2, 1)[p[1]+1]/16
            if max(map(abs, p)) <= 1 else 0.) for p in coordinates}
low2 = {p: (1, 4, 6, 4, 1)[p[0]+2]*(1, 4, 6, 4, 1)[p[1]+2]/256
        for p in coordinates}
bands = [[float(p == (0, 0))-low1[p] for p in coordinates],
         [low1[p]-low2[p] for p in coordinates],
         [low2[p] for p in coordinates]]
first = [100. if p == (0, 0) or max(map(abs, p)) == 2 else 10000.
         for p in coordinates]
second = [v+(20. if p == (0, 0) else 0.) for p, v in zip(coordinates, first)]
covariances = [[[sum(bands[i][k]*bands[j][k]*means[k] for k in range(25))
                 for j in range(3)] for i in range(3)]
               for means in (first, second)]
combined = [[covariances[0][i][j]+covariances[1][i][j] for j in range(3)]
            for i in range(3)]
count, seed = 1024, 117
rng = random.Random(seed)
observations = []
for _ in range(count):
    raw = [[rng.gauss(m, math.sqrt(m)) for m in means] for means in (first, second)]
    observations.append([[sum(a*b for a, b in zip(weights, values)) for weights in bands]
                         for values in raw])

def interval(observed, trace, frobenius2, spectral_bound):
    t = math.log(100.)
    z, v, a = observed-trace, spectral_bound, frobenius2
    rad = t*(a+2*v*z+4*t*v*v)
    if rad < 0:
        return None
    upper = z+4*t*v+2*math.sqrt(rad)
    q = z-2*v*t
    lower = (0. if q <= 2*math.sqrt(t*a) else
             max(0., q+4*t*v-2*math.sqrt(t*(a+2*v*q+4*t*v*v))))
    return [lower, upper]

results = []
for b in range(3):
    vx, vy = covariances[0][b][b], covariances[1][b][b]
    v = vx+vy
    ex = interval(sum(x[b]**2 for x, y in observations), count*vx, count*vx*vx, vx)
    ey = interval(sum(y[b]**2 for x, y in observations), count*vy, count*vy*vy, vy)
    ed = interval(sum((x[b]-y[b])**2 for x, y in observations), count*v, count*v*v, v)
    es = interval(sum((x[b]+y[b])**2 for x, y in observations), count*v, count*v*v, v)
    cross = [(es[0]-ed[1])/4, (es[1]-ed[0])/4]
    yx, xy = [cross[0]/ex[1], cross[1]/ex[0]], [cross[0]/ey[1], cross[1]/ey[0]]
    loss = [value/(count*v) for value in ed]
    admitted = loss[1] <= .5 and (b == 2 or
                  all(.95 <= lo <= hi <= 1.05 for lo, hi in (yx, xy)))
    results.append(dict(band=b, loss=loss, y_from_x=yx, x_from_y=xy, admitted=admitted))
vop = max(sum(abs(v) for v in row) for row in combined)
trace = count*sum(combined[i][i] for i in range(3))
frob = count*sum(v*v for row in combined for v in row)
observed = sum(sum((x[b]-y[b])**2 for b in range(3)) for x, y in observations)
joint_loss = [v/trace for v in interval(observed, trace, frob, vop)]
native_variance = sum(map(sum, combined))
native_observed = sum((sum(x)-sum(y))**2 for x, y in observations)
native_loss = [v/(count*native_variance) for v in interval(
    native_observed, count*native_variance, count*native_variance**2, native_variance)]
report = dict(
    scope="Independent Gaussian arithmetic plant; actual integer-phase binomial taps; not engine execution or camera calibration.",
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    points=count, seed=seed, original_site_variance="known signal",
    first_original_means=first, second_original_means=second,
    covariances=covariances, bands=results, joint_loss=joint_loss,
    identity_loss=native_loss, true_identity_loss=400/220,
    true_native_equal_mean_excess_mse=400/4-220/4,
    old_admitted=all(b["admitted"] for b in results) and joint_loss[1] <= .5,
    fixed_identity_gate_admitted=native_loss[1] <= .5)
assert report["old_admitted"]
assert not report["fixed_identity_gate_admitted"]
assert native_loss[0] > .5
print(json.dumps(report, indent=2))
