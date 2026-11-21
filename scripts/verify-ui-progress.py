"""Check the desktop observer on the actual pyramid TIFF path (no quality score)."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
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
    # The fresh solve ends at its first result. A render that aligns first
    # and then loads that solve for its fold (the lateral-CA refinement does)
    # reports a later cache result, which must repeat the solve exactly.
    results = [index for index, item in enumerate(parsed) if item['event'] == 'align-result']
    assert results, 'Alignment reported no result'
    reloads, parsed = parsed[results[0] + 1:], parsed[:results[0] + 1]
    phases = [item['name'] for item in parsed if item['event'] == 'align-phase']
    for phase in ['planes', 'pairs', 'cycle-check', 'solve', 'validate']:
        assert phase in phases, f'Fresh alignment did not expose {phase}: {phases}'
    pair_phase, = [item for item in parsed
                   if item['event'] == 'align-phase' and item['name'] == 'pairs']
    planned = int(pair_phase['total'])
    assert planned > 0
    # The streaming solve builds each plane's pyramid with its plane, so a
    # separate pyramid phase and its per-frame events appear only when the
    # whole-stack reference builds pyramids on their own; then all must.
    streamed = 'pyramids' not in phases
    for event in ['align-plane'] + ([] if streamed else ['align-pyramid']):
        finished = [item for item in parsed if item['event'] == event]
        assert {int(item['index']) for item in finished} == set(range(frame_count)), event
        assert int(finished[-1]['completed']) == frame_count, event
    if streamed:
        assert not any(item['event'] == 'align-pyramid' for item in parsed), "Pyramid events without their phase"
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
    result = parsed[-1]
    assert result['source'] == 'solved', 'This check must exercise fresh alignment, not cache reuse'
    assert int(result['placed']) + int(result['refused']) == frame_count
    assert 0 <= int(result['reference']) < frame_count
    for item in reloads:
        assert item['event'] in {'align-phase', 'align-result'}, f'Work after the solve: {item}'
        if item['event'] == 'align-phase':
            assert item['name'] == 'cache', f'A reload is a cache read, not {item}'
        else:
            assert item['source'] == 'cache' and all(item[key] == result[key] for key in
                                                     ['reference', 'placed', 'refused']), (
                f'A reload must repeat the solve: {item}')
    return dict(plane_events=frame_count, pyramid_events=0 if streamed else frame_count,
                streamed=streamed, comparisons=done, accepted_fits=accepted, source=result['source'],
                reloads=sum(item['event'] == 'align-result' for item in reloads), phases=phases)


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
    streaming = [line for line in events
                 if 'name=pyramids' not in line and 'event=align-pyramid ' not in line]
    reload = ['STREHL_UI_PROGRESS event=align-phase name=cache total=3 frames=3',
              'STREHL_UI_PROGRESS event=align-result source=cache reference=1 placed=3 refused=0 total=3 frames=3']
    streamed = alignment_events(streaming + reload, 3)
    assert streamed['streamed'] and streamed['reloads'] == 1
    for label, broken in [
            ('changed-reload', streaming + [reload[0], reload[1].replace('reference=1', 'reference=2')]),
            ('missing-streamed-plane', [line for line in streaming if 'event=align-plane index=2 ' not in line]),
            ('orphan-pyramid', streaming[:3] + ['STREHL_UI_PROGRESS event=align-pyramid index=0 completed=1 total=3 frames=3']
             + streaming[3:]),
            ('work-after-solve', streaming + ['STREHL_UI_PROGRESS event=align-pair i=0 j=1 completed=4 accepted=3 total=3 frames=3'])]:
        try:
            alignment_events(broken, 3)
        except (AssertionError, KeyError, ValueError):
            continue
        raise AssertionError(f'The alignment verifier accepted {label}')
    missing_refusal = [line for line in events if 'event=align-pair i=0 j=2 ' not in line]
    changed_population = [line.replace('total=3', 'total=2').replace('completed=3', 'completed=2')
                          if 'event=align-pair ' in line else line for line in missing_refusal]
    for label, sabotage in [('missing-refusal', missing_refusal), ('edited-finish-population', changed_population)]:
        try:
            alignment_events(sabotage, 3)
        except AssertionError:
            continue
        raise AssertionError(f'The alignment verifier accepted its {label} negative control')
    return dict(valid_mixed_result=True, missing_refusal_rejected=True, edited_population_rejected=True,
                valid_streamed_with_reload=True, changed_reload_rejected=True, missing_streamed_plane_rejected=True,
                orphan_pyramid_rejected=True, work_after_solve_rejected=True)


def merge_events(events, frame_count, levels=8, chunk_frames=None, require_intrachunk=False, plain_base=True,
                 bounded_live=False):
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
    preview = preview_events(parsed, frame_count, chunk_frames, require_intrachunk, levels=levels,
                             bounded_live=bounded_live)
    base = [item for item in maps if item['kind'] == 'gate-support' and int(item['level']) == levels - 1]
    assert base, 'The base band reported no support'
    if plain_base:
        assert all(set(item['data']) <= {'0'} for item in base), 'The configured plain-mean base cannot claim selected support'
    render = [item for item in parsed if item['event'] == 'render-step']
    assert [(item['name'], item['state']) for item in render] == [
        (name, state) for name in ['reconstruct', 'develop', 'write'] for state in ['started', 'finished']]
    return dict(step_events=len(steps), band_work_events=len(work), levels=levels,
                diagnostic_maps=len(maps), diagnostic_bytes=sum(len(item['data']) // 2 for item in maps),
                kinds=sorted({item['kind'] for item in maps}), render_steps=len(render),
                preview=preview)


def preview_events(parsed, frame_count, chunk_frames=None, require_intrachunk=False, levels=None,
                   bounded_live=False):
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
        # With the live side file, every generation keeps its averaging maps
        # but only the newest keeps its coefficient maps (and whole preview).
        expected = {(folded, kind, level) for folded in accepted_steps
                    for kind in ['averaging', 'coefficient'] for level in range(levels)
                    if not (bounded_live and kind == 'coefficient' and folded != accepted_steps[-1])}
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


EVIDENCE_KINDS = {0: ('gate-support', 'linear'), 1: ('averaging', 'linear'), 2: ('focus-energy', 'log'),
                  3: ('gate-floor', 'log'), 6: ('preview', 'linear')}


def diagnostic_line(sequence, frame, level, kind, scope, scale, width, height, low, high, folded, total, pixels):
    return (f'STREHL_UI_PROGRESS event=diagnostic seq={sequence} frame={frame} level={level} kind={kind} '
            f'scope={scope} scale={scale} width={width} height={height} min={low} max={high} '
            f'folded={folded} total={total} sampling=nearest data={pixels.hex()}')


def revision_lattice(width, height):
    """The desktop's revision lattice (process-revision.rs compare), written
    here from its definition: at most 64 x 48, nearest sites."""
    scale = min(64 / width, 48 / height, 1.0)
    w, h = max(1, math.floor(width * scale)), max(1, math.floor(height * scale))
    sites = [min((2 * y + 1) * height // (2 * h), height - 1) * width
             + min((2 * x + 1) * width // (2 * w), width - 1) for y in range(h) for x in range(w)]
    return (w, h), sites


def evidence_events(data):
    """The engine's evidence file (crates/strehl-cli/src/ui-evidence.rs) read
    back as the hex diagnostic lines it replaces, from an independent decoder.
    Returns (sequence, frame, scope, line) tuples; any malformed byte fails.
    A preview's revision sample (kind 6) stands for its preview: the bytes
    the full preview has at the revision lattice."""
    assert data[:8] == b'STRHEVD1', 'not an evidence file'
    version, levels = struct.unpack_from('<II', data, 8)
    assert version == 1 and 1 <= levels <= 64
    lattices = [struct.unpack_from('<HHII', data, 16 + 12 * k)[:2] for k in range(levels)]
    at = 16 + 12 * levels
    (total,) = struct.unpack_from('<I', data, at)
    at += 4
    out = []
    while at < len(data):
        assert len(data) - at >= 16, 'torn record header'
        frame, level, kind, reserved, sequence, length = struct.unpack_from('<IBBHII', data, at)
        payload = data[at + 16:at + 16 + length]
        assert len(payload) == length and reserved == 0 and kind in EVIDENCE_KINDS
        at += 16 + length
        width, height = lattices[level]
        name, scale = EVIDENCE_KINDS[kind]
        scope, folded = 'frame', 1
        if kind in (0, 1):
            if kind == 1:
                (folded,), payload, scope = struct.unpack_from('<I', payload, 0), payload[4:], 'stack'
            assert len(payload) == (width * height + 7) // 8
            pixels = bytes(255 * ((payload[i // 8] >> (i % 8)) & 1) for i in range(width * height))
            assert not any(payload[i // 8] >> (i % 8) & 1 for i in range(width * height, 8 * len(payload)))
            low, high = '0e0', '1e0'
        elif kind == 6:
            folded, pw, ph, width, height, low, high = struct.unpack_from('<IHHHHff', payload, 0)
            assert (width, height) == revision_lattice(pw, ph)[0] and len(payload) == 20 + width * height
            low, high, pixels, scope = repr(low), repr(high), payload[20:], 'stack'
        else:
            assert length == 8 + width * height
            low, high = (repr(v) for v in struct.unpack_from('<ff', payload, 0))
            pixels = payload[8:]
        out.append((sequence, frame, scope, diagnostic_line(
            sequence, frame, level, name, scope, scale, width, height, low, high, folded, total, pixels)))
    return out


def live_events(data):
    """The live side file (the newest generation's coefficient maps and coarse
    preview): coefficient lines for the stream, and the preview kept apart.
    Returns (records, preview) with preview = (sequence, frame, folded, width,
    height, min, max, bytes)."""
    assert data[:8] == b'STRHLIV1', 'not a live file'
    version, total, count = struct.unpack_from('<III', data, 8)
    assert version == 1 and total > 0
    at, records, previews = 20, [], []
    while at < len(data):
        frame, level, kind, reserved, sequence, length = struct.unpack_from('<IBBHII', data, at)
        payload = data[at + 16:at + 16 + length]
        assert len(payload) == length >= 16 and reserved == 0 and kind in (4, 5)
        at += 16 + length
        folded, width, height, low, high = struct.unpack_from('<IHHff', payload, 0)
        pixels = payload[16:]
        assert len(pixels) == width * height and 0 < folded <= total
        if kind == 4:
            records.append((sequence, frame, 'stack', diagnostic_line(
                sequence, frame, level, 'coefficient', 'stack', 'symmetric', width, height,
                repr(low), repr(high), folded, total, pixels)))
        else:
            previews.append((sequence, frame, folded, width, height, low, high, pixels))
    assert len(records) + len(previews) == count and len(previews) == 1, 'one whole live generation'
    return records, previews[0]


def with_evidence(events, evidence):
    """Place the files' maps where the engine emitted them: a plane's maps just
    before its frame-finished event, the stack maps of the generation it
    completed just after; maps with no such event at the end. Within a place
    and against the log's own maps, the shared sequence orders them."""
    before, after, rest = {}, {}, []
    for sequence, frame, scope, line in evidence:
        (before if scope == 'frame' else after).setdefault(frame, []).append((sequence, line))
    merged = []
    for line in events:
        if line.startswith('STREHL_UI_PROGRESS event=frame-finished '):
            index = int(line.split(' index=', 1)[1].split()[0])
            merged.extend(line for _, line in sorted(before.pop(index, [])))
            merged.append(line)
            merged.extend(line for _, line in sorted(after.pop(index, [])))
        else:
            merged.append(line)
    # A map with no frame event of its own cannot be placed; appended, it
    # breaks the sequence order and fails the merge checks, as it should.
    for group in list(before.values()) + list(after.values()):
        rest.extend(group)
    merged.extend(line for _, line in sorted(rest))
    return merged


