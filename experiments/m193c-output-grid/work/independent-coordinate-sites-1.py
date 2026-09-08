"""Independent saved-Q8 site review. JSON only; no subject imports or fits.

Predeclared failure inputs: repeated physical sites must not be counted as
independent split support; distinct sites must not be collapsed; a 5-pixel
one-source/two-destination contradiction must be found, while 4 pixels is
only the triangle-inequality boundary. Radius-1 components may chain, and a
0,.75,1.5 pixel control must expose that diameter rather than hide it.
"""
import hashlib
import itertools
import json
import math
import pathlib
import time

BASE = pathlib.Path(__file__).resolve().parent
WORKER = BASE.parent / 'direct-pair-1' / 'worker'
OUTPUT = BASE / 'independent-coordinate-sites-1.json'
Q = 256
SIDES = ('source_q8', 'reference_q8', 'joint')


def d2(a, b):
    return sum((x-y)**2 for x, y in zip(a, b))


def endpoints(row, side):
    return [row['source_q8'], row['reference_q8']] if side == 'joint' else [row[side]]


def endpoint_distance2(a, b, side):
    # Joint adjacency requires BOTH endpoint distances within the radius.
    return max(d2(x, y) for x, y in zip(endpoints(a, side), endpoints(b, side)))


def grouped(rows, side, radius_q8):
    # Explicit undirected adjacency + graph traversal, not author's dictionary.
    adjacency = [set() for _ in rows]
    cross_edges = []
    for i, j in itertools.combinations(range(len(rows)), 2):
        if endpoint_distance2(rows[i], rows[j], side) <= radius_q8**2:
            adjacency[i].add(j)
            adjacency[j].add(i)
            if rows[i]['split'] != rows[j]['split']:
                cross_edges.append([i, j])
    remaining, components = set(range(len(rows))), []
    while remaining:
        pending, component = [min(remaining)], []
        while pending:
            i = pending.pop()
            if i not in remaining:
                continue
            remaining.remove(i)
            component.append(i)
            pending.extend(adjacency[i] & remaining)
        components.append(sorted(component))
    mixed, chained = [], []
    for ids in components:
        diameter2 = max((endpoint_distance2(rows[i], rows[j], side)
                         for i, j in itertools.combinations(ids, 2)), default=0)
        entry = {'rows': ids, 'diameter_native_px': math.sqrt(diameter2)/Q}
        if len({rows[i]['split'] for i in ids}) > 1:
            mixed.append(entry)
        if diameter2 > radius_q8**2:
            chained.append(entry)
    return {'groups': len(components), 'repeated_groups': sum(len(x)>1 for x in components),
            'mixed_split_groups': mixed, 'direct_cross_split_edges': cross_edges,
            'chained_components': chained}


def contradictions(rows):
    out = []
    for i, j in itertools.combinations(range(len(rows)), 2):
        if rows[i]['source_q8'] == rows[j]['source_q8']:
            separation2 = d2(rows[i]['reference_q8'], rows[j]['reference_q8'])
            if separation2 > (4*Q)**2:
                out.append({'rows': [i,j], 'source_q8': rows[i]['source_q8'],
                            'reference_q8': [rows[i]['reference_q8'],rows[j]['reference_q8']],
                            'reference_separation_native_px': math.sqrt(separation2)/Q,
                            'splits': [rows[i]['split'], rows[j]['split']]})
    return out


def summary(rows):
    return {f'{side}:{radius}': grouped(rows, side, radius)
            for side in SIDES for radius in (0, Q)}


def row(x, split, y=None):
    return {'source_q8': [x,0], 'reference_q8': [x if y is None else y,0], 'split': split}


