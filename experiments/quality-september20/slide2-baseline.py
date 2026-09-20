"""One complete held-renderer slide2 baseline. Root executes; originals read only."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RAW = Path('D:/personal/macro/requests/misc-diagnostic/high-res-calibration-slide-2-cpl')
BUILD = ROOT/'experiments/native-gpu-gather/build-native-6'
EXE = BUILD/'strehl.exe'
EXE_SHA = '2fd0a1615989e262fbba61e0a1587a9b8f20ff4913d3969510e967ce9d9219d7'
spec = importlib.util.spec_from_file_location('slide2_bounded', ROOT/'experiments/m193c-output-grid/bounded-process.py')
bounded = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bounded
spec.loader.exec_module(bounded)


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def binding(path):
    return dict(path=str(path.resolve()), **bounded.binding(path))


def inventory():
    # pathlib does not suppress Windows hidden/system files, unlike default PowerShell enumeration.
    return [dict(path=str(p.resolve()), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns)
            for p in sorted(RAW.rglob('*')) if p.is_file()]


def views(tiff, out):
    import numpy as np
    import tifffile
    from PIL import Image
    with tifffile.TiffFile(tiff) as source:
        assert len(source.pages) == 1
        page = source.pages[0]
        icc = bytes(page.tags[34675].value)
        pixels = page.asarray()
    assert pixels.dtype == np.uint16 and pixels.ndim == 3 and pixels.shape[2] == 3
    assert hashlib.sha256(icc).hexdigest() == '238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
    pixel_sha = hashlib.sha256(np.ascontiguousarray(pixels, dtype='<u2').tobytes()).hexdigest()
    image = Image.fromarray(((pixels.astype(np.uint32)+128)//257).astype(np.uint8))
    full, overview = out/'slide2-full.png', out/'slide2-overview-only.png'
    assert not full.exists() and not overview.exists()
    image.save(full, icc_profile=icc)
    image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
    image.save(overview, icc_profile=icc)
    return dict(shape=list(pixels.shape), decoded_rgb16_le_sha256=pixel_sha,
        full_native_png=binding(full), overview_only=binding(overview),
        icc_sha256=hashlib.sha256(icc).hexdigest(),
        display='rounded u16/257; original sRGB ICC; full PNG unresampled; overview is orientation only')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=HERE/'slide2-baseline-1')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    assert bounded.binding(EXE)['sha256'] == EXE_SHA
    inputs = inventory()
    raw_files = sorted(p for p in RAW.iterdir() if p.is_file() and p.suffix.upper() == '.ARW')
    assert [p.name for p in raw_files] == [f'DSC{i:05d}.ARW' for i in range(1, 300)]
    assert len([i for i in inputs if Path(i['path']).suffix.upper() == '.ARW']) == 299
    print('SLIDE2 input hashing 299 originals', flush=True)
    original_hashes = {i['path']: bounded.binding(i['path'])['sha256'] for i in inputs}
    save(out/'inputs.json', dict(inventory=inputs, sha256=original_hashes,
                               hidden_system_files_included=True))
    warp, tiff = out/'slide2.warpmap.txt', out/'slide2.tiff'
    fields = dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
        STREHL_WARPMAP=str(warp), STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded',
        STREHL_PROBE_GATHER='green', STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on',
        STREHL_GPU_SCHEDULE='device', STREHL_GPU_GATHER_LOG='off', STREHL_DEFECT='off')
    environment, removed = bounded.clean_environment(fields.items())
    harness = ROOT/'experiments/m12-scorecard/m12-harness.py'
    api = bounded.load_job_api(bounded.binding(harness))
    sources = [Path(__file__), HERE/'slide2-baseline-plan.md', Path(spec.origin), harness,
               ROOT/'experiments/quality-september14/checker-baseline.py',
               BUILD/'invocation.json', BUILD/'executables.json', BUILD/'build-result.json']
    source_bindings = [binding(p) for p in sources]
    commands = [
        ('align', [str(EXE), 'align', str(RAW), '--out', str(warp), '--threads', '8', '--resampler', 'catmull-rom']),
        ('render', [str(EXE), 'stack', str(RAW), '--merge', 'pyramid', '--pyramid-bands', '7',
            '--pyramid-gate', '2', '--pyramid-exponent', '2', '--pyramid-sharpen', '1.4',
            '--pyramid-select', 'soft', '--pyramid-base', 'mean', '--srgb', '--demosaic',
            '--resampler', 'catmull-rom', '--cover', 'crop', '--out', str(tiff)])]
    save(out/'invocation.json', dict(executable=binding(EXE), sources=source_bindings,
        commands=commands, environment=fields, removed_environment=removed,
        original_count=299, expected_reference=149,
        limits=dict(wall_seconds_per_stage=900, cpu_seconds_per_stage=7200, committed_bytes_per_stage=12<<30),
        scope='Unchanged historical renderer baseline; automatic gear profile and tone; no source witness or quality-gain claim',
        binary_provenance='Retained build-native-6 receipts; no claim it was built from current edited sources'))
    for stage, command in commands:
        assert not (warp if stage == 'align' else tiff).exists()
        print('SLIDE2 stage', stage, flush=True)
        result = bounded.run(command, environment, ROOT, out/f'{stage}.log', api=api,
            wall_seconds=900, cpu_seconds=7200, log_bytes=8<<20, committed_bytes=12<<30)
        save(out/f'{stage}-process.json', result)
        assert result['exit_code'] == 0 and result['error'] is None
        assert result['terminal_job_accounting'] and not result['cleanup_errors']
        assert inventory() == inputs and bounded.binding(EXE)['sha256'] == EXE_SHA
        if stage == 'align':
            lines = warp.read_text().splitlines()
            placements = [line.split() for line in lines if line and line.split()[0].isdigit()]
            assert len(placements) == 299 and all(p[1] == 'placed' for p in placements)
            assert {int(p[0]) for p in placements} == set(range(299)) and 'reference 149' in lines
    log = (out/'render.log').read_text(encoding='utf-8', errors='replace')
    assert 'camera          : ILCE-7CM2' in log
    assert 'profile "a7c2-fe100gm-2xtc-x4cpl" (gear matched; default on)' in log
    assert re.search(r'frames\s*:\s*299\b', log)
    domain = re.search(r'analysis domain\s*:\s*(\d+) x (\d+) at full-plane origin \((\d+), (\d+)\)', log)
    assert domain is not None
    width, height, x, y = map(int, domain.groups())
    display = views(tiff, out)
    assert display['shape'] == [2*height, 2*width, 3]
    print('SLIDE2 final original content check', flush=True)
    assert inventory() == inputs
    assert all(bounded.binding(p)['sha256'] == digest for p, digest in original_hashes.items())
    assert all(bounded.binding(b['path'])['sha256'] == b['sha256'] for b in source_bindings)
    assert bounded.binding(EXE)['sha256'] == EXE_SHA
    receipt = dict(status='BASELINE_RENDERED', original_count=299, reference=149,
        crop_quad_xywh=[x, y, width, height], original_metadata_and_content_unchanged=True,
        map=binding(warp), master=binding(tiff), display=display, executable=binding(EXE),
        selected_render_log=[line for line in log.splitlines() if re.match(r'^(camera|lateral CA|iso|levels|frames|analysis domain|bands|exposure|tone|output)\s*:', line)],
        baseline_only=True, quality_gain_claim=False)
    save(out/'completion.json', receipt)
    links = '\n'.join([f'# Complete slide2 baseline', '', f'[RGB16 master]({tiff.as_posix()})', '',
        f'[Full native PNG]({(out/"slide2-full.png").as_posix()})', '',
        f'[Overview — orientation only]({(out/"slide2-overview-only.png").as_posix()})', '',
        'All299 captures. No improvement or source-detail-retention claim.', ''])
    with (out/'images.md').open('x', encoding='utf-8') as stream:
        stream.write(links)
    print('SLIDE2_BASELINE_COMPLETE', json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
