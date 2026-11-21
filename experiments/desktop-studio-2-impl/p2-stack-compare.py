"""Compare the stack's live maps of a run that kept them as hex log lines
(BEFORE) with a run that wrote them to `evidence.strehl` and `live.strehl`
(AFTER), from independent decoders of both forms.

Checks, for the same input and fold:
- every accepted generation's averaging maps, bit for bit;
- every generation's preview revision sample against the BEFORE preview's
  bytes at the desktop's revision lattice (process-revision.rs), with its
  min and max;
- the live file's coefficient maps and whole preview against BEFORE's newest
  generation, byte for byte.

Usage: python -I p2-stack-compare.py BEFORE_RUN AFTER_RUN. Prints one JSON object.
"""
import json
import math
import struct
import sys
from pathlib import Path


def revision_sites(width, height):
    scale = min(64 / width, 48 / height, 1.0)
    w, h = max(1, math.floor(width * scale)), max(1, math.floor(height * scale))
    sites = [min((2 * y + 1) * height // (2 * h), height - 1) * width
             + min((2 * x + 1) * width // (2 * w), width - 1) for y in range(h) for x in range(w)]
    return (w, h), sites


def f32(text):
    return struct.unpack('<f', struct.pack('<f', float(text)))[0]


def before_maps(run):
    averaging, coefficient, previews = {}, {}, {}
    with (Path(run) / 'render.log').open('r', encoding='utf-8', errors='replace') as stream:
        for line in stream:
            if not line.startswith('STREHL_UI_PROGRESS event=diagnostic '):
                continue
            item = dict(part.split('=', 1) for part in line.split()[1:])
            if item['scope'] != 'stack':
                continue
            data = bytes.fromhex(item['data'])
            folded, level = int(item['folded']), int(item['level'])
            if item['kind'] == 'averaging':
                averaging[(folded, level)] = bytes(1 if v == 255 else 0 for v in data)
            elif item['kind'] == 'coefficient':
                coefficient[(folded, level)] = (f32(item['min']), f32(item['max']), data)
            elif item['kind'] == 'preview':
                previews[folded] = (int(item['width']), int(item['height']), f32(item['min']),
                                    f32(item['max']), data, int(item['level']))
    return averaging, coefficient, previews


def after_maps(run):
    data = (Path(run) / 'evidence.strehl').read_bytes()
    assert data[:8] == b'STRHEVD1'
    levels = struct.unpack_from('<I', data, 12)[0]
    lattices = [struct.unpack_from('<HH', data, 16 + 12 * k) for k in range(levels)]
    at = 16 + 12 * levels + 4
    averaging, samples = {}, {}
    while at < len(data):
        frame, level, kind, _, sequence, length = struct.unpack_from('<IBBHII', data, at)
        payload = data[at + 16:at + 16 + length]
        at += 16 + length
        if kind == 1:
            (folded,) = struct.unpack_from('<I', payload, 0)
            lw, lh = lattices[level]
            bits = payload[4:]
            averaging[(folded, level)] = bytes((bits[i // 8] >> (i % 8)) & 1 for i in range(lw * lh))
        elif kind == 6:
            folded, pw, ph, w, h, low, high = struct.unpack_from('<IHHHHff', payload, 0)
            samples[folded] = (pw, ph, w, h, low, high, payload[20:], level)
    live = (Path(run) / 'live.strehl').read_bytes()
    assert live[:8] == b'STRHLIV1'
    count = struct.unpack_from('<I', live, 16)[0]
    at, coefficient, preview = 20, {}, None
    while at < len(live):
        frame, level, kind, _, sequence, length = struct.unpack_from('<IBBHII', live, at)
        payload = live[at + 16:at + 16 + length]
        at += 16 + length
        folded, w, h, low, high = struct.unpack_from('<IHHff', payload, 0)
        if kind == 4:
            coefficient[(folded, level)] = (low, high, payload[16:])
        else:
            preview = (folded, w, h, low, high, payload[16:], level)
    assert len(coefficient) + 1 == count
    return averaging, samples, coefficient, preview, len(data), len(live)


def main():
    b_avg, b_coef, b_prev = before_maps(sys.argv[1])
    a_avg, a_samples, a_coef, a_prev, evidence_bytes, live_bytes = after_maps(sys.argv[2])
    report = dict(before=sys.argv[1], after=sys.argv[2], evidence_bytes=evidence_bytes, live_bytes=live_bytes)
    report['averaging_keys_equal'] = set(b_avg) == set(a_avg)
    report['averaging_compared'] = len(set(b_avg) & set(a_avg))
    report['averaging_differing'] = sum(b_avg[k] != a_avg[k] for k in set(b_avg) & set(a_avg))
    differing, compared = 0, 0
    for folded, (pw, ph, low, high, data, level) in b_prev.items():
        sample = a_samples.get(folded)
        if sample is None:
            differing += 1
            continue
        (w, h), sites = revision_sites(pw, ph)
        compared += 1
        differing += sample != (pw, ph, w, h, low, high, bytes(data[i] for i in sites), level)
    report['generations_before'] = len(b_prev)
    report['samples_after'] = len(a_samples)
    report['samples_compared'] = compared
    report['samples_differing'] = differing
    final = max(b_prev)
    pw, ph, low, high, data, level = b_prev[final]
    report['live_preview_equal'] = a_prev == (final, pw, ph, low, high, data, level)
    report['live_preview_folded'] = a_prev[0]
    newest = {level: value for (folded, level), value in b_coef.items() if folded == final}
    report['live_coefficient_levels'] = len(a_coef)
    report['live_coefficient_equal'] = (
        set(a_coef) == {(final, level) for level in newest}
        and all(a_coef[(final, level)] == newest[level] for level in newest))
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
