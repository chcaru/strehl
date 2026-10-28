"""Fixed native spectral pilot. Import has no numerical or CUDA side effects."""
from dataclasses import dataclass
from pathlib import Path
import ctypes as C
import hashlib
import math
import re
import types


HERE = Path(__file__).resolve().parent
LOADER = HERE.parents[1] / "dual-tree-cfa-gpu" / "ordered-fir.py"
LOADER_SHA = "16688f2bf6b555c2fe5c90e4d141415ddc0b59d0d7574f847f55a13bbd715dce"
PHASES = ((0, 0), (1, 0), (0, 1), (1, 1))
MAX_BATCH = 16
PROBES = 16


CUDA_SOURCE = r'''
__device__ int reflect_site(long long p, int n) {
    const long long period = 2LL * (n - 1);
    p %= period;
    if (p < 0) p += period;
    return (int)(p < n ? p : period - p);
}
__device__ unsigned int mix32(unsigned int v) {
    v ^= v >> 16; v *= 0x7feb352dU;
    v ^= v >> 15; v *= 0x846ca68bU;
    return v ^ (v >> 16);
}
__device__ float original_probe(unsigned int site, unsigned int source, int draw) {
    const unsigned int key = mix32(site ^ mix32(source + 0x9e3779b9U)
        ^ mix32((unsigned int)draw + 0x243f6a88U) ^ 0xb7e15162U);
    const float u = __fmul_rn(__fadd_rn((float)(mix32(key) >> 8), 0.5f), 0.000000059604644775390625f);
    const float v = __fmul_rn(__fadd_rn((float)(mix32(key ^ 0xa511e9b3U) >> 8), 0.5f), 0.000000059604644775390625f);
    return __fmul_rn(sqrtf(__fmul_rn(-2.0f, logf(u))),
                    cosf(__fmul_rn(6.283185482025146484375f, v)));
}
extern "C" __global__ void spectral_extract(
    const unsigned short* raw, const long long* origins, const float* noise,
    float* dst, int height, int width, int size, int kind, int square_green,
    int shift_x, int shift_y, unsigned int source, int draw, long long count) {
    const long long n = (long long)blockIdx.x * blockDim.x + threadIdx.x;
    if (n >= count) return;
    const int x = (int)(n % size), y = (int)((n / size) % size);
    const long long patch = n / ((long long)size * size);
    const long long u = origins[6*patch + 2*kind] + x;
    const long long v = origins[6*patch + 2*kind + 1] + y;
    long long px, py;
    if (kind == 1 && !square_green) { px=u+v+1; py=u-v; }
    else { px=2*u+(kind==0?0:1); py=2*v+(kind==2?1:0); }
    const int sx=reflect_site(px+shift_x,width), sy=reflect_site(py+shift_y,height);
    const unsigned int index=(unsigned int)((long long)sy*width+sx);
    const float signal=__fadd_rn((float)raw[index],-noise[0]);
    if (draw < 0) { dst[n]=signal; return; }
    const int phase=2*(sy&1)+(sx&1);
    const float variance=__fadd_rn(noise[5+phase],__fmul_rn(noise[1+phase],fmaxf(signal,0.0f)));
    dst[n]=__fmul_rn(sqrtf(variance),original_probe(index,source,draw));
}
extern "C" __global__ void spectral_weights(
    const double* queries, long long* bases, float* weights, long long count) {
    const long long n=(long long)blockIdx.x*blockDim.x+threadIdx.x;
    if(n>=count) return;
    const double q=4.0*queries[n];
    const long long m=(long long)floor(q);
    const float t=(float)(q-(double)m);
    bases[n]=m-7;
    // Ordinary degree15 cardinal polynomials; ordered f32 products.
    for(int j=0;j<16;++j) {
        float w=1.0f;
        for(int k=0;k<16;++k) if(k!=j)
            w=__fmul_rn(w,__fdiv_rn(__fadd_rn(t,(float)(7-k)),(float)(j-k)));
        weights[16*n+j]=w;
    }
}
extern "C" __global__ void spectral_evaluate(
    const float* grid, const float* means, const long long* bases,
    const float* weights, float* dst, int size, int phase, long long count) {
    const long long n=(long long)blockIdx.x*blockDim.x+threadIdx.x;
    if(n>=count) return;
    const long long patch=n/4096, pixel=n%4096;
    const long long query=(patch*4+phase)*4096+pixel;
    const long long bx=bases[2*query], by=bases[2*query+1];
    const float* wx=weights+32*query;
    const float* wy=wx+16;
    float total=0.0f;
    for(int j=0;j<16;++j) {
        int sy=(int)((by+j)%size); if(sy<0)sy+=size;
        float row=0.0f;
        for(int k=0;k<16;++k) {
            int sx=(int)((bx+k)%size); if(sx<0)sx+=size;
            row=__fadd_rn(row,__fmul_rn(wx[k],grid[(patch*size+sy)*size+sx]));
        }
        total=__fadd_rn(total,__fmul_rn(wy[j],row));
    }
    dst[query]=__fadd_rn(total,means[patch]);
}
'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def spectral_ptx_guard(ptx):
    """Scope the inherited no-FMA contract without changing CUDA operations.

    The extraction entry contains the Gaussian noise transcendentals. Its
    fused instructions are recorded, not attributed to libdevice merely by
    their location. Unknown fused-helper paths still fail closed.
    """
    text=ptx.decode("utf-8").rstrip("\x00")
    # Preserve positions while masking comments, so evidence hashes use the
    # actual original PTX bodies and instruction locations remain unambiguous.
    masked=re.sub(r"/\*[\s\S]*?\*/|//[^\n]*",lambda m:" "*len(m.group()),text)
    bodies={}
    for mark in re.finditer(r"\.(entry|func)\b",masked):
        cursor=mark.end()
        while cursor<len(masked) and masked[cursor].isspace():cursor+=1
        if cursor<len(masked) and masked[cursor]=="(":
            depth=1;cursor+=1
            while cursor<len(masked) and depth:
                depth+=(masked[cursor]=="(")-(masked[cursor]==")");cursor+=1
            require(depth==0,"malformed PTX return parameters")
            while cursor<len(masked) and masked[cursor].isspace():cursor+=1
        name=re.match(r"[A-Za-z_$][A-Za-z0-9_$]*",masked[cursor:])
        require(name is not None,"PTX function name not understood")
        name=name.group()
        brace=masked.find("{",cursor)
        semicolon=masked.find(";",cursor)
        if brace<0 or (semicolon>=0 and semicolon<brace):
            continue  # function declaration without a body
        depth=1;end=brace+1
        while end<len(masked) and depth:
            depth+=(masked[end]=="{")-(masked[end]=="}");end+=1
        require(depth==0 and name not in bodies,"malformed/duplicate PTX function body")
        bodies[name]=(brace,end)
    protected=("ordered_x","ordered_y","spectral_weights","spectral_evaluate")
    require(all(name in bodies for name in (*protected,"spectral_extract")),"required PTX entries absent")
    fused=re.compile(r"\b(?:fma|mad)(?:\.[a-z0-9]+)*\.f(?:32|64)\b")
    sites=list(fused.finditer(masked))
    for site in sites:
        owner=[name for name,(left,right) in bodies.items() if left<=site.start()<right]
        require(owner==["spectral_extract"],
                "floating fused instruction outside approved extraction entry: "+repr(owner))
    evidence={}
    for name,(left,right) in bodies.items():
        body=masked[left:right]
        instructions=list(fused.finditer(body))
        if name in protected:
            require(not instructions and "mul.rn.f32" in body and "add.rn.f32" in body,
                    "ordered signal PTX contract failed: "+name)
        excerpts=[]
        for site in instructions:
            start=body.rfind("\n",0,site.start())+1
            stop=body.find("\n",site.end())
            excerpts.append(body[start:len(body) if stop<0 else stop].strip())
        evidence[name]=dict(ptx_body_sha256=hashlib.sha256(text[left:right].encode()).hexdigest(),
            floating_fused_instruction_count=len(instructions),floating_fused_instruction_lines=excerpts,
            separate_mul_rn_f32="mul.rn.f32" in body,separate_add_rn_f32="add.rn.f32" in body,
            protected_no_fused=name in protected)
    return dict(schema=1,whole_ptx_sha256=hashlib.sha256(ptx).hexdigest(),entries=evidence,
        floating_fused_instruction_count=len(sites),approved_fused_entry="spectral_extract",
        unclassified_fused_instructions=0,protected_entries=list(protected),
        instruction_to_libdevice_provenance_proven=False,
        scope="signal/interpolation entries retain ordered no-FMA; extraction/noise entry fused instructions explicitly reported")


@dataclass(frozen=True)
class Noise:
    black: float
    gain4: tuple
    read_variance4: tuple

    def __post_init__(self):
        require(len(self.gain4) == len(self.read_variance4) == 4, "four physical phase noise values required")
        require(all(math.isfinite(float(v)) for v in (self.black, *self.gain4, *self.read_variance4)), "finite noise required")
        require(all(v >= 0 for v in (*self.gain4, *self.read_variance4)), "negative noise model")


@dataclass
class Source:
    raw: object
    source_id: int
    noise: Noise
    noise_tensor: object
    hw: tuple


@dataclass
class Geometry:
    origins: tuple
    lattice_origins: tuple
    query_lattice: object
    pull_affine: tuple
    source_hw: tuple
    origin_tensor: object
    bases: object
    interpolation_weights: object
    diagnostic_green_square: bool
    diagnostic_phase_shift_xy: tuple
    evidence: dict


@dataclass
class Prepared:
    gathered: object
    coefficients: object
    means: object
    variance: object
    admission: object
    source_id: int
    evidence: dict


def patch_origins(width, height, origin_xy=(0, 0)):
    require(type(width) is int and type(height) is int and width > 0 and height > 0, "positive integer output extent required")
    require(len(origin_xy) == 2 and all(type(v) is int and v % 2 == 0 for v in origin_xy), "even native output origin required")
    return [(origin_xy[0]+x, origin_xy[1]+y)
            for y in range(-64, height, 64) for x in range(-64, width, 64)]


class SpectralConsumer:
    def __init__(self, torch, device_limit_bytes=10 << 30):
        self.t = torch
        self.limit = int(device_limit_bytes)
        require(torch.cuda.is_available() and torch.cuda.current_device() == 0, "cuda0 required")
        require(0 < self.limit <= 24 << 30, "device allocation bound")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        require(not torch.is_autocast_enabled(), "autocast forbidden")
        total = torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(min(self.limit / total, 1.0), 0)
        require(digest(LOADER) == LOADER_SHA, "pinned NVRTC loader changed")
        self.source_sha = digest(__file__)
        # Private module composition: original source and runtime stay untouched.
        loader = types.ModuleType("strehl_spectral_nvrtc_private")
        loader.__file__ = str(LOADER)
        loader_source=LOADER.read_text(encoding="utf-8")
        old_guard='''        require(b"fma." not in ptx and b"mad.f32" not in ptx,
                "ordered FIR PTX unexpectedly contains floating fused multiply-add")'''
        new_guard="        self.spectral_ptx_evidence = _spectral_ptx_guard(ptx)"
        require(loader_source.count(old_guard)==1,"pinned loader guard layout differs")
        adapted_loader=loader_source.replace(old_guard,new_guard)
        self.adapted_loader_sha256=hashlib.sha256(adapted_loader.encode()).hexdigest()
        loader._spectral_ptx_guard=spectral_ptx_guard
        exec(compile(adapted_loader, str(LOADER)+"[private-spectral-guard]", "exec"), loader.__dict__)
        loader.CUDA_SOURCE += "\n" + CUDA_SOURCE
        torch.empty(0, device="cuda")
        self.runtime = loader.OrderedFir(torch)
        self.functions = {}
        for name in ("spectral_extract", "spectral_weights", "spectral_evaluate"):
            fn = C.c_void_p()
            self.runtime.cucheck(self.runtime.cu_function(C.byref(fn), self.runtime.module, name.encode()), "cuModuleGetFunction")
            self.functions[name] = fn
        self.launches = {k: 0 for k in self.functions}
        self.probe_gathers = 0
        self.signal_gathers = 0
        self.prepared_sources = 0
        self.max_imaginary = torch.zeros((),device="cuda",dtype=torch.float32)
        self.all_finite = torch.ones((),device="cuda",dtype=torch.bool)
        self._tapers = {}
        self._ratios = {}
        self._ratio_geometry = None
        axis = torch.arange(64, device="cuda", dtype=torch.float32)
        a = torch.sin(axis * (math.pi / 64)).square()
        self.hann = (a[:, None] * a[None, :]).contiguous()
        self.sqrt_hann = self.hann.sqrt()
        self.window_mass = self.sqrt_hann.sum()
        self.opposite = (-torch.arange(64, device="cuda", dtype=torch.int64)) % 64

    def _check_memory(self):
        require(self.t.cuda.memory_allocated(0) <= self.limit, "device allocated limit exceeded")
        require(self.t.cuda.memory_reserved(0) <= self.limit, "device reserved limit exceeded")

    def _launch(self, name, count, values, tensors):
        require(0 < count < 2**31 and self.runtime.current_context() == self.runtime.context, "launch/context bound")
        stream = self.t.cuda.current_stream(0)
        for value in tensors:
            value.record_stream(stream)
        params = (C.c_void_p * len(values))(*(C.cast(C.byref(v), C.c_void_p) for v in values))
        self.runtime.cucheck(self.runtime.cu_launch(self.functions[name], (count+255)//256, 1, 1,
            256, 1, 1, 0, C.c_void_p(stream.cuda_stream), params, None), name)
        self.runtime.streams.add(stream.cuda_stream)
        self.launches[name] += 1

    def source(self, raw_u16, source_id, noise):
        t = self.t
        require(type(source_id) is int and 0 <= source_id < 2**32, "source ID range")
        require(isinstance(noise, Noise), "one supplied Noise required")
        raw = t.as_tensor(raw_u16)
        require(raw.dtype == t.uint16 and raw.ndim == 2 and raw.is_contiguous(), "original contiguous u16 HW source required")
        h, w = map(int, raw.shape)
        require(h >= 2 and w >= 2 and h*w < 2**32, "source extent bound")
        raw = raw.to(device="cuda", dtype=t.uint16, copy=raw.device.type != "cuda")
        nt = t.tensor([noise.black, *noise.gain4, *noise.read_variance4], device="cuda", dtype=t.float32)
        self._check_memory()
        return Source(raw, source_id, noise, nt, (h, w))

    def geometry(self, origins, pull_affine, source_hw, diagnostic_green_square=False,
                 diagnostic_phase_shift_xy=(0, 0)):
        t = self.t
        origins = tuple(tuple(int(v) for v in p) for p in origins)
        require(0 < len(origins) <= MAX_BATCH and all(len(p) == 2 and p[0]%2 == p[1]%2 == 0 for p in origins), "bounded even reference origins required")
        a = tuple(tuple(float(v) for v in row) for row in pull_affine)
        require(len(a) == 2 and all(len(row) == 3 for row in a)
                and all(math.isfinite(v) for row in a for v in row), "finite 2x3 pull required")
        require(abs(a[0][0]*a[1][1]-a[0][1]*a[1][0]) > 1e-12, "singular pull")
        require(len(source_hw) == 2 and min(source_hw) >= 2, "source extent")
        shift = tuple(diagnostic_phase_shift_xy)
        require(len(shift) == 2 and all(type(v) is int and abs(v) <= 1 for v in shift), "bounded diagnostic phase shift")
        lattice = []
        for ox, oy in origins:
            cx, cy = ox+63.5, oy+63.5
            sx = a[0][0]*cx+a[0][1]*cy+a[0][2]
            sy = a[1][0]*cx+a[1][1]*cy+a[1][2]
            centers = ((sx/2, sy/2),
                ((sx-1)/2, sy/2) if diagnostic_green_square else ((sx+sy-1)/2, (sx-sy-1)/2),
                ((sx-1)/2, (sy-1)/2))
            lattice.append(tuple((round(x-(n-1)/2), round(y-(n-1)/2))
                                 for (x,y),n in zip(centers,(128,256,128))))
        gt = t.tensor(lattice, device="cuda", dtype=t.int64)
        p = t.tensor(origins, device="cuda", dtype=t.float64)
        axis = 2*t.arange(64, device="cuda", dtype=t.float64)
        yy, xx = t.meshgrid(axis, axis, indexing="ij")
        query = t.empty((len(origins),4,64,64,2), device="cuda", dtype=t.float64)
        for phase,(dx,dy) in enumerate(PHASES):
            rx = p[:,0,None,None]+xx+dx
            ry = p[:,1,None,None]+yy+dy
            sx = a[0][0]*rx+a[0][1]*ry+a[0][2]
            sy = a[1][0]*rx+a[1][1]*ry+a[1][2]
            kind = (0,1,1,2)[phase]
            if kind == 1 and not diagnostic_green_square:
                u,v = (sx+sy-1)/2, (sx-sy-1)/2
            else:
                u,v = (sx-int(kind!=0))/2, (sy-int(kind==2))/2
            query[:,phase,:,:,0] = u-gt[:,kind,0,None,None]
            query[:,phase,:,:,1] = v-gt[:,kind,1,None,None]
        lower = t.tensor([18.,34.,34.,18.], device="cuda", dtype=t.float64)[None,:,None,None,None]
        upper = t.tensor([109.,221.,221.,109.], device="cuda", dtype=t.float64)[None,:,None,None,None]
        require(bool(t.isfinite(query).all() and (query >= lower).all() and (query <= upper).all()),
                "fixed source flat-top support refused; no recenter/enlargement")
        bases = t.empty_like(query, dtype=t.int64)
        weights = t.empty((*query.shape,16), device="cuda", dtype=t.float32)
        count = query.numel()
        self._launch("spectral_weights", count,
            [C.c_void_p(query.data_ptr()),C.c_void_p(bases.data_ptr()),C.c_void_p(weights.data_ptr()),C.c_longlong(count)],
            [query,bases,weights])
        evidence = dict(patch_count=len(origins), physical_phase_order=["R","G1","G2","B"],
            reference_origins_xy=[list(v) for v in origins], lattice_origins_xy=[[list(v) for v in row] for row in lattice],
            pull_affine=[list(row) for row in a], source_hw=list(source_hw),
            rounding="nearest ties even", diagnostic_green_square=bool(diagnostic_green_square),
            diagnostic_phase_shift_xy=list(shift), support_pass=True)
        return Geometry(origins,tuple(lattice),query,a,tuple(source_hw),gt,bases,weights,
                        bool(diagnostic_green_square),shift,evidence)

    def lattice_samples(self, source, geometry, draw=None):
        require(source.hw == geometry.source_hw, "source/geometry extent mismatch")
        require(draw is None or (type(draw) is int and 0 <= draw < PROBES), "fixed probe index")
        t = self.t
        result = {}
        for kind,(name,n) in enumerate((("R",128),("G",256),("B",128))):
            dst = t.empty((len(geometry.origins),n,n), device="cuda", dtype=t.float32)
            self._launch("spectral_extract", dst.numel(),
                [C.c_void_p(source.raw.data_ptr()),C.c_void_p(geometry.origin_tensor.data_ptr()),
                 C.c_void_p(source.noise_tensor.data_ptr()),C.c_void_p(dst.data_ptr()),
                 C.c_int(source.hw[0]),C.c_int(source.hw[1]),C.c_int(n),C.c_int(kind),
                 C.c_int(geometry.diagnostic_green_square),C.c_int(geometry.diagnostic_phase_shift_xy[0]),
                 C.c_int(geometry.diagnostic_phase_shift_xy[1]),C.c_uint(source.source_id),
                 C.c_int(-1 if draw is None else draw),C.c_longlong(dst.numel())],
                [source.raw,geometry.origin_tensor,source.noise_tensor,dst])
            result[name] = dst
        return result

    def taper(self, n):
        require(n in (128,256), "fixed source lattice size")
        if n not in self._tapers:
            t = self.t
            edge = n//8
            x = t.arange(n, device="cuda", dtype=t.float32)
            distance = t.minimum(x, n-1-x)
            a = t.where(distance < edge, 0.5-0.5*t.cos(math.pi*distance/edge), t.ones_like(x))
            self._tapers[n] = (a[:,None]*a[None,:]).contiguous()
        return self._tapers[n]

    def _expanded_spectrum(self, coefficients):
        t = self.t
        n = coefficients.shape[-1]
        k = t.arange(-n//2,n//2+1,device="cuda",dtype=t.int64)
        ix = k % n
        q = t.ones(n+1,device="cuda",dtype=t.float32)
        q[0] = q[-1] = 0.5
        expanded = coefficients.index_select(-2,ix).index_select(-1,ix)
        return expanded*(q[:,None]*q[None,:]), k

    def cell_ratio(self, n, kind, affine, square_green=False):
        t = self.t
        # Small (N+1)^2 multipliers, reused for the17 signal/probe gathers.
        key = (n,kind,tuple(v for row in affine for v in row[:2]),bool(square_green))
        geometry_key = (key[2],key[3])
        if self._ratio_geometry != geometry_key:
            self._ratios.clear()
            self._ratio_geometry = geometry_key
        if key not in self._ratios:
            k = t.arange(-n//2,n//2+1,device="cuda",dtype=t.float32)/n
            v,u = t.meshgrid(k,k,indexing="ij")
            if kind == "G" and not square_green:
                fx,fy = (u+v)/2,(u-v)/2
            else:
                fx,fy = u/2,v/2
            # f32 signal transfer; affine coordinates themselves remain f64.
            rx = float(affine[0][0])*fx+float(affine[1][0])*fy
            ry = float(affine[0][1])*fx+float(affine[1][1])*fy
            ratio = t.sinc(rx)*t.sinc(ry)/(t.sinc(fx)*t.sinc(fy))
            require(bool(t.isfinite(ratio).all()), "nonfinite cell transfer")
            self._ratios[key] = ratio
        return self._ratios[key]

    def interpolate_lattices(self, lattices, geometry, omit_cell_ratio=False):
        t = self.t
        count = len(geometry.origins)
        result = t.empty((count,4,64,64),device="cuda",dtype=t.float32)
        for name,n,phases in (("R",128,(0,)),("G",256,(1,2)),("B",128,(3,))):
            value = lattices[name]
            require(tuple(value.shape)==(count,n,n) and value.dtype==t.float32
                    and value.device.type=="cuda" and value.is_contiguous(), "lattice layout")
            means = value.mean(dim=(-2,-1)).contiguous()
            centered = (value-means[:,None,None])*self.taper(n)
            spectrum = t.fft.fft2(centered,norm="ortho")
            expanded,k = self._expanded_spectrum(spectrum)
            if not omit_cell_ratio:
                expanded = expanded*self.cell_ratio(n,name,geometry.pull_affine,geometry.diagnostic_green_square)
            size = 4*n
            padded = t.zeros((count,size,size),device="cuda",dtype=t.complex64)
            dest = k % size
            padded[:,dest[:,None],dest[None,:]] = expanded
            interpolant = t.fft.ifft2(padded,norm="ortho")*4.0
            # Imaginary residual is retained for controls, never silently used.
            self.max_imaginary = t.maximum(self.max_imaginary,interpolant.imag.abs().max())
            grid = interpolant.real.contiguous()
            for phase in phases:
                self._launch("spectral_evaluate", count*4096,
                    [C.c_void_p(grid.data_ptr()),C.c_void_p(means.data_ptr()),C.c_void_p(geometry.bases.data_ptr()),
                     C.c_void_p(geometry.interpolation_weights.data_ptr()),C.c_void_p(result.data_ptr()),
                     C.c_int(size),C.c_int(phase),C.c_longlong(count*4096)],
                    [grid,means,geometry.bases,geometry.interpolation_weights,result])
            del interpolant,grid,padded,expanded,spectrum,centered
        self.all_finite.logical_and_(t.isfinite(result).all())
        self._check_memory()
        return result

    def gather(self, source, geometry, draw=None, omit_cell_ratio=False):
        result = self.interpolate_lattices(self.lattice_samples(source,geometry,draw),geometry,omit_cell_ratio)
        if draw is None:
            self.signal_gathers += 1
        else:
            self.probe_gathers += 1
        return result

    def analyse(self, gathered):
        t = self.t
        require(gathered.dtype==t.float32 and gathered.ndim==4 and tuple(gathered.shape[1:])==(4,64,64), "gathered phase layout")
        means = (gathered*self.sqrt_hann).sum(dim=(-2,-1))/self.window_mass
        z = t.fft.fft2((gathered-means[:,:,None,None])*self.sqrt_hann,norm="ortho")
        z[:,:,0,0] = 0
        return z,means

    def admission(self, z, variance):
        t = self.t
        denominator = variance.clamp_min(1.0)
        energy = ((z.real.square()+z.imag.square())/denominator).mean(dim=1)
        floor = (variance/denominator).mean(dim=1)
        a = (energy-2*floor).clamp_min(0)
        a = (a+a.index_select(-2,self.opposite).index_select(-1,self.opposite))*0.5
        a[:,0,0] = 0
        require(bool(t.isfinite(a).all()), "nonfinite admission")
        return a

    def prepare_source(self, source, geometry, omit_cell_ratio=False):
        t = self.t
        gathered = self.gather(source,geometry,omit_cell_ratio=omit_cell_ratio)
        z,means = self.analyse(gathered)
        variance = t.zeros_like(z.real)
        for pair in range(PROBES//2):
            p0,_ = self.analyse(self.gather(source,geometry,2*pair,omit_cell_ratio))
            p1,_ = self.analyse(self.gather(source,geometry,2*pair+1,omit_cell_ratio))
            delta = p0-p1
            variance.add_((delta.real.square()+delta.imag.square())/PROBES)
        require(bool(self.all_finite & t.isfinite(variance).all()), "nonfinite gather or propagated variance")
        a = self.admission(z,variance)
        self.prepared_sources += 1
        evidence = dict(source_id=source.source_id,patch_count=len(geometry.origins),probe_draws=PROBES,
            conditional_noise_model_only=True,omit_cell_ratio=bool(omit_cell_ratio),
            phase_order=["R","G1","G2","B"],source_geometry=geometry.evidence)
        return Prepared(gathered,z,means,variance,a,source.source_id,evidence)

    def overlap_add(self, finished, origins, width, height, origin_xy=(0,0)):
        t = self.t
        require(len(origins)==finished["coefficients"].shape[0], "patch census mismatch")
        require(all(v%2==0 for v in origin_xy), "even delivery origin")
        candidate = t.zeros((height,width),device="cuda",dtype=t.float32)
        uniform = t.zeros_like(candidate)
        coverage = t.zeros_like(candidate)
        # Bounded16-patch inverse batches, never a source-aligned image volume.
        for start in range(0,len(origins),MAX_BATCH):
            end = min(start+MAX_BATCH,len(origins))
            mean = finished["means"][start:end,:,None,None]
            c = mean*self.hann+self.sqrt_hann*t.fft.ifft2(finished["coefficients"][start:end],norm="ortho").real
            u = mean*self.hann+self.sqrt_hann*t.fft.ifft2(finished["uniform_coefficients"][start:end],norm="ortho").real
            for local,(ox,oy) in enumerate(origins[start:end]):
                ox -= origin_xy[0]
                oy -= origin_xy[1]
                for phase,(dx,dy) in enumerate(PHASES):
                    x0,y0=ox+dx,oy+dy
                    qx0=max(0,(-x0+1)//2); qy0=max(0,(-y0+1)//2)
                    qx1=min(64,(width-x0+1)//2); qy1=min(64,(height-y0+1)//2)
                    if qx1<=qx0 or qy1<=qy0:
                        continue
                    target=(slice(y0+2*qy0,y0+2*qy1,2),slice(x0+2*qx0,x0+2*qx1,2))
                    source_slice=(slice(qy0,qy1),slice(qx0,qx1))
                    candidate[target].add_(c[local,phase][source_slice])
                    uniform[target].add_(u[local,phase][source_slice])
                    coverage[target].add_(self.hann[source_slice])
        support = coverage>0
        denominator = t.where(support,coverage,t.ones_like(coverage))
        candidate.div_(denominator)
        uniform.div_(denominator)
        require(bool(t.isfinite(candidate).all() and t.isfinite(uniform).all()), "nonfinite OLA result")
        return dict(candidate=candidate,uniform=uniform,coverage=coverage,
                    complete_coverage=bool(support.all()),physical_pattern="RGGB",
                    units="black-subtracted-DN",origin_xy=list(origin_xy))

    def metadata(self, strict=True):
        if strict:
            require(digest(__file__)==self.source_sha and digest(LOADER)==LOADER_SHA,"producer or loader changed")
        self._check_memory()
        require(bool(self.all_finite),"nonfinite spectral gather recorded")
        return dict(schema=1,operator_sha256=self.source_sha,loader_sha256=LOADER_SHA,
            private_loader_sha256=self.adapted_loader_sha256,
            private_loader_change="only global PTX no-FMA assertion replaced by per-entry audited contract",
            ptx_arithmetic_evidence=self.runtime.spectral_ptx_evidence,
            cuda_source_sha256=hashlib.sha256(CUDA_SOURCE.encode("ascii")).hexdigest(),
            runtime=self.runtime.metadata(strict),source_storage="u16 original CFA",
            arithmetic="f32/complex64; f64 geometry",fft_normalization="ortho",
            probe_key="original reflected site, source id, draw id; mix32 Box-Muller f32",
            signal_gathers=self.signal_gathers,probe_gathers=self.probe_gathers,
            prepared_source_batches=self.prepared_sources,kernel_launches=self.launches,
            maximum_discarded_imaginary_dn=float(self.max_imaginary.item()),device_limit_bytes=self.limit,
            peak_allocated_bytes=self.t.cuda.max_memory_allocated(0),
            peak_reserved_bytes=self.t.cuda.max_memory_reserved(0),
            quality_claim=False,photographic_admission=False)


class Accumulator:
    def __init__(self, engine, patch_count):
        self.engine=engine
        t=engine.t
        require(type(patch_count) is int and 0<patch_count<=20000,"patch accumulation bound")
        self.weighted=t.zeros((patch_count,4,64,64),device="cuda",dtype=t.complex64)
        self.uniform=t.zeros_like(self.weighted)
        self.weights=t.zeros((patch_count,64,64),device="cuda",dtype=t.float32)
        self.means=t.zeros((patch_count,4),device="cuda",dtype=t.float32)
        self.counts=t.zeros(patch_count,device="cuda",dtype=t.int64)
        self.last=[-1]*patch_count
        self.source_ids=[]
        self._last_source=-1
        engine._check_memory()

    def add(self, patch_indices, prepared):
        t=self.engine.t
        indices=list(patch_indices)
        require(len(indices)==prepared.coefficients.shape[0] and len(set(indices))==len(indices),"patch contribution census")
        require(all(type(i) is int and 0<=i<len(self.last) and self.last[i]<prepared.source_id for i in indices),"duplicate/out-of-order source patch")
        require(prepared.source_id>=self._last_source,"source order changed")
        if prepared.source_id!=self._last_source:
            require(bool((self.counts==len(self.source_ids)).all()),"previous source incomplete")
            self.source_ids.append(prepared.source_id)
            self._last_source=prepared.source_id
        for i in indices:self.last[i]=prepared.source_id
        ix=t.tensor(indices,device="cuda",dtype=t.int64)
        self.weighted[ix]=self.weighted[ix]+prepared.coefficients*prepared.admission[:,None]
        self.uniform[ix]=self.uniform[ix]+prepared.coefficients
        self.weights[ix]=self.weights[ix]+prepared.admission
        self.means[ix]=self.means[ix]+prepared.means
        self.counts[ix]=self.counts[ix]+1

    def finish(self):
        t=self.engine.t
        n=len(self.source_ids)
        require(n>0 and bool((self.counts==n).all()),"incomplete final source/patch census")
        uniform=self.uniform/n
        safe=t.where(self.weights>0,self.weights,t.ones_like(self.weights))
        coefficients=t.where((self.weights>0)[:,None],self.weighted/safe[:,None],uniform)
        means=self.means/n
        require(bool(t.isfinite(coefficients).all() and t.isfinite(uniform).all() and t.isfinite(means).all()),"nonfinite accumulated result")
        return dict(coefficients=coefficients,uniform_coefficients=uniform,means=means,counts=self.counts,
                    evidence=dict(source_count=n,source_ids=list(self.source_ids),patch_count=len(self.last),
                        fallback_frequency_count=int((self.weights==0).sum().item()),
                        source_shared_four_phase_weights=True,quality_claim=False,photographic_admission=False))
