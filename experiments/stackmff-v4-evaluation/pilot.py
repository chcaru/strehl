"""Fixed three-source research pilot. Root owns fetch/inference execution.

fetch is explicit and separate; run never installs or downloads anything.
Root wraps run in the existing Windows job: 120s wall, 300s CPU, 8GiB, 8 threads.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMMIT = 'd104b3f51fc3933c7dbb2da27a21816b574914f3'
REMOTE = f'https://raw.githubusercontent.com/Xinzhe99/GMFF/{COMMIT}/'
FILES = {
    'README.md': (10384, '051077c2fb839fbac640b3c60591f5a4a091e4ac'),
    'inference_stage1.py': (10888, 'ced133fe8a8e4cac0f972efb7bd633a0fd6786ee'),
    'stackmffv4/network.py': (25187, 'f59f61dd549caa9c7e34505a8e58ded8e397641c'),
    'weights/stackmffv4.pth': (3972415, 'a452536a934e8cb4c72270f8738db060556a72d5'),
}
INPUT = ROOT / 'experiments/marigold-source-pure/run-1/output'
RECEIPT_SHA = '7c4c464bf275a77f7ec18b3336f2da05fb25cfa9d350d58988aa0d1f0a553c24'
INPUT_SHA = {
    'baseline': '19e657e419d52adf567ec86472f917ad9b9abfc9b0812131e9bba0eacbae462f',
    'donor-112': 'cefa0e089713e45233c1e4c86de85ed6b47c4ff53110c843a182032bf4467236',
    'donor-152': '4a070033b76391386d3704cb17d4acb441d6f12be7721d3cb5639a70174542fc',
    'donor-320': '54f3c192b44dc4c0572100656d5eade6defb4994808a3e1e64de71315cf7de48',
}
ICC_SHA = '238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
ORDINALS = [112, 152, 320]
XYWH = [3230, 3000, 384, 384]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def binding(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha(path))


def blob(data):
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()


def local_dir(path, fresh=False):
    path = path.resolve()
    require(path != HERE and HERE in path.parents, 'Output/upstream must be inside this experiment folder')
    if fresh:
        path.mkdir(parents=True, exist_ok=False)
    return path


def fetch(out):
    started = time.perf_counter()
    manifest = dict(commit=COMMIT, repository='https://github.com/Xinzhe99/GMFF',
                    licence='Official pinned README declares MIT; research-only files', files={})
    # Keep external research downloads out of ordinary Git staging.
    (out / '.gitignore').write_text('*\n', encoding='ascii')
    for name, (size, expected_blob) in FILES.items():
        url = REMOTE + name
        request = urllib.request.Request(url, headers={'User-Agent': 'strehl-research-readiness'})
        with urllib.request.urlopen(request, timeout=30) as response:
            require(response.geturl() == url, 'Unexpected upstream redirect')
            data = response.read(size + 1)
        require(len(data) == size and blob(data) == expected_blob, f'Pinned Git blob mismatch: {name}')
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        manifest['files'][name] = dict(binding(dest), url=url, git_blob=expected_blob)
    manifest.update(status='FETCHED_PINNED_RESEARCH_FILES_ONLY', seconds=time.perf_counter() - started)
    save(out / 'manifest.json', manifest)


def upstream_check(folder):
    manifest_path = folder / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(manifest['commit'] == COMMIT and set(manifest['files']) == set(FILES), 'Wrong upstream manifest')
    for name, (size, expected_blob) in FILES.items():
        path = folder / name
        data = path.read_bytes()
        require(len(data) == size and blob(data) == expected_blob, f'Changed upstream: {name}')
        require(sha(path) == manifest['files'][name]['sha256'], f'Changed manifest SHA: {name}')
    return binding(manifest_path), manifest


def select_rgb(rgb, indices):
    import numpy as np
    require(rgb.ndim == 4 and rgb.shape[-1] == 3, 'RGB stack shape')
    require(indices.dtype == np.int64 and indices.shape == rgb.shape[1:3], 'Index dtype/shape')
    require(int(indices.min()) >= 0 and int(indices.max()) < rgb.shape[0], 'Index range')
    yy, xx = np.indices(indices.shape)
    return rgb[indices, yy, xx].copy()


def mixed_map_control():
    import numpy as np
    yy, xx = np.indices((7, 11))
    inputs = np.empty((3, 7, 11, 3), dtype=np.uint16)
    for k in range(3):
        for c in range(3):
            inputs[k, :, :, c] = 1000 * k + 100 * c + 11 * yy + xx
    labels = ((2 * yy + xx) % 3).astype(np.int64)
    expected = np.empty((7, 11, 3), dtype=np.uint16)
    for y in range(7):
        for x in range(11):
            for c in range(3):
                expected[y, x, c] = 1000 * int(labels[y, x]) + 100 * c + 11 * y + x
    require(np.array_equal(select_rgb(inputs, labels), expected), 'Mixed source reconstruction failed')
    swapped_rejected = not np.array_equal(select_rgb(inputs[::-1], labels), expected)
    shifted_rejected = not np.array_equal(select_rgb(inputs, (labels + 1) % 3), expected)
    require(swapped_rejected and shifted_rejected, 'Source mapping destroyer not detected')
    return dict(mixed_source_identity=True, swapped_source_rejected=swapped_rejected,
                index_shift_rejected=shifted_rejected, all_three_labels_exercised=True)


def run(upstream, out):
    start = time.perf_counter()
    manifest_binding, manifest = upstream_check(upstream)
    for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
        os.environ[key] = '8'
    import numpy as np
    import cv2
    import tifffile
    from PIL import Image
    import torch
    import torchvision
    from torchvision import models
    cv2.setNumThreads(8)
    torch.set_num_threads(8)
    torch.set_num_interop_threads(1)
    require(torch.cuda.is_available(), 'CUDA unavailable; no fallback/install authorized')
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.cuda.reset_peak_memory_stats()
    receipt_path = INPUT / 'receipt.json'
    require(sha(receipt_path) == RECEIPT_SHA, 'Changed source-pure receipt')
    original = json.loads(receipt_path.read_text(encoding='utf-8'))
    require(original['core_native_xywh'] == XYWH and original['indices'] == ORDINALS, 'Wrong source gauge')
    require(original['native_dimensions'] == [6268, 4176] and original['source_count'] == 488, 'Wrong source stack')
    crops, input_bindings = {}, {}
    icc = None
    x, y, w, h = XYWH
    for name, expected in INPUT_SHA.items():
        path = INPUT / f'{name}.tiff'
        record = binding(path)
        require(record['sha256'] == expected, f'Changed source TIFF: {name}')
        with tifffile.TiffFile(path) as tif:
            require(len(tif.pages) == 1 and tif.pages[0].shape == (4176, 6268, 3), 'Wrong TIFF shape')
            require(tif.pages[0].dtype == np.uint16, 'Expected RGB16')
            profile = bytes(tif.pages[0].tags[34675].value)
        require(hashlib.sha256(profile).hexdigest() == ICC_SHA, 'Wrong ICC')
        if icc is not None:
            require(profile == icc, 'ICC differs across donors')
        icc = profile
        # Existing TIFFs are uncompressed: map and copy ONLY the bounded core.
        mm = tifffile.memmap(path, mode='r')
        crops[name] = np.array(mm[y:y+h, x:x+w], dtype=np.uint16, copy=True)
        del mm
        record['crop_rgb16_sha256'] = hashlib.sha256(crops[name].astype('<u2').tobytes()).hexdigest()
        input_bindings[name] = record
    rgb = np.stack([crops[f'donor-{k}'] for k in ORDINALS])
    gray = np.stack([cv2.cvtColor(a.astype(np.float32) / np.float32(65535), cv2.COLOR_RGB2GRAY) for a in rgb])
    require(gray.shape == (3, 384, 384) and gray.dtype == np.float32, 'No-resize input contract')
    require(np.isfinite(gray).all() and float(gray.min()) >= 0 and float(gray.max()) <= 1, 'Gray range')
    controls = dict(mixed_mapping=mixed_map_control())
    save(out / 'controls.json', controls)
    spec = importlib.util.spec_from_file_location('strehl_pinned_stackmff_v4_network', upstream / 'stackmffv4/network.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory = models.mobilenet_v3_large
    initialization_calls = []

    def no_download(*args, **kwargs):
        require(not args and kwargs == {'pretrained': True}, 'Unexpected pretrained constructor request')
        initialization_calls.append(dict(pretrained=True, substituted_weights=None))
        return factory(weights=None)

    try:
        models.mobilenet_v3_large = no_download
        model = module.StackMFF_V4()
    finally:
        models.mobilenet_v3_large = factory
    require(len(initialization_calls) == 1, 'Expected exactly one discarded pretrained initialization')
    weights = torch.load(upstream / 'weights/stackmffv4.pth', map_location='cpu', weights_only=True)
    require(isinstance(weights, dict) and weights and all(isinstance(k, str) and torch.is_tensor(v) for k, v in weights.items()), 'Unsupported safe checkpoint structure')
    state = {}
    for k, v in weights.items():
        name = k[7:] if k.startswith('module.') else k
        require(name not in state, 'Duplicate checkpoint key after module prefix removal')
        require(not v.is_floating_point() or bool(torch.isfinite(v).all()), f'Nonfinite checkpoint state: {name}')
        state[name] = v
    incompat = model.load_state_dict(state, strict=True)
    require(not incompat.missing_keys and not incompat.unexpected_keys, 'Incomplete strict state load')
    loaded = model.state_dict()
    require(set(loaded) == set(state) and all(torch.equal(loaded[k], state[k]) for k in state), 'Loaded model differs from complete checkpoint')
    model = model.float().eval().cuda()
    require(all(not p.is_floating_point() or p.dtype == torch.float32 for p in model.state_dict().values()), 'Non-f32 floating model state')
    calls = []
    logit_checks = []

    def finite_logits(_module, inputs):
        logits = inputs[0]
        require(tuple(logits.shape) == (1, 3, 384, 384) and bool(torch.isfinite(logits).all()), 'Nonfinite or malformed pre-argmax logits')
        logit_checks.append(dict(shape=list(logits.shape), finite=True))
        return None

    # A validity observer must also prove identical output with the observer off.
    logit_hook = model.focus_map_creation.register_forward_pre_hook(finite_logits)

    def infer(name, inputs):
        tensor = torch.from_numpy(np.ascontiguousarray(inputs)).unsqueeze(0).cuda()
        torch.cuda.synchronize()
        t = time.perf_counter()
        with torch.no_grad():
            fused_t, indices_t = model(tensor)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - t
        require(tuple(fused_t.shape) == (1, 1, 384, 384) and tuple(indices_t.shape) == (1, 384, 384), 'Unexpected model output shape; resizing prohibited')
        require(indices_t.dtype == torch.int64 and fused_t.dtype == torch.float32, 'Unexpected output dtype')
        indices = indices_t[0].cpu().numpy().copy()
        fused = fused_t[0, 0].cpu().numpy().copy()
        require(np.isfinite(fused).all() and int(indices.min()) >= 0 and int(indices.max()) < 3, 'Nonfinite/out-of-range model output')
        yy, xx = np.indices((384, 384))
        require(np.array_equal(fused, inputs[indices, yy, xx]), 'Model grayscale is not exact selected input')
        calls.append(dict(name=name, synchronized_forward_seconds=elapsed,
                          selected_grayscale_exact=True, map_dtype=str(indices.dtype),
                          map_min=int(indices.min()), map_max=int(indices.max())))
        return fused, indices

    duplicate_gray = np.repeat(gray[:1], 3, axis=0)
    dup_fused, dup_indices = infer('duplicate-donor-112', duplicate_gray)
    require(np.array_equal(dup_fused, gray[0]), 'Duplicate grayscale fidelity')
    require(np.array_equal(select_rgb(np.repeat(rgb[:1], 3, axis=0), dup_indices), rgb[0]), 'Duplicate RGB16 fidelity')
    controls['duplicate'] = dict(grayscale_exact=True, rgb16_exact=True)
    const_rgb = np.full_like(rgb, 16384)
    const_gray = np.stack([cv2.cvtColor(a.astype(np.float32) / np.float32(65535), cv2.COLOR_RGB2GRAY) for a in const_rgb])
    const_fused, const_indices = infer('constant', const_gray)
    require(np.array_equal(const_fused, const_gray[0]) and np.array_equal(select_rgb(const_rgb, const_indices), const_rgb[0]), 'Constant fidelity')
    controls['constant'] = dict(grayscale_exact=True, rgb16_exact=True)
    save(out / 'controls.json', controls)
    fused, indices = infer('fixed-112-152-320', gray)
    candidate = select_rgb(rgb, indices)
    reversed_fused, reversed_indices = infer('fixed-reversal-320-152-112', gray[::-1])
    reverse_rgb = select_rgb(rgb[::-1], reversed_indices)
    mapped_back = 2 - reversed_indices
    controls['permutation'] = dict(map_disagreement_pixels=int(np.count_nonzero(mapped_back != indices)),
                                  rgb_disagreement_pixels=int(np.count_nonzero(np.any(reverse_rgb != candidate, axis=2))),
                                  max_rgb16_difference=int(np.max(np.abs(reverse_rgb.astype(np.int32) - candidate.astype(np.int32)))),
                                  grayscale_disagreement_pixels=int(np.count_nonzero(reversed_fused != fused)),
                                  authoritative_order=ORDINALS, quality_authority=False)
    require(len(logit_checks) == 4, 'Finite-logit observer did not exercise all four calls')
    logit_hook.remove()
    off_fused, off_indices = infer('fixed-primary-logit-observer-off', gray)
    off_rgb = select_rgb(rgb, off_indices)
    require(np.array_equal(off_fused, fused) and np.array_equal(off_indices, indices)
            and np.array_equal(off_rgb, candidate), 'Read-only logit observer altered actual output')
    controls['logit_observer'] = dict(calls=logit_checks, on_off_grayscale_exact=True,
                                    on_off_indices_exact=True, on_off_rgb16_exact=True,
                                    on_grayscale_sha256=hashlib.sha256(fused.tobytes()).hexdigest(),
                                    off_grayscale_sha256=hashlib.sha256(off_fused.tobytes()).hexdigest(),
                                    on_indices_sha256=hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest(),
                                    off_indices_sha256=hashlib.sha256(off_indices.astype('<i8').tobytes()).hexdigest(),
                                    on_rgb16_sha256=hashlib.sha256(candidate.astype('<u2').tobytes()).hexdigest(),
                                    off_rgb16_sha256=hashlib.sha256(off_rgb.astype('<u2').tobytes()).hexdigest())
    save(out / 'controls.json', controls)
    arrays = dict(source_indices=indices, source_ordinals=np.array(ORDINALS, dtype=np.int64)[indices],
                  model_grayscale=fused, model_input_grayscale=gray,
                  reversed_source_indices=reversed_indices, reversed_source_indices_original_order=mapped_back,
                  reversed_model_grayscale=reversed_fused)
    for name, data in arrays.items():
        np.save(out / f'{name}.npy', data, allow_pickle=False)
    pictures = dict(crops, candidate=candidate, reversed_candidate=reverse_rgb)
    for name, pixels in pictures.items():
        tifffile.imwrite(out / f'{name}.tiff', pixels, photometric='rgb', metadata=None,
                         extratags=[(34675, 'B', len(icc), icc, False)])
        display = np.rint(pixels.astype(np.float32) / 257).astype(np.uint8)
        Image.fromarray(display).save(out / f'{name}.png', icc_profile=icc)
    palette = np.array([[63, 195, 110], [82, 134, 238], [236, 91, 72]], dtype=np.uint8)
    Image.fromarray(palette[indices]).save(out / 'source-map.png')
    torch.cuda.synchronize()
    outputs = {p.name: binding(p) for p in sorted(out.iterdir()) if p.is_file()}
    receipt = dict(status='COMPLETE_FIXED_THREE_SOURCE_OBSERVATION', schema=1, commit=COMMIT,
                   upstream_manifest=manifest_binding, upstream_files=manifest['files'],
                   source_receipt=binding(receipt_path), input_files=input_bindings,
                   crop_native_xywh=XYWH, source_pure_rgb_interior_xywh=[2, 2, 380, 380],
                   reference_ordinal=244, source_ordinals=ORDINALS, source_stack_count=488,
                   model_input_count=3, precision='float32; no autocast or TF32',
                   grayscale='RGB16 /65535 then cv2.COLOR_RGB2GRAY; official 8-bit loader quantization intentionally omitted',
                   resizing=False, additional_tone=False, source_reconstruction='exact RGB16 vector copy at the same pixel',
                   resolved_development=original['resolved_development'], icc_sha256=ICC_SHA,
                   safe_load_weights_only=True, strict_complete_state_load=True, checkpoint_state_keys=len(state),
                   checkpoint_finite=True,
                   initialization_suppression=initialization_calls, constructor_restored=models.mobilenet_v3_large is factory,
                   torch_version=torch.__version__, torchvision_version=torchvision.__version__,
                   opencv_version=cv2.__version__, numpy_version=np.__version__,
                   gpu=torch.cuda.get_device_name(), cuda_version=torch.version.cuda,
                   cpu_threads=torch.get_num_threads(), gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                   gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved(), calls=calls, controls=controls,
                   outputs=outputs, total_seconds=time.perf_counter() - start,
                   limitations=['Three selected sources, not all488; no full output or SOTA claim',
                                'Outer2 RGB border may contain MHC blend-ring support',
                                'Crop boundary lacks full-image model context; inner380 is not an exact model-context boundary',
                                'Hard source selection may increase grain/seams; controls do not establish photographic quality'],
                   visual_verdict=None)
    save(out / 'receipt.json', receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['fetch', 'run'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--upstream', type=Path)
    args = parser.parse_args()
    out = local_dir(args.out, fresh=True)
    save(out / 'started.json', dict(phase=args.phase, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                  runner=binding(Path(__file__)), command=sys.argv,
                                  independent_plan=binding(HERE / 'independent-plan.md'),
                                  decision=binding(HERE / 'decision.md'), readiness=binding(HERE / 'readiness.md')))
    try:
        if args.phase == 'fetch':
            require(args.upstream is None, 'fetch has no upstream argument')
            fetch(out)
        else:
            require(args.upstream is not None, 'run requires the explicit prior fetch directory')
            run(local_dir(args.upstream), out)
    except Exception as error:
        save(out / 'refusal.json', dict(status='REFUSED', type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
