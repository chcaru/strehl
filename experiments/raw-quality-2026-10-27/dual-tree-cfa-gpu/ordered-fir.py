"""One independent NVRTC implementation of the frozen CPU forward FIR order.

The worker supplies Torch and owns every image/filter/output allocation. This
module neither creates a CUDA context nor changes the current Torch stream.
Runtime compilation occurs only inside the root-scheduled bounded worker.
"""
from pathlib import Path
import ctypes as C
import hashlib
import os
import time


CUDA_SOURCE = r'''
extern "C" __global__ void ordered_x(
    const float* __restrict__ src, const float* __restrict__ reversed_taps,
    float* __restrict__ dst, long long sc, long long sy, long long sx,
    int height, int width, int minimum, int taps, long long count) {
    const long long i = (long long)blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= count) return;
    const int half = width / 2;
    const int x = (int)(i % half);
    const long long row = i / half;
    const int y = (int)(row % height);
    const int tree = (int)(row / height);
    float lo = 0.0f;
    float hi = 0.0f;
    #pragma unroll 1
    for (int j = 0; j < taps; ++j) {
        int q = (2 * x - minimum - j) % width;
        if (q < 0) q += width;
        const float v = src[(long long)tree * sc + (long long)y * sy + (long long)q * sx];
        // Existing worker banks store reversed correlation taps. Recover the
        // original ascending CPU tap index without changing their f32 bits.
        const float l = reversed_taps[(2 * tree) * taps + (taps - 1 - j)];
        const float h = reversed_taps[(2 * tree + 1) * taps + (taps - 1 - j)];
        lo = __fadd_rn(lo, __fmul_rn(l, v));
        hi = __fadd_rn(hi, __fmul_rn(h, v));
    }
    const long long plane = (long long)height * half;
    const long long p = (long long)y * half + x;
    dst[(2 * tree) * plane + p] = lo;
    dst[(2 * tree + 1) * plane + p] = hi;
}

extern "C" __global__ void ordered_y(
    const float* __restrict__ src, const float* __restrict__ reversed_taps,
    float* __restrict__ dst, long long sc, long long sy, long long sx,
    int height, int width, int minimum, int taps, long long count) {
    const long long i = (long long)blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= count) return;
    const int x = (int)(i % width);
    const long long row = i / width;
    const int y = (int)(row % (height / 2));
    const int branch = (int)(row / (height / 2));
    float lo = 0.0f;
    float hi = 0.0f;
    #pragma unroll 1
    for (int j = 0; j < taps; ++j) {
        int q = (2 * y - minimum - j) % height;
        if (q < 0) q += height;
        const float v = src[(long long)branch * sc + (long long)q * sy + (long long)x * sx];
        const float l = reversed_taps[(2 * branch) * taps + (taps - 1 - j)];
        const float h = reversed_taps[(2 * branch + 1) * taps + (taps - 1 - j)];
        lo = __fadd_rn(lo, __fmul_rn(l, v));
        hi = __fadd_rn(hi, __fmul_rn(h, v));
    }
    const long long plane = (long long)(height / 2) * width;
    const long long p = (long long)y * width + x;
    dst[(2 * branch) * plane + p] = lo;
    dst[(2 * branch + 1) * plane + p] = hi;
}
'''


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def signature(lib, name, result, args):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = result, args
    return fn


