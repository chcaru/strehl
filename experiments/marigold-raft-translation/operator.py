"""Fixed torchvision RAFT inference and median/vector adapter; no fitting or IO."""
from pathlib import Path
import hashlib
import importlib.metadata
import time

import numpy as np

NATIVE_WH = (6268, 4176)
PROXY_WH = (880, 586)
SOURCE_WH = (7032, 4688)
SOURCE_PROXY_WH = (988, 658)
SCALE_XY = np.array(PROXY_WH, dtype=np.float64) / np.array(NATIVE_WH, dtype=np.float64)
INTERIOR_NATIVE_XYWH = (3258, 3028, 328, 328)
SUPPORT_NATIVE_XYWH = (3226, 2996, 392, 392)
WEIGHT_URL = 'https://download.pytorch.org/models/raft_large_C_T_SKHT_V2-ff5fadd5.pth'
WEIGHT_PREFIX = 'ff5fadd5'
VERSIONS = {'torch': '2.11.0+cu128', 'torchvision': '0.26.0+cu128'}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def array_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def native_grid():
    y, x = np.indices(PROXY_WH[::-1], dtype=np.float64)
    return (np.stack((x, y), axis=-1) + .5) / SCALE_XY - .5


def interior_mask():
    p = native_grid()
    x, y, w, h = INTERIOR_NATIVE_XYWH
    return (p[..., 0] >= x) & (p[..., 0] < x+w) & (p[..., 1] >= y) & (p[..., 1] < y+h)


def mapped_source(points_native, transform):
    p = np.asarray(points_native, dtype=np.float64)
    a, ai, bx, by = transform
    require(p.shape[-1] == 2 and np.isfinite(p).all()
            and np.isfinite(transform).all() and a*a+ai*ai > 0, 'Invalid source mapping')
    dx = p[..., 0] + 382 - 3516
    dy = p[..., 1] + 256 - 2344
    return np.stack((3516+a*dx-ai*dy+2*bx, 2344+ai*dx+a*dy+2*by), axis=-1)


def proxy_sample_coordinates(transform):
    native = mapped_source(native_grid(), transform)
    scale = np.array(SOURCE_PROXY_WH, dtype=np.float64)/np.array(SOURCE_WH, dtype=np.float64)
    sample = ((native+.5)*scale-.5).astype(np.float32)
    # Bilinear remap may quantize its phase but must never use the border mode.
    require(np.all(sample >= 0.) and np.all(np.floor(sample)+1 < np.array(SOURCE_PROXY_WH)),
            'Global proxy footprint exceeds retained source')
    return native, sample


def make_proxy(rgb_u16, transform):
    import cv2
    require(rgb_u16.dtype == np.uint16 and rgb_u16.shape == (*SOURCE_WH[::-1], 3), 'Wrong source RGB16')
    native, sample = proxy_sample_coordinates(transform)
    reduced = cv2.resize(rgb_u16, SOURCE_PROXY_WH, interpolation=cv2.INTER_AREA)
    reduced = reduced.astype(np.float32) / np.float32(65535)
    image = cv2.remap(reduced, sample[..., 0], sample[..., 1], interpolation=cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_CONSTANT, borderValue=0.)
    require(image.shape == (*PROXY_WH[::-1], 3) and image.dtype == np.float32
            and np.isfinite(image).all() and image.min() >= 0 and image.max() <= 1, 'Invalid proxy')
    return image, dict(native_coordinate_sha256=array_sha(native),
                       remap_f32_coordinate_sha256=array_sha(sample),
                       native_min_xy=native.min(axis=(0, 1)).tolist(),
                       native_max_xy=native.max(axis=(0, 1)).tolist(),
                       remap_min_xy=sample.min(axis=(0, 1)).tolist(),
                       remap_max_xy=sample.max(axis=(0, 1)).tolist(), all_bilinear_support_valid=True)


