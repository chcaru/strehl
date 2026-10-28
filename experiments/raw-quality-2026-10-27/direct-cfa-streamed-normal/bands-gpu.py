"""Original-grid physical-phase Haar and frozen marginal metric on CUDA f32."""
from dataclasses import dataclass
import math

SQRT_HALF = 0.7071067690849304
PHASE_CHANNEL = (0, 1, 1, 2)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(torch, value, name):
    require(bool(torch.isfinite(value).all()), "nonfinite " + name)
    return value


def f32(torch, value):
    require(torch.is_tensor(value) and value.dtype == torch.float32
            and value.device.type == "cuda" and value.device.index == 0,
            "CUDA0 f32 tensor required")
    return value


def pair(torch, value, axis, mode):
    n = value.shape[axis]
    paired = n // 2
    even = value.index_select(axis, torch.arange(0, 2*paired, 2, device=value.device))
    odd = value.index_select(axis, torch.arange(1, 2*paired, 2, device=value.device))
    if mode == "support":
        lo = even & odd
        hi = lo.clone()
    elif mode == "variance":
        lo = (even + odd) * .5
        hi = lo.clone()
    else:
        lo = (even + odd) * SQRT_HALF
        hi = (even - odd) * SQRT_HALF
    if n & 1:
        lo = torch.cat((lo, value.narrow(axis, n-1, 1)), dim=axis)
    return lo, hi


def unpair(torch, lo, hi, axis, n):
    shape = list(lo.shape)
    shape[axis] = n
    out = torch.empty(shape, dtype=torch.float32, device=lo.device)
    pairs = n // 2
    first = lo.narrow(axis, 0, pairs)
    out.index_copy_(axis, torch.arange(0, pairs*2, 2, device=lo.device), (first+hi)*SQRT_HALF)
    out.index_copy_(axis, torch.arange(1, pairs*2, 2, device=lo.device), (first-hi)*SQRT_HALF)
    if n & 1:
        out.narrow(axis,n-1,1).copy_(lo.narrow(axis,pairs,1))
    return out


