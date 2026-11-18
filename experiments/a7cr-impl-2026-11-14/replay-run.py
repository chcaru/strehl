"""Replay a completed capture run into a fresh folder in capture order (plan S1 replayer).

Usage: replay-run.py SRC_RUN DST_RUN [--seconds-per-plane 2] [--drop PLANE:MEMBER]
                     [--torn-tail] [--add-targets]

Members appear (hard-linked, never copied) before their durable receipt line,
then the plane's capture_buffered event is appended, as the receiver and
controller do. --drop withholds one member and its receipt (a member that never
arrives); --torn-tail leaves half an events line written for one poll interval;
--add-targets gives synthetic runs a focus target per plane. result.json comes
last. The source run is only read.
"""
import argparse, json, os, shutil, time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--seconds-per-plane', type=float, default=2.0)
ap.add_argument('--drop')
ap.add_argument('--torn-tail', action='store_true')
ap.add_argument('--add-targets', action='store_true')
a = ap.parse_args()
src, dst = Path(a.src), Path(a.dst)
dst.mkdir(parents=True)
drop = tuple(map(int, a.drop.split(':'))) if a.drop else None
shutil.copy2(src / 'manifest.json', dst / 'manifest.json')
receipts = {json.loads(l)['logical_name']: l for l in (src / 'transfer-receipts.jsonl').read_text().splitlines() if l.strip()}
events = [json.loads(l) for l in (src / 'events.jsonl').read_text().splitlines() if l.strip()]
(dst / 'events.jsonl').write_text('')
(dst / 'transfer-receipts.jsonl').write_text('')
for e in events:
    files = e.get('data', {}).get('response', {}).get('files')
    if a.add_targets and files:
        e['data']['target'] = 30000 + files[0]['plane']
    for f in files or []:
        if drop and (f['plane'], f['member_index']) == drop:
            continue
        name = f['name']
        stored = name + '.straw' if (src / (name + '.straw')).exists() else name
        os.link(src / stored, dst / stored)
        with open(dst / 'transfer-receipts.jsonl', 'a') as r:
            r.write(receipts[name] + '\n')
    line = json.dumps(e) + '\n'
    with open(dst / 'events.jsonl', 'a') as ev:
        if a.torn_tail and files and files[0]['plane'] == 2:
            ev.write(line[: len(line) // 2]); ev.flush()
            time.sleep(1.5)
            ev.write(line[len(line) // 2:])
        else:
            ev.write(line)
    print('replayed event', e.get('event'), flush=True)
    time.sleep(a.seconds_per_plane)
(dst / 'result.json').write_text(json.dumps({'schema': 'strehl-capture-result-v1', 'outcome': 'complete', 'replayed_from': str(src)}) + '\n')
print('result written', flush=True)
