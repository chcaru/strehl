"""Explicit paired A(x), A(ones) extension of the frozen measurement source.

No frozen file is edited. A private module compiles its literal CUDA source
plus the additional kernel below. The wrapper and combined source are bound.
"""
from pathlib import Path
import ctypes as C
import hashlib
import importlib.util
import sys
import time

FROZEN = Path(__file__).resolve().parent.parent / 'direct-cfa-forward-gpu/measurement-gpu.py'
FROZEN_SHA = '8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84'
source_bytes = FROZEN.read_bytes()
if hashlib.sha256(source_bytes).hexdigest() != FROZEN_SHA:
    raise ValueError('frozen measurement changed')
spec = importlib.util.spec_from_file_location('paired_measurement_private_frozen', FROZEN)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
exec(compile(source_bytes, str(FROZEN), 'exec'), base.__dict__)

PAIRED_SOURCE = r'''
extern "C" __global__ void measurement_paired(
    const float* __restrict__ field, float* __restrict__ measured,
    float* __restrict__ dc, int* status,
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
    if (error) { atomicOr(status,error); measured[i]=0.0f; dc[i]=0.0f; return; }
    float sum=0.0f,constant=0.0f;
    #pragma unroll 1
    for (int y=0;y<rh;++y) {
        #pragma unroll 1
        for (int x=0;x<rw;++x) {
            const float value=field[((long long)(top+y)*fw+left+x)*3+c];
            if (!isfinite(value)) { atomicOr(status,4); measured[i]=0.0f; dc[i]=0.0f; return; }
            sum=__fadd_rn(sum,__fmul_rn(w[y*8+x],value));
            constant=__fadd_rn(constant,__fmul_rn(w[y*8+x],1.0f));
        }
    }
    if (!isfinite(sum) || !isfinite(constant)) atomicOr(status,4);
    measured[i]=sum;
    dc[i]=constant;
}
'''

FROZEN_CUDA_SHA = hashlib.sha256(base.CUDA_SOURCE.encode('ascii')).hexdigest()
base.CUDA_SOURCE = base.CUDA_SOURCE + '\n' + PAIRED_SOURCE
COMBINED_CUDA_SHA = hashlib.sha256(base.CUDA_SOURCE.encode('ascii')).hexdigest()


class PairedMeasurementGpu(base.MeasurementGpu):
    def __init__(self, torch, field_hw, *, device_limit_bytes=8 << 30,
                 diagnostic_channel_map=None):
        self.wrapper_sha = base.digest(__file__)
        super().__init__(torch, field_hw, device_limit_bytes=device_limit_bytes,
                         diagnostic_channel_map=diagnostic_channel_map)
        function = C.c_void_p()
        self.cucheck(self.cu_function(C.byref(function), self.module,
                                     b'measurement_paired'), 'cuModuleGetFunction paired')
        self.functions['paired'] = function
        self.launches['paired'] = 0
        self.sensels['paired'] = 0
        self.seconds['paired'] = 0.0

    def forward_pair(self, x, source_xywh, source_to_latent_2x3):
        """Return A(x), actual f32 A(ones); one shared row construction."""
        started = time.perf_counter()
        t = self.torch
        rect, coefficients = self._geometry(source_xywh, source_to_latent_2x3)
        ox, oy, width, height = rect
        fh, fw = self.field_hw
        base.require(self.current_context() == self.context and t.cuda.current_device() == 0,
                     'current Torch CUDA context changed')
        self._tensor(x, (fh, fw, 3))
        self._budget()
        measured = t.empty((height, width), dtype=t.float32, device=x.device)
        dc = t.empty_like(measured)
        status = t.zeros(1, dtype=t.int32, device=x.device)
        self._budget()
        stream = t.cuda.current_stream(0)
        for tensor in (x, measured, dc, status):
            tensor.record_stream(stream)
        values = [C.c_void_p(x.data_ptr()), C.c_void_p(measured.data_ptr()),
                  C.c_void_p(dc.data_ptr()), C.c_void_p(status.data_ptr()),
                  C.c_int(fh), C.c_int(fw), C.c_longlong(ox), C.c_longlong(oy),
                  C.c_int(width), C.c_int(height),
                  *(C.c_double(v) for v in coefficients),
                  *(C.c_int(v) for v in self.channel_map)]
        params = (C.c_void_p * len(values))(*(C.cast(C.byref(v), C.c_void_p) for v in values))
        count = width * height
        self.cucheck(self.cu_launch(self.functions['paired'], (count+127)//128, 1, 1,
            128, 1, 1, 0, C.c_void_p(stream.cuda_stream), params, None), 'cuLaunchKernel paired')
        self.launches['paired'] += 1
        self.sensels['paired'] += count
        self.streams.add(stream.cuda_stream)
        code = int(status.item())
        self.seconds['paired'] += time.perf_counter() - started
        if code:
            self.refusals += 1
            error = ValueError if code == 1 else RuntimeError
            raise error('paired original-CFA measurement refused: status=' + str(code))
        self._budget()
        return measured, dc

    forward_with_dc = forward_pair

    def metadata(self, strict=True):
        result = super().metadata(strict=strict)
        wrapper_unchanged = base.digest(__file__) == self.wrapper_sha
        if strict:
            base.require(wrapper_unchanged, 'paired measurement wrapper changed')
        result['paired_extension'] = dict(
            wrapper_path=str(Path(__file__).resolve()), wrapper_sha256=self.wrapper_sha,
            wrapper_unchanged=wrapper_unchanged, frozen_source_sha256=FROZEN_SHA,
            frozen_cuda_sha256=FROZEN_CUDA_SHA, combined_cuda_sha256=COMBINED_CUDA_SHA,
            appended_cuda_sha256=hashlib.sha256(PAIRED_SOURCE.encode('ascii')).hexdigest(),
            semantics='literal frozen row builder; same-order A(x) and A(ones), no analytical DC substitution',
            paired_timing='synchronized QueryPerformanceCounter; inherited separate-call counters use coarse monotonic',
            original_file_changed=False, equivalence_claim='requires independent paired versus separate controls')
        return result
