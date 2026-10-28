"""Pinned StackMFF V3 soft RGB comparison, bounded only in spatial extent.

This consumes developed RGB16, not RAW. All sources attend jointly. The model,
two inference scales and post-crop smoothing are unchanged. No downloads occur.
"""
from pathlib import Path
import hashlib
import importlib
import importlib.util
import sys
import time

import cv2
import numpy as np
import torch


COMMIT = '6e1d7211f7634f60245706ebe3b839b320df9d00'
CORE = 256
HALO = 128
GPU_LIMIT = 24 << 30
PINNED = {
    'LICENSE': '90bcebd500cc79b5036fdae9bc054a3c8196a29bbb76905f5c729063e6050c6b',
    'THIRD_PARTY_NOTICES.md': '2a54830065f8f467c9a851a3badd9e2a1f3ba751c73c504de97f77494948ac57',
    'README.md': '9047c0875adeedabb0e460e2925292f40da64f4063546b2075fc968f07a6873e',
    'fuse.py': '99e247a4267f26d100b1738e1524d1115c9ad82b1c5ddbe84b957418cac31731',
    'stackmff_v3/__init__.py': '987d85714e3b7849a2d0e0e5750d501b7cfdc146d276d7a2c7de660879940126',
    'stackmff_v3/model_io.py': 'b26a2ec05f25bf14bce37de459308284ef9ae4c4d913fca1533456308717bdc2',
    'stackmff_v3/network.py': '849d5c4eed3e2a1c8f8b111b96f27ac35493920bf1da7f531977878346e4b198',
    'weights/stackmff_v3_final.pth': '39b2ea3738e8fea1676c379238d6be81a87988fc9952dbd6ac3825d5d7249f46',
}
FINAL_ARGS = {
    'arch': 'loop', 'C1': 48, 'C2': 96, 'heads': [3, 6], 'window': 8,
    'mlp_ratio': 2.0, 'inter_pool': 2, 'kmax': 1, 'k_eval': 1,
    'share_fine': False, 'intra': 'attn', 'layer_pos': False, 'loss': 'ce',
    'single_scale': True, 'fine_head': False,
}


def _bindings(root):
    result = {}
    for name, expected in PINNED.items():
        path = root / name
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ValueError(f'upstream binding changed: {name}')
        result[name] = dict(sha256=actual, bytes=len(data))
    return result


class ModelHandle:
    def __init__(self, model, upstream, fuse_module, network, device, bindings):
        self.model = model
        self.upstream = upstream
        self.fuse_module = fuse_module
        self.network = network
        self.device = device
        self.bindings = bindings


def load_model(upstream, device='cuda'):
    """Safe weights-only load of the exact released architecture/checkpoint."""
    root = Path(upstream).resolve()
    bindings = _bindings(root)
    for name in ('stackmff_v3', 'stackmff_v3.network', 'stackmff_v3.model_io'):
        previous = sys.modules.get(name)
        if previous is not None:
            location = Path(previous.__file__).resolve()
            if not location.is_relative_to(root):
                raise ValueError(f'foreign upstream module already imported: {name}')
    sys.path.insert(0, str(root))
    try:
        io = importlib.import_module('stackmff_v3.model_io')
        network = importlib.import_module('stackmff_v3.network')
        spec = importlib.util.spec_from_file_location('_strehl_pinned_stackmff_fuse', root / 'fuse.py')
        fuse_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fuse_module)
    finally:
        sys.path.pop(0)
    if io.FINAL_ARGS != FINAL_ARGS:
        raise ValueError('unexpected upstream architecture defaults')
    ck = torch.load(root / 'weights/stackmff_v3_final.pth', map_location='cpu', weights_only=True)
    if not isinstance(ck, dict) or not isinstance(ck.get('args'), dict) or 'model' not in ck:
        raise ValueError('expected released model+args checkpoint')
    args = dict(FINAL_ARGS, **ck['args'])
    if args != FINAL_ARGS:
        raise ValueError(f'checkpoint architecture differs: {args}')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    model = io.build(args)
    model.load_state_dict(ck['model'], strict=True)
    model.cur_K = 1
    model.adaptive = False
    model.ms_scales = (1.0, 0.75)
    dev = torch.device(device)
    if dev.type not in ('cpu', 'cuda'):
        raise ValueError('only explicit CPU/CUDA f32 execution is supported')
    model = model.to(device=dev, dtype=torch.float32).eval()
    if any(p.dtype != torch.float32 for p in model.parameters()):
        raise ValueError('non-f32 model parameter')
    return ModelHandle(model, root, fuse_module, network, dev, bindings)


def _integer_tuple(value, count, name):
    if len(value) != count or any(type(x) is not int for x in value):
        raise ValueError(f'{name} requires {count} Python integers')
    return tuple(value)


def _pad_index(index, length, mode):
    if index < length:
        return index
    return 2 * length - 2 - index if mode == 'reflect' else length - 1


