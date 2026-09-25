"""Read-only causal footprint check of the frozen pre-fix garnet census.

Independent of the observer's nominal-grid ROI calculation: expand every
recorded global band-2 bad site by the actual positive filter's two-step
support, then compare exact level-0 masks. No RAW or image output is read.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
PATH = HERE / 'garnet-on-1/census.json'
EXPECTED = '918f40337aabbdcd0c020efd56345dbbbdb18c83fbf2f64dd04031dd7f02907e'
raw = PATH.read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED
rows = json.loads(raw)
assert rows[0]['frames'] == 183 and rows[0]['sizes'][0] == [3262, 2174]
assert rows[-1] == dict(stage='end', completed_planes=4, expected_planes=4, complete=True)

def row(stage, plane, band=None):
    matches = [r for r in rows if r['stage'] == stage
               and r.get('plane') == plane and r.get('band') == band]
    assert len(matches) == 1
    return matches[0]

def decode(runs):
    result = set()
    for start, length, kind in runs:
        assert kind in (1, 2) and length > 0 and 0 <= start < start + length <= 192*192
        for i in range(start, start + length):
            assert (i % 192, i // 192) not in result
            result.add((i % 192, i // 192))
    return result

summary = []
for plane in range(4):
    band = row('resolved', plane, 2)
    coords = band['scan']['first_nonfinite_xy_bits']
    assert len(coords) == band['scan']['negative_infinity'] < 64
    assert band['scan']['nan'] == band['scan']['positive_infinity'] == 0
    assert all(bits == 0xff800000 for _, _, bits in coords)
    for k in range(8):
        for stage in ('denominator', 'unweighted_sum'):
            s = row(stage, 0 if stage == 'denominator' else plane, k)['scan']
            assert s['nan'] == s['positive_infinity'] == s['negative_infinity'] == 0
        if k != 2:
            s = row('resolved', plane, k)['scan']
            assert s['nan'] == s['positive_infinity'] == s['negative_infinity'] == 0
    # One expand is [2x-2,2x+2]; composing it gives [4x-6,4x+6].
    predicted = {(4*x+dx, 4*y+dy) for x,y,_ in coords
                 for dx in range(-6,7) for dy in range(-6,7)}
    inside = {(x-2334,y-929) for x,y in predicted if 2334 <= x < 2526 and 929 <= y < 1121}
    before = row('pre_hull',plane)
    actual = decode(before['island_nonfinite_runs'])
    after = row('post_hull',plane)
    lower = decode(after['previous_nonfinite_now_equal_lower_runs'])
    assert len(predicted) == before['scan']['negative_infinity']
    assert inside == actual == lower and actual
    # A one-site displacement preserves mask area but must fail correspondence.
    assert {(x+1,y) for x,y in inside} != actual
    assert not after['island_nonfinite_runs'] and not after['previous_nonfinite_now_equal_upper_runs']
    assert all(after['scan'][k] == 0 for k in ('nan','positive_infinity','negative_infinity'))
    summary.append(dict(plane=plane, band2_negative_infinities=len(coords),
                        pre_hull_global_sites=len(predicted), frozen_roi_sites=len(actual),
                        predicted_roi_exact=True, all_roi_bad_sites_equal_final_lower_bound=True,
                        shifted_mask_rejected=True))
print(json.dumps(dict(census_sha256=EXPECTED, planes=summary), indent=2))
