"""Root-executed omitted opal comparison; reuses the actual frozen native/writer paths."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RAW = Path('D:/personal/macro/minerals/rainbow-opal-cabochon/103MSDCF')
MAP = ROOT/'outputs/minerals-september24/103msdcf/alignment.txt'
CROP = [60, 40, 3396, 2264]
NATIVE = [6792, 4528]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


f = load('opal_full_cache', ROOT/'experiments/full-stack-source-prior/runner.py')
h = load('opal_highlight_replay', ROOT/'experiments/highlight-rendering/run.py')
g, c = f.g, f.c


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def shared_build(path):
    exe, sources = h.shared_build(path)
    own = [c.ref(HERE/name) for name in ('run.py', 'design.md', 'targets.json', 'integration.md')]
    # These are runtime orchestration bindings, not additions to the Rust binary.
    sources += own
    for target in read(HERE/'targets.json')['targets']:
        assert c.ref(ROOT/target['witness'])['sha256'] == target['sha256']
    return exe, sources


def rgb(path):
    import numpy as np
    import tifffile
    with tifffile.TiffFile(path) as tf:
        assert len(tf.pages) == 1
        pixels = tf.asarray()
        profile = bytes(tf.pages[0].tags[34675].value)
    assert pixels.dtype == np.uint16 and pixels.shape == (NATIVE[1], NATIVE[0], 3) and profile
    return pixels, profile


def cache(args, out, exe, sources):
    import numpy as np
    production = args.production.resolve()
    done = read(production/'completion.json')
    invocation = read(production/'invocation.json')
    order = read(production/'input-order.json')
    process = read(production/'render-process.json')
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    assert done['frames'] == 155 and done['native_dimensions'] == NATIVE
    assert done['crop_quad_xywh'] == CROP and done['original_bytes_and_metadata_unchanged']
    assert invocation['frames'] == 155 and invocation['executable'] == done['executable']
    assert c.ref(Path(done['executable']['path'])) == done['executable']
    # A fresh shared build may add test-only instrumentation. Accept either its
    # production binary or the separately pinned shipped numerical-repair build.
    shipped = read(ROOT/'scripts/native-build.json')['executable']
    shipped_path = Path(shipped['path'])
    if not shipped_path.is_absolute():
        shipped_path = ROOT/shipped_path
    assert c.ref(shipped_path)['sha256'] == shipped['sha256']
    allowed = {shipped['sha256'], c.ref(args.build.resolve()/'strehl.exe')['sha256']}
    assert done['executable']['sha256'] in allowed, 'fresh checked current production baseline required'
    assert len(invocation['commands']) == 1 and invocation['commands'][0][0] == 'render'
    command = invocation['commands'][0][1]
    assert command[1:3] == ['stack', str(RAW.resolve())] and '--exposure=-0.3' in command
    for flag, value in [('--merge', 'pyramid'), ('--pyramid-bands', '7'), ('--pyramid-gate', '2'),
                        ('--pyramid-exponent', '2'), ('--pyramid-sharpen', '1.4'),
                        ('--pyramid-select', 'soft'), ('--pyramid-base', 'mean'),
                        ('--resampler', 'catmull-rom'), ('--cover', 'crop')]:
        assert command[command.index(flag)+1] == value
    assert '--srgb' in command and '--demosaic' in command
    assert invocation['environment'] == dict(f.fields(), STREHL_WARPMAP=str(MAP.resolve()))
    assert done['warp_map'] == c.ref(MAP) == invocation['existing_map']
    assert len(order) == 155 and [r['index'] for r in order] == list(range(155))
    paths = [Path(r['path']) for r in order]
    assert paths == [RAW.resolve()/f'DSC{i:05d}.ARW' for i in range(46, 201)]
    assert all(p.stat().st_size == r['bytes'] and p.stat().st_mtime_ns == r['mtime_ns'] for p, r in zip(paths, order))
    master = production/'stack-master.tiff'
    assert c.ref(master) == done['master']
    pixels, icc = rgb(master)
    pixel_hash = hashlib.sha256(pixels.astype('<u2', copy=False).tobytes()).hexdigest()
    recipe = dict(schema=1, mode='current', stack_name='103MSDCF',
        inputs=[dict(index=r['index'], path=r['path'], identity_name=Path(r['path']).name,
                     bytes=r['bytes'], sha256=r['sha256']) for r in order],
        warp_map=str(MAP.resolve()), warp_map_sha256=c.ref(MAP)['sha256'], expected_reference=77,
        expected_full_geometry=[3516,2344], expected_crop=CROP,
        expected_baseline=str(master), expected_baseline_sha256=done['master']['sha256'],
        expected_baseline_pixels_sha256=pixel_hash, expected_camera='ILCE-7CM2',
        expected_iso=100.0, exposure_stops=-0.3, tone_policy='automatic-per-arm-current-writer')
    refs = [c.ref(production/name) for name in ('completion.json', 'invocation.json', 'input-order.json',
             'render-process.json', 'render.log', 'stack-master.tiff')]
    refs += [c.ref(MAP), c.ref(ROOT/'scripts/native-build.json')]
    c.save(out/'recipe.json', recipe)
    config = dict(recipe, phase='full', out_dir=str(out/'output'))
    c.save(out/'config.json', config)
    c.save(out/'bindings.json', dict(executable=c.ref(exe), sources=sources, production=refs,
        scope='Current complete native cache, bound to newly rendered production; no prior/candidate merge.'))
    env = f.fields()
    env.update(STREHL_WARPMAP=recipe['warp_map'], STREHL_FULL_STACK_SOURCE_PRIOR_CONFIG=str(out/'config.json'))
    g.job([str(exe), f.TEST, '--exact', '--ignored', '--nocapture', '--test-threads=1'],
          env, out, wall=900, cpu=6000, gib=12)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == ['1']
    receipt = f.validate(out, recipe, 'full')
    actual, actual_icc = rgb(out/'output/baseline.tiff')
    assert np.array_equal(actual, pixels) and actual_icc == icc
    prodlog = (production/'render.log').read_text(encoding='utf-8', errors='replace')
    plan = re.search(r'memory plan\s*:\s*(\d+) canonical chunks,.*?(\d+) execution threads', prodlog)
    assert plan and [int(v) for v in plan.groups()] == [receipt['plan']['canonical_chunks'], receipt['threads']]
    assert all(row['source_unchanged'] for row in receipt['frames'])
    g.unchanged(sources + refs)
    c.save(out/'completion.json', dict(phase='full', source_count=155, current_production_rgb16_icc_exact=True,
        canonical_chunk_count_and_threads_exact=True, actual_per_source_fields_retained=True,
        receipt=c.ref(out/'output/receipt.json'), production_completion=c.ref(production/'completion.json'),
        sources_and_production_unchanged=True, photographic_verdict=None))


def replay(args, out, exe, sources):
    run = args.cache_run.resolve()
    bound, done = read(run/'bindings.json'), read(run/'completion.json')
    assert bound['sources'] == sources and bound['executable'] == c.ref(exe)
    assert done['current_production_rgb16_icc_exact'] and done['sources_and_production_unchanged']
    assert done['receipt'] == c.ref(run/'output/receipt.json')
    g.unchanged(bound['production'])
    recipe = f.recipe(run/'recipe.json')
    f.validate(run, recipe, 'full')
    args.cache = run/'output/baseline-cache.json'
    args.current = Path(recipe['expected_baseline'])
    c.save(out/'opal-context.json', dict(cache_completion=c.ref(run/'completion.json'),
        cache_recipe=c.ref(run/'recipe.json'), targets=c.ref(HERE/'targets.json')))
    h.run_replay(args, out, exe, sources)


def views(args, out):
    import numpy as np
    from PIL import Image
    run = args.run.resolve()
    h.views(run, out)
    target_spec = read(HERE/'targets.json')
    rows = []
    receipt = read(run/'output/receipt.json')
    assert [receipt['width'], receipt['height']] == NATIVE
    for arm in h.ARMS:
        master = run/'output'/f'{arm}.tiff'
        pixels, icc = rgb(master)
        for target in target_spec['targets']:
            x, y, w, height = target['native_xywh']
            assert w <= 400 and height <= 400 and 0 <= x < x+w <= NATIVE[0] and 0 <= y < y+height <= NATIVE[1]
            patch = ((pixels[y:y+height,x:x+w].astype(np.uint32)+128)//257).astype(np.uint8)
            dest = out/f'{arm}-{target["name"]}-native.png'
            Image.fromarray(patch).save(dest, icc_profile=icc)
            rows.append(dict(arm=arm, target=target['name'], native_xywh=target['native_xywh'], file=c.ref(dest)))
    c.save(out/'native-views.json', dict(targets=c.ref(HERE/'targets.json'), views=rows,
        display='Exact native crop; rounded u16/257, shared ICC, no resampling or contrast normalization.',
        visual_verdict=None))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('cache', 'controls', 'replay', 'views'))
    parser.add_argument('--out', type=Path, required=True)
    for name in ('build', 'production', 'controls', 'cache-run', 'run'):
        parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    if args.phase == 'views':
        assert args.run
        out.mkdir()
        views(args, out)
        return
    assert args.build
    exe, sources = shared_build(args.build.resolve())
    if args.phase == 'cache':
        assert args.production
    if args.phase == 'replay':
        assert args.controls and args.cache_run
    out.mkdir()
    if args.phase == 'cache':
        cache(args, out, exe, sources)
    elif args.phase == 'controls':
        h.run_controls(out, exe, sources)
    else:
        replay(args, out, exe, sources)


if __name__ == '__main__':
    main()