class OrderedFir:
    def __init__(self, torch):
        require(os.name == "nt" and C.sizeof(C.c_void_p) == 8,
                "ordered FIR requires the pinned Windows x64 runtime")
        self.torch = torch
        self.helper_sha256 = digest(__file__)
        self.launches = {"x": 0, "y": 0}
        self.streams = set()
        lib = Path(torch.__file__).resolve().parent / "lib"
        self.paths = {
            "nvrtc": lib / "nvrtc64_120_0.dll",
            "nvrtc_builtins": lib / "nvrtc-builtins64_128.dll",
            "driver": Path(os.environ["SystemRoot"]) / "System32" / "nvcuda.dll",
        }
        require(all(p.is_file() for p in self.paths.values()), "required CUDA DLL absent")
        self.library_hashes = {k: digest(p) for k, p in self.paths.items()}
        self.dll_directory = os.add_dll_directory(str(lib))
        # Retain DLL handles and the module until process exit. Loading the
        # builtins by absolute path also binds the actual compiler dependency.
        self.builtins = C.WinDLL(str(self.paths["nvrtc_builtins"]))
        self.nvrtc = C.WinDLL(str(self.paths["nvrtc"]))
        self.driver = C.WinDLL(str(self.paths["driver"]))
        vp, ip, sp = C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_size_t)
        self.nv_error = signature(self.nvrtc, "nvrtcGetErrorString", C.c_char_p, [C.c_int])
        self.nv_version = signature(self.nvrtc, "nvrtcVersion", C.c_int, [ip, ip])
        self.nv_arch_count = signature(self.nvrtc, "nvrtcGetNumSupportedArchs", C.c_int, [ip])
        self.nv_archs = signature(self.nvrtc, "nvrtcGetSupportedArchs", C.c_int, [ip])
        self.nv_create = signature(self.nvrtc, "nvrtcCreateProgram", C.c_int,
            [C.POINTER(vp), C.c_char_p, C.c_char_p, C.c_int,
             C.POINTER(C.c_char_p), C.POINTER(C.c_char_p)])
        self.nv_compile = signature(self.nvrtc, "nvrtcCompileProgram", C.c_int,
            [vp, C.c_int, C.POINTER(C.c_char_p)])
        self.nv_log_size = signature(self.nvrtc, "nvrtcGetProgramLogSize", C.c_int, [vp, sp])
        self.nv_log = signature(self.nvrtc, "nvrtcGetProgramLog", C.c_int, [vp, vp])
        self.nv_ptx_size = signature(self.nvrtc, "nvrtcGetPTXSize", C.c_int, [vp, sp])
        self.nv_ptx = signature(self.nvrtc, "nvrtcGetPTX", C.c_int, [vp, vp])
        self.nv_destroy = signature(self.nvrtc, "nvrtcDestroyProgram", C.c_int, [C.POINTER(vp)])
        self.cu_error = signature(self.driver, "cuGetErrorName", C.c_int,
                                  [C.c_int, C.POINTER(C.c_char_p)])
        self.cu_version = signature(self.driver, "cuDriverGetVersion", C.c_int, [ip])
        self.cu_context = signature(self.driver, "cuCtxGetCurrent", C.c_int, [C.POINTER(vp)])
        self.cu_memory = signature(self.driver, "cuMemGetInfo_v2", C.c_int, [sp, sp])
        self.cu_load = signature(self.driver, "cuModuleLoadData", C.c_int, [C.POINTER(vp), vp])
        self.cu_function = signature(self.driver, "cuModuleGetFunction", C.c_int,
                                     [C.POINTER(vp), vp, C.c_char_p])
        self.cu_launch = signature(self.driver, "cuLaunchKernel", C.c_int,
            [vp, C.c_uint, C.c_uint, C.c_uint, C.c_uint, C.c_uint, C.c_uint,
             C.c_uint, vp, C.POINTER(vp), C.POINTER(vp)])
        major, minor, driver_version = C.c_int(), C.c_int(), C.c_int()
        self.nvcheck(self.nv_version(C.byref(major), C.byref(minor)), "nvrtcVersion")
        self.nvrtc_version = [major.value, minor.value]
        self.cucheck(self.cu_version(C.byref(driver_version)), "cuDriverGetVersion")
        self.driver_version = driver_version.value
        count = C.c_int()
        self.nvcheck(self.nv_arch_count(C.byref(count)), "nvrtcGetNumSupportedArchs")
        require(0 < count.value <= 128, "invalid NVRTC architecture count")
        archs = (C.c_int * count.value)()
        self.nvcheck(self.nv_archs(archs), "nvrtcGetSupportedArchs")
        self.supported_archs = list(archs)
        props = torch.cuda.get_device_properties(0)
        self.arch = 10 * props.major + props.minor
        require(self.arch in self.supported_archs, "installed NVRTC lacks exact device architecture")
        self.options = ["--std=c++11", "--gpu-architecture=compute_" + str(self.arch),
                        "--fmad=false", "--ftz=false", "--prec-div=true", "--prec-sqrt=true"]
        self.context = self.current_context()
        require(self.context != 0 and torch.cuda.current_device() == 0,
                "Torch CUDA context must already be current on device0")
        started = time.monotonic()
        program = vp()
        self.nvcheck(self.nv_create(C.byref(program), CUDA_SOURCE.encode("ascii"),
                                   b"strehl_ordered_forward.cu", 0, None, None), "nvrtcCreateProgram")
        try:
            options = (C.c_char_p * len(self.options))(*(x.encode("ascii") for x in self.options))
            status = self.nv_compile(program, len(self.options), options)
            size = C.c_size_t()
            self.nvcheck(self.nv_log_size(program, C.byref(size)), "nvrtcGetProgramLogSize")
            require(0 < size.value <= 1024 * 1024, "NVRTC log bound")
            log = C.create_string_buffer(size.value)
            self.nvcheck(self.nv_log(program, log), "nvrtcGetProgramLog")
            self.compile_log = log.value.decode("utf-8", errors="replace")
            if status != 0:
                raise RuntimeError("nvrtcCompileProgram: " + self.nv_error(status).decode()
                                   + "\n" + self.compile_log)
            self.nvcheck(self.nv_ptx_size(program, C.byref(size)), "nvrtcGetPTXSize")
            require(0 < size.value <= 4 * 1024 * 1024, "NVRTC PTX bound")
            self.ptx = C.create_string_buffer(size.value)
            self.nvcheck(self.nv_ptx(program, self.ptx), "nvrtcGetPTX")
        finally:
            self.nvcheck(self.nv_destroy(C.byref(program)), "nvrtcDestroyProgram")
        self.compile_seconds = time.monotonic() - started
        ptx = self.ptx.raw
        require(b"fma." not in ptx and b"mad.f32" not in ptx,
                "ordered FIR PTX unexpectedly contains floating fused multiply-add")
        require(b"mul.rn.f32" in ptx and b"add.rn.f32" in ptx,
                "ordered FIR PTX lacks explicit rounded f32 multiply/add")
        self.ptx_sha256 = hashlib.sha256(ptx).hexdigest()
        self.before_module = self.device_memory()
        self.module = vp()
        self.cucheck(self.cu_load(C.byref(self.module), self.ptx), "cuModuleLoadData")
        self.functions = {}
        for axis in ("x", "y"):
            function = vp()
            self.cucheck(self.cu_function(C.byref(function), self.module,
                                         ("ordered_" + axis).encode()), "cuModuleGetFunction")
            self.functions[axis] = function
        self.after_module = self.device_memory()

    def nvcheck(self, code, operation):
        if code != 0:
            raise RuntimeError(operation + ": " + self.nv_error(code).decode())

    def cucheck(self, code, operation):
        if code != 0:
            name = C.c_char_p()
            self.cu_error(code, C.byref(name))
            raise RuntimeError(operation + ": " + str(code) + " "
                               + (name.value.decode() if name.value else "unknown CUDA error"))

    def current_context(self):
        value = C.c_void_p()
        self.cucheck(self.cu_context(C.byref(value)), "cuCtxGetCurrent")
        return value.value or 0

    def device_memory(self):
        free, total = C.c_size_t(), C.c_size_t()
        self.cucheck(self.cu_memory(C.byref(free), C.byref(total)), "cuMemGetInfo_v2")
        return {"free_bytes": free.value, "total_bytes": total.value}

    def apply(self, axis, source, taps, minimum):
        t = self.torch
        channels = 4 if axis == "x" else 8
        require(source.ndim == 4 and source.shape[0] == 1 and source.shape[1] == channels,
                "ordered FIR source shape")
        h, w = source.shape[-2:]
        require(2 <= h <= 8192 and 2 <= w <= 8192 and h % 2 == 0 and w % 2 == 0,
                "ordered FIR bounded even dimensions")
        length = taps.numel() // (2 * channels)
        require((length, minimum) in ((10, 0), (14, -6)), "ordered FIR fixed bank extent")
        expected = (8, 1, 1, length) if axis == "x" else (16, 1, length, 1)
        require(tuple(taps.shape) == expected and taps.is_contiguous(), "ordered FIR filter layout")
        for a in (source, taps):
            require(a.dtype == t.float32 and a.device.type == "cuda" and a.device.index == 0,
                    "ordered FIR requires Torch-owned cuda0 f32")
        strides = source.stride()[1:]
        require(all(type(s) is int and 0 <= s < 2**63 for s in strides)
                and sum((n - 1) * s for n, s in zip(source.shape[1:], strides)) < 2**63,
                "ordered FIR stride/index bound")
        require(self.current_context() == self.context and t.cuda.current_device() == 0,
                "current Torch CUDA context changed")
        oh, ow = (h, w // 2) if axis == "x" else (h // 2, w)
        output = t.empty((1, 2 * channels, oh, ow), device=source.device, dtype=t.float32)
        count = channels * oh * ow
        blocks = (count + 255) // 256
        require(0 < blocks <= 2**31 - 1, "ordered FIR launch bound")
        stream = t.cuda.current_stream(0)
        # The external driver launch uses exactly this Torch stream. Recording
        # it keeps input/filter/output storage live through asynchronous use.
        for a in (source, taps, output):
            a.record_stream(stream)
        values = [C.c_void_p(source.data_ptr()), C.c_void_p(taps.data_ptr()),
                  C.c_void_p(output.data_ptr()), *(C.c_longlong(s) for s in strides),
                  C.c_int(h), C.c_int(w), C.c_int(minimum), C.c_int(length), C.c_longlong(count)]
        params = (C.c_void_p * len(values))(*(C.cast(C.byref(v), C.c_void_p) for v in values))
        self.cucheck(self.cu_launch(self.functions[axis], blocks, 1, 1, 256, 1, 1, 0,
                                    C.c_void_p(stream.cuda_stream), params, None), "cuLaunchKernel")
        self.launches[axis] += 1
        self.streams.add(stream.cuda_stream)
        return output

    def horizontal(self, source, taps, minimum):
        return self.apply("x", source, taps, minimum)

    def vertical(self, source, taps, minimum):
        return self.apply("y", source, taps, minimum)

    def metadata(self, strict=True):
        observed = {}
        for name, path in {"helper": Path(__file__), **self.paths}.items():
            try:
                observed[name] = digest(path)
            except OSError:
                observed[name] = None
        unchanged = observed["helper"] == self.helper_sha256 and all(
            observed[k] == self.library_hashes[k] for k in self.paths)
        if strict:
            require(unchanged, "ordered FIR helper or CUDA DLL bytes changed during worker")
        return {
            "helper_sha256": self.helper_sha256,
            "bindings_unchanged": unchanged, "observed_file_sha256": observed,
            "cuda_source_sha256": hashlib.sha256(CUDA_SOURCE.encode("ascii")).hexdigest(),
            "libraries": {k: {"path": str(p), "sha256": self.library_hashes[k]}
                          for k, p in self.paths.items()},
            "nvrtc_version": self.nvrtc_version, "driver_version": self.driver_version,
            "supported_architectures": self.supported_archs, "device_architecture": self.arch,
            "compiler_options": self.options, "compile_seconds": self.compile_seconds,
            "compile_log": self.compile_log, "ptx_sha256": self.ptx_sha256,
            "ptx_bytes_including_terminator": len(self.ptx.raw),
            "current_context_handle": self.context, "torch_stream_handles": sorted(self.streams),
            "kernel_launches": dict(self.launches),
            "forward_arithmetic": "ascending taps; separate __fmul_rn then __fadd_rn; no FMA/FTZ/fast-math",
            "module_memory": {"before_load": self.before_module, "after_load": self.after_module,
                "scope": "driver module/JIT storage excluded from Torch allocator cap; free-memory delta is descriptive, may include other activity or lazy loading"},
            "image_storage": "all input/filter/output tensors Torch-owned; original expanded zero-stride channels supported",
        }
