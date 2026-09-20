"""Fixed-pupil coupled visibility stencil. No fitter; compilation is lazy."""
import ctypes as ct
from dataclasses import dataclass
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import numpy as np
import torch
from torch.autograd.function import once_differentiable

HERE = Path(__file__).resolve().parent
MODEL_SHA = "5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if sha(HERE/"model.py") != MODEL_SHA:
    raise AssertionError("frozen optical model changed")
spec = importlib.util.spec_from_file_location("pupil_stencil_frozen_model", HERE/"model.py")
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def _array_sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _pupil(pupil):
    a = np.asarray(pupil, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2 or not 1 <= len(a) <= 16384:
        raise ValueError("one to16384 explicit equal-weight pupil points required")
    if not np.isfinite(a).all() or np.any(np.sum(a*a, axis=1) > 1.000001):
        raise ValueError("finite unit-disc pupil points required")
    return np.ascontiguousarray(a)


@dataclass(frozen=True)
class JointTable:
    offsets: np.ndarray             # int32[K,4]: px,py,qx,qy
    weights: np.ndarray             # float32[K], same-ray joint mass
    near_offsets: np.ndarray        # int32[M,2]: px,py
    near_weights: np.ndarray        # float32[M], marginal of stored joint mass
    metadata: dict


def build_table(pupil_xy, near_shift, far_shift):
    pupil = _pupil(pupil_xy)
    shifts = np.asarray([near_shift, far_shift], dtype=np.float64)
    if not np.isfinite(shifts).all() or np.any(np.abs(shifts) > 24):
        raise ValueError("finite supplied shifts in[-24,24] native pixels required")

    def tents(shift):
        position = pupil*shift
        lower = np.floor(position).astype(np.int32)
        f = position-lower
        offsets = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.int32)
        weights = np.stack(((1-f[:, 0])*(1-f[:, 1]), f[:, 0]*(1-f[:, 1]),
                            (1-f[:, 0])*f[:, 1], f[:, 0]*f[:, 1]), axis=1)
        return lower[:, None, :]+offsets[None], weights

    p, pw = tents(float(shifts[0]))
    q, qw = tents(float(shifts[1]))
    # Enumerate the16 products for EACH SAME ray, never an outer product of marginals.
    entries = np.concatenate((np.broadcast_to(p[:, :, None, :], (len(p), 4, 4, 2)),
                              np.broadcast_to(q[:, None, :, :], (len(q), 4, 4, 2))), axis=3).reshape(-1, 4)
    mass = (pw[:, :, None]*qw[:, None, :]/len(pupil)).reshape(-1)
    positive = mass > 0
    offsets, inverse = np.unique(entries[positive], axis=0, return_inverse=True)
    accumulated = np.bincount(inverse, weights=mass[positive], minlength=len(offsets))
    weights = accumulated.astype(np.float32)
    near_offsets, near_inverse = np.unique(offsets[:, :2], axis=0, return_inverse=True)
    near_weights = np.bincount(near_inverse, weights=weights.astype(np.float64),
                               minlength=len(near_offsets)).astype(np.float32)
    if not 1 <= len(weights) <= 65536 or np.any(weights <= 0) or not np.isfinite(weights).all():
        raise ValueError("invalid or excessive joint table")
    if abs(float(accumulated.sum())-1) > 1e-12 or abs(float(weights.astype(np.float64).sum())-1) > 1e-6:
        raise ArithmeticError("joint mass is not unity within declared rounding")
    arrays = [np.ascontiguousarray(a) for a in (offsets, weights, near_offsets, near_weights)]
    for a in arrays:
        a.setflags(write=False)
    metadata = dict(pupil_count=len(pupil), pupil_sha256=_array_sha(pupil),
        near_shift=float(shifts[0]), far_shift=float(shifts[1]), entries=len(weights),
        near_entries=len(near_weights), joint_sum_f64=float(accumulated.sum()),
        stored_joint_sum_f64=float(weights.astype(np.float64).sum()),
        bytes=sum(a.nbytes for a in arrays), array_sha256=[_array_sha(a) for a in arrays],
        setup="f64 same-ray bilinear-product aggregation; stored f32; no renormalization")
    return JointTable(*arrays, metadata)


