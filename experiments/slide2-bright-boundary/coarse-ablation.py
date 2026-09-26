"""One fixed coarsest-AC ablation; no sweep or default promotion."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('boundary_render', HERE/'render.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
b = r.b


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.parent == HERE and not out.exists()
    prior = HERE/'render-1'
    ready = r.read(prior/'completion.json')
    assert ready['observer_pixel_and_byte_identical'] and ready['raw_locator_consumer_bit_exact']
    master = Path(ready['full_image']['path'])
    assert r.ref(master) == ready['full_image'] and ready['full_image']['sha256'] == r.OFF_SHA
    old_cfg = r.read(prior/'on/config.json')
    invocation = r.read(prior/'on/invocation.json')
    exe = Path(invocation['command'][0])
    assert r.ref(exe)['sha256'] == r.EXE_SHA
    sources = r.read(r.BUILD/'sources.json')
    core = ROOT/'crates/strehl-core/src/pyramid.rs'
    assert any(Path(v['path']) == core and r.ref(core) == v for v in sources)
    # Existing build's mean_coarse default reads this environment in a fresh
    # process. In the source, only AC k=6 of seven is routed to mean fallback;
    # terminal Mean remains Mean. This is source evidence, not band hashes.
    assert 'STREHL_PYRAMID_MEAN_COARSE' not in invocation['environment']
    rawdir = Path(old_cfg['dir'])
    inventory = lambda: [dict(path=str(p.resolve()),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns)
        for p in sorted(rawdir.rglob('*')) if p.is_file()]
    before = inventory()
    assert before == r.read(r.BASE/'inputs.json')['inventory'] and len(before) == 299
    out.mkdir()
    cfg = dict(old_cfg, observe=False, out=str(out/'output'))
    r.save(out/'config.json', cfg)
    paths = [Path(__file__), HERE/'coarse-ablation-plan.md', HERE/'render.py', core,
        prior/'completion.json', prior/'on/config.json', prior/'on/invocation.json',
        r.BUILD/'sources.json', r.BUILD/'executable.json', Path(cfg['map']),
        ROOT/'experiments/m193c-output-grid/bounded-process.py',
        ROOT/'experiments/m12-scorecard/m12-harness.py']
    refs = [r.ref(p) for p in paths]
    r.save(out/'bindings.json', dict(inputs=refs, baseline=r.ref(master), executable=r.ref(exe), originals=before))
    fields = dict(invocation['environment'], STREHL_MATCHED_SOURCE_CONFIG=str(out/'config.json'),
        STREHL_PYRAMID_MEAN_COARSE='1')
    env, removed = b.clean_environment(fields.items())
    r.save(out/'invocation.json', dict(command=invocation['command'],environment=fields,removed_environment=removed))
    api = b.load_job_api(b.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    result = b.run(invocation['command'],env,ROOT,out/'process.log',api=api,
        wall_seconds=900,cpu_seconds=7200,committed_bytes=12<<30,log_bytes=16<<20)
    r.save(out/'process.json',result)
    assert result['exit_code'] == 0 and result['error'] is None and result['terminal_job_accounting'] and not result['cleanup_errors']
    assert 'test result: ok. 1 passed;' in (out/'process.log').read_text()
    assert inventory() == before and r.ref(master) == ready['full_image']
    assert all(r.ref(Path(v['path'])) == v for v in refs)
    assert r.ref(exe)['sha256'] == r.EXE_SHA
    receipt = r.read(out/'output/receipt.json')
    old_receipt = r.read(prior/'on/output/receipt.json')
    for key in ('tone_bits','wb_bits','levels','crop_quad_xywh','source_frame_count','native_map_reference'):
        assert receipt[key] == old_receipt[key]
    assert receipt['raw_count'] == receipt['gathered_count'] == receipt['merged_count'] == 0
    import numpy as np
    import tifffile
    from PIL import Image
    candidate = out/'output/replay.tiff'
    a, z = tifffile.imread(master), tifffile.imread(candidate)
    assert a.shape == z.shape == (4316,6476,3) and a.dtype == z.dtype == np.uint16
    differing = int(np.count_nonzero(a != z))
    assert differing > 0, 'Intervention inert; no causal inference possible'
    with tifffile.TiffFile(master) as f:
        icc = bytes(f.pages[0].tags[34675].value)
    with tifffile.TiffFile(candidate) as f:
        assert bytes(f.pages[0].tags[34675].value) == icc
    # Original bar/lettering protections, new defect sites, and pale control:
    # all fixed before the candidate. No crop selection from this image.
    sites = {v['name']:[v['x'],v['y'],v['width'],v['height']]
        for v in r.read(r.OLD/'slide2-source-config.json')['regions']}
    sites.update(r.read(ROOT/'experiments/slide2-focus-witness/render-1/broad-artifact-inspection/coordinates.json'))
    views = out/'views'; views.mkdir()
    for label, pixels in [('baseline',a),('candidate',z)]:
        full = Image.fromarray(((pixels.astype(np.uint32)+128)//257).astype(np.uint8))
        full.save(views/f'{label}-full.png',icc_profile=icc)
        for name,(x,y,w,h) in sites.items():
            full.crop((x,y,x+w,y+h)).save(views/f'{label}-{name}.png',icc_profile=icc)
        full.thumbnail((1800,1800),Image.Resampling.LANCZOS)
        full.save(views/f'{label}-overview.png',icc_profile=icc)
    r.save(out/'completion.json',dict(status='FIXED_COARSE_ABLATION_RENDERED',quality_gain_claim=False,
        baseline=r.ref(master),candidate=r.ref(candidate),baseline_rgb16_sha256=r.pixel_sha(a),
        candidate_rgb16_sha256=r.pixel_sha(z),different_rgb16_samples=differing,
        sites=sites,original_metadata_unchanged=True,bound_files_unchanged=True,
        interpretation='One fixed mean_coarse=1 observation. Fine AC and terminal policy held by code path, not measured coefficient hashes; final hull can couple the change. No sweep or default admission.'))
    print('COARSE_ABLATION_COMPLETE',flush=True)


if __name__ == '__main__':
    main()
