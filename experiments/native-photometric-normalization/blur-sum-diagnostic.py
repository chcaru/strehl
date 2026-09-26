"""Tiny standalone diagnostic for the generated fixture; no RAW or stack code."""
from pathlib import Path
import json
import math
import hashlib
import struct

W, H = 384, 320


def naive(values):
    # Python 3.12 sum() is compensated; explicitly reproduce a left fold.
    result = 0.0
    for value in values:
        result += value
    return result


def compensated(values):
    total, correction = 0.0, 0.0
    for value in values:
        adjusted = value-correction
        updated = total+adjusted
        correction = (updated-total)-adjusted
        total = updated
    return total


def blur(src, radius):
    mid, out = [0.0]*(W*H), [0.0]*(W*H)
    n = float(2*radius+1)
    for y in range(H):
        total = naive(src[y*W+(W+j-radius) % W] for j in range(2*radius+1))
        for x in range(W):
            mid[y*W+x] = total/n
            total += src[y*W+(x+radius+1) % W]-src[y*W+(x+W-radius) % W]
    for x in range(W):
        total = naive(mid[((H+j-radius) % H)*W+x] for j in range(2*radius+1))
        for y in range(H):
            out[y*W+x] = total/n
            total += mid[((y+radius+1) % H)*W+x]-mid[((y+H-radius) % H)*W+x]
    return out


rows = []
inside = [(j % W-192)**2+(j//W-160)**2 < 58**2 for j in range(W*H)]
for c, (base, amplitude) in enumerate(zip((.30, .28, .24), (.32, .30, .22))):
    src = [base+(amplitude if value else 0.0) for value in inside]
    for radius in (32, 80):
        out = blur(src, radius)
        source_naive, output_naive = naive(src), naive(out)
        source_fsum, output_fsum = math.fsum(src), math.fsum(out)
        before_hash = hashlib.sha256(b''.join(struct.pack('<d', x) for x in out)).hexdigest()
        source_compensated, output_compensated = compensated(src), compensated(out)
        after_hash = hashlib.sha256(b''.join(struct.pack('<d', x) for x in out)).hexdigest()
        assert before_hash == after_hash
        assert abs(source_compensated-output_compensated)/abs(source_compensated) < 1e-12
        rows.append(dict(channel=c, radius=radius,
            naive_source=source_naive, naive_output=output_naive,
            naive_relative_difference=abs(source_naive-output_naive)/abs(source_naive),
            fsum_source=source_fsum, fsum_output=output_fsum,
            fsum_relative_difference=abs(source_fsum-output_fsum)/abs(source_fsum),
            compensated_source=source_compensated, compensated_output=output_compensated,
            compensated_relative_difference=abs(source_compensated-output_compensated)/abs(source_compensated),
            output_f64_le_sha256=before_hash, output_unchanged=before_hash == after_hash,
            analytic_source=base*W*H+amplitude*inside.count(True)))
result = dict(scope="Fixture-only f64 summation diagnostic, no candidate or RAW run",
              fixed_tolerance=1e-12, rows=rows)
path = Path(__file__).with_name('blur-sum-diagnostic-2.json')
with path.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result, indent=2))