def reduce_flow(flow, source_a):
    require(flow.dtype == np.float32 and flow.shape == (*PROXY_WH[::-1], 2)
            and np.isfinite(flow).all(), 'Invalid complete flow')
    require(len(source_a) == 2 and np.isfinite(source_a).all()
            and np.dot(source_a, source_a) > 0, 'Invalid destination linear map')
    points = flow[interior_mask()].astype(np.float64)
    median_proxy = np.median(points, axis=0)
    median_native = median_proxy / SCALE_XY
    ar, ai = source_a
    x, y = median_native
    return dict(native_median=median_native.tolist(), median_proxy=median_proxy.tolist(),
                source_native_translation=[float(ar*x-ai*y), float(ai*x+ar*y)],
                interior_count=len(points), componentwise_unweighted_median=True,
                learned_spatial_variation_discarded=True)


def load_model(checkpoint):
    import torch
    import torchvision
    from torchvision.models.optical_flow import raft_large, Raft_Large_Weights
    for name, version in VERSIONS.items():
        require(importlib.metadata.version(name) == version, f'Installed {name} differs from frozen runtime')
    require(Raft_Large_Weights.C_T_SKHT_V2.url == WEIGHT_URL, 'Installed weight selection differs')
    require(torch.cuda.is_available(), 'CUDA unavailable; no install or CPU fallback')
    torch.set_num_threads(8)
    torch.set_num_interop_threads(1)
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)
    total = torch.cuda.get_device_properties(0).total_memory
    require(total > 8 << 30, 'Insufficient GPU memory for fixed allocator cap')
    torch.cuda.set_per_process_memory_fraction((8 << 30)/total)
    torch.cuda.reset_peak_memory_stats()
    with Path(checkpoint).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    require(digest.startswith(WEIGHT_PREFIX), 'Checkpoint published hash prefix differs')
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    require(isinstance(state, dict) and state and all(isinstance(k, str) and torch.is_tensor(v)
            for k, v in state.items()), 'Unsupported safe checkpoint structure')
    require(all(not v.is_floating_point() or (v.dtype == torch.float32 and bool(torch.isfinite(v).all()))
                for v in state.values()), 'Invalid/non-f32 checkpoint state')
    model = raft_large(weights=None, progress=False)
    model.load_state_dict(state, strict=True)
    require(set(model.state_dict()) == set(state) and all(torch.equal(v, state[k])
            for k, v in model.state_dict().items()), 'Loaded complete state differs')
    model.eval().requires_grad_(False).cuda()
    model.pilot_metadata = dict(torch_version=torch.__version__, torchvision_version=torchvision.__version__,
        gpu=torch.cuda.get_device_name(), cuda_version=torch.version.cuda, checkpoint_sha256=digest,
        strict_complete_load=True, weights_only=True, floating_dtype='float32', updates=12,
        preprocessing='official weight transform; replicate bottom6 then remove output padding', calls=[])
    return model


def infer_pair(model, reference_rgb_f32, source_rgb_f32):
    import torch
    from torchvision.models.optical_flow import Raft_Large_Weights
    images = (reference_rgb_f32, source_rgb_f32)
    for image in images:
        require(image.shape == (*PROXY_WH[::-1], 3) and image.dtype == np.float32
                and np.isfinite(image).all() and image.min() >= 0 and image.max() <= 1, 'Invalid model image')
    before = [array_sha(image) for image in images]
    tensors = [torch.from_numpy(np.ascontiguousarray(image.transpose(2, 0, 1))).unsqueeze(0) for image in images]
    tensors = Raft_Large_Weights.C_T_SKHT_V2.transforms()(*tensors)
    tensors = [torch.nn.functional.pad(t, (0, 0, 0, 6), mode='replicate').cuda() for t in tensors]
    torch.cuda.synchronize()
    start = time.perf_counter()
    with torch.inference_mode():
        flows = model(*tensors, num_flow_updates=12)
    torch.cuda.synchronize()
    seconds = time.perf_counter()-start
    require(len(flows) == 12 and all(f.shape == (1, 2, 592, 880) and f.dtype == torch.float32
            and bool(torch.isfinite(f).all()) for f in flows), 'Invalid intermediate/final RAFT flow')
    result = flows[-1][0, :, :586, :].permute(1, 2, 0).contiguous().cpu().numpy().copy()
    require(before == [array_sha(image) for image in images], 'Inference modified input')
    model.pilot_metadata['calls'].append(dict(index=len(model.pilot_metadata['calls']), synchronized_seconds=seconds,
        inputs_sha256=before, flow_sha256=array_sha(result), input_arrays_unchanged=True,
        gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(), gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved()))
    return result
