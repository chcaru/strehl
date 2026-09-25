"""Root-only bounded controls and full merged-cache rendering; no RAW reads."""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('highlight_rendering_bounds', ROOT/'experiments/cross-scale-source-prior/run.py')
g = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = g
spec.loader.exec_module(g)
c = g.c
FILTER = 'image_out::highlight_rendering::independent_controls::'
TEST = 'merge_cmd::highlight_rendering_replay::complete_cached_factorial'
ARMS = ('current', 'sensor-rolloff-off', 'shoulder', 'both')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def shared_build(path):
    sources = read(path/'sources.json')
    g.unchanged(sources)
    required = [HERE/'image-out-bridge.rs', HERE/'merge-replay.rs', HERE/'independent-controls.rs',
                ROOT/'crates/strehl-cli/src/image_out.rs', ROOT/'crates/strehl-cli/src/merge_cmd.rs',
                ROOT/'experiments/full-stack-source-prior/adapter.rs']
    assert {str(p.resolve()) for p in required} <= {r['path'] for r in sources}, 'shared build did not bind new hooks and both adapters'
    log = (path/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log, 'fresh shared CLI compilation required'
    exe = path/'cli-tests.exe'
    assert c.ref(exe) == read(path/'executables.json')['cli-tests']
    own = [c.ref(HERE/name) for name in ('run.py', 'design.md', 'integration.md', 'independent-plan.md')]
    return exe, sources + own


def run_controls(out, exe, sources):
    c.save(out/'bindings.json', dict(executable=c.ref(exe), sources=sources))
    g.job([str(exe), FILTER, '--nocapture', '--test-threads=1'],
          dict(RAYON_NUM_THREADS='8'), out, wall=90, cpu=240, gib=3)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == ['4']
    g.unchanged(sources)
    c.save(out/'completion.json', dict(controls_executed=4, sources_unchanged=True,
        scope='Structural and behavioral commissioning only; no photographic quality pass.'))


def check_controls(path, exe, sources):
    assert read(path/'bindings.json') == dict(executable=c.ref(exe), sources=sources)
    done = read(path/'completion.json')
    assert done['controls_executed'] == 4 and done['sources_unchanged']
    process = read(path/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting']
    assert not process['cleanup_errors']
    invocation = read(path/'invocation.json')
    assert invocation['command'] == [str(exe), FILTER, '--nocapture', '--test-threads=1']


def run_replay(args, out, exe, sources):
    assert args.controls and args.cache and args.current
    check_controls(args.controls.resolve(), exe, sources)
    cache, current = args.cache.resolve(), args.current.resolve()
    meta = read(cache)
    assert meta['phase'] == 'full', 'cost/subset cache is not a photograph'
    binary = cache.parent/meta['binary']
    assert binary.parent.resolve() == cache.parent
    refs = [c.ref(p) for p in (cache, binary, current)]
    assert refs[1]['sha256'] == meta['binary_sha256']
    config = dict(schema=1, cache=str(cache), expected_current_tiff=str(current),
        expected_current_file_sha256=refs[2]['sha256'], out_dir=str(out/'output'))
    c.save(out/'config.json', config)
    c.save(out/'bindings.json', dict(executable=c.ref(exe), sources=sources, inputs=refs,
        controls=c.ref(args.controls.resolve()/'completion.json')))
    g.job([str(exe), TEST, '--exact', '--ignored', '--nocapture', '--test-threads=1'],
        dict(RAYON_NUM_THREADS='8', STREHL_HIGHLIGHT_RENDERING_CONFIG=str(out/'config.json')),
        out, wall=240, cpu=1200, gib=8)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == ['1']
    assert 'HIGHLIGHT_RENDERING_COMPLETE ' in log
    receipt = read(out/'output/receipt.json')
    assert receipt['status'] == 'COMPLETE_CACHED_FACTORIAL' and receipt['raw_reads'] == 0
    assert receipt['observer_on_off_file_exact'] and receipt['retained_current_pixels_and_icc_exact']
    assert receipt['merged_planes_unchanged'] and [r['arm'] for r in receipt['arms']] == list(ARMS)
    assert all(row['resolved_development'] == receipt['arms'][0]['resolved_development'] for row in receipt['arms'])
    g.unchanged(sources + refs)
    c.save(out/'completion.json', dict(receipt=c.ref(out/'output/receipt.json'), sources_unchanged=True,
        inputs_unchanged=True, whole_output_arms=list(ARMS), visual_verdict=None))


def views(run, out):
    import hashlib
    import numpy as np
    import tifffile
    from PIL import Image
    done = read(run/'completion.json')
    receipt_path = run/'output/receipt.json'
    assert done['receipt'] == c.ref(receipt_path)
    receipt = read(receipt_path)
    output = []
    for row in receipt['arms']:
        source = run/'output'/row['file']
        assert c.ref(source)['sha256'] == row['file_sha256']
        with tifffile.TiffFile(source) as tf:
            assert len(tf.pages) == 1
            pixels = tf.asarray()
            icc = bytes(tf.pages[0].tags[34675].value)
        assert pixels.dtype == np.uint16 and pixels.shape == (receipt['height'], receipt['width'], 3)
        assert hashlib.sha256(pixels.astype('<u2', copy=False).tobytes()).hexdigest() == row['rgb16_le_sha256']
        assert hashlib.sha256(icc).hexdigest() == receipt['icc_sha256']
        image = Image.fromarray(((pixels.astype(np.uint32)+128)//257).astype(np.uint8))
        native = out/(row['arm']+'-full.png')
        image.save(native, icc_profile=icc)
        image.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
        overview = out/(row['arm']+'-overview.png')
        image.save(overview, icc_profile=icc)
        with Image.open(native) as check:
            assert check.size == (receipt['width'], receipt['height']) and check.info['icc_profile'] == icc
        output.append(dict(arm=row['arm'], master=c.ref(source), native_png=c.ref(native),
            whole_overview=c.ref(overview), display='rounded u16/257, shared ICC, no contrast normalization'))
    c.save(out/'views.json', dict(receipt=c.ref(receipt_path), whole_outputs=output, visual_verdict=None))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('controls', 'replay', 'views'))
    parser.add_argument('--out', type=Path, required=True)
    for name in ('build', 'controls', 'cache', 'current', 'run'):
        parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    if args.phase == 'views':
        assert args.run
        out.mkdir()
        views(args.run.resolve(), out)
        return
    assert args.build
    exe, sources = shared_build(args.build.resolve())
    out.mkdir()
    if args.phase == 'controls':
        run_controls(out, exe, sources)
    else:
        run_replay(args, out, exe, sources)


if __name__ == '__main__':
    main()