class HaarPlan:
    def __init__(self, torch, observed_hw, origin_xy=(0, 0)):
        self.torch = torch
        self.observed_hw = tuple(int(v) for v in observed_hw)
        self.origin_xy = tuple(int(v) for v in origin_xy)
        require(len(self.observed_hw)==2 and min(self.observed_hw)>=2
                and max(self.observed_hw)<=8192, "Haar extent unsupported")
        require(len(self.origin_xy)==2 and min(self.origin_xy)>=0, "Haar origin unsupported")
        self.bands, self.sizes, self._phase = [], [], []
        offset = 0
        for phase in range(4):
            dx = (phase % 2 - self.origin_xy[0]) % 2
            dy = (phase // 2 - self.origin_xy[1]) % 2
            h = len(range(dy, self.observed_hw[0], 2))
            w = len(range(dx, self.observed_hw[1], 2))
            sizes, entries = [(h,w)], []
            for level in range(7):
                if min(h,w)<2:
                    break
                shapes = [(h//2,(w+1)//2),((h+1)//2,w//2),(h//2,w//2)]
                current = []
                for kind, shape in zip(("LH","HL","HH"), shapes):
                    count = shape[0]*shape[1]
                    band = dict(phase=phase,level=level,kind=kind,shape=shape,start=offset,end=offset+count)
                    self.bands.append(band)
                    current.append(band)
                    offset += count
                entries.append(current)
                h,w = (h+1)//2,(w+1)//2
                sizes.append((h,w))
            low = dict(phase=phase,level=len(entries),kind="LL",shape=(h,w),start=offset,end=offset+h*w)
            self.bands.append(low)
            offset += h*w
            self.sizes.append(sizes)
            self._phase.append((dy,dx,entries,low,sizes))
        self.count = offset
        require(offset==self.observed_hw[0]*self.observed_hw[1], "incomplete Haar packing")

    def _forward(self, value, mode):
        t=self.torch
        require(tuple(value.shape)==self.observed_hw, "Haar shape differs")
        if mode=="support":
            require(value.dtype==t.bool and value.device.type=="cuda" and value.device.index==0,
                    "CUDA0 Boolean support required")
        else:
            f32(t,value)
        values=[]
        for dy,dx,entries,_,_ in self._phase:
            current=value[dy::2,dx::2]
            for _ in entries:
                lx,hx=pair(t,current,1,mode)
                ll,lh=pair(t,lx,0,mode)
                hl,hh=pair(t,hx,0,mode)
                values.extend((lh.reshape(-1),hl.reshape(-1),hh.reshape(-1)))
                current=ll
            values.append(current.reshape(-1))
        return t.cat(values)

    def forward(self, value):
        return self._forward(value,"signal")

    def variance(self, value):
        require(bool((value>=0).all()), "negative original variance")
        return self._forward(value,"variance")

    def inverse(self, coefficients):
        t=self.torch
        f32(t,coefficients)
        require(coefficients.ndim==1 and coefficients.numel()==self.count,"coefficient count differs")
        out=t.empty(self.observed_hw,dtype=t.float32,device=coefficients.device)
        for dy,dx,entries,low,sizes in self._phase:
            current=coefficients[low["start"]:low["end"]].reshape(low["shape"])
            for k in range(len(entries)-1,-1,-1):
                lh,hl,hh=[coefficients[b["start"]:b["end"]].reshape(b["shape"]) for b in entries[k]]
                h,w=sizes[k]
                lx=unpair(t,current,lh,0,h)
                hx=unpair(t,hl,hh,0,h)
                current=unpair(t,lx,hx,1,w)
            out[dy::2,dx::2]=current
        return out

    def support(self, valid_original, admission_window=True):
        valid=self._forward(valid_original,"support")
        return self.expand_support(valid) if admission_window else valid

    def expand_support(self, support):
        valid=support.clone()
        for b in self.bands:
            if b["kind"]!="LL":
                a,z=b["start"],b["end"]
                valid[a:z]=window_all(self.torch,valid[a:z].reshape(b["shape"])).reshape(-1)
        return valid


def smooth3(torch, value):
    h,w=value.shape
    yi=torch.arange(-1,h+1,device=value.device).clamp(0,h-1)
    xi=torch.arange(-1,w+1,device=value.device).clamp(0,w-1)
    padded=value[yi[:,None],xi[None,:]]
    out=torch.zeros_like(value)
    for y in range(3):
        for x in range(3):
            out=out+padded[y:y+h,x:x+w]
    return out/9.0


def window_all(torch, value):
    h,w=value.shape
    yi=torch.arange(-1,h+1,device=value.device).clamp(0,h-1)
    xi=torch.arange(-1,w+1,device=value.device).clamp(0,w-1)
    padded=value[yi[:,None],xi[None,:]]
    out=torch.ones_like(value)
    for y in range(3):
        for x in range(3):
            out=out & padded[y:y+h,x:x+w]
    return out


@dataclass(frozen=True)
class Noise:
    shot4: tuple
    read4: tuple
    black4: tuple
    saturation: int

    def __post_init__(self):
        for name in ("shot4","read4","black4"):
            values=getattr(self,name)
            require(len(values)==4 and all(math.isfinite(v) and 0<=v<3.4028234663852886e38 for v in values),
                    "invalid supplied phase noise/levels")
        require(type(self.saturation)is int and 0<self.saturation<=65535
                and max(self.black4)<self.saturation,"invalid saturation")


@dataclass
class SourceBands:
    torch: object
    plan: object
    observed: object
    d: object
    variance: object
    admission: object
    metric: object
    valid_original: object
    valid_coeff: object
    support_coeff: object
    evidence: dict

    def factors(self, metric_scale, count):
        t=self.torch
        scale=t.as_tensor(metric_scale,dtype=t.float32,device="cuda:0")
        n=t.tensor(count,dtype=t.float32,device="cuda:0")
        require(scale.ndim==0 and bool(t.isfinite(scale)) and float(scale)>0 and count>0,"invalid common scale/count")
        factor=(t.sqrt(self.metric)/t.sqrt(scale))/t.sqrt(n)
        finite(t,factor,"weighted factor")
        require(bool((factor[self.valid_coeff]>0).all()),"admitted factor underflow")
        return factor


def prepare_source(torch,codes,origin_xy,noise,mode="candidate",metric_override=None,
                   frozen_valid=None,diagnostic_admission_window=True,collect_evidence=True):
    t=torch
    code_tensor=t.as_tensor(codes)
    require(code_tensor.dtype==t.uint16 and code_tensor.ndim==2,"original u16 H,W required")
    plan=HaarPlan(t,tuple(code_tensor.shape),origin_xy)
    observed=code_tensor.to(device="cuda:0",dtype=t.float32,copy=True)
    valid=observed<noise.saturation
    if frozen_valid is not None:
        supplied=t.as_tensor(frozen_valid,device="cuda:0")
        require(supplied.dtype==t.bool and tuple(supplied.shape)==plan.observed_hw,"frozen support shape/dtype")
        valid=supplied.clone()
    variance=t.empty_like(observed)
    for phase,(dy,dx,_,_,_) in enumerate(plan._phase):
        view=observed[dy::2,dx::2]
        view.sub_(noise.black4[phase])
        variance[dy::2,dx::2]=noise.shot4[phase]*view.clamp_min(0)+noise.read4[phase]
    d=finite(t,plan.forward(observed),"Haar observations")
    variance=finite(t,plan.variance(variance),"Haar marginal variance")
    support=plan.support(valid,admission_window=False)
    valid_coeff=plan.expand_support(support) if diagnostic_admission_window else support
    admission=t.ones_like(d)
    require(mode in ("candidate","no-focus"),"only frozen candidate/no-focus modes supported here")
    if mode=="candidate":
        for band in plan.bands:
            if band["kind"]=="LL":
                continue
            a,b=band["start"],band["end"]
            energy=smooth3(t,d[a:b].reshape(band["shape"]).square())
            floor=smooth3(t,variance[a:b].reshape(band["shape"]))
            value=((energy-2*floor).clamp_min(0)/(64*floor.clamp_min(1))).square().clamp_min(1e-4)
            admission[a:b]=value.reshape(-1)
    finite(t,admission,"admission")
    metric=admission/variance.clamp_min(1)
    if metric_override is not None:
        override=t.tensor(metric_override,dtype=t.float32,device="cuda:0")
        require(override.ndim==0 and bool(t.isfinite(override)) and float(override)>0,"invalid metric override")
        metric=t.full_like(metric,float(override))
    metric=t.where(valid_coeff,metric,t.zeros_like(metric))
    finite(t,metric,"metric")
    require(bool((metric[valid_coeff]>0).all()),"admitted metric nonpositive")
    evidence={}
    if collect_evidence:
        omitted=[]
        for b in plan.bands:
            a,z=b["start"],b["end"]
            omitted.append({**b,"support_invalid":int((~support[a:z]).sum()),
                            "omitted":int((~valid_coeff[a:z]).sum())})
        evidence={"original_shape":list(plan.observed_hw),"origin_xy":list(origin_xy),
              "clipped_or_frozen_invalid_sites":int((~valid).sum()),"bands":omitted,
              "diagnostic_frozen_mask":frozen_valid is not None,
              "diagnostic_admission_window":bool(diagnostic_admission_window),
              "mode":mode,"metric_max":float(metric.max()),"metric_min":float(metric.min()),
              "coefficient_count":plan.count,"phase_sizes":plan.sizes,
              "noise":"supplied shot*max(signed_DN,0)+read_variance; no quantization term",
                  "omission":"invalid original Haar support plus replicated3x3 AC admission support; no inequality likelihood"}
    return SourceBands(t,plan,observed,d,variance,admission,metric,valid,valid_coeff,support,evidence)
