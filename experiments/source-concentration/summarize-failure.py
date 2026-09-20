"""Read retained locator records only; descriptive counts, not quality scores."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
TARGETS = [
    ('facet-core', 'facet-edges', [2624, 2906]),
    ('facet-fixed-fan', 'facet-edges', [2602, 2945]),
    ('dark-core', 'dark-inclusion', [3080, 2150]),
    ('dark-fixed-fan', 'dark-inclusion', [3102, 2203]),
    ('dark-visible-tail-postfailure', 'dark-inclusion', [3080, 2212]),
    ('nearby-structure', 'dark-inclusion', [3240, 2070]),
]


def bind(path):
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.output.resolve()
    assert source.is_relative_to(HERE) and out.is_relative_to(HERE) and not out.exists()
    receipt = json.loads(source.read_text())
    rows, frame_reasons, decision_reasons = [], Counter(), Counter()
    region_counts = Counter()
    for index, track in enumerate(receipt['tracks']):
        decision, seed = track['decision'], track['seed']
        frames = decision['frames']
        assert len(frames) == 70 and [f['index0'] for f in frames] == list(range(70))
        reasons = Counter(reason for frame in frames for reason in frame['eligibility_reasons'])
        frame_reasons.update(reasons)
        decision_reasons[decision['reason']] += 1
        region_counts[track['region']] += 1
        eligible = [f['index0'] for f in frames if f['eligible']]
        rows.append(dict(track=index, region=track['region'], seed_xy=[seed['x'], seed['y']],
                         status=decision['status'], reason=decision['reason'], index0=decision['index0'],
                         eligible_indices=eligible, eligible_frames=len(eligible), frame_reasons=dict(reasons)))
    nearest = []
    for name, region, point in TARGETS:
        candidates = sorted((row for row in rows if row['region'] == region),
                            key=lambda row: (math.dist(row['seed_xy'], point), row['seed_xy'][1], row['seed_xy'][0]))[:3]
        matches = []
        for row in candidates:
            track = receipt['tracks'][row['track']]
            eligible = [f for f in track['decision']['frames'] if f['eligible']]
            # Describe the rule's existing minimum; do not promote it as a donor.
            minimum = min((f['r'] for f in eligible), default=None)
            minimum_indices = [f['index0'] for f in eligible if f['r'] == minimum]
            witness_indices = sorted(set([25, 28, 33, 35, 52, 69] + minimum_indices))
            witnesses = [f for f in track['decision']['frames'] if f['index0'] in witness_indices]
            matches.append(dict(**row, seed_distance_native=math.dist(row['seed_xy'], point),
                                rule_minimum_indices=minimum_indices, source_records=witnesses))
        nearest.append(dict(name=name, region=region, native_xy=point, nearest=matches,
                            membership='Unknown; seed distance and footprint bounds do not prove component membership'))
    summary = dict(scope='Read-only failure characterization; failed generated screen remains failed; no repair admission',
                   helper=bind(Path(__file__)), input=bind(source), tracks=len(rows),
                   nominations=sum(row['status'] == 'nominated' for row in rows), regions=dict(region_counts),
                   decision_reasons=dict(decision_reasons), frame_track_records=70 * len(rows),
                   frame_eligibility_reasons=dict(frame_reasons),
                   reason_count_scope='Frame reasons are multilabel; tracks/frames are correlated and are not independent trials',
                   rows=rows, nearest_targets=nearest)
    out.mkdir(parents=True)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    lines = ['# Complete seed and refusal table', '',
             f"Tracks: {len(rows)}. Nominations: {summary['nominations']}. All input tracks retained.", '',
             'Counts describe this failed-rule scan, not photographic quality or calibrated confidence.', '',
             'Decision reasons: ' + ', '.join(f'{name}={count}' for name, count in decision_reasons.most_common()) + '.', '',
             f"Frame/track records: {summary['frame_track_records']}; reason counts are multilabel.",
             'Frame eligibility reasons: ' + ', '.join(f'{name}={count}' for name, count in frame_reasons.most_common()) + '.', '',
             '| Track | Field | Seed x,y | Status | Decision reason | Eligible frames | Frame reasons (counts) |',
             '| ---: | --- | --- | --- | --- | ---: | --- |']
    for row in rows:
        reasons = ', '.join(f'{k}:{v}' for k, v in sorted(row['frame_reasons'].items()))
        lines.append(f"|{row['track']}|{row['region']}|{row['seed_xy']}|{row['status']}|{row['reason']}|{row['eligible_frames']}|{reasons}|")
    lines += ['', '## Nearest seeds at fixed evaluation points', '',
              'Geometric proximity only. Bounding rectangles do not establish connected-component membership.', '',
              '| Point | Point x,y | Track | Seed x,y | Distance, native px | Reason | Eligible frames |',
              '| --- | --- | ---: | --- | ---: | --- | ---: |']
    for item in nearest:
        for row in item['nearest']:
            lines.append(f"|{item['name']}|{item['native_xy']}|{row['track']}|{row['seed_xy']}|{row['seed_distance_native']:.3f}|{row['reason']}|{row['eligible_frames']}|")
    (out / 'all-seeds.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({key: summary[key] for key in ('tracks', 'nominations', 'regions', 'decision_reasons',
                                                   'frame_track_records', 'frame_eligibility_reasons')}))


if __name__ == '__main__':
    main()
