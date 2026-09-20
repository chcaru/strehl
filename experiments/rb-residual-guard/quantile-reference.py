"""Independent SciPy quantiles for the fixed proposed local null rule."""
import hashlib
import json
from pathlib import Path
import scipy
from scipy.stats import f

out = Path(__file__).resolve().with_name('quantile-reference.json')
assert not out.exists()
rows = []
for count, bands in [(2, 1), (5, 4), (9, 4), (16, 7), (70, 7), (299, 7)]:
    tail = .01 / (2 * count * bands * 25)
    q = float(f.isf(tail, 1, 8))
    measured_tail = float(f.sf(q, 1, 8))
    assert abs(measured_tail / tail - 1) < 2e-7
    assert float(f.sf(.5 * q, 1, 8)) > 5 * tail
    rows.append(dict(sources=count, bands=bands, tail=tail, quantile=q,
                     scipy_survival=measured_tail,
                     half_quantile_survival=float(f.sf(.5*q, 1, 8))))
result = dict(scipy_version=scipy.__version__, rows=rows,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    primary_reference='https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.f.html',
    scope='Distribution arithmetic only; does not establish Gaussianity, independence, camera calibration or photographic quality.')
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(rows))
