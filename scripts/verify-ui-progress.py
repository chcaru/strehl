"""Check the desktop observer on the actual pyramid TIFF path (no quality score)."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def alignment_events(events, frame_count):
    """Reject missing/fictional work without copying a producer calculation."""
    parsed = []
    for line in events:
        fields = line.split()[1:]
        pairs = [field.split('=', 1) for field in fields]
        assert all(len(pair) == 2 for pair in pairs), line
        item = dict(pairs)
        assert len(item) == len(pairs), f'Duplicate event fields: {line}'
        if item.get('event', '').startswith('align-'):
            assert int(item['frames']) == frame_count
            parsed.append(item)
    phases = [item['name'] for item in parsed if item['event'] == 'align-phase']
    for phase in ['planes', 'pyramids', 'pairs', 'cycle-check', 'solve', 'validate']:
        assert phase in phases, f'Fresh alignment did not expose {phase}: {phases}'
    pair_phase, = [item for item in parsed
                   if item['event'] == 'align-phase' and item['name'] == 'pairs']
    planned = int(pair_phase['total'])
    assert planned > 0
    for event in ['align-plane', 'align-pyramid']:
        finished = [item for item in parsed if item['event'] == event]
        assert {int(item['index']) for item in finished} == set(range(frame_count)), event
        assert int(finished[-1]['completed']) == frame_count, event
    comparisons = [item for item in parsed if item['event'] == 'align-pair']
    starts = [item for item in parsed if item['event'] == 'align-pair-start']
    assert comparisons and starts, 'No real pair-fit work reached the observer'
    for item in starts + comparisons:
        assert int(item['total']) == planned, f'Pair event changed the planned population: {item}'
        assert 0 <= int(item['i']) < int(item['j']) < frame_count
    started_pairs = [(int(item['i']), int(item['j'])) for item in starts]
    finished_pairs = [(int(item['i']), int(item['j'])) for item in comparisons]
    assert len(set(started_pairs)) == len(started_pairs), 'A comparison started twice'
    assert len(set(finished_pairs)) == len(finished_pairs), 'A comparison finished twice'
    if planned <= 512:
        # The producer emits every operation in this range. An aggregate-only
        # check would let a missing refusal change the apparent population.
        assert len(starts) == len(comparisons) == planned
        assert set(started_pairs) == set(finished_pairs)
        assert [int(item['started']) for item in starts] == list(range(1, planned + 1))
        assert [int(item['completed']) for item in comparisons] == list(range(1, planned + 1))
    if frame_count == 3:
        assert planned == 3
        assert set(started_pairs) == set(finished_pairs) == {(0, 1), (0, 2), (1, 2)}
    done, accepted = 0, 0
    for item in comparisons:
        current, current_accepted, total = (int(item[key]) for key in ['completed', 'accepted', 'total'])
        assert 0 <= int(item['i']) < int(item['j']) < frame_count
        assert done < current <= total and accepted <= current_accepted <= current
        assert current_accepted - accepted <= current - done
        done, accepted = current, current_accepted
    assert done == planned, 'Pair progress ended before all attempts completed'
    result, = [item for item in parsed if item['event'] == 'align-result']
    assert result['source'] == 'solved', 'This check must exercise fresh alignment, not cache reuse'
    assert int(result['placed']) + int(result['refused']) == frame_count
    assert 0 <= int(result['reference']) < frame_count
    return dict(plane_events=frame_count, pyramid_events=frame_count,
                comparisons=done, accepted_fits=accepted, source=result['source'], phases=phases)


def commission_alignment_verifier():
    """A dropped rejected comparison must fail, even with edited final totals."""
    events = []
    def emit(fields):
        events.append('STREHL_UI_PROGRESS ' + fields + ' frames=3')
    emit('event=align-phase name=planes total=3')
    for index in range(3):
        emit(f'event=align-plane index={index} completed={index + 1} total=3')
    emit('event=align-phase name=pyramids total=3')
    for index in range(3):
        emit(f'event=align-pyramid index={index} completed={index + 1} total=3')
    emit('event=align-phase name=pairs total=3')
    for completed, (i, j, accepted) in enumerate([(0, 1, 1), (0, 2, 1), (1, 2, 2)], 1):
        emit(f'event=align-pair-start i={i} j={j} started={completed} total=3')
        emit(f'event=align-pair i={i} j={j} completed={completed} accepted={accepted} total=3')
    for phase in ['cycle-check', 'solve', 'validate']:
        emit(f'event=align-phase name={phase} total=3')
    emit('event=align-result source=solved reference=1 placed=3 refused=0 total=3')
    valid = alignment_events(events, 3)
    assert valid['comparisons'] == 3 and valid['accepted_fits'] == 2
    missing_refusal = [line for line in events if 'event=align-pair i=0 j=2 ' not in line]
    changed_population = [line.replace('total=3', 'total=2').replace('completed=3', 'completed=2')
                          if 'event=align-pair ' in line else line for line in missing_refusal]
    for label, sabotage in [('missing-refusal', missing_refusal), ('edited-finish-population', changed_population)]:
        try:
            alignment_events(sabotage, 3)
        except AssertionError:
            continue
        raise AssertionError(f'The alignment verifier accepted its {label} negative control')
    return dict(valid_mixed_result=True, missing_refusal_rejected=True, edited_population_rejected=True)


def merge_events(events, frame_count, levels=8, chunk_frames=None, require_intrachunk=False):
    """Observe the consumer's required populations, not a producer-only count."""
    parsed = []
    for line in events:
        pairs = [word.split('=', 1) for word in line.split()[1:]]
        assert all(len(pair) == 2 for pair in pairs)
        item = dict(pairs)
        assert len(item) == len(pairs), 'Duplicate telemetry field'
        if item.get('event') in {'merge-step', 'band-work', 'diagnostic', 'render-step', 'frame-finished'}:
            assert int(item['total']) == frame_count
            parsed.append(item)
    steps = [item for item in parsed if item['event'] == 'merge-step']
    for index in range(frame_count):
        own = [item for item in steps if int(item['index']) == index]
        for name in ['decode', 'extract', 'pyramid']:
            assert any(item['name'] == name and item['state'] == 'finished' for item in own), (index, name)
        assert any(item['name'] == 'gather' and item['state'] in {'finished', 'skipped'} for item in own)
        assert {int(item['level']) for item in own if item['name'] == 'focus' and item['state'] == 'started'} == set(range(levels - 1))
        assert {int(item['level']) for item in own if item['name'] == 'fold' and item['state'] == 'finished'} == set(range(levels))
    work = [item for item in parsed if item['event'] == 'band-work']
    assert {int(item['level']) for item in work} == set(range(levels)), 'An entire band is missing'
    for level in range(levels):
        own = [item for item in work if int(item['level']) == level]
        assert [int(item['completed']) for item in own] == list(range(1, frame_count + 1))
        assert {int(item['index']) for item in own} == set(range(frame_count))
    maps = [item for item in parsed if item['event'] == 'diagnostic']
    assert maps, 'No actual diagnostic buffers were observed'
    previous = 0
    expected = {'focus-energy': ('frame', 'log'), 'gate-floor': ('frame', 'log'),
                'gate-support': ('frame', 'linear'), 'averaging': ('stack', 'linear'),
                'coefficient': ('stack', 'symmetric'), 'preview': ('stack', 'linear'),
                'reconstructed': ('stack', 'linear')}
    for item in maps:
        sequence = int(item['seq'])
        assert sequence > previous
        previous = sequence
        assert 0 <= int(item['frame']) < frame_count
        assert 0 <= int(item['level']) < levels
        kind = item['kind']
        width, height = int(item['width']), int(item['height'])
        max_width, max_height = (512, 384) if kind == 'preview' else (128, 96)
        assert 1 <= width <= max_width and 1 <= height <= max_height
        assert item['sampling'] == 'nearest'
        low, high = float(item['min']), float(item['max'])
        assert math.isfinite(low) and math.isfinite(high) and low <= high
        assert (item['scope'], item['scale']) == expected[kind]
        if kind in {'focus-energy', 'gate-floor', 'gate-support', 'averaging'}:
            assert low >= 0
        if kind in {'gate-support', 'averaging'}:
            assert (low, high) == (0, 1)
        assert 1 <= int(item['folded']) <= frame_count
        if item['scope'] == 'frame':
            assert int(item['folded']) == 1
        payload = item['data']
        assert len(payload) == width * height * 2
        assert all(c in '0123456789abcdef' for c in payload)
        assert len(bytes.fromhex(payload)) == width * height
        if kind in {'gate-support', 'averaging'}:
            assert set(bytes.fromhex(payload)) <= {0, 255}, 'Nonbinary mask would be rejected by the UI consumer'
    for frame in range(frame_count):
        for kind in ['focus-energy', 'gate-floor', 'gate-support']:
            wanted = set(range(levels if kind == 'gate-support' else levels - 1))
            assert {int(item['level']) for item in maps if item['kind'] == kind and int(item['frame']) == frame} == wanted
    assert any(item['kind'] == 'reconstructed' and int(item['folded']) == frame_count for item in maps)
    preview = preview_events(parsed, frame_count, chunk_frames, require_intrachunk, levels=levels)
    base = [item for item in maps if item['kind'] == 'gate-support' and int(item['level']) == levels - 1]
    assert base and all(set(item['data']) <= {'0'} for item in base), 'The configured plain-mean base cannot claim selected support'
    render = [item for item in parsed if item['event'] == 'render-step']
    assert [(item['name'], item['state']) for item in render] == [
        (name, state) for name in ['reconstruct', 'develop', 'write'] for state in ['started', 'finished']]
    return dict(step_events=len(steps), band_work_events=len(work), levels=levels,
                diagnostic_maps=len(maps), diagnostic_bytes=sum(len(item['data']) // 2 for item in maps),
                kinds=sorted({item['kind'] for item in maps}), render_steps=len(render),
                preview=preview)


def preview_events(parsed, frame_count, chunk_frames=None, require_intrachunk=False, levels=None):
    """Check every accepted generation against separately emitted input counts.

    Every accepted input must expose all accumulated scales and a preview.
    Refusals advance processing, never the accepted population. Changed pixels
    are a liveness witness on a deliberately changing input, never a sharpness
    or quality score: noise can change pixels too. This verifier targets the
    CLI's serial canonical fold path, whose completed input identities are exact.
    """
    accepted = None
    accepted_steps = []
    processed = 0
    last_frame = None
    previews = []
    reconstructed = []
    shape = None
    current_was_accepted = False
    accumulated = {}
    for item in parsed:
        if item['event'] == 'frame-finished':
            current = int(item['processed'])
            current_accepted = int(item['accepted'])
            assert current == processed + 1 and current <= frame_count, "A completed input event was skipped or repeated"
            assert (accepted or 0) <= current_accepted <= current
            assert current_accepted - (accepted or 0) <= current - processed
            current_was_accepted = current_accepted > (accepted or 0)
            if current_was_accepted:
                accepted_steps.append(current_accepted)
            processed, accepted = current, current_accepted
            last_frame = int(item['index'])
            assert last_frame == processed - 1, "Completed input identity is repeated or out of canonical order"
        elif item['event'] == 'diagnostic':
            kind = item['kind']
            if levels is not None and kind in {'averaging', 'coefficient'}:
                folded, level = int(item['folded']), int(item['level'])
                assert current_was_accepted and folded == accepted, 'Accumulated map does not describe the current accepted generation'
                assert int(item['frame']) == last_frame, 'Accumulated map is disconnected from the accepted input'
                assert 0 <= level < levels
                key = (folded, kind, level)
                assert key not in accumulated, 'Accumulated map generation was replayed'
                accumulated[key] = last_frame
            if kind == 'preview':
                folded = int(item['folded'])
                assert 1 <= folded <= frame_count
                assert current_was_accepted and folded == accepted, 'Preview count disagrees with accepted inputs'
                assert int(item['frame']) == last_frame, 'Preview frame is disconnected from the actual input event'
                assert not previews or folded > previews[-1]['folded'], 'Preview folded count did not advance'
                geometry = (int(item['level']), int(item['width']), int(item['height']))
                assert shape is None or shape == geometry, 'Preview geometry changed during accumulation'
                shape = geometry
                previews.append(dict(frame=last_frame, folded=folded,
                                     pixel_sha256=hashlib.sha256(bytes.fromhex(item['data'])).hexdigest()))
            elif kind == 'reconstructed':
                reconstructed.append(int(item['folded']))
    assert previews, 'No accumulated coarse preview was observed'
    assert processed == frame_count, 'Input events stopped before the final frame'
    assert len(previews) <= frame_count, 'Preview invented an accepted input'
    folds = [item['folded'] for item in previews]
    assert folds[0] == 1, 'First accepted image waited for a later chunk boundary'
    assert folds == accepted_steps, 'An accepted input has no preview generation'
    if levels is not None:
        expected = {(folded, kind, level) for folded in accepted_steps
                    for kind in ['averaging', 'coefficient'] for level in range(levels)}
        assert set(accumulated) == expected, 'An accepted input has missing accumulated scales'
    assert reconstructed and folds[-1] == reconstructed[-1] == accepted, 'Final preview does not cover the reconstructed stack'
    changes = []
    if chunk_frames is not None:
        assert chunk_frames > 0
        for before, after in zip(previews, previews[1:]):
            if (before['frame'] // chunk_frames == after['frame'] // chunk_frames
                    and before['pixel_sha256'] != after['pixel_sha256']):
                changes.append(dict(chunk=before['frame'] // chunk_frames,
                                    before_frame=before['frame'], after_frame=after['frame'],
                                    before_folded=before['folded'], after_folded=after['folded']))
    if require_intrachunk:
        assert changes, 'No changing preview pixels were witnessed within one canonical chunk'
    return dict(observations=len(previews), folded_counts=folds, samples=previews,
                distinct_pixel_payloads=len({item['pixel_sha256'] for item in previews}),
                canonical_chunk_frames=chunk_frames, intra_chunk_changed_pairs=changes,
                finest_retained_level=shape[0], width=shape[1], height=shape[2],
                scope='stack', scale='linear', cadence='every accepted input, all accumulated scales',
                accumulated_scale_maps=len(accumulated),
                product='coarse green reconstruction before hull bounds and colour development')


def commission_merge_verifier():
    events = []
    emit = lambda fields: events.append('STREHL_UI_PROGRESS ' + fields + ' total=3')
    sequence = 0
    def surface(frame, level, kind, scope, scale, folded):
        nonlocal sequence
        sequence += 1
        low, high, data = (-1, 2, '00ff') if kind in {'preview', 'reconstructed'} else (0, 1, '00ff')
        if kind == 'preview':
            data = ['00ff', '20bf', '408f'][frame]
        if kind == 'gate-support' and level == 1:
            data = '0000'
        emit(f'event=diagnostic seq={sequence} frame={frame} level={level} kind={kind} scope={scope} scale={scale} width=2 height=1 min={low} max={high} folded={folded} sampling=nearest data={data}')
    for frame in range(3):
        for name in ['decode', 'gather', 'extract', 'pyramid']:
            emit(f'event=merge-step index={frame} name={name} state=finished level=none')
        emit(f'event=merge-step index={frame} name=focus state=started level=0')
        for level in range(2):
            emit(f'event=merge-step index={frame} name=fold state=finished level={level}')
            emit(f'event=band-work index={frame} level={level} completed={frame + 1}')
        surface(frame, 0, 'focus-energy', 'frame', 'log', 1)
        surface(frame, 0, 'gate-floor', 'frame', 'log', 1)
        for level in range(2):
            surface(frame, level, 'gate-support', 'frame', 'linear', 1)
        emit(f'event=frame-finished index={frame} processed={frame + 1} accepted={frame + 1}')
        for level in range(2):
            surface(frame, level, 'averaging', 'stack', 'linear', frame + 1)
            surface(frame, level, 'coefficient', 'stack', 'symmetric', frame + 1)
        surface(frame, 0, 'preview', 'stack', 'linear', frame + 1)
    surface(2, 0, 'reconstructed', 'stack', 'linear', 3)
    for name in ['reconstruct', 'develop', 'write']:
        for state in ['started', 'finished']:
            emit(f'event=render-step name={name} state={state}')
    valid = merge_events(events, 3, 2, chunk_frames=3, require_intrachunk=True)
    assert valid['preview']['folded_counts'] == [1, 2, 3]
    assert len(valid['preview']['intra_chunk_changed_pairs']) == 2
    assert valid['preview']['distinct_pixel_payloads'] == 3
    first_preview = next(i for i, line in enumerate(events) if 'kind=preview ' in line)
    first_map = next(i for i, line in enumerate(events) if 'kind=coefficient ' in line)
    assert first_map < first_preview
    static = [re.sub(r'data=[0-9a-f]+', 'data=00ff', line)
              if 'kind=preview ' in line else line for line in events]
    # A flat input is a valid observer stream, but cannot establish visibly
    # advancing image content. Keep validity separate from the liveness proof.
    assert merge_events(static, 3, 2)['preview']['distinct_pixel_payloads'] == 1
    # A preview is allowed to be larger than the diagnostic maps, up to its
    # distinct bound. Positive boundary control prevents a 64×48-only checker
    # from passing merely because every sabotage was also small.
    def resized_preview(line, width, height):
        if 'kind=preview ' not in line:
            return line
        pattern = re.search(r'data=([0-9a-f]+)', line).group(1)
        data = (pattern * (width * height))[:width * height * 2]
        line = re.sub(r'width=\d+ height=\d+', f'width={width} height={height}', line)
        return re.sub(r'data=[0-9a-f]+', 'data=' + data, line)
    boundary = [resized_preview(line, 512, 384) for line in events]
    assert merge_events(boundary, 3, 2)['preview']['width'] == 512
    # Repeat a fully valid final preview with a fresh sequence. Its input and
    # acceptance counts still agree: only the nonadvancing-preview guard can
    # reject this. Merely editing folded=3 to folded=1 would be caught by the
    # independent accepted-count check and would not test that guard's power.
    last_preview = max(index for index, line in enumerate(events) if 'kind=preview ' in line)
    repeated = events[:last_preview + 1] + [events[last_preview]] + events[last_preview + 1:]
    sequence = 0
    for index, line in enumerate(repeated):
        if 'event=diagnostic ' in line:
            sequence += 1
            repeated[index] = ' '.join(f'seq={sequence}' if word.startswith('seq=') else word
                                       for word in line.split())
    sabotages = {
        'missing-early-accumulated-scale': [line for line in events if not ('kind=coefficient ' in line and 'folded=1 ' in line and 'level=1 ' in line)],
        'missing-early-averaging-generation': [line for line in events if not ('kind=averaging ' in line and 'folded=2 ' in line)],
        'nonbinary-frame-support': [line.replace('data=00ff', 'data=0080') if 'kind=gate-support ' in line else line for line in events],
        'nonbinary-stack-fallback': [line.replace('data=00ff', 'data=0080') if 'kind=averaging ' in line else line for line in events],
        'missing-maps': [line for line in events if 'event=diagnostic ' not in line],
        'missing-band': [line for line in events if not ('event=band-work ' in line and 'level=1 ' in line)],
        'nonfinite-map': [line.replace('min=0 ', 'min=NaN ') if 'event=diagnostic ' in line else line for line in events],
        'truncated-map': [line.replace('data=00ff', 'data=00') if 'event=diagnostic ' in line else line for line in events],
        'missing-writer-finish': [line for line in events if 'name=write state=finished' not in line],
        'missing-preview': [line for line in events if 'kind=preview ' not in line],
        'preview-nonadvancing-folds': repeated,
        'preview-delayed-first-state': [line for line in events if not ('kind=preview ' in line and 'folded=1 ' in line)],
        'preview-skipped-small-state': [line for line in events if not ('kind=preview ' in line and 'folded=2 ' in line)],
        'preview-folded-count-mismatch': [line.replace('folded=3 ', 'folded=1 ') if 'kind=preview ' in line else line for line in events],
        'preview-ahead-of-inputs': [line.replace('folded=1 ', 'folded=2 ') if 'kind=preview ' in line else line for line in events],
        'preview-oversize-width': [resized_preview(line, 513, 384) for line in events],
        'preview-oversize-height': [resized_preview(line, 512, 385) for line in events],
        'preview-truncated': [line.replace('data=00ff', 'data=00') if 'kind=preview ' in line else line for line in events],
        'preview-wrong-scope': [line.replace('scope=stack', 'scope=frame') if 'kind=preview ' in line else line for line in events],
        'preview-wrong-scale': [line.replace('scale=linear', 'scale=log') if 'kind=preview ' in line else line for line in events],
    }
    for label, sabotage in sabotages.items():
        try:
            merge_events(sabotage, 3, 2)
        except (AssertionError, ValueError, KeyError):
            pass
        else:
            raise AssertionError(f'Merge verifier accepted {label}')
    liveness_sabotages = {
        'static-preview-content': (static, 3),
        'only-between-chunk-changes': (events, 1),
    }
    for label, (sabotage, chunk_frames) in liveness_sabotages.items():
        try:
            merge_events(sabotage, 3, 2, chunk_frames, require_intrachunk=True)
        except AssertionError as failure:
            assert 'within one canonical chunk' in str(failure), (label, failure)
        else:
            raise AssertionError(f'Intra-chunk witness accepted {label}')

    def cadence_fixture(total, refused=(), levels=5, static=False):
        # Independently choose irregular admission and counts beyond all three
        # retired caps (32 source frames, 16 chunks, 96 preview observations).
        parsed = []
        accepted = 0
        for frame in range(total):
            accepted += frame not in refused
            parsed.append(dict(event='frame-finished', index=frame, processed=frame + 1, accepted=accepted))
            if frame in refused:
                continue
            for level in range(levels):
                for kind in ['averaging', 'coefficient']:
                    parsed.append(dict(event='diagnostic', kind=kind, frame=frame,
                                       level=level, folded=accepted))
            data = '00ff' if static else f'{frame % 256:02x}{(255 - frame) % 256:02x}'
            parsed.append(dict(event='diagnostic', kind='preview', frame=frame,
                               level=1, width=2, height=1, folded=accepted, data=data))
        parsed.append(dict(event='diagnostic', kind='reconstructed', folded=accepted))
        return parsed
    cadence_controls = {}
    # 41 changes all source identities; 67 rechooses refusal and 11-frame
    # chunks; 137 crosses the old preview cap and rechooses 23-frame chunks.
    for total, refused, chunk in [(41, (), 7), (67, {2, 17, 31, 32, 33, 34, 35, 65}, 11), (137, (), 23)]:
        fixture = cadence_fixture(total, refused)
        checked = preview_events(fixture, total, chunk, require_intrachunk=True, levels=5)
        assert checked['folded_counts'] == list(range(1, total - len(refused) + 1))
        assert checked['accumulated_scale_maps'] == (total - len(refused)) * 10
        assert checked['distinct_pixel_payloads'] == total - len(refused)
        missing_middle = [item for item in fixture if not (item.get('kind') == 'preview' and item.get('folded') == 19)]
        maps_at_boundaries = [item for item in fixture if not (item.get('kind') in {'averaging', 'coefficient'}
                               and item['frame'] % chunk != chunk - 1 and item['frame'] != total - 1)]
        missing_coarse_scale = [item for item in fixture if not (item.get('kind') == 'coefficient'
                                and item['level'] == 4 and item['folded'] == 29)]
        sparse_old_preview = [item for item in fixture if not (item.get('kind') == 'preview'
                              and item['folded'] > 1 and item['folded'] % 2)]
        repeated_identity = [dict(item, index=0) if item.get('event') == 'frame-finished' and item['index'] == 1 else item
                             for item in fixture]
        for label, broken in [('missing-middle-preview', missing_middle), ('chunk-only-maps', maps_at_boundaries),
                              ('missing-coarse-scale', missing_coarse_scale), ('old-sparse-preview', sparse_old_preview),
                              ('repeated-input-identity', repeated_identity)]:
            try:
                preview_events(broken, total, levels=5)
            except AssertionError:
                pass
            else:
                raise AssertionError(f'{total}-input verifier accepted {label}')
        cadence_controls[str(total)] = dict(accepted=total - len(refused), canonical_chunk_frames=chunk,
                                            changed_within_chunk=True, all_scales_each_input=True,
                                            rejected_missing_middle=True, rejected_chunk_only_maps=True,
                                            rejected_missing_coarse_scale=True, rejected_old_sparse_preview=True,
                                            rejected_repeated_input_identity=True)
    flat_large = preview_events(cadence_fixture(137, static=True), 137, levels=5)
    assert flat_large['observations'] == 137 and flat_large['distinct_pixel_payloads'] == 1
    return dict(valid_signed_reconstruction=True, cadence_controls=cadence_controls,
                valid_refused_inputs_do_not_invent_images=True, valid_all_scales_before_chunk_boundary=True,
                valid_flat_stream_without_liveness_claim=True, valid_flat_large_stream_without_sampling=True,
                valid_maximum_preview_dimensions=True,
                **{f'{label}_rejected': True for label in sabotages | liveness_sabotages})



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--binned', action='store_true')
    parser.add_argument('--limit', type=int, default=3, help='Real RAW frames to compare (3-256; the proof requires every input identity and accumulated scale)')
    parser.add_argument('--workers', type=int, default=1, help='Execution threads for both Rayon and pyramid pools (1–1024)')
    parser.add_argument('--require-intrachunk-preview', action='store_true', help='Require changed real preview pixels between accepted folds inside one canonical chunk')
    parser.add_argument('--commission', action='store_true', help='Exercise verifier controls without reading RAW files')
    args = parser.parse_args()
    if not 1 <= args.workers <= 1024:
        parser.error('--workers must be between 1 and 1024')
    if not 3 <= args.limit <= 256:
        parser.error('--limit must be between 3 and 256')
    validator_controls = commission_alignment_verifier()
    merge_validator_controls = commission_merge_verifier()
    if args.commission:
        print(json.dumps(dict(alignment=validator_controls, merge=merge_validator_controls), sort_keys=True))
        return
    if args.engine is None or args.source is None or args.out is None:
        parser.error('--engine, --source and --out are required unless --commission is used')
    engine, source, out = args.engine.resolve(), args.source.resolve(), args.out.resolve()
    assert engine.is_file() and source.is_dir()
    assert not out.is_relative_to(source), 'Outputs must be outside the source folder'
    out.mkdir(parents=True, exist_ok=False)
    environment = {k: v for k, v in os.environ.items()
                   if not k.upper().startswith('STREHL_') and k.upper() != 'RAYON_NUM_THREADS'}
    environment.update(RAYON_NUM_THREADS=str(args.workers), STREHL_PYRAMID_WORKERS=str(args.workers))
    controls = dict(schema=6, validator_controls=validator_controls, merge_validator_controls=merge_validator_controls,
                    engine=str(engine), engine_sha256=digest(engine),
                    source=str(source), limit=args.limit, binned=args.binned, workers=args.workers,
                    require_intrachunk_preview=args.require_intrachunk_preview, environment_overrides={k: v for k, v in environment.items()
                        if k.startswith('STREHL_') or k == 'RAYON_NUM_THREADS'}, runs=[])
    # Failure inputs: a telemetry arm that emits no frame events, an off/placebo
    # arm that emits events, a cached on-arm hiding the real alignment path,
    # missing/refusal-discarding work counts, or one differing completed byte.
    # These reject independently of the observer's internal accounting formula.
    for name, enabled in [('off', '0'), ('on', '1'), ('placebo', 'placebo')]:
        image, log = out / f'{name}.tiff', out / f'{name}.log'
        command = [str(engine), 'stack', str(source), '--limit', str(args.limit), '--merge', 'pyramid',
                   '--srgb', '--pyramid-gate', '2', '--pyramid-bands', '7',
                   '--pyramid-exponent', '2', '--pyramid-sharpen', '1.4', '--resampler', 'catmull-rom',
                   '--out', str(image)]
        if args.binned:
            command.append('--binned')
        # Each arm must actually re-fit the same bracket. A shared cache would
        # exercise fresh work only in the first (disabled) arm.
        arm_environment = dict(environment, STREHL_UI_PROGRESS=enabled,
                               STREHL_CACHE_DIR=str(out / f'cache-{name}'))
        with log.open('xb') as stream:
            result = subprocess.run(command, env=arm_environment, stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=900, check=False)
        assert result.returncode == 0, f'{name} exited {result.returncode}: {log}'
        text = log.read_text(encoding='utf-8', errors='replace')
        events = [line for line in text.splitlines() if line.startswith('STREHL_UI_PROGRESS ')]
        finished = [line for line in events if 'event=frame-finished ' in line]
        assert (len(finished) == args.limit) if name == 'on' else not events, f'Unexpected observer routing: {name}'
        alignment = alignment_events(events, args.limit) if name == 'on' else None
        merge = None
        if name == 'on':
            plan = re.search(r'memory plan\s*:\s*(\d+) canonical chunks', text)
            assert plan, 'The actual canonical partition plan was not reported'
            chunks = int(plan.group(1))
            assert 1 <= chunks <= args.limit
            chunk_frames = (args.limit + chunks - 1) // chunks
            merge = merge_events(events, args.limit, chunk_frames=chunk_frames,
                                 require_intrachunk=args.require_intrachunk_preview)
            merge['canonical_planned_chunks'] = chunks
        assert image.stat().st_size > 0
        controls['runs'].append(dict(name=name, command=command, observer=enabled,
                                    bytes=image.stat().st_size, sha256=digest(image),
                                    events=len(events), frame_events=len(finished), alignment=alignment, merge=merge,
                                    environment_overrides={k: v for k, v in arm_environment.items()
                                        if k.startswith('STREHL_') or k == 'RAYON_NUM_THREADS'}))
        print(name, controls['runs'][-1]['sha256'], flush=True)
    controls['byte_identical'] = len({run['sha256'] for run in controls['runs']}) == 1
    (out / 'verification.json').write_text(json.dumps(controls, indent=2) + '\n', encoding='utf-8')
    assert controls['byte_identical'], 'Observer perturbed the completed TIFF'
    print('VERIFIED: on/off/placebo completed TIFF bytes identical', flush=True)


if __name__ == '__main__':
    main()
