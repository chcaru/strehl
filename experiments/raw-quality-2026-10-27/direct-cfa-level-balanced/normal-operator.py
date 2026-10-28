"""Streamed B' P B and B' P b. No source residual/factor volume."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import importlib.util
import sys

HERE=Path(__file__).resolve().parent
MEASUREMENT_PATH=HERE.parent/"direct-cfa-forward-gpu"/"measurement-gpu.py"
MEASUREMENT_SHA="8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84"
CPU_PATH=HERE.parent/"joint-cfa-local-fit"/"band-residual"/"sensor-operator.py"
CPU_SHA="536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac"


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(path,name,expected=None):
    if expected is not None and digest(path)!=expected:
        raise ValueError("frozen dependency changed: "+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(Path(path).read_bytes(),str(path),"exec"),module.__dict__)
    return module


bands=load_module(HERE/"bands-gpu.py","level_balanced_bands")
Noise,HaarPlan,prepare_source=bands.Noise,bands.HaarPlan,bands.prepare_source
require,finite=bands.require,bands.finite


def resolve_level_balance(torch,Q,R,metric_override=None):
    """Actual producing seven shared f32 multipliers; empty strata stay omitted."""
    t=torch
    bands.f32(t,Q);bands.f32(t,R)
    require(Q.shape==R.shape==(7,),"seven AC level sums required")
    finite(t,Q,"level Q");finite(t,R,"level R")
    require(bool((Q>=0).all()) and bool((R>=0).all()),"negative level mass")
    require(bool(((Q==0)==(R==0)).all()),"inconsistent empty level support")
    active=R>0
    multipliers=t.zeros_like(Q)
    if metric_override is not None:
        multipliers[active]=1
    else:
        multipliers[active]=R[active]/Q[active]
    finite(t,multipliers,"level multipliers")
    require(bool((multipliers[active]>0).all()),"level multiplier underflow")
    return multipliers


def level_statistics(current):
    """Current-source Q/R/max in band order, no f64 or independent-noise claim."""
    t=current.torch
    Q=t.zeros(7,dtype=t.float32,device="cuda:0")
    R=t.zeros_like(Q);maximum=t.zeros_like(Q);ll=t.zeros((),dtype=t.float32,device="cuda:0")
    for b in current.plan.bands:
        a,z=b["start"],b["end"];q=current.metric[a:z]
        if b["kind"]=="LL":
            ll=t.maximum(ll,q.max())
        else:
            k=b["level"]
            precision=t.where(current.valid_coeff[a:z],t.ones_like(q)/current.variance[a:z].clamp_min(1),t.zeros_like(q))
            Q[k]+=q.sum(dtype=t.float32)
            R[k]+=precision.sum(dtype=t.float32)
            maximum[k]=t.maximum(maximum[k],q.max())
    return Q,R,maximum,ll


def apply_level_balance(current,multipliers):
    """Shared metric edit used by every original-source preparation after census."""
    t=current.torch;bands.f32(t,multipliers)
    require(multipliers.shape==(7,),"seven level multipliers required")
    finite(t,multipliers,"applied level multipliers")
    for b in current.plan.bands:
        if b["kind"]!="LL":
            current.metric[b["start"]:b["end"]].mul_(multipliers[b["level"]])
    finite(t,current.metric,"balanced metric")
    require(bool((current.metric[current.valid_coeff]>0).all()),"admitted balanced metric underflow")
    return current


@dataclass
class SquaredNorm:
    torch: object
    mantissa: object
    exponent: int

    @property
    def is_zero(self):
        return float(self.mantissa)==0

    def ratio(self,other):
        require(not other.is_zero,"zero norm denominator")
        t=self.torch
        return t.ldexp(self.mantissa/other.mantissa,
                       t.tensor(self.exponent-other.exponent,dtype=t.int32,device="cuda:0"))

    def root_ratio(self,other):
        require(not other.is_zero,"zero norm denominator")
        t=self.torch
        delta=self.exponent-other.exponent
        v=t.sqrt(self.mantissa/other.mantissa)
        if delta%2:
            v=v*1.4142135381698608
        return t.ldexp(v,t.tensor(delta//2,dtype=t.int32,device="cuda:0"))

    def add(self,other):
        if self.is_zero:
            return other
        if other.is_zero:
            return self
        t=self.torch
        exponent=max(self.exponent,other.exponent)
        a=t.ldexp(self.mantissa,t.tensor(self.exponent-exponent,dtype=t.int32,device="cuda:0"))
        b=t.ldexp(other.mantissa,t.tensor(other.exponent-exponent,dtype=t.int32,device="cuda:0"))
        m,e=t.frexp(a+b)
        return SquaredNorm(t,m,exponent+int(e))

    def scaled(self,factor):
        t=self.torch
        factor=t.as_tensor(factor,dtype=t.float32,device="cuda:0")
        require(bool(t.isfinite(factor)) and float(factor)>0,"invalid norm scale")
        if self.is_zero:
            return self
        f,e=t.frexp(factor)
        m,k=t.frexp(self.mantissa*f)
        return SquaredNorm(t,m,self.exponent+int(e)+int(k))

    def le(self,other):
        if self.is_zero:
            return True
        if other.is_zero:
            return False
        return self.exponent<other.exponent or (self.exponent==other.exponent and float(self.mantissa)<=float(other.mantissa))

    def receipt(self):
        t=self.torch
        value=t.ldexp(self.mantissa,t.tensor(self.exponent,dtype=t.int32,device="cuda:0"))
        return dict(mantissa_f32=float(self.mantissa),binary_exponent=self.exponent,
                    value_f32=float(value) if bool(t.isfinite(value)) else None,nonzero=not self.is_zero)


def norm_pair(t,value):
    bands.f32(t,value)
    finite(t,value,"norm input")
    maximum=value.abs().max()
    if float(maximum)==0:
        return SquaredNorm(t,t.zeros((),dtype=t.float32,device="cuda:0"),0)
    total=(value/maximum).square().sum(dtype=t.float32)
    mf,me=t.frexp(maximum)
    sf,se=t.frexp(mf.square()*total)
    finite(t,sf,"scaled squared norm")
    return SquaredNorm(t,sf,2*int(me)+int(se))


def stable_dot(t,a,b):
    """F32 dot with exponent-separated range; not a f64 accumulation."""
    require(a.shape==b.shape,"dot shape differs")
    bands.f32(t,a);bands.f32(t,b)
    finite(t,a,"dot left");finite(t,b,"dot right")
    am,bm=a.abs().max(),b.abs().max()
    if float(am)==0 or float(bm)==0:
        return t.zeros((),dtype=t.float32,device="cuda:0")
    total=((a/am)*(b/bm)).sum(dtype=t.float32)
    af,ae=t.frexp(am);bf,be=t.frexp(bm)
    sf,se=t.frexp((af*bf)*total)
    value=t.ldexp(sf,ae+be+se)
    finite(t,value,"stable dot")
    require(float(sf)==0 or float(value)!=0,"dot underflow")
    return value


@dataclass
class Source:
    source_id: int
    source_xywh: tuple
    affine: object
    load_codes: object
    frozen_valid: object = None


class StreamedProblem:
    def __init__(self,torch,field_hw,sources,noise,mode="candidate",metric_override=None,
                 device_limit_bytes=8<<30,measurement=None,diagnostic_admission_window=True):
        t=self.torch=torch
        require(digest(CPU_PATH)==CPU_SHA,"frozen CPU formula changed")
        require(digest(MEASUREMENT_PATH)==MEASUREMENT_SHA,"frozen measurement changed")
        self.field_hw=tuple(field_hw)
        self.sources=tuple(sources)
        require(1<=len(self.sources)<=299 and len({s.source_id for s in self.sources})==len(self.sources),
                "distinct source IDs required")
        self.noise,self.mode,self.metric_override=noise,mode,metric_override
        self.device_limit_bytes=device_limit_bytes
        self.diagnostic_admission_window=diagnostic_admission_window
        self.count=0
        for s in self.sources:
            require(type(s.source_id)is int and callable(s.load_codes),"source ID/loader invalid")
            require(len(s.source_xywh)==4 and all(type(v)is int for v in s.source_xywh),"source rectangle invalid")
            ox,oy,w,h=s.source_xywh
            require(ox>=0 and oy>=0 and 4<=w<=8192 and 4<=h<=8192,"source rectangle unsupported")
            self.count+=w*h
        if measurement is None:
            module=load_module(MEASUREMENT_PATH,"streamed_frozen_measurement",MEASUREMENT_SHA)
            measurement=module.MeasurementGpu(t,self.field_hw,device_limit_bytes=device_limit_bytes)
        require(tuple(measurement.field_hw)==self.field_hw,"measurement global field differs")
        self.measurement=measurement
        self.paired=callable(getattr(measurement,"forward_with_dc",None))
        self.ones=t.ones((*self.field_hw,3),dtype=t.float32,device="cuda:0")
        self.metric_scale=t.zeros((),dtype=t.float32,device="cuda:0")
        self.level_multipliers_f32=None
        self.level_Q_f32=t.zeros(7,dtype=t.float32,device="cuda:0")
        self.level_R_f32=t.zeros_like(self.level_Q_f32)
        level_max=t.zeros_like(self.level_Q_f32)
        ll_max=t.zeros((),dtype=t.float32,device="cuda:0")
        self.calls={"source_preparations":0,"normal":0,"rhs_passes":0,"measure_source":0,"adjoint_source":0,
                    "actual_forward_rectangles":0,"paired_forward_rectangles":0,"adjoint_rectangles":0}
        source_evidence=[]
        # One original-source census freezes global level masses before factors.
        # All N original sensels remain the common count, including omissions.
        for s in self.sources:
            current=self.current_source(s,collect_evidence=True)
            Q,R,maximum,ll=level_statistics(current)
            self.level_Q_f32+=Q;self.level_R_f32+=R
            level_max=t.maximum(level_max,maximum);ll_max=t.maximum(ll_max,ll)
            source_evidence.append(dict(source_id=s.source_id,**current.evidence))
            del current
        self.level_multipliers_f32=resolve_level_balance(t,self.level_Q_f32,self.level_R_f32,metric_override)
        self.metric_scale=t.maximum(ll_max,(level_max*self.level_multipliers_f32).max())
        finite(t,self.metric_scale,"global metric scale")
        require(float(self.metric_scale)>0,"no admitted measurement support")
        self.gram=t.zeros(3,dtype=t.float32,device="cuda:0")
        self.tb=t.zeros_like(self.gram)
        self.G=t.zeros_like(self.ones)
        # Actual T=B*C; the packed single vector contains three disjoint color
        # columns. Do not replace actual odd-boundary detail coefficients by0.
        for s in self.sources:
            current=self.current_source(s)
            factor=current.factors(self.metric_scale,self.count)
            aones,_=self._measure(s,self.ones,need_dc=False)
            column=factor*current.plan.forward(aones)
            rhs=factor*current.d
            self.gram+=self._color_dot(current.plan,column,column)
            self.tb+=self._color_dot(current.plan,column,rhs)
            self._adjoint(s,current.plan.inverse(factor*column),self.G)
            del current,factor,aones,column,rhs
        finite(t,self.gram,"color Gram");finite(t,self.G,"G=B'T")
        require(bool((self.gram>0).all()),"absent or underflowed color-constant support")
        self.rhs_constants=finite(t,self.tb/self.gram,"RHS constants")
        self.projected_rhs=self._rhs_pass(projected=True)
        self.initial_norm=norm_pair(t,self.projected_rhs)
        self.evidence=dict(source_count=len(self.sources),source_ids=[s.source_id for s in self.sources],
            sources=source_evidence,original_sensel_count=self.count,metric_scale_f32=float(self.metric_scale),
            level_balance={"Q_f32":self.level_Q_f32.tolist(),"R_f32":self.level_R_f32.tolist(),
                "multipliers_f32":self.level_multipliers_f32.tolist(),"raw_max_f32":level_max.tolist(),
                "raw_LL_max_f32":float(ll_max),"scope":"all sources/phases/orientations; one multiplier per AC level",
                "LL_unchanged":True,"override_bypasses_balance":metric_override is not None,
                "formula":"q_new=q*sum(1/max(V,1))/sum(q), same admitted support; f32 source-order sums"},
            field_hw=list(self.field_hw),mode=mode,metric_override=None if metric_override is None else float(metric_override),
            supplied_noise=dict(shot4=list(noise.shot4),read_variance_dn2_4=list(noise.read4),
                                black4=list(noise.black4),saturation=noise.saturation),
            color_gram_f32=self.gram.tolist(),T_b_f32=self.tb.tolist(),rhs_constants_f32=self.rhs_constants.tolist(),
            physical_phase_channels=list(bands.PHASE_CHANNEL),green_constant_covers_both_phases=True,
            gram_cross_terms="exact disjoint measured-color supports; each packed band belongs to one color",
            projection="B' P B; coefficient-space nuisance subtraction before each adjoint",
            common_factor="(sqrt(q)/sqrt(global_max_q))/sqrt(all_original_sensel_count)",
            clipping="fixed original code>=saturation omitted through Haar support and3x3 AC admission support",
            measurement_sha256=MEASUREMENT_SHA,cpu_formula_sha256=CPU_SHA,
            paired_forward=self.paired,one_global_field=True,per_source_rgb=False,
            residual_volume=False,factor_volume=False,prior=None,quality_claim=False,admission=False)
        self._budget()

    def _budget(self):
        t=self.torch
        require(max(t.cuda.max_memory_allocated(0),t.cuda.max_memory_reserved(0))<=self.device_limit_bytes,
                "streamed normal Torch budget exceeded")

    def _source(self,source):
        if isinstance(source,Source):
            return source
        found=[s for s in self.sources if s.source_id==source]
        require(len(found)==1,"unknown source ID")
        return found[0]

    def current_source(self,source,collect_evidence=False):
        s=self._source(source)
        codes=s.load_codes()
        require(tuple(codes.shape)==(s.source_xywh[3],s.source_xywh[2]),"loaded original extent differs")
        current=prepare_source(self.torch,codes,s.source_xywh[:2],self.noise,self.mode,self.metric_override,
            frozen_valid=s.frozen_valid,diagnostic_admission_window=self.diagnostic_admission_window,
            collect_evidence=collect_evidence)
        self.calls["source_preparations"]+=1
        if self.level_multipliers_f32 is not None:
            apply_level_balance(current,self.level_multipliers_f32)
        return current

    def _rectangles(self,s):
        ox,oy,w,h=s.source_xywh
        rows=max(1,1048576//w)
        for y in range(0,h,rows):
            count=min(rows,h-y)
            yield y,count,(ox,oy+y,w,count)

    def _measure(self,s,x,need_dc=True):
        t=self.torch
        h,w=s.source_xywh[3],s.source_xywh[2]
        observed=t.empty((h,w),dtype=t.float32,device="cuda:0")
        dc=t.empty_like(observed) if need_dc else None
        for y,count,rect in self._rectangles(s):
            if need_dc and self.paired:
                a,c=self.measurement.forward_with_dc(x,rect,s.affine)
                self.calls["paired_forward_rectangles"]+=1
            else:
                a=self.measurement.forward(x,rect,s.affine)
                self.calls["actual_forward_rectangles"]+=1
                c=self.measurement.forward(self.ones,rect,s.affine) if need_dc else None
                self.calls["actual_forward_rectangles"]+=int(need_dc)
            observed[y:y+count].copy_(a)
            if need_dc:
                dc[y:y+count].copy_(c)
        self.calls["measure_source"]+=1
        return observed,dc

    def _adjoint(self,s,y,out):
        for start,count,rect in self._rectangles(s):
            self.measurement.adjoint(y[start:start+count].contiguous(),rect,s.affine,out=out)
            self.calls["adjoint_rectangles"]+=1
        self.calls["adjoint_source"]+=1
        return out

    def _color_dot(self,plan,left,right):
        t=self.torch
        result=t.zeros(3,dtype=t.float32,device="cuda:0")
        # Sum complete phase ranges, preserving G1/G2 as separate observations.
        for phase,(_,_,entries,low,_) in enumerate(plan._phase):
            start=entries[0][0]["start"] if entries else low["start"]
            end=low["end"]
            c=bands.PHASE_CHANNEL[phase]
            result[c]+=stable_dot(t,left[start:end],right[start:end])
        return result

    def _subtract(self,plan,coefficients,column,amplitudes):
        out=coefficients.clone()
        for phase,(_,_,entries,low,_) in enumerate(plan._phase):
            start=entries[0][0]["start"] if entries else low["start"]
            end=low["end"]
            out[start:end]-=column[start:end]*amplitudes[bands.PHASE_CHANNEL[phase]]
        return finite(self.torch,out,"projected coefficients")

    def constants(self,x):
        return finite(self.torch,self._image_cross(x)/self.gram,"image nuisance coefficients")

    def _image_cross(self,x):
        t=self.torch
        values=t.stack([stable_dot(t,self.G[...,c],x[...,c]) for c in range(3)])
        return finite(t,values,"image nuisance cross product")

    def weighted_forward(self,x,source_id):
        s=self._source(source_id);current=self.current_source(s)
        y,_=self._measure(s,x,need_dc=False)
        return current.factors(self.metric_scale,self.count)*current.plan.forward(y)

    def weighted_adjoint(self,coefficients,source_id):
        s=self._source(source_id);current=self.current_source(s)
        factor=current.factors(self.metric_scale,self.count)
        out=self.torch.zeros_like(self.ones)
        return self._adjoint(s,current.plan.inverse(coefficients*factor),out)

    def normal(self,x,projected=True):
        t=self.torch
        amplitudes=self.constants(x) if projected else None
        out=t.zeros_like(self.ones)
        for s in self.sources:
            current=self.current_source(s)
            factor=current.factors(self.metric_scale,self.count)
            y,dc=self._measure(s,x,need_dc=projected)
            coeff=factor*current.plan.forward(y)
            if projected:
                column=factor*current.plan.forward(dc)
                coeff=self._subtract(current.plan,coeff,column,amplitudes)
            self._adjoint(s,current.plan.inverse(coeff*factor),out)
            if projected:
                del column
            del current,factor,y,dc,coeff
        self.calls["normal"]+=1
        self._budget()
        return finite(t,out,"streamed normal")

    def _rhs_pass(self,projected):
        t=self.torch
        out=t.zeros_like(self.ones)
        for s in self.sources:
            current=self.current_source(s)
            factor=current.factors(self.metric_scale,self.count)
            coeff=factor*current.d
            if projected:
                dc,_=self._measure(s,self.ones,need_dc=False)
                column=factor*current.plan.forward(dc)
                coeff=self._subtract(current.plan,coeff,column,self.rhs_constants)
            self._adjoint(s,current.plan.inverse(coeff*factor),out)
            if projected:
                del dc,column
            del current,factor,coeff
        self.calls["rhs_passes"]+=1
        return finite(t,out,"streamed RHS")

    def rhs(self,projected=True):
        return self.projected_rhs.clone() if projected else self._rhs_pass(False)

    def restore(self,z):
        coefficients=(self.tb-self._image_cross(z))/self.gram
        return finite(self.torch,z+coefficients.reshape(1,1,3),"restored X")

    def evaluate(self,z):
        """Actual final physical residual, objective, full/projected normal."""
        t=self.torch
        x=self.restore(z)
        full=t.zeros_like(x)
        nuisance=t.zeros(3,dtype=t.float32,device="cuda:0")
        objective=norm_pair(t,t.zeros(1,dtype=t.float32,device="cuda:0"))
        for s in self.sources:
            current=self.current_source(s)
            factor=current.factors(self.metric_scale,self.count)
            y,dc=self._measure(s,x,need_dc=True)
            residual=(factor*current.d)-(factor*current.plan.forward(y))
            column=factor*current.plan.forward(dc)
            nuisance+=self._color_dot(current.plan,column,residual)
            objective=objective.add(norm_pair(t,residual))
            self._adjoint(s,current.plan.inverse(residual*factor),full)
            del current,factor,y,dc,residual,column
        # Compute the final projected normal by another coefficient-space pass;
        # never obtain it by subtracting large accumulated global images.
        projected=t.zeros_like(x)
        amplitudes=nuisance/self.gram
        for s in self.sources:
            current=self.current_source(s)
            factor=current.factors(self.metric_scale,self.count)
            y,dc=self._measure(s,x,need_dc=True)
            residual=(factor*current.d)-(factor*current.plan.forward(y))
            column=factor*current.plan.forward(dc)
            residual=self._subtract(current.plan,residual,column,amplitudes)
            self._adjoint(s,current.plan.inverse(residual*factor),projected)
            del current,factor,y,dc,residual,column
        self._budget()
        return {"x":x,"full_normal":finite(t,full,"true full normal"),
                "projected_normal":finite(t,projected,"true projected normal"),
                "nuisance_T_residual":finite(t,nuisance,"true nuisance residual"),
                "nuisance_U_residual":nuisance/t.sqrt(self.gram),
                "objective":objective,"original_objective":objective.scaled(self.metric_scale),
                "restored_constants":(self.tb-self._image_cross(z))/self.gram}

    def metadata(self):
        return {**self.evidence,"calls":dict(self.calls),"measurement":self.measurement.metadata(strict=True),
                "parent_source_unchanged":digest(CPU_PATH)==CPU_SHA and digest(MEASUREMENT_PATH)==MEASUREMENT_SHA}
