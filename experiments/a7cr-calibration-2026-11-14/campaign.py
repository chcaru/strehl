"""Lens-capped dark campaign: ISO sweep at the working shutter, shutter sweep at
ISO 100, and four-shot dark groups. Restores the owner's controller state once."""
import json
import time
import darks

SHUTTER_06 = 393226          # 0.6 s, the owner's working shutter (manifest)
ISO_EXT50 = 268435506        # extended ISO 50 (0x10000032)
SERIES = (
    [(16, 1, ISO_EXT50, SHUTTER_06, 'iso50ext-0.6s')]
    + [(16, 1, iso, SHUTTER_06, f'iso{iso}-0.6s') for iso in
       (125, 160, 200, 250, 320, 400, 500, 640, 800, 1600, 3200, 6400)]
    + [(16, 1, 100, 65544, 'iso100-1/8s'), (16, 1, 100, 1638410, 'iso100-2.5s'),
       (4, 4, 100, SHUTTER_06, 'iso100-0.6s-fourshot')]
)


def main():
    darks.OUT.mkdir(parents=True, exist_ok=True)
    before = darks.settled()
    (darks.OUT / f'campaign-before-{int(time.time())}.json').write_text(
        json.dumps({k: v for k, v in before.items() if k != 'samples'}, indent=2) + '\n')
    try:
        for frames, shots, iso, shutter, label in SERIES:
            r = darks.series(frames, shots, iso, shutter, label)
            with (darks.OUT / 'series.jsonl').open('a') as f:
                f.write(json.dumps(r) + '\n')
            print(label, r['folder'], round(r['wall_seconds'], 1), flush=True)
    finally:
        if darks.api.state()['editable']:
            darks.restore(before)
        after = darks.api.state()
        print('restored', after['exposure']['iso'], after['exposure']['shutter'],
              after['shots_per_plane'], after['plan'] == before['plan'], after['position'] == before['position'])


if __name__ == '__main__':
    main()