CUDA_SOURCE = r'''
__device__ __forceinline__ float one(const float* v,int x,int y,int w,int h) {
    return (x>=0 && x<w && y>=0 && y<h) ? v[y*w+x] : 0.0f;
}
__device__ __forceinline__ float rgb(const float* v,int x,int y,int c,int w,int h) {
    return (x>=0 && x<w && y>=0 && y<h) ? v[3*(y*w+x)+c] : 0.0f;
}
extern "C" __global__ void coupled_forward(
    const float* n,const float* f,const float* a,float* out,
    const int* joint,const float* jw,const int* marginal,const float* mw,
    int w,int h,int k,int m) {
    int z=(int)(blockIdx.x*blockDim.x+threadIdx.x); if(z>=w*h)return;
    int x=z%w,y=z/w; float v[3]={0.0f,0.0f,0.0f};
    for(int i=0;i<m;++i) {
        int px=x+marginal[2*i],py=y+marginal[2*i+1];
        float alpha=one(a,px,py,w,h);
        for(int c=0;c<3;++c)v[c]+=mw[i]*(alpha*rgb(n,px,py,c,w,h));
    }
    for(int i=0;i<k;++i) {
        int px=x+joint[4*i],py=y+joint[4*i+1];
        int qx=x+joint[4*i+2],qy=y+joint[4*i+3];
        float transmission=1.0f-one(a,px,py,w,h);
        for(int c=0;c<3;++c)v[c]+=jw[i]*(transmission*rgb(f,qx,qy,c,w,h));
    }
    for(int c=0;c<3;++c)out[3*z+c]=v[c];
}
extern "C" __global__ void coupled_backward(
    const float* n,const float* f,const float* a,const float* e,
    float* dn,float* df,float* da,
    const int* joint,const float* jw,const int* marginal,const float* mw,
    int w,int h,int k,int m) {
    int z=(int)(blockIdx.x*blockDim.x+threadIdx.x); if(z>=w*h)return;
    int x=z%w,y=z/w; float t[3]={0.0f,0.0f,0.0f},b[3]={0.0f,0.0f,0.0f};
    for(int i=0;i<m;++i) {
        int ex=x-marginal[2*i],ey=y-marginal[2*i+1];
        for(int c=0;c<3;++c)t[c]+=mw[i]*rgb(e,ex,ey,c,w,h);
    }
    float av=0.0f;
    for(int c=0;c<3;++c) { dn[3*z+c]=a[z]*t[c]; av+=n[3*z+c]*t[c]; }
    for(int i=0;i<k;++i) {
        int px=joint[4*i],py=joint[4*i+1],qx=joint[4*i+2],qy=joint[4*i+3];
        float transmission=1.0f-one(a,x+px-qx,y+py-qy,w,h);
        float dot=0.0f;
        for(int c=0;c<3;++c) {
            b[c]+=jw[i]*(transmission*rgb(e,x-qx,y-qy,c,w,h));
            dot+=rgb(e,x-px,y-py,c,w,h)*rgb(f,x+qx-px,y+qy-py,c,w,h);
        }
        av-=jw[i]*dot;
    }
    for(int c=0;c<3;++c)df[3*z+c]=b[c];
    da[z]=av;
}
'''