def tile_spec(core_rect_xywh, full_wh, diagnostic_halo=None):
    """Fixed core<=256, halo128, globally aligned contexts; zero-halo foil only.

    For large dimensions this deliberately supports the pinned photograph and
    controls (global padded extents divisible256), not arbitrary image shapes.
    Small dimensions use their entire globally padded extent.
    """
    x, y, width, height = _integer_tuple(core_rect_xywh, 4, 'core')
    full_w, full_h = _integer_tuple(full_wh, 2, 'full_wh')
    if min(full_w, full_h, width, height) <= 0 or max(width, height) > CORE:
        raise ValueError('invalid image/core extent')
    if min(x, y) < 0 or x + width > full_w or y + height > full_h:
        raise ValueError('core outside physical image')
    if x % 128 or y % 128:
        raise ValueError('core origin must preserve the fixed128-pixel global lattice')
    if diagnostic_halo not in (None, 0):
        raise ValueError('the only diagnostic override is zero halo')
    halo = HALO if diagnostic_halo is None else 0
    padded_w, padded_h = ((full_w + 63) // 64) * 64, ((full_h + 63) // 64) * 64
    mode = 'reflect' if padded_w - full_w < full_w and padded_h - full_h < full_h else 'replicate'
    axes = []
    for start, count, original, padded in ((x, width, full_w, padded_w),
                                          (y, height, full_h, padded_h)):
        context_count = min(CORE + 2 * halo, padded)
        if padded > context_count and padded % 256:
            raise ValueError('large global padded dimensions must be divisible256')
        context_start = min(max(start - halo, 0), padded - context_count)
        if context_start % 128:
            raise ValueError('context origin breaks global inference phase')
        if not (context_start <= start and start + count <= context_start + context_count):
            raise ValueError('core outside context')
        mapped = [_pad_index(k, original, mode)
                  for k in range(context_start, context_start + context_count)]
        if min(mapped) < 0 or max(mapped) >= original:
            raise ValueError('unsupported global padding extent')
        axes.append((context_start, context_count, min(mapped), max(mapped) - min(mapped) + 1))
    ax, ay = axes
    return dict(schema=1, core_rect=[x, y, width, height], full_wh=[full_w, full_h],
                padded_wh=[padded_w, padded_h], global_pad_mode=mode,
                context_rect=[ax[0], ay[0], ax[1], ay[1]],
                read_rect=[ax[2], ay[2], ax[3], ay[3]], plugin_halo=halo,
                diagnostic_only=diagnostic_halo is not None)


def _rgb_input(rgb):
    if not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint16 or rgb.ndim != 4:
        raise ValueError('input must be uint16 N,H,W,3 RGB')
    if rgb.shape[-1] != 3 or not (1 <= rgb.shape[0] <= 299) or min(rgb.shape[1:3]) <= 0:
        raise ValueError('invalid source/channel/spatial extent')
    return rgb


def _probabilities(p, rgb):
    if not isinstance(p, np.ndarray) or p.dtype != np.float32 or p.shape != rgb.shape[:3]:
        raise ValueError('probabilities must be f32 N,H,W matching RGB')
    if not np.isfinite(p).all() or p.min() < 0 or p.max() > np.float32(1.000001):
        raise ValueError('invalid source probabilities')
    error = float(np.max(np.abs(p.sum(axis=0) - np.float32(1))))
    if error > 5e-5:
        raise ValueError(f'probability normalization error: {error}')
    return error


def fuse_rgb16(probabilities, rgb16):
    """Producing composer: same f32 source sum and ties-to-even u16 as upstream.

    Returns (normalized_f32_RGB, uint16_RGB). One probability is shared by RGB.
    """
    rgb = _rgb_input(rgb16)
    _probabilities(probabilities, rgb)
    h, w = rgb.shape[1:3]
    fused = np.empty((h, w, 3), dtype=np.uint16)
    continuous = np.empty((h, w, 3), dtype=np.float32)
    for y in range(0, h, 256):
        values = (probabilities[:, y:y+256, :, None] *
                  rgb[:, y:y+256].astype(np.float32)).sum(axis=0)
        if not np.isfinite(values).all():
            raise ValueError('nonfinite soft fusion')
        continuous[y:y+256] = values / np.float32(65535)
        fused[y:y+256] = np.clip(np.round(values), 0, 65535).astype(np.uint16)
    return continuous, fused


def _start(handle):
    if handle.model.training or handle.model.ms_scales != (1.0, 0.75) or handle.model.cur_K != 1:
        raise ValueError('model inference defaults changed')
    if torch.backends.cuda.matmul.allow_tf32 or torch.backends.cudnn.allow_tf32:
        raise ValueError('TF32 must remain disabled')
    if handle.device.type == 'cuda':
        torch.cuda.synchronize(handle.device)
    return time.perf_counter()


def _metadata(handle, started, source_count, p, spec, route):
    if handle.device.type == 'cuda':
        torch.cuda.synchronize(handle.device)
        allocated = int(torch.cuda.max_memory_allocated(handle.device))
        reserved = int(torch.cuda.max_memory_reserved(handle.device))
    else:
        allocated = reserved = 0
    if max(allocated, reserved) > GPU_LIMIT:
        raise RuntimeError('Torch GPU high-water exceeds24GiB')
    return dict(upstream_commit=COMMIT, upstream_bindings=handle.bindings,
                route=route, input='developed uint16 RGB; OpenCV uint16 BGR2GRAY rounding /65535',
                source_count=int(source_count), source_order='supplied order, all jointly attended',
                source_axis_subsets=False, scales=[1.0, 0.75], sigma=0.5, soft_fusion=True,
                dtype='float32', tf32=False, autocast=False, device=str(handle.device),
                torch_version=str(torch.__version__), opencv_version=str(cv2.__version__),
                seconds=time.perf_counter()-started,
                peak_cuda_allocated_bytes=allocated, peak_cuda_reserved_bytes=reserved,
                gpu_limit_bytes=GPU_LIMIT, high_water_scope='process since caller last reset; not reset here',
                probability_min=float(p.min()), probability_max=float(p.max()),
                probability_sum_max_error=float(np.max(np.abs(p.sum(axis=0)-np.float32(1)))),
                spec=spec, quality_claim=False)


def predict_tile(handle, rgb16, spec, return_probs=False):
    """Predict a core using an aligned valid RGB read rectangle supplied by caller."""
    rgb = _rgb_input(rgb16)
    expected = tile_spec(spec['core_rect'], spec['full_wh'],
                         diagnostic_halo=0 if spec.get('diagnostic_only') else None)
    if spec != expected:
        raise ValueError('modified or inconsistent tile specification')
    rx, ry, rw, rh = spec['read_rect']
    if rgb.shape[1:3] != (rh, rw):
        raise ValueError('RGB shape differs from physical read rectangle')
    started = _start(handle)
    cx, cy, cw, ch = spec['context_rect']
    full_w, full_h = spec['full_wh']
    mode = spec['global_pad_mode']
    ix = np.array([_pad_index(k, full_w, mode)-rx for k in range(cx, cx+cw)], dtype=np.int64)
    iy = np.array([_pad_index(k, full_h, mode)-ry for k in range(cy, cy+ch)], dtype=np.int64)
    gray = np.empty((rgb.shape[0], ch, cw), dtype=np.float32)
    for index in range(rgb.shape[0]):
        bgr = np.ascontiguousarray(rgb[index, :, :, ::-1])
        source_gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray[index] = source_gray[iy[:, None], ix[None, :]].astype(np.float32) / np.float32(65535)
    x, y, width, height = spec['core_rect']
    with torch.inference_mode(), torch.autocast(device_type=handle.device.type, enabled=False):
        tensor = torch.from_numpy(gray).unsqueeze(0).to(handle.device)
        p = handle.model.forward_probs(tensor).float()
        # Match upstream: remove GLOBAL outer padding before probability smoothing.
        valid_h, valid_w = min(ch, full_h-cy), min(cw, full_w-cx)
        p = handle.network.smooth_probs(p[:, :, :valid_h, :valid_w], 0.5)
        p = p[0, :, y-cy:y-cy+height, x-cx:x-cx+width].contiguous().cpu().numpy()
        del tensor
    core_rgb = rgb[:, y-ry:y-ry+height, x-rx:x-rx+width]
    continuous, fused = fuse_rgb16(p, core_rgb)
    result = dict(fused=fused, fused_float=continuous,
                  metadata=_metadata(handle, started, rgb.shape[0], p, spec, 'bounded-spatial-context'))
    if return_probs:
        result['probabilities'] = p
    return result


def predict_full(handle, rgb16, return_probs=True):
    """Small unmodified upstream probability reference, for commissioning only."""
    rgb = _rgb_input(rgb16)
    if max(rgb.shape[1:3]) > 1024 or rgb.shape[0] * rgb.shape[1] * rgb.shape[2] > 5_000_000:
        raise ValueError('direct reference is bounded to small controls')
    started = _start(handle)
    bgr = [np.ascontiguousarray(frame[:, :, ::-1]) for frame in rgb]
    with torch.inference_mode(), torch.autocast(device_type=handle.device.type, enabled=False):
        p = handle.fuse_module.probabilities(handle.model, bgr, handle.device, sigma=0.5)
    continuous, fused = fuse_rgb16(p, rgb)
    result = dict(fused=fused, fused_float=continuous,
                  metadata=_metadata(handle, started, rgb.shape[0], p, None, 'upstream-probabilities-full-control'))
    if return_probs:
        result['probabilities'] = p
    return result
