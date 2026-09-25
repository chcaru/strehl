"""Root-run fixed three-source counterfactual. This file does not build or choose donors."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('oracle_full_runner', ROOT/'experiments/full-stack-source-prior/runner.py')
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
c = base.c
TEST = 'merge_cmd::marigold_source_pure::three_source_oracle'
CONTROL = 'merge_cmd::marigold_source_pure::mask_and_support_controls'
SCOPE = 'Fixed manual source-purity counterfactual; no automatic merge, quality, or SOTA claim.'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def bindings():
    paths = {Path(r['path']) for r in base.bindings()}
    paths.update(HERE/n for n in ('oracle.rs', 'run.py', 'design.md'))
    return [c.ref(p.resolve()) for p in sorted(paths)]


def shared_build(path):
    sources = read(path/'sources.json')
    base.g.unchanged(sources)
    expected = {str((HERE/n).resolve()) for n in ('oracle.rs', 'run.py', 'design.md')}
    assert expected <= {r['path'] for r in sources}, 'Root build must bind all oracle files before compilation.'
    executable = path/'cli-tests.exe'
    assert c.ref(executable) == read(path/'executables.json')['cli-tests']
    assert 'Compiling strehl-cli' in (path/'process.log').read_text(encoding='utf-8', errors='replace')
    return executable, sources


def run_test(executable, name, out, fields, ignored=False):
    command = [str(executable), name, '--exact', '--nocapture', '--test-threads=1']
    if ignored:
        command.append('--ignored')
    result = base.job(command, fields, out, wall=120, cpu=900, gib=8)
    assert re.findall(r'test result: ok\. (\d+) passed;', (out/'process.log').read_text()) == ['1']
    return result


def validate(run):
    import numpy as np
    import tifffile
    receipt = read(run/'output/receipt.json')
    config = read(run/'config.json')
    assert receipt['status'] == 'COMPLETE_FIXED_THREE_DONOR_ORACLE'
    assert receipt['raw_decode_count'] == 3 and receipt['source_count'] == 488
    assert receipt['indices'] == [112, 152, 320]
    assert receipt['zero_mask_rgb16_and_icc_exact'] and receipt['baseline_cache_unchanged']
    for key in ('cache', 'full_receipt'):
        assert c.ref(Path(config[key]))['sha256'] == config[key+'_sha256'] == receipt[key+'_sha256']
    def image(path):
        with tifffile.TiffFile(path) as f:
            array = f.asarray()
            icc = bytes(f.pages[0].tags[34675].value)
            assert len(f.pages) == 1 and array.dtype == np.uint16 and array.ndim == 3 and array.shape[2] == 3
        return array, icc
    baseline, icc = image(run/'output/baseline.tiff')
    assert c.ref(run/'output/baseline.tiff')['sha256'] == receipt['baseline_sha256']
    assert hashlib.sha256(baseline.astype('<u2', copy=False).tobytes()).hexdigest() == receipt['baseline_rgb16_le_sha256']
    assert hashlib.sha256(icc).hexdigest() == receipt['icc_sha256']
    expected, expected_icc = image(Path(config['expected_current_tiff']))
    assert expected_icc == icc and np.array_equal(expected, baseline)
    del expected
    zero, zero_icc = image(run/'output/zero-placebo.tiff')
    assert zero_icc == icc and np.array_equal(zero, baseline)
    del zero
    assert receipt['rgb_support_native_xywh'] == [3196, 2966, 452, 452]
    x, y, w, h = receipt['rgb_support_native_xywh']
    for row in receipt['arms']:
        path = Path(row['file'])
        assert path.resolve().parent == (run/'output').resolve()
        assert c.ref(path)['sha256'] == row['sha256']
        candidate, ci = image(path)
        assert ci == icc and candidate.shape == baseline.shape
        assert hashlib.sha256(candidate.astype('<u2', copy=False).tobytes()).hexdigest() == row['rgb16_le_sha256']
        # Rectangular strips cover the entire outside, including unchanged controls.
        for a, b in ((candidate[:y], baseline[:y]), (candidate[y+h:], baseline[y+h:]),
                     (candidate[y:y+h, :x], baseline[y:y+h, :x]),
                     (candidate[y:y+h, x+w:], baseline[y:y+h, x+w:])):
            assert np.array_equal(a, b), 'Candidate escaped the actual MHC support.'
        assert row['outside_cfa_exact'] and row['outside_rgb_support_exact']
        del candidate
    assert [r['index'] for r in receipt['arms']] == [112, 152, 320]
    assert all(r['full_receipt_match'] and r['original_unchanged'] for r in receipt['sources'])
    return receipt


def views(run, out):
    import numpy as np
    import tifffile
    from PIL import Image
    receipt = validate(run)
    out.mkdir(exist_ok=False)
    records = []
    # Ring tiles overlap the core and reach the complete outer ring. Native
    # tiles never resample, and complete images accompany every donor arm.
    regions = {'fan-core': [3230, 3000, 384, 384],
               'ring-upper-left': [3184, 2954, 384, 384],
               'ring-lower-right': [3276, 3046, 384, 384],
               'rim-hairs-control': [1436, 1596, 384, 384],
               'inner-bud-control': [4320, 1540, 384, 384]}
    paths = [('baseline', run/'output/baseline.tiff')]
    paths += [(row['name'], Path(row['file'])) for row in receipt['arms']]
    for name, path in paths:
        with tifffile.TiffFile(path) as f:
            a = f.asarray()
            icc = bytes(f.pages[0].tags[34675].value)
        rgb8 = ((a.astype(np.uint32)+128)//257).astype(np.uint8)
        whole = Image.fromarray(rgb8)
        whole.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
        overview = out/(name+'-whole.png')
        whole.save(overview, icc_profile=icc)
        tiles = []
        for label, (x, y, w, h) in regions.items():
            assert w <= 384 and h <= 384 and x+w <= a.shape[1] and y+h <= a.shape[0]
            target = out/(name+'-'+label+'.png')
            Image.fromarray(rgb8[y:y+h, x:x+w]).save(target, icc_profile=icc)
            tiles.append(dict(name=label, native_xywh=[x, y, w, h], file=c.ref(target)))
        records.append(dict(name=name, master=c.ref(path), whole=c.ref(overview), tiles=tiles,
                            icc_sha256=hashlib.sha256(icc).hexdigest()))
    c.save(out/'receipt.json', dict(scope=SCOPE, full_images=records, receipt=c.ref(run/'output/receipt.json'),
                                  encoding='round RGB16/257, retain embedded ICC; whole views <=1617, native tiles 384 without resampling',
                                  visual_verdict=None))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('controls', 'run', 'views'))
    parser.add_argument('--out', type=Path, required=True)
    for name in ('build', 'controls', 'recipe', 'cache', 'full-receipt', 'baseline', 'run'):
        parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    if args.phase == 'views':
        assert args.run is not None
        views(args.run.resolve(), out)
        return
    assert args.build is not None
    executable, sources = shared_build(args.build.resolve())
    out.mkdir(exist_ok=False)
    if args.phase == 'controls':
        c.save(out/'bindings.json', dict(executable=c.ref(executable), sources=sources))
        run_test(executable, CONTROL, out, base.fields())
        base.g.unchanged(sources)
        c.save(out/'completion.json', dict(controls_passed=True, sources_unchanged=True, scope=SCOPE))
        return
    assert all(getattr(args, n) is not None for n in ('controls', 'recipe', 'cache', 'full_receipt', 'baseline'))
    controls = args.controls.resolve()
    assert read(controls/'bindings.json') == dict(executable=c.ref(executable), sources=sources)
    assert read(controls/'completion.json')['controls_passed']
    cp = read(controls/'process.json')
    assert cp['exit_code'] == 0 and cp['error'] is None and cp['terminal_job_accounting'] and not cp['cleanup_errors']
    recipe, cache, full_receipt, baseline = (getattr(args,n).resolve() for n in ('recipe','cache','full_receipt','baseline'))
    config = dict(schema=1, recipe=str(recipe), recipe_sha256=c.ref(recipe)['sha256'],
                  cache=str(cache), cache_sha256=c.ref(cache)['sha256'],
                  full_receipt=str(full_receipt), full_receipt_sha256=c.ref(full_receipt)['sha256'],
                  expected_current_tiff=str(baseline), expected_current_file_sha256=c.ref(baseline)['sha256'],
                  out_dir=str(out/'output'))
    c.save(out/'config.json', config)
    c.save(out/'bindings.json', dict(executable=c.ref(executable), sources=sources,
                                   controls=c.ref(controls/'completion.json'), config=c.ref(out/'config.json'), scope=SCOPE))
    fields = base.fields()
    fields.update(STREHL_MARIGOLD_SOURCE_PURE_CONFIG=str(out/'config.json'), STREHL_WARPMAP=read(recipe)['warp_map'])
    run_test(executable, TEST, out, fields, ignored=True)
    base.g.unchanged(sources)
    validate(out)
    c.save(out/'completion.json', dict(receipt=c.ref(out/'output/receipt.json'), sources_unchanged=True,
                                      raw_decode_count=3, paired_image_validation=True, scope=SCOPE))


if __name__ == '__main__':
    main()