class _Runtime:
    def __init__(self):
        if os.name != "nt" or ct.sizeof(ct.c_void_p) != 8:
            raise RuntimeError("commissioned loader scope is Windows x64")
        if torch.cuda.is_current_stream_capturing():
            raise RuntimeError("CUDA graph capture unsupported")
        self.device = torch.cuda.current_device()
        lib = Path(torch.__file__).resolve().parent/"lib"
        self.dll_directory = os.add_dll_directory(str(lib))
        nvpath, drvpath = lib/"nvrtc64_120_0.dll", Path(os.environ["SystemRoot"])/"System32"/"nvcuda.dll"
        self.nv, self.drv = ct.CDLL(str(nvpath)), ct.WinDLL(str(drvpath))
        P, I, U, S, C = ct.c_void_p, ct.c_int, ct.c_uint, ct.c_size_t, ct.c_char_p
        PP, PI, PC = ct.POINTER(P), ct.POINTER(I), ct.POINTER(C)

        def bind(dll, name, args, result=I):
            fun = getattr(dll, name); fun.argtypes, fun.restype = args, result
            return fun
        self.nv_error = bind(self.nv, "nvrtcGetErrorString", [I], C)
        self.nv_version = bind(self.nv, "nvrtcVersion", [PI, PI])
        self.nv_arch_count = bind(self.nv, "nvrtcGetNumSupportedArchs", [PI])
        self.nv_archs = bind(self.nv, "nvrtcGetSupportedArchs", [PI])
        self.create = bind(self.nv, "nvrtcCreateProgram", [PP, C, C, I, PC, PC])
        self.compile = bind(self.nv, "nvrtcCompileProgram", [P, I, PC])
        self.log_size = bind(self.nv, "nvrtcGetProgramLogSize", [P, ct.POINTER(S)])
        self.log_get = bind(self.nv, "nvrtcGetProgramLog", [P, P])
        self.ptx_size = bind(self.nv, "nvrtcGetPTXSize", [P, ct.POINTER(S)])
        self.ptx_get = bind(self.nv, "nvrtcGetPTX", [P, P])
        self.destroy = bind(self.nv, "nvrtcDestroyProgram", [PP])
        self.driver_error = bind(self.drv, "cuGetErrorString", [I, PC])
        self.ctx_get = bind(self.drv, "cuCtxGetCurrent", [PP])
        self.ctx_device = bind(self.drv, "cuCtxGetDevice", [PI])
        self.module_load = bind(self.drv, "cuModuleLoadDataEx", [PP, P, U, PI, PP])
        self.function_get = bind(self.drv, "cuModuleGetFunction", [PP, P, C])
        self.launch_kernel = bind(self.drv, "cuLaunchKernel", [P]+[U]*7+[P, PP, PP])
        self.context = P()
        self.check_driver(self.ctx_get(ct.byref(self.context)))
        if not self.context.value:
            raise RuntimeError("Torch must already own an initialized current CUDA context")
        self.check_context()
        major, minor, count = I(), I(), I()
        self.check_nv(self.nv_version(ct.byref(major), ct.byref(minor)))
        self.check_nv(self.nv_arch_count(ct.byref(count)))
        if not 1 <= count.value <= 256:
            raise RuntimeError("invalid compiler architecture inventory")
        archs = (I*count.value)(); self.check_nv(self.nv_archs(archs))
        capability = torch.cuda.get_device_capability(self.device)
        arch = capability[0]*10+capability[1]
        if arch not in list(archs):
            raise RuntimeError("current GPU architecture is not supported by bundled NVRTC")
        options = [f"--gpu-architecture=compute_{arch}", "--std=c++11", "--fmad=false", "--ftz=false",
                   "--prec-div=true", "--prec-sqrt=true"]
        opts = (C*len(options))(*(x.encode() for x in options))
        program = P()
        self.check_nv(self.create(ct.byref(program), CUDA_SOURCE.encode(), b"pupil-stencil.cu", 0, None, None))
        try:
            status = self.compile(program, len(options), opts)
            length = S(); self.check_nv(self.log_size(program, ct.byref(length)))
            log = ct.create_string_buffer(max(1, length.value)); self.check_nv(self.log_get(program, log))
            self.compile_log = log.value.decode(errors="replace")
            if status:
                raise RuntimeError(f"NVRTC compile: {self.nv_error(status).decode()}\n{self.compile_log}")
            self.check_nv(self.ptx_size(program, ct.byref(length)))
            ptx = ct.create_string_buffer(length.value); self.check_nv(self.ptx_get(program, ptx))
        finally:
            self.check_nv(self.destroy(ct.byref(program)))
        self.module = P()
        self.check_driver(self.module_load(ct.byref(self.module), ptx, 0, None, None))
        self.functions = {}
        for name in ("coupled_forward", "coupled_backward"):
            fun = P(); self.check_driver(self.function_get(ct.byref(fun), self.module, name.encode()))
            self.functions[name] = fun
        # Module and DLL handles live for the process, including every asynchronous launch.
        self.metadata = dict(nvrtc_path=str(nvpath), driver_path=str(drvpath),
            nvrtc_version=[major.value, minor.value], device=self.device, capability=list(capability),
            compile_options=options, compile_log=self.compile_log,
            cuda_source_sha256=hashlib.sha256(CUDA_SOURCE.encode()).hexdigest(),
            ptx_sha256=hashlib.sha256(ptx.raw).hexdigest(), context=int(self.context.value))

    def check_nv(self, status):
        if status:
            raise RuntimeError("NVRTC: "+self.nv_error(status).decode(errors="replace"))

    def check_driver(self, status):
        if status:
            text = ct.c_char_p(); self.driver_error(status, ct.byref(text))
            raise RuntimeError(f"CUDA driver {status}: {text.value!r}")

    def check_context(self):
        context, device = ct.c_void_p(), ct.c_int()
        self.check_driver(self.ctx_get(ct.byref(context)))
        self.check_driver(self.ctx_device(ct.byref(device)))
        if context.value != self.context.value or device.value != self.device or torch.cuda.current_device() != self.device:
            raise RuntimeError("CUDA context/device changed; multi-device use unsupported")

    def launch(self, name, tensors, integers, pixels):
        self.check_context()
        if torch.cuda.is_current_stream_capturing():
            raise RuntimeError("CUDA graph capture unsupported")
        stream = torch.cuda.current_stream(self.device)
        arguments = [ct.c_void_p(t.data_ptr()) for t in tensors]+[ct.c_int(v) for v in integers]
        pointers = (ct.c_void_p*len(arguments))(*(ct.cast(ct.pointer(v), ct.c_void_p) for v in arguments))
        self.check_driver(self.launch_kernel(self.functions[name], (pixels+127)//128, 1, 1,
            128, 1, 1, 0, ct.c_void_p(stream.cuda_stream), pointers, None))
        for tensor in tensors:
            tensor.record_stream(stream)


