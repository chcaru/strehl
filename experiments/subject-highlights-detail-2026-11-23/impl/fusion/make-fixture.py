"""Build a tiered fixture capture (plan X4) from single-plane test runs.

Each plane is a base four-shot run, optionally with a highlight run taken at the
same focus; the fixture is a new folder in the format of `impl/tiers.md`: the
`.straw` members copied under new names, `capture_buffered` events with `tier`
and `exposure`, durable receipts with the original hashes, and a manifest with
`plan.highlight`. The source runs are read only.

  python make-fixture.py OUT --every N --highlight-shutter CODE \
      --plane BASE_RUN[+HIGHLIGHT_RUN] [--plane ...] [--no-tiers]

`--no-tiers` writes the base planes alone, without any tier field (the
"capture without highlight groups" control).
"""
import argparse
import json
import pathlib
import shutil


def groups(run):
    """The run's capture_buffered events: (event, files) in order."""
    out = []
    for line in open(run / 'events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        if e.get('event') == 'capture_buffered':
            out.append(e)
    return out


def receipts(run):
    r = {}
    for line in open(run / 'transfer-receipts.jsonl', encoding='utf-8'):
        try:
            v = json.loads(line)
        except json.JSONDecodeError:
            continue
        if v.get('durable') and v.get('ok'):
            r[v['logical_name']] = v['sha256']
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--plane', action='append', required=True)
    ap.add_argument('--every', type=int, default=1)
    ap.add_argument('--highlight-shutter', type=int, default=None)
    ap.add_argument('--no-tiers', action='store_true')
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    events, recs = [], []
    n = 0
    seq = 0
    first_manifest = None
    hl_planes = []
    for plane, spec in enumerate(a.plane, start=1):
        parts = spec.split('+', 1)
        tiers = [('base', pathlib.Path(parts[0]))]
        if len(parts) > 1 and parts[1] and not a.no_tiers:
            tiers.append(('highlight', pathlib.Path(parts[1])))
            hl_planes.append(plane)
        for tier, run in tiers:
            manifest = json.load(open(run / 'manifest.json', encoding='utf-8'))
            if first_manifest is None:
                first_manifest = manifest
            shutter = manifest['initial_status']['properties']['ShutterSpeed']['value']
            iso = manifest['initial_status']['properties']['IsoSensitivity']['value']
            sha = receipts(run)
            ev = groups(run)
            assert len(ev) == 1, f'{run}: expected one group'
            e = ev[0]
            files = []
            gid = f'{tier}-{plane}-' + e['data']['response']['files'][0]['group_id']
            for f in sorted(e['data']['response']['files'], key=lambda f: f['member_index']):
                n += 1
                name = f'frame-{n:06d}.ARW'
                src = run / (f['name'] + '.straw')
                shutil.copyfile(src, out / (name + '.straw'))
                assert sha[f['name']] == f['sha256']
                entry = {'name': name, 'plane': plane, 'sha256': f['sha256'], 'group_id': gid,
                         'member_index': f['member_index'], 'members': f['members'], 'durable': False}
                if not a.no_tiers:
                    entry['tier'] = tier
                files.append(entry)
                recs.append({'logical_name': name, 'sha256': f['sha256'], 'durable': True, 'ok': True,
                             'source': str(src)})
            data = {'target': e['data'].get('target'), 'response': {'files': files}}
            if not a.no_tiers:
                data['tier'] = tier
                data['exposure'] = {'iso': iso, 'shutter': shutter}
            seq += 1
            events.append({'event': 'capture_buffered', 'sequence': seq, 'data': data,
                           'source_run': str(run)})
    manifest = dict(first_manifest)
    manifest['capture_kind'] = 'x4-fixture'
    manifest['planned_planes'] = len(a.plane)
    plan = dict(manifest.get('plan', {}))
    plan.pop('highlight', None)
    if hl_planes and not a.no_tiers:
        plan['highlight'] = {'shutter': a.highlight_shutter, 'every': a.every,
                             'first_plane': min(hl_planes), 'last_plane': max(hl_planes), 'shots': 4}
    manifest['plan'] = plan
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    (out / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
    (out / 'transfer-receipts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in recs), encoding='utf-8')
    (out / 'result.json').write_text(json.dumps({'outcome': 'complete', 'schema': 'strehl-capture-result-v1'}) + '\n',
                                     encoding='utf-8')
    print(f'{out}: {len(a.plane)} planes, {n} files, highlight planes {hl_planes}')


if __name__ == '__main__':
    main()
