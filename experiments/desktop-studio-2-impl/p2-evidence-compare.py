"""Compare per-plane maps between render arms, from either source.

Reads `evidence.strehl` (format in crates/strehl-cli/src/ui-evidence.rs, an
independent decoder here) and the hex `event=diagnostic` lines of a render
log (an older engine's form), and compares the gate-support maps of every
(frame, level) between two arms bit for bit. Float maps (focus energy, gate
floor) are compared byte for byte where both arms carry them.

Usage: python -I p2-evidence-compare.py A B
where each of A and B is a run folder (its evidence.strehl if present, else
the hex lines of its render.log). Prints one JSON object.
"""
import json
import struct
import sys
from pathlib import Path

KINDS = {0: 'gate-support', 1: 'averaging', 2: 'focus-energy', 3: 'gate-floor'}


def read_evidence(path):
    data = path.read_bytes()
    assert data[:8] == b'STRHEVD1', 'magic'
    version, levels = struct.unpack_from('<II', data, 8)
    assert version == 1, version
    lattices, at = [], 16
    for _ in range(levels):
        lw, lh, ew, eh = struct.unpack_from('<HHII', data, at)
        lattices.append(((lw, lh), (ew, eh)))
        at += 12
    (frames,) = struct.unpack_from('<I', data, at)
    at += 4
    maps, sequences, torn = {}, [], 0
    while at < len(data):
        if len(data) - at < 16:
            torn = len(data) - at
            break
        frame, level, kind, reserved, sequence, length = struct.unpack_from('<IBBHII', data, at)
        if len(data) - at - 16 < length:
            torn = len(data) - at
            break
        payload = data[at + 16:at + 16 + length]
        at += 16 + length
        assert reserved == 0
        (lw, lh), _ = lattices[level]
        sites = lw * lh
        if kind == 0:
            assert length == (sites + 7) // 8
            bits = [(payload[i // 8] >> (i % 8)) & 1 for i in range(sites)]
            assert sites % 8 == 0 or payload[-1] >> (sites % 8) == 0, 'dirty tail'
            value = bytes(bits)
        else:
            assert length == 8 + sites
            value = payload
        key = (frame, level, KINDS[kind])
        assert key not in maps, f'duplicate {key}'
        maps[key] = value
        sequences.append(sequence)
    return dict(source='evidence', lattices=lattices, frames=frames, maps=maps,
                sequences_increasing=all(a < b for a, b in zip(sequences, sequences[1:])),
                records=len(sequences), torn=torn, bytes=len(data))


def read_log(path):
    maps = {}
    with path.open('r', encoding='utf-8', errors='replace') as stream:
        for line in stream:
            if not line.startswith('STREHL_UI_PROGRESS event=diagnostic '):
                continue
            fields = dict(part.split('=', 1) for part in line.split()[1:])
            if fields['scope'] != 'frame':
                continue
            raw = bytes.fromhex(fields['data'])
            kind = fields['kind']
            if kind == 'gate-support':
                assert set(raw) <= {0, 255}
                value = bytes(1 if v == 255 else 0 for v in raw)
            else:
                value = struct.pack('<ff', float(fields['min']), float(fields['max'])) + raw
            key = (int(fields['frame']), int(fields['level']), kind)
            assert key not in maps, f'duplicate {key}'
            maps[key] = value
    return dict(source='log', maps=maps, records=len(maps))


def load(run):
    run = Path(run)
    evidence = run / 'evidence.strehl'
    return read_evidence(evidence) if evidence.exists() else read_log(run / 'render.log')


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    report = dict(a=sys.argv[1], b=sys.argv[2], a_source=a['source'], b_source=b['source'])
    for name, arm in [('a', a), ('b', b)]:
        kinds = {}
        for (_, _, kind) in arm['maps']:
            kinds[kind] = kinds.get(kind, 0) + 1
        report[f'{name}_kinds'] = kinds
        for key in ['records', 'bytes', 'frames', 'torn', 'sequences_increasing']:
            if key in arm:
                report[f'{name}_{key}'] = arm[key]
    support = lambda arm: {k: v for k, v in arm['maps'].items() if k[2] == 'gate-support'}
    sa, sb = support(a), support(b)
    report['support_keys_equal'] = set(sa) == set(sb)
    report['support_only_in_a'] = len(set(sa) - set(sb))
    report['support_only_in_b'] = len(set(sb) - set(sa))
    common = set(sa) & set(sb)
    differing = [k for k in common if sa[k] != sb[k]]
    report['support_compared'] = len(common)
    report['support_differing_maps'] = len(differing)
    report['support_sites_compared'] = sum(len(sa[k]) for k in common)
    report['support_sites_on'] = sum(sum(sa[k]) for k in common)
    floats = [k for k in set(a['maps']) & set(b['maps']) if k[2] != 'gate-support']
    report['float_compared'] = len(floats)
    report['float_differing'] = sum(a['maps'][k] != b['maps'][k] for k in floats)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
