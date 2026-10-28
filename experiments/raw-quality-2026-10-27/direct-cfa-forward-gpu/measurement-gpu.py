"""Matrix-free original-photosite measurement, not a reconstruction algorithm.

The root-scheduled process supplies Torch. Importing this module imports only
the standard library; NVRTC compilation first occurs in MeasurementGpu().
"""
from pathlib import Path
import ctypes as C
import hashlib
import math
import os
import time


CPU_SHA256 = "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac"
CPU_PATH = Path(__file__).resolve().parent.parent / "joint-cfa-local-fit" / "band-residual" / "sensor-operator.py"
MAX_RECT_SENSELS = 1048576

CUDA_SOURCE = r'''
// All image arithmetic is f32. Only physical footprint geometry is f64.
__device__ bool axis_weights(double q, int base, float* w) {
    if (q == (double)base) {
        #pragma unroll
        for (int j = 0; j < 6; ++j) w[j] = j == 2 ? 1.0f : 0.0f;
        return true;
    }
    float total = 0.0f;
    #pragma unroll 1
    for (int j = 0; j < 6; ++j) {
        const float d = (float)(q - (double)(base - 2 + j));
        const float angle = __fmul_rn(3.1415927410125732421875f, d);
        const float angle3 = __fdiv_rn(angle, 3.0f);
        float value = 1.0f;
        if (d != 0.0f)
            value = __fmul_rn(__fdiv_rn(sinf(angle), angle),
                             __fdiv_rn(sinf(angle3), angle3));
        if (fabsf(d) >= 3.0f) value = 0.0f;
        w[j] = value;
        total = __fadd_rn(total, value);
    }
    if (!isfinite(total) || total == 0.0f) return false;
    #pragma unroll
    for (int j = 0; j < 6; ++j) {
        w[j] = __fdiv_rn(w[j], total);
        if (!isfinite(w[j])) return false;
    }
    return true;
}

// One row has at most 8x8 distinct latent sites under the declared affine
// bound. Coalesce the nine overlapping 6x6 stencils before row normalization.
// This is bounded thread-local scratch, not a field-sized node/stencil cube.
__device__ int make_row(long long px, long long py, int fh, int fw,
    double a00, double a01, double a02, double a10, double a11, double a12,
    float* weights, int* left, int* top, int* rw, int* rh) {
    const double abscissa = 0.38729833462074168852;
    const double sub[3] = {-abscissa, 0.0, abscissa};
    const double quadrature[3] = {5.0/18.0, 4.0/9.0, 5.0/18.0};
    double qx[9], qy[9];
    int ix[9], iy[9];
    int xmin = 2147483647, ymin = 2147483647;
    int xmax = -2147483647, ymax = -2147483647;
    #pragma unroll 1
    for (int gy = 0; gy < 3; ++gy) {
        #pragma unroll 1
        for (int gx = 0; gx < 3; ++gx) {
            const int n = 3 * gy + gx;
            const double sx = __dadd_rn((double)px, sub[gx]);
            const double sy = __dadd_rn((double)py, sub[gy]);
            qx[n] = __dadd_rn(__dadd_rn(__dmul_rn(a00,sx), __dmul_rn(a01,sy)), a02);
            qy[n] = __dadd_rn(__dadd_rn(__dmul_rn(a10,sx), __dmul_rn(a11,sy)), a12);
            if (!isfinite(qx[n]) || !isfinite(qy[n]) ||
                qx[n] < 2.0 || qy[n] < 2.0 || qx[n] >= fw-3.0 || qy[n] >= fh-3.0)
                return 1;
            ix[n] = (int)floor(qx[n]); iy[n] = (int)floor(qy[n]);
            xmin = min(xmin,ix[n]-2); xmax = max(xmax,ix[n]+3);
            ymin = min(ymin,iy[n]-2); ymax = max(ymax,iy[n]+3);
        }
    }
    *left=xmin; *top=ymin; *rw=xmax-xmin+1; *rh=ymax-ymin+1;
    if (*rw > 8 || *rh > 8 || xmin < 0 || ymin < 0 || xmax >= fw || ymax >= fh)
        return 1;
    #pragma unroll
    for (int j=0;j<64;++j) weights[j]=0.0f;
    #pragma unroll 1
    for (int n=0;n<9;++n) {
        float wx[6],wy[6];
        if (!axis_weights(qx[n],ix[n],wx) || !axis_weights(qy[n],iy[n],wy)) return 2;
        const float area = (float)__dmul_rn(quadrature[n/3],quadrature[n%3]);
        #pragma unroll 1
        for (int y=0;y<6;++y) {
            #pragma unroll 1
            for (int x=0;x<6;++x) {
                const int p=(iy[n]-2+y-ymin)*8+(ix[n]-2+x-xmin);
                const float v=__fmul_rn(__fmul_rn(wy[y],wx[x]),area);
                weights[p]=__fadd_rn(weights[p],v);
            }
        }
    }
    float mass=0.0f;
    #pragma unroll 1
    for (int y=0;y<*rh;++y) {
        #pragma unroll 1
        for (int x=0;x<*rw;++x) mass=__fadd_rn(mass,weights[y*8+x]);
    }
    if (!isfinite(mass) || mass<=0.0f) return 2;
    #pragma unroll 1
    for (int y=0;y<*rh;++y) {
        #pragma unroll 1
        for (int x=0;x<*rw;++x) {
            const int j=y*8+x;
            weights[j]=__fdiv_rn(weights[j],mass);
            if (!isfinite(weights[j])) return 2;
        }
    }
    return 0;
}

extern "C" __global__ void measurement_forward(
    const float* __restrict__ field, float* __restrict__ measured, int* status,
    int fh,int fw,long long ox,long long oy,int width,int height,
    double a00,double a01,double a02,double a10,double a11,double a12,
    int c0,int c1,int c2,int c3) {
    const long long i=(long long)blockIdx.x*blockDim.x+threadIdx.x;
    if (i >= (long long)width*height) return;
    const long long px=ox+i%width,py=oy+i/width;
    const int map[4]={c0,c1,c2,c3};
    const int c=map[2*(py&1)+(px&1)];
    float w[64]; int left,top,rw,rh;
    const int error=make_row(px,py,fh,fw,a00,a01,a02,a10,a11,a12,w,&left,&top,&rw,&rh);
    if (error) { atomicOr(status,error); measured[i]=0.0f; return; }
    float sum=0.0f;
    #pragma unroll 1
    for (int y=0;y<rh;++y) {
        #pragma unroll 1
        for (int x=0;x<rw;++x) {
            const float value=field[((long long)(top+y)*fw+left+x)*3+c];
            if (!isfinite(value)) { atomicOr(status,4); measured[i]=0.0f; return; }
            sum=__fadd_rn(sum,__fmul_rn(w[y*8+x],value));
        }
    }
    if (!isfinite(sum)) atomicOr(status,4);
    measured[i]=sum;
}

extern "C" __global__ void measurement_adjoint(
    const float* __restrict__ measured, float* __restrict__ field, int* status,
    int fh,int fw,long long ox,long long oy,int width,int height,
    double a00,double a01,double a02,double a10,double a11,double a12,
    int c0,int c1,int c2,int c3) {
    const long long i=(long long)blockIdx.x*blockDim.x+threadIdx.x;
    if (i >= (long long)width*height) return;
    const float value=measured[i];
    if (!isfinite(value)) { atomicOr(status,4); return; }
    const long long px=ox+i%width,py=oy+i/width;
    const int map[4]={c0,c1,c2,c3};
    const int c=map[2*(py&1)+(px&1)];
    float w[64]; int left,top,rw,rh;
    const int error=make_row(px,py,fh,fw,a00,a01,a02,a10,a11,a12,w,&left,&top,&rw,&rh);
    if (error) { atomicOr(status,error); return; }
    #pragma unroll 1
    for (int y=0;y<rh;++y) {
        #pragma unroll 1
        for (int x=0;x<rw;++x) {
            const float increment=__fmul_rn(w[y*8+x],value);
            if (!isfinite(increment)) { atomicOr(status,4); return; }
            const long long p=((long long)(top+y)*fw+left+x)*3+c;
            const float old=atomicAdd(field+p,increment);
            if (!isfinite(old) || !isfinite(__fadd_rn(old,increment))) atomicOr(status,4);
        }
    }
}
'''


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def signature(lib, name, result, args):
    function = getattr(lib, name)
    function.restype, function.argtypes = result, args
    return function


