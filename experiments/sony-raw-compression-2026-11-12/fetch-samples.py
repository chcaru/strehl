"""Download the original samples explicitly offered by Mirrorless Comparison.

Inputs stay under ignored outputs and are not redistributed with this experiment.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parents[2] / 'outputs/sony-raw-compression-2026-11-12'
SOURCE = 'https://mirrorlesscomparison.com/galleries/sony-a7r-iv-sample-photos/'
FROZEN = Path(__file__).with_name('evidence') / 'input-manifest.json'
EXPECTED = {re.split(r'[\\/]', r['path'])[-1]: r for r in json.loads(FROZEN.read_text())} if FROZEN.exists() else {}


def fetch(item):
    group, row = item
    name = re.search(r'DSC\d+\.ARW', row['label']).group()
    dest = OUT / 'inputs' / ('pixel-shift-' + group) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        session = requests.Session()
        url = 'https://drive.google.com/uc'
        params = {'export': 'download', 'id': row['id']}
        response = session.get(url, params=params, stream=True, timeout=60)
        response.raise_for_status()
        if 'text/html' in response.headers.get('Content-Type', ''):
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form', id='download-form')
            if not form:
                raise RuntimeError('Public download not offered: ' + name)
            url = form['action']
            assert url.startswith('https://drive.usercontent.google.com/')
            params = {e['name']: e.get('value', '') for e in form.select('input[name]')}
            response = session.get(url, params=params, stream=True, timeout=60)
            response.raise_for_status()
        assert 'text/html' not in response.headers.get('Content-Type', '')
        count = 0
        partial = dest.with_suffix('.partial')
        with partial.open('wb') as f:
            for chunk in response.iter_content(1024 * 1024):
                count += len(chunk)
                assert count < 150_000_000, 'Per-file download bound'
                f.write(chunk)
        assert count > 100_000_000
        assert partial.read_bytes()[:4] in (b'II*\0', b'MM\0*')
        partial.replace(dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if name in EXPECTED:
        assert digest == EXPECTED[name]['sha256'] and dest.stat().st_size == EXPECTED[name]['bytes'], 'Public input identity changed'
    receipt = {'path': str(dest), 'bytes': dest.stat().st_size,
               'sha256': digest, 'group': group, 'drive_id': row['id'],
               'source': SOURCE, 'author': 'Mathieu Gasquet / Mirrorless Comparison',
               'camera': 'Sony ILCE-7RM4', 'redistribution': False}
    print(json.dumps({'downloaded': name, 'bytes': receipt['bytes']}), flush=True)
    return receipt


if __name__ == '__main__':
    items = [(group, row) for group in ['4', '16']
             for row in json.loads((OUT / ('public-files-' + group + '.json')).read_text())]
    assert len(items) == 20
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(fetch, items))
    (OUT / 'input-manifest.json').write_text(json.dumps(rows, indent=2) + '\n')
