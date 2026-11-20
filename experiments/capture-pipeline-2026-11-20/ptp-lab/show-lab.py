"""Print a lab log compactly. Times are seconds since the last `mark` (or shutter if none)."""
import json
import statistics as st
import sys

zero = 0.0
for line in open(sys.argv[1], encoding='utf-8'):
    line = line.strip()
    if not line or line.startswith('#'):
        if line.startswith('#'):
            print(line[:300])
        continue
    try:
        v = json.loads(line)
    except ValueError:
        print('??', line[:200])
        continue
    kind = v.get('lab')
    t = v.get('t')
    if kind is None:
        keep = {k: v[k] for k in v if k not in ('properties', 'jpeg', 'progress', 'files')}
        props = v.get('properties')
        if props:
            keep['properties'] = {k: p.get('value') for k, p in props.items()}
        print('        product reply', json.dumps(keep)[:700])
        continue
    if kind == 'mark':
        zero = t
        print('=== %s (t=%.3f)' % (v['text'], t))
        continue
    rel = '%7.3f' % (t - zero)
    if kind == 'props':
        p, e = v['properties_ms'], v['events_ms']
        print(rel, 'props: properties() %.1f ms median (%.1f-%.1f), events() %.1f ms median (%.1f-%.1f), n=%d' % (
            st.median(p), min(p), max(p), st.median(e), min(e), max(e), len(p)))
    elif kind == 'allowed':
        allowed = v['allowed']
        print(rel, 'property %s value %s writable %s enabled %s form %s allowed %s' % (
            v['code'], v['value'], v['writable'], v['enabled'], v['form'],
            allowed if len(allowed) <= 24 else '%d values: %s ... %s' % (len(allowed), allowed[:8], allowed[-4:])))
    elif kind == 'shutter':
        print(rel, 'SHUTTER %s pre %d ms (command took %.0f ms)' % (v['mode'], v['pre_ms'], 1000 * (v['done_t'] - t)))
    elif kind == 'state':
        print(rel, 'state active=%s member=%s buffer=%s focus=%s setting=%s' % (v['active'], v['member'], v['buffer'], v['focus'], v['focus_setting']))
    elif kind == 'event':
        print(rel, 'event %s arg %s' % (v['code'], v['arg']))
    elif kind == 'download':
        dt = v['done_t'] - v['info_t']
        print(rel, 'download start; info %.0f ms; body %.3f s = %.0f MB/s; done at %.3f (%s)' % (
            1000 * (v['info_t'] - t), dt, v['bytes'] / 1e6 / dt, v['done_t'] - zero, v['camera_name']))
    elif kind in ('set', 'jog', 'setrb'):
        print(rel, kind, {k: v[k] for k in v if k not in ('lab', 't', 'done_t')}, 'took %.0f ms' % (1000 * (v['done_t'] - t)))
    elif kind == 'watch':
        print(rel, 'watch ended by %s after %d polls' % (v['ended'], v['polls']))
    elif kind == 'sleep':
        pass
    else:
        print(rel, json.dumps(v)[:300])
