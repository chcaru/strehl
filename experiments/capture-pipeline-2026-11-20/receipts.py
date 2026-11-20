"""Read-only: for each RAW of a run, when the Pi had it (journal) and when the PC had saved it
(receipt), so the uplink's lag and rate are visible. Clocks: the Pi's and the PC's (NTP);
differences of the same clock are exact, cross-clock lags carry the clocks' offset."""
import json
import statistics as st
import sys

for run in sys.argv[1:]:
    rows = [json.loads(l) for l in open(run + '/transfer-receipts.jsonl', encoding='utf-8') if l.strip()]
    saved = {}
    for r in rows:
        name = r.get('logical_name') or r.get('name') or ''
        if 'wire_bytes' in r and 'saved_unix_ms' in r:
            saved[name] = r
    events = [json.loads(l) for l in open(run + '/events.jsonl', encoding='utf-8') if l.strip()]
    lags, planes, wire, size, stored = [], [], [], [], []
    prev_last = None
    for e in events:
        if e.get('event') != 'capture_buffered':
            continue
        resp = e['data']['response']
        reply = resp.get('camera_reply') or {}
        start = e['unix_ms'] - 1000 * resp.get('camera_seconds', reply.get('seconds', 0))
        cam = {f['member_index']: f['seconds'] for f in reply.get('files', [])}
        row = []
        for f in resp.get('files', []):
            r = saved.get(f['name'])
            if not r:
                continue
            on_pi = start + 1000 * cam.get(f['member_index'], 0)
            row.append((f['member_index'], (on_pi - start) / 1000, (r['saved_unix_ms'] - start) / 1000))
            lags.append((r['saved_unix_ms'] - on_pi) / 1000)
            wire.append(r['wire_bytes'])
            size.append(r['bytes'])
            stored.append(r.get('storage_bytes', 0))
        if row:
            last = max(x[2] for x in row) * 1000 + start
            planes.append((e['data']['ordinal'], row, None if prev_last is None else (last - prev_last) / 1000))
            prev_last = last
    if not lags:
        print(run.split('/')[-1], 'no matched RAWs')
        continue
    print('%s: %d RAWs, %.1f MB each, wire %.1f MB (%.1f %%), stored %.1f MB; lag Pi-has-it -> PC-saved: median %.2f s (%.2f-%.2f)' % (
        run.split('/')[-1], len(lags), st.median(size) / 1e6, st.median(wire) / 1e6, 100 * sum(wire) / sum(size),
        st.median(stored) / 1e6, st.median(lags), min(lags), max(lags)))
    periods = [p[2] for p in planes if p[2]]
    if periods:
        per_plane = sum(wire) / len(planes)
        print('   last-RAW-saved period %.2f s median; wire per plane %.0f MB -> %.1f MB/s averaged over the period' % (
            st.median(periods), per_plane / 1e6, per_plane / 1e6 / st.median(periods)))
    for ordinal, row, _ in planes[1:3]:
        print('   plane %d: ' % ordinal + '; '.join('RAW %d on Pi %.2f s, saved on PC %.2f s' % x for x in row))
