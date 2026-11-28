"""Fetch one or two public sample RAW files per camera from raw.pixls.us (CC0)
into samples/<n>/ (one directory per file). Prints what it took."""
import pathlib
import re
import sys
import urllib.parse
import urllib.request

BASE = 'https://raw.pixls.us/data/'
OUT = pathlib.Path('C:/strehl-scratch/calib-page/samples')
WANT = [
    ('Canon', 'EOS R5', ['RAW_ISO_100_nocrop_nodual', 'CRAW_ISO_100_nocrop_nodual']),
    ('Canon', 'EOS 5D Mark IV', [None]),
    ('Canon', 'EOS 90D', [None]),
    ('Canon', 'EOS R6 Mark II', [None]),
    ('Nikon', 'Z 7', [None]),
    ('Nikon', 'Z 8', [None]),
    ('Nikon', 'D850', [None]),
    ('Fujifilm', 'X-T4', [None]),
    ('Fujifilm', 'GFX 100S', [None]),
    ('OM Digital Solutions', 'OM-1', [None]),
    ('Olympus', 'E-M1 Mark III', [None]),
    ('Panasonic', 'DC-S1R', [None]),
    ('Panasonic', 'DC-GH5', [None]),
    ('Pentax', 'K-1 Mark II', [None]),
    ('Leica', 'M11', [None]),
    ('Hasselblad', 'X1D II 50C', [None]),
    ('Sony', 'ILCE-7RM5', [None]),
]


def listing(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            html = r.read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return None, str(e)
    names = [urllib.parse.unquote(h) for h in re.findall(r'href="([^"?/][^"]*)"', html)]
    return names, None


def main():
    only = sys.argv[1:] or None
    n = 0
    for maker, model, picks in WANT:
        if only and model not in only:
            continue
        url = BASE + urllib.parse.quote(maker) + '/' + urllib.parse.quote(model) + '/'
        names, err = listing(url)
        if names is None:
            mk, _ = listing(BASE + urllib.parse.quote(maker) + '/')
            close = [m for m in (mk or []) if model.split()[0].lower() in m.lower()][:12]
            print('MISSING', maker, model, err, 'near:', close)
            continue
        files = [f for f in names if not f.endswith('/')]
        chosen = []
        for pick in picks:
            if pick is None:
                chosen += files[:2]
            else:
                chosen += [f for f in files if pick in f][:1]
        print(maker, model, 'has', len(files), 'files; taking', chosen)
        for f in chosen:
            n += 1
            d = OUT / ('%02d-%s' % (n, re.sub(r'[^A-Za-z0-9]+', '-', model).strip('-').lower()))
            d.mkdir(parents=True, exist_ok=True)
            target = d / f
            if target.exists():
                continue
            with urllib.request.urlopen(url + urllib.parse.quote(f), timeout=180) as r:
                target.write_bytes(r.read())
            print('  ', target, round(target.stat().st_size / 1e6, 1), 'MB')


main()
