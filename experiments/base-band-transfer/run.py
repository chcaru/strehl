"""One root-executed garnet183 mean-versus-weighted base comparison; no build or sweep."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE = ROOT/'outputs/quality-september25/garnet-104'
HELPER = ROOT/'experiments/m193c-output-grid/bounded-process.py'
HARNESS = ROOT/'experiments/m12-scorecard/m12-harness.py'
EXPECTED_EXE = 'bec4c357836ad1383800a6c933460ee7ef072c525b5957a6f5deb5194b203314'
PINNED = {'invocation.json': 'b7ef4688da81b31186558918df117d8fcefe097bb3b71fe1b1de3182b39bf2c0',
          'input-order.json': 'bb6088a70737f9581c85fd89caaeb586fbb4c29a25196c9e60b953034c40633e',
          'completion.json': 'f40f3fdeab28d92000a91b64906c90a0bc30935b51a13ca9bec840c359130bfd'}


def ref(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1 << 20):
            digest.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def original_records(folder):
    paths = sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == '.arw'), key=str)
    return [dict(index=i, mtime_ns=p.stat().st_mtime_ns, **ref(p)) for i, p in enumerate(paths)]


def photographic_metadata(log):
    prefixes = ('camera ', 'lateral CA ', 'iso ', 'levels ', 'planes ', 'analysis domain ',
                'bands ', 'selection ', 'noise gate ', 'exponent ', 'per-band exp ', 'memory plan ',
                'colour ', 'characterisation:', 'XYZ->cam rows:', 'implied daylight WB ', 'Order:')
    return [line.strip() for line in log.splitlines() if line.lstrip().startswith(prefixes)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists() and out.parent.is_dir()
    started = time.perf_counter()
    baseline_bindings = [ref(BASELINE/name) for name in PINNED]
    assert all(row['sha256'] == PINNED[Path(row['path']).name] for row in baseline_bindings)
    invocation, delivered = read(BASELINE/'invocation.json'), read(BASELINE/'completion.json')
    assert invocation['frames'] == delivered['frames'] == 183
    assert delivered['native_dimensions'] == [6524, 4348] and delivered['crop_quad_xywh'] == [127, 85, 3262, 2174]
    assert len(invocation['commands']) == 1 and invocation['commands'][0][0] == 'render'
    old = invocation['commands'][0][1]
    executable = Path(old[0])
    assert ref(executable) == invocation['executable'] == delivered['executable']
    assert invocation['executable']['sha256'] == EXPECTED_EXE
    assert old[1] == 'stack' and old.count('--pyramid-base') == old.count('--out') == 1
    base_index, out_index = old.index('--pyramid-base')+1, old.index('--out')+1
    assert old[base_index] == 'mean' and Path(old[out_index]) == Path(delivered['master']['path'])
    assert old[-1] == '--exposure=0.0' and '--limit' not in old
    assert ref(Path(delivered['master']['path'])) == delivered['master']
    assert ref(Path(delivered['full_jpeg']['path'])) == delivered['full_jpeg']
    assert ref(Path(delivered['overview']['path'])) == delivered['overview']
    source = Path(old[2])
    before = original_records(source)
    assert len(before) == 183 and before == read(BASELINE/'input-order.json'), 'Original order/content/mtime changed.'
    fields = invocation['environment'].copy()  # Exact baseline fields, including unchanged corrected binary.
    warp = Path(fields['STREHL_WARPMAP'])
    assert ref(warp) == invocation['existing_map'] == delivered['warp_map']
    map_lines = warp.read_text().splitlines()
    assert 'reference 91' in map_lines and 'frames 183' in map_lines and 'resampler catmull-rom' in map_lines
    rows = [line.split() for line in map_lines if line and line.split()[0].isdigit()]
    assert [int(row[0]) for row in rows] == list(range(183)) and all(row[1] == 'placed' for row in rows)
    assert 'STREHL_LOCAL_PLACEMENT_FILE' not in fields
    master = out/'stack-master.tiff'
    command = old.copy()
    command[base_index], command[out_index] = 'weighted', str(master)
    differences = [dict(index=i, baseline=a, candidate=b) for i, (a, b) in enumerate(zip(old, command)) if a != b]
    assert len(command) == len(old) and [row['index'] for row in differences] == sorted([base_index, out_index])
    out.mkdir()
    save(out/'input-order.json', before)
    spec = importlib.util.spec_from_file_location('base_band_bounded_process', HELPER)
    bounded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bounded
    spec.loader.exec_module(bounded)
    assert ref(HELPER) == invocation['helper'] and ref(HARNESS) == invocation['harness']
    env, removed = bounded.clean_environment(fields.items())
    sources = [ref(Path(__file__).resolve()), ref(HERE/'design.md'), ref(HELPER), ref(HARNESS)]
    save(out/'invocation.json', dict(schema=1, baseline=baseline_bindings, baseline_master=delivered['master'],
         baseline_full_jpeg=delivered['full_jpeg'], baseline_overview=delivered['overview'],
         executable=ref(executable), map=ref(warp), reference=91, frames=183, command=command,
         baseline_command=old, command_differences=differences, environment=fields, removed_environment=removed,
         sources=sources, limits=dict(wall_seconds=180, cpu_seconds=900, committed_bytes=8 << 30),
         tone_policy='Actual production automatic tone is independently remeasured in each arm. Logged anchors are rounded, not exact f32. Do not interpret darkening as improvement.',
         scope='One complete base-weighting counterfactual with corrected current production binary; no automatic promotion or sweep.'))
    api = bounded.load_job_api(bounded.binding(HARNESS))
    result = bounded.run(command, env, ROOT, out/'render.log', api=api, wall_seconds=180, cpu_seconds=900,
                         committed_bytes=8 << 30, log_bytes=8 << 20)
    save(out/'render-process.json', result)
    assert result['exit_code'] == 0 and result['error'] is None and result['terminal_job_accounting'] and not result['cleanup_errors']
    log = (out/'render.log').read_text(encoding='utf-8', errors='replace')
    baseline_log = (BASELINE/'render.log').read_text(encoding='utf-8', errors='replace')
    assert photographic_metadata(log) == photographic_metadata(baseline_log), 'Held camera/geometry/merge metadata differ.'
    base_lines = [line for line in log.splitlines() if line.startswith('base band')]
    assert len(base_lines) == 1 and 'weighted by the coarsest' in base_lines[0], 'Weighted base not exercised.'
    assert re.search(r'alignment\s*:\s*ON \(sidecar-override\), reference frame 91, 183 placed / 0 refused', log)
    domain = re.search(r'analysis domain\s*:\s*(\d+) x (\d+) at full-plane origin \((\d+), (\d+)\)', log)
    assert domain and list(map(int, domain.groups())) == [3262, 2174, 127, 85]
    tones = {name: [line for line in text.splitlines() if line.startswith('tone ')] for name, text in (('mean', baseline_log), ('weighted', log))}
    assert all(len(lines) == 1 for lines in tones.values())
    import numpy as np
    import tifffile
    from PIL import Image
    with tifffile.TiffFile(delivered['master']['path']) as f:
        baseline_rgb = f.asarray()
        baseline_icc = bytes(f.pages[0].tags[34675].value)
        assert len(f.pages) == 1 and baseline_rgb.dtype == np.uint16 and baseline_rgb.shape == (4348, 6524, 3)
        baseline_pixel_hash = hashlib.sha256(baseline_rgb.astype('<u2', copy=False).tobytes()).hexdigest()
    del baseline_rgb
    with tifffile.TiffFile(master) as f:
        rgb = f.asarray()
        icc = bytes(f.pages[0].tags[34675].value)
        assert len(f.pages) == 1 and rgb.dtype == np.uint16 and rgb.shape == (4348, 6524, 3) and icc == baseline_icc and icc
    pixel_hash = hashlib.sha256(rgb.astype('<u2', copy=False).tobytes()).hexdigest()
    image = Image.fromarray(((rgb.astype(np.uint32)+128)//257).astype(np.uint8))
    image.save(out/'stack-full.jpg', quality=98, subsampling=0, icc_profile=icc)
    image.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
    image.save(out/'overview.jpg', quality=98, icc_profile=icc)
    with Image.open(out/'stack-full.jpg') as check:
        assert check.size == (6524, 4348) and check.info.get('icc_profile') == icc
    after = original_records(source)
    save(out/'input-order-after.json', after)
    assert after == before, 'Original order/content/mtime changed.'
    for bound in [*sources, *baseline_bindings, invocation['executable'], invocation['existing_map'], delivered['master']]:
        assert ref(Path(bound['path'])) == bound, 'Held reference or source changed.'
    save(out/'completion.json', dict(schema=1, status='COMPLETE_AWAITING_INDEPENDENT_PHOTOGRAPHIC_REVIEW', frames=183,
         reference=91, crop_quad_xywh=[127, 85, 3262, 2174], native_dimensions=[6524, 4348],
         master=ref(master), full_jpeg=ref(out/'stack-full.jpg'), overview=ref(out/'overview.jpg'),
         baseline_master=delivered['master'], baseline_full_jpeg=delivered['full_jpeg'], baseline_overview=delivered['overview'],
         baseline_rgb16_le_sha256=baseline_pixel_hash, candidate_rgb16_le_sha256=pixel_hash,
         icc_sha256=hashlib.sha256(icc).hexdigest(), command_differences=differences, tone_log_lines=tones,
         tone_anchors_exactly_pinned=False, original_bytes_and_metadata_unchanged=True,
         total_wrapper_wall_seconds=time.perf_counter()-started,
         resource_scope='Render job includes183 original decodes through final TIFF. Original hash audits and JPEG preparation are outside render-job timing.',
         visual_verdict=None, scope='Judge structural retention and broad spill; darker is not evidence of improvement. No sweep or default change.'))
    print(f'Complete weighted-base counterfactual: {master}', flush=True)


if __name__ == '__main__':
    main()