def commission_evidence_reader():
    """Maps moved to the files must verify exactly as their hex lines did, in
    the engine's order, and a missing or malformed map must fail."""
    header = b'STRHEVD1' + struct.pack('<II', 1, 2) + struct.pack('<HHII', 2, 1, 4, 2) \
        + struct.pack('<HHII', 1, 1, 2, 1) + struct.pack('<I', 3)
    def record(frame, level, kind, sequence, payload):
        return struct.pack('<IBBHII', frame, level, kind, 0, sequence, len(payload)) + payload
    preview = bytes(range(0, 200, 2)) * 3  # 10 x 30
    (sw, sh), sites = revision_lattice(30, 10)
    sample = struct.pack('<IHHHHff', 1, 30, 10, sw, sh, 0.5, 9.0) + bytes(preview[i] for i in sites)
    data = (header + record(1, 0, 0, 4, bytes([0b10])) + record(1, 0, 2, 5, struct.pack('<ff', 0.5, 2.0) + bytes([0, 255]))
            + record(1, 0, 1, 6, struct.pack('<I', 1) + bytes([0b01])) + record(1, 1, 6, 8, sample))
    parsed = evidence_events(data)
    lines = [line for _, _, _, line in parsed]
    assert 'kind=gate-support' in lines[0] and lines[0].endswith('data=00ff') and 'seq=4 ' in lines[0]
    assert 'kind=focus-energy' in lines[1] and 'min=0.5 max=2.0' in lines[1] and lines[1].endswith('data=00ff')
    assert 'kind=averaging scope=stack' in lines[2] and 'folded=1 ' in lines[2] and lines[2].endswith('data=ff00')
    assert f'kind=preview scope=stack scale=linear width={sw} height={sh} ' in lines[3]
    live = b'STRHLIV1' + struct.pack('<III', 1, 3, 2) + record(1, 0, 4, 7, struct.pack('<IHHff', 1, 2, 1, -1.0, 1.0) + bytes([0, 255])) \
        + record(1, 1, 5, 8, struct.pack('<IHHff', 1, 30, 10, 0.5, 9.0) + preview)
    coefficients, final = live_events(live)
    assert final[:3] == (8, 1, 1) and final[7] == preview
    log = ['STREHL_UI_PROGRESS event=frame-finished index=0 processed=1 accepted=0',
           'STREHL_UI_PROGRESS event=frame-finished index=1 processed=2 accepted=1',
           'STREHL_UI_PROGRESS event=diagnostic seq=9 frame=1 kind=reconstructed']
    merged = with_evidence(log, parsed + coefficients)
    order = [line.split(' seq=')[1].split()[0] if 'seq=' in line else line.split('index=')[1][0] for line in merged]
    assert order == ['0', '4', '5', '1', '6', '7', '8', '9'], order
    broken_records = [('torn', data[:-1]), ('magic', b'X' + data[1:]),
                      ('kind', data[:-len(sample) - 11] + b'\x09' + data[-len(sample) - 10:]),
                      ('sample-lattice', data[:-len(sample) + 8] + struct.pack('<H', sw + 1) + data[-len(sample) + 10:])]
    for label, broken in broken_records:
        try:
            evidence_events(broken)
        except (AssertionError, struct.error, IndexError, KeyError):
            continue
        raise AssertionError(f'Evidence reader accepted a {label} file')
    try:
        live_events(live[:16] + struct.pack('<I', 3) + live[20:])
    except AssertionError:
        pass
    else:
        raise AssertionError('Live reader accepted a miscounted file')
    return dict(round_trip=True, placed_by_frame_events=True, malformed_rejected=True, live_read=True)


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
    # The live side file keeps only the newest generation's coefficient maps:
    # valid under that contract alone, and every averaging generation and the
    # final coefficient maps are still required.
    bounded = [line for line in events if not ('kind=coefficient ' in line and 'folded=3 ' not in line)]
    assert merge_events(bounded, 3, 2, bounded_live=True)['preview']['accumulated_scale_maps'] == 8
    for label, sabotage, contract in [
            ('bounded-under-full-contract', bounded, False),
            ('bounded-missing-final-coefficient', [line for line in bounded if 'kind=coefficient ' not in line], True),
            ('bounded-missing-averaging-generation',
             [line for line in bounded if not ('kind=averaging ' in line and 'folded=2 ' in line)], True)]:
        try:
            merge_events(sabotage, 3, 2, bounded_live=contract)
        except (AssertionError, ValueError, KeyError):
            continue
        raise AssertionError(f'Merge verifier accepted {label}')
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
    parser.add_argument('--merge-only', action='store_true',
                        help='Skip the alignment-event checks (the merge and bytes are still checked)')
    args = parser.parse_args()
    if not 1 <= args.workers <= 1024:
        parser.error('--workers must be between 1 and 1024')
    if not 3 <= args.limit <= 256:
        parser.error('--limit must be between 3 and 256')
    validator_controls = commission_alignment_verifier()
    merge_validator_controls = commission_merge_verifier()
    evidence_controls = commission_evidence_reader()
    if args.commission:
        print(json.dumps(dict(alignment=validator_controls, merge=merge_validator_controls,
                              evidence=evidence_controls), sort_keys=True))
        return
    if args.engine is None or args.source is None or args.out is None:
        parser.error('--engine, --source and --out are required unless --commission is used')
    engine, source, out = args.engine.resolve(), args.source.resolve(), args.out.resolve()
    assert engine.is_file() and source.is_dir()
    assert not out.is_relative_to(source), 'Outputs must be outside the source folder'
    out.mkdir(parents=True, exist_ok=False)
    environment = {k: v for k, v in os.environ.items()
                   if not k.upper().startswith('STREHL_') and k.upper() != 'RAYON_NUM_THREADS'}
    # This verifier checks the CPU fold's per-step events (extraction, focus).
    # The GPU fold is the default where a device passes its self-test, and it
    # reports neither, so the CPU fold is named here, not inherited.
    environment.update(RAYON_NUM_THREADS=str(args.workers), STREHL_PYRAMID_WORKERS=str(args.workers),
                       STREHL_GPU_FOLD='off')
    controls = dict(schema=7, validator_controls=validator_controls, merge_validator_controls=merge_validator_controls,
                    evidence_controls=evidence_controls,
                    engine=str(engine), engine_sha256=digest(engine),
                    source=str(source), limit=args.limit, binned=args.binned, workers=args.workers,
                    require_intrachunk_preview=args.require_intrachunk_preview, merge_only=args.merge_only,
                    environment_overrides={k: v for k, v in environment.items()
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
        # The per-plane maps are in the evidence file the log names (engines
        # before it keep them in the log); a disabled or placebo arm must
        # neither name nor create one.
        evidence = out / 'evidence.strehl'
        named = [line for line in events if line.startswith('STREHL_UI_PROGRESS event=evidence-file ')]
        assert bool(named) == evidence.exists() and (name == 'on' or not named), (
            f'Unexpected evidence routing: {name}')
        evidence_records, final_preview = 0, None
        live = out / 'live.strehl'
        live_named = [line for line in events if line.startswith('STREHL_UI_PROGRESS event=live-file ')]
        assert bool(live_named) == live.exists() and (name == 'on' or not live_named), (
            f'Unexpected live-file routing: {name}')
        if named:
            assert named == ['STREHL_UI_PROGRESS event=evidence-file path=evidence.strehl version=1'], named
            records = evidence_events(evidence.read_bytes())
            if live_named:
                assert live_named == ['STREHL_UI_PROGRESS event=live-file path=live.strehl version=1'], live_named
                coefficients, final_preview = live_events(live.read_bytes())
                records += coefficients
                live.rename(out / f'{name}.live.strehl')
            evidence_records = len(records)
            events = with_evidence(events, records)
            evidence.rename(out / f'{name}.evidence.strehl')
        alignment = alignment_events(events, args.limit) if name == 'on' and not args.merge_only else None
        merge = None
        if name == 'on':
            plan = re.search(r'memory plan\s*:\s*(\d+) canonical chunks', text)
            assert plan, 'The actual canonical partition plan was not reported'
            chunks = int(plan.group(1))
            assert 1 <= chunks <= args.limit
            chunk_frames = (args.limit + chunks - 1) // chunks
            # The base band is weighted from the coarsest band by default
            # (image-quality-2026-11-02 section 1b); a weighted base may
            # report support. The engine's banner says which one ran.
            plain_base = not re.search(r'^base band\s*:\s*weighted', text, re.M)
            merge = merge_events(events, args.limit, chunk_frames=chunk_frames,
                                 require_intrachunk=args.require_intrachunk_preview, plain_base=plain_base,
                                 bounded_live=final_preview is not None)
            if final_preview is not None:
                # The whole preview left on disk is the final generation's, and
                # at the revision lattice it is that generation's sample.
                sequence, frame, folded, width, height, low, high, pixels = final_preview
                samples = [line for line in events if 'kind=preview ' in line]
                last = dict(part.split('=', 1) for part in samples[-1].split()[1:])
                (sw, sh), sites = revision_lattice(width, height)
                assert (int(last['seq']), int(last['frame']), int(last['folded'])) == (sequence, frame, folded)
                assert folded == merge['preview']['folded_counts'][-1], 'The live preview is not the final generation'
                assert bytes.fromhex(last['data']) == bytes(pixels[i] for i in sites), 'Live preview and sample differ'
                merge['live_preview'] = dict(folded=folded, width=width, height=height,
                                             sha256=hashlib.sha256(pixels).hexdigest())
            merge['plain_base'] = plain_base
            merge['canonical_planned_chunks'] = chunks
        assert image.stat().st_size > 0
        controls['runs'].append(dict(name=name, command=command, observer=enabled,
                                    bytes=image.stat().st_size, sha256=digest(image),
                                    events=len(events), frame_events=len(finished), alignment=alignment, merge=merge,
                                    evidence_records=evidence_records,
                                    environment_overrides={k: v for k, v in arm_environment.items()
                                        if k.startswith('STREHL_') or k == 'RAYON_NUM_THREADS'}))
        print(name, controls['runs'][-1]['sha256'], flush=True)
    controls['byte_identical'] = len({run['sha256'] for run in controls['runs']}) == 1
    (out / 'verification.json').write_text(json.dumps(controls, indent=2) + '\n', encoding='utf-8')
    assert controls['byte_identical'], 'Observer perturbed the completed TIFF'
    print('VERIFIED: on/off/placebo completed TIFF bytes identical', flush=True)


if __name__ == '__main__':
    main()