class MeasurementGpu:
    def __init__(self, torch, field_hw, *, device_limit_bytes=8 << 30, diagnostic_channel_map=None):
        require(os.name == "nt" and C.sizeof(C.c_void_p) == 8,
                "CFA measurement requires the pinned Windows x64 runtime")
        self.torch = torch
        self.helper_sha256 = digest(__file__)
        require(len(field_hw) == 2 and all(type(v) is int and 8 <= v <= 8192 for v in field_hw),
                "global latent field dimensions must be bounded integers")
        require(type(device_limit_bytes) is int and 0 < device_limit_bytes <= 24 << 30,
                "invalid Torch device allocation limit")
        require(digest(CPU_PATH) == CPU_SHA256, "frozen CPU measurement reference changed")
        self.field_hw = tuple(field_hw)
        self.device_limit_bytes = device_limit_bytes
        self.channel_map = (0, 1, 1, 2) if diagnostic_channel_map is None else tuple(diagnostic_channel_map)
        require(len(self.channel_map) == 4 and all(type(v) is int and 0 <= v < 3 for v in self.channel_map),
                "invalid diagnostic physical-phase channel map")
        self.diagnostic = diagnostic_channel_map is not None
        self.launches = {"forward": 0, "adjoint": 0}
        self.sensels = {"forward": 0, "adjoint": 0}
        self.seconds = {"forward": 0.0, "adjoint": 0.0}
        self.refusals = 0
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
        # The first measurement object may precede any caller image allocation.
        # Let Torch initialize/own its context through an ordinary allocation;
        # never create, push or replace a context through the driver API.
        self.context_anchor = torch.empty(1, dtype=torch.float32, device="cuda:0")
        self.context = self.current_context()
        require(self.context != 0 and torch.cuda.current_device() == 0,
                "Torch CUDA context must already be current on device0")
        started = time.monotonic()
        program = vp()
        self.nvcheck(self.nv_create(C.byref(program), CUDA_SOURCE.encode("ascii"),
                                   b"strehl_integrated_cfa_measurement.cu", 0, None, None), "nvrtcCreateProgram")
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
        # --fmad=false and explicit rounded intrinsics govern our row arithmetic.
        # Precise libdevice sinf can internally use explicit FMA; this is not the
        # old ordered-FIR no-transcendental kernel, so record rather than ban it.
        self.ptx_fma_instruction_lines = sum(b"fma." in line or b"mad.f32" in line for line in ptx.splitlines())
        require(b"mul.rn.f32" in ptx and b"add.rn.f32" in ptx,
                "CFA measurement PTX lacks explicit rounded f32 multiply/add")
        self.ptx_sha256 = hashlib.sha256(ptx).hexdigest()
        self.before_module = self.device_memory()
        self.module = vp()
        self.cucheck(self.cu_load(C.byref(self.module), self.ptx), "cuModuleLoadData")
        self.functions = {}
        for axis in ("forward", "adjoint"):
            function = vp()
            self.cucheck(self.cu_function(C.byref(function), self.module,
                                         ("measurement_" + axis).encode()), "cuModuleGetFunction")
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

    def _budget(self):
        t = self.torch
        observed = {
            "allocated_bytes": t.cuda.memory_allocated(0),
            "reserved_bytes": t.cuda.memory_reserved(0),
            "peak_allocated_bytes": t.cuda.max_memory_allocated(0),
            "peak_reserved_bytes": t.cuda.max_memory_reserved(0),
        }
        require(max(observed.values()) <= self.device_limit_bytes,
                "Torch allocator exceeds declared device budget")
        return observed

    def _tensor(self, tensor, shape):
        t = self.torch
        require(tuple(tensor.shape) == tuple(shape) and tensor.is_contiguous()
                and tensor.dtype == t.float32 and tensor.device.type == "cuda"
                and tensor.device.index == 0,
                "measurement requires contiguous Torch cuda0 f32 with exact shape")

    def _geometry(self, source_xywh, source_to_latent_2x3):
        require(len(source_xywh) == 4 and all(type(v) is int for v in source_xywh),
                "source rectangle must contain four Python integers")
        ox, oy, width, height = source_xywh
        require(0 <= ox <= 2**31-1 and 0 <= oy <= 2**31-1
                and 1 <= width <= 8192 and 1 <= height <= 8192
                and ox + width <= 2**31 and oy + height <= 2**31
                and width * height <= MAX_RECT_SENSELS,
                "source rectangle outside explicit bounds")
        require(len(source_to_latent_2x3) == 2
                and all(len(row) == 3 for row in source_to_latent_2x3),
                "source-to-latent map must be 2x3")
        affine = tuple(float(v) for row in source_to_latent_2x3 for v in row)
        require(all(math.isfinite(v) for v in affine), "nonfinite physical affine map")
        a, b, c, d, e, f = affine
        require(abs(a) + abs(b) <= 2 and abs(d) + abs(e) <= 2
                and a * e - b * d != 0,
                "affine exceeds fixed eight-site row support or is singular")
        # Affine coordinate extrema occur at rectangle corners. Evaluate all
        # quadrature nodes there; this refuses before any caller-owned out is
        # touched. The CUDA row builder independently checks every actual row.
        sub = (-0.38729833462074168852, 0.0, 0.38729833462074168852)
        fh, fw = self.field_hw
        for y in (oy, oy + height - 1):
            for x in (ox, ox + width - 1):
                for dy in sub:
                    for dx in sub:
                        qx = (a * (x + dx) + b * (y + dy)) + c
                        qy = (d * (x + dx) + e * (y + dy)) + f
                        if not (math.isfinite(qx) and math.isfinite(qy)
                                and 2 <= qx < fw - 3 and 2 <= qy < fh - 3):
                            raise ValueError("unsupported original-sensor footprint: no latent extension permitted")
        return (ox, oy, width, height), affine

    def _apply(self, operation, data, source_xywh, affine, out=None):
        started = time.monotonic()
        t = self.torch
        rect, coefficients = self._geometry(source_xywh, affine)
        ox, oy, width, height = rect
        fh, fw = self.field_hw
        require(self.current_context() == self.context and t.cuda.current_device() == 0,
                "current Torch CUDA context changed")
        self._budget()
        if operation == "forward":
            self._tensor(data, (fh, fw, 3))
            output = t.empty((height, width), dtype=t.float32, device=data.device)
        else:
            self._tensor(data, (height, width))
            output = t.zeros((fh, fw, 3), dtype=t.float32, device=data.device) if out is None else out
            self._tensor(output, (fh, fw, 3))
            # Atomic accumulation must never race with the residual read.
            dp, op = data.data_ptr(), output.data_ptr()
            require(dp + data.numel()*4 <= op or op + output.numel()*4 <= dp,
                    "adjoint residual aliases its output")
        status = t.zeros(1, dtype=t.int32, device=data.device)
        self._budget()
        stream = t.cuda.current_stream(0)
        for tensor in (data, output, status):
            tensor.record_stream(stream)
        values = [C.c_void_p(data.data_ptr()), C.c_void_p(output.data_ptr()),
                  C.c_void_p(status.data_ptr()), C.c_int(fh), C.c_int(fw),
                  C.c_longlong(ox), C.c_longlong(oy), C.c_int(width), C.c_int(height),
                  *(C.c_double(v) for v in coefficients),
                  *(C.c_int(v) for v in self.channel_map)]
        params = (C.c_void_p * len(values))(*(C.cast(C.byref(v), C.c_void_p) for v in values))
        count = width * height
        self.cucheck(self.cu_launch(self.functions[operation], (count+127)//128, 1, 1,
            128, 1, 1, 0, C.c_void_p(stream.cuda_stream), params, None), "cuLaunchKernel")
        self.launches[operation] += 1
        self.sensels[operation] += count
        self.streams.add(stream.cuda_stream)
        # This scalar synchronization both surfaces runtime errors and makes
        # the returned output/status concrete. No latent field is copied out.
        code = int(status.item())
        self.seconds[operation] += time.monotonic() - started
        if code:
            self.refusals += 1
            error = ValueError if code == 1 else RuntimeError
            raise error("CFA measurement refused: status=" + str(code)
                        + " (1=support,2=row weights,4=nonfinite). Discard supplied adjoint out.")
        self._budget()
        return output

    def forward(self, x, source_xywh, source_to_latent_2x3):
        """Measure one source rectangle from the global HWC camera-RGB field."""
        return self._apply("forward", x, source_xywh, source_to_latent_2x3)

    def adjoint(self, y, source_xywh, source_to_latent_2x3, out=None):
        """Transpose into global HWC; out=None zeros, supplied out accumulates."""
        return self._apply("adjoint", y, source_xywh, source_to_latent_2x3, out=out)

    def metadata(self, strict=True):
        observed = {}
        for name, path in {"helper": Path(__file__), "cpu_reference": CPU_PATH, **self.paths}.items():
            try:
                observed[name] = digest(path)
            except OSError:
                observed[name] = None
        unchanged = (observed["helper"] == self.helper_sha256
                     and observed["cpu_reference"] == CPU_SHA256
                     and all(observed[k] == self.library_hashes[k] for k in self.paths))
        if strict:
            require(unchanged, "measurement source, CPU reference or CUDA DLL changed during worker")
        return {
            "schema": 1, "backend": "original-cfa-integrated-lanczos3-cuda-f32",
            "measurement_only": True, "reconstruction_quality_claim": False,
            "helper_sha256": self.helper_sha256, "cpu_reference_sha256": CPU_SHA256,
            "bindings_unchanged": unchanged, "observed_file_sha256": observed,
            "cuda_source_sha256": hashlib.sha256(CUDA_SOURCE.encode("ascii")).hexdigest(),
            "field_hw": list(self.field_hw), "physical_phase_channels": list(self.channel_map),
            "diagnostic_channel_override": self.diagnostic,
            "max_rectangle_sensels": MAX_RECT_SENSELS,
            "max_affine_linear_row_absolute_sum": 2,
            "quadrature": "GL3xGL3 source unit square, dy-major then dx; f64 geometry; f32 product weights",
            "row_normalization": "axis-normalize then coalesce nine stencils, then normalize row mass",
            "source_rectangle_coordinates": "absolute original active-sensor coordinates; RGGB at (0,0)",
            "value_units": "linear camera DN or caller-declared common linear scale; A has unit DC response",
            "support_policy": "all six taps of all nine nodes must be in global latent field; refuse otherwise",
            "finite_policy": "consumed field/residual and touched adjoint accumulator sites checked; untouched field sites are caller-owned",
            "arithmetic": "f32 explicit rounded products/additions; f64 geometry; precise sinf; no fast-math/f16/TF32",
            "adjoint_reduction": "f32 atomicAdd, order nondeterministic; numerical comparison required",
            "libraries": {k: {"path": str(p), "sha256": self.library_hashes[k]} for k,p in self.paths.items()},
            "nvrtc_version": self.nvrtc_version, "driver_version": self.driver_version,
            "supported_architectures": self.supported_archs, "device_architecture": self.arch,
            "compiler_options": self.options, "compile_seconds": self.compile_seconds,
            "compile_log": self.compile_log, "ptx_sha256": self.ptx_sha256,
            "ptx_bytes_including_terminator": len(self.ptx.raw),
            "ptx_fma_instruction_lines_including_libdevice": self.ptx_fma_instruction_lines,
            "current_context_handle": self.context, "torch_stream_handles": sorted(self.streams),
            "kernel_launches": dict(self.launches), "processed_sensels": dict(self.sensels),
            "synchronized_call_seconds": dict(self.seconds), "kernel_refusals": self.refusals,
            "device_limit_bytes": self.device_limit_bytes,
            "torch_memory": self._budget(),
            "module_memory": {"before_load": self.before_module, "after_load": self.after_module,
                "scope": "driver/JIT/local spill memory outside Torch cap; whole-device free delta descriptive"},
            "storage": "Torch-owned global field and bounded measured/residual rectangle; at most64 coalesced weights per CUDA thread; no sparse matrix or node cube",
        }