_RUNTIME = None


def runtime_metadata():
    """Does not initialize CUDA/compiler; return metadata only after a kernel call."""
    return None if _RUNTIME is None else dict(_RUNTIME.metadata)


def _runtime():
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = _Runtime()
    return _RUNTIME


class _Joint(torch.autograd.Function):
    @staticmethod
    def forward(ctx, near, far, alpha, table):
        runtime = _runtime()
        arrays = (table.offsets, table.weights, table.near_offsets, table.near_weights)
        buffers = tuple(torch.tensor(np.array(a, copy=True), device=near.device) for a in arrays)
        out = torch.empty_like(near)
        h, w = alpha.shape
        runtime.launch("coupled_forward", (near, far, alpha, out)+buffers,
                       (w, h, len(table.weights), len(table.near_weights)), w*h)
        if not bool(torch.isfinite(out).all()):
            raise FloatingPointError("nonfinite stencil output")
        ctx.save_for_backward(near, far, alpha, *buffers)
        ctx.geometry = (w, h, len(table.weights), len(table.near_weights))
        return out

    @staticmethod
    @once_differentiable
    def backward(ctx, incoming):
        near, far, alpha, *buffers = ctx.saved_tensors
        e = incoming.contiguous()
        if not bool(torch.isfinite(e).all()):
            raise FloatingPointError("nonfinite incoming adjoint")
        dn, df, da = torch.empty_like(near), torch.empty_like(far), torch.empty_like(alpha)
        w, h, _, _ = ctx.geometry
        _runtime().launch("coupled_backward", (near, far, alpha, e, dn, df, da)+tuple(buffers),
                          ctx.geometry, w*h)
        if not all(bool(torch.isfinite(g).all()) for g in (dn, df, da)):
            raise FloatingPointError("nonfinite stencil adjoint")
        return dn, df, da, None


def joint_pupil(near, far, alpha, table):
    """Pre-PSF coupled RGB with fixed table; f32 CUDA, no capture/higher-order AD."""
    if not isinstance(table, JointTable):
        raise TypeError("build_table output required")
    if any(t.device.type != "cuda" or t.dtype != torch.float32 or not t.is_contiguous() for t in (near, far, alpha)):
        raise ValueError("contiguous CUDAf32 latents required")
    if near.device != far.device or near.device != alpha.device or near.device.index != torch.cuda.current_device():
        raise ValueError("latents must share the current CUDA device")
    if torch.cuda.is_current_stream_capturing():
        raise RuntimeError("CUDA graph capture unsupported")
    if alpha.ndim != 2 or not all(1 <= n <= 96 for n in alpha.shape) or near.shape != (*alpha.shape, 3) or far.shape != near.shape:
        raise ValueError("native1..96 HW/HWC geometry required")
    if not all(bool(torch.isfinite(t).all()) for t in (near, far, alpha)):
        raise ValueError("finite latent inputs required")
    if bool((near < 0).any() or (far < 0).any() or (alpha < 0).any() or (alpha > 1).any()):
        raise ValueError("nonnegative radiance and physical coverage required")
    arrays = (table.offsets, table.weights, table.near_offsets, table.near_weights)
    if [_array_sha(a) for a in arrays] != table.metadata["array_sha256"]:
        raise ValueError("table changed after setup")
    return _Joint.apply(near, far, alpha, table)


def forward(near, far, alpha, config, index, *, pupil, table=None):
    """Same original common PSF after coupled integration; no CFA/black added."""
    if not 0 <= index < len(config.focus_coordinates) or alpha.shape != (config.height, config.width):
        raise ValueError("invalid original optical index/geometry")
    points = _pupil(pupil)
    f = config.focus_coordinates[index]
    ns, fs = (config.defocus_scale*(f-d) for d in config.inverse_depths)
    if table is None:
        table = build_table(points, ns, fs)
    if table.metadata["pupil_sha256"] != _array_sha(points) or (table.metadata["near_shift"], table.metadata["far_shift"]) != (ns, fs):
        raise ValueError("table does not match supplied pupil/focus geometry")
    return model._blur(joint_pupil(near, far, alpha, table), config.psf_sigma)
