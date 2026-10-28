"""One fixed final-CFA spectral completion. Import performs no numerical work."""

from dataclasses import dataclass
from pathlib import Path
import ctypes as C
import hashlib
import math
import struct
import time
import types


HERE = Path(__file__).resolve().parent
LOADER = HERE.parents[1] / "dual-tree-cfa-gpu" / "ordered-fir.py"
LOADER_SHA256 = "16688f2bf6b555c2fe5c90e4d141415ddc0b59d0d7574f847f55a13bbd715dce"
COLORS = ("R", "G", "B")
FOILS = (None, "green-square", "swap-rb", "double-gain")
SMALL_PRE_RESTORE_PIXELS = 16384
MAX_PIXELS = 40_000_000


CUDA_SOURCE = r'''
extern "C" __global__ void completion_normalize(
    const float* input, float* output, int height, int width,
    int origin_x, int origin_y, float red, float blue, float range,
    long long count) {
    const long long n=(long long)blockIdx.x*blockDim.x+threadIdx.x;
    if(n>=count) return;
    const int x=(int)(n%width), y=(int)(n/width);
    const int px=(x+origin_x)&1, py=(y+origin_y)&1;
    const float gain=(!px&&!py)?red:((px&&py)?blue:1.0f);
    // The held native developer's exact operation order. No reciprocal multiply.
    const float positive=fmaxf(input[n],0.0f);
    const float balanced=__fmul_rn(positive,gain);
    const float exposed=__fmul_rn(balanced,1.0f);
    output[n]=__fdiv_rn(exposed,range);
}
extern "C" __global__ void completion_extend(
    const float* input, float* output, int height, int width,
    int origin_x, int origin_y, int color, long long count) {
    const long long n=(long long)blockIdx.x*blockDim.x+threadIdx.x;
    if(n>=count) return;
    const int lx=2*(width-1), ly=2*(height-1);
    const int x=(int)(n%lx), y=(int)(n/lx);
    const int sx=x<width?x:lx-x, sy=y<height?y:ly-y;
    const int px=(sx+origin_x)&1, py=(sy+origin_y)&1;
    const int known=(!px&&!py)?0:((px&&py)?2:1);
    output[n]=known==color?input[(long long)sy*width+sx]:0.0f;
}
extern "C" __global__ void completion_mask(
    float* output, int ly, int lx, int color, int green_square,
    int double_gain, long long count) {
    const long long n=(long long)blockIdx.x*blockDim.x+threadIdx.x;
    if(n>=count) return;
    const int rw=lx/2+1;
    const long long kx=n%rw;
    const long long row=n/rw;
    const long long ky=row<=ly/2?row:row-ly;
    const long long ay=ky<0?-ky:ky;
    float value;
    if(color==1&&!green_square) {
        const long long left=2*(kx*(long long)ly+ay*(long long)lx);
        const long long right=(long long)lx*ly;
        value=left<right?2.0f:(left==right?1.0f:0.0f);
    } else {
        const long long ax4=4*kx, ay4=4*ay;
        const float sx=ax4<lx?2.0f:(ax4==lx?1.0f:0.0f);
        const float sy=ay4<ly?2.0f:(ay4==ly?1.0f:0.0f);
        value=__fmul_rn(sx,sy);
        if(color==1) value=__fmul_rn(value,0.5f);
    }
    if(double_gain) value=__fmul_rn(value,2.0f);
    output[n]=value;
}
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1 << 20), b""):
            h.update(data)
    return h.hexdigest()


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def from_bits(value):
    require(type(value) is int and 0 <= value < 2**32, "invalid f32 bits")
    return struct.unpack("<f", struct.pack("<I", value))[0]


def source_dependencies():
    """Files the caller must bind alongside its own driver/writer sources."""
    return [Path(__file__).resolve(), LOADER.resolve()]


def tensor_version(value):
    try:
        return value._version
    except RuntimeError:
        # Inference-mode tensors deliberately have no mutation counter. The
        # caller still binds input files and independently checks their bytes.
        return None


def normalization_spec(development):
    require(isinstance(development, dict) and development.get("schema") == 1,
            "held development schema1 required")
    levels = development.get("levels_bits")
    wb = development.get("wb_bits")
    require(isinstance(levels, (list, tuple)) and len(levels) == 2,
            "two level bit values required")
    require(isinstance(wb, (list, tuple)) and len(wb) == 3,
            "three WB bit values required")
    black, white = [from_bits(v) for v in levels]
    gains = [from_bits(v) for v in wb]
    require(all(math.isfinite(v) for v in (black, white, *gains))
            and 0 <= black < white and all(v > 0 for v in gains),
            "invalid held levels/WB")
    require(wb[1] == 0x3F800000 and development.get("exposure_bits") == 0x3F800000,
            "exact green-normalized WB and exposure1 required")
    # Binary32 subtraction is rounded once, as Levels::range(). Inputs are
    # already black-subtracted; black is not subtracted from the CFA again.
    dynamic_range = f32(white - black)
    require(math.isfinite(dynamic_range) and dynamic_range > 0,
            "invalid f32 level range")
    return {"levels_bits": list(levels), "wb_bits": list(wb),
            "exposure_bits": 0x3F800000, "range": dynamic_range,
            "range_bits": struct.unpack("<I", struct.pack("<f", dynamic_range))[0],
            "gains": [gains[0], 1.0, 1.0, gains[2]],
            "phase_order": ["R", "G1", "G2", "B"],
            "operation": "max0(DN) * f32(WBcolor/WBgreen) * 1.0f / f32(white-black)",
            "arithmetic": "separate __fmul_rn, __fmul_rn, __fdiv_rn; no reciprocal replacement"}


@dataclass
class Completion:
    camera_rgb: object
    normalized_cfa: object
    evidence: dict
    pre_restore_rgb: object = None


class SpectralCompletion:
    def __init__(self, torch, device_limit_bytes=8 << 30):
        self.t = torch
        require(type(device_limit_bytes) is int and 0 < device_limit_bytes <= 8 << 30,
                "positive device budget no greater than8GiB required")
        require(torch.cuda.is_available() and torch.cuda.current_device() == 0,
                "CUDA device0 required")
        require(not torch.is_autocast_enabled(), "autocast must be disabled")
        self.limit = device_limit_bytes
        props = torch.cuda.get_device_properties(0)
        require(props.total_memory >= self.limit, "physical CUDA memory below requested limit")
        torch.cuda.set_per_process_memory_fraction(self.limit / props.total_memory, 0)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        self.source_sha256 = digest(__file__)
        require(digest(LOADER) == LOADER_SHA256, "frozen NVRTC loader binding differs")
        loader = types.ModuleType("strehl_final_color_nvrtc_private")
        loader.__file__ = str(LOADER)
        # Reuse only our frozen runtime, in a private namespace. Its old kernels
        # and whole-module no-FMA/precise-math checks remain unchanged.
        exec(compile(LOADER.read_text(encoding="utf-8"), str(LOADER), "exec"), loader.__dict__)
        loader.CUDA_SOURCE += CUDA_SOURCE
        torch.empty(0, device="cuda:0")
        self.runtime = loader.OrderedFir(torch)
        self.functions = {}
        self.launches = {name: 0 for name in ("normalize", "extend", "mask")}
        for name in self.launches:
            function = C.c_void_p()
            self.runtime.cucheck(self.runtime.cu_function(
                C.byref(function), self.runtime.module, ("completion_" + name).encode("ascii")),
                "cuModuleGetFunction")
            self.functions[name] = function
        self.completed_fields = 0
        self.check_budget()

    def check_budget(self):
        t = self.t
        allocated = int(t.cuda.memory_allocated(0))
        reserved = int(t.cuda.memory_reserved(0))
        require(allocated <= self.limit and reserved <= self.limit,
                "Torch allocation/reservation exceeds fixed device budget")
        return {"allocated_bytes": allocated, "reserved_bytes": reserved,
                "peak_allocated_bytes": int(t.cuda.max_memory_allocated(0)),
                "peak_reserved_bytes": int(t.cuda.max_memory_reserved(0))}

    def _shape(self, height, width):
        require(type(height) is int and type(width) is int and 4 <= height <= 16384
                and 4 <= width <= 16384 and height * width <= MAX_PIXELS,
                "bounded full-field shape required; no automatic tiling")
        return 2 * (height - 1), 2 * (width - 1)

    def _field(self, field):
        t = self.t
        require(isinstance(field, t.Tensor) and field.ndim == 2
                and field.dtype == t.float32 and field.device.type == "cuda"
                and field.device.index == 0 and field.is_contiguous()
                and not field.requires_grad, "contiguous cuda0 f32 HW, no gradients required")
        self._shape(*field.shape)
        require(not t.is_autocast_enabled(), "autocast must remain disabled")
        require(bool(t.isfinite(field).all().item()), "nonfinite CFA refused")

    def _origin(self, origin):
        require(isinstance(origin, (list, tuple)) and len(origin) == 2
                and all(type(v) is int and -(2**30) < v < 2**30 for v in origin),
                "physical integer origin xy required")
        # Only parity enters this final unwarped sampling operator.
        return tuple(v % 2 for v in origin)

    def _launch(self, name, count, arguments, tensors):
        t, rt = self.t, self.runtime
        require(rt.current_context() == rt.context and t.cuda.current_device() == 0,
                "Torch current CUDA context changed")
        require(0 < count < 2**63, "kernel count bound")
        stream = t.cuda.current_stream(0)
        for value in tensors:
            value.record_stream(stream)
        params = (C.c_void_p * len(arguments))(*(
            C.cast(C.byref(value), C.c_void_p) for value in arguments))
        rt.cucheck(rt.cu_launch(self.functions[name], (count + 255) // 256, 1, 1,
                   256, 1, 1, 0, C.c_void_p(stream.cuda_stream), params, None),
                   "cuLaunchKernel completion_" + name)
        rt.streams.add(stream.cuda_stream)
        self.launches[name] += 1

    def normalize_cfa(self, cfa_dn, development, physical_origin_xy=(0, 0)):
        self._field(cfa_dn)
        spec = normalization_spec(development)
        ox, oy = self._origin(physical_origin_xy)
        h, w = cfa_dn.shape
        output = self.t.empty_like(cfa_dn)
        values = [C.c_void_p(cfa_dn.data_ptr()), C.c_void_p(output.data_ptr()),
                  C.c_int(h), C.c_int(w), C.c_int(ox), C.c_int(oy),
                  C.c_float(spec["gains"][0]), C.c_float(spec["gains"][3]),
                  C.c_float(spec["range"]), C.c_longlong(h * w)]
        self._launch("normalize", h * w, values, (cfa_dn, output))
        require(bool(self.t.isfinite(output).all().item()), "nonfinite normalized CFA")
        self.check_budget()
        return output

    def mask(self, height, width, color, diagnostic_foil=None):
        require(color in COLORS and diagnostic_foil in FOILS, "invalid color/diagnostic foil")
        ly, lx = self._shape(height, width)
        output = self.t.empty((ly, lx // 2 + 1), dtype=self.t.float32, device="cuda:0")
        values = [C.c_void_p(output.data_ptr()), C.c_int(ly), C.c_int(lx),
                  C.c_int(COLORS.index(color)), C.c_int(diagnostic_foil == "green-square"),
                  C.c_int(diagnostic_foil == "double-gain"), C.c_longlong(output.numel())]
        self._launch("mask", output.numel(), values, (output,))
        self.check_budget()
        return output

    def _extend(self, field, color, origin, foil):
        h, w = field.shape
        ly, lx = self._shape(h, w)
        ox, oy = self._origin(origin)
        source_color = 2 - color if foil == "swap-rb" else color
        output = self.t.empty((ly, lx), dtype=self.t.float32, device="cuda:0")
        values = [C.c_void_p(field.data_ptr()), C.c_void_p(output.data_ptr()),
                  C.c_int(h), C.c_int(w), C.c_int(ox), C.c_int(oy),
                  C.c_int(source_color), C.c_longlong(ly * lx)]
        self._launch("extend", ly * lx, values, (field, output))
        self.check_budget()
        return output

    def _known_slices(self, color, origin):
        ox, oy = self._origin(origin)
        phases = (((0, 0),), ((1, 0), (0, 1)), ((1, 1),))[color]
        return [(slice((py - oy) % 2, None, 2), slice((px - ox) % 2, None, 2))
                for px, py in phases]

    def _known_error(self, completed, original, slices):
        t = self.t
        diffs = [(completed[s] - original[s]).reshape(-1) for s in slices]
        delta = t.cat(diffs) if len(diffs) > 1 else diffs[0]
        require(bool(t.isfinite(delta).all().item()), "nonfinite pre-restoration error")
        peak = delta.abs().max()
        scale = t.where(peak > 0, peak, t.ones_like(peak))
        scaled = delta / scale
        rms = scaled.square().mean().sqrt() * scale
        return {"count": delta.numel(), "max_abs": float(peak.item()),
                "rms": float(rms.item()), "units": "normalized-camera"}

    def complete_normalized(self, normalized_cfa, physical_origin_xy=(0, 0), diagnostic_foil=None):
        self._field(normalized_cfa)
        self._origin(physical_origin_xy)
        require(diagnostic_foil in FOILS, "unknown diagnostic foil")
        t = self.t
        h, w = normalized_cfa.shape
        ly, lx = self._shape(h, w)
        input_version = tensor_version(normalized_cfa)
        camera = t.empty((h, w, 3), dtype=t.float32, device="cuda:0")
        before = t.empty_like(camera) if h * w <= SMALL_PRE_RESTORE_PIXELS else None
        pre_restore, timings = {}, {}
        t.cuda.synchronize(0)
        begin = time.perf_counter()
        for color, name in enumerate(COLORS):
            started = time.perf_counter()
            extended = self._extend(normalized_cfa, color, physical_origin_xy, diagnostic_foil)
            spectrum = t.fft.rfft2(extended, norm="ortho")
            require(spectrum.dtype == t.complex64, "FFT precision changed")
            del extended
            multiplier = self.mask(h, w, name, diagnostic_foil)
            spectrum.mul_(multiplier)
            del multiplier
            completed = t.fft.irfft2(spectrum, s=(ly, lx), norm="ortho")
            require(completed.dtype == t.float32, "inverse FFT precision changed")
            del spectrum
            require(bool(t.isfinite(completed).all().item()), "nonfinite full inverse FFT")
            crop = completed[:h, :w]
            slices = self._known_slices(color, physical_origin_xy)
            pre_restore[name] = self._known_error(crop, normalized_cfa, slices)
            camera[:, :, color].copy_(crop)
            if before is not None:
                before[:, :, color].copy_(crop)
            del crop, completed
            for site in slices:
                camera[:, :, color][site].copy_(normalized_cfa[site])
            self.check_budget()
            t.cuda.synchronize(0)
            timings[name] = time.perf_counter() - started
        require(input_version is None or tensor_version(normalized_cfa) == input_version,
                "normalized input was modified")
        require(bool(t.isfinite(camera).all().item()), "nonfinite final camera RGB")
        # Bit equality is an output mechanics check, not missing-site fidelity.
        restored = all(t.equal(camera[:, :, c][s].contiguous().view(t.int32),
                               normalized_cfa[s].contiguous().view(t.int32))
                       for c in range(3) for s in self._known_slices(c, physical_origin_xy))
        require(restored, "known-site bit restoration differs")
        self.completed_fields += 1
        evidence = {"schema": 1, "status": "COMPLETE_FINAL_CFA_SPECTRAL_COMPLETION",
                    "complete": True, "height": h, "width": w,
                    "physical_origin_xy": list(physical_origin_xy),
                    "extension_hw": [ly, lx], "input": "already-normalized finite signed CFA",
                    "camera_layout": "HWC", "camera_units": "normalized-camera-RGB",
                    "pre_restore": pre_restore, "known_sites_restored_bit_exact": restored,
                    "normalized_input_version_unchanged": True if input_version is not None else None,
                    "pre_restore_rgb_retained": before is not None,
                    "diagnostic_foil": diagnostic_foil, "FFT_norm": "ortho",
                    "signal_dtype": "float32", "spectrum_dtype": "complex64",
                    "source_demosaic_calls": 0, "final_color_completion_calls": 1,
                    "MHC_calls": 0, "remosaic_calls": 0, "RAW_reads": 0,
                    "channel_seconds": timings, "total_seconds": time.perf_counter() - begin,
                    "quality_claim": False, "photographic_admission": False,
                    "memory": self.check_budget()}
        return Completion(camera, normalized_cfa, evidence, before)

    def complete(self, cfa_dn, development, physical_origin_xy=(0, 0), diagnostic_foil=None):
        self._field(cfa_dn)
        version = tensor_version(cfa_dn)
        negative_count = int((cfa_dn < 0).sum().item())
        normalized = self.normalize_cfa(cfa_dn, development, physical_origin_xy)
        result = self.complete_normalized(normalized, physical_origin_xy, diagnostic_foil)
        require(version is None or tensor_version(cfa_dn) == version, "signed input CFA was modified")
        result.evidence.update({"input": "black-subtracted signed camera-DN CFA",
                                "normalization": normalization_spec(development),
                                "negative_input_samples": negative_count,
                                "signed_input_tensor_version_unchanged": True if version is not None else None})
        return result

    def metadata(self, strict=True):
        unchanged = digest(__file__) == self.source_sha256 and digest(LOADER) == LOADER_SHA256
        if strict:
            require(unchanged, "completion source/loader changed during worker")
        return {"schema": 1, "source_sha256": self.source_sha256,
                "source_path": str(Path(__file__).resolve()), "bindings_unchanged": unchanged,
                "loader_path": str(LOADER), "loader_sha256": LOADER_SHA256,
                "completion_cuda_sha256": hashlib.sha256(CUDA_SOURCE.encode("ascii")).hexdigest(),
                "runtime": self.runtime.metadata(strict=strict),
                "device_limit_bytes": self.limit, "memory": self.check_budget(),
                "completed_fields": self.completed_fields, "completion_kernel_launches": dict(self.launches),
                "torch_version": str(self.t.__version__), "torch_cuda_version": self.t.version.cuda,
                "tf32": False, "autocast": False, "f16_storage": False,
                "boundaries": "periodic reflection about0 andN-1; no duplicated endpoints",
                "sampling_prior": "independent R/B square and combined-green diamond Nyquist",
                "noise_model": "none added; no inferred final-CFA variance",
                "quality_claim": False, "photographic_admission": False}