def control():
    repeated = [row((i//6)*10*Q, 'calibration' if i%2==0 else 'holdout') for i in range(12)]
    distinct = [row(i*10*Q, 'calibration' if i%2==0 else 'holdout') for i in range(12)]
    a, b = summary(repeated), summary(distinct)
    assert all(x['groups']==2 and len(x['mixed_split_groups'])==2 for x in a.values())
    assert all(x['groups']==12 and not x['mixed_split_groups'] for x in b.values())
    bad = [row(0, 'calibration', 0), row(0, 'holdout', 5*Q)]
    edge = [row(0, 'calibration', 0), row(0, 'holdout', 4*Q)]
    assert len(contradictions(bad))==1 and not contradictions(edge)
    chain = [row(0, 'calibration'),row(3*Q//4, 'calibration'),row(3*Q//2, 'holdout')]
    c = grouped(chain, 'joint', Q)
    assert c['groups']==1 and c['chained_components'][0]['diameter_native_px']==1.5
    assert c['direct_cross_split_edges']==[[1,2]]
    assert grouped(chain, 'joint', 0)['groups']==3
    shifted = [{**r, 'source_q8': [r['source_q8'][0]+173*Q,41*Q],
                'reference_q8': [r['reference_q8'][0]+173*Q,41*Q]} for r in repeated]
    assert summary(shifted)==a
    assert len(contradictions(list(reversed(bad))))==1
    return {'status': 'PASS', 'cases': [
        'twelve_rows_two_sites_mixed_splits', 'twelve_distinct_sites_disjoint_splits',
        'five_pixel_destination_contradiction', 'four_pixel_boundary_companion',
        'radius_one_chains_to_one_point_five', 'joint_translation_placebo',
        'row_reversal_contradiction_preserved']}


def digest(path):
    raw = path.read_bytes()
    return raw, {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    wall, cpu = time.perf_counter(), time.process_time()
    controls = control()  # Before any real statistic.
    paths = sorted(WORKER.glob('pair-*-*.json'))
    assert len(paths)==23
    inputs, results = [], []
    for path in paths:
        raw, ref = digest(path)
        assert len(raw)<60000
        value = json.loads(raw)
        outcome, pair = value['outcome'], value['pair']
        assert path.stem==pair['id']
        assert outcome['status']=='REGISTRATION_REFUSED' and outcome['transform'] is None
        rows = outcome['landmarks']
        assert len(rows)<257
        assert len({r['digest'] for r in rows})==len(rows)
        for r in rows:
            assert r['inlier'] is None and r['split'] in ('calibration','holdout')
            for side in SIDES[:2]:
                assert len(r[side])==2 and all(type(x) is int for x in r[side])
                assert 0<=r[side][0]<7032*Q and 0<=r[side][1]<4688*Q
        identity = [i for i,r in enumerate(rows) if d2(r['source_q8'],r['reference_q8']) <= (2*Q)**2]
        nearrows = [rows[i] for i in identity]
        stats = summary(rows)
        conflicts = contradictions(rows)
        results.append({'pair': pair, 'rows': len(rows), 'groups': stats,
                        'exact_source_conflicts': conflicts,
                        'identity_within_two_native_px': {
                            'rows': identity, 'count': len(identity),
                            'reference_exact_sites': grouped(nearrows,'reference_q8',0)['groups'],
                            'reference_radius_one_sites': grouped(nearrows,'reference_q8',Q)['groups']}})
        inputs.append(ref)
    for ref in inputs:
        assert digest(pathlib.Path(ref['path']))[1]==ref
    source = digest(pathlib.Path(__file__).resolve())[1]
    totals = {
        'pair_count': len(results),
        'pairs_with_exact_source_contradiction': [r['pair']['id'] for r in results if r['exact_source_conflicts']],
        'contradictory_exact_source_groups': sum(len({tuple(c['source_q8']) for c in r['exact_source_conflicts']}) for r in results),
        'mixed_exact_joint_pairs_all_23': sum(bool(r['groups']['joint:0']['mixed_split_groups']) for r in results),
        'mixed_exact_joint_pairs_at_least_24_rows': sum(bool(r['groups']['joint:0']['mixed_split_groups']) for r in results if r['rows']>=24),
        'mixed_radius_one_joint_pairs_all_23': sum(bool(r['groups']['joint:256']['mixed_split_groups']) for r in results),
        'chained_components_all_sides_radius_one': sum(len(r['groups'][f'{s}:256']['chained_components']) for r in results for s in SIDES)}
    receipt = {'schema':'m193c-independent-coordinate-sites-v1',
               'status':'PASS_SAVED_COORDINATE_REVIEW_ONLY', 'source':source,'inputs':inputs,
               'controls':controls,'summary':totals,'pairs':results,
               'image_feature_fit_calls':0,
               'timing': {'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-wall}}
    raw = (json.dumps(receipt,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    assert len(raw)+source['bytes'] < 120000
    with OUTPUT.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'output': str(OUTPUT),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                      'summary':totals,'timing':receipt['timing']},sort_keys=True))
    for r in results:
        if r['rows']>=24:
            print(json.dumps({'pair':r['pair']['id'],'rows':r['rows'],
                              'exact_joint_mixed':len(r['groups']['joint:0']['mixed_split_groups']),
                              'near_joint_mixed':len(r['groups']['joint:256']['mixed_split_groups']),
                              'identity':r['identity_within_two_native_px'],
                              'conflicts':r['exact_source_conflicts']},sort_keys=True))


if __name__=='__main__':
    main()
